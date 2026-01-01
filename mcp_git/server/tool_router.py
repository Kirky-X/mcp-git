"""
Tool router for MCP Git server.

Provides a decorator-based registration system for tool handlers,
replacing the large if-elif chain with dictionary-based routing.
"""

from functools import wraps
from typing import Any, Callable

from loguru import logger

# Registry for tool handlers
TOOL_HANDLERS: dict[str, Callable] = {}


def register_tool(name: str) -> Callable:
    """
    Decorator to register a tool handler.

    Args:
        name: The name of the tool

    Returns:
        Decorator function

    Example:
        @register_tool("git_allocate_workspace")
        async def handle_allocate_workspace(server, arguments):
            result = await server.allocate_workspace()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
    """

    def decorator(func: Callable) -> Callable:
        TOOL_HANDLERS[name] = func
        logger.debug(f"Registered tool handler: {name}")
        return func

    return decorator


def get_tool_handler(name: str) -> Callable | None:
    """
    Get a tool handler by name.

    Args:
        name: The name of the tool

    Returns:
        The handler function, or None if not found
    """
    return TOOL_HANDLERS.get(name)


def list_registered_tools() -> list[str]:
    """
    List all registered tool names.

    Returns:
        List of tool names
    """
    return sorted(TOOL_HANDLERS.keys())