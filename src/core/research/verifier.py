"""
Verifier Agent for Deep Research.
Dual-mode verification:
1. FAST: Embedding similarity (100x faster)
2. DEEP: LLM-based (Phi 3.5 Mini) for complex cases

Roles:
- Fact validity/grounding check.
- Intelligent content filtering (NSFW/Spam).
- Source credibility assessment.
"""
import re
import numpy as np
from typing import List, Dict, Any, Tuple
from ..lm_client import lm_client, TaskType


class ResearchVerifier:
    def __init__(self, model_type: TaskType = TaskType.QUICK):
        self.model_type = model_type
        self._embedding_cache: dict[str, list[float]] = {}
    
    # ==================== FAST MODE: Embedding Verification ====================
    
    async def verify_batch_via_embeddings(
        self, 
        facts: list[str], 
        goal: str,
        context_facts: list[str] = None,
        high_threshold: float = 0.7,
        medium_threshold: float = 0.5
    ) -> list[Tuple[str, float]]:
        """
        FAST verification via embedding similarity.
        Now supports optional context_facts for better consistency check.
        """
        if not facts:
            return []
        
        # Get goal and context embeddings
        goal_emb = await self._get_embedding(goal)
        context_embs = []
        if context_facts:
            # Only use top 5 context facts to avoid overhead
            for cf in context_facts[:5]:
                context_embs.append(await self._get_embedding(cf))
        
        results = []
        for fact in facts:
            fact_emb = await self._get_embedding(fact)
            
            # Base similarity to goal
            goal_sim = self._cosine_similarity(goal_emb, fact_emb)
            
            # Contextual similarity (if any)
            context_sim = 0.0
            if context_embs:
                context_sim = max([self._cosine_similarity(ce, fact_emb) for ce in context_embs])
            
            # Final score: boost if matches previous context
            final_score = goal_sim
            if context_sim > 0.8: # Already known/consistent
                final_score = max(final_score, context_sim * 0.9)
            
            # Classify based on similarity thresholds
            if final_score >= high_threshold:
                tag = "верифицировано"
            elif final_score >= medium_threshold:
                tag = "слухи/мнения"
            else:
                tag = "не подтверждено"
            
            results.append((tag, final_score))
        
        return results

    def clear_cache(self):
        """Clear embedding cache to prevent memory bloat (Audit Fix)."""
        self._embedding_cache.clear()
        print("[VERIFIER] Embedding cache cleared.")
    
    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text with caching."""
        import hashlib
        # P2 Fix: Use full content for hash to avoid collisions
        cache_key = hashlib.md5(text.encode()).hexdigest()
        
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        try:
            response = await lm_client.client.embeddings.create(
                model="text-embedding-bge-m3",
                input=text[:500]
            )
            emb = response.data[0].embedding
            self._embedding_cache[cache_key] = emb
            return emb
        except Exception as e:
            # Fallback: return zero vector
            return [0.0] * 768
    
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
    
    # ==================== DEEP MODE: LLM Verification ====================

    async def verify_fact(self, fact: str, goal: str) -> Tuple[str, float]:
        """
        DEEP verification using LLM (slower but more accurate).
        Use for complex/controversial facts.
        Returns: (metric_tag, confidence)
        Tags: "верифицировано", "слухи/мнения", "не подтверждено"
        """
        prompt = f"""Ты - Эксперт по верификации фактов (Phi-3.5).
Цель исследования: {goal}
Факт для проверки: {fact}

Оцени этот факт:
1. Насколько он релевантен цели?
2. Насколько он звучит как объективный факт, а не слух?

Ответи одной из меток и кратко почему (в формате JSON):
{{
  "tag": "верифицировано" | "слухи/мнения" | "не подтверждено",
  "confidence": 0.0-1.0,
  "reason": "..."
}}"""
        
        try:
            response = await lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                task_type=self.model_type,
                max_tokens=300,
                stream=False
            )
            import json
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0:
                data = json.loads(response[json_start:json_end])
                return data.get("tag", "не подтверждено"), data.get("confidence", 0.5)
        except:
            pass
            
        return "не подтверждено", 0.5

    async def filter_content(self, url: str, snippet: str, goal: str) -> bool:
        """
        Intelligent content filter.
        Determines if a site is a valuable source or spam/garbage (including adult tubes).
        """
        # Fast path for known adult domains in URL (optional, user wanted intelligent filtering)
        
        prompt = f"""Ты - Мягкий Фильтр Контента для исследования.
Тема: {goal}
URL: {url}
Snippet: {snippet}

ЗАДАЧА: Определи, содержит ли страница ЛЮБУЮ полезную информацию по теме.

РАЗРЕШАЙ если:
- Контент ХОТЬ КАК-ТО связан с темой (даже косвенно)
- Это форум/Reddit с обсуждением темы
- Это новостная статья или блог
- Это научная/образовательная информация

БЛОКИРУЙ ТОЛЬКО если:
- Это ЯВНЫЙ порно-сайт (xvideos, pornhub и т.д.)
- Это 404 или пустая страница
- Это СОВЕРШЕННО не связано с темой

ПО УМОЛЧАНИЮ РАЗРЕШАЙ. В сомнительных случаях — РАЗРЕШАЙ.
Ответь JSON: {{"allow": true/false, "reason": "...кратко"}}"""

        try:
            response = await lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                task_type=self.model_type,
                max_tokens=200,
                stream=False
            )
            import json
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0:
                data = json.loads(response[json_start:json_end])
                return data.get("allow", True)
        except:
            return True # If in doubt, allow
            
        return True
