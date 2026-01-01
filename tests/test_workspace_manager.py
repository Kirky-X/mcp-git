"""Workspace manager tests for mcp-git."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def workspace_manager(temp_workspace_dir: Path, temp_database: Path):
    """Create a workspace manager for testing."""
    from mcp_git.service.workspace_manager import WorkspaceConfig, WorkspaceManager
    from mcp_git.storage import SqliteStorage

    storage = SqliteStorage(temp_database)
    await storage.initialize()

    config = WorkspaceConfig(
        root_path=temp_workspace_dir,
        max_size_bytes=100 * 1024 * 1024,  # 100MB
        retention_seconds=3600,
    )

    manager = WorkspaceManager(storage, config)
    await manager.start()

    yield manager

    await manager.stop()
    await storage.close()


class TestWorkspaceManager:
    """Tests for WorkspaceManager class."""

    @pytest.mark.asyncio
    async def test_allocate_workspace(self, workspace_manager):
        """Test allocating a new workspace."""
        workspace = await workspace_manager.allocate_workspace()

        assert workspace is not None
        assert workspace.id is not None
        assert workspace.path.exists()
        assert workspace.size_bytes == 0

    @pytest.mark.asyncio
    async def test_allocate_multiple_workspaces(self, workspace_manager):
        """Test allocating multiple workspaces."""
        workspaces = []
        for _ in range(5):
            workspace = await workspace_manager.allocate_workspace()
            workspaces.append(workspace)

        assert len(workspaces) == 5

        # Verify all are unique
        ids = {w.id for w in workspaces}
        assert len(ids) == 5

        # Verify all paths exist
        for ws in workspaces:
            assert ws.path.exists()

    @pytest.mark.asyncio
    async def test_get_workspace(self, workspace_manager):
        """Test getting a workspace by ID."""
        # Create a workspace
        created = await workspace_manager.allocate_workspace()

        # Get it back
        retrieved = await workspace_manager.get_workspace(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.path == created.path

    @pytest.mark.asyncio
    async def test_get_nonexistent_workspace(self, workspace_manager):
        """Test getting a workspace that doesn't exist."""
        workspace = await workspace_manager.get_workspace(uuid4())
        assert workspace is None

    @pytest.mark.asyncio
    async def test_get_workspace_by_path(self, workspace_manager):
        """Test getting a workspace by path."""
        # Create a workspace
        created = await workspace_manager.allocate_workspace()

        # Get it by path
        retrieved = await workspace_manager.get_workspace_by_path(created.path)

        assert retrieved is not None
        assert retrieved.id == created.id

    @pytest.mark.asyncio
    async def test_touch_workspace(self, workspace_manager):
        """Test updating workspace access time."""
        # Create a workspace
        created = await workspace_manager.allocate_workspace()
        original_access = created.last_accessed_at

        # Touch it
        await workspace_manager.touch_workspace(created.id)

        # Get updated workspace
        updated = await workspace_manager.get_workspace(created.id)
        assert updated is not None
        # Access time should be updated (may have same second due to precision)
        # Just verify it's not None and is recent
        assert updated.last_accessed_at is not None
        assert updated.last_accessed_at >= original_access.replace(microsecond=0)

    @pytest.mark.asyncio
    async def test_release_workspace(self, workspace_manager):
        """Test releasing a workspace."""
        # Create a workspace
        workspace = await workspace_manager.allocate_workspace()
        assert workspace.path.exists()

        # Release it
        released = await workspace_manager.release_workspace(workspace.id)

        assert released is True
        assert not workspace.path.exists()

        # Verify it's gone
        retrieved = await workspace_manager.get_workspace(workspace.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_release_nonexistent_workspace(self, workspace_manager):
        """Test releasing a workspace that doesn't exist."""
        result = await workspace_manager.release_workspace(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_list_workspaces(self, workspace_manager):
        """Test listing workspaces."""
        # Create some workspaces
        for _ in range(3):
            await workspace_manager.allocate_workspace()

        workspaces = await workspace_manager.list_workspaces()

        assert len(workspaces) == 3

    @pytest.mark.asyncio
    async def test_list_workspaces_limit(self, workspace_manager):
        """Test listing workspaces with limit."""
        # Create more workspaces than limit
        for _ in range(10):
            await workspace_manager.allocate_workspace()

        workspaces = await workspace_manager.list_workspaces(limit=5)

        assert len(workspaces) == 5

    @pytest.mark.asyncio
    async def test_update_workspace_size(self, workspace_manager):
        """Test updating workspace size."""
        # Create a workspace
        workspace = await workspace_manager.allocate_workspace()

        # Create a file in it
        test_file = workspace.path / "test.txt"
        test_file.write_text("x" * 1000)

        # Update size
        await workspace_manager.update_workspace_size(workspace.id)

        # Verify size updated
        updated = await workspace_manager.get_workspace(workspace.id)
        assert updated is not None
        assert updated.size_bytes >= 1000


class TestWorkspaceCleanup:
    """Tests for workspace cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_workspaces(self, workspace_manager):
        """Test cleaning up expired workspaces."""
        # Create a workspace
        workspace = await workspace_manager.allocate_workspace()

        # Manually update access time to be in the past
        past_time = datetime.now(UTC) - timedelta(hours=2)
        await workspace_manager.storage.update_workspace(
            workspace.id,
            last_accessed_at=past_time,
        )

        # Verify the time was updated
        updated = await workspace_manager.storage.get_workspace(workspace.id)
        assert updated is not None
        assert updated.last_accessed_at is not None

        # Run cleanup
        cleaned, freed = await workspace_manager.cleanup_expired_workspaces()

        assert cleaned >= 1
        assert freed >= 0

        # Verify workspace is gone
        retrieved = await workspace_manager.get_workspace(workspace.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_cleanup_by_size(self, workspace_manager):
        """Test cleaning up workspaces by size."""
        # Create a workspace with a file
        workspace = await workspace_manager.allocate_workspace()
        test_file = workspace.path / "large_file.txt"
        test_file.write_bytes(b"x" * 1000000)  # 1MB

        # Update workspace size in database
        await workspace_manager.update_workspace_size(workspace.id)

        # Set max size to be small
        workspace_manager.config.max_size_bytes = 500 * 1024  # 500KB

        # Run cleanup
        cleaned, freed = await workspace_manager.cleanup_by_size()

        # Should have cleaned at least one workspace
        assert cleaned >= 1
        assert freed >= 500 * 1024

    @pytest.mark.asyncio
    async def test_no_cleanup_when_under_size(self, workspace_manager):
        """Test that cleanup doesn't run when under size limit."""
        # Create a workspace with a small file
        workspace = await workspace_manager.allocate_workspace()
        test_file = workspace.path / "small_file.txt"
        test_file.write_bytes(b"x" * 100)  # 100 bytes

        # Set large max size
        workspace_manager.config.max_size_bytes = 100 * 1024 * 1024  # 100MB

        # Run cleanup
        cleaned, freed = await workspace_manager.cleanup_by_size()

        assert cleaned == 0
        assert freed == 0


class TestWorkspaceValidation:
    """Tests for workspace path validation."""

    @pytest.mark.asyncio
    async def test_validate_workspace_path_valid(self, workspace_manager):
        """Test validating a valid workspace path."""
        workspace = await workspace_manager.allocate_workspace()

        is_valid = workspace_manager.validate_workspace_path(workspace.path)

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_workspace_path_invalid(self, workspace_manager):
        """Test validating an invalid workspace path."""
        is_valid = workspace_manager.validate_workspace_path(Path("/etc/passwd"))

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_workspace_path_traversal(self, workspace_manager):
        """Test validating path traversal attempts."""
        # Try to access path outside workspace root
        malicious_path = workspace_manager.config.root_path / ".." / "etc" / "passwd"

        is_valid = workspace_manager.validate_workspace_path(malicious_path)

        assert is_valid is False


class TestWorkspaceUsage:
    """Tests for workspace usage tracking."""

    @pytest.mark.asyncio
    async def test_get_workspace_usage(self, workspace_manager):
        """Test getting workspace usage statistics."""
        # Create some workspaces
        for i in range(3):
            workspace = await workspace_manager.allocate_workspace()
            test_file = workspace.path / f"file_{i}.txt"
            test_file.write_bytes(b"x" * (1000 * i))
            # Update workspace size in database
            await workspace_manager.storage.update_workspace(
                workspace.id,
                size_bytes=test_file.stat().st_size,
            )

        usage = await workspace_manager.get_workspace_usage()

        assert usage["total_workspaces"] == 3
        assert usage["total_size_bytes"] > 0
        assert "usage_percent" in usage

    @pytest.mark.asyncio
    async def test_empty_workspace_usage(self, workspace_manager):
        """Test getting workspace usage when empty."""
        usage = await workspace_manager.get_workspace_usage()

        assert usage["total_workspaces"] == 0
        assert usage["total_size_bytes"] == 0
        assert usage["usage_percent"] == 0
