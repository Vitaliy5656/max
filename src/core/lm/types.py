"""
LM Client Types — Enums and dataclasses.

Defines types used throughout the LM client package:
- TaskType: Categories of tasks for smart routing
- ThinkingMode: User-selectable thinking depth modes
- ModelInfo: Information about a loaded model
"""
from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """Type of task for smart routing."""
    REASONING = "reasoning"  # Complex thinking, chain-of-thought
    VISION = "vision"        # Image analysis
    QUICK = "quick"          # Fast simple responses
    DEFAULT = "default"      # General purpose


class ThinkingMode(Enum):
    """User-selectable thinking depth modes."""
    FAST = "fast"           # Quick responses, minimal reasoning
    STANDARD = "standard"   # Balanced quality/speed
    DEEP = "deep"           # Chain-of-thought, detailed analysis
    VISION = "vision"       # Auto-activated for images


@dataclass
class ModelInfo:
    """Information about a loaded model."""
    id: str
    object: str = "model"
    owned_by: str = "lmstudio"
