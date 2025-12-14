"""
Router Analytics & Feedback API.

Endpoints:
- GET /api/router/stats - Routing statistics
- GET /api/router/traces - Recent routing traces
- POST /api/router/feedback - Submit routing feedback
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.routing import get_routing_observer, get_smart_router, FeedbackType
from src.core.logger import log

router = APIRouter(prefix="/api/router", tags=["router"])


class FeedbackRequest(BaseModel):
    """User feedback for routing decision."""
    trace_id: str
    feedback: str  # good, bad, wrong_intent, wrong_prompt
    corrected_intent: Optional[str] = None
    comment: Optional[str] = None


@router.get("/stats")
async def get_router_stats():
    """
    Get routing analytics.
    
    Returns hit rates, latencies, accuracy estimates.
    """
    observer = get_routing_observer()
    smart_router = get_smart_router()
    
    observer_stats = observer.get_stats()
    router_stats = smart_router.get_stats()
    
    return {
        "observer": observer_stats,
        "router": router_stats,
        "summary": {
            "total_requests": observer_stats.get("total_requests", 0),
            "semantic_hit_rate": observer_stats.get("semantic_hit_rate", 0),
            "avg_latency_ms": observer_stats.get("avg_latency_ms", 0),
            "accuracy_estimate": observer_stats.get("accuracy_estimate", 0),
            "private_mode": router_stats.get("private_mode", False),
        }
    }


@router.get("/traces")
async def get_recent_traces(limit: int = 50, intent: Optional[str] = None):
    """
    Get recent routing traces.
    
    Use for debugging and analysis.
    """
    observer = get_routing_observer()
    
    if intent:
        traces = observer.get_traces_by_intent(intent, limit)
    else:
        traces = observer.get_recent_traces(limit)
    
    return [t.to_dict() for t in traces]


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get specific trace by ID."""
    observer = get_routing_observer()
    trace = observer.get_trace(trace_id)
    
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    return trace.to_dict()


@router.post("/feedback")
async def submit_feedback(data: FeedbackRequest):
    """
    Submit feedback for a routing decision.
    
    Used for improving the router over time.
    """
    observer = get_routing_observer()
    
    try:
        feedback_type = FeedbackType(data.feedback)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid feedback type. Use: good, bad, wrong_intent, wrong_prompt"
        )
    
    success = observer.add_feedback(
        trace_id=data.trace_id,
        feedback=feedback_type,
        corrected_intent=data.corrected_intent
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    log.api(f"Feedback received: {data.trace_id} -> {data.feedback}")
    
    return {"status": "ok", "message": "Feedback recorded"}


@router.get("/bad-traces")
async def get_bad_traces(limit: int = 50):
    """
    Get traces with negative feedback.
    
    Useful for training data collection.
    """
    observer = get_routing_observer()
    traces = observer.get_bad_feedback_traces(limit)
    return [t.to_dict() for t in traces]


@router.get("/learning-data")
async def get_learning_data():
    """
    Export data for training semantic router.
    
    Returns corrected examples from user feedback.
    """
    observer = get_routing_observer()
    return observer.get_learning_dataset()


@router.get("/intents")
async def get_intent_distribution():
    """Get distribution of intents."""
    observer = get_routing_observer()
    stats = observer.get_stats()
    return stats.get("by_intent", {})


@router.get("/sources")
async def get_source_distribution():
    """Get distribution of routing sources (semantic vs LLM vs CPU)."""
    observer = get_routing_observer()
    stats = observer.get_stats()
    return {
        "counts": stats.get("by_source", {}),
        "rates": stats.get("hit_rates", {})
    }


# ============= Auto-Learning Endpoints =============

class TeachRequest(BaseModel):
    """Manual teaching of new example."""
    message: str
    intent: str
    topic: Optional[str] = None


@router.get("/learner/stats")
async def get_learner_stats():
    """Get auto-learner statistics."""
    from src.core.routing import get_auto_learner
    return get_auto_learner().get_stats()


@router.post("/learner/teach")
async def teach_example(data: TeachRequest):
    """
    Manually teach the router a new example.
    
    Immediately adds to Semantic Router and persists.
    """
    from src.core.routing import get_auto_learner
    
    learner = get_auto_learner()
    learner.force_learn(
        message=data.message,
        intent=data.intent,
        topic=data.topic
    )
    
    log.api(f"Manual teach: '{data.message[:30]}...' -> {data.intent}")
    
    return {"status": "ok", "message": f"Learned: {data.intent}"}


# ============= Shadow Mode Endpoints =============

@router.get("/shadow/stats")
async def get_shadow_stats():
    """Get shadow mode statistics."""
    from src.core.routing.shadow_mode import get_shadow_mode
    return get_shadow_mode().get_stats()


@router.post("/shadow/enable")
async def enable_shadow(shadow_router: str = "llm"):
    """
    Enable shadow mode for A/B testing.
    
    Args:
        shadow_router: Router to run in shadow (semantic, llm, cpu)
    """
    from src.core.routing.shadow_mode import get_shadow_mode, RouterVariant
    
    try:
        variant = RouterVariant(shadow_router)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid router: {shadow_router}")
    
    get_shadow_mode().enable(variant)
    log.api(f"Shadow mode enabled: {shadow_router}")
    
    return {"status": "ok", "shadow_router": shadow_router}


@router.post("/shadow/disable")
async def disable_shadow():
    """Disable shadow mode."""
    from src.core.routing.shadow_mode import get_shadow_mode
    get_shadow_mode().disable()
    log.api("Shadow mode disabled")
    return {"status": "ok", "message": "Shadow mode disabled"}


@router.get("/shadow/mismatches")
async def get_shadow_mismatches(limit: int = 10):
    """Get recent intent mismatches between routers."""
    from src.core.routing.shadow_mode import get_shadow_mode
    return get_shadow_mode().get_recent_mismatches(limit)


@router.get("/shadow/results")
async def get_shadow_results(limit: int = 20):
    """Get recent shadow comparison results."""
    from src.core.routing.shadow_mode import get_shadow_mode
    return get_shadow_mode().get_recent_results(limit)


# ============= Health Check Endpoints =============

@router.get("/health")
async def get_router_health():
    """
    Get comprehensive health status of routing system.
    
    Checks: SemanticRouter, LLMRouter, Cache, Observer, PromptLibrary
    """
    from src.core.routing.health_check import check_health
    health = await check_health()
    return health.to_dict()


@router.get("/classify")
async def classify_message_endpoint(message: str):
    """
    Test message classification.
    
    Returns type, language, flags.
    """
    from src.core.routing.message_classifier import classify_message
    result = classify_message(message)
    return {
        "type": result.message_type.value,
        "language": result.language.value,
        "has_code": result.has_code,
        "has_url": result.has_url,
        "word_count": result.word_count,
        "requires_response": result.requires_response
    }
