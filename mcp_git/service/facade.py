"""
Git Service Facade for mcp-git.

This module provides a unified interface for all Git operations,
orchestrating the Git adapter, workspace manager, credential manager,
and task manager.
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from loguru import logger

from mcp_git.git.adapter import (
    BlameOptions,
    CheckoutOptions,
    CloneOptions,
    CommitOptions,
    DiffOptions,
    GitAdapter,
    LogOptions,
    MergeOptions,
    PullOptions,
    PushOptions,
    RebaseOptions,
    StashOptions,
    SubmoduleOptions,
    TagOptions,
    TransferProgressCallback,
)
from mcp_git.git.adapter_gitpython import GitPythonAdapter
from mcp_git.service.credential_manager import CredentialManager
from mcp_git.service.task_manager import TaskConfig, TaskManager
from mcp_git.service.workspace_manager import WorkspaceConfig, WorkspaceManager
from mcp_git.storage import SqliteStorage
from mcp_git.storage.models import (
    GitOperation,
    Task,
    TaskResult,
    TaskStatus,
)
from mcp_git.utils import sanitize_branch_name, sanitize_commit_message, sanitize_remote_url


class GitServiceFacade:
    """
    Unified interface for Git operations.

    This facade orchestrates all services to provide a clean API
    for Git operations with workspace management, credential handling,
    and task tracking.
    """

    def __init__(
        self,
        storage: SqliteStorage,
        workspace_config: WorkspaceConfig | None = None,
        task_config: TaskConfig | None = None,
        adapter: GitAdapter | None = None,
    ):
        """
        Initialize the Git service facade.

        Args:
            storage: SQLite storage for persistence
            workspace_config: Workspace configuration
            task_config: Task configuration
            adapter: Git adapter implementation (default: GitPythonAdapter)
        """
        self.storage = storage

        # Initialize services
        self.workspace_manager = WorkspaceManager(
            storage,
            workspace_config
            or WorkspaceConfig(
                root_path=Path(tempfile.gettempdir()) / "mcp-git" / "workspaces",
                max_size_bytes=10 * 1024 * 1024 * 1024,  # 10GB
                retention_seconds=3600,  # 1 hour
            ),
        )

        self.credential_manager = CredentialManager()

        self.task_manager = TaskManager(
            storage,
            task_config
            or TaskConfig(
                max_concurrent_tasks=10,
                task_timeout_seconds=300,
                result_retention_seconds=3600,
            ),
        )

        self.git_adapter = adapter or GitPythonAdapter()
        self.git_adapter.set_credential_manager(self.credential_manager)  # type: ignore[attr-defined]

        # Track service state
        self._started = False

    async def start(self) -> None:
        """Start all services."""
        if self._started:
            return

        logger.info("Starting Git service facade")

        # Start workspace manager
        await self.workspace_manager.start()

        # Start task manager
        await self.task_manager.start()

        self._started = True
        logger.info("Git service facade started")

    async def stop(self) -> None:
        """Stop all services."""
        if not self._started:
            return

        logger.info("Stopping Git service facade")

        await self.task_manager.stop()
        await self.workspace_manager.stop()

        self._started = False
        logger.info("Git service facade stopped")

    # Workspace operations

    async def allocate_workspace(self) -> dict[str, Any]:
        """
        Allocate a new workspace.

        Returns:
            Dictionary with workspace information
        """
        workspace = await self.workspace_manager.allocate_workspace()
        return {
            "workspace_id": str(workspace.id),
            "path": str(workspace.path),
        }

    async def get_workspace(self, workspace_id: UUID) -> dict[str, Any] | None:
        """
        Get workspace information.

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace information or None
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            return None

        return {
            "workspace_id": str(workspace.id),
            "path": str(workspace.path),
            "size_bytes": workspace.size_bytes,
            "last_accessed_at": workspace.last_accessed_at.isoformat()
            if workspace.last_accessed_at
            else None,
            "created_at": workspace.created_at.isoformat() if workspace.created_at else None,
        }

    async def release_workspace(self, workspace_id: UUID) -> bool:
        """
        Release a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            True if released
        """
        return await self.workspace_manager.release_workspace(workspace_id)

    async def list_workspaces(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        List all workspaces.

        Args:
            limit: Maximum number to return

        Returns:
            List of workspace information
        """
        workspaces = await self.workspace_manager.list_workspaces(limit)
        return [
            {
                "workspace_id": str(ws.id),
                "path": str(ws.path),
                "size_bytes": ws.size_bytes,
                "last_accessed_at": ws.last_accessed_at.isoformat()
                if ws.last_accessed_at
                else None,
            }
            for ws in workspaces
        ]

    async def get_workspace_usage(self) -> dict[str, Any]:
        """
        Get workspace disk usage.

        Returns:
            Usage statistics
        """
        return await self.workspace_manager.get_workspace_usage()

    def get_disk_space_info(self, warning_threshold: float = 20.0) -> dict[str, Any]:
        """
        Get disk space information and warning status.

        Args:
            warning_threshold: Percentage of free space below which to warn

        Returns:
            Disk space information with warning status
        """
        return self.workspace_manager.check_disk_space_warning(warning_threshold)

    # Submodule operations

    async def add_submodule(
        self,
        workspace_id: UUID,
        options: "SubmoduleOptions",
    ) -> None:
        """
        Add a submodule to the repository.

        Args:
            workspace_id: Workspace ID
            options: Submodule options
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        await self.git_adapter.add_submodule(workspace.path, options)  # type: ignore[attr-defined]

        # Stage .gitmodules if created
        try:
            await self.git_adapter.add(workspace.path, [".gitmodules"])
        except Exception:  # nosec: B110 - Expected case: .gitmodules may not exist
            pass  # .gitmodules may not exist or be already staged

    async def update_submodule(
        self,
        workspace_id: UUID,
        name: str | None = None,
        init: bool = True,
    ) -> None:
        """
        Update a submodule.

        Args:
            workspace_id: Workspace ID
            name: Submodule name/path (optional, updates all if not specified)
            init: Initialize submodules if not already
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        await self.git_adapter.update_submodule(workspace.path, name, init)  # type: ignore[attr-defined]

    async def deinit_submodule(
        self,
        workspace_id: UUID,
        name: str | None = None,
        force: bool = False,
    ) -> None:
        """
        Deinitialize a submodule.

        Args:
            workspace_id: Workspace ID
            name: Submodule name/path (optional, deinits all if not specified)
            force: Force deinitialization even with local changes
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        await self.git_adapter.deinit_submodule(workspace.path, name, force)  # type: ignore[attr-defined]

    async def list_submodules(
        self,
        workspace_id: UUID,
    ) -> list[dict[str, Any]]:
        """
        List submodules in the repository.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of submodule information
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        submodules = await self.git_adapter.list_submodules(workspace.path)  # type: ignore[attr-defined]
        return [
            {
                "name": s.name,
                "path": s.path,
                "url": s.url,
                "branch": s.branch,
                "commit_oid": s.commit_oid,
                "status": s.status,
            }
            for s in submodules
        ]

    # Git operations with workspace

    async def clone(
        self,
        url: str,
        workspace_id: UUID,
        options: CloneOptions | None = None,
        progress_callback: TransferProgressCallback | None = None,
    ) -> dict[str, Any]:
        """
        Clone a repository into a workspace.

        Args:
            url: Repository URL
            workspace_id: Workspace ID
            options: Clone options
            progress_callback: Optional progress callback

        Returns:
            Clone result with commit info
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        # Sanitize remote URL to prevent injection attacks
        sanitized_url = sanitize_remote_url(url)

        commit_info = await self.git_adapter.clone(
            sanitized_url,
            workspace.path,
            options,
            progress_callback,
        )

        # Update workspace size
        await self.workspace_manager.update_workspace_size(workspace_id)

        return {
            "oid": commit_info.oid,
            "message": commit_info.message,
            "author_name": commit_info.author_name,
            "author_email": commit_info.author_email,
            "commit_time": commit_info.commit_time.isoformat(),
        }

    async def init(
        self,
        workspace_id: UUID,
        bare: bool = False,
        default_branch: str = "main",
    ) -> None:
        """
        Initialize a new repository.

        Args:
            workspace_id: Workspace ID
            bare: Create bare repository
            default_branch: Default branch name
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        await self.git_adapter.init(
            workspace.path,
            bare=bare,
            default_branch=default_branch,
        )

    async def status(self, workspace_id: UUID) -> list[dict[str, Any]]:
        """
        Get repository status.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of file statuses
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        statuses = await self.git_adapter.status(workspace.path)

        return [
            {
                "path": status.path,
                "status": status.status,
            }
            for status in statuses
        ]

    async def add(
        self,
        workspace_id: UUID,
        files: list[str],
    ) -> None:
        """
        Stage files for commit.

        Args:
            workspace_id: Workspace ID
            files: Files to stage
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        await self.git_adapter.add(workspace.path, files)

    async def commit(
        self,
        workspace_id: UUID,
        message: str,
        author_name: str | None = None,
        author_email: str | None = None,
    ) -> str:
        """
        Create a commit.

        Args:
            workspace_id: Workspace ID
            message: Commit message
            author_name: Optional author name
            author_email: Optional author email

        Returns:
            Commit OID
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        # Sanitize commit message to prevent injection attacks
        sanitized_message = sanitize_commit_message(message)

        options = CommitOptions(
            message=sanitized_message,
            author_name=author_name,
            author_email=author_email,
        )

        # Invalidate cache for this workspace since we're creating a commit
        from mcp_git.cache import repo_metadata_cache
        await repo_metadata_cache.invalidate(workspace.path)

        return await self.git_adapter.commit(workspace.path, options)

    async def push(
        self,
        workspace_id: UUID,
        remote: str = "origin",
        branch: str | None = None,
        force: bool = False,
    ) -> None:
        """
        Push to remote.

        Args:
            workspace_id: Workspace ID
            remote: Remote name
            branch: Branch name
            force: Force push
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        # Sanitize branch name to prevent injection attacks
        sanitized_branch = sanitize_branch_name(branch) if branch else None

        options = PushOptions(
            remote=remote,
            branch=sanitized_branch,
            force=force,
        )

        await self.git_adapter.push(workspace.path, options)

        # Invalidate cache for this workspace since we're pushing changes
        from mcp_git.cache import repo_metadata_cache
        await repo_metadata_cache.invalidate(workspace.path)

    async def pull(
        self,
        workspace_id: UUID,
        remote: str = "origin",
        branch: str | None = None,
        rebase: bool = False,
    ) -> None:
        """
        Pull from remote.

        Args:
            workspace_id: Workspace ID
            remote: Remote name
            branch: Branch name
            rebase: Rebase instead of merge
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        # Sanitize branch name to prevent injection attacks
        sanitized_branch = sanitize_branch_name(branch) if branch else None

        options = PullOptions(
            remote=remote,
            branch=sanitized_branch,
            rebase=rebase,
        )

        await self.git_adapter.pull(workspace.path, options)

        # Invalidate cache for this workspace since we're pulling changes
        from mcp_git.cache import repo_metadata_cache
        await repo_metadata_cache.invalidate(workspace.path)

    async def fetch(
        self,
        workspace_id: UUID,
        remote: str | None = None,
        tags: bool = False,
    ) -> None:
        """
        Fetch from remote.

        Args:
            workspace_id: Workspace ID
            remote: Remote name
            tags: Fetch tags
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        await self.git_adapter.fetch(workspace.path, remote, tags)

    async def checkout(
        self,
        workspace_id: UUID,
        branch: str,
        create_new: bool = False,
        force: bool = False,
    ) -> None:
        """
        Checkout a branch or commit.

        Args:
            workspace_id: Workspace ID
            branch: Branch or commit to checkout
            create_new: Create new branch
            force: Force checkout
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        options = CheckoutOptions(
            branch=branch,
            create_new=create_new,
            force=force,
        )

        await self.git_adapter.checkout(workspace.path, options)

    async def list_branches(
        self,
        workspace_id: UUID,
        local: bool = True,
        remote: bool = False,
        all: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List branches.

        Args:
            workspace_id: Workspace ID
            local: Include local branches
            remote: Include remote branches
            all: Include all branches

        Returns:
            List of branch information
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        branches = await self.git_adapter.list_branches(workspace.path, local, remote, all)

        return [
            {
                "name": branch.name,
                "oid": branch.oid,
                "is_local": branch.is_local,
                "is_remote": branch.is_remote,
            }
            for branch in branches
        ]

    async def create_branch(
        self,
        workspace_id: UUID,
        name: str,
        revision: str | None = None,
        force: bool = False,
    ) -> None:
        """
        Create a branch.

        Args:
            workspace_id: Workspace ID
            name: Branch name
            revision: Starting revision
            force: Overwrite existing
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        # Sanitize branch name to prevent injection attacks
        sanitized_name = sanitize_branch_name(name)

        await self.git_adapter.create_branch(workspace.path, sanitized_name, revision, force)

    async def delete_branch(
        self,
        workspace_id: UUID,
        name: str,
        force: bool = False,
        remote: bool = False,
    ) -> None:
        """
        Delete a branch.

        Args:
            workspace_id: Workspace ID
            name: Branch name
            force: Force delete
            remote: Delete remote branch
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        # Sanitize branch name to prevent injection attacks
        sanitized_name = sanitize_branch_name(name)

        await self.git_adapter.delete_branch(workspace.path, sanitized_name, force, remote)

    async def merge(
        self,
        workspace_id: UUID,
        source_branch: str,
        fast_forward: bool = True,
    ) -> dict[str, Any]:
        """
        Merge branches.

        Args:
            workspace_id: Workspace ID
            source_branch: Source branch
            fast_forward: Fast-forward only

        Returns:
            Merge result
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        # Sanitize branch name to prevent injection attacks
        sanitized_branch = sanitize_branch_name(source_branch)

        options = MergeOptions(
            source_branch=sanitized_branch,
            fast_forward=fast_forward,
        )

        result = await self.git_adapter.merge(workspace.path, options)

        return {
            "result": result.value if hasattr(result, "value") else str(result),
        }

    async def rebase(
        self,
        workspace_id: UUID,
        branch: str | None = None,
        abort: bool = False,
        continue_rebase: bool = False,
    ) -> None:
        """
        Rebase current branch.

        Args:
            workspace_id: Workspace ID
            branch: Branch to rebase onto
            abort: Abort ongoing rebase
            continue: Continue ongoing rebase
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        # Sanitize branch name to prevent injection attacks
        sanitized_branch = sanitize_branch_name(branch) if branch else None

        options = RebaseOptions(
            branch=sanitized_branch,
            abort=abort,
            continue_rebase=continue_rebase,
        )

        await self.git_adapter.rebase(workspace.path, options)

    async def log(
        self,
        workspace_id: UUID,
        max_count: int | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        author: str | None = None,
        all: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Get commit log.

        Args:
            workspace_id: Workspace ID
            max_count: Maximum commits
            since: Since date
            until: Until date
            author: Filter by author
            all: All branches

        Returns:
            List of commit information
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        options = LogOptions(
            max_count=max_count,
            since=since,
            until=until,
            author=author,
            all=all,
        )

        commits = await self.git_adapter.log(workspace.path, options)

        return [
            {
                "oid": commit.oid,
                "message": commit.message,
                "author_name": commit.author_name,
                "author_email": commit.author_email,
                "commit_time": commit.commit_time.isoformat() if commit.commit_time else None,
            }
            for commit in commits
        ]

    async def show(
        self,
        workspace_id: UUID,
        revision: str,
    ) -> dict[str, Any]:
        """
        Show a commit.

        Args:
            workspace_id: Workspace ID
            revision: Commit revision

        Returns:
            Commit diff information
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        diff_info = await self.git_adapter.show(workspace.path, revision)

        return {
            "revision": revision,
            "old_path": diff_info.old_path,
            "new_path": diff_info.new_path,
            "change_type": diff_info.change_type,
            "diff_lines": diff_info.diff_lines,
        }

    async def diff(
        self,
        workspace_id: UUID,
        cached: bool = False,
        commit_oid: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Show differences.

        Args:
            workspace_id: Workspace ID
            cached: Show staged changes
            commit_oid: Compare with commit

        Returns:
            List of diff information
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        options = DiffOptions(
            cached=cached,
            commit_oid=commit_oid,
        )

        diffs = await self.git_adapter.diff(workspace.path, options)

        return [
            {
                "old_path": diff.old_path,
                "new_path": diff.new_path,
                "change_type": diff.change_type,
                "diff_lines": diff.diff_lines,
            }
            for diff in diffs
        ]

    async def blame(
        self,
        workspace_id: UUID,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get blame information for a file.

        Args:
            workspace_id: Workspace ID
            path: File path
            start_line: Start line
            end_line: End line

        Returns:
            List of blame information
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        file_path = Path(path) if not Path(path).is_absolute() else Path(path)
        if not file_path.is_absolute():
            file_path = workspace.path / file_path

        options = BlameOptions(
            path=file_path,
            start_line=start_line,
            end_line=end_line,
        )

        blame_lines = await self.git_adapter.blame(options)

        return [
            {
                "line_number": blame.line_number,
                "commit_oid": blame.commit_oid,
                "author": blame.author,
                "date": blame.date.isoformat() if blame.date else None,
                "summary": blame.summary,
            }
            for blame in blame_lines
        ]

    async def stash(
        self,
        workspace_id: UUID,
        save: bool = False,
        pop: bool = False,
        apply: bool = False,
        drop: bool = False,
        list_stash: bool = False,
        message: str | None = None,
        include_untracked: bool = False,
    ) -> str | None:
        """
        Stash changes.

        Args:
            workspace_id: Workspace ID
            save: Save stash
            pop: Pop stash
            apply: Apply stash
            drop: Drop stash
            list_stash: List stash
            message: Stash message
            include_untracked: Include untracked files

        Returns:
            Stash reference or None
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        options = StashOptions(
            save=save,
            pop=pop,
            apply=apply,
            drop=drop,
            list=list_stash,
            message=message,
            include_untracked=include_untracked,
        )

        return await self.git_adapter.stash(workspace.path, options)

    async def list_stash(self, workspace_id: UUID) -> list[dict[str, Any]]:
        """
        List stash entries.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of stash entries
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        return await self.git_adapter.list_stash(workspace.path)

    async def list_tags(self, workspace_id: UUID) -> list[str]:
        """
        List tags.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of tag names
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        return await self.git_adapter.list_tags(workspace.path)

    async def create_tag(
        self,
        workspace_id: UUID,
        name: str,
        message: str | None = None,
        force: bool = False,
    ) -> None:
        """
        Create a tag.

        Args:
            workspace_id: Workspace ID
            name: Tag name
            message: Tag message
            force: Overwrite existing
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        options = TagOptions(
            name=name,
            message=message,
            force=force,
        )

        await self.git_adapter.create_tag(workspace.path, options)

    async def delete_tag(self, workspace_id: UUID, name: str) -> None:
        """
        Delete a tag.

        Args:
            workspace_id: Workspace ID
            name: Tag name
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        await self.git_adapter.delete_tag(workspace.path, name)

    async def list_remotes(self, workspace_id: UUID) -> list[dict[str, str]]:
        """
        List remotes.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of remote information
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        return await self.git_adapter.list_remotes(workspace.path)

    async def add_remote(
        self,
        workspace_id: UUID,
        name: str,
        url: str,
    ) -> None:
        """
        Add a remote.

        Args:
            workspace_id: Workspace ID
            name: Remote name
            url: Remote URL
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        await self.git_adapter.add_remote(workspace.path, name, url)

    async def remove_remote(self, workspace_id: UUID, name: str) -> None:
        """
        Remove a remote.

        Args:
            workspace_id: Workspace ID
            name: Remote name
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        await self.git_adapter.remove_remote(workspace.path, name)

    # Git LFS operations

    async def lfs_init(self, workspace_id: UUID) -> None:
        """
        Initialize Git LFS in a repository.

        Args:
            workspace_id: Workspace ID
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        await self.git_adapter.lfs_init(workspace.path)

    async def lfs_track(
        self,
        workspace_id: UUID,
        patterns: list[str],
        lockable: bool = False,
    ) -> list[str]:
        """
        Track files with Git LFS.

        Args:
            workspace_id: Workspace ID
            patterns: File patterns to track
            lockable: Make files lockable

        Returns:
            List of tracked patterns
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        return await self.git_adapter.lfs_track(workspace.path, patterns, lockable)

    async def lfs_untrack(
        self,
        workspace_id: UUID,
        patterns: list[str],
    ) -> list[str]:
        """
        Stop tracking files with Git LFS.

        Args:
            workspace_id: Workspace ID
            patterns: File patterns to untrack

        Returns:
            List of untracked patterns
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        return await self.git_adapter.lfs_untrack(workspace.path, patterns)

    async def lfs_status(self, workspace_id: UUID) -> list[dict[str, Any]]:
        """
        Show Git LFS status and tracked files.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of LFS file information
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        lfs_files = await self.git_adapter.lfs_status(workspace.path)

        return [
            {
                "name": lfs_file.name,
                "path": lfs_file.path,
                "size": lfs_file.size,
                "oid": lfs_file.oid,
                "tracked": lfs_file.tracked,
            }
            for lfs_file in lfs_files
        ]

    async def lfs_pull(
        self,
        workspace_id: UUID,
        objects: list[str] | None = None,
        all: bool = True,
    ) -> None:
        """
        Download LFS files from the remote repository.

        Args:
            workspace_id: Workspace ID
            objects: Specific objects to pull
            all: Pull all LFS objects
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        await self.git_adapter.lfs_pull(workspace.path, objects, all)

    async def lfs_push(
        self,
        workspace_id: UUID,
        remote: str = "origin",
        all: bool = True,
    ) -> None:
        """
        Push LFS objects to the remote repository.

        Args:
            workspace_id: Workspace ID
            remote: Remote name
            all: Push all LFS objects
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        await self.git_adapter.lfs_push(workspace.path, remote, all)

    async def lfs_fetch(
        self,
        workspace_id: UUID,
        objects: list[str] | None = None,
    ) -> None:
        """
        Fetch LFS objects from the remote without merging.

        Args:
            workspace_id: Workspace ID
            objects: Specific objects to fetch
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        await self.git_adapter.lfs_fetch(workspace.path, objects)

    async def lfs_install(self, workspace_id: UUID) -> None:
        """
        Install Git LFS hooks in the repository.

        Args:
            workspace_id: Workspace ID
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        await self.git_adapter.lfs_install(workspace.path)

    async def sparse_checkout(
        self,
        workspace_id: UUID,
        paths: list[str],
        mode: str = "replace",
    ) -> list[str]:
        """Configure sparse checkout for a repository.

        Args:
            workspace_id: Workspace ID
            paths: Paths to include in checkout
            mode: Operation mode (replace, add, remove)

        Returns:
            List of paths currently configured in sparse checkout
        """
        from mcp_git.git.adapter import SparseCheckoutOptions

        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        options = SparseCheckoutOptions(paths=paths, mode=mode)
        return await self.git_adapter.sparse_checkout(workspace.path, options)

    # Task operations

    async def create_git_task(
        self,
        operation: GitOperation,
        workspace_id: UUID,
        params: dict[str, Any],
    ) -> Task:
        """
        Create a Git task.

        Args:
            operation: Git operation type
            workspace_id: Workspace ID
            params: Operation parameters

        Returns:
            Created task
        """
        workspace = await self.workspace_manager.get_workspace(workspace_id)
        if workspace is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        return await self.task_manager.create_task(
            operation=operation,
            params=params,
            workspace_path=str(workspace.path),
        )

    async def get_task(self, task_id: UUID) -> Task | None:
        """
        Get task information.

        Args:
            task_id: Task ID

        Returns:
            Task information or None
        """
        return await self.task_manager.get_task(task_id)

    async def get_task_result(self, task_id: UUID) -> TaskResult | None:
        """
        Get task result.

        Args:
            task_id: Task ID

        Returns:
            Task result or None
        """
        return await self.task_manager.get_task_result(task_id)

    async def cancel_task(self, task_id: UUID) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled
        """
        return await self.task_manager.cancel_task(task_id)

    async def list_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        List tasks.

        Args:
            status: Filter by status
            limit: Maximum number

        Returns:
            List of task information
        """
        tasks = await self.task_manager.list_tasks(status=status, limit=limit)

        return [
            {
                "task_id": str(task.id),
                "operation": task.operation.value
                if hasattr(task.operation, "value")
                else task.operation,
                "status": task.status.value if hasattr(task.status, "value") else task.status,
                "progress": task.progress,
                "workspace_path": str(task.workspace_path) if task.workspace_path else None,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            }
            for task in tasks
        ]

    def get_stats(self) -> dict[str, Any]:
        """
        Get service statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "task_manager": self.task_manager.get_stats(),
            "workspace_usage": asyncio.run(self.workspace_manager.get_workspace_usage()),
        }
