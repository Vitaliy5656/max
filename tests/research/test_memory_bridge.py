
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.tools import tools
from src.core.memory import memory
import aiosqlite

async def test_memory_bridge():
    print("Testing direct save_knowledge tool execution...")
    
    # Initialize Memory
    db_path = Path("data/test_audit_v2.db") # reuse the one from auto test
    if not db_path.exists():
        print("Creating new DB...")
        
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    memory._db = db # Manual injection because tools.py uses global memory
    
    # 1. Save Fact
    fact_content = "Python 3.13 was released in October 2024 (Simulated Fact)"
    print(f"Saving: {fact_content}")
    
    result = await tools.execute("save_knowledge", {"content": fact_content, "category": "research", "tags": "python,release"})
    print(f"Tool Result: {result}")
    
    # 2. Verify in DB
    async with db.execute("SELECT * FROM memory_facts WHERE content LIKE '%Python 3.13%'") as c:
        row = await c.fetchone()
        
    if row:
        print(f"\n[OK] Found in memory: ID={row['id']}, Content='{row['content']}'")
    else:
        print("\n[FAIL] Fact not found in DB!")

    await db.close()

if __name__ == "__main__":
    asyncio.run(test_memory_bridge())
