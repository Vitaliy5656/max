import math
from typing import List, Union

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
     optimized for speed (no numpy dependency for lightweight usage).
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    
    # Optimization: Use inner product
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a)
    norm_b = sum(x * x for x in b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))

def euclidean_distance(a: List[float], b: List[float]) -> float:
    """Calculate Euclidean distance."""
    if not a or not b or len(a) != len(b):
        return float('inf')
        
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
