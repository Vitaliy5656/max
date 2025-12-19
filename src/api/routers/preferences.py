"""
Preferences Router for Dynamic Persona API.

Endpoints:
- GET /api/preferences — List all user rules
- POST /api/preferences — Add a new rule
- DELETE /api/preferences/{id} — Delete a rule
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.dynamic_persona import dynamic_persona
from src.core.logger import log

router = APIRouter(prefix="/api", tags=["preferences"])


# ============= Pydantic Models =============

class RuleCreate(BaseModel):
    """Request model for creating a rule."""
    rule: str
    weight: float = 1.0


class RuleResponse(BaseModel):
    """Response model for a rule."""
    id: int
    rule_content: str
    source: str
    weight: float
    is_active: bool


# ============= Endpoints =============

@router.get("/preferences")
async def list_preferences(user_id: str = "default"):
    """List all active user preference rules."""
    try:
        rules = await dynamic_persona.get_active_rules(user_id)
        return {
            "user_id": user_id,
            "rules": [
                RuleResponse(
                    id=r.id,
                    rule_content=r.rule_content,
                    source=r.source,
                    weight=r.weight,
                    is_active=r.is_active
                ).model_dump()
                for r in rules
            ],
            "count": len(rules)
        }
    except Exception as e:
        log.error(f"Error listing preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preferences")
async def create_preference(data: RuleCreate, user_id: str = "default"):
    """Add a new preference rule manually."""
    if not data.rule or len(data.rule.strip()) < 3:
        raise HTTPException(status_code=400, detail="Rule must be at least 3 characters")
    
    try:
        rule_id = await dynamic_persona.add_rule(
            rule_content=data.rule.strip(),
            source="manual",
            weight=data.weight,
            user_id=user_id
        )
        
        if rule_id < 0:
            raise HTTPException(status_code=500, detail="Failed to create rule")
        
        log.api(f"📝 Manual rule added via API: {data.rule[:50]}...")
        
        return {
            "id": rule_id,
            "rule": data.rule,
            "source": "manual",
            "weight": data.weight,
            "message": "Rule created successfully"
        }
    except Exception as e:
        log.error(f"Error creating preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/preferences/{rule_id}")
async def delete_preference(rule_id: int):
    """Delete a preference rule."""
    try:
        success = await dynamic_persona.delete_rule(rule_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        log.api(f"🗑️ Rule {rule_id} deleted via API")
        
        return {"message": f"Rule {rule_id} deleted", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error deleting preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))
