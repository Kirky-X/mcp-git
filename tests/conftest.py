"""
Pytest configuration and fixtures for mcp-git tests.
"""

import asyncio
import os
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# Set test environment variables before imports
os.environ["MCP_GIT_WORKSPACE_PATH"] = "/tmp/mcp-git-test/workspaces"
os.environ["MCP_GIT_DATABASE_PATH"] = "/tmp/mcp-git-test/database/mcp-git.db"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_workspace_dir(temp_dir: Path) -> Path:
    """Create a temporary workspace directory."""
    workspace_dir = temp_dir / "workspaces"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    return workspace_dir


@pytest_asyncio.fixture
async def temp_database(temp_dir: Path) -> Path:
    """Create a temporary database file."""
    db_path = temp_dir / "test.db"
    return db_path


@pytest_asyncio.fixture
async def mock_storage(temp_database: Path) -> AsyncGenerator[MagicMock, None]:
    """Create a mock storage for testing."""
    from mcp_git.storage import SqliteStorage
    from mcp_git.storage.models import Task, TaskStatus

    storage = SqliteStorage(temp_database)
    await storage.initialize()

    # Create mock tasks
    mock_task = Task(
        id=None,  # Will be set by storage
        operation=None,
        status=TaskStatus.QUEUED,
        params={},
    )

    # Mock storage methods
    storage.create_task = AsyncMock(return_value=mock_task)
    storage.get_task = AsyncMock(return_value=None)
    storage.update_task = AsyncMock(return_value=True)
    storage.list_tasks = AsyncMock(return_value=[])
    storage.create_workspace = AsyncMock()
    storage.get_workspace = AsyncMock(return_value=None)
    storage.list_workspaces = AsyncMock(return_value=[])

    yield storage

    await storage.close()


@pytest.fixture
def mock_git_adapter() -> MagicMock:
    """Create a mock Git adapter."""
    from mcp_git.git.adapter import GitAdapter

    adapter = MagicMock(spec=GitAdapter)
    adapter.clone = AsyncMock()
    adapter.init = AsyncMock()
    adapter.status = AsyncMock(return_value=[])
    adapter.add = AsyncMock()
    adapter.commit = AsyncMock(return_value="abc123")
    adapter.push = AsyncMock()
    adapter.pull = AsyncMock()
    adapter.fetch = AsyncMock()
    adapter.checkout = AsyncMock()
    adapter.list_branches = AsyncMock(return_value=[])
    adapter.create_branch = AsyncMock()
    adapter.delete_branch = AsyncMock()
    adapter.merge = AsyncMock()
    adapter.rebase = AsyncMock()
    adapter.log = AsyncMock(return_value=[])
    adapter.show = AsyncMock()
    adapter.diff = AsyncMock(return_value=[])
    adapter.blame = AsyncMock(return_value=[])
    adapter.stash = AsyncMock(return_value=None)
    adapter.list_stash = AsyncMock(return_value=[])
    adapter.list_tags = AsyncMock(return_value=[])
    adapter.create_tag = AsyncMock()
    adapter.delete_tag = AsyncMock()
    adapter.list_remotes = AsyncMock(return_value=[])
    adapter.add_remote = AsyncMock()
    adapter.remove_remote = AsyncMock()
    adapter.get_head_commit = AsyncMock(return_value=None)
    adapter.get_current_branch = AsyncMock(return_value=None)
    adapter.is_repository = AsyncMock(return_value=True)
    adapter.count_commits = AsyncMock(return_value=0)
    adapter.is_merged = AsyncMock(return_value=True)

    return adapter


@pytest.fixture
def sample_clone_options() -> dict:
    """Sample clone options."""
    return {
        "url": "https://github.com/example/repo.git",
        "branch": "main",
        "depth": 1,
    }


@pytest.fixture
def sample_commit_options() -> dict:
    """Sample commit options."""
    return {
        "message": "Test commit",
        "author_name": "Test User",
        "author_email": "test@example.com",
    }


@pytest.fixture
def sample_push_options() -> dict:
    """Sample push options."""
    return {
        "remote": "origin",
        "branch": "main",
        "force": False,
    }


@pytest.fixture
def sample_pull_options() -> dict:
    """Sample pull options."""
    return {
        "remote": "origin",
        "branch": "main",
        "rebase": False,
    }


@pytest.fixture
def sample_workspace_id() -> str:
    """Sample workspace ID."""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest_asyncio.fixture
async def initialized_storage(temp_database: Path) -> AsyncGenerator:
    """Create and initialize a storage instance."""
    from mcp_git.storage import SqliteStorage

    storage = SqliteStorage(temp_database)
    await storage.initialize()

    yield storage

    await storage.close()
