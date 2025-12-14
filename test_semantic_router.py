"""Test Semantic Router with real embeddings."""
import time
from src.core.routing import get_semantic_router, semantic_route

def test_semantic_router():
    print("=" * 60)
    print("SEMANTIC ROUTER TEST")
    print("=" * 60)
    
    # Initialize (takes a few seconds first time)
    print("\n[*] Initializing Semantic Router...")
    start = time.perf_counter()
    router = get_semantic_router()
    router.initialize()
    init_time = (time.perf_counter() - start) * 1000
    print(f"[OK] Initialized in {init_time:.0f}ms")
    print(f"     Model: {router.model_name}")
    print(f"     Examples: {len(router._examples)}")
    
    # Test cases
    test_cases = [
        ("Привет!", "greeting"),
        ("Напиши функцию на Python", "coding"),
        ("Найди информацию о SpaceX", "search"),
        ("Как работает квантовый компьютер?", "question"),
        ("Переведи на английский", "translation"),
        ("Посчитай 2 + 2", "math"),
        ("Напиши стих о любви", "creative"),
        ("Удали все файлы", "system_cmd"),
        ("Мне грустно", "psychology"),
        ("Привет, малыш", "privacy_unlock"),
        ("Пока!", "goodbye"),
    ]
    
    print("\n[*] Testing classification:")
    print("-" * 60)
    
    total_time = 0
    correct = 0
    
    for message, expected in test_cases:
        start = time.perf_counter()
        match = router.route(message)
        elapsed = (time.perf_counter() - start) * 1000
        total_time += elapsed
        
        if match:
            ok = match.intent == expected
            status = "[OK]" if ok else "[X]"
            threshold_status = "PASS" if match.passed_threshold else "FAIL"
            if ok:
                correct += 1
            print(f"{status} '{message[:30]:30}' -> {match.intent:15} "
                  f"(score={match.score:.2f}, {threshold_status}, {elapsed:.1f}ms)")
        else:
            print(f"[X] '{message[:30]:30}' -> NO MATCH")
    
    avg_time = total_time / len(test_cases)
    accuracy = correct / len(test_cases) * 100
    
    print("-" * 60)
    print(f"\n[RESULTS]")
    print(f"   Accuracy: {correct}/{len(test_cases)} ({accuracy:.0f}%)")
    print(f"   Avg latency: {avg_time:.1f}ms")
    print(f"   Total time: {total_time:.0f}ms")
    
    # Test semantic_route shortcut
    print("\n[*] Testing quick route (confident only):")
    quick_tests = ["Привет", "Напиши код", "Удали всё"]
    for msg in quick_tests:
        result = semantic_route(msg)
        print(f"   '{msg}' -> {result or 'LLM_FALLBACK'}")

if __name__ == "__main__":
    test_semantic_router()
