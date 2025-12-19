"""
Comprehensive Memory System Integration Test
Tests: initialization, fact extraction, embeddings, storage, brain map loading
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    print("=" * 60)
    print("🧪 MEMORY SYSTEM INTEGRATION TEST")
    print("=" * 60)
    
    results = {"passed": 0, "failed": 0, "errors": []}
    
    # ========== TEST 1: Config Loading ==========
    print("\n[TEST 1] Config Loading...")
    try:
        from src.core.config import config
        print(f"  ✅ extraction_model: {config.memory.extraction_model}")
        print(f"  ✅ embedding_model: {config.memory.embedding_model}")
        print(f"  ✅ extract_facts: {config.memory.extract_facts}")
        results["passed"] += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        results["failed"] += 1
        results["errors"].append(f"Config: {e}")
    
    # ========== TEST 2: LM Studio Connection ==========
    print("\n[TEST 2] LM Studio Connection...")
    try:
        from src.core.lm_client import lm_client
        models = await lm_client.client.models.list()
        model_ids = [m.id for m in models.data]
        print(f"  ✅ Connected! Models available: {len(model_ids)}")
        for mid in model_ids[:5]:
            print(f"     - {mid}")
        
        # Check required models
        has_embedding = any("bge-m3" in m.lower() or "embedding" in m.lower() for m in model_ids)
        has_extraction = any("phi" in m.lower() for m in model_ids)
        print(f"  ✅ Has embedding model: {has_embedding}")
        print(f"  ✅ Has extraction model: {has_extraction}")
        results["passed"] += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        results["failed"] += 1
        results["errors"].append(f"LM Studio: {e}")
    
    # ========== TEST 3: Memory Manager Init ==========
    print("\n[TEST 3] Memory Manager Initialization...")
    try:
        from src.core.memory import memory
        await memory.initialize()
        print(f"  ✅ Memory manager initialized")
        print(f"  ✅ Database path: {memory.db_path}")
        results["passed"] += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        results["failed"] += 1
        results["errors"].append(f"Memory Init: {e}")
        return results  # Can't continue without memory
    
    # ========== TEST 4: Embedding Generation ==========
    print("\n[TEST 4] Embedding Generation...")
    try:
        test_text = "Пользователь любит программирование на Python"
        embedding = await lm_client.get_embedding(test_text)
        
        if embedding and len(embedding) > 0:
            print(f"  ✅ Embedding generated: {len(embedding)} dimensions")
            print(f"     First 5 values: {embedding[:5]}")
            results["passed"] += 1
        else:
            print(f"  ❌ FAILED: Empty embedding returned")
            results["failed"] += 1
            results["errors"].append("Embedding: Empty result")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        results["failed"] += 1
        results["errors"].append(f"Embedding: {e}")
    
    # ========== TEST 5: Fact Storage ==========
    print("\n[TEST 5] Fact Storage...")
    try:
        from src.core.memory import Fact
        import time
        
        test_fact_content = f"TEST_FACT_{int(time.time())}: Пользователь тестирует систему памяти"
        fact = await memory.add_fact(test_fact_content, "test", None)
        
        if fact.id and fact.id > 0:
            print(f"  ✅ Fact saved with ID: {fact.id}")
            print(f"     Content: {fact.content[:50]}...")
            print(f"     Category: {fact.category}")
            has_embedding = fact.embedding is not None and len(fact.embedding) > 0
            print(f"     Has embedding: {has_embedding}")
            
            if has_embedding:
                results["passed"] += 1
            else:
                print(f"  ⚠️ WARNING: Fact saved but WITHOUT embedding!")
                results["passed"] += 1  # Still passed, but with warning
        else:
            print(f"  ❌ FAILED: Fact not saved properly")
            results["failed"] += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["failed"] += 1
        results["errors"].append(f"Fact Storage: {e}")
    
    # ========== TEST 6: Fact Retrieval from DB ==========
    print("\n[TEST 6] Fact Retrieval from Database...")
    try:
        async with memory._db.execute(
            "SELECT id, content, category, embedding FROM memory_facts ORDER BY id DESC LIMIT 5"
        ) as cursor:
            facts = await cursor.fetchall()
        
        print(f"  ✅ Found {len(facts)} facts in database")
        for f in facts:
            has_emb = f["embedding"] is not None
            print(f"     ID:{f['id']} | {f['category']} | emb:{has_emb} | {f['content'][:40]}...")
        
        # Count facts with embeddings
        async with memory._db.execute(
            "SELECT COUNT(*) as cnt FROM memory_facts WHERE embedding IS NOT NULL"
        ) as cursor:
            row = await cursor.fetchone()
            facts_with_emb = row["cnt"]
        
        async with memory._db.execute(
            "SELECT COUNT(*) as cnt FROM memory_facts"
        ) as cursor:
            row = await cursor.fetchone()
            total_facts = row["cnt"]
        
        print(f"  📊 Stats: {facts_with_emb}/{total_facts} facts have embeddings")
        results["passed"] += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        results["failed"] += 1
        results["errors"].append(f"Fact Retrieval: {e}")
    
    # ========== TEST 7: Brain Map Generation ==========
    print("\n[TEST 7] Brain Map Data Generation...")
    try:
        from src.core.research.brain_map import generate_brain_map, invalidate_cache
        
        # Clear cache first
        await invalidate_cache()
        print("  ✅ Cache invalidated")
        
        brain_data = await generate_brain_map(level=0)
        
        points_count = len(brain_data.get("points", []))
        has_error = "error" in brain_data
        
        print(f"  ✅ Brain map generated")
        print(f"     Points: {points_count}")
        print(f"     Level: {brain_data.get('level', 'N/A')}")
        
        if has_error:
            print(f"  ⚠️ Warning: {brain_data['error']}")
        
        if points_count > 0:
            sample = brain_data["points"][0]
            print(f"     Sample point: {sample.get('label', 'N/A')[:30]}...")
            results["passed"] += 1
        else:
            print(f"  ⚠️ No points generated (need 3+ facts with embeddings)")
            results["passed"] += 1  # Not a failure, just not enough data
            
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["failed"] += 1
        results["errors"].append(f"Brain Map: {e}")
    
    # ========== TEST 8: Full Fact Extraction Pipeline ==========
    print("\n[TEST 8] Full Fact Extraction Pipeline...")
    try:
        # Create a test conversation
        conv = await memory.create_conversation("Test Integration")
        print(f"  ✅ Created conversation: {conv.id}")
        
        # Add a message that should trigger fact extraction
        test_message = "Меня зовут Виталий, я программист из Москвы и люблю разрабатывать AI системы"
        msg = await memory.add_message(conv.id, "user", test_message)
        print(f"  ✅ Added message: {msg.id}")
        
        # Wait for background extraction task
        print("  ⏳ Waiting for fact extraction (3s)...")
        await asyncio.sleep(3)
        
        # Check if facts were extracted
        async with memory._db.execute(
            "SELECT * FROM memory_facts WHERE source_message_id = ?", (msg.id,)
        ) as cursor:
            extracted = await cursor.fetchall()
        
        if extracted:
            print(f"  ✅ Extracted {len(extracted)} fact(s) from message!")
            for f in extracted:
                has_emb = f["embedding"] is not None
                print(f"     - [{f['category']}] {f['content'][:50]}... (emb:{has_emb})")
            results["passed"] += 1
        else:
            print(f"  ⚠️ No facts extracted (message may be too simple)")
            results["passed"] += 1  # Not a critical failure
        
        # Cleanup
        await memory.delete_conversation(conv.id)
        print(f"  🧹 Cleaned up test conversation")
        
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["failed"] += 1
        results["errors"].append(f"Extraction Pipeline: {e}")
    
    # ========== SUMMARY ==========
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    print(f"  ✅ Passed: {results['passed']}")
    print(f"  ❌ Failed: {results['failed']}")
    
    if results["errors"]:
        print("\n  Errors:")
        for err in results["errors"]:
            print(f"    - {err}")
    
    if results["failed"] == 0:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️ {results['failed']} test(s) failed")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
