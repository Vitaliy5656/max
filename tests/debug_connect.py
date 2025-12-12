
import asyncio
from openai import AsyncOpenAI

async def test_connection():
    print("Testing connection to LM Studio at http://localhost:1234/v1...")
    client = AsyncOpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
    
    try:
        models = await client.models.list()
        print(f"Successfully connected! Found {len(models.data)} models.")
        for m in models.data:
            print(f" - {m.id}")
            
        print("\nSending test chat message...")
        response = await client.chat.completions.create(
            model=models.data[0].id,
            messages=[{"role": "user", "content": "Hello, are you working?"}],
            temperature=0.7
        )
        print("Response received:")
        print(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Failed to connect or chat: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
