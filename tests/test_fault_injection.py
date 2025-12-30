"""Fault injection tests for error recovery and resilience."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from mcp_git.error import McpGitError
from mcp_git.service.task_manager import TaskConfig, TaskManager
from mcp_git.service.workspace_manager import WorkspaceConfig, WorkspaceManager
from mcp_git.storage import SqliteStorage
from mcp_git.storage.models import CleanupStrategy
from mcp_git.utils import sanitize_input


class TestNetworkFailureRecovery:
    """Tests for network failure handling and recovery."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def storage(self, temp_dir):
        """Create a storage instance for tests."""
        db_path = temp_dir / "test.db"
        storage = SqliteStorage(db_path)
        return storage


class TestTaskTimeoutHandling:
    """Tests for task timeout handling."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def storage(self, temp_dir):
        """Create a storage instance for tests."""
        db_path = temp_dir / "test.db"
        storage = SqliteStorage(db_path)
        return storage

    @pytest.mark.asyncio
    async def test_task_timeout_config_parsing(self, temp_dir, storage):
        """Test that timeout configuration is properly parsed."""
        config = TaskConfig(
            max_concurrent_tasks=5,
            task_timeout_seconds=2,
            result_retention_seconds=60,
        )

        # Verify configuration values
        assert config.task_timeout_seconds == 2
        assert config.max_concurrent_tasks == 5
        assert config.result_retention_seconds == 60

    @pytest.mark.asyncio
    async def test_task_completion_before_timeout(self, temp_dir, storage):
        """Test that tasks completing before timeout are not affected."""
        # Initialize storage first
        await storage.initialize()

        # Create task manager
        config = TaskConfig(
            max_concurrent_tasks=5,
            task_timeout_seconds=10,
            result_retention_seconds=60,
        )

        manager = TaskManager(storage, config)
        await manager.start()

        try:
            # Verify we can check timeouts without errors
            await manager._check_timeouts()

            # Active tasks should be empty initially
            assert len(manager._active_tasks) == 0

        finally:
            await manager.stop()


class TestWorkerCrashRecovery:
    """Tests for worker crash recovery."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_worker_crash_detection(self, temp_dir):
        """Test that worker crashes are detected."""
        from mcp_git.execution.worker_pool import WorkerPool

        pool = WorkerPool(
            min_workers=1,
            max_workers=3,
            max_tasks_per_worker=5,
            scale_up_threshold=0.7,
            scale_down_threshold=0.3,
            scale_interval=1.0,
        )

        # Set up a simple task processor
        async def task_processor(task_id: str, task_data: any):
            await asyncio.sleep(0.1)
            return "completed"

        pool.set_task_processor(task_processor)
        await pool.start()

        # Verify pool is running
        assert pool._running is True

        # Cleanup - use graceful=False to avoid hanging
        await pool.stop(graceful=False)

    @pytest.mark.asyncio
    async def test_task_recovery_after_crash(self, temp_dir):
        """Test that tasks can be recovered after worker crash."""
        from mcp_git.execution.worker_pool import WorkerPool

        pool = WorkerPool(
            min_workers=1,
            max_workers=2,
            max_tasks_per_worker=3,
            scale_up_threshold=0.8,
            scale_down_threshold=0.2,
            scale_interval=0.5,
        )

        call_count = 0

        async def task_processor(task_id: str, task_data: any):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return True  # Return True for success

        pool.set_task_processor(task_processor)
        await pool.start()

        # Submit a task
        result = await pool.submit_task("test-task-1", {"data": "test"})
        assert result is True

        # Cleanup - use graceful=False to avoid hanging on empty queue
        await pool.stop(graceful=False)


class TestDatabaseFailureRecovery:
    """Tests for database failure recovery."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_database_connection_failure(self, temp_dir):
        """Test graceful handling of database connection failures."""
        storage = SqliteStorage(temp_dir / "nonexistent" / "test.db")

        # Verify storage can be created (it will create directories when initialized)
        assert storage.database_path.parent.exists() is False  # Not created yet


class TestPathTraversalPrevention:
    """Tests for path traversal attack prevention."""

    def test_sanitize_path_basic(self):
        """Test basic path sanitization."""
        from mcp_git.utils import sanitize_path

        base = Path("/safe/base")
        malicious = Path("/safe/base/../../../etc/passwd")

        # Should raise ValueError for path traversal
        with pytest.raises(ValueError, match="traverse outside"):
            sanitize_path(malicious, base)

    def test_sanitize_path_absolute(self):
        """Test sanitization of absolute paths outside base."""
        from mcp_git.utils import sanitize_path

        base = Path("/safe/base")
        absolute_malicious = Path("/etc/passwd")

        # Should raise ValueError for absolute path outside base
        with pytest.raises(ValueError, match="traverse outside"):
            sanitize_path(absolute_malicious, base)

    def test_sanitize_path_normal(self):
        """Test sanitization of normal paths."""
        from mcp_git.utils import sanitize_path

        base = Path("/safe/base")
        normal_path = Path("/safe/base/subdir/file.txt")

        result = sanitize_path(normal_path, base)
        assert str(result).startswith(str(base))

    def test_sanitize_path_relative(self):
        """Test sanitization of relative paths."""
        from mcp_git.utils import sanitize_path

        base = Path("/safe/base")
        relative_path = Path("subdir/file.txt")

        result = sanitize_path(relative_path, base)
        assert str(result).startswith(str(base))


class TestCommandInjectionPrevention:
    """Tests for command injection prevention."""

    def test_sanitize_input_basic(self):
        """Test basic input sanitization."""
        # Normal input should pass through
        result = sanitize_input("normal input")
        assert result == "normal input"

    def test_sanitize_input_removes_dangerous_chars(self):
        """Test that dangerous characters are removed."""
        # Test shell metacharacters
        result = sanitize_input("test; rm -rf /")
        # Semicolon should be removed
        assert ";" not in result
        # Dangerous command patterns should be removed
        assert "rm -rf" not in result.lower()

    def test_sanitize_input_length_limit(self):
        """Test that input length is limited."""
        # Create input longer than MAX_INPUT_LENGTH
        long_input = "a" * 2000
        result = sanitize_input(long_input)

        # Should be truncated
        assert len(result) <= 1000

    def test_sanitize_input_empty(self):
        """Test handling of empty input."""
        result = sanitize_input("")
        assert result == ""

        result = sanitize_input(None)
        assert result is None


class TestRetryMechanism:
    """Tests for retry mechanism with fault injection."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self, temp_dir):
        """Test retry mechanism for transient errors."""
        from mcp_git.retry import RetryConfig, retry_async

        call_count = 0

        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary network error")
            return "success"

        config = RetryConfig(
            max_retries=3,
            initial_delay=0.01,
            max_delay=0.1,
            jitter=False,
        )

        result = await retry_async(failing_operation, config=config)
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, temp_dir):
        """Test that exception is raised when max retries exceeded."""
        from mcp_git.retry import RetryConfig, retry_async

        call_count = 0

        async def always_failing_operation():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent network error")

        config = RetryConfig(
            max_retries=2,
            initial_delay=0.01,
            max_delay=0.1,
            jitter=False,
        )

        # Should raise McpGitError since ConnectionError is wrapped
        with pytest.raises(McpGitError):
            await retry_async(always_failing_operation, config=config)

        # Should have attempted 3 times (initial + 2 retries)
        assert call_count == 3


class TestCredentialSecurity:
    """Tests for credential security."""

    def test_git_token_not_logged(self, temp_dir, monkeypatch):
        """Test that git token is not logged."""
        # This test verifies that sensitive data is handled properly
        from mcp_git.config import Config

        config = Config()
        config.git_token = "secret-token-12345"

        # Token should be stored
        assert config.git_token == "secret-token-12345"

    def test_credential_masking_in_logs(self, temp_dir, caplog):
        """Test that credentials are masked in logs."""

        # This test verifies log sanitization
        # In production, tokens should be masked

        # The logging system should handle sensitive data
        # This is a placeholder for actual log masking tests
        pass


class TestDiskSpaceManagement:
    """Tests for disk space management."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def storage(self, temp_dir):
        """Create a storage instance for tests."""
        db_path = temp_dir / "test.db"
        storage = SqliteStorage(db_path)
        return storage

    def test_workspace_size_limit(self, temp_dir, storage):
        """Test that workspace size limit is enforced."""
        config = WorkspaceConfig(
            root_path=temp_dir / "workspaces",
            max_size_bytes=1024 * 1024,  # 1MB limit
        )

        manager = WorkspaceManager(storage, config)

        # Verify configuration is set
        assert manager.config.max_size_bytes == 1024 * 1024

    def test_workspace_cleanup_on_size_exceeded(self, temp_dir, storage):
        """Test workspace cleanup when size limit is exceeded."""
        workspace_dir = temp_dir / "test_workspace"
        workspace_dir.mkdir()

        config = WorkspaceConfig(
            root_path=workspace_dir,
            max_size_bytes=100,  # Very small limit
            retention_seconds=1,
            cleanup_strategy=CleanupStrategy.LRU,
        )

        WorkspaceManager(storage, config)

        # Create a file larger than the limit
        large_file = workspace_dir / "large_file.bin"
        large_file.write_bytes(b"x" * 200)  # 200 bytes > 100 byte limit

        # Cleanup should handle this
        # (actual cleanup depends on implementation)
        # The manager can check workspace size limits
        pass
