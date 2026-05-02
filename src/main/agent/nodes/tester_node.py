"""
Tester Node - Generates test code and test runner commands.

Uses LLM to generate pytest tests and produces commands
to run the test suite.
"""

from typing import Any
import logging

from src.main.agent.nodes.base_node import BaseNode
from src.main.agent.models.agent_state import AgentState
from src.main.agent.models.test_result import TestResult, TestSummary

logger = logging.getLogger(__name__)


class TesterNode(BaseNode):
    """
    Node responsible for test generation and runner command output.

    This node:
    - Analyzes generated code structure
    - Uses LLM to generate pytest test files
    - Generates commands to run tests and collect coverage
    - Returns test artifacts and runner commands

    Dependencies:
        - model (needs generated code)
    """

    def __init__(
        self,
        llm_wrapper: Any,
        prompt_wrapper: Any,
        test_output_dir: str = "./tests",
        max_retries: int = 2,
    ):
        super().__init__(max_retries=max_retries, timeout_seconds=300)
        self._llm = llm_wrapper
        self._prompts = prompt_wrapper
        self._output_dir = test_output_dir

    @property
    def node_name(self) -> str:
        return "tester"

    @property
    def description(self) -> str:
        return "Generates tests and test runner commands"

    def get_required_dependencies(self) -> list[str]:
        return ["model"]

    def get_optional_dependencies(self) -> list[str]:
        return ["security"]

    async def run(self, state: AgentState) -> AgentState:
        """
        Generate tests for generated code and produce runner commands.

        Steps:
        1. Get generated code from state artifacts
        2. Build prompt for test generation
        3. Call LLM to generate test files
        4. Add test files as artifacts
        5. Generate test runner commands
        """
        artifacts = state.get("artifacts", [])
        code_files = [a for a in artifacts if a.get("type") == "file"]

        if not code_files:
            logger.warning("No code artifacts found, skipping test generation")
            state["test_report"] = {
                "status": "skipped",
                "reason": "No code files to test",
                "commands": [],
            }
            return state

        # Build code context for LLM
        code_context = "\n\n".join([
            f"# File: {f['path']}\n{f['content']}"
            for f in code_files
        ])

        # Generate tests via LLM
        prompt = (
            "Generate comprehensive pytest tests for the following Python code.\n"
            "Include:\n"
            "- Unit tests for each function/method\n"
            "- Edge case tests (empty input, None, large values)\n"
            "- Error handling tests\n"
            "- Use pytest fixtures where appropriate\n"
            "- Use clear, descriptive test names\n\n"
            f"Code to test:\n```python\n{code_context}\n```\n\n"
            "Output ONLY the test code, no explanations."
        )

        response = await self._llm.generate(prompt)
        test_content = response["content"]

        # Add test file as artifact
        state["artifacts"].append({
            "type": "file",
            "path": f"{self._output_dir}/test_generated.py",
            "content": test_content,
            "created_at": state.get("updated_at", ""),
            "category": "test",
        })

        # Generate test runner commands
        commands = [
            {
                "tool": "pytest",
                "command": f"pytest {self._output_dir}/ -v --tb=short",
                "description": "Run all tests with verbose output",
            },
            {
                "tool": "pytest-coverage",
                "command": f"pytest {self._output_dir}/ -v --cov=. --cov-report=html",
                "description": "Run tests with coverage report",
            },
            {
                "tool": "pytest-parallel",
                "command": f"pytest {self._output_dir}/ -v -n auto",
                "description": "Run tests in parallel (requires pytest-xdist)",
            },
        ]

        state["test_report"] = {
            "status": "generated",
            "test_files": [f"{self._output_dir}/test_generated.py"],
            "commands": commands,
            "model_used": response.get("model", "unknown"),
        }

        logger.info(f"Generated test file with {len(test_content.splitlines())} lines")
        return state
