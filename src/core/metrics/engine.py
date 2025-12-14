"""
Metrics Engine Module.

Core engine for IQ & Empathy metrics calculation.
"""
import json
import math
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Optional, Any

import aiosqlite

from .types import (
    MetricBreakdown, MetricResult, Achievement, AdaptationProof
)
from .analyzer import ImplicitFeedbackAnalyzer
from .storage import MetricsStorage


class MetricsEngine:
    """
    Core engine for IQ & Empathy metrics calculation.
    
    Provides API endpoints for React UI:
    - get_current_metrics() -> MetricResult for IQ and Empathy
    - get_achievements() -> List of achievements with progress
    - get_adaptation_proof() -> Comparison of early vs recent performance
    - record_interaction_outcome() -> Track each interaction
    """
    
    # Weight configuration for composite scores
    IQ_WEIGHTS = {
        "accuracy": 0.40,
        "correction": 0.30,
        "first_try": 0.20,
        "context": 0.10
    }
    
    EMPATHY_WEIGHTS = {
        "habit_match": 0.40,
        "mood": 0.25,
        "anticipation": 0.20,
        "friction": 0.15
    }
    
    def __init__(self, db: Optional[aiosqlite.Connection] = None):
        self._db = db
        self._feedback_analyzer = ImplicitFeedbackAnalyzer()
        self._storage = MetricsStorage(db)
        self._cache: dict[str, Any] = {}
        self._cache_ttl = 60  # seconds
        self._last_cache_time: Optional[datetime] = None
    
    async def initialize(self, db: aiosqlite.Connection):
        """Initialize with database connection."""
        self._db = db
        self._storage = MetricsStorage(db)
        await self._storage.initialize(db)
    
    def analyze_message(self, text: str) -> tuple[bool, bool, bool]:
        """
        Analyze user message for implicit feedback.
        
        Returns:
            tuple: (is_positive, is_negative, is_correction)
        """
        return self._feedback_analyzer.analyze(text)
    
    async def record_interaction_outcome(
        self,
        message_id: Optional[int] = None,
        user_message: str = "",
        was_correction: Optional[bool] = None,
        facts_in_context: int = 0,
        facts_referenced: int = 0,
        style_prompt_length: int = 0,
        response_time_ms: Optional[int] = None,
        detected_positive: Optional[bool] = None,
        detected_negative: Optional[bool] = None
    ):
        """
        Record outcome of an interaction for metrics calculation.
        
        Called after each assistant response.
        """
        # Auto-detect implicit signals from text
        implicit_pos, implicit_neg, detected_corr = self.analyze_message(user_message)
        
        # Use provided explicit values (if any), otherwise use implicit
        is_positive = detected_positive if detected_positive is not None else implicit_pos
        is_negative = detected_negative if detected_negative is not None else implicit_neg
        
        if was_correction is None:
            was_correction = detected_corr
        
        await self._storage.record_outcome(
            message_id=message_id,
            is_positive=is_positive,
            is_negative=is_negative,
            was_correction=was_correction,
            facts_in_context=facts_in_context,
            facts_referenced=facts_referenced,
            style_prompt_length=style_prompt_length,
            response_time_ms=response_time_ms
        )
        
        # Invalidate cache
        self._cache.clear()
        self._last_cache_time = None
        
        # Check for achievement updates
        await self._update_achievements()
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached value is still valid based on TTL."""
        if key not in self._cache:
            return False
        if self._last_cache_time is None:
            return False
        elapsed = (datetime.now() - self._last_cache_time).total_seconds()
        return elapsed < self._cache_ttl
    
    def _set_cache(self, key: str, value: Any):
        """Set cache value with timestamp."""
        self._cache[key] = value
        self._last_cache_time = datetime.now()
    
    async def calculate_iq(self) -> MetricResult:
        """
        Calculate IQ score based on outcome metrics.
        
        Components:
        - Accuracy Rate (40%): positive / (positive + negative)
        - Correction Rate (30%): 1 - corrections / total
        - First-Try Rate (20%): single exchanges / total
        - Context Utilization (10%): facts_used / facts_available
        """
        data = await self._storage.get_recent_outcomes(days=30)
        
        if not data["total"]:
            return self._empty_result("iq")
        
        # Calculate components
        accuracy = data["positive"] / max(1, data["positive"] + data["negative"])
        correction_rate = data["corrections"] / max(1, data["total"])
        
        # First-try success: interactions without any negative signal
        neutral_or_positive = data["total"] - data["negative"]
        first_try = neutral_or_positive / max(1, data["total"])
        
        context_util = data["avg_context_util"]
        
        # Weighted composite score
        score = (
            accuracy * self.IQ_WEIGHTS["accuracy"] +
            (1 - correction_rate) * self.IQ_WEIGHTS["correction"] +
            first_try * self.IQ_WEIGHTS["first_try"] +
            context_util * self.IQ_WEIGHTS["context"]
        ) * 100
        
        # Calculate level (logarithmic)
        level, progress = self._calculate_level(score)
        
        # Get trend
        trend, trend_value = await self._get_trend("iq", days=7)
        
        breakdown = MetricBreakdown(
            accuracy_rate=accuracy,
            correction_rate=correction_rate,
            first_try_rate=first_try,
            context_utilization=context_util
        )
        
        return MetricResult(
            score=score,
            level=level,
            progress=progress,
            breakdown=breakdown,
            trend=trend,
            trend_value=trend_value
        )
    
    async def calculate_empathy(self) -> MetricResult:
        """
        Calculate Empathy score based on user understanding.
        
        Components:
        - Habit Match (40%): profile completeness + habit richness
        - Mood Accuracy (25%): based on feedback after mood detection
        - Anticipation (20%): suggestions accepted rate
        - Friction Trend (15%): improvement in correction rate over time
        """
        profile_data = await self._get_profile_metrics()
        friction = await self._calculate_friction_trend()
        
        habit_match = profile_data["completeness"]
        mood_accuracy = profile_data["mood_success"]
        anticipation = profile_data["anticipation_rate"]
        
        # Normalize friction to 0-1 (negative friction = improving = higher score)
        friction_score = max(0, min(1, 0.5 - friction / 2))
        
        # Weighted composite score
        score = (
            habit_match * self.EMPATHY_WEIGHTS["habit_match"] +
            mood_accuracy * self.EMPATHY_WEIGHTS["mood"] +
            anticipation * self.EMPATHY_WEIGHTS["anticipation"] +
            friction_score * self.EMPATHY_WEIGHTS["friction"]
        ) * 100
        
        level, progress = self._calculate_level(score)
        trend, trend_value = await self._get_trend("empathy", days=7)
        
        breakdown = MetricBreakdown(
            habit_match=habit_match,
            mood_accuracy=mood_accuracy,
            anticipation_rate=anticipation,
            friction_trend=friction
        )
        
        return MetricResult(
            score=score,
            level=level,
            progress=progress,
            breakdown=breakdown,
            trend=trend,
            trend_value=trend_value
        )
    
    async def get_current_metrics(self) -> dict:
        """
        Get current IQ and Empathy metrics for UI.
        
        Returns dict ready for JSON serialization.
        """
        iq = await self.calculate_iq()
        empathy = await self.calculate_empathy()
        
        return {
            "iq": iq.to_dict(),
            "empathy": empathy.to_dict(),
            "updated_at": datetime.now().isoformat()
        }
    
    async def get_achievements(self) -> list[dict]:
        """Get all achievements with current progress for UI."""
        achievements = []
        
        rows = await self._storage.get_achievements()
        
        for row in rows:
            ach = Achievement(
                id=row[0],
                name=row[1],
                description=row[2],
                category=row[3],
                icon=row[4],
                threshold_type=row[5],
                threshold_value=row[6],
                current_value=row[7] or 0,
                unlocked=row[8] is not None,
                unlocked_at=datetime.fromisoformat(row[8]) if row[8] else None,
                notified=bool(row[9])
            )
            achievements.append(ach.to_dict())
        
        return achievements
    
    async def get_new_achievements(self) -> list[dict]:
        """Get newly unlocked achievements that haven't been notified."""
        achievements = []
        
        rows = await self._storage.get_new_achievements()
        
        for row in rows:
            ach = Achievement(
                id=row[0],
                name=row[1],
                description=row[2],
                category=row[3],
                icon=row[4],
                threshold_type=row[5],
                threshold_value=row[6],
                current_value=row[7] or 0,
                unlocked=True,
                unlocked_at=datetime.fromisoformat(row[8]) if row[8] else None
            )
            achievements.append(ach.to_dict())
            
            # Mark as notified
            await self._storage.mark_achievement_notified(row[0])
        
        return achievements
    
    async def get_adaptation_proof(self, comparison_days: int = 7) -> dict:
        """
        Get proof of adaptation by comparing early vs recent performance.
        
        This is the key API for showing "Day 1 vs Day 30" improvement.
        """
        rows = await self._storage.get_daily_metrics()
        
        if len(rows) < 2:
            return AdaptationProof(
                first_period_error_rate=0,
                last_period_error_rate=0,
                first_period_corrections=0,
                last_period_corrections=0,
                error_reduction_percent=0,
                correction_reduction_percent=0,
                iq_growth=0,
                empathy_growth=0,
                days_tracked=len(rows),
                verdict="📊 Недостаточно данных. Продолжайте общение!"
            ).to_dict()
        
        # Split into first period and last period
        first_rows = rows[:comparison_days]
        last_rows = rows[-comparison_days:]
        
        def calc_period(rs):
            total = sum(r[1] for r in rs if r[1])
            negative = sum(r[3] for r in rs if r[3])
            corrections = sum(r[4] for r in rs if r[4])
            iq = sum(r[5] for r in rs if r[5]) / max(1, len([r for r in rs if r[5]]))
            empathy = sum(r[6] for r in rs if r[6]) / max(1, len([r for r in rs if r[6]]))
            error_rate = negative / max(1, total)
            return error_rate, corrections, iq, empathy
        
        first_error, first_corr, first_iq, first_emp = calc_period(first_rows)
        last_error, last_corr, last_iq, last_emp = calc_period(last_rows)
        
        error_reduction = ((first_error - last_error) / max(0.01, first_error)) * 100 if first_error > 0 else 0
        corr_reduction = ((first_corr - last_corr) / max(1, first_corr)) * 100 if first_corr > 0 else 0
        
        if error_reduction > 30:
            verdict = f"🎉 Отличная адаптация! Ошибок меньше на {error_reduction:.0f}%"
        elif error_reduction > 10:
            verdict = f"📈 Хороший прогресс! Ошибок меньше на {error_reduction:.0f}%"
        elif error_reduction > 0:
            verdict = f"🌱 Начальная адаптация. Ошибок меньше на {error_reduction:.0f}%"
        elif len(rows) < 7:
            verdict = "📊 Идёт сбор данных. Подождите неделю для анализа."
        else:
            verdict = "🔧 Требуется больше фидбека для улучшения"
        
        return AdaptationProof(
            first_period_error_rate=first_error,
            last_period_error_rate=last_error,
            first_period_corrections=first_corr,
            last_period_corrections=last_corr,
            error_reduction_percent=error_reduction,
            correction_reduction_percent=corr_reduction,
            iq_growth=last_iq - first_iq,
            empathy_growth=last_emp - first_emp,
            days_tracked=len(rows),
            verdict=verdict
        ).to_dict()
    
    async def save_daily_metrics(self):
        """
        Aggregate today's interactions into daily_metrics.
        Should be called at end of day or on demand.
        """
        iq = await self.calculate_iq()
        empathy = await self.calculate_empathy()
        
        await self._storage.save_daily_metrics(
            iq_score=iq.score,
            empathy_score=empathy.score,
            iq_breakdown=asdict(iq.breakdown),
            empathy_breakdown=asdict(empathy.breakdown)
        )
    
    # ==================== Private Methods ====================
    
    async def _get_profile_metrics(self) -> dict:
        """Get profile-based metrics for empathy calculation."""
        row = await self._storage.get_profile_data()
        
        if not row:
            return {"completeness": 0, "mood_success": 0.5, "anticipation_rate": 0}
        
        name = row[0]
        prefs = json.loads(row[1] or "{}")
        habits = json.loads(row[2] or "{}")
        dislikes = json.loads(row[3] or "[]")
        
        # Calculate profile completeness
        completeness_factors = [
            1 if name else 0,
            min(1, len(prefs) / 5),
            min(1, len(habits.get("frequent_topics", [])) / 3),
            min(1, len(dislikes) / 2),
            min(1, habits.get("total_interactions", 0) / 50)
        ]
        completeness = sum(completeness_factors) / len(completeness_factors)
        
        # Mood success
        mood_row = await self._storage.get_mood_data()
        if mood_row and mood_row[0] > 0:
            negative_rate = mood_row[1] / mood_row[0]
            mood_success = max(0.3, min(1.0, 1 - negative_rate))
        else:
            mood_success = 0.5 + completeness * 0.2
        
        # Anticipation
        ant_row = await self._storage.get_anticipation_data()
        if ant_row and ant_row[0] >= 5:
            anticipation = ant_row[1] / ant_row[0]
        else:
            anticipation = 0.2 + completeness * 0.3
        
        return {
            "completeness": completeness,
            "mood_success": mood_success,
            "anticipation_rate": anticipation
        }
    
    async def _calculate_friction_trend(self) -> float:
        """Calculate trend in correction rate."""
        rows = await self._storage.get_friction_data()
        
        if len(rows) < 2:
            return 0.0
        
        today = date.today()
        cutoff = (today - timedelta(days=7)).isoformat()
        prev_period = [r for r in rows if r[0] < cutoff]
        last_period = [r for r in rows if r[0] >= cutoff]
        
        def calc_rate(period):
            total_corr = sum(r[1] for r in period)
            total_int = sum(r[2] for r in period)
            return total_corr / max(1, total_int)
        
        if not prev_period or not last_period:
            return 0.0
        
        prev_rate = calc_rate(prev_period)
        last_rate = calc_rate(last_period)
        
        return last_rate - prev_rate
    
    async def _get_trend(self, metric_type: str, days: int = 7) -> tuple[str, float]:
        """Get trend direction and value for a metric."""
        rows = await self._storage.get_trend_data(metric_type, days)
        
        if len(rows) < 2:
            return "stable", 0.0
        
        first_score = rows[0][0] or 0
        last_score = rows[-1][0] or 0
        
        diff = last_score - first_score
        
        if abs(diff) < 2:
            return "stable", diff
        elif diff > 0:
            return "up", diff
        else:
            return "down", diff
    
    def _calculate_level(self, score: float) -> tuple[int, float]:
        """Calculate level from score using logarithmic scaling."""
        if score <= 0:
            return 0, 0.0
        
        level = int(math.log2(score / 10 + 1))
        level = max(0, min(5, level))
        
        level_start = 10 * (2 ** level - 1) if level > 0 else 0
        level_end = 10 * (2 ** (level + 1) - 1)
        
        if level_end <= level_start:
            progress = 100.0
        else:
            progress = ((score - level_start) / (level_end - level_start)) * 100
            progress = max(0, min(100, progress))
        
        return level, progress
    
    async def _update_achievements(self):
        """Check and update achievement progress."""
        counts = await self._storage.get_achievement_counts()
        
        updates = [
            ("first_chat", counts["messages"]),
            ("first_thank", counts["positive"]),
            ("memory_10", counts["facts"]),
            ("memory_50", counts["facts"]),
            ("week_together", counts["active_days"]),
            ("month_together", counts["active_days"]),
            ("habit_5", min(5, counts["active_days"] // 3)),
        ]
        
        for ach_id, value in updates:
            await self._storage.update_achievement_value(ach_id, value)
    
    def _empty_result(self, metric_type: str) -> MetricResult:
        """Return empty result for cold start."""
        return MetricResult(
            score=0,
            level=0,
            progress=0,
            breakdown=MetricBreakdown(),
            trend="stable",
            trend_value=0
        )


# Global metrics engine instance
metrics_engine = MetricsEngine()
