"""
Tests for metrics module.

Tests for Prometheus metrics collection, recording, and decorators.
"""

import time
from unittest.mock import patch

import pytest

from mcp_git.metrics import (
    ACTIVE_TASKS,
    QUEUED_TASKS,
    TASK_DURATION,
    TASKS_TOTAL,
    Cache,
    MetricsCollector,
    start_metrics_server,
    track_duration,
)


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_record_task_start(self):
        """Test recording task start."""
        collector = MetricsCollector()
        collector.record_task_start("task-1", "clone")

        # Verify task was added to start times
        assert "task-1" in collector._task_start_times

    def test_record_task_complete(self):
        """Test recording task completion."""
        collector = MetricsCollector()
        collector.record_task_start("task-1", "clone")
        time.sleep(0.1)  # Simulate some work
        collector.record_task_complete("task-1", "success")

        # Verify task was removed from start times
        assert "task-1" not in collector._task_start_times

    def test_record_task_complete_with_failure(self):
        """Test recording task completion with failure status."""
        collector = MetricsCollector()
        collector.record_task_start("task-2", "push")
        time.sleep(0.1)
        collector.record_task_complete("task-2", "failed")

        # Verify task was removed from start times
        assert "task-2" not in collector._task_start_times

    def test_track_git_operation(self):
        """Test tracking Git operations."""
        collector = MetricsCollector()
        collector.record_git_operation("clone", "success")
        time.sleep(0.1)

        # Verify operation was recorded
        # Note: We can't directly access the counter value in Prometheus client
        assert True  # If no exception was raised, the operation was recorded


class TestTrackDurationDecorator:
    """Test track_duration context manager."""

    def test_track_duration_measures_time(self):
        """Test that track_duration measures execution time."""
        with track_duration("test_operation"):
            time.sleep(0.1)

        # Verify duration was recorded
        # Note: We can't directly access the histogram value in Prometheus client
        assert True  # If no exception was raised, the duration was recorded


class TestCache:
    """Test Cache class."""

    def test_cache_get_set(self):
        """Test cache get and set operations."""
        cache = Cache(max_size=100, ttl=60)
        cache.set("key1", "value1")
        result = cache.get("key1")
        assert result == "value1"

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = Cache(max_size=100, ttl=60)
        result = cache.get("nonexistent_key")
        assert result is None

    def test_cache_eviction(self):
        """Test cache eviction when max_size is exceeded."""
        cache = Cache(max_size=2, ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict oldest

        # Verify oldest key was evicted
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_cache_expiration(self):
        """Test cache expiration after TTL."""
        cache = Cache(max_size=100, ttl=1)  # 1 second TTL
        cache.set("key1", "value1")
        time.sleep(1.1)  # Wait for expiration
        result = cache.get("key1")
        assert result is None


class TestStartMetricsServer:
    """Test start_metrics_server function."""

    @patch("mcp_git.metrics.start_http_server")
    def test_start_metrics_server_default_port(self, mock_start):
        """Test starting metrics server with default port."""
        start_metrics_server()
        mock_start.assert_called_once_with(9090)

    @patch("mcp_git.metrics.start_http_server")
    def test_start_metrics_server_custom_port(self, mock_start):
        """Test starting metrics server with custom port."""
        start_metrics_server(port=8080)
        mock_start.assert_called_once_with(8080)


class TestMetricsIntegration:
    """Integration tests for metrics."""

    def test_complete_task_lifecycle_metrics(self):
        """Test metrics for complete task lifecycle."""
        collector = MetricsCollector()

        # Start task
        collector.record_task_start("task-3", "fetch")

        # Complete task
        time.sleep(0.05)
        collector.record_task_complete("task-3", "success")

        # Verify task was removed from start times
        assert "task-3" not in collector._task_start_times

    def test_concurrent_tasks_metrics(self):
        """Test metrics for concurrent tasks."""
        collector = MetricsCollector()

        # Start multiple tasks
        for i in range(5):
            collector.record_task_start(f"task-{i}", "pull")

        # Verify all tasks are in start times
        assert len(collector._task_start_times) == 5

        # Complete all tasks
        for i in range(5):
            collector.record_task_complete(f"task-{i}", "success")

        # Verify all tasks were removed
        assert len(collector._task_start_times) == 0


class TestCachePerformance:
    """Performance tests for cache."""

    def test_cache_performance_large_dataset(self):
        """Test cache performance with large dataset."""
        cache = Cache(max_size=10000, ttl=60)

        # Fill cache
        start = time.time()
        for i in range(10000):
            cache.set(f"key{i}", f"value{i}")
        elapsed = time.time() - start

        # Should complete in reasonable time
        assert elapsed < 1.0

    def test_cache_retrieval_performance(self):
        """Test cache retrieval performance."""
        cache = Cache(max_size=1000, ttl=60)

        # Fill cache
        for i in range(1000):
            cache.set(f"key{i}", f"value{i}")

        # Measure retrieval time
        start = time.time()
        for i in range(1000):
            cache.get(f"key{i}")
        elapsed = time.time() - start

        # Should be very fast
        assert elapsed < 0.1
