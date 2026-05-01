from abc import ABC, abstractmethod
import time
import logging
from typing import Any

from src.main.agent.interfaces.node_interface import NodeInterface
from src.main.agent.models.agent_state import AgentState

logger = logging.getLogger(__name__)

class BaseNode(NodeInterface, ABC):
    """
    Base implementation for all agent nodes.
    Provides common functionality while enforcing the run() contract.
    """

    def __init__(self, max_retries: int = 3, timeout_seconds: int = 300):
        self._max_retries = max_retries
        self._timeout_seconds = timeout_seconds

    @property
    @abstractmethod
    def node_name(self) -> str:
        """Unique identifier for this node."""
        pass

    @abstractmethod
    async def run(self, state: AgentState) -> AgentState:
        """
        Main execution logic.
        Juniors should implement this method.
        """
        pass

    def get_metrics(self) -> dict[str, Any]:
        """Get node execution metrics."""
        return {
            "node_name": self.node_name,
            "max_retries": self._max_retries,
            "timeout_seconds": self._timeout_seconds,
        }

