# Core modules
"""Core business logic for MAX AI Assistant."""

from .metrics import metrics_engine, MetricsEngine
from .adaptation import (
    correction_detector,
    feedback_miner,
    fact_tracker,
    prompt_builder,
    anticipation_engine,
    initialize_adaptation
)

__all__ = [
    # Metrics
    "metrics_engine",
    "MetricsEngine",
    # Adaptation
    "correction_detector",
    "feedback_miner", 
    "fact_tracker",
    "prompt_builder",
    "anticipation_engine",
    "initialize_adaptation",
]
