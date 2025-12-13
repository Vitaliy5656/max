"""Quick test to check memory database facts."""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.memory import MemoryManager
from src.core.config import config

async def test_facts():
    print("=" * 60)
    print("Memory Facts Database Test")
    print("=" * 60)
    
    # Initialize memory
    print("\n[1/3] Initializing memory manager...")
    memory = MemoryManager()
    await memory.initialize()
    print("✅ Memory initialized")
    
    # Check facts
    print("\n[2/3] Querying facts from database...")
    async with memory._db.execute("SELECT COUNT(*) FROM memory_facts") as cursor:
        count = (await cursor.fetchone())[0]
        print(f"Total facts in DB: {count}")
    
    if count > 0:
        async with memory._db.execute(
            "SELECT id, content, category FROM memory_facts ORDER BY created_at DESC LIMIT 10"
        ) as cursor:
            facts = await cursor.fetchall()
            print("\nRecent facts:")
            for row in facts:
                print(f"  [{row[0]}] ({row[2]}) {row[1]}")
    else:
        print("⚠️ No facts found in database!")
    
    # Try to add a test fact
    print("\n[3/3] Testing fact addition...")
    try:
        fact = await memory.add_fact("Test user name is Виталий", "personal", None)
        print(f"✅ Test fact added (ID: {fact.id})")
        
        # Verify it was saved
        async with memory._db.execute(
            "SELECT content FROM memory_facts WHERE id = ?", (fact.id,)
        ) as cursor:
            result = await cursor.fetchone()
            if result:
                print(f"✅ Verified in DB: {result[0]}")
            else:
                print("❌ Fact not found in DB!")
    except Exception as e:
        print(f"❌ Failed to add fact: {e}")
    
    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_facts())
