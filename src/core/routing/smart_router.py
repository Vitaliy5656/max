"""
SmartRouter - Central Routing Orchestrator for MAX AI.

Implements 6-Layer Pipeline Architecture:
    Layer 1: Guardrails (regex/blocklist) - <1ms
    Layer 2: Semantic Router (vector search) - ~10ms
    Layer 3: Cache (hash-based) - ~2ms
    Layer 4: LLM Router (Phi-3.5) - ~400ms
    Layer 5: CPU Fallback (heuristics) - 0ms
    Layer 6: Tracing (async fire-and-forget)

This is the main entry point for all routing decisions.
"""
import asyncio
import hashlib
import time
import re
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from cachetools import TTLCache

from .semantic_router import get_semantic_router, SemanticMatch
from .llm_router import llm_router
from .cpu_router import cpu_router, IntentType, TaskComplexity, RoutingDecision
from .observer import record_routing_trace
from ..prompts import get_prompt_library
from ..logger import log


# System version for cache invalidation
SYSTEM_VERSION = "1.0.0"

# Privacy unlock pattern (compiled for speed)
PRIVACY_UNLOCK_PATTERN = re.compile(r"привет,?\s*малыш", re.IGNORECASE)

# Simple greetings for speculative decoding (instant response)
GREETING_RESPONSES = [
    "Привет!", "Слушаю.", "На связи.", "Чем помочь?",
    "Здравствуй!", "Рад тебя слышать!", "Привет, что нового?",
    "Хей!", "Приветствую!", "Готов помочь!",
    "Привет! Чем могу быть полезен?", "Здорово!",
    "На связи, слушаю!", "Да, я тут!", "Приветствую! Что интересного?",
    "Хай! Рассказывай.", "Добрый день!", "Здравствуйте!",
    "Йо! Что новенького?", "Ку! Слушаю внимательно."
]

# Dangerous patterns (strict threshold)
DANGEROUS_PATTERNS = {
    "rm -rf", "format", "delete all", "удали всё", "удалить всё",
    "drop table", "truncate", "удали все файлы"
}

# Temperature mapping by intent
TEMPERATURE_MAP = {
    "coding": 0.3,
    "math": 0.2,
    "question": 0.7,
    "creative": 0.9,
    "psychology": 0.7,
    "greeting": 0.8,
    "search": 0.5,
    "default": 0.7
}

# Intents that don't need RAG
SKIP_RAG_INTENTS = {"greeting", "goodbye", "math", "privacy_unlock"}


@dataclass
class SmartRoutingResult:
    """Complete routing decision with all features."""
    
    # Core routing
    intent: str
    complexity: str = "medium"
    confidence: float = 0.0
    
    # Features
    temperature: float = 0.7
    use_rag: bool = True
    use_tools: bool = False
    streaming_strategy: str = "immediate"  # immediate, delayed, chunked
    
    # Privacy
    is_privacy_unlock: bool = False
    private_mode_active: bool = False
    
    # Prompt
    prompt_id: Optional[str] = None
    prompt_name: Optional[str] = None
    system_prompt: Optional[str] = None
    
    # Topic (for dynamic learning)
    detected_topic: Optional[str] = None
    
    # Safety
    safety_level: str = "safe"  # safe, caution, danger
    requires_confirmation: bool = False
    
    # Speculative response (for greetings)
    speculative_response: Optional[str] = None
    
    # Metadata
    routing_source: str = "unknown"  # semantic, llm, cpu, cache
    routing_time_ms: float = 0.0
    cache_hit: bool = False
    trace_id: Optional[str] = None  # For feedback loop
    
    # Emotional analysis
    emotional_tone: Optional[str] = None
    formality: Optional[str] = None
    
    # Cost estimate
    estimated_tokens: int = 0
    
    # Context
    context_window_size: int = 10


@dataclass
class RoutingTrace:
    """Trace record for observability."""
    timestamp: datetime
    message_preview: str
    predicted_intent: str
    routing_source: str
    routing_time_ms: float
    confidence: float
    cache_hit: bool


class SmartRouter:
    """
    Central routing orchestrator implementing 6-Layer Pipeline.
    
    Features:
        - Privacy Lock detection
        - Semantic routing (10ms)
        - LLM routing with timeout fallback
        - Dynamic temperature tuning
        - RAG trigger decision
        - Safety filtering
        - Async tracing
    """
    
    def __init__(self):
        # Cache with version key
        self._cache: TTLCache = TTLCache(maxsize=100, ttl=300)
        
        # Session state
        self._private_mode = False
        self._private_unlock_time: Optional[datetime] = None
        
        # Stats
        self._stats = {
            "total_requests": 0,
            "semantic_hits": 0,
            "llm_calls": 0,
            "cpu_fallbacks": 0,
            "cache_hits": 0,
            "privacy_unlocks": 0,
        }
        
        # Traces (ring buffer)
        self._traces: List[RoutingTrace] = []
        self._max_traces = 100
        
        log.debug("SmartRouter initialized")
    
    async def route(self, message: str) -> SmartRoutingResult:
        """
        Main routing entry point.
        
        Implements 6-Layer Pipeline for optimal speed and accuracy.
        """
        start = time.perf_counter()
        self._stats["total_requests"] += 1
        
        # =========================================
        # Layer 1: Guardrails (< 1ms)
        # =========================================
        
        # Check privacy unlock
        if PRIVACY_UNLOCK_PATTERN.search(message):
            self._private_mode = True
            self._private_unlock_time = datetime.now()
            self._stats["privacy_unlocks"] += 1
            
            elapsed = (time.perf_counter() - start) * 1000
            return SmartRoutingResult(
                intent="privacy_unlock",
                is_privacy_unlock=True,
                private_mode_active=True,
                speculative_response="Привет! Личная память разблокирована. Теперь я помню всё о тебе.",
                routing_source="guardrail",
                routing_time_ms=elapsed,
                confidence=1.0
            )
        
        # Check for simple greeting (speculative decoding)
        if self._is_simple_greeting(message):
            import random
            elapsed = (time.perf_counter() - start) * 1000
            return SmartRoutingResult(
                intent="greeting",
                speculative_response=random.choice(GREETING_RESPONSES),
                streaming_strategy="immediate",
                use_rag=False,
                routing_source="speculative",
                routing_time_ms=elapsed,
                confidence=1.0
            )
        
        # =========================================
        # Layer 2: Cache (< 2ms)
        # =========================================
        
        cache_key = self._get_cache_key(message)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            self._stats["cache_hits"] += 1
            elapsed = (time.perf_counter() - start) * 1000
            
            # Return cached result with updated metadata
            cached.cache_hit = True
            cached.routing_time_ms = elapsed
            return cached
        
        # =========================================
        # Layer 2.5: Topic Detection + Tone (~2ms)
        # =========================================
        
        from .entity_extractor import detect_topic
        from .tone_detector import detect_tone
        
        detected_topic = detect_topic(message)
        tone_analysis = detect_tone(message)
        
        # =========================================
        # Layer 3: Semantic Router (~10ms)
        # =========================================
        
        semantic_result = await self._semantic_route(message)
        
        if semantic_result and semantic_result.passed_threshold:
            result = self._build_result_from_semantic(semantic_result, message)
            result.routing_time_ms = (time.perf_counter() - start) * 1000
            
            # Use EntityExtractor topic if Semantic didn't provide one
            if not result.detected_topic and detected_topic:
                result.detected_topic = detected_topic
            
            # Cache it
            self._cache[cache_key] = result
            self._stats["semantic_hits"] += 1
            
            # Fire-and-forget trace
            asyncio.create_task(self._log_trace(message, result))
            
            return result
        
        # =========================================
        # Layer 4: LLM Router (~400ms with timeout)
        # =========================================
        
        try:
            llm_result = await asyncio.wait_for(
                llm_router.route(message),
                timeout=0.5  # Strict 500ms budget
            )
            
            result = self._build_result_from_llm(llm_result, message)
            result.routing_time_ms = (time.perf_counter() - start) * 1000
            
            # Add topic from EntityExtractor
            if detected_topic:
                result.detected_topic = detected_topic
            
            # Cache it
            self._cache[cache_key] = result
            self._stats["llm_calls"] += 1
            
            # Fire-and-forget trace
            asyncio.create_task(self._log_trace(message, result))
            
            # Queue for auto-learning (LLM classified, Semantic didn't)
            from .auto_learner import get_auto_learner
            get_auto_learner().queue_for_learning(
                trace_id=result.trace_id or "",
                message=message,
                intent=result.intent,
                confidence=result.confidence,
                topic=result.detected_topic
            )
            
            return result
            
        except asyncio.TimeoutError:
            log.warn("LLM Router timeout, falling back to CPU")
        except Exception as e:
            log.warn(f"LLM Router error: {e}, falling back to CPU")
        
        # =========================================
        # Layer 5: CPU Fallback (0ms)
        # =========================================
        
        cpu_result = cpu_router.route(message)
        result = self._build_result_from_cpu(cpu_result, message)
        result.routing_time_ms = (time.perf_counter() - start) * 1000
        
        # Add topic from EntityExtractor
        if detected_topic:
            result.detected_topic = detected_topic
        
        self._stats["cpu_fallbacks"] += 1
        
        # Fire-and-forget trace
        asyncio.create_task(self._log_trace(message, result))
        
        return result
    
    # =========================================
    # Helper Methods
    # =========================================
    
    def _get_cache_key(self, message: str) -> str:
        """Generate versioned cache key."""
        raw = f"{SYSTEM_VERSION}:{message}"
        return hashlib.sha256(raw.encode()).hexdigest()
    
    def _is_simple_greeting(self, message: str) -> bool:
        """Check if message is a simple greeting."""
        clean = message.lower().strip()
        simple_greetings = {
            "привет", "здравствуй", "хай", "хей", "hi", "hello", "hey",
            "добрый день", "доброе утро", "добрый вечер", "приветствую",
            "здорово", "ку", "йо", "салют"
        }
        return clean in simple_greetings or len(clean) <= 10 and any(g in clean for g in simple_greetings)
    
    async def _semantic_route(self, message: str) -> Optional[SemanticMatch]:
        """Run semantic routing in thread pool (CPU-bound)."""
        router = get_semantic_router()
        # Run in thread pool since sentence-transformers is CPU-bound
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, router.route, message)
    
    def _build_result_from_semantic(self, match: SemanticMatch, message: str) -> SmartRoutingResult:
        """Build result from semantic match."""
        intent = match.intent
        
        # Select prompt from library
        prompt = get_prompt_library().select(
            intent=intent,
            topic=match.topic,
            message=message
        )
        
        return SmartRoutingResult(
            intent=intent,
            confidence=match.score,
            temperature=prompt.temperature or TEMPERATURE_MAP.get(intent, 0.7),
            use_rag=intent not in SKIP_RAG_INTENTS,
            use_tools=intent in {"coding", "search"},
            streaming_strategy="immediate" if match.score > 0.9 else "delayed",
            safety_level=self._assess_safety(message),
            requires_confirmation=self._needs_confirmation(message),
            private_mode_active=self._private_mode,
            routing_source="semantic",
            detected_topic=match.topic,
            prompt_id=prompt.id,
            prompt_name=prompt.name,
            system_prompt=prompt.system_prompt
        )
    
    def _build_result_from_llm(self, decision: RoutingDecision, message: str) -> SmartRoutingResult:
        """Build result from LLM routing decision."""
        intent = decision.intent.value if hasattr(decision.intent, 'value') else str(decision.intent)
        complexity = decision.complexity.value if hasattr(decision.complexity, 'value') else str(decision.complexity)
        
        # Select prompt from library
        prompt = get_prompt_library().select(intent=intent, message=message)
        
        return SmartRoutingResult(
            intent=intent,
            complexity=complexity,
            confidence=decision.confidence,
            temperature=prompt.temperature or TEMPERATURE_MAP.get(intent, 0.7),
            use_rag=decision.needs_search or intent not in SKIP_RAG_INTENTS,
            use_tools=decision.needs_code or decision.needs_search,
            streaming_strategy=decision.suggested_mode,
            safety_level=self._assess_safety(message),
            requires_confirmation=self._needs_confirmation(message),
            private_mode_active=self._private_mode,
            routing_source="llm",
            prompt_id=prompt.id,
            prompt_name=prompt.name,
            system_prompt=prompt.system_prompt
        )
    
    def _build_result_from_cpu(self, decision: RoutingDecision, message: str) -> SmartRoutingResult:
        """Build result from CPU routing decision."""
        intent = decision.intent.value if hasattr(decision.intent, 'value') else str(decision.intent)
        
        return SmartRoutingResult(
            intent=intent,
            complexity="medium",
            confidence=0.6,  # Lower confidence for CPU fallback
            temperature=TEMPERATURE_MAP.get(intent, 0.7),
            use_rag=intent not in SKIP_RAG_INTENTS,
            streaming_strategy="immediate",
            safety_level=self._assess_safety(message),
            private_mode_active=self._private_mode,
            routing_source="cpu"
        )
    
    def _assess_safety(self, message: str) -> str:
        """Assess safety level of the message."""
        lower = message.lower()
        if any(p in lower for p in DANGEROUS_PATTERNS):
            return "danger"
        return "safe"
    
    def _needs_confirmation(self, message: str) -> bool:
        """Check if action needs user confirmation."""
        lower = message.lower()
        return any(p in lower for p in DANGEROUS_PATTERNS)
    
    async def _log_trace(self, message: str, result: SmartRoutingResult) -> None:
        """Log routing trace using Observer (fire-and-forget)."""
        # Record to global observer for analytics & feedback
        trace_id = record_routing_trace(
            message=message,
            intent=result.intent,
            confidence=result.confidence,
            routing_source=result.routing_source,
            routing_time_ms=result.routing_time_ms,
            prompt_id=result.prompt_id,
            prompt_name=result.prompt_name,
            detected_topic=result.detected_topic,
            cache_hit=result.cache_hit,
            temperature=result.temperature,
            use_rag=result.use_rag
        )
        
        # Store trace_id in result for feedback
        result.trace_id = trace_id  # Will add this field
        
        # Also keep local ring buffer for quick access
        trace = RoutingTrace(
            timestamp=datetime.now(),
            message_preview=message[:50],
            predicted_intent=result.intent,
            routing_source=result.routing_source,
            routing_time_ms=result.routing_time_ms,
            confidence=result.confidence,
            cache_hit=result.cache_hit
        )
        
        self._traces.append(trace)
        if len(self._traces) > self._max_traces:
            self._traces.pop(0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        return {
            **self._stats,
            "private_mode": self._private_mode,
            "cache_size": len(self._cache),
            "traces_count": len(self._traces),
        }
    
    def is_private_mode(self) -> bool:
        """Check if private mode is active."""
        # Auto-lock after 30 minutes
        if self._private_unlock_time:
            from datetime import timedelta
            if datetime.now() - self._private_unlock_time > timedelta(minutes=30):
                self._private_mode = False
                self._private_unlock_time = None
        return self._private_mode
    
    def lock_private_mode(self) -> None:
        """Manually lock private mode."""
        self._private_mode = False
        self._private_unlock_time = None
        log.debug("Private mode locked")


# Global instance
_smart_router: Optional[SmartRouter] = None


def get_smart_router() -> SmartRouter:
    """Get or create global SmartRouter instance."""
    global _smart_router
    if _smart_router is None:
        _smart_router = SmartRouter()
    return _smart_router


# Convenience function
async def smart_route(message: str) -> SmartRoutingResult:
    """Quick smart routing."""
    return await get_smart_router().route(message)
