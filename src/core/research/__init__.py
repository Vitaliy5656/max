"""
Research Lab Module

Autonomous research agent with Double-Pass LLM processing,
Topic Skills generation, and ChromaDB storage.
"""

# Note: Imports are lazy to avoid circular dependencies
# Use: from src.core.research.storage import ResearchStorage
# Or:  from src.core.research import research_storage

__all__ = [
    "ResearchStorage", "research_storage",
    "DualParser", "ParseResult",
    "ResearchAgent", "research_agent",
    "ResearchWorker", "research_worker"
]


def __getattr__(name):
    """Lazy import for module components."""
    if name in ("ResearchStorage", "research_storage"):
        from .storage import ResearchStorage, research_storage
        return research_storage if name == "research_storage" else ResearchStorage
    elif name in ("DualParser", "ParseResult"):
        from .parser import DualParser, ParseResult
        return DualParser if name == "DualParser" else ParseResult
    elif name in ("ResearchAgent", "research_agent"):
        from .agent import ResearchAgent, research_agent
        return research_agent if name == "research_agent" else ResearchAgent
    elif name in ("ResearchWorker", "research_worker"):
        from .worker import ResearchWorker, research_worker
        return research_worker if name == "research_worker" else ResearchWorker
    raise AttributeError(f"module 'src.core.research' has no attribute '{name}'")
