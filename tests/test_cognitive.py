"""
Unit Tests for Cognitive Loop Components.

Tests the cognitive architecture nodes:
- Planner
- Executor  
- Verifier
- Memory
- Graph routing
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Import cognitive components
from src.core.cognitive.types import CognitiveState, CognitiveConfig, DEFAULT_COGNITIVE_CONFIG
from src.core.cognitive.graph import route_verification, build_cognitive_graph


# ============== Fixtures ==============

@pytest.fixture
def empty_state() -> CognitiveState:
    """Create an empty cognitive state for testing."""
    return {
        "input": "Test question",
        "conversation_id": "test-123",
        "user_context": None,
        "plan": None,
        "steps": [],
        "draft_answer": "",
        "critique": "",
        "score": 0.0,
        "iterations": 0,
        "total_iterations": 0,
        "past_failures": [],
        "thinking_tokens": [],
        "step_name": None,
        "step_content": None,
        "status": "planning"
    }


@pytest.fixture
def good_state(empty_state) -> CognitiveState:
    """State with a good score that should be accepted."""
    return {**empty_state, "score": 0.85, "draft_answer": "Good answer"}


@pytest.fixture
def failing_state(empty_state) -> CognitiveState:
    """State with a low score that needs re-planning."""
    return {**empty_state, "score": 0.2, "iterations": 1, "total_iterations": 1}


# ============== route_verification Tests ==============

class TestRouteVerification:
    """Tests for the route_verification function."""
    
    def test_accept_high_score(self, good_state):
        """High score should route to accept."""
        result = route_verification(good_state)
        assert result == "accept"
    
    def test_accept_on_threshold(self, empty_state):
        """Score exactly at threshold should accept."""
        empty_state["score"] = 0.75
        result = route_verification(empty_state)
        assert result == "accept"
    
    def test_refine_medium_score(self, empty_state):
        """Medium score should route to refine."""
        empty_state["score"] = 0.5
        empty_state["iterations"] = 1
        result = route_verification(empty_state)
        assert result == "refine"
    
    def test_replan_low_score(self, failing_state):
        """Very low score should route to replan."""
        result = route_verification(failing_state)
        assert result == "replan"
    
    def test_abort_max_iterations(self, empty_state):
        """Max iterations with low score should abort."""
        empty_state["score"] = 0.4
        empty_state["iterations"] = 5
        result = route_verification(empty_state)
        assert result == "abort"
    
    def test_abort_max_total_iterations(self, empty_state):
        """Max total iterations should force decision."""
        empty_state["score"] = 0.4
        empty_state["total_iterations"] = 10
        result = route_verification(empty_state)
        assert result == "abort"
    
    def test_accept_after_max_total_if_decent(self, empty_state):
        """If total_iterations maxed but score decent, accept."""
        empty_state["score"] = 0.55
        empty_state["total_iterations"] = 10
        result = route_verification(empty_state)
        assert result == "accept"


# ============== Verifier Tests ==============

class TestVerifier:
    """Tests for the verifier node."""
    
    @pytest.mark.asyncio
    async def test_verifier_empty_draft(self, empty_state):
        """Empty draft should get low score."""
        from src.core.cognitive.nodes.verifier import verify_answer
        
        empty_state["draft_answer"] = ""
        result = await verify_answer(empty_state)
        
        assert result["score"] == 0.1
        assert "empty" in result["critique"].lower()
    
    @pytest.mark.asyncio
    async def test_verifier_returns_step_info(self, good_state):
        """Verifier should return step_name and step_content."""
        from src.core.cognitive.nodes.verifier import verify_answer
        
        with patch('src.core.cognitive.nodes.verifier.lm_client') as mock_lm:
            mock_lm.chat = AsyncMock(return_value='{"score": 0.8, "critique": "Good job"}')
            
            result = await verify_answer(good_state)
            
            assert "step_name" in result
            assert result["step_name"] == "Verifier"
            assert "step_content" in result


# ============== Planner Tests ==============

class TestPlanner:
    """Tests for the planner node."""
    
    @pytest.mark.asyncio
    async def test_planner_generates_plan(self, empty_state):
        """Planner should generate a plan from input."""
        from src.core.cognitive.nodes.planner import plan_task
        
        with patch('src.core.cognitive.nodes.planner.lm_client') as mock_lm:
            mock_lm.chat = AsyncMock(return_value="1. Analyze question\n2. Research\n3. Answer")
            
            result = await plan_task(empty_state)
            
            assert "plan" in result
            assert len(result["plan"]) > 0
            assert result["iterations"] == 0
    
    @pytest.mark.asyncio
    async def test_planner_replan_increments_total(self, empty_state):
        """Re-planning should increment total_iterations."""
        from src.core.cognitive.nodes.planner import plan_task
        
        empty_state["plan"] = "Old plan"
        empty_state["past_failures"] = ["Previous attempt failed"]
        empty_state["total_iterations"] = 3
        
        with patch('src.core.cognitive.nodes.planner.lm_client') as mock_lm:
            mock_lm.chat = AsyncMock(return_value="New better plan")
            
            result = await plan_task(empty_state)
            
            assert result["total_iterations"] == 4
            assert result["iterations"] == 0  # Reset for new plan


# ============== Memory Tests ==============

class TestMemory:
    """Tests for the memory node."""
    
    @pytest.mark.asyncio
    async def test_memory_summarize_failure(self, empty_state):
        """Memory should summarize failures and increment counters."""
        from src.core.cognitive.nodes.memory import summarize_failure
        
        empty_state["critique"] = "The answer lacks depth and specific examples."
        empty_state["score"] = 0.4
        empty_state["iterations"] = 2
        empty_state["total_iterations"] = 3
        
        result = await summarize_failure(empty_state)
        
        assert len(result["past_failures"]) == 1
        assert result["iterations"] == 3
        assert result["total_iterations"] == 4
    
    @pytest.mark.asyncio
    async def test_memory_rolling_window(self, empty_state):
        """Memory should keep only last 3 failures."""
        from src.core.cognitive.nodes.memory import summarize_failure
        
        empty_state["past_failures"] = ["Old 1", "Old 2", "Old 3"]
        empty_state["critique"] = "New failure"
        empty_state["iterations"] = 4
        
        result = await summarize_failure(empty_state)
        
        assert len(result["past_failures"]) == 3
        assert "New failure" in result["past_failures"][-1]


# ============== Executor Tests ==============

class TestExecutor:
    """Tests for the executor node."""
    
    @pytest.mark.asyncio
    async def test_executor_uses_plan(self, empty_state):
        """Executor should use the plan in prompts."""
        from src.core.cognitive.nodes.executor import execute_with_cot
        
        empty_state["plan"] = "1. Step one\n2. Step two"
        
        with patch('src.core.cognitive.nodes.executor.lm_client') as mock_lm:
            mock_lm.chat = AsyncMock(return_value="Here is my answer based on the plan")
            
            result = await execute_with_cot(empty_state)
            
            assert "draft_answer" in result
            assert len(result["draft_answer"]) > 0
            mock_lm.chat.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_executor_handles_empty_response(self, empty_state):
        """Executor should handle empty LLM response gracefully."""
        from src.core.cognitive.nodes.executor import execute_with_cot
        
        with patch('src.core.cognitive.nodes.executor.lm_client') as mock_lm:
            mock_lm.chat = AsyncMock(return_value="")
            
            result = await execute_with_cot(empty_state)
            
            # Should have a fallback message
            assert "draft_answer" in result
            assert len(result["draft_answer"]) > 0


# ============== Config Tests ==============

class TestCognitiveConfig:
    """Tests for CognitiveConfig."""
    
    def test_default_config_values(self):
        """Default config should have sensible values."""
        config = DEFAULT_COGNITIVE_CONFIG
        
        assert config.max_iterations_per_plan == 5
        assert config.max_total_iterations == 10
        assert config.accept_threshold == 0.75
        assert config.timeout_seconds == 180


# ============== Integration Test ==============

class TestCognitiveGraph:
    """Integration tests for the cognitive graph."""
    
    def test_graph_builds(self):
        """Graph should build without errors."""
        graph = build_cognitive_graph()
        assert graph is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
