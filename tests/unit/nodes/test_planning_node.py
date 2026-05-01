import pytest
from unittest.mock import AsyncMock, MagicMock
from src.main.agent.nodes.planning_node import PlanningNode
from src.main.agent.models.agent_state import create_initial_state

@pytest.mark.asyncio
async def test_planning_node_run():
    # Mock dependencies
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = {
        "content": "Project Plan: Step 1, Step 2",
        "usage": {},
        "model": "test"
    }
    mock_prompts = MagicMock()
    
    node = PlanningNode(llm_wrapper=mock_llm, prompt_wrapper=mock_prompts)
    
    # Create initial state
    state = create_initial_state("s1", "u1", "Build a calculator")
    
    # Run node
    updated_state = await node.run(state)
    
    # Verify
    assert updated_state["plan"] == "Project Plan: Step 1, Step 2"
    mock_llm.generate.assert_called_once()
    assert "calculator" in mock_llm.generate.call_args[0][0]
