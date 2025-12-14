"""
Semantic Router for MAX AI.

Uses sentence embeddings + FAISS vector search for fast (~10ms) intent classification.
This replaces 60% of LLM routing calls with instant vector similarity search.

Architecture:
    1. Load bootstrap training data (200+ examples)
    2. Encode examples to vectors with sentence-transformers
    3. Build FAISS index for fast similarity search
    4. At runtime: encode query → search → return intent if confident
"""
import numpy as np
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import time

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

from .bootstrap_loader import get_all_examples, TrainingExample
from ..logger import log


# Model for embeddings (384-dim, fast, multilingual)
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# Dynamic thresholds per intent (higher = more strict)
INTENT_THRESHOLDS: Dict[str, float] = {
    "greeting": 0.75,        # Can afford mistakes
    "goodbye": 0.75,
    "search": 0.80,
    "question": 0.80,
    "coding": 0.82,
    "creative": 0.80,
    "math": 0.82,
    "translation": 0.78,
    "task": 0.80,
    "psychology": 0.85,      # Important to get right
    "vision": 0.85,
    "system_cmd": 0.92,      # 🔥 STRICT - dangerous actions
    "privacy_unlock": 0.95,  # ⚠️ VERY STRICT - security critical
}

DEFAULT_THRESHOLD = 0.85


@dataclass
class SemanticMatch:
    """Result of semantic search."""
    intent: str
    score: float  # 0.0 - 1.0 (cosine similarity)
    example_text: str  # Matched example
    passed_threshold: bool
    topic: Optional[str] = None  # Domain topic (astronomy, jewelry, etc.)


class SemanticRouter:
    """
    Fast intent classification using vector similarity.
    
    ~10ms latency vs ~500ms for LLM routing.
    """
    
    def __init__(self, model_name: str = EMBED_MODEL_NAME):
        if not SEMANTIC_AVAILABLE:
            raise ImportError(
                "SemanticRouter requires: pip install sentence-transformers faiss-cpu"
            )
        
        self.model_name = model_name
        self._model: Optional[SentenceTransformer] = None
        self._index: Optional[faiss.IndexFlatIP] = None
        self._examples: List[TrainingExample] = []
        self._initialized = False
        
        log.debug(f"SemanticRouter created (model: {model_name})")
    
    def initialize(self) -> None:
        """
        Load model and build index from bootstrap data.
        Call this once at startup (takes ~5-10 seconds).
        """
        if self._initialized:
            return
        
        start = time.perf_counter()
        
        # 1. Load embedding model
        log.debug(f"Loading embedding model: {self.model_name}...")
        self._model = SentenceTransformer(self.model_name)
        
        # 2. Load training examples
        log.debug("Loading bootstrap training data...")
        self._examples = get_all_examples()
        
        if not self._examples:
            log.warn("No training examples found! SemanticRouter will not work.")
            return
        
        # 3. Encode all examples
        log.debug(f"Encoding {len(self._examples)} examples...")
        texts = [ex.text for ex in self._examples]
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        
        # 4. Build FAISS index (Inner Product = Cosine Similarity for normalized vectors)
        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)  # IP = Inner Product
        self._index.add(embeddings.astype(np.float32))
        
        elapsed = (time.perf_counter() - start) * 1000
        self._initialized = True
        
        log.debug(
            f"SemanticRouter initialized: {len(self._examples)} examples, "
            f"dim={dim}, took {elapsed:.0f}ms"
        )
    
    def route(self, message: str, k: int = 1) -> Optional[SemanticMatch]:
        """
        Find best matching intent for a message.
        
        Args:
            message: User input to classify
            k: Number of nearest neighbors to check
            
        Returns:
            SemanticMatch if found, None if no confident match
        """
        if not self._initialized:
            self.initialize()
        
        if not self._index or not self._examples:
            return None
        
        start = time.perf_counter()
        
        # Encode query
        query_embedding = self._model.encode(
            [message], 
            normalize_embeddings=True
        ).astype(np.float32)
        
        # Search
        scores, indices = self._index.search(query_embedding, k)
        
        if len(indices[0]) == 0:
            return None
        
        best_idx = indices[0][0]
        best_score = float(scores[0][0])
        best_example = self._examples[best_idx]
        
        # Get threshold for this intent
        threshold = INTENT_THRESHOLDS.get(best_example.intent, DEFAULT_THRESHOLD)
        passed = best_score >= threshold
        
        elapsed = (time.perf_counter() - start) * 1000
        
        log.debug(
            f"SemanticRouter: '{message[:30]}...' → {best_example.intent} "
            f"(score={best_score:.3f}, threshold={threshold}, pass={passed}, {elapsed:.1f}ms)"
        )
        
        return SemanticMatch(
            intent=best_example.intent,
            score=best_score,
            example_text=best_example.text,
            passed_threshold=passed
        )
    
    def route_if_confident(self, message: str) -> Optional[str]:
        """
        Route and return intent only if confident.
        
        This is the main entry point for the routing pipeline.
        Returns None if LLM fallback is needed.
        """
        match = self.route(message)
        
        if match and match.passed_threshold:
            return match.intent
        
        return None  # → LLM fallback
    
    def get_stats(self) -> Dict:
        """Get router statistics."""
        return {
            "initialized": self._initialized,
            "model": self.model_name,
            "num_examples": len(self._examples),
            "index_size": self._index.ntotal if self._index else 0,
        }
    
    def add_example(self, text: str, intent: str, topic: Optional[str] = None) -> None:
        """
        Add new training example at runtime.
        
        Useful for learning from user feedback and dynamic topic discovery.
        
        Args:
            text: Example phrase
            intent: Intent category (coding, question, etc.)
            topic: Optional domain topic (astronomy, jewelry, etc.)
        """
        if not self._initialized:
            self.initialize()
        
        # Encode and add to index
        embedding = self._model.encode(
            [text], 
            normalize_embeddings=True
        ).astype(np.float32)
        
        self._index.add(embedding)
        
        # Create example with optional topic
        example = TrainingExample(text=text, intent=intent)
        # Store topic separately (for now, until we extend TrainingExample)
        if topic:
            if not hasattr(self, '_topics'):
                self._topics = {}
            self._topics[len(self._examples)] = topic
        
        self._examples.append(example)
        
        topic_str = f" (topic={topic})" if topic else ""
        log.debug(f"Added example: '{text[:30]}...' -> {intent}{topic_str}")


# Global instance (lazy initialization)
_semantic_router: Optional[SemanticRouter] = None


def get_semantic_router() -> SemanticRouter:
    """Get or create the global SemanticRouter instance."""
    global _semantic_router
    
    if _semantic_router is None:
        _semantic_router = SemanticRouter()
    
    return _semantic_router


# Convenience function
def semantic_route(message: str) -> Optional[str]:
    """
    Quick semantic routing.
    
    Returns intent if confident, None for LLM fallback.
    """
    return get_semantic_router().route_if_confident(message)
