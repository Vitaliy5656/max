import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

async def test_tools_security():
    print("Testing Tools Security...")
    from src.core.tools import tools
    
    # 1. Check ALLOWED_COMMANDS (node should be blocked)
    print("  Checking 'node -v'...")
    res = await tools.execute("run_command", {"command": "node -v"})
    if "not in whitelist" in res.lower() or "blocked" in res.lower():
        print("  [OK] Dangerous command 'node' blocked correctly.")
    else:
        print(f"  [FAIL] Dangerous command 'node' NOT blocked: {res}")

    # 2. Check ls (should be allowed)
    print("  Checking 'echo test'...")
    res = await tools.execute("run_command", {"command": "echo test"})
    if "test" in res:
         print("  [OK] Safe command 'echo' allowed.")
    else:
         print(f"  [WARN] Safe command 'echo' output: {res}")

async def test_config_values():
    print("\nTesting Config Values...")
    from src.core.config import config
    
    if hasattr(config.lm_studio, "max_concurrent_requests"):
        print(f"  [OK] max_concurrent_requests present: {config.lm_studio.max_concurrent_requests}")
    else:
        print("  [FAIL] max_concurrent_requests MISSING in config")
        
    if hasattr(config.memory, "summary_token_ratio"):
        print(f"  [OK] summary_token_ratio present: {config.memory.summary_token_ratio}")
    else:
        print("  [FAIL] summary_token_ratio MISSING in config")

async def test_autogpt_structure():
    print("\nTesting AutoGPT Structure...")
    from src.core.autogpt import autogpt
    
    if hasattr(autogpt, "_run_lock"):
        print("  [OK] AutoGPT Lock present")
    else:
        print("  [FAIL] AutoGPT Lock MISSING")
        
    if hasattr(autogpt, "run_generator"):
        print("  [OK] AutoGPT run_generator present")
    else:
        print("  [FAIL] AutoGPT run_generator MISSING")

async def main():
    print("=== MAX AI Assistant Fix Verification ===")
    try:
        await test_config_values()
        await test_tools_security()
        await test_autogpt_structure()
        print("\n[OK] Verification Complete!")
    except Exception as e:
        print(f"\n[FAIL] Verification Failed: {e}")

        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
