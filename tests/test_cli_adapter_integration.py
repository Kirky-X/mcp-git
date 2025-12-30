"""Tests for CLI adapter integration with retry mechanism."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_git.git.adapter import TagOptions
from mcp_git.git.cli_adapter import CliAdapter, CliConfig


class TestCliAdapterIntegration:
    """Integration tests for CLI adapter."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cli_adapter(self):
        """Create a CLI adapter for testing."""
        config = CliConfig(
            git_path="git",
            timeout=30,
            encoding="utf-8",
        )
        return CliAdapter(config)

    @pytest.mark.asyncio
    async def test_init_new_repository(self, temp_dir, cli_adapter):
        """Test initializing a new repository."""
        repo_path = temp_dir / "test_repo"
        await cli_adapter.init(repo_path, bare=False, default_branch="main")

        # Verify repository was created
        assert repo_path.exists()
        assert (repo_path / ".git").exists()

    @pytest.mark.asyncio
    async def test_init_bare_repository(self, temp_dir, cli_adapter):
        """Test initializing a bare repository."""
        repo_path = temp_dir / "bare_repo.git"
        await cli_adapter.init(repo_path, bare=True)

        # Verify bare repository was created
        assert repo_path.exists()

    @pytest.mark.asyncio
    async def test_status_clean_repository(self, temp_dir, cli_adapter):
        """Test status on clean repository."""
        repo_path = temp_dir / "clean_repo"
        await cli_adapter.init(repo_path)

        # Status should return empty list for clean repo
        status = await cli_adapter.status(repo_path)
        assert isinstance(status, list)

    @pytest.mark.asyncio
    async def test_status_with_changes(self, temp_dir, cli_adapter):
        """Test status with unstaged changes."""
        repo_path = temp_dir / "changes_repo"
        await cli_adapter.init(repo_path)

        # Create a file
        test_file = repo_path / "test.txt"
        test_file.write_text("test content")

        # Status should show untracked file
        status = await cli_adapter.status(repo_path)
        assert len(status) > 0

    @pytest.mark.asyncio
    async def test_add_file(self, temp_dir, cli_adapter):
        """Test staging a file."""
        repo_path = temp_dir / "add_repo"
        await cli_adapter.init(repo_path)

        # Create and stage a file
        test_file = repo_path / "test.txt"
        test_file.write_text("test content")

        await cli_adapter.add(repo_path, ["test.txt"])

    @pytest.mark.asyncio
    async def test_commit_file(self, temp_dir, cli_adapter):
        """Test committing a file."""
        repo_path = temp_dir / "commit_repo"
        await cli_adapter.init(repo_path)

        # Create and stage a file
        test_file = repo_path / "test.txt"
        test_file.write_text("test content")
        await cli_adapter.add(repo_path, ["test.txt"])

        # Commit
        commit_oid = await cli_adapter.commit(
            repo_path,
            options=MagicMock(
                message="Test commit",
                author_name="Test User",
                author_email="test@example.com",
                amend=False,
                allow_empty=False,
            ),
        )

        assert commit_oid is not None
        assert len(commit_oid) == 40  # SHA-1 hash length

    @pytest.mark.asyncio
    async def test_list_branches(self, temp_dir, cli_adapter):
        """Test listing branches."""
        repo_path = temp_dir / "branch_repo"
        await cli_adapter.init(repo_path)

        # Create a commit first (needed for branch operations)
        test_file = repo_path / "test.txt"
        test_file.write_text("initial content")
        await cli_adapter.add(repo_path, ["test.txt"])
        await cli_adapter.commit(
            repo_path,
            options=MagicMock(
                message="Initial commit",
                author_name="Test",
                author_email="test@test.com",
                amend=False,
                allow_empty=False,
            ),
        )

        # List branches
        branches = await cli_adapter.list_branches(repo_path)

        assert isinstance(branches, list)
        # Should have at least the default branch
        assert len(branches) > 0

    @pytest.mark.asyncio
    async def test_create_and_delete_branch(self, temp_dir, cli_adapter):
        """Test creating and deleting a branch."""
        repo_path = temp_dir / "branch_test_repo"
        await cli_adapter.init(repo_path)

        # Create a commit first (needed for branch)
        test_file = repo_path / "test.txt"
        test_file.write_text("initial content")
        await cli_adapter.add(repo_path, ["test.txt"])
        await cli_adapter.commit(
            repo_path,
            options=MagicMock(
                message="Initial commit",
                author_name="Test",
                author_email="test@test.com",
                amend=False,
                allow_empty=False,
            ),
        )

        # Create branch
        await cli_adapter.create_branch(repo_path, "feature", force=False)

        # Verify branch exists
        branches = await cli_adapter.list_branches(repo_path)
        branch_names = [b.name for b in branches]
        assert "feature" in branch_names

        # Delete branch
        await cli_adapter.delete_branch(repo_path, "feature", force=False)

        # Verify branch is gone
        branches = await cli_adapter.list_branches(repo_path)
        branch_names = [b.name for b in branches]
        assert "feature" not in branch_names

    @pytest.mark.asyncio
    async def test_checkout_branch(self, temp_dir, cli_adapter):
        """Test checking out a branch."""
        repo_path = temp_dir / "checkout_repo"
        await cli_adapter.init(repo_path)

        # Create initial commit
        test_file = repo_path / "test.txt"
        test_file.write_text("initial")
        await cli_adapter.add(repo_path, ["test.txt"])
        await cli_adapter.commit(
            repo_path,
            options=MagicMock(
                message="Initial",
                author_name="Test",
                author_email="test@test.com",
                amend=False,
                allow_empty=False,
            ),
        )

        # Create and checkout feature branch
        await cli_adapter.create_branch(repo_path, "feature", force=False)
        await cli_adapter.checkout(
            repo_path,
            options=MagicMock(branch="feature", create_new=False, force=False),
        )

        # Verify we're on feature branch
        current = await cli_adapter.get_current_branch(repo_path)
        assert current == "feature"

    @pytest.mark.asyncio
    async def test_log_commits(self, temp_dir, cli_adapter):
        """Test viewing commit log."""
        repo_path = temp_dir / "log_repo"
        await cli_adapter.init(repo_path)

        # Create a commit
        test_file = repo_path / "test.txt"
        test_file.write_text("content")
        await cli_adapter.add(repo_path, ["test.txt"])
        await cli_adapter.commit(
            repo_path,
            options=MagicMock(
                message="Test commit",
                author_name="Test",
                author_email="test@test.com",
                amend=False,
                allow_empty=False,
            ),
        )

        # Get log
        log = await cli_adapter.log(repo_path)

        assert isinstance(log, list)
        assert len(log) >= 1

    @pytest.mark.asyncio
    async def test_remote_operations(self, temp_dir, cli_adapter):
        """Test remote operations."""
        repo_path = temp_dir / "remote_repo"
        await cli_adapter.init(repo_path)

        # Add remote
        await cli_adapter.add_remote(repo_path, "origin", "https://github.com/example/repo.git")

        # List remotes
        remotes = await cli_adapter.list_remotes(repo_path)

        assert len(remotes) > 0
        assert any(r["name"] == "origin" for r in remotes)

        # Remove remote
        await cli_adapter.remove_remote(repo_path, "origin")

        remotes = await cli_adapter.list_remotes(repo_path)
        assert not any(r["name"] == "origin" for r in remotes)

    @pytest.mark.asyncio
    async def test_tag_operations(self, temp_dir, cli_adapter):
        """Test tag operations."""
        repo_path = temp_dir / "tag_repo"
        await cli_adapter.init(repo_path)

        # Create a commit
        test_file = repo_path / "test.txt"
        test_file.write_text("content")
        await cli_adapter.add(repo_path, ["test.txt"])
        await cli_adapter.commit(
            repo_path,
            options=MagicMock(
                message="Release commit",
                author_name="Test",
                author_email="test@test.com",
                amend=False,
                allow_empty=False,
            ),
        )

        # Create tag using real TagOptions
        await cli_adapter.create_tag(
            repo_path,
            options=TagOptions(
                name="v1.0.0",
                create=True,
                message="Release version 1.0.0",
                force=False,
            ),
        )

        # List tags
        tags = await cli_adapter.list_tags(repo_path)
        assert "v1.0.0" in tags

        # Delete tag
        await cli_adapter.delete_tag(repo_path, "v1.0.0")

        tags = await cli_adapter.list_tags(repo_path)
        assert "v1.0.0" not in tags


class TestCliAdapterErrorHandling:
    """Tests for CLI adapter error handling."""

    @pytest.fixture
    def cli_adapter(self):
        """Create a CLI adapter for testing."""
        config = CliConfig(git_path="git", timeout=10)
        return CliAdapter(config)

    def test_invalid_branch_name(self, cli_adapter):
        """Test validation of invalid branch names."""
        with pytest.raises(Exception):
            cli_adapter._validate_branch_name("")

        with pytest.raises(Exception):
            cli_adapter._validate_branch_name("HEAD")

    def test_sanitize_path(self, cli_adapter):
        """Test path sanitization."""
        # Test normal path
        result = cli_adapter._sanitize_path("normal/path/file.txt")
        assert result == "normal/path/file.txt"

    def test_sanitize_input_command_injection(self, cli_adapter):
        """Test sanitization prevents command injection."""
        from mcp_git.git.cli_adapter import CommandInjectionError

        malicious_input = "test; rm -rf /"

        # Should raise CommandInjectionError for dangerous input
        with pytest.raises(CommandInjectionError):
            cli_adapter._sanitize_input(malicious_input, "test")
