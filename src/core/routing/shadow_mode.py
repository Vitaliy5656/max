"""
Shadow Mode for Router A/B Testing.

Runs multiple routers in parallel and compares their decisions
without affecting the production response.

Use cases:
    - Compare Semantic vs LLM Router accuracy
    - Test new routing strategies
    - Validate before promoting changes
"""
import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json

from ..logger import log


class RouterVariant(Enum):
    """Router variants for comparison."""
    SEMANTIC = "semantic"
    LLM = "llm"
    CPU = "cpu"
    SMART = "smart"


@dataclass
class ShadowResult:
    """Result of shadow comparison."""
    message: str
    timestamp: datetime
    
    # Primary (production) result
    primary_router: RouterVariant
    primary_intent: str
    primary_confidence: float
    primary_time_ms: float
    
    # Shadow result
    shadow_router: RouterVariant
    shadow_intent: str
    shadow_confidence: float
    shadow_time_ms: float
    
    # Comparison
    intent_match: bool
    winner: Optional[str] = None  # faster, more_confident
    
    def to_dict(self) -> Dict:
        """Convert to dict for JSON."""
        return {
            "message_preview": self.message[:50],
            "timestamp": self.timestamp.isoformat(),
            "primary": {
                "router": self.primary_router.value,
                "intent": self.primary_intent,
                "confidence": self.primary_confidence,
                "time_ms": self.primary_time_ms
            },
            "shadow": {
                "router": self.shadow_router.value,
                "intent": self.shadow_intent,
                "confidence": self.shadow_confidence,
                "time_ms": self.shadow_time_ms
            },
            "intent_match": self.intent_match,
            "winner": self.winner
        }


@dataclass
class ShadowStats:
    """Aggregated shadow mode statistics."""
    total_comparisons: int = 0
    intent_matches: int = 0
    primary_wins_speed: int = 0
    shadow_wins_speed: int = 0
    primary_wins_confidence: int = 0
    shadow_wins_confidence: int = 0
    
    @property
    def agreement_rate(self) -> float:
        if self.total_comparisons == 0:
            return 0.0
        return self.intent_matches / self.total_comparisons * 100
    
    def to_dict(self) -> Dict:
        return {
            "total_comparisons": self.total_comparisons,
            "agreement_rate": f"{self.agreement_rate:.1f}%",
            "intent_matches": self.intent_matches,
            "primary_wins_speed": self.primary_wins_speed,
            "shadow_wins_speed": self.shadow_wins_speed,
        }


class ShadowMode:
    """
    Shadow mode for router comparison.
    
    Runs shadow router in parallel with production and logs differences.
    Does NOT affect the actual response.
    """
    
    def __init__(
        self,
        enabled: bool = False,
        shadow_router: RouterVariant = RouterVariant.LLM,
        persist_path: Optional[Path] = None
    ):
        self._enabled = enabled
        self._shadow_variant = shadow_router
        self._persist_path = persist_path or Path("data/shadow_results.jsonl")
        
        self._results: List[ShadowResult] = []
        self._stats = ShadowStats()
        self._max_results = 500
        
        log.debug(f"ShadowMode initialized (enabled={enabled}, shadow={shadow_router.value})")
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    def enable(self, shadow_router: Optional[RouterVariant] = None) -> None:
        """Enable shadow mode."""
        if shadow_router:
            self._shadow_variant = shadow_router
        self._enabled = True
        log.debug(f"ShadowMode enabled with {self._shadow_variant.value}")
    
    def disable(self) -> None:
        """Disable shadow mode."""
        self._enabled = False
        log.debug("ShadowMode disabled")
    
    async def compare(
        self,
        message: str,
        primary_result: Tuple[str, float, float],  # intent, confidence, time_ms
        primary_router: RouterVariant = RouterVariant.SEMANTIC
    ) -> Optional[ShadowResult]:
        """
        Run shadow comparison in background.
        
        Args:
            message: User message
            primary_result: (intent, confidence, time_ms) from production router
            primary_router: Which router was used in production
            
        Returns:
            ShadowResult if comparison was made, None if shadow mode disabled
        """
        if not self._enabled:
            return None
        
        primary_intent, primary_confidence, primary_time_ms = primary_result
        
        # Run shadow router
        shadow_intent, shadow_confidence, shadow_time_ms = await self._run_shadow(message)
        
        # Create result
        intent_match = primary_intent.lower() == shadow_intent.lower()
        
        # Determine winner
        winner = None
        if primary_time_ms < shadow_time_ms:
            winner = "primary_faster"
            self._stats.primary_wins_speed += 1
        else:
            winner = "shadow_faster"
            self._stats.shadow_wins_speed += 1
        
        result = ShadowResult(
            message=message,
            timestamp=datetime.now(),
            primary_router=primary_router,
            primary_intent=primary_intent,
            primary_confidence=primary_confidence,
            primary_time_ms=primary_time_ms,
            shadow_router=self._shadow_variant,
            shadow_intent=shadow_intent,
            shadow_confidence=shadow_confidence,
            shadow_time_ms=shadow_time_ms,
            intent_match=intent_match,
            winner=winner
        )
        
        # Update stats
        self._stats.total_comparisons += 1
        if intent_match:
            self._stats.intent_matches += 1
        
        # Store result
        self._results.append(result)
        if len(self._results) > self._max_results:
            self._results.pop(0)
        
        # Log difference
        if not intent_match:
            log.debug(
                f"ShadowMode MISMATCH: {primary_router.value}={primary_intent} vs "
                f"{self._shadow_variant.value}={shadow_intent} for '{message[:30]}...'"
            )
        
        # Persist async
        asyncio.create_task(self._persist(result))
        
        return result
    
    async def _run_shadow(self, message: str) -> Tuple[str, float, float]:
        """Run the shadow router and return (intent, confidence, time_ms)."""
        start = time.perf_counter()
        
        try:
            if self._shadow_variant == RouterVariant.LLM:
                from .llm_router import llm_router
                result = await llm_router.route(message)
                intent = result.intent.value
                confidence = result.confidence
                
            elif self._shadow_variant == RouterVariant.SEMANTIC:
                from .semantic_router import get_semantic_router
                router = get_semantic_router()
                match = await router.route(message)
                intent = match.intent if match else "unknown"
                confidence = match.score if match else 0.0
                
            elif self._shadow_variant == RouterVariant.CPU:
                from .cpu_router import cpu_router
                result = cpu_router.route(message)
                intent = result.intent.value
                confidence = result.confidence
                
            else:
                intent = "unknown"
                confidence = 0.0
                
        except Exception as e:
            log.warn(f"Shadow router error: {e}")
            intent = "error"
            confidence = 0.0
        
        elapsed = (time.perf_counter() - start) * 1000
        return intent, confidence, elapsed
    
    async def _persist(self, result: ShadowResult) -> None:
        """Persist result to file."""
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            log.error(f"Failed to persist shadow result: {e}")
    
    def get_stats(self) -> Dict:
        """Get shadow mode statistics."""
        return {
            "enabled": self._enabled,
            "shadow_router": self._shadow_variant.value,
            "stats": self._stats.to_dict()
        }
    
    def get_recent_mismatches(self, limit: int = 10) -> List[Dict]:
        """Get recent intent mismatches for analysis."""
        mismatches = [r for r in self._results if not r.intent_match]
        return [r.to_dict() for r in mismatches[-limit:]]
    
    def get_recent_results(self, limit: int = 20) -> List[Dict]:
        """Get recent comparison results."""
        return [r.to_dict() for r in self._results[-limit:]]


# Global instance
_shadow_mode: Optional[ShadowMode] = None


def get_shadow_mode() -> ShadowMode:
    """Get or create global ShadowMode."""
    global _shadow_mode
    if _shadow_mode is None:
        _shadow_mode = ShadowMode()
    return _shadow_mode


def enable_shadow_mode(shadow_router: RouterVariant = RouterVariant.LLM) -> None:
    """Quick helper to enable shadow mode."""
    get_shadow_mode().enable(shadow_router)


def disable_shadow_mode() -> None:
    """Quick helper to disable shadow mode."""
    get_shadow_mode().disable()
