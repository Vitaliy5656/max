"""
Models Router for MAX AI API.

Endpoints:
- GET /api/models
- GET /api/config/model_selection_mode
- POST /api/config/model_selection_mode
"""
from fastapi import APIRouter, HTTPException

from src.core.lm import lm_client
from src.api.schemas import ModelSelectionModeRequest

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models")
async def get_models():
    """Get available LLM models."""
    # P1 Fix: Use async and sync state
    models = await lm_client.get_available_models()
    # Force sync state from LM Studio
    current = await lm_client.sync_state()
    
    return {
        "models": models,
        "current": current,
        "smart_routing": True
    }


@router.get("/config/model_selection_mode")
async def get_model_selection_mode():
    """Get current model selection mode (manual/auto)."""
    from src.core.config import config as app_config
    return {"mode": app_config.lm_studio.model_selection_mode}


@router.post("/config/model_selection_mode")
async def set_model_selection_mode(request: ModelSelectionModeRequest):
    """Set model selection mode (manual/auto)."""
    from src.core.config import config as app_config
    
    if request.mode not in ["manual", "auto"]:
        raise HTTPException(400, "Invalid mode. Must be 'manual' or 'auto'")
    
    app_config.lm_studio.model_selection_mode = request.mode
    
    from src.core.logger import log
    log.api(f"🔧 Model selection mode changed to: {request.mode}")
    
    return {"success": True, "mode": request.mode}


# =============================================================================
# PROVIDER SWITCHING (Phase 8: Gemini Integration)
# =============================================================================

@router.get("/provider")
async def get_provider():
    """Get current LLM provider (lmstudio/gemini)."""
    return {
        "provider": lm_client.provider,
        "available": list(lm_client.PROVIDERS)
    }


@router.post("/provider")
async def set_provider(request: dict):
    """Set LLM provider (lmstudio/gemini)."""
    provider = request.get("provider", "lmstudio")
    
    if provider not in lm_client.PROVIDERS:
        raise HTTPException(400, f"Invalid provider. Must be one of {lm_client.PROVIDERS}")
    
    lm_client.provider = provider
    
    from src.core.logger import log
    log.api(f"🔌 Provider switched to: {provider}")
    
    return {"success": True, "provider": provider}

