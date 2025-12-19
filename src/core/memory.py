"""
Memory System with Multi-tier Architecture.

Features:
- Session Memory: Recent messages within token limit
- Summary Memory: Auto-summarization of old messages  
- Facts Database: Extracted key facts about user
- Cross-Session Memory: Semantic search across all conversations
"""
import json
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

import aiosqlite
import tiktoken

from .config import config
from .lm_client import lm_client


# P3 fix: Constants for context allocation (magic numbers extracted)
# SUMMARY_TOKEN_RATIO moved to config
MESSAGES_TOKEN_RATIO = 0.7  # Reserve 70% of tokens for messages
FACTS_TOKEN_RATIO = 0.1  # Reserve 10% of tokens for facts

# Protection against summarization loops
MAX_SUMMARIZATION_RETRIES = 3
_summarization_failures: dict[str, int] = {}  # conversation_id -> failure count


def _log_task_exception(task: asyncio.Task):
    """Log exceptions from background tasks (P1 fix: fire-and-forget)."""
    try:
        exc = task.exception()
        if exc:
            from .logger import log
            log.error(f"Background task error: {exc}")
    except asyncio.CancelledError:
        pass


def _escape_like(query: str) -> str:
    """Escape special characters for SQL LIKE queries (P1 fix: SQL injection)."""
    # Escape %, _, and \ which have special meaning in LIKE
    return query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass
class Message:
    """Represents a conversation message."""
    id: Optional[int] = None
    conversation_id: str = ""
    role: str = "user"  # user, assistant, system, tool
    content: str = ""
    tool_calls: Optional[list] = None
    tokens_used: int = 0
    model_used: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class Fact:
    """Represents an extracted fact for long-term memory."""
    id: Optional[int] = None
    content: str = ""
    category: str = "general"  # personal, preference, project, general
    embedding: Optional[list[float]] = None
    confidence: float = 1.0
    created_at: Optional[datetime] = None


@dataclass
class Conversation:
    """Represents a conversation session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MemoryManager:
    """
    Multi-tier memory system for maintaining conversation context.
    
    Tiers:
    1. Session Memory - Full recent messages
    2. Summary Memory - Compressed older messages
    3. Facts Database - Extracted key information
    4. Cross-Session - Semantic search across history
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.db_path
        self._db: Optional[aiosqlite.Connection] = None
        self._encoder = None  # Lazy loaded
        self._pending_tasks: set[asyncio.Task] = set()  # Track background fact extraction
        
        # Phase 2B: Conversation History RAM Cache
        self._conversation_cache: dict[str, list] = {}  # conv_id -> messages
        self._conversation_locks: dict[str, asyncio.Lock] = {}  # Per-conversation locks
        self._cache_max_conversations = 100  # Limit cached conversations
        
        # Phase 2B: Embedding Cache (RAM optimization - 2x speedup, +50MB RAM)
        self._embedding_cache: dict[int, list[float]] = {}  # fact_id -> embedding
        
    async def initialize(self):
        """Initialize database connection and create tables."""
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row
        
        # Load and execute schema
        schema_path = Path(__file__).parent.parent.parent / "data" / "schema.sql"
        if schema_path.exists():
            schema = schema_path.read_text(encoding="utf-8")
            # Filter out comments and empty lines
            statements = [
                s.strip() for s in schema.split(';') 
                if s.strip()
            ]
            for statement in statements:
                try:
                    await self._db.execute(statement)
                except Exception as e:
                    from .logger import log
                    log.warn(f"Schema warning: {e}")
            await self._db.commit()
            
    async def close(self):
        """Close database connection after waiting for pending tasks."""
        if self._pending_tasks:
            from .logger import log
            log.api(f"⏳ Waiting for {len(self._pending_tasks)} pending extraction tasks...")
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)
        
        if self._db:
            await self._db.close()
            
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        if self._encoder is None:
            self._encoder = tiktoken.get_encoding("cl100k_base")
        return len(self._encoder.encode(text))
    
    # ==================== Conversations ====================
    
    async def create_conversation(self, title: Optional[str] = None) -> Conversation:
        """Create a new conversation."""
        conv = Conversation(title=title)
        await self._db.execute(
            "INSERT INTO conversations (id, title) VALUES (?, ?)",
            (conv.id, conv.title)
        )
        await self._db.commit()
        return conv
    
    async def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        """Get conversation by ID."""
        async with self._db.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return Conversation(
                    id=row["id"],
                    title=row["title"],
                    summary=row["summary"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
        return None
    
    async def list_conversations(self, limit: int = 50, offset: int = 0) -> list[Conversation]:
        """List recent conversations with pagination."""
        async with self._db.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Conversation(
                    id=row["id"],
                    title=row["title"],
                    summary=row["summary"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                for row in rows
            ]

    async def delete_conversation(self, conv_id: str) -> bool:
        """Delete a conversation and all its messages/summaries."""
        # Delete messages first (foreign key constraint)
        await self._db.execute(
            "DELETE FROM messages WHERE conversation_id = ?", (conv_id,)
        )
        # Delete summaries
        await self._db.execute(
            "DELETE FROM conversation_summaries WHERE conversation_id = ?", (conv_id,)
        )
        # Delete conversation
        cursor = await self._db.execute(
            "DELETE FROM conversations WHERE id = ?", (conv_id,)
        )
        await self._db.commit()

        # Clear summarization failure counter
        _summarization_failures.pop(conv_id, None)

        return cursor.rowcount > 0
    
    # ==================== Messages ====================
    
    async def add_message(
        self, 
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: Optional[list] = None,
        model_used: Optional[str] = None
    ) -> Message:
        """Add a message to conversation."""
        tokens = self.count_tokens(content)
        tool_calls_json = json.dumps(tool_calls) if tool_calls else None
        
        cursor = await self._db.execute(
            """INSERT INTO messages 
               (conversation_id, role, content, tool_calls, tokens_used, model_used)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (conversation_id, role, content, tool_calls_json, tokens, model_used)
        )
        await self._db.commit()
        
        # Update conversation timestamp
        await self._db.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )
        await self._db.commit()
        
        # Check if we need to trigger summarization
        await self._maybe_summarize(conversation_id)
        
        # Extract facts from user messages (with error logging)
        if role == "user" and config.memory.extract_facts:
            task = asyncio.create_task(self._extract_facts(cursor.lastrowid, content))
            self._pending_tasks.add(task)
            task.add_done_callback(lambda t: self._pending_tasks.discard(t))
            task.add_done_callback(_log_task_exception)
        
        return Message(
            id=cursor.lastrowid,
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tokens_used=tokens,
            model_used=model_used
        )
    
    async def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> list[Message]:
        """Get messages from conversation."""
        query = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at"
        params = [conversation_id]
        
        if limit:
            query += " DESC LIMIT ?"
            params.append(limit)
            # Reverse to get chronological order
            async with self._db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                rows = list(reversed(rows))
        else:
            async with self._db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
        
        return [
            Message(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=row["role"],
                content=row["content"],
                tool_calls=json.loads(row["tool_calls"]) if row["tool_calls"] else None,
                tokens_used=row["tokens_used"],
                model_used=row["model_used"],
                created_at=row["created_at"]
            )
            for row in rows
        ]
    
    # ==================== Smart Context ====================
    
    async def get_smart_context(
        self,
        conversation_id: str,
        max_tokens: Optional[int] = None,
        include_facts: bool = True,
        include_cross_session: bool = True
    ) -> list[dict]:
        """
        Get optimized context for LLM within token budget.
        
        Strategy:
        1. Include conversation summary if exists
        2. Include recent messages (up to limit)
        3. Include relevant facts
        4. Include cross-session relevant context
        
        IMPORTANT: All system content is consolidated into ONE system message
        to satisfy strict message alternation requirements (System -> User -> Assistant -> ...)
        """
        max_tokens = max_tokens or config.memory.max_context_tokens
        context = []
        tokens_used = 0
        
        # Collect all system content parts
        system_parts = []
        
        # 1. Get conversation summary
        async with self._db.execute(
            """SELECT summary FROM conversation_summaries 
               WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1""",
            (conversation_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row["summary"]:
                summary_msg = f"[Краткое содержание предыдущего разговора: {row['summary']}]"
                tokens = self.count_tokens(summary_msg)
                if tokens_used + tokens < max_tokens * config.memory.summary_token_ratio:
                    system_parts.append(summary_msg)
                    tokens_used += tokens
        
        # 2. Include relevant facts (add to system parts)
        if include_facts:
            facts = await self.get_relevant_facts(
                conversation_id, 
                limit=5,
                max_tokens=int(max_tokens * FACTS_TOKEN_RATIO)
            )
            if facts:
                facts_text = "\n".join([f"• {f.content}" for f in facts])
                facts_msg = f"[Известные факты о пользователе:\n{facts_text}]"
                if tokens_used + self.count_tokens(facts_msg) < max_tokens:
                    system_parts.append(facts_msg)
                    tokens_used += self.count_tokens(facts_msg)
        
        # 3. Build consolidated system message (ONE system message only)
        if system_parts:
            consolidated_system = "\n\n".join(system_parts)
            context.append({"role": "system", "content": consolidated_system})
        
        # 4. Get recent messages (User/Assistant only, no system messages from history)
        messages = await self.get_messages(
            conversation_id, 
            limit=config.memory.max_session_messages
        )
        
        # Add messages from newest to oldest until budget exhausted
        messages_to_add = []
        for msg in reversed(messages):
            # Skip system messages from history (they would break alternation)
            if msg.role == "system":
                continue
            msg_tokens = msg.tokens_used or self.count_tokens(msg.content)
            if tokens_used + msg_tokens > max_tokens * MESSAGES_TOKEN_RATIO:
                break
            messages_to_add.insert(0, {"role": msg.role, "content": msg.content})
            tokens_used += msg_tokens
        
        context.extend(messages_to_add)
        
        return context
    
    # ==================== Summarization ====================
    
    async def _maybe_summarize(self, conversation_id: str):
        """Check if summarization is needed and trigger it with loop protection."""
        # Protection: skip if too many failures for this conversation
        if _summarization_failures.get(conversation_id, 0) >= MAX_SUMMARIZATION_RETRIES:
            return

        async with self._db.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row["cnt"] >= config.memory.summarize_after_messages:
                # Check if we already have a recent summary
                async with self._db.execute(
                    """SELECT messages_covered FROM conversation_summaries
                       WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1""",
                    (conversation_id,)
                ) as cursor:
                    summary_row = await cursor.fetchone()
                    if not summary_row or summary_row["messages_covered"] < row["cnt"] - 10:
                        task = asyncio.create_task(self._safe_compress_history(conversation_id))
                        task.add_done_callback(_log_task_exception)

    async def _safe_compress_history(self, conversation_id: str):
        """Wrapper for compress_history with failure tracking."""
        try:
            result = await self.compress_history(conversation_id)
            if result:
                # Success - reset failure counter
                _summarization_failures.pop(conversation_id, None)
            else:
                # Empty result - count as failure
                _summarization_failures[conversation_id] = _summarization_failures.get(conversation_id, 0) + 1
        except Exception as e:
            _summarization_failures[conversation_id] = _summarization_failures.get(conversation_id, 0) + 1
            raise
    
    async def compress_history(self, conversation_id: str) -> str:
        """
        Summarize older messages to reduce context size.
        """
        # Optimization: Fetch only older messages for summarization
        # Get count first
        async with self._db.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        ) as cursor:
            row = await cursor.fetchone()
            count = row["cnt"]
        
        if count < config.memory.summarize_after_messages:
            return ""

        cutoff = count // 2
        
        # Fetch only top half (oldest)
        query = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?"
        async with self._db.execute(query, (conversation_id, cutoff)) as cursor:
            rows = await cursor.fetchall()
            
        to_summarize = [
            Message(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=row["role"],
                content=row["content"]
            )
            for row in rows
        ]
        
        # Build text for summarization
        text_parts = []
        for msg in to_summarize:
            prefix = "User:" if msg.role == "user" else "Assistant:"
            text_parts.append(f"{prefix} {msg.content[:500]}")  # Truncate long messages
        
        # P1 Fix: Recursive Summarization
        # Retrieve previous summary to ensure we don't lose history
        old_summary = ""
        async with self._db.execute(
            """SELECT summary FROM conversation_summaries 
               WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1""",
            (conversation_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row["summary"]:
                old_summary = row["summary"]

        if old_summary:
            summarize_prompt = f"""У нас есть краткое содержание предыдущей части разговора:
"{old_summary}"

А вот новые сообщения:
{chr(10).join(text_parts)}

Задача: Обнови краткое содержание, объединив старое резюме и новую информацию.
Итоговое резюме должно быть связным текстом (2-4 предложения), охватывающим ВЕСЬ разговор целиком.

Новое резюме:"""
        else:
            summarize_prompt = f"""Кратко суммируй основные темы и ключевые моменты этого разговора (2-3 предложения):

{chr(10).join(text_parts)}

Резюме:"""
        
        try:
            summary = await lm_client.chat(
                messages=[{"role": "user", "content": summarize_prompt}],
                stream=False,
                max_tokens=300 # Increased for combined summary
            )
            
            # Save summary
            await self._db.execute(
                """INSERT INTO conversation_summaries 
                   (conversation_id, summary, messages_covered) VALUES (?, ?, ?)""",
                (conversation_id, summary, len(to_summarize))
            )
            await self._db.commit()
            
            return summary
            return summary
        except Exception as e:
            from .logger import log
            log.error(f"Summarization error: {e}")
            return ""
    
    # ==================== Facts Database ====================
    
    async def _extract_facts(self, message_id: int, content: str):
        """
        Extract facts from user message using LM Studio JSON mode with GBNF grammar.
        
        Uses response_format with JSON Schema to guarantee valid structured output
        via server-side token constraint (no parsing required).
        """
        if len(content) < 10:  # Too short to contain facts
            return
        
        from .logger import log
        log.api(f"🔍 FACT EXTRACTION STARTED for message {message_id}: '{content[:100]}...'")
        
        try:
            import json
            
            # Define JSON Schema for structured fact extraction
            json_schema = {
                "type": "json_schema",
                "json_schema": {
                    "name": "extracted_facts",
                    "strict": True,  # Enable GBNF grammar enforcement
                    "schema": {
                        "type": "object",
                        "properties": {
                            "personal_facts": {
                                "type": "array",
                                "description": "Personal information: name, age, location, family, etc.",
                                "items": {"type": "string"}
                            },
                            "preference_facts": {
                                "type": "array",
                                "description": "Interests, hobbies, likes, dislikes, favorites",
                                "items": {"type": "string"}
                            },
                            "project_facts": {
                                "type": "array",
                                "description": "Work, profession, current projects, skills",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["personal_facts", "preference_facts", "project_facts"],
                        "additionalProperties": False
                    }
                }
            }
            
            # Craft extraction prompt
            extract_prompt = f"""Extract ALL facts about the user from their message.

USER MESSAGE: "{content}"

Instructions:
- Extract ANY personal information (name, age, location, family)
- Extract ALL preferences (hobbies, interests, likes, dislikes)
- Extract ALL work/project information (profession, current work, skills)
- If a category has no facts, return empty array
- Be thorough and extract EVERYTHING relevant

Respond with valid JSON matching the schema."""

            # Call LM Studio with JSON Schema enforcement
            response = await lm_client.client.chat.completions.create(
                model=config.memory.extraction_model,
                messages=[{"role": "user", "content": extract_prompt}],
                response_format=json_schema,  # GBNF grammar enforcement
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=400  # Enough for multiple facts
            )
            
            # Parse guaranteed-valid JSON
            facts_data = json.loads(response.choices[0].message.content)
            
            log.api(f"📝 Extracted JSON: {json.dumps(facts_data, ensure_ascii=False)[:200]}...")
            
            # Save extracted facts to database
            facts_added = 0
            
            for fact in facts_data.get("personal_facts", []):
                if fact and len(fact.strip()) > 3:
                    await self.add_fact(fact.strip(), "personal", message_id)
                    log.api(f"💾 Personal fact saved: {fact}")
                    facts_added += 1
            
            for fact in facts_data.get("preference_facts", []):
                if fact and len(fact.strip()) > 3:
                    await self.add_fact(fact.strip(), "preference", message_id)
                    log.api(f"💾 Preference fact saved: {fact}")
                    facts_added += 1
            
            for fact in facts_data.get("project_facts", []):
                if fact and len(fact.strip()) > 3:
                    await self.add_fact(fact.strip(), "project", message_id)
                    log.api(f"💾 Project fact saved: {fact}")
                    facts_added += 1
            
            if facts_added > 0:
                log.api(f"✨ УСПЕХ: {facts_added} факт(ов) извлечено и сохранено (message {message_id})")
            else:
                log.api(f"📭 Фактов не обнаружено в сообщении {message_id}")
                
        except json.JSONDecodeError as e:
            log.error(f"❌ JSON parsing failed (should never happen with schema): {e}")
            log.error(f"   Response was: {response.choices[0].message.content[:200]}")
        except Exception as e:
            log.error(f"❌ Fact extraction error: {e}")
            import traceback
            log.error(traceback.format_exc())
    
    async def _extract_with_model(self, prompt: str, max_tokens: int = 200) -> str:
        """
        Call extraction model via LM Studio API.
        
        Simple approach: just call the model through API.
        LM Studio will handle loading if needed.
        """
        from .logger import log
        
        extraction_model = config.memory.extraction_model
        
        try:
            log.debug(f"🤖 Calling extraction model: {extraction_model}")
            
            # Direct API call - let LM Studio handle the model
            response = await lm_client.client.chat.completions.create(
                model=extraction_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.1,
                stream=False
            )
            
            content = response.choices[0].message.content or ""
            log.debug(f"✅ Extraction complete ({len(content)} chars)")
            
            return content
            
        except Exception as e:
            log.error(f"Extraction failed: {e}")
            log.warn(f"Make sure {extraction_model} is available in LM Studio")
            return ""
    
    async def add_fact(
        self, 
        content: str, 
        category: str = "general",
        source_message_id: Optional[int] = None
    ) -> Fact:
        """Add a fact to long-term memory."""
        from .logger import log
        
        try:
            log.debug(f"💾 Attempting to save fact: [{category}] {content[:50]}...")
            
            # Logic Fix: Deduplication
            async with self._db.execute(
                "SELECT * FROM memory_facts WHERE content = ? LIMIT 1",
                (content,)
            ) as cursor:
                existing = await cursor.fetchone()
                if existing:
                    log.debug(f"⚠️ Fact already exists (ID: {existing['id']})")
                    return Fact(
                        id=existing["id"],
                        content=existing["content"],
                        category=existing["category"],
                        embedding=json.loads(existing["embedding"].decode()) if existing["embedding"] else None
                    )

            # Get embedding for semantic search (optional - fallback works without)
            log.debug("🔢 Generating embedding...")
            try:
                embedding = await lm_client.get_embedding(content)
                if not embedding or len(embedding) == 0:
                    log.warn(f"⚠️ Embedding empty (LM Studio embedding model not loaded) - saving without embedding")
                    log.warn(f"   Fact will still work via fallback search")
                    embedding = None
                else:
                    log.debug(f"✅ Embedding generated: {len(embedding)} dimensions")
            except Exception as e:
                log.debug(f"Embedding generation skipped: {e}")
                embedding = None
            
            embedding_blob = json.dumps(embedding).encode() if embedding else None
            
            # Save to database
            log.debug("💿 Writing to database...")
            cursor = await self._db.execute(
                """INSERT INTO memory_facts (content, category, embedding, source_message_id)
                   VALUES (?, ?, ?, ?)""",
                (content, category, embedding_blob, source_message_id)
            )
            await self._db.commit()
            
            fact_id = cursor.lastrowid
            
            # Verify persistence
            async with self._db.execute(
                "SELECT id FROM memory_facts WHERE id = ?", (fact_id,)
            ) as verify_cursor:
                verified = await verify_cursor.fetchone()
                if not verified:
                    log.error(f"❌ CRITICAL: Fact {fact_id} not found after commit!")
                else:
                    log.api(f"✅ FACT SAVED TO DATABASE (ID: {fact_id})")
            
            return Fact(
                id=fact_id,
                content=content,
                category=category,
                embedding=embedding
            )
        
        except Exception as e:
            log.error(f"❌ FAILED TO SAVE FACT: {e}")
            import traceback
            log.error(traceback.format_exc())
            # Return dummy to avoid crashing extraction
            return Fact(id=-1, content=content, category=category, embedding=None)
    
    async def get_relevant_facts(
        self,
        conversation_id: str,
        limit: int = 5,
        max_tokens: int = 500,
        category: Optional[str] = None,
        query: Optional[str] = None
    ) -> list[Fact]:
        """Get facts relevant to current conversation using semantic similarity.
        
        Args:
            conversation_id: Conversation ID for context
            limit: Maximum facts to return
            max_tokens: Token budget
            category: Filter by category ("general", "work", "shadow", "vault")
            query: Optional custom query for semantic search
        """
        # Get recent user messages for context
        messages = await self.get_messages(conversation_id, limit=5)
        user_messages = [m for m in messages if m.role == "user"]

        if not user_messages:
            return []

        # Build query from recent messages or use provided query
        if query:
            query_text = query
        else:
            query_text = " ".join([m.content for m in user_messages[-3:]])

        # Try semantic search with embeddings
        query_embedding = await lm_client.get_embedding(query_text)

        if query_embedding:
            # Build SQL query with optional category filter
            sql = "SELECT * FROM memory_facts WHERE embedding IS NOT NULL"
            params = []
            if category:
                sql += " AND category = ?"
                params.append(category)
            
            async with self._db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()

            # Calculate relevance scores with embedding cache
            scored_facts = []
            for row in rows:
                try:
                    fact_id = row["id"]
                    # Check embedding cache first (RAM optimization)
                    if fact_id in self._embedding_cache:
                        fact_embedding = self._embedding_cache[fact_id]
                    else:
                        fact_embedding = json.loads(row["embedding"].decode())
                        self._embedding_cache[fact_id] = fact_embedding
                    
                    score = self._cosine_similarity(query_embedding, fact_embedding)
                    scored_facts.append((row, score))
                except (json.JSONDecodeError, AttributeError):
                    continue

            # Sort by relevance
            scored_facts.sort(key=lambda x: x[1], reverse=True)
            rows = [sf[0] for sf in scored_facts[:limit * 2]]  # Get more for token filtering
        else:
            # Fallback: get ALL facts (no embedding-based filtering)
            from .logger import log
            log.warn("No embeddings available for semantic search, using fallback")
            
            # Build SQL with optional category filter
            sql = "SELECT * FROM memory_facts"
            params = []
            if category:
                sql += " WHERE category = ?"
                params.append(category)
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit * 2)
            
            async with self._db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()

        # Filter by token budget
        facts = []
        tokens = 0
        for row in rows:
            if len(facts) >= limit:
                break
            fact = Fact(
                id=row["id"],
                content=row["content"],
                category=row["category"],
                embedding=json.loads(row["embedding"].decode()) if row["embedding"] else None
            )
            fact_tokens = self.count_tokens(fact.content)
            if tokens + fact_tokens > max_tokens:
                break
            facts.append(fact)
            tokens += fact_tokens

            # Update last_accessed
            await self._db.execute(
                "UPDATE memory_facts SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                (row["id"],)
            )

        await self._db.commit()
        return facts

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        
        # Optimization: Use inner product
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a)
        norm_b = sum(x * x for x in b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / ((norm_a ** 0.5) * (norm_b ** 0.5))

    async def delete_fact(self, fact_id: int) -> bool:
        """Delete a fact from memory."""
        cursor = await self._db.execute(
            "DELETE FROM memory_facts WHERE id = ?", (fact_id,)
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def update_fact(self, fact_id: int, content: str, category: Optional[str] = None) -> bool:
        """Update an existing fact."""
        # Get new embedding
        embedding = await lm_client.get_embedding(content)
        embedding_blob = json.dumps(embedding).encode() if embedding else None

        if category:
            cursor = await self._db.execute(
                """UPDATE memory_facts
                   SET content = ?, category = ?, embedding = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (content, category, embedding_blob, fact_id)
            )
        else:
            cursor = await self._db.execute(
                """UPDATE memory_facts
                   SET content = ?, embedding = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (content, embedding_blob, fact_id)
            )
        await self._db.commit()
        return cursor.rowcount > 0

    async def list_facts(self, category: Optional[str] = None, limit: int = 50) -> list[Fact]:
        """List all facts, optionally filtered by category."""
        if category:
            query = "SELECT * FROM memory_facts WHERE category = ? ORDER BY created_at DESC LIMIT ?"
            params = (category, limit)
        else:
            query = "SELECT * FROM memory_facts ORDER BY created_at DESC LIMIT ?"
            params = (limit,)

        async with self._db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [
            Fact(
                id=row["id"],
                content=row["content"],
                category=row["category"],
                confidence=row["confidence"],
                created_at=row["created_at"]
            )
            for row in rows
        ]
    
    # ==================== Search ====================
    
    async def search_history(
        self,
        query: str,
        limit: int = 20
    ) -> list[Message]:
        """Full-text search across all messages."""
        # Escape special SQL LIKE characters for safety
        escaped_query = _escape_like(query)
        async with self._db.execute(
            """SELECT m.*, c.title as conv_title 
               FROM messages m 
               JOIN conversations c ON m.conversation_id = c.id
               WHERE m.content LIKE ? ESCAPE '\\'
               ORDER BY m.created_at DESC LIMIT ?""",
            (f"%{escaped_query}%", limit)
        ) as cursor:
            rows = await cursor.fetchall()
            
        return [
            Message(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"]
            )
            for row in rows
        ]


# Global memory manager instance
memory = MemoryManager()
