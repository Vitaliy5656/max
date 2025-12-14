"""
Metrics Router for MAX AI API.

Endpoints:
- GET /api/metrics
- GET /api/metrics/proof
- GET /api/achievements
- POST /api/feedback
"""
from fastapi import APIRouter

from src.core.metrics import metrics_engine
from src.api.schemas import FeedbackRequest

router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/metrics")
async def get_metrics():
    """Get current IQ and Empathy scores."""
    iq = await metrics_engine.calculate_iq()
    empathy = await metrics_engine.calculate_empathy()
    
    return {
        "iq": iq.to_dict(),
        "empathy": empathy.to_dict()
    }


@router.get("/metrics/proof")
async def get_adaptation_proof():
    """Get adaptation proof (Day 1 vs Day 30)."""
    proof = await metrics_engine.get_adaptation_proof()
    return proof


@router.get("/achievements")
async def get_achievements():
    """Get all achievements."""
    achievements = await metrics_engine.get_achievements()
    return [a.to_dict() for a in achievements]


@router.post("/feedback")
async def submit_feedback(data: FeedbackRequest):
    """Submit feedback on a message."""
    # Record to interaction_outcomes
    is_positive = data.rating > 0
    is_negative = data.rating < 0
    
    await metrics_engine.record_interaction_outcome(
        message_id=data.message_id,
        user_message="[explicit feedback]",
        detected_positive=is_positive,
        detected_negative=is_negative
    )
    
    return {"success": True}
