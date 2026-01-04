"""
Response Formatter for MAX AI.

Formats response metadata for frontend display.
Provides confidence indicators, timing info, and debug data.

Features:
    - Confidence display formatting
    - Timing breakdown
    - Source attribution
    - Debug mode data
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..logger import log


@dataclass
class FormattedResponse:
    """Formatted response with metadata."""
    content: str
    
    # Confidence display
    confidence_percent: int
    confidence_label: str
    confidence_color: str
    
    # Timing
    routing_time_ms: float
    total_time_ms: float
    
    # Source
    source: str
    intent: str
    
    # Debug (optional)
    debug: Optional[Dict[str, Any]] = None


class ResponseFormatter:
    """
    Formats routing results for frontend display.
    """
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        log.debug("ResponseFormatter initialized")
    
    def format(
        self,
        content: str,
        confidence: float,
        routing_time_ms: float,
        source: str = "unknown",
        intent: str = "unknown",
        total_time_ms: float = 0.0,
        extra_debug: Optional[Dict] = None
    ) -> FormattedResponse:
        """Format response with metadata."""
        
        # Confidence display
        confidence_percent = int(confidence * 100)
        confidence_label = self._get_confidence_label(confidence)
        confidence_color = self._get_confidence_color(confidence)
        
        # Debug data
        debug = None
        if self.debug_mode:
            debug = {
                "raw_confidence": confidence,
                "source": source,
                "routing_ms": routing_time_ms,
                **(extra_debug or {})
            }
        
        return FormattedResponse(
            content=content,
            confidence_percent=confidence_percent,
            confidence_label=confidence_label,
            confidence_color=confidence_color,
            routing_time_ms=routing_time_ms,
            total_time_ms=total_time_ms,
            source=source,
            intent=intent,
            debug=debug
        )
    
    def _get_confidence_label(self, confidence: float) -> str:
        """Get human-readable confidence label."""
        if confidence >= 0.9:
            return "Высокая"
        elif confidence >= 0.7:
            return "Хорошая"
        elif confidence >= 0.5:
            return "Средняя"
        else:
            return "Низкая"
    
    def _get_confidence_color(self, confidence: float) -> str:
        """Get color for confidence indicator."""
        if confidence >= 0.9:
            return "#22c55e"  # Green
        elif confidence >= 0.7:
            return "#84cc16"  # Lime
        elif confidence >= 0.5:
            return "#eab308"  # Yellow
        else:
            return "#f97316"  # Orange
    
    def format_timing_breakdown(
        self,
        routing_ms: float,
        rag_ms: float = 0.0,
        llm_ms: float = 0.0,
        tools_ms: float = 0.0
    ) -> Dict[str, Any]:
        """Format timing breakdown for display."""
        total = routing_ms + rag_ms + llm_ms + tools_ms
        
        breakdown = []
        if routing_ms > 0:
            breakdown.append({"name": "Routing", "ms": routing_ms, "percent": routing_ms / total * 100})
        if rag_ms > 0:
            breakdown.append({"name": "RAG", "ms": rag_ms, "percent": rag_ms / total * 100})
        if llm_ms > 0:
            breakdown.append({"name": "LLM", "ms": llm_ms, "percent": llm_ms / total * 100})
        if tools_ms > 0:
            breakdown.append({"name": "Tools", "ms": tools_ms, "percent": tools_ms / total * 100})
        
        return {
            "total_ms": total,
            "breakdown": breakdown
        }
    
    def format_source_badge(self, source: str) -> Dict[str, str]:
        """Format source badge for UI."""
        badges = {
            "semantic": {"label": "🎯 Semantic", "color": "#8b5cf6"},
            "llm": {"label": "🤖 LLM", "color": "#3b82f6"},
            "cpu": {"label": "⚡ CPU", "color": "#f59e0b"},
            "cache": {"label": "💾 Cache", "color": "#10b981"},
            "speculative": {"label": "⚡ Instant", "color": "#06b6d4"},
        }
        return badges.get(source, {"label": source, "color": "#6b7280"})


# Global instance
_formatter: Optional[ResponseFormatter] = None


def get_response_formatter(debug_mode: bool = False) -> ResponseFormatter:
    """Get or create global formatter."""
    global _formatter
    if _formatter is None:
        _formatter = ResponseFormatter(debug_mode=debug_mode)
    return _formatter


def format_response(content: str, **kwargs) -> FormattedResponse:
    """Quick helper for formatting."""
    return get_response_formatter().format(content, **kwargs)
