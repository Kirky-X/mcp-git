"""Tests for configuration management and hot-reload functionality."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_git.config import Config
from mcp_git.config_watcher import ConfigManager, ConfigWatcher


class TestConfigWatcher:
    """Tests for ConfigWatcher class."""

    @pytest.fixture
    def sample_config(self):
        """Create a sample configuration."""
        return Config()

    def test_initialization(self, sample_config):
        """Test ConfigWatcher initialization."""
        watcher = ConfigWatcher(config=sample_config)

        assert watcher.config == sample_config
        assert watcher._running is False
        assert len(watcher._change_callbacks) == 0

    def test_add_change_callback(self, sample_config):
        """Test adding change callbacks."""
        watcher = ConfigWatcher(config=sample_config)

        callback = MagicMock()
        watcher.add_change_callback(callback)

        assert len(watcher._change_callbacks) == 1
        assert watcher._change_callbacks[0] == callback

    def test_remove_change_callback(self, sample_config):
        """Test removing change callbacks."""
        watcher = ConfigWatcher(config=sample_config)

        callback = MagicMock()
        watcher.add_change_callback(callback)
        watcher.remove_change_callback(callback)

        assert len(watcher._change_callbacks) == 0

    def test_get_config_value(self, sample_config):
        """Test getting configuration values."""
        watcher = ConfigWatcher(config=sample_config)

        # Test getting existing value
        value = watcher.get("workspace.path")
        assert value == sample_config.workspace.path

        # Test getting non-existing value with default
        value = watcher.get("nonexistent.key", "default")
        assert value == "default"

    def test_get_nested_config_value(self, sample_config):
        """Test getting nested configuration values."""
        watcher = ConfigWatcher(config=sample_config)

        # Test nested access
        value = watcher.get("workspace.max_size_bytes")
        assert value == sample_config.workspace.max_size_bytes

        value = watcher.get("server.port")
        assert value == sample_config.server.port


class TestConfigManager:
    """Tests for ConfigManager class."""

    def test_singleton_pattern(self):
        """Test that ConfigManager is a singleton."""
        manager1 = ConfigManager()
        manager2 = ConfigManager()

        assert manager1 is manager2

    def test_initial_config(self):
        """Test initial configuration loading."""
        # Reset singleton for test
        ConfigManager._instance = None
        ConfigManager._initialized = False

        manager = ConfigManager()

        assert manager.config is not None
        assert isinstance(manager.config, Config)

    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        # Reset singleton for test
        ConfigManager._instance = None
        ConfigManager._initialized = False

        # Set environment variable
        os.environ["MCP_GIT_LOG_LEVEL"] = "DEBUG"

        try:
            manager = ConfigManager()
            config = manager.load_from_env()

            assert config.log_level == "DEBUG"
        finally:
            # Clean up
            del os.environ["MCP_GIT_LOG_LEVEL"]

    def test_get_config_value(self):
        """Test getting configuration values through manager."""
        # Reset singleton for test
        ConfigManager._instance = None
        ConfigManager._initialized = False

        manager = ConfigManager()

        value = manager.get("log_level")
        assert value == "INFO"  # Default value

    def test_get_with_default(self):
        """Test getting configuration value with default."""
        # Reset singleton for test
        ConfigManager._instance = None
        ConfigManager._initialized = False

        manager = ConfigManager()

        value = manager.get("nonexistent", "default_value")
        assert value == "default_value"


class TestConfigHotReload:
    """Tests for configuration hot-reload functionality."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory."""
        return tmp_path

    @pytest.mark.asyncio
    async def test_watcher_start_stop(self, temp_dir):
        """Test starting and stopping the configuration watcher."""
        config = Config()
        watcher = ConfigWatcher(
            config=config,
            watch_paths=[str(temp_dir)],
            debounce_seconds=0.1,
        )

        # Start watcher
        await watcher.start()
        assert watcher._running is True
        assert len(watcher._watch_tasks) > 0

        # Stop watcher
        await watcher.stop()
        assert watcher._running is False

    @pytest.mark.asyncio
    async def test_reload_preserves_git_token(self, temp_dir):
        """Test that git token is preserved during reload."""
        config = Config()
        config.git_token = "secret_token"

        watcher = ConfigWatcher(config=config, watch_paths=[str(temp_dir)])

        # Mock load_config to return a new config without git_token
        with patch("mcp_git.config_watcher.load_config") as mock_load:
            mock_load.return_value = Config()

            await watcher.reload()

            # Git token should be preserved
            assert watcher.config.git_token == "secret_token"

    @pytest.mark.asyncio
    async def test_change_callback_invoked(self, temp_dir):
        """Test that change callbacks are invoked on reload."""
        config = Config()
        watcher = ConfigWatcher(config=config, watch_paths=[str(temp_dir)])

        callback = AsyncMock()
        watcher.add_change_callback(callback)

        with patch("mcp_git.config_watcher.load_config") as mock_load:
            mock_load.return_value = Config()

            await watcher.reload()

            # Callback should have been called
            callback.assert_called_once()


class TestConfigIntegration:
    """Integration tests for configuration management."""

    def test_config_from_env(self):
        """Test configuration loading from environment."""
        # Reset singleton
        ConfigManager._instance = None
        ConfigManager._initialized = False

        # Set test environment variables
        os.environ["MCP_GIT_WORKSPACE_PATH"] = "/test/workspace"
        os.environ["MCP_GIT_SERVER_PORT"] = "9999"
        os.environ["MCP_GIT_LOG_LEVEL"] = "DEBUG"

        try:
            manager = ConfigManager()
            config = manager.load_from_env()

            assert config.workspace.path == Path("/test/workspace")
            assert config.server.port == 9999
            assert config.log_level == "DEBUG"
        finally:
            # Clean up
            for key in ["MCP_GIT_WORKSPACE_PATH", "MCP_GIT_SERVER_PORT", "MCP_GIT_LOG_LEVEL"]:
                if key in os.environ:
                    del os.environ[key]

    def test_default_config_values(self):
        """Test that default configuration values are set correctly."""
        # Reset singleton
        ConfigManager._instance = None
        ConfigManager._initialized = False

        manager = ConfigManager()
        config = manager.config

        # Check default values
        assert config.workspace.path == Path("/tmp/mcp-git/workspaces")
        assert config.workspace.max_size_bytes == 10 * 1024 * 1024 * 1024
        assert config.server.port == 3001
        assert config.server.host == "127.0.0.1"
        assert config.execution.max_concurrent_tasks == 10
        assert config.execution.task_timeout == 300
        assert config.log_level == "INFO"
        assert config.git_token is None
