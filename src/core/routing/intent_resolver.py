"""
Intent Resolver for SmartRouter.

Advanced intent resolution with multi-layer voting.
Combines signals from multiple sources.

Features:
    - Multi-source voting
    - Confidence weighting
    - Conflict resolution
    - Intent hierarchies
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

from ..logger import log


@dataclass
class IntentVote:
    """A vote for an intent from a source."""
    intent: str
    confidence: float
    source: str
    weight: float = 1.0
    
    @property
    def weighted_score(self) -> float:
        return self.confidence * self.weight


class IntentHierarchy:
    """Hierarchical intent relationships."""
    
    PARENT_MAP = {
        # Specific -> General
        "greeting": "social",
        "goodbye": "social",
        "feedback": "social",
        
        "coding": "task",
        "math": "task",
        "translation": "task",
        "search": "task",
        
        "question": "information",
        "explanation": "information",
        
        "creative": "generation",
        "writing": "generation",
    }
    
    @classmethod
    def get_parent(cls, intent: str) -> Optional[str]:
        """Get parent intent if exists."""
        return cls.PARENT_MAP.get(intent)
    
    @classmethod
    def are_related(cls, intent1: str, intent2: str) -> bool:
        """Check if two intents are related (same parent)."""
        parent1 = cls.get_parent(intent1)
        parent2 = cls.get_parent(intent2)
        
        if parent1 and parent1 == parent2:
            return True
        if intent1 == parent2 or intent2 == parent1:
            return True
        return False


class IntentResolver:
    """
    Resolves final intent from multiple signals.
    
    Uses weighted voting with conflict resolution.
    """
    
    # Source weights
    SOURCE_WEIGHTS = {
        "semantic": 1.0,
        "llm": 0.9,
        "cpu": 0.5,
        "user_history": 0.7,
        "context": 0.6,
    }
    
    def __init__(self):
        log.debug("IntentResolver initialized")
    
    def resolve(self, votes: List[IntentVote]) -> Tuple[str, float]:
        """
        Resolve final intent from votes.
        
        Returns (intent, confidence).
        """
        if not votes:
            return "unknown", 0.0
        
        # Apply source weights
        for vote in votes:
            vote.weight = self.SOURCE_WEIGHTS.get(vote.source, 1.0)
        
        # Group by intent
        intent_scores: Dict[str, float] = defaultdict(float)
        for vote in votes:
            intent_scores[vote.intent] += vote.weighted_score
        
        # Find winner
        winner = max(intent_scores.items(), key=lambda x: x[1])
        intent, total_score = winner
        
        # Normalize confidence
        max_possible = sum(v.weight for v in votes)
        confidence = min(total_score / max_possible, 1.0) if max_possible > 0 else 0.0
        
        # Check for conflicts
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_intents) >= 2:
            second_score = sorted_intents[1][1]
            if second_score / total_score > 0.8:  # Close race
                # Check if they're related
                if IntentHierarchy.are_related(intent, sorted_intents[1][0]):
                    confidence *= 0.9  # Slight reduction for related conflict
                else:
                    confidence *= 0.7  # Larger reduction for unrelated conflict
                    log.debug(f"IntentResolver: conflict between {intent} and {sorted_intents[1][0]}")
        
        return intent, confidence
    
    def add_context_vote(
        self,
        votes: List[IntentVote],
        recent_intents: List[str]
    ) -> List[IntentVote]:
        """
        Add context-based vote from recent conversation.
        
        Boosts intents that match recent context.
        """
        if not recent_intents:
            return votes
        
        # Find most common recent intent
        from collections import Counter
        counter = Counter(recent_intents)
        most_common = counter.most_common(1)[0][0]
        
        # Add context vote
        votes.append(IntentVote(
            intent=most_common,
            confidence=0.5,
            source="context",
            weight=self.SOURCE_WEIGHTS["context"]
        ))
        
        return votes
    
    def explain_decision(self, votes: List[IntentVote]) -> Dict:
        """Explain how the decision was made."""
        intent, confidence = self.resolve(votes)
        
        return {
            "final_intent": intent,
            "confidence": confidence,
            "votes": [
                {
                    "intent": v.intent,
                    "source": v.source,
                    "confidence": v.confidence,
                    "weight": v.weight,
                    "weighted_score": v.weighted_score
                }
                for v in votes
            ],
            "explanation": f"Resolved to '{intent}' with {confidence:.0%} confidence from {len(votes)} votes"
        }


# Global instance
_resolver: Optional[IntentResolver] = None


def get_intent_resolver() -> IntentResolver:
    """Get or create global resolver."""
    global _resolver
    if _resolver is None:
        _resolver = IntentResolver()
    return _resolver


def resolve_intent(votes: List[IntentVote]) -> Tuple[str, float]:
    """Quick helper for intent resolution."""
    return get_intent_resolver().resolve(votes)
