"""
Performance benchmarks for mcp-git.

Tests for measuring and tracking performance of critical operations.
Run with: pytest tests/test_benchmarks.py --benchmark-only
"""

# type: ignore  # pytest-benchmark functions have special patterns that don't match mypy's expectations

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

from mcp_git.service.workspace_manager import WorkspaceConfig, WorkspaceManager
from mcp_git.storage import SqliteStorage
from mcp_git.storage.models import GitOperation, Task, TaskStatus, Workspace


@pytest_asyncio.fixture
async def storage(temp_database: Path) -> AsyncGenerator[SqliteStorage, None]:
    """Create a storage instance for benchmarking."""
    storage = SqliteStorage(temp_database)
    await storage.initialize()
    yield storage
    await storage.close()


@pytest_asyncio.fixture
async def workspace_manager(
    temp_workspace_dir: Path, temp_database: Path
) -> AsyncGenerator[WorkspaceManager, None]:
    """Create a workspace manager for benchmarking."""
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


class TestStorageBenchmarks:
    """Benchmark storage operations."""

    def benchmark_storage_initialize(self, benchmark, temp_database: Path):
        """Benchmark storage initialization."""

        async def init_storage():
            storage = SqliteStorage(temp_database)
            await storage.initialize()
            await storage.close()

        benchmark(asyncio.run, init_storage())

    def benchmark_task_create(self, benchmark, storage: SqliteStorage):
        """Benchmark task creation."""
        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params={"url": "https://example.com/repo.git"},
        )

        async def create():
            return await storage.create_task(task)

        benchmark(asyncio.run, create())

    def benchmark_task_get(self, benchmark, storage: SqliteStorage):
        """Benchmark task retrieval."""
        # Create a task first
        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params={"url": "https://example.com/repo.git"},
        )
        created = asyncio.run(storage.create_task(task))

        async def get():
            return await storage.get_task(created.id)

        benchmark(asyncio.run, get())

    def benchmark_task_update(self, benchmark, storage: SqliteStorage):
        """Benchmark task update."""
        # Create a task first
        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params={"url": "https://example.com/repo.git"},
        )
        created = asyncio.run(storage.create_task(task))

        async def update():
            return await storage.update_task(
                created.id,
                status=TaskStatus.RUNNING,
                progress=50,
            )

        benchmark(asyncio.run, update())

    def benchmark_task_delete(self, benchmark, storage: SqliteStorage):
        """Benchmark task deletion."""
        # Create a task first
        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params={"url": "https://example.com/repo.git"},
        )
        created = asyncio.run(storage.create_task(task))

        async def delete():
            return await storage.delete_task(created.id)

        benchmark(asyncio.run, delete())

    def benchmark_task_list(self, benchmark, storage: SqliteStorage):
        """Benchmark task listing."""

        # Create 100 tasks first
        async def create_tasks():
            tasks = [
                Task(
                    id=uuid4(),
                    operation=GitOperation.CLONE,
                    status=TaskStatus.QUEUED,
                    params={"url": f"https://example.com/repo{i}.git"},
                )
                for i in range(100)
            ]
            for task in tasks:
                await storage.create_task(task)

        asyncio.run(create_tasks())

        async def list_tasks():
            return await storage.list_tasks()

        benchmark(asyncio.run, list_tasks())

    def benchmark_workspace_create(
        self, benchmark, storage: SqliteStorage, temp_workspace_dir: Path
    ):
        """Benchmark workspace creation."""
        workspace = Workspace(
            path=temp_workspace_dir / "benchmark_workspace",
            size_bytes=0,
        )

        async def create():
            return await storage.create_workspace(workspace)

        benchmark(asyncio.run, create())

    def benchmark_workspace_get(self, benchmark, storage: SqliteStorage, temp_workspace_dir: Path):
        """Benchmark workspace retrieval."""
        # Create a workspace first
        workspace = Workspace(
            path=temp_workspace_dir / "benchmark_workspace",
            size_bytes=0,
        )
        created = asyncio.run(storage.create_workspace(workspace))

        async def get():
            return await storage.get_workspace(created.id)

        benchmark(asyncio.run, get())

    def benchmark_workspace_update(
        self, benchmark, storage: SqliteStorage, temp_workspace_dir: Path
    ):
        """Benchmark workspace update."""
        # Create a workspace first
        workspace = Workspace(
            path=temp_workspace_dir / "benchmark_workspace",
            size_bytes=0,
        )
        created = asyncio.run(storage.create_workspace(workspace))

        async def update():
            return await storage.update_workspace(
                created.id,
                size_bytes=1024,
            )

        benchmark(asyncio.run, update())

    def benchmark_workspace_list(self, benchmark, storage: SqliteStorage, temp_workspace_dir: Path):
        """Benchmark workspace listing."""

        # Create 50 workspaces first
        async def create_workspaces():
            for i in range(50):
                workspace = Workspace(
                    path=temp_workspace_dir / f"benchmark_workspace_{i}",
                    size_bytes=0,
                )
                await storage.create_workspace(workspace)

        asyncio.run(create_workspaces())

        async def list_workspaces():
            return await storage.list_workspaces()

        benchmark(asyncio.run, list_workspaces())

    def benchmark_batch_task_operations(self, benchmark, storage: SqliteStorage):
        """Benchmark batch task operations."""
        # Create 100 tasks
        task_ids = []

        async def create_tasks():
            for i in range(100):
                task = Task(
                    id=uuid4(),
                    operation=GitOperation.CLONE,
                    status=TaskStatus.QUEUED,
                    params={"url": f"https://example.com/repo{i}.git"},
                )
                created = await storage.create_task(task)
                task_ids.append(created.id)

        asyncio.run(create_tasks())

        async def batch_get():
            return await storage.get_tasks_batch(task_ids)

        benchmark(asyncio.run, batch_get())


class TestWorkspaceManagerBenchmarks:
    """Benchmark workspace manager operations."""

    def benchmark_workspace_allocation(self, benchmark, workspace_manager: WorkspaceManager):
        """Benchmark workspace allocation."""

        async def allocate():
            return await workspace_manager.allocate_workspace()

        benchmark(asyncio.run, allocate())

    def benchmark_workspace_release(self, benchmark, workspace_manager: WorkspaceManager):
        """Benchmark workspace release."""
        # Allocate a workspace first
        ws = asyncio.run(workspace_manager.allocate_workspace())

        async def release():
            return await workspace_manager.release_workspace(ws.id)

        benchmark(asyncio.run, release())

    def benchmark_workspace_touch(self, benchmark, workspace_manager: WorkspaceManager):
        """Benchmark workspace touch operation."""
        # Allocate a workspace first
        ws = asyncio.run(workspace_manager.allocate_workspace())

        async def touch():
            return await workspace_manager.touch_workspace(ws.id)

        benchmark(asyncio.run, touch())

    def benchmark_concurrent_workspace_allocation(
        self, benchmark, workspace_manager: WorkspaceManager
    ):
        """Benchmark concurrent workspace allocation."""

        async def allocate_multiple():
            tasks = [workspace_manager.allocate_workspace() for _ in range(10)]
            return await asyncio.gather(*tasks)

        benchmark(asyncio.run, allocate_multiple())

    def benchmark_cleanup_expired_workspaces(self, benchmark, workspace_manager: WorkspaceManager):
        """Benchmark cleanup of expired workspaces."""

        # Create some old workspaces first
        async def create_old_workspaces():
            for _ in range(20):
                workspace = await workspace_manager.allocate_workspace()
                # Simulate old access time
                await workspace_manager.storage.update_workspace(
                    workspace.id,
                    last_accessed_at=None,  # Will use old timestamp
                )

        asyncio.run(create_old_workspaces())

        async def cleanup():
            return await workspace_manager.cleanup_expired_workspaces()

        benchmark(asyncio.run, cleanup())


class TestBatchOperationsBenchmarks:
    """Benchmark batch operations."""

    def benchmark_batch_task_creation(self, benchmark, storage: SqliteStorage):
        """Benchmark batch task creation."""

        async def create_batch():
            tasks = [
                Task(
                    id=uuid4(),
                    operation=GitOperation.CLONE,
                    status=TaskStatus.QUEUED,
                    params={"url": f"https://example.com/repo{i}.git"},
                )
                for i in range(100)
            ]
            return await asyncio.gather(*[storage.create_task(task) for task in tasks])

        benchmark(asyncio.run, create_batch())

    def benchmark_batch_task_updates(self, benchmark, storage: SqliteStorage):
        """Benchmark batch task updates."""
        # Create tasks first
        task_ids = []

        async def create_tasks():
            for i in range(100):
                task = Task(
                    id=uuid4(),
                    operation=GitOperation.CLONE,
                    status=TaskStatus.QUEUED,
                    params={"url": f"https://example.com/repo{i}.git"},
                )
                created = await storage.create_task(task)
                task_ids.append(created.id)

        asyncio.run(create_tasks())

        async def update_batch():
            updates = [
                storage.update_task(task_id, status=TaskStatus.RUNNING, progress=i)
                for i, task_id in enumerate(task_ids)
            ]
            return await asyncio.gather(*updates)

        benchmark(asyncio.run, update_batch())

    def benchmark_batch_workspace_creation(
        self, benchmark, storage: SqliteStorage, temp_workspace_dir: Path
    ):
        """Benchmark batch workspace creation."""

        async def create_batch():
            workspaces = [
                Workspace(
                    path=temp_workspace_dir / f"workspace_{i}",
                    size_bytes=0,
                )
                for i in range(50)
            ]
            return await asyncio.gather(*[storage.create_workspace(ws) for ws in workspaces])

        benchmark(asyncio.run, create_batch())


class TestPerformanceRegression:
    """Tests for performance regression detection."""

    @pytest.mark.asyncio
    async def test_task_creation_performance_baseline(self, storage: SqliteStorage):
        """Establish baseline for task creation performance."""
        import time

        # Create 100 tasks and measure time
        start = time.time()
        for i in range(100):
            task = Task(
                id=uuid4(),
                operation=GitOperation.CLONE,
                status=TaskStatus.QUEUED,
                params={"url": f"https://example.com/repo{i}.git"},
            )
            await storage.create_task(task)
        elapsed = time.time() - start

        # Baseline: 100 tasks should complete in less than 1 second
        assert elapsed < 1.0, f"Task creation too slow: {elapsed}s for 100 tasks"

    @pytest.mark.asyncio
    async def test_workspace_allocation_performance_baseline(
        self, workspace_manager: WorkspaceManager
    ):
        """Establish baseline for workspace allocation performance."""
        import time

        # Allocate 20 workspaces and measure time
        start = time.time()
        for _ in range(20):
            await workspace_manager.allocate_workspace()
        elapsed = time.time() - start

        # Baseline: 20 workspaces should allocate in less than 2 seconds
        assert elapsed < 2.0, f"Workspace allocation too slow: {elapsed}s for 20 workspaces"

    @pytest.mark.asyncio
    async def test_batch_operations_performance_baseline(self, storage: SqliteStorage):
        """Establish baseline for batch operations performance."""
        import time

        # Create 100 tasks
        task_ids = []
        for i in range(100):
            task = Task(
                id=uuid4(),
                operation=GitOperation.CLONE,
                status=TaskStatus.QUEUED,
                params={"url": f"https://example.com/repo{i}.git"},
            )
            created = await storage.create_task(task)
            task_ids.append(created.id)

        # Batch retrieve and measure time
        start = time.time()
        tasks = await storage.get_tasks_batch(task_ids)
        elapsed = time.time() - start

        # Baseline: Batch retrieve of 100 tasks should complete in less than 0.1 seconds
        assert elapsed < 0.1, f"Batch retrieve too slow: {elapsed}s for 100 tasks"
        assert len(tasks) == 100


# Performance thresholds for CI/CD
PERFORMANCE_THRESHOLDS = {
    "task_creation_ms_per_task": 10,  # 10ms per task
    "workspace_allocation_ms": 100,  # 100ms per workspace
    "batch_retrieve_ms_per_100": 50,  # 50ms for 100 tasks
}


def check_performance_threshold(metric_name: str, actual_value: float, threshold: float):
    """Check if performance meets threshold."""
    if actual_value > threshold:
        pytest.fail(
            f"Performance regression detected: {metric_name} = {actual_value}ms "
            f"(threshold: {threshold}ms)"
        )


class TestPerformanceThresholds:
    """Tests that verify performance thresholds are met."""

    @pytest.mark.asyncio
    async def test_task_creation_meets_threshold(self, storage: SqliteStorage):
        """Verify task creation meets performance threshold."""
        import time

        # Create 100 tasks
        start = time.time()
        for i in range(100):
            task = Task(
                id=uuid4(),
                operation=GitOperation.CLONE,
                status=TaskStatus.QUEUED,
                params={"url": f"https://example.com/repo{i}.git"},
            )
            await storage.create_task(task)
        elapsed_ms = (time.time() - start) * 1000

        # Check threshold: 10ms per task
        per_task = elapsed_ms / 100
        check_performance_threshold(
            "task_creation_ms_per_task",
            per_task,
            PERFORMANCE_THRESHOLDS["task_creation_ms_per_task"],
        )

    @pytest.mark.asyncio
    async def test_workspace_allocation_meets_threshold(self, workspace_manager: WorkspaceManager):
        """Verify workspace allocation meets performance threshold."""
        import time

        # Allocate 10 workspaces
        start = time.time()
        for _ in range(10):
            await workspace_manager.allocate_workspace()
        elapsed_ms = (time.time() - start) * 1000

        # Check threshold: 100ms per workspace
        per_workspace = elapsed_ms / 10
        check_performance_threshold(
            "workspace_allocation_ms",
            per_workspace,
            PERFORMANCE_THRESHOLDS["workspace_allocation_ms"],
        )

    @pytest.mark.asyncio
    async def test_batch_retrieve_meets_threshold(self, storage: SqliteStorage):
        """Verify batch retrieve meets performance threshold."""
        import time

        # Create 100 tasks
        task_ids = []
        for i in range(100):
            task = Task(
                id=uuid4(),
                operation=GitOperation.CLONE,
                status=TaskStatus.QUEUED,
                params={"url": f"https://example.com/repo{i}.git"},
            )
            created = await storage.create_task(task)
            task_ids.append(created.id)

        # Batch retrieve
        start = time.time()
        tasks = await storage.get_tasks_batch(task_ids)
        elapsed_ms = (time.time() - start) * 1000

        # Check threshold: 50ms for 100 tasks
        check_performance_threshold(
            "batch_retrieve_ms_per_100",
            elapsed_ms,
            PERFORMANCE_THRESHOLDS["batch_retrieve_ms_per_100"],
        )
        assert len(tasks) == 100
