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
        self, repo_path: Path, include_remote: bool = False
    ) -> list[dict[str, Any]]:
        """
        List branches in a repository.

        Args:
            repo_path: Path to the repository
            include_remote: Whether to include remote branches

        Returns:
            List of branch information
        """
        branches = await self.adapter.list_branches(
            repo_path, include_remote=include_remote
        )
        return [
            {
                "name": branch.name,
                "is_remote": branch.is_remote,
                "is_head": branch.is_head,
                "commit_id": branch.commit_id,
            }
            for branch in branches
        ]

    async def create_branch(
        self, repo_path: Path, name: str, start_point: str | None = None
    ) -> str:
        """
        Create a new branch.

        Args:
            repo_path: Path to the repository
            name: Branch name
            start_point: Starting point for the branch

        Returns:
            Branch name
        """
        sanitized_name = sanitize_branch_name(name)
        await self.adapter.create_branch(repo_path, sanitized_name, start_point=start_point)
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
        self, repo_path: Path, branch: str, options: MergeOptions | None = None
    ) -> dict[str, Any]:
        """
        Merge a branch into the current branch.

        Args:
            repo_path: Path to the repository
            branch: Branch to merge
            options: Merge options

        Returns:
            Merge result
        """
        result = await self.adapter.merge(repo_path, branch, options=options or MergeOptions())
        logger.info(f"Merged {branch} into current branch in {repo_path}")
        return {
            "success": result.success,
            "fast_forward": result.fast_forward,
            "conflicts": result.conflicts,
        }
