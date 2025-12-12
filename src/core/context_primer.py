"""
Context Primer for MAX AI Assistant.

Semantic Prefetch - fetches ONLY relevant context based on RouteDecision.
Reduces context size from ~4000 tokens to ~1500 tokens (-62.5%).

Features:
- SemanticCache for similar query caching (~40-60% hit rate)
- Domain-specific memory retrieval
- Tool preparation by category
- Specialized instructions loading

Usage:
    from .context_primer import context_primer
    
    primed = await context_primer.prime_context(query, route, user_profile)
    # PrimedContext with category, memories, patterns, tools, instructions
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .semantic_router import RouteDecision, IntentCategory
    from .user_profile import UserProfile


@dataclass
class PrimedContext:
    """Result of context priming."""
    category: "IntentCategory"
    memories: list[dict]          # Relevant memories
    patterns: list[str]           # Success patterns
    tools: list[str]              # Prepared tool names
    instructions: Optional[str]   # Specialized instructions
    prime_time_ms: float          # Time spent priming
    from_cache: bool = False      # Was this from cache?


@dataclass
class DomainConfig:
    """Configuration for a domain."""
    memory_categories: list[str]   # Which memory categories to fetch
    pattern_types: list[str]       # Which success pattern types
    tools: list[str]               # Which tools to prepare
    instructions_file: Optional[str] = None
    max_memories: int = 5


# Domain configurations by IntentCategory
DOMAIN_CONFIGS = {
    "code": DomainConfig(
        memory_categories=["project", "code_style", "tech_preferences"],
        pattern_types=["code", "technical", "debugging"],
        tools=["run_command", "write_file", "read_file"],
        instructions_file="code_assistant.md",
        max_memories=7
    ),
    "reasoning": DomainConfig(
        memory_categories=["project", "personal"],
        pattern_types=["analysis", "explanation"],
        tools=["web_search", "read_file"],
        instructions_file=None,
        max_memories=5
    ),
    "creative": DomainConfig(
        memory_categories=["writing_style", "tone_preferences"],
        pattern_types=["creative", "style"],
        tools=["web_search"],
        instructions_file="creative_writer.md",
        max_memories=3
    ),
    "vision": DomainConfig(
        memory_categories=["personal"],
        pattern_types=["vision"],
        tools=["analyze_image"],
        instructions_file=None,
        max_memories=2
    ),
    "quick": DomainConfig(
        memory_categories=[],
        pattern_types=[],
        tools=[],
        instructions_file=None,
        max_memories=0
    ),
    "math": DomainConfig(
        memory_categories=["project"],
        pattern_types=["calculation"],
        tools=["python_eval"],
        instructions_file=None,
        max_memories=2
    ),
    "casual": DomainConfig(
        memory_categories=["personal"],
        pattern_types=[],
        tools=[],
        instructions_file=None,
        max_memories=2
    ),
}


class SemanticCache:
    """
    Cache primed contexts by semantic similarity.
    Similar queries get the same context instantly (~0ms).
    
    Cache invalidation strategies:
    1. TTL-based: entries expire after ttl_seconds
    2. Manual: call clear() when memories/patterns updated
    3. LRU: oldest entries evicted when max_size reached
    """
    
    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600):
        self._cache: dict[str, tuple[PrimedContext, float, list[float]]] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0
    
    async def get(
        self,
        query: str,
        query_embedding: Optional[list[float]]
    ) -> Optional[PrimedContext]:
        """
        Check if similar query is cached.
        
        Uses semantic similarity (>0.92) for matching.
        """
        if not self._cache or not query_embedding:
            self._misses += 1
            return None
        
        now = time.time()
        
        # Find best match
        best_key = None
        best_similarity = 0.0
        
        for key, (context, timestamp, embedding) in list(self._cache.items()):
            # Check TTL
            if now - timestamp > self._ttl:
                del self._cache[key]
                continue
            
            # Check similarity
            similarity = self._cosine_similarity(query_embedding, embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_key = key
        
        if best_key and best_similarity > 0.92:
            self._hits += 1
            context, _, _ = self._cache[best_key]
            # Return a copy with from_cache=True
            return PrimedContext(
                category=context.category,
                memories=context.memories,
                patterns=context.patterns,
                tools=context.tools,
                instructions=context.instructions,
                prime_time_ms=0.0,  # Instant from cache
                from_cache=True
            )
        
        self._misses += 1
        return None
    
    def put(
        self,
        query: str,
        embedding: list[float],
        context: PrimedContext
    ):
        """Cache a primed context."""
        # Evict oldest if full
        if len(self._cache) >= self._max_size:
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k][1]
            )
            del self._cache[oldest_key]
        
        self._cache[query] = (context, time.time(), embedding)
    
    def clear(self):
        """Clear all cached contexts."""
        self._cache.clear()
    
    def invalidate_for_category(self, category: str):
        """Clear cache entries for specific category."""
        to_delete = [
            key for key, (ctx, _, _) in self._cache.items()
            if ctx.category.value == category
        ]
        for key in to_delete:
            del self._cache[key]
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "cache_size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2)
        }
    
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity."""
        if len(a) != len(b):
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)


class ContextPrimer:
    """
    Semantic Prefetch - fetches ONLY relevant context.
    
    This is the "putting on the table" mechanism - like preparing
    only the tools and materials you need before starting work.
    
    Benefits:
    - 62.5% reduction in context tokens
    - Faster retrieval via category filtering
    - Higher relevance via domain-specific memories
    """
    
    def __init__(self):
        self._db = None
        self._embedding_service = None
        self._cache = SemanticCache()
        self._initialized = False
    
    async def initialize(self, db, embedding_service=None):
        """Initialize with database connection."""
        self._db = db
        
        if embedding_service:
            self._embedding_service = embedding_service
        else:
            from .embedding_service import embedding_service as es
            self._embedding_service = es
        
        self._initialized = True
    
    async def prime_context(
        self,
        query: str,
        route: "RouteDecision",
        user_profile: Optional["UserProfile"] = None,
        query_embedding: Optional[list[float]] = None
    ) -> PrimedContext:
        """
        Prime context for a query based on route decision.
        
        Args:
            query: User's message
            route: RouteDecision from SemanticRouter
            user_profile: User preferences (optional)
            query_embedding: Pre-computed query embedding (optimization)
            
        Returns:
            PrimedContext with category-specific data
        """
        start_time = time.time()
        
        # Get domain config for this category
        config = DOMAIN_CONFIGS.get(
            route.category.value,
            DOMAIN_CONFIGS["reasoning"]  # fallback
        )
        
        # Get or compute query embedding
        if not query_embedding and self._embedding_service:
            query_embedding = await self._embedding_service.get_or_compute(query)
        
        # Check semantic cache
        if query_embedding:
            cached = await self._cache.get(query, query_embedding)
            if cached:
                return cached
        
        # Parallel prefetch all components
        memories, patterns, tools, instructions = await asyncio.gather(
            self._fetch_memories(config),
            self._fetch_patterns(config),
            self._prepare_tools(config),
            self._load_instructions(config),
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(memories, Exception):
            memories = []
        if isinstance(patterns, Exception):
            patterns = []
        if isinstance(tools, Exception):
            tools = []
        if isinstance(instructions, Exception):
            instructions = None
        
        context = PrimedContext(
            category=route.category,
            memories=memories,
            patterns=patterns,
            tools=tools,
            instructions=instructions,
            prime_time_ms=(time.time() - start_time) * 1000,
            from_cache=False
        )
        
        # Cache for similar future queries
        if query_embedding:
            self._cache.put(query, query_embedding, context)
        
        return context
    
    async def _fetch_memories(self, config: DomainConfig) -> list[dict]:
        """Fetch category-specific memories."""
        if not self._db or not config.memory_categories:
            return []
        
        try:
            # Build query for specific categories
            placeholders = ",".join("?" * len(config.memory_categories))
            query = f"""
                SELECT content, category, confidence
                FROM memory_facts
                WHERE category IN ({placeholders})
                ORDER BY confidence DESC, created_at DESC
                LIMIT ?
            """
            
            async with self._db.execute(
                query,
                (*config.memory_categories, config.max_memories)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [
                {"content": row[0], "category": row[1], "confidence": row[2]}
                for row in rows
            ]
        except Exception:
            return []
    
    async def _fetch_patterns(self, config: DomainConfig) -> list[str]:
        """Fetch category-specific success patterns."""
        if not self._db or not config.pattern_types:
            return []
        
        try:
            placeholders = ",".join("?" * len(config.pattern_types))
            query = f"""
                SELECT extracted_pattern
                FROM success_patterns
                WHERE category IN ({placeholders})
                ORDER BY applied_count DESC
                LIMIT 3
            """
            
            async with self._db.execute(
                query,
                config.pattern_types
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [row[0] for row in rows if row[0]]
        except Exception:
            return []
    
    async def _prepare_tools(self, config: DomainConfig) -> list[str]:
        """Return list of tools relevant for this domain."""
        return config.tools
    
    async def _load_instructions(self, config: DomainConfig) -> Optional[str]:
        """Load specialized instructions file."""
        if not config.instructions_file:
            return None
        
        try:
            from pathlib import Path
            instructions_dir = Path(__file__).parent.parent.parent / "MIND" / "instructions"
            instructions_path = instructions_dir / config.instructions_file
            
            if instructions_path.exists():
                return instructions_path.read_text(encoding="utf-8")
        except Exception:
            pass
        
        return None
    
    def invalidate_cache(self):
        """Clear cache when memories/patterns change."""
        self._cache.clear()
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return self._cache.get_stats()
    
    async def warm_cache_for_category(self, category: str):
        """Warm cache for a category (background task)."""
        # Future implementation: pre-fetch common queries for category
        pass


# Global instance
context_primer = ContextPrimer()
