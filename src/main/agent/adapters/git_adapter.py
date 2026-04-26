"""
Git Adapter - Concrete implementation using GitPython.

This adapter implements RepoInterface using GitPython library,
providing git operations for local repositories.
"""

from typing import Any
import os
from pathlib import Path

import git
from git import Repo, GitCommandError

from src.main.agent.interfaces.repo_interface import (
    RepoInterface,
    RepoStatus,
    CommitInfo,
    PRInfo,
    BranchInfo,
    DiffInfo,
    TagInfo,
)
from src.main.agent.exceptions import ConnectionError, ValidationError


class GitAdapter(RepoInterface):
    """
    Git adapter using GitPython.

    Provides local git operations for repositories.

    Usage:
        adapter = GitAdapter()
        adapter.clone("https://github.com/user/repo.git", "/path/to/repo")
        adapter.commit("Initial commit", files=["file1.py"])
    """

    def __init__(self, path: str | None = None):
        """
        Initialize Git adapter.

        Args:
            path: Optional path to existing repository.
        """
        self._repo: Repo | None = None
        if path:
            self._repo = Repo(path)

    def clone(self, url: str, path: str, branch: str | None = None) -> bool:
        """
        Clone a repository to local path.

        Args:
            url: Repository URL.
            path: Local destination path.
            branch: Optional branch to checkout.

        Returns:
            True if cloned successfully.

        Raises:
            ConnectionError: On clone failure.
        """
        try:
            if branch:
                self._repo = Repo.clone_from(url, path, branch=branch)
            else:
                self._repo = Repo.clone_from(url, path)
            return True
        except GitCommandError as e:
            raise ConnectionError(f"Failed to clone repository: {e}") from e

    def get_status(self) -> RepoStatus:
        """Get current repository status."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        if not self._repo.head.is_detached:
            if self._repo.is_dirty():
                return RepoStatus.DIRTY
            return RepoStatus.CLEAN
        return RepoStatus.DETACHED

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        try:
            return self._repo.active_branch.name
        except TypeError:
            return self._repo.head.commit.hexsha[:7]

    def list_branches(self, remote: bool = False) -> list[BranchInfo]:
        """List all branches."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        branches = []
        if remote:
            for ref in self._repo.remote().refs:
                branches.append(BranchInfo(
                    name=ref.name.replace("origin/", ""),
                    is_current=False,
                    is_remote=True,
                    tracking_branch=ref.name,
                    ahead_behind=None,
                    last_commit_sha=ref.commit.hexsha if ref.commit else None,
                ))
        else:
            for branch in self._repo.branches:
                branches.append(BranchInfo(
                    name=branch.name,
                    is_current=branch == self._repo.active_branch,
                    is_remote=False,
                    tracking_branch=None,
                    ahead_behind=None,
                    last_commit_sha=branch.commit.hexsha if branch.commit else None,
                ))

        return branches

    def create_branch(self, name: str, checkout: bool = True) -> BranchInfo:
        """Create a new branch."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        try:
            branch = self._repo.create_head(name)
            if checkout:
                branch.checkout()

            return BranchInfo(
                name=name,
                is_current=checkout,
                is_remote=False,
                tracking_branch=None,
                ahead_behind=(0, 0),
                last_commit_sha=self._repo.head.commit.hexsha,
            )
        except GitCommandError as e:
            raise ValidationError(f"Failed to create branch: {e}") from e

    def delete_branch(self, name: str, force: bool = False) -> bool:
        """Delete a branch."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        try:
            branch = self._repo.branches[name]
            self._repo.delete_head(branch, force=force)
            return True
        except GitCommandError:
            return False

    def checkout(self, ref: str, create_branch: bool = False) -> bool:
        """Checkout a branch, commit, or tag."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        try:
            if create_branch:
                self._repo.git.checkout("-b", ref)
            else:
                self._repo.git.checkout(ref)
            return True
        except GitCommandError as e:
            raise ValidationError(f"Checkout failed: {e}") from e

    def get_diff(self, ref: str | None = None) -> list[DiffInfo]:
        """Get diff of changes."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        diffs = []
        try:
            if ref:
                # Diff against specific ref
                parent = self._repo.commit(ref)
                for commit in parent.traverse():
                    break
                diff_index = commit.diff(None)
            else:
                # Unstaged changes
                diff_index = self._repo.index.diff(None)

            for diff in diff_index:
                diffs.append(DiffInfo(
                    file_path=diff.b_path if diff.b_path else diff.a_path,
                    status="renamed" if diff.renamed else ("modified" if diff.diff else "added"),
                    additions=0,  # Would need more complex parsing
                    deletions=0,
                    old_path=diff.a_path if diff.renamed else None,
                    diff=str(diff.diff) if diff.diff else None,
                ))

        except GitCommandError:
            pass

        return diffs

    def stage_files(self, files: list[str], all: bool = False) -> bool:
        """Stage files for commit."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        try:
            if all:
                self._repo.index.add(["*"])
            else:
                self._repo.index.add(files)
            return True
        except GitCommandError as e:
            raise ValidationError(f"Failed to stage files: {e}") from e

    def commit(self, message: str, files: list[str] | None = None) -> CommitInfo:
        """Commit staged changes."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        try:
            if files:
                self._repo.index.add(files)

            commit = self._repo.index.commit(message)

            return CommitInfo(
                sha=commit.hexsha,
                message=commit.message,
                author=str(commit.author),
                author_email=commit.author.email,
                timestamp=commit.committed_datetime.isoformat(),
                files_changed=[],
                insertions=0,
                deletions=0,
            )
        except GitCommandError as e:
            raise ValidationError(f"Failed to commit: {e}") from e

    def push(
        self,
        branch: str | None = None,
        force: bool = False,
        upstream: bool = False,
    ) -> bool:
        """Push commits to remote."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        try:
            if self._repo.remotes:
                remote = self._repo.remote()[0]
                refspec = f"+{branch or self.get_current_branch()}"
                if upstream:
                    remote.push(refspec, set_upstream=True)
                elif force:
                    remote.push(refspec, force=force)
                else:
                    remote.push(refspec)
            return True
        except GitCommandError as e:
            raise ConnectionError(f"Push failed: {e}") from e

    def pull(self, branch: str | None = None, rebase: bool = False) -> bool:
        """Pull changes from remote."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        try:
            if self._repo.remotes:
                remote = self._repo.remote()[0]
                if rebase:
                    remote.pull(rebase=True)
                else:
                    remote.pull()
            return True
        except GitCommandError as e:
            raise ConnectionError(f"Pull failed: {e}") from e

    def fetch(self, remote: str | None = None, all: bool = False) -> bool:
        """Fetch changes from remote."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        try:
            if all:
                for remote in self._repo.remotes:
                    remote.fetch()
            elif remote:
                self._repo.remotes[remote].fetch()
            else:
                self._repo.remotes[0].fetch() if self._repo.remotes else None
            return True
        except GitCommandError:
            return False

    def create_pr(
        self,
        title: str,
        body: str,
        source_branch: str,
        target_branch: str,
        draft: bool = False,
    ) -> PRInfo:
        """
        Create a pull request.

        Note: This requires GitHub/GitLab CLI or API integration.
        For local git, this creates a local branch and commits.

        For actual PR creation, use GitAdapter with GitHub API.
        """
        if not self._repo:
            raise ConnectionError("No repository initialized")

        # Create branch and commit if needed
        current = self.get_current_branch()

        if source_branch != current:
            self.create_branch(source_branch, checkout=True)

        return PRInfo(
            number=0,
            title=title,
            description=body,
            source_branch=source_branch,
            target_branch=target_branch,
            url=None,
            status="open" if not draft else "draft",
            review_status="pending",
            author=self._repo.config_reader().get_value("user", "name", "unknown"),
            created_at="",
            updated_at=None,
        )

    def get_pr(self, pr_number: int | None = None) -> PRInfo | None:
        """Get pull request information (requires remote API)."""
        # PR info requires GitHub/GitLab API
        return None

    def merge_pr(self, pr_number: int, method: str = "merge") -> bool:
        """Merge a pull request (requires remote API)."""
        # Merge requires GitHub/GitLab API
        return False

    def get_commit_history(
        self,
        ref: str | None = None,
        limit: int = 100,
    ) -> list[CommitInfo]:
        """Get commit history."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        commits = []
        try:
            if ref:
                commits_iter = self._repo.iter_commits(ref, max_count=limit)
            else:
                commits_iter = self._repo.iter_commits(max_count=limit)

            for commit in commits_iter:
                commits.append(CommitInfo(
                    sha=commit.hexsha,
                    message=commit.message,
                    author=str(commit.author),
                    author_email=commit.author.email,
                    timestamp=commit.committed_datetime.isoformat(),
                    files_changed=[],
                    insertions=0,
                    deletions=0,
                ))

        except GitCommandError:
            pass

        return commits

    def get_tags(self) -> list[TagInfo]:
        """Get all tags."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        tags = []
        for tag in self._repo.tags:
            tags.append(TagInfo(
                name=str(tag),
                sha=tag.commit.hexsha if tag.commit else None,
                message=None,
                author=str(tag.commit.author) if tag.commit else None,
                date=tag.commit.committed_datetime.isoformat() if tag.commit else None,
            ))

        return tags

    def create_tag(
        self,
        name: str,
        ref: str | None = None,
        message: str | None = None,
    ) -> TagInfo:
        """Create a tag."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        try:
            if message:
                tag = self._repo.create_tag(name, ref=ref, message=message)
            else:
                tag = self._repo.create_tag(name, ref=ref)

            return TagInfo(
                name=name,
                sha=tag.commit.hexsha if tag.commit else None,
                message=message,
                author=str(tag.commit.author) if tag.commit else None,
                date=tag.commit.committed_datetime.isoformat() if tag.commit else None,
            )
        except GitCommandError as e:
            raise ValidationError(f"Failed to create tag: {e}") from e

    def get_remote_url(self) -> str | None:
        """Get the URL of the origin remote."""
        if not self._repo:
            raise ConnectionError("No repository initialized")

        if self._repo.remotes:
            return self._repo.remotes[0].url
        return None
