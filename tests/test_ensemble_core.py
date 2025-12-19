
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from src.core.cognitive.ensemble_loop import ensemble_thinking, EnsembleConfig, EnsembleResult
from src.core.cognitive.ensemble_types import EnsembleState

@pytest.fixture
def mock_lm_client():
    with patch("src.core.cognitive.ensemble_loop.lm_client") as mock:
        # Default mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Mocked Response"
        mock.chat = AsyncMock(return_value=mock_response)
        yield mock

@pytest.fixture
def mock_cpo():
    with patch("src.core.cognitive.ensemble_loop.cpo_engine") as mock:
        mock.get_preference = AsyncMock(return_value=("temp", 0.5))
        mock.record_preference = AsyncMock()
        mock.cpo_enabled = True # Config handled separately
        yield mock

@pytest.mark.asyncio
async def test_ensemble_basic_flow(mock_lm_client, mock_cpo):
    """Test full flow with mocked LLM."""
    
    # Configure mock for specific steps
    async def side_effect(*args, **kwargs):
        messages = kwargs.get("messages", [])
        prompt = messages[0]["content"] if messages else ""
        
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        
        if "эксперт" in prompt or "учитель" in prompt:
            content = "Draft Answer"
        elif "Ты интегратор" in prompt:
            content = "Synthesized Answer"
        elif "Ты критик" in prompt:
            content = "Valid critique"
        elif "Учитывая критику" in prompt:
            content = "Improved Answer"
        elif "Создай финальный ответ" in prompt:
            content = "Final Answer [WINNER: TEMP]"
        elif "Оцени качество ответа" in prompt:
            content = "9"
        elif "Предыдущий ответ получил низкую оценку" in prompt: # Mutation
            content = "Mutated Answer"
        else:
            print(f"UNMATCHED PROMPT: {prompt[:50]}...")
            content = "Generic Response"
            
        mock_resp.choices[0].message.content = content
        return mock_resp

    mock_lm_client.chat.side_effect = side_effect
    
    config = EnsembleConfig(
        timeout_total=10, # Short timeout for test
        max_mutations=0
    )
    
    # Run
    results = []
    async for event in ensemble_thinking("Question?", config=config):
        results.append(event)
        
    # Check
    assert len(results) > 0
    final_result = results[-1].get("result")
    assert final_result is not None
    assert final_result["answer"] == "Final Answer"
    assert final_result["final_score"] == 9.0
    
    # Check trace was recorded (mock needed for file io)
    # But function handles exception so it shouldn't fail test

@pytest.mark.asyncio
async def test_ensemble_mutation_success(mock_lm_client, mock_cpo):
    """Test that mutation triggers when score is low."""
    
    # State for the mock to track calls
    call_counts = {"verification": 0}

    async def side_effect(*args, **kwargs):
        messages = kwargs.get("messages", [])
        prompt = messages[0]["content"] if messages else ""
        
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        
        if "Оцени качество ответа" in prompt:
            call_counts["verification"] += 1
            if call_counts["verification"] == 1:
                content = "4" # Fail first time
            else:
                content = "9" # Pass second time
        elif "Предыдущий ответ получил низкую оценку" in prompt:
            content = "Mutated Improved Answer"
        elif "Создай финальный ответ" in prompt:
            content = "Final Answer"
        else:
            content = "Generic Response"
            
        mock_resp.choices[0].message.content = content
        return mock_resp

    mock_lm_client.chat.side_effect = side_effect
    
    config = EnsembleConfig(
        timeout_total=10,
        max_mutations=1,  # Enable mutation
        # verification_threshold removed as it is not a valid param
    )
    
    results = []
    async for event in ensemble_thinking("Hard Question?", config=config):
        results.append(event)
        
    final_result = results[-1].get("result")
    assert final_result is not None
    # We expect the score to be the improved one
    assert final_result["final_score"] == 9.0
    
@pytest.mark.asyncio
async def test_ensemble_fallback(mock_lm_client, mock_cpo):
    """Test graceful fallback on critical error."""
    
    # Force error immediately
    mock_lm_client.chat.side_effect = Exception("Critical LLM Failure")
    
    config = EnsembleConfig(timeout_total=5)
    
    results = []
    async for event in ensemble_thinking("Question?", config=config):
        results.append(event)
        
    # Should end with a result, not crash
    assert len(results) > 0
    final_result = results[-1].get("result")
    
    assert final_result is not None
    # Check that error is populated in the answer text
    assert "Critical LLM Failure" in final_result["answer"]
    assert final_result["final_score"] == 0.0
