"""
SQLite storage implementation for mcp-git using SQLAlchemy ORM.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import OperationLog, Task, TaskStatus, Workspace
from .orm_models import Base, OperationLogORM, TaskORM, WorkspaceORM

UTC = timezone.utc


class SqliteStorage:
    """SQLite storage implementation using SQLAlchemy ORM."""

    def __init__(self, database_path: str | Path):
        """
        Initialize SQLite storage.

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = Path(database_path)
        self._engine: Any = None
        self._async_session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            None, expire_on_commit=False, class_=AsyncSession
        )
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize database and create tables if needed."""
        async with self._lock:
            # Ensure parent directory exists
            self.database_path.parent.mkdir(parents=True, exist_ok=True)

            # Create async engine with SQLite-specific settings
            database_url = f"sqlite+aiosqlite:///{self.database_path}"
            self._engine = create_async_engine(
                database_url,
                echo=False,
                future=True,
                # SQLite-specific settings (SQLite uses NullPool)
                pool_pre_ping=True,  # Verify connections before use
                connect_args={
                    "check_same_thread": False,  # SQLite-specific
                },
            )

            # Create async session maker
            self._async_session_maker = async_sessionmaker(
                self._engine,
                expire_on_commit=False,
                class_=AsyncSession,
            )

            # Create tables
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("Database initialized", path=str(self.database_path))

    async def close(self) -> None:
        """Close database connection."""
        async with self._lock:
            if self._engine:
                await self._engine.dispose()
                self._engine = None
                logger.info("Database connection closed")

    def _get_session_maker(self) -> async_sessionmaker[AsyncSession]:
        """Get session maker with type assertion."""
        if self._async_session_maker is None:
            raise RuntimeError("Storage not initialized")
        return self._async_session_maker

    async def __aenter__(self) -> "SqliteStorage":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    # Task operations

    async def create_task(self, task: Task) -> Task:
        """
        Create a new task in the database.

        Args:
            task: Task to create

        Returns:
            Created task with generated ID
        """
        assert self._async_session_maker is not None
        async with self._lock:
            async with self._async_session_maker() as session:
                task_orm = TaskORM.from_task(task)
                session.add(task_orm)
                await session.commit()
                await session.refresh(task_orm)

                logger.info("Task created", task_id=str(task.id))
                return task

        # Log task creation outside of lock
        await self.log_operation(
            task_id=task.id,
            operation=task.operation,
            level="info",
            message=f"Task created: {task.operation.value}",
        )

    async def get_task(self, task_id: UUID) -> Task | None:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                result = await session.execute(
                    select(TaskORM).where(TaskORM.id == str(task_id))
                )
                task_orm = result.scalar_one_or_none()
                if task_orm is None:
                    return None
                return task_orm.to_task()

    async def update_task(
        self,
        task_id: UUID,
        status: TaskStatus | None = None,
        progress: int | None = None,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
        workspace_path: Path | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> bool:
        """
        Update a task.

        Args:
            task_id: Task ID
            status: New status
            progress: New progress
            result: New result
            error_message: New error message
            workspace_path: New workspace path
            started_at: New start time
            completed_at: New completion time

        Returns:
            True if updated, False if not found
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                query_result = await session.execute(
                    select(TaskORM).where(TaskORM.id == str(task_id))
                )
                task_orm = query_result.scalar_one_or_none()

                if task_orm is None:
                    return False

                if status is not None:
                    task_orm.status = status.value
                if progress is not None:
                    task_orm.progress = progress
                if result is not None:
                    task_orm.result = json.dumps(result) if result else None
                if error_message is not None:
                    task_orm.error_message = error_message
                if workspace_path is not None:
                    task_orm.workspace_path = str(workspace_path)
                if started_at is not None:
                    task_orm.started_at = int(started_at.timestamp())
                if completed_at is not None:
                    task_orm.completed_at = int(completed_at.timestamp())

                await session.commit()
                return True

    async def delete_task(self, task_id: UUID) -> bool:
        """
        Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                result = await session.execute(
                    select(TaskORM).where(TaskORM.id == str(task_id))
                )
                task_orm = result.scalar_one_or_none()

                if task_orm is None:
                    return False

                await session.delete(task_orm)
                await session.commit()
                return True

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
            limit: Maximum number of tasks to return
            offset: Offset for pagination

        Returns:
            List of tasks
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                query = select(TaskORM)

                if status:
                    query = query.where(TaskORM.status == status.value)

                query = query.order_by(TaskORM.created_at.desc()).limit(limit).offset(offset)

                result = await session.execute(query)
                task_orms = result.scalars().all()
                return [task_orm.to_task() for task_orm in task_orms]

    async def get_tasks_batch(self, task_ids: list[UUID]) -> list[Task]:
        """
        Batch get multiple tasks by IDs to avoid N+1 queries.

        Args:
            task_ids: List of task IDs to retrieve

        Returns:
            List of tasks
        """
        if not task_ids:
            return []

        async with self._lock:
            async with self._async_session_maker() as session:
                result = await session.execute(
                    select(TaskORM)
                    .where(TaskORM.id.in_([str(tid) for tid in task_ids]))
                    .order_by(TaskORM.created_at.desc())
                )
                task_orms = result.scalars().all()
                return [task_orm.to_task() for task_orm in task_orms]

    async def get_workspace_info_batch(self, workspace_ids: list[UUID]) -> list[dict[str, Any]]:
        """
        Batch get workspace info for multiple workspaces.

        Args:
            workspace_ids: List of workspace IDs

        Returns:
            List of workspace info dictionaries
        """
        if not workspace_ids:
            return []

        async with self._lock:
            async with self._async_session_maker() as session:
                result = await session.execute(
                    select(WorkspaceORM)
                    .where(WorkspaceORM.id.in_([str(wid) for wid in workspace_ids]))
                )
                workspace_orms = result.scalars().all()
                return [
                    {
                        "id": ws.id,
                        "path": ws.path,
                        "size_bytes": ws.size_bytes,
                        "last_accessed_at": datetime.fromtimestamp(ws.last_accessed_at).isoformat()
                        if ws.last_accessed_at
                        else None,
                        "created_at": datetime.fromtimestamp(ws.created_at).isoformat(),
                    }
                    for ws in workspace_orms
                ]

    async def get_pending_tasks(self, limit: int = 10) -> list[Task]:
        """
        Get pending tasks for execution.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of pending tasks
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                result = await session.execute(
                    select(TaskORM)
                    .where(TaskORM.status == TaskStatus.QUEUED.value)
                    .order_by(TaskORM.created_at.asc())
                    .limit(limit)
                )
                task_orms = result.scalars().all()
                return [task_orm.to_task() for task_orm in task_orms]

    async def cleanup_expired_tasks(self, retention_seconds: int) -> int:
        """
        Clean up expired tasks.

        Args:
            retention_seconds: Retention period in seconds

        Returns:
            Number of tasks cleaned up
        """
        from datetime import timedelta

        cutoff_timestamp = int((datetime.now(UTC) - timedelta(seconds=retention_seconds)).timestamp())

        async with self._lock:
            async with self._async_session_maker() as session:
                result = await session.execute(
                    select(TaskORM).where(TaskORM.created_at < cutoff_timestamp)
                )
                task_orms = result.scalars().all()

                for task_orm in task_orms:
                    await session.delete(task_orm)

                await session.commit()

                logger.info(
                    "Cleaned up expired tasks",
                    count=len(task_orms),
                    retention_seconds=retention_seconds,
                )
                return len(task_orms)

    # Workspace operations

    async def create_workspace(self, workspace: Workspace) -> Workspace:
        """
        Create a new workspace.

        Args:
            workspace: Workspace to create

        Returns:
            Created workspace
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                workspace_orm = WorkspaceORM.from_workspace(workspace)
                session.add(workspace_orm)
                await session.commit()
                await session.refresh(workspace_orm)

                logger.info("Workspace created", workspace_id=str(workspace.id))
                return workspace

    async def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        """
        Get a workspace by ID.

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace if found, None otherwise
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                result = await session.execute(
                    select(WorkspaceORM).where(WorkspaceORM.id == str(workspace_id))
                )
                workspace_orm = result.scalar_one_or_none()
                if workspace_orm is None:
                    return None
                return workspace_orm.to_workspace()

    async def get_workspace_by_path(self, path: Path) -> Workspace | None:
        """
        Get a workspace by path.

        Args:
            path: Workspace path

        Returns:
            Workspace if found, None otherwise
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                result = await session.execute(
                    select(WorkspaceORM).where(WorkspaceORM.path == str(path))
                )
                workspace_orm = result.scalar_one_or_none()
                if workspace_orm is None:
                    return None
                return workspace_orm.to_workspace()

    async def update_workspace(
        self,
        workspace_id: UUID,
        size_bytes: int | None = None,
        last_accessed_at: datetime | None = None,
    ) -> bool:
        """
        Update a workspace.

        Args:
            workspace_id: Workspace ID
            size_bytes: New size in bytes
            last_accessed_at: New access time

        Returns:
            True if updated, False if not found
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                result = await session.execute(
                    select(WorkspaceORM).where(WorkspaceORM.id == str(workspace_id))
                )
                workspace_orm = result.scalar_one_or_none()

                if workspace_orm is None:
                    return False

                if size_bytes is not None:
                    workspace_orm.size_bytes = size_bytes
                if last_accessed_at is not None:
                    workspace_orm.last_accessed_at = int(last_accessed_at.timestamp())

                await session.commit()
                return True

    async def delete_workspace(self, workspace_id: UUID) -> bool:
        """
        Delete a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                result = await session.execute(
                    select(WorkspaceORM).where(WorkspaceORM.id == str(workspace_id))
                )
                workspace_orm = result.scalar_one_or_none()

                if workspace_orm is None:
                    return False

                await session.delete(workspace_orm)
                await session.commit()
                return True

    async def list_workspaces(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Workspace]:
        """
        List workspaces.

        Args:
            limit: Maximum number of workspaces to return
            offset: Offset for pagination

        Returns:
            List of workspaces
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                query = (
                    select(WorkspaceORM)
                    .order_by(WorkspaceORM.last_accessed_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
                result = await session.execute(query)
                workspace_orms = result.scalars().all()
                return [workspace_orm.to_workspace() for workspace_orm in workspace_orms]

    async def get_oldest_workspaces(self, count: int = 10) -> list[Workspace]:
        """
        Get oldest workspaces by access time (for LRU cleanup).

        Args:
            count: Number of workspaces to return

        Returns:
            List of oldest workspaces
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                query = (
                    select(WorkspaceORM)
                    .order_by(WorkspaceORM.last_accessed_at.asc())
                    .limit(count)
                )
                result = await session.execute(query)
                workspace_orms = result.scalars().all()
                return [workspace_orm.to_workspace() for workspace_orm in workspace_orms]

    async def get_workspace_total_size(self) -> int:
        """
        Get total size of all workspaces.

        Returns:
            Total size in bytes
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                from sqlalchemy import func

                result = await session.execute(
                    select(func.sum(WorkspaceORM.size_bytes))
                )
                total = result.scalar()
                return total if total else 0

    # Operation log operations

    async def log_operation(
        self,
        task_id: UUID,
        operation: Any,
        level: str,
        message: str,
    ) -> None:
        """
        Log an operation.

        Args:
            task_id: Task ID
            operation: Operation type
            level: Log level (info, warn, error)
            message: Log message
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                log_orm = OperationLogORM(
                    task_id=str(task_id),
                    operation=operation.value if hasattr(operation, "value") else operation,
                    level=level,
                    message=message,
                    timestamp=int(datetime.now(UTC).timestamp()),
                )
                session.add(log_orm)
                await session.commit()

    async def get_operation_logs(
        self,
        task_id: UUID,
        limit: int = 100,
    ) -> list[OperationLog]:
        """
        Get operation logs for a task.

        Args:
            task_id: Task ID
            limit: Maximum number of logs

        Returns:
            List of operation logs
        """
        async with self._lock:
            async with self._async_session_maker() as session:
                query = (
                    select(OperationLogORM)
                    .where(OperationLogORM.task_id == str(task_id))
                    .order_by(OperationLogORM.timestamp.desc())
                    .limit(limit)
                )
                result = await session.execute(query)
                log_orms = result.scalars().all()
                return [log_orm.to_operation_log() for log_orm in log_orms]
