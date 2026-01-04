import sqlite3

conn = sqlite3.connect('data/max.db')

# List all tables
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print("Tables in database:", tables)

# Check each table for content
for table in tables:
    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  {table}: {count} rows")
    
    # If it's a facts table, show some content
    if 'fact' in table.lower() or 'knowledge' in table.lower() or 'memory' in table.lower():
        cursor = conn.execute(f"SELECT * FROM {table} LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(f"    {row}")

conn.close()
