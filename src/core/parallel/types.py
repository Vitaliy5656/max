from enum import Enum, auto
from dataclasses import dataclass, field

class SlotPriority(Enum):
    """Priority levels for slot acquisition."""
    BACKGROUND = 0  # Fact extraction, indexing
    STANDARD = 1    # Regular chat
    HIGH = 2        # Cognitive loop, System 2
    CRITICAL = 3    # System alerts, errors

@dataclass
class SlotConfig:
    """Configuration for the SlotManager."""
    # Start with safe default (2) or env variable
    max_slots: int = field(default_factory=lambda: int(__import__("os").getenv("OLLAMA_NUM_PARALLEL", "2")))
    max_queue_size: int = 5
    slot_timeout: float = 60.0    # Max time to hold a slot
    queue_timeout: float = 30.0   # Max time to wait in queue
