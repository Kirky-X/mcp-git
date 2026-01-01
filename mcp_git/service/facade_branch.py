"""Git branch operations for Git Service Facade.

This module contains branch-related operations extracted from the facade.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from mcp_git.git.adapter import MergeOptions
from mcp_git.utils import sanitize_branch_name

if TYPE_CHECKING:
    from mcp_git.git.adapter import GitAdapter


class BranchOperations:
    """Git branch operations."""

    def __init__(self, adapter: "GitAdapter"):
        """
        Initialize branch operations.

        Args:
            adapter: Git adapter instance
        """
        self.adapter = adapter

    async def list_branches(
        self, repo_path: Path, local: bool = True, remote: bool = False, all: bool = False
    ) -> list[dict[str, Any]]:
        """
        List branches in a repository.

        Args:
            repo_path: Path to the repository
            local: Include local branches
            remote: Include remote branches
            all: Include all branches

        Returns:
            List of branch information
        """
        branches = await self.adapter.list_branches(
            repo_path, local=local, remote=remote, all=all
        )
        return [
            {
                "name": branch.name,
                "oid": branch.oid,
                "is_local": branch.is_local,
                "is_remote": branch.is_remote,
                "upstream_name": branch.upstream_name,
            }
            for branch in branches
        ]

    async def create_branch(
        self, repo_path: Path, name: str, revision: str | None = None
    ) -> str:
        """
        Create a new branch.

        Args:
            repo_path: Path to the repository
            name: Branch name
            revision: Starting revision for the branch

        Returns:
            Branch name
        """
        sanitized_name = sanitize_branch_name(name)
        await self.adapter.create_branch(repo_path, sanitized_name, revision=revision)
        logger.info(f"Created branch {sanitized_name} in {repo_path}")
        return sanitized_name

    async def delete_branch(
        self, repo_path: Path, name: str, force: bool = False
    ) -> None:
        """
        Delete a branch.

        Args:
            repo_path: Path to the repository
            name: Branch name
            force: Whether to force delete
        """
        sanitized_name = sanitize_branch_name(name)
        await self.adapter.delete_branch(repo_path, sanitized_name, force=force)
        logger.info(f"Deleted branch {sanitized_name} from {repo_path}")

    async def merge(
        self, repo_path: Path, branch: str, fast_forward: bool = True, commit: bool = True
    ) -> dict[str, Any]:
        """
        Merge a branch into the current branch.

        Args:
            repo_path: Path to the repository
            branch: Branch to merge
            fast_forward: Use fast-forward merge
            commit: Create a merge commit

        Returns:
            Merge result
        """
        options = MergeOptions(source_branch=branch, fast_forward=fast_forward, commit=commit)
        result = await self.adapter.merge(repo_path, options=options)
        logger.info(f"Merged {branch} into current branch in {repo_path}")
        return {
            "result": result.value,
        }
