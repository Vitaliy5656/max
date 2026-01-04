"""
Prompts package for MAX AI.

Provides prompt management, selection, and customization.
"""
from .library import (
    PromptLibrary,
    get_prompt_library,
    select_prompt,
    Prompt,
    PromptCategory
)

__all__ = [
    'PromptLibrary',
    'get_prompt_library',
    'select_prompt',
    'Prompt',
    'PromptCategory'
]
