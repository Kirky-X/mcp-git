"""
GitPython implementation of GitAdapter.

This module provides a native Python implementation of Git operations
using the GitPython library.
"""

import asyncio
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import git
from git import RemoteProgress, Repo

from mcp_git.error import (
    AuthenticationError,
    GitOperationError,
    MergeConflictError,
    RepositoryNotFoundError,
)
from mcp_git.retry import RetryPolicy, retry_async
from mcp_git.storage.models import (
    BlameLine,
    BranchInfo,
    CommitInfo,
    DiffInfo,
    FileStatus,
)
from mcp_git.utils import sanitize_path

from .adapter import (
    BlameOptions,
    CheckoutOptions,
    CloneOptions,
    CommitOptions,
    DiffOptions,
    GitAdapter,
    LogOptions,
    MergeOptions,
    MergeResult,
    PullOptions,
    PushOptions,
    RebaseOptions,
    StashOptions,
    TagOptions,
    TransferProgressCallback,
)


class GitPythonAdapter(GitAdapter):
    """GitPython implementation of GitAdapter."""

    def __init__(self):
        """Initialize the adapter."""
        self._credential_manager = None

    def set_credential_manager(self, credential_manager) -> None:
        """Set the credential manager for authentication.

        Args:
            credential_manager: Credential manager instance
        """
        self._credential_manager = credential_manager

    async def _execute_with_retry(
        self,
        operation: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """Execute a network operation with automatic retry.

        Args:
            operation: Type of operation (clone, push, pull, fetch)
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function
        """
        config = RetryPolicy.NETWORK
        if operation.lower() == "clone":
            config = RetryPolicy.CLONE

        return await retry_async(func, *args, config=config, **kwargs)

    async def _get_repo(self, path: Path) -> Repo:
        """Get a GitPython Repo object.

        Args:
            path: Repository path

        Returns:
            Repo object

        Raises:
            McpGitError: If not a valid repository
        """
        try:
            return Repo(str(path))
        except (git.InvalidGitRepositoryError, ValueError) as e:
            raise GitOperationError(
                message=f"Not a valid Git repository: {path}",
                details=str(e),
                suggestion="Ensure the path contains a valid .git directory",
            )

    async def _ensure_repo(self, path: Path) -> Repo:
        """Ensure repository exists, create if not.

        Args:
            path: Repository path

        Returns:
            Repo object
        """
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        try:
            return Repo(str(path))
        except git.InvalidGitRepositoryError:
            # Initialize new repository
            return Repo.init(str(path))

    async def clone(
        self,
        url: str,
        path: Path,
        options: CloneOptions | None = None,
        progress_callback: TransferProgressCallback | None = None,
    ) -> CommitInfo:
        """Clone a remote repository with automatic retry."""
        options = options or CloneOptions()

        # Sanitize the path
        path = sanitize_path(path)
        parent_dir = path.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

        async def _do_clone() -> CommitInfo:
            """Perform the actual clone operation."""
            # Prepare clone arguments
            clone_kwargs = {
                "depth": options.depth,
                "single_branch": options.single_branch,
                "no_single_branch": not options.single_branch,
                "bare": options.bare,
                "mirror": options.mirror,
            }

            # Remove None values
            clone_kwargs = {k: v for k, v in clone_kwargs.items() if v is not None}

            # Add branch if specified
            if options.branch:
                clone_kwargs["branch"] = options.branch

            # Add filter for partial clone (GitPython supports this)
            if options.filter:
                clone_kwargs["filter"] = options.filter

            # Create progress tracker if callback provided
            if progress_callback:

                class ProgressTracker(RemoteProgress):
                    def __init__(self, callback: TransferProgressCallback):
                        super().__init__()
                        self.callback = callback
                        self.op_codes = []

                    def update(
                        self,
                        op_code: int,
                        cur_count: str | float,
                        max_count: str | float | None,
                        message: str = "",
                    ):
                        if op_code & RemoteProgress.COUNTING:
                            self.op_codes.append(op_code)
                        total = float(max_count) if max_count else 100
                        progress = int((float(cur_count) / total) * 100) if total else 0
                        self.callback(progress, 100, 0)

                progress_tracker = ProgressTracker(progress_callback)
                clone_kwargs["progress"] = progress_tracker

            # Clone the repository
            repo = await asyncio.to_thread(
                git.Repo.clone_from,
                url,
                str(path),
                **clone_kwargs,
            )

            # Handle sparse checkout if specified
            if options.sparse_paths:
                await self._setup_sparse_checkout(repo, options.sparse_paths)

            # Handle filter_spec (additional filter specification)
            if options.filter_spec:
                await self._apply_filter_spec(repo, options.filter_spec)

            # Return commit info
            head_commit = repo.head.commit
            return CommitInfo(
                oid=head_commit.hexsha,
                message=head_commit.message,
                author_name=head_commit.author.name,
                author_email=head_commit.author.email,
                commit_time=datetime.fromtimestamp(head_commit.authored_date),
                parent_oids=[p.hexsha for p in head_commit.parents],
            )

        try:
            return await self._execute_with_retry("clone", _do_clone)

        except git.GitCommandError as e:
            if "not found" in str(e).lower() or "could not resolve" in str(e).lower():
                raise RepositoryNotFoundError(url)
            elif "authentication" in str(e).lower():
                raise AuthenticationError(message=str(e))
            else:
                raise GitOperationError(
                    message=f"Clone failed: {e.stderr}",
                    details=str(e),
                )
        except Exception as e:
            raise GitOperationError(
                message=f"Clone failed: {str(e)}",
                details=str(e),
            )

    async def init(
        self,
        path: Path,
        bare: bool = False,
        default_branch: str = "main",
    ) -> None:
        """Initialize a new repository."""
        path = sanitize_path(path)

        try:
            if bare:
                git.Repo.init(str(path), bare=True)
            else:
                repo = git.Repo.init(str(path))

                # Set default branch
                if default_branch and not bare:
                    # Create the branch if it doesn't exist
                    if default_branch not in repo.branches:
                        repo.create_head(default_branch)
                    # Checkout the default branch
                    repo.heads[default_branch].checkout()

        except Exception as e:
            raise GitOperationError(
                message=f"Init failed: {str(e)}",
                details=str(e),
            )

    async def _setup_sparse_checkout(
        self,
        repo: Repo,
        paths: list[str],
    ) -> None:
        """
        Set up sparse checkout for the repository.

        Args:
            repo: GitPython Repo object
            paths: List of paths to checkout
        """
        try:
            # Enable sparse checkout
            repo.git.update_index("--no-assume-unchanged")

            # Use git sparse-checkout
            sparse_dir = repo.worktree / ".git" / "info" / "sparse-checkout"
            sparse_dir.parent.mkdir(parents=True, exist_ok=True)

            with open(sparse_dir, "w") as f:
                for path in paths:
                    f.write(f"{path}\n")

            # Set sparse-checkout mode
            repo.git.config("core.sparseCheckout", "true")

        except Exception as e:
            raise GitOperationError(
                message=f"Failed to set up sparse checkout: {str(e)}",
                details=str(e),
            )

    async def _apply_filter_spec(
        self,
        repo: Repo,
        filter_spec: str,
    ) -> None:
        """
        Apply a filter specification to the repository.

        Args:
            repo: GitPython Repo object
            filter_spec: Git filter specification (e.g., "blob:limit=1m")
        """
        try:
            # Set the filter configuration
            repo.git.config("filter.lfs.required", "true")
            repo.git.config("filter.lfs.clean", "git-lfs clean -- %f")
            repo.git.config("filter.lfs.smudge", "git-lfs smudge -- %f")
            repo.git.config("filter.lfs.process", "git-lfs filter-process")

            # Apply custom filter if specified
            if filter_spec:
                parts = filter_spec.split("=")
                if len(parts) == 2:
                    filter_name, filter_value = parts
                    repo.git.config(
                        f"filter.{filter_name}.clean", f"git filter-{filter_name} clean -- %f"
                    )
                    repo.git.config(
                        f"filter.{filter_name}.smudge", f"git filter-{filter_name} smudge -- %f"
                    )

        except Exception as e:
            raise GitOperationError(
                message=f"Failed to apply filter spec: {str(e)}",
                details=str(e),
            )

    async def status(self, path: Path) -> list[FileStatus]:
        """Get working directory status."""
        repo = await self._get_repo(path)
        statuses = []

        # Get staged changes
        staged = repo.index.diff("HEAD")
        for item in staged:
            statuses.append(
                FileStatus(
                    path=item.a_path or item.b_path,
                    status="staged",
                )
            )

        # Get unstaged changes
        unstaged = repo.diff(None)
        for item in unstaged:
            if item.new_file:
                statuses.append(FileStatus(path=item.a_path, status="modified"))
            elif item.deleted_file:
                statuses.append(FileStatus(path=item.a_path, status="deleted"))
            else:
                statuses.append(FileStatus(path=item.a_path, status="modified"))

        # Get untracked files
        untracked = repo.untracked_files
        for file in untracked:
            statuses.append(FileStatus(path=file, status="untracked"))

        return statuses

    async def add(self, path: Path, files: list[str]) -> None:
        """Stage files for commit."""
        repo = await self._get_repo(path)

        try:
            # Convert to Path objects and resolve
            file_paths = []
            for f in files:
                full_path = path / f if not Path(f).is_absolute() else Path(f)
                full_path = sanitize_path(full_path)
                file_paths.append(str(full_path))

            repo.index.add(file_paths)

        except Exception as e:
            raise GitOperationError(
                message=f"Add failed: {str(e)}",
                details=str(e),
            )

    async def reset(
        self, path: Path, files: list[str] | None = None, hard: bool = False
    ) -> None:
        """Reset staging area and/or working directory."""
        repo = await self._get_repo(path)

        try:
            if hard:
                repo.head.reset(index=True, working_tree=True)
            elif files:
                for f in files:
                    full_path = path / f if not Path(f).is_absolute() else Path(f)
                    full_path = sanitize_path(full_path)
                    repo.index.remove([str(full_path)], working_tree=hard)
            else:
                repo.head.reset(index=True)

        except Exception as e:
            raise GitOperationError(
                message=f"Reset failed: {str(e)}",
                details=str(e),
            )

    async def commit(self, path: Path, options: CommitOptions) -> str:
        """Create a new commit."""
        repo = await self._get_repo(path)

        try:
            # Set author if provided
            author = None
            if options.author_name or options.author_email:
                author = git.Actor(
                    options.author_name or "Unknown",
                    options.author_email or "",
                )

            # Create commit
            commit = repo.index.commit(
                options.message,
                author=author,
            )

            return commit.hexsha

        except Exception as e:
            raise GitOperationError(
                message=f"Commit failed: {str(e)}",
                details=str(e),
            )

    async def restore(
        self,
        path: Path,
        files: list[str],
        staged: bool = False,
        revision: str | None = None,
    ) -> None:
        """Restore working tree files."""
        repo = await self._get_repo(path)

        try:
            if revision:
                commit = repo.commit(revision)
                for f in files:
                    full_path = path / f if not Path(f).is_absolute() else Path(f)
                    full_path = sanitize_path(full_path)
                    commit.tree[str(full_path)].stream_to_destination(str(full_path))
            elif staged:
                # Restore from index
                for f in files:
                    full_path = path / f if not Path(f).is_absolute() else Path(f)
                    full_path = sanitize_path(full_path)
                    repo.index.restore在工作区文件中保留暂存更改
                    repo.index.restore(str(full_path), working_tree=True)
            else:
                # Discard changes
                for f in files:
                    full_path = path / f if not Path(f).is_absolute() else Path(f)
                    full_path = sanitize_path(full_path)
                    if (full_path).exists():
                        full_path.unlink()

        except Exception as e:
            raise GitOperationError(
                message=f"Restore failed: {str(e)}",
                details=str(e),
            )

    async def fetch(
        self,
        path: Path,
        remote: str | None = None,
        tags: bool = False,
        progress_callback: TransferProgressCallback | None = None,
    ) -> None:
        """Fetch from remote repository with automatic retry."""
        repo = await self._get_repo(path)

        async def _do_fetch() -> None:
            """Perform the actual fetch operation."""
            if remote is None:
                # Get origin or first remote
                if repo.remotes:
                    remote = repo.remotes[0].name
                else:
                    return  # No remotes to fetch

            git_remote = repo.remotes[remote]

            # Prepare fetch kwargs
            fetch_kwargs = {}
            if progress_callback:

                class ProgressTracker(RemoteProgress):
                    def __init__(self, callback: TransferProgressCallback):
                        super().__init__()
                        self.callback = callback

                    def update(
                        self,
                        op_code: int,
                        cur_count: str | float,
                        max_count: str | float | None,
                        message: str = "",
                    ):
                        total = float(max_count) if max_count else 100
                        progress = int((float(cur_count) / total) * 100) if total else 0
                        self.callback(progress, 100, 0)

                fetch_kwargs["progress"] = ProgressTracker(progress_callback)

            # Fetch
            if tags:
                git_remote.fetch(tags=True, **fetch_kwargs)
            else:
                git_remote.fetch(**fetch_kwargs)

        try:
            await self._execute_with_retry("fetch", _do_fetch)

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Fetch failed: {str(e)}",
                details=str(e),
            )

    async def push(self, path: Path, options: PushOptions) -> None:
        """Push to remote repository with automatic retry."""
        repo = await self._get_repo(path)

        async def _do_push() -> None:
            """Perform the actual push operation."""
            if options.branch:
                # Push specific branch
                branch = repo.heads[options.branch]
                remote = repo.remotes[options.remote]

                push_kwargs = {}
                if options.force:
                    push_kwargs["force"] = True
                elif options.force_with_lease:
                    push_kwargs["force"] = True

                remote.push(refspec=f"{branch.name}:{branch.name}", **push_kwargs)
            else:
                # Push all branches
                remote = repo.remotes[options.remote]
                remote.push(**{"force": options.force} if options.force else {})

        try:
            await self._execute_with_retry("push", _do_push)

        except git.GitCommandError as e:
            if "authentication" in str(e).lower():
                raise AuthenticationError(message=str(e))
            elif "rejected" in str(e).lower() or "non-fast-forward" in str(e).lower():
                raise GitOperationError(
                    message="Push was rejected",
                    details=str(e),
                    suggestion="Pull the latest changes and try again, or use force push",
                )
            else:
                raise GitOperationError(
                    message=f"Push failed: {str(e)}",
                    details=str(e),
                )
        except Exception as e:
            raise GitOperationError(
                message=f"Push failed: {str(e)}",
                details=str(e),
            )

    async def pull(self, path: Path, options: PullOptions) -> None:
        """Pull from remote repository with automatic retry."""
        repo = await self._get_repo(path)

        async def _do_pull() -> None:
            """Perform the actual pull operation."""
            remote = repo.remotes[options.remote]

            pull_kwargs = {}
            if options.rebase:
                pull_kwargs["rebase"] = True

            # Fetch first
            remote.fetch()

            # Get remote branch
            branch_name = options.branch or repo.active_branch.name
            remote_branch = f"{options.remote}/{branch_name}"

            if options.rebase:
                # Rebase onto remote branch
                repo.git.rebase(remote_branch)
            else:
                # Merge remote branch
                repo.git.merge(remote_branch)

        try:
            await self._execute_with_retry("pull", _do_pull)

        except git.GitCommandError as e:
            if "conflict" in str(e).lower():
                # Check for merge conflicts
                if repo.index.conflicts:
                    conflicted_files = [c.path for c in repo.index.conflicts]
                    raise MergeConflictError(conflicted_files=conflicted_files)
            elif "authentication" in str(e).lower():
                raise AuthenticationError(message=str(e))
            else:
                raise GitOperationError(
                    message=f"Pull failed: {str(e)}",
                    details=str(e),
                )
        except Exception as e:
            raise GitOperationError(
                message=f"Pull failed: {str(e)}",
                details=str(e),
            )

    async def list_branches(
        self,
        path: Path,
        local: bool = True,
        remote: bool = False,
        all: bool = False,
    ) -> list[BranchInfo]:
        """List branches."""
        repo = await self._get_repo(path)
        branches = []

        if local or all:
            for branch in repo.branches:
                branches.append(
                    BranchInfo(
                        name=branch.name,
                        oid=branch.commit.hexsha,
                        is_local=True,
                        is_remote=False,
                    )
                )

        if remote or all:
            for remote_ref in repo.refs:
                if isinstance(remote_ref, git.RemoteReference):
                    branch_name = remote_ref.remote_head
                    if all or not any(b.name == branch_name and b.is_local for b in branches):
                        branches.append(
                            BranchInfo(
                                name=branch_name,
                                oid=remote_ref.commit.hexsha if remote_ref.commit else "",
                                is_local=False,
                                is_remote=True,
                            )
                        )

        return branches

    async def create_branch(
        self, path: Path, name: str, revision: str | None = None, force: bool = False
    ) -> None:
        """Create a new branch."""
        repo = await self._get_repo(path)

        try:
            if revision:
                commit = repo.commit(revision)
                repo.create_head(name, commit=commit, force=force)
            else:
                repo.create_head(name, force=force)

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Create branch failed: {str(e)}",
                details=str(e),
            )

    async def delete_branch(
        self, path: Path, name: str, force: bool = False, remote: bool = False
    ) -> None:
        """Delete a branch."""
        repo = await self._get_repo(path)

        try:
            if remote:
                if name.startswith("origin/"):
                    name = name[7:]
                repo.remotes.origin.push(refspec=f":refs/heads/{name}")
            else:
                branch = repo.branches[name]
                repo.delete_head(branch, force=force)

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Delete branch failed: {str(e)}",
                details=str(e),
            )

    async def checkout(self, path: Path, options: CheckoutOptions) -> None:
        """Checkout a branch or commit."""
        repo = await self._get_repo(path)

        try:
            if options.create_new:
                # Create and checkout new branch
                repo.create_head(options.branch)
                repo.heads[options.branch].checkout(
                    checkout_type="force" if options.force else None
                )
            else:
                # Checkout existing branch or commit
                if options.force:
                    repo.head.reference = repo.commit(options.branch)
                    repo.head.reset(index=True, working_tree=True)
                else:
                    repo.heads[options.branch].checkout()

        except (git.GitCommandError, ValueError) as e:
            raise GitOperationError(
                message=f"Checkout failed: {str(e)}",
                details=str(e),
            )

    async def merge(self, path: Path, options: MergeOptions) -> MergeResult:
        """Merge branches."""
        repo = await self._get_repo(path)

        try:
            # Get source branch commit
            source_commit = repo.commit(options.source_branch)

            # Perform merge
            if options.fast_forward:
                # Fast-forward only
                result = repo.merge_tree(
                    repo.head.commit,
                    source_commit,
                    allow_fast_forward=True,
                    renormalize=True,
                )
                if result:
                    # Can't fast-forward, need real merge
                    repo.index.merge_tree(source_commit)
                    repo.index.commit(
                        f"Merge {options.source_branch} into {repo.active_branch.name}",
                        parent_commits=[repo.head.commit, source_commit],
                    )
                    return MergeResult.MERGED
                else:
                    # Fast-forward
                    repo.head.reference = source_commit
                    repo.head.reset(index=True, working_tree=True)
                    return MergeResult.FAST_FORWARD
            else:
                # Regular merge
                repo.index.merge_tree(source_commit)
                if repo.index.conflicts:
                    # Conflicts detected
                    conflicted_files = [c.path for c in repo.index.conflicts]
                    raise MergeConflictError(conflicted_files=conflicted_files)

                repo.index.commit(
                    f"Merge {options.source_branch} into {repo.active_branch.name}",
                    parent_commits=[repo.head.commit, source_commit],
                )
                return MergeResult.MERGED

        except MergeConflictError:
            raise
        except git.GitCommandError as e:
            if "up to date" in str(e).lower():
                return MergeResult.ALREADY_UP_TO_DATE
            else:
                raise GitOperationError(
                    message=f"Merge failed: {str(e)}",
                    details=str(e),
                )

    async def rebase(self, path: Path, options: RebaseOptions) -> None:
        """Rebase current branch onto another."""
        repo = await self._get_repo(path)

        try:
            if options.abort:
                repo.git.rebase("--abort")
            elif options.continue_rebase:
                repo.git.rebase("--continue")
            elif options.branch:
                repo.git.rebase(options.branch)
            else:
                repo.git.rebase()

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Rebase failed: {str(e)}",
                details=str(e),
            )

    async def log(self, path: Path, options: LogOptions | None = None) -> list[CommitInfo]:
        """Get commit history."""
        repo = await self._get_repo(path)
        options = options or LogOptions()

        try:
            # Build git log arguments
            # Use %aI for ISO 8601 format (e.g., 2025-01-20T10:30:00+00:00)
            log_args = ["--format=%H%n%an%n%ae%n%aI%n%s%n%b"]
            log_args.append("--no-merges")

            if options.max_count:
                log_args.extend(["-n", str(options.max_count)])

            if options.since:
                log_args.extend(["--since", options.since.isoformat()])

            if options.until:
                log_args.extend(["--until", options.until.isoformat()])

            if options.author:
                log_args.extend(["--author", options.author])

            if options.all:
                log_args.append("--all")

            output = repo.git.log(*log_args)

            commits = []
            lines = output.strip().split("\n")

            # Each commit produces 6 lines: hash, author_name, author_email, date, subject, body
            for i in range(0, len(lines), 6):
                if i + 5 < len(lines):
                    commit = CommitInfo(
                        oid=lines[i],
                        message=lines[i + 4],
                        author_name=lines[i + 1],
                        author_email=lines[i + 2],
                        commit_time=datetime.fromisoformat(lines[i + 3]),
                        parent_oids=[],
                    )
                    commits.append(commit)

            return commits

        except Exception as e:
            raise GitOperationError(
                message=f"Log failed: {str(e)}",
                details=str(e),
            )

    async def show(self, path: Path, revision: str, path_filter: Path | None = None) -> DiffInfo:
        """Show a specific commit."""
        repo = await self._get_repo(path)

        try:
            commit = repo.commit(revision)
            diff_text = ""

            for parent in commit.parents:
                diff_text += repo.git.diff(parent.hexsha, commit.hexsha)

            return DiffInfo(
                old_path="",
                new_path=revision,
                change_type="commit",
                diff_lines=diff_text.split("\n"),
            )

        except Exception as e:
            raise GitOperationError(
                message=f"Show failed: {str(e)}",
                details=str(e),
            )

    async def diff(self, path: Path, options: DiffOptions) -> list[DiffInfo]:
        """Show differences."""
        repo = await self._get_repo(path)
        diffs = []

        try:
            if options.cached:
                # Show staged changes
                diffs_text = repo.git.diff("--cached")
            elif options.commit_oid:
                # Compare with specific commit
                if options.cached:
                    diffs_text = repo.git.diff(options.commit_oid + "^", options.commit_oid)
                else:
                    diffs_text = repo.git.diff(options.commit_oid)
            else:
                # Show working directory changes
                diffs_text = repo.git.diff()

            # Parse diff output
            diff_info = DiffInfo(
                old_path="",
                new_path="",
                change_type="modified",
                diff_lines=diffs_text.split("\n"),
            )
            diffs.append(diff_info)

            return diffs

        except Exception as e:
            raise GitOperationError(
                message=f"Diff failed: {str(e)}",
                details=str(e),
            )

    async def blame(self, options: BlameOptions) -> list[BlameLine]:
        """Show who last modified each line of a file."""
        path = sanitize_path(options.path)

        try:
            repo = Repo(str(path.parent))
            blame = repo.blame(options.path)

            lines = []
            for line_commit, line_no in blame:
                lines.append(
                    BlameLine(
                        line_number=line_no,
                        commit_oid=line_commit.hexsha,
                        author=line_commit.author.name,
                        date=datetime.fromtimestamp(line_commit.authored_date),
                        summary=line_commit.message.split("\n")[0],
                    )
                )

            return lines

        except Exception as e:
            raise GitOperationError(
                message=f"Blame failed: {str(e)}",
                details=str(e),
            )

    async def stash(self, path: Path, options: StashOptions) -> str | None:
        """Stash changes."""
        repo = await self._get_repo(path)

        try:
            if options.save:
                stash_args = ["save"]
                if options.message:
                    stash_args.append(options.message)
                if options.include_untracked:
                    stash_args.append("-u")

                result = repo.git.stash(*stash_args)
                if "No local changes to save" not in result:
                    return result.split("\n")[0]

            elif options.pop:
                repo.git.stash("pop")
            elif options.apply:
                repo.git.stash("apply")
            elif options.drop:
                if options.stash_index is not None:
                    repo.git.stash(f"drop stash@{{{options.stash_index}}}")
                else:
                    repo.git.stash("drop")
            elif options.list:
                repo.git.stash("list")

            return None

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Stash failed: {str(e)}",
                details=str(e),
            )

    async def list_stash(self, path: Path) -> list[dict[str, Any]]:
        """List stash entries."""
        repo = await self._get_repo(path)

        try:
            # Use %aI for ISO 8601 format timestamp
            output = repo.git.stash("list", "--format=%H|%gd|%gs|%aI")
            entries = []

            for line in output.strip().split("\n"):
                if line:
                    parts = line.split("|")
                    entries.append(
                        {
                            "oid": parts[0] if len(parts) > 0 else "",
                            "branch": parts[1] if len(parts) > 1 else "",
                            "message": parts[2] if len(parts) > 2 else "",
                            "timestamp": parts[3] if len(parts) > 3 else "",
                        }
                    )

            return entries

        except Exception as e:
            raise GitOperationError(
                message=f"List stash failed: {str(e)}",
                details=str(e),
            )

    async def list_tags(self, path: Path) -> list[str]:
        """List tags."""
        repo = await self._get_repo(path)

        try:
            return [tag.name for tag in repo.tags]

        except Exception as e:
            raise GitOperationError(
                message=f"List tags failed: {str(e)}",
                details=str(e),
            )

    async def create_tag(self, path: Path, options: TagOptions) -> None:
        """Create a tag."""
        repo = await self._get_repo(path)

        try:
            if options.message:
                repo.create_tag(options.name, message=options.message, force=options.force)
            else:
                repo.create_tag(options.name, force=options.force)

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Create tag failed: {str(e)}",
                details=str(e),
            )

    async def delete_tag(self, path: Path, name: str) -> None:
        """Delete a tag."""
        repo = await self._get_repo(path)

        try:
            tag = repo.tags[name]
            repo.delete_tag(tag)

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Delete tag failed: {str(e)}",
                details=str(e),
            )

    async def list_remotes(self, path: Path) -> list[dict[str, str]]:
        """List remote repositories."""
        repo = await self._get_repo(path)

        try:
            remotes = []
            for remote in repo.remotes:
                remotes.append(
                    {
                        "name": remote.name,
                        "url": remote.url,
                    }
                )
            return remotes

        except Exception as e:
            raise GitOperationError(
                message=f"List remotes failed: {str(e)}",
                details=str(e),
            )

    async def add_remote(self, path: Path, name: str, url: str) -> None:
        """Add a remote repository."""
        repo = await self._get_repo(path)

        try:
            repo.create_remote(name, url)

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Add remote failed: {str(e)}",
                details=str(e),
            )

    async def remove_remote(self, path: Path, name: str) -> None:
        """Remove a remote repository."""
        repo = await self._get_repo(path)

        try:
            remote = repo.remotes[name]
            repo.delete_remote(remote)

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Remove remote failed: {str(e)}",
                details=str(e),
            )

    async def get_head_commit(self, path: Path) -> CommitInfo | None:
        """Get the current HEAD commit."""
        try:
            repo = await self._get_repo(path)
            commit = repo.head.commit

            return CommitInfo(
                oid=commit.hexsha,
                message=commit.message,
                author_name=commit.author.name,
                author_email=commit.author.email,
                commit_time=datetime.fromtimestamp(commit.authored_date),
                parent_oids=[p.hexsha for p in commit.parents],
            )

        except (ValueError, AttributeError):
            return None

    async def get_current_branch(self, path: Path) -> str | None:
        """Get the current branch name."""
        try:
            repo = await self._get_repo(path)
            return repo.active_branch.name

        except (TypeError, ValueError):
            return None  # Detached HEAD

    async def is_repository(self, path: Path) -> bool:
        """Check if path is a valid Git repository."""
        try:
            # First check if path exists
            if not path.exists():
                return False
            repo = Repo(str(path))
            return not repo.bare
        except (git.InvalidGitRepositoryError, ValueError, TypeError):
            return False

    async def count_commits(self, path: Path, branch: str | None = None) -> int:
        """Count commits in repository."""
        try:
            repo = await self._get_repo(path)

            if branch:
                commit_range = f"{branch}..HEAD"
            else:
                commit_range = "HEAD"

            output = repo.git.rev_list("--count", commit_range)
            return int(output.strip())

        except Exception:
            return 0

    async def is_merged(self, path: Path, branch: str, target: str) -> bool:
        """Check if branch is merged into target."""
        try:
            repo = await self._get_repo(path)
            repo.git.merge_base("--is-ancestor", branch, target)
            return True
        except git.GitCommandError:
            return False

    # Git LFS operations

    async def lfs_init(self, path: Path) -> None:
        """Initialize Git LFS in a repository."""
        repo = await self._get_repo(path)

        try:
            # Check if LFS is already initialized
            try:
                repo.git.lfs("version")
            except git.GitCommandError:
                raise GitOperationError(
                    message="Git LFS is not installed",
                    details="Please install Git LFS (https://git-lfs.github.io/)",
                    suggestion="Run: git lfs install",
                )

            # Initialize LFS
            repo.git.lfs("install")

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Git LFS initialization failed: {str(e)}",
                details=str(e),
            )

    async def lfs_track(self, path: Path, patterns: list[str], lockable: bool = False) -> list[str]:
        """Track files with Git LFS."""
        repo = await self._get_repo(path)

        try:
            tracked_patterns = []
            for pattern in patterns:
                # Add pattern to .gitattributes
                lockable_flag = "--lockable" if lockable else ""
                repo.git.lfs("track", lockable_flag, pattern)
                tracked_patterns.append(pattern)

            # Stage .gitattributes if it was created/modified
            try:
                repo.index.add([".gitattributes"])
            except (git.GitCommandError, ValueError):
                # No .gitattributes to stage or already tracked
                pass

            return tracked_patterns

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Git LFS track failed: {str(e)}",
                details=str(e),
            )

    async def lfs_untrack(self, path: Path, patterns: list[str]) -> list[str]:
        """Stop tracking files with Git LFS."""
        repo = await self._get_repo(path)

        try:
            untracked_patterns = []
            for pattern in patterns:
                # Remove pattern from .gitattributes
                repo.git.lfs("untrack", pattern)
                untracked_patterns.append(pattern)

            # Stage .gitattributes if it was modified
            try:
                repo.index.add([".gitattributes"])
            except (git.GitCommandError, ValueError):
                pass

            return untracked_patterns

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Git LFS untrack failed: {str(e)}",
                details=str(e),
            )

    async def lfs_status(self, path: Path) -> list["LfsFileInfo"]:
        """Show Git LFS status and tracked files."""
        from mcp_git.git.adapter import LfsFileInfo

        repo = await self._get_repo(path)

        try:
            # Get list of tracked files using git lfs ls-files
            output = repo.git.lfs("ls-files", "--name-only", "--size")
            files = []

            if output and output.strip():
                for line in output.strip().split("\n"):
                    if line:
                        parts = line.rsplit("(", 1)
                        if len(parts) == 2:
                            name = parts[0].strip()
                            size_str = parts[1].replace(")", "").strip()
                            try:
                                size = int(size_str)
                            except ValueError:
                                size = 0
                            files.append(
                                LfsFileInfo(
                                    name=name,
                                    path=name,
                                    size=size,
                                    tracked=True,
                                )
                            )
                        else:
                            name = line.strip()
                            files.append(
                                LfsFileInfo(
                                    name=name,
                                    path=name,
                                    size=0,
                                    tracked=True,
                                )
                            )

            return files

        except git.GitCommandError as e:
            if "not a git repository" in str(e).lower():
                return []
            raise GitOperationError(
                message=f"Git LFS status failed: {str(e)}",
                details=str(e),
            )

    async def lfs_pull(
        self, path: Path, objects: list[str] | None = None, all: bool = True
    ) -> None:
        """Download LFS files from the remote repository."""
        repo = await self._get_repo(path)

        try:
            if all:
                repo.git.lfs("pull")
            elif objects:
                for obj in objects:
                    repo.git.lfs("pull", "--objects", obj)

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Git LFS pull failed: {str(e)}",
                details=str(e),
            )

    async def lfs_push(self, path: Path, remote: str = "origin", all: bool = True) -> None:
        """Push LFS objects to the remote repository."""
        repo = await self._get_repo(path)

        try:
            if all:
                repo.git.lfs("push", remote, "--all")
            else:
                # Push only tracked files that have changes
                repo.git.lfs("push", remote)

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Git LFS push failed: {str(e)}",
                details=str(e),
            )

    async def lfs_fetch(self, path: Path, objects: list[str] | None = None) -> None:
        """Fetch LFS objects from the remote without merging."""
        repo = await self._get_repo(path)

        try:
            if objects:
                for obj in objects:
                    repo.git.lfs("fetch", "--objects", obj)
            else:
                repo.git.lfs("fetch")

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Git LFS fetch failed: {str(e)}",
                details=str(e),
            )

    async def lfs_install(self, path: Path) -> None:
        """Install Git LFS hooks in the repository."""
        repo = await self._get_repo(path)

        try:
            repo.git.lfs("install")

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Git LFS install failed: {str(e)}",
                details=str(e),
            )

    # Submodule operations

    async def add_submodule(
        self,
        path: Path,
        options: "SubmoduleOptions",
    ) -> None:
        """Add a submodule to the repository."""

        repo = await self._get_repo(path)

        try:
            # Build submodule add command
            cmd = ["add"]
            if options.name:
                cmd.extend(["--name", options.name])
            if options.branch:
                cmd.extend(["--branch", options.branch])
            if options.depth:
                cmd.extend(["--depth", str(options.depth)])

            # Add the URL and path at the end
            cmd.extend(["--", options.url, options.path])

            # Execute the submodule command using repo.git.submodule()
            repo.git.submodule(*cmd)

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Failed to add submodule: {str(e)}",
                details=str(e),
            )

    async def update_submodule(
        self,
        path: Path,
        name: str | None = None,
        init: bool = True,
    ) -> None:
        """Update a submodule."""
        repo = await self._get_repo(path)

        try:
            cmd = ["submodule", "update", "--init", "--recursive"]
            if name:
                cmd.append(name)
            repo.git(*cmd)

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Failed to update submodule: {str(e)}",
                details=str(e),
            )

    async def deinit_submodule(
        self,
        path: Path,
        name: str | None = None,
        force: bool = False,
    ) -> None:
        """Deinitialize a submodule."""
        repo = await self._get_repo(path)

        try:
            cmd = ["submodule", "deinit"]
            if force:
                cmd.append("--force")
            if name:
                cmd.append(name)
            else:
                cmd.append("--all")
            repo.git(*cmd)

        except git.GitCommandError as e:
            raise GitOperationError(
                message=f"Failed to deinitialize submodule: {str(e)}",
                details=str(e),
            )

    async def list_submodules(self, path: Path) -> list["SubmoduleInfo"]:
        """List submodules in the repository."""
        from mcp_git.git.adapter import SubmoduleInfo

        repo = await self._get_repo(path)

        try:
            # Get submodule status
            status_output = repo.git.submodule("status")
            submodules = []

            for line in status_output.strip().split("\n"):
                if line:
                    # Parse: <commit> <path> <name>
                    parts = line.split()
                    if len(parts) >= 2:
                        commit_oid = parts[0]
                        submodule_path = parts[1]

                        # Get URL and other info
                        info_output = repo.git.config("--get", f"submodule.{submodule_path}.url")

                        # Get branch
                        branch_output = repo.git.config(
                            "--get", f"submodule.{submodule_path}.branch", default="HEAD"
                        )

                        submodules.append(
                            SubmoduleInfo(
                                name=submodule_path.split("/")[-1],
                                path=submodule_path,
                                url=info_output.strip() if info_output else "",
                                branch=branch_output.strip() if branch_output else "HEAD",
                                commit_oid=commit_oid.lstrip("+- "),  # Remove status prefix
                                status="clean",
                            )
                        )

            return submodules

        except git.GitCommandError as e:
            if "no submodule" in str(e).lower():
                return []
            raise GitOperationError(
                message=f"Failed to list submodules: {str(e)}",
                details=str(e),
            )
