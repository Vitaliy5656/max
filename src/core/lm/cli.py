"""
LM Studio CLI Operations.

Provides functions for interacting with LM Studio via CLI:
- scan_models_cli: Get list of available models
- load_model_impl: Load a model
- unload_model_impl: Unload a model
"""
from typing import Optional

from ..safe_shell import safe_shell
from ..logger import log


async def scan_models_cli() -> list[str]:
    """
    Run 'lms ls' to get real models from LM Studio.
    
    Returns:
        List of model keys/paths
    """
    try:
        result = await safe_shell.execute("lms ls", timeout=30.0)
        
        if result.return_code != 0:
            return []
            
        lines = result.stdout.splitlines()
        models = []
        for line in lines:
            line = line.strip()
            # Skip headers or decorative lines
            if not line or line.startswith("SIZE") or line.startswith("Downloaded"):
                continue
            # Assume model key is the first contiguous string
            parts = line.split()
            if parts:
                models.append(parts[0])
        
        return models
    except Exception as e:
        log.error(f"Error scanning models: {e}")
        return []


async def load_model_impl(model_key: str, ttl: Optional[int] = None) -> bool:
    """
    Load a model via LMS CLI.
    
    Args:
        model_key: Model identifier to load
        ttl: Time-to-live in seconds (auto-unload)
        
    Returns:
        True if successful
    """
    try:
        cmd = f"lms load {model_key}"
        if ttl:
            cmd += f" --ttl {ttl}"

        result = await safe_shell.execute(cmd, timeout=120.0)

        if result.return_code == 0:
            log.lm(f"✓ Model loaded: {model_key}")
            return True
        else:
            log.error(f"✗ Failed to load model: {result.stderr}")
            return False
    except Exception as e:
        log.error(f"✗ Error loading model: {e}")
        return False


async def unload_model_impl(model_key: Optional[str] = None) -> bool:
    """
    Unload a model via LMS CLI.
    
    Args:
        model_key: Specific model to unload, or None for all
        
    Returns:
        True if successful
    """
    try:
        if model_key:
            cmd = f"lms unload {model_key}"
        else:
            cmd = "lms unload --all"

        result = await safe_shell.execute(cmd, timeout=30.0)

        if result.return_code == 0:
            log.lm("✓ Model unloaded")
            return True
        return False
    except Exception as e:
        log.error(f"✗ Error unloading model: {e}")
        return False
