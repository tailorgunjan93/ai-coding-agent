"""
Git Interface - Abstract contract for version control operations.

Defines the types and ABC for all git/repo adapters.
"""

from abc import ABC, abstractmethod
from typing import Any, TypedDict, NotRequired


class CommitInfo(TypedDict):
    """Information about a git commit."""
    message: str
    author: str
    timestamp: str
    files_changed: list[str]
    sha: NotRequired[str]


class BranchInfo(TypedDict):
    """Information about a git branch."""
    name: str
    is_current: bool
    last_commit_sha: NotRequired[str]
    last_commit_message: NotRequired[str]


class PRInfo(TypedDict):
    """Information about a pull request."""
    title: str
    description: str
    source_branch: str
    target_branch: str
    url: NotRequired[str]
    status: NotRequired[str]


class GitInterface(ABC):
    """
    Abstract base for Git/repository operations.

    Adapters must implement this interface to be used
    by the Git node and Git wrapper.
    """

    @abstractmethod
    def connect(self, repo_path: str, **kwargs) -> bool:
        """
        Connect to / open a git repository.

        Args:
            repo_path: Path to the local repository.

        Returns:
            True if connection successful.
        """
        pass

    @abstractmethod
    def clone(self, repo_url: str, dest: str) -> bool:
        """
        Clone a remote repository.

        Args:
            repo_url: URL of the remote repository.
            dest: Local destination path.

        Returns:
            True if clone successful.
        """
        pass

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """
        Get repository status (modified, staged, untracked files).

        Returns:
            Dict with 'modified', 'staged', 'untracked' file lists.
        """
        pass

    @abstractmethod
    def stage_files(self, files: list[str]) -> bool:
        """
        Stage files for commit.

        Args:
            files: List of file paths to stage. Use ['.'] for all.

        Returns:
            True if staging successful.
        """
        pass

    @abstractmethod
    def commit(self, message: str, files: list[str] | None = None) -> CommitInfo:
        """
        Create a commit with staged changes.

        Args:
            message: Commit message.
            files: Optional list of files to commit (stages first).

        Returns:
            CommitInfo with commit details.
        """
        pass

    @abstractmethod
    def push(self, branch: str | None = None, remote: str = "origin") -> bool:
        """
        Push commits to remote.

        Args:
            branch: Branch to push (default: current).
            remote: Remote name (default: origin).

        Returns:
            True if push successful.
        """
        pass

    @abstractmethod
    def create_branch(self, branch_name: str, checkout: bool = True) -> bool:
        """
        Create a new branch.

        Args:
            branch_name: Name for the new branch.
            checkout: If True, switch to the new branch.

        Returns:
            True if branch created successfully.
        """
        pass

    @abstractmethod
    def list_branches(self) -> list[BranchInfo]:
        """Return list of all branches."""
        pass

    @abstractmethod
    def create_pr(
        self,
        title: str,
        body: str,
        source: str,
        target: str,
    ) -> PRInfo:
        """
        Create a pull request.

        Args:
            title: PR title.
            body: PR description.
            source: Source branch name.
            target: Target branch name.

        Returns:
            PRInfo with PR details.
        """
        pass

    @abstractmethod
    def get_diff(self, staged: bool = False) -> str:
        """
        Get diff of changes.

        Args:
            staged: If True, show staged changes only.

        Returns:
            Diff string.
        """
        pass