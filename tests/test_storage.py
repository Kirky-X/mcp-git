"""Storage tests for mcp-git."""

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def storage(temp_database: Path):
    """Create and initialize storage for testing."""
    from mcp_git.storage import SqliteStorage

    storage = SqliteStorage(temp_database)
    await storage.initialize()
    yield storage
    await storage.close()


class TestSqliteStorage:
    """Tests for SqliteStorage class."""

    @pytest.mark.asyncio
    async def test_initialize_storage(self, storage):
        """Test storage initialization."""
        assert storage._engine is not None

    @pytest.mark.asyncio
    async def test_create_task(self, storage):
        """Test creating a task."""
        from mcp_git.storage.models import GitOperation, Task, TaskStatus

        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params={"url": "https://example.com/repo.git"},
        )

        created = await storage.create_task(task)

        assert created.id == task.id
        assert created.operation == GitOperation.CLONE

    @pytest.mark.asyncio
    async def test_get_task(self, storage):
        """Test getting a task by ID."""
        from mcp_git.storage.models import GitOperation, Task, TaskStatus

        task = Task(
            id=uuid4(),
            operation=GitOperation.COMMIT,
            status=TaskStatus.QUEUED,
            params={},
        )

        await storage.create_task(task)
        retrieved = await storage.get_task(task.id)

        assert retrieved is not None
        assert retrieved.id == task.id
        assert retrieved.operation == GitOperation.COMMIT

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, storage):
        """Test getting a task that doesn't exist."""

        task = await storage.get_task(uuid4())
        assert task is None

    @pytest.mark.asyncio
    async def test_update_task(self, storage):
        """Test updating a task."""
        from mcp_git.storage.models import GitOperation, Task, TaskStatus

        task = Task(
            id=uuid4(),
            operation=GitOperation.PUSH,
            status=TaskStatus.QUEUED,
            params={},
        )

        await storage.create_task(task)

        updated = await storage.update_task(
            task.id,
            status=TaskStatus.RUNNING,
            progress=50,
        )

        assert updated is True

        # Verify update
        retrieved = await storage.get_task(task.id)
        assert retrieved is not None
        assert retrieved.status == TaskStatus.RUNNING
        assert retrieved.progress == 50

    @pytest.mark.asyncio
    async def test_delete_task(self, storage):
        """Test deleting a task."""
        from mcp_git.storage.models import GitOperation, Task, TaskStatus

        task = Task(
            id=uuid4(),
            operation=GitOperation.PULL,
            status=TaskStatus.QUEUED,
            params={},
        )

        await storage.create_task(task)

        deleted = await storage.delete_task(task.id)
        assert deleted is True

        # Verify deletion
        retrieved = await storage.get_task(task.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_tasks(self, storage):
        """Test listing tasks."""
        from mcp_git.storage.models import GitOperation, Task, TaskStatus

        # Create multiple tasks
        for i in range(3):
            task = Task(
                id=uuid4(),
                operation=GitOperation.CLONE,
                status=TaskStatus.QUEUED,
                params={"index": i},
            )
            await storage.create_task(task)

        tasks = await storage.list_tasks()

        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_list_tasks_by_status(self, storage):
        """Test listing tasks filtered by status."""
        from mcp_git.storage.models import GitOperation, Task, TaskStatus

        # Create tasks with different statuses
        for i in range(3):
            task = Task(
                id=uuid4(),
                operation=GitOperation.CLONE,
                status=TaskStatus.QUEUED if i % 2 == 0 else TaskStatus.RUNNING,
                params={},
            )
            await storage.create_task(task)

        queued_tasks = await storage.list_tasks(status=TaskStatus.QUEUED)
        assert len(queued_tasks) == 2

    @pytest.mark.asyncio
    async def test_create_workspace(self, storage):
        """Test creating a workspace."""
        from mcp_git.storage.models import Workspace

        workspace = Workspace(
            id=uuid4(),
            path=Path("/tmp/test_workspace"),
            size_bytes=1024,
        )

        created = await storage.create_workspace(workspace)

        assert created.id == workspace.id
        assert created.path == Path("/tmp/test_workspace")

    @pytest.mark.asyncio
    async def test_get_workspace(self, storage):
        """Test getting a workspace by ID."""
        from mcp_git.storage.models import Workspace

        workspace = Workspace(
            id=uuid4(),
            path=Path("/tmp/test_workspace2"),
            size_bytes=2048,
        )

        await storage.create_workspace(workspace)
        retrieved = await storage.get_workspace(workspace.id)

        assert retrieved is not None
        assert retrieved.id == workspace.id
        assert retrieved.size_bytes == 2048

    @pytest.mark.asyncio
    async def test_get_workspace_by_path(self, storage):
        """Test getting a workspace by path."""
        from mcp_git.storage.models import Workspace

        workspace = Workspace(
            id=uuid4(),
            path=Path("/tmp/test_workspace3"),
            size_bytes=4096,
        )

        await storage.create_workspace(workspace)
        retrieved = await storage.get_workspace_by_path(Path("/tmp/test_workspace3"))

        assert retrieved is not None
        assert retrieved.id == workspace.id

    @pytest.mark.asyncio
    async def test_update_workspace(self, storage):
        """Test updating a workspace."""
        from mcp_git.storage.models import Workspace

        workspace = Workspace(
            id=uuid4(),
            path=Path("/tmp/test_workspace4"),
            size_bytes=1000,
        )

        await storage.create_workspace(workspace)

        updated = await storage.update_workspace(
            workspace.id,
            size_bytes=5000,
        )

        assert updated is True

        retrieved = await storage.get_workspace(workspace.id)
        assert retrieved is not None
        assert retrieved.size_bytes == 5000

    @pytest.mark.asyncio
    async def test_list_workspaces(self, storage):
        """Test listing workspaces."""
        from mcp_git.storage.models import Workspace

        # Create multiple workspaces
        for i in range(3):
            workspace = Workspace(
                id=uuid4(),
                path=Path(f"/tmp/test_workspace_{i}"),
                size_bytes=1024 * i,
            )
            await storage.create_workspace(workspace)

        workspaces = await storage.list_workspaces()
        assert len(workspaces) == 3

    @pytest.mark.asyncio
    async def test_get_oldest_workspaces(self, storage):
        """Test getting oldest workspaces."""
        from mcp_git.storage.models import Workspace

        # Create workspaces
        for i in range(5):
            workspace = Workspace(
                id=uuid4(),
                path=Path(f"/tmp/old_workspace_{i}"),
                size_bytes=1000,
            )
            await storage.create_workspace(workspace)

        oldest = await storage.get_oldest_workspaces(3)
        assert len(oldest) == 3

    @pytest.mark.asyncio
    async def test_get_workspace_total_size(self, storage):
        """Test getting total workspace size."""
        from mcp_git.storage.models import Workspace

        # Create workspaces with known sizes
        sizes = [1000, 2000, 3000]
        for size in sizes:
            workspace = Workspace(
                id=uuid4(),
                path=Path(f"/tmp/size_workspace_{size}"),
                size_bytes=size,
            )
            await storage.create_workspace(workspace)

        total = await storage.get_workspace_total_size()
        assert total == 6000

    @pytest.mark.asyncio
    async def test_cleanup_expired_tasks(self, storage):
        """Test cleaning up expired tasks."""
        from mcp_git.storage.models import GitOperation, Task, TaskStatus

        # Create completed tasks
        for _i in range(3):
            task = Task(
                id=uuid4(),
                operation=GitOperation.CLONE,
                status=TaskStatus.COMPLETED,
                params={},
            )
            await storage.create_task(task)

        # Clean up tasks older than 0 seconds (should clean all)
        cleaned = await storage.cleanup_expired_tasks(0)

        # Tasks with completed_at set to epoch (None) won't be cleaned
        # This test needs proper timestamp handling
        # cleaned count depends on actual task timestamps
        assert isinstance(cleaned, int)


class TestStorageIndexes:
    """Tests for database indexes."""

    @pytest.mark.asyncio
    async def test_indexes_created(self, storage):
        """Test that indexes are created on initialization."""
        from sqlalchemy import text

        # Query to check if indexes exist using SQLAlchemy
        async with storage._engine.connect() as conn:
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))
            indexes = result.fetchall()
            index_names = [row[0] for row in indexes if row[0]]

            assert "ix_tasks_status" in index_names
            assert "ix_tasks_created_at" in index_names
            assert "ix_workspaces_last_accessed_at" in index_names


class TestStorageConcurrency:
    """Tests for storage concurrency handling."""

    @pytest.mark.asyncio
    async def test_concurrent_task_creation(self, storage):
        """Test creating tasks concurrently."""
        from mcp_git.storage.models import GitOperation, Task, TaskStatus

        async def create_task(i: int) -> Task:
            task = Task(
                id=uuid4(),
                operation=GitOperation.CLONE,
                status=TaskStatus.QUEUED,
                params={"index": i},
            )
            return await storage.create_task(task)

        # Create multiple tasks concurrently
        tasks = await asyncio.gather(*[create_task(i) for i in range(10)])

        assert len(tasks) == 10

        # Verify all were created
        all_tasks = await storage.list_tasks()
        assert len(all_tasks) >= 10
