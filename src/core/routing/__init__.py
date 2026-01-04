"""
Routing package for MAX AI.

Provides intent classification, complexity estimation, and entropy-based routing.
"""
from .cpu_router import CPURouter, cpu_router, IntentType, TaskComplexity, RoutingDecision
from .entropy_router import EntropyRouter, entropy_router, SamplingStrategy, SamplingParams, EntropyMetrics
from .llm_router import LLMRouter, llm_router
from .semantic_router import SemanticRouter, get_semantic_router, semantic_route, SemanticMatch
from .smart_router import SmartRouter, get_smart_router, smart_route, SmartRoutingResult
from .privacy_guard import PrivacyGuard, get_privacy_guard, PrivacyLevel
from .observer import RoutingObserver, get_routing_observer, FeedbackType
from .auto_learner import AutoLearner, get_auto_learner, initialize_auto_learning
from .grammar import GrammarManager, GrammarType, get_grammar_manager

__all__ = [
    # SmartRouter (Main Entry Point - 6-Layer Pipeline)
    'SmartRouter', 'get_smart_router', 'smart_route', 'SmartRoutingResult',
    # Privacy Guard
    'PrivacyGuard', 'get_privacy_guard', 'PrivacyLevel',
    # Observer (Tracing & Feedback)
    'RoutingObserver', 'get_routing_observer', 'FeedbackType',
    # Auto-Learner
    'AutoLearner', 'get_auto_learner', 'initialize_auto_learning',
    # Grammar (GBNF for structured output)
    'GrammarManager', 'GrammarType', 'get_grammar_manager',
    # Semantic Router (Layer 2 - fast vector search)
    'SemanticRouter', 'get_semantic_router', 'semantic_route', 'SemanticMatch',
    # CPU Router (heuristic fallback)
    'CPURouter', 'cpu_router',
    # LLM Router (Phi-3.5)
    'LLMRouter', 'llm_router',
    # Common types
    'IntentType', 'TaskComplexity', 'RoutingDecision',
    # Entropy Router
    'EntropyRouter', 'entropy_router', 'SamplingStrategy', 'SamplingParams', 'EntropyMetrics'
]


