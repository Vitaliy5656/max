"""
Message Classifier for MAX AI.

Pre-routing classification of message types.
Helps decide processing strategy before routing.

Features:
    - Message type detection (question, command, statement)
    - Language detection
    - Code presence detection
    - URL/link detection
"""
import re
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum

from ..logger import log


class MessageType(Enum):
    """Types of user messages."""
    QUESTION = "question"
    COMMAND = "command"
    STATEMENT = "statement"
    REQUEST = "request"
    GREETING = "greeting"
    FEEDBACK = "feedback"
    CODE = "code"
    URL = "url"


class Language(Enum):
    """Detected language."""
    RUSSIAN = "ru"
    ENGLISH = "en"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass
class MessageClassification:
    """Result of message classification."""
    message_type: MessageType
    language: Language
    
    # Content flags
    has_code: bool
    has_url: bool
    has_mention: bool
    has_emoji: bool
    
    # Metrics
    word_count: int
    char_count: int
    
    # Processing hints
    requires_response: bool
    is_continuation: bool


# Patterns
QUESTION_PATTERNS = [
    r'\?$',
    r'^(как|что|где|когда|почему|зачем|кто|какой|какая|сколько|можно|можешь)',
    r'^(how|what|where|when|why|who|which|can you|could you)',
]

COMMAND_PATTERNS = [
    r'^(сделай|создай|напиши|найди|покажи|открой|запусти|удали|измени)',
    r'^(make|create|write|find|show|open|run|delete|change|edit|fix|add)',
]

GREETING_PATTERNS = [
    r'^(привет|здравствуй|добр|хей|хай|здоров)',
    r'^(hi|hello|hey|good morning|good evening)',
]

FEEDBACK_PATTERNS = [
    r'^(спасибо|благодарю|отлично|хорошо|понял|ок|окей)',
    r'^(thanks|thank you|great|good|ok|okay|got it)',
]


class MessageClassifier:
    """
    Fast message classification.
    
    ~1ms, CPU-only.
    """
    
    def __init__(self):
        self._question_re = [re.compile(p, re.I) for p in QUESTION_PATTERNS]
        self._command_re = [re.compile(p, re.I) for p in COMMAND_PATTERNS]
        self._greeting_re = [re.compile(p, re.I) for p in GREETING_PATTERNS]
        self._feedback_re = [re.compile(p, re.I) for p in FEEDBACK_PATTERNS]
        
        log.debug("MessageClassifier initialized")
    
    def classify(self, message: str) -> MessageClassification:
        """Classify a message."""
        text = message.strip()
        text_lower = text.lower()
        
        # Detect content flags
        has_code = bool(re.search(r'```|`[^`]+`', text))
        has_url = bool(re.search(r'https?://\S+', text))
        has_mention = bool(re.search(r'@\w+', text))
        has_emoji = bool(re.search(r'[\U0001F600-\U0001F64F]', text))
        
        # Detect language
        language = self._detect_language(text)
        
        # Metrics
        word_count = len(text.split())
        char_count = len(text)
        
        # Detect message type
        message_type = self._detect_type(text, text_lower)
        
        # Processing hints
        requires_response = message_type not in {MessageType.FEEDBACK}
        is_continuation = text_lower in {"и", "а также", "еще", "ещё", "and", "also"}
        
        return MessageClassification(
            message_type=message_type,
            language=language,
            has_code=has_code,
            has_url=has_url,
            has_mention=has_mention,
            has_emoji=has_emoji,
            word_count=word_count,
            char_count=char_count,
            requires_response=requires_response,
            is_continuation=is_continuation
        )
    
    def _detect_language(self, text: str) -> Language:
        """Detect message language."""
        cyrillic = len(re.findall(r'[а-яё]', text.lower()))
        latin = len(re.findall(r'[a-z]', text.lower()))
        
        if cyrillic > 0 and latin > 0:
            ratio = cyrillic / (cyrillic + latin)
            if 0.3 < ratio < 0.7:
                return Language.MIXED
        
        if cyrillic > latin:
            return Language.RUSSIAN
        elif latin > cyrillic:
            return Language.ENGLISH
        return Language.UNKNOWN
    
    def _detect_type(self, text: str, text_lower: str) -> MessageType:
        """Detect message type."""
        # Check patterns in order
        if any(p.search(text_lower) for p in self._greeting_re):
            return MessageType.GREETING
        
        if any(p.search(text_lower) for p in self._feedback_re):
            return MessageType.FEEDBACK
        
        if any(p.search(text) for p in self._question_re):
            return MessageType.QUESTION
        
        if any(p.search(text_lower) for p in self._command_re):
            return MessageType.COMMAND
        
        if re.search(r'```', text):
            return MessageType.CODE
        
        if re.search(r'https?://', text):
            return MessageType.URL
        
        # Default based on length
        if len(text.split()) < 5:
            return MessageType.REQUEST
        
        return MessageType.STATEMENT


# Global instance
_classifier: Optional[MessageClassifier] = None


def get_message_classifier() -> MessageClassifier:
    """Get or create global classifier."""
    global _classifier
    if _classifier is None:
        _classifier = MessageClassifier()
    return _classifier


def classify_message(message: str) -> MessageClassification:
    """Quick helper for classification."""
    return get_message_classifier().classify(message)
