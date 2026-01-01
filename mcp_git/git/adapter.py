"""
Git adapter interface for mcp-git.

This module defines the abstract interface for Git operations,
allowing different implementations (GitPython, CLI, etc.) to be used.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from mcp_git.storage.models import (
    BlameLine,
    BranchInfo,
    CommitInfo,
    DiffInfo,
    FileStatus,
)


@dataclass
class CloneOptions:
    """Options for repository cloning."""

    depth: int | None = None  # Shallow clone depth
    single_branch: bool = False  # Clone only one branch
    branch: str | None = None  # Specific branch to clone
    filter: str | None = None  # Partial clone filter (blob:none)
    filter_spec: str | None = None  # Git filter specification (e.g., blob:limit=1m)
    sparse_paths: list[str] | None = None  # Sparse checkout paths (only fetch specific paths)
    bare: bool = False  # Create bare repository
    mirror: bool = False  # Create mirror repository


@dataclass
class CommitOptions:
    """Options for creating a commit."""

    message: str
    author_name: str | None = None
    author_email: str | None = None
    amend: bool = False
    allow_empty: bool = False


@dataclass
class PushOptions:
    """Options for pushing to remote."""

    remote: str = "origin"
    branch: str | None = None
    force: bool = False
    force_with_lease: bool = False


@dataclass
class PullOptions:
    """Options for pulling from remote."""

    remote: str = "origin"
    branch: str | None = None
    rebase: bool = False


@dataclass
class MergeOptions:
    """Options for merging branches."""

    source_branch: str
    fast_forward: bool = True
    commit: bool = True


@dataclass
class DiffOptions:
    """Options for showing differences."""

    cached: bool = False  # Show staged changes
    unstaged: bool = False  # Show unstaged changes
    commit_oid: str | None = None  # Compare with specific commit
    path: Path | None = None  # Limit to specific path
    unified: int = 3  # Number of context lines


@dataclass
class LogOptions:
    """Options for viewing commit log."""

    max_count: int | None = None  # Limit number of commits
    skip: int = 0  # Skip N commits
    author: str | None = None  # Filter by author
    since: datetime | None = None  # Since date
    until: datetime | None = None  # Until date
    path: Path | None = None  # Filter by path
    all: bool = False  # Show all branches


@dataclass
class BlameOptions:
    """Options for git blame."""

    path: Path
    start_line: int | None = None  # Start line
    end_line: int | None = None  # End line


@dataclass
class CheckoutOptions:
    """Options for checkout."""

    branch: str
    create_new: bool = False  # Create new branch if not exists
    force: bool = False  # Force checkout, discard changes


@dataclass
class BranchOptions:
    """Options for branch operations."""

    name: str
    create: bool = False  # Create branch
    delete: bool = False  # Delete branch
    rename: bool = False  # Rename branch
    force: bool = False


@dataclass
class RebaseOptions:
    """Options for rebase."""

    branch: str | None = None  # Branch to rebase onto
    interactive: bool = False
    abort: bool = False
    continue_rebase: bool = False


@dataclass
class StashOptions:
    """Options for stash operations."""

    save: bool = False
    pop: bool = False
    apply: bool = False
    drop: bool = False
    list: bool = False
    message: str | None = None
    include_untracked: bool = False
    stash_index: int | None = None


@dataclass
class TagOptions:
    """Options for tag operations."""

    name: str
    create: bool = False
    delete: bool = False
    message: str | None = None  # Annotated tag message
    force: bool = False


@dataclass
class LfsOptions:
    """Options for Git LFS operations."""

    patterns: list[str]  # File patterns to track/untrack
    lockable: bool = False  # Make files lockable
    remote: str = "origin"  # Remote name for push/pull
    all: bool = True  # Push/pull all objects


@dataclass
class SparseCheckoutOptions:
    """Options for sparse checkout operations."""

    paths: list[str]  # List of paths to include in checkout
    mode: str = "replace"  # "replace" | "add" | "remove"


@dataclass
class LfsFileInfo:
    """Information about an LFS-tracked file."""

    name: str  # File name
    path: str  # Relative path
    size: int  # File size in bytes
    oid: str | None = None  # LFS object ID
    tracked: bool = True  # Whether file is tracked by LFS


class TransferProgressCallback(Protocol):
    """Protocol for transfer progress callbacks."""

    def __call__(
        self,
        progress: int,
        total: int,
        bytes_transferred: int,
    ) -> None:
        """Called during clone/fetch operations.

        Args:
            progress: Current progress (0-100)
            total: Total items
            bytes_transferred: Bytes transferred
        """
        ...


class MergeResult(Enum):
    """Result of a merge operation."""

    ALREADY_UP_TO_DATE = "already_up_to_date"
    FAST_FORWARD = "fast_forward"
    MERGED = "merged"
    CONFLICTED = "conflicted"
    FAILED = "failed"


class GitAdapter(ABC):
    """Abstract interface for Git operations.

    This interface defines the contract for all Git operations
    supported by mcp-git. Different implementations (GitPython, CLI)
    can be used based on requirements.
    """

    # Repository operations

    @abstractmethod
    async def clone(
        self,
        url: str,
        path: Path,
        options: CloneOptions | None = None,
        progress_callback: TransferProgressCallback | None = None,
    ) -> CommitInfo:
        """Clone a remote repository.

        Args:
            url: Repository URL
            path: Target directory
            options: Clone options
            progress_callback: Optional progress callback

        Returns:
            CommitInfo of the cloned repository's HEAD

        Raises:
            RepositoryNotFoundError: If repository doesn't exist
            AuthenticationError: If authentication fails
            McpGitError: On other errors
        """
        ...

    @abstractmethod
    async def init(
        self,
        path: Path,
        bare: bool = False,
        default_branch: str = "main",
    ) -> None:
        """Initialize a new repository.

        Args:
            path: Repository path
            bare: Create bare repository
            default_branch: Default branch name
        """
        ...

    @abstractmethod
    async def status(
        self,
        path: Path,
    ) -> list[FileStatus]:
        """Get working directory status.

        Args:
            path: Repository path

        Returns:
            List of FileStatus for each changed file
        """
        ...

    # File operations

    @abstractmethod
    async def add(
        self,
        path: Path,
        files: list[str],
    ) -> None:
        """Stage files for commit.

        Args:
            path: Repository path
            files: List of file patterns/paths to stage
        """
        ...

    @abstractmethod
    async def reset(
        self,
        path: Path,
        files: list[str] | None = None,
        hard: bool = False,
    ) -> None:
        """Reset staging area and/or working directory.

        Args:
            path: Repository path
            files: Files to reset (None for all)
            hard: Also reset working directory
        """
        ...

    @abstractmethod
    async def commit(
        self,
        path: Path,
        options: CommitOptions,
    ) -> str:
        """Create a new commit.

        Args:
            path: Repository path
            options: Commit options

        Returns:
            Commit OID
        """
        ...

    @abstractmethod
    async def restore(
        self,
        path: Path,
        files: list[str],
        staged: bool = False,
        revision: str | None = None,
    ) -> None:
        """Restore working tree files.

        Args:
            path: Repository path
            files: Files to restore
            staged: Restore from staging area
            revision: Restore from specific revision
        """
        ...

    # Remote operations

    @abstractmethod
    async def fetch(
        self,
        path: Path,
        remote: str | None = None,
        tags: bool = False,
        progress_callback: TransferProgressCallback | None = None,
    ) -> None:
        """Fetch from remote repository.

        Args:
            path: Repository path
            remote: Remote name (default: origin)
            tags: Fetch all tags
            progress_callback: Optional progress callback
        """
        ...

    @abstractmethod
    async def push(
        self,
        path: Path,
        options: PushOptions,
    ) -> None:
        """Push to remote repository.

        Args:
            path: Repository path
            options: Push options

        Raises:
            AuthenticationError: If authentication fails
            McpGitError: On other errors
        """
        ...

    @abstractmethod
    async def pull(
        self,
        path: Path,
        options: PullOptions,
    ) -> None:
        """Pull from remote repository.

        Args:
            path: Repository path
            options: Pull options

        Raises:
            MergeConflictError: If merge conflicts occur
            McpGitError: On other errors
        """
        ...

    # Branch operations

    @abstractmethod
    async def list_branches(
        self,
        path: Path,
        local: bool = True,
        remote: bool = False,
        all: bool = False,
    ) -> list[BranchInfo]:
        """List branches.

        Args:
            path: Repository path
            local: Include local branches
            remote: Include remote branches
            all: Include all branches (both local and remote)

        Returns:
            List of BranchInfo
        """
        ...

    @abstractmethod
    async def create_branch(
        self,
        path: Path,
        name: str,
        revision: str | None = None,
        force: bool = False,
    ) -> None:
        """Create a new branch.

        Args:
            path: Repository path
            name: Branch name
            revision: Starting revision
            force: Overwrite existing branch
        """
        ...

    @abstractmethod
    async def delete_branch(
        self,
        path: Path,
        name: str,
        force: bool = False,
        remote: bool = False,
    ) -> None:
        """Delete a branch.

        Args:
            path: Repository path
            name: Branch name
            force: Force delete unmerged branch
            remote: Delete remote branch
        """
        ...

    @abstractmethod
    async def checkout(
        self,
        path: Path,
        options: CheckoutOptions,
    ) -> None:
        """Checkout a branch or commit.

        Args:
            path: Repository path
            options: Checkout options
        """
        ...

    # Merge and rebase operations

    @abstractmethod
    async def merge(
        self,
        path: Path,
        options: MergeOptions,
    ) -> MergeResult:
        """Merge branches.

        Args:
            path: Repository path
            options: Merge options

        Returns:
            MergeResult indicating merge outcome

        Raises:
            MergeConflictError: If conflicts occur
        """
        ...

    @abstractmethod
    async def rebase(
        self,
        path: Path,
        options: RebaseOptions,
    ) -> None:
        """Rebase current branch onto another.

        Args:
            path: Repository path
            options: Rebase options

        Raises:
            McpGitError: If rebase fails
        """
        ...

    # History operations

    @abstractmethod
    async def log(
        self,
        path: Path,
        options: LogOptions | None = None,
    ) -> list[CommitInfo]:
        """Get commit history.

        Args:
            path: Repository path
            options: Log options

        Returns:
            List of CommitInfo
        """
        ...

    @abstractmethod
    async def show(
        self,
        path: Path,
        revision: str,
        path_filter: Path | None = None,
    ) -> DiffInfo:
        """Show a specific commit.

        Args:
            path: Repository path
            revision: Commit revision
            path_filter: Limit to specific path

        Returns:
            DiffInfo with commit details
        """
        ...

    @abstractmethod
    async def diff(
        self,
        path: Path,
        options: DiffOptions,
    ) -> list[DiffInfo]:
        """Show differences between commits, commit and working tree, etc.

        Args:
            path: Repository path
            options: Diff options

        Returns:
            List of DiffInfo
        """
        ...

    @abstractmethod
    async def blame(
        self,
        options: BlameOptions,
    ) -> list[BlameLine]:
        """Show who last modified each line of a file.

        Args:
            options: Blame options

        Returns:
            List of BlameLine for each line
        """
        ...

    # Stash operations

    @abstractmethod
    async def stash(
        self,
        path: Path,
        options: StashOptions,
    ) -> str | None:
        """Stash changes.

        Args:
            path: Repository path
            options: Stash options

        Returns:
            Stash reference or None
        """
        ...

    @abstractmethod
    async def list_stash(
        self,
        path: Path,
    ) -> list[dict[str, Any]]:
        """List stash entries.

        Args:
            path: Repository path

        Returns:
            List of stash entries
        """
        ...

    # Tag operations

    @abstractmethod
    async def list_tags(
        self,
        path: Path,
    ) -> list[str]:
        """List tags.

        Args:
            path: Repository path

        Returns:
            List of tag names
        """
        ...

    @abstractmethod
    async def create_tag(
        self,
        path: Path,
        options: TagOptions,
    ) -> None:
        """Create a tag.

        Args:
            path: Repository path
            options: Tag options
        """
        ...

    @abstractmethod
    async def delete_tag(
        self,
        path: Path,
        name: str,
    ) -> None:
        """Delete a tag.

        Args:
            path: Repository path
            name: Tag name
        """
        ...

    # Remote operations

    @abstractmethod
    async def list_remotes(
        self,
        path: Path,
    ) -> list[dict[str, str]]:
        """List remote repositories.

        Args:
            path: Repository path

        Returns:
            List of remote info dictionaries
        """
        ...

    @abstractmethod
    async def add_remote(
        self,
        path: Path,
        name: str,
        url: str,
    ) -> None:
        """Add a remote repository.

        Args:
            path: Repository path
            name: Remote name
            url: Remote URL
        """
        ...

    @abstractmethod
    async def remove_remote(
        self,
        path: Path,
        name: str,
    ) -> None:
        """Remove a remote repository.

        Args:
            path: Repository path
            name: Remote name
        """
        ...

    # Utility operations

    @abstractmethod
    async def get_head_commit(
        self,
        path: Path,
    ) -> CommitInfo | None:
        """Get the current HEAD commit.

        Args:
            path: Repository path

        Returns:
            CommitInfo of HEAD or None
        """
        ...

    @abstractmethod
    async def get_current_branch(
        self,
        path: Path,
    ) -> str | None:
        """Get the current branch name.

        Args:
            path: Repository path

        Returns:
            Current branch name or None (detached HEAD)
        """
        ...

    @abstractmethod
    async def is_repository(
        self,
        path: Path,
    ) -> bool:
        """Check if path is a valid Git repository.

        Args:
            path: Path to check

        Returns:
            True if valid Git repository
        """
        ...

    @abstractmethod
    async def count_commits(
        self,
        path: Path,
        branch: str | None = None,
    ) -> int:
        """Count commits in repository.

        Args:
            path: Repository path
            branch: Optional branch to count

        Returns:
            Number of commits
        """
        ...

    @abstractmethod
    async def is_merged(
        self,
        path: Path,
        branch: str,
        target: str,
    ) -> bool:
        """Check if branch is merged into target.

        Args:
            path: Repository path
            branch: Branch to check
            target: Target branch

        Returns:
            True if branch is merged into target
        """
        ...

    # Git LFS operations

    @abstractmethod
    async def lfs_init(
        self,
        path: Path,
    ) -> None:
        """Initialize Git LFS in a repository.

        Args:
            path: Repository path
        """
        ...

    @abstractmethod
    async def lfs_track(
        self,
        path: Path,
        patterns: list[str],
        lockable: bool = False,
    ) -> list[str]:
        """Track files with Git LFS.

        Args:
            path: Repository path
            patterns: File patterns to track
            lockable: Make files lockable

        Returns:
            List of patterns now being tracked
        """
        ...

    @abstractmethod
    async def lfs_untrack(
        self,
        path: Path,
        patterns: list[str],
    ) -> list[str]:
        """Stop tracking files with Git LFS.

        Args:
            path: Repository path
            patterns: File patterns to untrack

        Returns:
            List of patterns no longer tracked
        """
        ...

    @abstractmethod
    async def lfs_status(
        self,
        path: Path,
    ) -> list[LfsFileInfo]:
        """Show Git LFS status and tracked files.

        Args:
            path: Repository path

        Returns:
            List of LfsFileInfo for tracked files
        """
        ...

    @abstractmethod
    async def lfs_pull(
        self,
        path: Path,
        objects: list[str] | None = None,
        all: bool = True,
    ) -> None:
        """Download LFS files from the remote repository.

        Args:
            path: Repository path
            objects: Specific objects to pull
            all: Pull all LFS objects
        """
        ...

    @abstractmethod
    async def lfs_push(
        self,
        path: Path,
        remote: str = "origin",
        all: bool = True,
    ) -> None:
        """Push LFS objects to the remote repository.

        Args:
            path: Repository path
            remote: Remote name
            all: Push all LFS objects
        """
        ...

    @abstractmethod
    async def lfs_fetch(
        self,
        path: Path,
        objects: list[str] | None = None,
    ) -> None:
        """Fetch LFS objects from the remote without merging.

        Args:
            path: Repository path
            objects: Specific objects to fetch
        """
        ...

    @abstractmethod
    async def lfs_install(
        self,
        path: Path,
    ) -> None:
        """Install Git LFS hooks in the repository.

        Args:
            path: Repository path
        """
        ...

    @abstractmethod
    async def sparse_checkout(
        self,
        path: Path,
        options: SparseCheckoutOptions,
    ) -> list[str]:
        """Configure sparse checkout for a repository.

        Sparse checkout allows you to only checkout specific paths in a repository,
        reducing disk usage for large repositories.

        Args:
            path: Repository path
            options: Sparse checkout options with paths and mode

        Returns:
            List of paths currently configured in sparse checkout
        """
        ...


@dataclass
class SubmoduleOptions:
    """Options for submodule operations."""

    path: str  # Path where the submodule should be placed
    url: str  # URL of the submodule repository
    name: str | None = None  # Name for the submodule (optional, derived from path)
    branch: str | None = None  # Branch to track
    depth: int | None = None  # Shallow clone depth for submodule
    recursive: bool = True  # Initialize submodules recursively


@dataclass
class SubmoduleInfo:
    """Information about a submodule."""

    name: str  # Name of the submodule
    path: str  # Path relative to repository root
    url: str  # URL of the submodule repository
    branch: str  # Branch being tracked
    commit_oid: str  # Current commit OID
    status: str  # Status (e.g., "clean", "modified")
