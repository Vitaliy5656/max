"""
Pytest configuration and fixtures for MAX AI tests.
"""
import asyncio
import sys
import os
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============= Event Loop =============

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============= Mock LLM Client =============

@pytest.fixture
def mock_lm_client():
    """Mock LLM client for unit tests."""
    mock = MagicMock()
    mock.chat_completion = AsyncMock(return_value="Mocked AI response")
    mock.stream_chat_completion = AsyncMock()
    mock.get_available_models = MagicMock(return_value=["mock-model"])
    mock.current_model = "mock-model"
    return mock


@pytest.fixture
def mock_streaming_response():
    """Mock streaming response generator."""
    async def stream():
        for token in ["Hello", " ", "World", "!"]:
            yield token
    return stream


# ============= Mock Database =============

@pytest.fixture
def mock_db():
    """Mock database connection."""
    mock = MagicMock()
    mock.execute = AsyncMock()
    mock.executemany = AsyncMock()
    mock.fetchone = AsyncMock(return_value=None)
    mock.fetchall = AsyncMock(return_value=[])
    mock.commit = AsyncMock()
    return mock


@pytest.fixture
def sample_conversation():
    """Sample conversation data."""
    return {
        "id": "test-conv-1",
        "title": "Test Conversation",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "message_count": 2
    }


@pytest.fixture
def sample_messages():
    """Sample messages data."""
    return [
        {"id": 1, "role": "user", "content": "Hello", "created_at": "2024-01-01T00:00:00"},
        {"id": 2, "role": "assistant", "content": "Hi there!", "created_at": "2024-01-01T00:00:01"}
    ]


@pytest.fixture
def sample_document():
    """Sample RAG document."""
    return {
        "id": "doc-1",
        "name": "test.txt",
        "type": "text/plain",
        "chunks": 5,
        "status": "indexed"
    }


@pytest.fixture
def sample_template():
    """Sample prompt template."""
    return {
        "id": "tpl-1",
        "name": "Code Review",
        "content": "Review this code: {code}",
        "category": "Dev"
    }


# ============= Mock Metrics =============

@pytest.fixture
def sample_metrics():
    """Sample IQ/EQ metrics."""
    return {
        "iq": {
            "score": 75,
            "components": {
                "accuracy": 80,
                "first_try": 70,
                "correction_rate": 75
            }
        },
        "empathy": {
            "score": 68,
            "components": {
                "profile_completeness": 60,
                "mood_success": 70,
                "anticipation_rate": 74
            }
        }
    }


@pytest.fixture
def sample_feedback_signals():
    """Sample feedback analysis signals."""
    return {
        "positive": ["спасибо", "отлично", "супер"],
        "negative": ["не то", "неправильно", "опять"],
        "correction": ["я имел в виду", "нет, другое"]
    }


# ============= Test Client for FastAPI =============

@pytest.fixture
def test_client():
    """Create test client for FastAPI."""
    from fastapi.testclient import TestClient
    
    # Import with mocked dependencies
    with patch('src.api.api.memory') as mock_memory, \
         patch('src.api.api.lm_client') as mock_lm, \
         patch('src.api.api.rag') as mock_rag:
        
        mock_memory.get_conversations = AsyncMock(return_value=[])
        mock_lm.chat_completion = AsyncMock(return_value="Test response")
        mock_rag.search = AsyncMock(return_value=[])
        
        from src.api.api import app
        client = TestClient(app)
        yield client


# ============= Temporary Files =============

@pytest.fixture
def temp_file(tmp_path):
    """Create temporary test file."""
    file_path = tmp_path / "test_document.txt"
    file_path.write_text("This is test content for RAG indexing.")
    return file_path
