"""
Task management for mcp-git.

This module manages task lifecycle including creation, status updates,
timeout handling, and result retention.
"""

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from loguru import logger

from mcp_git.storage import SqliteStorage
from mcp_git.storage.models import (
    GitOperation,
    Task,
    TaskResult,
    TaskStatus,
)


class TaskConfig:
    """Configuration for task management."""

    def __init__(
        self,
        max_concurrent_tasks: int = 10,
        task_timeout_seconds: int = 300,  # 5 minutes
        result_retention_seconds: int = 3600,  # 1 hour
        cleanup_interval_seconds: int = 300,  # 5 minutes
    ):
        """
        Initialize task configuration.

        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks
            task_timeout_seconds: Default task timeout in seconds
            result_retention_seconds: How long to retain task results
            cleanup_interval_seconds: Interval for cleanup tasks
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_timeout_seconds = task_timeout_seconds
        self.result_retention_seconds = result_retention_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds


class TaskManager:
    """
    Manager for task lifecycle.

    This class handles task creation, execution tracking, status updates,
    timeout detection, and result retention.
    """

    def __init__(
        self,
        storage: SqliteStorage,
        config: TaskConfig | None = None,
    ):
        """
        Initialize the task manager.

        Args:
            storage: SQLite storage for task persistence
            config: Task configuration
        """
        self.storage = storage
        self.config = config or TaskConfig()

        # Active task tracking
        self._active_tasks: dict[UUID, asyncio.Task] = {}
        self._task_locks: dict[str, asyncio.Lock] = {}
        self._semaphore: asyncio.Semaphore | None = None

        # Background cleanup task
        self._cleanup_task: asyncio.Task | None = None
        self._cleanup_event = asyncio.Event()

        # Callbacks
        self._on_task_start: Callable | None = None
        self._on_task_complete: Callable | None = None
        self._on_task_error: Callable | None = None

    def set_task_callbacks(
        self,
        on_start: Callable | None = None,
        on_complete: Callable | None = None,
        on_error: Callable | None = None,
    ) -> None:
        """
        Set callbacks for task lifecycle events.

        Args:
            on_start: Called when task starts
            on_complete: Called when task completes
            on_error: Called when task errors
        """
        self._on_task_start = on_start
        self._on_task_complete = on_complete
        self._on_task_error = on_error

    async def start(self) -> None:
        """Start the task manager."""
        logger.info(
            "Starting task manager",
            max_concurrent=self.config.max_concurrent_tasks,
            timeout=self.config.task_timeout_seconds,
        )

        # Create semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)

        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop the task manager."""
        logger.info("Stopping task manager")

        if self._cleanup_task:
            self._cleanup_event.set()
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Cancel all active tasks
        for _task_id, task in self._active_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._active_tasks.clear()

    async def create_task(
        self,
        operation: GitOperation,
        params: dict[str, Any],
        workspace_path: str | None = None,
        priority: int = 0,
    ) -> Task:
        """
        Create a new task.

        Args:
            operation: Type of Git operation
            params: Operation parameters
            workspace_path: Optional workspace path
            priority: Task priority (higher = more important)

        Returns:
            Created task
        """
        task = Task(
            id=uuid4(),
            operation=operation,
            status=TaskStatus.QUEUED,
            workspace_path=workspace_path,
            params=params,
            progress=0,
            priority=priority,
            created_at=datetime.utcnow(),
        )

        await self.storage.create_task(task)

        logger.info(
            "Task created",
            task_id=str(task.id),
            operation=operation.value if hasattr(operation, "value") else operation,
        )

        return task

    async def get_task(self, task_id: UUID) -> Task | None:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """
        return await self.storage.get_task(task_id)

    async def list_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Task]:
        """
        List tasks with optional filtering.

        Args:
            status: Filter by status
            limit: Maximum number to return
            offset: Offset for pagination

        Returns:
            List of tasks
        """
        return await self.storage.list_tasks(status=status, limit=limit, offset=offset)

    async def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        progress: int | None = None,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> bool:
        """
        Update task status.

        Args:
            task_id: Task ID
            status: New status
            progress: Optional progress value (0-100)
            result: Optional result data
            error_message: Optional error message

        Returns:
            True if updated, False if not found
        """
        updates: dict[str, Any] = {"status": status}

        if progress is not None:
            updates["progress"] = progress

        if result is not None:
            updates["result"] = result

        if error_message is not None:
            updates["error_message"] = error_message

        if status == TaskStatus.RUNNING:
            updates["started_at"] = datetime.utcnow()
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            updates["completed_at"] = datetime.utcnow()

        return await self.storage.update_task(task_id, **updates)

    async def start_task(self, task_id: UUID) -> bool:
        """
        Mark a task as running.

        Args:
            task_id: Task ID

        Returns:
            True if started, False if not found or not in queued state
        """
        task = await self.storage.get_task(task_id)
        if task is None or task.status != TaskStatus.QUEUED:
            return False

        await self.update_task_status(task_id, TaskStatus.RUNNING, started_at=datetime.utcnow())

        logger.info("Task started", task_id=str(task_id))

        if self._on_task_start:
            try:
                await self._on_task_start(task)
            except Exception as e:
                logger.error("Task start callback failed", error=str(e))

        return True

    async def complete_task(
        self,
        task_id: UUID,
        result: dict[str, Any] | None = None,
    ) -> bool:
        """
        Mark a task as completed.

        Args:
            task_id: Task ID
            result: Optional result data

        Returns:
            True if completed, False if not found
        """
        success = await self.update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            progress=100,
            result=result,
            completed_at=datetime.utcnow(),
        )

        if success:
            logger.info("Task completed", task_id=str(task_id))

            # Remove from active tasks
            self._active_tasks.pop(task_id, None)

            if self._on_task_complete:
                try:
                    await self._on_task_complete(task_id, result)
                except Exception as e:
                    logger.error("Task complete callback failed", error=str(e))

        return success

    async def fail_task(
        self,
        task_id: UUID,
        error_message: str,
    ) -> bool:
        """
        Mark a task as failed.

        Args:
            task_id: Task ID
            error_message: Error message

        Returns:
            True if failed, False if not found
        """
        success = await self.update_task_status(
            task_id,
            TaskStatus.FAILED,
            error_message=error_message,
            completed_at=datetime.utcnow(),
        )

        if success:
            logger.error("Task failed", task_id=str(task_id), error=error_message)

            # Remove from active tasks
            self._active_tasks.pop(task_id, None)

            if self._on_task_error:
                try:
                    await self._on_task_error(task_id, error_message)
                except Exception as e:
                    logger.error("Task error callback failed", error=str(e))

        return success

    async def cancel_task(self, task_id: UUID) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled, False if not found
        """
        # Cancel active task if running
        if task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            if not task.done():
                task.cancel()
            self._active_tasks.pop(task_id, None)

        success = await self.update_task_status(
            task_id,
            TaskStatus.CANCELLED,
            completed_at=datetime.utcnow(),
        )

        if success:
            logger.info("Task cancelled", task_id=str(task_id))

        return success

    async def submit_task(
        self,
        task_id: UUID,
        coroutine: "asyncio.coroutines.Coroutine",
    ) -> bool:
        """
        Submit a task for execution.

        This schedules the task to run with concurrency control.

        Args:
            task_id: Task ID
            coroutine: Async function to execute

        Returns:
            True if submitted, False if task not found
        """
        task = await self.storage.get_task(task_id)
        if task is None:
            return False

        async def run_with_semaphore():
            async with self._semaphore:
                await self._execute_task(task_id, coroutine)

        self._active_tasks[task_id] = asyncio.create_task(run_with_semaphore())

        return True

    async def _execute_task(
        self,
        task_id: UUID,
        coroutine: "asyncio.coroutines.Coroutine",
    ) -> None:
        """Execute a task with error handling and timeout."""
        try:
            # Mark as running
            await self.start_task(task_id)

            # Create timeout task
            timeout_seconds = self.config.task_timeout_seconds
            timeout_task = asyncio.create_task(asyncio.wait_for(coroutine, timeout=timeout_seconds))

            # Store timeout task
            self._active_tasks[task_id] = timeout_task

            # Wait for completion
            result = await timeout_task

            # Mark as completed
            await self.complete_task(task_id, result)

        except asyncio.TimeoutError:
            await self.fail_task(
                task_id,
                f"Task timed out after {timeout_seconds} seconds",
            )
        except asyncio.CancelledError:
            await self.update_task_status(
                task_id,
                TaskStatus.CANCELLED,
                completed_at=datetime.utcnow(),
            )
            self._active_tasks.pop(task_id, None)
        except Exception as e:
            await self.fail_task(task_id, str(e))

    async def get_task_result(self, task_id: UUID) -> TaskResult | None:
        """
        Get task result.

        Args:
            task_id: Task ID

        Returns:
            TaskResult if found, None otherwise
        """
        task = await self.storage.get_task(task_id)
        if task is None:
            return None

        return TaskResult(
            task_id=task.id,
            status=task.status,
            result=task.result,
            error_message=task.error_message,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
        )

    async def get_active_tasks(self) -> list[Task]:
        """
        Get all active tasks.

        Returns:
            List of active tasks
        """
        tasks = []
        for task_id in list(self._active_tasks.keys()):
            task = await self.storage.get_task(task_id)
            if task and task.status == TaskStatus.RUNNING:
                tasks.append(task)
        return tasks

    async def get_queued_tasks(self, limit: int = 10) -> list[Task]:
        """
        Get pending queued tasks.

        Args:
            limit: Maximum number to return

        Returns:
            List of queued tasks ordered by priority and creation time
        """
        return await self.storage.get_pending_tasks(limit)

    async def cleanup_expired_tasks(self) -> int:
        """
        Clean up expired tasks.

        Returns:
            Number of cleaned up tasks
        """
        return await self.storage.cleanup_expired_tasks(self.config.result_retention_seconds)

    async def _cleanup_loop(self) -> None:
        """Background task for periodic cleanup."""
        while not self._cleanup_event.is_set():
            try:
                # Wait for cleanup interval or event
                await asyncio.wait_for(
                    self._cleanup_event.wait(),
                    timeout=self.config.cleanup_interval_seconds,
                )
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue cleanup

            # Perform cleanup
            try:
                await self.cleanup_expired_tasks()
                await self._check_timeouts()
            except Exception as e:
                logger.error("Cleanup error", error=str(e))

    async def _check_timeouts(self) -> None:
        """Check for timed out tasks."""
        for task_id, task in list(self._active_tasks.items()):
            if task.done():
                continue

            db_task = await self.storage.get_task(task_id)
            if db_task and db_task.started_at:
                elapsed = (datetime.utcnow() - db_task.started_at).total_seconds()
                if elapsed > self.config.task_timeout_seconds:
                    logger.warning("Task timeout detected", task_id=str(task_id))
                    task.cancel()
                    await self.fail_task(
                        task_id,
                        f"Task timed out after {self.config.task_timeout_seconds} seconds",
                    )

    def get_stats(self) -> dict[str, Any]:
        """
        Get task manager statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "active_tasks": len(self._active_tasks),
            "max_concurrent": self.config.max_concurrent_tasks,
            "available_slots": self._semaphore._value if self._semaphore else 0,
            "timeout_seconds": self.config.task_timeout_seconds,
            "result_retention_seconds": self.config.result_retention_seconds,
        }
