"""
MCP Tool handlers for mcp-git.

This module implements the handlers for all MCP tools.
"""

import json
from collections.abc import Callable
from typing import Any
from uuid import UUID

from loguru import logger
from mcp.types import TextContent

from mcp_git.error import (
    AuthenticationError,
    GitOperationError,
    McpGitError,
    MergeConflictError,
    RepositoryNotFoundError,
)
from mcp_git.error_sanitizer import error_sanitizer

# Tool handler registry for O(1) lookup
TOOL_HANDLER_REGISTRY: dict[str, Callable[[Any, dict[str, Any]], list[TextContent]]] = {}


def format_error(error: Exception) -> str:
    """Format an error for MCP response with sensitive information sanitized."""
    if isinstance(error, RepositoryNotFoundError):
        sanitized_message = error_sanitizer.sanitize(error.message)
        return f"Repository not found: {sanitized_message}"
    elif isinstance(error, AuthenticationError):
        sanitized_message = error_sanitizer.sanitize(error.message)
        return f"Authentication failed: {sanitized_message}"
    elif isinstance(error, MergeConflictError):
        conflicts = ", ".join(error.conflicted_files)
        return f"Merge conflict: {conflicts}"
    elif isinstance(error, GitOperationError):
        sanitized_message = error_sanitizer.sanitize(error.message)
        suggestion = f"\n\nSuggestion: {error.suggestion}" if error.suggestion else ""
        return f"Git operation error: {sanitized_message}{suggestion}"
    elif isinstance(error, McpGitError):
        sanitized_message = error_sanitizer.sanitize(error.message)
        return f"Error: {sanitized_message}"
    else:
        sanitized_message = error_sanitizer.sanitize(str(error))
        return f"Unexpected error: {sanitized_message}"


def register_tool_handler(name: str, handler: Callable) -> None:
    """Register a tool handler in the registry."""
    TOOL_HANDLER_REGISTRY[name] = handler


def handle_list_tools() -> list[Any]:
    """
    Return list of available tools.

    Returns:
        List of Tool definitions
    """
    from mcp_git.server.tools import ALL_TOOLS

    return ALL_TOOLS


async def handle_call_tool(server: Any, name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle a tool call.

    Args:
        server: MCP server instance
        name: Tool name
        arguments: Tool arguments

    Returns:
        List of text content responses
    """
    logger.info("Tool call", tool=name, args=arguments)

    try:
        # Fast path: check if handler is registered in the registry
        handler = TOOL_HANDLER_REGISTRY.get(name)
        if handler:
            return await handler(server, arguments)

        # Fallback to if-elif chain for unregistered tools
        # Workspace operations
        # Workspace operations
        if name == "git_allocate_workspace":
            result = await server.allocate_workspace()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "git_get_workspace":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.get_workspace(workspace_id)
            if result:
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            return [TextContent(type="text", text="Workspace not found")]

        elif name == "git_release_workspace":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.release_workspace(workspace_id)
            return [TextContent(type="text", text=f"Released: {result}")]

        elif name == "git_list_workspaces":
            result = await server.list_workspaces()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "git_disk_space":
            warning_threshold = arguments.get("warning_threshold", 20.0)
            result = server.get_disk_space_info(warning_threshold)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        # Submodule operations
        elif name == "git_submodule_add":
            workspace_id = UUID(arguments["workspace_id"])
            from mcp_git.git.adapter import SubmoduleOptions

            await server.add_submodule(
                workspace_id=workspace_id,
                options=SubmoduleOptions(
                    path=arguments["path"],
                    url=arguments["url"],
                    name=arguments.get("name"),
                    branch=arguments.get("branch"),
                    depth=arguments.get("depth"),
                ),
            )
            return [TextContent(type="text", text=f"Submodule added at {arguments['path']}")]

        elif name == "git_submodule_update":
            workspace_id = UUID(arguments["workspace_id"])
            await server.update_submodule(
                workspace_id=workspace_id,
                name=arguments.get("name"),
                init=arguments.get("init", True),
            )
            return [TextContent(type="text", text="Submodules updated")]

        elif name == "git_submodule_deinit":
            workspace_id = UUID(arguments["workspace_id"])
            await server.deinit_submodule(
                workspace_id=workspace_id,
                name=arguments.get("name"),
                force=arguments.get("force", False),
            )
            return [TextContent(type="text", text="Submodule deinitialized")]

        elif name == "git_submodule_list":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.list_submodules(workspace_id)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        # Repository operations
        elif name == "git_clone":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.clone(
                url=arguments["url"],
                workspace_id=workspace_id,
                branch=arguments.get("branch"),
                depth=arguments.get("depth"),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "git_init":
            workspace_id = UUID(arguments["workspace_id"])
            await server.init_repository(
                workspace_id=workspace_id,
                bare=arguments.get("bare", False),
                default_branch=arguments.get("default_branch", "main"),
            )
            return [TextContent(type="text", text="Repository initialized")]

        elif name == "git_status":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.get_status(workspace_id)
            if not result:
                return [TextContent(type="text", text="Working tree is clean")]
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        # Commit operations
        elif name == "git_stage":
            workspace_id = UUID(arguments["workspace_id"])
            await server.stage_files(
                workspace_id=workspace_id,
                files=arguments["files"],
            )
            return [TextContent(type="text", text=f"Staged {len(arguments['files'])} files")]

        elif name == "git_commit":
            workspace_id = UUID(arguments["workspace_id"])
            oid = await server.create_commit(
                workspace_id=workspace_id,
                message=arguments["message"],
                author_name=arguments.get("author_name"),
                author_email=arguments.get("author_email"),
            )
            return [TextContent(type="text", text=f"Commit created: {oid}")]

        # Remote operations
        elif name == "git_push":
            workspace_id = UUID(arguments["workspace_id"])
            await server.push(
                workspace_id=workspace_id,
                remote=arguments.get("remote", "origin"),
                branch=arguments.get("branch"),
                force=arguments.get("force", False),
            )
            return [TextContent(type="text", text="Push successful")]

        elif name == "git_pull":
            workspace_id = UUID(arguments["workspace_id"])
            await server.pull(
                workspace_id=workspace_id,
                remote=arguments.get("remote", "origin"),
                branch=arguments.get("branch"),
                rebase=arguments.get("rebase", False),
            )
            return [TextContent(type="text", text="Pull successful")]

        elif name == "git_fetch":
            workspace_id = UUID(arguments["workspace_id"])
            await server.fetch(
                workspace_id=workspace_id,
                remote=arguments.get("remote"),
                tags=arguments.get("tags", False),
            )
            return [TextContent(type="text", text="Fetch successful")]

        # Branch operations
        elif name == "git_checkout":
            workspace_id = UUID(arguments["workspace_id"])
            await server.checkout(
                workspace_id=workspace_id,
                branch=arguments["branch"],
                create_new=arguments.get("create_new", False),
                force=arguments.get("force", False),
            )
            return [TextContent(type="text", text=f"Checked out: {arguments['branch']}")]

        elif name == "git_list_branches":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.list_branches(
                workspace_id=workspace_id,
                local=arguments.get("local", True),
                remote=arguments.get("remote", False),
                all=arguments.get("all", False),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "git_create_branch":
            workspace_id = UUID(arguments["workspace_id"])
            await server.create_branch(
                workspace_id=workspace_id,
                name=arguments["name"],
                revision=arguments.get("revision"),
                force=arguments.get("force", False),
            )
            return [TextContent(type="text", text=f"Branch created: {arguments['name']}")]

        elif name == "git_delete_branch":
            workspace_id = UUID(arguments["workspace_id"])
            await server.delete_branch(
                workspace_id=workspace_id,
                name=arguments["name"],
                force=arguments.get("force", False),
                remote=arguments.get("remote", False),
            )
            return [TextContent(type="text", text=f"Branch deleted: {arguments['name']}")]

        # Merge and rebase
        elif name == "git_merge":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.merge(
                workspace_id=workspace_id,
                source_branch=arguments["source_branch"],
                fast_forward=arguments.get("fast_forward", True),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "git_rebase":
            workspace_id = UUID(arguments["workspace_id"])
            await server.rebase(
                workspace_id=workspace_id,
                branch=arguments.get("branch"),
                abort=arguments.get("abort", False),
                continue_rebase=arguments.get("continue_rebase", False),
            )
            return [TextContent(type="text", text="Rebase completed")]

        # History operations
        elif name == "git_log":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.get_log(
                workspace_id=workspace_id,
                max_count=arguments.get("max_count"),
                author=arguments.get("author"),
                all=arguments.get("all", False),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "git_show":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.show_commit(
                workspace_id=workspace_id,
                revision=arguments["revision"],
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "git_diff":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.get_diff(
                workspace_id=workspace_id,
                cached=arguments.get("cached", False),
                commit_oid=arguments.get("commit_oid"),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "git_blame":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.get_blame(
                workspace_id=workspace_id,
                path=arguments["path"],
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        # Stash operations
        elif name == "git_stash":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.stash_changes(
                workspace_id=workspace_id,
                save=arguments.get("save", False),
                pop=arguments.get("pop", False),
                apply=arguments.get("apply", False),
                drop=arguments.get("drop", False),
                message=arguments.get("message"),
                include_untracked=arguments.get("include_untracked", False),
            )
            if result:
                return [TextContent(type="text", text=f"Stashed: {result}")]
            return [TextContent(type="text", text="Stash operation completed")]

        elif name == "git_list_stash":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.list_stash(workspace_id)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        # Tag operations
        elif name == "git_list_tags":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.list_tags(workspace_id)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "git_create_tag":
            workspace_id = UUID(arguments["workspace_id"])
            await server.create_tag(
                workspace_id=workspace_id,
                name=arguments["name"],
                message=arguments.get("message"),
                force=arguments.get("force", False),
            )
            return [TextContent(type="text", text=f"Tag created: {arguments['name']}")]

        elif name == "git_delete_tag":
            workspace_id = UUID(arguments["workspace_id"])
            await server.delete_tag(workspace_id, arguments["name"])
            return [TextContent(type="text", text=f"Tag deleted: {arguments['name']}")]

        # Remote operations
        elif name == "git_list_remotes":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.list_remotes(workspace_id)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "git_add_remote":
            workspace_id = UUID(arguments["workspace_id"])
            await server.add_remote(
                workspace_id=workspace_id,
                name=arguments["name"],
                url=arguments["url"],
            )
            return [TextContent(type="text", text=f"Remote added: {arguments['name']}")]

        elif name == "git_remove_remote":
            workspace_id = UUID(arguments["workspace_id"])
            await server.remove_remote(workspace_id, arguments["name"])
            return [TextContent(type="text", text=f"Remote removed: {arguments['name']}")]

        # Git LFS operations
        elif name == "git_lfs_init":
            workspace_id = UUID(arguments["workspace_id"])
            await server.lfs_init(workspace_id)
            return [TextContent(type="text", text="Git LFS initialized")]

        elif name == "git_lfs_track":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.lfs_track(
                workspace_id=workspace_id,
                patterns=arguments["patterns"],
                lockable=arguments.get("lockable", False),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "git_lfs_untrack":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.lfs_untrack(
                workspace_id=workspace_id,
                patterns=arguments["patterns"],
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "git_lfs_status":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.lfs_status(workspace_id)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "git_lfs_pull":
            workspace_id = UUID(arguments["workspace_id"])
            await server.lfs_pull(
                workspace_id=workspace_id,
                objects=arguments.get("objects"),
                all=arguments.get("all", True),
            )
            return [TextContent(type="text", text="LFS files pulled")]

        elif name == "git_lfs_push":
            workspace_id = UUID(arguments["workspace_id"])
            await server.lfs_push(
                workspace_id=workspace_id,
                remote=arguments.get("remote", "origin"),
                all=arguments.get("all", True),
            )
            return [TextContent(type="text", text="LFS objects pushed")]

        elif name == "git_lfs_fetch":
            workspace_id = UUID(arguments["workspace_id"])
            await server.lfs_fetch(
                workspace_id=workspace_id,
                objects=arguments.get("objects"),
            )
            return [TextContent(type="text", text="LFS objects fetched")]

        elif name == "git_lfs_install":
            workspace_id = UUID(arguments["workspace_id"])
            await server.lfs_install(workspace_id)
            return [TextContent(type="text", text="Git LFS hooks installed")]

        # Sparse checkout operations
        elif name == "git_sparse_checkout":
            workspace_id = UUID(arguments["workspace_id"])
            result = await server.sparse_checkout(
                workspace_id=workspace_id,
                paths=arguments["paths"],
                mode=arguments.get("mode", "replace"),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        # Task operations
        elif name == "git_get_task":
            task_id = UUID(arguments["task_id"])
            result = await server.get_task(task_id)
            if result:
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            return [TextContent(type="text", text="Task not found")]

        elif name == "git_list_tasks":
            result = await server.list_tasks(
                status=arguments.get("status"),
                limit=arguments.get("limit", 100),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "git_cancel_task":
            task_id = UUID(arguments["task_id"])
            result = await server.cancel_task(task_id)
            return [TextContent(type="text", text=f"Cancelled: {result}")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except RepositoryNotFoundError as e:
        logger.error("Repository not found", error=str(e))
        from mcp_git.metrics import GIT_OPERATIONS_TOTAL
        GIT_OPERATIONS_TOTAL.labels(operation=name, status="not_found").inc()
        return [TextContent(type="text", text=f"Error: Repository not found - {e.message}")]

    except AuthenticationError as e:
        logger.error("Authentication failed", error=str(e))
        from mcp_git.metrics import GIT_OPERATIONS_TOTAL
        GIT_OPERATIONS_TOTAL.labels(operation=name, status="auth_failed").inc()
        return [TextContent(type="text", text=f"Error: Authentication failed - {e.message}")]

    except MergeConflictError as e:
        logger.error("Merge conflict", files=e.conflicted_files)
        from mcp_git.metrics import GIT_OPERATIONS_TOTAL
        GIT_OPERATIONS_TOTAL.labels(operation=name, status="conflict").inc()
        return [
            TextContent(
                type="text", text=f"Error: Merge conflict in files: {', '.join(e.conflicted_files)}"
            )
        ]

    except GitOperationError as e:
        logger.error("Git operation error", error=str(e))
        from mcp_git.metrics import GIT_OPERATIONS_TOTAL
        GIT_OPERATIONS_TOTAL.labels(operation=name, status="error").inc()
        suggestion = f"\n\nSuggestion: {e.suggestion}" if e.suggestion else ""
        return [TextContent(type="text", text=f"Error: {e.message}{suggestion}")]

    except McpGitError as e:
        logger.error("MCP Git error", error=str(e))
        from mcp_git.metrics import GIT_OPERATIONS_TOTAL
        GIT_OPERATIONS_TOTAL.labels(operation=name, status="mcp_error").inc()
        return [TextContent(type="text", text=f"Error: {e.message}")]

    except ValueError as e:
        logger.error("Invalid argument", error=str(e))
        from mcp_git.metrics import GIT_OPERATIONS_TOTAL
        GIT_OPERATIONS_TOTAL.labels(operation=name, status="invalid_arg").inc()
        return [TextContent(type="text", text=f"Invalid argument: {str(e)}")]

    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        from mcp_git.metrics import GIT_OPERATIONS_TOTAL
        GIT_OPERATIONS_TOTAL.labels(operation=name, status="unexpected").inc()
        return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]
