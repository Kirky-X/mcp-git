# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

mcp-git is a Git operations MCP (Model Context Protocol) server written in Python that enables AI Agents to perform Git operations through a standardized interface. The service provides async task management, credential security, and supports large repository operations with optimizations like shallow cloning and sparse checkout.

**Primary Users**: AI Agent developers building LLM-powered code generation, analysis, and automation tools.

## Common Commands

```bash
# Setup
python -m venv venv              # Create virtual environment
source venv/bin/activate          # Activate virtual environment (Linux/Mac)
.\venv\Scripts\activate           # Activate virtual environment (Windows)
pip install -e ".[dev]"           # Install in development mode with dev dependencies

# Build and run
python -m mcp_git                 # Run in debug mode
python -m mcp_git --reload        # Run with auto-reload (development)

# Using uv (recommended)
uv run python -m mcp_git          # Run with uv
uv run pytest                     # Run tests
uv run ruff check .               # Run linter
uv run ruff format .              # Format code

# Testing
pytest                            # Run all tests
pytest -v                         # Run tests with verbose output
pytest tests/                     # Run tests in specific directory
pytest -k test_name               # Run specific test

# Code quality
ruff check .                      # Run linter
ruff format .                     # Format code
mypy .                            # Type checking
pytest --cov=mcp_git              # Run tests with coverage

# Documentation
mkdocs serve                     # Serve documentation locally
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AI Agent / MCP Client                   │
└────────────────────────┬────────────────────────────────────┘
                         │ MCP Protocol
┌────────────────────────▼────────────────────────────────────┐
│  MCP Protocol Layer (mcp_git/mcp/)                           │
│  ├── __init__.py       - MCP server initialization           │
│  ├── tools.py          - Tool definitions (JSON Schema)      │
│  └── handlers.py       - Tool request handlers               │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  Business Logic Layer (mcp_git/service/)                     │
│  ├── facade.py         - GitService facade (orchestration)   │
│  ├── task_manager.py   - Task lifecycle, timeout, retention  │
│  ├── workspace_manager.py - Workspace allocation, cleanup    │
│  └── credential_manager.py - Credentials (secrecy/zeroize)   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  Execution Layer (mcp_git/executor/)                         │
│  ├── queue.py          - Async task queue (asyncio.Queue)    │
│  ├── worker.py         - Worker pool for task execution      │
│  └── progress.py       - Progress tracking                   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  Git Operation Layer (mcp_git/git/)                          │
│  ├── adapter.py        - GitAdapter abstract base class      │
│  ├── adapter_git2.py   - Primary implementation (GitPython)  │
│  ├── cli_adapter.py    - Fallback CLI implementation         │
│  └── options.py        - Operation options (clone, merge, etc)│
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  Storage Layer (mcp_git/storage/)                            │
│  ├── sqlite.py         - SQLite operations                   │
│  ├── models.py         - Task, Workspace, OperationLog models│
│  └── migrations.py     - Database migrations (alembic)       │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Patterns

**Facade Pattern**: `GitService` (mcp_git/service/facade.py) orchestrates TaskManager, WorkspaceManager, CredentialManager, and GitAdapter - simplifies complex operations for MCP handlers.

**Adapter Pattern**: `GitAdapter` ABC with two implementations:
- `GitPythonAdapter` (primary): Uses GitPython for native Git operations
- `CliAdapter` (fallback): Shell out to `git` CLI for unsupported operations

**Async Task Queue**: Long-running Git operations (clone, push, pull) return `task_id` immediately; status polled via `get-task-status`.

### Data Flow (Async Operation Example)

```
1. MCP Client → git-clone tool
2. Handler → GitService.facade.clone_repository()
3. Facade → WorkspaceManager.allocate() → returns workspace_path
4. Facade → TaskManager.create_task() → returns task_id
5. Facade → TaskManager.queue_task() → enqueues task
6. Response → { task_id: "uuid", status: "queued" }
7. Worker Pool dequeues → executes clone
8. Progress → TaskManager.update_progress()
9. Client polls → get-task-status(task_id)
10. Final response → { status: "completed", workspace: "/path" }
```

## Project Structure

```
mcp-git/
├── mcp_git/
│   ├── __init__.py          # Package exports
│   ├── __main__.py          # Entry point
│   ├── config.py            # Configuration (pydantic-settings)
│   ├── exceptions.py        # Custom exceptions
│   ├── mcp/                 # MCP protocol layer
│   ├── service/             # Business logic
│   ├── executor/            # Async execution
│   ├── git/                 # Git operations
│   └── storage/             # SQLite persistence
├── tests/                   # Test suite
├── docs/                    # Documentation (PRD, TDD, TASK, TEST, UAT)
├── templeate/               # PRD template
├── pyproject.toml           # Project configuration
└── requirements.txt         # Dependencies
```

## Configuration

Environment variables (see `mcp_git/config.py`):

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_GIT_WORKSPACE_ROOT` | Workspace directory | `/tmp/mcp-git-workspaces` |
| `MCP_GIT_WORKSPACE_RETENTION` | Workspace TTL (seconds) | 3600 |
| `MCP_GIT_MAX_WORKSPACE_SIZE` | Max workspace size (bytes) | 10GB |
| `MCP_GIT_WORKER_COUNT` | Worker pool size | 4 |
| `MCP_GIT_TASK_QUEUE_SIZE` | Max queued tasks | 100 |
| `MCP_GIT_TASK_TIMEOUT` | Task timeout (seconds) | 1800 |
| `GIT_TOKEN` | Git access token | - |
| `MCP_GIT_LOG_LEVEL` | Log level (debug, info, warn, error) | `info` |
| `DATABASE_URL` | SQLite database path | `sqlite:///./mcp_git.db` |

## Security

- **Credentials**: Use `python-dotenv` and encryption for credential handling
- **Path Validation**: All paths validated against workspace root to prevent path traversal
- **Command Injection**: CLI adapter sanitizes all inputs with allowlist approach
- **Logs**: Sensitive data (tokens, passwords) automatically redacted using `logging` filters

## Key Error Codes

See `mcp_git/exceptions.py` for complete error type hierarchy:

| Code | Meaning | User Message |
|------|---------|--------------|
| `RepoNotFoundError` | Repository URL invalid/not found | "Repository not found" |
| `AuthError` | Authentication error | "Authentication failed" |
| `MergeConflictError` | Merge conflict detected | "Merge conflict in files: ..." |
| `TaskNotFoundError` | Task ID invalid | "Task not found" |
| `WorkspaceError` | Workspace issues | Context-dependent |

## Development Notes

### Adding New Git Operations

1. Define abstract method in `GitAdapter` ABC (mcp_git/git/adapter.py)
2. Implement in `GitPythonAdapter` (mcp_git/git/adapter_git2.py)
3. Create Tool definition (mcp_git/mcp/tools.py)
4. Implement Handler (mcp_git/mcp/handlers.py)
5. Add tests (tests/)

### Testing Strategy

- **Unit Tests**: Per-module tests using `tempfile` for isolated repos and `pytest`
- **Integration Tests**: End-to-end workflows in `tests/mcp_git_test.py`
- **Async Tests**: Use `pytest-asyncio` for testing async code
- **Fixtures**: Use `pytest fixtures` for database and workspace setup

### Database Schema

SQLite stores:
- `tasks` - Task records with status, params, result, progress
- `workspaces` - Workspace metadata with size and access time
- `operation_logs` - Audit logs for operations

Using SQLAlchemy ORM with async support.

## Documentation Hierarchy

| Document | Purpose |
|----------|---------|
| `docs/prd.md` | Product requirements and user analysis |
| `docs/tdd.md` | Technical architecture and design |
| `docs/task.md` | Development task breakdown with dependencies |
| `docs/test.md` | Comprehensive testing strategy |
| `docs/uat.md` | User acceptance criteria |
| `templeate/prd-template.md` | PRD template for new features |

## Python Version Requirements

- Python 3.10 or higher
- Requires asyncio support for async task management
