"""
Confidence Scorer for MAX AI Assistant.

Scores the confidence of generated responses based on:
- Linguistic hedging patterns ("возможно", "не уверен")
- Response structure (code blocks, lists, etc.)
- Task category match

Usage:
    from .confidence import confidence_scorer
    
    result = confidence_scorer.score_response(response, category="code")
    # ConfidenceResult(score=0.85, level="high", factors=["code_present", "structured"])
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class ConfidenceLevel(Enum):
    """Confidence level categories."""
    LOW = "low"           # 0.0 - 0.4
    MEDIUM = "medium"     # 0.4 - 0.7
    HIGH = "high"         # 0.7 - 1.0


@dataclass
class ConfidenceResult:
    """Result of confidence scoring."""
    score: float              # 0.0 - 1.0
    level: ConfidenceLevel
    factors: List[str] = field(default_factory=list)


# Hedging patterns that indicate uncertainty
HEDGING_PATTERNS_RU = [
    r"\bвозможно\b",
    r"\bможет быть\b",
    r"\bне уверен\b",
    r"\bне знаю\b",
    r"\bнаверное\b",
    r"\bвероятно\b",
    r"\bпохоже\b",
    r"\bможет\s+быть\b",
    r"\bскорее\s+всего\b",
    r"\bкак\s+мне\s+кажется\b",
    r"\bмне\s+кажется\b",
]

HEDGING_PATTERNS_EN = [
    r"\bmaybe\b",
    r"\bperhaps\b",
    r"\bnot sure\b",
    r"\bprobably\b",
    r"\bmight\b",
    r"\bcould be\b",
    r"\bseems like\b",
    r"\bi think\b",
    r"\bi believe\b",
    r"\bpossibly\b",
]

# Positive confidence signals
CONFIDENCE_SIGNALS = [
    r"```",           # Code blocks
    r"^\d+\.\s",      # Numbered lists
    r"^-\s",          # Bullet points
    r"^\*\s",         # Asterisk bullets
    r"\bпотому что\b",  # Explanations (RU)
    r"\bbecause\b",     # Explanations (EN)
]


class ConfidenceScorer:
    """
    Scores response confidence.
    
    Uses heuristics to estimate how confident the response appears.
    Higher confidence responses tend to:
    - Use fewer hedging words
    - Have structured formats (code, lists)
    - Be concise and direct
    """
    
    def __init__(self):
        self._hedging_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE) 
            for p in HEDGING_PATTERNS_RU + HEDGING_PATTERNS_EN
        ]
        self._confidence_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in CONFIDENCE_SIGNALS
        ]
    
    def score_response(
        self,
        response: str,
        category: Optional[str] = None
    ) -> ConfidenceResult:
        """
        Score confidence of a response.
        
        Args:
            response: The response text
            category: Optional task category (code, reasoning, creative)
            
        Returns:
            ConfidenceResult with score, level, and contributing factors
        """
        if not response or not response.strip():
            return ConfidenceResult(
                score=0.0,
                level=ConfidenceLevel.LOW,
                factors=["empty_response"]
            )
        
        factors = []
        score = 0.5  # Start neutral
        
        # 1. Check for hedging patterns (-0.1 each, max -0.3)
        hedging_count = 0
        for pattern in self._hedging_patterns:
            if pattern.search(response):
                hedging_count += 1
        
        hedging_penalty = min(hedging_count * 0.1, 0.3)
        if hedging_count > 0:
            factors.append(f"hedging_x{hedging_count}")
            score -= hedging_penalty
        
        # 2. Check for confidence signals (+0.1 each, max +0.3)
        confidence_count = 0
        for pattern in self._confidence_patterns:
            if pattern.search(response):
                confidence_count += 1
        
        confidence_bonus = min(confidence_count * 0.1, 0.3)
        if confidence_count > 0:
            factors.append(f"structured_x{confidence_count}")
            score += confidence_bonus
        
        # 3. Code present in code category = high confidence
        if category == "code" and "```" in response:
            factors.append("code_present")
            score += 0.2
        
        # 4. Length factor (very short = lower, structured long = higher)
        length = len(response)
        if length < 50:
            factors.append("very_short")
            score -= 0.1
        elif length > 500 and confidence_count > 2:
            factors.append("detailed_structured")
            score += 0.1
        
        # 5. Error mentions reduce confidence
        error_patterns = [r"ошибк[аи]", r"error", r"exception", r"fail"]
        for ep in error_patterns:
            if re.search(ep, response, re.IGNORECASE):
                factors.append("mentions_error")
                score -= 0.1
                break
        
        # Clamp score
        score = max(0.0, min(1.0, score))
        
        # Determine level
        if score < 0.4:
            level = ConfidenceLevel.LOW
        elif score < 0.7:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.HIGH
        
        return ConfidenceResult(
            score=round(score, 2),
            level=level,
            factors=factors
        )


# Global instance
confidence_scorer = ConfidenceScorer()
