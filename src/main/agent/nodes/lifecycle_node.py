"""
Lifecycle Node - Handles code lifecycle operations (create/update/fix/delete).

Determines the operation type from the user request and routes
artifacts through the appropriate handler.
"""

from typing import Any
import logging
from datetime import datetime, timezone

from src.main.agent.nodes.base_node import BaseNode
from src.main.agent.models.agent_state import AgentState

logger = logging.getLogger(__name__)


class LifecycleNode(BaseNode):
    """
    Node responsible for code lifecycle management.

    Operations:
    - create: Write new files to output
    - enhance: Add features to existing code
    - fix: Apply fixes from model output
    - debug: Collect debug diagnostic info
    - delete: Generate file removal commands

    Dependencies:
        - planning (needs plan context)
    """

    def __init__(self, max_retries: int = 2):
        super().__init__(max_retries=max_retries, timeout_seconds=60)
        self._operations = {
            "create": self._handle_create,
            "enhance": self._handle_enhance,
            "fix": self._handle_fix,
            "debug": self._handle_debug,
            "delete": self._handle_delete,
        }

    @property
    def node_name(self) -> str:
        return "lifecycle"

    @property
    def description(self) -> str:
        return "Handles code lifecycle operations"

    def get_required_dependencies(self) -> list[str]:
        return ["planning"]

    async def run(self, state: AgentState) -> AgentState:
        """
        Execute the appropriate lifecycle operation.

        Detects operation type from the request and routes
        to the correct handler.
        """
        request_type = self._detect_operation(state)
        state["lifecycle_operation"] = request_type

        handler = self._operations.get(request_type, self._handle_create)
        result = await handler(state)

        logger.info(f"Lifecycle operation '{request_type}' completed")
        return result

    def _detect_operation(self, state: AgentState) -> str:
        """Detect operation type from the user request."""
        request = state.get("original_request", "").lower()

        if any(w in request for w in ["fix", "bug", "repair", "patch", "resolve"]):
            return "fix"
        elif any(w in request for w in ["debug", "diagnose", "investigate", "trace"]):
            return "debug"
        elif any(w in request for w in ["delete", "remove", "drop", "cleanup"]):
            return "delete"
        elif any(w in request for w in ["add", "enhance", "update", "extend", "improve", "refactor"]):
            return "enhance"
        else:
            return "create"

    async def _handle_create(self, state: AgentState) -> AgentState:
        """Handle create — generate file write commands."""
        artifacts = state.get("artifacts", [])
        file_artifacts = [a for a in artifacts if a.get("type") == "file"]

        commands = []
        for artifact in file_artifacts:
            path = artifact.get("path", "")
            # Generate directory creation + file write commands
            dir_path = "/".join(path.split("/")[:-1])
            if dir_path:
                commands.append({
                    "command": f"mkdir -p {dir_path}",
                    "description": f"Create directory: {dir_path}",
                })
            commands.append({
                "command": f"# Write content to {path}",
                "description": f"Create file: {path}",
            })

        state["lifecycle_result"] = {
            "operation": "create",
            "files": len(file_artifacts),
            "commands": commands,
            "status": "ready",
        }
        return state

    async def _handle_enhance(self, state: AgentState) -> AgentState:
        """Handle enhance — add features to existing code."""
        artifacts = state.get("artifacts", [])
        file_artifacts = [a for a in artifacts if a.get("type") == "file"]

        commands = []
        for artifact in file_artifacts:
            path = artifact.get("path", "")
            commands.append({
                "command": f"# Apply changes to {path}",
                "description": f"Update existing file: {path}",
            })
            # Generate a diff-apply command suggestion
            commands.append({
                "command": f"diff {path} {path}.new && cp {path}.new {path}",
                "description": f"Review diff and apply changes to {path}",
            })

        state["lifecycle_result"] = {
            "operation": "enhance",
            "files_modified": len(file_artifacts),
            "commands": commands,
            "status": "ready",
        }
        return state

    async def _handle_fix(self, state: AgentState) -> AgentState:
        """Handle fix — apply bug fixes."""
        artifacts = state.get("artifacts", [])
        file_artifacts = [a for a in artifacts if a.get("type") == "file"]

        commands = []
        for artifact in file_artifacts:
            path = artifact.get("path", "")
            commands.append({
                "command": f"# Apply fix to {path}",
                "description": f"Fix: {path}",
            })

        # Add verification commands
        commands.append({
            "command": "pytest -v --tb=short",
            "description": "Run tests to verify fix",
        })

        state["lifecycle_result"] = {
            "operation": "fix",
            "files_fixed": len(file_artifacts),
            "commands": commands,
            "status": "ready",
        }
        return state

    async def _handle_debug(self, state: AgentState) -> AgentState:
        """Handle debug — collect diagnostic info."""
        commands = [
            {
                "command": "python -m py_compile <file>",
                "description": "Check for syntax errors",
            },
            {
                "command": "python -c 'import traceback; traceback.print_exc()'",
                "description": "Print full stack trace",
            },
            {
                "command": "python -m pdb <script>",
                "description": "Start interactive debugger",
            },
            {
                "command": "pytest -v --tb=long -s",
                "description": "Run tests with full output",
            },
        ]

        state["lifecycle_result"] = {
            "operation": "debug",
            "commands": commands,
            "status": "ready",
            "suggestion": "Use the commands above to diagnose the issue",
        }
        return state

    async def _handle_delete(self, state: AgentState) -> AgentState:
        """Handle delete — generate file removal commands."""
        request = state.get("original_request", "")

        commands = [
            {
                "command": "# Review files before deletion",
                "description": "Always review before deleting",
            },
            {
                "command": f"# rm -i <files>  # Based on request: {request[:50]}",
                "description": "Delete specified files (interactive)",
            },
            {
                "command": "git status",
                "description": "Check what was removed",
            },
        ]

        state["lifecycle_result"] = {
            "operation": "delete",
            "commands": commands,
            "status": "ready",
            "warning": "Review files carefully before executing delete commands",
        }
        return state
