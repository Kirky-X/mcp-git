"""
Worker pool implementation for mcp-git.

This module manages a pool of worker processes for parallel task execution
with health monitoring, automatic scaling, and graceful shutdown.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any
from uuid import uuid4

from loguru import logger


class WorkerStatus(Enum):
    """Worker status."""

    STARTING = "starting"
    RUNNING = "running"
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class Worker:
    """A worker instance."""

    id: str
    name: str
    status: WorkerStatus
    current_task_id: str | None
    started_at: float
    last_heartbeat: float
    tasks_completed: int
    tasks_failed: int
    cpu_usage: float
    memory_usage: int

    def is_healthy(self) -> bool:
        """Check if worker is healthy."""
        return (
            self.status in (WorkerStatus.RUNNING, WorkerStatus.IDLE, WorkerStatus.BUSY)
            and (time.time() - self.last_heartbeat) < 30
        )


@dataclass
class WorkerConfig:
    """Configuration for a worker."""

    name: str
    max_tasks: int = 100
    heartbeat_interval: float = 5.0
    timeout_seconds: float = 300.0
    restart_on_failure: bool = True
    environment: dict[str, str] | None = None


class WorkerPool:
    """
    Pool of workers for parallel task execution.

    This class manages worker lifecycle, task distribution, health monitoring,
    and automatic scaling based on queue length.
    """

    def __init__(
        self,
        min_workers: int = 2,
        max_workers: int = 10,
        max_tasks_per_worker: int = 100,
        scale_up_threshold: float = 0.8,
        scale_down_threshold: float = 0.3,
        scale_interval: float = 30.0,
    ):
        """
        Initialize the worker pool.

        Args:
            min_workers: Minimum number of workers
            max_workers: Maximum number of workers
            max_tasks_per_worker: Tasks before worker restart
            scale_up_threshold: Queue usage threshold to scale up
            scale_down_threshold: Queue usage threshold to scale down
            scale_interval: Interval between scale checks
        """
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.max_tasks_per_worker = max_tasks_per_worker
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.scale_interval = scale_interval

        # Worker management
        self._workers: dict[str, Worker] = {}
        self._worker_tasks: dict[str, asyncio.Task] = {}
        self._worker_locks: dict[str, asyncio.Lock] = {}

        # Task management
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._task_assignments: dict[str, str] = {}  # task_id -> worker_id

        # Pool state
        self._running = False
        self._scaling_task: asyncio.Task | None = None
        self._supervisor_task: asyncio.Task | None = None

        # Metrics
        self._metrics = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_workers_created": 0,
            "total_workers_failed": 0,
        }

        # Callbacks
        self._on_worker_start: Callable | None = None
        self._on_worker_stop: Callable | None = None
        self._on_worker_failure: Callable | None = None
        self._on_task_assigned: Callable | None = None
        self._on_task_completed: Callable | None = None
        self._on_task_failed: Callable | None = None

        # Task processor
        self._task_processor: Callable | None = None

    def set_callbacks(
        self,
        on_worker_start: Callable | None = None,
        on_worker_stop: Callable | None = None,
        on_worker_failure: Callable | None = None,
        on_task_assigned: Callable | None = None,
        on_task_completed: Callable | None = None,
        on_task_failed: Callable | None = None,
    ) -> None:
        """
        Set callbacks for pool events.

        Args:
            on_worker_start: Called when worker starts
            on_worker_stop: Called when worker stops
            on_worker_failure: Called when worker fails
            on_task_assigned: Called when task is assigned
            on_task_completed: Called when task completes
            on_task_failed: Called when task fails
        """
        self._on_worker_start = on_worker_start
        self._on_worker_stop = on_worker_stop
        self._on_worker_failure = on_worker_failure
        self._on_task_assigned = on_task_assigned
        self._on_task_completed = on_task_completed
        self._on_task_failed = on_task_failed

    def set_task_processor(self, processor: Callable) -> None:
        """
        Set the task processor function.

        Args:
            processor: Async function to process tasks
        """
        self._task_processor = processor

    async def start(self) -> None:
        """Start the worker pool."""
        if self._running:
            return

        logger.info(
            "Starting worker pool",
            min_workers=self.min_workers,
            max_workers=self.max_workers,
        )

        self._running = True

        # Start supervisor
        self._supervisor_task = asyncio.create_task(self._supervisor_loop())

        # Start scaling
        self._scaling_task = asyncio.create_task(self._scaling_loop())

        # Start initial workers
        for i in range(self.min_workers):
            await self._create_worker(f"worker-{i + 1}")

        logger.info("Worker pool started", worker_count=len(self._workers))

    async def stop(self, graceful: bool = True) -> None:
        """
        Stop the worker pool.

        Args:
            graceful: Wait for tasks to complete
        """
        if not self._running:
            return

        logger.info("Stopping worker pool", graceful=graceful)

        self._running = False

        # Cancel scaling
        if self._scaling_task:
            self._scaling_task.cancel()
            try:
                await self._scaling_task
            except asyncio.CancelledError:
                pass

        # Cancel supervisor
        if self._supervisor_task:
            self._supervisor_task.cancel()
            try:
                await self._supervisor_task
            except asyncio.CancelledError:
                pass

        if graceful:
            # Wait for tasks to complete
            while not self._task_queue.empty():
                await asyncio.sleep(0.5)

        # Stop all workers
        worker_ids = list(self._workers.keys())
        for worker_id in worker_ids:
            await self._stop_worker(worker_id, graceful)

        logger.info("Worker pool stopped")

    async def submit_task(
        self,
        task_id: str,
        task_data: Any,
        priority: int = 0,
    ) -> bool:
        """
        Submit a task to the pool.

        Args:
            task_id: Task identifier
            task_data: Task data
            priority: Task priority

        Returns:
            True if submitted
        """
        if not self._running:
            return False

        try:
            await self._task_queue.put((priority, task_id, task_data))
            self._metrics["total_tasks"] += 1
            return True
        except asyncio.QueueFull:
            logger.warning("Task queue full, task rejected", task_id=task_id)
            return False

    async def get_worker_count(self) -> int:
        """Get number of active workers."""
        return len(self._workers)

    async def get_workers(self) -> list[Worker]:
        """Get all workers."""
        return list(self._workers.values())

    async def get_worker(self, worker_id: str) -> Worker | None:
        """Get a specific worker."""
        return self._workers.get(worker_id)

    def get_metrics(self) -> dict[str, Any]:
        """
        Get pool metrics.

        Returns:
            Metrics dictionary
        """
        healthy_workers = sum(1 for w in self._workers.values() if w.is_healthy())
        busy_workers = sum(1 for w in self._workers.values() if w.status == WorkerStatus.BUSY)

        return {
            "total_tasks": self._metrics["total_tasks"],
            "completed_tasks": self._metrics["completed_tasks"],
            "failed_tasks": self._metrics["failed_tasks"],
            "success_rate": (
                self._metrics["completed_tasks"] / self._metrics["total_tasks"]
                if self._metrics["total_tasks"] > 0
                else 0.0
            ),
            "worker_count": len(self._workers),
            "healthy_workers": healthy_workers,
            "busy_workers": busy_workers,
            "idle_workers": healthy_workers - busy_workers,
            "queue_size": self._task_queue.qsize(),
            "total_workers_created": self._metrics["total_workers_created"],
            "total_workers_failed": self._metrics["total_workers_failed"],
        }

    async def _create_worker(self, name: str) -> str:
        """Create a new worker."""
        worker_id = str(uuid4())

        worker = Worker(
            id=worker_id,
            name=name,
            status=WorkerStatus.STARTING,
            current_task_id=None,
            started_at=time.time(),
            last_heartbeat=time.time(),
            tasks_completed=0,
            tasks_failed=0,
            cpu_usage=0.0,
            memory_usage=0,
        )

        self._workers[worker_id] = worker
        self._worker_locks[worker_id] = asyncio.Lock()
        self._metrics["total_workers_created"] += 1

        # Start worker task
        self._worker_tasks[worker_id] = asyncio.create_task(self._worker_loop(worker_id))

        logger.info("Worker created", worker_id=worker_id, name=name)

        # Callback
        if self._on_worker_start:
            try:
                await self._on_worker_start(worker)
            except Exception as e:
                logger.error("Worker start callback failed", error=str(e))

        return worker_id

    async def _stop_worker(self, worker_id: str, graceful: bool = True) -> None:
        """Stop a worker."""
        worker = self._workers.get(worker_id)
        if worker is None:
            return

        logger.info("Stopping worker", worker_id=worker_id, name=worker.name)

        worker.status = WorkerStatus.STOPPING

        # Cancel worker task
        task = self._worker_tasks.pop(worker_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Remove from tracking
        self._workers.pop(worker_id, None)
        self._worker_locks.pop(worker_id, None)

        # Callback
        if self._on_worker_stop:
            try:
                await self._on_worker_stop(worker)
            except Exception as e:
                logger.error("Worker stop callback failed", error=str(e))

    async def _worker_loop(self, worker_id: str) -> None:
        """Main worker loop."""
        worker = self._workers.get(worker_id)
        if worker is None:
            return

        worker.status = WorkerStatus.IDLE

        while self._running and worker_id in self._workers:
            try:
                # Get next task
                try:
                    priority, task_id, task_data = await asyncio.wait_for(
                        self._task_queue.get(),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    continue

                # Check if worker should stop
                if worker_id not in self._workers:
                    # Put task back
                    await self._task_queue.put((priority, task_id, task_data))
                    break

                # Update worker status
                worker.status = WorkerStatus.BUSY
                worker.current_task_id = task_id
                worker.last_heartbeat = time.time()

                # Track assignment
                self._task_assignments[task_id] = worker_id

                # Callback
                if self._on_task_assigned:
                    try:
                        await self._on_task_assigned(worker_id, task_id)
                    except Exception as e:
                        logger.error("Task assigned callback failed", error=str(e))

                # Process task
                try:
                    if self._task_processor:
                        await self._task_processor(task_id, task_data)

                    # Success
                    worker.tasks_completed += 1
                    self._metrics["completed_tasks"] += 1

                    logger.debug(
                        "Task completed",
                        worker_id=worker_id,
                        task_id=task_id,
                    )

                    # Callback
                    if self._on_task_completed:
                        try:
                            await self._on_task_completed(worker_id, task_id, None)
                        except Exception as e:
                            logger.error("Task completed callback failed", error=str(e))

                except Exception as e:
                    # Failure
                    worker.tasks_failed += 1
                    self._metrics["failed_tasks"] += 1

                    logger.error(
                        "Task failed",
                        worker_id=worker_id,
                        task_id=task_id,
                        error=str(e),
                    )

                    # Callback
                    if self._on_task_failed:
                        try:
                            await self._on_task_failed(worker_id, task_id, str(e))
                        except Exception as cb_e:
                            logger.error("Task failed callback failed", error=str(cb_e))

                # Clear assignment
                self._task_assignments.pop(task_id, None)
                worker.current_task_id = None
                worker.status = WorkerStatus.IDLE
                worker.last_heartbeat = time.time()

                # Check if worker needs restart
                total_tasks = worker.tasks_completed + worker.tasks_failed
                if total_tasks >= self.max_tasks_per_worker:
                    logger.info(
                        "Worker max tasks reached, restarting",
                        worker_id=worker_id,
                        name=worker.name,
                    )
                    await self._stop_worker(worker_id, graceful=False)
                    await self._create_worker(f"{worker.name}-restarted")
                    break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Worker loop error", worker_id=worker_id, error=str(e))
                worker.status = WorkerStatus.FAILED
                self._metrics["total_workers_failed"] += 1

                # Callback
                if self._on_worker_failure:
                    try:
                        await self._on_worker_failure(worker_id, str(e))
                    except Exception as cb_e:
                        logger.error("Worker failure callback failed", error=str(cb_e))

                break

    async def _supervisor_loop(self) -> None:
        """Supervise workers and handle failures."""
        while self._running:
            try:
                await asyncio.sleep(5.0)

                # Check worker health
                for worker_id, worker in list(self._workers.items()):
                    if not worker.is_healthy():
                        logger.warning(
                            "Worker unhealthy, restarting",
                            worker_id=worker_id,
                            name=worker.name,
                            status=worker.status.value
                            if hasattr(worker.status, "value")
                            else worker.status,
                        )
                        await self._stop_worker(worker_id, graceful=False)
                        await self._create_worker(f"{worker.name}-health")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Supervisor error", error=str(e))

    async def _scaling_loop(self) -> None:
        """Automatically scale workers based on load."""
        while self._running:
            try:
                await asyncio.sleep(self.scale_interval)

                if not self._running:
                    break

                queue_usage = (
                    self._task_queue.qsize() / self._task_queue.maxsize
                    if self._task_queue.maxsize > 0
                    else 0
                )

                current_count = len(self._workers)

                # Scale up
                if queue_usage > self.scale_up_threshold and current_count < self.max_workers:
                    new_workers = min(
                        self.max_workers - current_count,
                        max(1, int(queue_usage * 5)),
                    )
                    for i in range(new_workers):
                        await self._create_worker(f"worker-scaleup-{i + 1}")
                    logger.info(
                        "Scaled up workers",
                        added=new_workers,
                        total=current_count + new_workers,
                    )

                # Scale down
                elif queue_usage < self.scale_down_threshold and current_count > self.min_workers:
                    workers_to_remove = min(
                        current_count - self.min_workers,
                        max(1, int((self.scale_down_threshold - queue_usage) * 10)),
                    )
                    for _ in range(workers_to_remove):
                        # Find idle worker
                        idle_workers = [
                            wid for wid, w in self._workers.items() if w.status == WorkerStatus.IDLE
                        ]
                        if idle_workers:
                            await self._stop_worker(idle_workers[0], graceful=True)
                    logger.info(
                        "Scaled down workers",
                        removed=workers_to_remove,
                        total=current_count - workers_to_remove,
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scaling error", error=str(e))

    async def force_scale(self, target_count: int) -> int:
        """
        Force scale to target worker count.

        Args:
            target_count: Desired number of workers

        Returns:
            Actual number of workers after scaling
        """
        target_count = max(self.min_workers, min(self.max_workers, target_count))
        current_count = len(self._workers)

        if target_count > current_count:
            # Scale up
            for i in range(target_count - current_count):
                await self._create_worker(f"worker-force-{i + 1}")
        elif target_count < current_count:
            # Scale down
            for _ in range(current_count - target_count):
                idle_workers = [
                    wid for wid, w in self._workers.items() if w.status == WorkerStatus.IDLE
                ]
                if idle_workers:
                    await self._stop_worker(idle_workers[0], graceful=True)
                else:
                    break

        return len(self._workers)

    async def cleanup_stale_tasks(self, timeout_seconds: float = 600) -> int:
        """
        Clean up tasks that have been assigned but not completed.

        Args:
            timeout_seconds: Task timeout

        Returns:
            Number of tasks cleaned up
        """
        cleaned = 0
        current_time = time.time()

        for task_id, worker_id in list(self._task_assignments.items()):
            worker = self._workers.get(worker_id)
            if worker and worker.current_task_id == task_id:
                elapsed = current_time - worker.last_heartbeat
                if elapsed > timeout_seconds:
                    # Mark as failed
                    self._metrics["failed_tasks"] += 1
                    worker.tasks_failed += 1

                    # Clear assignment
                    self._task_assignments.pop(task_id, None)
                    worker.current_task_id = None
                    worker.status = WorkerStatus.IDLE

                    cleaned += 1

                    logger.warning(
                        "Stale task cleaned up",
                        task_id=task_id,
                        worker_id=worker_id,
                        elapsed=elapsed,
                    )

        return cleaned
