from abc import ABC, abstractmethod
from typing import Any

class CICDInterface(ABC):
    """
    Interface for CI/CD providers.
    Every file must expose connect().
    """

    @abstractmethod
    def connect(self, **kwargs) -> Any:
        """Connect to the CI/CD provider."""
        pass

    @abstractmethod
    def trigger_pipeline(self, pipeline_id: str, **kwargs) -> str:
        """Trigger a pipeline run."""
        pass