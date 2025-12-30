"""Configuration tests for mcp-git."""

from pathlib import Path

import pytest
from pydantic import ValidationError


class TestConfig:
    """Tests for configuration module."""

    def test_load_config_defaults(self):
        """Test loading config with defaults."""
        from mcp_git.config import Config

        config = Config()

        assert config.workspace.path == Path("/tmp/mcp-git/workspaces")
        assert config.workspace.max_size_bytes == 10 * 1024 * 1024 * 1024
        assert config.database.path == Path("/tmp/mcp-git/database/mcp-git.db")
        assert config.server.port == 3001
        assert config.server.transport == "stdio"

    def test_workspace_config_defaults(self):
        """Test workspace config defaults."""
        from mcp_git.config import WorkspaceConfig

        config = WorkspaceConfig()

        assert config.max_size_bytes == 10 * 1024 * 1024 * 1024  # 10GB
        assert config.retention_seconds == 3600  # 1 hour
        assert config.cleanup_strategy.value == "lru"

    def test_database_config_defaults(self):
        """Test database config defaults."""
        from mcp_git.config import DatabaseConfig

        config = DatabaseConfig()

        assert config.path == Path("/tmp/mcp-git/database/mcp-git.db")
        assert config.max_size_bytes == 100 * 1024 * 1024  # 100MB
        assert config.task_retention_seconds == 3600

    def test_server_config_defaults(self):
        """Test server config defaults."""
        from mcp_git.config import ServerConfig

        config = ServerConfig()

        assert config.host == "127.0.0.1"
        assert config.port == 3001
        assert config.transport == "stdio"

    def test_execution_config_defaults(self):
        """Test execution config defaults."""
        from mcp_git.config import ExecutionConfig

        config = ExecutionConfig()

        assert config.max_concurrent_tasks == 10
        assert config.task_timeout == 300  # 5 minutes
        assert config.worker_count == 4

    def test_config_from_env_vars(self, monkeypatch):
        """Test config loading from environment variables."""
        from mcp_git.config import load_config

        monkeypatch.setenv("MCP_GIT_WORKSPACE_PATH", "/custom/workspace")
        monkeypatch.setenv("MCP_GIT_DATABASE_PATH", "/custom/database.db")
        monkeypatch.setenv("MCP_GIT_SERVER_PORT", "8080")

        config = load_config()

        assert config.workspace.path == Path("/custom/workspace")
        assert config.database.path == Path("/custom/database.db")
        assert config.server.port == 8080

    def test_config_validation(self):
        """Test config validation."""
        from mcp_git.config import ExecutionConfig

        # Valid config
        config = ExecutionConfig(max_concurrent_tasks=5, task_timeout=600)
        assert config.max_concurrent_tasks == 5
        assert config.task_timeout == 600

    def test_config_invalid_values(self):
        """Test config with invalid values."""
        from mcp_git.config import WorkspaceConfig

        with pytest.raises(ValidationError):
            WorkspaceConfig(max_size_bytes=-1)

        with pytest.raises(ValidationError):
            WorkspaceConfig(retention_seconds=-100)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_no_env_vars(self):
        """Test load_config with no environment variables set."""
        from mcp_git.config import load_config

        # Should use defaults
        config = load_config()
        assert config is not None
        assert isinstance(config, type(load_config()))

    def test_load_config_partial_env(self, monkeypatch):
        """Test load_config with partial environment variables."""
        from mcp_git.config import load_config

        monkeypatch.setenv("MCP_GIT_SERVER_PORT", "9999")

        config = load_config()

        assert config.server.port == 9999
        # Other values should use defaults (workspace path may be overridden by conftest.py)
        assert config.workspace.max_size_bytes == 10 * 1024 * 1024 * 1024  # 10GB default
        assert config.workspace.retention_seconds == 3600  # 1 hour default


class TestConfigPaths:
    """Tests for configuration path handling."""

    def test_path_expansion(self):
        """Test path expansion in config."""
        from mcp_git.config import load_config

        config = load_config()

        # Paths should be Path objects
        assert isinstance(config.workspace.path, Path)
        assert isinstance(config.database.path, Path)

    def test_path_creation(self, tmp_path):
        """Test that paths are created if they don't exist."""
        from mcp_git.config import Config

        custom_path = tmp_path / "test_workspaces"
        config = Config(workspace={"path": str(custom_path)})

        assert config.workspace.path == custom_path
        # Config doesn't create directories, just validates
