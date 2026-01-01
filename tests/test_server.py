"""
Tests for server module.

Tests for MCP server initialization, workspace operations, and Git operations.
"""

import socket
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def free_port():
    """Get a free port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


class TestMcpGitServerInitialization:
    """Test McpGitServer initialization."""

    @pytest.mark.asyncio
    async def test_server_initializes_components(self, free_port):
        """Test that server initializes all components correctly."""
        from mcp_git.config import Config
        from mcp_git.server.server import McpGitServer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
                metrics_port=free_port,
            )
            server = McpGitServer(config)
            await server.initialize()

            assert server._storage_initialized is True
            assert server.facade is not None

            await server.shutdown()

    @pytest.mark.asyncio
    async def test_server_double_shutdown(self, free_port):
        """Test that server can be shut down multiple times."""
        from mcp_git.config import Config
        from mcp_git.server.server import McpGitServer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
                metrics_port=free_port,
            )
            server = McpGitServer(config)
            await server.initialize()
            await server.shutdown()
            await server.shutdown()  # Should not raise error


class TestWorkspaceOperations:
    """Test workspace operations through server."""

    @pytest.mark.asyncio
    async def test_allocate_workspace(self, free_port):
        """Test allocating a workspace."""
        from mcp_git.config import Config
        from mcp_git.server.server import McpGitServer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
                metrics_port=free_port,
            )
            server = McpGitServer(config)
            await server.initialize()

            workspace = await server.allocate_workspace()
            assert workspace is not None
            assert "workspace_id" in workspace

            await server.shutdown()

    @pytest.mark.asyncio
    async def test_get_workspace(self, free_port):
        """Test getting a workspace."""
        from mcp_git.config import Config
        from mcp_git.server.server import McpGitServer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
                metrics_port=free_port,
            )
            server = McpGitServer(config)
            await server.initialize()

            # Allocate workspace
            workspace = await server.allocate_workspace()
            workspace_id = workspace["workspace_id"]

            # Get workspace
            result = await server.get_workspace(workspace_id)
            assert result is not None
            assert result["workspace_id"] == workspace_id

            await server.shutdown()

    @pytest.mark.asyncio
    async def test_release_workspace(self, free_port):
        """Test releasing a workspace."""
        from mcp_git.config import Config
        from mcp_git.server.server import McpGitServer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
                metrics_port=free_port,
            )
            server = McpGitServer(config)
            await server.initialize()

            # Allocate workspace
            workspace = await server.allocate_workspace()
            workspace_id = workspace["workspace_id"]

            # Release workspace
            result = await server.release_workspace(workspace_id)
            assert result is True

            await server.shutdown()

    @pytest.mark.asyncio
    async def test_list_workspaces(self, free_port):
        """Test listing workspaces."""
        from mcp_git.config import Config
        from mcp_git.server.server import McpGitServer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
                metrics_port=free_port,
            )
            server = McpGitServer(config)
            await server.initialize()

            # Allocate multiple workspaces
            await server.allocate_workspace()
            await server.allocate_workspace()

            # List workspaces
            workspaces = await server.list_workspaces()
            assert len(workspaces) >= 2

            await server.shutdown()


class TestGitOperations:
    """Test Git operations through server."""

    @pytest.mark.asyncio
    async def test_init_repository(self, free_port):
        """Test initializing a Git repository."""
        from mcp_git.config import Config
        from mcp_git.server.server import McpGitServer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
                metrics_port=free_port,
            )
            server = McpGitServer(config)
            await server.initialize()

            # Allocate workspace
            workspace = await server.allocate_workspace()
            workspace_id = workspace["workspace_id"]

            # Initialize repository
            await server.init_repository(
                workspace_id=workspace_id,
                bare=False,
                default_branch="main",
            )

            # Verify repository was created
            workspace_info = await server.get_workspace(workspace_id)
            assert workspace_info is not None

            await server.shutdown()

    @pytest.mark.asyncio
    async def test_stage_and_commit(self, free_port):
        """Test staging files and creating a commit."""
        from mcp_git.config import Config
        from mcp_git.server.server import McpGitServer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
                metrics_port=free_port,
            )
            server = McpGitServer(config)
            await server.initialize()

            # Allocate workspace and init repository
            workspace = await server.allocate_workspace()
            workspace_id = workspace["workspace_id"]
            await server.init_repository(workspace_id=workspace_id)

            # Create a file
            workspace_info = await server.get_workspace(workspace_id)
            workspace_path = Path(workspace_info["path"])
            test_file = workspace_path / "test.txt"
            test_file.write_text("test content")

            # Stage file
            await server.stage_files(
                workspace_id=workspace_id,
                files=["test.txt"],
            )

            # Commit
            commit_oid = await server.create_commit(
                workspace_id=workspace_id,
                message="Test commit",
                author_name="Test User",
                author_email="test@example.com",
            )

            assert commit_oid is not None

            await server.shutdown()

    @pytest.mark.asyncio
    async def test_get_status(self, free_port):
        """Test getting repository status."""
        from mcp_git.config import Config
        from mcp_git.server.server import McpGitServer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
                metrics_port=free_port,
            )
            server = McpGitServer(config)
            await server.initialize()

            # Allocate workspace and init repository
            workspace = await server.allocate_workspace()
            workspace_id = workspace["workspace_id"]
            await server.init_repository(workspace_id=workspace_id)

            # Get status (should be clean)
            status = await server.get_status(workspace_id)
            assert status is None or len(status) == 0

            await server.shutdown()


class TestTaskManagement:
    """Test task management through server."""

    @pytest.mark.asyncio
    async def test_get_task(self, free_port):
        """Test getting a task."""
        from mcp_git.config import Config
        from mcp_git.server.server import McpGitServer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
                metrics_port=free_port,
            )
            server = McpGitServer(config)
            await server.initialize()

            # Create a task through facade
            task_id = await server.facade.task_manager.create_task(
                operation="test_operation",
                workspace_id=uuid.uuid4(),
                parameters={},
            )

            # Get task
            task = await server.get_task(task_id)
            assert task is not None
            assert task["task_id"] == str(task_id)

            await server.shutdown()

    @pytest.mark.asyncio
    async def test_list_tasks(self, free_port):
        """Test listing tasks."""
        from mcp_git.config import Config
        from mcp_git.server.server import McpGitServer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
                metrics_port=free_port,
            )
            server = McpGitServer(config)
            await server.initialize()

            # Create multiple tasks
            await server.facade.task_manager.create_task(
                operation="test_operation_1",
                workspace_id=uuid.uuid4(),
                parameters={},
            )
            await server.facade.task_manager.create_task(
                operation="test_operation_2",
                workspace_id=uuid.uuid4(),
                parameters={},
            )

            # List tasks
            tasks = await server.list_tasks(limit=10)
            assert len(tasks) >= 2

            await server.shutdown()

    @pytest.mark.asyncio
    async def test_cancel_task(self, free_port):
        """Test cancelling a task."""
        from mcp_git.config import Config
        from mcp_git.server.server import McpGitServer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
                metrics_port=free_port,
            )
            server = McpGitServer(config)
            await server.initialize()

            # Create a task
            task_id = await server.facade.task_manager.create_task(
                operation="test_operation",
                workspace_id=uuid.uuid4(),
                parameters={},
            )

            # Cancel task
            result = await server.cancel_task(task_id)
            assert result is True

            await server.shutdown()


class TestErrorHandling:
    """Test error handling in server."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_workspace(self, free_port):
        """Test getting a non-existent workspace."""
        from mcp_git.config import Config
        from mcp_git.server.server import McpGitServer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
                metrics_port=free_port,
            )
            server = McpGitServer(config)
            await server.initialize()

            # Try to get non-existent workspace
            result = await server.get_workspace(uuid.uuid4())
            assert result is None

            await server.shutdown()

    @pytest.mark.asyncio
    async def test_release_nonexistent_workspace(self, free_port):
        """Test releasing a non-existent workspace."""
        from mcp_git.config import Config
        from mcp_git.server.server import McpGitServer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
                metrics_port=free_port,
            )
            server = McpGitServer(config)
            await server.initialize()

            # Try to release non-existent workspace
            result = await server.release_workspace(uuid.uuid4())
            assert result is False

            await server.shutdown()
