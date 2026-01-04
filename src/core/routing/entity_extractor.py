"""
Entity Extraction for MAX AI.

Extracts named entities and topics from messages for:
    - Smart context building
    - Topic detection for Prompt Library
    - Memory indexing
    - Auto-learning topic tagging

Uses lightweight regex + keyword matching for speed.
LLM extraction available for complex cases.
"""
import re
from typing import Optional, Dict, List, Set
from dataclasses import dataclass, field
from enum import Enum

from ..logger import log


class EntityType(Enum):
    """Types of extractable entities."""
    PERSON = "person"
    LOCATION = "location"
    ORGANIZATION = "org"
    DATE = "date"
    TIME = "time"
    NUMBER = "number"
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"
    CODE = "code"
    TOPIC = "topic"


@dataclass
class Entity:
    """Extracted entity."""
    type: EntityType
    value: str
    start: int = 0
    end: int = 0
    confidence: float = 1.0


@dataclass
class ExtractionResult:
    """Result of entity extraction."""
    entities: List[Entity] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    language: str = "ru"
    has_code: bool = False
    has_question: bool = False
    word_count: int = 0
    
    def get_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get entities of specific type."""
        return [e for e in self.entities if e.type == entity_type]
    
    def get_primary_topic(self) -> Optional[str]:
        """Get most likely topic."""
        return self.topics[0] if self.topics else None


# Topic patterns (keyword -> topic mapping)
TOPIC_PATTERNS: Dict[str, List[str]] = {
    "astronomy": [
        "звезд", "планет", "галактик", "космос", "телескоп", "орбит",
        "солнц", "лун", "черная дыра", "nasa", "spacex", "ракет",
        "астроном", "спутник", "комет", "астероид", "вселен", "марс"
    ],
    "jewelry": [
        "бриллиант", "карат", "золот", "серебр", "огранк", "ювелир",
        "кольц", "ожерель", "рубин", "изумруд", "сапфир", "алмаз",
        "драгоцен", "украшен", "проба", "платин"
    ],
    "construction": [
        "фундамент", "стен", "кровл", "бетон", "кирпич", "ремонт",
        "стройк", "материал", "смет", "цемент", "арматур", "крыш",
        "штукатур", "гипсокартон", "теплоизоляц", "водоснабжен"
    ],
    "programming": [
        "python", "javascript", "java", "код", "функци", "класс",
        "алгоритм", "api", "базы данных", "git", "docker", "linux",
        "react", "vue", "node", "sql", "программ", "разработ"
    ],
    "medicine": [
        "болезн", "симптом", "лечен", "врач", "диагноз", "таблетк",
        "лекарств", "здоровь", "медицин", "терапи", "хирург", "анализ"
    ],
    "psychology": [
        "тревог", "стресс", "депресс", "настроен", "эмоци", "чувств",
        "психолог", "терапевт", "отношен", "обида", "злость", "страх"
    ],
    "finance": [
        "деньг", "инвестиц", "акци", "криптовалют", "биткоин", "банк",
        "кредит", "ипотек", "вклад", "сбережен", "бюджет", "налог"
    ],
    "cooking": [
        "рецепт", "готов", "блюд", "ингредиент", "варить", "жарить",
        "печь", "кухн", "вкус", "приправ", "торт", "суп", "салат"
    ],
    "travel": [
        "путешеств", "отпуск", "туризм", "отель", "билет", "виза",
        "самолет", "поезд", "экскурс", "достопримечательн", "страна"
    ],
    "education": [
        "учеб", "урок", "экзамен", "школ", "университет", "курс",
        "студент", "препоавател", "лекц", "семинар", "диплом"
    ],
}

# Regex patterns for entities
PATTERNS = {
    EntityType.URL: re.compile(
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        re.IGNORECASE
    ),
    EntityType.EMAIL: re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE
    ),
    EntityType.PHONE: re.compile(
        r'(?:\+7|8)[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}'
    ),
    EntityType.DATE: re.compile(
        r'\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|'
        r'(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|'
        r'сентябр|октябр|ноябр|декабр)[а-я]*\s+\d{1,4}',
        re.IGNORECASE
    ),
    EntityType.TIME: re.compile(
        r'\d{1,2}:\d{2}(?::\d{2})?'
    ),
    EntityType.NUMBER: re.compile(
        r'\b\d+(?:[.,]\d+)?(?:\s*(?:руб|₽|\$|€|%|кг|м|см|мм|л|мл|шт))?\b'
    ),
    EntityType.CODE: re.compile(
        r'```[\s\S]*?```|`[^`]+`'
    ),
}

# Question indicators
QUESTION_WORDS = {
    "как", "что", "почему", "зачем", "где", "когда", "кто", "какой", "какая",
    "какие", "сколько", "чем", "можно ли", "правда ли", "есть ли"
}


class EntityExtractor:
    """
    Fast entity and topic extraction.
    
    Uses regex and keyword matching for speed.
    """
    
    def __init__(self):
        log.debug("EntityExtractor initialized")
    
    def extract(self, text: str) -> ExtractionResult:
        """
        Extract entities and topics from text.
        
        Fast: ~1ms for typical messages.
        """
        result = ExtractionResult()
        text_lower = text.lower()
        
        # Basic stats
        result.word_count = len(text.split())
        result.language = self._detect_language(text)
        result.has_question = self._is_question(text_lower)
        
        # Extract regex entities
        for entity_type, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                result.entities.append(Entity(
                    type=entity_type,
                    value=match.group(),
                    start=match.start(),
                    end=match.end()
                ))
                
                if entity_type == EntityType.CODE:
                    result.has_code = True
        
        # Detect topics
        result.topics = self._detect_topics(text_lower)
        
        return result
    
    def _detect_language(self, text: str) -> str:
        """Detect language (ru/en)."""
        cyrillic = len(re.findall(r'[а-яё]', text.lower()))
        latin = len(re.findall(r'[a-z]', text.lower()))
        
        if cyrillic > latin:
            return "ru"
        elif latin > cyrillic:
            return "en"
        return "ru"  # Default
    
    def _is_question(self, text_lower: str) -> bool:
        """Check if text is a question."""
        if "?" in text_lower:
            return True
        
        words = text_lower.split()
        if words and words[0] in QUESTION_WORDS:
            return True
        
        return any(qw in text_lower for qw in QUESTION_WORDS)
    
    def _detect_topics(self, text_lower: str) -> List[str]:
        """Detect topics based on keyword matching."""
        scores: Dict[str, int] = {}
        
        for topic, keywords in TOPIC_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[topic] = score
        
        # Sort by score
        sorted_topics = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Return topics with at least 1 keyword match (relaxed for single-topic messages)
        return [t for t, s in sorted_topics if s >= 1]
    
    def get_topic_for_message(self, text: str) -> Optional[str]:
        """
        Quick topic detection for routing.
        
        Returns primary topic or None.
        """
        result = self.extract(text)
        return result.get_primary_topic()
    
    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """
        Extract key terms from text.
        
        Simple approach: longest words that aren't stopwords.
        """
        stopwords = {
            "это", "как", "что", "быть", "для", "так", "но", "или", "если",
            "при", "когда", "где", "уже", "все", "они", "его", "было", "мне",
            "you", "the", "and", "for", "are", "but", "not", "can", "had"
        }
        
        words = re.findall(r'\b[а-яёa-z]{4,}\b', text.lower())
        unique = list(dict.fromkeys(w for w in words if w not in stopwords))
        
        # Sort by length (longer = more specific)
        unique.sort(key=len, reverse=True)
        
        return unique[:max_keywords]


# Global instance
_extractor: Optional[EntityExtractor] = None


def get_entity_extractor() -> EntityExtractor:
    """Get or create global EntityExtractor."""
    global _extractor
    if _extractor is None:
        _extractor = EntityExtractor()
    return _extractor


def extract_entities(text: str) -> ExtractionResult:
    """Quick helper for entity extraction."""
    return get_entity_extractor().extract(text)


def detect_topic(text: str) -> Optional[str]:
    """Quick helper for topic detection."""
    return get_entity_extractor().get_topic_for_message(text)
