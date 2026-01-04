"""
Metrics Types Module.

Contains all dataclasses and enums used by the metrics system.
"""
import json
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Optional
from enum import Enum


class MetricCategory(Enum):
    """Categories for metrics and achievements."""
    IQ = "iq"
    EMPATHY = "empathy"
    GENERAL = "general"


@dataclass
class MetricBreakdown:
    """Detailed breakdown of a metric score."""
    accuracy_rate: float = 0.0        # 0-1
    correction_rate: float = 0.0      # 0-1 (lower is better)
    first_try_rate: float = 0.0       # 0-1
    context_utilization: float = 0.0  # 0-1
    habit_match: float = 0.0          # 0-1
    mood_accuracy: float = 0.0        # 0-1
    anticipation_rate: float = 0.0    # 0-1
    friction_trend: float = 0.0       # negative = improving


@dataclass
class MetricResult:
    """Result of metric calculation for UI."""
    score: float                      # 0-100 composite score
    level: int                        # Computed level (logarithmic)
    progress: float                   # 0-100 progress to next level
    breakdown: MetricBreakdown
    trend: str                        # "up", "down", "stable"
    trend_value: float                # Percentage change
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization (React API)."""
        return {
            "score": round(self.score, 1),
            "level": self.level,
            "progress": round(self.progress, 1),
            "trend": self.trend,
            "trend_value": round(self.trend_value, 1),
            "breakdown": asdict(self.breakdown)
        }


@dataclass
class Achievement:
    """Achievement data for UI."""
    id: str
    name: str
    description: str
    category: str
    icon: str
    threshold_type: str
    threshold_value: float
    current_value: float
    unlocked: bool
    unlocked_at: Optional[datetime] = None
    notified: bool = False
    
    @property
    def progress(self) -> float:
        """Progress to unlock (0-100)."""
        if self.unlocked:
            return 100.0
        if self.threshold_value <= 0:
            return 0.0
        return min(100.0, (self.current_value / self.threshold_value) * 100)
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "progress": round(self.progress, 1),
            "unlocked": self.unlocked,
            "unlocked_at": self.unlocked_at.isoformat() if self.unlocked_at else None
        }


@dataclass
class AdaptationProof:
    """Proof of adaptation for UI (Day 1 vs Day 30 comparison)."""
    first_period_error_rate: float
    last_period_error_rate: float
    first_period_corrections: int
    last_period_corrections: int
    error_reduction_percent: float
    correction_reduction_percent: float
    iq_growth: float
    empathy_growth: float
    days_tracked: int
    verdict: str
    
    def to_dict(self) -> dict:
        return {
            "first_period": {
                "error_rate": round(self.first_period_error_rate * 100, 1),
                "corrections": self.first_period_corrections
            },
            "last_period": {
                "error_rate": round(self.last_period_error_rate * 100, 1),
                "corrections": self.last_period_corrections
            },
            "improvement": {
                "error_reduction": f"{round(self.error_reduction_percent, 1)}%",
                "correction_reduction": f"{round(self.correction_reduction_percent, 1)}%",
                "iq_growth": f"+{round(self.iq_growth, 1)} points",
                "empathy_growth": f"+{round(self.empathy_growth, 1)} points"
            },
            "days_tracked": self.days_tracked,
            "verdict": self.verdict
        }


@dataclass 
class DailySummary:
    """Daily metrics summary."""
    date: date
    total_interactions: int
    positive_count: int
    negative_count: int
    corrections_count: int
    iq_score: float
    empathy_score: float
