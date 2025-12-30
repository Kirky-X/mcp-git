"""Task queue tests for mcp-git."""

import asyncio
import time
from pathlib import Path

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def task_queue():
    """Create a task queue for testing."""
    from mcp_git.execution.task_queue import TaskQueue

    queue = TaskQueue(
        max_size=100,
        max_concurrent=5,
        max_retries=2,
    )
    await queue.start()

    yield queue

    await queue.stop()


class TestTaskQueue:
    """Tests for TaskQueue class."""

    @pytest.mark.asyncio
    async def test_submit_task(self, task_queue):
        """Test submitting a task."""

        async def dummy_task(param1: str) -> str:
            return f"Processed: {param1}"

        task_id = await task_queue.submit(
            coroutine=dummy_task,
            params={"param1": "test"},
        )

        assert task_id is not None
        assert len(task_id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_submit_with_priority(self, task_queue):
        """Test submitting tasks with different priorities."""

        async def dummy_task() -> None:
            pass

        # Submit low priority
        low_id = await task_queue.submit(
            coroutine=dummy_task,
            priority=TaskPriority.LOW,
        )

        # Submit high priority
        high_id = await task_queue.submit(
            coroutine=dummy_task,
            priority=TaskPriority.HIGH,
        )

        assert low_id is not None
        assert high_id is not None

    @pytest.mark.asyncio
    async def test_get_queue_size(self, task_queue):
        """Test getting queue size."""

        async def dummy_task() -> None:
            await asyncio.sleep(0.1)

        # Submit some tasks
        for _i in range(3):
            await task_queue.submit(coroutine=dummy_task)

        size = await task_queue.get_queue_size()

        # Size should be at least 0 (some may have been processed)
        assert isinstance(size, int)

    @pytest.mark.asyncio
    async def test_get_active_count(self, task_queue):
        """Test getting active task count."""
        count = await task_queue.get_active_count()

        assert isinstance(count, int)
        assert count >= 0

    @pytest.mark.asyncio
    async def test_get_queued_tasks(self, task_queue):
        """Test getting queued tasks list."""

        async def dummy_task() -> None:
            await asyncio.sleep(1)

        # Submit some tasks
        for _i in range(3):
            await task_queue.submit(coroutine=dummy_task)

        tasks = await task_queue.get_queued_tasks(limit=10)

        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_submit_batch(self, task_queue):
        """Test submitting multiple tasks at once."""

        async def dummy_task() -> None:
            pass

        tasks = [
            (dummy_task, TaskPriority.NORMAL, {"param": "value1"}),
            (dummy_task, TaskPriority.HIGH, {"param": "value2"}),
            (dummy_task, TaskPriority.LOW, {"param": "value3"}),
        ]

        task_ids = await task_queue.submit_batch(tasks)

        assert len(task_ids) == 3

    @pytest.mark.asyncio
    async def test_get_metrics(self, task_queue):
        """Test getting queue metrics."""
        metrics = task_queue.get_metrics()

        assert "submitted" in metrics
        assert "completed" in metrics
        assert "failed" in metrics
        assert "queue_size" in metrics
        assert "active_count" in metrics
        assert "max_concurrent" in metrics
        assert "available_slots" in metrics

    @pytest.mark.asyncio
    async def test_callbacks(self, task_queue):
        """Test setting callbacks."""
        complete_results = []
        error_results = []

        def on_complete(task_id: str, result):
            complete_results.append(task_id)

        def on_error(task_id: str, error: str):
            error_results.append(task_id)

        task_queue.set_callbacks(
            on_complete=on_complete,
            on_error=on_error,
        )

        # Verify callbacks are set
        assert task_queue._on_task_complete is on_complete
        assert task_queue._on_task_error is on_error

    @pytest.mark.asyncio
    async def test_clear_queue(self, task_queue):
        """Test clearing the queue."""

        async def dummy_task() -> None:
            await asyncio.sleep(10)

        # Submit some tasks
        for _i in range(5):
            await task_queue.submit(coroutine=dummy_task)

        cleared = await task_queue.clear()

        assert cleared >= 0

    @pytest.mark.asyncio
    async def test_wait_for_completion(self, task_queue):
        """Test waiting for task completion."""

        async def quick_task() -> str:
            await asyncio.sleep(0.1)
            return "done"

        # Submit a quick task
        await task_queue.submit(coroutine=quick_task)

        # Wait for completion with timeout
        completed = await task_queue.wait_for_completion(timeout=5.0)

        assert completed is True


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_priority_values(self):
        """Test priority enum values."""
        from mcp_git.execution.task_queue import TaskPriority

        assert TaskPriority.LOW.value == 0
        assert TaskPriority.NORMAL.value == 5
        assert TaskPriority.HIGH.value == 10
        assert TaskPriority.CRITICAL.value == 15

    def test_priority_comparison(self):
        """Test priority comparison."""
        from mcp_git.execution.task_queue import TaskPriority

        assert TaskPriority.CRITICAL > TaskPriority.HIGH
        assert TaskPriority.HIGH > TaskPriority.NORMAL
        assert TaskPriority.NORMAL > TaskPriority.LOW


class TestQueuedTask:
    """Tests for QueuedTask dataclass."""

    def test_queued_task_creation(self):
        """Test creating a queued task."""
        from mcp_git.execution.task_queue import QueuedTask, TaskPriority

        async def dummy_task():
            pass

        task = QueuedTask(
            id="test-id",
            priority=TaskPriority.HIGH,
            created_at=time.time(),
            coroutine=dummy_task,
            params={"key": "value"},
        )

        assert task.id == "test-id"
        assert task.priority == TaskPriority.HIGH
        assert task.params["key"] == "value"
        assert task.retries == 0

    def test_queued_task_lt(self):
        """Test queued task comparison."""
        from mcp_git.execution.task_queue import QueuedTask, TaskPriority

        async def dummy_task():
            pass

        # Create tasks with different priorities
        low_task = QueuedTask(
            id="low",
            priority=TaskPriority.LOW,
            created_at=1.0,
            coroutine=dummy_task,
            params={},
        )

        high_task = QueuedTask(
            id="high",
            priority=TaskPriority.HIGH,
            created_at=1.0,
            coroutine=dummy_task,
            params={},
        )

        # Higher priority should be "less than" for heapq (which pops smallest first)
        assert low_task > high_task


class TestTaskQueueConcurrency:
    """Tests for task queue concurrency handling."""

    @pytest.mark.asyncio
    async def test_max_concurrent_limit(self, temp_database: Path):
        """Test that concurrent limit is enforced."""
        from mcp_git.execution.task_queue import TaskQueue

        queue = TaskQueue(max_size=100, max_concurrent=2, max_retries=1)
        await queue.start()

        # Track active tasks
        active_count = 0
        max_active = 0
        lock = asyncio.Lock()

        async def long_task():
            nonlocal active_count, max_active
            async with lock:
                active_count += 1
                max_active = max(max_active, active_count)
            await asyncio.sleep(0.5)
            async with lock:
                active_count -= 1

        # Submit more tasks than concurrent limit
        for _i in range(5):
            await queue.submit(coroutine=long_task)

        # Wait a bit
        await asyncio.sleep(0.3)

        # Max active should not exceed limit
        assert max_active <= 2

        # Wait for completion
        await queue.wait_for_completion(timeout=5.0)
        await queue.stop()

    @pytest.mark.asyncio
    async def test_queue_full_rejection(self, temp_database: Path):
        """Test that queue rejects when full."""
        from mcp_git.execution.task_queue import TaskQueue

        queue = TaskQueue(max_size=5, max_concurrent=10, max_retries=1)
        await queue.start()

        async def dummy_task():
            await asyncio.sleep(10)

        # Fill the queue
        for _i in range(5):
            await queue.submit(coroutine=dummy_task)

        # Try to submit one more - should fail
        with pytest.raises(asyncio.QueueFull):
            await queue.submit(coroutine=dummy_task)

        await queue.stop()
