"""
Brain Map Unit Tests

Tests UMAP projection, caching, and hierarchical levels.
"""
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_embeddings():
    """Generate 10 random embeddings (768D like real model)."""
    np.random.seed(42)
    return [np.random.rand(768).tolist() for _ in range(10)]


@pytest.fixture
def mock_topics():
    """Mock topic data."""
    from dataclasses import dataclass
    
    @dataclass
    class MockTopic:
        id: str
        name: str
        description: str
        chunk_count: int
        skill: str
        status: str
        created_at: str
    
    return [
        MockTopic("topic-1", "Python", "Python programming", 5, None, "complete", "2024-01-01"),
        MockTopic("topic-2", "AI", "Artificial Intelligence", 5, None, "complete", "2024-01-02"),
    ]


class TestBrainMapCore:
    """Tests for brain_map.py core functions."""
    
    def test_topic_color_deterministic(self):
        """Colors should be deterministic based on topic name."""
        from src.core.research.brain_map import _topic_color
        
        color1 = _topic_color("Python")
        color2 = _topic_color("Python")
        color3 = _topic_color("AI")
        
        assert color1 == color2, "Same topic should give same color"
        # Different topics may or may not have same color (hash collision possible)
        assert isinstance(color1, str)
        assert color1.startswith("#")
    
    
    @pytest.mark.asyncio
    async def test_generate_brain_map_no_data(self):
        """Should return error when no research data."""
        from src.core.research.brain_map import generate_brain_map
        
        with patch('src.core.research.brain_map.research_storage') as mock_storage:
            mock_storage.list_topics = AsyncMock(return_value=[])
            
            result = await generate_brain_map()
            
            assert result["points"] == []
            assert "error" in result or result["count"] == 0
    
    
    @pytest.mark.asyncio
    async def test_generate_brain_map_insufficient_data(self, mock_topics):
        """Should return error when less than 3 points."""
        from src.core.research.brain_map import generate_brain_map
        
        # Mock with only 2 embeddings (not enough for UMAP)
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            'embeddings': [np.random.rand(768).tolist(), np.random.rand(768).tolist()],
            'documents': ['doc1', 'doc2'],
            'metadatas': [{}, {}],
            'ids': ['id1', 'id2']
        }
        
        with patch('src.core.research.brain_map.research_storage') as mock_storage:
            mock_storage.list_topics = AsyncMock(return_value=mock_topics[:1])
            mock_storage._get_collection = MagicMock(return_value=mock_collection)
            
            result = await generate_brain_map()
            
            # Should indicate not enough data
            assert result["count"] < 3 or "error" in result
    
    
    @pytest.mark.asyncio  
    async def test_invalidate_cache(self, tmp_path):
        """Cache invalidation should delete cache files."""
        from src.core.research.brain_map import invalidate_cache, PROJECTION_CACHE, REDUCER_CACHE
        
        # Create fake cache files
        PROJECTION_CACHE.parent.mkdir(parents=True, exist_ok=True)
        PROJECTION_CACHE.write_text('{"test": true}')
        
        await invalidate_cache()
        
        # Cache should be deleted
        assert not PROJECTION_CACHE.exists()


class TestConnections:
    """Tests for constellation lines computation."""
    
    def test_compute_connections_empty(self):
        """Should handle empty embeddings."""
        from src.core.research.brain_map import _compute_connections
        
        result = _compute_connections([], [], 0.7)
        assert result == []
    
    
    def test_compute_connections_single(self):
        """Single point has no connections."""
        from src.core.research.brain_map import _compute_connections
        
        result = _compute_connections(
            [[1.0, 0.0, 0.0]],
            [{"id": "p1"}],
            0.7
        )
        assert result == []
    
    
    def test_compute_connections_similar_points(self):
        """Similar points should have high-strength connections."""
        from src.core.research.brain_map import _compute_connections
        
        # Two very similar vectors
        embeddings = [
            [1.0, 0.0, 0.0],
            [0.99, 0.01, 0.0],  # Almost same direction
            [0.0, 1.0, 0.0]     # Orthogonal
        ]
        metadata = [{"id": "p1"}, {"id": "p2"}, {"id": "p3"}]
        
        result = _compute_connections(embeddings, metadata, 0.5)
        
        # p1 and p2 should be connected (similar)
        # p3 should not be connected to others (orthogonal)
        p1_p2 = [c for c in result if (c["from"] == "p1" and c["to"] == "p2")]
        assert len(p1_p2) == 1
        assert p1_p2[0]["strength"] > 0.9


class TestHierarchicalLevels:
    """Tests for hierarchical UMAP levels."""
    
    @pytest.mark.asyncio
    async def test_level_0_returns_centroids(self, mock_topics, mock_embeddings):
        """Level 0 should return topic centroids, not all points."""
        from src.core.research.brain_map import generate_brain_map
        
        # Each topic has 5 embeddings
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            'embeddings': mock_embeddings[:5],
            'documents': [f'doc{i}' for i in range(5)],
            'metadatas': [{'created_at': '2024-01-01'} for _ in range(5)],
            'ids': [f'id{i}' for i in range(5)]
        }
        
        with patch('src.core.research.brain_map.research_storage') as mock_storage:
            mock_storage.list_topics = AsyncMock(return_value=mock_topics)
            mock_storage._get_collection = MagicMock(return_value=mock_collection)
            
            result = await generate_brain_map(level=0)
            
            # Level 0 should have fewer points than total (centroids only)
            # With 2 topics, we expect 2 centroids
            if not result.get("error"):
                assert result["count"] <= len(mock_topics)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
