"""
CI/CD Interface - Abstract contract for CI/CD pipeline operations.

Defines the types and ABC for CI/CD provider adapters.
Supports GitHub Actions, GitLab CI, Jenkins, Azure DevOps.
"""

from abc import ABC, abstractmethod
from typing import Any, TypedDict, NotRequired
from enum import Enum


class CICDProvider(Enum):
    """Supported CI/CD providers."""
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    JENKINS = "jenkins"
    AZURE_DEVOPS = "azure_devops"


class PipelineStatus(Enum):
    """Status of a CI/CD pipeline run."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class PipelineConfig(TypedDict, total=False):
    """Configuration for a CI/CD pipeline."""
    name: str
    trigger_branches: list[str]
    stages: list[str]
    environment: dict[str, str]
    timeout_minutes: int


class PipelineResult(TypedDict):
    """Result of a CI/CD pipeline run."""
    pipeline_id: str
    status: str
    url: NotRequired[str]
    duration_seconds: NotRequired[float]
    stages: NotRequired[list[dict[str, Any]]]
    logs: NotRequired[str]


class CICDInterface(ABC):
    """
    Abstract base for CI/CD pipeline operations.

    Adapters must implement this interface to integrate
    with CI/CD providers.
    """

    @abstractmethod
    def connect(self, **kwargs) -> Any:
        """Connect to the CI/CD provider."""
        pass

    @abstractmethod
    def trigger_pipeline(
        self,
        pipeline_id: str,
        branch: str = "main",
        **kwargs,
    ) -> PipelineResult:
        """
        Trigger a pipeline run.

        Args:
            pipeline_id: Pipeline identifier.
            branch: Branch to run pipeline on.

        Returns:
            PipelineResult with run details.
        """
        pass

    @abstractmethod
    def get_pipeline_status(self, run_id: str) -> PipelineResult:
        """
        Get the status of a pipeline run.

        Args:
            run_id: Pipeline run identifier.

        Returns:
            PipelineResult with current status.
        """
        pass

    @abstractmethod
    def get_logs(self, run_id: str) -> str:
        """
        Get logs from a pipeline run.

        Args:
            run_id: Pipeline run identifier.

        Returns:
            Log output as string.
        """
        pass

    @abstractmethod
    def cancel_pipeline(self, run_id: str) -> bool:
        """
        Cancel a running pipeline.

        Args:
            run_id: Pipeline run identifier.

        Returns:
            True if cancellation was successful.
        """
        pass

    @abstractmethod
    def generate_config(
        self,
        config: PipelineConfig,
        provider: CICDProvider,
    ) -> str:
        """
        Generate CI/CD configuration file content.

        Args:
            config: Pipeline configuration.
            provider: Target CI/CD provider.

        Returns:
            Configuration file content (YAML, Jenkinsfile, etc.).
        """
        pass

    @abstractmethod
    def list_pipelines(self) -> list[dict[str, Any]]:
        """List all available pipelines."""
        pass