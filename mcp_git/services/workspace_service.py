"""
Workspace management service implementation.

This module provides the workspace management service for the microservices architecture.
"""

from uuid import UUID

from loguru import logger

from mcp_git.service.workspace_manager import WorkspaceManager
from mcp_git.services.service_interface import WorkspaceServiceInterface
from mcp_git.storage.models import Workspace


class WorkspaceService(WorkspaceServiceInterface):
    """
    Workspace management service.

    This service handles workspace allocation, release, and cleanup.
    """

    def __init__(self, workspace_manager: WorkspaceManager):
        """
        Initialize the workspace service.

        Args:
            workspace_manager: Workspace manager instance
        """
        self.workspace_manager = workspace_manager

    async def allocate_workspace(self) -> Workspace:
        """
        Allocate a new workspace.

        Returns:
            Allocated workspace
        """
        logger.info("Allocating new workspace")

        workspace = await self.workspace_manager.allocate_workspace()

        logger.info("Workspace allocated", workspace_id=str(workspace.id))
        return workspace

    async def release_workspace(self, workspace_id: UUID) -> bool:
        """
        Release a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            True if released, False otherwise
        """
        logger.info("Releasing workspace", workspace_id=str(workspace_id))

        success = await self.workspace_manager.release_workspace(workspace_id)

        if success:
            logger.info("Workspace released", workspace_id=str(workspace_id))
        else:
            logger.warning("Workspace not found", workspace_id=str(workspace_id))

        return success

    async def get_workspace_size(self, workspace_id: UUID) -> int:
        """
        Get workspace size in bytes.

        Args:
            workspace_id: Workspace ID

        Returns:
            Size in bytes
        """
        logger.debug("Getting workspace size", workspace_id=str(workspace_id))

        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        return workspace.size_bytes

    async def cleanup_expired_workspaces(self) -> tuple[int, int]:
        """
        Clean up expired workspaces.

        Returns:
            Tuple of (cleaned_count, freed_space)
        """
        logger.info("Cleaning up expired workspaces")

        cleaned = await self.workspace_manager.cleanup_expired_workspaces()

        logger.info("Cleanup completed", count=cleaned[0], freed_space=cleaned[1])
        return cleaned
