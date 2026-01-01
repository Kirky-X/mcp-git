"""
Git remote operations for Git Service Facade.

This module contains remote-related operations extracted from the facade.
"""

from uuid import UUID

from loguru import logger


class RemoteOperations:
    """Git remote operations."""

    def __init__(self, adapter: "GitAdapter"):
        """
        Initialize remote operations.

        Args:
            adapter: Git adapter instance
        """
        self.adapter = adapter

    async def list_remotes(self, repo_path: Path) -> list[dict[str, str]]:
        """
        List remotes in a repository.

        Args:
            repo_path: Path to the repository

        Returns:
            List of remote information
        """
        remotes = await self.adapter.list_remotes(repo_path)
        return [
            {
                "name": remote.name,
                "url": remote.url,
                "fetch_url": remote.fetch_url,
                "push_url": remote.push_url,
            }
            for remote in remotes
        ]

    async def add_remote(
        self, repo_path: Path, name: str, url: str, fetch: str = "+refs/heads/*:refs/remotes/{name}/*"
    ) -> None:
        """
        Add a remote.

        Args:
            repo_path: Path to the repository
            name: Remote name
            url: Remote URL
            fetch: Fetch refspec
        """
        await self.adapter.add_remote(repo_path, name, url, fetch=fetch)
        logger.info(f"Added remote {name} ({url}) to {repo_path}")

    async def remove_remote(self, repo_path: Path, name: str) -> None:
        """
        Remove a remote.

        Args:
            repo_path: Path to the repository
            name: Remote name
        """
        await self.adapter.remove_remote(repo_path, name)
        logger.info(f"Removed remote {name} from {repo_path}")