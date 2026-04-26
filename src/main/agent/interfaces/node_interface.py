"""
Node Interface - Abstract contract for LangGraph agent nodes.

This interface defines the contract that all agent nodes must implement,
ensuring consistent behavior across the workflow state machine.
"""

from abc import ABC, abstractmethod
from typing import Any, TypedDict, NotRequired
from enum import Enum


class NodeStatus(Enum):
    """Possible states for node execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class NodeExecutionContext(TypedDict):
    """Context information for node execution."""
    node_id: str
    attempt: int
    max_attempts: int
    timeout_seconds: int
    callbacks: NotRequired[list[Any]]
    session_id: str | None
    checkpoint_id: str | None


class NodeResult(TypedDict):
    """Result from node execution."""
    status: NodeStatus
    output: NotRequired[Any]
    error: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]
    execution_time_ms: float
    retry_count: NotRequired[int]


class ValidationResult(TypedDict):
    """Result from input validation."""
    valid: bool
    error_message: str | None
    missing_fields: NotRequired[list[str]]


class NodeInterface(ABC):
    """
    Abstract base for all agent nodes in the LangGraph workflow.

    Nodes are the fundamental execution units that transform input state
    into output state. Each node implements:
    - Input validation
    - Main execution logic
    - Retry handling
    - Dependency management

    The framework guarantees:
    - execute() is called with valid input (validate_input passes)
    - should_retry() determines retry behavior on failure
    - get_required_dependencies() controls execution order
    """

    @property
    @abstractmethod
    def node_name(self) -> str:
        """
        Unique identifier for this node type.

        Returns:
            String identifier unique within the agent workflow.
            Examples: "planning", "model", "security", "tester"
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Human-readable description of this node's purpose.

        Returns:
            Description string for documentation and debugging.
        """
        pass

    @property
    def input_schema(self) -> type:
        """
        Return the required input state schema.

        Returns:
            Type/class defining required input fields.
            Should be AgentState or a TypedDict subclass.
        """
        raise NotImplementedError("Subclass must define input_schema")

    @property
    def output_schema(self) -> type:
        """
        Return the output state schema for this node.

        Returns:
            Type/class defining output fields produced by this node.
        """
        raise NotImplementedError("Subclass must define output_schema")

    @abstractmethod
    def validate_input(self, state: dict) -> ValidationResult:
        """
        Validate that state contains required fields for this node.

        Args:
            state: Current workflow state.

        Returns:
            ValidationResult with valid flag and error details.
        """
        pass

    @abstractmethod
    async def execute(
        self,
        state: dict,
        context: NodeExecutionContext
    ) -> NodeResult:
        """
        Execute the node's main logic.

        This method is called by the LangGraph framework after input validation.
        Subclasses should override _execute() for actual logic.

        Args:
            state: Current workflow state (read-only).
            context: Execution context with retry info and callbacks.

        Returns:
            NodeResult with status, output, and metadata.

        Raises:
            RetryableError: When execution should be retried.
            NodeExecutionError: When execution fails unrecoverably.
        """
        pass

    @abstractmethod
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determine if node should retry after an error.

        Args:
            error: The exception that occurred.
            attempt: Current attempt number (1-indexed).

        Returns:
            True if should retry, False to fail immediately.
        """
        pass

    @abstractmethod
    def get_required_dependencies(self) -> list[str]:
        """
        Return list of node names that must execute before this node.

        The graph builder uses this to ensure correct execution order.
        Nodes without dependencies can run immediately after entry point.

        Returns:
            List of node names that must complete before this node runs.
        """
        pass

    @abstractmethod
    def get_optional_dependencies(self) -> list[str]:
        """
        Return list of node names that should run before this node if available.

        Unlike required dependencies, optional dependencies do not block
        execution if they are not present in the workflow.

        Returns:
            List of optional node names.
        """
        pass

    def get_timeout_seconds(self) -> int:
        """
        Return the timeout for this node's execution.

        Returns:
            Timeout in seconds. Default 300 (5 minutes).
        """
        return 300

    def get_max_retries(self) -> int:
        """
        Return the maximum number of retries for this node.

        Returns:
            Max retry count. Default 3.
        """
        return 3

    def on_skip(self, state: dict) -> NodeResult:
        """
        Called when this node is skipped due to unmet dependencies.

        Override to provide custom skip handling.

        Args:
            state: Current workflow state.

        Returns:
            NodeResult with SKIPPED status.
        """
        return NodeResult(
            status=NodeStatus.SKIPPED,
            metadata={"reason": "dependency_not_met", "node": self.node_name}
        )
