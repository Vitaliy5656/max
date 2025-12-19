"""Test MAX chat API directly."""
import asyncio
import httpx

async def test_max_api():
    print("Testing MAX /api/chat endpoint...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "http://localhost:8000/api/chat",
            json={
                "message": "Hello!",
                "thinking_mode": "standard"
            },
            headers={"Accept": "text/event-stream"}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print("\nSSE Stream:")
        print("-" * 40)
        
        for line in response.text.split("\n"):
            if line.strip():
                print(line)

if __name__ == "__main__":
    asyncio.run(test_max_api())
