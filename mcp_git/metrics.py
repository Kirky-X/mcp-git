"""
Metrics and monitoring module for mcp-git.

Provides Prometheus-compatible metrics for task execution,
workspace management, and Git operations.
"""

import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from functools import wraps
from typing import Any

from loguru import logger
from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server

# Task metrics
TASKS_TOTAL = Counter(
    "mcp_git_tasks_total", "Total number of tasks processed", ["operation", "status"]
)

TASK_DURATION = Histogram(
    "mcp_git_task_duration_seconds",
    "Task execution duration in seconds",
    ["operation"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600],
)

ACTIVE_TASKS = Gauge("mcp_git_active_tasks", "Number of tasks currently running")

QUEUED_TASKS = Gauge("mcp_git_queued_tasks", "Number of tasks waiting in queue")

# Workspace metrics
WORKSPACE_COUNT = Gauge("mcp_git_workspace_count", "Number of active workspaces")

WORKSPACE_DISK_USAGE = Gauge("mcp_git_workspace_disk_usage_bytes", "Total disk usage by workspaces")

WORKSPACE_SIZE_LIMIT = Gauge(
    "mcp_git_workspace_size_limit_bytes", "Maximum workspace size in bytes"
)

# Git operation metrics
GIT_OPERATIONS_TOTAL = Counter(
    "mcp_git_git_operations_total", "Total number of Git operations", ["operation", "status"]
)

CLONE_DURATION = Histogram(
    "mcp_git_clone_duration_seconds",
    "Repository clone duration in seconds",
    ["repository_type"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800],
)

# System metrics
WORKER_COUNT = Gauge("mcp_git_worker_count", "Number of active workers")

MEMORY_USAGE = Gauge("mcp_git_memory_usage_bytes", "Current memory usage in bytes")

CPU_USAGE = Gauge("mcp_git_cpu_usage_percent", "Current CPU usage percentage")

# Cache metrics
CACHE_HITS = Counter("mcp_git_cache_hits_total", "Total number of cache hits", ["cache_type"])

CACHE_MISSES = Counter("mcp_git_cache_misses_total", "Total number of cache misses", ["cache_type"])

CACHE_SIZE = Gauge("mcp_git_cache_size_bytes", "Current cache size in bytes", ["cache_type"])

# Server info
SERVER_INFO = Info("mcp_git_server", "Information about the mcp-git server")


class MetricsCollector:
    """Collector for mcp-git metrics."""

    def __init__(self) -> None:
        self._task_start_times: dict[str, tuple[str, float]] = {}
        self._repository_cache: dict[str, Any] = {}

    def record_task_start(self, task_id: str, operation: str) -> None:
        """Record the start of a task."""
        self._task_start_times[task_id] = (operation, time.time())
        ACTIVE_TASKS.inc()

    def record_task_complete(self, task_id: str, status: str = "success") -> None:
        """Record the completion of a task."""
        if task_id in self._task_start_times:
            operation, start_time = self._task_start_times.pop(task_id)
            duration = time.time() - start_time

            TASKS_TOTAL.labels(operation=operation, status=status).inc()
            TASK_DURATION.labels(operation=operation).observe(duration)

        ACTIVE_TASKS.dec()

    def record_git_operation(self, operation: str, status: str = "success") -> None:
        """Record a Git operation."""
        GIT_OPERATIONS_TOTAL.labels(operation=operation, status=status).inc()

    def record_clone(self, duration: float, repository_type: str = "unknown") -> None:
        """Record a clone operation."""
        CLONE_DURATION.labels(repository_type=repository_type).observe(duration)
        GIT_OPERATIONS_TOTAL.labels(operation="clone", status="success").inc()

    def update_queue_size(self, size: int) -> None:
        """Update the queued tasks gauge."""
        QUEUED_TASKS.set(size)

    def update_workspace_metrics(self, count: int, disk_usage: int, limit: int) -> None:
        """Update workspace metrics."""
        WORKSPACE_COUNT.set(count)
        WORKSPACE_DISK_USAGE.set(disk_usage)
        WORKSPACE_SIZE_LIMIT.set(limit)

    def update_worker_count(self, count: int) -> None:
        """Update the worker count gauge."""
        WORKER_COUNT.set(count)

    def record_cache_hit(self, cache_type: str) -> None:
        """Record a cache hit."""
        CACHE_HITS.labels(cache_type=cache_type).inc()

    def record_cache_miss(self, cache_type: str) -> None:
        """Record a cache miss."""
        CACHE_MISSES.labels(cache_type=cache_type).inc()

    def update_cache_size(self, cache_type: str, size: int) -> None:
        """Update cache size gauge."""
        CACHE_SIZE.labels(cache_type=cache_type).set(size)

    def set_server_info(self, version: str, python_version: str) -> None:
        """Set server information."""
        SERVER_INFO.info(
            {
                "version": version,
                "python_version": python_version,
            }
        )


# Global metrics collector
metrics = MetricsCollector()


def track_task(operation: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to track task execution metrics."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            task_id = f"{id(func)}-{time.time()}"
            metrics.record_task_start(task_id, operation)
            try:
                result = await func(*args, **kwargs)
                metrics.record_task_complete(task_id, "success")
                return result
            except Exception:
                metrics.record_task_complete(task_id, "failed")
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            task_id = f"{id(func)}-{time.time()}"
            metrics.record_task_start(task_id, operation)
            try:
                result = func(*args, **kwargs)
                metrics.record_task_complete(task_id, "success")
                return result
            except Exception:
                metrics.record_task_complete(task_id, "failed")
                raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def track_git_operation(operation: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to track Git operation metrics."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                if operation == "clone":
                    metrics.record_clone(duration)
                else:
                    metrics.record_git_operation(operation, "success")
                return result
            except Exception:
                metrics.record_git_operation(operation, "failed")
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                if operation == "clone":
                    metrics.record_clone(duration)
                else:
                    metrics.record_git_operation(operation, "success")
                return result
            except Exception:
                metrics.record_git_operation(operation, "failed")
                raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class Cache:
    """Moka-based cache with metrics."""

    def __init__(self, max_size: int = 1000, ttl: int = 3600) -> None:
        self._cache: Any = None
        self._max_size = max_size
        self._ttl = ttl
        self._access_times: dict[str, float] = {}
        self._use_moka = False

        try:
            from moka import MokaCache

            self._cache = MokaCache(
                max_capacity=max_size,
                time_to_live=ttl,
                timer=time.time,
            )
            self._cache_type = "generic"
            self._use_moka = True
        except ImportError:
            logger.warning("moka not installed, falling back to simple dict cache")
            self._cache = {}
            self._use_moka = False

    def get(self, key: str, cache_type: str = "generic") -> Any | None:
        """Get a value from the cache."""
        if self._use_moka:
            value = self._cache.get(key)
            if value is not None:
                metrics.record_cache_hit(cache_type)
            else:
                metrics.record_cache_miss(cache_type)
            return value
        else:
            # Fallback to simple dict cache
            if key in self._cache:
                # Check TTL
                if time.time() - self._access_times[key] < self._ttl:
                    self._access_times[key] = time.time()
                    metrics.record_cache_hit(cache_type)
                    return self._cache[key]
                else:
                    # Expired
                    del self._cache[key]
                    del self._access_times[key]

            metrics.record_cache_miss(cache_type)
            return None

    def set(self, key: str, value: Any, cache_type: str = "generic") -> None:
        """Set a value in the cache."""
        if self._use_moka:
            self._cache.insert(key, value)
            metrics.update_cache_size(cache_type, len(self._cache))
        else:
            # Fallback to simple dict cache
            # Check if cache is full
            if len(self._cache) >= self._max_size:
                # Remove oldest entry
                oldest_key = min(self._access_times, key=lambda k: self._access_times[k])
                del self._cache[oldest_key]
                del self._access_times[oldest_key]

            self._cache[key] = value
            self._access_times[key] = time.time()
            metrics.update_cache_size(cache_type, len(self._cache))

    def clear(self, cache_type: str = "generic") -> None:
        """Clear the cache."""
        if self._use_moka:
            self._cache.invalidate_all()
        else:
            self._cache.clear()
            self._access_times.clear()
        metrics.update_cache_size(cache_type, 0)

    @property
    def size(self) -> int:
        """Return the cache size."""
        if self._use_moka:
            return len(self._cache)
        else:
            return len(self._cache)


# Pre-configured caches
task_state_cache = Cache(max_size=1000, ttl=3600)
git_cache = Cache(max_size=500, ttl=1800)
repository_metadata_cache = Cache(max_size=200, ttl=7200)  # 2 hours for repo metadata


def start_metrics_server(port: int = 9090) -> None:
    """Start the Prometheus metrics HTTP server."""
    start_http_server(port)


@contextmanager
def track_duration(operation: str) -> Generator[None, None, None]:
    """Context manager to track operation duration."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        TASK_DURATION.labels(operation=operation).observe(duration)
