"""
Adaptation Engine — Real User Adaptation Techniques.

Implements:
1. AdaptivePromptBuilder - Dynamic system prompts based on success patterns
2. CorrectionDetector - Learn from user corrections  
3. FeedbackMiner - Extract patterns from positive/negative feedback
4. FactEffectivenessTracker - Prioritize facts that actually help

These techniques make the model genuinely adapt to user preferences.
"""
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Any

import aiosqlite

from .config import config


@dataclass
class SuccessPattern:
    """A pattern extracted from successful interactions."""
    id: int
    pattern: str           # What worked
    category: str          # style, format, depth, approach
    context: str          # When to apply
    applied_count: int
    
    def to_dict(self) -> dict:
        return {
            "pattern": self.pattern,
            "category": self.category,
            "context": self.context
        }


@dataclass
class CorrectionEntry:
    """A learned correction from user feedback."""
    id: int
    original: str         # What we said wrong
    correction: str       # What user wanted
    pattern: str          # Extracted rule
    category: str         # style, content, format, misunderstanding
    applied_count: int
    
    def to_dict(self) -> dict:
        return {
            "pattern": self.pattern,
            "category": self.category
        }


class CorrectionDetector:
    """
    Detects when user is correcting the model and extracts learnings.
    
    Correction signals:
    - "нет, я имел в виду..."
    - "не так, я хотел..."
    - "ты не понял, я про..."
    """
    
    CORRECTION_PATTERNS = [
        # Русские паттерны — misunderstanding
        (r"нет,?\s*(я\s+)?(имел|имела|имею)\s+в\s+виду", "misunderstanding"),
        (r"ты\s+(меня\s+)?не\s+понял", "misunderstanding"),
        (r"ты\s+(меня\s+)?не\s+поняла", "misunderstanding"),
        (r"я\s+(хотел|хотела)\s+сказать", "misunderstanding"),
        (r"имелось\s+в\s+виду", "misunderstanding"),
        (r"перечитай\s+(мой\s+)?(вопрос|что)", "misunderstanding"),
        (r"я\s+же\s+(написал|сказал)", "misunderstanding"),
        (r"слушай\s+внимательн", "misunderstanding"),
        (r"читай\s+внимательн", "misunderstanding"),
        
        # Русские паттерны — content
        (r"не\s+так,?\s*(я\s+)?(хотел|хотела)", "content"),
        (r"другое,?\s*(я\s+)?про", "content"),
        (r"не\s+то,?\s+(что|о\s+чём)", "content"),
        (r"не\s+это,?\s+а", "content"),
        (r"совсем\s+не\s+то", "content"),
        (r"вообще\s+не\s+то", "content"),
        (r"абсолютно\s+не\s+то", "content"),
        (r"не\s+про\s+это", "content"),
        (r"не\s+об\s+этом", "content"),
        (r"при\s+чём\s+тут", "content"),
        
        # Русские паттерны — style
        (r"слишком\s+(длинно|коротко|сложно|просто|много|мало)", "style"),
        (r"без\s+(эмодзи|смайлов|юмора|воды)", "style"),
        (r"короче\s+(напиши|скажи|давай)", "style"),
        (r"подробнее\s+(напиши|расскажи)", "style"),
        (r"проще\s+(объясни|скажи)", "style"),
        
        # English patterns — misunderstanding
        (r"no,?\s*i\s+meant", "misunderstanding"),
        (r"that'?s\s+not\s+what\s+i", "misunderstanding"),
        (r"you\s+(mis)?understood", "misunderstanding"),
        (r"you\s+got\s+it\s+wrong", "misunderstanding"),
        (r"let\s+me\s+(rephrase|clarify)", "misunderstanding"),
        (r"reread\s+(my|the)\s+question", "misunderstanding"),
        (r"read\s+again", "misunderstanding"),
        
        # English patterns — content
        (r"not\s+what\s+i\s+(asked|meant|wanted)", "content"),
        (r"i\s+was\s+asking\s+about", "content"),
        (r"i\s+meant\s+something\s+else", "content"),
        (r"wrong\s+(topic|thing|answer)", "content"),
        
        # English patterns — style  
        (r"too\s+(long|short|complex|simple|much|verbose)", "style"),
        (r"more\s+(details?|specific|brief)", "style"),
        (r"less\s+(details?|verbose|text)", "style"),
    ]
    
    def __init__(self, db: Optional[aiosqlite.Connection] = None):
        self._db = db
    
    async def initialize(self, db: aiosqlite.Connection):
        """Initialize with database connection."""
        self._db = db
    
    def detect(self, text: str) -> tuple[bool, Optional[str]]:
        """
        Detect if text contains a correction.
        
        Returns:
            tuple: (is_correction, category)
        """
        text_lower = text.lower()
        
        for pattern, category in self.CORRECTION_PATTERNS:
            if re.search(pattern, text_lower):
                return True, category
        
        return False, None
    
    async def record_correction(
        self,
        original_message_id: int,
        correction_message_id: int,
        original_response: str,
        user_correction: str,
        lm_client: Any = None
    ):
        """
        Record a correction and optionally extract pattern via LLM.
        """
        is_correction, category = self.detect(user_correction)
        
        if not is_correction:
            return
        
        # Extract pattern (simple version without LLM)
        pattern = self._extract_simple_pattern(user_correction, category)
        
        await self._db.execute("""
            INSERT INTO correction_log 
            (original_message_id, correction_message_id, original_response, 
             user_correction, extracted_pattern, category)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            original_message_id, correction_message_id, 
            original_response[:500], user_correction[:500],
            pattern, category
        ))
        await self._db.commit()
    
    def _extract_simple_pattern(self, correction: str, category: str) -> str:
        """Extract a simple pattern without LLM."""
        patterns = {
            "style": "Адаптировать стиль ответа",
            "content": "Уточнить содержание перед ответом",
            "format": "Изменить формат вывода",
            "misunderstanding": "Переспросить если неясно"
        }
        return patterns.get(category, "Учесть коррекцию пользователя")
    
    async def get_recent_corrections(self, limit: int = 5) -> list[CorrectionEntry]:
        """Get recent corrections for prompt context."""
        async with self._db.execute("""
            SELECT id, original_response, user_correction, extracted_pattern, 
                   category, applied_count
            FROM correction_log
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
        
        return [
            CorrectionEntry(
                id=row[0],
                original=row[1],
                correction=row[2],
                pattern=row[3],
                category=row[4],
                applied_count=row[5]
            )
            for row in rows
        ]


class FeedbackMiner:
    """
    Mines patterns from positive and negative feedback.
    
    Positive feedback → Success patterns to replicate
    Negative feedback → Patterns to avoid
    """
    
    def __init__(self, db: Optional[aiosqlite.Connection] = None):
        self._db = db
    
    async def initialize(self, db: aiosqlite.Connection):
        """Initialize with database connection."""
        self._db = db
    
    async def record_success_pattern(
        self,
        message_id: int,
        response_summary: str,
        category: str = "general",
        relevance_context: str = ""
    ):
        """Record a successful response pattern."""
        # Simple pattern extraction
        pattern = f"Успешный подход: {category}"
        
        await self._db.execute("""
            INSERT INTO success_patterns 
            (message_id, response_summary, extracted_pattern, category, relevance_context)
            VALUES (?, ?, ?, ?, ?)
        """, (message_id, response_summary[:500], pattern, category, relevance_context))
        await self._db.commit()
    
    async def get_success_patterns(self, category: Optional[str] = None, limit: int = 5) -> list[SuccessPattern]:
        """Get success patterns, optionally filtered by category."""
        if category:
            query = """
                SELECT id, extracted_pattern, category, relevance_context, applied_count
                FROM success_patterns
                WHERE category = ?
                ORDER BY applied_count DESC, created_at DESC
                LIMIT ?
            """
            params = (category, limit)
        else:
            query = """
                SELECT id, extracted_pattern, category, relevance_context, applied_count
                FROM success_patterns
                ORDER BY applied_count DESC, created_at DESC
                LIMIT ?
            """
            params = (limit,)
        
        async with self._db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
        
        return [
            SuccessPattern(
                id=row[0],
                pattern=row[1],
                category=row[2],
                context=row[3],
                applied_count=row[4]
            )
            for row in rows
        ]
    
    async def increment_pattern_usage(self, pattern_id: int):
        """Mark a pattern as used."""
        await self._db.execute(
            "UPDATE success_patterns SET applied_count = applied_count + 1 WHERE id = ?",
            (pattern_id,)
        )
        await self._db.commit()


class FactEffectivenessTracker:
    """
    Tracks which facts are actually helpful when used in context.
    
    Facts that lead to positive outcomes → higher priority
    Facts that lead to negative outcomes → lower priority
    """
    
    def __init__(self, db: Optional[aiosqlite.Connection] = None):
        self._db = db
    
    async def initialize(self, db: aiosqlite.Connection):
        """Initialize with database connection."""
        self._db = db
    
    async def record_fact_usage(
        self,
        fact_id: int,
        was_positive: bool
    ):
        """Record that a fact was used and the outcome."""
        # Ensure effectiveness record exists
        await self._db.execute("""
            INSERT OR IGNORE INTO fact_effectiveness (fact_id, times_used, positive_outcomes, negative_outcomes)
            VALUES (?, 0, 0, 0)
        """, (fact_id,))
        
        # Update counts
        if was_positive:
            await self._db.execute("""
                UPDATE fact_effectiveness 
                SET times_used = times_used + 1, positive_outcomes = positive_outcomes + 1
                WHERE fact_id = ?
            """, (fact_id,))
        else:
            await self._db.execute("""
                UPDATE fact_effectiveness 
                SET times_used = times_used + 1, negative_outcomes = negative_outcomes + 1
                WHERE fact_id = ?
            """, (fact_id,))
        
        await self._db.commit()
    
    async def get_effective_fact_ids(self, limit: int = 10) -> list[int]:
        """Get IDs of most effective facts for prioritization."""
        async with self._db.execute("""
            SELECT fact_id FROM fact_effectiveness
            WHERE times_used >= 2
            ORDER BY effectiveness_score DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
        
        return [row[0] for row in rows]
    
    async def get_fact_score(self, fact_id: int) -> float:
        """Get effectiveness score for a specific fact."""
        async with self._db.execute("""
            SELECT effectiveness_score FROM fact_effectiveness
            WHERE fact_id = ?
        """, (fact_id,)) as cursor:
            row = await cursor.fetchone()
        
        return row[0] if row else 0.5  # Default neutral score


class AdaptivePromptBuilder:
    """
    Builds dynamic system prompts based on learned patterns.
    
    Components:
    1. Base style from user preferences
    2. Recent corrections to avoid
    3. Success patterns to replicate
    4. Effective facts context
    """
    
    def __init__(
        self,
        db: Optional[aiosqlite.Connection] = None,
        correction_detector: Optional[CorrectionDetector] = None,
        feedback_miner: Optional[FeedbackMiner] = None
    ):
        self._db = db
        self._correction_detector = correction_detector or CorrectionDetector()
        self._feedback_miner = feedback_miner or FeedbackMiner()
    
    async def initialize(self, db: aiosqlite.Connection):
        """Initialize with database connection."""
        self._db = db
        await self._correction_detector.initialize(db)
        await self._feedback_miner.initialize(db)
    
    async def build_adaptive_prompt(
        self,
        base_style_prompt: str = "",
        include_corrections: bool = True,
        include_successes: bool = True,
        context_hint: str = ""
    ) -> str:
        """
        Build an adaptive system prompt that learns from history.
        
        Args:
            base_style_prompt: Base prompt from user_profile.get_style_prompt()
            include_corrections: Include recent correction learnings
            include_successes: Include success patterns
            context_hint: Current context for pattern matching
            
        Returns:
            Enhanced system prompt
        """
        parts = []
        
        # 1. Base style
        if base_style_prompt:
            parts.append(base_style_prompt)
        
        # 2. Corrections to avoid
        if include_corrections:
            corrections = await self._correction_detector.get_recent_corrections(limit=3)
            if corrections:
                correction_hints = [c.pattern for c in corrections]
                parts.append(f"УЧТИ ПРЕДПОЧТЕНИЯ: {'; '.join(correction_hints)}")
        
        # 3. Success patterns to replicate
        if include_successes:
            patterns = await self._feedback_miner.get_success_patterns(limit=2)
            if patterns:
                success_hints = [p.pattern for p in patterns]
                parts.append(f"ПРИМЕНЯЙ: {'; '.join(success_hints)}")
        
        # 4. Add interaction stats for context
        stats = await self._get_interaction_stats()
        if stats["total"] >= 10:
            accuracy = stats["positive"] / max(1, stats["positive"] + stats["negative"])
            if accuracy > 0.8:
                parts.append("Текущий стиль общения работает хорошо, продолжай.")
            elif accuracy < 0.5:
                parts.append("Будь более внимателен к запросам пользователя.")
        
        return " ".join(parts)
    
    async def _get_interaction_stats(self) -> dict:
        """Get recent interaction statistics."""
        week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
        
        async with self._db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN implicit_positive THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN implicit_negative THEN 1 ELSE 0 END) as negative
            FROM interaction_outcomes
            WHERE session_date >= ?
        """, (week_ago,)) as cursor:
            row = await cursor.fetchone()
        
        return {
            "total": row[0] or 0,
            "positive": row[1] or 0,
            "negative": row[2] or 0
        }
    
    async def get_prompt_enhancement_length(self) -> int:
        """Get the length of adaptive additions for metrics tracking."""
        prompt = await self.build_adaptive_prompt()
        return len(prompt)


class AnticipationEngine:
    """
    Predicts user needs based on patterns.
    
    Analyzes:
    - Frequent action sequences
    - Time-based patterns
    - Context triggers
    """
    
    # Common action sequences
    SEQUENCES = {
        "написал код": ["запусти тест", "проверь ошибки", "отформатируй"],
        "git": ["commit", "push", "статус"],
        "ошибка": ["логи", "отладка", "стектрейс"],
        "файл": ["создай", "редактируй", "удали"],
    }
    
    def __init__(self, db: Optional[aiosqlite.Connection] = None):
        self._db = db
    
    async def initialize(self, db: aiosqlite.Connection):
        """Initialize with database connection."""
        self._db = db
    
    async def get_suggestions(self, context: str, user_habits: dict) -> list[str]:
        """
        Get anticipation suggestions based on context and habits.
        
        Returns list of predicted useful actions.
        """
        suggestions = []
        context_lower = context.lower()
        
        # Pattern-based suggestions
        for trigger, actions in self.SEQUENCES.items():
            if trigger in context_lower:
                suggestions.extend(actions[:2])  # Max 2 per trigger
        
        # Time-based suggestions
        hour = datetime.now().hour
        active_hours = user_habits.get("active_hours", [])
        
        if 22 <= hour or hour < 6:
            if active_hours and hour not in active_hours:
                suggestions.append("Отдохни?")
        
        # Topic-based from frequent topics
        frequent_topics = user_habits.get("frequent_topics", [])
        if frequent_topics:
            recent_topic = frequent_topics[-1] if frequent_topics else None
            topic_suggestions = {
                "тесты": "Напиши тест",
                "git": "Сделай коммит",
                "баги": "Проверь edge cases"
            }
            if recent_topic in topic_suggestions:
                suggestions.append(topic_suggestions[recent_topic])
        
        return suggestions[:3]  # Limit to 3 suggestions


# Global instances
correction_detector = CorrectionDetector()
feedback_miner = FeedbackMiner()
fact_tracker = FactEffectivenessTracker()
prompt_builder = AdaptivePromptBuilder()
anticipation_engine = AnticipationEngine()


async def initialize_adaptation(db: aiosqlite.Connection):
    """Initialize all adaptation components with database."""
    await correction_detector.initialize(db)
    await feedback_miner.initialize(db)
    await fact_tracker.initialize(db)
    await prompt_builder.initialize(db)
    await anticipation_engine.initialize(db)
