"""
Streaming Strategy for SmartRouter.

Determines optimal streaming behavior based on intent and message.

Features:
    - Intent-based strategy selection
    - Chunk size optimization
    - Buffer management
    - Speculative vs delayed streaming
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..logger import log


class StreamMode(Enum):
    """Streaming modes."""
    IMMEDIATE = "immediate"   # Stream tokens as they arrive
    BUFFERED = "buffered"     # Buffer chunks before sending
    DELAYED = "delayed"       # Wait for full response
    SPECULATIVE = "speculative"  # Pre-computed response


@dataclass
class StreamConfig:
    """Streaming configuration."""
    mode: StreamMode
    chunk_size: int = 1       # Tokens per chunk (for IMMEDIATE)
    buffer_size: int = 50     # Buffer size (for BUFFERED)
    initial_delay_ms: int = 0 # Delay before first token
    between_delay_ms: int = 0 # Delay between chunks
    
    # Advanced
    enable_thinking: bool = True
    show_typing_indicator: bool = True


# Default configs per intent
INTENT_STREAM_CONFIGS: Dict[str, StreamConfig] = {
    "greeting": StreamConfig(
        mode=StreamMode.SPECULATIVE,
        initial_delay_ms=0
    ),
    "coding": StreamConfig(
        mode=StreamMode.BUFFERED,
        chunk_size=10,
        buffer_size=100,
        enable_thinking=True
    ),
    "math": StreamConfig(
        mode=StreamMode.DELAYED,
        enable_thinking=True
    ),
    "question": StreamConfig(
        mode=StreamMode.IMMEDIATE,
        chunk_size=3
    ),
    "creative": StreamConfig(
        mode=StreamMode.IMMEDIATE,
        chunk_size=5,
        between_delay_ms=20  # Slight delay for dramatic effect
    ),
    "search": StreamConfig(
        mode=StreamMode.BUFFERED,
        buffer_size=200  # Wait for search results
    ),
}

DEFAULT_CONFIG = StreamConfig(
    mode=StreamMode.IMMEDIATE,
    chunk_size=3
)


class StreamingStrategy:
    """
    Determines streaming behavior for responses.
    """
    
    def __init__(self):
        log.debug("StreamingStrategy initialized")
    
    def get_config(
        self,
        intent: str,
        confidence: float = 1.0,
        is_complex: bool = False
    ) -> StreamConfig:
        """
        Get streaming config for intent.
        
        Args:
            intent: Detected intent
            confidence: Routing confidence
            is_complex: Is this a complex query
        """
        config = INTENT_STREAM_CONFIGS.get(intent, DEFAULT_CONFIG)
        
        # Adjust for low confidence
        if confidence < 0.7:
            # More conservative streaming for uncertain intents
            config = StreamConfig(
                mode=StreamMode.BUFFERED,
                buffer_size=50,
                enable_thinking=True
            )
        
        # Adjust for complex queries
        if is_complex:
            config = StreamConfig(
                mode=config.mode,
                chunk_size=config.chunk_size,
                buffer_size=max(config.buffer_size, 100),
                enable_thinking=True,
                initial_delay_ms=config.initial_delay_ms
            )
        
        return config
    
    def should_stream(
        self,
        intent: str,
        message_length: int = 0
    ) -> bool:
        """Quick check if streaming should be used."""
        config = self.get_config(intent)
        
        if config.mode == StreamMode.DELAYED:
            return False
        if config.mode == StreamMode.SPECULATIVE:
            return False  # Pre-computed, no streaming needed
        
        return True
    
    def get_thinking_config(
        self,
        intent: str,
        is_deep_thinking: bool = False
    ) -> Dict[str, Any]:
        """Get config for thinking indicator."""
        if is_deep_thinking:
            return {
                "show_thinking": True,
                "thinking_label": "Глубокий анализ...",
                "estimated_time_ms": 5000
            }
        
        intent_thinking = {
            "coding": {"label": "Пишу код...", "time": 2000},
            "math": {"label": "Считаю...", "time": 1500},
            "search": {"label": "Ищу информацию...", "time": 3000},
            "creative": {"label": "Творю...", "time": 2000},
            "question": {"label": "Думаю...", "time": 1000},
        }
        
        thinking = intent_thinking.get(intent, {"label": "Думаю...", "time": 1000})
        
        return {
            "show_thinking": True,
            "thinking_label": thinking["label"],
            "estimated_time_ms": thinking["time"]
        }


# Global instance
_strategy: Optional[StreamingStrategy] = None


def get_streaming_strategy() -> StreamingStrategy:
    """Get or create global strategy."""
    global _strategy
    if _strategy is None:
        _strategy = StreamingStrategy()
    return _strategy


def get_stream_config(intent: str, **kwargs) -> StreamConfig:
    """Quick helper for getting stream config."""
    return get_streaming_strategy().get_config(intent, **kwargs)
