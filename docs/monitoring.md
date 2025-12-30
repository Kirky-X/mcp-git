# mcp-git Monitoring Guide

This document describes the monitoring and metrics capabilities of mcp-git.

## Health Check

### Endpoint

```http
GET /health
```

### Response

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime_seconds": 3600
}
```

### Status Values

| Status | Description |
|--------|-------------|
| `healthy` | All systems operational |
| `degraded` | Some systems not optimal |
| `unhealthy` | Critical systems down |

### Using the Tool

```python
# Via MCP Tool
result = await mcp_server.git_get_health()
print(result)
```

---

## Metrics

### Endpoint

```http
GET /metrics
```

### Response (Prometheus Format)

```
# HELP mcp_git_active_tasks Number of currently running tasks
# TYPE mcp_git_active_tasks gauge
mcp_git_active_tasks 2

# HELP mcp_git_queued_tasks Number of tasks waiting in queue
# TYPE mcp_git_queued_tasks gauge
mcp_git_queued_tasks 5

# HELP mcp_git_completed_tasks_total Total number of completed tasks
# TYPE mcp_git_completed_tasks_total counter
mcp_git_completed_tasks_total 100

# HELP mcp_git_failed_tasks_total Total number of failed tasks
# TYPE mcp_git_failed_tasks_total counter
mcp_git_failed_tasks_total 2

# HELP mcp_git_task_duration_seconds Task execution duration
# TYPE mcp_git_task_duration_seconds histogram
mcp_git_task_duration_seconds_bucket{le="1"} 50
mcp_git_task_duration_seconds_bucket{le="5"} 80
mcp_git_task_duration_seconds_bucket{le="10"} 95
mcp_git_task_duration_seconds_bucket{le="+Inf"} 100

# HELP mcp_git_workspace_count Number of active workspaces
# TYPE mcp_git_workspace_count gauge
mcp_git_workspace_count 10

# HELP mcp_git_workspace_disk_usage_bytes Disk usage by workspaces
# TYPE mcp_git_workspace_disk_usage_bytes gauge
mcp_git_workspace_disk_usage_bytes 5368709120

# HELP mcp_git_clone_operations_total Total clone operations
# TYPE mcp_git_clone_operations_total counter
mcp_git_clone_operations_total 25

# HELP mcp_git_push_operations_total Total push operations
# TYPE mcp_git_push_operations_total counter
mcp_git_push_operations_total 15

# HELP mcp_git_pull_operations_total Total pull operations
# TYPE mcp_git_pull_operations_total counter
mcp_git_pull_operations_total 20
```

### Using the Tool

```python
# Via MCP Tool
result = await mcp_server.git_get_metrics()
print(result)
```

---

## Available Metrics

### Task Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `mcp_git_active_tasks` | Gauge | Number of tasks currently running |
| `mcp_git_queued_tasks` | Gauge | Number of tasks waiting to be processed |
| `mcp_git_completed_tasks_total` | Counter | Total tasks completed |
| `mcp_git_failed_tasks_total` | Counter | Total tasks that failed |
| `mcp_git_task_duration_seconds` | Histogram | Task execution time |

### Workspace Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `mcp_git_workspace_count` | Gauge | Number of active workspaces |
| `mcp_git_workspace_disk_usage_bytes` | Gauge | Total disk usage by workspaces |

### Operation Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `mcp_git_clone_operations_total` | Counter | Total clone operations |
| `mcp_git_push_operations_total` | Counter | Total push operations |
| `mcp_git_pull_operations_total` | Counter | Total pull operations |
| `mcp_git_fetch_operations_total` | Counter | Total fetch operations |
| `mcp_git_commit_operations_total` | Counter | Total commit operations |

### System Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `mcp_git_worker_count` | Gauge | Number of active workers |
| `mcp_git_memory_usage_bytes` | Gauge | Memory usage |
| `mcp_git_cpu_usage_percent` | Gauge | CPU usage percentage |

---

## Alerting Rules

### Recommended Alert Rules (Prometheus)

```yaml
groups:
  - name: mcp-git-alerts
    rules:
      # High task queue depth
      - alert: McpGitHighTaskQueue
        expr: mcp_git_queued_tasks > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High task queue depth"
          description: "Task queue has {{ $value }} pending tasks"

      # High failure rate
      - alert: McpGitHighFailureRate
        expr: |
          rate(mcp_git_failed_tasks_total[5m]) /
          rate(mcp_git_completed_tasks_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High task failure rate"
          description: "Failure rate is above 10%"

      # Disk space warning
      - alert: McpGitDiskSpaceWarning
        expr: mcp_git_workspace_disk_usage_bytes > 0.8 * 10737418240
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Workspace disk space running low"
          description: "Disk usage is above 80%"

      # Worker offline
      - alert: McpGitWorkerOffline
        expr: mcp_git_worker_count < 2
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Few workers available"
          description: "Only {{ $value }} workers running"
```

---

## Grafana Dashboard

### Dashboard JSON

```json
{
  "dashboard": {
    "title": "mcp-git Overview",
    "panels": [
      {
        "title": "Task Queue",
        "type": "graph",
        "targets": [
          {
            "expr": "mcp_git_active_tasks",
            "legendFormat": "Active Tasks"
          },
          {
            "expr": "mcp_git_queued_tasks",
            "legendFormat": "Queued Tasks"
          }
        ]
      },
      {
        "title": "Operations per Minute",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(mcp_git_clone_operations_total[1m])",
            "legendFormat": "Clones"
          },
          {
            "expr": "rate(mcp_git_push_operations_total[1m])",
            "legendFormat": "Pushes"
          },
          {
            "expr": "rate(mcp_git_pull_operations_total[1m])",
            "legendFormat": "Pulls"
          }
        ]
      },
      {
        "title": "Task Duration",
        "type": "heatmap",
        "targets": [
          {
            "expr": "rate(mcp_git_task_duration_seconds_bucket[5m])",
            "legendFormat": "{{ le }}"
          }
        ]
      },
      {
        "title": "Failure Rate",
        "type": "gauge",
        "targets": [
          {
            "expr": "rate(mcp_git_failed_tasks_total[5m]) / rate(mcp_git_completed_tasks_total[5m]) * 100",
            "legendFormat": "Failure %"
          }
        ]
      }
    ]
  }
}
```

---

## Logging

### Log Levels

| Level | Description |
|-------|-------------|
| `debug` | Detailed debug information |
| `info` | General informational messages |
| `warning` | Warning conditions |
| `error` | Error conditions |

### Log Format

Logs are output in JSON format by default:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "info",
  "message": "Task completed",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "operation": "clone",
  "duration_ms": 1250
}
```

### Sensitive Data Redaction

Credentials and tokens are automatically redacted from logs:

```
# Before redaction
{"token": "ghp_abc123xyz"}

# After redaction
{"token": "[REDACTED]"}
```

---

## Performance Benchmarks

### Expected Performance

| Operation | Expected Duration | Notes |
|-----------|-------------------|-------|
| Clone (small repo) | < 5 seconds | < 1MB, shallow clone |
| Clone (medium repo) | < 30 seconds | < 10MB, shallow clone |
| Clone (large repo) | < 5 minutes | > 100MB |
| Status check | < 100ms | Cached when possible |
| Add file | < 50ms | Local operation |
| Commit | < 100ms | Local operation |
| Push | < 10 seconds | Network dependent |
| Pull | < 10 seconds | Network dependent |

### Performance Tuning

For better performance:

1. **Increase worker count** for higher throughput
2. **Use shallow clone** (`depth=1`) when possible
3. **Use partial clone** (`filter=blob:none`) for large repositories
4. **Increase timeout** for large repository operations
5. **Monitor disk I/O** for storage-bound operations

---

## Troubleshooting

### High Memory Usage

1. Check active workspaces: `git_list_workspaces`
2. Release unused workspaces: `git_release_workspace`
3. Reduce `MCP_GIT_WORKER_COUNT`
4. Check for memory leaks in long-running processes

### Slow Operations

1. Check disk space: `git_get_metrics`
2. Verify network connectivity
3. Check repository size before cloning
4. Consider using shallow clone

### Task Failures

1. Check task status: `git_get_task`
2. Review logs for error messages
3. Verify credentials are set correctly
4. Check network connectivity for remote operations
