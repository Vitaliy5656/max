import asyncio
import aiosqlite

async def show_facts():
    db = await aiosqlite.connect("data/max.db")
    db.row_factory = aiosqlite.Row
    cursor = await db.execute("SELECT id, content, category FROM memory_facts ORDER BY id DESC LIMIT 20")
    rows = await cursor.fetchall()
    
    print("=" * 60)
    print("       ПОСЛЕДНИЕ 20 СОХРАНЁННЫХ ФАКТОВ")
    print("=" * 60)
    
    for row in rows:
        content = row["content"]
        # Truncate for display
        if len(content) > 200:
            content = content[:200] + "..."
        print(f"\n[ID: {row['id']}] ({row['category']})")
        print(f"  {content}")
    
    # Count total
    cursor = await db.execute("SELECT COUNT(*) FROM memory_facts")
    count = (await cursor.fetchone())[0]
    print(f"\n{'=' * 60}")
    print(f"ВСЕГО ФАКТОВ В БАЗЕ: {count}")
    
    await db.close()

asyncio.run(show_facts())
