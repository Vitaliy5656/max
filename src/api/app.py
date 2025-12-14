"""
MAX AI API Application.

FastAPI application with modular routers.
This is the new main entry point for the API.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import core modules for initialization
from src.core.memory import memory
from src.core.lm import lm_client
from src.core.rag import rag
from src.core.templates import templates
from src.core.user_profile import user_profile
from src.core.metrics import metrics_engine
from src.core.adaptation import initialize_adaptation
from src.core.backup import backup_manager
from src.core.embedding_service import embedding_service
from src.core.semantic_router import semantic_router
from src.core.context_primer import context_primer
from src.core.self_reflection import initialize_self_reflection
from src.core.error_memory import error_memory
from src.core.autogpt import AutoGPTAgent
from src.core.logger import log

# Import routers
from src.api.routers import (
    chat_router,
    documents_router,
    agent_router,
    templates_router,
    metrics_router,
    models_router,
    health_router,
    backup_router,
)
from src.api.routers.router_analytics import router as router_analytics
from src.api.routers.agent import set_agent

# ============= Global State =============

_initialized = False
_autogpt_agent: Optional[AutoGPTAgent] = None


def is_initialized() -> bool:
    """Check if app is initialized."""
    return _initialized


# ============= Lifespan Context Manager =============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Modern lifespan context manager for startup/shutdown.
    
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown").
    """
    global _initialized, _autogpt_agent
    
    # ===== STARTUP =====
    if not _initialized:
        await memory.initialize()
        await user_profile.initialize(memory._db)
        await rag.initialize(memory._db)
        await templates.initialize(memory._db)
        await metrics_engine.initialize(memory._db)
        await initialize_adaptation(memory._db)
        
        # AI Next Gen: Initialize semantic routing and context priming
        await embedding_service.initialize(lm_client)
        await semantic_router.initialize(lm_client, embedding_service)
        await context_primer.initialize(memory._db, embedding_service)
        await initialize_self_reflection(memory._db)
        
        # Initialize error_memory for learning from mistakes
        await error_memory.initialize(memory._db, embedding_service)
        
        # Use AutoGPTAgent for autonomous task execution
        _autogpt_agent = AutoGPTAgent(memory._db)
        await _autogpt_agent.initialize(memory._db)
        
        # Register agent with router
        set_agent(_autogpt_agent)
        
        # Initialize auto-learning for SmartRouter
        from src.core.routing import initialize_auto_learning
        await initialize_auto_learning()
        
        _initialized = True
        log.api("✅ AI Next Gen modules initialized (SemanticRouter, ContextPrimer, SelfReflection, ErrorMemory, AutoGPTAgent, AutoLearner)")
    
    yield  # Application runs here
    
    # ===== SHUTDOWN =====
    log.api("📦 Spawning backup worker before shutdown...")
    backup_manager.spawn_backup_worker()
    await memory.close()


# ============= FastAPI App =============

app = FastAPI(
    title="MAX AI API",
    description="REST API for MAX AI Assistant React frontend",
    version="1.2.0",
    lifespan=lifespan
)

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ============= Register Routers =============

app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(agent_router)
app.include_router(templates_router)
app.include_router(metrics_router)
app.include_router(models_router)
app.include_router(health_router)
app.include_router(backup_router)
app.include_router(router_analytics)


# ============= Run Server =============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
