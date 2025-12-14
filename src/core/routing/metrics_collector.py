"""
Metrics Collector for SmartRouter.

Collects and exposes metrics for monitoring and alerting.

Features:
    - Latency histograms
    - Request counters
    - Error rates
    - Prometheus-compatible format
"""
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta

from ..logger import log


@dataclass
class LatencyHistogram:
    """Simple histogram for latency tracking."""
    buckets: List[float] = field(default_factory=lambda: [10, 50, 100, 250, 500, 1000, 5000])
    counts: Dict[float, int] = field(default_factory=dict)
    total: float = 0.0
    count: int = 0
    
    def __post_init__(self):
        for bucket in self.buckets:
            self.counts[bucket] = 0
        self.counts[float('inf')] = 0
    
    def observe(self, value: float) -> None:
        """Record a latency observation."""
        self.total += value
        self.count += 1
        
        for bucket in self.buckets:
            if value <= bucket:
                self.counts[bucket] += 1
                return
        self.counts[float('inf')] += 1
    
    @property
    def mean(self) -> float:
        """Get mean latency."""
        if self.count == 0:
            return 0.0
        return self.total / self.count
    
    def percentile(self, p: float) -> float:
        """Estimate percentile from histogram."""
        target = self.count * p
        cumulative = 0
        
        for bucket in self.buckets:
            cumulative += self.counts[bucket]
            if cumulative >= target:
                return bucket
        return self.buckets[-1]


@dataclass
class Counter:
    """Simple counter metric."""
    value: int = 0
    
    def inc(self, amount: int = 1) -> None:
        self.value += amount
    
    def reset(self) -> None:
        self.value = 0


class MetricsCollector:
    """
    Collects routing metrics for monitoring.
    """
    
    def __init__(self):
        # Latency histograms
        self.routing_latency = LatencyHistogram()
        self.semantic_latency = LatencyHistogram()
        self.llm_latency = LatencyHistogram()
        
        # Request counters
        self.requests_total = Counter()
        self.requests_by_source: Dict[str, Counter] = defaultdict(Counter)
        self.requests_by_intent: Dict[str, Counter] = defaultdict(Counter)
        
        # Error counters
        self.errors_total = Counter()
        self.errors_by_type: Dict[str, Counter] = defaultdict(Counter)
        
        # Time window for rate calculations
        self._window_start = time.time()
        self._window_requests = 0
        
        log.debug("MetricsCollector initialized")
    
    def record_request(
        self,
        source: str,
        intent: str,
        latency_ms: float
    ) -> None:
        """Record a routing request."""
        self.requests_total.inc()
        self.requests_by_source[source].inc()
        self.requests_by_intent[intent].inc()
        self.routing_latency.observe(latency_ms)
        self._window_requests += 1
    
    def record_semantic_route(self, latency_ms: float) -> None:
        """Record semantic router latency."""
        self.semantic_latency.observe(latency_ms)
    
    def record_llm_route(self, latency_ms: float) -> None:
        """Record LLM router latency."""
        self.llm_latency.observe(latency_ms)
    
    def record_error(self, error_type: str) -> None:
        """Record an error."""
        self.errors_total.inc()
        self.errors_by_type[error_type].inc()
    
    def get_metrics(self) -> Dict:
        """Get all metrics in a structured format."""
        # Calculate request rate
        window_duration = time.time() - self._window_start
        rps = self._window_requests / window_duration if window_duration > 0 else 0
        
        return {
            "requests": {
                "total": self.requests_total.value,
                "by_source": {k: v.value for k, v in self.requests_by_source.items()},
                "by_intent": {k: v.value for k, v in self.requests_by_intent.items()},
                "per_second": round(rps, 2)
            },
            "latency": {
                "routing": {
                    "mean_ms": round(self.routing_latency.mean, 2),
                    "p50_ms": self.routing_latency.percentile(0.50),
                    "p95_ms": self.routing_latency.percentile(0.95),
                    "p99_ms": self.routing_latency.percentile(0.99),
                },
                "semantic": {
                    "mean_ms": round(self.semantic_latency.mean, 2),
                    "count": self.semantic_latency.count
                },
                "llm": {
                    "mean_ms": round(self.llm_latency.mean, 2),
                    "count": self.llm_latency.count
                }
            },
            "errors": {
                "total": self.errors_total.value,
                "by_type": {k: v.value for k, v in self.errors_by_type.items()},
                "rate": round(
                    self.errors_total.value / max(self.requests_total.value, 1) * 100, 2
                )
            }
        }
    
    def get_prometheus_format(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        # Requests
        lines.append(f"# HELP router_requests_total Total routing requests")
        lines.append(f"# TYPE router_requests_total counter")
        lines.append(f"router_requests_total {self.requests_total.value}")
        
        for source, counter in self.requests_by_source.items():
            lines.append(f'router_requests_total{{source="{source}"}} {counter.value}')
        
        # Latency
        lines.append(f"# HELP router_latency_seconds Routing latency")
        lines.append(f"# TYPE router_latency_seconds histogram")
        for bucket, count in self.routing_latency.counts.items():
            bucket_str = f"+Inf" if bucket == float('inf') else f"{bucket/1000:.3f}"
            lines.append(f'router_latency_seconds_bucket{{le="{bucket_str}"}} {count}')
        
        # Errors
        lines.append(f"# HELP router_errors_total Total errors")
        lines.append(f"# TYPE router_errors_total counter")
        lines.append(f"router_errors_total {self.errors_total.value}")
        
        return "\n".join(lines)
    
    def reset_window(self) -> None:
        """Reset rate calculation window."""
        self._window_start = time.time()
        self._window_requests = 0


# Global instance
_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


def record_request(source: str, intent: str, latency_ms: float) -> None:
    """Quick helper for recording requests."""
    get_metrics_collector().record_request(source, intent, latency_ms)
