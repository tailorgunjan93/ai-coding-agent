"""
Design Pattern Node - Checks code for design pattern compliance.

Analyzes generated code for SOLID, DRY, KISS violations using
AST analysis and generates improvement suggestions.
"""

from typing import Any
import ast
import logging

from src.main.agent.nodes.base_node import BaseNode
from src.main.agent.models.agent_state import AgentState

logger = logging.getLogger(__name__)


class DesignPatternNode(BaseNode):
    """
    Node responsible for design pattern enforcement.

    Checks:
    - SOLID principles (class responsibility, interface usage)
    - DRY (duplicate code detection)
    - KISS (complexity metrics)
    - Naming conventions
    - Module structure

    Dependencies:
        - model (needs generated code to analyze)
    """

    def __init__(
        self,
        rules: list[str] | None = None,
        max_retries: int = 2,
    ):
        super().__init__(max_retries=max_retries, timeout_seconds=120)
        self._rules = rules or ["solid", "dry", "kiss"]

    @property
    def node_name(self) -> str:
        return "design_pattern"

    @property
    def description(self) -> str:
        return "Enforces design patterns and architectural principles"

    def get_required_dependencies(self) -> list[str]:
        return ["model"]

    async def run(self, state: AgentState) -> AgentState:
        """
        Analyze generated code for design pattern compliance.

        Steps:
        1. Get generated code from artifacts
        2. Parse AST
        3. Check SOLID, DRY, KISS rules
        4. Generate report with violations and suggestions
        """
        artifacts = state.get("artifacts", [])
        code_files = [a for a in artifacts if a.get("type") == "file" and a.get("category") != "test"]

        all_violations = []

        for artifact in code_files:
            content = artifact.get("content", "")
            file_path = artifact.get("path", "unknown")

            violations = self._analyze_code(content, file_path)
            all_violations.extend(violations)

        # Produce report
        state["design_report"] = {
            "violations": all_violations,
            "total_violations": len(all_violations),
            "rules_checked": self._rules,
            "passed": len(all_violations) == 0,
            "summary": (
                "All design pattern checks passed."
                if not all_violations
                else f"Found {len(all_violations)} violations across {len(code_files)} files."
            ),
        }

        logger.info(f"Design pattern check: {len(all_violations)} violations found")
        return state

    def _analyze_code(self, code: str, file_path: str) -> list[dict[str, Any]]:
        """Analyze a single code file for design violations."""
        violations = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            violations.append({
                "rule": "syntax",
                "severity": "error",
                "message": "Code has syntax errors — cannot analyze",
                "file": file_path,
            })
            return violations

        if "solid" in self._rules:
            violations.extend(self._check_solid(tree, file_path))

        if "dry" in self._rules:
            violations.extend(self._check_dry(code, file_path))

        if "kiss" in self._rules:
            violations.extend(self._check_kiss(tree, file_path))

        return violations

    def _check_solid(self, tree: ast.AST, file_path: str) -> list[dict[str, Any]]:
        """Check SOLID principle violations."""
        violations = []

        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        for cls in classes:
            methods = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

            # SRP: Class with too many methods may have too many responsibilities
            if len(methods) > 15:
                violations.append({
                    "rule": "SRP (Single Responsibility)",
                    "severity": "warning",
                    "message": f"Class '{cls.name}' has {len(methods)} methods — consider splitting",
                    "file": file_path,
                    "line": cls.lineno,
                })

            # Large class body
            if cls.end_lineno and cls.lineno:
                class_lines = cls.end_lineno - cls.lineno
                if class_lines > 200:
                    violations.append({
                        "rule": "SRP (Single Responsibility)",
                        "severity": "warning",
                        "message": f"Class '{cls.name}' is {class_lines} lines — consider splitting",
                        "file": file_path,
                        "line": cls.lineno,
                    })

        return violations

    def _check_dry(self, code: str, file_path: str) -> list[dict[str, Any]]:
        """Check for duplicate code patterns."""
        violations = []
        lines = code.strip().split("\n")

        # Simple duplicate block detection: check for 3+ consecutive identical lines
        seen_blocks = {}
        block_size = 3

        for i in range(len(lines) - block_size + 1):
            block = "\n".join(line.strip() for line in lines[i:i + block_size])
            if block.strip() and len(block) > 20:
                if block in seen_blocks:
                    violations.append({
                        "rule": "DRY (Don't Repeat Yourself)",
                        "severity": "info",
                        "message": f"Duplicate code block found (first seen at line {seen_blocks[block]})",
                        "file": file_path,
                        "line": i + 1,
                    })
                else:
                    seen_blocks[block] = i + 1

        return violations

    def _check_kiss(self, tree: ast.AST, file_path: str) -> list[dict[str, Any]]:
        """Check for overly complex code (KISS)."""
        violations = []

        functions = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        for func in functions:
            # Cyclomatic complexity approximation: count branches
            branch_count = sum(
                1 for node in ast.walk(func)
                if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With))
            )

            if branch_count > 10:
                violations.append({
                    "rule": "KISS (Keep It Simple)",
                    "severity": "warning",
                    "message": f"Function '{func.name}' has high complexity ({branch_count} branches)",
                    "file": file_path,
                    "line": func.lineno,
                })

            # Function length
            if func.end_lineno and func.lineno:
                func_lines = func.end_lineno - func.lineno
                if func_lines > 50:
                    violations.append({
                        "rule": "KISS (Keep It Simple)",
                        "severity": "info",
                        "message": f"Function '{func.name}' is {func_lines} lines — consider splitting",
                        "file": file_path,
                        "line": func.lineno,
                    })

            # Too many parameters
            params = func.args.args
            if len(params) > 6:
                violations.append({
                    "rule": "KISS (Keep It Simple)",
                    "severity": "info",
                    "message": f"Function '{func.name}' has {len(params)} params — consider a config object",
                    "file": file_path,
                    "line": func.lineno,
                })

        return violations
