from abc import ABC, abstractmethod
from src.main.agent.models.agent_state import AgentState

class NodeInterface(ABC):
    """
    Minimal contract for all agent nodes.
    Forces juniors to follow a consistent pattern.
    """

    @abstractmethod
    def run(self, state: AgentState) -> AgentState:
        """
        All nodes must implement run().
        
        Args:
            state: The current AgentState.
            
        Returns:
            The updated AgentState.
        """
        pass

