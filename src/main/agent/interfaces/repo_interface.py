"""
Repo Interface - Abstract contract for version control operations.

This interface defines the contract that all repository providers must implement,
enabling interchangeable backends (Git local, GitHub, GitLab, Bitbucket).
"""

from abc import ABC, abstractmethod
from typing import Any, TypedDict, NotRequired
from enum import Enum


class RepoStatus(Enum):
    """Repository status states."""
    CLEAN = "clean"
    DIRTY = "dirty"
    DETACHED = "detached"
    UNBORN = "unborn"


class CommitInfo(TypedDict):
    """Information about a commit."""
    sha: str
    message: str
    author: str
    author_email: str
    timestamp: str
    files_changed: list[str]
    insertions: int
    deletions: int


class PRInfo(TypedDict):
    """Information about a pull request."""
    number: int
    title: str
    description: str
    source_branch: str
    target_branch: str
    url: str | None
    status: str | None  # open, closed, merged
    review_status: str | None  # approved, changes_requested, pending
    author: str
    created_at: str
    updated_at: str | None


class BranchInfo(TypedDict):
    """Information about a branch."""
    name: str
    is_current: bool
    is_remote: bool
    tracking_branch: str | None
    ahead_behind: "tuple[int, int] | None"  # Not directly JSON-serializable
    last_commit_sha: str | None


class DiffInfo(TypedDict):
    """Information about file changes."""
    file_path: str
    status: str  # added, modified, deleted, renamed
    additions: int
    deletions: int
    old_path: str | None  # For renamed files
    diff: str | None  # Unified diff


class TagInfo(TypedDict):
    """Information about a tag."""
    name: str
    sha: str
    message: str | None
    author: str
    date: str


class RepoInterface(ABC):
    """
    Abstract base for repository operations.

    This interface supports both local git operations and remote API operations
    (GitHub, GitLab, etc.) through the same contract.
    """

    @abstractmethod
    def clone(self, url: str, path: str, branch: str | None = None) -> bool:
        """
        Clone a repository to local path.

        Args:
            url: Repository URL (git URL or remote API URL).
            path: Local destination path.
            branch: Optional branch to checkout after clone.

        Returns:
            True if cloned successfully.

        Raises:
            ConnectionError: On clone failure.
        """
        pass

    @abstractmethod
    def get_status(self) -> RepoStatus:
        """
        Get current repository status.

        Returns:
            RepoStatus enum value.
        """
        pass

    @abstractmethod
    def get_current_branch(self) -> str:
        """
        Get the current branch name.

        Returns:
            Current branch name.
        """
        pass

    @abstractmethod
    def list_branches(self, remote: bool = False) -> list[BranchInfo]:
        """
        List all branches.

        Args:
            remote: If True, list remote branches.

        Returns:
            List of BranchInfo dictionaries.
        """
        pass

    @abstractmethod
    def create_branch(self, name: str, checkout: bool = True) -> BranchInfo:
        """
        Create a new branch.

        Args:
            name: Branch name.
            checkout: If True, checkout the new branch.

        Returns:
            BranchInfo for the created branch.
        """
        pass

    @abstractmethod
    def delete_branch(self, name: str, force: bool = False) -> bool:
        """
        Delete a branch.

        Args:
            name: Branch name to delete.
            force: If True, force delete even if not merged.

        Returns:
            True if deleted successfully.
        """
        pass

    @abstractmethod
    def checkout(self, ref: str, create_branch: bool = False) -> bool:
        """
        Checkout a branch, commit, or tag.

        Args:
            ref: Branch name, commit SHA, or tag.
            create_branch: If True, create and checkout new branch.

        Returns:
            True if checkout successful.
        """
        pass

    @abstractmethod
    def get_diff(self, ref: str | None = None) -> list[DiffInfo]:
        """
        Get diff of changes.

        Args:
            ref: Optional ref to diff against (None = unstaged changes).

        Returns:
            List of DiffInfo for changed files.
        """
        pass

    @abstractmethod
    def stage_files(self, files: list[str], all: bool = False) -> bool:
        """
        Stage files for commit.

        Args:
            files: List of file paths to stage.
            all: If True, stage all changed files.

        Returns:
            True if staged successfully.
        """
        pass

    @abstractmethod
    def commit(self, message: str, files: list[str] | None = None) -> CommitInfo:
        """
        Commit staged changes.

        Args:
            message: Commit message.
            files: Optional list of files to commit (commits all staged if None).

        Returns:
            CommitInfo for the new commit.

        Raises:
            ValidationError: If nothing to commit.
        """
        pass

    @abstractmethod
    def push(
        self,
        branch: str | None = None,
        force: bool = False,
        upstream: bool = False
    ) -> bool:
        """
        Push commits to remote.

        Args:
            branch: Branch to push (current if None).
            force: If True, force push.
            upstream: If True, set upstream tracking branch.

        Returns:
            True if pushed successfully.
        """
        pass

    @abstractmethod
    def pull(self, branch: str | None = None, rebase: bool = False) -> bool:
        """
        Pull changes from remote.

        Args:
            branch: Branch to pull (current if None).
            rebase: If True, rebase instead of merge.

        Returns:
            True if pulled successfully.
        """
        pass

    @abstractmethod
    def fetch(self, remote: str | None = None, all: bool = False) -> bool:
        """
        Fetch changes from remote.

        Args:
            remote: Specific remote to fetch from.
            all: If True, fetch all remotes.

        Returns:
            True if fetched successfully.
        """
        pass

    @abstractmethod
    def create_pr(
        self,
        title: str,
        body: str,
        source_branch: str,
        target_branch: str,
        draft: bool = False
    ) -> PRInfo:
        """
        Create a pull request.

        Args:
            title: PR title.
            body: PR description.
            source_branch: Source branch name.
            target_branch: Target branch name.
            draft: If True, create as draft PR.

        Returns:
            PRInfo for the created PR.

        Raises:
            ConnectionError: If remote API call fails.
        """
        pass

    @abstractmethod
    def get_pr(self, pr_number: int | None = None) -> PRInfo | None:
        """
        Get pull request information.

        Args:
            pr_number: PR number (current branch's PR if None).

        Returns:
            PRInfo if PR exists, None otherwise.
        """
        pass

    @abstractmethod
    def merge_pr(self, pr_number: int, method: str = "merge") -> bool:
        """
        Merge a pull request.

        Args:
            pr_number: PR number to merge.
            method: Merge method ("merge", "squash", "rebase").

        Returns:
            True if merged successfully.
        """
        pass

    @abstractmethod
    def get_commit_history(
        self,
        ref: str | None = None,
        limit: int = 100
    ) -> list[CommitInfo]:
        """
        Get commit history.

        Args:
            ref: Optional ref to start from (HEAD if None).
            limit: Maximum number of commits to return.

        Returns:
            List of CommitInfo in reverse chronological order.
        """
        pass

    @abstractmethod
    def get_tags(self) -> list[TagInfo]:
        """
        Get all tags.

        Returns:
            List of TagInfo.
        """
        pass

    @abstractmethod
    def create_tag(
        self,
        name: str,
        ref: str | None = None,
        message: str | None = None
    ) -> TagInfo:
        """
        Create a tag.

        Args:
            name: Tag name.
            ref: Commit/tag to tag (HEAD if None).
            message: Optional annotated tag message.

        Returns:
            TagInfo for the created tag.
        """
        pass

    @abstractmethod
    def get_remote_url(self) -> str | None:
        """
        Get the URL of the origin remote.

        Returns:
            Remote URL string or None if no origin.
        """
        pass
