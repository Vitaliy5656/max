"""
Quick test script for LM Studio API.
Run: python test_lm_studio.py
"""
import asyncio
from openai import AsyncOpenAI

async def test_direct():
    """Test LM Studio API directly."""
    client = AsyncOpenAI(
        base_url="http://localhost:1234/v1",
        api_key="not-needed"
    )
    
    print("=" * 50)
    print("TEST 1: List models")
    print("=" * 50)
    
    models = await client.models.list()
    for m in models.data:
        print(f"  - {m.id}")
    
    if not models.data:
        print("  [FAIL] No models loaded!")
        return
    
    model_id = models.data[0].id
    print(f"\n[OK] Using model: {model_id}")
    
    print("\n" + "=" * 50)
    print("TEST 2: Simple completion (non-streaming)")
    print("=" * 50)
    
    try:
        response = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "user", "content": "Привет! Скажи одно слово."}
            ],
            max_tokens=50,
            temperature=0.7,
            stream=False
        )
        content = response.choices[0].message.content
        print(f"  Response: {content}")
        print(f"  [OK] Non-streaming works!" if content else "  [FAIL] Empty response!")
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
    
    print("\n" + "=" * 50)
    print("TEST 3: Streaming completion")
    print("=" * 50)
    
    try:
        stream = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "user", "content": "Привет! Как дела?"}
            ],
            max_tokens=100,
            temperature=0.7,
            stream=True
        )
        
        chunks = []
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                chunks.append(content)
                print(content, end="", flush=True)
        
        print(f"\n  Total chunks: {len(chunks)}")
        print(f"  [OK] Streaming works!" if chunks else "  [FAIL] No chunks received!")
        
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
    
    print("\n" + "=" * 50)
    print("TEST 4: With system prompt (like MAX uses)")
    print("=" * 50)
    
    system_prompt = """Ты — Макс. Интеллектуальный напарник.
Отвечай кратко."""
    
    try:
        stream = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Привет!"}
            ],
            max_tokens=100,
            temperature=0.7,
            stream=True
        )
        
        chunks = []
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                chunks.append(content)
                print(content, end="", flush=True)
        
        print(f"\n  Total chunks: {len(chunks)}")
        print(f"  [OK] System prompt works!" if chunks else "  [FAIL] No chunks with system prompt!")
        
    except Exception as e:
        print(f"  [FAIL] Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct())
