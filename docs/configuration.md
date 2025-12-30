# mcp-git Configuration Guide

This document describes all configuration options available in mcp-git.

## Environment Variables

### Workspace Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MCP_GIT_WORKSPACE_PATH` | Root directory for temporary workspaces | `/tmp/mcp-git/workspaces` | No |
| `MCP_GIT_WORKSPACE_RETENTION` | Workspace retention time in seconds | `3600` (1 hour) | No |
| `MCP_GIT_MAX_WORKSPACE_SIZE` | Maximum workspace size in bytes | `10737418240` (10GB) | No |
| `MCP_GIT_CLEANUP_STRATEGY` | Cleanup strategy (`lru` or `fifo`) | `lru` | No |

### Database Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MCP_GIT_DATABASE_PATH` | SQLite database path | `/tmp/mcp-git/database/mcp-git.db` | No |

### Server Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MCP_GIT_SERVER_HOST` | Server host address | `127.0.0.1` | No |
| `MCP_GIT_SERVER_PORT` | Server port | `3001` | No |
| `MCP_GIT_SERVER_TRANSPORT` | Transport type (`stdio`, `sse`) | `stdio` | No |

### Execution Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MCP_GIT_WORKER_COUNT` | Number of worker threads | `4` | No |
| `MCP_GIT_MAX_CONCURRENT_TASKS` | Maximum concurrent tasks | `10` | No |
| `MCP_GIT_TASK_TIMEOUT` | Task timeout in seconds | `300` (5 minutes) | No |
| `MCP_GIT_RESULT_RETENTION` | Result retention in seconds | `3600` (1 hour) | No |

### Git Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GIT_TOKEN` | Git access token | - | Conditionally |
| `MCP_GIT_GIT_TOKEN` | Alternative Git token variable | - | Conditionally |
| `GIT_USERNAME` | Git username | - | Conditionally |
| `GIT_PASSWORD` | Git password | - | Conditionally |
| `GIT_SSH_KEY_PATH` | SSH private key path | - | Conditionally |
| `GIT_SSH_PASSPHRASE` | SSH key passphrase | - | Conditionally |
| `MCP_GIT_DEFAULT_CLONE_DEPTH` | Default shallow clone depth | `1` | No |

### Logging Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MCP_GIT_LOG_LEVEL` | Log level (`debug`, `info`, `warning`, `error`) | `info` | No |

---

## Configuration File

You can also use a YAML configuration file:

```yaml
workspace:
  path: "/tmp/mcp-git/workspaces"
  max_size_bytes: 10737418240  # 10GB
  retention_seconds: 3600
  cleanup_strategy: "lru"

database:
  path: "/tmp/mcp-git/database/mcp-git.db"
  max_size_bytes: 104857600  # 100MB
  task_retention_seconds: 3600

server:
  host: "127.0.0.1"
  port: 3001
  transport: "stdio"

execution:
  max_concurrent_tasks: 10
  task_timeout: 300
  worker_count: 4
  max_retries: 3

git:
  token: "${GIT_TOKEN}"  # Can use environment variables
  default_clone_depth: 1

logging:
  level: "info"
  format: "json"
```

---

## Credential Configuration

### GitHub Token

For GitHub repositories, set your personal access token:

```bash
export GIT_TOKEN="ghp_your_token_here"
```

Create a token at: https://github.com/settings/tokens

Required scopes:
- `repo`: Full control of private repositories
- `read:user`: Read user profile data

### SSH Key

For SSH authentication:

```bash
export GIT_SSH_KEY_PATH="/path/to/private_key"
export GIT_SSH_PASSPHRASE="your_passphrase"  # Optional
```

### Username/Password

For basic authentication:

```bash
export GIT_USERNAME="your_username"
export GIT_PASSWORD="your_password"
```

---

## Docker Configuration

### Using Docker

```bash
docker run -d \
  --name mcp-git \
  -p 3001:3001 \
  -v /tmp/mcp-git-workspaces:/tmp/mcp-git-workspaces \
  -v /tmp/mcp-git-database:/tmp/mcp-git/database \
  -e GIT_TOKEN="your_token" \
  mcp-git:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  mcp-git:
    image: mcp-git:latest
    ports:
      - "3001:3001"
    volumes:
      - workspaces:/tmp/mcp-git/workspaces
      - database:/tmp/mcp-git/database
    environment:
      - GIT_TOKEN=${GIT_TOKEN}
      - MCP_GIT_WORKER_COUNT=4
      - MCP_GIT_LOG_LEVEL=info
    restart: unless-stopped

volumes:
  workspaces:
  database:
```

---

## Production Configuration

### High Performance

```bash
# Increase worker count for higher throughput
export MCP_GIT_WORKER_COUNT=8
export MCP_GIT_MAX_CONCURRENT_TASKS=20

# Increase task timeout for large repositories
export MCP_GIT_TASK_TIMEOUT=1800  # 30 minutes

# Increase workspace size for multiple large repos
export MCP_GIT_MAX_WORKSPACE_SIZE=53687091200  # 50GB
export MCP_GIT_WORKSPACE_RETENTION=7200  # 2 hours
```

### Resource Constrained

```bash
# Reduce resource usage
export MCP_GIT_WORKER_COUNT=2
export MCP_GIT_MAX_CONCURRENT_TASKS=5
export MCP_GIT_TASK_TIMEOUT=60
export MCP_GIT_MAX_WORKSPACE_SIZE=2147483648  # 2GB
```

---

## Security Considerations

### Sensitive Data

- Never commit configuration files with credentials to version control
- Use environment variables or secret management systems
- Credentials are automatically redacted from logs

### Path Security

- Workspaces are automatically created with restricted permissions
- Path traversal attacks are prevented through sanitization
- Absolute paths outside workspace are rejected

### Network Security

- HTTPS is used by default for Git operations
- SSH keys are read from file, never passed as command-line arguments
- Certificate validation is enabled by default

---

## Configuration Precedence

Configuration values are loaded in the following order (later values override earlier):

1. Hard-coded defaults
2. Configuration file
3. Environment variables

Example:

```bash
# config.yaml sets port to 3001
# Environment variable overrides:
export MCP_GIT_SERVER_PORT=8080

# Final port will be 8080
```

---

## Validation

Validate your configuration before starting the server:

```python
from mcp_git.config import load_config

config = load_config()

# Check workspace path
import os
if not os.path.exists(config.workspace.path):
    os.makedirs(config.workspace.path, exist_ok=True)

# Check database directory
db_dir = config.database.path.parent
if not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

print("Configuration validated successfully!")
```
