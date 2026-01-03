"""
SQLAlchemy ORM models for mcp-git storage layer.

This module defines SQLAlchemy ORM models that map to the database tables.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .models import GitOperation, Task, TaskStatus, Workspace

UTC = timezone.utc


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all ORM models."""


class TaskORM(Base):
    """SQLAlchemy ORM model for tasks table."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    operation: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    workspace_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    params: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    started_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_status_created", "status", "created_at"),  # For get_pending_tasks()
        Index("idx_operation_status", "operation", "status"),  # For operation filtering
        Index("idx_workspace_created", "workspace_path", "created_at"),  # For workspace queries
        {"comment": "Task tracking table"},
    )

    def to_task(self) -> Task:
        """Convert ORM model to Task object."""
        from uuid import UUID

        return Task(
            id=UUID(self.id),
            operation=GitOperation(self.operation),
            status=TaskStatus(self.status),
            workspace_path=Path(self.workspace_path) if self.workspace_path else None,
            params=json.loads(self.params) if self.params else {},
            result=json.loads(self.result) if self.result else None,
            error_message=self.error_message,
            progress=self.progress,
            created_at=datetime.fromtimestamp(self.created_at, UTC) if self.created_at else None,
            started_at=datetime.fromtimestamp(self.started_at, UTC) if self.started_at else None,
            completed_at=datetime.fromtimestamp(self.completed_at, UTC)
            if self.completed_at
            else None,
        )

    @classmethod
    def from_task(cls, task: Task) -> "TaskORM":
        """Create ORM model from Task object."""
        return cls(
            id=str(task.id),
            operation=task.operation.value,
            status=task.status.value,
            workspace_path=str(task.workspace_path) if task.workspace_path else None,
            params=json.dumps(task.params) if task.params else "{}",
            result=json.dumps(task.result) if task.result else None,
            error_message=task.error_message,
            progress=task.progress,
            created_at=int(task.created_at.timestamp()) if task.created_at else None,
            started_at=int(task.started_at.timestamp()) if task.started_at else None,
            completed_at=int(task.completed_at.timestamp()) if task.completed_at else None,
        )


class WorkspaceORM(Base):
    """SQLAlchemy ORM model for workspaces table."""

    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    metadata_json: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_last_accessed", "last_accessed_at"),  # For LRU cleanup
        Index("idx_size_accessed", "size_bytes", "last_accessed_at"),  # For size-based cleanup
        {"comment": "Workspace tracking table"},
    )

    def to_workspace(self) -> Workspace:
        """Convert ORM model to Workspace object."""
        from uuid import UUID

        return Workspace(
            id=UUID(self.id),
            path=Path(self.path),
            size_bytes=self.size_bytes,
            last_accessed_at=datetime.fromtimestamp(self.last_accessed_at, UTC),
            created_at=datetime.fromtimestamp(self.created_at, UTC),
            metadata=json.loads(self.metadata_json) if self.metadata_json else {},
        )

    @classmethod
    def from_workspace(cls, workspace: Workspace) -> "WorkspaceORM":
        """Create ORM model from Workspace object."""
        return cls(
            id=str(workspace.id),
            path=str(workspace.path),
            size_bytes=workspace.size_bytes,
            last_accessed_at=int(workspace.last_accessed_at.timestamp()),
            created_at=int(workspace.created_at.timestamp()),
            metadata_json=json.dumps(workspace.metadata) if workspace.metadata else "{}",
        )


class OperationLogORM(Base):
    """SQLAlchemy ORM model for operation_logs table."""

    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(50), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[int] = mapped_column(Integer, nullable=False)

    def to_operation_log(self) -> Any:
        """Convert ORM model to OperationLog object."""
        from uuid import UUID

        from .models import OperationLog

        return OperationLog(
            id=self.id,
            task_id=UUID(self.task_id),
            operation=GitOperation(self.operation),
            level=self.level,
            message=self.message,
            timestamp=datetime.fromtimestamp(self.timestamp, UTC),
        )
