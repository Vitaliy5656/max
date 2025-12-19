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
from src.core.dynamic_persona import initialize_dynamic_persona
from src.core.backup import backup_manager
from src.core.embedding_service import embedding_service
from src.core.semantic_router import semantic_router
from src.core.context_primer import context_primer
from src.core.self_reflection import initialize_self_reflection
from src.core.error_memory import error_memory
from src.core.autogpt import AutoGPTAgent
from src.core.logger import log
from src.core.soul import soul_manager  # Soul Manager for BDI
from src.core.model_loader import smart_load_models, is_lms_available  # GPU/CPU allocation

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
    preferences_router,
)
from src.api.routers.router_analytics import router as router_analytics
from src.api.routers.research import router as research_router
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
        await initialize_dynamic_persona(memory._db)
        
        # Soul Manager: Load asynchronously (non-blocking)
        await soul_manager.load_async()
        await soul_manager.start_persistence_loop()
        log.api("🧠 Soul Manager initialized with persistence loops")
        
        # Smart Model Loading: Allocate GPU/CPU for each model
        if is_lms_available():
            log.api("🎮 LMS CLI available, configuring GPU/CPU allocation...")
            asyncio.create_task(smart_load_models())
        else:
            log.warn("⚠️ LMS CLI not available, skipping hardware configuration")
        
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
        
        # Initialize Research Lab
        from src.core.research.storage import research_storage
        from src.core.research.worker import research_worker
        from src.core.research.agent import research_agent
        from src.core.web_search import WebSearchTool
        from src.core.research.agent import AsyncRateLimiter
        
        await research_storage.initialize(embedding_service)
        await research_worker.cleanup_zombies()
        
        # Initialize research agent with services
        web_search = WebSearchTool()
        rate_limiter = AsyncRateLimiter(requests=40, period=60)
        await research_agent.initialize(lm_client, embedding_service, web_search, rate_limiter)
        
        log.api("🔬 Research Lab initialized (Storage, Worker, Agent)")
        
        _initialized = True
        log.api("✅ AI Next Gen modules initialized (SemanticRouter, ContextPrimer, SelfReflection, ErrorMemory, AutoGPTAgent, AutoLearner)")
    
    yield  # Application runs here
    
    # ===== SHUTDOWN =====
    # Soul Manager: Graceful shutdown — save pending changes
    await soul_manager.save_on_exit()
    
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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
app.include_router(preferences_router)
app.include_router(router_analytics)
app.include_router(research_router)  # Research Lab


# ============= Run Server =============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
