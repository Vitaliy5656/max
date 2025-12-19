"""Quick test for LLM Router."""
import asyncio
from src.core.routing import llm_router

async def test():
    tests = [
        "Привет!",
        "Напиши функцию на Python для сортировки списка",
        "Как работает квантовый компьютер?",
        "Найди последние новости о SpaceX",
        "Объясни пошагово как решить уравнение 2x + 5 = 15"
    ]
    
    print("LLM Router Tests (Phi-3.5-mini)")
    print("=" * 60)
    
    for msg in tests:
        result = await llm_router.route(msg)
        print(f"\nMessage: {msg[:50]}...")
        print(f"  Intent: {result.intent.value}")
        print(f"  Complexity: {result.complexity.value}")
        print(f"  Mode: {result.suggested_mode}")
        print(f"  Needs Search: {result.needs_search}")
        print(f"  Needs Code: {result.needs_code}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Reasoning: {result.reasoning}")
    
    print("\n" + "=" * 60)
    print(f"Stats: {llm_router.get_stats()}")

if __name__ == "__main__":
    asyncio.run(test())
