"""
LM Providers package.

Contains adapters for different LLM backends:
- LM Studio (local)
- Gemini (cloud)
"""
from .gemini import GeminiProvider, GeminiConfig, get_gemini_provider

__all__ = [
    "GeminiProvider",
    "GeminiConfig", 
    "get_gemini_provider",
]
