import os
import sys
import json
import sqlite3
import asyncio
import csv
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
sys.path.append(os.getcwd())

try:
    from src.core.lm_client import lm_client
    from src.core.paths import get_db_path
    from src.core.logger import log
except Exception as e:
    print(f"INFO: Could not import project modules ({e}). Falling back to local paths.")
    def get_db_path():
        if os.name == 'nt':
            base = Path(os.environ.get('APPDATA', Path.home()))
        else:
            base = Path.home() / '.local' / 'share'
        return base / 'MAX_AI' / 'max.db'

class BoostImporter:
    def __init__(self, db_path):
        self.db_path = db_path
        print(f"INFO: Connecting to database: {self.db_path}")
        # Ensure parent dir exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                embedding BLOB,
                confidence REAL DEFAULT 1.0,
                created_at TEXT
            )
        """)
        # Create index on category for speed
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_category ON memory_facts(category)")
        self.conn.commit()

    async def add_fact(self, content, category="general"):
        cursor = self.conn.cursor()
        
        # Check duplicate
        cursor.execute("SELECT id FROM memory_facts WHERE content = ?", (content,))
        if cursor.fetchone():
            return
            
        # Get embedding if possible (async placeholder)
        embedding_blob = None
        # try:
        #     embedding = await lm_client.get_embedding(content)
        #     if embedding:
        #         embedding_blob = json.dumps(embedding).encode()
        # except Exception as e:
        #     pass
            
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO memory_facts (content, category, embedding, confidence, created_at) VALUES (?, ?, ?, ?, ?)",
            (content, category, embedding_blob, 1.0, now)
        )
        self.conn.commit()

    async def import_logic(self, file_path, limit=50):
        print(f"LOGIC: Importing from {file_path}...")
        if not os.path.exists(file_path): return
        # Logic for ConceptNet CSV
        with open(file_path, 'r', encoding='utf-8') as f:
            count = 0
            for line in f:
                if count >= limit: break
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    rel = parts[1].split('/')[-1]
                    start = parts[2].split('/')[-1]
                    end = parts[3].split('/')[-1]
                    fact = f"Concept: {start} {rel} {end}"
                    await self.add_fact(fact, category="logic")
                    count += 1

    async def import_coding(self, file_path, limit=50):
        print(f"CODING: Importing from {file_path}...")
        if not os.path.exists(file_path): return
        with open(file_path, 'r', encoding='utf-8') as f:
            count = 0
            for line in f:
                if count >= limit: break
                try:
                    data = json.loads(line)
                    title = data.get('title', 'No Title')
                    desc = data.get('description', '')
                    fact = f"Coding Problem: {title}\nSummary: {desc[:200]}..."
                    await self.add_fact(fact, category="coding")
                    count += 1
                except: continue

    async def import_russian(self, file_path, limit=50):
        print(f"RU_SOUL: Importing from {file_path}...")
        if not os.path.exists(file_path): return
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            # Split by paragraphs or sentences
            paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
            count = 0
            for p in paragraphs:
                if count >= limit: break
                await self.add_fact(p, category="russian")
                count += 1

    async def import_literature(self, file_path, limit=50):
        print(f"LITERATURE: Importing from {file_path}...")
        if not os.path.exists(file_path): return
        with open(file_path, 'r', encoding='utf-8') as f:
            count = 0
            for line in f:
                if count >= limit: break
                await self.add_fact(f"Literary Line: {line.strip()}", category="literature")
                count += 1

    async def import_facts(self, file_path, limit=50):
        print(f"FACTS: Importing from {file_path}...")
        if not os.path.exists(file_path): return
        with open(file_path, 'r', encoding='utf-8') as f:
            count = 0
            for line in f:
                if count >= limit: break
                if line.startswith('<'):
                    await self.add_fact(line.strip(), category="facts")
                    count += 1

    async def import_psycho(self, file_path, limit=50):
        print(f"PSYCHO: Importing from {file_path}...")
        if not os.path.exists(file_path): return
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
            count = 0
            for p in paragraphs:
                if count >= limit: break
                await self.add_fact(p, category="psycho")
                count += 1

    async def import_esoteric(self, file_path, limit=50):
        print(f"ESOTERIC: Importing from {file_path}...")
        if not os.path.exists(file_path): return
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                # Handle different tarot JSON structures
                if isinstance(data, dict) and 'cards' in data:
                    items = data['cards']
                elif isinstance(data, list):
                    items = data
                else:
                    items = []
                    
                count = 0
                for item in items:
                    if count >= limit: break
                    name = item.get('name', 'Unknown Card')
                    meanings = item.get('meanings', {})
                    if isinstance(meanings, dict):
                        m_text = ", ".join(meanings.get('light', []) + meanings.get('upright', []))
                    else:
                        m_text = str(meanings)
                    fact = f"Tarot: {name}. Meanings: {m_text}"
                    await self.add_fact(fact, category="esoteric")
                    count += 1
            except Exception as e:
                print(f"ERROR: Esoteric error: {e}")

    def close(self):
        self.conn.close()

async def main():
    base_dir = Path("EXTERNAL_DATA")
    db_path = get_db_path()
    importer = BoostImporter(db_path)
    
    print("\n---    # Test each category with lite files")
    await importer.import_russian(base_dir / "RU_SOUL/dostoevsky_test.txt", limit=10)
    # Note: LOGIC file is .gz, we might need a decompressor or use a decompressed sample
    # await importer.import_logic(base_dir / "LOGIC/conceptnet_sample.csv.gz", limit=5) 
    await importer.import_coding(base_dir / "CODING/xcode_sample.jsonl", limit=10)
    await importer.import_literature(base_dir / "LITERATURE/dialog_test.txt", limit=10)
    await importer.import_facts(base_dir / "FACTS/yago_sample.ttl", limit=5)
    await importer.import_psycho(base_dir / "PSYCHO/freud_test.txt", limit=10)
    await importer.import_esoteric(base_dir / "ESOTERIC/tarot_sample.json", limit=10)
    
    importer.close()
    print("\n✅ LITE TEST COMPLETE!")

if __name__ == "__main__":
    asyncio.run(main())
