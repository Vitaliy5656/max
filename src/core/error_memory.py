"""
Error Memory for MAX AI Assistant.

Vector-based memory of past errors, extending CorrectionDetector.
Allows MAX to recall similar mistakes and warn against repeating them.

Usage:
    from .error_memory import error_memory
    
    # Record error from correction
    await error_memory.record_from_correction(
        original_response="Here's the weather...",
        user_correction="I asked about the news, not weather"
    )
    
    # Recall similar errors
    warnings = await error_memory.recall_similar_errors(query_embedding, top_k=3)
    # ["⚠️ Previously confused 'news' with 'weather'"]
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

import json


@dataclass
class ErrorEntry:
    """A recorded error pattern."""
    id: int
    error_pattern: str
    wrong_action: str
    correct_action: str
    occurrences: int
    embedding: Optional[List[float]] = None


class ErrorMemory:
    """
    Vector-based error memory.
    
    Extends the existing correction_log table with semantic search
    capability for recalling similar past mistakes.
    
    Integration points:
    - CorrectionDetector: provides correction data
    - ContextPrimer: includes warnings in context
    - SelfReflection: builds "don't repeat" section
    """
    
    SIMILARITY_THRESHOLD = 0.75
    
    def __init__(self):
        self._db = None
        self._embedding_service = None
        self._initialized = False
    
    async def initialize(self, db, embedding_service=None):
        """Initialize with database and embedding service."""
        self._db = db
        
        if embedding_service:
            self._embedding_service = embedding_service
        else:
            try:
                from .embedding_service import embedding_service as es
                self._embedding_service = es
            except ImportError:
                pass
        
        self._initialized = True
    
    async def record_from_user_correction(
        self,
        original_response: str,
        user_correction: str,
        context_summary: Optional[str] = None
    ) -> Optional[int]:
        """
        Record an error from user correction.
        
        Args:
            original_response: What MAX said wrong
            user_correction: User's correction message
            context_summary: Optional context description
            
        Returns:
            Error entry ID if created
        """
        if not self._db:
            return None
        
        # Generate embedding for similarity search
        embedding = None
        if self._embedding_service:
            combined_text = f"{original_response[:200]} | {user_correction[:200]}"
            embedding = await self._embedding_service.get_or_compute(combined_text)
        
        # Check for similar existing error
        if embedding:
            similar = await self._find_similar_error(embedding)
            if similar:
                # Increment occurrence count
                await self._increment_occurrence(similar.id)
                return similar.id
        
        # Create new error entry
        try:
            # P0 Security: Use JSON instead of pickle
            embedding_blob = json.dumps(embedding) if embedding else None
            
            async with self._db.execute("""
                INSERT INTO error_memory (
                    error_pattern, wrong_action, correct_action,
                    context_summary, embedding
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                user_correction[:500],
                original_response[:500],
                user_correction[:500],
                context_summary,
                embedding_blob
            )) as cursor:
                error_id = cursor.lastrowid
            
            await self._db.commit()
            return error_id
        except Exception:
            return None
    
    async def recall_similar_errors(
        self,
        context_embedding: Optional[List[float]],
        top_k: int = 3
    ) -> List[str]:
        """
        Recall similar past errors as warnings.
        
        Args:
            context_embedding: Embedding of current context
            top_k: Maximum warnings to return
            
        Returns:
            List of warning strings
        """
        if not self._db or not context_embedding:
            return []
        
        try:
            # Get all errors with embeddings
            async with self._db.execute("""
                SELECT id, error_pattern, wrong_action, correct_action, embedding
                FROM error_memory
                WHERE embedding IS NOT NULL
                ORDER BY occurrences DESC
                LIMIT 20
            """) as cursor:
                rows = await cursor.fetchall()
            
            # Find similar errors
            similar_errors = []
            for row in rows:
                emb_blob = row[4]
                if emb_blob:
                    error_embedding = json.loads(emb_blob)
                    similarity = self._cosine_similarity(context_embedding, error_embedding)
                    if similarity > self.SIMILARITY_THRESHOLD:
                        similar_errors.append((similarity, row))
            
            # Sort by similarity and take top_k
            similar_errors.sort(reverse=True, key=lambda x: x[0])
            
            warnings = []
            for sim, row in similar_errors[:top_k]:
                error_pattern = row[1]
                warnings.append(f"⚠️ Раньше ты ошибся: {error_pattern[:100]}...")
            
            return warnings
        except Exception:
            return []
    
    async def _find_similar_error(self, embedding: List[float]) -> Optional[ErrorEntry]:
        """Find existing similar error entry."""
        if not self._db:
            return None
        
        try:
            async with self._db.execute("""
                SELECT id, error_pattern, wrong_action, correct_action, occurrences, embedding
                FROM error_memory
                WHERE embedding IS NOT NULL
                LIMIT 50
            """) as cursor:
                rows = await cursor.fetchall()
            
            for row in rows:
                emb_blob = row[5]
                if emb_blob:
                    error_embedding = json.loads(emb_blob)
                    similarity = self._cosine_similarity(embedding, error_embedding)
                    if similarity > 0.9:  # Very similar = same error
                        return ErrorEntry(
                            id=row[0],
                            error_pattern=row[1],
                            wrong_action=row[2],
                            correct_action=row[3],
                            occurrences=row[4]
                        )
            
            return None
        except Exception:
            return None
    
    async def _increment_occurrence(self, error_id: int):
        """Increment occurrence count for an error."""
        if not self._db:
            return
        
        try:
            await self._db.execute("""
                UPDATE error_memory
                SET occurrences = occurrences + 1,
                    last_recalled = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (error_id,))
            await self._db.commit()
        except Exception:
            pass
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity."""
        if not a or not b or len(a) != len(b):
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)


# Global instance
error_memory = ErrorMemory()
