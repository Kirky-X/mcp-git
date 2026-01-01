"""
Task management service implementation.

This module provides the task management service for the microservices architecture.
"""

from typing import Any
from uuid import UUID

from loguru import logger

from mcp_git.service.task_manager import TaskManager
from mcp_git.services.service_interface import TaskServiceInterface
from mcp_git.storage.models import Task, TaskStatus


class TaskService(TaskServiceInterface):
    """
    Task management service.

    This service handles task creation, tracking, and management.
    """

    def __init__(self, task_manager: TaskManager):
        """
        Initialize the task service.

        Args:
            task_manager: Task manager instance
        """
        self.task_manager = task_manager

    async def create_task(
        self,
        operation: str,
        workspace_id: UUID | None = None,
        params: dict[str, Any] | None = None,
    ) -> Task:
        """
        Create a new task.

        Args:
            operation: Operation to perform
            workspace_id: Workspace ID
            params: Task parameters

        Returns:
            Created task
        """
        logger.info("Creating task", operation=operation, workspace_id=str(workspace_id))

        task = await self.task_manager.create_task(
            operation=operation,
            workspace_id=workspace_id,
            params=params or {},
        )

        logger.info("Task created", task_id=str(task.id), operation=operation)
        return task

    async def get_task(self, task_id: UUID) -> Task | None:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None
        """
        logger.debug("Getting task", task_id=str(task_id))

        return await self.task_manager.get_task(task_id)

    async def list_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int = 100,
    ) -> list[Task]:
        """
        List tasks.

        Args:
            status: Filter by status
            limit: Maximum number of tasks

        Returns:
            List of tasks
        """
        logger.debug("Listing tasks", status=status, limit=limit)

        return await self.task_manager.list_tasks(status=status, limit=limit)

    async def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> bool:
        """
        Update task status.

        Args:
            task_id: Task ID
            status: New status
            result: Task result
            error_message: Error message

        Returns:
            True if updated, False otherwise
        """
        logger.info("Updating task status", task_id=str(task_id), status=status)

        if status == TaskStatus.COMPLETED:
            success = await self.task_manager.complete_task(task_id, result)
        elif status == TaskStatus.FAILED:
            success = await self.task_manager.fail_task(task_id, error_message)
        elif status == TaskStatus.CANCELLED:
            success = await self.task_manager.cancel_task(task_id)
        else:
            success = await self.task_manager.update_task_status(task_id, status)

        return success

    async def cancel_task(self, task_id: UUID) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled, False otherwise
        """
        logger.info("Cancelling task", task_id=str(task_id))

        return await self.task_manager.cancel_task(task_id)
