
import asyncio
import json
import httpx

async def test_api_chat():
    url = "http://localhost:8000/api/chat"
    payload = {
        "message": "Hello API, are you working?",
        "conversation_id": None,
        "model": "auto",
        "temperature": 0.7,
        "use_rag": False
    }

    print(f"Sending POST to {url}...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                print(f"Status Code: {response.status_code}")
                if response.status_code != 200:
                    print(f"Error: {await response.aread()}")
                    return

                print("Streaming response:")
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                            if "token" in data:
                                print(data["token"], end="", flush=True)
                            elif "done" in data:
                                print("\n[DONE]")
                        except json.JSONDecodeError:
                            print(f"[Invalid JSON]: {line}")
    except Exception as e:
        print(f"\n[ERROR] Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_chat())
