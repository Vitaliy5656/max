"""
Ensemble Cognitive Loop v2 — Types and Configuration.

Defines data structures for the multi-path reasoning system.
"""
from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum


class EnsembleState(Enum):
    """States of the Ensemble thinking process."""
    IDLE = "idle"
    GENERATING = "generating"
    SYNTHESIZING = "synthesizing"
    DEBATING = "debating"
    MEGA_SYNTH = "mega_synth"
    VERIFYING = "verifying"
    MUTATING = "mutating"
    DONE = "done"
    FALLBACK = "fallback"
    CANCELLED = "cancelled"


@dataclass
class EnsembleConfig:
    """Configuration for Ensemble Cognitive Loop."""
    
    # Parallelism: 2 concurrent LLM calls (2+2 rounds)
    max_concurrent: int = 2
    
    # Temperatures for diversity
    temperatures: tuple[float, float] = (0.5, 0.9)
    
    # Persona variants
    personas: tuple[str, str] = ("expert", "teacher")
    
    # Timeouts per stage (seconds)
    timeout_generate: float = 30.0
    timeout_synthesis: float = 20.0
    timeout_verify: float = 15.0
    timeout_debate: float = 25.0
    timeout_total: float = 120.0
    
    # Verification thresholds
    accept_threshold: float = 7.0
    mutation_threshold_1: float = 7.0  # First mutation if score < this
    mutation_threshold_2: float = 6.0  # Second mutation if score < this
    max_mutations: int = 2
    
    # Verifier fallback
    verifier_fallback_score: float = 5.0  # Conservative (not 6!)
    
    # Score aggregation
    score_disagreement_threshold: float = 3.0  # Use min() if diff > this
    
    # CPO
    cpo_enabled: bool = True
    cpo_confidence_threshold: float = 0.6
    cpo_min_observations: int = 5
    cpo_tie_winner: str = "temp"  # Deterministic tie-breaker
    
    # Empty response threshold
    min_response_length: int = 10


@dataclass
class GenerationResult:
    """Result from a single generation."""
    content: str
    temperature: float
    persona: Optional[str] = None
    elapsed_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


@dataclass
class SynthesisResult:
    """Result from axis synthesis."""
    content: str
    axis: Literal["temp", "prompt"]
    sources: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0


@dataclass
class VerificationResult:
    """Result from verifier."""
    score: float
    raw_response: str
    is_fallback: bool = False


@dataclass
class AxisResults:
    """Scores per axis for CPO."""
    temp_axis_score: float
    prompt_axis_score: float
    
    @property
    def winner(self) -> str:
        """Deterministic winner (temp wins ties)."""
        if self.temp_axis_score >= self.prompt_axis_score:
            return "temp"
        return "prompt"
    
    @property
    def margin(self) -> float:
        return abs(self.temp_axis_score - self.prompt_axis_score)


@dataclass
class EnsembleResult:
    """Final result from Ensemble thinking."""
    answer: str
    final_score: float
    mutations_used: int = 0
    axis_results: Optional[AxisResults] = None
    state: EnsembleState = EnsembleState.DONE
    elapsed_ms: float = 0.0
    total_llm_calls: int = 0
    
    # For streaming
    thinking_log: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "answer": self.answer,
            "final_score": self.final_score,
            "mutations_used": self.mutations_used,
            "state": self.state.value,
            "elapsed_ms": self.elapsed_ms,
            "thinking_log": self.thinking_log,
            # Skip axis_results for simple response
        }


@dataclass
class ThinkingStep:
    """A step in the thinking process for UI streaming."""
    name: str = "Thinking"
    stage: int = 0
    total: int = 0
    text: str = ""
    elapsed_ms: float = 0.0


def get_config_for_mode(mode: str) -> EnsembleConfig:
    """
    Factory for EnsembleConfig based on thinking mode.
    
    Modes:
    - fast: 1 min, no retry (Good for simple code/logic)
    - standard: 2 min, 2 retries (Balanced)
    - deep: 5 min, 5 retries, lower cpo threshold (Complex research)
    """
    if mode == "fast":
        return EnsembleConfig(
            timeout_total=60.0,
            max_mutations=0,
            timeout_debate=15.0,
            cpo_min_observations=3
        )
    elif mode == "deep":
        return EnsembleConfig(
            timeout_total=300.0,
            max_mutations=5,
            timeout_generate=60.0,
            timeout_debate=45.0,
            cpo_confidence_threshold=0.8
        )
    
    # Default / Standard
    return EnsembleConfig()

