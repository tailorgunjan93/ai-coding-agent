"""
Output Node - Aggregates and formats final workflow output.

Collects results from all previous nodes and produces
a formatted summary for the user.
"""

from typing import Any
import logging
from datetime import datetime, timezone

from src.main.agent.nodes.base_node import BaseNode
from src.main.agent.models.agent_state import AgentState

logger = logging.getLogger(__name__)


class OutputNode(BaseNode):
    """
    Node responsible for output aggregation and formatting.

    Collects results from all nodes and produces:
    - Formatted summary (markdown/JSON)
    - File manifest
    - Command checklist
    - Error report

    Dependencies:
        - All preceding nodes (for result aggregation)
    """

    def __init__(
        self,
        output_format: str = "markdown",
        max_retries: int = 1,
    ):
        super().__init__(max_retries=max_retries, timeout_seconds=60)
        self._format = output_format

    @property
    def node_name(self) -> str:
        return "output"

    @property
    def description(self) -> str:
        return "Aggregates and formats final output for user"

    def get_required_dependencies(self) -> list[str]:
        return ["model"]

    async def run(self, state: AgentState) -> AgentState:
        """
        Aggregate and format final output.

        Steps:
        1. Collect all artifacts
        2. Collect all commands from nodes
        3. Collect security and test reports
        4. Generate formatted summary
        """
        artifacts = state.get("artifacts", [])
        errors = state.get("errors", [])

        # Collect files
        code_files = [a for a in artifacts if a.get("type") == "file" and a.get("category") != "test"]
        test_files = [a for a in artifacts if a.get("type") == "file" and a.get("category") == "test"]
        cicd_files = [a for a in artifacts if a.get("type") == "file" and a.get("category") == "cicd"]
        migration_files = [a for a in artifacts if a.get("type") == "file" and a.get("category") == "migration"]

        # Collect commands from all nodes
        all_commands = []
        for key in ["git_commands", "cicd_config", "test_report", "db_config"]:
            node_output = state.get(key, {})
            cmds = node_output.get("commands", [])
            all_commands.extend(cmds)

        # Collect reports
        security_report = state.get("security_report", {})
        design_report = state.get("design_report", {})
        test_report = state.get("test_report", {})

        # Build summary
        if self._format == "markdown":
            summary = self._format_markdown(
                state, code_files, test_files, cicd_files,
                migration_files, all_commands, security_report,
                design_report, test_report, errors,
            )
        else:
            summary = self._format_json(
                state, code_files, test_files, all_commands,
                security_report, design_report, errors,
            )

        state["final_output"] = {
            "summary": summary,
            "format": self._format,
            "files_generated": len(artifacts),
            "commands_generated": len(all_commands),
            "errors": len(errors),
            "success": len(errors) == 0,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"Output aggregated: {len(artifacts)} files, "
            f"{len(all_commands)} commands, {len(errors)} errors"
        )
        return state

    def _format_markdown(
        self, state, code_files, test_files, cicd_files,
        migration_files, commands, security, design, tests, errors,
    ) -> str:
        """Format output as markdown."""
        parts = [
            "# AI Coding Agent — Execution Summary\n",
            f"**Request:** {state.get('original_request', 'N/A')}\n",
        ]

        # Files Generated
        if code_files:
            parts.append("## 📁 Generated Files\n")
            for f in code_files:
                parts.append(f"- `{f['path']}` ({len(f.get('content', '').splitlines())} lines)")
            parts.append("")

        if test_files:
            parts.append("## 🧪 Test Files\n")
            for f in test_files:
                parts.append(f"- `{f['path']}`")
            parts.append("")

        if cicd_files:
            parts.append("## ⚙️ CI/CD Configuration\n")
            for f in cicd_files:
                parts.append(f"- `{f['path']}`")
            parts.append("")

        if migration_files:
            parts.append("## 🗄️ Database Migrations\n")
            for f in migration_files:
                parts.append(f"- `{f['path']}`")
            parts.append("")

        # Security Report
        if security:
            status = "⚠️ BLOCKED" if security.get("blocked") else "✅ PASSED"
            parts.append(f"## 🔒 Security Report — {status}\n")
            parts.append(f"- Critical: {security.get('critical', 0)}")
            parts.append(f"- High: {security.get('high', 0)}")
            parts.append(f"- Medium: {security.get('medium', 0)}")
            parts.append("")

        # Design Report
        if design:
            status = "✅ PASSED" if design.get("passed") else "⚠️ VIOLATIONS"
            parts.append(f"## 📐 Design Pattern Check — {status}\n")
            parts.append(f"- Violations: {design.get('total_violations', 0)}")
            parts.append("")

        # Commands to Run
        if commands:
            parts.append("## 🚀 Commands to Execute\n")
            parts.append("```bash")
            for cmd in commands:
                desc = cmd.get("description", "")
                command = cmd.get("command", "")
                parts.append(f"# {desc}")
                parts.append(command)
                parts.append("")
            parts.append("```")

        # Errors
        if errors:
            parts.append("## ❌ Errors\n")
            for err in errors:
                parts.append(f"- **{err.get('node', 'unknown')}**: {err.get('error', '')}")
            parts.append("")

        return "\n".join(parts)

    def _format_json(
        self, state, code_files, test_files, commands,
        security, design, errors,
    ) -> dict:
        """Format output as structured JSON."""
        return {
            "request": state.get("original_request", ""),
            "files": [{"path": f["path"], "lines": len(f.get("content", "").splitlines())} for f in code_files],
            "test_files": [f["path"] for f in test_files],
            "commands": commands,
            "security": security,
            "design": design,
            "errors": errors,
        }
