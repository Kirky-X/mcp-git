"""
Services module for mcp-git.

This module provides the microservices architecture interfaces.
"""

from mcp_git.services.service_interface import (
    AuditServiceInterface,
    GitServiceInterface,
    MetricsServiceInterface,
    StorageServiceInterface,
    TaskServiceInterface,
    WorkspaceServiceInterface,
)

__all__ = [
    "GitServiceInterface",
    "TaskServiceInterface",
    "StorageServiceInterface",
    "WorkspaceServiceInterface",
    "MetricsServiceInterface",
    "AuditServiceInterface",
]
