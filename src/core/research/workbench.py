"""
Research Workbench — Ephemeral Vector Store for Batch Analysis.

Architecture:
1. HARVEST: Параллельный сбор страниц → chunks с embeddings
2. ACCUMULATE: Накопление на "столе" до threshold
3. ANALYZE: Кластеризация, паттерны, противоречия, gaps
4. COMMIT: Перенос качественных фактов в постоянную память
5. ADAPT: Генерация следующих запросов на основе findings
"""

import asyncio
import hashlib
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

# ChromaDB for ephemeral storage
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

from ..lm_client import lm_client, TaskType


@dataclass
class WorkbenchChunk:
    """Single chunk on the workbench."""
    content: str
    source_url: str = ""
    embedding: Optional[list[float]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    chunk_id: str = ""
    
    def __post_init__(self):
        if not self.chunk_id:
            # Hash content + URL to avoid collisions
            self.chunk_id = hashlib.md5((self.content + self.source_url).encode()).hexdigest()[:16]


@dataclass
class ClusterInfo:
    """Information about a semantic cluster."""
    cluster_id: int
    chunks: list[WorkbenchChunk]
    centroid: Optional[np.ndarray] = None
    theme: str = ""
    size: int = 0


@dataclass
class WorkbenchAnalysis:
    """Results of workbench analysis."""
    total_chunks: int
    clusters: list[ClusterInfo]
    common_themes: list[str]
    unique_insights: list[str]
    contradictions: list[tuple[str, str]]
    gaps: list[str]
    next_queries: list[str]
    quality_facts: list[str]  # Facts ready for permanent memory


class ResearchWorkbench:
    """
    Ephemeral 'table' for accumulating and analyzing raw research data.
    
    Flow:
    1. add_page() — добавляет chunks на стол
    2. is_ready() — проверяет, пора ли анализировать
    3. analyze() — кластеризация и извлечение инсайтов
    4. get_quality_facts() — факты для постоянной памяти
    5. clear() — очистка для следующей итерации
    """
    
    def __init__(self, threshold: int = 30, chunk_size: int = 500):
        self.threshold = threshold
        self.chunk_size = chunk_size
        self.chunks: list[WorkbenchChunk] = []
        self._embeddings_cache: dict[str, list[float]] = {}
        
        # Initialize ChromaDB ephemeral client
        if CHROMA_AVAILABLE:
            self._chroma = chromadb.Client(Settings(
                anonymized_telemetry=False,
                is_persistent=False  # Ephemeral mode
            ))
            self._collection = self._chroma.create_collection(
                name="workbench",
                metadata={"hnsw:space": "cosine"}
            )
        else:
            self._chroma = None
            self._collection = None
        
        print(f"[WORKBENCH] Initialized (threshold={threshold}, ChromaDB={'ON' if CHROMA_AVAILABLE else 'OFF'})")
    
    async def add_page(self, url: str, content: str) -> bool:
        """
        Add a page to the workbench.
        Returns True if threshold reached (time to analyze).
        """
        if not content or len(content) < 100:
            return False
        
        # Split into chunks
        page_chunks = self._split_into_chunks(content)
        
        # Generate embeddings for all chunks
        embeddings = await self._embed_chunks([c.content for c in page_chunks])
        
        # Store chunks
        for chunk, emb in zip(page_chunks, embeddings):
            chunk.source_url = url
            chunk.embedding = emb
            self.chunks.append(chunk)
            
            # Add to ChromaDB if available
            if self._collection and emb:
                self._collection.add(
                    ids=[chunk.chunk_id],
                    embeddings=[emb],
                    documents=[chunk.content],
                    metadatas=[{"url": url, "timestamp": chunk.timestamp.isoformat()}]
                )
        
        print(f"[WORKBENCH] Added {len(page_chunks)} chunks from {url[:50]}... (total: {len(self.chunks)})")
        
        return len(self.chunks) >= self.threshold
    
    def is_ready(self) -> bool:
        """Check if workbench has enough data for analysis."""
        return len(self.chunks) >= self.threshold
    
    async def should_deep_dive(self, url: str, content: str, goal: str, threshold: float = 0.55) -> bool:
        """
        Check if a page is relevant enough for Deep Dive.
        Uses embedding similarity to determine if we should follow internal links.
        """
        if len(content) < 500:
            return False
        
        # Get embeddings
        content_emb = await self._get_embedding(content[:1000])  # First 1000 chars
        goal_emb = await self._get_embedding(goal)
        
        # Check similarity
        similarity = self._cosine_similarity(content_emb, goal_emb)
        
        if similarity >= threshold:
            print(f"[WORKBENCH] Site is highly relevant ({similarity:.2f}) — Deep Dive recommended!")
            return True
        
        return False

    async def analyze(self, goal: str) -> WorkbenchAnalysis:
        """
        Analyze accumulated data:
        1. Cluster by semantic similarity
        2. Extract common themes
        3. Find unique insights
        4. Detect contradictions
        5. Identify gaps
        6. Generate next queries
        """
        print(f"[WORKBENCH] Analyzing {len(self.chunks)} chunks...")
        
        if not self.chunks:
            return WorkbenchAnalysis(
                total_chunks=0, clusters=[], common_themes=[],
                unique_insights=[], contradictions=[], gaps=[],
                next_queries=[goal], quality_facts=[]
            )
        
        # 1. Simple clustering (semantic similarity to goal)
        goal_embedding = await self._get_embedding(goal)
        clusters = await self._cluster_by_relevance(goal_embedding)
        
        # 2. Extract insights using LLM (single batch call!)
        analysis_prompt = self._build_analysis_prompt(goal, clusters)
        
        try:
            response = await lm_client.chat(
                messages=[{"role": "user", "content": analysis_prompt}],
                stream=False,
                task_type=TaskType.REASONING,
                max_tokens=2000
            )
            parsed = self._parse_analysis_response(response)
        except Exception as e:
            print(f"[WORKBENCH] Analysis error: {e}")
            parsed = {
                "common": [], "unique": [], "contradictions": [],
                "gaps": [], "next_queries": [goal], "facts": []
            }
        
    async def triangulate_facts(self, goal: str, similarity_threshold: float = 0.85) -> list[str]:
        """
        Identify "Gold Facts" by finding semantic overlap between DIFFERENT sources.
        
        Logic:
        1. Group chunks by their source URL.
        2. Compare chunks from source A with chunks from source B, C, etc.
        3. If high similarity is found across 2+ DIFFERENT domains, it's a "Gold Fact".
        """
        if len(self.chunks) < 2:
            return []

        # 1. Group by domain (to ensure source diversity)
        from urllib.parse import urlparse
        domain_groups: dict[str, list[WorkbenchChunk]] = {}
        for chunk in self.chunks:
            domain = urlparse(chunk.source_url).netloc
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(chunk)

        if len(domain_groups) < 2:
            print("[WORKBENCH] Not enough diverse sources for triangulation.")
            return await self.quick_extract_facts(goal)

        gold_candidates = []
        domains = list(domain_groups.keys())
        
        # 2. Compare domains
        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                dom_a, dom_b = domains[i], domains[j]
                
                for chunk_a in domain_groups[dom_a]:
                    if not chunk_a.embedding: continue
                    
                    for chunk_b in domain_groups[dom_b]:
                        if not chunk_b.embedding: continue
                        
                        sim = self._cosine_similarity(chunk_a.embedding, chunk_b.embedding)
                        if sim >= similarity_threshold:
                            # We found a cross-source match!
                            # Combine or pick the one closer to the goal
                            gold_candidates.append({
                                "content": chunk_a.content,
                                "similarity": sim,
                                "sources": {dom_a, dom_b}
                            })

        if not gold_candidates:
            return []

        # 3. Deduplicate and refine candidates using LLM
        # Group candidates by content similarity to avoid redundancy
        refined_content = "\n---\n".join([c["content"][:500] for c in gold_candidates[:10]])
        
        prompt = f"""Ниже приведены фрагменты текста, найденные в РАЗНЫХ независимых источниках по теме: {goal}
Эти факты подтверждают друг друга (триангуляция).

Твоя задача: СИНТЕЗИРУЙ из этих фрагментов 3-5 максимально точных, "золотых" фактов.
Для каждого факта укажи уровень уверенности: [ВЕРИФИЦИРОВАНО (GOLD)].

Фрагменты:
{refined_content}

Ответить списком строк. Каждый факт должен быть законченным предложением."""

        try:
            response = await lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                task_type=TaskType.REASONING,
                max_tokens=1000
            )
            gold_facts = [
                line.lstrip("0123456789.-•) ").strip()
                for line in response.split("\n")
                if len(line.strip()) > 20
            ]
            
            print(f"[WORKBENCH] Triangulated {len(gold_facts)} GOLD facts from {len(domain_groups)} sources")
            return [f"[ВЕРИФИЦИРОВАНО (GOLD)] {f}" for f in gold_facts]
            
        except Exception as e:
            print(f"[WORKBENCH] Triangulation error: {e}")
            return [f"[ВЕРИФИЦИРОВАНО (GOLD)] {c['content']}" for c in gold_candidates[:3]]

    async def quick_extract_facts(self, goal: str) -> list[str]:
        """
        Fast fact extraction with embedding-based verification.
        No LLM calls for verification — uses cosine similarity.
        """
        if not self.chunks:
            return []
        
        goal_embedding = await self._get_embedding(goal)
        
        # Score chunks by relevance
        scored = []
        for chunk in self.chunks:
            if chunk.embedding:
                sim = self._cosine_similarity(goal_embedding, chunk.embedding)
                if sim > 0.4:  # Lower threshold to get more candidates
                    scored.append((sim, chunk.content))
        
        # Sort by relevance
        scored.sort(reverse=True)
        
        # Take top chunks and extract facts with single LLM call
        top_content = "\n---\n".join([c for _, c in scored[:10]])
        
        if not top_content:
            return []
        
        prompt = f"""Extract key facts about: {goal}

Content:
{top_content[:4000]}

Return as numbered list. Only include factual statements."""

        try:
            response = await lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                task_type=TaskType.REASONING,
                max_tokens=1500
            )
            raw_facts = [
                line.lstrip("0123456789.-•) ").strip()
                for line in response.split("\n")
                if len(line.strip()) > 30
            ]
            
            # EMBEDDING VERIFICATION: Tag facts based on similarity to goal
            tagged_facts = []
            for fact in raw_facts[:15]:
                fact_emb = await self._get_embedding(fact)
                sim = self._cosine_similarity(goal_embedding, fact_emb)
                
                # Classify based on similarity
                if sim >= 0.7:
                    tag = "верифицировано"
                elif sim >= 0.5:
                    tag = "слухи/мнения"
                else:
                    continue  # Skip low-relevance facts
                
                tagged_facts.append(f"[{tag}] {fact}")
            
            print(f"[WORKBENCH] Verified {len(tagged_facts)} facts via embeddings (no LLM!)")
            return tagged_facts
            
        except Exception as e:
            print(f"[WORKBENCH] Fact extraction error: {e}")
            return []
    
    def clear(self):
        """Clear workbench for next iteration."""
        self.chunks = []
        if self._collection:
            # Recreate collection (fastest way to clear)
            self._chroma.delete_collection("workbench")
            self._collection = self._chroma.create_collection(
                name="workbench",
                metadata={"hnsw:space": "cosine"}
            )
        print("[WORKBENCH] Cleared")
    
    # =============== PRIVATE METHODS ===============
    
    def _split_into_chunks(self, content: str) -> list[WorkbenchChunk]:
        """Split content into semantic chunks."""
        # Simple split by paragraphs, then by size
        paragraphs = content.split("\n\n")
        chunks = []
        current = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current) + len(para) < self.chunk_size:
                current += "\n" + para if current else para
            else:
                if current:
                    chunks.append(WorkbenchChunk(content=current))
                current = para
        
        if current:
            chunks.append(WorkbenchChunk(content=current))
        
        return chunks
    
    async def _embed_chunks(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts (batch analysis)."""
        if not texts:
            return []
        
        # Check cache first
        results = [None] * len(texts)
        to_embed_indices = []
        to_embed_texts = []
        
        for i, text in enumerate(texts):
            # P2 Fix: Use full content for hash to avoid collisions
            cache_key = hashlib.md5(text.encode()).hexdigest()
            if cache_key in self._embeddings_cache:
                results[i] = self._embeddings_cache[cache_key]
            else:
                to_embed_indices.append(i)
                to_embed_texts.append(text[:500]) # Limit per chunk
        
        if to_embed_texts:
            try:
                # Actual batch call
                response = await lm_client.client.embeddings.create(
                    model="text-embedding-bge-m3",
                    input=to_embed_texts
                )
                for i, data in enumerate(response.data):
                    emb = data.embedding
                    idx = to_embed_indices[i]
                    results[idx] = emb
                    # Update cache (P2 Fix: full content hash)
                    cache_key = hashlib.md5(texts[idx].encode()).hexdigest()
                    self._embeddings_cache[cache_key] = emb
            except Exception as e:
                print(f"[WORKBENCH] Batch embedding error: {e}")
                # Fallback for failed batch
                for idx in to_embed_indices:
                    results[idx] = [0.0] * 768
                    
        return results
    
    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for single text."""
        # P2 Fix: Use full content for hash to avoid collisions
        cache_key = hashlib.md5(text.encode()).hexdigest()
        
        if cache_key in self._embeddings_cache:
            return self._embeddings_cache[cache_key]
        
        try:
            # Use LM Studio embedding endpoint
            response = await lm_client.client.embeddings.create(
                model="text-embedding-bge-m3",
                input=text[:500]  # Limit for speed
            )
            emb = response.data[0].embedding
            self._embeddings_cache[cache_key] = emb
            return emb
        except Exception as e:
            # Fallback: return zero vector
            return [0.0] * 768
    
    async def _cluster_by_relevance(self, goal_embedding: list[float]) -> list[ClusterInfo]:
        """Simple clustering: high/medium/low relevance to goal."""
        high, medium, low = [], [], []
        
        for chunk in self.chunks:
            if not chunk.embedding:
                continue
            
            sim = self._cosine_similarity(goal_embedding, chunk.embedding)
            
            if sim > 0.7:
                high.append(chunk)
            elif sim > 0.5:
                medium.append(chunk)
            else:
                low.append(chunk)
        
        clusters = []
        if high:
            clusters.append(ClusterInfo(cluster_id=0, chunks=high, theme="Высокая релевантность", size=len(high)))
        if medium:
            clusters.append(ClusterInfo(cluster_id=1, chunks=medium, theme="Средняя релевантность", size=len(medium)))
        if low:
            clusters.append(ClusterInfo(cluster_id=2, chunks=low, theme="Низкая релевантность", size=len(low)))
        
        return clusters
    
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b:
            return 0.0
        
        a_arr = np.array(a)
        b_arr = np.array(b)
        
        dot = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot / (norm_a * norm_b))
    
    def _build_analysis_prompt(self, goal: str, clusters: list[ClusterInfo]) -> str:
        """Build prompt for batch analysis."""
        high_rel = ""
        if clusters and clusters[0].theme == "Высокая релевантность":
            high_rel = "\n".join([c.content[:300] for c in clusters[0].chunks[:5]])
        
        return f"""Ты — Аналитик Исследований. Проанализируй найденную информацию.

Цель исследования: {goal}

Релевантные фрагменты:
{high_rel[:3000]}

Задачи:
1. Выдели 3-5 ОБЩИХ ТЕМ, которые повторяются
2. Найди 2-3 УНИКАЛЬНЫХ ИНСАЙТА (неожиданных)
3. Есть ли ПРОТИВОРЕЧИЯ между источниками?
4. Какие ПРОБЕЛЫ в информации? Чего не хватает?
5. Сгенерируй 3 УТОЧНЯЮЩИХ ЗАПРОСА для следующего поиска
6. Выдели 5-10 ФАКТОВ, готовых для сохранения

Ответь в JSON:
{{
  "common": ["тема1", "тема2"],
  "unique": ["инсайт1", "инсайт2"],
  "contradictions": [["утверждение1", "противоречит утверждению2"]],
  "gaps": ["чего не хватает"],
  "next_queries": ["запрос1", "запрос2", "запрос3"],
  "facts": ["факт1", "факт2", ...]
}}"""
    
    def _parse_analysis_response(self, response: str) -> dict:
        """Parse LLM analysis response."""
        import json
        
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0:
                return json.loads(response[json_start:json_end])
        except:
            pass
        
        # Fallback: extract what we can
        return {
            "common": [],
            "unique": [],
            "contradictions": [],
            "gaps": [],
            "next_queries": [],
            "facts": []
        }
    
    # ==================== ADAPTIVE QUERIES (P4) ====================
    
    async def generate_adaptive_queries(
        self, 
        goal: str, 
        found_themes: list[str] = None,
        gaps: list[str] = None
    ) -> list[str]:
        """
        Generate refined search queries based on what was found.
        This enables iterative, intelligent research.
        """
        if not self.chunks:
            return [goal]  # No data yet, use original goal
        
        # Build context from what we've accumulated
        chunk_summary = "\n".join([c.content[:200] for c in self.chunks[:5]])
        
        prompt = f"""На основе уже найденной информации, сгенерируй 3 уточняющих поисковых запроса.

Цель исследования: {goal}

Уже найдено (кратко):
{chunk_summary[:1500]}

{"Основные темы: " + ", ".join(found_themes[:3]) if found_themes else ""}
{"Пробелы: " + ", ".join(gaps[:3]) if gaps else ""}

Сгенерируй 3 УТОЧНЯЮЩИХ запроса для поиска недостающей информации.
Ответь JSON: {{"queries": ["запрос1", "запрос2", "запрос3"]}}"""

        try:
            response = await lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                task_type=TaskType.QUICK,
                max_tokens=400
            )
            
            import json
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0:
                data = json.loads(response[json_start:json_end])
                queries = data.get("queries", [])
                if queries:
                    print(f"[WORKBENCH] Generated {len(queries)} adaptive queries")
                    return queries
        except Exception as e:
            print(f"[WORKBENCH] Adaptive query generation error: {e}")
        
        return [goal]  # Fallback to original
    
    # ==================== DEDUPLICATION (P5) ====================
    
    async def deduplicate_facts(
        self, 
        new_facts: list[str], 
        existing_facts: list[str],
        similarity_threshold: float = 0.92
    ) -> list[str]:
        """
        Remove facts that are too similar to existing ones.
        Uses embedding similarity for semantic deduplication.
        """
        if not existing_facts:
            return new_facts
        
        # Get embeddings for existing facts
        existing_embeddings = []
        for fact in existing_facts[:50]:  # Limit for performance
            emb = await self._get_embedding(fact)
            if emb and any(x != 0 for x in emb):
                existing_embeddings.append((fact, emb))
        
        if not existing_embeddings:
            return new_facts
        
        unique_facts = []
        duplicates_skipped = 0
        
        for new_fact in new_facts:
            new_emb = await self._get_embedding(new_fact)
            
            is_duplicate = False
            if new_emb and any(x != 0 for x in new_emb):
                for _, existing_emb in existing_embeddings:
                    sim = self._cosine_similarity(new_emb, existing_emb)
                    if sim >= similarity_threshold:
                        is_duplicate = True
                        duplicates_skipped += 1
                        break
            
            if not is_duplicate:
                unique_facts.append(new_fact)
        
        if duplicates_skipped > 0:
            print(f"[WORKBENCH] Deduplicated: skipped {duplicates_skipped} similar facts")
        
        return unique_facts
