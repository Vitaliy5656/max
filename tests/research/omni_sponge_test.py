"""
Final Verification Test for Project Omni-Sponge.
"""

import asyncio
import sys
import os
import json
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.research.deep_research import DeepResearchAgent, RunStatus
from src.core.quantum.titans_engine import TitansEngine

async def test_omni_sponge_loop():
    print("Starting Omni-Sponge Verification Test (Final)...")
    
    # 1. Setup Mock DB
    db = MagicMock()
    cursor_mock = AsyncMock()
    class AsyncCM:
        async def __aenter__(self): return cursor_mock
        async def __aexit__(self, *args): pass
        def __await__(self):
            async def _wrap(): return self
            return _wrap().__await__()
    db.execute.return_value = AsyncCM()
    db.commit = AsyncMock()
    
    # 2. Setup Agent
    agent = DeepResearchAgent(db)
    await agent.initialize(db)
    
    # 3. Mock Planner
    mock_planner = AsyncMock()
    mock_planner.create_initial_plan.return_value = [
        {"stage": "Phase1", "description": "Part One"},
        {"stage": "Phase2", "description": "Part Two"}
    ]
    agent._planner = mock_planner

    # 4. Mock LM Client
    from src.core.lm_client import lm_client
    
    surprise_values = [0.3, 0.25, 0.22, 0.18, 0.15, 0.08, 0.05, 0.03, 0.02, 0.01]
    surprise_ptr = 0
    
    async def mock_get_embedding(text):
        return [0.1] * 1024
    lm_client.get_embedding = AsyncMock(side_effect=mock_get_embedding)

    # Mock Titans process_signal
    from src.core.memory import memory
    original_process_signal = memory.titans.process_signal
    async def mock_process_signal(embedding):
        nonlocal surprise_ptr
        val = surprise_values[min(surprise_ptr, len(surprise_values)-1)]
        surprise_ptr += 1
        memory.titans.surprise_history.append(val)
        return {
            "surprise": val,
            "is_stored": val > 0.1,
            "recall_embedding": [0.0]*1024,
            "saturation": memory.titans.get_saturation_level()
        }
    memory.titans.process_signal = AsyncMock(side_effect=mock_process_signal)

    # Mock LM Chat
    async def mock_chat(*args, **kwargs):
        messages = kwargs.get('messages', args[0] if args else [])
        prompt = messages[-1]['content'] if messages else ""
        
        # Action selector
        if "Что нужно сделать следующим шагом?" in prompt:
            # Check history to decide
            history = prompt.split("Previous Steps:\n")[1] if "Previous Steps:\n" in prompt else ""
            
            if "read_webpage" in history and "save_knowledge" not in history.split("read_webpage")[-1]:
                return json.dumps({
                    "action": "save_knowledge",
                    "action_input": {"content": "Found Fact", "batch": ["Fact A", "Fact B"]},
                    "is_final": False
                })
            
            if "web_search" in history and "read_webpage" not in history.split("web_search")[-1]:
                return json.dumps({
                    "action": "read_webpage",
                    "action_input": {"url": "http://example.com/topic-x"},
                    "is_final": False
                })

            return json.dumps({
                "action": "web_search",
                "action_input": {"query": "Search for more"},
                "is_final": False
            })
            
        if "Information Forager" in prompt:
            return "[0]"
            
        return "Generic response"
    lm_client.chat = AsyncMock(side_effect=mock_chat)

    # 5. Mock Tools
    from src.core.tools import tools
    async def mock_tool_execute(action, action_input):
        if action == "read_webpage":
            return "This is a very long text " * 20 + ' <a href="http://topic-y.com">Lead Y</a>'
        if action == "web_search":
            return "Results: URL: http://example.com/topic-x"
        return "[OK] Success (IDs: [1, 2])"
    tools.execute = AsyncMock(side_effect=mock_tool_execute)

    # 6. Execute Run
    run = await agent.set_goal("Test Omni-Sponge", max_steps=10, use_editable_cot=False)
    
    steps_count = 0
    async for step in agent.run_generator(max_steps=10):
        steps_count += 1
        print(f"Step {steps_count}: {step.action} -> {step.status.value}")
        if agent._discovery_stack:
            print(f"  [STACK] Leads: {len(agent._discovery_stack)}")
        if hasattr(agent, '_last_saturation'):
            print(f"  [SAT] {agent._last_saturation:.2f}")
        
        # New stats check
        if agent._current_run and agent._current_run.stats:
            s = agent._current_run.stats
            print(f"  [HARVEST] Read: {s['articles_read']}, Sites: {s['sites_visited']}, Facts: {s['facts_saved']}")

    print(f"\nFinal Saturation: {getattr(agent, '_last_saturation', 0):.2f}")
    print(f"Stack size: {len(agent._discovery_stack)}")
    if agent._current_run:
        print(f"Final Stats: {agent._current_run.stats}")
    
    # Restore
    memory.titans.process_signal = original_process_signal

if __name__ == "__main__":
    asyncio.run(test_omni_sponge_loop())
