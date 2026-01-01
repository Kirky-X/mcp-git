"""
MCP Server implementation for mcp-git.

This module provides the main MCP server that handles client connections,
processes requests, and manages the Git service facade.
"""

import asyncio
import signal
from typing import Any
from uuid import UUID

from loguru import logger
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from mcp_git.config import Config, load_config
from mcp_git.error import ErrorCode, McpGitError
from mcp_git.service.facade import GitServiceFacade
from mcp_git.service.task_manager import TaskConfig
from mcp_git.service.workspace_manager import WorkspaceConfig
from mcp_git.storage import SqliteStorage


class McpGitServer:
    """
    MCP Git Server implementation.

    This class manages the MCP server lifecycle, handles requests,
    and provides access to Git operations through the service facade.
    """

    def __init__(self, config: Config | None = None):
        """
        Initialize the MCP server.

        Args:
            config: Server configuration
        """
        self.config = config or load_config()
        self.server = Server("mcp-git")

        # Initialize storage
        self.storage = SqliteStorage(self.config.database.path)
        self._storage_initialized = False

        # Initialize facade
        self.facade: GitServiceFacade | None = None

        # Register handlers
        self._register_handlers()

        # Running state
        self._running = False

    def _register_handlers(self) -> None:
        """Register MCP request handlers."""
        from mcp_git.server.handlers import handle_call_tool, handle_list_tools

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return handle_list_tools()

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            return await handle_call_tool(self, name, arguments)

    async def initialize(self) -> None:
        """Initialize server components."""
        logger.info("Initializing MCP server")

        try:
            # Initialize storage
            await self.storage.initialize()
            self._storage_initialized = True

            # Initialize facade
            workspace_config = WorkspaceConfig(
                root_path=self.config.workspace.path,
                max_size_bytes=self.config.workspace.max_size_bytes,
                retention_seconds=self.config.workspace.retention_seconds,
            )

            task_config = TaskConfig(
                max_concurrent_tasks=self.config.execution.max_concurrent_tasks,
                task_timeout_seconds=self.config.execution.task_timeout_seconds,
                result_retention_seconds=self.config.database.task_retention_seconds,
            )

            self.facade = GitServiceFacade(
                storage=self.storage,
                workspace_config=workspace_config,
                task_config=task_config,
            )

            await self.facade.start()

            # Start metrics server
            from mcp_git.metrics import start_metrics_server

            metrics_port = self.config.metrics_port or 9090
            try:
                start_metrics_server(metrics_port)
                logger.info(f"Metrics server started on port {metrics_port}")
            except OSError as e:
                logger.warning(f"Failed to start metrics server on port {metrics_port}: {e}")

            logger.info("MCP server initialized")
        except Exception as e:
            # Clean up resources if initialization fails
            logger.error("Server initialization failed, cleaning up resources", error=str(e))
            await self._cleanup_on_error()
            raise

    async def get_health(self) -> dict[str, Any]:
        """
        Get server health status.

        Returns:
            Dictionary containing health status information
        """
        health = {
            "status": "healthy",
            "components": {
                "storage": "ok" if self._storage_initialized else "not_initialized",
                "facade": "ok" if self.facade else "not_initialized",
            },
            "version": "1.0.0",
        }

        # Check facade health if available
        if self.facade:
            try:
                active_tasks = await self.facade.task_manager.get_active_tasks()
                components = health["components"]
                if isinstance(components, dict):
                    components["workers"] = f"{len(active_tasks)} active"
            except Exception:
                components = health["components"]
                if isinstance(components, dict):
                    components["workers"] = "unknown"

        return health

    async def _cleanup_on_error(self) -> None:
        """Clean up resources after initialization error."""
        try:
            if self.facade:
                await self.facade.stop()
                self.facade = None
        except Exception as e:
            logger.warning("Error stopping facade during cleanup", error=str(e))

        try:
            if self._storage_initialized:
                await self.storage.close()
                self._storage_initialized = False
        except Exception as e:
            logger.warning("Error closing storage during cleanup", error=str(e))

    async def shutdown(self) -> None:
        """Shutdown server components."""
        logger.info("Shutting down MCP server")

        if self.facade:
            await self.facade.stop()

        if self._storage_initialized:
            await self.storage.close()

        self._running = False
        logger.info("MCP server shutdown complete")

    async def run(self) -> None:
        """Run the MCP server."""
        if self._running:
            return

        await self.initialize()
        self._running = True

        logger.info(
            "Starting MCP server",
            transport=self.config.server.transport,
        )

        # Handle shutdown signals
        loop = asyncio.get_event_loop()

        def signal_handler() -> None:
            logger.info("Received shutdown signal")
            asyncio.create_task(self.shutdown())

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

        # Run server with stdio transport
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )

    # Workspace operations

    async def allocate_workspace(self) -> dict[str, Any]:
        """
        Allocate a new workspace.

        Returns:
            Workspace information
        """
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.allocate_workspace()

    async def get_workspace(self, workspace_id: UUID) -> dict[str, Any] | None:
        """
        Get workspace information.

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace information or None
        """
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.get_workspace(workspace_id)

    async def release_workspace(self, workspace_id: UUID) -> bool:
        """
        Release a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            True if released
        """
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.release_workspace(workspace_id)

    async def list_workspaces(self) -> list[dict[str, Any]]:
        """
        List all workspaces.

        Returns:
            List of workspace information
        """
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.list_workspaces()

    # Git operations

    async def clone(
        self,
        url: str,
        workspace_id: UUID,
        branch: str | None = None,
        depth: int | None = None,
    ) -> dict[str, Any]:
        """
        Clone a repository.

        Args:
            url: Repository URL
            workspace_id: Workspace ID
            branch: Optional branch
            depth: Optional clone depth

        Returns:
            Clone result
        """
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")

        from mcp_git.git.adapter import CloneOptions

        options = CloneOptions(
            branch=branch,
            depth=depth,
            single_branch=branch is not None,
        )

        return await self.facade.clone(url, workspace_id, options)

    async def init_repository(
        self,
        workspace_id: UUID,
        bare: bool = False,
        default_branch: str = "main",
    ) -> None:
        """Initialize a repository."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.init(workspace_id, bare, default_branch)

    async def get_status(self, workspace_id: UUID) -> list[dict[str, Any]]:
        """Get repository status."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.status(workspace_id)

    async def stage_files(
        self,
        workspace_id: UUID,
        files: list[str],
    ) -> None:
        """Stage files."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.add(workspace_id, files)

    async def create_commit(
        self,
        workspace_id: UUID,
        message: str,
        author_name: str | None = None,
        author_email: str | None = None,
    ) -> str:
        """Create a commit."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.commit(workspace_id, message, author_name, author_email)

    async def push(
        self,
        workspace_id: UUID,
        remote: str = "origin",
        branch: str | None = None,
        force: bool = False,
    ) -> None:
        """Push to remote."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.push(workspace_id, remote, branch, force)

    async def pull(
        self,
        workspace_id: UUID,
        remote: str = "origin",
        branch: str | None = None,
        rebase: bool = False,
    ) -> None:
        """Pull from remote."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.pull(workspace_id, remote, branch, rebase)

    async def fetch(
        self,
        workspace_id: UUID,
        remote: str | None = None,
        tags: bool = False,
    ) -> None:
        """Fetch from remote."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.fetch(workspace_id, remote, tags)

    async def checkout(
        self,
        workspace_id: UUID,
        branch: str,
        create_new: bool = False,
        force: bool = False,
    ) -> None:
        """Checkout a branch."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.checkout(workspace_id, branch, create_new, force)

    async def list_branches(
        self,
        workspace_id: UUID,
        local: bool = True,
        remote: bool = False,
        all: bool = False,
    ) -> list[dict[str, Any]]:
        """List branches."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.list_branches(workspace_id, local, remote, all)

    async def create_branch(
        self,
        workspace_id: UUID,
        name: str,
        revision: str | None = None,
        force: bool = False,
    ) -> None:
        """Create a branch."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.create_branch(workspace_id, name, revision, force)

    async def delete_branch(
        self,
        workspace_id: UUID,
        name: str,
        force: bool = False,
        remote: bool = False,
    ) -> None:
        """Delete a branch."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.delete_branch(workspace_id, name, force, remote)

    async def merge(
        self,
        workspace_id: UUID,
        source_branch: str,
        fast_forward: bool = True,
    ) -> dict[str, Any]:
        """Merge branches."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.merge(workspace_id, source_branch, fast_forward)

    async def rebase(
        self,
        workspace_id: UUID,
        branch: str | None = None,
        abort: bool = False,
        continue_rebase: bool = False,
    ) -> None:
        """Rebase branch."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.rebase(workspace_id, branch, abort, continue_rebase)

    async def get_log(
        self,
        workspace_id: UUID,
        max_count: int | None = None,
        author: str | None = None,
        all: bool = False,
    ) -> list[dict[str, Any]]:
        """Get commit log."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.log(workspace_id, max_count, None, None, author, all)

    async def show_commit(
        self,
        workspace_id: UUID,
        revision: str,
    ) -> dict[str, Any]:
        """Show a commit."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.show(workspace_id, revision)

    async def get_diff(
        self,
        workspace_id: UUID,
        cached: bool = False,
        commit_oid: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get diff."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.diff(workspace_id, cached, commit_oid)

    async def get_blame(
        self,
        workspace_id: UUID,
        path: str,
    ) -> list[dict[str, Any]]:
        """Get blame information."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.blame(workspace_id, path)

    async def stash_changes(
        self,
        workspace_id: UUID,
        save: bool = False,
        pop: bool = False,
        apply: bool = False,
        drop: bool = False,
        message: str | None = None,
        include_untracked: bool = False,
    ) -> str | None:
        """Stash changes."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.stash(
            workspace_id, save, pop, apply, drop, False, message, include_untracked
        )

    async def list_stash(self, workspace_id: UUID) -> list[dict[str, Any]]:
        """List stash entries."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.list_stash(workspace_id)

    async def list_tags(self, workspace_id: UUID) -> list[str]:
        """List tags."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.list_tags(workspace_id)

    async def create_tag(
        self,
        workspace_id: UUID,
        name: str,
        message: str | None = None,
        force: bool = False,
    ) -> None:
        """Create a tag."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.create_tag(workspace_id, name, message, force)

    async def delete_tag(self, workspace_id: UUID, name: str) -> None:
        """Delete a tag."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.delete_tag(workspace_id, name)

    async def list_remotes(self, workspace_id: UUID) -> list[dict[str, str]]:
        """List remotes."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.list_remotes(workspace_id)

    async def add_remote(
        self,
        workspace_id: UUID,
        name: str,
        url: str,
    ) -> None:
        """Add a remote."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.add_remote(workspace_id, name, url)

    async def remove_remote(self, workspace_id: UUID, name: str) -> None:
        """Remove a remote."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.remove_remote(workspace_id, name)

    # Git LFS operations

    async def lfs_init(self, workspace_id: UUID) -> None:
        """Initialize Git LFS in a repository."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.lfs_init(workspace_id)

    async def lfs_track(
        self,
        workspace_id: UUID,
        patterns: list[str],
        lockable: bool = False,
    ) -> list[dict[str, Any]]:
        """Track files with Git LFS."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        result = await self.facade.lfs_track(workspace_id, patterns, lockable)
        return [{"pattern": p, "tracked": True} for p in result]

    async def lfs_untrack(
        self,
        workspace_id: UUID,
        patterns: list[str],
    ) -> list[dict[str, Any]]:
        """Stop tracking files with Git LFS."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        result = await self.facade.lfs_untrack(workspace_id, patterns)
        return [{"pattern": p, "untracked": True} for p in result]

    async def lfs_status(self, workspace_id: UUID) -> list[dict[str, Any]]:
        """Show Git LFS status and tracked files."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.lfs_status(workspace_id)

    async def lfs_pull(
        self,
        workspace_id: UUID,
        objects: list[str] | None = None,
        all: bool = True,
    ) -> None:
        """Download LFS files from the remote repository."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.lfs_pull(workspace_id, objects, all)

    async def lfs_push(
        self,
        workspace_id: UUID,
        remote: str = "origin",
        all: bool = True,
    ) -> None:
        """Push LFS objects to the remote repository."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.lfs_push(workspace_id, remote, all)

    async def lfs_fetch(
        self,
        workspace_id: UUID,
        objects: list[str] | None = None,
    ) -> None:
        """Fetch LFS objects from the remote without merging."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.lfs_fetch(workspace_id, objects)

    async def lfs_install(self, workspace_id: UUID) -> None:
        """Install Git LFS hooks in the repository."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        await self.facade.lfs_install(workspace_id)

    async def sparse_checkout(
        self,
        workspace_id: UUID,
        paths: list[str],
        mode: str = "replace",
    ) -> list[str]:
        """Configure sparse checkout for a repository."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.sparse_checkout(workspace_id, paths, mode)

    # Task operations

    async def get_task(self, task_id: UUID) -> dict[str, Any] | None:
        """Get task information."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        task = await self.facade.get_task(task_id)
        if task:
            return {
                "task_id": str(task.id),
                "operation": task.operation.value
                if hasattr(task.operation, "value")
                else task.operation,
                "status": task.status.value if hasattr(task.status, "value") else task.status,
                "progress": task.progress,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
        return None

    async def list_tasks(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List tasks."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")

        from mcp_git.storage.models import TaskStatus

        task_status = None
        if status:
            try:
                task_status = TaskStatus(status)
            except ValueError:
                pass

        return await self.facade.list_tasks(task_status, limit)

    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a task."""
        if not self.facade:
            raise McpGitError(code=ErrorCode.SYSTEM_ERROR, message="Server not initialized")
        return await self.facade.cancel_task(task_id)

    def get_stats(self) -> dict[str, Any]:
        """Get server statistics."""
        if self.facade:
            return self.facade.get_stats()
        return {}


async def run_server(config: Config | None = None) -> None:
    """
    Run the MCP server.

    Args:
        config: Server configuration
    """
    server = McpGitServer(config)
    await server.run()


def main() -> None:
    """Main entry point."""
    import sys

    config = load_config()

    try:
        asyncio.run(run_server(config))
    except KeyboardInterrupt:
        logger.info("Server interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error("Server error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
