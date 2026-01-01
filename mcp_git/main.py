"""
Main entry point for mcp-git MCP server.
"""

import asyncio
import re
import signal
import sys
from typing import Any

from dotenv import load_dotenv
from loguru import logger

from mcp_git.config import Config, load_config
from mcp_git.server import McpGitServer

# Load environment variables from .env file
load_dotenv()


# Sensitive patterns for log sanitization
SENSITIVE_PATTERNS = [
    # Git tokens in URLs
    (r"(https?://)[^:]+:(.+?)@", r"\1***:***@"),
    # Authorization headers
    (r"(Authorization:\s*).+", r"\1***"),
    # Git token environment variables
    (r"(GIT_TOKEN=).+", r"\1***"),
    # Password in URL
    (r"password[=]\S+", "password=***"),
    # Private key patterns
    (r"(-{5}BEGIN\s+.*?PRIVATE\s+KEY-{5}).+", r"\1***"),
]


def sanitize_log_message(message: str) -> str:
    """Sanitize sensitive information from log messages.

    Args:
        message: Original log message

    Returns:
        Sanitized log message
    """
    sanitized = message
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized


class SanitizingSink:
    """A loguru sink wrapper that sanitizes log messages."""

    def __init__(self, sink: Any) -> None:
        self.sink = sink

    def write(self, message: str) -> None:
        """Write sanitized message to sink."""
        sanitized = sanitize_log_message(message)
        self.sink.write(sanitized)

    def flush(self) -> None:
        """Flush the sink."""
        if hasattr(self.sink, "flush"):
            self.sink.flush()


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging with loguru and sensitive data sanitization."""
    # Remove default handler
    logger.remove()

    # Add handler with format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{message}</cyan>"
    )

    log_levels = {
        "DEBUG": "DEBUG",
        "INFO": "INFO",
        "WARNING": "WARNING",
        "ERROR": "ERROR",
    }
    level = log_levels.get(log_level.upper(), "INFO")

    # Create a sink that sanitizes sensitive data
    class SanitizedStream:
        def __init__(self, original: Any) -> None:
            self.original = original

        def write(self, message: str) -> None:
            self.original.write(sanitize_log_message(message))

        def flush(self) -> None:
            self.original.flush()

    stderr_sanitized = SanitizedStream(sys.stderr)
    logger.add(stderr_sanitized, format=log_format, level=level, colorize=True)


async def run_server(config: Config | None = None) -> None:
    """Run the MCP server."""
    if config is None:
        config = load_config()

    setup_logging(config.log_level)

    logger.info("Starting mcp-git server", version="0.1.0")

    try:
        # Create and configure MCP server
        server = McpGitServer(config)

        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()

        def signal_handler() -> None:
            logger.info("Received shutdown signal")
            asyncio.create_task(server.shutdown())

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

        # Run server
        await server.run()

    except Exception as e:
        logger.error("Server error", error=str(e))
        raise
    finally:
        logger.info("Server shutting down")


def main() -> int:
    """Main entry point."""
    try:
        asyncio.run(run_server())
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
