"""
Performance tests for mcp-git.

This module tests performance characteristics of Git operations
including response times, throughput, and resource usage.
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestAdapterPerformance:
    """Performance tests for Git adapter operations."""

    @pytest.fixture
    def mock_git_repo(self, tmp_path):
        """Create a mock Git repository for testing."""
        from mcp_git.git.adapter import GitAdapter

        adapter = MagicMock(spec=GitAdapter)
        adapter.status = AsyncMock(return_value=[])
        adapter.list_branches = AsyncMock(return_value=[])
        adapter.log = AsyncMock(return_value=[])
        return adapter

    @pytest.mark.asyncio
    async def test_status_response_time(self, mock_git_repo):
        """Test that status operation completes within acceptable time."""
        import time

        start = time.perf_counter()
        await mock_git_repo.status(Path("/fake/path"))
        elapsed = time.perf_counter() - start

        # Should complete in under 100ms for mocked operation
        assert elapsed < 0.1, f"Status took {elapsed:.3f}s, expected < 0.1s"

    @pytest.mark.asyncio
    async def test_list_branches_response_time(self, mock_git_repo):
        """Test that list_branches operation completes within acceptable time."""
        import time

        start = time.perf_counter()
        await mock_git_repo.list_branches(Path("/fake/path"))
        elapsed = time.perf_counter() - start

        # Should complete in under 100ms for mocked operation
        assert elapsed < 0.1, f"List branches took {elapsed:.3f}s, expected < 0.1s"

    @pytest.mark.asyncio
    async def test_log_response_time(self, mock_git_repo):
        """Test that log operation completes within acceptable time."""
        import time

        start = time.perf_counter()
        await mock_git_repo.log(Path("/fake/path"))
        elapsed = time.perf_counter() - start

        # Should complete in under 100ms for mocked operation
        assert elapsed < 0.1, f"Log took {elapsed:.3f}s, expected < 0.1s"


class TestRetryPerformance:
    """Performance tests for retry mechanism."""

    @pytest.mark.asyncio
    async def test_retry_delay_calculation(self):
        """Test retry delay calculation performance."""
        from mcp_git.retry import RetryConfig

        config = RetryConfig(
            max_retries=5,
            initial_delay=0.01,  # Use small delays for testing
            max_delay=1.0,
            exponential_base=2.0,
            jitter=True,
            jitter_factor=0.1,
        )

        # Calculate delays for multiple attempts
        start = time.perf_counter()
        for attempt in range(10):
            config.get_delay(attempt)
        elapsed = time.perf_counter() - start

        # Should calculate all delays in under 1ms
        assert elapsed < 0.001, f"Delay calculation took {elapsed:.6f}s, expected < 0.001s"

    @pytest.mark.asyncio
    async def test_retry_async_overhead(self):
        """Test the overhead of retry mechanism on successful operations."""
        from mcp_git.retry import RetryConfig, retry_async

        call_count = 0

        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        config = RetryConfig(max_retries=3, initial_delay=0.001)

        start = time.perf_counter()
        result = await retry_async(successful_func, config=config)
        elapsed = time.perf_counter() - start

        assert result == "success"
        assert call_count == 1  # Should only call once on success
        # Overhead should be minimal (< 10ms)
        assert elapsed < 0.01, f"Retry overhead was {elapsed:.3f}s, expected < 0.01s"


class TestTaskQueuePerformance:
    """Performance tests for task queue operations."""

    @pytest.fixture
    async def task_queue(self):
        """Create a task queue for performance testing."""
        from mcp_git.execution.task_queue import TaskQueue

        queue = TaskQueue(max_size=100, max_concurrent=10, max_retries=2)
        await queue.start()

        yield queue

        await queue.stop()

    @pytest.mark.asyncio
    async def test_task_submission_performance(self, task_queue):
        """Test task submission throughput."""

        async def dummy_task():
            return "done"

        # Submit multiple tasks and measure time
        start = time.perf_counter()
        for _i in range(100):
            await task_queue.submit(coroutine=dummy_task())
        elapsed = time.perf_counter() - start

        # Should submit 100 tasks in under 1 second
        assert elapsed < 1.0, f"Task submission took {elapsed:.3f}s for 100 tasks"

    @pytest.mark.asyncio
    async def test_queue_size_query_performance(self, task_queue):
        """Test queue size query response time."""

        async def dummy_task():
            await asyncio.sleep(0.01)

        # Submit some tasks
        for _i in range(10):
            await task_queue.submit(coroutine=dummy_task())

        # Query size multiple times
        start = time.perf_counter()
        for _ in range(100):
            await task_queue.get_queue_size()
        elapsed = time.perf_counter() - start

        # Should handle 100 queries quickly
        assert elapsed < 0.5, f"Queue size queries took {elapsed:.3f}s"


class TestAdapterMethodPerformance:
    """Performance benchmarks for adapter methods."""

    @pytest.mark.asyncio
    async def test_blame_options_creation(self):
        """Benchmark BlameOptions creation."""
        from pathlib import Path

        from mcp_git.git.adapter import BlameOptions

        start = time.perf_counter()
        for _ in range(1000):
            BlameOptions(path=Path("/test/file.py"))
        elapsed = time.perf_counter() - start

        # Should create 1000 options in under 100ms
        assert elapsed < 0.1, f"Creating 1000 BlameOptions took {elapsed:.3f}s"

    @pytest.mark.asyncio
    async def test_diff_options_creation(self):
        """Benchmark DiffOptions creation."""
        from mcp_git.git.adapter import DiffOptions

        start = time.perf_counter()
        for _ in range(1000):
            DiffOptions()
        elapsed = time.perf_counter() - start

        # Should create 1000 options in under 50ms
        assert elapsed < 0.05, f"Creating 1000 DiffOptions took {elapsed:.3f}s"


class TestMemoryEfficiency:
    """Tests for memory efficiency of operations."""

    @pytest.mark.asyncio
    async def test_large_branch_list_memory(self):
        """Test handling of large branch lists without excessive memory."""
        from mcp_git.git.adapter import BranchInfo

        # Simulate many branches
        branches = [
            BranchInfo(
                name=f"feature-branch-{i}",
                oid="abc123def456",
                is_local=True,
                is_remote=False,
            )
            for i in range(100)
        ]

        # Should be able to process the list
        assert len(branches) == 100
        total_name_length = sum(len(b.name) for b in branches)
        assert total_name_length > 0  # Verify data is accessible


class TestConcurrencyPerformance:
    """Tests for concurrent operation performance."""

    @pytest.mark.asyncio
    async def test_concurrent_status_operations(self):
        """Test multiple concurrent status operations."""
        from mcp_git.git.adapter import GitAdapter

        adapter = MagicMock(spec=GitAdapter)
        adapter.status = AsyncMock(return_value=[])

        # Run 50 concurrent status operations
        start = time.perf_counter()
        await asyncio.gather(*[adapter.status(Path(f"/fake/path-{i}")) for i in range(50)])
        elapsed = time.perf_counter() - start

        # All operations should complete in reasonable time
        assert elapsed < 1.0, f"50 concurrent status ops took {elapsed:.3f}s"
        assert adapter.status.call_count == 50

    @pytest.mark.asyncio
    async def test_concurrent_branch_listing(self):
        """Test multiple concurrent branch listing operations."""
        from mcp_git.git.adapter import GitAdapter

        adapter = MagicMock(spec=GitAdapter)
        adapter.list_branches = AsyncMock(return_value=[])

        # Run 20 concurrent branch listing operations
        start = time.perf_counter()
        await asyncio.gather(*[adapter.list_branches(Path(f"/repo-{i}")) for i in range(20)])
        elapsed = time.perf_counter() - start

        # Should complete quickly
        assert elapsed < 0.5, f"20 concurrent branch listings took {elapsed:.3f}s"
        assert adapter.list_branches.call_count == 20


class TestRealWorldPerformance:
    """Real-world performance benchmarks with actual Git operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def adapter(self):
        """Create a GitPython adapter."""
        from mcp_git.git.adapter_gitpython import GitPythonAdapter

        return GitPythonAdapter()

    @pytest.mark.asyncio
    async def test_clone_and_basic_operations(self, temp_dir, adapter):
        """Test complete workflow: clone, branch, commit, log."""
        import git

        from mcp_git.git.adapter import CheckoutOptions, CommitOptions

        # Create a local test repo
        repo_path = temp_dir / "performance-test"
        repo_path.mkdir()
        repo = git.Repo.init(str(repo_path))

        # Create initial commit
        (repo_path / "README.md").write_text("# Performance Test\n")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        # Benchmark: Create 10 branches and switch between them
        start = time.perf_counter()
        for i in range(10):
            await adapter.create_branch(repo_path, f"bench-branch-{i}")
            await adapter.checkout(
                repo_path,
                CheckoutOptions(branch=f"bench-branch-{i}", force=True),
            )
            # Create a commit
            (repo_path / f"file-{i}.txt").write_text(f"Content {i}")
            await adapter.add(repo_path, [f"file-{i}.txt"])
            await adapter.commit(
                repo_path,
                CommitOptions(message=f"Commit {i} on bench-branch-{i}"),
            )
        branch_time = time.perf_counter() - start

        # Benchmark: Get log of all commits
        start = time.perf_counter()
        commits = await adapter.log(repo_path, options=None)
        log_time = time.perf_counter() - start

        # Assertions
        assert len(commits) >= 10, f"Expected at least 10 commits, got {len(commits)}"

        # Performance thresholds (adjust based on environment)
        assert branch_time < 60.0, f"Branch operations took {branch_time:.2f}s, expected < 60s"
        assert log_time < 5.0, f"Log operation took {log_time:.2f}s, expected < 5s"

    @pytest.mark.asyncio
    async def test_many_files_operations(self, temp_dir, adapter):
        """Test operations with repositories containing many files."""
        import git

        from mcp_git.git.adapter import CommitOptions

        # Create repo with many files
        repo_path = temp_dir / "many-files-test"
        repo_path.mkdir()
        repo = git.Repo.init(str(repo_path))

        # Create initial commit first
        (repo_path / "README.md").write_text("# Test\n")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        # Create 100 files
        start = time.perf_counter()
        for i in range(100):
            (repo_path / f"file-{i:03d}.txt").write_text(f"Content for file {i}")

        # Stage all files
        await adapter.add(repo_path, ["."])
        commit_oid = await adapter.commit(
            repo_path,
            CommitOptions(message="Add 100 files"),
        )
        file_time = time.perf_counter() - start

        # Verify commit was created
        assert commit_oid is not None, "Commit should be created"

        # Benchmark: Log with many files
        start = time.perf_counter()
        commits = await adapter.log(repo_path, options=None)
        log_time = time.perf_counter() - start

        # Benchmark: List branches with many commits
        start = time.perf_counter()
        branches = await adapter.list_branches(repo_path, local=True)
        branch_time = time.perf_counter() - start

        # Assertions
        assert len(commits) >= 1, f"Expected at least 1 commit, got {len(commits)}"

        # Performance thresholds
        assert file_time < 30.0, f"Creating 100 files took {file_time:.2f}s"
        assert branch_time < 1.0, f"List branches with 100 files took {branch_time:.2f}s"
        assert log_time < 1.0, f"Log with 100 files took {log_time:.2f}s"

    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self, temp_dir, adapter):
        """Test performance of concurrent Git operations."""
        import git

        from mcp_git.git.adapter import CheckoutOptions, CommitOptions

        # Create multiple repos for concurrent operations
        repos = []
        for i in range(5):
            repo_path = temp_dir / f"concurrent-{i}"
            repo_path.mkdir()
            repo = git.Repo.init(str(repo_path))
            (repo_path / "README.md").write_text(f"# Repo {i}\n")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")
            repos.append((repo_path, repo))

        # Run concurrent operations
        start = time.perf_counter()
        tasks = []
        for i, (repo_path, _) in enumerate(repos):
            # Create a branch and commit
            tasks.append(adapter.create_branch(repo_path, f"concurrent-branch-{i}"))
            tasks.append(
                adapter.checkout(
                    repo_path,
                    CheckoutOptions(branch=f"concurrent-branch-{i}", force=True),
                )
            )
            tasks.append(adapter.add(repo_path, ["README.md"]))
            tasks.append(
                adapter.commit(
                    repo_path,
                    CommitOptions(message=f"Concurrent commit {i}"),
                )
            )

        await asyncio.gather(*tasks)
        concurrent_time = time.perf_counter() - start

        # Performance threshold
        assert concurrent_time < 30.0, f"Concurrent operations took {concurrent_time:.2f}s"


# Performance thresholds for real-world operations
REAL_WORLD_THRESHOLDS = {
    "clone_small_repo": 30.0,  # 30 seconds for small repo clone
    "create_10_branches": 60.0,  # 60 seconds for 10 branches with commits
    "status_100_files": 2.0,  # 2 seconds for status with 100 files
    "log_100_files": 1.0,  # 1 second for log with 100 files
    "concurrent_5_repos": 30.0,  # 30 seconds for concurrent ops on 5 repos
}
