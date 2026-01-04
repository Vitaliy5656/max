"""
Graph Memory Agent for Deep Research.
Implements GraphRAG capabilities by building a knowledge graph of entities and relations.
"""
from typing import List, Dict, Any, Optional
import aiosqlite
import json
from ..lm_client import lm_client, TaskType

class GraphMemory:
    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def initialize(self):
        """Create graph tables if they don't exist."""
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS graph_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                type TEXT,
                description TEXT,
                metadata TEXT
            )
        """)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS graph_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                target_id INTEGER,
                relation_type TEXT,
                description TEXT,
                run_id TEXT,
                FOREIGN KEY(source_id) REFERENCES graph_entities(id),
                FOREIGN KEY(target_id) REFERENCES graph_entities(id),
                UNIQUE(source_id, target_id, relation_type)
            )
        """)
        await self._db.commit()

    async def add_extraction(self, text: str, run_id: str):
        """Extract entities and relations from text and add to graph."""
        prompt = f"""Ты - Аналитик Графа Знаний (GraphRAG).
Извлеки сущности и связи из текста.

Текст:
{text[:4000]}

Ответи в JSON:
{{
  "entities": [
    {{"name": "Сущность 1", "type": "Человек/Организация/Понятие", "desc": "..."}},
    ...
  ],
  "relations": [
    {{"source": "Сущность 1", "relation": "связана с", "target": "Сущность 2", "desc": "..."}}
  ]
}}"""
        
        try:
            response = await lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                task_type=TaskType.REASONING,
                max_tokens=2000
            )
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0:
                data = json.loads(response[json_start:json_end])
                await self._process_graph_data(data, run_id)
        except Exception as e:
            print(f"Graph extraction error: {e}")

    async def _process_graph_data(self, data: Dict[str, Any], run_id: str):
        """Save entities and relations to DB."""
        entity_map = {}
        
        for ent in data.get("entities", []):
            try:
                await self._db.execute(
                    "INSERT OR IGNORE INTO graph_entities (name, type, description) VALUES (?, ?, ?)",
                    (ent["name"], ent["type"], ent["desc"])
                )
                async with self._db.execute("SELECT id FROM graph_entities WHERE name = ?", (ent["name"],)) as cursor:
                    row = await cursor.fetchone()
                    if row: entity_map[ent["name"]] = row[0]
            except: pass
            
        for rel in data.get("relations", []):
            try:
                src_id = entity_map.get(rel["source"])
                tgt_id = entity_map.get(rel["target"])
                if src_id and tgt_id:
                    await self._db.execute(
                        "INSERT OR IGNORE INTO graph_relations (source_id, target_id, relation_type, description, run_id) VALUES (?, ?, ?, ?, ?)",
                        (src_id, tgt_id, rel["relation"], rel["desc"], run_id)
                    )
            except: pass
            
        await self._db.commit()

    async def get_related_entities(self, entity_name: str) -> List[Dict[str, Any]]:
        """Find related entities in the graph."""
        query = """
            SELECT e.name, e.type, r.relation_type, r.description 
            FROM graph_entities e
            JOIN graph_relations r ON (e.id = r.target_id OR e.id = r.source_id)
            WHERE (SELECT id FROM graph_entities WHERE name = ?) IN (r.source_id, r.target_id)
            AND e.name != ?
        """
        async with self._db.execute(query, (entity_name, entity_name)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
