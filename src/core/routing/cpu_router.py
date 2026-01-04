"""
CPU-Resident Router for MAX AI.

Provides lightweight CPU-based classification for:
- Intent classification (without GPU load)
- PII detection
- RAG chunk reranking
- Quick task routing

Uses rule-based heuristics and optionally a small CPU model.
"""
import re
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

from ..logger import log


class IntentType(Enum):
    """High-level intent categories."""
    GREETING = "greeting"
    QUESTION = "question"
    CODING = "coding"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    COMMAND = "command"
    SEARCH = "search"
    VISION = "vision"
    UNKNOWN = "unknown"


class TaskComplexity(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"      # Single-turn, fast response
    MEDIUM = "medium"      # May need context, standard response
    COMPLEX = "complex"    # Multi-step reasoning, cognitive loop


@dataclass
class RoutingDecision:
    """Result of CPU router analysis."""
    intent: IntentType
    complexity: TaskComplexity
    confidence: float  # 0.0 - 1.0
    suggested_mode: str  # 'fast', 'standard', 'deep'
    flags: Dict[str, bool]  # has_code, has_question, etc.


class CPURouter:
    """
    Lightweight CPU-resident router for fast initial classification.
    
    Uses zero GPU resources - purely heuristic/pattern-based.
    Can be extended to use a small CPU model (Phi-3.5-mini) in future.
    """
    
    # Patterns for intent detection
    GREETING_PATTERNS = [
        r'^(привет|здравствуй|добрый\s+\w+|hi|hello|hey)\b',
        r'^(как\s+дела|what\'s\s+up|как\s+ты)\??$'
    ]
    
    QUESTION_PATTERNS = [
        r'\?$',
        r'^(что|как|почему|зачем|когда|где|кто|какой|сколько)',
        r'^(what|how|why|when|where|who|which)\b'
    ]
    
    CODING_PATTERNS = [
        r'(код|code|программ|function|def\s|class\s|import\s)',
        r'(python|javascript|typescript|java|c\+\+|rust|go)\b',
        r'(исправь|debug|ошибка|error|bug|fix)',
        r'(напиши|write|создай|create|implement)'
    ]
    
    CREATIVE_PATTERNS = [
        r'(напиши\s+(стих|расска|историю|сказку|песню))',
        r'(придумай|сочини|write\s+a\s+(story|poem|song))',
        r'(generate|create|design)\s+(a\s+)?(logo|image|art)'
    ]
    
    SEARCH_PATTERNS = [
        r'(найди|поищи|search|find|look\s+up)\b',
        r'(в\s+интернете|online|web|google)',
        r'(последние\s+новости|current|latest|recent)'
    ]
    
    COMPLEX_INDICATORS = [
        r'объясни.*подробно',
        r'проанализируй',
        r'сравни.*и.*',
        r'пошагово',
        r'step\s+by\s+step',
        r'in\s+detail',
        r'compare.*and.*',
        r'analyze'
    ]
    
    def __init__(self):
        # Compile patterns for efficiency
        self._greeting_re = [re.compile(p, re.IGNORECASE) for p in self.GREETING_PATTERNS]
        self._question_re = [re.compile(p, re.IGNORECASE) for p in self.QUESTION_PATTERNS]
        self._coding_re = [re.compile(p, re.IGNORECASE) for p in self.CODING_PATTERNS]
        self._creative_re = [re.compile(p, re.IGNORECASE) for p in self.CREATIVE_PATTERNS]
        self._search_re = [re.compile(p, re.IGNORECASE) for p in self.SEARCH_PATTERNS]
        self._complex_re = [re.compile(p, re.IGNORECASE) for p in self.COMPLEX_INDICATORS]
        
        log.debug("CPURouter initialized (heuristic mode)")
    
    def _match_any(self, text: str, patterns: List[re.Pattern]) -> bool:
        """Check if text matches any of the patterns."""
        return any(p.search(text) for p in patterns)
    
    def _count_matches(self, text: str, patterns: List[re.Pattern]) -> int:
        """Count how many patterns match."""
        return sum(1 for p in patterns if p.search(text))
    
    def detect_intent(self, text: str) -> Tuple[IntentType, float]:
        """
        Detect the primary intent of the input.
        
        Returns (IntentType, confidence score).
        """
        text = text.strip()
        
        # Check for greeting (high priority, simple pattern)
        if len(text) < 50 and self._match_any(text, self._greeting_re):
            return IntentType.GREETING, 0.9
        
        # Check for search intent
        if self._match_any(text, self._search_re):
            return IntentType.SEARCH, 0.85
        
        # Check for coding
        coding_matches = self._count_matches(text, self._coding_re)
        if coding_matches >= 2:
            return IntentType.CODING, 0.9
        elif coding_matches == 1:
            return IntentType.CODING, 0.7
        
        # Check for creative
        if self._match_any(text, self._creative_re):
            return IntentType.CREATIVE, 0.85
        
        # Check for question
        if self._match_any(text, self._question_re):
            return IntentType.QUESTION, 0.8
        
        # Default to unknown
        return IntentType.UNKNOWN, 0.5
    
    def detect_complexity(self, text: str) -> Tuple[TaskComplexity, float]:
        """
        Estimate task complexity.
        
        Returns (TaskComplexity, confidence score).
        """
        text_lower = text.lower()
        word_count = len(text.split())
        
        # Very short = simple
        if word_count < 5:
            return TaskComplexity.SIMPLE, 0.9
        
        # Check for complexity indicators
        complex_matches = self._count_matches(text, self._complex_re)
        
        if complex_matches >= 2:
            return TaskComplexity.COMPLEX, 0.85
        elif complex_matches == 1:
            return TaskComplexity.MEDIUM, 0.75
        
        # Long text = likely more complex
        if word_count > 50:
            return TaskComplexity.MEDIUM, 0.7
        
        # Default
        return TaskComplexity.SIMPLE, 0.6
    
    def detect_flags(self, text: str) -> Dict[str, bool]:
        """
        Detect various flags/features in the input.
        """
        return {
            "has_question": self._match_any(text, self._question_re),
            "has_code_request": self._match_any(text, self._coding_re),
            "has_search_request": self._match_any(text, self._search_re),
            "is_greeting": self._match_any(text, self._greeting_re),
            "needs_creativity": self._match_any(text, self._creative_re),
            "is_complex": self._count_matches(text, self._complex_re) > 0
        }
    
    def route(self, text: str) -> RoutingDecision:
        """
        Main routing method.
        
        Analyzes input and returns a routing decision.
        """
        intent, intent_conf = self.detect_intent(text)
        complexity, complexity_conf = self.detect_complexity(text)
        flags = self.detect_flags(text)
        
        # Determine suggested mode
        if complexity == TaskComplexity.SIMPLE:
            suggested_mode = "fast"
        elif complexity == TaskComplexity.COMPLEX:
            suggested_mode = "deep"
        else:
            suggested_mode = "standard"
        
        # Greeting always uses fast mode
        if intent == IntentType.GREETING:
            suggested_mode = "fast"
        
        # Search triggers standard mode
        if intent == IntentType.SEARCH:
            suggested_mode = "standard"
        
        # Combine confidence
        overall_confidence = (intent_conf + complexity_conf) / 2
        
        decision = RoutingDecision(
            intent=intent,
            complexity=complexity,
            confidence=overall_confidence,
            suggested_mode=suggested_mode,
            flags=flags
        )
        
        log.debug(
            f"CPURouter: intent={intent.value}, complexity={complexity.value}, "
            f"mode={suggested_mode}, conf={overall_confidence:.2f}"
        )
        
        return decision
    
    def detect_pii(self, text: str) -> Dict[str, List[str]]:
        """
        Detect potential PII in text (basic patterns).
        
        This is a lightweight check - not a complete PII solution.
        """
        pii_found = {
            "emails": [],
            "phones": [],
            "card_numbers": []
        }
        
        # Email pattern
        emails = re.findall(r'\b[\w.-]+@[\w.-]+\.\w+\b', text)
        pii_found["emails"] = emails
        
        # Phone pattern (basic)
        phones = re.findall(r'\b(?:\+7|8)?[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b', text)
        pii_found["phones"] = phones
        
        # Card number pattern (basic - 16 digits)
        cards = re.findall(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', text)
        pii_found["card_numbers"] = cards
        
        return pii_found
    
    def quick_rerank(
        self,
        query: str,
        chunks: List[str],
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Quick CPU-based reranking of RAG chunks.
        
        Uses simple keyword overlap scoring.
        Returns list of (chunk_index, score) sorted by score.
        """
        query_words = set(query.lower().split())
        
        scores = []
        for i, chunk in enumerate(chunks):
            chunk_words = set(chunk.lower().split())
            
            # Jaccard-like overlap
            overlap = len(query_words & chunk_words)
            union = len(query_words | chunk_words)
            
            score = overlap / union if union > 0 else 0.0
            scores.append((i, score))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_k]


# Global instance
cpu_router = CPURouter()
