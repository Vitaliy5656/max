"""
Research Agent Module

Orchestrates research with 3-pass LLM pipeline:
1. MINER: Extract raw facts (JSON mode)
2. JEWELER: Polish facts into knowledge base entry
3. DIPLOMA: Generate Topic Lens skill

Features:
- Query generation for comprehensive coverage
- Dual parsing with fallback
- Fact deduplication via embedding similarity
- Source and stats tracking
- Topic status management
"""

import asyncio
import json
from typing import Optional
from dataclasses import dataclass, field

from .storage import research_storage
from .parser import DualParser


# Configuration
MAX_CHUNK_TOKENS = 6000
DEDUP_SIMILARITY_THRESHOLD = 0.9
DEFAULT_MAX_PAGES = 10


# LLM Prompts
QUERY_GENERATOR_PROMPT = """Generate 5-7 search queries to comprehensively research this topic.

Topic: {topic}
Description: {description}

Return ONLY a JSON array of search queries, no explanation:
["query 1", "query 2", ...]"""


MINER_PROMPT = """Extract ALL factual information from this text.

OUTPUT FORMAT (JSON):
{{
  "entities": ["name1", "name2"],
  "dates": ["date1", "date2"],
  "numbers": ["stat1", "stat2"],
  "claims": ["fact1", "fact2", "fact3"]
}}

Be thorough. Include:
- Names of people, organizations, places
- Specific dates and time periods
- Numbers, statistics, measurements
- Key claims and factual statements

TEXT:
{content}

JSON:"""


JEWELER_PROMPT = """You are an academic editor. Transform these raw facts into a polished knowledge base entry.

REQUIREMENTS:
- Academic, encyclopedic style
- Well-structured paragraphs
- Remove duplicates and contradictions
- Cite sources when available
- Be comprehensive but concise

RAW FACTS:
{facts}

KNOWLEDGE BASE ENTRY:"""


DIPLOMA_PROMPT = """Based on this knowledge base entry, create a "Topic Lens" - a short system prompt 
that would make an AI assistant an expert on this topic.

The Topic Lens should:
- Be 3-5 sentences
- Capture the key expertise areas
- Include specific facts/numbers that demonstrate expertise
- Be written as instructions for an AI

EXAMPLE Topic Lens for "Astrophotography":
"You are an expert in astrophotography. You know that modern CMOS sensors have replaced CCDs for most applications due to their lower read noise. You understand that tracking accuracy of 1 arcsecond is needed for 1000mm focal length. You can recommend appropriate ISO settings and stacking techniques."

KNOWLEDGE BASE ENTRY:
{summary}

TOPIC LENS:"""


@dataclass
class ResearchStats:
    """Statistics for a research run."""
    pages_found: int = 0
    pages_processed: int = 0
    pages_skipped: int = 0
    parser_trafilatura: int = 0
    parser_bs4: int = 0
    facts_raw: int = 0
    facts_unique: int = 0


class ResearchAgent:
    """
    Orchestrates research with 3-pass LLM pipeline.
    
    Flow:
    1. Generate search queries
    2. Search & parse pages
    3. PASS 1 (Miner): Extract raw facts
    4. Deduplicate facts via embedding similarity
    5. PASS 2 (Jeweler): Polish into KB entry
    6. PASS 3 (Diploma): Generate Topic Lens
    7. Store in ChromaDB
    """
    
    def __init__(self):
        self._parser = DualParser()
        self._storage = research_storage
        self._web_searcher = None
        self._llm_client = None
        self._embedding_service = None
        self._rate_limiter = None
    
    async def initialize(self, llm_client, embedding_service, web_searcher, rate_limiter=None):
        """Initialize with required services."""
        self._llm_client = llm_client
        self._embedding_service = embedding_service
        self._web_searcher = web_searcher
        self._rate_limiter = rate_limiter or AsyncRateLimiter()
    
    async def research(
        self,
        topic: str,
        description: str,
        max_pages: int = DEFAULT_MAX_PAGES,
        progress_callback=None
    ) -> str:
        """
        Execute full research pipeline.
        
        Returns topic_id on success.
        Topic starts as 'incomplete', marked 'complete' only on success.
        """
        if not self._llm_client:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        # Create topic with incomplete status
        topic_id = await self._storage.create_topic(topic, description, status="incomplete")
        
        try:
            # Progress helper
            async def report(stage: str, detail: str = "", progress: float = 0):
                if progress_callback:
                    await progress_callback(stage, detail, progress)
            
            await report("planning", f"Generating queries for: {topic}", 0.05)
            
            # 1. Generate search queries
            queries = await self._generate_queries(topic, description)
            
            await report("hunting", f"Found {len(queries)} queries", 0.1)
            
            # 2. Hunt for pages
            all_facts = []
            sources = []
            stats = ResearchStats()
            
            for i, query in enumerate(queries):
                if stats.pages_processed >= max_pages:
                    break
                
                progress = 0.1 + (i / len(queries)) * 0.3
                await report("hunting", f"Searching: {query[:50]}...", progress)
                
                # Rate limit
                if self._rate_limiter:
                    await self._rate_limiter.acquire()
                
                # Search
                try:
                    results = await self._web_searcher.search(query, max_results=5)
                    stats.pages_found += len(results)
                except Exception:
                    continue
                
                # Process each result
                for result in results:
                    if stats.pages_processed >= max_pages:
                        break
                    
                    try:
                        html = await self._fetch_page(result.url)
                        if not html:
                            stats.pages_skipped += 1
                            continue
                        
                        parsed = await self._parser.extract(result.url, html)
                        
                        if parsed.parser_used == "skipped":
                            stats.pages_skipped += 1
                            continue
                        
                        # Track parser stats
                        if parsed.parser_used == "trafilatura":
                            stats.parser_trafilatura += 1
                        else:
                            stats.parser_bs4 += 1
                        
                        sources.append(result.url)
                        
                        await report("mining", f"Extracting facts from: {result.url[:40]}...", progress)
                        
                        # 3. PASS 1: Mine facts
                        facts = await self._mine(parsed.content)
                        all_facts.extend(facts)
                        stats.pages_processed += 1
                        
                    except Exception:
                        stats.pages_skipped += 1
            
            stats.facts_raw = len(all_facts)
            
            await report("mining", f"Extracted {len(all_facts)} raw facts", 0.5)
            
            # 4. Deduplicate facts
            unique_facts = await self._deduplicate_facts(all_facts)
            stats.facts_unique = len(unique_facts)
            
            await report("polishing", f"Polishing {len(unique_facts)} unique facts", 0.6)
            
            # 5. PASS 2: Polish into KB entry
            kb_entry = await self._polish(unique_facts)
            
            await report("polishing", "Creating knowledge base entry", 0.75)
            
            # 6. Store in ChromaDB
            await self._storage.add_chunk(topic_id, kb_entry, {
                "type": "knowledge_base",
                "topic": topic,
                "facts_count": len(unique_facts),
                "sources": sources[:10],  # Limit sources in metadata
                "stats": {
                    "pages_found": stats.pages_found,
                    "pages_processed": stats.pages_processed,
                    "pages_skipped": stats.pages_skipped,
                    "parser_trafilatura": stats.parser_trafilatura,
                    "parser_bs4": stats.parser_bs4,
                    "facts_raw": stats.facts_raw,
                    "facts_unique": stats.facts_unique
                }
            })
            
            await report("diploma", "Generating Topic Lens", 0.85)
            
            # 7. PASS 3: Generate skill
            skill = await self._generate_skill(kb_entry)
            await self._storage.save_skill(topic_id, skill)
            
            # Mark topic as complete
            await self._storage.update_topic_status(topic_id, "complete")
            
            await report("complete", f"Research complete! {stats.facts_unique} facts stored.", 1.0)
            
            return topic_id
            
        except asyncio.CancelledError:
            # On cancel, topic remains "incomplete"
            # User can see partial topic in UI and decide to delete or retry
            raise
        except Exception as e:
            # Mark as failed but keep partial data
            await self._storage.update_topic_status(topic_id, "failed")
            raise
    
    async def research_into_existing(
        self,
        topic_id: str,
        topic: str,
        description: str,
        max_pages: int = DEFAULT_MAX_PAGES,
        progress_callback=None
    ):
        """
        Add new research data to an EXISTING topic.
        Used by refresh - doesn't create new topic.
        """
        if not self._llm_client:
            raise RuntimeError("Agent not initialized")
        
        try:
            async def report(stage: str, detail: str = "", progress: float = 0):
                if progress_callback:
                    await progress_callback(stage, detail, progress)
            
            await report("planning", f"Refreshing: {topic}", 0.05)
            
            queries = await self._generate_queries(topic, description)
            
            all_facts = []
            sources = []
            stats = ResearchStats()
            
            for i, query in enumerate(queries):
                if stats.pages_processed >= max_pages:
                    break
                
                progress = 0.1 + (i / len(queries)) * 0.3
                await report("hunting", f"Searching: {query[:50]}...", progress)
                
                if self._rate_limiter:
                    await self._rate_limiter.acquire()
                
                try:
                    results = await self._web_searcher.search(query, max_results=5)
                    stats.pages_found += len(results)
                except Exception:
                    continue
                
                for result in results:
                    if stats.pages_processed >= max_pages:
                        break
                    
                    try:
                        html = await self._fetch_page(result.url)
                        if not html:
                            stats.pages_skipped += 1
                            continue
                        
                        parsed = await self._parser.extract(result.url, html)
                        if parsed.parser_used == "skipped":
                            stats.pages_skipped += 1
                            continue
                        
                        if parsed.parser_used == "trafilatura":
                            stats.parser_trafilatura += 1
                        else:
                            stats.parser_bs4 += 1
                        
                        sources.append(result.url)
                        facts = await self._mine(parsed.content)
                        all_facts.extend(facts)
                        stats.pages_processed += 1
                        
                    except Exception:
                        stats.pages_skipped += 1
            
            stats.facts_raw = len(all_facts)
            unique_facts = await self._deduplicate_facts(all_facts)
            stats.facts_unique = len(unique_facts)
            
            await report("polishing", f"Polishing {len(unique_facts)} facts", 0.6)
            
            kb_entry = await self._polish(unique_facts)
            
            # Add to EXISTING topic
            await self._storage.add_chunk(topic_id, kb_entry, {
                "type": "knowledge_base_refresh",
                "topic": topic,
                "facts_count": len(unique_facts),
                "sources": sources[:10],
                "stats": {
                    "pages_found": stats.pages_found,
                    "pages_processed": stats.pages_processed,
                    "pages_skipped": stats.pages_skipped,
                    "facts_raw": stats.facts_raw,
                    "facts_unique": stats.facts_unique
                }
            })
            
            await report("diploma", "Regenerating Topic Lens", 0.85)
            
            # Regenerate skill with all data
            skill = await self._generate_skill(kb_entry)
            await self._storage.save_skill(topic_id, skill)
            
            await report("complete", "Refresh complete!", 1.0)
            
        except asyncio.CancelledError:
            raise
    
    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch page HTML content."""
        try:
            return await self._web_searcher.read_page(url)
        except Exception:
            return None
    
    async def _generate_queries(self, topic: str, description: str) -> list[str]:
        """Generate search queries using LLM."""
        prompt = QUERY_GENERATOR_PROMPT.format(topic=topic, description=description)
        
        try:
            response = await self._llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                json_mode=True
            )
            
            # Parse JSON array
            queries = json.loads(response)
            if isinstance(queries, list):
                return queries[:10]  # Limit queries
        except Exception:
            pass
        
        # Fallback: basic queries
        return [
            f"{topic}",
            f"{topic} overview",
            f"{topic} facts",
            f"{topic} guide",
            f"what is {topic}"
        ]
    
    async def _mine(self, content: str) -> list[str]:
        """
        PASS 1: Extract raw facts from content.
        Uses JSON mode for structured output.
        """
        # Chunk if too long
        chunks = self._chunk_by_tokens(content, MAX_CHUNK_TOKENS)
        all_facts = []
        
        for chunk in chunks:
            prompt = MINER_PROMPT.format(content=chunk)
            
            try:
                response = await self._llm_client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    json_mode=True
                )
                
                data = json.loads(response)
                
                # Collect all facts
                if isinstance(data, dict):
                    for key in ["entities", "dates", "numbers", "claims"]:
                        if key in data and isinstance(data[key], list):
                            all_facts.extend(str(f) for f in data[key] if f)
                            
            except Exception:
                # If JSON parsing fails, try to extract plain text facts
                all_facts.append(chunk[:500])
        
        return all_facts
    
    async def _deduplicate_facts(self, facts: list[str]) -> list[str]:
        """Remove duplicate facts using embedding similarity."""
        if not facts or not self._embedding_service:
            return facts
        
        unique = []
        embeddings = []
        
        for fact in facts:
            if not fact or len(fact) < 10:
                continue
            
            try:
                emb = await self._embedding_service.get_or_compute(fact)
                if not emb:
                    unique.append(fact)
                    continue
                
                # Check similarity with existing
                is_duplicate = False
                for existing_emb in embeddings:
                    similarity = self._cosine_similarity(emb, existing_emb)
                    if similarity > DEDUP_SIMILARITY_THRESHOLD:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique.append(fact)
                    embeddings.append(emb)
                    
            except Exception:
                unique.append(fact)
        
        return unique
    
    def _cosine_similarity(self, a: list, b: list) -> float:
        """Compute cosine similarity between two vectors."""
        import math
        
        if len(a) != len(b):
            return 0.0
        
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot / (norm_a * norm_b)
    
    async def _polish(self, facts: list[str]) -> str:
        """
        PASS 2: Polish facts into knowledge base entry.
        """
        if not facts:
            return "No facts collected during research."
        
        # Combine facts
        facts_text = "\n".join(f"- {fact}" for fact in facts[:100])  # Limit
        
        prompt = JEWELER_PROMPT.format(facts=facts_text)
        
        try:
            response = await self._llm_client.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            return response
        except Exception:
            return facts_text
    
    async def _generate_skill(self, summary: str) -> str:
        """
        PASS 3: Generate Topic Lens (skill) from summary.
        """
        prompt = DIPLOMA_PROMPT.format(summary=summary)
        
        try:
            response = await self._llm_client.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            return response
        except Exception:
            return f"You have knowledge about this topic based on: {summary[:200]}..."
    
    def _chunk_by_tokens(self, text: str, max_tokens: int) -> list[str]:
        """Split text into chunks by approximate token count."""
        # Rough estimate: 1 token ≈ 4 chars
        max_chars = max_tokens * 4
        
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split by paragraphs
        paragraphs = text.split('\n\n')
        
        for para in paragraphs:
            if len(current_chunk) + len(para) <= max_chars:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text[:max_chars]]


class AsyncRateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, requests: int = 40, period: float = 60):
        self._requests = requests
        self._period = period
        self._timestamps = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait if rate limit reached."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            
            # Remove old timestamps
            self._timestamps = [t for t in self._timestamps if now - t < self._period]
            
            if len(self._timestamps) >= self._requests:
                # Wait until oldest expires
                wait_time = self._period - (now - self._timestamps[0])
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                self._timestamps = self._timestamps[1:]
            
            self._timestamps.append(now)


# Global instance
research_agent = ResearchAgent()
