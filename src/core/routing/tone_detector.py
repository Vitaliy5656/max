"""
Emotional Tone Detection for MAX AI.

CPU-based heuristics for detecting emotional tone in messages.
Used for response adaptation without additional LLM calls.

Features:
    - Tone classification (neutral, positive, negative, urgent)
    - Formality detection
    - Emoji analysis
    - Punctuation patterns
"""
import re
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum

from ..logger import log


class EmotionalTone(Enum):
    """Detected emotional tones."""
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    URGENT = "urgent"
    FRUSTRATED = "frustrated"
    CONFUSED = "confused"
    EXCITED = "excited"


class Formality(Enum):
    """Message formality level."""
    FORMAL = "formal"
    NEUTRAL = "neutral"
    CASUAL = "casual"


@dataclass
class ToneAnalysis:
    """Result of tone analysis."""
    primary_tone: EmotionalTone
    formality: Formality
    confidence: float
    
    # Signals
    has_exclamation: bool
    has_question: bool
    has_capslock: bool
    has_emoji: bool
    
    # Suggestions
    suggested_temperature: float
    suggested_style: str


# Keyword patterns
POSITIVE_WORDS = {
    "спасибо", "благодарю", "отлично", "супер", "круто", "класс", "здорово",
    "молодец", "прекрасно", "замечательно", "хорошо", "рад", "люблю", "нравится",
    "thanks", "great", "awesome", "perfect", "amazing", "love", "nice"
}

NEGATIVE_WORDS = {
    "плохо", "ужасно", "отстой", "ненавижу", "бесит", "раздражает", "злой",
    "грустно", "печально", "разочарован", "обидно", "больно", "страшно",
    "bad", "terrible", "hate", "angry", "sad", "frustrated", "annoying"
}

URGENT_WORDS = {
    "срочно", "немедленно", "быстро", "скоро", "дедлайн", "горит", "критично",
    "сейчас", "asap", "urgent", "quickly", "hurry", "now", "deadline"
}

CONFUSED_WORDS = {
    "непонятно", "странно", "не понимаю", "почему", "как так", "что это",
    "confused", "why", "don't understand", "what", "how"
}

FORMAL_MARKERS = {
    "уважаемый", "пожалуйста", "извините", "будьте добры", "не могли бы",
    "dear", "please", "kindly", "would you", "sir", "madam"
}

CASUAL_MARKERS = {
    "хей", "йоу", "чё", "ну", "типа", "короч", "норм", "ок", "окей",
    "hey", "yo", "bruh", "nah", "gonna", "wanna", "kinda"
}


class ToneDetector:
    """
    CPU-based emotional tone detection.
    
    ~5ms, no LLM required.
    """
    
    def __init__(self):
        log.debug("ToneDetector initialized")
    
    def analyze(self, text: str) -> ToneAnalysis:
        """Analyze emotional tone of text."""
        text_lower = text.lower()
        
        # Check signals
        has_exclamation = "!" in text
        has_question = "?" in text
        has_capslock = len(re.findall(r'[A-ZА-Я]{3,}', text)) > 0
        has_emoji = bool(re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]', text))
        
        # Score tones
        scores = {
            EmotionalTone.POSITIVE: self._count_matches(text_lower, POSITIVE_WORDS),
            EmotionalTone.NEGATIVE: self._count_matches(text_lower, NEGATIVE_WORDS),
            EmotionalTone.URGENT: self._count_matches(text_lower, URGENT_WORDS),
            EmotionalTone.CONFUSED: self._count_matches(text_lower, CONFUSED_WORDS),
        }
        
        # Bonus signals
        if has_capslock:
            scores[EmotionalTone.URGENT] += 2
            scores[EmotionalTone.NEGATIVE] += 1
        
        if has_exclamation and "!" * 2 in text:
            scores[EmotionalTone.EXCITED] = scores.get(EmotionalTone.EXCITED, 0) + 2
        
        # Determine primary tone
        max_score = max(scores.values()) if scores.values() else 0
        
        if max_score == 0:
            primary_tone = EmotionalTone.NEUTRAL
            confidence = 0.5
        else:
            primary_tone = max(scores.items(), key=lambda x: x[1])[0]
            confidence = min(0.9, 0.5 + max_score * 0.1)
        
        # Formality
        formality = self._detect_formality(text_lower)
        
        # Suggestions
        temp, style = self._get_suggestions(primary_tone, formality)
        
        return ToneAnalysis(
            primary_tone=primary_tone,
            formality=formality,
            confidence=confidence,
            has_exclamation=has_exclamation,
            has_question=has_question,
            has_capslock=has_capslock,
            has_emoji=has_emoji,
            suggested_temperature=temp,
            suggested_style=style
        )
    
    def _count_matches(self, text: str, words: set) -> int:
        """Count keyword matches."""
        return sum(1 for w in words if w in text)
    
    def _detect_formality(self, text: str) -> Formality:
        """Detect formality level."""
        formal_count = sum(1 for w in FORMAL_MARKERS if w in text)
        casual_count = sum(1 for w in CASUAL_MARKERS if w in text)
        
        if formal_count > casual_count:
            return Formality.FORMAL
        elif casual_count > formal_count:
            return Formality.CASUAL
        return Formality.NEUTRAL
    
    def _get_suggestions(
        self,
        tone: EmotionalTone,
        formality: Formality
    ) -> tuple:
        """Get temperature and style suggestions."""
        temp_map = {
            EmotionalTone.NEUTRAL: 0.7,
            EmotionalTone.POSITIVE: 0.8,
            EmotionalTone.NEGATIVE: 0.5,
            EmotionalTone.URGENT: 0.3,
            EmotionalTone.FRUSTRATED: 0.4,
            EmotionalTone.CONFUSED: 0.5,
            EmotionalTone.EXCITED: 0.9,
        }
        
        style_map = {
            EmotionalTone.NEUTRAL: "balanced",
            EmotionalTone.POSITIVE: "friendly",
            EmotionalTone.NEGATIVE: "empathetic",
            EmotionalTone.URGENT: "concise",
            EmotionalTone.FRUSTRATED: "patient",
            EmotionalTone.CONFUSED: "explanatory",
            EmotionalTone.EXCITED: "enthusiastic",
        }
        
        return temp_map.get(tone, 0.7), style_map.get(tone, "balanced")


# Global instance
_detector: Optional[ToneDetector] = None


def get_tone_detector() -> ToneDetector:
    """Get or create global ToneDetector."""
    global _detector
    if _detector is None:
        _detector = ToneDetector()
    return _detector


def detect_tone(text: str) -> ToneAnalysis:
    """Quick helper for tone detection."""
    return get_tone_detector().analyze(text)
