"""
Configuration management module for mcp-git.

This module provides configuration loading and hot-reload functionality
for the mcp-git server.
"""

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from watchfiles import awatch

from mcp_git.config import (
    Config,
    load_config,
)


class ConfigWatcher:
    """Configuration watcher with hot-reload support.

    This class monitors configuration sources and can trigger
    reloads when changes are detected.
    """

    def __init__(
        self,
        config: Config | None = None,
        watch_paths: list | None = None,
        debounce_seconds: float = 1.0,
    ):
        """Initialize the configuration watcher.

        Args:
            config: Initial configuration
            watch_paths: Paths to watch for changes
            debounce_seconds: Minimum time between reloads
        """
        self.config = config or load_config()
        self.watch_paths = watch_paths or []
        self.debounce_seconds = debounce_seconds
        self._watch_task: asyncio.Task | None = None
        self._running = False
        self._change_callbacks: list[Callable[[Config], None]] = []

    def add_change_callback(self, callback: Callable[[Config], None]) -> None:
        """Add a callback to be called when configuration changes.

        Args:
            callback: Function to call with new config
        """
        self._change_callbacks.append(callback)

    def remove_change_callback(self, callback: Callable[[Config], None]) -> None:
        """Remove a change callback.

        Args:
            callback: Function to remove
        """
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)

    async def _watch_path(self, path: Path) -> None:
        """Watch a single path for changes.

        Args:
            path: Path to watch
        """
        try:
            async for changes in awatch(path, debounce=int(self.debounce_seconds)):
                logger.info(f"Configuration changes detected in {path}: {changes}")
                await self.reload()
        except Exception as e:
            logger.error(f"Error watching {path}: {e}")

    async def start(self) -> None:
        """Start watching for configuration changes."""
        if self._running:
            return

        self._running = True
        self._watch_tasks = []

        for watch_path in self.watch_paths:
            path = Path(watch_path)
            if path.exists():
                task = asyncio.create_task(self._watch_path(path))
                self._watch_tasks.append(task)
                logger.info(f"Started watching {path} for configuration changes")

        if self._watch_tasks:
            await asyncio.gather(*self._watch_tasks)

    async def stop(self) -> None:
        """Stop watching for configuration changes."""
        self._running = False

        for task in self._watch_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._watch_tasks.clear()
        logger.info("Configuration watcher stopped")

    async def reload(self) -> Config:
        """Reload configuration from environment variables.

        Returns:
            New configuration object
        """
        try:
            new_config = load_config()

            # Preserve sensitive data from old config
            if self.config.git_token:
                new_config.git_token = self.config.git_token

            self.config = new_config

            logger.info("Configuration reloaded successfully")

            # Notify callbacks
            for callback in self._change_callbacks:
                try:
                    callback(new_config)
                except Exception as e:
                    logger.error(f"Error in config change callback: {e}")

            return new_config

        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            return self.config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found

        Returns:
            Configuration value
        """
        # Handle dot notation (e.g., "workspace.path")
        if "." in key:
            parts = key.split(".")
            value = self.config
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return default
            return value

        # Direct attribute access
        if hasattr(self.config, key):
            return getattr(self.config, key)

        return default


class ConfigManager:
    """Enhanced configuration manager with hot-reload support.

    This class provides a singleton-like interface for configuration
    management with support for hot-reloading.
    """

    _instance: Optional["ConfigManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "ConfigManager":
        """Create singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        if not ConfigManager._initialized:
            self._config = load_config()
            self._watcher: ConfigWatcher | None = None
            ConfigManager._initialized = True

    @property
    def config(self) -> Config:
        """Get current configuration."""
        return self._config

    def load_from_env(self) -> Config:
        """Load configuration from environment variables."""
        self._config = load_config()
        return self._config  # type: ignore[no-any-return]

    def load_from_file(self, file_path: Path) -> Config:
        """Load configuration from a file.

        Args:
            file_path: Path to configuration file

        Returns:
            Loaded configuration
        """
        # For now, this is a placeholder for future JSON/YAML config support
        logger.info(f"Configuration file loading not yet implemented: {file_path}")
        return self._config  # type: ignore[no-any-return]

    def start_watcher(
        self,
        watch_paths: list | None = None,
        debounce_seconds: float = 1.0,
    ) -> None:
        """Start configuration file watcher.

        Args:
            watch_paths: Paths to watch for changes
            debounce_seconds: Debounce interval
        """
        if self._watcher is None or not self._watcher._running:
            self._watcher = ConfigWatcher(
                config=self._config,
                watch_paths=watch_paths,
                debounce_seconds=debounce_seconds,
            )
            asyncio.create_task(self._watcher.start())
            logger.info("Configuration watcher started")

    def stop_watcher(self) -> None:
        """Stop configuration file watcher."""
        if self._watcher:
            asyncio.create_task(self._watcher.stop())
            self._watcher = None
            logger.info("Configuration watcher stopped")

    def add_change_callback(self, callback: Callable[[Config], None]) -> None:
        """Add a callback for configuration changes.

        Args:
            callback: Function to call on config change
        """
        if self._watcher:
            self._watcher.add_change_callback(callback)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key
            default: Default value

        Returns:
            Configuration value
        """
        return self._config.model_dump().get(key, default)


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> Config:
    """Get the current configuration.

    Returns:
        Current configuration object
    """
    return config_manager.config


def reload_config() -> Config:
    """Reload configuration from environment.

    Returns:
        New configuration object
    """
    return config_manager.load_from_env()
