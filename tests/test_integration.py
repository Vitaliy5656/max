"""
Integration Test for SmartRouter System.

Tests all components working together:
    - Semantic Router
    - SmartRouter (6-Layer Pipeline)
    - Privacy Guard
    - Prompt Library
    - Entity Extraction
    - Observability
    - Auto-Learning
"""
import asyncio
import time
from dataclasses import asdict

print("=" * 70)
print("SMARTROUTER INTEGRATION TEST")
print("=" * 70)


async def test_all():
    errors = []
    passed = 0
    
    # =========================================
    # 1. Import Test
    # =========================================
    print("\n[1] IMPORTS...")
    try:
        from src.core.routing import (
            get_smart_router, get_semantic_router, get_privacy_guard,
            get_routing_observer, get_auto_learner, initialize_auto_learning
        )
        from src.core.prompts import get_prompt_library
        from src.core.routing.entity_extractor import detect_topic, extract_entities
        print("    [OK] All imports successful")
        passed += 1
    except Exception as e:
        errors.append(f"Import: {e}")
        print(f"    [FAIL] {e}")
        return
    
    # =========================================
    # 2. Initialization Test
    # =========================================
    print("\n[2] INITIALIZATION...")
    try:
        await initialize_auto_learning()
        
        router = get_smart_router()
        semantic = get_semantic_router()
        privacy = get_privacy_guard()
        observer = get_routing_observer()
        learner = get_auto_learner()
        prompts = get_prompt_library()
        
        print(f"    [OK] SmartRouter ready")
        print(f"    [OK] SemanticRouter: {len(semantic._examples)} examples")
        print(f"    [OK] PromptLibrary: {len(prompts.list_all())} prompts")
        print(f"    [OK] Privacy: {'UNLOCKED' if privacy.is_unlocked() else 'LOCKED'}")
        passed += 1
    except Exception as e:
        errors.append(f"Init: {e}")
        print(f"    [FAIL] {e}")
    
    # =========================================
    # 3. Speculative Response Test (Greeting)
    # =========================================
    print("\n[3] SPECULATIVE RESPONSE...")
    try:
        start = time.perf_counter()
        result = await router.route("Привет")
        elapsed = (time.perf_counter() - start) * 1000
        
        assert result.intent == "greeting", f"Expected greeting, got {result.intent}"
        assert result.routing_source == "speculative", f"Expected speculative, got {result.routing_source}"
        assert result.speculative_response is not None, "No speculative response"
        
        print(f"    [OK] Intent: {result.intent}")
        print(f"    [OK] Source: {result.routing_source}")
        print(f"    [OK] Response: '{result.speculative_response[:30]}...'")
        print(f"    [OK] Time: {elapsed:.2f}ms")
        passed += 1
    except Exception as e:
        errors.append(f"Speculative: {e}")
        print(f"    [FAIL] {e}")
    
    # =========================================
    # 4. Privacy Unlock Test
    # =========================================
    print("\n[4] PRIVACY UNLOCK...")
    try:
        result = await router.route("Привет, малыш")
        
        assert result.is_privacy_unlock == True, "Privacy not unlocked"
        assert router.is_private_mode() == True, "Private mode not active"
        
        print(f"    [OK] Privacy unlocked")
        print(f"    [OK] Response: '{result.speculative_response[:40]}...'")
        passed += 1
    except Exception as e:
        errors.append(f"Privacy: {e}")
        print(f"    [FAIL] {e}")
    
    # =========================================
    # 5. Semantic Router Test
    # =========================================
    print("\n[5] SEMANTIC ROUTING...")
    try:
        result = await router.route("Напиши функцию на Python для сортировки")
        
        assert result.intent == "coding", f"Expected coding, got {result.intent}"
        assert result.routing_source == "semantic", f"Expected semantic, got {result.routing_source}"
        
        print(f"    [OK] Intent: {result.intent}")
        print(f"    [OK] Source: {result.routing_source}")
        print(f"    [OK] Confidence: {result.confidence:.2f}")
        print(f"    [OK] Time: {result.routing_time_ms:.1f}ms")
        passed += 1
    except Exception as e:
        errors.append(f"Semantic: {e}")
        print(f"    [FAIL] {e}")
    
    # =========================================
    # 6. Prompt Selection Test
    # =========================================
    print("\n[6] PROMPT SELECTION...")
    try:
        result = await router.route("Напиши код на Python")
        
        assert result.prompt_name is not None, "No prompt selected"
        assert result.system_prompt is not None, "No system prompt"
        
        print(f"    [OK] Prompt: {result.prompt_name}")
        print(f"    [OK] System prompt: {len(result.system_prompt)} chars")
        passed += 1
    except Exception as e:
        errors.append(f"Prompt: {e}")
        print(f"    [FAIL] {e}")
    
    # =========================================
    # 7. Topic Detection Test
    # =========================================
    print("\n[7] TOPIC DETECTION...")
    try:
        topics = {
            "Какая звезда самая яркая?": "astronomy",
            "Сколько карат в бриллианте?": "jewelry",
            "Как залить фундамент?": "construction",
        }
        
        for msg, expected in topics.items():
            topic = detect_topic(msg)
            assert topic == expected, f"Expected {expected}, got {topic}"
            print(f"    [OK] '{msg[:25]}...' -> {topic}")
        passed += 1
    except Exception as e:
        errors.append(f"Topic: {e}")
        print(f"    [FAIL] {e}")
    
    # =========================================
    # 8. Entity Extraction Test
    # =========================================
    print("\n[8] ENTITY EXTRACTION...")
    try:
        result = extract_entities("Позвони на +7 999 123-45-67 или напиши test@mail.ru")
        
        emails = result.get_by_type(result.entities[0].type.__class__.EMAIL)
        phones = [e for e in result.entities if e.type.value == "phone"]
        
        assert len(emails) > 0 or len(phones) > 0, "No entities found"
        
        print(f"    [OK] Found {len(result.entities)} entities")
        print(f"    [OK] Is question: {result.has_question}")
        print(f"    [OK] Language: {result.language}")
        passed += 1
    except Exception as e:
        errors.append(f"Entity: {e}")
        print(f"    [FAIL] {e}")
    
    # =========================================
    # 9. Cache Test
    # =========================================
    print("\n[9] CACHE TEST...")
    try:
        # First call
        result1 = await router.route("Объясни квантовую механику")
        
        # Second call (should be cached)
        start = time.perf_counter()
        result2 = await router.route("Объясни квантовую механику")
        elapsed = (time.perf_counter() - start) * 1000
        
        assert result2.cache_hit == True, "Cache miss on second call"
        
        print(f"    [OK] First call: {result1.routing_time_ms:.1f}ms")
        print(f"    [OK] Cache hit: {result2.cache_hit}")
        print(f"    [OK] Cached call: {elapsed:.2f}ms")
        passed += 1
    except Exception as e:
        errors.append(f"Cache: {e}")
        print(f"    [FAIL] {e}")
    
    # =========================================
    # 10. Observer Stats Test
    # =========================================
    print("\n[10] OBSERVER STATS...")
    try:
        stats = observer.get_stats()
        router_stats = router.get_stats()
        
        assert stats["total_requests"] > 0, "No requests recorded"
        
        print(f"    [OK] Total requests: {stats['total_requests']}")
        print(f"    [OK] Semantic hits: {router_stats['semantic_hits']}")
        print(f"    [OK] Cache hits: {router_stats['cache_hits']}")
        print(f"    [OK] Avg latency: {stats.get('avg_latency_ms', 0):.1f}ms")
        passed += 1
    except Exception as e:
        errors.append(f"Observer: {e}")
        print(f"    [FAIL] {e}")
    
    # =========================================
    # Summary
    # =========================================
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/10 tests passed")
    
    if errors:
        print("\nERRORS:")
        for err in errors:
            print(f"  - {err}")
    else:
        print("\n[SUCCESS] All tests passed!")
    
    print("=" * 70)
    
    return passed == 10


if __name__ == "__main__":
    success = asyncio.run(test_all())
    exit(0 if success else 1)
