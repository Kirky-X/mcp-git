"""
Workspace management for mcp-git.

This module manages temporary workspaces where Git repositories
are cloned and operated on.
"""

import asyncio
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel

from mcp_git.storage import SqliteStorage, Workspace
from mcp_git.storage.models import CleanupStrategy

UTC = timezone.utc


class WorkspaceConfig(BaseModel):
    """Configuration for workspace management."""

    root_path: Path
    max_size_bytes: int = 10 * 1024 * 1024 * 1024  # 10GB total
    retention_seconds: int = 3600  # 1 hour
    cleanup_strategy: CleanupStrategy = CleanupStrategy.LRU
    max_workspaces: int | None = None  # No limit by default
    # Per-workspace size limit (None = use max_size_bytes / 10 as default)
    max_per_workspace_bytes: int | None = None


class WorkspaceAllocation:
    """Result of workspace allocation."""

    def __init__(
        self,
        workspace: Workspace,
        cleanup_needed: bool = False,
        freed_bytes: int = 0,
    ):
        self.workspace = workspace
        self.cleanup_needed = cleanup_needed
        self.freed_bytes = freed_bytes


class WorkspaceManager:
    """Manager for temporary Git workspaces."""

    def __init__(
        self,
        storage: SqliteStorage,
        config: WorkspaceConfig,
    ):
        """
        Initialize the workspace manager.

        Args:
            storage: SQLite storage for persistence
            config: Workspace configuration
        """
        self.storage = storage
        self.config = config

        # Ensure root path exists
        config.root_path.mkdir(parents=True, exist_ok=True)

        # Background cleanup task
        self._cleanup_task: asyncio.Task | None = None
        self._cleanup_event = asyncio.Event()

    async def start(self) -> None:
        """Start the workspace manager."""
        logger.info(
            "Starting workspace manager",
            root=str(self.config.root_path),
            max_size=self.config.max_size_bytes,
            retention=self.config.retention_seconds,
        )

        # Ensure root directory exists
        self.config.root_path.mkdir(parents=True, exist_ok=True)

        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop the workspace manager."""
        logger.info("Stopping workspace manager")

        if self._cleanup_task:
            self._cleanup_event.set()
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def allocate_workspace(self) -> Workspace:
        """
        Allocate a new workspace.

        This creates a new unique directory for a Git repository.

        Returns:
            Workspace object with path information

        Raises:
            OSError: If workspace cannot be created
        """
        # Generate unique workspace ID
        workspace_id = uuid4()
        workspace_path = self.config.root_path / str(workspace_id)

        # Ensure parent directory exists
        self.config.root_path.mkdir(parents=True, exist_ok=True)

        try:
            # Create workspace directory
            workspace_path.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            # Should not happen with UUID, but handle gracefully
            workspace_id = uuid4()
            workspace_path = self.config.root_path / str(workspace_id)
            workspace_path.mkdir(parents=True, exist_ok=False)

        # Create workspace record
        workspace = Workspace(
            id=workspace_id,
            path=workspace_path,
            size_bytes=0,
            last_accessed_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )

        # Persist to database
        await self.storage.create_workspace(workspace)

        logger.info(
            "Workspace allocated",
            workspace_id=str(workspace_id),
            path=str(workspace_path),
        )

        return workspace

    async def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        """
        Get workspace by ID.

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace if found, None otherwise
        """
        return await self.storage.get_workspace(workspace_id)

    async def get_workspace_by_path(self, path: Path) -> Workspace | None:
        """
        Get workspace by path.

        Args:
            path: Workspace path

        Returns:
            Workspace if found, None otherwise
        """
        return await self.storage.get_workspace_by_path(path)

    async def touch_workspace(self, workspace_id: UUID) -> None:
        """
        Update workspace access time.

        This is called when the workspace is used to update
        the LRU ordering for cleanup.

        Args:
            workspace_id: Workspace ID
        """
        await self.storage.update_workspace(
            workspace_id,
            last_accessed_at=datetime.now(UTC),
        )

    async def update_workspace_size(
        self,
        workspace_id: UUID,
        path: Path | None = None,
    ) -> None:
        """
        Update workspace size in bytes.

        Args:
            workspace_id: Workspace ID
            path: Optional path to measure (uses workspace path if not provided)
        """
        workspace = await self.storage.get_workspace(workspace_id)
        if workspace is None:
            return

        if path is None:
            path = workspace.path

        try:
            size = self._get_directory_size(path)
            await self.storage.update_workspace(
                workspace_id,
                size_bytes=size,
                last_accessed_at=datetime.now(UTC),
            )
        except OSError:
            pass  # Directory may have been deleted

    async def release_workspace(self, workspace_id: UUID) -> bool:
        """
        Release a workspace, cleaning up files.

        Args:
            workspace_id: Workspace ID

        Returns:
            True if released, False if not found
        """
        workspace = await self.storage.get_workspace(workspace_id)
        if workspace is None:
            return False

        # Delete workspace directory
        try:
            if workspace.path.exists():
                shutil.rmtree(workspace.path)
        except OSError as e:
            logger.warning(
                "Failed to remove workspace directory",
                workspace_id=str(workspace_id),
                path=str(workspace.path),
                error=str(e),
            )

        # Delete from database
        await self.storage.delete_workspace(workspace_id)

        logger.info(
            "Workspace released",
            workspace_id=str(workspace_id),
            path=str(workspace.path),
        )

        return True

    async def cleanup_expired_workspaces(self) -> tuple[int, int]:
        """
        Clean up expired workspaces.

        Returns:
            Tuple of (cleaned_count, freed_bytes)
        """
        cleaned = 0
        freed = 0

        # Get oldest workspaces by access time
        workspaces = await self.storage.get_oldest_workspaces(100)

        # Calculate thresholds
        cutoff = datetime.now(UTC) - timedelta(seconds=self.config.retention_seconds)

        for workspace in workspaces:
            # Check if expired
            if workspace.last_accessed_at and workspace.last_accessed_at < cutoff:
                # Get size before deletion
                size = await self._get_workspace_size(workspace)

                # Release workspace
                await self.release_workspace(workspace.id)

                cleaned += 1
                freed += size

        if cleaned > 0:
            logger.info(
                "Cleaned up expired workspaces",
                count=cleaned,
                freed_bytes=freed,
            )

        return cleaned, freed

    async def cleanup_by_size(self) -> tuple[int, int]:
        """
        Clean up workspaces to free disk space.

        Returns:
            Tuple of (cleaned_count, freed_bytes)
        """
        cleaned = 0
        freed = 0

        # Get total workspace size
        total_size = await self.storage.get_workspace_total_size()

        # Check if we need to free space
        if total_size <= self.config.max_size_bytes:
            return 0, 0

        # Calculate how much to free
        target_size = self.config.max_size_bytes * 0.8  # Target 80% of max

        # Get oldest workspaces
        workspaces = await self.storage.get_oldest_workspaces(100)

        for workspace in workspaces:
            if total_size <= target_size:
                break

            size = await self._get_workspace_size(workspace)
            await self.release_workspace(workspace.id)

            cleaned += 1
            freed += size
            total_size -= size

        if cleaned > 0:
            logger.info(
                "Cleaned up workspaces for size",
                count=cleaned,
                freed_bytes=freed,
            )

        return cleaned, freed

    async def list_workspaces(self, limit: int = 100) -> list[Workspace]:
        """
        List all workspaces.

        Args:
            limit: Maximum number to return

        Returns:
            List of workspaces
        """
        return await self.storage.list_workspaces(limit=limit)

    async def get_workspace_usage(self) -> dict:
        """
        Get workspace disk usage information.

        Returns:
            Dictionary with usage statistics
        """
        workspaces = await self.list_workspaces(1000)

        total_size = 0
        for ws in workspaces:
            total_size += ws.size_bytes or 0

        return {
            "total_workspaces": len(workspaces),
            "total_size_bytes": total_size,
            "max_size_bytes": self.config.max_size_bytes,
            "usage_percent": (
                (total_size / self.config.max_size_bytes) * 100
                if self.config.max_size_bytes > 0
                else 0
            ),
        }

    async def _cleanup_loop(self) -> None:
        """Background task for periodic cleanup."""
        while not self._cleanup_event.is_set():
            try:
                # Wait for cleanup interval or event
                await asyncio.wait_for(
                    self._cleanup_event.wait(),
                    timeout=300,  # 5 minutes
                )
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue cleanup

            # Perform cleanup
            try:
                await self.cleanup_expired_workspaces()
                await self.cleanup_by_size()
            except Exception as e:
                logger.error("Cleanup error", error=str(e))

    async def _get_workspace_size(self, workspace: Workspace) -> int:
        """Get workspace size in bytes."""
        try:
            return await self._get_directory_size(workspace.path)
        except OSError:
            return workspace.size_bytes or 0

    async def _get_directory_size(self, path: Path) -> int:
        """
        Get total size of directory in bytes.

        Uses asyncio.to_thread to avoid blocking the event loop.
        """
        import asyncio

        def _calculate_size_sync() -> int:
            total = 0
            try:
                # Use os.walk for better performance than Path.rglob
                for root, _dirs, files in os.walk(path):
                    for file in files:
                        file_path = Path(root) / file
                        try:
                            total += file_path.stat().st_size
                        except (OSError, FileNotFoundError):
                            pass
            except (OSError, PermissionError):
                pass
            return total

        # Run in a separate thread to avoid blocking the event loop
        return await asyncio.to_thread(_calculate_size_sync)

    def get_per_workspace_limit(self) -> int:
        """Get the per-workspace size limit in bytes."""
        if self.config.max_per_workspace_bytes:
            return self.config.max_per_workspace_bytes
        # Default: 10% of total workspace limit
        return max(self.config.max_size_bytes // 10, 1024 * 1024 * 1024)  # Min 1GB

    async def check_workspace_size_limit(
        self,
        workspace_id: UUID,
    ) -> tuple[bool, int]:
        """
        Check if workspace is within size limits.

        Args:
            workspace_id: Workspace ID

        Returns:
            Tuple of (is_within_limit, current_size_bytes)
        """
        workspace = await self.storage.get_workspace(workspace_id)
        if workspace is None:
            return True, 0

        size = workspace.size_bytes or 0
        limit = self.get_per_workspace_limit()

        return size < limit, size

    async def enforce_workspace_size_limit(
        self,
        workspace_id: UUID,
    ) -> bool:
        """
        Enforce workspace size limit by cleaning up if necessary.

        Args:
            workspace_id: Workspace ID

        Returns:
            True if workspace is now within limits, False otherwise
        """
        is_within, size = await self.check_workspace_size_limit(workspace_id)
        if is_within:
            return True

        # Try to clean up large files or the entire workspace
        workspace = await self.storage.get_workspace(workspace_id)
        if workspace is None:
            return False

        limit = self.get_per_workspace_limit()

        # If over limit by more than 20%, release the workspace
        if size > limit * 1.2:
            await self.release_workspace(workspace_id)
            logger.warning(
                "Workspace exceeded size limit, released",
                workspace_id=str(workspace_id),
                size_bytes=size,
                limit_bytes=limit,
            )
            return False

        # Otherwise just log a warning
        logger.warning(
            "Workspace approaching size limit",
            workspace_id=str(workspace_id),
            size_bytes=size,
            limit_bytes=limit,
        )
        return True

    def validate_workspace_path(self, path: Path) -> bool:
        """
        Validate that a path is within the workspace root.

        This prevents path traversal attacks.

        Args:
            path: Path to validate

        Returns:
            True if path is valid
        """
        try:
            # Resolve to absolute path
            resolved = path.resolve()

            # Check if it's within the workspace root
            return resolved.is_relative_to(self.config.root_path)
        except (ValueError, OSError):
            return False

    def get_disk_space_info(self) -> dict:
        """
        Get disk space information for the workspace root filesystem.

        Returns:
            Dictionary with disk space statistics
        """
        import shutil

        total, used, free = shutil.disk_usage(self.config.root_path)

        return {
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "usage_percent": (used / total * 100) if total > 0 else 0,
        }

    def check_disk_space_warning(self, warning_threshold: float = 20.0) -> dict:
        """
        Check disk space and return warning status.

        Args:
            warning_threshold: Percentage of free space below which to warn

        Returns:
            Dictionary with warning status and disk info
        """
        disk_info = self.get_disk_space_info()

        free_percent = (
            (disk_info["free_bytes"] / disk_info["total_bytes"] * 100)
            if disk_info["total_bytes"] > 0
            else 0
        )

        is_low = free_percent < warning_threshold

        return {
            "is_low": is_low,
            "warning_threshold_percent": warning_threshold,
            "free_percent": free_percent,
            **disk_info,
        }
