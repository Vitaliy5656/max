"""
Detailed Live Test for Cognitive Loop.

Tests all cognitive loop components with real LLM interaction.
"""
import asyncio
import httpx
import json

APP_URL = "http://localhost:8000"

async def test_cognitive_loop_detailed():
    """Test cognitive loop with detailed step tracking."""
    print("\n" + "="*60)
    print("DETAILED COGNITIVE LOOP TEST")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Complex question to trigger full cognitive loop
        payload = {
            "message": "Объясни как работает квантовый компьютер простыми словами.",
            "model": "auto",
            "thinking_mode": "deep"
        }
        
        print(f"\n[REQUEST] {payload['message']}")
        print("-" * 50)
        
        try:
            async with client.stream("POST", f"{APP_URL}/api/chat", json=payload) as response:
                if response.status_code != 200:
                    print(f"[FAIL] Request failed: {response.status_code}")
                    return False
                
                # Track events
                events = {
                    "thinking_start": 0,
                    "thinking_end": 0,
                    "steps": [],
                    "tokens": 0,
                    "errors": []
                }
                
                final_response = ""
                
                async for chunk in response.aiter_lines():
                    if not chunk.startswith("data: "):
                        continue
                        
                    data_str = chunk[6:]
                    try:
                        data = json.loads(data_str)
                        
                        # Thinking events
                        if "thinking" in data:
                            if data["thinking"] == "start":
                                events["thinking_start"] += 1
                                print(f"[THINKING] Started")
                            elif data["thinking"] == "end":
                                events["thinking_end"] += 1
                                duration = data.get("duration_ms", 0)
                                print(f"[THINKING] Ended (duration: {duration}ms)")
                            elif data["thinking"] == "step":
                                step_name = data.get("name", "unknown")
                                step_content = data.get("content", "")[:100]
                                events["steps"].append(step_name)
                                print(f"  [STEP] {step_name}: {step_content}...")
                        
                        # Token events
                        if "token" in data:
                            events["tokens"] += 1
                            final_response += data["token"]
                        
                        # Error events
                        if "error" in data:
                            events["errors"].append(data["error"])
                            print(f"[ERROR] {data['error']}")
                        
                        # Conversation ID
                        if "conversation_id" in data:
                            print(f"[CONV] New conversation: {data['conversation_id']}")
                            
                    except json.JSONDecodeError:
                        pass
                
                # Summary
                print("\n" + "="*60)
                print("RESULTS")
                print("="*60)
                print(f"Thinking events: {events['thinking_start']} start, {events['thinking_end']} end")
                print(f"Step events: {len(events['steps'])} ({', '.join(events['steps'])})")
                print(f"Token events: {events['tokens']}")
                print(f"Errors: {len(events['errors'])}")
                print(f"\nFinal response preview ({len(final_response)} chars):")
                print("-" * 50)
                print(final_response[:500] + "..." if len(final_response) > 500 else final_response)
                print("-" * 50)
                
                # Validation
                success = True
                if events["thinking_start"] == 0:
                    print("[WARN] No thinking start events!")
                    success = False
                if len(events["steps"]) == 0:
                    print("[WARN] No step events - cognitive loop may not be streaming steps!")
                if events["tokens"] == 0:
                    print("[FAIL] No tokens received!")
                    success = False
                if len(events["errors"]) > 0:
                    print(f"[FAIL] {len(events['errors'])} errors occurred!")
                    success = False
                
                return success
                
        except Exception as e:
            print(f"[FAIL] Test failed: {e}")
            return False


async def test_standard_chat():
    """Test standard chat (non-cognitive) for comparison."""
    print("\n" + "="*60)
    print("STANDARD CHAT TEST (Baseline)")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {
            "message": "Привет!",
            "model": "auto",
            "thinking_mode": "standard"
        }
        
        print(f"[REQUEST] {payload['message']}")
        
        try:
            async with client.stream("POST", f"{APP_URL}/api/chat", json=payload) as response:
                if response.status_code != 200:
                    print(f"[FAIL] Request failed: {response.status_code}")
                    return False
                
                tokens = 0
                response_text = ""
                
                async for chunk in response.aiter_lines():
                    if chunk.startswith("data: "):
                        try:
                            data = json.loads(chunk[6:])
                            if "token" in data:
                                tokens += 1
                                response_text += data["token"]
                        except:
                            pass
                
                print(f"[PASS] Standard chat: {tokens} tokens, {len(response_text)} chars")
                print(f"Preview: {response_text[:100]}...")
                return True
                
        except Exception as e:
            print(f"[FAIL] Standard chat failed: {e}")
            return False


async def main():
    print("DETAILED LIVE VERIFICATION")
    print("="*60)
    
    # Test standard chat first (baseline)
    await test_standard_chat()
    
    # Test cognitive loop
    await test_cognitive_loop_detailed()
    
    print("\n[DONE] All tests completed.")


if __name__ == "__main__":
    asyncio.run(main())
