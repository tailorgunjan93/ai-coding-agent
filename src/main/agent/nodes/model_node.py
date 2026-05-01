"""
Model Node - Generates code using LLM.

This node transforms plans into executable code using LLM generation
with context from the codebase and planning documents.
"""

from typing import Any

from src.main.agent.nodes.base_node import BaseNode
from src.main.agent.models.agent_state import AgentState


class ModelNode(BaseNode):
    """
    Node responsible for LLM-based code generation.

    This node:
    - Takes a plan and generates code files
    - Uses file context from the codebase
    - Applies design patterns as specified
    - Generates tests alongside production code

    Dependencies:
        - planning (needs the plan)
        - human_approval (needs approval)
    """

    def __init__(
        self,
        llm_wrapper: Any,
        prompt_wrapper: Any,
        code_output_dir: str = "./output",
        max_retries: int = 3,
    ):
        """
        Initialize the model node.

        Args:
            llm_wrapper: LLMWrapper for LLM access.
            prompt_wrapper: PromptWrapper for prompt templates.
            code_output_dir: Directory to write generated code.
            max_retries: Max retries for LLM calls.
        """
        super().__init__(max_retries=max_retries, timeout_seconds=300)
        self._llm = llm_wrapper
        self._prompts = prompt_wrapper
        self._output_dir = code_output_dir

    @property
    def node_name(self) -> str:
        return "model"

    @property
    def description(self) -> str:
        return "Generates code from plans using LLM"

    @property
    def input_schema(self) -> type:
        return AgentState

    @property
    def output_schema(self) -> type:
        # Returns dict with generated files
        return dict

    def get_required_dependencies(self) -> list[str]:
        return ["planning", "human_approval"]

    async def run(self, state: AgentState) -> AgentState:
        """
        Generate code from the current plan.
        """
        prompt = f"Generate code for the following plan: {state['plan']}"
        response = await self._llm.generate(prompt)
        
        # Add to artifacts
        state["artifacts"].append({
            "type": "file",
            "path": "generated_code.py",
            "content": response["content"],
            "created_at": "now"
        })
        return state

