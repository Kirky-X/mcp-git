"""Workspace management operations for Git Service Facade.

This module contains workspace-related operations extracted from the facade.
"""

from typing import Any
from uuid import UUID

from mcp_git.service.workspace_manager import WorkspaceManager


class WorkspaceOperations:
    """Workspace management operations."""

    def __init__(self, workspace_manager: WorkspaceManager):
        """
        Initialize workspace operations.

        Args:
            workspace_manager: Workspace manager instance
        """
        self.workspace_manager = workspace_manager

    async def allocate_workspace(self) -> dict[str, Any]:
        """
        Allocate a new workspace.

        Returns:
            Workspace information
        """
        workspace = await self.workspace_manager.allocate_workspace()
        return {
            "id": str(workspace.id),
            "path": str(workspace.path),
            "created_at": workspace.created_at.isoformat(),
        }

    async def get_workspace(self, workspace_id: UUID) -> dict[str, Any] | None:
        """
        Get workspace information.

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace information or None
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            return None

        return {
            "id": str(workspace.id),
            "path": str(workspace.path),
            "created_at": workspace.created_at.isoformat(),
            "size_bytes": workspace.size_bytes,
            "last_accessed_at": workspace.last_accessed_at.isoformat()
            if workspace.last_accessed_at
            else None,
        }

    async def release_workspace(self, workspace_id: UUID) -> bool:
        """
        Release a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            True if released, False if not found
        """
        return await self.workspace_manager.release_workspace(workspace_id)

    async def list_workspaces(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        List all workspaces.

        Args:
            limit: Maximum number of workspaces to return

        Returns:
            List of workspace information
        """
        workspaces = await self.workspace_manager.list_workspaces(limit=limit)
        return [
            {
                "id": str(ws.id),
                "path": str(ws.path),
                "created_at": ws.created_at.isoformat(),
                "size_bytes": ws.size_bytes,
                "last_accessed_at": ws.last_accessed_at.isoformat()
                if ws.last_accessed_at
                else None,
            }
            for ws in workspaces
        ]

    async def get_workspace_usage(self) -> dict[str, Any]:
        """
        Get workspace usage statistics.

        Returns:
            Usage statistics
        """
        workspaces = await self.workspace_manager.list_workspaces()
        total_size = sum(ws.size_bytes for ws in workspaces)
        return {
            "total_workspaces": len(workspaces),
            "total_size_bytes": total_size,
            "average_size_bytes": total_size / len(workspaces) if workspaces else 0,
        }
