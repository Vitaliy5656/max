"""
Semantic Router for MAX AI Assistant.

Replaces keyword-based task detection with semantic similarity routing.
Uses pre-computed embeddings for intent categories to determine
the best model and thinking mode for each query.

Usage:
    from .semantic_router import semantic_router
    
    route = await semantic_router.route("Напиши функцию сортировки", user_profile)
    # RouteDecision(category=CODE, model="deepseek-coder", thinking_mode="deep")
"""
import asyncio
from enum import Enum
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .user_profile import UserProfile


class IntentCategory(Enum):
    """Categories of user intents."""
    CODE = "code"           # Programming, debugging, code review
    REASONING = "reasoning" # Analysis, explanations, complex problem solving
    CREATIVE = "creative"   # Writing, stories, creative content
    VISION = "vision"       # Image analysis (auto-detected)
    QUICK = "quick"         # Simple questions, yes/no, factual
    MATH = "math"           # Calculations, equations, data analysis
    CASUAL = "casual"       # Chit-chat, greetings


@dataclass
class RouteDecision:
    """Result of semantic routing."""
    category: IntentCategory
    model: str
    thinking_mode: str  # fast/standard/deep
    confidence: float   # 0.0 - 1.0


# Intent probes for semantic matching
# Each category has multiple example phrases for better matching
INTENT_PROBES = {
    IntentCategory.CODE: [
        "напиши код функции",
        "исправь ошибку в программе",
        "отладка кода python",
        "создай класс",
        "рефакторинг кода",
        "write code function",
        "fix bug in program",
        "debug python code",
    ],
    IntentCategory.REASONING: [
        "объясни почему это работает",
        "проанализируй ситуацию",
        "в чём причина проблемы",
        "сравни подходы",
        "explain why this works",
        "analyze the situation",
        "what is the reason",
    ],
    IntentCategory.CREATIVE: [
        "напиши историю",
        "придумай текст",
        "сочини стихотворение",
        "write a story",
        "compose a poem",
        "create content",
    ],
    IntentCategory.QUICK: [
        "да или нет",
        "кратко ответь",
        "сколько будет",
        "yes or no",
        "briefly answer",
        "what is",
    ],
    IntentCategory.MATH: [
        "посчитай",
        "вычисли",
        "реши уравнение",
        "calculate",
        "compute",
        "solve equation",
    ],
    IntentCategory.CASUAL: [
        "привет как дела",
        "что ты умеешь",
        "расскажи о себе",
        "hello how are you",
        "what can you do",
    ],
}

# Model selection by category
CATEGORY_MODELS = {
    IntentCategory.CODE: "deepseek-coder",
    IntentCategory.REASONING: "qwen2.5-14b-instruct",
    IntentCategory.CREATIVE: "qwen2.5-14b-instruct",
    IntentCategory.VISION: "llava",  # Vision model
    IntentCategory.QUICK: "qwen2.5-7b-instruct",
    IntentCategory.MATH: "qwen2.5-14b-instruct",
    IntentCategory.CASUAL: "qwen2.5-7b-instruct",
}

# Thinking mode by category
CATEGORY_THINKING = {
    IntentCategory.CODE: "deep",
    IntentCategory.REASONING: "deep",
    IntentCategory.CREATIVE: "standard",
    IntentCategory.VISION: "standard",
    IntentCategory.QUICK: "fast",
    IntentCategory.MATH: "deep",
    IntentCategory.CASUAL: "fast",
}

# Keyword fallback patterns (used when embedding unavailable)
KEYWORD_PATTERNS = {
    IntentCategory.CODE: [
        "код", "функци", "класс", "баг", "ошибк", "python", "js", "api",
        "code", "function", "class", "bug", "error", "debug"
    ],
    IntentCategory.REASONING: [
        "почему", "объясн", "причин", "анализ", "сравн",
        "why", "explain", "reason", "analyze", "compare"
    ],
    IntentCategory.CREATIVE: [
        "напиши", "придумай", "сочин", "история", "текст",
        "write", "compose", "story", "poem", "creative"
    ],
    IntentCategory.QUICK: [
        "да или нет", "кратко", "быстро", "что такое",
        "yes or no", "briefly", "quickly", "what is"
    ],
    IntentCategory.MATH: [
        "посчитай", "вычисл", "сколько", "уравнен",
        "calculate", "compute", "how much", "equation"
    ],
}


class SemanticRouter:
    """
    Semantic-based query router.
    
    Uses embedding similarity to determine intent category,
    then maps to optimal model and thinking mode.
    
    Features:
    - Pre-computed category embeddings (fast lookup)
    - User profile integration (respects verbosity)
    - Keyword fallback when embeddings unavailable
    """
    
    def __init__(self):
        self._embedding_service = None
        self._lm_client = None
        self._category_embeddings: dict[IntentCategory, list[list[float]]] = {}
        self._initialized = False
    
    async def initialize(self, lm_client, embedding_service=None):
        """
        Initialize with LM client and compute category embeddings.
        
        Args:
            lm_client: LM client for embedding computation
            embedding_service: Optional shared embedding service
        """
        self._lm_client = lm_client
        
        if embedding_service:
            self._embedding_service = embedding_service
        else:
            from .embedding_service import embedding_service as es
            self._embedding_service = es
            await self._embedding_service.initialize(lm_client)
        
        # Pre-compute embeddings for all intent probes
        await self._compute_category_embeddings()
        self._initialized = True
    
    async def _compute_category_embeddings(self):
        """Pre-compute embeddings for intent probes."""
        for category, probes in INTENT_PROBES.items():
            embeddings = []
            for probe in probes:
                emb = await self._embedding_service.get_or_compute(probe)
                if emb:
                    embeddings.append(emb)
            self._category_embeddings[category] = embeddings
    
    async def route(
        self,
        query: str,
        user_profile: Optional["UserProfile"] = None,
        has_image: bool = False
    ) -> RouteDecision:
        """
        Route query to optimal model and thinking mode.
        
        Args:
            query: User's message
            user_profile: User preferences (optional)
            has_image: Whether query includes an image
            
        Returns:
            RouteDecision with category, model, thinking_mode, confidence
        """
        # Vision always takes priority
        if has_image:
            return RouteDecision(
                category=IntentCategory.VISION,
                model=CATEGORY_MODELS[IntentCategory.VISION],
                thinking_mode=CATEGORY_THINKING[IntentCategory.VISION],
                confidence=1.0
            )
        
        # Try semantic routing first
        if self._initialized and self._category_embeddings:
            decision = await self._semantic_route(query)
            if decision.confidence > 0.5:
                # Apply user preferences
                decision = self._apply_user_preferences(decision, user_profile)
                return decision
        
        # Fallback to keyword-based routing
        decision = self._fallback_route(query)
        decision = self._apply_user_preferences(decision, user_profile)
        return decision
    
    async def route_with_embedding(
        self,
        query: str,
        user_profile: Optional["UserProfile"] = None,
        has_image: bool = False
    ) -> tuple[RouteDecision, Optional[list[float]]]:
        """
        Route query and return the computed embedding for reuse.
        
        This is an optimization - the embedding can be reused by
        ContextPrimer instead of computing it again.
        """
        if has_image:
            return (
                RouteDecision(
                    category=IntentCategory.VISION,
                    model=CATEGORY_MODELS[IntentCategory.VISION],
                    thinking_mode=CATEGORY_THINKING[IntentCategory.VISION],
                    confidence=1.0
                ),
                None
            )
        
        # Get query embedding
        query_embedding = await self._embedding_service.get_or_compute(query)
        
        if query_embedding and self._initialized:
            decision = await self._semantic_route_with_embedding(query, query_embedding)
            if decision.confidence > 0.5:
                decision = self._apply_user_preferences(decision, user_profile)
                return (decision, query_embedding)
        
        # Fallback
        decision = self._fallback_route(query)
        decision = self._apply_user_preferences(decision, user_profile)
        return (decision, query_embedding)
    
    async def _semantic_route(self, query: str) -> RouteDecision:
        """Route using semantic similarity."""
        query_embedding = await self._embedding_service.get_or_compute(query)
        if not query_embedding:
            return self._fallback_route(query)
        
        return await self._semantic_route_with_embedding(query, query_embedding)
    
    async def _semantic_route_with_embedding(
        self,
        query: str,
        query_embedding: list[float]
    ) -> RouteDecision:
        """Route using pre-computed query embedding."""
        best_category = IntentCategory.REASONING
        best_score = 0.0
        
        for category, embeddings in self._category_embeddings.items():
            if not embeddings:
                continue
            
            # Compute max similarity to any probe in category
            for emb in embeddings:
                score = self._cosine_similarity(query_embedding, emb)
                if score > best_score:
                    best_score = score
                    best_category = category
        
        return RouteDecision(
            category=best_category,
            model=CATEGORY_MODELS.get(best_category, "auto"),
            thinking_mode=CATEGORY_THINKING.get(best_category, "standard"),
            confidence=best_score
        )
    
    def _fallback_route(self, query: str) -> RouteDecision:
        """Fallback to keyword-based routing."""
        query_lower = query.lower()
        
        # Check each category's keywords
        for category, keywords in KEYWORD_PATTERNS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return RouteDecision(
                        category=category,
                        model=CATEGORY_MODELS.get(category, "auto"),
                        thinking_mode=CATEGORY_THINKING.get(category, "standard"),
                        confidence=0.6  # Lower confidence for keyword match
                    )
        
        # Default to REASONING for longer queries, QUICK for short
        if len(query) > 200:
            return RouteDecision(
                category=IntentCategory.REASONING,
                model=CATEGORY_MODELS[IntentCategory.REASONING],
                thinking_mode="deep",
                confidence=0.4
            )
        
        return RouteDecision(
            category=IntentCategory.QUICK,
            model=CATEGORY_MODELS[IntentCategory.QUICK],
            thinking_mode="standard",
            confidence=0.3
        )
    
    def _apply_user_preferences(
        self,
        decision: RouteDecision,
        user_profile: Optional["UserProfile"]
    ) -> RouteDecision:
        """Apply user preferences to route decision."""
        if not user_profile:
            return decision
        
        # Check verbosity preference
        try:
            prefs = user_profile.preferences
            if hasattr(prefs, 'verbosity'):
                from .user_profile import Verbosity
                if prefs.verbosity == Verbosity.BRIEF:
                    # Brief users prefer faster responses
                    if decision.category not in [IntentCategory.CODE, IntentCategory.REASONING]:
                        return RouteDecision(
                            category=decision.category,
                            model=decision.model,
                            thinking_mode="fast",
                            confidence=decision.confidence
                        )
        except Exception:
            pass
        
        return decision
    
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)


# Global instance
semantic_router = SemanticRouter()
