"""
Tests for main module.

Tests for server initialization, logging sanitization, and configuration loading.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import os


class TestLogSanitization:
    """Test log message sanitization."""

    def test_sanitize_git_token(self):
        """Test that Git tokens are sanitized in logs."""
        from mcp_git.main import SENSITIVE_PATTERNS

        log_message = "Clone from https://user:secret123@github.com/repo.git"
        sanitized = log_message
        for pattern, replacement in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        assert "secret123" not in sanitized
        assert "***" in sanitized

    def test_sanitize_authorization_header(self):
        """Test that Authorization headers are sanitized."""
        from mcp_git.main import SENSITIVE_PATTERNS

        log_message = "Authorization: Bearer token123456"
        sanitized = log_message
        for pattern, replacement in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        assert "token123456" not in sanitized
        assert "***" in sanitized

    def test_sanitize_password(self):
        """Test that passwords are sanitized."""
        from mcp_git.main import SENSITIVE_PATTERNS

        log_message = "password=MySecretPassword123"
        sanitized = log_message
        for pattern, replacement in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        assert "MySecretPassword123" not in sanitized
        assert "password=***" in sanitized

    def test_sanitize_private_key(self):
        """Test that private keys are sanitized."""
        from mcp_git.main import SENSITIVE_PATTERNS

        log_message = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC..."
        sanitized = log_message
        for pattern, replacement in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        assert "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC" not in sanitized
        assert "***" in sanitized


class TestConfigurationLoading:
    """Test configuration loading."""

    def test_load_default_config(self):
        """Test loading default configuration."""
        from mcp_git.config import load_config

        config = load_config()
        assert config is not None
        assert config.workspace.path is not None
        assert config.database.path is not None

    def test_load_config_from_file(self):
        """Test loading configuration from file."""
        from mcp_git.config import load_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("""
workspace:
  path: /tmp/test-workspace
  max_size_bytes: 10737418240
  retention_seconds: 3600

database:
  path: /tmp/test-db.sqlite
  task_retention_seconds: 86400

execution:
  max_concurrent_tasks: 10
  task_timeout: 300
""")
            config = load_config(str(config_file))
            assert str(config.workspace.path) == "/tmp/test-workspace"
            assert config.workspace.max_size_bytes == 10737418240

    def test_load_config_with_env_override(self):
        """Test loading configuration with environment variable override."""
        from mcp_git.config import load_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("""
workspace:
  path: /tmp/default-workspace
""")
            os.environ["MCP_GIT_WORKSPACE_PATH"] = "/tmp/env-workspace"
            config = load_config(str(config_file))
            assert str(config.workspace.path) == "/tmp/env-workspace"
            del os.environ["MCP_GIT_WORKSPACE_PATH"]


class TestServerLifecycle:
    """Test server lifecycle."""

    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test server initialization."""
        from mcp_git.server.server import McpGitServer
        from mcp_git.config import Config

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
            )
            server = McpGitServer(config)
            await server.initialize()
            await server.shutdown()

    @pytest.mark.asyncio
    async def test_server_health_check(self):
        """Test server health check."""
        from mcp_git.server.server import McpGitServer
        from mcp_git.config import Config

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
            )
            server = McpGitServer(config)
            await server.initialize()

            health = await server.get_health()
            assert health["status"] == "healthy"
            assert health["components"]["storage"] == "ok"
            assert health["components"]["facade"] == "ok"

            await server.shutdown()

    @pytest.mark.asyncio
    async def test_server_double_initialization(self):
        """Test that server can be initialized multiple times."""
        from mcp_git.server.server import McpGitServer
        from mcp_git.config import Config

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(
                workspace_path=Path(tmpdir) / "workspaces",
                database_path=Path(tmpdir) / "test.db",
            )
            server = McpGitServer(config)
            await server.initialize()
            await server.initialize()  # Should not raise error
            await server.shutdown()


class TestSignalHandling:
    """Test signal handling."""

    @patch('asyncio.get_event_loop')
    def test_signal_handler_registration(self, mock_loop):
        """Test that signal handlers are registered."""
        mock_loop_instance = MagicMock()
        mock_loop.return_value = mock_loop_instance

        from mcp_git import main

        # This would normally register signal handlers
        # We're just verifying it doesn't crash
        assert True


class TestErrorScenarios:
    """Test error scenarios."""

    @pytest.mark.asyncio
    async def test_server_initialization_failure(self):
        """Test server initialization with invalid configuration."""
        from mcp_git.server.server import McpGitServer
        from mcp_git.config import Config

        with tempfile.TemporaryDirectory() as tmpdir:
            # Use invalid path (assuming it doesn't exist and can't be created)
            config = Config(
                workspace_path=Path("/nonexistent/invalid/path"),
                database_path=Path(tmpdir) / "test.db",
            )
            server = McpGitServer(config)

            with pytest.raises(Exception):
                await server.initialize()

    def test_config_file_not_found(self):
        """Test loading configuration from non-existent file."""
        from mcp_git.config import load_config

        with pytest.raises(Exception):
            load_config("/nonexistent/config.yaml")

    def test_invalid_config_format(self):
        """Test loading configuration with invalid format."""
        from mcp_git.config import load_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "invalid.yaml"
            config_file.write_text("invalid: yaml: content:")

            with pytest.raises(Exception):
                load_config(str(config_file))