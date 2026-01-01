"""
Security audit logging for mcp-git.

This module provides comprehensive audit logging for security-relevant operations
including Git operations, credential access, and security events.
"""

import json
import logging
from collections import deque
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Git operations
    GIT_CLONE = "git_clone"
    GIT_PUSH = "git_push"
    GIT_PULL = "git_pull"
    GIT_FETCH = "git_fetch"
    GIT_COMMIT = "git_commit"
    GIT_CHECKOUT = "git_checkout"
    GIT_MERGE = "git_merge"
    GIT_REBASE = "git_rebase"

    # Credential operations
    CREDENTIAL_LOADED = "credential_loaded"
    CREDENTIAL_ACCESSED = "credential_accessed"
    CREDENTIAL_CLEARED = "credential_cleared"
    CREDENTIAL_ROTATED = "credential_rotated"

    # Security events
    AUTH_FAILED = "auth_failed"
    AUTH_SUCCEEDED = "auth_succeeded"
    PERMISSION_DENIED = "permission_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # System events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIG_CHANGED = "config_changed"

    # Data access
    WORKSPACE_ALLOCATED = "workspace_allocated"
    WORKSPACE_RELEASED = "workspace_released"
    WORKSPACE_ACCESSED = "workspace_accessed"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEvent:
    """Represents a single audit event."""

    def __init__(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: str | None = None,
        workspace_id: str | None = None,
        details: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize an audit event.

        Args:
            event_type: Type of the audit event
            severity: Severity level of the event
            user_id: Optional user identifier
            workspace_id: Optional workspace identifier
            details: Detailed information about the event
            metadata: Additional metadata
        """
        self.event_id = str(uuid4())
        self.timestamp = datetime.now().isoformat()
        self.event_type = event_type
        self.severity = severity
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.details = details or {}
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert audit event to dictionary."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "details": self.details,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Convert audit event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """Main audit logger for security events."""

    def __init__(
        self,
        log_path: Path | None = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5,
        max_memory_events: int = 1000,
    ):
        """
        Initialize the audit logger.

        Args:
            log_path: Path to the audit log file
            max_file_size: Maximum size of a single log file in bytes
            backup_count: Number of backup files to keep
            max_memory_events: Maximum number of events to keep in memory
        """
        self.log_path = log_path
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.max_memory_events = max_memory_events
        # Use deque for O(1) pop operations instead of list's O(n)
        self._in_memory_events: deque[dict[str, Any]] = deque(maxlen=max_memory_events)

        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(self, event: AuditEvent) -> None:
        """
        Log an audit event.

        Args:
            event: The audit event to log
        """
        # Add to in-memory events (deque automatically handles max length)
        event_dict = event.to_dict()
        self._in_memory_events.append(event_dict)

        # Write to file if configured
        if self.log_path:
            self._write_to_file(event_dict)

        # Log to application logger
        log_level = self._get_log_level(event.severity)
        logger.log(
            log_level,
            f"Audit event: {event.event_type.value}",
            extra={"audit_event": event_dict},
        )

    def _write_to_file(self, event_dict: dict[str, Any]) -> None:
        """
        Write audit event to file.

        Args:
            event_dict: Event dictionary to write
        """
        if not self.log_path:
            return

        try:
            # Check if file rotation is needed
            if self.log_path.exists() and self.log_path.stat().st_size >= self.max_file_size:
                self._rotate_log_file()

            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_dict, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit event to file: {e}")

    def _rotate_log_file(self) -> None:
        """Rotate the audit log file."""
        if not self.log_path:
            return

        try:
            # Shift backup files
            for i in range(self.backup_count - 1, 0, -1):
                old_backup = self.log_path.with_suffix(f".log.{i}")
                new_backup = self.log_path.with_suffix(f".log.{i + 1}")
                if old_backup.exists():
                    old_backup.rename(new_backup)

            # Move current log to .log.1
            if self.log_path.exists():
                self.log_path.rename(self.log_path.with_suffix(".log.1"))

            logger.info(f"Rotated audit log file: {self.log_path}")
        except Exception as e:
            logger.error(f"Failed to rotate audit log file: {e}")

    def _get_log_level(self, severity: AuditSeverity) -> int:
        """
        Get Python logging level from severity.

        Args:
            severity: Audit severity level

        Returns:
            Python logging level
        """
        severity_map = {
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.ERROR: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL,
        }
        return severity_map.get(severity, logging.INFO)

    def query_events(
        self,
        event_type: AuditEventType | None = None,
        severity: AuditSeverity | None = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Query audit events from memory.

        Args:
            event_type: Filter by event type
            severity: Filter by severity
            user_id: Filter by user ID
            workspace_id: Filter by workspace ID
            start_time: Filter events after this time
            end_time: Filter events before this time
            limit: Maximum number of events to return

        Returns:
            List of matching audit events
        """
        events = self._in_memory_events

        # Apply filters
        if event_type:
            events = [e for e in events if e["event_type"] == event_type.value]

        if severity:
            events = [e for e in events if e["severity"] == severity.value]

        if user_id:
            events = [e for e in events if e["user_id"] == user_id]

        if workspace_id:
            events = [e for e in events if e["workspace_id"] == workspace_id]

        if start_time:
            start_str = start_time.isoformat()
            events = [e for e in events if e["timestamp"] >= start_str]

        if end_time:
            end_str = end_time.isoformat()
            events = [e for e in events if e["timestamp"] <= end_str]

        # Sort by timestamp (newest first) and limit
        events = sorted(events, key=lambda e: e["timestamp"], reverse=True)
        return events[:limit]

    def get_recent_events(self, count: int = 50) -> list[dict[str, Any]]:
        """
        Get recent audit events.

        Args:
            count: Number of recent events to return

        Returns:
            List of recent audit events
        """
        return self.query_events(limit=count)

    def get_security_events(self, hours: int = 24) -> list[dict[str, Any]]:
        """
        Get security-related events from the last N hours.

        Args:
            hours: Number of hours to look back

        Returns:
            List of security events
        """
        from datetime import timedelta

        start_time = datetime.now() - timedelta(hours=hours)

        security_types = [
            AuditEventType.AUTH_FAILED,
            AuditEventType.PERMISSION_DENIED,
            AuditEventType.SUSPICIOUS_ACTIVITY,
            AuditEventType.RATE_LIMIT_EXCEEDED,
        ]

        events = []
        for event_type in security_types:
            events.extend(self.query_events(event_type=event_type, start_time=start_time))

        return sorted(events, key=lambda e: e["timestamp"], reverse=True)

    def get_statistics(self) -> dict[str, Any]:
        """
        Get audit log statistics.

        Returns:
            Dictionary with audit statistics
        """
        events = list(self._in_memory_events)

        if not events:
            return {
                "total_events": 0,
                "by_type": {},
                "by_severity": {},
                "recent_activity": [],
            }

        # Count by type
        by_type: dict[str, int] = {}
        for event in events:
            event_type = event["event_type"]
            by_type[event_type] = by_type.get(event_type, 0) + 1

        # Count by severity
        by_severity: dict[str, int] = {}
        for event in events:
            severity = event["severity"]
            by_severity[severity] = by_severity.get(severity, 0) + 1

        return {
            "total_events": len(events),
            "by_type": by_type,
            "by_severity": by_severity,
            "recent_activity": events[:10],
        }


# Global audit logger instance
audit_logger = AuditLogger()


def log_git_operation(
    operation: str,
    repo_url: str | None = None,
    user_id: str | None = None,
    workspace_id: str | None = None,
    success: bool = True,
    error_message: str | None = None,
    additional_details: dict[str, Any] | None = None,
) -> None:
    """
    Log a Git operation.

    Args:
        operation: Type of Git operation (clone, push, pull, etc.)
        repo_url: Repository URL
        user_id: Optional user identifier
        workspace_id: Optional workspace identifier
        success: Whether the operation succeeded
        error_message: Error message if operation failed
        additional_details: Additional operation details
    """
    event_type_map = {
        "clone": AuditEventType.GIT_CLONE,
        "push": AuditEventType.GIT_PUSH,
        "pull": AuditEventType.GIT_PULL,
        "fetch": AuditEventType.GIT_FETCH,
        "commit": AuditEventType.GIT_COMMIT,
        "checkout": AuditEventType.GIT_CHECKOUT,
        "merge": AuditEventType.GIT_MERGE,
        "rebase": AuditEventType.GIT_REBASE,
    }

    event_type = event_type_map.get(operation.lower())
    if not event_type:
        logger.warning(f"Unknown Git operation type: {operation}")
        return

    severity = AuditSeverity.INFO if success else AuditSeverity.ERROR

    details = {
        "operation": operation,
        "success": success,
        **(additional_details or {}),
    }

    if repo_url:
        # Sanitize repo URL to remove credentials
        from mcp_git.error_sanitizer import error_sanitizer

        details["repo_url"] = error_sanitizer.sanitize(repo_url)

    if error_message:
        details["error"] = error_message

    event = AuditEvent(
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        workspace_id=workspace_id,
        details=details,
    )

    audit_logger.log_event(event)


def log_security_event(
    event_type: AuditEventType,
    severity: AuditSeverity = AuditSeverity.WARNING,
    user_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Log a security event.

    Args:
        event_type: Type of security event
        severity: Severity level
        user_id: Optional user identifier
        details: Event details
    """
    event = AuditEvent(
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        details=details,
    )

    audit_logger.log_event(event)