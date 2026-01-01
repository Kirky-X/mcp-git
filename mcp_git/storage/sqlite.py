"""
SQLite storage implementation for mcp-git.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import aiosqlite
from loguru import logger

from .models import OperationLog, Task, TaskStatus, Workspace

UTC = timezone.utc


class SqliteStorage:
    """SQLite storage implementation for persisting tasks and workspaces."""

    def __init__(self, database_path: str | Path):
        """
        Initialize SQLite storage.

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = Path(database_path)
        self._connection: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()
        self._slow_query_threshold = 0.1  # 100ms

    @property
    def connection(self) -> aiosqlite.Connection:
        """Get the database connection, raising an error if not initialized."""
        if self._connection is None:
            raise RuntimeError("Database connection not initialized. Call initialize() first.")
        return self._connection

    async def initialize(self) -> None:
        """Initialize database and create tables if needed."""
        async with self._lock:
            # Ensure parent directory exists
            self.database_path.parent.mkdir(parents=True, exist_ok=True)

            self._connection = await aiosqlite.connect(
                str(self.database_path),
                timeout=30.0,
            )

            # Enable foreign keys
            await self.connection.execute("PRAGMA foreign_keys = ON")

            # Set journal mode to WAL for better concurrency
            await self.connection.execute("PRAGMA journal_mode = WAL")

            # Create tables
            await self._create_tables()

            # Create indexes
            await self._create_indexes()

            await self.connection.commit()

        logger.info("Database initialized", path=str(self.database_path))

    async def _create_tables(self) -> None:
        """Create database tables."""
        # Tasks table
        await self.connection.execute("""
                                       CREATE TABLE IF NOT EXISTS tasks
                                       (
                                           id
                                           TEXT
                                           PRIMARY
                                           KEY,
                                           operation
                                           TEXT
                                           NOT
                                           NULL,
                                           status
                                           TEXT
                                           NOT
                                           NULL,
                                           workspace_path
                                           TEXT,
                                           params
                                           TEXT
                                           NOT
                                           NULL,
                                           result
                                           TEXT,
                                           error_message
                                           TEXT,
                                           progress
                                           INTEGER
                                           DEFAULT
                                           0,
                                           created_at
                                           INTEGER
                                           NOT
                                           NULL,
                                           started_at
                                           INTEGER,
                                           completed_at
                                           INTEGER
                                       )
                                       """)

        # Workspaces table
        await self.connection.execute("""
                                       CREATE TABLE IF NOT EXISTS workspaces
                                       (
                                           id
                                           TEXT
                                           PRIMARY
                                           KEY,
                                           path
                                           TEXT
                                           UNIQUE
                                           NOT
                                           NULL,
                                           size_bytes
                                           INTEGER
                                           DEFAULT
                                           0,
                                           last_accessed_at
                                           INTEGER
                                           NOT
                                           NULL,
                                           created_at
                                           INTEGER
                                           NOT
                                           NULL,
                                           metadata
                                           TEXT
                                       )
                                       """)

        # Operation logs table
        await self.connection.execute("""
                                       CREATE TABLE IF NOT EXISTS operation_logs
                                       (
                                           id
                                           INTEGER
                                           PRIMARY
                                           KEY
                                           AUTOINCREMENT,
                                           task_id
                                           TEXT
                                           NOT
                                           NULL,
                                           operation
                                           TEXT
                                           NOT
                                           NULL,
                                           level
                                           TEXT
                                           NOT
                                           NULL,
                                           message
                                           TEXT
                                           NOT
                                           NULL,
                                           timestamp
                                           INTEGER
                                           NOT
                                           NULL,
                                           FOREIGN
                                           KEY
                                       (
                                           task_id
                                       ) REFERENCES tasks
                                       (
                                           id
                                       )
                                           )
                                       """)

    async def _create_indexes(self) -> None:
        """Create database indexes for query optimization."""
        await self.connection.execute("""
                                       CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
                                       """)

        await self.connection.execute("""
                                       CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)
                                       """)

        await self.connection.execute("""
                                       CREATE INDEX IF NOT EXISTS idx_tasks_operation ON tasks(operation)
                                       """)

        await self.connection.execute("""
                                       CREATE INDEX IF NOT EXISTS idx_workspaces_last_accessed ON workspaces(last_accessed_at)
                                       """)

        await self.connection.execute("""
                                       CREATE INDEX IF NOT EXISTS idx_operation_logs_task_id ON operation_logs(task_id)
                                       """)

        await self.connection.execute("""
                                       CREATE INDEX IF NOT EXISTS idx_operation_logs_timestamp ON operation_logs(timestamp)
                                       """)

    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    # Task operations

    async def create_task(self, task: Task) -> Task:
        """
        Create a new task in the database.

        Args:
            task: Task to create

        Returns:
            Created task with generated ID
        """
        async with self._lock:
            now = int(datetime.now(UTC).timestamp())

            await self.connection.execute(
                """
                INSERT INTO tasks (id, operation, status, workspace_path, params,
                                   result, error_message, progress, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(task.id),
                    task.operation.value if hasattr(task.operation, "value") else task.operation,
                    task.status.value if hasattr(task.status, "value") else task.status,
                    str(task.workspace_path) if task.workspace_path else None,
                    json.dumps(task.params),
                    json.dumps(task.result) if task.result else None,
                    task.error_message,
                    task.progress,
                    now,
                ),
            )

            await self.connection.commit()

            # Log task creation (release lock first to avoid deadlock)
            task_id_for_log = task.id
            operation_for_log = task.operation

        # Log outside of the lock to avoid deadlock
        await self.log_operation(
            task_id=task_id_for_log,
            operation=operation_for_log,
            level="info",
            message=f"Task created: {operation_for_log.value if hasattr(operation_for_log, 'value') else operation_for_log}",
        )

        logger.info("Task created", task_id=str(task.id))

        return task

    async def get_task(self, task_id: UUID) -> Task | None:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """
        async with self._lock:
            cursor = await self.connection.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (str(task_id),),
            )

            try:
                row = await cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_task(row)
            finally:
                await cursor.close()

    # nosec: B608 - Field names are validated against ALLOWED_FIELDS whitelist
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
            result: Task result
            error_message: Error message
            workspace_path: Workspace path
            started_at: Start time
            completed_at: Completion time

        Returns:
            True if updated, False if not found
        """
        updates = []
        params: list[Any] = []

        if status is not None:
            updates.append("status = ?")
            params.append(status.value if hasattr(status, "value") else status)

        if progress is not None:
            updates.append("progress = ?")
            params.append(progress)

        if result is not None:
            updates.append("result = ?")
            params.append(json.dumps(result))

        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)

        if workspace_path is not None:
            updates.append("workspace_path = ?")
            params.append(str(workspace_path))

        if started_at is not None:
            updates.append("started_at = ?")
            params.append(int(started_at.timestamp()))

        if completed_at is not None:
            updates.append("completed_at = ?")
            params.append(int(completed_at.timestamp()))

        if not updates:
            return False

        # Whitelist of allowed update fields to prevent SQL injection
        ALLOWED_FIELDS = {
            "status",
            "progress",
            "result",
            "error_message",
            "workspace_path",
            "started_at",
            "completed_at",
        }

        # Validate that all updates are for allowed fields
        for update in updates:
            field_name = update.split(" = ")[0]
            if field_name not in ALLOWED_FIELDS:
                raise ValueError(f"Invalid field for update: {field_name}")

        params.append(str(task_id))

        async with self._lock:
            cursor = await self.connection.execute(  # nosec: B608 - Field names are validated against ALLOWED_FIELDS whitelist
                f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
                params,
            )

            await self.connection.commit()
            updated = cursor.rowcount > 0

            if updated:
                logger.info("Task updated", task_id=str(task_id))

            return updated

    async def delete_task(self, task_id: UUID) -> bool:
        """
        Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            # First delete associated logs to avoid foreign key constraint
            await self.connection.execute(
                "DELETE FROM operation_logs WHERE task_id = ?",
                (str(task_id),),
            )

            # Then delete the task
            cursor = await self.connection.execute(
                "DELETE FROM tasks WHERE id = ?",
                (str(task_id),),
            )

            await self.connection.commit()

            if cursor.rowcount > 0:
                logger.info("Task deleted", task_id=str(task_id))
                return True

            return False

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
            if status:
                cursor = await self.connection.execute(
                    """
                    SELECT *
                    FROM tasks
                    WHERE status = ?
                    ORDER BY created_at DESC LIMIT ?
                    OFFSET ?
                    """,
                    (status.value if hasattr(status, "value") else status, limit, offset),
                )
return [self._row_to_task(row) for row in rows]

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
            placeholders = ",".join(["?"] * len(task_ids))
            cursor = await self.connection.execute(
                f"""
                SELECT *
                FROM tasks
                WHERE id IN ({placeholders})
                ORDER BY created_at DESC
                """,
                [str(tid) for tid in task_ids],
            )
            rows = await cursor.fetchall()
            return [self._row_to_task(row) for row in rows]

    async def get_workspace_info_batch(self, workspace_ids: list[UUID]) -> list[dict[str, Any]]:
        """
        Batch get workspace information for multiple workspaces.

        Args:
            workspace_ids: List of workspace IDs to retrieve

        Returns:
            List of workspace information dictionaries
        """
        if not workspace_ids:
            return []

        async with self._lock:
            placeholders = ",".join(["?"] * len(workspace_ids))
            cursor = await self.connection.execute(
                f"""
                SELECT id, path, size_bytes, created_at, last_accessed_at
                FROM workspaces
                WHERE id IN ({placeholders})
                ORDER BY created_at DESC
                """,
                [str(wid) for wid in workspace_ids],
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "path": row[1],
                    "size_bytes": row[2],
                    "created_at": row[3],
                    "last_accessed_at": row[4],
                }
                for row in rows
            ]

    async def get_pending_tasks(self, limit: int = 10) -> list[Task]:
        """
        Get pending tasks ordered by creation time.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of pending tasks
        """
        async with self._lock:
            cursor = await self.connection.execute(
                """
                SELECT *
                FROM tasks
                WHERE status = ?
                ORDER BY created_at ASC LIMIT ?
                """,
                (TaskStatus.QUEUED.value, limit),
            )

            try:
                rows = await cursor.fetchall()
                return [self._row_to_task(row) for row in rows]
            finally:
                await cursor.close()

    async def cleanup_expired_tasks(self, retention_seconds: int) -> int:
        """
        Delete tasks older than retention period.

        Args:
            retention_seconds: Task retention time in seconds

        Returns:
            Number of deleted tasks
        """
        async with self._lock:
            cutoff = datetime.now(UTC) - timedelta(seconds=retention_seconds)
            cutoff_timestamp = int(cutoff.timestamp())

            cursor = await self.connection.execute(
                """
                DELETE
                FROM tasks
                WHERE status IN (?, ?, ?)
                  AND completed_at < ?
                """,
                (
                    TaskStatus.COMPLETED.value,
                    TaskStatus.FAILED.value,
                    TaskStatus.CANCELLED.value,
                    cutoff_timestamp,
                ),
            )

            await self.connection.commit()
            deleted_count = cursor.rowcount

            if deleted_count > 0:
                logger.info(
                    "Cleaned up expired tasks",
                    count=deleted_count,
                    retention_seconds=retention_seconds,
                )

            return deleted_count

    def _row_to_task(self, row: tuple | aiosqlite.Row) -> Task:
        """Convert database row to Task object."""
        return Task(
            id=UUID(row[0]),
            operation=row[1],
            status=TaskStatus(row[2]),
            workspace_path=Path(row[3]) if row[3] else None,
            params=json.loads(row[4]) if row[4] else {},
            result=json.loads(row[5]) if row[5] else None,
            error_message=row[6],
            progress=row[7] or 0,
            created_at=datetime.fromtimestamp(row[8]) if row[8] else None,
            started_at=datetime.fromtimestamp(row[9]) if row[9] else None,
            completed_at=datetime.fromtimestamp(row[10]) if row[10] else None,
        )

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
            now = int(datetime.now(UTC).timestamp())

            await self.connection.execute(
                """
                INSERT INTO workspaces (id, path, size_bytes, last_accessed_at, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(workspace.id),
                    str(workspace.path),
                    workspace.size_bytes,
                    now,
                    now,
                    json.dumps(workspace.metadata),
                ),
            )

            await self.connection.commit()

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
            cursor = await self.connection.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (str(workspace_id),),
            )

            try:
                row = await cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_workspace(row)
            finally:
                await cursor.close()

    async def get_workspace_by_path(self, path: Path) -> Workspace | None:
        """
        Get a workspace by path.

        Args:
            path: Workspace path

        Returns:
            Workspace if found, None otherwise
        """
        async with self._lock:
            cursor = await self.connection.execute(
                "SELECT * FROM workspaces WHERE path = ?",
                (str(path),),
            )

            try:
                row = await cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_workspace(row)
            finally:
                await cursor.close()

    # nosec: B608 - Field names are validated against ALLOWED_FIELDS whitelist
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
        # Whitelist of allowed update fields to prevent SQL injection
        ALLOWED_FIELDS = {
            "size_bytes",
            "last_accessed_at",
        }

        updates = []
        params: list[Any] = []

        if size_bytes is not None:
            updates.append("size_bytes = ?")
            params.append(size_bytes)

        if last_accessed_at is not None:
            updates.append("last_accessed_at = ?")
            params.append(int(last_accessed_at.timestamp()))

        # Validate that all updates are for allowed fields
        for update in updates:
            field_name = update.split(" = ")[0]
            if field_name not in ALLOWED_FIELDS:
                raise ValueError(f"Invalid field for update: {field_name}")

        if not updates:
            return False

        params.append(str(workspace_id))

        async with self._lock:
            cursor = await self.connection.execute(  # nosec: B608 - Field names are validated against whitelist
                f"UPDATE workspaces SET {', '.join(updates)} WHERE id = ?",
                params,
            )

            await self.connection.commit()
            return cursor.rowcount > 0

    async def delete_workspace(self, workspace_id: UUID) -> bool:
        """
        Delete a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            cursor = await self.connection.execute(
                "DELETE FROM workspaces WHERE id = ?",
                (str(workspace_id),),
            )

            await self.connection.commit()
            return cursor.rowcount > 0

    async def list_workspaces(
        self,
        limit: int = 100,
        order_by_accessed: bool = True,
    ) -> list[Workspace]:
        """
        List workspaces.

        Args:
            limit: Maximum number of workspaces
            order_by_accessed: Order by last accessed time

        Returns:
            List of workspaces
        """
        async with self._lock:
            if order_by_accessed:
                cursor = await self.connection.execute(
                    """
                    SELECT *
                    FROM workspaces
                    ORDER BY last_accessed_at DESC LIMIT ?
                    """,
                    (limit,),
                )
            else:
                cursor = await self.connection.execute(
                    """
                    SELECT *
                    FROM workspaces
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (limit,),
                )

            try:
                rows = await cursor.fetchall()
                return [self._row_to_workspace(row) for row in rows]
            finally:
                await cursor.close()

    async def get_oldest_workspaces(self, count: int = 10) -> list[Workspace]:
        """
        Get oldest workspaces by access time (for LRU cleanup).

        Args:
            count: Number of workspaces to return

        Returns:
            List of oldest workspaces
        """
        async with self._lock:
            cursor = await self.connection.execute(
                """
                SELECT *
                FROM workspaces
                ORDER BY last_accessed_at ASC LIMIT ?
                """,
                (count,),
            )

            try:
                rows = await cursor.fetchall()
                return [self._row_to_workspace(row) for row in rows]
            finally:
                await cursor.close()

    async def get_workspace_total_size(self) -> int:
        """
        Get total size of all workspaces.

        Returns:
            Total size in bytes
        """
        async with self._lock:
            cursor = await self.connection.execute("SELECT SUM(size_bytes) FROM workspaces")

            try:
                result = await cursor.fetchone()
                return result[0] if result and result[0] else 0
            finally:
                await cursor.close()

    def _row_to_workspace(self, row: tuple | aiosqlite.Row) -> Workspace:
        """Convert database row to Workspace object."""
        return Workspace(
            id=UUID(row[0]),
            path=Path(row[1]),
            size_bytes=row[2] or 0,
            last_accessed_at=datetime.fromtimestamp(row[3]) if row[3] else None,
            created_at=datetime.fromtimestamp(row[4]) if row[4] else None,
            metadata=json.loads(row[5]) if row[5] else {},
        )

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
            await self.connection.execute(
                """
                INSERT INTO operation_logs (task_id, operation, level, message, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(task_id),
                    operation.value if hasattr(operation, "value") else operation,
                    level,
                    message,
                    int(datetime.now(UTC).timestamp()),
                ),
            )

            await self.connection.commit()

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
            cursor = await self.connection.execute(
                """
                SELECT *
                FROM operation_logs
                WHERE task_id = ?
                ORDER BY timestamp DESC
                    LIMIT ?
                """,
                (str(task_id), limit),
            )

            try:
                rows = await cursor.fetchall()
                return [self._row_to_operation_log(row) for row in rows]
            finally:
                await cursor.close()

    def _row_to_operation_log(self, row: tuple | aiosqlite.Row) -> OperationLog:
        """Convert database row to OperationLog object."""
        return OperationLog(
            id=row[0],
            task_id=UUID(row[1]),
            operation=row[2],
            level=row[3],
            message=row[4],
            timestamp=datetime.fromtimestamp(row[5]) if row[5] else None,
        )
