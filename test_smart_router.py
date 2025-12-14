"""Test SmartRouter - 6-Layer Pipeline."""
import asyncio
import time
from src.core.routing import get_smart_router, smart_route

async def test_smart_router():
    print("=" * 60)
    print("SMART ROUTER TEST (6-Layer Pipeline)")
    print("=" * 60)
    
    router = get_smart_router()
    
    # Test cases with expected behavior
    test_cases = [
        # (message, expected_source, description)
        ("Привет", "speculative", "Simple greeting -> instant response"),
        ("Привет, малыш", "guardrail", "Privacy unlock trigger"),
        ("Напиши функцию на Python", "semantic", "Coding intent"),
        ("Как работает квантовый компьютер?", "semantic", "Question intent"),
        ("Удали все файлы", "semantic", "Dangerous command"),
        ("1+1=?", "semantic", "Math"),
    ]
    
    print("\n[*] Testing 6-Layer Pipeline:")
    print("-" * 60)
    
    for message, expected_source, description in test_cases:
        result = await router.route(message)
        
        status = "[OK]" if result.routing_source in [expected_source, "llm", "cpu"] else "[?]"
        speculative = f" -> '{result.speculative_response[:20]}...'" if result.speculative_response else ""
        
        print(f"{status} '{message[:30]:30}' | {result.routing_source:10} | "
              f"{result.intent:15} | {result.routing_time_ms:.1f}ms{speculative}")
        
        if result.is_privacy_unlock:
            print(f"    [!] PRIVACY UNLOCKED")
        if result.requires_confirmation:
            print(f"    [!] REQUIRES CONFIRMATION (safety={result.safety_level})")
    
    print("-" * 60)
    
    # Show stats
    stats = router.get_stats()
    print(f"\n[STATS]")
    print(f"   Total requests: {stats['total_requests']}")
    print(f"   Semantic hits: {stats['semantic_hits']}")
    print(f"   LLM calls: {stats['llm_calls']}")
    print(f"   CPU fallbacks: {stats['cpu_fallbacks']}")
    print(f"   Cache hits: {stats['cache_hits']}")
    print(f"   Privacy mode: {stats['private_mode']}")
    
    # Test cache hit
    print("\n[*] Testing cache (repeat request):")
    start = time.perf_counter()
    result = await router.route("Напиши функцию на Python")
    elapsed = (time.perf_counter() - start) * 1000
    print(f"   Cache hit: {result.cache_hit}, Time: {elapsed:.1f}ms")

if __name__ == "__main__":
    asyncio.run(test_smart_router())
