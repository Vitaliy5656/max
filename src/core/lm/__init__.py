"""
LM Client Package — OpenAI-compatible LM Studio client.

This package provides a modular client for LM Studio's API:

Modules:
- types: TaskType, ThinkingMode, ModelInfo
- routing: Task detection and model selection
- cli: LMS CLI operations (load/unload/scan)
- streaming: SSE streaming with think-tag filtering
- client: Main LMStudioClient class

Usage:
    from src.core.lm import lm_client, TaskType, ThinkingMode
    
    # Chat with thinking mode
    response = await lm_client.chat(messages, thinking_mode=ThinkingMode.DEEP)
    
    # Detect task type
    task_type = lm_client.detect_task_type("Explain quantum physics")
"""

from .types import TaskType, ThinkingMode, ModelInfo
from .client import LMStudioClient

# Global singleton instance
lm_client = LMStudioClient()

__all__ = [
    # Types
    "TaskType",
    "ThinkingMode", 
    "ModelInfo",
    # Classes
    "LMStudioClient",
    # Global instance
    "lm_client",
]
