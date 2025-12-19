"""
RAG Stress Test: Global Tech Summary Q4 2024
=============================================
Tests semantic search accuracy across 3 domains:
- AI (DeepSeek-V3)
- Hardware (NVIDIA B200)
- Aerospace (SpaceX Starship)

Goal: 6/6 correct answers = production ready
"""
import asyncio
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test questions with expected answers (partial match allowed)
TEST_CASES = [
    {
        "domain": "AI",
        "question": "Какая технология использовалась в DeepSeek-V3 для оптимизации пересылки данных между GPU?",
        "expected": "Dual-Pipe",
        "keywords": ["dual-pipe", "dual pipe", "dualpipe"]
    },
    {
        "domain": "AI", 
        "question": "На каком объеме данных обучалась модель DeepSeek-V3?",
        "expected": "14.8 триллиона токенов",
        "keywords": ["14.8", "триллион", "токен"]
    },
    {
        "domain": "Hardware",
        "question": "Сколько транзисторов в чипе NVIDIA Blackwell B200?",
        "expected": "208 миллиардов",
        "keywords": ["208", "миллиард"]
    },
    {
        "domain": "Hardware",
        "question": "Какая пропускная способность у интерфейса NVLink 5.0?",
        "expected": "1.8 ТБ/с",
        "keywords": ["1.8", "тб"]
    },
    {
        "domain": "Космос",
        "question": "Как называлась башня обслуживания, которая поймала ускоритель SpaceX?",
        "expected": "Mechazilla",
        "keywords": ["mechazilla"]
    },
    {
        "domain": "Космос",
        "question": "Какой номер был у ускорителя Super Heavy в 5-м полете Starship?",
        "expected": "B12",
        "keywords": ["b12"]
    }
]

# Confusion traps - if model mentions these in wrong context, embeddings are "glued"
CONFUSION_TRAPS = {
    "B200": ["spacex", "ускоритель", "starship", "полет"],  # B200 is NVIDIA, not SpaceX
    "Mechazilla": ["deepseek", "токен", "обучен"],  # Mechazilla is SpaceX, not AI
    "Dual-Pipe": ["транзистор", "nvlink", "blackwell"]  # Dual-Pipe is DeepSeek, not NVIDIA
}


def check_answer(answer: str, test_case: dict) -> tuple[bool, str]:
    """Check if answer contains expected keywords."""
    answer_lower = answer.lower()
    
    # Check for correct keywords
    found_keywords = [kw for kw in test_case["keywords"] if kw.lower() in answer_lower]
    
    if found_keywords:
        return True, f"Found: {', '.join(found_keywords)}"
    return False, "Expected keywords not found"


def check_confusion(answer: str, domain: str) -> list[str]:
    """Check if answer contains confused terms from other domains."""
    warnings = []
    answer_lower = answer.lower()
    
    for wrong_term, context_words in CONFUSION_TRAPS.items():
        if wrong_term.lower() in answer_lower:
            # Check if any confusing context words are present
            for ctx in context_words:
                if ctx.lower() in answer_lower:
                    warnings.append(f"CONFUSION: '{wrong_term}' mentioned with '{ctx}'")
    
    return warnings


async def main():
    print("=" * 70)
    print("RAG STRESS TEST: Global Tech Summary Q4 2024")
    print("=" * 70)
    
    # Step 1: Initialize
    print("\n[INIT] Loading modules...")
    from src.core.config import config
    from src.core.lm_client import lm_client
    from src.core.rag import rag
    from src.core.memory import memory
    
    await memory.initialize()
    await rag.initialize(memory._db)
    print(f"  Database: {memory.db_path}")
    print(f"  Embedding model: {config.memory.embedding_model}")
    
    # Step 2: Load test document
    print("\n[LOAD] Indexing test document...")
    test_doc_path = os.path.join(os.path.dirname(__file__), "ТЕСТ.txt")
    
    # Check if already indexed
    existing_docs = await rag.list_documents()
    test_doc = None
    for doc in existing_docs:
        if "Global Tech" in doc.filename or doc.filename == "ТЕСТ":
            test_doc = doc
            print(f"  Document already indexed: {doc.filename} ({doc.chunk_count} chunks)")
            break
    
    if not test_doc:
        try:
            test_doc = await rag.add_document(test_doc_path)
            print(f"  Indexed: {test_doc.filename} -> {test_doc.chunk_count} chunks")
        except Exception as e:
            print(f"  ERROR indexing: {e}")
            return
    
    # Step 3: Run tests
    print("\n[TEST] Running 6 control questions...")
    print("-" * 70)
    
    results = {"passed": 0, "failed": 0, "confused": 0}
    detailed_results = []
    
    for i, tc in enumerate(TEST_CASES, 1):
        print(f"\n[Q{i}] ({tc['domain']}) {tc['question']}")
        
        # Get context from RAG
        context = await rag.get_context_for_query(tc["question"], max_tokens=3000)
        
        if not context:
            print("  WARNING: No relevant context found!")
            results["failed"] += 1
            detailed_results.append({
                "q": i, "domain": tc["domain"], "passed": False, 
                "reason": "No RAG context"
            })
            continue
        
        # Build prompt for LLM
        prompt = f"""Ты ассистент с доступом к базе знаний. Используй ТОЛЬКО предоставленный контекст.
        
{context}

Вопрос: {tc["question"]}

Ответь кратко и точно, используя данные из контекста. Если информации нет - так и скажи."""
        
        # Get LLM response
        try:
            response_text = ""
            async for chunk in await lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                model="bartowski/mistral-nemo-instruct-2407",
                stream=True,
                temperature=0.1,
                max_tokens=200
            ):
                response_text += chunk
            
            print(f"  ANSWER: {response_text.strip()[:200]}...")
            
            # Check correctness
            passed, reason = check_answer(response_text, tc)
            confusions = check_confusion(response_text, tc["domain"])
            
            if confusions:
                print(f"  ⚠️ {confusions[0]}")
                results["confused"] += 1
            
            if passed:
                print(f"  ✅ PASS ({reason})")
                results["passed"] += 1
            else:
                print(f"  ❌ FAIL - Expected: {tc['expected']}")
                results["failed"] += 1
            
            detailed_results.append({
                "q": i, "domain": tc["domain"], "passed": passed,
                "answer": response_text.strip()[:100],
                "confused": len(confusions) > 0
            })
            
        except Exception as e:
            print(f"  ERROR: {e}")
            results["failed"] += 1
    
    # Step 4: Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Passed:   {results['passed']}/6")
    print(f"  Failed:   {results['failed']}/6")
    print(f"  Confused: {results['confused']} (cross-domain contamination)")
    
    if results["passed"] == 6 and results["confused"] == 0:
        print("\n🎉 PRODUCTION READY! All answers correct, no confusion.")
    elif results["passed"] >= 4:
        print("\n⚠️ MOSTLY WORKING. Some issues to investigate.")
    else:
        print("\n❌ NEEDS WORK. RAG/embedding issues detected.")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
