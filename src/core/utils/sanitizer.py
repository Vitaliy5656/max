"""
Output Sanitizer — Cleans model output from artifacts.

Removes:
- Multiple asterisks (**)
- Role artifacts (User:, Assistant:)
- Excessive newlines
- Chinese characters at end (Qwen artifact)
- Special tokens

Usage:
    from src.core.utils import sanitizer
    
    clean_text = sanitizer.clean_output(raw_text)
    clean_chunk = sanitizer.stream_cleaner(chunk)
"""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SanitizerConfig:
    """Configuration for text sanitization."""
    # Remove multiple asterisks
    remove_asterisks: bool = True
    # Remove role artifacts at end
    remove_role_artifacts: bool = True
    # Collapse multiple newlines
    collapse_newlines: bool = True
    # Remove Chinese characters at end (Qwen artifact)
    remove_chinese_suffix: bool = True
    # Remove special tokens
    remove_special_tokens: bool = True
    # Max consecutive newlines allowed
    max_newlines: int = 2


class TextSanitizer:
    """
    Cleans model output from common artifacts.
    
    Designed for speed — uses compiled regex patterns.
    No LLM calls, pure regex cleaning.
    """
    
    # Pre-compiled patterns for performance
    PATTERNS = [
        # Multiple asterisks (bold artifacts) — but keep single pairs for markdown
        (re.compile(r'\*{3,}'), '**'),
        
        # Role artifacts at the end of text
        (re.compile(r'User:\s*$', re.IGNORECASE), ''),
        (re.compile(r'Assistant:\s*$', re.IGNORECASE), ''),
        (re.compile(r'Human:\s*$', re.IGNORECASE), ''),
        
        # Multiple consecutive newlines → max 2
        (re.compile(r'\n{3,}'), '\n\n'),
        
        # Chinese/Japanese characters at end (Qwen/mistral artifact)
        (re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]+\s*$'), ''),
        
        # Special tokens (should be stopped by model, but just in case)
        (re.compile(r'<\|im_end\|>.*', re.DOTALL), ''),
        (re.compile(r'<\|im_start\|>.*', re.DOTALL), ''),
        (re.compile(r'<\|endoftext\|>.*', re.DOTALL), ''),
        (re.compile(r'</s>.*', re.DOTALL), ''),
        
        # Trailing whitespace
        (re.compile(r'\s+$'), ''),
    ]
    
    # Lightweight patterns for streaming (less aggressive)
    STREAM_PATTERNS = [
        # Only remove obviously broken tokens in stream
        (re.compile(r'<\|im_end\|>'), ''),
        (re.compile(r'<\|endoftext\|>'), ''),
        (re.compile(r'</s>'), ''),
    ]
    
    def __init__(self, config: Optional[SanitizerConfig] = None):
        self.config = config or SanitizerConfig()
        self._buffer = ""  # For stream processing
    
    def clean_output(self, text: str) -> str:
        """
        Full cleaning of final output.
        
        Apply all patterns to remove artifacts.
        Use this on the complete response before saving.
        """
        if not text:
            return text
        
        result = text
        
        for pattern, replacement in self.PATTERNS:
            result = pattern.sub(replacement, result)
        
        # Final trim
        result = result.strip()
        
        return result
    
    def stream_cleaner(self, chunk: str) -> str:
        """
        Lightweight cleaning for SSE stream chunks.
        
        Less aggressive - only removes obvious broken tokens.
        Full cleaning happens on final output.
        """
        if not chunk:
            return chunk
        
        result = chunk
        
        for pattern, replacement in self.STREAM_PATTERNS:
            result = pattern.sub(replacement, result)
        
        return result
    
    def clean_before_save(self, text: str) -> str:
        """
        Clean text before saving to memory.
        
        Alias for clean_output with explicit intent.
        """
        return self.clean_output(text)
    
    def remove_trailing_artifacts(self, text: str) -> str:
        """
        Remove only trailing artifacts (for partial cleaning).
        
        Useful when you want to preserve formatting but remove
        model artifacts at the end.
        """
        if not text:
            return text
        
        result = text
        
        # Only apply end-of-string patterns
        trailing_patterns = [
            (re.compile(r'User:\s*$', re.IGNORECASE), ''),
            (re.compile(r'Assistant:\s*$', re.IGNORECASE), ''),
            (re.compile(r'[\u4e00-\u9fff]+\s*$'), ''),
            (re.compile(r'<\|im_end\|>.*$', re.DOTALL), ''),
            (re.compile(r'\s+$'), ''),
        ]
        
        for pattern, replacement in trailing_patterns:
            result = pattern.sub(replacement, result)
        
        return result


# Global singleton instance
sanitizer = TextSanitizer()
