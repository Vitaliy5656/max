"""
Smart Model Loader — GPU/CPU Allocation for LM Studio.

Forces models to specific hardware:
- Qwen (main brain): GPU max
- Phi-3 (MO_Guard): CPU only (saves ~3GB VRAM)
- Embeddings: CPU only (lightweight)
"""
import asyncio
import subprocess
import shutil
from src.core.logger import log


# Model configurations: (model_pattern, gpu_setting, identifier)
# NOTE: Use patterns that match your actual LM Studio models.
# Run `lms ps` to see currently loaded models and their identifiers.
MODEL_CONFIGS = [
    # Main brain -> ALL GPU (matches 'openai/gpt-oss-20b' or similar)
    ("openai/gpt-oss-20b", "max", "main"),
    # MO_Guard/extraction -> CPU only (Phi-3.5)
    ("phi-3.5-mini-instruct", "off", "mo_guard"),
    # Embeddings -> CPU only
    ("text-embedding-nomic-embed-text-v1.5", "off", "embeddings"),
]


def is_lms_available() -> bool:
    """Check if lms CLI is available in PATH."""
    return shutil.which("lms") is not None


async def load_model(model_pattern: str, gpu: str = "max", identifier: str = None, quiet: bool = True) -> bool:
    """
    Load a model via LM Studio CLI (Async).
    """
    if not is_lms_available():
        log.warn("LMS CLI not available, skipping model load")
        return False
    
    cmd = ["lms", "load", model_pattern, "--gpu", gpu, "-y"]
    if identifier:
        cmd.extend(["--identifier", identifier])
    if quiet:
        cmd.append("--quiet")
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
        except asyncio.TimeoutError:
            log.error(f"⏱️ Timeout loading {model_pattern}")
            process.kill()
            return False
            
        if process.returncode == 0:
            log.api(f"✅ Model loaded: {model_pattern} (GPU: {gpu})")
            return True
        else:
            log.error(f"❌ Failed to load {model_pattern}: {stderr.decode()}")
            return False
    except Exception as e:
        log.error(f"❌ Error loading {model_pattern}: {e}")
        return False


async def unload_model(model_pattern: str) -> bool:
    """Unload a model from LM Studio (Async)."""
    if not is_lms_available():
        return False
    
    try:
        process = await asyncio.create_subprocess_exec(
            "lms", "unload", model_pattern, "-y", "--quiet",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(process.wait(), timeout=30)
        return process.returncode == 0
    except Exception:
        return False


async def get_loaded_models() -> list:
    """Get list of currently loaded models (Async)."""
    if not is_lms_available():
        return []
    
    try:
        process = await asyncio.create_subprocess_exec(
            "lms", "ps",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10)
        
        if process.returncode == 0:
            output = stdout.decode().strip()
            return output.split("\n") if output else []
        return []
    except Exception:
        return []


async def smart_load_models(force: bool = False):
    """
    Load all models with optimized allocation (Async).
    """
    if not is_lms_available():
        log.warn("⚠️ LMS CLI not found. Install via LM Studio > Developer > Install lms to PATH")
        return
    
    log.api("🤖 Starting smart model loading (Async)...")
    
    loaded = await get_loaded_models()
    
    for model_pattern, gpu, identifier in MODEL_CONFIGS:
        # Check if already loaded
        already_loaded = any(model_pattern in m.lower() for m in loaded)
        
        if already_loaded and not force:
            log.debug(f"⏭️ {model_pattern} already loaded, skipping")
            continue
        
        await load_model(model_pattern, gpu=gpu, identifier=identifier)
    
    log.api("✅ Smart model loading complete")


if __name__ == "__main__":
    asyncio.run(smart_load_models())
