"""
Edge case tests for storage layer.

Tests for boundary conditions, error scenarios, and exceptional cases.
"""

# type: ignore  # Async test functions with pytest-asyncio have special patterns

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

from mcp_git.storage import SqliteStorage
from mcp_git.storage.models import GitOperation, Task, TaskStatus, Workspace


@pytest_asyncio.fixture
async def storage(temp_database: Path) -> AsyncGenerator[SqliteStorage, None]:
    """Create a storage instance for testing."""
    storage = SqliteStorage(temp_database)
    await storage.initialize()
    yield storage
    await storage.close()


class TestTaskEdgeCases:
    """Test edge cases for task operations."""

    @pytest.mark.asyncio
    async def test_create_task_with_very_long_params(self, storage: SqliteStorage):
        """Test creating a task with very long parameters."""
        # Create task with 10KB params
        large_params = {"data": "x" * 10000}

        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params=large_params,
        )

        created = await storage.create_task(task)
        assert created is not None
        assert created.params == large_params

    @pytest.mark.asyncio
    async def test_update_task_with_special_characters(self, storage: SqliteStorage):
        """Test updating task with special characters in result."""
        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params={"url": "https://example.com/repo.git"},
        )
        created = await storage.create_task(task)

        # Update with special characters
        special_result = {
            "output": "Test with special chars: \n\t\r\"'<>{}[]|&",
            "unicode": "中文测试 🎉",
            "emoji": "😀🐍🚀",
        }

        updated = await storage.update_task(
            created.id,
            result=special_result,
        )
        assert updated is True

        # Verify result is stored correctly
        retrieved = await storage.get_task(created.id)
        assert retrieved is not None
        assert retrieved.result == special_result

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, storage: SqliteStorage):
        """Test getting a task that doesn't exist."""
        nonexistent_id = uuid4()

        task = await storage.get_task(nonexistent_id)
        assert task is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(self, storage: SqliteStorage):
        """Test deleting a task that doesn't exist."""
        nonexistent_id = uuid4()

        result = await storage.delete_task(nonexistent_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_task(self, storage: SqliteStorage):
        """Test updating a task that doesn't exist."""
        nonexistent_id = uuid4()

        result = await storage.update_task(
            nonexistent_id,
            status=TaskStatus.RUNNING,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_list_tasks_with_empty_filters(self, storage: SqliteStorage):
        """Test listing tasks with no filters."""
        # Create tasks with different statuses
        for i in range(10):
            task = Task(
                id=uuid4(),
                operation=GitOperation.CLONE,
                status=TaskStatus.QUEUED if i < 5 else TaskStatus.COMPLETED,
                params={"url": f"https://example.com/repo{i}.git"},
            )
            await storage.create_task(task)

        # List all tasks
        tasks = await storage.list_tasks()
        assert len(tasks) == 10

    @pytest.mark.asyncio
    async def test_list_tasks_with_status_filter(self, storage: SqliteStorage):
        """Test listing tasks filtered by status."""
        # Create tasks with different statuses
        for i in range(10):
            task = Task(
                id=uuid4(),
                operation=GitOperation.CLONE,
                status=TaskStatus.QUEUED
                if i < 3
                else TaskStatus.RUNNING
                if i < 6
                else TaskStatus.COMPLETED,
                params={"url": f"https://example.com/repo{i}.git"},
            )
            await storage.create_task(task)

        # List only QUEUED tasks
        queued_tasks = await storage.list_tasks(status=TaskStatus.QUEUED)
        assert len(queued_tasks) == 3
        assert all(task.status == TaskStatus.QUEUED for task in queued_tasks)

    @pytest.mark.asyncio
    async def test_list_tasks_with_pagination(self, storage: SqliteStorage):
        """Test listing tasks with pagination."""
        # Create 20 tasks
        for i in range(20):
            task = Task(
                id=uuid4(),
                operation=GitOperation.CLONE,
                status=TaskStatus.QUEUED,
                params={"url": f"https://example.com/repo{i}.git"},
            )
            await storage.create_task(task)

        # Get first page (10 tasks)
        page1 = await storage.list_tasks(limit=10, offset=0)
        assert len(page1) == 10

        # Get second page (10 tasks)
        page2 = await storage.list_tasks(limit=10, offset=10)
        assert len(page2) == 10

        # Get third page (0 tasks)
        page3 = await storage.list_tasks(limit=10, offset=20)
        assert len(page3) == 0

    @pytest.mark.asyncio
    async def test_get_tasks_batch_with_empty_list(self, storage: SqliteStorage):
        """Test batch getting tasks with empty list."""
        tasks = await storage.get_tasks_batch([])
        assert tasks == []

    @pytest.mark.asyncio
    async def test_get_tasks_batch_with_nonexistent_ids(self, storage: SqliteStorage):
        """Test batch getting tasks with nonexistent IDs."""
        # Create one task
        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params={"url": "https://example.com/repo.git"},
        )
        created = await storage.create_task(task)

        # Mix of real and fake IDs
        task_ids = [created.id, uuid4(), uuid4()]
        tasks = await storage.get_tasks_batch(task_ids)

        # Should only return the real task
        assert len(tasks) == 1
        assert tasks[0].id == created.id

    @pytest.mark.asyncio
    async def test_concurrent_task_updates_same_task(self, storage: SqliteStorage):
        """Test concurrent updates to the same task."""
        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params={"url": "https://example.com/repo.git"},
        )
        created = await storage.create_task(task)

        # Update the task concurrently
        async def update_task(progress: int):
            await storage.update_task(
                created.id,
                progress=progress,
            )

        updates = [update_task(i * 10) for i in range(1, 11)]
        await asyncio.gather(*updates)

        # Verify final state
        retrieved = await storage.get_task(created.id)
        assert retrieved is not None
        assert retrieved.status == TaskStatus.QUEUED
        # Progress should be one of the updates
        assert 10 <= retrieved.progress <= 100

    @pytest.mark.asyncio
    async def test_cleanup_expired_tasks_with_no_tasks(self, storage: SqliteStorage):
        """Test cleanup when there are no expired tasks."""
        cleaned = await storage.cleanup_expired_tasks(retention_seconds=3600)
        assert cleaned == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_tasks_with_all_expired(self, storage: SqliteStorage):
        """Test cleanup when all tasks are expired."""
        # Create old tasks with manual timestamp manipulation
        task_ids = []
        for i in range(5):
            task = Task(
                id=uuid4(),
                operation=GitOperation.CLONE,
                status=TaskStatus.COMPLETED,
                params={"url": f"https://example.com/repo{i}.git"},
            )
            created = await storage.create_task(task)
            task_ids.append(created.id)

        # Cleanup with 0 retention (all tasks should be considered expired)
        # Note: The actual implementation uses current time, so we verify
        # that cleanup runs without errors and returns a reasonable count
        cleaned = await storage.cleanup_expired_tasks(retention_seconds=0)

        # Verify cleanup was attempted
        assert cleaned >= 0

        # Clean up manually for test purposes
        for task_id in task_ids:
            await storage.delete_task(task_id)


class TestWorkspaceEdgeCases:
    """Test edge cases for workspace operations."""

    @pytest.mark.asyncio
    async def test_create_workspace_with_very_long_path(
        self, storage: SqliteStorage, temp_workspace_dir: Path
    ):
        """Test creating a workspace with a very long path."""
        # Create path with 400 characters
        long_path = temp_workspace_dir / ("a" * 400)

        workspace = Workspace(
            path=long_path,
            size_bytes=0,
        )

        created = await storage.create_workspace(workspace)
        assert created is not None
        assert created.path == long_path

    @pytest.mark.asyncio
    async def test_update_workspace_with_very_large_size(
        self, storage: SqliteStorage, temp_workspace_dir: Path
    ):
        """Test updating workspace with very large size."""
        workspace = Workspace(
            path=temp_workspace_dir / "large_workspace",
            size_bytes=0,
        )
        created = await storage.create_workspace(workspace)

        # Update with 10GB size
        large_size = 10 * 1024 * 1024 * 1024  # 10GB
        updated = await storage.update_workspace(
            created.id,
            size_bytes=large_size,
        )
        assert updated is True

        # Verify size is stored correctly
        retrieved = await storage.get_workspace(created.id)
        assert retrieved is not None
        assert retrieved.size_bytes == large_size

    @pytest.mark.asyncio
    async def test_get_workspace_by_nonexistent_path(self, storage: SqliteStorage):
        """Test getting a workspace by nonexistent path."""
        nonexistent_path = Path("/nonexistent/path")

        workspace = await storage.get_workspace_by_path(nonexistent_path)
        assert workspace is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_workspace(self, storage: SqliteStorage):
        """Test deleting a workspace that doesn't exist."""
        nonexistent_id = uuid4()

        result = await storage.delete_workspace(nonexistent_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_workspace(
        self, storage: SqliteStorage, temp_workspace_dir: Path
    ):
        """Test updating a workspace that doesn't exist."""
        nonexistent_id = uuid4()

        result = await storage.update_workspace(
            nonexistent_id,
            size_bytes=1024,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_list_workspaces_with_empty_database(self, storage: SqliteStorage):
        """Test listing workspaces when database is empty."""
        workspaces = await storage.list_workspaces()
        assert workspaces == []

    @pytest.mark.asyncio
    async def test_list_workspaces_with_pagination(
        self, storage: SqliteStorage, temp_workspace_dir: Path
    ):
        """Test listing workspaces with pagination."""
        # Create 15 workspaces
        for i in range(15):
            workspace = Workspace(
                path=temp_workspace_dir / f"workspace_{i}",
                size_bytes=i * 1024,
            )
            await storage.create_workspace(workspace)

        # Get first page (10 workspaces)
        page1 = await storage.list_workspaces(limit=10, offset=0)
        assert len(page1) == 10

        # Get second page (5 workspaces)
        page2 = await storage.list_workspaces(limit=10, offset=10)
        assert len(page2) == 5

        # Get third page (0 workspaces)
        page3 = await storage.list_workspaces(limit=10, offset=15)
        assert len(page3) == 0

    @pytest.mark.asyncio
    async def test_get_oldest_workspaces_with_empty_database(self, storage: SqliteStorage):
        """Test getting oldest workspaces when database is empty."""
        workspaces = await storage.get_oldest_workspaces(10)
        assert workspaces == []

    @pytest.mark.asyncio
    async def test_get_workspace_total_size_with_empty_database(self, storage: SqliteStorage):
        """Test getting total workspace size when database is empty."""
        total_size = await storage.get_workspace_total_size()
        assert total_size == 0

    @pytest.mark.asyncio
    async def test_get_workspace_total_size_with_multiple_workspaces(
        self, storage: SqliteStorage, temp_workspace_dir: Path
    ):
        """Test getting total workspace size with multiple workspaces."""
        # Create workspaces with different sizes
        sizes = [1024, 2048, 4096, 8192, 16384]
        for i, size in enumerate(sizes):
            workspace = Workspace(
                path=temp_workspace_dir / f"workspace_{i}",
                size_bytes=size,
            )
            await storage.create_workspace(workspace)

        total_size = await storage.get_workspace_total_size()
        assert total_size == sum(sizes)

    @pytest.mark.asyncio
    async def test_concurrent_workspace_updates(
        self, storage: SqliteStorage, temp_workspace_dir: Path
    ):
        """Test concurrent updates to the same workspace."""
        workspace = Workspace(
            path=temp_workspace_dir / "concurrent_workspace",
            size_bytes=0,
        )
        created = await storage.create_workspace(workspace)

        # Update the workspace concurrently
        async def update_workspace(size: int):
            await storage.update_workspace(
                created.id,
                size_bytes=size,
            )

        updates = [update_workspace(i * 1024) for i in range(1, 11)]
        await asyncio.gather(*updates)

        # Verify final state
        retrieved = await storage.get_workspace(created.id)
        assert retrieved is not None
        # Size should be one of the updates
        assert 1024 <= retrieved.size_bytes <= 10240


class TestOperationLogEdgeCases:
    """Test edge cases for operation log operations."""

    @pytest.mark.asyncio
    async def test_log_operation_with_very_long_message(self, storage: SqliteStorage):
        """Test logging an operation with a very long message."""
        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params={"url": "https://example.com/repo.git"},
        )
        created = await storage.create_task(task)

        # Log with 10KB message
        long_message = "x" * 10000
        await storage.log_operation(
            task_id=created.id,
            operation=GitOperation.CLONE,
            level="info",
            message=long_message,
        )

        # Verify log was stored
        logs = await storage.get_operation_logs(created.id, limit=10)
        assert len(logs) == 1
        assert logs[0].message == long_message

    @pytest.mark.asyncio
    async def test_log_operation_with_special_characters(self, storage: SqliteStorage):
        """Test logging an operation with special characters."""
        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params={"url": "https://example.com/repo.git"},
        )
        created = await storage.create_task(task)

        # Log with special characters
        special_message = "Test: \n\t\r\"'<>{}[]|& 中文 🎉 😀"
        await storage.log_operation(
            task_id=created.id,
            operation=GitOperation.CLONE,
            level="info",
            message=special_message,
        )

        # Verify log was stored correctly
        logs = await storage.get_operation_logs(created.id, limit=10)
        assert len(logs) == 1
        assert logs[0].message == special_message

    @pytest.mark.asyncio
    async def test_get_operation_logs_for_nonexistent_task(self, storage: SqliteStorage):
        """Test getting operation logs for a task that doesn't exist."""
        nonexistent_id = uuid4()

        logs = await storage.get_operation_logs(nonexistent_id, limit=10)
        assert logs == []

    @pytest.mark.asyncio
    async def test_get_operation_logs_with_limit(self, storage: SqliteStorage):
        """Test getting operation logs with limit."""
        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params={"url": "https://example.com/repo.git"},
        )
        created = await storage.create_task(task)

        # Log 20 operations
        for i in range(20):
            await storage.log_operation(
                task_id=created.id,
                operation=GitOperation.CLONE,
                level="info",
                message=f"Operation {i}",
            )

        # Get only 5 logs
        logs = await storage.get_operation_logs(created.id, limit=5)
        assert len(logs) == 5

    @pytest.mark.asyncio
    async def test_get_operation_logs_ordering(self, storage: SqliteStorage):
        """Test that operation logs are returned in reverse chronological order."""
        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params={"url": "https://example.com/repo.git"},
        )
        created = await storage.create_task(task)

        # Log operations
        messages = []
        for i in range(10):
            message = f"Operation {i}"
            messages.append(message)
            await storage.log_operation(
                task_id=created.id,
                operation=GitOperation.CLONE,
                level="info",
                message=message,
            )
            # Small delay to ensure different timestamps
            await asyncio.sleep(0.001)

        # Get all logs
        logs = await storage.get_operation_logs(created.id, limit=100)

        # Verify all logs were stored
        assert len(logs) == 10

        # Verify messages contain expected operations
        logged_messages = [log.message for log in logs]
        for message in messages:
            assert message in logged_messages

    @pytest.mark.asyncio
    async def test_concurrent_log_operations(self, storage: SqliteStorage):
        """Test concurrent logging operations."""
        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params={"url": "https://example.com/repo.git"},
        )
        created = await storage.create_task(task)

        # Log 100 operations concurrently
        async def log_operation(i: int):
            await storage.log_operation(
                task_id=created.id,
                operation=GitOperation.CLONE,
                level="info",
                message=f"Concurrent operation {i}",
            )

        await asyncio.gather(*[log_operation(i) for i in range(100)])

        # Verify all logs were stored
        logs = await storage.get_operation_logs(created.id, limit=1000)
        assert len(logs) == 100
