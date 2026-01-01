"""
Configuration management module for mcp-git.
"""

import os
import tempfile
from dataclasses import field
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class CleanupStrategy(str, Enum):
    """Workspace cleanup strategy."""

    LRU = "lru"  # Least Recently Used
    FIFO = "fifo"  # First In First Out


class TransportType(str, Enum):
    """Server transport type."""

    STDIO = "stdio"
    SSE = "sse"
    WEBSOCKET = "websocket"


class WorkspaceConfig(BaseModel):
    """Workspace configuration."""

    path: Path = Field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "mcp-git" / "workspaces"
    )
    max_size_bytes: int = Field(default=10 * 1024 * 1024 * 1024, gt=0)  # 10GB
    retention_seconds: int = Field(default=3600, gt=0)  # 1 hour
    cleanup_strategy: CleanupStrategy = CleanupStrategy.LRU

    @field_validator("path")
    @classmethod
    def path_must_be_valid(cls, v: Path) -> Path:
        """Validate path is safe and can be created if needed."""
        # Resolve to absolute path
        resolved = v.resolve()

        # Check for path traversal attempts
        if ".." in str(resolved) and not str(resolved).startswith(str(v.resolve())):
            raise ValueError(f"Invalid path with potential traversal: {v}")

        # Check if path exists or parent is writable
        if resolved.exists():
            if not resolved.is_dir():
                raise ValueError(f"Path exists but is not a directory: {resolved}")
            # Check if directory is writable
            if not os.access(resolved, os.W_OK):
                raise ValueError(f"Directory is not writable: {resolved}")
        else:
            # Check if parent directory exists and is writable
            parent = resolved.parent
            if not parent.exists():
                # Try to create parent directories if possible
                try:
                    parent.mkdir(parents=True, exist_ok=True)
                except (OSError, PermissionError) as e:
                    # Provide more helpful error message
                    raise ValueError(
                        f"Cannot create parent directory '{parent}'. "
                        f"Please ensure the path exists and is writable. Error: {e}"
                    ) from e
            if not os.access(parent, os.W_OK):
                raise ValueError(f"Parent directory is not writable: {parent}")

        return resolved


class DatabaseConfig(BaseModel):
    """Database configuration."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path = Field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "mcp-git" / "database" / "mcp-git.db"
    )
    max_size_bytes: int = Field(default=100 * 1024 * 1024, gt=0, le=10 * 1024 * 1024 * 1024)  # 100MB to 10GB
    task_retention_seconds: int = Field(default=3600, gt=0, le=86400)  # 1 hour to 24 hours

    @field_validator("path")
    @classmethod
    def path_must_be_valid(cls, v: Path) -> Path:
        """Validate database path."""
        resolved = v.resolve()

        # Ensure parent directory can be created
        parent = resolved.parent
        if not parent.exists():
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                raise ValueError(
                    f"Cannot create database directory '{parent}'. Error: {e}"
                ) from e

        return resolved


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = Field(default="127.0.0.1", pattern=r'^[a-zA-Z0-9\.\-]+$')
    port: int = Field(default=3001, ge=1, le=65535)
    transport: TransportType = TransportType.STDIO


class ExecutionConfig(BaseModel):
    """Execution configuration."""

    max_concurrent_tasks: int = Field(default=10, ge=1, le=100)
    max_retries: int = Field(default=3, ge=0, le=10)
    task_timeout_seconds: int = Field(default=300, ge=1, le=3600)  # 5 minutes to 1 hour
    worker_count: int = Field(default=4, ge=1, le=20)


class Config(BaseModel):
    """Main configuration for mcp-git server."""

    model_config = ConfigDict(extra="ignore")

    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)

    # Git configuration - use SecretStr for sensitive data
    git_token: SecretStr | None = Field(default=None, exclude=True)
    default_clone_depth: int = Field(default=1, ge=1)

    # Logging configuration
    log_level: str = Field(default="INFO")


def load_config() -> Config:
    """
    Load configuration from environment variables.

    Returns:
        Config object with loaded settings
    """
    config = Config()

    # Workspace configuration
    workspace_path = os.getenv("MCP_GIT_WORKSPACE_PATH")
    if workspace_path:
        config.workspace = WorkspaceConfig(path=Path(workspace_path))

    # Database configuration
    database_path = os.getenv("MCP_GIT_DATABASE_PATH")
    if database_path:
        config.database = DatabaseConfig(path=Path(database_path))

    # Server configuration
    server_port = os.getenv("MCP_GIT_SERVER_PORT")
    if server_port:
        config.server = ServerConfig(port=int(server_port))

    server_host = os.getenv("MCP_GIT_SERVER_HOST")
    if server_host:
        config.server.host = server_host

    # Git configuration - use SecretStr for sensitive data
    git_token = os.getenv("GIT_TOKEN") or os.getenv("MCP_GIT_GIT_TOKEN")
    if git_token:
        config.git_token = SecretStr(git_token)

    clone_depth = os.getenv("MCP_GIT_DEFAULT_CLONE_DEPTH")
    if clone_depth:
        config.default_clone_depth = int(clone_depth)

    # Logging configuration
    log_level = os.getenv("MCP_GIT_LOG_LEVEL")
    if log_level:
        config.log_level = log_level.upper()

    # Execution configuration
    max_concurrent = os.getenv("MCP_GIT_MAX_CONCURRENT_TASKS")
    if max_concurrent:
        config.execution = ExecutionConfig(max_concurrent_tasks=int(max_concurrent))

    task_timeout = os.getenv("MCP_GIT_TASK_TIMEOUT")
    if task_timeout:
        config.execution.task_timeout_seconds = int(task_timeout)

    worker_count = os.getenv("MCP_GIT_WORKER_COUNT")
    if worker_count:
        config.execution.worker_count = int(worker_count)

    return config


def get_default_config() -> Config:
    """Get default configuration."""
    return Config()
