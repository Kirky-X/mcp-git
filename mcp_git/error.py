"""
Error type definitions and handling for mcp-git.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


class ErrorCategory(str, Enum):
    """Error category for classification."""

    PARAMETER_VALIDATION = "PARAMETER_VALIDATION"
    GIT_OPERATION = "GIT_OPERATION"
    REPOSITORY_ACCESS = "REPOSITORY_ACCESS"
    NETWORK = "NETWORK"
    SYSTEM = "SYSTEM"
    TASK_EXECUTION = "TASK_EXECUTION"


class ErrorCode(int, Enum):
    """Error codes for mcp-git.

    Format:
    - 40001-40099: Parameter validation errors
    - 40100-40199: Git operation errors
    - 40200-40299: Repository access errors
    - 40300-40399: Network errors
    - 40400-40499: System errors
    - 40500-40599: Task execution errors
    """

    # Parameter validation errors (40001-40099)
    INVALID_REPO_PATH = 40001
    INVALID_REMOTE_URL = 40002
    INVALID_BRANCH_NAME = 40003
    INVALID_COMMIT_MESSAGE = 40004
    INVALID_TIMEOUT = 40005
    INVALID_TARGET_PATH = 40006
    MISSING_REQUIRED_PARAM = 40007
    PARAMETER_CONFLICT = 40008

    # Git operation errors (40100-40199)
    GIT_COMMAND_FAILED = 40100
    GIT_NOT_A_REPO = 40101
    GIT_NO_CHANGES = 40102
    GIT_DETACHED_HEAD = 40103
    GIT_MERGE_CONFLICT = 40104
    GIT_REBASE_CONFLICT = 40105
    GIT_UP_TO_DATE = 40106
    GIT_PUSH_REJECTED = 40107

    # Repository access errors (40200-40299)
    REPO_ACCESS_DENIED = 40200
    REPO_NOT_FOUND = 40201
    REPO_LOCKED = 40202

    # Network errors (40300-40399)
    NETWORK_ERROR = 40300
    TIMEOUT = 40301
    AUTH_FAILED = 40302

    # System errors (40400-40499)
    SYSTEM_ERROR = 40400
    PERMISSION_DENIED = 40401
    RESOURCE_EXHAUSTED = 40402

    # Task execution errors (40500-40599)
    TASK_NOT_FOUND = 40501
    TASK_CANCELLED = 40502
    TASK_TIMEOUT = 40503
    TASK_EXECUTOR_ERROR = 40504


@dataclass
class ErrorContext:
    """Error context information."""

    operation: str
    repo_path: Path | None = None
    branch: str | None = None
    commit: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: str(uuid4()))


class McpGitError(Exception):
    """Base exception for mcp-git errors."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: str | None = None,
        suggestion: str | None = None,
        context: ErrorContext | None = None,
    ):
        self.code = code
        self.message = message
        self.details = details
        self.suggestion = suggestion
        self.context = context or ErrorContext(operation="unknown")
        self.timestamp = str(uuid4())

        super().__init__(self.message)

    @property
    def category(self) -> ErrorCategory:
        """Get error category based on code range."""
        code_value = self.code.value

        if 40001 <= code_value <= 40099:
            return ErrorCategory.PARAMETER_VALIDATION
        elif 40100 <= code_value <= 40199:
            return ErrorCategory.GIT_OPERATION
        elif 40200 <= code_value <= 40299:
            return ErrorCategory.REPOSITORY_ACCESS
        elif 40300 <= code_value <= 40399:
            return ErrorCategory.NETWORK
        elif 40400 <= code_value <= 40499:
            return ErrorCategory.SYSTEM
        else:
            return ErrorCategory.TASK_EXECUTION

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        return {
            "code": self.code.value,
            "name": self.code.name,
            "message": self.message,
            "details": self.details,
            "suggestion": self.suggestion,
            "context": {
                "operation": self.context.operation,
                "repo_path": str(self.context.repo_path) if self.context.repo_path else None,
                "branch": self.context.branch,
                "commit": self.context.commit,
                "parameters": self.context.parameters,
            },
            "timestamp": self.timestamp,
            "category": self.category.value,
        }

    def to_user_message(self) -> str:
        """Get user-friendly error message."""
        msg = self.message
        if self.suggestion:
            msg += f"\n\nSuggestion: {self.suggestion}"
        return msg


class ParameterValidationError(McpGitError):
    """Raised when parameter validation fails."""

    def __init__(
        self,
        message: str,
        details: str | None = None,
        suggestion: str | None = None,
        context: ErrorContext | None = None,
    ):
        super().__init__(
            code=ErrorCode.INVALID_REPO_PATH,
            message=message,
            details=details,
            suggestion=suggestion,
            context=context,
        )


class GitOperationError(McpGitError):
    """Raised when a Git operation fails."""

    def __init__(
        self,
        message: str,
        details: str | None = None,
        suggestion: str | None = None,
        context: ErrorContext | None = None,
    ):
        super().__init__(
            code=ErrorCode.GIT_COMMAND_FAILED,
            message=message,
            details=details,
            suggestion=suggestion,
            context=context,
        )


class RepositoryNotFoundError(McpGitError):
    """Raised when repository is not found."""

    def __init__(
        self,
        path: str,
        context: ErrorContext | None = None,
    ):
        ctx = context or ErrorContext(operation="repository_access")
        ctx.repo_path = Path(path) if isinstance(path, str) else path

        super().__init__(
            code=ErrorCode.REPO_NOT_FOUND,
            message=f"Repository not found: {path}",
            details=f"Cannot find repository at {path}",
            suggestion="Check the repository path and ensure it exists",
            context=ctx,
        )


class AuthenticationError(McpGitError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: str | None = None,
        context: ErrorContext | None = None,
    ):
        super().__init__(
            code=ErrorCode.AUTH_FAILED,
            message=message,
            details=details,
            suggestion="Check your credentials and ensure they have the required permissions",
            context=context,
        )


class MergeConflictError(McpGitError):
    """Raised when a merge conflict occurs."""

    def __init__(
        self,
        conflicted_files: list[str],
        context: ErrorContext | None = None,
    ):
        ctx = context or ErrorContext(operation="merge")

        super().__init__(
            code=ErrorCode.GIT_MERGE_CONFLICT,
            message=f"Merge conflict in files: {', '.join(conflicted_files)}",
            details=f"Conflicted files: {conflicted_files}",
            suggestion="Resolve the conflicts manually, then stage and commit the resolution",
            context=ctx,
        )


class TaskNotFoundError(McpGitError):
    """Raised when a task is not found."""

    def __init__(
        self,
        task_id: str,
        context: ErrorContext | None = None,
    ):
        ctx = context or ErrorContext(operation="task_query")
        ctx.parameters["task_id"] = task_id

        super().__init__(
            code=ErrorCode.TASK_NOT_FOUND,
            message=f"Task not found: {task_id}",
            details=f"Cannot find task with ID {task_id}",
            suggestion="Verify the task_id is correct and the task hasn't expired",
            context=ctx,
        )


class TaskCancelledError(McpGitError):
    """Raised when a task is cancelled."""

    def __init__(
        self,
        task_id: str,
        context: ErrorContext | None = None,
    ):
        ctx = context or ErrorContext(operation="task_cancel")
        ctx.parameters["task_id"] = task_id

        super().__init__(
            code=ErrorCode.TASK_CANCELLED,
            message=f"Task was cancelled: {task_id}",
            details=f"Task {task_id} was cancelled before completion",
            suggestion="Create a new task to continue the operation",
            context=ctx,
        )


class TaskTimeoutError(McpGitError):
    """Raised when a task times out."""

    def __init__(
        self,
        task_id: str,
        timeout_seconds: int,
        context: ErrorContext | None = None,
    ):
        ctx = context or ErrorContext(operation="task_execution")
        ctx.parameters["task_id"] = task_id
        ctx.parameters["timeout_seconds"] = timeout_seconds

        super().__init__(
            code=ErrorCode.TASK_TIMEOUT,
            message=f"Task timed out after {timeout_seconds} seconds",
            details=f"Task {task_id} exceeded the configured timeout",
            suggestion="Increase the timeout value or simplify the operation",
            context=ctx,
        )


def is_retryable_error(error: McpGitError) -> bool:
    """Check if an error is retryable."""
    retryable_codes = {
        ErrorCode.NETWORK_ERROR,
        ErrorCode.TIMEOUT,
        ErrorCode.AUTH_FAILED,
        ErrorCode.GIT_PUSH_REJECTED,
    }
    return error.code in retryable_codes


def get_user_friendly_message(error: McpGitError) -> str:
    """Get a user-friendly message for an error."""
    message_map = {
        ErrorCode.REPO_NOT_FOUND: "The repository was not found. Please check the URL or path.",
        ErrorCode.AUTH_FAILED: "Authentication failed. Please check your credentials.",
        ErrorCode.GIT_MERGE_CONFLICT: "There are merge conflicts that need to be resolved.",
        ErrorCode.TIMEOUT: "The operation timed out. Please try again.",
        ErrorCode.NETWORK_ERROR: "A network error occurred. Please check your connection.",
    }

    base_message = message_map.get(error.code, "An error occurred. Please try again.")

    if error.suggestion:
        return f"{base_message}\n\nSuggestion: {error.suggestion}"

    return base_message
