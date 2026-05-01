"""
Human Approval Node - Gates human confirmation for sensitive operations.

This node pauses execution to wait for human approval
before proceeding with code generation.
"""

from typing import Any

from src.main.agent.nodes.base_node import BaseNode
from src.main.agent.models.agent_state import AgentState


class HumanApprovalNode(BaseNode):
    """
    Node responsible for human approval gates.

    This node:
    - Presents plan to human for review
    - Collects approval or rejection
    - Records approver information
    - Can require re-planning on rejection

    Dependencies:
        - planning (needs the plan to present)
    """

    def __init__(
        self,
        approval_timeout_seconds: int = 3600,
        require_explicit_approval: bool = True,
    ):
        """
        Initialize the human approval node.

        Args:
            approval_timeout_seconds: Max time to wait for approval.
            require_explicit_approval: If True, requires explicit approve/reject.
        """
        super().__init__(max_retries=0, timeout_seconds=approval_timeout_seconds)
        self._require_explicit = require_explicit_approval
        self._approval_timeout = approval_timeout_seconds

    @property
    def node_name(self) -> str:
        return "human_approval"

    @property
    def description(self) -> str:
        return "Gates execution for human approval"

    @property
    def input_schema(self) -> type:
        return AgentState

    @property
    def output_schema(self) -> type:
        # Returns dict with approval status
        return dict

    def get_required_dependencies(self) -> list[str]:
        return ["planning"]

    async def run(self, state: AgentState) -> AgentState:
        """
        Wait for human approval.
        For simulation, we assume auto-approval if a flag is set in metadata.
        """
        # In a real LangGraph app, this would be a __break__ or interrupt.
        # For unit testing, we check if it's already approved.
        if state.get("approval_status") == "approved":
            return state
            
        # Simulate auto-approval for testing
        if state.get("metadata", {}).get("auto_approve"):
            state["approval_status"] = "approved"
            state["approved_at"] = "now"
            return state
            
        raise Exception("Human approval required but not provided.")

