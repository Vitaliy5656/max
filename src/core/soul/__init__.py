"""Soul module — BDI-based Meta-Cognition Layer for MAX AI."""
from .models import SoulState, Meta, Identity, BDIState, CurrentFocus
from .soul_manager import SoulManager, soul_manager

__all__ = [
    "SoulState",
    "Meta", 
    "Identity",
    "BDIState",
    "CurrentFocus",
    "SoulManager",
    "soul_manager",
]
