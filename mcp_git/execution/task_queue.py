"""
Task queue implementation for mcp-git.

This module provides an async task queue with priority support,
backpressure handling, and metrics tracking.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any
from uuid import uuid4

from loguru import logger


class TaskPriority(int, Enum):
    """Task priority levels."""

    LOW = 0
    NORMAL = 5
    HIGH = 10
    CRITICAL = 15


@dataclass
class QueuedTask:
    """A task in the queue."""

    id: str
    priority: TaskPriority
    created_at: float
    coroutine: Callable
    params: dict[str, Any]
    retries: int = 0
    max_retries: int = 3

    def __lt__(self, other: "QueuedTask") -> bool:
        """Compare tasks by priority (higher priority first)."""
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.created_at < other.created_at


class TaskQueue:
    """
    Async task queue with priority support.

    This queue manages task submission, prioritization, and processing
    with configurable concurrency limits and backpressure.
    """

    def __init__(
        self,
        max_size: int = 1000,
        max_concurrent: int = 10,
        max_retries: int = 3,
    ):
        """
        Initialize the task queue.

        Args:
            max_size: Maximum queue size (0 = unlimited)
            max_concurrent: Maximum concurrent tasks
            max_retries: Maximum retry attempts for failed tasks
        """
        self.max_size = max_size
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries

        # Priority queue (uses heapq internally)
        self._queue: asyncio.PriorityQueue[QueuedTask] = asyncio.PriorityQueue(maxsize=max_size)

        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # Active task tracking
        self._active_tasks: set[asyncio.Task] = set()
        self._active_count = 0

        # Metrics
        self._metrics = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
            "retried": 0,
            "cancelled": 0,
            "avg_processing_time": 0.0,
            "total_processing_time": 0.0,
        }

        # Worker task
        self._worker_task: asyncio.Task | None = None
        self._running = False

        # Callbacks
        self._on_task_complete: Callable | None = None
        self._on_task_error: Callable | None = None
        self._on_queue_full: Callable | None = None

    def set_callbacks(
        self,
        on_complete: Callable | None = None,
        on_error: Callable | None = None,
        on_queue_full: Callable | None = None,
    ) -> None:
        """
        Set callbacks for queue events.

        Args:
            on_complete: Called when task completes
            on_error: Called when task errors
            on_queue_full: Called when queue is full
        """
        self._on_task_complete = on_complete
        self._on_task_error = on_error
        self._on_queue_full = on_queue_full

    async def start(self) -> None:
        """Start the queue worker."""
        if self._running:
            return

        logger.info(
            "Starting task queue",
            max_size=self.max_size,
            max_concurrent=self.max_concurrent,
        )

        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())

    async def stop(self) -> None:
        """Stop the queue and wait for active tasks."""
        if not self._running:
            return

        logger.info("Stopping task queue")

        self._running = False

        # Cancel worker
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        # Wait for active tasks
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        logger.info("Task queue stopped")

    async def submit(
        self,
        coroutine: Callable,
        priority: TaskPriority = TaskPriority.NORMAL,
        params: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> str:
        """
        Submit a task to the queue.

        Args:
            coroutine: Async function to execute
            priority: Task priority
            params: Task parameters
            max_retries: Override max retries

        Returns:
            Task ID

        Raises:
            asyncio.QueueFull: If queue is at capacity
        """
        task = QueuedTask(
            id=str(uuid4()),
            priority=priority,
            created_at=time.time(),
            coroutine=coroutine,
            params=params or {},
            max_retries=max_retries if max_retries is not None else self.max_retries,
        )

        try:
            await self._queue.put(task)
            self._metrics["submitted"] += 1
            logger.debug("Task submitted", task_id=task.id, priority=priority)
            return task.id
        except asyncio.QueueFull:
            logger.warning("Queue full, task rejected", task_id=task.id)
            if self._on_queue_full:
                try:
                    await self._on_queue_full(task)
                except Exception as e:
                    logger.error("Queue full callback failed", error=str(e))
            raise

    async def submit_batch(
        self,
        tasks: list[tuple[Callable, TaskPriority, dict[str, Any]]],
    ) -> list[str]:
        """
        Submit multiple tasks at once.

        Args:
            tasks: List of (coroutine, priority, params) tuples

        Returns:
            List of task IDs
        """
        task_ids = []
        for coroutine, priority, params in tasks:
            try:
                task_id = await self.submit(coroutine, priority, params)
                task_ids.append(task_id)
            except asyncio.QueueFull:
                # Stop on first failure for batch
                break
        return task_ids

    async def get_queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    async def get_active_count(self) -> int:
        """Get number of active tasks."""
        return self._active_count

    async def get_queued_tasks(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get queued tasks (snapshot).

        Args:
            limit: Maximum to return

        Returns:
            List of task info
        """
        tasks = []
        items = list(self._queue._queue)  # Internal heap

        for task in sorted(items)[:limit]:
            tasks.append(
                {
                    "id": task.id,
                    "priority": task.priority.value
                    if hasattr(task.priority, "value")
                    else task.priority,
                    "created_at": task.created_at,
                    "params": task.params,
                }
            )

        return tasks

    def get_metrics(self) -> dict[str, Any]:
        """
        Get queue metrics.

        Returns:
            Metrics dictionary
        """
        avg_time = (
            self._metrics["total_processing_time"] / self._metrics["completed"]
            if self._metrics["completed"] > 0
            else 0.0
        )

        return {
            "submitted": self._metrics["submitted"],
            "completed": self._metrics["completed"],
            "failed": self._metrics["failed"],
            "retried": self._metrics["retried"],
            "cancelled": self._metrics["cancelled"],
            "avg_processing_time_seconds": avg_time,
            "queue_size": self._queue.qsize(),
            "active_count": self._active_count,
            "max_concurrent": self.max_concurrent,
            "available_slots": self.max_concurrent - self._active_count,
        }

    async def _process_queue(self) -> None:
        """Process tasks from the queue."""
        while self._running:
            try:
                # Get next task with timeout
                try:
                    task = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue

                # Acquire semaphore
                async with self._semaphore:
                    if not self._running:
                        # Put task back if we're stopping
                        await self._queue.put(task)
                        break

                    # Create worker task
                    self._active_count += 1
                    worker = asyncio.create_task(self._run_task(task))
                    self._active_tasks.add(worker)

                    def done_callback(t: asyncio.Task):
                        self._active_tasks.discard(t)
                        self._active_count -= 1

                    worker.add_done_callback(done_callback)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Queue processing error", error=str(e))
                await asyncio.sleep(0.1)

    async def _run_task(self, task: QueuedTask) -> None:
        """Run a single task."""
        start_time = time.time()

        try:
            # Execute the coroutine
            if asyncio.iscoroutinefunction(task.coroutine):
                result = await task.coroutine(**task.params)
            else:
                result = task.coroutine(**task.params)

            # Update metrics
            processing_time = time.time() - start_time
            self._metrics["completed"] += 1
            self._metrics["total_processing_time"] += processing_time

            logger.debug(
                "Task completed",
                task_id=task.id,
                processing_time=processing_time,
            )

            # Callback
            if self._on_task_complete:
                try:
                    await self._on_task_complete(task.id, result)
                except Exception as e:
                    logger.error("Complete callback failed", error=str(e))

        except asyncio.CancelledError:
            self._metrics["cancelled"] += 1
            logger.info("Task cancelled", task_id=task.id)

        except Exception as e:
            # Check if we should retry
            if task.retries < task.max_retries:
                task.retries += 1
                self._metrics["retried"] += 1

                logger.warning(
                    "Task failed, retrying",
                    task_id=task.id,
                    attempt=task.retries,
                    max_attempts=task.max_retries,
                    error=str(e),
                )

                # Re-queue with same priority
                try:
                    await self._queue.put(task)
                except asyncio.QueueFull:
                    self._metrics["failed"] += 1
                    logger.error("Task failed permanently, queue full", task_id=task.id)
            else:
                self._metrics["failed"] += 1
                logger.error(
                    "Task failed permanently",
                    task_id=task.id,
                    error=str(e),
                )

                # Callback
                if self._on_task_error:
                    try:
                        await self._on_task_error(task.id, str(e))
                    except Exception as cb_e:
                        logger.error("Error callback failed", error=str(cb_e))

    async def clear(self) -> int:
        """
        Clear all queued tasks.

        Returns:
            Number of tasks cleared
        """
        cleared = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                cleared += 1
            except asyncio.QueueEmpty:
                break

        logger.info("Queue cleared", count=cleared)
        return cleared

    async def wait_for_completion(self, timeout: float | None = None) -> bool:
        """
        Wait for all tasks to complete.

        Args:
            timeout: Maximum time to wait

        Returns:
            True if all tasks completed, False if timeout
        """
        start = time.time()

        while True:
            if self._queue.empty() and self._active_count == 0:
                return True

            if timeout and (time.time() - start) >= timeout:
                return False

            await asyncio.sleep(0.1)
