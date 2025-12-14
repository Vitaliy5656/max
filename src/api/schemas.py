"""
Pydantic Schemas for MAX AI API.

All request/response models in one place for reusability.
"""
from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request for chat endpoint."""
    message: str
    conversation_id: Optional[str] = None
    model: str = "auto"
    temperature: float = 0.7
    use_rag: bool = True
    thinking_mode: str = "standard"  # fast/standard/deep
    has_image: bool = False  # Auto-activates vision mode


class ConversationCreate(BaseModel):
    """Request to create a new conversation."""
    title: str = "Новый разговор"


class TemplateCreate(BaseModel):
    """Request to create a new template."""
    name: str
    prompt: str
    category: str = "general"


class AgentStartRequest(BaseModel):
    """Request to start autonomous agent."""
    goal: str
    max_steps: int = 20
    use_internet: bool = True
    use_files: bool = False


class FeedbackRequest(BaseModel):
    """Request to submit feedback on a message."""
    message_id: int
    rating: int  # 1 = positive, -1 = negative


class ModelSelectionModeRequest(BaseModel):
    """Request to change model selection mode."""
    mode: str  # "manual" or "auto"
