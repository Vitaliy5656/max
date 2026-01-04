"""
Metrics Package.

IQ & Empathy Metrics Engine for MAX AI Assistant.

Outcome-based metrics system that tracks real adaptation quality:
- Accuracy Rate: positive feedback ratio
- Correction Rate: how often user corrects the model
- Context Utilization: how well we use stored facts
- Implicit Feedback: detecting "спасибо" vs "нет, не то"

Provides API for React UI to display metrics and achievements.
"""

from .types import (
    MetricCategory,
    MetricBreakdown,
    MetricResult,
    Achievement,
    AdaptationProof,
    DailySummary
)
from .analyzer import ImplicitFeedbackAnalyzer
from .storage import MetricsStorage
from .engine import MetricsEngine, metrics_engine

__all__ = [
    # Types
    "MetricCategory",
    "MetricBreakdown", 
    "MetricResult",
    "Achievement",
    "AdaptationProof",
    "DailySummary",
    # Classes
    "ImplicitFeedbackAnalyzer",
    "MetricsStorage",
    "MetricsEngine",
    # Global instance
    "metrics_engine"
]
