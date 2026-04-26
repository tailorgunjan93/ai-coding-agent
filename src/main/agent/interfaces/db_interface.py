from abc import ABC, abstractmethod
from typing import Any

class DBInterface(ABC):
    """
    Interface for Database providers.
    Every file must expose connect().
    """

    @abstractmethod
    def connect(self, **kwargs) -> Any:
        """Establish connection to the database."""
        pass

    @abstractmethod
    def run_query(self, query: str, params: dict | None = None) -> Any:
        """Execute a query."""
        pass

