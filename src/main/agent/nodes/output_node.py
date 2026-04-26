"""
Output Node - Aggregates and formats final output.

This node collects results from all previous nodes and
produces the final response for the user.
"""

from typing import Any

from src.main.agent.nodes.base_node import BaseNode
from src.main.agent.interfaces.node_interface import NodeExecutionContext
from src.main.agent.models.agent_state import AgentState


class OutputNode(BaseNode):
    """
    Node responsible for output aggregation and formatting.

    This node:
    - Collects results from all previous nodes
    - Formats output for the user
    - Generates summary reports
    - Creates artifacts for download

    Dependencies:
        - All preceding nodes (for result aggregation)
    """

    def __init__(
        self,
        output_format: str = "markdown",
        max_retries: int = 1,
    ):
        """
        Initialize the output node.

        Args:
            output_format: Format for output (markdown, json, html).
            max_retries: Max retries for output generation.
        """
        super().__init__(max_retries=max_retries, timeout_seconds=60)
        self._format = output_format

    @property
    def node_name(self) -> str:
        return "output"

    @property
    def description(self) -> str:
        return "Aggregates and formats final output for user"

    @property
    def input_schema(self) -> type:
        return AgentState

    @property
    def output_schema(self) -> type:
        return dict

    def get_required_dependencies(self) -> list[str]:
        # Aggregates all node outputs
        return ["cicd"]

    async def _execute(
        self,
        state: dict,
        context: NodeExecutionContext,
    ) -> dict[str, Any]:
        """
        Aggregate and format final output.

        Steps:
        1. Collect all node outputs from state
        2. Aggregate success/failure status
        3. Generate summary
        4. Format according to output_format
        5. Return formatted response

        Args:
            state: Current workflow state.
            context: Execution context.

        Returns:
            Dict with formatted output and metadata.
        """
        # TODO: Implement output aggregation
        raise NotImplementedError(
            "OutputNode._execute() not yet implemented. "
            "See LLD.md for implementation guidance."
        )
