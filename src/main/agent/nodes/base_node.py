"""
Base Node - Abstract base implementation for LangGraph nodes.

This module provides the BaseNode abstract class that implements NodeInterface
with common functionality for all nodes: validation, retry logic, metrics.
"""

from abc import ABC, abstractmethod
import time
import logging
from typing import Any

from src.main.agent.interfaces.node_interface import (
    NodeInterface,
    NodeStatus,
    NodeExecutionContext,
    NodeResult,
    ValidationResult,
)
from src.main.agent.exceptions import NodeExecutionError, RetryableError

logger = logging.getLogger(__name__)


class BaseNode(NodeInterface, ABC):
    """
    Base implementation for all agent nodes.

    This class provides common functionality:
    - Input validation with detailed error messages
    - Retry logic with configurable policies
    - Execution timing and metrics
    - Error handling and transformation

    Subclasses must implement:
    - node_name: Unique identifier
    - _execute(): Actual node logic

    Subclasses may override:
    - validate_input(): Custom validation logic
    - should_retry(): Custom retry policy
    - get_required_dependencies(): Node dependencies
    - get_timeout_seconds(): Custom timeout

    Usage:
        class PlanningNode(BaseNode):
            @property
            def node_name(self) -> str:
                return "planning"

            async def _execute(self, state, context):
                # Implementation here
                return {"plan": "..."}
    """

    def __init__(
        self,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        retry_delay_seconds: float = 1.0,
    ):
        """
        Initialize the base node.

        Args:
            max_retries: Maximum retry attempts (default 3).
            timeout_seconds: Execution timeout in seconds (default 300).
            retry_delay_seconds: Delay between retries in seconds (default 1).
        """
        self._max_retries = max_retries
        self._timeout_seconds = timeout_seconds
        self._retry_delay = retry_delay_seconds
        self._execution_count = 0
        self._total_execution_time_ms = 0.0

    @property
    @abstractmethod
    def node_name(self) -> str:
        """Unique identifier for this node. Must be implemented by subclass."""
        pass

    @property
    def description(self) -> str:
        """Human-readable description. Override in subclass."""
        return f"Node: {self.node_name}"

    @property
    def input_schema(self) -> type:
        """Input schema. Override in subclass to define required fields."""
        from src.main.agent.models.agent_state import AgentState
        return AgentState

    @property
    def output_schema(self) -> type:
        """Output schema. Override in subclass to define output fields."""
        return dict

    def validate_input(self, state: dict) -> ValidationResult:
        """
        Validate that state contains required fields.

        Default implementation checks that input_schema fields exist in state.
        Override for custom validation logic.

        Args:
            state: Current workflow state.

        Returns:
            ValidationResult with valid flag and error details.
        """
        # Get annotations from input_schema
        schema = self.input_schema
        if hasattr(schema, "__annotations__"):
            required_fields = list(schema.__annotations__.keys())
        elif hasattr(schema, "__dict__"):
            required_fields = list(schema.__dict__.keys()) if isinstance(schema, dict) else []
        else:
            required_fields = []

        missing = [f for f in required_fields if f not in state]

        if missing:
            return ValidationResult(
                valid=False,
                error_message=f"Missing required fields: {missing}",
                missing_fields=missing,
            )

        return ValidationResult(valid=True, error_message=None)

    async def execute(
        self,
        state: dict,
        context: NodeExecutionContext,
    ) -> NodeResult:
        """
        Execute the node with validation, timing, and error handling.

        This is the main entry point called by the LangGraph framework.
        It wraps _execute() with common concerns.

        Args:
            state: Current workflow state (read-only).
            context: Execution context with retry info.

        Returns:
            NodeResult with status, output, and metadata.
        """
        import asyncio

        start_time = time.time()
        self._execution_count += 1

        # Validate input
        is_valid, error_msg = self._validate_with_result(state)
        if not is_valid:
            logger.warning(f"{self.node_name}: Invalid input - {error_msg}")
            return NodeResult(
                status=NodeStatus.FAILED,
                error=error_msg,
                metadata={"validation_failed": True},
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # Execute with retry loop
        attempt = context.get("attempt", 1)
        last_error: Exception | None = None

        while attempt <= self._max_retries:
            try:
                output = await self._execute(state, context)

                execution_time_ms = (time.time() - start_time) * 1000
                self._total_execution_time_ms += execution_time_ms

                return NodeResult(
                    status=NodeStatus.COMPLETED,
                    output=output,
                    metadata={
                        "node": self.node_name,
                        "attempt": attempt,
                    },
                    execution_time_ms=execution_time_ms,
                )

            except RetryableError as e:
                last_error = e
                if self.should_retry(e, attempt):
                    logger.warning(
                        f"{self.node_name}: Retryable error on attempt {attempt}, retrying..."
                    )
                    attempt += 1
                    await asyncio.sleep(self._retry_delay * (attempt - 1))
                    continue
                else:
                    logger.error(
                        f"{self.node_name}: Retryable error but should not retry: {e}"
                    )
                    break

            except Exception as e:
                last_error = e
                if self.should_retry(e, attempt):
                    logger.warning(
                        f"{self.node_name}: Error on attempt {attempt}, retrying: {e}"
                    )
                    attempt += 1
                    await asyncio.sleep(self._retry_delay * (attempt - 1))
                    continue
                else:
                    logger.error(f"{self.node_name}: Non-retryable error: {e}")
                    break

        # All retries exhausted
        execution_time_ms = (time.time() - start_time) * 1000
        error_msg = str(last_error) if last_error else "Unknown error"

        return NodeResult(
            status=NodeStatus.FAILED,
            error=error_msg,
            metadata={
                "node": self.node_name,
                "attempts": attempt,
                "exhausted_retries": True,
            },
            execution_time_ms=execution_time_ms,
        )

    def _validate_with_result(self, state: dict) -> tuple[bool, str | None]:
        """Helper to convert ValidationResult to tuple."""
        result = self.validate_input(state)
        return result["valid"], result.get("error_message")

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determine if execution should be retried after an error.

        Default policy:
        - Retry on network errors, timeouts
        - Don't retry on validation errors
        - Respect max_retries setting

        Override for custom retry policy.

        Args:
            error: The exception that occurred.
            attempt: Current attempt number (1-indexed).

        Returns:
            True if should retry, False to fail immediately.
        """
        if attempt >= self._max_retries:
            return False

        # Don't retry validation errors
        from src.main.agent.exceptions import ValidationError
        if isinstance(error, ValidationError):
            return False

        # Retry on these exception types
        retryable_types = (
            ConnectionError,
            TimeoutError,
            RetryableError,
        )

        error_str = str(error).lower()
        if isinstance(error, retryable_types):
            return True
        if "timeout" in error_str or "network" in error_str or "connection" in error_str:
            return True

        return False

    def get_required_dependencies(self) -> list[str]:
        """
        Return list of node names that must execute before this node.

        Override in subclass to specify dependencies.

        Returns:
            List of node names. Empty list if no dependencies.
        """
        return []

    def get_optional_dependencies(self) -> list[str]:
        """Return list of optional node names."""
        return []

    def get_timeout_seconds(self) -> int:
        """Return the execution timeout in seconds."""
        return self._timeout_seconds

    def get_max_retries(self) -> int:
        """Return the maximum number of retries."""
        return self._max_retries

    @abstractmethod
    async def _execute(
        self,
        state: dict,
        context: NodeExecutionContext,
    ) -> Any:
        """
        Execute the node's main logic.

        This is the abstract method that subclasses must implement.
        It should perform the actual node operation and return the output.

        Args:
            state: Current workflow state.
            context: Execution context.

        Returns:
            The node's output (will be wrapped in NodeResult by execute()).

        Raises:
            RetryableError: To trigger retry with current attempt count.
            Exception: Any other exception will fail the node immediately
                       unless should_retry() returns True.
        """
        raise NotImplementedError("Subclass must implement _execute")

    def get_metrics(self) -> dict[str, Any]:
        """
        Get node execution metrics.

        Returns:
            Dict with execution_count, avg_time_ms, etc.
        """
        avg_time = (
            self._total_execution_time_ms / self._execution_count
            if self._execution_count > 0
            else 0
        )

        return {
            "node_name": self.node_name,
            "execution_count": self._execution_count,
            "total_execution_time_ms": self._total_execution_time_ms,
            "avg_execution_time_ms": avg_time,
            "max_retries": self._max_retries,
            "timeout_seconds": self._timeout_seconds,
        }

    def reset_metrics(self) -> None:
        """Reset execution metrics."""
        self._execution_count = 0
        self._total_execution_time_ms = 0.0
