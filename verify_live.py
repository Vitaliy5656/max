import asyncio
import httpx
import json
import sys

# Configuration
LM_STUDIO_URL = "http://localhost:1234/v1"
APP_URL = "http://localhost:8000"

async def check_lm_studio():
    print(f"\n[TEST] Checking LM Studio Direct Connection ({LM_STUDIO_URL})...")
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            # Check models endpoint (Standard OpenAI)
            resp = await client.get(f"{LM_STUDIO_URL}/models")
            if resp.status_code == 200:
                print("[PASS] LM Studio is ONLINE and reachable.")
                models = resp.json()
                model_ids = [m['id'] for m in models['data']]
                print(f"       Available Models: {len(model_ids)}")
                return True
            else:
                print(f"[FAIL] LM Studio returned status {resp.status_code}")
                return False
        except Exception as e:
            print(f"[FAIL] Could not connect to LM Studio: {e}")
            print("       Make sure LM Studio is running and Server is ON via port 1234.")
            return False

async def check_app_health():
    print(f"\n[TEST] Checking App Health ({APP_URL})...")
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{APP_URL}/api/health")
            if resp.status_code == 200:
                print("[PASS] App Server is ONLINE.")
                return True
            else:
                print(f"[FAIL] App Health Failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"[FAIL] App Server unreachable: {e}")
            return False

async def verify_chat_deep():
    print("\n[TEST] DEEP Chat via App (LangGraph + Reasoning)...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "message": "2+2?",
            "model": "auto",
            "thinking_mode": "deep"
        }
        try:
            async with client.stream("POST", f"{APP_URL}/api/chat", json=payload) as response:
                if response.status_code != 200:
                    print(f"[FAIL] Deep Chat Request Failed: {response.status_code}")
                    try:
                        print(f"       Response: {await response.read()}")
                    except:
                        pass
                    return False
                
                print("   Receiving thoughts:", end=" ", flush=True)
                has_thinking = False
                has_response = False
                
                async for chunk in response.aiter_lines():
                    if chunk.startswith("data: "):
                        data_str = chunk[6:]
                        try:
                            data = json.loads(data_str)
                            if "thinking" in data:
                                if data["thinking"] == "start":
                                    print(" [Thinking Started]", end="", flush=True)
                                    has_thinking = True
                                elif data["thinking"] == "step":
                                    print(".", end="", flush=True)
                                elif data["thinking"] == "end":
                                    print(" [Thinking Ended]", end="", flush=True)
                                    
                            if "token" in data:
                                has_response = True
                                
                            if "error" in data:
                                print(f"\n[FAIL] Error in Deep stream: {data['error']}")
                                return False
                        except:
                            pass
                            
                if not has_thinking:
                    print("\n[WARN] Warning: No thinking events received.")
                if not has_response:
                    print("\n[FAIL] No final response received.")
                    return False
                    
                print("\n[PASS] Deep Chat Complete!")
                return True
        except Exception as e:
            print(f"\n[FAIL] Deep Chat test failed: {e}")
            return False

async def main():
    print("STARTING LIVE SYSTEM VERIFICATION")
    print("====================================")
    
    # 1. Check LM Studio (Critical Dependency)
    lm_ok = await check_lm_studio()
    if not lm_ok:
        print("\nSTOP: LM Studio is down. Cannot proceed.")
        return

    # 2. Check App
    app_ok = await check_app_health()
    if not app_ok:
        print("\nWARN: App is down. Existing process might have crashed.")
        # We will exit here so the Agent can decide to restart it
        return

    # 3. Test Functionality
    await verify_chat_deep()

if __name__ == "__main__":
    asyncio.run(main())
