"""
Storage service implementation.

This module provides the storage service for the microservices architecture.
"""

from typing import Any
from uuid import UUID

from loguru import logger

from mcp_git.services.service_interface import StorageServiceInterface
from mcp_git.storage.models import Workspace
from mcp_git.storage.sqlite import SqliteStorage


class StorageService(StorageServiceInterface):
    """
    Storage service.

    This service handles all storage operations including workspace management
    and task persistence.
    """

    def __init__(self, storage: SqliteStorage):
        """
        Initialize the storage service.

        Args:
            storage: Storage instance
        """
        self.storage = storage

    async def create_workspace(self, workspace: Workspace) -> Workspace:
        """
        Create a new workspace.

        Args:
            workspace: Workspace to create

        Returns:
            Created workspace
        """
        logger.info("Creating workspace", workspace_id=str(workspace.id))

        return await self.storage.create_workspace(workspace)

    async def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        """
        Get a workspace by ID.

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace or None
        """
        logger.debug("Getting workspace", workspace_id=str(workspace_id))

        return await self.storage.get_workspace(workspace_id)

    async def list_workspaces(self) -> list[Workspace]:
        """
        List all workspaces.

        Returns:
            List of workspaces
        """
        logger.debug("Listing workspaces")

        return await self.storage.list_workspaces()

    async def update_workspace(
        self,
        workspace_id: UUID,
        **kwargs,
    ) -> bool:
        """
        Update workspace.

        Args:
            workspace_id: Workspace ID
            **kwargs: Fields to update

        Returns:
            True if updated, False otherwise
        """
        logger.info("Updating workspace", workspace_id=str(workspace_id))

        return await self.storage.update_workspace(workspace_id, **kwargs)

    async def delete_workspace(self, workspace_id: UUID) -> bool:
        """
        Delete a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            True if deleted, False otherwise
        """
        logger.info("Deleting workspace", workspace_id=str(workspace_id))

        return await self.storage.delete_workspace(workspace_id)