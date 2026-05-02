"""
Base Node - Abstract base with execute() template method.

Provides common functionality for all agent nodes:
  - execute() template method with retry, timeout, error wrapping
  - run() abstract method for node-specific logic
  - Metrics and dependency tracking
"""

from abc import ABC, abstractmethod
import time
import logging
import asyncio
from typing import Any
from datetime import datetime, timezone

from src.main.agent.interfaces.node_interface import (
    NodeInterface,
    NodeExecutionContext,
    NodeResult,
    NodeStatus,
)
from src.main.agent.models.agent_state import AgentState
from src.main.agent.exceptions import NodeExecutionError, RetryableError

logger = logging.getLogger(__name__)


class BaseNode(NodeInterface, ABC):
    """
    Base implementation for all agent nodes.

    Provides:
    - execute() template method with retry logic and error handling
    - run() abstract method that subclasses implement
    - Metrics tracking (execution time, retries, errors)
    - Dependency declaration

    Usage:
        class MyNode(BaseNode):
            @property
            def node_name(self) -> str:
                return "my_node"

            async def run(self, state: AgentState) -> AgentState:
                # node logic here
                return state
    """

    def __init__(self, max_retries: int = 3, timeout_seconds: int = 300):
        self._max_retries = max_retries
        self._timeout_seconds = timeout_seconds
        self._execution_count = 0
        self._total_errors = 0
        self._last_execution_ms = 0.0

    @property
    @abstractmethod
    def node_name(self) -> str:
        """Unique identifier for this node."""
        pass

    @property
    def description(self) -> str:
        """Human-readable description. Override in subclass."""
        return f"{self.node_name} node"

    @property
    def input_schema(self) -> type:
        """Input schema type. Override in subclass."""
        return AgentState

    @property
    def output_schema(self) -> type:
        """Output schema type. Override in subclass."""
        return dict

    @abstractmethod
    async def run(self, state: AgentState) -> AgentState:
        """
        Main execution logic. Subclasses MUST implement this.

        Args:
            state: The current AgentState.

        Returns:
            The updated AgentState.
        """
        pass

    def get_required_dependencies(self) -> list[str]:
        """Return node names that must execute before this node. Override in subclass."""
        return []

    def get_optional_dependencies(self) -> list[str]:
        """Return node names that optionally execute before this. Override in subclass."""
        return []

    async def execute(self, state: AgentState) -> AgentState:
        """
        Template method — wraps run() with retry, timeout, and error handling.

        This is what LangGraph calls. It:
        1. Updates current_node in state
        2. Calls run() with retry logic
        3. Catches and records errors
        4. Updates node output in state

        Args:
            state: The current AgentState.

        Returns:
            The updated AgentState with node output recorded.
        """
        start_time = time.monotonic()
        self._execution_count += 1
        node_name = self.node_name

        # Track current node in state
        state["current_node"] = node_name
        state["updated_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"[{node_name}] Starting execution (attempt 1/{self._max_retries + 1})")

        last_error = None

        for attempt in range(1, self._max_retries + 2):  # +1 for initial attempt
            try:
                # Run with timeout
                result_state = await asyncio.wait_for(
                    self.run(state),
                    timeout=self._timeout_seconds,
                )

                # Record success
                elapsed_ms = (time.monotonic() - start_time) * 1000
                self._last_execution_ms = elapsed_ms

                output_key = f"{node_name}_output"
                result_state[output_key] = {
                    "status": "success",
                    "metadata": {
                        "execution_time_ms": elapsed_ms,
                        "attempt": attempt,
                        "node_name": node_name,
                    },
                }

                logger.info(f"[{node_name}] Completed in {elapsed_ms:.0f}ms")
                return result_state

            except asyncio.TimeoutError:
                last_error = f"Timeout after {self._timeout_seconds}s"
                logger.warning(f"[{node_name}] {last_error} (attempt {attempt})")

            except RetryableError as e:
                last_error = str(e)
                logger.warning(f"[{node_name}] Retryable error: {last_error} (attempt {attempt})")

            except Exception as e:
                last_error = str(e)
                self._total_errors += 1

                # Don't retry non-retryable errors
                if attempt > 1 or not self._should_retry(e, attempt):
                    break

                logger.warning(f"[{node_name}] Error: {last_error} (attempt {attempt})")

        # All retries exhausted — record failure
        elapsed_ms = (time.monotonic() - start_time) * 1000
        self._last_execution_ms = elapsed_ms

        error_entry = {
            "node": node_name,
            "error": last_error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        state.setdefault("errors", []).append(error_entry)

        output_key = f"{node_name}_output"
        state[output_key] = {
            "status": "error",
            "error": last_error,
            "metadata": {
                "execution_time_ms": elapsed_ms,
                "attempts": self._max_retries + 1,
                "node_name": node_name,
            },
        }

        logger.error(f"[{node_name}] Failed after all retries: {last_error}")
        return state

    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if node should retry after an error."""
        if attempt >= self._max_retries + 1:
            return False
        if isinstance(error, RetryableError):
            return True
        # Don't retry validation or permission errors
        error_type = type(error).__name__
        non_retryable = {"ValidationError", "PermissionError", "SecurityError", "ConfigurationError"}
        return error_type not in non_retryable

    def get_metrics(self) -> dict[str, Any]:
        """Get node execution metrics."""
        return {
            "node_name": self.node_name,
            "max_retries": self._max_retries,
            "timeout_seconds": self._timeout_seconds,
            "execution_count": self._execution_count,
            "total_errors": self._total_errors,
            "last_execution_ms": self._last_execution_ms,
        }
