"""
Centralized Logging Module for MAX AI Assistant.

Provides structured terminal logging with:
- Color-coded output by component
- Request tracing with correlation IDs
- Streaming chunk visibility
- Performance timing

Usage:
    from src.core.logger import log
    log.api("Incoming chat request", message=msg[:50])
    log.lm("Chunk received", size=len(chunk), in_think=True)
"""
import sys
import time
from datetime import datetime
from typing import Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from contextvars import ContextVar

# ANSI Colors
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Components
    API = "\033[38;5;39m"      # Blue
    LM = "\033[38;5;208m"      # Orange
    STREAM = "\033[38;5;82m"   # Green
    THINK = "\033[38;5;141m"   # Purple
    ERROR = "\033[38;5;196m"   # Red
    WARN = "\033[38;5;226m"    # Yellow

    DEBUG = "\033[38;5;245m"   # Gray
    PARALLEL = "\033[38;5;51m" # Cyan


class Component(Enum):
    API = "API"
    LM = "LM"
    STREAM = "STREAM"
    THINK = "THINK"
    SSE = "SSE"
    FRONTEND = "FE"

    COGNITIVE = "COGNITIVE"
    PARALLEL = "PARALLEL"


# Context variable for request tracing
_request_id: ContextVar[str] = ContextVar('request_id', default='----')


@dataclass
class LogConfig:
    """Logging configuration."""
    enabled: bool = True
    show_timestamps: bool = True
    show_request_id: bool = True
    show_chunks: bool = True          # Show each streaming chunk
    show_think_content: bool = False  # Show actual thinking content (verbose)
    max_chunk_preview: int = 50       # Max chars to show per chunk
    component_filter: set = field(default_factory=set)  # Empty = show all


# Global config
config = LogConfig()


class Logger:
    """Centralized logger with component-based coloring."""
    
    def __init__(self):
        self._start_times: dict[str, float] = {}
    
    def set_request_id(self, req_id: str):
        """Set correlation ID for current request."""
        _request_id.set(req_id[:4])
    
    def _format(
        self, 
        component: Component, 
        message: str, 
        level: str = "INFO",
        **kwargs
    ) -> str:
        """Format log line with colors and metadata."""
        if not config.enabled:
            return ""
        
        if config.component_filter and component.value not in config.component_filter:
            return ""
        
        # Color mapping
        color_map = {
            Component.API: Colors.API,
            Component.LM: Colors.LM,
            Component.STREAM: Colors.STREAM,
            Component.THINK: Colors.THINK,
            Component.SSE: Colors.STREAM,
            Component.FRONTEND: Colors.API,

            Component.COGNITIVE: "\033[38;5;213m", # Pink
            Component.PARALLEL: Colors.PARALLEL,
        }
        
        level_colors = {
            "INFO": Colors.RESET,
            "WARN": Colors.WARN,
            "ERROR": Colors.ERROR,
            "DEBUG": Colors.DEBUG,
        }
        
        parts = []
        
        # Timestamp
        if config.show_timestamps:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            parts.append(f"{Colors.DIM}{ts}{Colors.RESET}")
        
        # Request ID
        if config.show_request_id:
            req_id = _request_id.get()
            parts.append(f"{Colors.DIM}[{req_id}]{Colors.RESET}")
        
        # Component tag
        color = color_map.get(component, Colors.RESET)
        parts.append(f"{color}{Colors.BOLD}[{component.value:6}]{Colors.RESET}")
        
        # Level (only for non-INFO)
        if level != "INFO":
            parts.append(f"{level_colors.get(level, Colors.RESET)}{level}{Colors.RESET}")
        
        # Message
        parts.append(message)
        
        # Extra kwargs as key=value
        if kwargs:
            extras = " ".join(f"{Colors.DIM}{k}={Colors.RESET}{v}" for k, v in kwargs.items())
            parts.append(extras)
        
        return " ".join(parts)
    
    def _print(self, component: Component, message: str, level: str = "INFO", **kwargs):
        """Print formatted log line."""
        line = self._format(component, message, level, **kwargs)
        if line:
            print(line, file=sys.stderr, flush=True)
    
    # === Component-specific methods ===
    
    def api(self, message: str, **kwargs):
        """Log API layer events."""
        self._print(Component.API, message, **kwargs)
    
    def lm(self, message: str, **kwargs):
        """Log LM Client events."""
        self._print(Component.LM, message, **kwargs)
    
    def stream(self, message: str, **kwargs):
        """Log streaming events."""
        self._print(Component.STREAM, message, **kwargs)
    
    def think(self, message: str, **kwargs):
        """Log thinking/reasoning events."""
        self._print(Component.THINK, message, **kwargs)
    
    def sse(self, message: str, **kwargs):
        """Log SSE events."""
        self._print(Component.SSE, message, **kwargs)

    def cognitive(self, message: str, **kwargs):
        """Log Cognitive Loop events (System 2)."""
        self._print(Component.COGNITIVE, message, **kwargs)

    def parallel(self, message: str, **kwargs):
        """Log Parallel execution events."""
        self._print(Component.PARALLEL, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log errors from any component."""
        self._print(Component.API, message, level="ERROR", **kwargs)
    
    def warn(self, message: str, **kwargs):
        """Log warnings."""
        self._print(Component.API, message, level="WARN", **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug info (only when verbose)."""
        self._print(Component.API, message, level="DEBUG", **kwargs)
    
    # === Chunk logging ===
    
    def chunk(self, content: str, filtered: bool = False, chunk_num: int = 0):
        """Log a streaming chunk."""
        if not config.show_chunks:
            return
        
        preview = content[:config.max_chunk_preview]
        if len(content) > config.max_chunk_preview:
            preview += "..."
        
        # Escape newlines for single-line display
        preview = preview.replace("\n", "\\n").replace("\r", "")
        
        status = "🚫 FILTERED" if filtered else "✓"
        self._print(
            Component.STREAM, 
            f"[#{chunk_num:03d}] {status}",
            chars=len(content),
            preview=f'"{preview}"'
        )
    
    # === Timing helpers ===
    
    def start_timer(self, name: str):
        """Start a named timer."""
        self._start_times[name] = time.perf_counter()
    
    def end_timer(self, name: str) -> float:
        """End timer and return elapsed ms."""
        if name not in self._start_times:
            return 0.0
        elapsed = (time.perf_counter() - self._start_times.pop(name)) * 1000
        return round(elapsed, 2)
    
    # === Structured events ===
    
    def request_start(self, message: str, model: str, thinking_mode: str):
        """Log incoming chat request."""
        import uuid
        req_id = str(uuid.uuid4())[:8]
        self.set_request_id(req_id)
        self.start_timer("request")
        
        self.api("━" * 60)
        self.api(f"📨 REQUEST START", 
                 model=model, 
                 mode=thinking_mode,
                 msg=f'"{message[:40]}..."' if len(message) > 40 else f'"{message}"')
    
    def request_end(self, total_chunks: int, total_chars: int, filtered_chars: int):
        """Log request completion."""
        elapsed = self.end_timer("request")
        self.api(f"✅ REQUEST END",
                 duration=f"{elapsed}ms",
                 chunks=total_chunks,
                 output_chars=total_chars,
                 filtered_chars=filtered_chars)
        self.api("━" * 60)
    
    def lm_stream_start(self, model: str):
        """Log LM stream start."""
        self.start_timer("lm_stream")
        self.lm(f"🔌 Stream started", model=model)
    
    def lm_stream_end(self, chunk_count: int):
        """Log LM stream end."""
        elapsed = self.end_timer("lm_stream")
        self.lm(f"📤 Stream ended", 
                duration=f"{elapsed}ms", 
                chunks=chunk_count)
    
    def think_block_start(self, tag_type: str):
        """Log entering think block."""
        self.start_timer("think")
        self.think(f"🧠 THINK BLOCK START", tag=tag_type)
    
    def think_block_end(self, chars_filtered: int):
        """Log exiting think block."""
        elapsed = self.end_timer("think")
        self.think(f"🧠 THINK BLOCK END", 
                   duration=f"{elapsed}ms",
                   filtered=f"{chars_filtered} chars")
    
    def sse_yield(self, data_type: str, size: int):
        """Log SSE yield event."""
        self.sse(f"→ SSE", type=data_type, size=size)


# Global logger instance
log = Logger()


# Convenience function to enable/disable logging
def configure_logging(
    enabled: bool = True,
    show_chunks: bool = True,
    show_think_content: bool = False,
    components: Optional[set[str]] = None
):
    """Configure logging options at runtime."""
    config.enabled = enabled
    config.show_chunks = show_chunks
    config.show_think_content = show_think_content
    if components:
        config.component_filter = components
