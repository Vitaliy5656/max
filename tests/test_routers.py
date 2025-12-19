
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.core.routing import SmartRouter

@pytest.fixture
def mock_lm_client():
    mock = MagicMock()
    mock.chat = AsyncMock(return_value="Mocked response")
    return mock

@pytest.fixture
def mock_embedding_service():
    mock = MagicMock()
    mock.get_embedding = AsyncMock(return_value=[0.1] * 384)
    mock.get_embeddings = AsyncMock(return_value=[[0.1]*384])
    return mock

@pytest.mark.asyncio
async def test_router_thinking_triggers(mock_lm_client, mock_embedding_service):
    """Test that coding/analysis trigger thinking mode."""
    
    # Mock Semantic Router FACTORY inside Smart Router
    with patch("src.core.routing.smart_router.get_semantic_router") as mock_get:
        mock_router = MagicMock()
        mock_get.return_value = mock_router
        
        # We also need to mock the result object structure (SemanticMatch)
        from src.core.routing.semantic_router import SemanticMatch
        
        router = SmartRouter() # Logic doesn't need constructor args currently based on source?
        # Actually init sets up cache and stats. 
        # But wait, SmartRouter doesn't take lm_client in __init__ in the source I saw!
        # It imports get_semantic_router etc.
        
        # 1. Coding
        # Mock route return value
        mock_match = SemanticMatch(
            intent="coding", 
            score=0.9, 
            example_text="write python code",
            passed_threshold=True,
            topic="python"
        )
        mock_router.route.return_value = mock_match
        
        res = await router.route("Write python code")
        assert res.is_thinking_required == True
        assert res.intent == "coding"
        
        # 2. Analysis
        mock_match = SemanticMatch(
            intent="analysis", 
            score=0.9, 
            example_text="analyze data",
            passed_threshold=True, 
            topic="data"
        )
        mock_router.route.return_value = mock_match
        
        res = await router.route("Analyze this data")
        assert res.is_thinking_required == True
        
        # 3. Simple
        mock_match = SemanticMatch(
            intent="general", 
            score=0.9, 
            example_text="hello",
            passed_threshold=True, 
            topic="chat"
        )
        mock_router.route.return_value = mock_match
        
        res = await router.route("Hi")
        # "general" intent -> is_thinking_required logic:
        # if intent="general" and no system prompt -> pass (False)
        assert res.is_thinking_required == False
