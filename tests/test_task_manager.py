"""Task manager tests for mcp-git."""

from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def task_manager(temp_database: Path):
    """Create a task manager for testing."""
    from mcp_git.service.task_manager import TaskConfig, TaskManager
    from mcp_git.storage import SqliteStorage

    storage = SqliteStorage(temp_database)
    await storage.initialize()

    config = TaskConfig(
        max_concurrent_tasks=5,
        task_timeout_seconds=60,
        result_retention_seconds=3600,
    )

    manager = TaskManager(storage, config)
    await manager.start()

    yield manager

    await manager.stop()
    await storage.close()


class TestTaskManager:
    """Tests for TaskManager class."""

    @pytest.mark.asyncio
    async def test_create_task(self, task_manager):
        """Test creating a task."""
        from mcp_git.storage.models import GitOperation

        task = await task_manager.create_task(
            operation=GitOperation.CLONE,
            params={"url": "https://example.com/repo.git"},
        )

        assert task is not None
        assert task.id is not None
        assert task.operation == GitOperation.CLONE
        assert task.status.value == "queued"
        assert task.progress == 0

    @pytest.mark.asyncio
    async def test_get_task(self, task_manager):
        """Test getting a task by ID."""
        from mcp_git.storage.models import GitOperation

        # Create a task
        created = await task_manager.create_task(
            operation=GitOperation.COMMIT,
            params={"message": "Test commit"},
        )

        # Get it back
        retrieved = await task_manager.get_task(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.params["message"] == "Test commit"

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, task_manager):
        """Test getting a task that doesn't exist."""
        task = await task_manager.get_task(uuid4())
        assert task is None

    @pytest.mark.asyncio
    async def test_update_task_status(self, task_manager):
        """Test updating task status."""
        from mcp_git.storage.models import GitOperation, TaskStatus

        task = await task_manager.create_task(
            operation=GitOperation.PUSH,
            params={},
        )

        # Update status
        updated = await task_manager.update_task_status(
            task.id,
            TaskStatus.RUNNING,
            progress=50,
        )

        assert updated is True

        # Verify update
        retrieved = await task_manager.get_task(task.id)
        assert retrieved is not None
        assert retrieved.status == TaskStatus.RUNNING
        assert retrieved.progress == 50

    @pytest.mark.asyncio
    async def test_start_task(self, task_manager):
        """Test starting a task."""
        from mcp_git.storage.models import GitOperation, TaskStatus

        task = await task_manager.create_task(
            operation=GitOperation.PULL,
            params={},
        )

        started = await task_manager.start_task(task.id)

        assert started is True

        # Verify status
        retrieved = await task_manager.get_task(task.id)
        assert retrieved is not None
        assert retrieved.status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_complete_task(self, task_manager):
        """Test completing a task."""
        from mcp_git.storage.models import GitOperation, TaskStatus

        task = await task_manager.create_task(
            operation=GitOperation.BRANCH,
            params={},
        )

        await task_manager.start_task(task.id)
        completed = await task_manager.complete_task(
            task.id,
            result={"branch": "feature-1"},
        )

        assert completed is True

        # Verify status
        retrieved = await task_manager.get_task(task.id)
        assert retrieved is not None
        assert retrieved.status == TaskStatus.COMPLETED
        assert retrieved.progress == 100
        assert retrieved.result["branch"] == "feature-1"

    @pytest.mark.asyncio
    async def test_fail_task(self, task_manager):
        """Test failing a task."""
        from mcp_git.storage.models import GitOperation, TaskStatus

        task = await task_manager.create_task(
            operation=GitOperation.MERGE,
            params={},
        )

        await task_manager.start_task(task.id)
        failed = await task_manager.fail_task(
            task.id,
            error_message="Merge conflict",
        )

        assert failed is True

        # Verify status
        retrieved = await task_manager.get_task(task.id)
        assert retrieved is not None
        assert retrieved.status == TaskStatus.FAILED
        assert retrieved.error_message == "Merge conflict"

    @pytest.mark.asyncio
    async def test_cancel_task(self, task_manager):
        """Test cancelling a task."""
        from mcp_git.storage.models import GitOperation, TaskStatus

        task = await task_manager.create_task(
            operation=GitOperation.CLONE,
            params={},
        )

        cancelled = await task_manager.cancel_task(task.id)

        assert cancelled is True

        # Verify status
        retrieved = await task_manager.get_task(task.id)
        assert retrieved is not None
        assert retrieved.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_list_tasks(self, task_manager):
        """Test listing tasks."""
        from mcp_git.storage.models import GitOperation

        # Create multiple tasks
        for i in range(5):
            await task_manager.create_task(
                operation=GitOperation.CLONE,
                params={"index": i},
            )

        tasks = await task_manager.list_tasks()

        assert len(tasks) == 5

    @pytest.mark.asyncio
    async def test_list_tasks_by_status(self, task_manager):
        """Test listing tasks filtered by status."""
        from mcp_git.storage.models import GitOperation, TaskStatus

        # Create tasks with different statuses
        for i in range(4):
            task = await task_manager.create_task(
                operation=GitOperation.CLONE,
                params={},
            )
            if i % 2 == 0:
                await task_manager.start_task(task.id)

        queued = await task_manager.list_tasks(status=TaskStatus.QUEUED)
        running = await task_manager.list_tasks(status=TaskStatus.RUNNING)

        assert len(queued) == 2
        assert len(running) == 2


class TestTaskExecution:
    """Tests for task execution."""

    @pytest.mark.asyncio
    async def test_submit_task(self, task_manager):
        """Test submitting a task for execution."""
        from mcp_git.storage.models import GitOperation

        task = await task_manager.create_task(
            operation=GitOperation.CLONE,
            params={},
        )

        # Create a simple coroutine
        async def dummy_task():
            return {"result": "success"}

        submitted = await task_manager.submit_task(task.id, dummy_task())

        assert submitted is True

    @pytest.mark.asyncio
    async def test_get_active_tasks(self, task_manager):
        """Test getting active tasks."""
        from mcp_git.storage.models import GitOperation

        # Create a task
        task = await task_manager.create_task(
            operation=GitOperation.CLONE,
            params={},
        )

        # Start it (but don't complete)
        await task_manager.start_task(task.id)

        active = await task_manager.get_active_tasks()

        assert len(active) >= 1

    @pytest.mark.asyncio
    async def test_get_queued_tasks(self, task_manager):
        """Test getting queued tasks."""
        from mcp_git.storage.models import GitOperation

        # Create multiple tasks
        for _i in range(3):
            await task_manager.create_task(
                operation=GitOperation.CLONE,
                params={},
            )

        queued = await task_manager.get_queued_tasks(limit=10)

        assert len(queued) == 3


class TestTaskCallbacks:
    """Tests for task callbacks."""

    @pytest.mark.asyncio
    async def test_task_callbacks(self, task_manager, temp_database):
        """Test task lifecycle callbacks."""
        from mcp_git.storage.models import GitOperation

        start_called = []
        complete_called = []
        error_called = []

        def on_start(task):
            start_called.append(task.id)

        def on_complete(task_id, result):
            complete_called.append(task_id)

        def on_error(task_id, error):
            error_called.append(task_id)

        task_manager.set_task_callbacks(
            on_start=on_start,
            on_complete=on_complete,
            on_error=on_error,
        )

        # Create and complete a task
        task = await task_manager.create_task(
            operation=GitOperation.CLONE,
            params={},
        )

        await task_manager.start_task(task.id)
        await task_manager.complete_task(task.id, {"result": "ok"})

        assert task.id in start_called
        assert task.id in complete_called
        assert len(error_called) == 0


class TestTaskManagerStats:
    """Tests for task manager statistics."""

    @pytest.mark.asyncio
    async def test_get_stats(self, task_manager):
        """Test getting task manager stats."""
        stats = task_manager.get_stats()

        assert "active_tasks" in stats
        assert "max_concurrent" in stats
        assert "timeout_seconds" in stats
        assert "result_retention_seconds" in stats

    @pytest.mark.asyncio
    async def test_stats_with_active_tasks(self, task_manager):
        """Test stats with active tasks."""
        from mcp_git.storage.models import GitOperation

        # Create and start some tasks
        for _i in range(3):
            task = await task_manager.create_task(
                operation=GitOperation.CLONE,
                params={},
            )
            await task_manager.start_task(task.id)

        stats = task_manager.get_stats()

        assert stats["active_tasks"] == 3


class TestTaskCleanup:
    """Tests for task cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_tasks(self, task_manager, temp_database):
        """Test cleaning up expired tasks."""
        from mcp_git.storage.models import GitOperation

        # Create some completed tasks
        for _i in range(3):
            task = await task_manager.create_task(
                operation=GitOperation.CLONE,
                params={},
            )
            await task_manager.start_task(task.id)
            await task_manager.complete_task(task.id)

        # Cleanup with 0 second retention
        cleaned = await task_manager.cleanup_expired_tasks(0)

        assert isinstance(cleaned, int)
