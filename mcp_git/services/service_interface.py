"""
Service interface definitions for mcp-git.

This module defines the interfaces for all services in the microservices architecture.
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from mcp_git.storage.models import Task, TaskStatus, Workspace


class GitServiceInterface(ABC):
    """Interface for Git operations service."""

    @abstractmethod
    async def clone(
        self,
        url: str,
        workspace_id: UUID,
        branch: str | None = None,
        depth: int | None = None,
    ) -> dict[str, Any]:
        """Clone a repository."""
        pass

    @abstractmethod
    async def commit(
        self,
        workspace_id: UUID,
        message: str,
        author_name: str | None = None,
        author_email: str | None = None,
    ) -> str:
        """Create a commit."""
        pass

    @abstractmethod
    async def push(
        self,
        workspace_id: UUID,
        remote: str = "origin",
        branch: str | None = None,
        force: bool = False,
    ) -> None:
        """Push changes to remote."""
        pass

    @abstractmethod
    async def pull(
        self,
        workspace_id: UUID,
        remote: str = "origin",
        branch: str | None = None,
        rebase: bool = False,
    ) -> None:
        """Pull changes from remote."""
        pass

    @abstractmethod
    async def get_status(self, workspace_id: UUID) -> dict[str, Any] | None:
        """Get repository status."""
        pass


class TaskServiceInterface(ABC):
    """Interface for task management service."""

    @abstractmethod
    async def create_task(
        self,
        operation: str,
        workspace_id: UUID | None = None,
        params: dict[str, Any] | None = None,
    ) -> Task:
        """Create a new task."""
        pass

    @abstractmethod
    async def get_task(self, task_id: UUID) -> Task | None:
        """Get a task by ID."""
        pass

    @abstractmethod
    async def list_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int = 100,
    ) -> list[Task]:
        """List tasks."""
        pass

    @abstractmethod
    async def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> bool:
        """Update task status."""
        pass

    @abstractmethod
    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a task."""
        pass


class StorageServiceInterface(ABC):
    """Interface for storage service."""

    @abstractmethod
    async def create_workspace(self, workspace: Workspace) -> Workspace:
        """Create a new workspace."""
        pass

    @abstractmethod
    async def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        """Get a workspace by ID."""
        pass

    @abstractmethod
    async def list_workspaces(self) -> list[Workspace]:
        """List all workspaces."""
        pass

    @abstractmethod
    async def update_workspace(
        self,
        workspace_id: UUID,
        **kwargs: Any,
    ) -> bool:
        """Update workspace."""
        pass

    @abstractmethod
    async def delete_workspace(self, workspace_id: UUID) -> bool:
        """Delete a workspace."""
        pass


class WorkspaceServiceInterface(ABC):
    """Interface for workspace management service."""

    @abstractmethod
    async def allocate_workspace(self) -> Workspace:
        """Allocate a new workspace."""
        pass

    @abstractmethod
    async def release_workspace(self, workspace_id: UUID) -> bool:
        """Release a workspace."""
        pass

    @abstractmethod
    async def get_workspace_size(self, workspace_id: UUID) -> int:
        """Get workspace size in bytes."""
        pass

    @abstractmethod
    async def cleanup_expired_workspaces(self) -> tuple[int, int]:
        """Clean up expired workspaces."""
        pass


class MetricsServiceInterface(ABC):
    """Interface for metrics service."""

    @abstractmethod
    async def record_metric(
        self, name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        """Record a metric."""
        pass

    @abstractmethod
    async def get_metrics(
        self, name: str, time_range: tuple[float, float] | None = None
    ) -> list[dict[str, Any]]:
        """Get metrics."""
        pass

    @abstractmethod
    async def increment_counter(
        self, name: str, value: float = 1.0, tags: dict[str, str] | None = None
    ) -> None:
        """Increment a counter."""
        pass


class AuditServiceInterface(ABC):
    """Interface for audit service."""

    @abstractmethod
    async def log_event(
        self,
        event_type: str,
        severity: str,
        user_id: str | None = None,
        workspace_id: UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit event."""
        pass

    @abstractmethod
    async def get_events(
        self,
        event_type: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get audit events."""
        pass

    @abstractmethod
    async def get_statistics(self) -> dict[str, Any]:
        """Get audit statistics."""
        pass
