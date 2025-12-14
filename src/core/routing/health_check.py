"""
Health Check for SmartRouter.

Provides diagnostic information and health status.

Features:
    - Component health checks
    - Performance metrics
    - Model availability
    - Cache status
"""
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio

from ..logger import log


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health of a single component."""
    name: str
    status: HealthStatus
    latency_ms: float
    message: str
    details: Optional[Dict] = None


@dataclass
class SystemHealth:
    """Overall system health."""
    status: HealthStatus
    components: List[ComponentHealth]
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "latency_ms": c.latency_ms,
                    "message": c.message,
                    "details": c.details
                }
                for c in self.components
            ]
        }


class HealthChecker:
    """
    Health diagnostics for routing system.
    """
    
    def __init__(self):
        log.debug("HealthChecker initialized")
    
    async def check_all(self) -> SystemHealth:
        """Run all health checks."""
        components = []
        
        # Check each component
        components.append(await self._check_semantic_router())
        components.append(await self._check_llm_router())
        components.append(self._check_cache())
        components.append(self._check_observer())
        components.append(self._check_prompts())
        
        # Determine overall status
        statuses = [c.status for c in components]
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY
        
        return SystemHealth(
            status=overall,
            components=components,
            timestamp=time.time()
        )
    
    async def _check_semantic_router(self) -> ComponentHealth:
        """Check Semantic Router health."""
        start = time.perf_counter()
        
        try:
            from .semantic_router import get_semantic_router
            router = get_semantic_router()
            
            # Try a test route
            if hasattr(router, '_examples') and len(router._examples) > 0:
                elapsed = (time.perf_counter() - start) * 1000
                return ComponentHealth(
                    name="SemanticRouter",
                    status=HealthStatus.HEALTHY,
                    latency_ms=elapsed,
                    message=f"{len(router._examples)} examples loaded",
                    details={"example_count": len(router._examples)}
                )
            else:
                elapsed = (time.perf_counter() - start) * 1000
                return ComponentHealth(
                    name="SemanticRouter",
                    status=HealthStatus.DEGRADED,
                    latency_ms=elapsed,
                    message="No examples loaded",
                    details={"example_count": 0}
                )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ComponentHealth(
                name="SemanticRouter",
                status=HealthStatus.UNHEALTHY,
                latency_ms=elapsed,
                message=str(e)
            )
    
    async def _check_llm_router(self) -> ComponentHealth:
        """Check LLM Router / LM Studio connection."""
        start = time.perf_counter()
        
        try:
            from .llm_router import llm_router
            
            # Quick connectivity check
            stats = llm_router.get_stats()
            elapsed = (time.perf_counter() - start) * 1000
            
            return ComponentHealth(
                name="LLMRouter",
                status=HealthStatus.HEALTHY,
                latency_ms=elapsed,
                message=f"Model: {llm_router.model}",
                details=stats
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ComponentHealth(
                name="LLMRouter",
                status=HealthStatus.DEGRADED,
                latency_ms=elapsed,
                message=f"LM Studio may be offline: {e}"
            )
    
    def _check_cache(self) -> ComponentHealth:
        """Check cache status."""
        start = time.perf_counter()
        
        try:
            from .smart_router import get_smart_router
            router = get_smart_router()
            stats = router.get_stats()
            elapsed = (time.perf_counter() - start) * 1000
            
            hit_rate = stats.get("cache_hits", 0) / max(stats.get("total_requests", 1), 1) * 100
            
            return ComponentHealth(
                name="Cache",
                status=HealthStatus.HEALTHY,
                latency_ms=elapsed,
                message=f"Hit rate: {hit_rate:.1f}%",
                details={"hit_rate": hit_rate, "size": len(router._cache)}
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ComponentHealth(
                name="Cache",
                status=HealthStatus.DEGRADED,
                latency_ms=elapsed,
                message=str(e)
            )
    
    def _check_observer(self) -> ComponentHealth:
        """Check Observer status."""
        start = time.perf_counter()
        
        try:
            from .observer import get_routing_observer
            observer = get_routing_observer()
            stats = observer.get_stats()
            elapsed = (time.perf_counter() - start) * 1000
            
            return ComponentHealth(
                name="Observer",
                status=HealthStatus.HEALTHY,
                latency_ms=elapsed,
                message=f"Traces: {stats.get('total_requests', 0)}",
                details=stats
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ComponentHealth(
                name="Observer",
                status=HealthStatus.DEGRADED,
                latency_ms=elapsed,
                message=str(e)
            )
    
    def _check_prompts(self) -> ComponentHealth:
        """Check Prompt Library."""
        start = time.perf_counter()
        
        try:
            from ..prompts import get_prompt_library
            library = get_prompt_library()
            prompts = library.list_all()
            elapsed = (time.perf_counter() - start) * 1000
            
            return ComponentHealth(
                name="PromptLibrary",
                status=HealthStatus.HEALTHY,
                latency_ms=elapsed,
                message=f"{len(prompts)} prompts",
                details={"count": len(prompts), "prompts": [p.name for p in prompts]}
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ComponentHealth(
                name="PromptLibrary",
                status=HealthStatus.DEGRADED,
                latency_ms=elapsed,
                message=str(e)
            )


# Global instance
_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get or create global checker."""
    global _checker
    if _checker is None:
        _checker = HealthChecker()
    return _checker


async def check_health() -> SystemHealth:
    """Quick helper for health check."""
    return await get_health_checker().check_all()
