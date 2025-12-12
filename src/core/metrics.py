"""
IQ & Empathy Metrics Engine.

Outcome-based metrics system that tracks real adaptation quality:
- Accuracy Rate: positive feedback ratio
- Correction Rate: how often user corrects the model
- Context Utilization: how well we use stored facts
- Implicit Feedback: detecting "спасибо" vs "нет, не то"

Provides API for React UI to display metrics and achievements.
"""
import json
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from typing import Optional, Any
from enum import Enum

import aiosqlite


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


class ImplicitFeedbackAnalyzer:
    """Detects implicit positive/negative signals in user messages."""
    
    POSITIVE_SIGNALS = [
        # Благодарность и одобрение
        "спасибо", "благодарю", "благодарствую",
        "отлично", "превосходно", "замечательно", "великолепно", "прекрасно",
        "супер", "класс", "круто", "кайф", "огонь", "топ",
        "молодец", "молодчина", "умница",
        "хорошо", "неплохо", "нормально",
        "это то что надо", "то что нужно", "именно так",
        "да, это", "точно", "верно", "правильно", "абсолютно",
        "согласен", "согласна", "соглашусь",
        "понял", "понятно", "ясно", "разобрался",
        "именно", "в точку", "попал",
        "годится", "подходит", "устраивает", "сойдет",
        "работает", "получилось", "заработало", "решено",
        "ага", "угу", "окей", "ок", "лады", "гуд",
        
        # English
        "thanks", "thank you", "thx", "ty",
        "great", "awesome", "excellent", "perfect", "amazing", "wonderful",
        "nice", "good", "cool", "neat",
        "good job", "well done", "nicely done",
        "exactly", "precisely", "correct", "right",
        "yes", "yeah", "yep", "yup",
        "got it", "understood", "makes sense",
        "works", "working", "solved", "fixed"
    ]
    
    NEGATIVE_SIGNALS = [
        # Отрицание и несогласие
        "нет", "не то", "не так", "не совсем", "не совсем то",
        "неправильно", "ошибка", "неверно", "неточно",
        "ты ошибся", "ты ошибаешься", "ошибешься",
        "это неправда", "неправда",
        "плохо", "ужасно", "отвратительно", "кошмар",
        "не понимаешь", "не понял", "не поняла",
        "опять", "снова", "заново", "переделай", "исправь",
        "бред", "чушь", "ерунда", "глупость", "фигня",
        "не надо", "не нужно", "убери", "удали",
        "хватит", "достаточно", "прекрати", "стоп",
        "я же сказал", "я уже говорил", "повторяю",
        "ты издеваешься", "ты прикалываешься",
        "при чём тут", "не об этом", "не про это",
        "мимо", "промахнулся",
        "забудь", "неважно", "проехали",
        
        # Переспрашивание / непонимание
        "я имел в виду", "я имела в виду",
        "ты не понял", "ты не поняла",
        "другое", "другой", "иначе",
        
        # English
        "no", "nope", "wrong", "incorrect", "not right",
        "error", "mistake", "fail",
        "bad", "terrible", "awful",
        "not what i", "that's not", "this is not",
        "i meant", "i said", "i asked",
        "again", "redo", "retry", "fix",
        "stop", "enough", "nevermind", "forget it"
    ]
    
    CORRECTION_SIGNALS = [
        # Русские паттерны коррекции
        "нет, я имел в виду",
        "нет, я имела в виду",
        "нет, имелось в виду",
        "не так, я хотел",
        "не так, я хотела",
        "ты не понял",
        "ты не поняла",
        "ты меня не понял",
        "я хотел сказать",
        "я хотела сказать",
        "имелось в виду",
        "другое, я про",
        "не то что я просил",
        "не то что я просила",
        "я просил другое",
        "я просила другое",
        "перечитай мой вопрос",
        "перечитай что я написал",
        "я же написал",
        "я же сказал",
        "не это, а",
        "совсем не то",
        "вообще не то",
        "абсолютно не то",
        "нет-нет-нет",
        "стоп, не так",
        "подожди, не то",
        "слушай внимательнее",
        "читай внимательнее",
        
        # English correction patterns
        "no, i meant",
        "no i meant",
        "that's not what i",
        "thats not what i",
        "not what i asked",
        "not what i meant",
        "i was asking about",
        "i meant something else",
        "reread my question",
        "read again",
        "you misunderstood",
        "you got it wrong",
        "let me rephrase",
        "let me clarify"
    ]
    
    # Words that indicate emphasis (important) when in caps, not frustration
    EMPHASIS_CONTEXT = [
        "важно", "внимание", "срочно", "обязательно", "критично",
        "запомни", "учти", "никогда", "всегда", "только",
        "именно", "ключевое", "главное", "основное",
        "important", "urgent", "critical", "never", "always", "must",
        "note", "remember", "key", "main", "only"
    ]
    
    # Minimum caps ratio to consider it significant (avoid short words)
    MIN_CAPS_RATIO = 0.5
    MIN_CAPS_LENGTH = 3  # Minimum word length to analyze for caps
    
    def analyze(self, text: str) -> tuple[bool, bool, bool]:
        """
        Analyze text for implicit feedback signals.
        
        Returns:
            tuple: (is_positive, is_negative, is_correction)
        """
        text_lower = text.lower()
        
        is_positive = any(sig in text_lower for sig in self.POSITIVE_SIGNALS)
        is_negative = any(sig in text_lower for sig in self.NEGATIVE_SIGNALS)
        is_correction = any(sig in text_lower for sig in self.CORRECTION_SIGNALS)
        
        # Correction overrides simple negative
        if is_correction:
            is_negative = True
        
        # CAPS detection with context
        caps_analysis = self._analyze_caps(text, is_negative)
        if caps_analysis == "frustration":
            is_negative = True
        elif caps_analysis == "emphasis" and not is_negative:
            # Emphasis is neutral, not negative
            pass
        
        return is_positive, is_negative, is_correction
    
    def _analyze_caps(self, text: str, already_negative: bool) -> str:
        """
        Analyze CAPS usage in text to determine intent.
        
        Returns:
            "frustration" - angry caps (negative signal)
            "emphasis" - important emphasis (neutral)
            "none" - no significant caps
        """
        # Find all caps words (3+ chars)
        words = text.split()
        caps_words = []
        
        for word in words:
            # Remove punctuation for analysis
            clean = ''.join(c for c in word if c.isalpha())
            if len(clean) >= self.MIN_CAPS_LENGTH:
                upper_count = sum(1 for c in clean if c.isupper())
                ratio = upper_count / len(clean)
                if ratio >= self.MIN_CAPS_RATIO:
                    caps_words.append(clean)
        
        if not caps_words:
            return "none"
        
        # Calculate overall caps presence
        total_alpha = sum(1 for c in text if c.isalpha())
        total_upper = sum(1 for c in text if c.isupper())
        
        if total_alpha == 0:
            return "none"
        
        caps_ratio = total_upper / total_alpha
        
        # If less than 20% caps overall, probably not significant
        if caps_ratio < 0.2:
            return "none"
        
        # Check context: is it emphasis or frustration?
        text_lower = text.lower()
        
        # Check for emphasis context
        is_emphasis = any(ctx in text_lower for ctx in self.EMPHASIS_CONTEXT)
        
        # Check for frustration signals
        frustration_signals = [
            "!!!", "?!",  # Multiple punctuation
            "блин", "черт", "damn", "hell",  # Mild swearing
            "сколько раз", "я же", "опять",  # Repetition frustration
            "почему ты не", "зачем ты",  # Questioning actions
        ]
        has_frustration = any(sig in text_lower for sig in frustration_signals)
        
        # Decision logic
        if has_frustration or already_negative:
            # CAPS + frustration signals = definitely frustrated
            return "frustration"
        elif is_emphasis:
            # CAPS + emphasis words = just highlighting importance
            return "emphasis"
        elif caps_ratio > 0.7:
            # Very high caps ratio with no context = likely frustration
            return "frustration"
        else:
            # Default to emphasis if unclear
            return "emphasis"
    
    def get_caps_info(self, text: str) -> dict:
        """
        Get detailed caps analysis for debugging/UI.
        
        Returns dict with caps ratio, interpretation, etc.
        """
        total_alpha = sum(1 for c in text if c.isalpha())
        total_upper = sum(1 for c in text if c.isupper())
        
        caps_ratio = total_upper / total_alpha if total_alpha > 0 else 0
        interpretation = self._analyze_caps(text, False)
        
        return {
            "caps_ratio": round(caps_ratio, 2),
            "interpretation": interpretation,
            "significant": caps_ratio >= 0.2
        }


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
        self._cache: dict[str, Any] = {}
        self._cache_ttl = 60  # seconds
        self._last_cache_time: Optional[datetime] = None
    
    async def initialize(self, db: aiosqlite.Connection):
        """Initialize with database connection."""
        self._db = db
        # Ensure tables exist (they should from schema.sql)
        await self._ensure_tables()
    
    async def _ensure_tables(self):
        """Create tables if they don't exist."""
        # Tables are created via schema.sql, but we ensure achievements exist
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
        # P1 Fix: Allow explicit feedback signals
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
        
        # Invalidate cache (set time for TTL tracking)
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
        # Get recent data (last 30 days)
        data = await self._get_recent_outcomes(days=30)
        
        if not data["total"]:
            return self._empty_result("iq")
        
        # Calculate components
        accuracy = data["positive"] / max(1, data["positive"] + data["negative"])
        correction_rate = data["corrections"] / max(1, data["total"])
        
        # First-try success: interactions without any negative signal
        # (different from correction_rate which only counts explicit corrections)
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
        # Get profile data
        profile_data = await self._get_profile_metrics()
        
        # Get friction trend
        friction = await self._calculate_friction_trend()
        
        # Calculate components
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
        
        async with self._db.execute("""
            SELECT id, name, description, category, icon, 
                   threshold_type, threshold_value, current_value,
                   unlocked_at, notified
            FROM achievements
            ORDER BY unlocked_at DESC NULLS LAST, threshold_value ASC
        """) as cursor:
            rows = await cursor.fetchall()
        
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
        
        async with self._db.execute("""
            SELECT id, name, description, category, icon, 
                   threshold_type, threshold_value, current_value,
                   unlocked_at, notified
            FROM achievements
            WHERE unlocked_at IS NOT NULL AND notified = FALSE
        """) as cursor:
            rows = await cursor.fetchall()
        
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
            await self._db.execute(
                "UPDATE achievements SET notified = TRUE WHERE id = ?",
                (row[0],)
            )
        
        await self._db.commit()
        return achievements
    
    async def get_adaptation_proof(self, comparison_days: int = 7) -> dict:
        """
        Get proof of adaptation by comparing early vs recent performance.
        
        This is the key API for showing "Day 1 vs Day 30" improvement.
        """
        # Get all daily metrics
        async with self._db.execute("""
            SELECT metric_date, total_interactions, positive_count, negative_count,
                   corrections_count, iq_score, empathy_score
            FROM daily_metrics
            ORDER BY metric_date ASC
        """) as cursor:
            rows = await cursor.fetchall()
        
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
        
        # Calculate metrics for each period
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
        
        # Calculate improvements
        error_reduction = ((first_error - last_error) / max(0.01, first_error)) * 100 if first_error > 0 else 0
        corr_reduction = ((first_corr - last_corr) / max(1, first_corr)) * 100 if first_corr > 0 else 0
        
        # Generate verdict
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
        
        # Calculate scores
        iq = await self.calculate_iq()
        empathy = await self.calculate_empathy()
        
        breakdown = {
            "iq": asdict(iq.breakdown),
            "empathy": asdict(empathy.breakdown)
        }
        
        await self._db.execute("""
            INSERT OR REPLACE INTO daily_metrics
            (metric_date, total_interactions, positive_count, negative_count,
             corrections_count, avg_context_utilization, iq_score, empathy_score, breakdown_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            today.isoformat(), row[0], row[1] or 0, row[2] or 0,
            row[3] or 0, row[4] or 0, iq.score, empathy.score, json.dumps(breakdown)
        ))
        await self._db.commit()
    
    # ==================== Private Methods ====================
    
    async def _get_recent_outcomes(self, days: int = 30) -> dict:
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
    
    async def _get_profile_metrics(self) -> dict:
        """Get profile-based metrics for empathy calculation."""
        # Get profile data
        async with self._db.execute(
            "SELECT name, preferences, habits, dislikes FROM user_profile WHERE id = 1"
        ) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            return {"completeness": 0, "mood_success": 0.5, "anticipation_rate": 0}
        
        name = row[0]
        prefs = json.loads(row[1] or "{}")
        habits = json.loads(row[2] or "{}")
        dislikes = json.loads(row[3] or "[]")
        
        # Calculate profile completeness
        completeness_factors = [
            1 if name else 0,
            min(1, len(prefs) / 5),  # At least 5 preferences
            min(1, len(habits.get("frequent_topics", [])) / 3),  # At least 3 topics
            min(1, len(dislikes) / 2),  # At least 2 dislikes learned
            min(1, habits.get("total_interactions", 0) / 50)  # At least 50 interactions
        ]
        completeness = sum(completeness_factors) / len(completeness_factors)
        
        # Mood success: Calculate from actual feedback data
        # Good mood detection = fewer negative signals after responses
        async with self._db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN implicit_negative THEN 1 ELSE 0 END) as negative
            FROM interaction_outcomes
            WHERE session_date >= date('now', '-7 days')
        """) as cursor:
            mood_row = await cursor.fetchone()
        
        if mood_row and mood_row[0] > 0:
            # Invert negative rate: fewer negatives = better mood understanding
            negative_rate = mood_row[1] / mood_row[0]
            mood_success = max(0.3, min(1.0, 1 - negative_rate))
        else:
            # Cold start: default to neutral, boosted by profile completeness
            mood_success = 0.5 + completeness * 0.2
        
        # Anticipation: Based on positive feedback rate (proxy for successful predictions)
        async with self._db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN implicit_positive THEN 1 ELSE 0 END) as positive
            FROM interaction_outcomes
            WHERE session_date >= date('now', '-7 days')
        """) as cursor:
            ant_row = await cursor.fetchone()
        
        if ant_row and ant_row[0] >= 5:
            # Positive rate indicates we anticipated user needs correctly
            anticipation = ant_row[1] / ant_row[0]
        else:
            # Cold start: base anticipation boosted by profile completeness
            anticipation = 0.2 + completeness * 0.3
        
        return {
            "completeness": completeness,
            "mood_success": mood_success,
            "anticipation_rate": anticipation
        }
    
    async def _calculate_friction_trend(self) -> float:
        """
        Calculate trend in correction rate.
        Negative = improving, Positive = getting worse.
        """
        # Compare recent week to previous week
        today = date.today()
        last_week_start = (today - timedelta(days=7)).isoformat()
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
            rows = await cursor.fetchall()
        
        if len(rows) < 2:
            return 0.0
        
        # Split into two periods
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
        
        # Positive = more errors now, Negative = fewer errors now
        return last_rate - prev_rate
    
    async def _get_trend(self, metric_type: str, days: int = 7) -> tuple[str, float]:
        """Get trend direction and value for a metric."""
        since = (date.today() - timedelta(days=days)).isoformat()
        
        column = "iq_score" if metric_type == "iq" else "empathy_score"
        
        async with self._db.execute(f"""
            SELECT {column}, metric_date
            FROM daily_metrics
            WHERE metric_date >= ?
            ORDER BY metric_date ASC
        """, (since,)) as cursor:
            rows = await cursor.fetchall()
        
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
        """
        Calculate level from score using logarithmic scaling.
        
        Level 0: 0-10
        Level 1: 10-25
        Level 2: 25-45
        Level 3: 45-70
        Level 4: 70-90
        Level 5: 90-100
        """
        import math
        
        if score <= 0:
            return 0, 0.0
        
        # Logarithmic level calculation
        level = int(math.log2(score / 10 + 1))
        level = max(0, min(5, level))  # Cap at level 5
        
        # Progress within level
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
        # Get counts for achievements
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
        
        # Update achievement values
        updates = [
            ("first_chat", msg_count),
            ("first_thank", positive_count),
            ("memory_10", fact_count),
            ("memory_50", fact_count),
            ("week_together", active_days),
            ("month_together", active_days),
            ("habit_5", min(5, active_days // 3)),  # Proxy for habits
        ]
        
        for ach_id, value in updates:
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
