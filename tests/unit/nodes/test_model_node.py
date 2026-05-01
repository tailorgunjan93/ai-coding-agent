import pytest
from unittest.mock import AsyncMock, MagicMock
from src.main.agent.nodes.model_node import ModelNode
from src.main.agent.models.agent_state import create_initial_state

@pytest.mark.asyncio
async def test_model_node_run():
    # Mock dependencies
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = {
        "content": "def hello(): print('world')",
        "usage": {},
        "model": "test"
    }
    
    node = ModelNode(llm_wrapper=mock_llm, prompt_wrapper=MagicMock())
    
    # Create initial state with a plan
    state = create_initial_state("s1", "u1", "req")
    state["plan"] = "Plan details"
    
    # Run node
    updated_state = await node.run(state)
    
    # Verify
    assert len(updated_state["artifacts"]) == 1
    assert updated_state["artifacts"][0]["path"] == "generated_code.py"
    assert "hello" in updated_state["artifacts"][0]["content"]
    mock_llm.generate.assert_called_once()
    assert "Plan details" in mock_llm.generate.call_args[0][0]
