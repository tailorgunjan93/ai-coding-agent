"""
Agent State - Central state schema for LangGraph workflow.

This TypedDict defines the shared state that flows through all nodes
in the agent workflow. Using TypedDict ensures:
- Explicit field names (no magic dict access)
- IDE autocomplete and type checking
- LangGraph state compatibility
"""

from typing import TypedDict, NotRequired, Any
from enum import Enum


class TaskStatus(Enum):
    """Status of a task within the plan."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class Task(TypedDict):
    """A single task in the execution plan."""
    id: str
    description: str
    status: TaskStatus
    assignee: NotRequired[str]
    depends_on: list[str]
    created_at: str
    completed_at: NotRequired[str]
    error: NotRequired[str]


class Artifact(TypedDict):
    """A code or document artifact produced by the agent."""
    type: str  # "file", "directory", "document", "image"
    path: str
    content: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]
    created_at: str
    modified_at: NotRequired[str]


class NodeOutput(TypedDict):
    """Generic output from any node."""
    status: str  # "success", "error", "skipped"
    data: NotRequired[Any]
    error: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]


class AgentState(TypedDict, total=False):
    """
    Central state schema for the LangGraph workflow.

    This state is passed between all nodes and represents the complete
    execution context of the agent.

    Fields marked as NotRequired can be absent, but nodes should
    handle missing fields gracefully.
    """

    # === Session Info ===
    session_id: str
    user_id: str
    created_at: str
    updated_at: str
    original_request: str
    request_type: str  # "generate", "enhance", "fix", "debug", "plan"

    # === Planning & Tasks ===
    plan: str  # Planning markdown
    tasks: list[Task]
    current_task_index: int
    approval_status: str  # "pending", "approved", "rejected"
    approved_by: NotRequired[str]
    approved_at: NotRequired[str]

    # === Messages & Artifacts ===
    messages: list[dict[str, Any]]  # Chat message history
    artifacts: list[Artifact]  # Files, documents, images

    # === Node Outputs ===
    # Each node stores its output here when it completes
    input_output: NotRequired[NodeOutput]
    planning_output: NotRequired[NodeOutput]
    model_output: NotRequired[NodeOutput]
    design_output: NotRequired[NodeOutput]
    security_output: NotRequired[NodeOutput]
    tester_output: NotRequired[NodeOutput]
    db_output: NotRequired[NodeOutput]
    git_output: NotRequired[NodeOutput]
    cicd_output: NotRequired[NodeOutput]
    lifecycle_output: NotRequired[NodeOutput]
    output_node_output: NotRequired[NodeOutput]

    # === Status ===
    current_node: str  # Which node is currently executing
    errors: list[dict[str, Any]]
    warnings: list[str]
    success: bool
    metadata: dict[str, Any]  # Miscellaneous metadata


class ExecutionContext(TypedDict):
    """Context passed to each node during execution."""
    session_id: str
    node_name: str
    attempt: int
    max_attempts: int
    timeout_seconds: int
    checkpoint_id: NotRequired[str]


def create_initial_state(
    session_id: str,
    user_id: str,
    original_request: str,
    request_type: str = "generate"
) -> AgentState:
    """
    Factory function to create initial agent state.

    Args:
        session_id: Unique session identifier.
        user_id: User identifier.
        original_request: The original user request.
        request_type: Type of request (generate, enhance, fix, etc.).

    Returns:
        AgentState with sensible defaults.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()

    return AgentState(
        session_id=session_id,
        user_id=user_id,
        created_at=now,
        updated_at=now,
        original_request=original_request,
        request_type=request_type,
        tasks=[],
        current_task_index=0,
        approval_status="pending",
        messages=[],
        artifacts=[],
        errors=[],
        warnings=[],
        success=False,
        metadata={},
        current_node="input"
    )
