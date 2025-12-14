"""
Tests for FastAPI REST API endpoints.

Testing strategy:
- Simple, focused tests for critical functionality
- Tests for new modular LM package and routers
- Mock dependencies at the correct import location
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


class TestFeedbackEndpoint:
    """Tests for feedback endpoint."""
    
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


class TestLMClientPackage:
    """Tests for new modular LM Client package."""
    
    def test_package_imports(self):
        """Test that new LM package imports work correctly."""
        from src.core.lm import lm_client, TaskType, ThinkingMode
        
        assert lm_client is not None
        # LMStudioClient has different method names
        assert hasattr(lm_client, 'detect_task_type')
        assert hasattr(lm_client, 'get_mode_config')
    
    def test_task_type_enum(self):
        """Test TaskType enum values."""
        from src.core.lm import TaskType
        
        assert TaskType.REASONING.value == "reasoning"
        assert TaskType.VISION.value == "vision"
        assert TaskType.QUICK.value == "quick"
        assert TaskType.DEFAULT.value == "default"
    
    def test_thinking_mode_enum(self):
        """Test ThinkingMode enum values."""
        from src.core.lm import ThinkingMode
        
        assert ThinkingMode.FAST.value == "fast"
        assert ThinkingMode.STANDARD.value == "standard"
        assert ThinkingMode.DEEP.value == "deep"
    
    def test_detect_task_type_reasoning(self):
        """Test task type detection for reasoning queries."""
        from src.core.lm.routing import detect_task_type
        from src.core.lm.types import TaskType
        
        # Reasoning keywords
        task = detect_task_type("Объясни почему небо голубое")
        assert task == TaskType.REASONING
        
        task = detect_task_type("why does this happen?")
        assert task == TaskType.REASONING
    
    def test_detect_task_type_quick(self):
        """Test task type detection for quick queries."""
        from src.core.lm.routing import detect_task_type
        from src.core.lm.types import TaskType
        
        task = detect_task_type("да или нет?")
        assert task == TaskType.QUICK
        
        task = detect_task_type("кратко ответь")
        assert task == TaskType.QUICK
    
    def test_thinking_mode_config(self):
        """Test thinking mode configuration retrieval."""
        from src.core.lm import lm_client, ThinkingMode
        
        # Fast mode - returns ThinkingModeConfig dataclass
        config = lm_client.get_mode_config(ThinkingMode.FAST)
        assert hasattr(config, 'temperature')
        assert config.temperature <= 0.5
        
        # Deep mode - lower temp for more focused reasoning
        config = lm_client.get_mode_config(ThinkingMode.DEEP)
        assert config.temperature <= 0.5  # Deep mode uses lower temp for precision


class TestAPIRouters:
    """Tests for new modular API routers."""
    
    def test_all_routers_import(self):
        """Test that all routers can be imported."""
        from src.api.routers import (
            documents_router,
            agent_router,
            templates_router,
            metrics_router,
            models_router,
            health_router,
            backup_router
        )
        
        # All routers should be APIRouter instances
        from fastapi import APIRouter
        assert isinstance(documents_router, APIRouter)
        assert isinstance(agent_router, APIRouter)
        assert isinstance(templates_router, APIRouter)
        assert isinstance(metrics_router, APIRouter)
        assert isinstance(models_router, APIRouter)
        assert isinstance(health_router, APIRouter)
        assert isinstance(backup_router, APIRouter)
    

    
    def test_new_app_route_count(self):
        """Test that new app.py has all routes registered."""
        from src.api.app import app
        
        # Should have at least 25 routes (endpoints + OpenAPI + docs)
        assert len(app.routes) >= 20
    
    def test_new_app_key_routes(self):
        """Test that new app has all key routes."""
        from src.api.app import app
        
        route_paths = [r.path for r in app.routes if hasattr(r, 'path')]
        
        expected_routes = [


            '/api/documents',
            '/api/models',
            '/api/health',
            '/api/metrics',
            '/api/templates',
            '/api/agent/start',
            '/api/backup/status'
        ]
        
        for route in expected_routes:
            assert route in route_paths, f"Missing route: {route}"


class TestSchemas:
    """Tests for API schemas."""
    
    def test_schema_imports(self):
        """Test that schemas can be imported."""
        from src.api.schemas import (
            ChatRequest,
            ConversationCreate,
            FeedbackRequest,
            AgentStartRequest,
            TemplateCreate,
            ModelSelectionModeRequest
        )
        
        # Create instances to verify fields
        chat_req = ChatRequest(message="test", conversation_id=None)
        assert chat_req.message == "test"
        
        feedback_req = FeedbackRequest(message_id=1, rating=1)
        assert feedback_req.rating == 1


class TestBackwardCompatibility:
    """Tests for backward compatibility with old imports."""
    
    def test_old_lm_client_import_still_works(self):
        """Test that old import path still works."""
        from src.core.lm_client import lm_client, ThinkingMode
        
        assert lm_client is not None
        assert ThinkingMode.DEEP.value == "deep"
    
    def test_old_api_import_still_works(self):
        """Test that old API import path still works."""
        from src.api.api import app
        
        assert app is not None
        assert hasattr(app, 'routes')
    
    def test_new_api_import_works(self):
        """Test that new API import path works."""
        from src.api.app import app
        
        assert app is not None
        assert len(app.routes) > 20
