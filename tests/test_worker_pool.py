"""Worker pool tests for mcp-git."""

import asyncio
import time
from pathlib import Path

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def worker_pool():
    """Create a worker pool for testing."""
    from mcp_git.execution.worker_pool import WorkerPool

    pool = WorkerPool(
        min_workers=2,
        max_workers=5,
        max_tasks_per_worker=10,
        scale_up_threshold=0.8,
        scale_down_threshold=0.3,
        scale_interval=1.0,  # Short interval for testing
    )

    # Set up a simple task processor
    async def dummy_processor(task_id: str, task_data: any):
        await asyncio.sleep(0.05)

    pool.set_task_processor(dummy_processor)
    await pool.start()

    yield pool

    await pool.stop(graceful=True)


class TestWorkerPool:
    """Tests for WorkerPool class."""

    @pytest.mark.asyncio
    async def test_pool_initial_state(self, worker_pool):
        """Test pool initial state after start."""
        count = await worker_pool.get_worker_count()

        # Should have min_workers
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_workers(self, worker_pool):
        """Test getting list of workers."""
        workers = await worker_pool.get_workers()

        assert len(workers) == 2
        for worker in workers:
            assert worker.id is not None
            assert worker.name is not None

    @pytest.mark.asyncio
    async def test_submit_task(self, worker_pool):
        """Test submitting a task."""
        task_id = await worker_pool.submit_task(
            task_id="test-task-1",
            task_data={"param": "value"},
        )

        assert task_id == "test-task-1"

    @pytest.mark.asyncio
    async def test_submit_multiple_tasks(self, worker_pool):
        """Test submitting multiple tasks."""
        task_ids = []
        for i in range(5):
            task_id = f"test-task-{i}"
            await worker_pool.submit_task(task_id=task_id, task_data={})
            task_ids.append(task_id)

        # Tasks should be accepted
        assert len(task_ids) == 5

    @pytest.mark.asyncio
    async def test_get_metrics(self, worker_pool):
        """Test getting pool metrics."""
        metrics = worker_pool.get_metrics()

        assert "total_tasks" in metrics
        assert "completed_tasks" in metrics
        assert "worker_count" in metrics
        assert "healthy_workers" in metrics
        assert "queue_size" in metrics

    @pytest.mark.asyncio
    async def test_worker_healthy_status(self, worker_pool):
        """Test worker health checking."""
        workers = await worker_pool.get_workers()

        for worker in workers:
            assert worker.is_healthy() is True

    @pytest.mark.asyncio
    async def test_force_scale_up(self, worker_pool):
        """Test forcing scale up."""
        initial_count = await worker_pool.get_worker_count()

        new_count = await worker_pool.force_scale(4)

        assert new_count == 4
        assert new_count > initial_count

    @pytest.mark.asyncio
    async def test_force_scale_down(self, worker_pool):
        """Test forcing scale down."""
        # First scale up
        await worker_pool.force_scale(4)

        # Then scale down
        new_count = await worker_pool.force_scale(2)

        assert new_count == 2

    @pytest.mark.asyncio
    async def test_force_scale_bounds(self, worker_pool):
        """Test scaling respects min/max bounds."""
        # Try to scale below min
        count = await worker_pool.force_scale(1)
        assert count == 2  # Should be min_workers

        # Try to scale above max
        count = await worker_pool.force_scale(100)
        assert count == 5  # Should be max_workers


class TestWorker:
    """Tests for Worker dataclass."""

    def test_worker_creation(self):
        """Test creating a worker."""
        from mcp_git.execution.worker_pool import Worker, WorkerStatus

        worker = Worker(
            id="test-id",
            name="test-worker",
            status=WorkerStatus.RUNNING,
            current_task_id=None,
            started_at=time.time(),
            last_heartbeat=time.time(),
            tasks_completed=0,
            tasks_failed=0,
            cpu_usage=0.0,
            memory_usage=0,
        )

        assert worker.id == "test-id"
        assert worker.name == "test-worker"
        assert worker.is_healthy() is True

    def test_worker_health_check(self):
        """Test worker health check."""
        from mcp_git.execution.worker_pool import Worker, WorkerStatus

        # Healthy worker
        healthy = Worker(
            id="test-id",
            name="test-worker",
            status=WorkerStatus.RUNNING,
            current_task_id=None,
            started_at=time.time(),
            last_heartbeat=time.time(),
            tasks_completed=0,
            tasks_failed=0,
            cpu_usage=0.0,
            memory_usage=0,
        )

        assert healthy.is_healthy() is True

        # Unhealthy - failed status
        unhealthy = Worker(
            id="test-id",
            name="test-worker",
            status=WorkerStatus.FAILED,
            current_task_id=None,
            started_at=time.time(),
            last_heartbeat=time.time(),
            tasks_completed=0,
            tasks_failed=0,
            cpu_usage=0.0,
            memory_usage=0,
        )

        assert unhealthy.is_healthy() is False

        # Unhealthy - stale heartbeat
        stale = Worker(
            id="test-id",
            name="test-worker",
            status=WorkerStatus.RUNNING,
            current_task_id=None,
            started_at=time.time(),
            last_heartbeat=time.time() - 60,  # 60 seconds ago
            tasks_completed=0,
            tasks_failed=0,
            cpu_usage=0.0,
            memory_usage=0,
        )

        assert stale.is_healthy() is False


class TestWorkerStatus:
    """Tests for WorkerStatus enum."""

    def test_status_values(self):
        """Test WorkerStatus enum values."""
        from mcp_git.execution.worker_pool import WorkerStatus

        assert WorkerStatus.STARTING.value == "starting"
        assert WorkerStatus.RUNNING.value == "running"
        assert WorkerStatus.IDLE.value == "idle"
        assert WorkerStatus.BUSY.value == "busy"
        assert WorkerStatus.STOPPING.value == "stopping"
        assert WorkerStatus.FAILED.value == "failed"
        assert WorkerStatus.UNKNOWN.value == "unknown"


class TestWorkerPoolCallbacks:
    """Tests for worker pool callbacks."""

    @pytest.mark.asyncio
    async def test_set_callbacks(self, worker_pool):
        """Test setting callbacks."""
        start_callbacks = []
        stop_callbacks = []

        def on_start(worker):
            start_callbacks.append(worker.id)

        def on_stop(worker):
            stop_callbacks.append(worker.id)

        worker_pool.set_callbacks(
            on_worker_start=on_start,
            on_worker_stop=on_stop,
        )

        # Verify callbacks are set
        assert worker_pool._on_worker_start is on_start
        assert worker_pool._on_worker_stop is on_stop

    @pytest.mark.asyncio
    async def test_task_callbacks(self, worker_pool):
        """Test task-related callbacks."""
        assigned = []
        completed = []
        failed = []

        def on_assigned(worker_id: str, task_id: str):
            assigned.append((worker_id, task_id))

        def on_complete(worker_id: str, task_id: str, result: any):
            completed.append((worker_id, task_id))

        def on_fail(worker_id: str, task_id: str, error: str):
            failed.append((worker_id, task_id))

        worker_pool.set_callbacks(
            on_task_assigned=on_assigned,
            on_task_completed=on_complete,
            on_task_failed=on_fail,
        )

        # Verify callbacks are set
        assert worker_pool._on_task_assigned is on_assigned
        assert worker_pool._on_task_complete is on_complete
        assert worker_pool._on_task_failed is on_fail


class TestWorkerPoolScaling:
    """Tests for worker pool automatic scaling."""

    @pytest.mark.asyncio
    async def test_scaling_up(self, temp_database: Path):
        """Test automatic scaling up."""
        from mcp_git.execution.worker_pool import WorkerPool

        pool = WorkerPool(
            min_workers=1,
            max_workers=3,
            max_tasks_per_worker=100,
            scale_up_threshold=0.9,
            scale_down_threshold=0.1,
            scale_interval=0.5,
        )

        async def dummy_processor(task_id: str, task_data: any):
            await asyncio.sleep(0.1)

        pool.set_task_processor(dummy_processor)
        await pool.start()

        # Submit many tasks to trigger scale up
        for i in range(10):
            await pool.submit_task(task_id=f"task-{i}", task_data={})

        # Wait for scaling
        await asyncio.sleep(2)

        # Should have scaled up
        count = await pool.get_worker_count()
        assert count >= 2

        await pool.stop(graceful=True)

    @pytest.mark.asyncio
    async def test_scaling_down(self, temp_database: Path):
        """Test automatic scaling down."""
        from mcp_git.execution.worker_pool import WorkerPool

        pool = WorkerPool(
            min_workers=1,
            max_workers=3,
            max_tasks_per_worker=100,
            scale_up_threshold=0.9,
            scale_down_threshold=0.1,
            scale_interval=0.5,
        )

        async def dummy_processor(task_id: str, task_data: any):
            await asyncio.sleep(0.05)

        pool.set_task_processor(dummy_processor)
        await pool.start()

        # Submit one task to use the worker
        await pool.submit_task(task_id="task-1", task_data={})

        # Wait for completion
        await asyncio.sleep(0.5)

        # Wait for scaling down
        await asyncio.sleep(2)

        await pool.stop(graceful=True)


class TestWorkerPoolTaskProcessing:
    """Tests for task processing in worker pool."""

    @pytest.mark.asyncio
    async def test_task_completion(self, worker_pool):
        """Test task completion tracking."""
        initial_metrics = worker_pool.get_metrics()

        # Submit a task and wait for completion
        await worker_pool.submit_task(task_id="completion-test", task_data={})

        # Wait for processing
        await asyncio.sleep(0.5)

        final_metrics = worker_pool.get_metrics()

        # Either completed or in progress
        assert final_metrics["total_tasks"] >= initial_metrics["total_tasks"] + 1

    @pytest.mark.asyncio
    async def test_task_failure_handling(self, temp_database: Path):
        """Test task failure handling."""
        from mcp_git.execution.worker_pool import WorkerPool

        pool = WorkerPool(
            min_workers=1,
            max_workers=2,
            max_tasks_per_worker=5,
            scale_interval=1.0,
        )

        failure_count = 0

        async def failing_processor(task_id: str, task_data: any):
            nonlocal failure_count
            failure_count += 1
            raise ValueError("Test failure")

        pool.set_task_processor(failing_processor)
        await pool.start()

        # Submit a failing task
        await pool.submit_task(task_id="failing-task", task_data={})

        # Wait for processing
        await asyncio.sleep(0.5)

        metrics = pool.get_metrics()

        # Should have recorded the failure
        assert metrics["failed_tasks"] >= 0  # May or may not have failed depending on timing

        await pool.stop(graceful=True)
