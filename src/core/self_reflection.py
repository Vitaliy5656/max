"""
Self-Reflection System for MAX AI Assistant.

Creates an "architectural illusion of self-improvement" by showing
the LLM its own statistics and progress. This helps the model:
- Avoid repeating past mistakes
- Reinforce successful patterns
- Maintain consistent behavior

The model doesn't have memory between requests, but by injecting
statistics and examples into context, we can influence its behavior.

Usage:
    from .self_reflection import self_reflection
    
    prompt = await self_reflection.build_reflection_prompt()
    # Returns: "[📊 Твоя статистика] IQ: 72 → 85 (+13) ↑ ..."
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class ReflectionData:
    """Data for self-reflection prompt."""
    iq_week_ago: float
    iq_today: float
    iq_trend: str  # "↑", "↓", "→"
    empathy_week_ago: float
    empathy_today: float
    recent_mistakes: list[str]  # Concrete examples
    what_works: list[str]       # Success patterns
    streak_days: int            # Days without negative feedback


class SelfReflectionBuilder:
    """
    Builds self-reflection prompts showing model its progress.
    
    Philosophy:
    - LLM follows instructions - showing "don't repeat X" works
    - Concrete examples better than abstract rules
    - Numbers create context and "motivation"
    
    This COMPLEMENTS AdaptivePromptBuilder, doesn't replace it.
    """
    
    def __init__(self):
        self._db = None
        self._metrics_engine = None
        self._correction_detector = None
        self._feedback_miner = None
    
    async def initialize(self, db):
        """Initialize with database connection."""
        self._db = db
        
        # Get references to existing modules
        try:
            from .metrics import metrics_engine
            self._metrics_engine = metrics_engine
        except ImportError:
            pass
        
        try:
            from .adaptation import correction_detector, feedback_miner
            self._correction_detector = correction_detector
            self._feedback_miner = feedback_miner
        except ImportError:
            pass
    
    async def build_reflection_prompt(
        self,
        include_motivation: bool = True
    ) -> str:
        """
        Build a self-reflection prompt with statistics and examples.
        
        Args:
            include_motivation: Add motivational framing
            
        Returns:
            System prompt showing model its progress
        """
        if not self._db:
            return ""
        
        try:
            data = await self._gather_reflection_data()
        except Exception:
            return ""
        
        parts = []
        
        # 1. Statistics header
        parts.append(self._build_stats_section(data))
        
        # 2. Specific mistakes to avoid
        if data.recent_mistakes:
            parts.append(self._build_mistakes_section(data.recent_mistakes))
        
        # 3. What works well
        if data.what_works:
            parts.append(self._build_success_section(data.what_works))
        
        # 4. Motivational framing (optional)
        if include_motivation:
            parts.append(self._build_motivation_section(data))
        
        return "\n\n".join(parts)
    
    def _build_stats_section(self, data: ReflectionData) -> str:
        """Build statistics section."""
        iq_diff = data.iq_today - data.iq_week_ago
        empathy_diff = data.empathy_today - data.empathy_week_ago
        
        iq_sign = "+" if iq_diff > 0 else ""
        empathy_sign = "+" if empathy_diff > 0 else ""
        
        return f"""[📊 Твоя статистика]
IQ: {data.iq_week_ago:.0f} → {data.iq_today:.0f} ({iq_sign}{iq_diff:.0f}) {data.iq_trend}
Empathy: {data.empathy_week_ago:.0f} → {data.empathy_today:.0f} ({empathy_sign}{empathy_diff:.0f})
Streak: {data.streak_days} дней без негатива"""
    
    def _build_mistakes_section(self, mistakes: list[str]) -> str:
        """Build mistakes to avoid section."""
        items = "\n".join(f"  ❌ {m}" for m in mistakes[:3])
        return f"""[⚠️ Не повторяй эти ошибки]
{items}"""
    
    def _build_success_section(self, successes: list[str]) -> str:
        """Build what works section."""
        items = "\n".join(f"  ✓ {s}" for s in successes[:2])
        return f"""[✅ Что работает хорошо]
{items}"""
    
    def _build_motivation_section(self, data: ReflectionData) -> str:
        """Build motivational framing."""
        if data.iq_today > data.iq_week_ago:
            return "📈 Твой прогресс заметен. Продолжай в том же духе!"
        elif data.streak_days >= 3:
            return f"🔥 {data.streak_days} дней отличной работы! Не сбавляй."
        elif data.iq_today < data.iq_week_ago:
            return "💪 Небольшой спад — это нормально. Сосредоточься на точности."
        else:
            return "🎯 Стабильная работа. Есть потенциал для роста!"
    
    async def _gather_reflection_data(self) -> ReflectionData:
        """Gather all data for reflection using parallel fetches."""
        # Parallel data fetching for speed
        results = await asyncio.gather(
            self._get_iq_today(),
            self._get_metric_for_date("iq", days_ago=7),
            self._get_empathy_today(),
            self._get_metric_for_date("empathy", days_ago=7),
            self._get_recent_corrections(),
            self._get_success_patterns(),
            self._calculate_positive_streak(),
            return_exceptions=True
        )
        
        # Unpack results with fallbacks
        iq_today = results[0] if not isinstance(results[0], Exception) else 50.0
        iq_week_ago = results[1] if not isinstance(results[1], Exception) else 50.0
        empathy_today = results[2] if not isinstance(results[2], Exception) else 50.0
        empathy_week_ago = results[3] if not isinstance(results[3], Exception) else 50.0
        corrections = results[4] if not isinstance(results[4], Exception) else []
        patterns = results[5] if not isinstance(results[5], Exception) else []
        streak = results[6] if not isinstance(results[6], Exception) else 0
        
        # Determine trend
        iq_diff = iq_today - iq_week_ago
        if iq_diff > 5:
            trend = "↑"
        elif iq_diff < -5:
            trend = "↓"
        else:
            trend = "→"
        
        # Process mistakes into readable format
        mistakes = []
        for c in corrections[:3]:
            if isinstance(c, dict):
                category = c.get("category", "general")
                correction = c.get("correction", "")[:50]
                if category == "misunderstanding":
                    mistakes.append(f"Неправильно понял запрос: '{correction}...'")
                elif category == "style":
                    mistakes.append(f"Стиль не подошёл")
                elif category == "content":
                    mistakes.append(f"Ответил не на тот вопрос")
                else:
                    mistakes.append(f"Ошибка: {correction}...")
        
        return ReflectionData(
            iq_week_ago=iq_week_ago,
            iq_today=iq_today,
            iq_trend=trend,
            empathy_week_ago=empathy_week_ago,
            empathy_today=empathy_today,
            recent_mistakes=mistakes,
            what_works=patterns[:2],
            streak_days=streak
        )
    
    async def _get_iq_today(self) -> float:
        """Get today's IQ score."""
        if self._metrics_engine:
            result = await self._metrics_engine.calculate_iq()
            return result.score
        return 50.0
    
    async def _get_empathy_today(self) -> float:
        """Get today's Empathy score."""
        if self._metrics_engine:
            result = await self._metrics_engine.calculate_empathy()
            return result.score
        return 50.0
    
    async def _get_metric_for_date(self, metric_type: str, days_ago: int) -> float:
        """Get historical metric value."""
        if not self._db:
            return 50.0
        
        target_date = (datetime.now() - timedelta(days=days_ago)).date().isoformat()
        column = "iq_score" if metric_type == "iq" else "empathy_score"
        
        try:
            async with self._db.execute(f"""
                SELECT {column} FROM daily_metrics
                WHERE metric_date <= ?
                ORDER BY metric_date DESC
                LIMIT 1
            """, (target_date,)) as cursor:
                row = await cursor.fetchone()
            
            return row[0] if row and row[0] else 50.0
        except Exception:
            return 50.0
    
    async def _get_recent_corrections(self) -> list[dict]:
        """Get recent correction examples."""
        if not self._db:
            return []
        
        try:
            async with self._db.execute("""
                SELECT category, user_correction
                FROM correction_log
                ORDER BY created_at DESC
                LIMIT 3
            """) as cursor:
                rows = await cursor.fetchall()
            
            return [
                {"category": row[0], "correction": row[1]}
                for row in rows
            ]
        except Exception:
            return []
    
    async def _get_success_patterns(self) -> list[str]:
        """Get successful patterns."""
        if not self._db:
            return []
        
        try:
            async with self._db.execute("""
                SELECT extracted_pattern
                FROM success_patterns
                ORDER BY applied_count DESC
                LIMIT 2
            """) as cursor:
                rows = await cursor.fetchall()
            
            return [row[0] for row in rows if row[0]]
        except Exception:
            return []
    
    async def _calculate_positive_streak(self) -> int:
        """Calculate days without negative feedback."""
        if not self._db:
            return 0
        
        try:
            async with self._db.execute("""
                SELECT metric_date, negative_count
                FROM daily_metrics
                ORDER BY metric_date DESC
                LIMIT 30
            """) as cursor:
                rows = await cursor.fetchall()
            
            streak = 0
            for row in rows:
                negative = row[1] if row[1] else 0
                if negative == 0:
                    streak += 1
                else:
                    break
            
            return streak
        except Exception:
            return 0


# Global instance
self_reflection = SelfReflectionBuilder()


async def initialize_self_reflection(db):
    """Initialize self-reflection with database."""
    await self_reflection.initialize(db)
