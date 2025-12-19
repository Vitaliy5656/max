"""
Test script for LM Studio JSON mode fact extraction

Tests the new JSON Schema-based fact extraction with GBNF grammar enforcement.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.memory import MemoryManager


async def test_fact_extraction():
    """Test fact extraction with user's original example"""
    
    print("=" * 60)
    print("Testing LM Studio JSON Mode Fact Extraction")
    print("=" * 60)
    
    # Initialize
    memory = MemoryManager()
    await memory.initialize()
    
    # Create test conversation
    conversation = await memory.create_conversation()
    conv_id = conversation.id
    print(f"\n[OK] Created test conversation: {conv_id}")
    
    # Test case 1: Original user example (astronomy bug)
    print("\n" + "=" * 60)
    print("TEST 1: Astronomy Example (Original Bug)")
    print("=" * 60)
    
    msg1 = "Я люблю астрономию"
    msg_id_1 = await memory.add_message(conv_id, "user", msg1)
    print(f"\n[MSG] Added message: \"{msg1}\"")
    print(f"[WAIT] Extracting facts...")
    
    # Wait a bit for background task
    await asyncio.sleep(3)
    
    # Check extracted facts
    facts1 = await memory.get_all_facts()
    print(f"\n[OK] Facts extracted: {len(facts1)}")
    for fact in facts1:
        print(f"   [{fact.category}] {fact.content}")
    
    # Test case 2: Complex multi-fact message
    print("\n" + "=" * 60)
    print("TEST 2: Complex Multi-Fact Message")
    print("=" * 60)
    
    msg2 = "Меня зовут Виталий. Я из России. Работаю над MAX AI assistant. Люблю программировать на Python."
    msg_id_2 = await memory.add_message(conv_id, "user", msg2)
    print(f"\n[MSG] Added message: \"{msg2}\"")
    print(f"[WAIT] Extracting facts...")
    
    await asyncio.sleep(3)
    
    facts2 = await memory.get_all_facts()
    new_facts = [f for f in facts2 if f.id not in [fact.id for fact in facts1]]
    print(f"\n[OK] New facts extracted: {len(new_facts)}")
    for fact in new_facts:
        print(f"   [{fact.category}] {fact.content}")
    
    # Test case 3: No facts
    print("\n" + "=" * 60)
    print("TEST 3: Message with No Facts")
    print("=" * 60)
    
    msg3 = "Привет, как дела?"
    msg_id_3 = await memory.add_message(conv_id, "user", msg3)
    print(f"\n[MSG] Added message: \"{msg3}\"")
    print(f"[WAIT] Extracting facts...")
    
    await asyncio.sleep(3)
    
    facts3 = await memory.get_all_facts()
    newest_facts = [f for f in facts3 if f.id not in [fact.id for fact in facts2]]
    print(f"\n[OK] New facts: {len(newest_facts)} (should be 0)")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_facts = await memory.get_all_facts()
    by_category = {}
    for fact in all_facts:
        by_category.setdefault(fact.category, []).append(fact.content)
    
    print(f"\n[STATS] Total facts extracted: {len(all_facts)}")
    for category, facts in by_category.items():
        print(f"\n{category.upper()}:")
        for fact in facts:
            print(f"  - {fact}")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] ALL TESTS COMPLETED")
    print("=" * 60)
    
    await memory.close()


if __name__ == "__main__":
    asyncio.run(test_fact_extraction())
