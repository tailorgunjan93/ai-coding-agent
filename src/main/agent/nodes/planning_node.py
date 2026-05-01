"""
Planning Node - Generates structured plans from user requests.

This node transforms raw user requests into detailed execution plans
with tasks, dependencies, risks, and technology choices.
"""

from typing import Any

from src.main.agent.nodes.base_node import BaseNode
from src.main.agent.models.agent_state import AgentState
from src.main.agent.models.plan_schema import PlanSchema


class PlanningNode(BaseNode):
    """
    Node responsible for creating structured plans from user requests.

    This node uses LLM to generate a comprehensive plan that includes:
    - Project requirements and architecture overview
    - Task breakdown with dependencies
    - Risk assessment and mitigation strategies
    - Technology stack recommendations
    - Human approval gate

    Dependencies:
        - input (must run first to validate the request)
    """

    def __init__(
        self,
        llm_wrapper: Any,
        prompt_wrapper: Any,
        output_dir: str = "./planning",
        max_retries: int = 2,
    ):
        """
        Initialize the planning node.

        Args:
            llm_wrapper: LLMWrapper for LLM access.
            prompt_wrapper: PromptWrapper for prompt templates.
            output_dir: Directory to write planning.md.
            max_retries: Max retries for LLM calls.
        """
        super().__init__(max_retries=max_retries, timeout_seconds=120)
        self._llm = llm_wrapper
        self._prompts = prompt_wrapper
        self._output_dir = output_dir

    @property
    def node_name(self) -> str:
        return "planning"

    @property
    def description(self) -> str:
        return "Generates structured plans from user requests using LLM"

    @property
    def input_schema(self) -> type:
        return AgentState

    @property
    def output_schema(self) -> type:
        return PlanSchema

    def get_required_dependencies(self) -> list[str]:
        return ["input"]

    async def run(self, state: AgentState) -> AgentState:
        """
        Generate a structured plan from the user's request.
        """
        prompt = f"Create a project plan for: {state['original_request']}"
        response = await self._llm.generate(prompt)
        
        state["plan"] = response["content"]
        state["updated_at"] = "now" # In real app use datetime
        return state


