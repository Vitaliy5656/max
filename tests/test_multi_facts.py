"""
Multi-fact extraction test
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.memory import MemoryManager


async def multi_fact_test():
    """Test JSON mode with complex multi-fact message"""
    
    print("=" * 70)
    print("MULTI-FACT EXTRACTION TEST")
    print("=" * 70)
    
    memory = MemoryManager()
    await memory.initialize()
    
    # Complex message with multiple facts across categories
    test_messages = [
        "Меня зовут Виталий, я из России, работаю над MAX AI, люблю программировать на Python.",
        "Мне 30 лет, живу в Москве, увлекаюсь астрономией и машинным обучением.",
        "Работаю разработчиком, знаю Python, JavaScript и TypeScript."
    ]
    
    conv = await memory.create_conversation()
    
    for i, msg in enumerate(test_messages, 1):
        print(f"\n{'=' * 70}")
        print(f"TEST {i}: {msg}")
        print('=' * 70)
        
        msg_id = await memory.add_message(conv.id, "user", msg)
        print(f"Message ID: {msg_id.id}")
        print("Waiting for extraction (3 seconds)...")
        await asyncio.sleep(3)
        
        # Query facts for this message
        query = "SELECT * FROM memory_facts WHERE source_message_id = ? ORDER BY id"
        async with memory._db.execute(query, (msg_id.id,)) as cursor:
            rows = await cursor.fetchall()
        
        print(f"\nExtracted {len(rows)} facts:")
        for row in rows:
            print(f"  [{row['category']}] {row['content']}")
    
    # Show all facts
    print(f"\n{'=' * 70}")
    print("ALL FACTS IN DATABASE")
    print('=' * 70)
    
    query = "SELECT * FROM memory_facts ORDER BY category, id"
    async with memory._db.execute(query) as cursor:
        all_facts = await cursor.fetchall()
    
    by_category = {}
    for fact in all_facts:
        by_category.setdefault(fact['category'], []).append(fact['content'])
    
    for category, facts in sorted(by_category.items()):
        print(f"\n{category.upper()}:")
        for fact in facts:
            print(f"  - {fact}")
    
    print(f"\n{'=' * 70}")
    print(f"[SUCCESS] Total facts extracted: {len(all_facts)}")
    print('=' * 70)
    
    await memory.close()


if __name__ == "__main__":
    asyncio.run(multi_fact_test())
