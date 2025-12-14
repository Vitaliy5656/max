"""
Routing Observability for MAX AI.

Provides tracing, analytics, and feedback loop for router decisions.
Essential for debugging and continuous improvement.

Features:
    - Trace storage (ring buffer + persistent)
    - Analytics (hit rates, latencies)
    - Feedback endpoint for UI
    - Export for analysis
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

from ..logger import log


class FeedbackType(Enum):
    """User feedback types."""
    GOOD = "good"
    BAD = "bad"
    WRONG_INTENT = "wrong_intent"
    WRONG_PROMPT = "wrong_prompt"


@dataclass
class RoutingTrace:
    """Complete trace of a routing decision."""
    id: str
    timestamp: datetime
    message: str
    message_preview: str
    
    # Routing decision
    intent: str
    confidence: float
    routing_source: str  # semantic, llm, cpu, cache, speculative
    routing_time_ms: float
    
    # Prompt
    prompt_id: Optional[str] = None
    prompt_name: Optional[str] = None
    
    # Features
    temperature: float = 0.7
    use_rag: bool = True
    cache_hit: bool = False
    
    # Topic (for learning)
    detected_topic: Optional[str] = None
    
    # Feedback
    user_feedback: Optional[str] = None  # good, bad, wrong_intent
    corrected_intent: Optional[str] = None
    feedback_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dict for JSON serialization."""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        if self.feedback_time:
            d['feedback_time'] = self.feedback_time.isoformat()
        return d


class RoutingObserver:
    """
    Observability system for routing decisions.
    
    Provides:
        - Real-time tracing
        - Analytics and metrics
        - Feedback collection
        - Data export for model improvement
    """
    
    def __init__(self, max_traces: int = 1000, persist_path: Optional[Path] = None):
        self._traces: Dict[str, RoutingTrace] = {}
        self._trace_order: List[str] = []  # For ring buffer
        self._max_traces = max_traces
        self._persist_path = persist_path or Path("data/routing_traces.jsonl")
        
        # Analytics counters
        self._stats = {
            "total_requests": 0,
            "by_source": {"semantic": 0, "llm": 0, "cpu": 0, "cache": 0, "speculative": 0, "guardrail": 0},
            "by_intent": {},
            "feedback_good": 0,
            "feedback_bad": 0,
            "avg_latency_ms": 0.0,
            "total_latency_ms": 0.0,
        }
        
        log.debug("RoutingObserver initialized")
    
    def record(self, trace: RoutingTrace) -> None:
        """Record a routing trace."""
        # Add to memory
        self._traces[trace.id] = trace
        self._trace_order.append(trace.id)
        
        # Enforce max size (ring buffer)
        while len(self._trace_order) > self._max_traces:
            old_id = self._trace_order.pop(0)
            del self._traces[old_id]
        
        # Update stats
        self._stats["total_requests"] += 1
        self._stats["by_source"][trace.routing_source] = \
            self._stats["by_source"].get(trace.routing_source, 0) + 1
        self._stats["by_intent"][trace.intent] = \
            self._stats["by_intent"].get(trace.intent, 0) + 1
        self._stats["total_latency_ms"] += trace.routing_time_ms
        self._stats["avg_latency_ms"] = \
            self._stats["total_latency_ms"] / self._stats["total_requests"]
        
        # Fire-and-forget persist
        asyncio.create_task(self._persist_trace(trace))
    
    async def _persist_trace(self, trace: RoutingTrace) -> None:
        """Persist trace to file (append mode)."""
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(trace.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            log.error(f"Failed to persist trace: {e}")
    
    def add_feedback(
        self,
        trace_id: str,
        feedback: FeedbackType,
        corrected_intent: Optional[str] = None
    ) -> bool:
        """
        Add user feedback to a trace.
        
        Returns True if feedback was recorded.
        """
        if trace_id not in self._traces:
            log.warn(f"Trace not found for feedback: {trace_id}")
            return False
        
        trace = self._traces[trace_id]
        trace.user_feedback = feedback.value
        trace.corrected_intent = corrected_intent
        trace.feedback_time = datetime.now()
        
        # Update stats
        if feedback == FeedbackType.GOOD:
            self._stats["feedback_good"] += 1
        else:
            self._stats["feedback_bad"] += 1
        
        log.debug(f"Feedback recorded: {trace_id} -> {feedback.value}")
        return True
    
    def get_trace(self, trace_id: str) -> Optional[RoutingTrace]:
        """Get trace by ID."""
        return self._traces.get(trace_id)
    
    def get_recent_traces(self, limit: int = 50) -> List[RoutingTrace]:
        """Get most recent traces."""
        recent_ids = self._trace_order[-limit:]
        return [self._traces[tid] for tid in reversed(recent_ids) if tid in self._traces]
    
    def get_traces_by_intent(self, intent: str, limit: int = 50) -> List[RoutingTrace]:
        """Get traces for specific intent."""
        matching = [t for t in self._traces.values() if t.intent == intent]
        return sorted(matching, key=lambda t: t.timestamp, reverse=True)[:limit]
    
    def get_bad_feedback_traces(self, limit: int = 50) -> List[RoutingTrace]:
        """Get traces with negative feedback (for training)."""
        bad_traces = [
            t for t in self._traces.values()
            if t.user_feedback and t.user_feedback != FeedbackType.GOOD.value
        ]
        return sorted(bad_traces, key=lambda t: t.timestamp, reverse=True)[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analytics summary."""
        total = self._stats["total_requests"]
        if total == 0:
            return self._stats
        
        # Calculate hit rates
        stats = {**self._stats}
        stats["hit_rates"] = {
            source: count / total * 100
            for source, count in self._stats["by_source"].items()
        }
        stats["semantic_hit_rate"] = self._stats["by_source"]["semantic"] / total * 100
        stats["feedback_rate"] = (
            (self._stats["feedback_good"] + self._stats["feedback_bad"]) / total * 100
        )
        stats["accuracy_estimate"] = (
            self._stats["feedback_good"] / 
            max(1, self._stats["feedback_good"] + self._stats["feedback_bad"]) * 100
        )
        
        return stats
    
    def get_learning_dataset(self) -> List[Dict]:
        """
        Export data for training semantic router.
        
        Returns traces with good feedback for adding to training set.
        """
        good_traces = [
            t for t in self._traces.values()
            if t.user_feedback == FeedbackType.GOOD.value or t.user_feedback is None
        ]
        
        # Also include corrected traces
        corrected = [
            {
                "text": t.message,
                "intent": t.corrected_intent or t.intent,
                "topic": t.detected_topic,
                "source": "user_feedback"
            }
            for t in self._traces.values()
            if t.corrected_intent
        ]
        
        return corrected
    
    def clear(self) -> None:
        """Clear all traces (for testing)."""
        self._traces.clear()
        self._trace_order.clear()
        self._stats = {
            "total_requests": 0,
            "by_source": {"semantic": 0, "llm": 0, "cpu": 0, "cache": 0, "speculative": 0, "guardrail": 0},
            "by_intent": {},
            "feedback_good": 0,
            "feedback_bad": 0,
            "avg_latency_ms": 0.0,
            "total_latency_ms": 0.0,
        }


# Global instance
_observer: Optional[RoutingObserver] = None


def get_routing_observer() -> RoutingObserver:
    """Get or create global RoutingObserver."""
    global _observer
    if _observer is None:
        _observer = RoutingObserver()
    return _observer


def record_routing_trace(
    message: str,
    intent: str,
    confidence: float,
    routing_source: str,
    routing_time_ms: float,
    prompt_id: Optional[str] = None,
    prompt_name: Optional[str] = None,
    detected_topic: Optional[str] = None,
    cache_hit: bool = False,
    **kwargs
) -> str:
    """
    Quick helper to record a trace.
    
    Returns trace_id for feedback.
    """
    import uuid
    
    trace_id = str(uuid.uuid4())[:8]
    trace = RoutingTrace(
        id=trace_id,
        timestamp=datetime.now(),
        message=message,
        message_preview=message[:50],
        intent=intent,
        confidence=confidence,
        routing_source=routing_source,
        routing_time_ms=routing_time_ms,
        prompt_id=prompt_id,
        prompt_name=prompt_name,
        detected_topic=detected_topic,
        cache_hit=cache_hit,
        **kwargs
    )
    
    get_routing_observer().record(trace)
    return trace_id
