"""
Tests for FastAPI REST API endpoints.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_returns_ok(self):
        """Test /api/health returns ok."""
        from fastapi.testclient import TestClient
        
        with patch('src.api.api.memory'), \
             patch('src.api.api.lm_client'), \
             patch('src.api.api.rag'), \
             patch('src.api.api.templates'), \
             patch('src.api.api.metrics_engine'):
            
            from src.api.api import app
            client = TestClient(app)
            
            response = client.get("/api/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"


class TestConversationEndpoints:
    """Tests for conversation endpoints."""
    
    def test_list_conversations_empty(self):
        """Test listing conversations when empty."""
        with patch('src.api.api.memory') as mock_memory, \
             patch('src.api.api.lm_client'), \
             patch('src.api.api.rag'), \
             patch('src.api.api.templates'), \
             patch('src.api.api.metrics_engine'):
            
            mock_memory.get_conversations = AsyncMock(return_value=[])
            
            from src.api.api import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            
            response = client.get("/api/conversations")
            
            assert response.status_code == 200
            assert response.json() == []
            
    def test_create_conversation(self):
        """Test creating a conversation."""
        with patch('src.api.api.memory') as mock_memory, \
             patch('src.api.api.lm_client'), \
             patch('src.api.api.rag'), \
             patch('src.api.api.templates'), \
             patch('src.api.api.metrics_engine'):
            
            mock_memory.create_conversation = AsyncMock(return_value="conv-123")
            
            from src.api.api import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            
            response = client.post("/api/conversations", json={"title": "Test"})
            
            assert response.status_code == 200
            data = response.json()
            assert "id" in data


class TestDocumentEndpoints:
    """Tests for RAG document endpoints."""
    
    def test_list_documents_empty(self):
        """Test listing documents when empty."""
        with patch('src.api.api.memory'), \
             patch('src.api.api.lm_client'), \
             patch('src.api.api.rag') as mock_rag, \
             patch('src.api.api.templates'), \
             patch('src.api.api.metrics_engine'):
            
            mock_rag.get_documents = AsyncMock(return_value=[])
            
            from src.api.api import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            
            response = client.get("/api/documents")
            
            assert response.status_code == 200
            assert response.json() == []
            
    def test_delete_document(self):
        """Test deleting a document."""
        with patch('src.api.api.memory'), \
             patch('src.api.api.lm_client'), \
             patch('src.api.api.rag') as mock_rag, \
             patch('src.api.api.templates'), \
             patch('src.api.api.metrics_engine'):
            
            mock_rag.delete_document = AsyncMock(return_value=True)
            
            from src.api.api import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            
            response = client.delete("/api/documents/doc-123")
            
            assert response.status_code == 200


class TestMetricsEndpoints:
    """Tests for metrics endpoints."""
    
    def test_get_metrics(self):
        """Test getting IQ/EQ metrics."""
        with patch('src.api.api.memory'), \
             patch('src.api.api.lm_client'), \
             patch('src.api.api.rag'), \
             patch('src.api.api.templates'), \
             patch('src.api.api.metrics_engine') as mock_metrics:
            
            mock_metrics.get_metrics = AsyncMock(return_value={
                "iq": {"score": 75, "components": {}},
                "empathy": {"score": 68, "components": {}}
            })
            
            from src.api.api import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            
            response = client.get("/api/metrics")
            
            assert response.status_code == 200
            data = response.json()
            assert "iq" in data
            assert "empathy" in data
            
    def test_submit_feedback(self):
        """Test submitting feedback."""
        with patch('src.api.api.memory') as mock_memory, \
             patch('src.api.api.lm_client'), \
             patch('src.api.api.rag'), \
             patch('src.api.api.templates'), \
             patch('src.api.api.metrics_engine') as mock_metrics:
            
            mock_memory.save_feedback = AsyncMock(return_value=True)
            mock_metrics.record_interaction_outcome = AsyncMock()
            
            from src.api.api import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            
            response = client.post("/api/feedback", json={
                "message_id": 1,
                "rating": 1
            })
            
            assert response.status_code == 200


class TestTemplatesEndpoints:
    """Tests for templates endpoints."""
    
    def test_list_templates(self):
        """Test listing templates."""
        with patch('src.api.api.memory'), \
             patch('src.api.api.lm_client'), \
             patch('src.api.api.rag'), \
             patch('src.api.api.templates') as mock_templates, \
             patch('src.api.api.metrics_engine'):
            
            mock_templates.get_all = AsyncMock(return_value=[
                {"id": "1", "name": "Code Review", "content": "Review: {code}", "category": "Dev"}
            ])
            
            from src.api.api import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            
            response = client.get("/api/templates")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "Code Review"


class TestModelsEndpoint:
    """Tests for models endpoint."""
    
    def test_get_models(self):
        """Test getting available models."""
        with patch('src.api.api.memory'), \
             patch('src.api.api.lm_client') as mock_lm, \
             patch('src.api.api.rag'), \
             patch('src.api.api.templates'), \
             patch('src.api.api.metrics_engine'):
            
            mock_lm.get_available_models = MagicMock(return_value=[
                {"id": "gpt-4", "name": "GPT-4"}
            ])
            
            from src.api.api import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            
            response = client.get("/api/models")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1
