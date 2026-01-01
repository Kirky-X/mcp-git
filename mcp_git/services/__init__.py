"""
Services module for mcp-git.

This module provides the microservices architecture implementation.
"""

from mcp_git.services.git_service import GitService
from mcp_git.services.service_interface import (
    AuditServiceInterface,
    GitServiceInterface,
    MetricsServiceInterface,
    StorageServiceInterface,
    TaskServiceInterface,
    WorkspaceServiceInterface,
)
from mcp_git.services.storage_service import StorageService
from mcp_git.services.task_service import TaskService
from mcp_git.services.workspace_service import WorkspaceService

__all__ = [
    "GitService",
    "TaskService",
    "StorageService",
    "WorkspaceService",
    "GitServiceInterface",
    "TaskServiceInterface",
    "StorageServiceInterface",
    "WorkspaceServiceInterface",
    "MetricsServiceInterface",
    "AuditServiceInterface",
]
