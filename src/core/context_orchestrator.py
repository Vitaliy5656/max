"""
Context Orchestrator for MAX AI Assistant.

Unified context assembly from RAG, Memory, and Context Primer.
Provides a single API for building optimized context for LLM requests.

Usage:
    from .context_orchestrator import context_orchestrator
    
    context = await context_orchestrator.build_context(
        query="What did we discuss about astronomy?",
        conversation_id="abc123",
        max_tokens=4000
    )
"""
import time
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Any, TYPE_CHECKING

import aiosqlite

if TYPE_CHECKING:
    from .rag import Chunk
    from .memory import Fact
    from .semantic_router import RouteDecision


@dataclass
class UnifiedContext:
    """Result of context orchestration."""
    messages: list[dict]                    # Final context messages for LLM
    rag_chunks: list[Any] = field(default_factory=list)  # Retrieved documents
    facts: list[Any] = field(default_factory=list)        # Long-term memory facts
    cross_session: list[dict] = field(default_factory=list)  # Cross-conversation context
    primed_context: Optional[str] = None    # ContextPrimer result
    route_decision: Optional[Any] = None    # SemanticRouter decision
    total_tokens: int = 0
    build_time_ms: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "messages_count": len(self.messages),
            "rag_chunks_count": len(self.rag_chunks),
            "facts_count": len(self.facts),
            "cross_session_count": len(self.cross_session),
            "has_primed_context": self.primed_context is not None,
            "total_tokens": self.total_tokens,
            "build_time_ms": round(self.build_time_ms, 2),
            "route": {
                "category": self.route_decision.category.value if self.route_decision else None,
                "confidence": self.route_decision.confidence if self.route_decision else None
            } if self.route_decision else None
        }


class ContextOrchestrator:
    """
    Unified context assembly from RAG, Memory, and Primer.
    
    Orchestrates:
    1. SemanticRouter → route decision (category, model, thinking mode)
    2. ContextPrimer → domain-specific context based on route
    3. MemoryManager → conversation history + facts
    4. RAGEngine → document chunks (if enabled)
    
    Returns optimized context within token budget.
    """
    
    def __init__(self):
        self._db: Optional[aiosqlite.Connection] = None
        self._rag = None
        self._memory = None
        self._primer = None
        self._router = None
        self._lm_client = None
        self._initialized = False
    
    async def initialize(self, db: aiosqlite.Connection, lm_client=None):
        """
        Initialize with database connection.
        
        Args:
            db: SQLite database connection
            lm_client: LM client for embeddings (optional, for router)
        """
        self._db = db
        self._lm_client = lm_client
        
        # Lazy import to avoid circular dependencies
        from .rag import rag
        from .memory import memory
        from .context_primer import context_primer
        from .semantic_router import semantic_router
        
        self._rag = rag
        self._memory = memory
        self._primer = context_primer
        self._router = semantic_router
        
        # Initialize components if not already done
        if lm_client and not self._router._initialized:
            try:
                await self._router.initialize(lm_client)
            except Exception:
                pass  # Router can work with keyword fallback
        
        self._initialized = True
    
    async def build_context(
        self,
        query: str,
        conversation_id: str,
        max_tokens: int = 4000,
        include_rag: bool = True,
        include_facts: bool = True,
        include_cross_session: bool = True,
        include_priming: bool = True,
        has_image: bool = False
    ) -> UnifiedContext:
        """
        Build unified context for LLM request.
        
        Orchestrates all context sources and returns optimized context
        within the specified token budget.
        
        Args:
            query: User's query text
            conversation_id: Current conversation ID
            max_tokens: Maximum context token budget
            include_rag: Whether to include RAG document chunks
            include_facts: Whether to include memory facts
            include_cross_session: Whether to include cross-session context
            include_priming: Whether to include context primer output
            has_image: Whether query includes an image (affects routing)
            
        Returns:
            UnifiedContext with all assembled context
        """
        if not self._initialized:
            raise RuntimeError("ContextOrchestrator not initialized. Call initialize() first.")
        
        start_time = time.time()
        
        # Step 1: Route the query (get category+model+thinking)
        route_decision = None
        query_embedding = None
        
        try:
            if self._router._initialized:
                route_decision, query_embedding = await self._router.route_with_embedding(
                    query, has_image=has_image
                )
            else:
                # Fallback route
                route_decision = self._router._fallback_route(query)
        except Exception:
            route_decision = None
        
        # Step 2: Get primed context based on route
        primed_context = None
        if include_priming and self._primer:
            try:
                primed = await self._primer.get_context(
                    query,
                    category=route_decision.category.value if route_decision else None,
                    query_embedding=query_embedding
                )
                if primed:
                    primed_context = primed.get("context", "")
            except Exception:
                pass  # Priming is optional
        
        # Step 3: Get memory context (parallel with RAG)
        memory_task = self._get_memory_context(
            conversation_id=conversation_id,
            max_tokens=max_tokens // 2,
            include_facts=include_facts,
            include_cross_session=include_cross_session
        )
        
        # Step 4: Get RAG context (parallel with memory)
        rag_task = self._get_rag_context(
            query=query,
            max_tokens=max_tokens // 4,
            query_embedding=query_embedding
        ) if include_rag else asyncio.coroutine(lambda: [])()
        
        # Execute in parallel
        memory_result, rag_chunks = await asyncio.gather(
            memory_task,
            rag_task,
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(memory_result, Exception):
            memory_result = {"messages": [], "facts": [], "cross_session": []}
        if isinstance(rag_chunks, Exception):
            rag_chunks = []
        
        # Extract components from memory result
        messages = memory_result.get("messages", [])
        facts = memory_result.get("facts", [])
        cross_session = memory_result.get("cross_session", [])
        
        # Step 5: Assemble final context messages
        final_messages = self._assemble_messages(
            conversation_messages=messages,
            facts=facts,
            cross_session=cross_session,
            rag_chunks=rag_chunks,
            primed_context=primed_context,
            max_tokens=max_tokens
        )
        
        # Calculate token count and build time
        total_tokens = self._estimate_tokens(final_messages)
        build_time_ms = (time.time() - start_time) * 1000
        
        return UnifiedContext(
            messages=final_messages,
            rag_chunks=rag_chunks if not isinstance(rag_chunks, Exception) else [],
            facts=facts,
            cross_session=cross_session,
            primed_context=primed_context,
            route_decision=route_decision,
            total_tokens=total_tokens,
            build_time_ms=build_time_ms
        )
    
    async def _get_memory_context(
        self,
        conversation_id: str,
        max_tokens: int,
        include_facts: bool,
        include_cross_session: bool
    ) -> dict:
        """Get context from MemoryManager."""
        try:
            result = await self._memory.get_smart_context(
                conversation_id=conversation_id,
                max_tokens=max_tokens,
                include_facts=include_facts,
                include_cross_session=include_cross_session
            )
            return result if result else {"messages": [], "facts": [], "cross_session": []}
        except Exception:
            return {"messages": [], "facts": [], "cross_session": []}
    
    async def _get_rag_context(
        self,
        query: str,
        max_tokens: int,
        query_embedding: Optional[list[float]] = None
    ) -> list:
        """Get context from RAG engine."""
        try:
            if not self._rag:
                return []
            
            # Use pre-computed embedding if available
            if query_embedding and hasattr(self._rag, 'search_by_embedding'):
                chunks = await self._rag.search_by_embedding(
                    query_embedding,
                    max_tokens=max_tokens
                )
            else:
                chunks = await self._rag.get_context_for_query(
                    query,
                    max_tokens=max_tokens
                )
            
            return chunks if chunks else []
        except Exception:
            return []
    
    def _assemble_messages(
        self,
        conversation_messages: list,
        facts: list,
        cross_session: list,
        rag_chunks: list,
        primed_context: Optional[str],
        max_tokens: int
    ) -> list[dict]:
        """Assemble final context messages for LLM."""
        messages = []
        token_count = 0
        
        # 1. Add system context (facts + RAG + priming)
        system_parts = []
        
        # Add primed context first (most relevant)
        if primed_context:
            system_parts.append(f"[Контекст]\n{primed_context}")
        
        # Add relevant facts
        if facts:
            facts_text = "\n".join([
                f"- {f.get('content', f) if isinstance(f, dict) else str(f)}"
                for f in facts[:10]  # Limit to 10 most relevant facts
            ])
            system_parts.append(f"[Память]\n{facts_text}")
        
        # Add RAG chunks
        if rag_chunks:
            rag_texts = []
            for chunk in rag_chunks[:5]:  # Limit to 5 chunks
                if hasattr(chunk, 'content'):
                    rag_texts.append(chunk.content)
                elif isinstance(chunk, dict):
                    rag_texts.append(chunk.get('content', str(chunk)))
                else:
                    rag_texts.append(str(chunk))
            
            if rag_texts:
                system_parts.append(f"[Документы]\n" + "\n---\n".join(rag_texts))
        
        # Create system message if we have context
        if system_parts:
            system_content = "\n\n".join(system_parts)
            # Trim if too long
            if len(system_content) > max_tokens * 4:  # Rough char estimate
                system_content = system_content[:max_tokens * 4] + "\n[...обрезано]"
            
            messages.append({
                "role": "system",
                "content": system_content
            })
            token_count += self._estimate_tokens([messages[-1]])
        
        # 2. Add cross-session context
        remaining_tokens = max_tokens - token_count
        if cross_session and remaining_tokens > 500:
            for msg in cross_session[-3:]:  # Last 3 cross-session messages
                if isinstance(msg, dict):
                    messages.append(msg)
                token_count += 100  # Rough estimate
        
        # 3. Add conversation history
        remaining_tokens = max_tokens - token_count
        if conversation_messages:
            # Take most recent messages that fit
            for msg in reversed(conversation_messages):
                if isinstance(msg, dict):
                    msg_tokens = self._estimate_message_tokens(msg)
                    if token_count + msg_tokens <= max_tokens:
                        messages.insert(-1 if messages else 0, msg)
                        token_count += msg_tokens
                    else:
                        break
        
        return messages
    
    def _estimate_tokens(self, messages: list[dict]) -> int:
        """Estimate token count for messages."""
        total = 0
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get("content", "")
                total += len(content) // 4 + 3  # Rough estimate
        return total
    
    def _estimate_message_tokens(self, msg: dict) -> int:
        """Estimate token count for a single message."""
        content = msg.get("content", "")
        return len(content) // 4 + 3


    def format_past_failures(self, failures: list[str]) -> str:
        """Format past failures for cognitive prompt injection."""
        if not failures:
            return "None"
        return "\n".join([f"- {f}" for f in failures])


# Global instance
context_orchestrator = ContextOrchestrator()
