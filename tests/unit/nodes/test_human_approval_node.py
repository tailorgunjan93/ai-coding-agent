import pytest
from src.main.agent.nodes.human_approval_node import HumanApprovalNode
from src.main.agent.models.agent_state import create_initial_state

@pytest.mark.asyncio
async def test_human_approval_node_auto_approve():
    node = HumanApprovalNode()
    state = create_initial_state("s1", "u1", "req")
    state["metadata"]["auto_approve"] = True
    
    updated_state = await node.run(state)
    assert updated_state["approval_status"] == "approved"

@pytest.mark.asyncio
async def test_human_approval_node_fails_without_approval():
    node = HumanApprovalNode()
    state = create_initial_state("s1", "u1", "req")
    
    with pytest.raises(Exception, match="Human approval required"):
        await node.run(state)
