"""
Metrics Storage Module.

Handles database operations for the metrics system.
"""
import json
from dataclasses import asdict
from datetime import date, timedelta
from typing import Optional

import aiosqlite


class MetricsStorage:
    """Database operations for metrics system."""
    
    def __init__(self, db: Optional[aiosqlite.Connection] = None):
        self._db = db
    
    async def initialize(self, db: aiosqlite.Connection):
        """Initialize with database connection."""
        self._db = db
        await self._ensure_tables()
    
    async def _ensure_tables(self):
        """Create tables if they don't exist."""
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS interaction_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                session_date DATE NOT NULL,
                was_correction BOOLEAN DEFAULT FALSE,
                implicit_positive BOOLEAN DEFAULT FALSE,
                implicit_negative BOOLEAN DEFAULT FALSE,
                facts_in_context INTEGER DEFAULT 0,
                facts_referenced INTEGER DEFAULT 0,
                style_prompt_length INTEGER DEFAULT 0,
                response_time_ms INTEGER,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS daily_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_date DATE UNIQUE NOT NULL,
                total_interactions INTEGER DEFAULT 0,
                positive_count INTEGER DEFAULT 0,
                negative_count INTEGER DEFAULT 0,
                corrections_count INTEGER DEFAULT 0,
                avg_context_utilization REAL DEFAULT 0,
                iq_score REAL,
                empathy_score REAL,
                breakdown_json TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS achievements (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                icon TEXT,
                threshold_type TEXT,
                threshold_value REAL,
                current_value REAL DEFAULT 0,
                unlocked_at TIMESTAMP,
                notified BOOLEAN DEFAULT FALSE
            );
        """)
        await self._db.commit()
    
    async def record_outcome(
        self,
        message_id: Optional[int],
        is_positive: bool,
        is_negative: bool,
        was_correction: bool,
        facts_in_context: int,
        facts_referenced: int,
        style_prompt_length: int,
        response_time_ms: Optional[int]
    ):
        """Record an interaction outcome."""
        today = date.today()
        
        await self._db.execute("""
            INSERT INTO interaction_outcomes 
            (message_id, session_date, was_correction, implicit_positive, implicit_negative,
             facts_in_context, facts_referenced, style_prompt_length, response_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id, today.isoformat(), was_correction, is_positive, is_negative,
            facts_in_context, facts_referenced, style_prompt_length, response_time_ms
        ))
        await self._db.commit()
    
    async def get_recent_outcomes(self, days: int = 30) -> dict:
        """Get aggregated outcomes for recent days."""
        since = (date.today() - timedelta(days=days)).isoformat()
        
        async with self._db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN implicit_positive THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN implicit_negative THEN 1 ELSE 0 END) as negative,
                SUM(CASE WHEN was_correction THEN 1 ELSE 0 END) as corrections,
                AVG(CASE WHEN facts_in_context > 0 
                    THEN CAST(facts_referenced AS REAL) / facts_in_context 
                    ELSE 0.5 END) as avg_util
            FROM interaction_outcomes
            WHERE session_date >= ?
        """, (since,)) as cursor:
            row = await cursor.fetchone()
        
        return {
            "total": row[0] or 0,
            "positive": row[1] or 0,
            "negative": row[2] or 0,
            "corrections": row[3] or 0,
            "avg_context_util": row[4] or 0.5
        }
    
    async def get_daily_metrics(self) -> list:
        """Get all daily metrics ordered by date."""
        async with self._db.execute("""
            SELECT metric_date, total_interactions, positive_count, negative_count,
                   corrections_count, iq_score, empathy_score
            FROM daily_metrics
            ORDER BY metric_date ASC
        """) as cursor:
            return await cursor.fetchall()
    
    async def save_daily_metrics(
        self,
        iq_score: float,
        empathy_score: float,
        iq_breakdown: dict,
        empathy_breakdown: dict
    ):
        """Save daily aggregated metrics."""
        today = date.today()
        
        # Get today's outcomes
        async with self._db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN implicit_positive THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN implicit_negative THEN 1 ELSE 0 END) as negative,
                SUM(CASE WHEN was_correction THEN 1 ELSE 0 END) as corrections,
                AVG(CASE WHEN facts_in_context > 0 
                    THEN CAST(facts_referenced AS REAL) / facts_in_context 
                    ELSE 0 END) as avg_util
            FROM interaction_outcomes
            WHERE session_date = ?
        """, (today.isoformat(),)) as cursor:
            row = await cursor.fetchone()
        
        if not row or not row[0]:
            return
        
        breakdown = {
            "iq": iq_breakdown,
            "empathy": empathy_breakdown
        }
        
        await self._db.execute("""
            INSERT OR REPLACE INTO daily_metrics
            (metric_date, total_interactions, positive_count, negative_count,
             corrections_count, avg_context_utilization, iq_score, empathy_score, breakdown_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            today.isoformat(), row[0], row[1] or 0, row[2] or 0,
            row[3] or 0, row[4] or 0, iq_score, empathy_score, json.dumps(breakdown)
        ))
        await self._db.commit()
    
    async def get_trend_data(self, metric_type: str, days: int = 7) -> list:
        """Get metric scores for trend calculation."""
        since = (date.today() - timedelta(days=days)).isoformat()
        column = "iq_score" if metric_type == "iq" else "empathy_score"
        
        async with self._db.execute(f"""
            SELECT {column}, metric_date
            FROM daily_metrics
            WHERE metric_date >= ?
            ORDER BY metric_date ASC
        """, (since,)) as cursor:
            return await cursor.fetchall()
    
    async def get_friction_data(self) -> list:
        """Get correction data for friction trend calculation."""
        today = date.today()
        prev_week_start = (today - timedelta(days=14)).isoformat()
        
        async with self._db.execute("""
            SELECT 
                session_date,
                SUM(CASE WHEN was_correction THEN 1 ELSE 0 END) as corrections,
                COUNT(*) as total
            FROM interaction_outcomes
            WHERE session_date >= ?
            GROUP BY session_date
        """, (prev_week_start,)) as cursor:
            return await cursor.fetchall()
    
    async def get_profile_data(self) -> Optional[tuple]:
        """Get user profile for empathy calculation."""
        async with self._db.execute(
            "SELECT name, preferences, habits, dislikes FROM user_profile WHERE id = 1"
        ) as cursor:
            return await cursor.fetchone()
    
    async def get_mood_data(self) -> tuple:
        """Get recent interaction data for mood success calculation."""
        async with self._db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN implicit_negative THEN 1 ELSE 0 END) as negative
            FROM interaction_outcomes
            WHERE session_date >= date('now', '-7 days')
        """) as cursor:
            return await cursor.fetchone()
    
    async def get_anticipation_data(self) -> tuple:
        """Get positive feedback data for anticipation calculation."""
        async with self._db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN implicit_positive THEN 1 ELSE 0 END) as positive
            FROM interaction_outcomes
            WHERE session_date >= date('now', '-7 days')
        """) as cursor:
            return await cursor.fetchone()
    
    async def get_achievements(self) -> list:
        """Get all achievements from database."""
        async with self._db.execute("""
            SELECT id, name, description, category, icon, 
                   threshold_type, threshold_value, current_value,
                   unlocked_at, notified
            FROM achievements
            ORDER BY unlocked_at DESC NULLS LAST, threshold_value ASC
        """) as cursor:
            return await cursor.fetchall()
    
    async def get_new_achievements(self) -> list:
        """Get unlocked but not notified achievements."""
        async with self._db.execute("""
            SELECT id, name, description, category, icon, 
                   threshold_type, threshold_value, current_value,
                   unlocked_at, notified
            FROM achievements
            WHERE unlocked_at IS NOT NULL AND notified = FALSE
        """) as cursor:
            return await cursor.fetchall()
    
    async def mark_achievement_notified(self, ach_id: str):
        """Mark an achievement as notified."""
        await self._db.execute(
            "UPDATE achievements SET notified = TRUE WHERE id = ?",
            (ach_id,)
        )
        await self._db.commit()
    
    async def update_achievement_value(self, ach_id: str, value: float):
        """Update achievement current value."""
        await self._db.execute("""
            UPDATE achievements 
            SET current_value = ?
            WHERE id = ? AND (unlocked_at IS NULL OR current_value < ?)
        """, (value, ach_id, value))
        
        # Check if newly unlocked
        await self._db.execute("""
            UPDATE achievements
            SET unlocked_at = CURRENT_TIMESTAMP
            WHERE id = ? AND current_value >= threshold_value AND unlocked_at IS NULL
        """, (ach_id,))
        
        await self._db.commit()
    
    async def get_achievement_counts(self) -> dict:
        """Get counts for achievement progress calculation."""
        async with self._db.execute("SELECT COUNT(*) FROM messages") as cursor:
            msg_count = (await cursor.fetchone())[0]
        
        async with self._db.execute("SELECT COUNT(*) FROM memory_facts") as cursor:
            fact_count = (await cursor.fetchone())[0]
        
        async with self._db.execute(
            "SELECT COUNT(DISTINCT session_date) FROM interaction_outcomes"
        ) as cursor:
            active_days = (await cursor.fetchone())[0]
        
        async with self._db.execute("""
            SELECT COUNT(*) FROM interaction_outcomes WHERE implicit_positive = TRUE
        """) as cursor:
            positive_count = (await cursor.fetchone())[0]
        
        return {
            "messages": msg_count,
            "facts": fact_count,
            "active_days": active_days,
            "positive": positive_count
        }
