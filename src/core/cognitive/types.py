from typing import TypedDict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass

class VerificationResult(Enum):
    """Result of the verification step."""
    VALID = "valid"
    NEEDS_REFINEMENT = "needs_refinement"
    CRITICAL_ERROR = "critical_error"

class CognitiveState(TypedDict):
    """
    State passed between LangGraph nodes in the Cognitive Loop.
    Tracks the evolution of the reasoning process.
    """
    input: str                      # Original user request
    conversation_id: str            # For memory context
    user_context: Optional[str]     # User profile/preferences context

    # Reasoning artifacts
    plan: Optional[str]             # Decomposed plan from Planner
    steps: List[str]                # Executed steps/logic
    draft_answer: str               # Current draft response

    # Verification & Refinement
    critique: str                   # Verification feedback
    score: float                    # Quality score (0.0 - 1.0)
    iterations: int                 # Cycle counter (resets on replan)
    total_iterations: int           # P0 FIX: Global counter that NEVER resets (prevents infinite loop)
    past_failures: List[str]        # Summarized failures from MemoryNode

    # UX Integration
    thinking_tokens: List[str]      # <think> content for UI streaming
    step_name: Optional[str]        # Current step name (Planning, Critiquing, etc)
    step_content: Optional[str]     # Current step detail/output

    # Metadata
    status: str                     # 'planning', 'executing', 'verifying', 'completed'

@dataclass
class CognitiveConfig:
    """Configuration for the cognitive loop execution."""
    # Iteration limits
    max_iterations_per_plan: int = 5    # Max attempts per plan
    max_total_iterations: int = 10      # Absolute max (never resets)

    # Score thresholds (P1 FIX: Now actually used!)
    accept_threshold: float = 0.75      # Score to accept answer
    abort_threshold: float = 0.6        # Min score to accept after max iterations
    replan_threshold: float = 0.3       # Score below which to create new plan

    # Timeout
    timeout_seconds: int = 180          # Max time for entire loop

    # Features
    enable_cot: bool = True
    enable_streaming: bool = True
    model_override: Optional[str] = None
    fallback_parsing: bool = True       # Regex backup if JSON fails (Logic Safety)


# Default configuration instance
DEFAULT_COGNITIVE_CONFIG = CognitiveConfig()
