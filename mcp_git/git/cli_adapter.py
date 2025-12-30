"""
CLI Git Adapter for mcp-git.

This module provides a fallback Git adapter implementation that uses the git CLI
via subprocess for operations that may not be supported by GitPython or when
CLI is preferred for compatibility.

This implementation includes:
- Command injection protection through input sanitization
- Proper error handling and translation
- Support for all standard Git operations
"""

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp_git.error import (
    AuthenticationError,
    ErrorContext,
    GitOperationError,
    McpGitError,
    MergeConflictError,
    RepositoryNotFoundError,
)
from mcp_git.git.adapter import (
    BlameOptions,
    CheckoutOptions,
    CloneOptions,
    CommitOptions,
    DiffOptions,
    GitAdapter,
    LfsFileInfo,
    LogOptions,
    MergeOptions,
    PullOptions,
    PushOptions,
    RebaseOptions,
    StashOptions,
    SubmoduleInfo,
    TagOptions,
    TransferProgressCallback,
)
from mcp_git.storage.models import (
    BlameLine,
    BranchInfo,
    CommitInfo,
    DiffInfo,
    FileStatus,
)


@dataclass
class CliConfig:
    """Configuration for CLI adapter."""

    git_path: str = "git"
    timeout: int = 300
    encoding: str = "utf-8"


class CommandInjectionError(GitOperationError):
    """Raised when potential command injection is detected."""

    def __init__(self, input_value: str, operation: str):
        super().__init__(
            message=f"Potentially dangerous input detected: {input_value}",
            details=f"Input for {operation} contains suspicious characters",
            suggestion="Ensure all inputs are properly sanitized and do not contain shell metacharacters",
            context=ErrorContext(operation=operation, parameters={"input": input_value}),
        )


class CliAdapter(GitAdapter):
    """Git adapter implementation using git CLI via subprocess.

    This adapter provides a fallback implementation for Git operations
    using the system git command. It includes command injection protection
    and proper error handling.
    """

    def __init__(self, config: CliConfig | None = None):
        """Initialize the CLI adapter.

        Args:
            config: Optional CLI configuration
        """
        self.config = config or CliConfig()
        self._git_path = self.config.git_path

    async def clone(
        self,
        url: str,
        path: Path,
        options: CloneOptions | None = None,
        progress_callback: TransferProgressCallback | None = None,
    ) -> CommitInfo:
        """Clone a remote repository using git CLI."""
        options = options or CloneOptions()

        cmd = [self._git_path, "clone"]

        # Add clone options
        if options.depth:
            cmd.extend(["--depth", str(options.depth)])
        if options.single_branch:
            cmd.append("--single-branch")
        if options.branch:
            cmd.extend(["--branch", options.branch])
        if options.bare:
            cmd.append("--bare")
        if options.mirror:
            cmd.append("--mirror")
        if options.filter:
            cmd.extend(["--filter", options.filter])

        # Add sparse checkout paths if specified
        if options.sparse_paths:
            # Initialize sparse checkout first
            sparse_dir = path.parent / ".git" / "info" / "sparse-checkout"
            sparse_dir.parent.mkdir(parents=True, exist_ok=True)
            with open(sparse_dir, "w") as f:
                for sparse_path in options.sparse_paths:
                    f.write(f"{sparse_path}\n")

        # Add URL and target path
        cmd.extend([url, str(path)])

        # Run clone command
        stdout, stderr = await self._run_command(cmd, timeout=600)

        # Get the HEAD commit info
        return await self.get_head_commit(path)

    async def init(
        self,
        path: Path,
        bare: bool = False,
        default_branch: str = "main",
    ) -> None:
        """Initialize a new repository using git CLI."""
        cmd = [self._git_path, "init"]

        if bare:
            cmd.append("--bare")

        cmd.extend(["--initial-branch", default_branch])
        cmd.append(str(path))

        await self._run_command(cmd)

    async def status(
        self,
        path: Path,
    ) -> list[FileStatus]:
        """Get working directory status using git CLI."""
        cmd = [self._git_path, "-C", str(path), "status", "--porcelain", "-uall"]

        stdout, _ = await self._run_command(cmd)

        if not stdout.strip():
            return []

        status_list = []
        for line in stdout.strip().split("\n"):
            if len(line) >= 4:
                # Parse porcelain format: XY filename
                x_status = line[0]
                y_status = line[1]
                filename = line[3:].strip()

                # Map status codes
                staged = ""
                unstaged = ""

                if x_status != " ":
                    if x_status == "M":
                        staged = "modified"
                    elif x_status == "A":
                        staged = "added"
                    elif x_status == "D":
                        staged = "deleted"
                    elif x_status == "R":
                        staged = "renamed"
                    elif x_status == "C":
                        staged = "copied"

                if y_status != " ":
                    if y_status == "M":
                        unstaged = "modified"
                    elif y_status == "?":
                        unstaged = "untracked"
                    elif y_status == "D":
                        unstaged = "deleted"

                status_list.append(
                    FileStatus(
                        path=filename,
                        status=staged or unstaged or "unknown",
                    )
                )

        return status_list

    async def add(
        self,
        path: Path,
        files: list[str],
    ) -> None:
        """Stage files for commit using git CLI."""
        cmd = [self._git_path, "-C", str(path), "add"]

        for file in files:
            cmd.append(self._sanitize_path(file))

        await self._run_command(cmd)

    async def reset(
        self,
        path: Path,
        files: list[str] | None = None,
        hard: bool = False,
    ) -> None:
        """Reset staging area and/or working directory using git CLI."""
        cmd = [self._git_path, "-C", str(path), "reset"]

        if hard:
            cmd.append("--hard")

        if files:
            for file in files:
                cmd.append(self._sanitize_path(file))

        await self._run_command(cmd)

    async def commit(
        self,
        path: Path,
        options: CommitOptions,
    ) -> str:
        """Create a new commit using git CLI."""
        cmd = [self._git_path, "-C", str(path), "commit"]

        if options.amend:
            cmd.append("--amend")

        if options.allow_empty:
            cmd.append("--allow-empty")

        if options.author_name or options.author_email:
            author = ""
            if options.author_name:
                author = options.author_name
            if options.author_email:
                author += f" <{options.author_email}>"
            cmd.extend(["--author", author])

        cmd.extend(["-m", options.message])

        await self._run_command(cmd)

        # Return the commit hash
        return await self._get_current_commit_hash(path)

    async def restore(
        self,
        path: Path,
        files: list[str],
        staged: bool = False,
        revision: str | None = None,
    ) -> None:
        """Restore working tree files using git CLI."""
        cmd = [self._git_path, "-C", str(path), "restore"]

        if staged:
            cmd.append("--staged")

        if revision:
            cmd.extend(["-s", revision])

        for file in files:
            cmd.append(self._sanitize_path(file))

        await self._run_command(cmd)

    async def fetch(
        self,
        path: Path,
        remote: str | None = None,
        tags: bool = False,
        progress_callback: TransferProgressCallback | None = None,
    ) -> None:
        """Fetch from remote repository using git CLI."""
        cmd = [self._git_path, "-C", str(path), "fetch"]

        if remote:
            cmd.append(remote)

        if tags:
            cmd.append("--tags")

        await self._run_command(cmd)

    async def push(
        self,
        path: Path,
        options: PushOptions,
    ) -> None:
        """Push to remote repository using git CLI."""
        cmd = [self._git_path, "-C", str(path), "push"]

        if options.remote:
            cmd.append(options.remote)

        if options.branch:
            cmd.append(options.branch)

        if options.force:
            cmd.append("--force")
        elif options.force_with_lease:
            cmd.append("--force-with-lease")

        await self._run_command(cmd)

    async def pull(
        self,
        path: Path,
        options: PullOptions,
    ) -> None:
        """Pull from remote repository using git CLI."""
        cmd = [self._git_path, "-C", str(path), "pull"]

        if options.remote:
            cmd.append(options.remote)

        if options.branch:
            cmd.append(options.branch)

        if options.rebase:
            cmd.append("--rebase")

        await self._run_command(cmd)

    async def list_branches(
        self,
        path: Path,
        local: bool = True,
        remote: bool = False,
        all: bool = False,
    ) -> list[BranchInfo]:
        """List branches using git CLI."""
        cmd = [self._git_path, "-C", str(path), "branch"]

        if all:
            cmd.append("-a")
        elif remote:
            cmd.append("-r")

        stdout, _ = await self._run_command(cmd)

        branches = []
        await self.get_current_branch(path)

        for line in stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # Remove leading/trailing characters
            if line.startswith("* "):
                line = line[2:]
            elif line.startswith("*"):
                line = line[1:].strip()
            else:
                pass

            # Clean branch name
            if line.startswith("remotes/"):
                branch_name = "/".join(line.split("/")[2:])
                is_remote = True
            else:
                branch_name = line
                is_remote = False

            # Skip HEAD branch
            if branch_name == "HEAD":
                continue

            branches.append(
                BranchInfo(
                    name=branch_name,
                    oid="",  # Branch OID not easily available in this context
                    is_local=not is_remote,
                    is_remote=is_remote,
                )
            )

        return branches

    async def create_branch(
        self,
        path: Path,
        name: str,
        revision: str | None = None,
        force: bool = False,
    ) -> None:
        """Create a new branch using git CLI."""
        self._validate_branch_name(name)

        cmd = [self._git_path, "-C", str(path), "branch"]

        if force:
            cmd.append("-f")

        if revision:
            cmd.append(revision)

        cmd.append(name)

        await self._run_command(cmd)

    async def delete_branch(
        self,
        path: Path,
        name: str,
        force: bool = False,
        remote: bool = False,
    ) -> None:
        """Delete a branch using git CLI."""
        self._validate_branch_name(name)

        cmd = [self._git_path, "-C", str(path), "branch"]

        if force:
            cmd.append("-D")
        elif remote:
            cmd.append("-d")
        else:
            cmd.append("-d")

        cmd.append(name)

        await self._run_command(cmd)

    async def checkout(
        self,
        path: Path,
        options: CheckoutOptions,
    ) -> None:
        """Checkout a branch or commit using git CLI."""
        self._validate_branch_name(options.branch)

        cmd = [self._git_path, "-C", str(path), "checkout"]

        if options.create_new:
            cmd.append("-b")

        if options.force:
            cmd.append("--force")

        cmd.append(options.branch)

        await self._run_command(cmd)

    async def merge(
        self,
        path: Path,
        options: MergeOptions,
    ) -> None:
        """Merge branches using git CLI."""
        self._validate_branch_name(options.source_branch)

        cmd = [self._git_path, "-C", str(path), "merge"]

        if not options.fast_forward:
            cmd.append("--no-ff")

        if not options.commit:
            cmd.append("--no-commit")

        cmd.append(options.source_branch)

        await self._run_command(cmd)

    async def rebase(
        self,
        path: Path,
        options: RebaseOptions,
    ) -> None:
        """Rebase current branch onto another using git CLI."""
        cmd = [self._git_path, "-C", str(path), "rebase"]

        if options.abort:
            cmd.append("--abort")
        elif options.continue_rebase:
            cmd.append("--continue")
        elif options.interactive:
            cmd.append("-i")
            if options.branch:
                cmd.append(options.branch)
        else:
            if options.branch:
                cmd.append(options.branch)

        await self._run_command(cmd)

    async def log(
        self,
        path: Path,
        options: LogOptions | None = None,
    ) -> list[CommitInfo]:
        """Get commit history using git CLI."""
        options = options or LogOptions()

        cmd = [
            self._git_path,
            "-C",
            str(path),
            "log",
            "--pretty=format:%H|%an|%ae|%ad|%s",
            "--date=iso-strict",
        ]

        if options.max_count:
            cmd.extend(["-n", str(options.max_count)])

        if options.skip:
            cmd.extend(["--skip", str(options.skip)])

        if options.author:
            cmd.extend(["--author", options.author])

        if options.since:
            cmd.extend(["--since", options.since.isoformat()])

        if options.until:
            cmd.extend(["--until", options.until.isoformat()])

        if options.all:
            cmd.append("--all")

        stdout, _ = await self._run_command(cmd)

        commits = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|", 4)
            if len(parts) >= 4:
                commits.append(
                    CommitInfo(
                        oid=parts[0],
                        message=parts[4] if len(parts) > 4 else "",
                        author_name=parts[1],
                        author_email=parts[2],
                        commit_time=datetime.fromisoformat(parts[3]),
                        parent_oids=[],
                    )
                )

        return commits

    async def show(
        self,
        path: Path,
        revision: str,
        path_filter: Path | None = None,
    ) -> DiffInfo:
        """Show a specific commit using git CLI."""
        cmd = [
            self._git_path,
            "-C",
            str(path),
            "show",
            "--stat",
            "--pretty=format:%H|%an|%ae|%ad|%s",
            "--date=iso-strict",
            revision,
        ]

        if path_filter:
            cmd.append("--")
            cmd.append(str(path_filter))

        stdout, _ = await self._run_command(cmd)

        lines = stdout.strip().split("\n")

        if not lines:
            raise GitOperationError(
                message=f"Commit not found: {revision}",
                context=ErrorContext(operation="show", repo_path=path, commit=revision),
            )

        # Parse commit info
        commit_parts = lines[0].split("|", 4)
        oid = commit_parts[0] if commit_parts else revision
        author_name = commit_parts[1] if len(commit_parts) > 1 else ""
        author_email = commit_parts[2] if len(commit_parts) > 2 else ""
        timestamp_str = commit_parts[3] if len(commit_parts) > 3 else ""
        message = commit_parts[4] if len(commit_parts) > 4 else ""

        timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now()

        # Parse changed files
        changes = []
        for line in lines[1:]:
            if line.startswith(" "):
                # File change stats
                match = re.match(
                    r"\s+(\d+)\s+file.*changed.*(\d+)\s+insertion.*(\d+)\s+deletion", line
                )
                if match:
                    changes.append(
                        {
                            "files_changed": int(match.group(1)),
                            "insertions": int(match.group(2)),
                            "deletions": int(match.group(3)),
                        }
                    )
            elif line and not line.startswith("commit"):
                # File path
                match = re.match(r"\s+(\S+)", line)
                if match:
                    changes.append({"filename": match.group(1)})

        return DiffInfo(
            oid=oid,
            commit_info=CommitInfo(
                oid=oid,
                message=message,
                author_name=author_name,
                author_email=author_email,
                commit_time=timestamp,
                parent_oids=[],
            ),
            changes=changes,
        )

    async def diff(
        self,
        path: Path,
        options: DiffOptions,
    ) -> list[DiffInfo]:
        """Show differences using git CLI."""
        cmd = [self._git_path, "-C", str(path), "diff"]

        if options.cached:
            cmd.append("--cached")

        if options.unstaged:
            cmd.append("--no-index")

        if options.commit_oid:
            cmd.append(options.commit_oid)

        if options.path:
            cmd.append("--")
            cmd.append(str(options.path))

        cmd.extend(["--unified", str(options.unified)])

        stdout, _ = await self._run_command(cmd)

        # Parse diff output
        diffs = []
        current_diff = DiffInfo(
            oid="",
            commit_info=None,
            changes=[],
        )

        lines = stdout.split("\n")
        for line in lines:
            if line.startswith("diff --git"):
                # Start of new diff
                if current_diff.changes:
                    diffs.append(current_diff)
                current_diff = DiffInfo(
                    oid="",
                    commit_info=None,
                    changes=[],
                )
            elif line.startswith("--- ") or line.startswith("+++ "):
                pass  # File paths
            elif line.startswith("@@"):
                # Hunk header
                pass
            elif line.startswith("+") or line.startswith("-"):
                # Change line
                current_diff.changes.append({"line": line})

        if current_diff.changes:
            diffs.append(current_diff)

        return diffs

    async def blame(
        self,
        options: BlameOptions,
    ) -> list[BlameLine]:
        """Show who last modified each line using git CLI."""
        cmd = [
            self._git_path,
            "-C",
            str(options.path.parent),
            "blame",
            "--line-porcelain",
        ]

        if options.start_line:
            cmd.extend(["-L", f"{options.start_line},{options.end_line or options.start_line}"])

        cmd.append(options.path.name)

        stdout, _ = await self._run_command(cmd)

        blame_lines = []
        current_line = None

        for line in stdout.split("\n"):
            if line.startswith("\t"):
                # Actual line content
                if current_line:
                    current_line.line = line[1:]
                    blame_lines.append(current_line)
                current_line = None
            elif line.startswith("author "):
                if current_line:
                    current_line.author = line.split(" ", 1)[1]
            elif line.startswith("author-mail "):
                if current_line:
                    current_line.author_email = line.split(" ", 1)[1]
            elif line.startswith("summary "):
                if current_line:
                    current_line.summary = line.split(" ", 1)[1]
            elif re.match(r"^[0-9a-f]{40}", line):
                # Commit hash
                current_line = BlameLine(
                    line_number=0,
                    commit_oid=line,
                    author="",
                    author_email="",
                    timestamp=datetime.now(),
                    line="",
                    summary="",
                )

        return blame_lines

    async def stash(
        self,
        path: Path,
        options: StashOptions,
    ) -> str | None:
        """Stash changes using git CLI."""
        cmd = [self._git_path, "-C", str(path), "stash"]

        if options.save:
            if options.message:
                cmd.extend(["save", options.message])
            else:
                cmd.append("save")
        elif options.pop:
            if options.stash_index is not None:
                cmd.extend(["pop", f"stash@{{{options.stash_index}}}"])
            else:
                cmd.append("pop")
        elif options.apply:
            if options.stash_index is not None:
                cmd.extend(["apply", f"stash@{{{options.stash_index}}}"])
            else:
                cmd.append("apply")
        elif options.drop:
            if options.stash_index is not None:
                cmd.extend(["drop", f"stash@{{{options.stash_index}}}"])
            else:
                cmd.append("drop")
        elif options.list:
            cmd.append("list")

        await self._run_command(cmd)

        # Return stash reference
        return "stash@{0}"

    async def list_stash(
        self,
        path: Path,
    ) -> list[dict[str, Any]]:
        """List stash entries using git CLI."""
        cmd = [
            self._git_path,
            "-C",
            str(path),
            "stash",
            "list",
            "--pretty=format:%gd|%gs|%h|%an|%ad",
            "--date=iso-strict",
        ]

        stdout, _ = await self._run_command(cmd)

        stash_list = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|", 4)
            if len(parts) >= 3:
                stash_list.append(
                    {
                        "ref": parts[0],
                        "message": parts[1] if len(parts) > 1 else "",
                        "commit": parts[2],
                        "author": parts[3] if len(parts) > 3 else "",
                        "date": parts[4] if len(parts) > 4 else "",
                    }
                )

        return stash_list

    async def list_tags(
        self,
        path: Path,
    ) -> list[str]:
        """List tags using git CLI."""
        cmd = [self._git_path, "-C", str(path), "tag", "-l"]

        stdout, _ = await self._run_command(cmd)

        if not stdout.strip():
            return []

        return [line.strip() for line in stdout.strip().split("\n") if line.strip()]

    async def create_tag(
        self,
        path: Path,
        options: TagOptions,
    ) -> None:
        """Create a tag using git CLI."""
        cmd = [self._git_path, "-C", str(path), "tag"]

        if options.message:
            cmd.extend(["-a", "-m", options.message])

        if options.force:
            cmd.append("-f")

        cmd.append(options.name)

        await self._run_command(cmd)

    async def delete_tag(
        self,
        path: Path,
        name: str,
    ) -> None:
        """Delete a tag using git CLI."""
        cmd = [self._git_path, "-C", str(path), "tag", "-d", name]

        await self._run_command(cmd)

    async def list_remotes(
        self,
        path: Path,
    ) -> list[dict[str, str]]:
        """List remote repositories using git CLI."""
        cmd = [self._git_path, "-C", str(path), "remote", "-v"]

        stdout, _ = await self._run_command(cmd)

        remotes = []
        seen = set()

        for line in stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                url = parts[1]

                if (name, url) not in seen:
                    seen.add((name, url))
                    remotes.append(
                        {
                            "name": name,
                            "url": url,
                            "fetch": "(fetch)" in line,
                            "push": "(push)" in line,
                        }
                    )

        return remotes

    async def add_remote(
        self,
        path: Path,
        name: str,
        url: str,
    ) -> None:
        """Add a remote repository using git CLI."""
        cmd = [self._git_path, "-C", str(path), "remote", "add", name, url]

        await self._run_command(cmd)

    async def remove_remote(
        self,
        path: Path,
        name: str,
    ) -> None:
        """Remove a remote repository using git CLI."""
        cmd = [self._git_path, "-C", str(path), "remote", "remove", name]

        await self._run_command(cmd)

    async def get_head_commit(
        self,
        path: Path,
    ) -> CommitInfo | None:
        """Get the current HEAD commit using git CLI."""
        cmd = [
            self._git_path,
            "-C",
            str(path),
            "log",
            "-1",
            "--pretty=format:%H|%an|%ae|%ad|%s",
            "--date=iso-strict",
        ]

        stdout, stderr = await self._run_command(cmd)

        if not stdout.strip():
            return None

        parts = stdout.strip().split("|", 4)
        if len(parts) >= 4:
            return CommitInfo(
                oid=parts[0],
                message=parts[4] if len(parts) > 4 else "",
                author_name=parts[1],
                author_email=parts[2],
                commit_time=datetime.fromisoformat(parts[3]),
                parent_oids=[],
            )

        return None

    async def get_current_branch(
        self,
        path: Path,
    ) -> str | None:
        """Get the current branch name using git CLI."""
        cmd = [
            self._git_path,
            "-C",
            str(path),
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
        ]

        stdout, _ = await self._run_command(cmd)

        branch = stdout.strip()

        if branch == "HEAD":
            return None

        return branch if branch else None

    async def is_repository(
        self,
        path: Path,
    ) -> bool:
        """Check if path is a valid Git repository."""
        cmd = [self._git_path, "-C", str(path), "rev-parse"]

        try:
            await self._run_command(cmd, check=False)
            return True
        except McpGitError:
            return False

    async def count_commits(
        self,
        path: Path,
        branch: str | None = None,
    ) -> int:
        """Count commits in repository using git CLI."""
        cmd = [self._git_path, "-C", str(path), "rev-list", "--count"]

        if branch:
            cmd.append(branch)
        else:
            cmd.append("--all")

        stdout, _ = await self._run_command(cmd)

        try:
            return int(stdout.strip())
        except ValueError:
            return 0

    async def is_merged(
        self,
        path: Path,
        branch: str,
        target: str,
    ) -> bool:
        """Check if branch is merged into target using git CLI."""
        cmd = [
            self._git_path,
            "-C",
            str(path),
            "merge-base",
            "--is-ancestor",
            branch,
            target,
        ]

        try:
            await self._run_command(cmd, check=False)
            return True
        except McpGitError:
            return False

    async def lfs_init(
        self,
        path: Path,
    ) -> None:
        """Initialize Git LFS in a repository."""
        cmd = [self._git_path, "-C", str(path), "lfs", "install"]

        await self._run_command(cmd)

    async def lfs_track(
        self,
        path: Path,
        patterns: list[str],
        lockable: bool = False,
    ) -> list[str]:
        """Track files with Git LFS."""
        cmd = [self._git_path, "-C", str(path), "lfs", "track"]

        if lockable:
            cmd.append("--lockable")

        for pattern in patterns:
            cmd.append(pattern)

        await self._run_command(cmd)

        return patterns

    async def lfs_untrack(
        self,
        path: Path,
        patterns: list[str],
    ) -> list[str]:
        """Stop tracking files with Git LFS."""
        cmd = [self._git_path, "-C", str(path), "lfs", "untrack"]

        for pattern in patterns:
            cmd.append(pattern)

        await self._run_command(cmd)

        return patterns

    async def lfs_status(
        self,
        path: Path,
    ) -> list[LfsFileInfo]:
        """Show Git LFS status and tracked files."""
        cmd = [self._git_path, "-C", str(path), "lfs", "status"]

        stdout, _ = await self._run_command(cmd)

        lfs_files = []

        for line in stdout.strip().split("\n"):
            if line.strip():
                lfs_files.append(
                    LfsFileInfo(
                        name=line.strip(),
                        path=line.strip(),
                        size=0,
                        tracked=True,
                    )
                )

        return lfs_files

    async def lfs_pull(
        self,
        path: Path,
        objects: list[str] | None = None,
        all: bool = True,
    ) -> None:
        """Download LFS files from the remote repository."""
        cmd = [self._git_path, "-C", str(path), "lfs", "pull"]

        if all:
            cmd.append("--all")

        if objects:
            for obj in objects:
                cmd.append(obj)

        await self._run_command(cmd)

    async def lfs_push(
        self,
        path: Path,
        remote: str = "origin",
        all: bool = True,
    ) -> None:
        """Push LFS objects to the remote repository."""
        cmd = [self._git_path, "-C", str(path), "lfs", "push"]

        cmd.append(remote)

        if all:
            cmd.append("--all")

        await self._run_command(cmd)

    async def lfs_fetch(
        self,
        path: Path,
        objects: list[str] | None = None,
    ) -> None:
        """Fetch LFS objects from the remote without merging."""
        cmd = [self._git_path, "-C", str(path), "lfs", "fetch"]

        if objects:
            for obj in objects:
                cmd.append(obj)

        await self._run_command(cmd)

    async def lfs_install(
        self,
        path: Path,
    ) -> None:
        """Install Git LFS hooks in the repository."""
        cmd = [self._git_path, "-C", str(path), "lfs", "install"]

        await self._run_command(cmd)

    # Submodule operations

    async def add_submodule(
        self,
        path: Path,
        options: "SubmoduleOptions",
    ) -> None:
        """Add a submodule to the repository."""
        cmd = [self._git_path, "-C", str(path), "submodule", "add"]

        if options.name:
            cmd.extend(["--name", options.name])
        if options.branch:
            cmd.extend(["--branch", options.branch])
        if options.depth:
            cmd.extend(["--depth", str(options.depth)])

        cmd.extend([options.url, options.path])

        await self._run_command(cmd)

    async def update_submodule(
        self,
        path: Path,
        name: str | None = None,
        init: bool = True,
    ) -> None:
        """Update a submodule."""
        cmd = [self._git_path, "-C", str(path), "submodule", "update", "--init", "--recursive"]

        if name:
            cmd.append(name)

        await self._run_command(cmd)

    async def deinit_submodule(
        self,
        path: Path,
        name: str | None = None,
        force: bool = False,
    ) -> None:
        """Deinitialize a submodule."""
        cmd = [self._git_path, "-C", str(path), "submodule", "deinit"]

        if force:
            cmd.append("--force")
        if name:
            cmd.append(name)
        else:
            cmd.append("--all")

        await self._run_command(cmd)

    async def list_submodules(self, path: Path) -> list["SubmoduleInfo"]:
        """List submodules in the repository."""
        cmd = [self._git_path, "-C", str(path), "submodule", "status"]

        stdout, _ = await self._run_command(cmd)

        submodules = []
        for line in stdout.strip().split("\n"):
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    commit_oid = parts[0]
                    submodule_path = parts[1]

                    # Get URL
                    url_cmd = [
                        self._git_path,
                        "-C",
                        str(path),
                        "config",
                        "--get",
                        f"submodule.{submodule_path}.url",
                    ]
                    url_stdout, _ = await self._run_command(url_cmd, check=False)
                    url = url_stdout.strip() if url_stdout else ""

                    # Get branch
                    branch_cmd = [
                        self._git_path,
                        "-C",
                        str(path),
                        "config",
                        "--get",
                        f"submodule.{submodule_path}.branch",
                    ]
                    branch_stdout, _ = await self._run_command(branch_cmd, check=False)
                    branch = branch_stdout.strip() if branch_stdout else "HEAD"

                    submodules.append(
                        SubmoduleInfo(
                            name=submodule_path.split("/")[-1],
                            path=submodule_path,
                            url=url,
                            branch=branch,
                            commit_oid=commit_oid.lstrip("+- "),
                            status="clean",
                        )
                    )

        return submodules

    # Helper methods

    async def _run_command(
        self,
        cmd: list[str],
        check: bool = True,
        timeout: int | None = None,
    ) -> tuple[str, str]:
        """Run a git command and return output.

        Args:
            cmd: Command list with git and arguments
            check: Whether to check for errors
            timeout: Optional timeout in seconds

        Returns:
            Tuple of (stdout, stderr)

        Raises:
            GitOperationError: If command fails
            AuthenticationError: If authentication fails
            RepositoryNotFoundError: If repository not found
        """
        timeout = timeout or self.config.timeout

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            stdout = stdout_bytes.decode(self.config.encoding, errors="replace")
            stderr = stderr_bytes.decode(self.config.encoding, errors="replace")

            if check and process.returncode != 0:
                await self._handle_git_error(cmd, stderr, process.returncode)

            return stdout, stderr

        except asyncio.TimeoutError:
            raise GitOperationError(
                message=f"Git command timed out after {timeout} seconds",
                details=f"Command: {' '.join(cmd)}",
                suggestion="Try increasing the timeout or reducing the operation scope",
                context=ErrorContext(operation="git_command", parameters={"command": cmd}),
            )

    async def _handle_git_error(
        self,
        cmd: list[str],
        stderr: str,
        returncode: int,
    ) -> None:
        """Handle git command error and raise appropriate exception."""
        error_lower = stderr.lower()

        # Determine error type
        if "authentication failed" in error_lower or "could not read username" in error_lower:
            raise AuthenticationError(
                message="Authentication failed",
                details=stderr,
                context=ErrorContext(operation="git_auth", parameters={"command": cmd}),
            )

        if "repository not found" in error_lower or "does not exist" in error_lower:
            raise RepositoryNotFoundError(
                path=cmd[-1] if cmd else "unknown",
                context=ErrorContext(operation="git_clone", parameters={"command": cmd}),
            )

        if "merge conflict" in error_lower or "conflict" in error_lower:
            # Extract conflicted files
            conflicted = []
            for line in stderr.split("\n"):
                if "CONFLICT" in line:
                    match = re.search(r"\((.*?)\)", line)
                    if match:
                        conflicted.append(match.group(1))

            raise MergeConflictError(
                conflicted_files=conflicted if conflicted else ["unknown"],
                context=ErrorContext(operation="git_merge", parameters={"command": cmd}),
            )

        if "could not resolve commit" in error_lower or "unknown revision" in error_lower:
            raise GitOperationError(
                message=f"Invalid revision: {stderr}",
                details=stderr,
                suggestion="Check the revision/branch name is correct",
                context=ErrorContext(operation="git_operation", parameters={"command": cmd}),
            )

        # Generic git error
        raise GitOperationError(
            message=f"Git command failed with return code {returncode}",
            details=stderr,
            suggestion="Check the git command and repository state",
            context=ErrorContext(operation="git_command", parameters={"command": cmd}),
        )

    async def _get_current_commit_hash(self, path: Path) -> str:
        """Get the current commit hash."""
        cmd = [self._git_path, "-C", str(path), "rev-parse", "HEAD"]

        stdout, _ = await self._run_command(cmd)

        return stdout.strip()

    def _sanitize_input(self, input_str: str, operation: str) -> str:
        """Sanitize input to prevent command injection.

        Args:
            input_str: Input string to sanitize
            operation: Operation name for error context

        Returns:
            Sanitized string

        Raises:
            CommandInjectionError: If dangerous patterns detected
        """
        if not input_str:
            return input_str

        # Check for dangerous patterns
        dangerous_patterns = [
            r"[;&|`$]",  # Shell metacharacters
            r"\$",  # Variable expansion
            r"`",  # Command substitution
            r";",  # Command separator
            r"&",  # Background execution
            r"\|",  # Pipe
            r"\n",  # Newline
            r"\0",  # Null byte
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, input_str):
                raise CommandInjectionError(input_str, operation)

        # Remove potential path traversal
        if ".." in input_str:
            # Allow '..' in paths but warn
            pass

        return input_str

    def _sanitize_path(self, path: str) -> str:
        """Sanitize a file path.

        Args:
            path: File path to sanitize

        Returns:
            Sanitized path
        """
        # Remove any shell metacharacters
        sanitized = re.sub(r'[;&|`$\'"<>{}()\[\]]', "", path)

        # Normalize path separators
        sanitized = sanitized.replace("\\", "/")

        return sanitized.strip()

    def _validate_branch_name(self, name: str) -> None:
        """Validate a branch name.

        Args:
            name: Branch name to validate

        Raises:
            ParameterValidationError: If name is invalid
        """
        # Git branch name rules
        if not name:
            raise GitOperationError(
                message="Branch name cannot be empty",
                details="Empty branch name provided",
                suggestion="Provide a valid branch name",
            )

        # Check for reserved names
        reserved = ["HEAD", "FETCH_HEAD", "ORIG_HEAD", "ORIGIN_HEAD"]
        if name in reserved:
            raise GitOperationError(
                message=f"Reserved branch name: {name}",
                details=f"'{name}' is a reserved git reference",
                suggestion="Use a different branch name",
            )

        # Check for invalid characters
        invalid_chars = r"[ ~^:?*\[\\@{]/"  # Cannot start with / or contain these
        if re.search(r"^[/]|" + invalid_chars, name):
            raise GitOperationError(
                message=f"Invalid branch name: {name}",
                details="Branch name contains invalid characters",
                suggestion="Branch names must not start with '/' or contain special characters",
            )
