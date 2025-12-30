"""
Metrics handlers for MCP server.
"""

import time
from pathlib import Path
from typing import Any

from mcp_git.metrics import (
    WORKSPACE_COUNT,
    WORKSPACE_DISK_USAGE,
    WORKSPACE_SIZE_LIMIT,
)


async def get_health() -> dict[str, Any]:
    """Get health status."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "uptime_seconds": time.time(),
    }


async def get_metrics() -> dict[str, Any]:
    """Get current metrics."""
    # Calculate cache hit rate

    # Get cache stats (simplified)
    cache_info = {
        "task_state": {"size": 0, "hit_rate": 0.0},
        "git": {"size": 0, "hit_rate": 0.0},
        "repository_metadata": {"size": 0, "hit_rate": 0.0},
    }

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tasks": {
            "active": 0,
            "queued": 0,
            "completed_total": 0,
            "failed_total": 0,
        },
        "workspaces": {
            "active": 0,
            "disk_usage_bytes": 0,
            "size_limit_bytes": 0,
        },
        "operations": {
            "clone": 0,
            "push": 0,
            "pull": 0,
            "fetch": 0,
            "commit": 0,
        },
        "workers": {
            "count": 0,
        },
        "cache": cache_info,
    }


def get_prometheus_metrics() -> str:
    """Get metrics in Prometheus format."""
    output = []

    # Task metrics
    output.append("# HELP mcp_git_tasks_total Total number of tasks processed")
    output.append("# TYPE mcp_git_tasks_total counter")
    output.append(f'mcp_git_tasks_total{{operation="clone",status="success"}} {0}')
    output.append(f'mcp_git_tasks_total{{operation="clone",status="failed"}} {0}')
    output.append(f'mcp_git_tasks_total{{operation="push",status="success"}} {0}')
    output.append(f'mcp_git_tasks_total{{operation="push",status="failed"}} {0}')
    output.append(f'mcp_git_tasks_total{{operation="pull",status="success"}} {0}')
    output.append(f'mcp_git_tasks_total{{operation="pull",status="failed"}} {0}')

    # Task duration
    output.append("# HELP mcp_git_task_duration_seconds Task execution duration")
    output.append("# TYPE mcp_git_task_duration_seconds histogram")
    for op in ["clone", "push", "pull", "fetch", "commit"]:
        output.append(f'mcp_git_task_duration_seconds_bucket{{operation="{op}",le="1"}} {0}')
        output.append(f'mcp_git_task_duration_seconds_bucket{{operation="{op}",le="5"}} {0}')
        output.append(f'mcp_git_task_duration_seconds_bucket{{operation="{op}",le="10"}} {0}')
        output.append(f'mcp_git_task_duration_seconds_bucket{{operation="{op}",le="+Inf"}} {0}')

    # Workspace metrics
    output.append("# HELP mcp_git_workspace_count Number of active workspaces")
    output.append("# TYPE mcp_git_workspace_count gauge")
    output.append("mcp_git_workspace_count 0")

    output.append("# HELP mcp_git_workspace_disk_usage_bytes Total disk usage by workspaces")
    output.append("# TYPE mcp_git_workspace_disk_usage_bytes gauge")
    output.append("mcp_git_workspace_disk_usage_bytes 0")

    # Git operations
    output.append("# HELP mcp_git_git_operations_total Total Git operations")
    output.append("# TYPE mcp_git_git_operations_total counter")
    output.append('mcp_git_git_operations_total{operation="clone",status="success"} 0')
    output.append('mcp_git_git_operations_total{operation="push",status="success"} 0')
    output.append('mcp_git_git_operations_total{operation="pull",status="success"} 0')

    # Worker metrics
    output.append("# HELP mcp_git_worker_count Number of active workers")
    output.append("# TYPE mcp_git_worker_count gauge")
    output.append("mcp_git_worker_count 0")

    # Cache metrics
    output.append("# HELP mcp_git_cache_hits_total Total cache hits")
    output.append("# TYPE mcp_git_cache_hits_total counter")
    output.append('mcp_git_cache_hits_total{cache_type="task_state"} 0')
    output.append('mcp_git_cache_hits_total{cache_type="git"} 0')
    output.append('mcp_git_cache_hits_total{cache_type="repository_metadata"} 0')

    output.append("# HELP mcp_git_cache_misses_total Total cache misses")
    output.append("# TYPE mcp_git_cache_misses_total counter")
    output.append('mcp_git_cache_misses_total{cache_type="task_state"} 0')
    output.append('mcp_git_cache_misses_total{cache_type="git"} 0')
    output.append('mcp_git_cache_misses_total{cache_type="repository_metadata"} 0')

    return "\n".join(output)


def update_workspace_metrics(workspace_path: Path, max_size_bytes: int):
    """Update workspace-related metrics."""

    total_size = 0
    workspace_count = 0

    if workspace_path.exists():
        for item in workspace_path.iterdir():
            if item.is_dir():
                workspace_count += 1
                total_size += sum(f.stat().st_size for f in item.rglob("*") if f.is_file())

    WORKSPACE_COUNT.set(workspace_count)
    WORKSPACE_DISK_USAGE.set(total_size)
    WORKSPACE_SIZE_LIMIT.set(max_size_bytes)
