"""
Tests for audit logging functionality.
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from mcp_git.audit import (
    AuditEvent,
    AuditEventType,
    AuditLogger,
    AuditSeverity,
    audit_logger,
    log_git_operation,
    log_security_event,
)


class TestAuditEvent:
    """Test AuditEvent class."""

    def test_create_audit_event(self):
        """Test creating an audit event."""
        event = AuditEvent(
            event_type=AuditEventType.GIT_CLONE,
            severity=AuditSeverity.INFO,
            user_id="user123",
            workspace_id="workspace456",
            details={"repo_url": "https://github.com/user/repo.git"},
        )

        assert event.event_type == AuditEventType.GIT_CLONE
        assert event.severity == AuditSeverity.INFO
        assert event.user_id == "user123"
        assert event.workspace_id == "workspace456"
        assert event.details["repo_url"] == "https://github.com/user/repo.git"

    def test_audit_event_to_dict(self):
        """Test converting audit event to dictionary."""
        event = AuditEvent(
            event_type=AuditEventType.GIT_CLONE,
            severity=AuditSeverity.INFO,
            details={"operation": "clone"},
        )

        event_dict = event.to_dict()

        assert "event_id" in event_dict
        assert "timestamp" in event_dict
        assert event_dict["event_type"] == "git_clone"
        assert event_dict["severity"] == "info"
        assert event_dict["details"]["operation"] == "clone"

    def test_audit_event_to_json(self):
        """Test converting audit event to JSON."""
        event = AuditEvent(
            event_type=AuditEventType.GIT_CLONE,
            severity=AuditSeverity.INFO,
            details={"operation": "clone"},
        )

        event_json = event.to_json()

        parsed = json.loads(event_json)
        assert parsed["event_type"] == "git_clone"
        assert parsed["severity"] == "info"


class TestAuditLogger:
    """Test AuditLogger class."""

    def test_init_audit_logger(self):
        """Test initializing audit logger."""
        logger = AuditLogger()
        assert logger.log_path is None
        assert len(logger._in_memory_events) == 0

    def test_init_audit_logger_with_file(self):
        """Test initializing audit logger with file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path=log_path)
            assert logger.log_path == log_path
            assert log_path.parent.exists()

    def test_log_event(self):
        """Test logging an event."""
        logger = AuditLogger()
        event = AuditEvent(
            event_type=AuditEventType.GIT_CLONE,
            severity=AuditSeverity.INFO,
            details={"operation": "clone"},
        )

        logger.log_event(event)

        assert len(logger._in_memory_events) == 1
        assert logger._in_memory_events[0]["event_type"] == "git_clone"

    def test_log_multiple_events(self):
        """Test logging multiple events."""
        logger = AuditLogger()

        for i in range(5):
            event = AuditEvent(
                event_type=AuditEventType.GIT_CLONE,
                severity=AuditSeverity.INFO,
                details={"operation": f"clone-{i}"},
            )
            logger.log_event(event)

        assert len(logger._in_memory_events) == 5

    def test_log_event_to_file(self):
        """Test logging event to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path=log_path)

            event = AuditEvent(
                event_type=AuditEventType.GIT_CLONE,
                severity=AuditSeverity.INFO,
                details={"operation": "clone"},
            )

            logger.log_event(event)

            assert log_path.exists()
            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()
                parsed = json.loads(content.strip())
                assert parsed["event_type"] == "git_clone"

    def test_query_events_by_type(self):
        """Test querying events by type."""
        logger = AuditLogger()

        # Log different event types
        logger.log_event(
            AuditEvent(event_type=AuditEventType.GIT_CLONE, severity=AuditSeverity.INFO)
        )
        logger.log_event(
            AuditEvent(event_type=AuditEventType.GIT_PUSH, severity=AuditSeverity.INFO)
        )
        logger.log_event(
            AuditEvent(event_type=AuditEventType.GIT_CLONE, severity=AuditSeverity.INFO)
        )

        events = logger.query_events(event_type=AuditEventType.GIT_CLONE)

        assert len(events) == 2
        for event in events:
            assert event["event_type"] == "git_clone"

    def test_query_events_by_severity(self):
        """Test querying events by severity."""
        logger = AuditLogger()

        logger.log_event(
            AuditEvent(event_type=AuditEventType.GIT_CLONE, severity=AuditSeverity.INFO)
        )
        logger.log_event(
            AuditEvent(event_type=AuditEventType.AUTH_FAILED, severity=AuditSeverity.ERROR)
        )
        logger.log_event(
            AuditEvent(event_type=AuditEventType.GIT_CLONE, severity=AuditSeverity.WARNING)
        )

        events = logger.query_events(severity=AuditSeverity.ERROR)

        assert len(events) == 1
        assert events[0]["event_type"] == "auth_failed"

    def test_query_events_by_user_id(self):
        """Test querying events by user ID."""
        logger = AuditLogger()

        logger.log_event(
            AuditEvent(
                event_type=AuditEventType.GIT_CLONE, severity=AuditSeverity.INFO, user_id="user1"
            )
        )
        logger.log_event(
            AuditEvent(
                event_type=AuditEventType.GIT_PUSH, severity=AuditSeverity.INFO, user_id="user2"
            )
        )
        logger.log_event(
            AuditEvent(
                event_type=AuditEventType.GIT_CLONE, severity=AuditSeverity.INFO, user_id="user1"
            )
        )

        events = logger.query_events(user_id="user1")

        assert len(events) == 2
        for event in events:
            assert event["user_id"] == "user1"

    def test_query_events_with_time_range(self):
        """Test querying events within a time range."""
        logger = AuditLogger()

        now = datetime.now()
        past = now - timedelta(hours=1)

        # Log event in the past
        old_event = AuditEvent(event_type=AuditEventType.GIT_CLONE, severity=AuditSeverity.INFO)
        old_event.timestamp = past.isoformat()
        logger._in_memory_events.append(old_event.to_dict())

        # Log current event
        logger.log_event(
            AuditEvent(event_type=AuditEventType.GIT_PUSH, severity=AuditSeverity.INFO)
        )

        # Query events from last 30 minutes
        start_time = now - timedelta(minutes=30)
        events = logger.query_events(start_time=start_time)

        assert len(events) == 1
        assert events[0]["event_type"] == "git_push"

    def test_query_events_with_limit(self):
        """Test querying events with limit."""
        logger = AuditLogger()

        for i in range(10):
            logger.log_event(
                AuditEvent(
                    event_type=AuditEventType.GIT_CLONE,
                    severity=AuditSeverity.INFO,
                    details={"index": i},
                )
            )

        events = logger.query_events(limit=5)

        assert len(events) == 5

    def test_get_recent_events(self):
        """Test getting recent events."""
        logger = AuditLogger()

        for i in range(10):
            logger.log_event(
                AuditEvent(
                    event_type=AuditEventType.GIT_CLONE,
                    severity=AuditSeverity.INFO,
                    details={"index": i},
                )
            )

        recent = logger.get_recent_events(count=5)

        assert len(recent) == 5

    def test_get_security_events(self):
        """Test getting security events."""
        logger = AuditLogger()

        logger.log_event(
            AuditEvent(event_type=AuditEventType.AUTH_FAILED, severity=AuditSeverity.ERROR)
        )
        logger.log_event(
            AuditEvent(event_type=AuditEventType.GIT_CLONE, severity=AuditSeverity.INFO)
        )
        logger.log_event(
            AuditEvent(event_type=AuditEventType.PERMISSION_DENIED, severity=AuditSeverity.ERROR)
        )

        security_events = logger.get_security_events(hours=24)

        assert len(security_events) == 2
        event_types = {e["event_type"] for e in security_events}
        assert "auth_failed" in event_types
        assert "permission_denied" in event_types

    def test_get_statistics(self):
        """Test getting audit statistics."""
        logger = AuditLogger()

        logger.log_event(
            AuditEvent(event_type=AuditEventType.GIT_CLONE, severity=AuditSeverity.INFO)
        )
        logger.log_event(
            AuditEvent(event_type=AuditEventType.GIT_CLONE, severity=AuditSeverity.INFO)
        )
        logger.log_event(
            AuditEvent(event_type=AuditEventType.GIT_PUSH, severity=AuditSeverity.WARNING)
        )
        logger.log_event(
            AuditEvent(event_type=AuditEventType.AUTH_FAILED, severity=AuditSeverity.ERROR)
        )

        stats = logger.get_statistics()

        assert stats["total_events"] == 4
        assert stats["by_type"]["git_clone"] == 2
        assert stats["by_type"]["git_push"] == 1
        assert stats["by_type"]["auth_failed"] == 1
        assert stats["by_severity"]["info"] == 2
        assert stats["by_severity"]["warning"] == 1
        assert stats["by_severity"]["error"] == 1

    def test_get_statistics_empty(self):
        """Test getting statistics when no events."""
        logger = AuditLogger()

        stats = logger.get_statistics()

        assert stats["total_events"] == 0
        assert stats["by_type"] == {}
        assert stats["by_severity"] == {}
        assert stats["recent_activity"] == []


class TestLogGitOperation:
    """Test log_git_operation function."""

    def test_log_successful_clone(self):
        """Test logging a successful clone operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path=log_path)

            # Replace global audit logger
            import mcp_git.audit as audit_module

            original_logger = audit_module.audit_logger
            audit_module.audit_logger = logger

            try:
                log_git_operation(
                    operation="clone",
                    repo_url="https://github.com/user/repo.git",
                    user_id="user123",
                    workspace_id="workspace456",
                    success=True,
                )

                events = logger.query_events(event_type=AuditEventType.GIT_CLONE)

                assert len(events) == 1
                assert events[0]["details"]["operation"] == "clone"
                assert events[0]["details"]["success"] is True
                assert events[0]["user_id"] == "user123"
                assert events[0]["workspace_id"] == "workspace456"
            finally:
                audit_module.audit_logger = original_logger

    def test_log_failed_push(self):
        """Test logging a failed push operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path=log_path)

            import mcp_git.audit as audit_module

            original_logger = audit_module.audit_logger
            audit_module.audit_logger = logger

            try:
                log_git_operation(
                    operation="push",
                    repo_url="https://github.com/user/repo.git",
                    success=False,
                    error_message="Authentication failed",
                )

                events = logger.query_events(event_type=AuditEventType.GIT_PUSH)

                assert len(events) == 1
                assert events[0]["details"]["success"] is False
                assert events[0]["details"]["error"] == "Authentication failed"
                assert events[0]["severity"] == "error"
            finally:
                audit_module.audit_logger = original_logger

    def test_log_git_operation_sanitizes_url(self):
        """Test that Git operation sanitizes URLs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path=log_path)

            import mcp_git.audit as audit_module

            original_logger = audit_module.audit_logger
            audit_module.audit_logger = logger

            try:
                log_git_operation(
                    operation="clone",
                    repo_url="https://user:secret123@github.com/repo.git",
                    success=True,
                )

                events = logger.query_events(event_type=AuditEventType.GIT_CLONE)

                assert len(events) == 1
                assert "secret123" not in events[0]["details"]["repo_url"]
                assert "***" in events[0]["details"]["repo_url"]
            finally:
                audit_module.audit_logger = original_logger


class TestLogSecurityEvent:
    """Test log_security_event function."""

    def test_log_auth_failed(self):
        """Test logging authentication failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path=log_path)

            import mcp_git.audit as audit_module

            original_logger = audit_module.audit_logger
            audit_module.audit_logger = logger

            try:
                log_security_event(
                    event_type=AuditEventType.AUTH_FAILED,
                    severity=AuditSeverity.ERROR,
                    user_id="user123",
                    details={"reason": "Invalid token"},
                )

                events = logger.query_events(event_type=AuditEventType.AUTH_FAILED)

                assert len(events) == 1
                assert events[0]["severity"] == "error"
                assert events[0]["user_id"] == "user123"
                assert events[0]["details"]["reason"] == "Invalid token"
            finally:
                audit_module.audit_logger = original_logger

    def test_log_suspicious_activity(self):
        """Test logging suspicious activity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path=log_path)

            import mcp_git.audit as audit_module

            original_logger = audit_module.audit_logger
            audit_module.audit_logger = logger

            try:
                log_security_event(
                    event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                    severity=AuditSeverity.CRITICAL,
                    details={"activity": "Multiple failed authentication attempts"},
                )

                events = logger.query_events(event_type=AuditEventType.SUSPICIOUS_ACTIVITY)

                assert len(events) == 1
                assert events[0]["severity"] == "critical"
            finally:
                audit_module.audit_logger = original_logger


class TestGlobalAuditLogger:
    """Test global audit logger instance."""

    def test_global_audit_logger_exists(self):
        """Test that global audit logger exists."""
        assert audit_logger is not None
        assert isinstance(audit_logger, AuditLogger)

    def test_log_to_global_logger(self):
        """Test logging to global audit logger."""
        event = AuditEvent(
            event_type=AuditEventType.GIT_CLONE,
            severity=AuditSeverity.INFO,
            details={"test": "global"},
        )

        # Get initial count
        initial_count = len(audit_logger._in_memory_events)

        audit_logger.log_event(event)

        # Check that event was added
        assert len(audit_logger._in_memory_events) == initial_count + 1
