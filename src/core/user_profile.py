"""
User Profile & Personalization System.

Features:
- Habits Database: Track user preferences and patterns
- Style Adaptation: Adjust response style based on preferences
- Feedback Learning: Learn from positive/negative feedback
- Mood Detection: Detect user mood from messages
- Soft Anticipation: Suggest relevant actions without being pushy
"""
import json
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass
from enum import Enum

import aiosqlite

from .config import config
from .lm_client import lm_client


class Mood(Enum):
    """User mood states."""
    HAPPY = "happy"
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    CURIOUS = "curious"
    BUSY = "busy"


class Verbosity(Enum):
    """Response verbosity levels."""
    BRIEF = "brief"
    BALANCED = "balanced"
    DETAILED = "detailed"


class Formality(Enum):
    """Response formality levels."""
    FORMAL = "formal"
    FRIENDLY = "friendly"
    CASUAL = "casual"


@dataclass
class UserPreferences:
    """User style preferences."""
    verbosity: Verbosity = Verbosity.BALANCED
    formality: Formality = Formality.FRIENDLY
    use_humor: bool = True
    use_emoji: bool = True
    prefer_lists: bool = True
    prefer_code_examples: bool = True
    language: str = "auto"  # auto, ru, en
    # Logic Fix: Security preference
    allow_dangerous: bool = False


@dataclass
class UserHabits:
    """Tracked user behavior patterns."""
    frequent_topics: list[str] = None
    preferred_formats: list[str] = None
    active_hours: list[int] = None
    average_message_length: int = 0
    total_interactions: int = 0
    
    def __post_init__(self):
        self.frequent_topics = self.frequent_topics or []
        self.preferred_formats = self.preferred_formats or []
        self.active_hours = self.active_hours or []


class UserProfile:
    """
    Manages user personalization and adaptation.
    
    Learns from:
    - Explicit preferences set by user
    - Implicit feedback (thumbs up/down)
    - Behavioral patterns
    - Mood signals in messages
    """
    
    def __init__(self, db: Optional[aiosqlite.Connection] = None):
        self._db = db
        self._preferences: Optional[UserPreferences] = None
        self._habits: Optional[UserHabits] = None
        self._dislikes: list[str] = []
        self._current_mood: Mood = Mood.NEUTRAL
        self._name: Optional[str] = None
        
    async def initialize(self, db: aiosqlite.Connection):
        """Load user profile from database."""
        self._db = db
        # P2 fix: Ensure profile exists before loading
        await self._ensure_profile_exists()
        await self._load_profile()

    async def _ensure_profile_exists(self):
        """Create default profile if it doesn't exist (P2 fix)."""
        await self._db.execute(
            """INSERT OR IGNORE INTO user_profile (id, name, preferences, habits, dislikes)
               VALUES (1, NULL, '{}', '{}', '[]')"""
        )
        await self._db.commit()
        
    async def _load_profile(self):
        """Load profile from database."""
        async with self._db.execute(
            "SELECT * FROM user_profile WHERE id = 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                self._name = row["name"]
                
                # Parse preferences
                prefs_data = json.loads(row["preferences"] or "{}")
                self._preferences = UserPreferences(
                    verbosity=Verbosity(prefs_data.get("verbosity", "balanced")),
                    formality=Formality(prefs_data.get("formality", "friendly")),
                    use_humor=prefs_data.get("use_humor", True),
                    use_emoji=prefs_data.get("use_emoji", True),
                    prefer_lists=prefs_data.get("prefer_lists", True),
                    prefer_code_examples=prefs_data.get("prefer_code_examples", True),
                    language=prefs_data.get("language", "auto"),
                    # Logic Fix: Load allow_dangerous preference
                    allow_dangerous=prefs_data.get("allow_dangerous", False)
                )
                
                # Parse habits
                habits_data = json.loads(row["habits"] or "{}")
                self._habits = UserHabits(
                    frequent_topics=habits_data.get("frequent_topics", []),
                    preferred_formats=habits_data.get("preferred_formats", []),
                    active_hours=habits_data.get("active_hours", []),
                    average_message_length=habits_data.get("average_message_length", 0),
                    total_interactions=habits_data.get("total_interactions", 0)
                )
                
                # Parse dislikes
                self._dislikes = json.loads(row["dislikes"] or "[]")
            else:
                self._preferences = UserPreferences()
                self._habits = UserHabits()
    
    async def _save_profile(self):
        """Save profile to database."""
        prefs_json = json.dumps({
            "verbosity": self._preferences.verbosity.value,
            "formality": self._preferences.formality.value,
            "use_humor": self._preferences.use_humor,
            "use_emoji": self._preferences.use_emoji,
            "prefer_lists": self._preferences.prefer_lists,
            "prefer_code_examples": self._preferences.prefer_code_examples,
            "language": self._preferences.language,
            # Logic Fix: Save allow_dangerous preference
            "allow_dangerous": self._preferences.allow_dangerous
        })
        
        habits_json = json.dumps({
            "frequent_topics": self._habits.frequent_topics,
            "preferred_formats": self._habits.preferred_formats,
            "active_hours": self._habits.active_hours,
            "average_message_length": self._habits.average_message_length,
            "total_interactions": self._habits.total_interactions
        })
        
        dislikes_json = json.dumps(self._dislikes)
        
        await self._db.execute(
            """UPDATE user_profile 
               SET name = ?, preferences = ?, habits = ?, dislikes = ?, 
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = 1""",
            (self._name, prefs_json, habits_json, dislikes_json)
        )
        await self._db.commit()
    
    # ==================== Preferences ====================
    
    async def update_preference(self, key: str, value: Any):
        """Update a specific preference."""
        if hasattr(self._preferences, key):
            if key == "verbosity":
                value = Verbosity(value)
            elif key == "formality":
                value = Formality(value)
            setattr(self._preferences, key, value)
            await self._save_profile()
    
    async def set_name(self, name: str):
        """Set user's name."""
        self._name = name
        await self._save_profile()
    
    # ==================== Style Prompt Generation ====================
    
    def get_style_prompt(self) -> str:
        """
        Generate a system prompt addition based on user preferences.
        This is added to every request to adapt response style.
        """
        parts = []
        
        # Name personalization
        if self._name:
            parts.append(f"Пользователя зовут {self._name}.")
        
        # Verbosity
        if self._preferences.verbosity == Verbosity.BRIEF:
            parts.append("Отвечай кратко и по существу. Избегай длинных объяснений.")
        elif self._preferences.verbosity == Verbosity.DETAILED:
            parts.append("Давай подробные развёрнутые ответы с объяснениями.")
        
        # Formality
        if self._preferences.formality == Formality.FORMAL:
            parts.append("Используй формальный стиль общения.")
        elif self._preferences.formality == Formality.CASUAL:
            parts.append("Общайся неформально, как с другом.")
        
        # Features
        if self._preferences.use_humor:
            parts.append("Можешь использовать лёгкий юмор, где уместно.")
        else:
            parts.append("Избегай шуток, будь серьёзен.")
            
        if self._preferences.use_emoji:
            parts.append("Используй эмодзи для наглядности.")
        else:
            parts.append("Не используй эмодзи.")
        
        if self._preferences.prefer_lists:
            parts.append("Структурируй информацию списками.")
        
        # Mood adaptation
        if self._current_mood == Mood.FRUSTRATED:
            parts.append("Пользователь возможно раздражён. Будь терпелив и понимающ. Избегай длинных преамбул.")
        elif self._current_mood == Mood.BUSY:
            parts.append("Пользователь занят. Отвечай максимально кратко.")
        elif self._current_mood == Mood.CURIOUS:
            parts.append("Пользователь заинтересован. Можешь дать дополнительные интересные детали.")
        
        # Dislikes
        if self._dislikes:
            parts.append(f"ИЗБЕГАЙ: {', '.join(self._dislikes[:5])}")
        
        return " ".join(parts) if parts else ""
    
    # ==================== Mood Detection ====================

    def analyze_mood(self, text: str) -> Mood:
        """
        Analyze mood from text without side effects.
        Returns detected mood without modifying state.
        """
        text_lower = text.lower()

        # Quick heuristic checks
        frustration_signals = [
            "не работает", "опять", "почему", "блин", "чёрт", "ошибка",
            "doesn't work", "again", "why", "damn", "error", "!!!"
        ]

        busy_signals = [
            "быстро", "срочно", "кратко", "нет времени",
            "quick", "urgent", "brief", "no time"
        ]

        curious_signals = [
            "интересно", "расскажи", "как работает", "почему так",
            "interesting", "tell me", "how does", "explain"
        ]

        happy_signals = [
            "спасибо", "отлично", "супер", "класс", "👍", "🎉",
            "thanks", "great", "awesome", "perfect"
        ]

        # Check signals
        if any(s in text_lower for s in frustration_signals):
            return Mood.FRUSTRATED
        elif any(s in text_lower for s in busy_signals):
            return Mood.BUSY
        elif any(s in text_lower for s in curious_signals):
            return Mood.CURIOUS
        elif any(s in text_lower for s in happy_signals):
            return Mood.HAPPY
        else:
            return Mood.NEUTRAL

    async def detect_mood(self, text: str) -> Mood:
        """
        Detect and set user mood from message text.
        Uses analyze_mood internally and updates state.
        """
        detected = self.analyze_mood(text)
        self.set_mood(detected)
        return detected

    def set_mood(self, mood: Mood):
        """Explicitly set user mood."""
        self._current_mood = mood

    def reset_mood_if_positive(self, text: str):
        """Reset negative mood if user shows positive signals."""
        if self._current_mood in (Mood.FRUSTRATED, Mood.BUSY):
            detected = self.analyze_mood(text)
            if detected == Mood.HAPPY:
                self._current_mood = Mood.NEUTRAL
    
    # ==================== Feedback Learning ====================
    
    async def record_feedback(
        self, 
        message_id: int, 
        positive: bool,
        reason: Optional[str] = None
    ):
        """
        Record user feedback on a response.
        Negative feedback helps avoid similar mistakes.
        """
        rating = 1 if positive else -1
        
        await self._db.execute(
            "INSERT INTO feedback (message_id, rating, reason) VALUES (?, ?, ?)",
            (message_id, rating, reason)
        )
        await self._db.commit()
        
        # If negative, try to learn what to avoid
        if not positive and reason:
            await self._learn_from_negative(reason)
    
    async def _learn_from_negative(self, reason: str):
        """Extract patterns to avoid from negative feedback."""
        # Add to dislikes if it's a pattern
        if len(reason) < 100:  # Short, specific complaint
            if reason not in self._dislikes:
                self._dislikes.append(reason)
                # Keep only last 20 dislikes
                self._dislikes = self._dislikes[-20:]
                await self._save_profile()
    
    # ==================== Habits Tracking ====================

    # Topic keywords for classification
    TOPIC_KEYWORDS = {
        "код": ["код", "функци", "класс", "метод", "переменн", "code", "function", "class"],
        "файлы": ["файл", "папк", "директор", "file", "folder", "directory", "path"],
        "git": ["git", "commit", "push", "pull", "branch", "merge"],
        "баги": ["баг", "ошибк", "bug", "error", "fix", "исправ"],
        "дизайн": ["дизайн", "ui", "ux", "интерфейс", "design", "style", "css"],
        "данные": ["данн", "база", "sql", "database", "db", "запрос", "query"],
        "api": ["api", "endpoint", "rest", "http", "request", "response"],
        "тесты": ["тест", "test", "assert", "mock", "pytest", "unittest"],
    }

    async def track_interaction(self, message: str):
        """Track user interaction patterns."""
        self._habits.total_interactions += 1

        # Track message length average
        length = len(message)
        prev_avg = self._habits.average_message_length
        self._habits.average_message_length = int(
            (prev_avg * (self._habits.total_interactions - 1) + length)
            / self._habits.total_interactions
        )

        # Track active hours
        hour = datetime.now().hour
        if hour not in self._habits.active_hours:
            self._habits.active_hours.append(hour)
            self._habits.active_hours = self._habits.active_hours[-24:]

        # Track frequent topics
        await self._track_topics(message)

        # Save periodically (P2 fix: reduced from 10 to 5 to minimize data loss on crash)
        if self._habits.total_interactions % 5 == 0:
            await self._save_profile()

    async def _track_topics(self, message: str):
        """Extract and track topics from message."""
        message_lower = message.lower()

        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(kw in message_lower for kw in keywords):
                # Add topic if not present, or move to end (most recent)
                if topic in self._habits.frequent_topics:
                    self._habits.frequent_topics.remove(topic)
                self._habits.frequent_topics.append(topic)

        # Keep only last 10 topics
        self._habits.frequent_topics = self._habits.frequent_topics[-10:]

    # ==================== Soft Anticipation ====================

    async def get_suggestions(self, context: str) -> list[str]:
        """
        Get soft suggestions based on context and user habits.
        Returns helpful hints without being pushy.
        """
        suggestions = []
        context_lower = context.lower()

        # Time-based suggestions
        hour = datetime.now().hour
        if 23 <= hour or hour < 6:
            suggestions.append("💤 Уже поздно, может отдохнёшь?")

        # Based on message complexity
        if self._habits.total_interactions > 0:
            avg_len = self._habits.average_message_length
            if len(context) > avg_len * 2:
                suggestions.append("📝 Похоже на сложную задачу. Может разбить на части?")

        # Context-aware suggestions based on content
        if any(kw in context_lower for kw in ["ошибк", "error", "не работает", "баг"]):
            suggestions.append("🔍 Попробуй добавить логирование для отладки")

        if any(kw in context_lower for kw in ["медленно", "slow", "долго", "тормоз"]):
            suggestions.append("⚡ Возможно стоит профилировать код")

        # Suggestions based on frequent topics
        if self._habits.frequent_topics:
            recent_topic = self._habits.frequent_topics[-1]
            topic_suggestions = {
                "тесты": "✅ Не забудь написать тесты",
                "git": "📦 Сделай коммит перед большими изменениями",
                "баги": "🐛 Проверь edge cases",
            }
            if recent_topic in topic_suggestions:
                suggestions.append(topic_suggestions[recent_topic])

        # Limit suggestions to avoid annoyance
        return suggestions[:2] if suggestions else []
    
    # ==================== Metrics Integration ====================
    
    def get_profile_completeness(self) -> float:
        """
        Calculate profile completeness for Empathy metric.
        
        Returns:
            float: 0-1 completeness score
        """
        factors = []
        
        # Name set?
        factors.append(1.0 if self._name else 0.0)
        
        # Preferences customized?
        prefs = self._preferences
        if prefs:
            pref_score = 0
            if prefs.verbosity != Verbosity.BALANCED:
                pref_score += 0.2
            if prefs.formality != Formality.FRIENDLY:
                pref_score += 0.2
            if not prefs.use_humor:
                pref_score += 0.2  # Explicitly turned off = personalized
            if not prefs.use_emoji:
                pref_score += 0.2
            if prefs.language != "auto":
                pref_score += 0.2
            factors.append(min(1.0, pref_score + 0.3))  # Base 0.3 for defaults
        else:
            factors.append(0.0)
        
        # Dislikes learned?
        factors.append(min(1.0, len(self._dislikes) / 5))  # 5 dislikes = full
        
        # Habits tracked?
        if self._habits:
            habits_score = 0
            if len(self._habits.frequent_topics) >= 3:
                habits_score += 0.4
            if len(self._habits.active_hours) >= 3:
                habits_score += 0.3
            if self._habits.total_interactions >= 20:
                habits_score += 0.3
            factors.append(habits_score)
        else:
            factors.append(0.0)
        
        return sum(factors) / len(factors) if factors else 0.0
    
    def get_habits_richness(self) -> float:
        """
        Calculate habits richness for Empathy metric.
        
        Returns:
            float: 0-1 richness score based on tracked habits
        """
        if not self._habits:
            return 0.0
        
        factors = []
        
        # Topics richness
        factors.append(min(1.0, len(self._habits.frequent_topics) / 8))
        
        # Formats richness
        factors.append(min(1.0, len(self._habits.preferred_formats) / 3))
        
        # Time coverage
        factors.append(min(1.0, len(self._habits.active_hours) / 12))
        
        # Interaction depth
        factors.append(min(1.0, self._habits.total_interactions / 100))
        
        return sum(factors) / len(factors) if factors else 0.0
    
    def get_habits_dict(self) -> dict:
        """
        Get habits as dictionary for anticipation engine.
        
        Returns:
            dict: Habits data for external use
        """
        if not self._habits:
            return {}
        
        return {
            "frequent_topics": self._habits.frequent_topics,
            "preferred_formats": self._habits.preferred_formats,
            "active_hours": self._habits.active_hours,
            "average_message_length": self._habits.average_message_length,
            "total_interactions": self._habits.total_interactions
        }
    
    @property
    def name(self) -> Optional[str]:
        return self._name
    
    @property
    def preferences(self) -> UserPreferences:
        return self._preferences
    
    @property
    def current_mood(self) -> Mood:
        return self._current_mood
    
    async def get_profile_summary_for_context(self, conversation_id: str) -> str:
        """
        Get a concise profile summary for System 2 cognitive context.
        """
        parts = []
        if self._name:
            parts.append(f"Name: {self._name}")
        
        if self._preferences:
            parts.append(f"Style: {self._preferences.verbosity.value}, {self._preferences.formality.value}")
            parts.append(f"Humor: {'Yes' if self._preferences.use_humor else 'No'}")
        
        if self._habits and self._habits.frequent_topics:
            topics = ", ".join(self._habits.frequent_topics[:5])
            parts.append(f"Interests: {topics}")
            
        if self._dislikes:
             parts.append(f"Avoid: {', '.join(self._dislikes)}")
             
        return " | ".join(parts)


# Global user profile instance
user_profile = UserProfile()
