
import time
import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def measure_import_lib(lib_name):
    start = time.time()
    try:
        __import__(lib_name)
        end = time.time()
        print(f"Import {lib_name}: {end - start:.4f}s")
    except Exception as e:
        print(f"Import {lib_name} FAILED: {e}")

def measure_import(module_name):
    start = time.time()
    try:
        __import__(module_name)
        end = time.time()
        print(f"Import {module_name}: {end - start:.4f}s")
    except Exception as e:
        print(f"Import {module_name} FAILED: {e}")

async def measure_startup():
    start = time.time()
    try:
        from src.api.api import startup
        await startup()
        end = time.time()
        print(f"Startup execution: {end - start:.4f}s")
    except Exception as e:
        print(f"Startup FAILED: {e}")

if __name__ == "__main__":
    print("--- BASELINE MEASUREMENTS ---")
    
    # Measure Libs
    measure_import_lib("tiktoken")
    measure_import_lib("aiosqlite")
    measure_import("src.core.config")

    # Measure Imports
    measure_import("src.core.memory")
    measure_import("src.core.rag")
    measure_import("src.core.lm_client")
    measure_import("src.api.api")
    
    # Measure Startup (simulated)
    # We invoke the startup function directly if possible
    # checks if event loop exists
    try:
        asyncio.run(measure_startup())
    except Exception as e:
        print(f"Startup Test Error: {e}")
