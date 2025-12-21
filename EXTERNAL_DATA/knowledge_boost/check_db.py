import sqlite3
import os
import sys
from pathlib import Path

# Force UTF-8 output for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def get_db_path():
    if os.name == 'nt':
        base = Path(os.environ.get('APPDATA', Path.home()))
    else:
        base = Path.home() / '.local' / 'share'
    return base / 'MAX_AI' / 'max.db'

def main():
    db_path = get_db_path()
    print(f"\n--- DATABASE CHECK ---")
    print(f"Target: {db_path}")
    
    if not db_path.exists():
        print("ERROR: Database file not found!")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Count totals
        cursor.execute("SELECT category, count(*) FROM memory_facts GROUP BY category")
        rows = cursor.fetchall()
        
        if not rows:
            print("WARN: Table 'memory_facts' is empty or doesn't exist.")
        else:
            print(f"\nFACTS BY CATEGORY:")
            total = 0
            for cat, count in rows:
                print(f"   - {cat:<12}: {count} items")
                total += count
            print(f"   -------------------------")
            print(f"   TOTAL        : {total} facts")

        # Show sample per category
        print(f"\nEXAMPLES BY CATEGORY:")
        # SQLite trick to get one row per group
        cursor.execute("SELECT category, content FROM memory_facts GROUP BY category")
        for cat, content in cursor.fetchall():
            preview = content[:300].replace('\n', ' ') 
            print(f"   [{cat}] {preview}")

        conn.close()
    except Exception as e:
        print(f"ERROR reading database: {e}")

if __name__ == "__main__":
    main()
