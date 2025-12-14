"""
Request Context for SmartRouter.

Carries all context through the routing pipeline.
Enables consistent access to request metadata.

Features:
    - User information
    - Session state
    - Timing
    - Feature flags
"""
import time
import uuid
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from contextvars import ContextVar

from ..logger import log


@dataclass
class UserContext:
    """User-specific context."""
    user_id: str = "anonymous"
    session_id: Optional[str] = None
    is_authenticated: bool = False
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    # User tier for rate limiting/features
    tier: str = "free"  # free, pro, enterprise


@dataclass
class FeatureFlags:
    """Feature flags for A/B testing and rollouts."""
    use_semantic_router: bool = True
    use_llm_router: bool = True
    use_rag: bool = True
    use_tools: bool = True
    use_shadow_mode: bool = False
    debug_mode: bool = False
    
    # Experimental features
    use_auto_learning: bool = True
    use_tone_adaptation: bool = True
    use_context_optimization: bool = True


@dataclass
class RequestContext:
    """
    Complete context for a routing request.
    
    Carries all information needed through the pipeline.
    """
    # Request info
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # User context
    user: UserContext = field(default_factory=UserContext)
    
    # Feature flags
    features: FeatureFlags = field(default_factory=FeatureFlags)
    
    # Conversation context
    conversation_id: Optional[str] = None
    message_history: List[Dict[str, str]] = field(default_factory=list)
    
    # Timing
    start_time: float = field(default_factory=time.perf_counter)
    
    # Results (populated during pipeline)
    routing_result: Optional[Any] = None
    errors: List[str] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def elapsed_ms(self) -> float:
        """Time elapsed since request start."""
        return (time.perf_counter() - self.start_time) * 1000
    
    def add_error(self, error: str) -> None:
        """Record an error."""
        self.errors.append(error)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging/debugging."""
        return {
            "request_id": self.request_id,
            "message_preview": self.message[:50] if self.message else "",
            "user_id": self.user.user_id,
            "conversation_id": self.conversation_id,
            "elapsed_ms": self.elapsed_ms(),
            "errors": self.errors,
            "features": {
                "semantic_router": self.features.use_semantic_router,
                "llm_router": self.features.use_llm_router,
                "shadow_mode": self.features.use_shadow_mode,
            }
        }


# Context variable for async access
_current_context: ContextVar[Optional[RequestContext]] = ContextVar('request_context', default=None)


def get_current_context() -> Optional[RequestContext]:
    """Get current request context."""
    return _current_context.get()


def set_current_context(ctx: RequestContext) -> None:
    """Set current request context."""
    _current_context.set(ctx)


def create_context(
    message: str,
    user_id: str = "anonymous",
    conversation_id: Optional[str] = None,
    **kwargs
) -> RequestContext:
    """Create a new request context."""
    ctx = RequestContext(
        message=message,
        conversation_id=conversation_id,
        user=UserContext(user_id=user_id),
        **kwargs
    )
    set_current_context(ctx)
    log.debug(f"Context created: {ctx.request_id}")
    return ctx


class RequestContextManager:
    """Context manager for request lifecycle."""
    
    def __init__(self, message: str, **kwargs):
        self.message = message
        self.kwargs = kwargs
        self.ctx: Optional[RequestContext] = None
    
    def __enter__(self) -> RequestContext:
        self.ctx = create_context(self.message, **self.kwargs)
        return self.ctx
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.ctx:
            elapsed = self.ctx.elapsed_ms()
            log.debug(f"Context {self.ctx.request_id} completed in {elapsed:.1f}ms")
        _current_context.set(None)
        return False
