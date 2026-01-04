"""
Entropy-Based Router for MAX AI.

Implements Entropix-style routing that adjusts parameters based on
response entropy and uncertainty metrics.

Reference: Entropix - Dynamic sampling based on token entropy/varentropy.
"""
import math
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..logger import log


class SamplingStrategy(Enum):
    """Sampling strategies based on entropy analysis."""
    CONFIDENT = "confident"      # Low entropy, low varentropy - use greedy/low temp
    EXPLORING = "exploring"      # High entropy, low varentropy - increase temp slightly
    UNCERTAIN = "uncertain"      # Low entropy, high varentropy - use more samples
    CONFUSED = "confused"        # High entropy, high varentropy - branch/multi-sample
    DEFAULT = "default"          # Fallback strategy


@dataclass
class EntropyMetrics:
    """Metrics computed from logprobs."""
    entropy: float          # Token-level entropy (uncertainty)
    varentropy: float       # Variance of entropy (consistency)
    top_prob: float         # Probability of top token
    
    @property
    def is_confident(self) -> bool:
        """Low entropy + low varentropy = confident."""
        return self.entropy < 0.5 and self.varentropy < 0.3
    
    @property
    def is_confused(self) -> bool:
        """High entropy + high varentropy = confused."""
        return self.entropy > 2.0 and self.varentropy > 1.0


@dataclass
class SamplingParams:
    """Adjusted sampling parameters."""
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    num_samples: int = 1


class EntropyRouter:
    """
    Routes requests based on entropy analysis.
    
    Uses logprobs from LLM responses to dynamically adjust
    sampling parameters for optimal quality.
    """
    
    # Thresholds (tunable)
    ENTROPY_LOW = 0.5
    ENTROPY_HIGH = 2.0
    VARENTROPY_LOW = 0.3
    VARENTROPY_HIGH = 1.0
    
    def __init__(self):
        self._history: list = []
        log.debug("EntropyRouter initialized")
    
    def compute_entropy(self, logprobs: list[float]) -> float:
        """
        Compute entropy from log probabilities.
        
        H = -sum(p * log(p)) = -sum(exp(logp) * logp)
        """
        if not logprobs:
            return 0.0
        
        entropy = 0.0
        for logp in logprobs:
            if logp > -100:  # Filter out -inf
                p = math.exp(logp)
                entropy -= p * logp  # Note: logp is already negative
        
        return entropy
    
    def compute_varentropy(self, token_entropies: list[float]) -> float:
        """
        Compute variance of entropy across tokens.
        
        High variance = inconsistent confidence = potential issues.
        """
        if len(token_entropies) < 2:
            return 0.0
        
        mean = sum(token_entropies) / len(token_entropies)
        variance = sum((e - mean) ** 2 for e in token_entropies) / len(token_entropies)
        return math.sqrt(variance)
    
    def analyze_response(
        self,
        logprobs_sequence: list[list[float]]
    ) -> EntropyMetrics:
        """
        Analyze a sequence of logprobs from a response.
        
        Args:
            logprobs_sequence: List of logprob lists, one per token
            
        Returns:
            EntropyMetrics with computed values
        """
        if not logprobs_sequence:
            return EntropyMetrics(entropy=0.0, varentropy=0.0, top_prob=1.0)
        
        # Compute entropy per token
        token_entropies = [self.compute_entropy(lps) for lps in logprobs_sequence]
        
        # Average entropy
        avg_entropy = sum(token_entropies) / len(token_entropies)
        
        # Variance of entropy
        varentropy = self.compute_varentropy(token_entropies)
        
        # Top probability (average)
        top_probs = [math.exp(lps[0]) if lps else 1.0 for lps in logprobs_sequence]
        avg_top_prob = sum(top_probs) / len(top_probs)
        
        return EntropyMetrics(
            entropy=avg_entropy,
            varentropy=varentropy,
            top_prob=avg_top_prob
        )
    
    def determine_strategy(self, metrics: EntropyMetrics) -> SamplingStrategy:
        """
        Determine sampling strategy based on metrics.
        
        Quadrant analysis:
        - Low E, Low V → CONFIDENT (greedy-ish)
        - High E, Low V → EXPLORING (higher temp)
        - Low E, High V → UNCERTAIN (more samples)
        - High E, High V → CONFUSED (branch/CoT)
        """
        if metrics.entropy < self.ENTROPY_LOW:
            if metrics.varentropy < self.VARENTROPY_LOW:
                return SamplingStrategy.CONFIDENT
            else:
                return SamplingStrategy.UNCERTAIN
        else:
            if metrics.varentropy < self.VARENTROPY_LOW:
                return SamplingStrategy.EXPLORING
            else:
                return SamplingStrategy.CONFUSED
    
    def get_sampling_params(
        self,
        strategy: SamplingStrategy,
        base_temp: float = 0.7
    ) -> SamplingParams:
        """
        Get adjusted sampling parameters for a strategy.
        """
        if strategy == SamplingStrategy.CONFIDENT:
            # Greedy-ish: lower temp, tighter top_p
            return SamplingParams(
                temperature=max(0.1, base_temp * 0.5),
                top_p=0.8,
                top_k=20,
                repeat_penalty=1.0,
                num_samples=1
            )
        
        elif strategy == SamplingStrategy.EXPLORING:
            # Slightly higher temp for exploration
            return SamplingParams(
                temperature=min(1.2, base_temp * 1.3),
                top_p=0.95,
                top_k=60,
                repeat_penalty=1.1,
                num_samples=1
            )
        
        elif strategy == SamplingStrategy.UNCERTAIN:
            # Multiple samples to find consensus
            return SamplingParams(
                temperature=base_temp,
                top_p=0.9,
                top_k=40,
                repeat_penalty=1.15,
                num_samples=3
            )
        
        elif strategy == SamplingStrategy.CONFUSED:
            # Could trigger Chain of Thought or branching
            return SamplingParams(
                temperature=min(1.0, base_temp * 1.2),
                top_p=0.92,
                top_k=50,
                repeat_penalty=1.2,
                num_samples=2  # Or trigger CoT
            )
        
        else:
            # Default
            return SamplingParams(temperature=base_temp)
    
    def should_use_cot(self, metrics: EntropyMetrics) -> bool:
        """
        Determine if Chain of Thought should be triggered.
        
        High confusion suggests the model needs to "think step by step".
        """
        return metrics.is_confused or (metrics.entropy > 1.5 and metrics.varentropy > 0.8)
    
    def route(
        self,
        logprobs_sequence: Optional[list[list[float]]] = None,
        base_temp: float = 0.7
    ) -> Tuple[SamplingStrategy, SamplingParams]:
        """
        Main routing method.
        
        Analyzes logprobs (if available) and returns strategy + params.
        """
        if not logprobs_sequence:
            # No logprobs available - use default
            return SamplingStrategy.DEFAULT, SamplingParams(temperature=base_temp)
        
        metrics = self.analyze_response(logprobs_sequence)
        strategy = self.determine_strategy(metrics)
        params = self.get_sampling_params(strategy, base_temp)
        
        log.debug(
            f"EntropyRouter: strategy={strategy.value}, "
            f"entropy={metrics.entropy:.2f}, varentropy={metrics.varentropy:.2f}"
        )
        
        # Track history for analysis
        self._history.append({
            "metrics": metrics,
            "strategy": strategy
        })
        
        return strategy, params
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        if not self._history:
            return {"total_routes": 0}
        
        strategy_counts = {}
        for h in self._history:
            s = h["strategy"].value
            strategy_counts[s] = strategy_counts.get(s, 0) + 1
        
        return {
            "total_routes": len(self._history),
            "strategy_distribution": strategy_counts
        }


# Global instance
entropy_router = EntropyRouter()
