from abc import ABC, abstractmethod
from typing import Any

class GitInterface(ABC):
    """
    Interface for Git providers.
    Every file must expose connect().
    """

    @abstractmethod
    def connect(self, **kwargs) -> Any:
        """Connect to the Git provider."""
        pass

    @abstractmethod
    def clone(self, repo_url: str, dest: str) -> bool:
        """Clone a repository."""
        pass