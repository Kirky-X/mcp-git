"""Git tag operations for Git Service Facade.

This module contains tag-related operations extracted from the facade.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from mcp_git.git.adapter import TagOptions

if TYPE_CHECKING:
    from mcp_git.git.adapter import GitAdapter


class TagOperations:
    """Git tag operations."""

    def __init__(self, adapter: "GitAdapter"):
        """
        Initialize tag operations.

        Args:
            adapter: Git adapter instance
        """
        self.adapter = adapter

    async def list_tags(self, repo_path: Path) -> list[str]:
        """
        List tags in a repository.

        Args:
            repo_path: Path to the repository

        Returns:
            List of tag names
        """
        tags = await self.adapter.list_tags(repo_path)
        return [tag.name for tag in tags]

    async def create_tag(
        self, repo_path: Path, name: str, message: str | None = None, ref: str = "HEAD"
    ) -> str:
        """
        Create a new tag.

        Args:
            repo_path: Path to the repository
            name: Tag name
            message: Tag message
            ref: Reference to tag

        Returns:
            Tag name
        """
        options = TagOptions(message=message)
        await self.adapter.create_tag(repo_path, name, ref=ref, options=options)
        logger.info(f"Created tag {name} at {ref} in {repo_path}")
        return name

    async def delete_tag(self, repo_path: Path, name: str) -> None:
        """
        Delete a tag.

        Args:
            repo_path: Path to the repository
            name: Tag name
        """
        await self.adapter.delete_tag(repo_path, name)
        logger.info(f"Deleted tag {name} from {repo_path}")
