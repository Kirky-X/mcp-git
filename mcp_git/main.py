"""
Main entry point for mcp-git MCP server.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

from mcp_git.config import load_config
from mcp_git.server import McpGitServer

# Load environment variables from .env file
load_dotenv()


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging with loguru."""
    # Remove default handler
    logger.remove()

    # Add handler with format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{message}</cyan>"
    )

    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    level = log_levels.get(log_level.upper(), logging.INFO)

    logger.add(sys.stderr, format=log_format, level=level, colorize=True)


async def run_server(config: Optional = None) -> None:
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

        def signal_handler():
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
