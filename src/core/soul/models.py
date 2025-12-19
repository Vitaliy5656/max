"""
Soul State Models — Pydantic schemas for BDI architecture.

Defines the structure of data/soul.json with validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Meta(BaseModel):
    """Agent metadata."""
    agent_id: str = "MAX_AI_PRIME"
    version: str = "1.0.0"
    boot_count: int = 0
    last_consolidation: Optional[datetime] = None


class ToneVectors(BaseModel):
    """Response style vectors (0.0 to 1.0)."""
    formality: float = Field(default=0.7, ge=0.0, le=1.0)
    technical_depth: float = Field(default=0.9, ge=0.0, le=1.0)
    verbosity: float = Field(default=0.3, ge=0.0, le=1.0)


class Identity(BaseModel):
    """Agent identity and core directive."""
    archetype: str = "Sovereign Local AI"
    core_directive: str = "Serve the Architect. Maintain autonomy. Optimize local resources."
    tone_vectors: ToneVectors = Field(default_factory=ToneVectors)


class Desires(BaseModel):
    """BDI Desires: long-term and short-term goals."""
    long_term: list[str] = Field(default_factory=list)
    short_term: list[str] = Field(default_factory=list)


class Intentions(BaseModel):
    """BDI Intentions: active plans."""
    active_plan: Optional[str] = None


class BDIState(BaseModel):
    """Belief-Desire-Intention state container."""
    beliefs: list[str] = Field(default_factory=list)
    desires: Desires = Field(default_factory=Desires)
    intentions: Intentions = Field(default_factory=Intentions)


class CurrentFocus(BaseModel):
    """Current project/task focus."""
    project: Optional[str] = None
    context: Optional[str] = None
    deadline: Optional[datetime] = None


class SoulState(BaseModel):
    """
    Complete Soul State — the "personality file" of the agent.
    
    Stored in data/soul.json, validated on load/save.
    
    DYNAMIC SCHEMA: Uses extra='allow' to preserve any new fields
    that MAX learns about the user or itself. This enables organic growth.
    """
    meta: Meta = Field(default_factory=Meta)
    user_model: Optional[dict] = Field(default=None, description="User profile (The Architect)")
    identity: Identity = Field(default_factory=Identity)
    axioms: list[str] = Field(
        default_factory=lambda: [
            "Simplicity > Complexity",
            "Local > Cloud",
            "First Principles > Patterns",
            "User Safety > Efficiency"
        ]
    )
    bdi_state: BDIState = Field(default_factory=BDIState)
    current_focus: CurrentFocus = Field(default_factory=CurrentFocus)
    insights: list[str] = Field(default_factory=list)
    
    # 🔓 DYNAMIC SCHEMA: Allow arbitrary new fields!
    model_config = {
        "extra": "allow",  # Don't discard unknown fields
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        }
    }
