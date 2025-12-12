"""
Shared Embedding Service for MAX AI Assistant.

Centralizes all embedding calls with in-memory caching to eliminate
duplicate API calls across modules (SemanticRouter, ContextPrimer, ErrorMemory).

Usage:
    from .embedding_service import embedding_service
    
    embedding = await embedding_service.get_or_compute("my text")
"""
import asyncio
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class CachedEmbedding:
    """Cached embedding with timestamp for TTL."""
    embedding: list[float]
    created_at: datetime


class EmbeddingService:
    """
    Centralized embedding service with in-memory cache.
    
    Features:
    - Deduplicates embedding calls across all modules
    - TTL-based cache expiration (default 1 hour)
    - LRU eviction when cache is full
    - Fallback to None if embedding API fails
    
    Memory Usage:
    - ~4KB per embedding (1536 dimensions * 4 bytes)
    - 1000 entries = ~4MB RAM
    """
    
    def __init__(
        self,
        max_cache_size: int = 1000,
        ttl_seconds: int = 3600  # 1 hour
    ):
        self._cache: dict[str, CachedEmbedding] = {}
        self._max_size = max_cache_size
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lm_client = None
        self._hits = 0
        self._misses = 0
    
    async def initialize(self, lm_client):
        """Initialize with LM client reference."""
        self._lm_client = lm_client
    
    async def get_or_compute(self, text: str) -> Optional[list[float]]:
        """
        Get embedding from cache or compute via LM client.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if unavailable
        """
        if not text or not text.strip():
            return None
        
        # Normalize text for cache key
        cache_key = text.strip()[:500]  # Limit key length
        
        # Check cache first
        now = datetime.now()
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if now - cached.created_at < self._ttl:
                self._hits += 1
                return cached.embedding
            else:
                # Expired
                del self._cache[cache_key]
        
        # Cache miss - compute embedding
        self._misses += 1
        
        if not self._lm_client:
            return None
        
        try:
            embedding = await self._lm_client.get_embedding(text)
            if embedding:
                self._cache_put(cache_key, embedding)
            return embedding
        except Exception:
            return None
    
    def _cache_put(self, key: str, embedding: list[float]):
        """Add embedding to cache with LRU eviction."""
        # Evict oldest if full
        if len(self._cache) >= self._max_size:
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].created_at
            )
            del self._cache[oldest_key]
        
        self._cache[key] = CachedEmbedding(
            embedding=embedding,
            created_at=datetime.now()
        )
    
    def clear(self):
        """Clear all cached embeddings."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "cache_size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2)
        }


# Global instance
embedding_service = EmbeddingService()
