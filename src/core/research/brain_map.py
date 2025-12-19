"""
Brain Map Generator

Converts ChromaDB embeddings to 3D projections via UMAP.
All heavy computation runs in executor to avoid blocking event loop.

Architecture:
- Level 0: Topic centroids (overview)
- Level 1: Clusters within topic  
- Level 2: All points in cluster
"""
import asyncio
import json
import pickle
import numpy as np
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# UMAP import - may take a moment on first load
try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False
    umap = None

from .storage import research_storage


# Cache paths
CACHE_DIR = Path("data/research")
REDUCER_CACHE = CACHE_DIR / "umap_reducer.pkl"
PROJECTION_CACHE = CACHE_DIR / "brain_map_cache.json"
MAX_POINTS_PER_LEVEL = 100

# Topic colors (deterministic hash for consistency)
COLORS = [
    "#6366f1",  # Indigo
    "#f43f5e",  # Rose  
    "#10b981",  # Emerald
    "#f59e0b",  # Amber
    "#8b5cf6",  # Violet
    "#ec4899",  # Pink
    "#14b8a6",  # Teal
    "#f97316",  # Orange
]


def _topic_color(topic_name: str) -> str:
    """Deterministic color based on topic name hash."""
    return COLORS[hash(topic_name) % len(COLORS)]


async def generate_brain_map(
    level: int = 0,
    topic_id: Optional[str] = None,
    force_recompute: bool = False,
    include_connections: bool = True,
    min_connection_strength: float = 0.7
) -> dict:
    """
    Generate hierarchical brain map with UMAP projection.
    
    Args:
        level: 0=topic centroids, 1=clusters, 2=all points
        topic_id: Filter to specific topic (for level > 0)
        force_recompute: Ignore cache
        include_connections: Add constellation lines
        min_connection_strength: Threshold for connections (0.0-1.0)
    
    Returns:
        {
            "points": [{"x": float, "y": float, "z": float, "topic": str, ...}],
            "connections": [{"from": str, "to": str, "strength": float}],
            "level": int,
            "count": int,
            "temporal_range": {"min": str, "max": str}
        }
    """
    if not UMAP_AVAILABLE:
        return {"points": [], "error": "UMAP not installed", "level": level}
    
    # Try cache first (only for level 0 without force)
    if level == 0 and not force_recompute and PROJECTION_CACHE.exists():
        try:
            cached = json.loads(PROJECTION_CACHE.read_text())
            if cached.get("level") == 0 and cached.get("points"):
                return cached
        except Exception:
            pass
    
    # Collect embeddings from ALL knowledge sources
    all_embeddings = []
    all_metadata = []
    timestamps = []
    
    # === SOURCE 1: Research Topics (ChromaDB) ===
    topics = await research_storage.list_topics()
    
    for topic in topics:
        # Skip other topics if specific topic requested
        if level > 0 and topic_id and topic.id != topic_id:
            continue
        
        collection = research_storage._get_collection(topic.id)
        if not collection:
            continue
        
        try:
            data = collection.get(include=['embeddings', 'metadatas', 'documents'])
        except Exception:
            continue
        
        if not data.get('embeddings') or len(data['embeddings']) == 0:
            continue
        
        for i, emb in enumerate(data['embeddings']):
            all_embeddings.append(emb)
            
            # Extract metadata
            meta = data['metadatas'][i] if data.get('metadatas') and i < len(data['metadatas']) else {}
            doc = data['documents'][i] if data.get('documents') and i < len(data['documents']) else ""
            doc_id = data['ids'][i] if data.get('ids') and i < len(data['ids']) else f"research_{i}"
            
            created_at = meta.get("created_at", topic.created_at)
            timestamps.append(created_at)
            
            all_metadata.append({
                "topic": topic.name,
                "topic_id": topic.id,
                "text": doc[:200] if doc else "",
                "id": doc_id,
                "color": _topic_color(topic.name),
                "source": "research",
                "created_at": created_at
            })
    
    # === SOURCE 2: Memory Facts (SQLite) ===
    try:
        from src.core.memory import memory
        if memory._db:
            async with memory._db.execute(
                "SELECT id, content, category, embedding, created_at FROM memory_facts WHERE embedding IS NOT NULL LIMIT 200"
            ) as cursor:
                facts = await cursor.fetchall()
            
            for fact in facts:
                if fact["embedding"]:
                    import json
                    try:
                        # P0 Fix: embedding is stored as BLOB (bytes), need to decode
                        embedding_data = fact["embedding"]
                        if isinstance(embedding_data, bytes):
                            embedding_data = embedding_data.decode('utf-8')
                        emb = json.loads(embedding_data)
                        all_embeddings.append(emb)
                        
                        category = fact["category"] or "memory"
                        all_metadata.append({
                            "topic": f"Memory: {category}",
                            "topic_id": f"memory_{category}",
                            "text": fact["content"][:200] if fact["content"] else "",
                            "id": f"fact_{fact['id']}",
                            "color": "#22c55e",  # Green for memory
                            "source": "memory",
                            "created_at": fact["created_at"]
                        })
                        timestamps.append(fact["created_at"])
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"[BrainMap] Failed to decode embedding for fact {fact['id']}: {e}")
    except Exception as e:
        print(f"[BrainMap] Could not load memory facts: {e}")
    
    # === SOURCE 3: Document Chunks (SQLite RAG) ===
    try:
        from src.core.rag import rag
        if rag._db:
            async with rag._db.execute(
                """SELECT c.id, c.content, c.embedding, d.filename 
                   FROM document_chunks c 
                   JOIN documents d ON c.document_id = d.id 
                   WHERE c.embedding IS NOT NULL LIMIT 100"""
            ) as cursor:
                chunks = await cursor.fetchall()
            
            for chunk in chunks:
                if chunk["embedding"]:
                    import json
                    try:
                        emb = json.loads(chunk["embedding"].decode() if isinstance(chunk["embedding"], bytes) else chunk["embedding"])
                        all_embeddings.append(emb)
                        
                        all_metadata.append({
                            "topic": f"Doc: {chunk['filename'][:20]}",
                            "topic_id": f"doc_{chunk['id']}",
                            "text": chunk["content"][:200] if chunk["content"] else "",
                            "id": f"chunk_{chunk['id']}",
                            "color": "#f59e0b",  # Amber for documents
                            "source": "document",
                            "created_at": None
                        })
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"[BrainMap] Failed to decode embedding for chunk {chunk['id']}: {e}")
    except Exception as e:
        print(f"[BrainMap] Could not load document chunks: {e}")
    
    # Need at least 3 points for UMAP
    if len(all_embeddings) < 3:
        return {
            "points": [],
            "level": level,
            "count": len(all_embeddings),
            "error": f"Not enough knowledge data (need 3+, have {len(all_embeddings)}). Start chatting or add documents!"
        }
    
    # Apply hierarchical processing
    if level == 0:
        # Compute centroids per topic for overview
        points = await _compute_topic_centroids(all_embeddings, all_metadata)
    else:
        # Limit points for performance
        if len(all_embeddings) > MAX_POINTS_PER_LEVEL:
            indices = np.random.choice(len(all_embeddings), MAX_POINTS_PER_LEVEL, replace=False)
            all_embeddings = [all_embeddings[i] for i in indices]
            all_metadata = [all_metadata[i] for i in indices]
        
        points = await _compute_projection(all_embeddings, all_metadata)
    
    # Compute connections if requested
    connections = []
    if include_connections and len(points) >= 2:
        connections = _compute_connections(all_embeddings, all_metadata, min_connection_strength)
    
    # Compute temporal range
    temporal_range = {"min": None, "max": None}
    if timestamps:
        valid_timestamps = [t for t in timestamps if t]
        if valid_timestamps:
            temporal_range = {
                "min": min(valid_timestamps),
                "max": max(valid_timestamps)
            }
    
    result = {
        "points": points,
        "connections": connections,
        "level": level,
        "count": len(points),
        "temporal_range": temporal_range
    }
    
    # Cache level 0 results
    if level == 0:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            PROJECTION_CACHE.write_text(json.dumps(result, ensure_ascii=False))
        except Exception:
            pass
    
    return result


async def _compute_topic_centroids(embeddings: list, metadata: list) -> list:
    """Compute one centroid per topic for level 0 overview."""
    from collections import defaultdict
    
    # Determine expected dimension (most common dimension in dataset)
    dims = [len(e) for e in embeddings if e]
    if not dims:
        return []
    expected_dim = max(set(dims), key=dims.count)
    
    topic_embeddings = defaultdict(list)
    topic_meta = {}
    
    # Group embeddings by topic (only matching dimensions)
    for emb, meta in zip(embeddings, metadata):
        if emb and len(emb) == expected_dim:
            topic_embeddings[meta["topic_id"]].append(emb)
            topic_meta[meta["topic_id"]] = meta
    
    # Compute centroids
    centroids = []
    centroid_meta = []
    
    for topic_id, embs in topic_embeddings.items():
        if not embs:
            continue
        centroid = np.mean(embs, axis=0)
        centroids.append(centroid)
        
        meta = topic_meta[topic_id].copy()
        meta["point_count"] = len(embs)
        meta["is_centroid"] = True
        meta["id"] = f"centroid_{topic_id}"  # Unique ID for centroid
        centroid_meta.append(meta)
    
    # Project centroids to 3D
    if len(centroids) < 3:
        # Not enough for UMAP, use simple 2D arrangement
        points = []
        for i, meta in enumerate(centroid_meta):
            angle = (2 * np.pi * i) / len(centroid_meta)
            points.append({
                "x": float(np.cos(angle) * 2),
                "y": float(np.sin(angle) * 2),
                "z": 0.0,
                **meta
            })
        return points

    
    return await _compute_projection(centroids, centroid_meta)


async def _compute_projection(embeddings: list, metadata: list) -> list:
    """
    Run UMAP projection in executor (non-blocking).
    
    Uses cached reducer if available for stable projections.
    """
    loop = asyncio.get_event_loop()
    
    # Convert to numpy array
    embeddings_array = np.array(embeddings, dtype=np.float32)
    
    def _run_umap():
        """Blocking UMAP computation (runs in thread pool)."""
        reducer = None
        
        # Try to load cached reducer
        if REDUCER_CACHE.exists():
            try:
                with open(REDUCER_CACHE, 'rb') as f:
                    reducer = pickle.load(f)
            except Exception:
                reducer = None
        
        # Create new reducer if needed
        if reducer is None:
            n_neighbors = min(15, len(embeddings_array) - 1)
            n_neighbors = max(2, n_neighbors)  # Minimum 2
            
            reducer = umap.UMAP(
                n_components=3,
                random_state=42,
                n_neighbors=n_neighbors,
                min_dist=0.1,
                metric='cosine'
            )
        
        # Fit or transform
        try:
            if hasattr(reducer, 'embedding_') and reducer.embedding_ is not None:
                # Already fitted, try transform
                result = reducer.transform(embeddings_array)
            else:
                # Fit new reducer
                result = reducer.fit_transform(embeddings_array)
                # Save for stability
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                with open(REDUCER_CACHE, 'wb') as f:
                    pickle.dump(reducer, f)
        except Exception:
            # Fallback: just fit_transform without caching
            n_neighbors = min(15, len(embeddings_array) - 1)
            n_neighbors = max(2, n_neighbors)
            reducer = umap.UMAP(n_components=3, random_state=42, n_neighbors=n_neighbors)
            result = reducer.fit_transform(embeddings_array)
        
        return result
    
    # Run in executor to avoid blocking
    projections = await loop.run_in_executor(None, _run_umap)
    
    # Build result points
    points = []
    for i, (x, y, z) in enumerate(projections):
        points.append({
            "x": float(x),
            "y": float(y),
            "z": float(z),
            **metadata[i]
        })
    
    return points


def _compute_connections(embeddings: list, metadata: list, min_strength: float) -> list:
    """
    Compute constellation lines based on semantic similarity.
    
    Only returns connections above min_strength threshold.
    """
    if len(embeddings) < 2:
        return []
    
    # Filter to consistent dimensions (most common)
    dims = [len(e) for e in embeddings if e]
    if not dims:
        return []
    expected_dim = max(set(dims), key=dims.count)
    
    filtered_embs = []
    filtered_meta = []
    for emb, meta in zip(embeddings, metadata):
        if emb and len(emb) == expected_dim:
            filtered_embs.append(emb)
            filtered_meta.append(meta)
    
    if len(filtered_embs) < 2:
        return []
    
    connections = []
    embeddings_array = np.array(filtered_embs, dtype=np.float32)
    
    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
    norms[norms == 0] = 1  # Avoid division by zero
    normalized = embeddings_array / norms
    
    # Compute pairwise similarities
    # (Only compute upper triangle to avoid duplicates)
    for i in range(len(filtered_embs)):
        for j in range(i + 1, len(filtered_embs)):
            similarity = float(np.dot(normalized[i], normalized[j]))
            
            if similarity >= min_strength:
                connections.append({
                    "from": filtered_meta[i]["id"],
                    "to": filtered_meta[j]["id"],
                    "strength": round(similarity, 3)
                })
    
    # Limit connections to avoid visual clutter
    connections.sort(key=lambda x: x["strength"], reverse=True)
    return connections[:100]  # Top 100 connections max


async def invalidate_cache():
    """
    Clear brain map cache.
    
    Should be called when new research is completed.
    """
    _invalidate_cache_sync()


def _invalidate_cache_sync():
    """Sync version for calling from non-async contexts."""
    if PROJECTION_CACHE.exists():
        try:
            PROJECTION_CACHE.unlink()
        except Exception:
            pass
    
    if REDUCER_CACHE.exists():
        try:
            REDUCER_CACHE.unlink()
        except Exception:
            pass


async def get_query_spotlight(query: str, top_k: int = 10) -> List[str]:
    """
    Get point IDs most relevant to a query for spotlight effect.
    
    Called during chat to highlight relevant knowledge in brain map.
    """
    results = await research_storage.search_all(query, top_k=top_k)
    return [r["id"] for r in results if r.get("id")]
