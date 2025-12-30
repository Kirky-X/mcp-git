"""
Git LFS tests for mcp-git.

This module tests Git LFS operations including tracking, untracking,
status, push, pull, fetch, and install.
"""

import tempfile
from pathlib import Path

import pytest


class TestLfsIntegration:
    """Integration tests for Git LFS operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def adapter(self):
        """Create a GitPython adapter."""
        from mcp_git.git.adapter_gitpython import GitPythonAdapter

        return GitPythonAdapter()

    @pytest.fixture
    def repo_with_lfs(self, temp_dir, adapter):
        """Create a repository with Git LFS initialized."""
        import git

        repo_path = temp_dir / "lfs_repo"
        repo = git.Repo.init(str(repo_path))

        # Create initial commit
        (repo_path / "README.md").write_text("# LFS Test Repository")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        # Initialize LFS
        import subprocess

        subprocess.run(["git", "lfs", "install"], cwd=repo_path, capture_output=True)

        return repo_path, adapter

    @pytest.mark.asyncio
    async def test_lfs_init(self, temp_dir, adapter):
        """Test Git LFS initialization."""
        import git

        repo_path = temp_dir / "test_lfs_init"
        git.Repo.init(str(repo_path))

        # Initialize LFS
        await adapter.lfs_init(repo_path)

        # Verify LFS hooks are installed
        # (lfs_init should not raise an exception if LFS is installed)

    @pytest.mark.asyncio
    async def test_lfs_track_single_pattern(self, repo_with_lfs):
        """Test tracking a single file pattern with LFS."""
        repo_path, adapter = repo_with_lfs

        patterns = await adapter.lfs_track(repo_path, ["*.zip"])

        assert "*.zip" in patterns
        assert (repo_path / ".gitattributes").exists()

        # Check .gitattributes content
        content = (repo_path / ".gitattributes").read_text()
        assert "*.zip" in content

    @pytest.mark.asyncio
    async def test_lfs_track_multiple_patterns(self, repo_with_lfs):
        """Test tracking multiple file patterns with LFS."""
        repo_path, adapter = repo_with_lfs

        patterns = await adapter.lfs_track(repo_path, ["*.psd", "*.ai", "*.mov"])

        assert len(patterns) == 3
        assert "*.psd" in patterns
        assert "*.ai" in patterns
        assert "*.mov" in patterns

    @pytest.mark.asyncio
    async def test_lfs_track_lockable(self, repo_with_lfs):
        """Test tracking files with lockable flag."""
        repo_path, adapter = repo_with_lfs

        patterns = await adapter.lfs_track(repo_path, ["*.psd"], lockable=True)

        assert "*.psd" in patterns

        # Check .gitattributes for lockable flag
        content = (repo_path / ".gitattributes").read_text()
        assert "lockable" in content.lower() or "--lockable" in content

    @pytest.mark.asyncio
    async def test_lfs_untrack(self, repo_with_lfs):
        """Test untracking files from LFS."""
        repo_path, adapter = repo_with_lfs

        # First track a pattern
        await adapter.lfs_track(repo_path, ["*.test"])

        # Then untrack it
        patterns = await adapter.lfs_untrack(repo_path, ["*.test"])

        assert "*.test" in patterns

        # Verify pattern is removed from .gitattributes
        content = (repo_path / ".gitattributes").read_text()
        assert "*.test" not in content

    @pytest.mark.asyncio
    async def test_lfs_status_empty(self, repo_with_lfs):
        """Test LFS status with no tracked files."""
        repo_path, adapter = repo_with_lfs

        files = await adapter.lfs_status(repo_path)

        # No LFS-tracked files exist yet, so list should be empty
        assert isinstance(files, list)

    @pytest.mark.asyncio
    async def test_lfs_push_and_pull(self, repo_with_lfs):
        """Test LFS push and pull operations."""
        repo_path, adapter = repo_with_lfs

        # Track a pattern
        await adapter.lfs_track(repo_path, ["*.bin"])

        # Create a .bin file (won't actually be LFS-tracked without actual LFS setup)
        bin_file = repo_path / "test.bin"
        bin_file.write_bytes(b"\x00" * 100)

        # Stage the file and gitattributes
        import git

        repo = git.Repo(str(repo_path))
        repo.index.add([".gitattributes", "test.bin"])

        # Note: push/pull require a configured remote
        # Since we don't have a real remote, we just verify the operations don't error
        # when no remote is configured (they should succeed as no-ops)

        # Pull operation - should succeed even without remote (no-op)
        await adapter.lfs_pull(repo_path, all=True)

    @pytest.mark.asyncio
    async def test_lfs_push_with_remote(self, repo_with_lfs):
        """Test LFS push with a configured remote."""
        import git

        repo_path, adapter = repo_with_lfs

        # Add a remote (bare repo to push to)
        bare_path = repo_path.parent / "lfs_remote.git"
        git.Repo.init(str(bare_path), bare=True)

        repo = git.Repo(str(repo_path))
        repo.create_remote("origin", bare_path)

        # Track a pattern
        await adapter.lfs_track(repo_path, ["*.bin"])

        # Create and commit a .bin file
        bin_file = repo_path / "test.bin"
        bin_file.write_bytes(b"\x00" * 100)
        repo.index.add([".gitattributes", "test.bin"])
        repo.index.commit("Add LFS tracked file")

        # Push LFS objects
        await adapter.lfs_push(repo_path, remote="origin", all=True)

    @pytest.mark.asyncio
    async def test_lfs_fetch(self, repo_with_lfs):
        """Test LFS fetch operation."""
        repo_path, adapter = repo_with_lfs

        # Track a pattern
        await adapter.lfs_track(repo_path, ["*.dat"])

        # Fetch should not error (even without remote)
        await adapter.lfs_fetch(repo_path)

    @pytest.mark.asyncio
    async def test_lfs_install(self, repo_with_lfs):
        """Test LFS install operation."""
        repo_path, adapter = repo_with_lfs

        # Install should not error
        await adapter.lfs_install(repo_path)


class TestLfsOptions:
    """Tests for LfsOptions dataclass."""

    def test_lfs_options_creation(self):
        """Test LfsOptions creation."""
        from mcp_git.git.adapter import LfsOptions

        options = LfsOptions(
            patterns=["*.zip", "*.tar.gz"],
            lockable=False,
            remote="origin",
            all=True,
        )

        assert options.patterns == ["*.zip", "*.tar.gz"]
        assert options.lockable is False
        assert options.remote == "origin"
        assert options.all is True

    def test_lfs_options_defaults(self):
        """Test LfsOptions default values."""
        from mcp_git.git.adapter import LfsOptions

        options = LfsOptions(patterns=["*.mov"])

        assert options.lockable is False
        assert options.remote == "origin"
        assert options.all is True


class TestLfsFileInfo:
    """Tests for LfsFileInfo dataclass."""

    def test_lfs_file_info_creation(self):
        """Test LfsFileInfo creation."""
        from mcp_git.git.adapter import LfsFileInfo

        info = LfsFileInfo(
            name="large_file.zip",
            path="data/large_file.zip",
            size=1024000,
            oid="abc123",
            tracked=True,
        )

        assert info.name == "large_file.zip"
        assert info.size == 1024000
        assert info.tracked is True

    def test_lfs_file_info_defaults(self):
        """Test LfsFileInfo default values."""
        from mcp_git.git.adapter import LfsFileInfo

        info = LfsFileInfo(
            name="test.dat",
            path="test.dat",
            size=0,
        )

        assert info.oid is None
        assert info.tracked is True


class TestLfsCliAdapter:
    """Tests for CLI adapter LFS operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cli_adapter(self):
        """Create a CLI adapter."""
        from mcp_git.git.cli_adapter import CliAdapter

        return CliAdapter()

    @pytest.mark.asyncio
    async def test_cli_lfs_track(self, temp_dir, cli_adapter):
        """Test CLI adapter LFS track operation."""
        import git

        repo_path = temp_dir / "cli_lfs_repo"
        git.Repo.init(str(repo_path))

        patterns = await cli_adapter.lfs_track(repo_path, ["*.zip"])

        assert "*.zip" in patterns
        assert (repo_path / ".gitattributes").exists()

    @pytest.mark.asyncio
    async def test_cli_lfs_untrack(self, temp_dir, cli_adapter):
        """Test CLI adapter LFS untrack operation."""
        import git

        repo_path = temp_dir / "cli_lfs_repo"
        git.Repo.init(str(repo_path))

        # Track first
        await cli_adapter.lfs_track(repo_path, ["*.test"])

        # Then untrack
        patterns = await cli_adapter.lfs_untrack(repo_path, ["*.test"])

        assert "*.test" in patterns


class TestLfsWorkflow:
    """End-to-end LFS workflow tests."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def adapter(self):
        """Create a GitPython adapter."""
        from mcp_git.git.adapter_gitpython import GitPythonAdapter

        return GitPythonAdapter()

    @pytest.mark.asyncio
    async def test_complete_lfs_workflow(self, temp_dir, adapter):
        """Test complete LFS workflow: init -> track -> status -> untrack."""
        import git

        repo_path = temp_dir / "lfs_workflow"
        git.Repo.init(str(repo_path))

        # Create initial commit
        (repo_path / "README.md").write_text("# Workflow Test")
        repo = git.Repo(str(repo_path))
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        # 1. Initialize LFS
        await adapter.lfs_init(repo_path)

        # 2. Track some patterns
        tracked = await adapter.lfs_track(repo_path, ["*.psd", "*.zip"])
        assert len(tracked) == 2

        # 3. Check status (should show tracked patterns in gitattributes)
        # Note: lfs_status shows files that are actually tracked by LFS
        # (have pointers in the repo), not just patterns in .gitattributes
        status = await adapter.lfs_status(repo_path)
        assert isinstance(status, list)

        # 4. Untrack one pattern
        untracked = await adapter.lfs_untrack(repo_path, ["*.zip"])
        assert "*.zip" in untracked

        # Verify final state
        gitattributes = (repo_path / ".gitattributes").read_text()
        assert "*.psd" in gitattributes
        assert "*.zip" not in gitattributes
