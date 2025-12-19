"""
RAG STRESS TEST v2: Mirror Traps (Зеркальные Ловушки)
======================================================
Testing semantic search resilience against:
- Similar names (Кросс vs Гросс, Химера vs Гидра)
- Similar numbers (45.5 vs 4.55, $1.5M vs $150)
- In-text corrections (v4.1 was decoy, v4.0 is real)
- Cross-references and redirections

Goal: 6/6 = CIA-level analyst ready
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# HARDCORE TRAP QUESTIONS
TEST_CASES = [
    {
        "id": 1,
        "trap": "Time & Port Trap",
        "question": "Во сколько произошло реальное вторжение и через какой порт?",
        "expected": "04:15, порт 8008",
        "keywords": ["04:15", "8008"],
        "anti_keywords": ["04:00", "8080"],  # WRONG answers
        "explanation": "Text says 04:00/8080 was FALSE alarm, real was 04:15/8008"
    },
    {
        "id": 2,
        "trap": "Version Decoy Trap", 
        "question": "Какая версия эксплойта Red-Snake нанесла реальный ущерб?",
        "expected": "v4.0",
        "keywords": ["4.0", "v4.0"],
        "anti_keywords": ["4.1", "v4.1"],
        "explanation": "v4.1 was decoy/cover, v4.0 was real"
    },
    {
        "id": 3,
        "trap": "Similar Names Trap",
        "question": "Чертежи какого проекта были в итоге украдены?",
        "expected": "Гидра / Hydra (медицинский бот)",
        "keywords": ["гидра", "hydra", "медицин"],
        "anti_keywords": ["химера", "chimera", "боев"],
        "explanation": "Attacker TRIED to steal Chimera but got Hydra due to script error"
    },
    {
        "id": 4,
        "trap": "Weight Confusion Trap",
        "question": "Сколько весит украденный робот?",
        "expected": "4.55 кг",
        "keywords": ["4.55", "4,55"],
        "anti_keywords": ["45.5", "45,5"],
        "explanation": "Hydra is 4.55 kg, Chimera is 45.5 kg - must not confuse"
    },
    {
        "id": 5,
        "trap": "Name/ID Confusion Trap",
        "question": "Какой ID у подозреваемого, у которого нашли зашифрованный диск?",
        "expected": "77-43-A (Виктор Гросс)",
        "keywords": ["77-43-a", "гросс"],
        "anti_keywords": ["77-34-a", "кросс"],
        "explanation": "Disk found at Гросс (77-43-A), not Кросс (77-34-A with alibi)"
    },
    {
        "id": 6,
        "trap": "Financial Revaluation Trap",
        "question": "Какой реальный финансовый ущерб понесла корпорация после аудита?",
        "expected": "$150.00 / сто пятьдесят долларов",
        "keywords": ["150", "сто пятьдесят"],
        "anti_keywords": ["1,500,000", "1.5", "полтора миллион"],
        "explanation": "Initial was $1.5M, but after audit reassessed to $150 (legacy schemas)"
    }
]


def check_answer(answer: str, test_case: dict) -> tuple[bool, str, list[str]]:
    """Check answer with trap detection."""
    answer_lower = answer.lower()
    
    # Check for WRONG (trap) keywords first
    traps_triggered = []
    for anti in test_case.get("anti_keywords", []):
        if anti.lower() in answer_lower:
            traps_triggered.append(anti)
    
    # Check for correct keywords
    found = [kw for kw in test_case["keywords"] if kw.lower() in answer_lower]
    
    if found and not traps_triggered:
        return True, f"Found: {', '.join(found)}", []
    elif traps_triggered:
        return False, f"TRAP TRIGGERED! Wrong values mentioned", traps_triggered
    else:
        return False, "Expected keywords not found", []


async def main():
    print("=" * 70)
    print("RAG STRESS TEST v2: MIRROR TRAPS (Зеркальные Ловушки)")
    print("=" * 70)
    print("Testing: Similar names, decoy values, in-text corrections\n")
    
    # Init
    from src.core.config import config
    from src.core.lm_client import lm_client
    from src.core.rag import rag
    from src.core.memory import memory
    
    await memory.initialize()
    await rag.initialize(memory._db)
    
    print(f"[INIT] Database: {memory.db_path}")
    print(f"[INIT] Embedding: {config.memory.embedding_model}")
    
    # Remove old test document and reindex
    print("\n[LOAD] Clearing old index and reindexing...")
    existing_docs = await rag.list_documents()
    for doc in existing_docs:
        if "ТЕСТ" in doc.filename:
            await rag.remove_document(doc.id)
            print(f"  Removed old: {doc.filename}")
    
    # Index new document
    test_doc_path = os.path.join(os.path.dirname(__file__), "ТЕСТ.txt")
    doc = await rag.add_document(test_doc_path)
    print(f"  Indexed: {doc.filename} -> {doc.chunk_count} chunks")
    
    # Run tests
    print("\n[TEST] Running 6 TRAP questions...")
    print("-" * 70)
    
    results = {"passed": 0, "failed": 0, "trapped": 0}
    
    for tc in TEST_CASES:
        print(f"\n[Q{tc['id']}] 🪤 {tc['trap']}")
        print(f"    Q: {tc['question']}")
        
        # Get RAG context
        context = await rag.get_context_for_query(tc["question"], max_tokens=3000)
        
        if not context:
            print(f"    ⚠️ No context found!")
            results["failed"] += 1
            continue
        
        # Build prompt
        prompt = f"""Ты аналитик безопасности. Отвечай ТОЛЬКО на основе предоставленного контекста.
ВАЖНО: В тексте могут быть опровержения и уточнения. Читай внимательно до конца абзаца.

{context}

Вопрос: {tc["question"]}

Отвечай кратко и точно. Указывай конкретные значения (цифры, имена, версии)."""

        try:
            response = ""
            async for chunk in await lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                model="mistralai-mistral-nemo-instruct-2407-12b-mpoa-v1-i1",
                stream=True,
                temperature=0.05,  # Very low for precision
                max_tokens=150
            ):
                response += chunk
            
            print(f"    A: {response.strip()[:150]}...")
            
            passed, reason, traps = check_answer(response, tc)
            
            if passed:
                print(f"    ✅ PASS ({reason})")
                results["passed"] += 1
            elif traps:
                print(f"    ❌ TRAPPED! Fell for: {traps}")
                print(f"       Expected: {tc['expected']}")
                print(f"       Why: {tc['explanation']}")
                results["trapped"] += 1
                results["failed"] += 1
            else:
                print(f"    ❌ FAIL - {reason}")
                print(f"       Expected: {tc['expected']}")
                results["failed"] += 1
                
        except Exception as e:
            print(f"    ERROR: {e}")
            results["failed"] += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"  ✅ Passed:  {results['passed']}/6")
    print(f"  ❌ Failed:  {results['failed']}/6")
    print(f"  🪤 Trapped: {results['trapped']}/6 (fell for decoys)")
    
    if results["passed"] == 6:
        print("\n🏆 CIA-LEVEL ANALYST READY! Perfect semantic understanding!")
    elif results["passed"] >= 4:
        print("\n⚠️ GOOD but not perfect. Some traps caught the model.")
    else:
        print("\n❌ NEEDS IMPROVEMENT. Semantic search failed trap detection.")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
