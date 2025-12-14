"""
Cost Estimator for routing decisions.

Estimates token costs and suggests optimizations.

Features:
    - Token estimation
    - Cost calculation per provider
    - RAG cost impact
    - Suggestions for cost reduction
"""
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

from ..logger import log


class ModelTier(Enum):
    """Model cost tiers."""
    FREE = "free"        # Local LM Studio
    CHEAP = "cheap"      # GPT-3.5, Claude Haiku
    STANDARD = "standard"  # GPT-4o-mini
    PREMIUM = "premium"   # GPT-4, Claude Opus


# Cost per 1K tokens (input/output)
COST_TABLE = {
    ModelTier.FREE: {"input": 0.0, "output": 0.0},
    ModelTier.CHEAP: {"input": 0.0005, "output": 0.0015},
    ModelTier.STANDARD: {"input": 0.003, "output": 0.006},
    ModelTier.PREMIUM: {"input": 0.03, "output": 0.06},
}


@dataclass
class CostEstimate:
    """Estimated cost for a request."""
    input_tokens: int
    estimated_output_tokens: int
    total_tokens: int
    
    model_tier: ModelTier
    estimated_cost_usd: float
    
    # Components
    context_tokens: int
    rag_tokens: int
    message_tokens: int
    
    # Suggestions
    suggestions: list


class CostEstimator:
    """
    Estimates and tracks request costs.
    """
    
    def __init__(self, default_tier: ModelTier = ModelTier.FREE):
        self.default_tier = default_tier
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._request_count = 0
        
        log.debug("CostEstimator initialized")
    
    def estimate(
        self,
        message: str,
        context_messages: int = 0,
        rag_chars: int = 0,
        model_tier: Optional[ModelTier] = None
    ) -> CostEstimate:
        """
        Estimate cost for a request.
        
        Args:
            message: User message
            context_messages: Number of context messages
            rag_chars: Characters from RAG
            model_tier: Model tier to use
        """
        tier = model_tier or self.default_tier
        
        # Token estimation
        message_tokens = len(message) // 4
        context_tokens = context_messages * 100  # ~100 tokens per message average
        rag_tokens = rag_chars // 4
        
        input_tokens = message_tokens + context_tokens + rag_tokens
        
        # Output estimation (varies by complexity)
        if "код" in message.lower() or "code" in message.lower():
            estimated_output = 500
        elif len(message) < 50:
            estimated_output = 100
        else:
            estimated_output = 250
        
        # Cost calculation
        costs = COST_TABLE[tier]
        cost = (input_tokens * costs["input"] + estimated_output * costs["output"]) / 1000
        
        # Generate suggestions
        suggestions = []
        if rag_tokens > 500:
            suggestions.append("Consider reducing RAG context size")
        if context_tokens > 1000:
            suggestions.append("Consider summarizing older messages")
        if tier == ModelTier.PREMIUM:
            suggestions.append("Switch to GPT-4o-mini for simple queries")
        
        return CostEstimate(
            input_tokens=input_tokens,
            estimated_output_tokens=estimated_output,
            total_tokens=input_tokens + estimated_output,
            model_tier=tier,
            estimated_cost_usd=cost,
            context_tokens=context_tokens,
            rag_tokens=rag_tokens,
            message_tokens=message_tokens,
            suggestions=suggestions
        )
    
    def track(self, input_tokens: int, output_tokens: int) -> None:
        """Track actual token usage."""
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        self._request_count += 1
    
    def get_session_stats(self) -> Dict:
        """Get session cost statistics."""
        return {
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
            "request_count": self._request_count,
            "avg_tokens_per_request": (
                (self._total_input_tokens + self._total_output_tokens) / self._request_count
                if self._request_count > 0 else 0
            )
        }


# Global instance
_estimator: Optional[CostEstimator] = None


def get_cost_estimator() -> CostEstimator:
    """Get or create global CostEstimator."""
    global _estimator
    if _estimator is None:
        _estimator = CostEstimator()
    return _estimator


def estimate_cost(message: str, **kwargs) -> CostEstimate:
    """Quick helper for cost estimation."""
    return get_cost_estimator().estimate(message, **kwargs)
