"""
Data models for mcp-git storage layer.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

# Compatibility with Python 3.10
UTC = timezone.utc


class TaskStatus(str, Enum):
    """Task execution status."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GitOperation(str, Enum):
    """Git operation types."""

    CLONE = "clone"
    COMMIT = "commit"
    PUSH = "push"
    PULL = "pull"
    FETCH = "fetch"
    BRANCH = "branch"
    MERGE = "merge"
    REBASE = "rebase"
    STASH = "stash"
    TAG = "tag"
    LOG = "log"
    DIFF = "diff"
    BLAME = "blame"
    STATUS = "status"
    ADD = "add"
    RESET = "reset"
    CHECKOUT = "checkout"
    CHERRY_PICK = "cherry_pick"
    REVERT = "revert"
    CLEAN = "clean"


class CleanupStrategy(str, Enum):
    """Workspace cleanup strategy."""

    LRU = "lru"
    FIFO = "fifo"


class Task:
    """Task model for tracking async Git operations."""

    def __init__(
        self,
        operation: GitOperation,
        workspace_path: Path | None = None,
        params: dict[str, Any] | None = None,
        id: UUID | None = None,
        status: TaskStatus = TaskStatus.QUEUED,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
        progress: int = 0,
        priority: int = 0,
        created_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ):
        self.id = id or uuid4()
        self.operation = operation
        self.status = status
        self.workspace_path = workspace_path
        self.params = params or {}
        self.result = result
        self.error_message = error_message
        self.progress = progress
        self.priority = priority
        self.created_at = created_at or datetime.now(UTC)
        self.started_at = started_at
        self.completed_at = completed_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "operation": self.operation.value
            if isinstance(self.operation, GitOperation)
            else self.operation,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "workspace_path": str(self.workspace_path) if self.workspace_path else None,
            "params": self.params,
            "result": self.result,
            "error_message": self.error_message,
            "progress": self.progress,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if "id" in data else None,
            operation=GitOperation(data["operation"])
            if "operation" in data
            else GitOperation.STATUS,
            status=TaskStatus(data["status"]) if "status" in data else TaskStatus.QUEUED,
            workspace_path=Path(data["workspace_path"]) if data.get("workspace_path") else None,
            params=data.get("params", {}),
            result=data.get("result"),
            error_message=data.get("error_message"),
            progress=data.get("progress", 0),
            priority=data.get("priority", 0),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            started_at=datetime.fromisoformat(data["started_at"])
            if data.get("started_at")
            else None,
            completed_at=datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None,
        )

    @property
    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }

    @property
    def duration_seconds(self) -> float | None:
        """Get task duration in seconds."""
        if self.started_at is None:
            return None

        end_time = self.completed_at or datetime.now(UTC)
        return (end_time - self.started_at).total_seconds()


class Workspace:
    """Workspace model for managing temporary Git repositories."""

    def __init__(
        self,
        path: Path,
        id: UUID | None = None,
        size_bytes: int = 0,
        last_accessed_at: datetime | None = None,
        created_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.id = id or uuid4()
        self.path = path
        self.size_bytes = size_bytes
        self.last_accessed_at = last_accessed_at or datetime.now(UTC)
        self.created_at = created_at or datetime.now(UTC)
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "path": str(self.path),
            "size_bytes": self.size_bytes,
            "last_accessed_at": self.last_accessed_at.isoformat()
            if self.last_accessed_at
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Workspace":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if "id" in data else None,
            path=Path(data["path"]),
            size_bytes=data.get("size_bytes", 0),
            last_accessed_at=datetime.fromisoformat(data["last_accessed_at"])
            if data.get("last_accessed_at")
            else None,
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            metadata=data.get("metadata", {}),
        )


class OperationLog:
    """Operation log model for auditing."""

    def __init__(
        self,
        task_id: UUID,
        operation: GitOperation,
        level: str,
        message: str,
        id: int | None = None,
        timestamp: datetime | None = None,
    ):
        self.id = id
        self.task_id = task_id
        self.operation = operation
        self.level = level
        self.message = message
        self.timestamp = timestamp or datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "task_id": str(self.task_id),
            "operation": self.operation.value
            if isinstance(self.operation, GitOperation)
            else self.operation,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class CommitInfo:
    """Information about a Git commit."""

    def __init__(
        self,
        oid: str,
        message: str,
        author_name: str,
        author_email: str,
        commit_time: datetime,
        parent_oids: list[str] | None = None,
    ):
        self.oid = oid
        self.message = message
        self.author_name = author_name
        self.author_email = author_email
        self.commit_time = commit_time
        self.parent_oids = parent_oids or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "oid": self.oid,
            "message": self.message,
            "author_name": self.author_name,
            "author_email": self.author_email,
            "commit_time": self.commit_time.isoformat(),
            "parent_oids": self.parent_oids,
        }


class BranchInfo:
    """Information about a Git branch."""

    def __init__(
        self,
        name: str,
        oid: str,
        is_local: bool = True,
        is_remote: bool = False,
        upstream_name: str | None = None,
    ):
        self.name = name
        self.oid = oid
        self.is_local = is_local
        self.is_remote = is_remote
        self.upstream_name = upstream_name

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "oid": self.oid,
            "is_local": self.is_local,
            "is_remote": self.is_remote,
            "upstream_name": self.upstream_name,
        }


class FileStatus:
    """Status of a file in the working directory."""

    def __init__(
        self,
        path: str,
        status: str,  # modified, added, deleted, untracked, staged
        new_path: str | None = None,
    ):
        self.path = path
        self.status = status
        self.new_path = new_path

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "status": self.status,
            "new_path": self.new_path,
        }


class DiffInfo:
    """Information about file differences."""

    def __init__(
        self,
        old_path: str,
        new_path: str,
        change_type: str,  # added, deleted, modified, renamed
        diff_lines: list[str] | None = None,
    ):
        self.old_path = old_path
        self.new_path = new_path
        self.change_type = change_type
        self.diff_lines = diff_lines or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "old_path": self.old_path,
            "new_path": self.new_path,
            "change_type": self.change_type,
            "diff_lines": self.diff_lines,
        }


class BlameLine:
    """Blame information for a single line."""

    def __init__(
        self,
        line_number: int,
        commit_oid: str,
        author: str,
        date: datetime,
        summary: str,
    ):
        self.line_number = line_number
        self.commit_oid = commit_oid
        self.author = author
        self.date = date
        self.summary = summary

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "line_number": self.line_number,
            "commit_oid": self.commit_oid,
            "author": self.author,
            "date": self.date.isoformat(),
            "summary": self.summary,
        }


class TaskStatusResult:
    """Result of a task status query."""

    def __init__(
        self,
        task_id: UUID,
        status: TaskStatus,
        operation: GitOperation,
        progress: int = 0,
        message: str | None = None,
        workspace: Path | None = None,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
        created_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ):
        self.task_id = task_id
        self.status = status
        self.operation = operation
        self.progress = progress
        self.message = message
        self.workspace = workspace
        self.result = result
        self.error_message = error_message
        self.created_at = created_at
        self.started_at = started_at
        self.completed_at = completed_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": str(self.task_id),
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "operation": self.operation.value
            if isinstance(self.operation, GitOperation)
            else self.operation,
            "progress": self.progress,
            "message": self.message,
            "workspace": str(self.workspace) if self.workspace else None,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class TaskResult:
    """Result of a task execution."""

    task_id: UUID
    status: TaskStatus
    result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
