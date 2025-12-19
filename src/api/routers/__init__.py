"""
Routers package for MAX AI API.

Contains domain-specific routers:
- chat: /chat, /conversations
- documents: /documents/*
- agent: /agent/*
- templates: /templates/*
- metrics: /metrics/*, /feedback, /achievements
- models: /models, /config/*
- health: /health/*
- backup: /backup/*
- preferences: /preferences/* (Dynamic Persona)
"""

from .chat import router as chat_router
from .documents import router as documents_router
from .agent import router as agent_router
from .templates import router as templates_router
from .metrics import router as metrics_router
from .models import router as models_router
from .health import router as health_router
from .backup import router as backup_router
from .preferences import router as preferences_router

__all__ = [
    "chat_router",
    "documents_router",
    "agent_router",
    "templates_router",
    "metrics_router",
    "models_router",
    "health_router",
    "backup_router",
    "preferences_router",
]
