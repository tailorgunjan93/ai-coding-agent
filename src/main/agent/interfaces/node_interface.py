"""
Node Interface - Abstract contract for all agent nodes.

Defines the NodeInterface ABC, execution context, status enums,
and result types that all LangGraph nodes must implement.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypedDict, NotRequired, Any
from enum import Enum

if TYPE_CHECKING:
    from src.main.agent.models.agent_state import AgentState


class NodeStatus(Enum):
    """Status of a node execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class NodeExecutionContext(TypedDict):
    """Context passed to each node during execution."""
    node_id: str
    attempt: int
    max_attempts: int
    timeout_seconds: int
    session_id: NotRequired[str]
    callbacks: NotRequired[list[Any]]


class NodeResult(TypedDict):
    """Structured result from a node execution."""
    status: str  # NodeStatus value
    output: NotRequired[Any]
    error: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]
    execution_time_ms: NotRequired[float]


class NodeInterface(ABC):
    """
    Minimal contract for all agent nodes.
    Forces consistent pattern across all node implementations.
    """

    @abstractmethod
    async def run(self, state: "AgentState") -> "AgentState":
        """
        All nodes must implement run().

        Args:
            state: The current AgentState.

        Returns:
            The updated AgentState.
        """
        pass
