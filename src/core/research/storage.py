"""
Research Storage Module

ChromaDB-based vector storage for research data with async-safe embedding computation.

CRITICAL: Embeddings are computed EXTERNALLY and passed as ready vectors to ChromaDB
to avoid run_until_complete() crash in FastAPI event loop.
"""

import json
import chromadb
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class TopicInfo:
    """Information about a research topic."""
    id: str
    name: str
    description: str
    chunk_count: int
    skill: Optional[str]
    status: str  # "incomplete" | "complete"
    created_at: str


class ResearchStorage:
    """
    ChromaDB-based vector storage for research data.
    
    CRITICAL: Do NOT pass embedding function to Chroma.
    Compute embeddings externally and pass ready vectors.
    """
    
    def __init__(self, persist_dir: str = "data/chroma"):
        self._persist_dir = Path(persist_dir)
        self._client: Optional[chromadb.PersistentClient] = None
        self._embedding_service = None
        self._skills_file = Path("data/research/skills.json")
        self._initialized = False
    
    async def initialize(self, embedding_service):
        """Setup ChromaDB client with embedding service."""
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self._persist_dir))
        self._embedding_service = embedding_service
        
        # Ensure skills file exists
        if not self._skills_file.exists():
            self._skills_file.parent.mkdir(parents=True, exist_ok=True)
            self._skills_file.write_text("{}")
        
        self._initialized = True
    
    async def create_topic(self, name: str, description: str = "", status: str = "incomplete") -> str:
        """
        Create new research topic (collection). Returns topic_id.
        
        Topics start as 'incomplete' and are marked 'complete' only after
        successful research completion.
        """
        if not self._initialized:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        
        topic_id = str(uuid4())
        # ChromaDB collection names must be alphanumeric with underscores
        safe_name = f"topic_{topic_id.replace('-', '_')}"
        self._client.create_collection(name=safe_name)
        
        # Store metadata with status
        self._save_topic_meta(topic_id, {
            "name": name,
            "description": description,
            "skill": None,
            "status": status,
            "created_at": datetime.now().isoformat()
        })
        return topic_id
    
    async def update_topic_status(self, topic_id: str, status: str):
        """Update topic status. Called after successful research or on failure."""
        skills = self._load_skills()
        if topic_id in skills:
            skills[topic_id]["status"] = status
            self._save_skills(skills)
    
    async def add_chunk(self, topic_id: str, content: str, metadata: dict):
        """
        Add distilled content to topic collection.
        
        IMPORTANT: Embedding computed OUTSIDE, passed as ready vector.
        This avoids run_until_complete() crash in FastAPI event loop.
        """
        if not self._embedding_service:
            raise RuntimeError("Embedding service not initialized")
        
        collection = self._get_collection(topic_id)
        if not collection:
            raise ValueError(f"Topic {topic_id} not found")
        
        # Compute embedding EXTERNALLY (async-safe)
        embedding = await self._embedding_service.get_or_compute(content)
        
        if embedding:
            collection.add(
                documents=[content],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[str(uuid4())]
            )
    
    async def search(self, topic_id: str, query: str, top_k: int = 5) -> list[dict]:
        """Semantic search within topic."""
        if not self._embedding_service:
            return []
        
        collection = self._get_collection(topic_id)
        if not collection:
            return []
        
        query_embedding = await self._embedding_service.get_or_compute(query)
        
        if not query_embedding:
            return []
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        return self._format_results(results)
    
    async def search_all(self, query: str, top_k: int = 10) -> list[dict]:
        """Search across ALL topics (for Lens routing)."""
        all_results = []
        topics = await self.list_topics()
        
        for topic in topics:
            results = await self.search(topic.id, query, top_k=3)
            for r in results:
                r["topic_name"] = topic.name
                r["topic_id"] = topic.id
            all_results.extend(results)
        
        # Sort by distance and return top_k
        all_results.sort(key=lambda x: x.get("distance", 999))
        return all_results[:top_k]
    
    async def save_skill(self, topic_id: str, skill_prompt: str):
        """Save generated Topic Lens (skill) for a topic."""
        skills = self._load_skills()
        if topic_id in skills:
            skills[topic_id]["skill"] = skill_prompt
            self._save_skills(skills)
    
    async def get_skill(self, topic_id: str) -> Optional[str]:
        """Get skill prompt for topic."""
        skills = self._load_skills()
        return skills.get(topic_id, {}).get("skill")
    
    async def get_all_skills(self) -> dict[str, str]:
        """Get all skills as {topic_name: skill_prompt}."""
        skills = self._load_skills()
        return {
            data.get("name", "Unknown"): data.get("skill", "")
            for tid, data in skills.items()
            if data.get("skill")
        }
    
    async def list_topics(self) -> list[TopicInfo]:
        """List all research topics with stats."""
        skills = self._load_skills()
        result = []
        
        for topic_id, data in skills.items():
            collection = self._get_collection(topic_id)
            chunk_count = collection.count() if collection else 0
            
            result.append(TopicInfo(
                id=topic_id,
                name=data.get("name", "Unknown"),
                description=data.get("description", ""),
                chunk_count=chunk_count,
                skill=data.get("skill"),
                status=data.get("status", "unknown"),
                created_at=data.get("created_at", "")
            ))
        
        return result
    
    async def get_topic(self, topic_id: str) -> Optional[TopicInfo]:
        """Get single topic by ID."""
        skills = self._load_skills()
        data = skills.get(topic_id)
        
        if not data:
            return None
        
        collection = self._get_collection(topic_id)
        chunk_count = collection.count() if collection else 0
        
        return TopicInfo(
            id=topic_id,
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            chunk_count=chunk_count,
            skill=data.get("skill"),
            status=data.get("status", "unknown"),
            created_at=data.get("created_at", "")
        )
    
    async def delete_topic(self, topic_id: str) -> bool:
        """Remove topic and all data."""
        safe_name = f"topic_{topic_id.replace('-', '_')}"
        
        try:
            self._client.delete_collection(name=safe_name)
        except Exception:
            pass
        
        # Remove from skills file
        skills = self._load_skills()
        if topic_id in skills:
            del skills[topic_id]
            self._save_skills(skills)
            return True
        
        return False
    
    def _get_collection(self, topic_id: str):
        """Get ChromaDB collection for topic."""
        safe_name = f"topic_{topic_id.replace('-', '_')}"
        try:
            return self._client.get_collection(name=safe_name)
        except Exception:
            return None
    
    def _save_topic_meta(self, topic_id: str, data: dict):
        """Save topic metadata to skills file."""
        skills = self._load_skills()
        skills[topic_id] = data
        self._save_skills(skills)
    
    def _load_skills(self) -> dict:
        """Load skills file."""
        try:
            return json.loads(self._skills_file.read_text())
        except Exception:
            return {}
    
    def _save_skills(self, skills: dict):
        """Save skills file."""
        self._skills_file.parent.mkdir(parents=True, exist_ok=True)
        self._skills_file.write_text(json.dumps(skills, indent=2, ensure_ascii=False))
    
    def _format_results(self, results: dict) -> list[dict]:
        """Format ChromaDB results to list of dicts."""
        formatted = []
        
        if not results.get("documents"):
            return []
        
        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(documents)
        distances = results["distances"][0] if results.get("distances") else [0] * len(documents)
        ids = results["ids"][0] if results.get("ids") else [str(i) for i in range(len(documents))]
        
        for i, doc in enumerate(documents):
            formatted.append({
                "id": ids[i],
                "content": doc,
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "distance": distances[i] if i < len(distances) else 0
            })
        
        return formatted


# Global instance
research_storage = ResearchStorage()
