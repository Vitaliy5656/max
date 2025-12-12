
import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.lm_client import LMStudioClient, TaskType

async def test_client():
    print("Initializing LMStudioClient...")
    client = LMStudioClient()
    
    print(f"Base URL: {client.base_url}")
    
    try:
        print("Listing models...")
        models = await client.list_models()
        print(f"Found {len(models)} models.")
        for m in models:
            print(f" - {m.id}")
            
        if not models:
            print("ERROR: No models found. Is LM Studio running and server started?")
            return

        print("\nTesting chat generation (TaskType.QUICK)...")
        response = await client.chat(
            messages=[{"role": "user", "content": "Say 'Hello User' and nothing else."}],
            task_type=TaskType.QUICK,
            stream=False
        )
        print(f"Response (Quick): {response}")
        
        print("\nTesting streaming chat...")
        full_response = ""
        async for chunk in await client.chat(
            messages=[{"role": "user", "content": "Count to 3."}],
            stream=True
        ):
            print(f"Chunk: {chunk}", end="", flush=True)
            full_response += chunk
        print("\nFull Stream Response received.")
            
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Fix for Windows loop policy if needed
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(test_client())
