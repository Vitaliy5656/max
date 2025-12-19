"""
Simple test for JSON mode fact extraction
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.memory import MemoryManager


async def simple_test():
    """Test JSON mode with direct database query"""
    
    print("=" * 60)
    print("Testing JSON Mode Fact Extraction")
    print("=" * 60)
    
    memory = MemoryManager()
    await memory.initialize()
    
    # Test message (astronomy bug example)
    test_message = "Я люблю астрономию"
    
    print(f"\nTest message: \"{test_message}\"")
    print("Extracting facts with JSON mode...")
    
    # Create conversation and add message
    conv = await memory.create_conversation()
    msg_id = await memory.add_message(conv.id, "user", test_message)
    
    print(f"Message ID: {msg_id}")
    print("Waiting for extraction (5 seconds)...")
    await asyncio.sleep(5)
    
    # Query database directly
    query = "SELECT * FROM memory_facts"
    async with memory._db.execute(query) as cursor:
        rows = await cursor.fetchall()
    
    print(f"\n--- Results ---")
    print(f"Total facts in database: {len(rows)}")
    
    for row in rows:
        print(f"\n  ID: {row['id']}")
        print(f"  Category: {row['category']}")
        print(f"  Content: {row['content']}")
        print(f"  Source message: {row['source_message_id']}")
    
    if len(rows) > 0:
        print(f"\n[SUCCESS] Facts were extracted!")
    else:
        print(f"\n[FAIL] No facts extracted - check logs")
    
    await memory.close()


if __name__ == "__main__":
    asyncio.run(simple_test())
