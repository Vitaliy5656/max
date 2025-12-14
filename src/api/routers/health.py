"""
Health Router for MAX AI API.

Endpoints:
- GET /api/health
- GET /api/health/cognitive
"""
from fastapi import APIRouter

from src.core.metrics import metrics_engine
from src.core.context_primer import context_primer
from src.core.embedding_service import embedding_service

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health():
    """Health check."""
    # Import here to avoid circular dependency  
    from src.api.app import is_initialized
    return {"status": "ok", "initialized": is_initialized()}


@router.get("/cognitive")
async def cognitive_health():
    """Get cognitive system health (AI Next Gen modules)."""
    try:
        iq = await metrics_engine.calculate_iq()
        cache_stats = context_primer.get_cache_stats()
        embedding_stats = embedding_service.get_stats()
        
        return {
            "iq_today": iq.score,
            "context_cache": cache_stats,
            "embedding_cache": embedding_stats,
            "semantic_routing": True,
            "context_priming": True
        }
    except Exception as e:
        return {
            "error": str(e),
            "semantic_routing": False,
            "context_priming": False
        }
