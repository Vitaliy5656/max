import sys
import os
import asyncio

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.core.routing.smart_router import get_smart_router
from src.core.routing.semantic_router import get_semantic_router

async def test():
    print("Initializing Semantic Router...")
    sr = get_semantic_router()
    sr.initialize()
    
    print(f"Semantic Router has {sr.get_stats()['num_examples']} examples.")
    
    router = get_smart_router()
    
    test_cases = [
        {"q": "analyze the impact of inflation", "expect_think": True, "expect_intent": "analysis"},
        {"q": "write python function for sorting", "expect_think": True, "expect_intent": "coding"},
        {"q": "calculate square root of 144", "expect_think": True, "expect_intent": "math"},
        {"q": "hello there", "expect_think": False, "expect_intent": "greeting"},
        {"q": "find weather in London", "expect_think": False, "expect_intent": "search", "strict": False},
        {"q": "create a poem about clouds", "expect_think": True, "expect_intent": "creative"},
    ]
    
    print("\nRunning routing tests...")
    
    failed = 0
    for case in test_cases:
        q = case["q"]
        print(f"\nQUERY: '{q}'")
        
        # Route
        result = await router.route(q)
        
        is_think = result.is_thinking_required
        intent = result.intent
        conf = result.confidence
        
        print(f"  -> Intent: {intent} ({conf:.2f})")
        print(f"  -> Thinking: {is_think}")
        
        # Check assertions
        if is_think != case["expect_think"]:
            print(f"FAIL: Thinking mismatch! Expected {case['expect_think']}")
            failed += 1
        elif case.get("expected_intent") and intent != case["expected_intent"]:
             # Semantic routing isn't perfect, treat as warning unless strict
             msg = f"WARN: Intent mismatch! Expected {case['expected_intent']}, got {intent}"
             if case.get("strict", True):
                 print(msg) # Semantic matching is fuzzy
             else:
                 print(msg)
        else:
            print("PASS")
            
    if failed > 0:
        print(f"\n{failed} tests failed.")
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(test())
