"""
LLM-Based Router for MAX AI.

Uses a lightweight model (Phi-3.5-mini) for accurate intent classification
and routing decisions. Runs via LM Studio API.

This replaces the heuristic-based cpu_router with proper LLM understanding.
"""
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import json

from openai import AsyncOpenAI
from ..logger import log


# Router model configuration
ROUTER_MODEL = "bartowski/phi-3.5-mini-instruct"  # Q4_K_L quantization


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
    MATH = "math"
    TRANSLATION = "translation"
    UNKNOWN = "unknown"


class TaskComplexity(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"      # Single-turn, fast response
    MEDIUM = "medium"      # May need context, standard response
    COMPLEX = "complex"    # Multi-step reasoning, cognitive loop


@dataclass
class RoutingDecision:
    """Result of LLM router analysis."""
    intent: IntentType
    complexity: TaskComplexity
    confidence: float  # 0.0 - 1.0
    suggested_mode: str  # 'fast', 'standard', 'deep'
    needs_search: bool
    needs_code: bool
    reasoning: str  # Brief explanation


# System prompt for routing
ROUTER_SYSTEM_PROMPT = """You are an intent classifier for an AI assistant.
Analyze the user message and classify it.

Respond ONLY with JSON in this exact format:
{
    "intent": "<greeting|question|coding|creative|analysis|search|math|translation|unknown>",
    "complexity": "<simple|medium|complex>",
    "needs_search": <true|false>,
    "needs_code": <true|false>,
    "confidence": <0.0-1.0>,
    "reasoning": "<brief 1-sentence explanation>"
}

Classification rules:
- greeting: Hi, hello, thanks, bye
- question: Asking for information or explanation
- coding: Requests involving code, programming, debugging
- creative: Writing stories, poems, creative content
- analysis: Deep analysis, comparison, evaluation
- search: Requests needing current/real-time information
- math: Mathematical calculations or problems
- translation: Language translation requests
- unknown: Cannot classify

Complexity rules:
- simple: Short answer, greeting, basic question (1-2 sentences to answer)
- medium: Needs explanation, context, or moderate detail
- complex: Multi-step reasoning, deep analysis, detailed code

Set needs_search=true if the user asks about current events, prices, news, weather.
Set needs_code=true if the user asks for code generation or debugging."""


class LLMRouter:
    """
    LLM-based router using Phi-3.5-mini for accurate classification.
    
    Communicates with LM Studio via OpenAI-compatible API.
    """
    
    def __init__(
        self,
        model: str = ROUTER_MODEL,
        base_url: str = "http://localhost:1234/v1",
        timeout: float = 10.0
    ):
        self.model = model
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key="lm-studio",
            timeout=timeout
        )
        self._cache: Dict[str, RoutingDecision] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        log.debug(f"LLMRouter initialized with model: {model}")
    
    async def route(self, message: str) -> RoutingDecision:
        """
        Classify user message using LLM.
        
        Args:
            message: User input to classify
            
        Returns:
            RoutingDecision with intent, complexity, and recommendations
        """
        # Check cache first (exact match)
        cache_key = message.strip().lower()[:100]
        if cache_key in self._cache:
            self._cache_hits += 1
            log.debug(f"LLMRouter cache hit: {self._cache[cache_key].intent.value}")
            return self._cache[cache_key]
        
        self._cache_misses += 1
        
        try:
            # Use GBNF grammar for guaranteed JSON output
            from .grammar import get_grammar_manager, GrammarType
            grammar_params = get_grammar_manager().build_chat_params(GrammarType.ROUTING)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                    {"role": "user", "content": message}
                ],
                stream=False,
                **grammar_params
            )
            
            content = response.choices[0].message.content or ""
            decision = self._parse_response(content, message)
            
            # Cache the result
            self._cache[cache_key] = decision
            
            log.debug(
                f"LLMRouter: intent={decision.intent.value}, "
                f"complexity={decision.complexity.value}, "
                f"mode={decision.suggested_mode}"
            )
            
            return decision
            
        except Exception as e:
            log.warn(f"LLMRouter error: {e}, falling back to defaults")
            return self._fallback_decision(message)
    
    def _parse_response(self, content: str, original_message: str) -> RoutingDecision:
        """Parse LLM JSON response into RoutingDecision."""
        import re
        
        try:
            # Try multiple extraction strategies
            clean = content.strip()
            
            # Strategy 1: Extract JSON from markdown code block
            if "```" in clean:
                match = re.search(r'```(?:json)?\s*([\s\S]*?)```', clean)
                if match:
                    clean = match.group(1).strip()
            
            # Strategy 2: Find JSON object with regex
            if not clean.startswith("{"):
                match = re.search(r'\{[^{}]*"intent"[^{}]*\}', clean, re.DOTALL)
                if match:
                    clean = match.group(0)
            
            # Strategy 3: Extract first complete JSON object
            if not clean.startswith("{"):
                start = clean.find("{")
                if start != -1:
                    # Find matching closing brace
                    depth = 0
                    for i, c in enumerate(clean[start:], start):
                        if c == "{":
                            depth += 1
                        elif c == "}":
                            depth -= 1
                            if depth == 0:
                                clean = clean[start:i+1]
                                break
            
            data = json.loads(clean)
            
            # Parse intent
            intent_str = data.get("intent", "unknown").lower()
            try:
                intent = IntentType(intent_str)
            except ValueError:
                intent = IntentType.UNKNOWN
            
            # Parse complexity
            complexity_str = data.get("complexity", "medium").lower()
            try:
                complexity = TaskComplexity(complexity_str)
            except ValueError:
                complexity = TaskComplexity.MEDIUM
            
            # Determine mode
            if complexity == TaskComplexity.SIMPLE:
                mode = "fast"
            elif complexity == TaskComplexity.COMPLEX:
                mode = "deep"
            else:
                mode = "standard"
            
            # Override for greeting
            if intent == IntentType.GREETING:
                mode = "fast"
            
            return RoutingDecision(
                intent=intent,
                complexity=complexity,
                confidence=float(data.get("confidence", 0.8)),
                suggested_mode=mode,
                needs_search=bool(data.get("needs_search", False)),
                needs_code=bool(data.get("needs_code", False)),
                reasoning=data.get("reasoning", "")
            )
            
        except (json.JSONDecodeError, Exception) as e:
            log.warn(f"LLMRouter JSON parse failed: {e}")
            return self._fallback_decision(original_message)
    
    def _fallback_decision(self, message: str) -> RoutingDecision:
        """Fallback when LLM fails - use simple heuristics."""
        msg_lower = message.lower()
        
        # Simple pattern matching as fallback
        if any(g in msg_lower for g in ["привет", "здравствуй", "hi", "hello"]):
            return RoutingDecision(
                intent=IntentType.GREETING,
                complexity=TaskComplexity.SIMPLE,
                confidence=0.7,
                suggested_mode="fast",
                needs_search=False,
                needs_code=False,
                reasoning="Fallback: greeting pattern detected"
            )
        
        if any(s in msg_lower for s in ["найди", "поищи", "search", "новости"]):
            return RoutingDecision(
                intent=IntentType.SEARCH,
                complexity=TaskComplexity.MEDIUM,
                confidence=0.6,
                suggested_mode="standard",
                needs_search=True,
                needs_code=False,
                reasoning="Fallback: search pattern detected"
            )
        
        # Default
        return RoutingDecision(
            intent=IntentType.QUESTION,
            complexity=TaskComplexity.MEDIUM,
            confidence=0.5,
            suggested_mode="standard",
            needs_search=False,
            needs_code=False,
            reasoning="Fallback: default classification"
        )
    
    async def batch_route(self, messages: List[str]) -> List[RoutingDecision]:
        """Route multiple messages concurrently."""
        tasks = [self.route(msg) for msg in messages]
        return await asyncio.gather(*tasks)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0
        
        return {
            "model": self.model,
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": f"{hit_rate:.1%}"
        }
    
    def clear_cache(self):
        """Clear the routing cache."""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0


# Global instance
llm_router = LLMRouter()
