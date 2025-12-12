"""
Tests for RAG (Retrieval-Augmented Generation) module.

ALIGNED WITH REAL API: RAGEngine class.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRAGEngineStructure:
    """Tests for RAGEngine class structure."""
    
    def test_imports_and_classes_exist(self):
        """Test that all expected classes can be imported."""
        from src.core.rag import (
            RAGEngine,
            Document,
            Chunk
        )
        
        assert RAGEngine is not None
        assert Document is not None
        assert Chunk is not None
        
    def test_document_dataclass(self):
        """Test Document dataclass fields."""
        from src.core.rag import Document
        
        doc = Document(
            id="doc-1",
            filename="test.txt",
            file_path="/path/to/test.txt",
            file_type="txt",
            chunk_count=5
        )
        
        assert doc.id == "doc-1"
        assert doc.filename == "test.txt"
        assert doc.chunk_count == 5
        
    def test_chunk_dataclass(self):
        """Test Chunk dataclass fields."""
        from src.core.rag import Chunk
        
        chunk = Chunk(
            document_id="doc-1",
            content="Text content here",
            chunk_index=0,
            tokens=10,
            score=0.9
        )
        
        assert chunk.document_id == "doc-1"
        assert chunk.content == "Text content here"
        assert chunk.score == 0.9


class TestRAGEngineMethods:
    """Tests for RAGEngine method signatures."""
    
    def test_rag_engine_has_methods(self):
        """Test that RAGEngine has expected methods."""
        from src.core.rag import RAGEngine
        
        # Check method existence
        assert hasattr(RAGEngine, 'initialize')
        assert hasattr(RAGEngine, 'add_document')
        assert hasattr(RAGEngine, 'list_documents')
        assert hasattr(RAGEngine, 'get_document')
        assert hasattr(RAGEngine, 'remove_document')
        assert hasattr(RAGEngine, 'query')
        assert hasattr(RAGEngine, 'get_context_for_query')
        assert hasattr(RAGEngine, 'count_tokens')
        
    def test_rag_engine_instantiation(self):
        """Test RAGEngine can be instantiated."""
        from src.core.rag import RAGEngine
        
        engine = RAGEngine()
        assert engine is not None
        
    def test_count_tokens_method(self):
        """Test count_tokens method exists and works."""
        from src.core.rag import RAGEngine
        
        engine = RAGEngine()
        
        # Should return integer
        count = engine.count_tokens("Hello world")
        assert isinstance(count, int)
        assert count > 0
        
    def test_split_into_chunks_method(self):
        """Test _split_into_chunks exists."""
        from src.core.rag import RAGEngine
        
        engine = RAGEngine()
        
        # Method should exist
        assert hasattr(engine, '_split_into_chunks')


class TestRAGEngineGlobal:
    """Tests for global RAG engine instance."""
    
    def test_global_rag_instance(self):
        """Test global rag instance exists."""
        from src.core.rag import rag
        
        assert rag is not None
        
    def test_global_rag_is_engine(self):
        """Test global rag is RAGEngine instance."""
        from src.core.rag import rag, RAGEngine
        
        assert isinstance(rag, RAGEngine)
