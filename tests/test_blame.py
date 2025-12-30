"""Unit tests for git blame functionality."""

from pathlib import Path

import pytest


class TestBlameOptions:
    """Tests for BlameOptions dataclass."""

    def test_blame_options_creation(self):
        """Test creating BlameOptions."""
        from mcp_git.git.adapter import BlameOptions

        options = BlameOptions(
            path=Path("/test/file.py"),
            start_line=1,
            end_line=10,
        )

        assert options.path == Path("/test/file.py")
        assert options.start_line == 1
        assert options.end_line == 10

    def test_blame_options_defaults(self):
        """Test BlameOptions default values."""
        from mcp_git.git.adapter import BlameOptions

        options = BlameOptions(path=Path("/test/file.py"))

        assert options.start_line is None
        assert options.end_line is None


class TestBlameAdapter:
    """Tests for blame functionality in GitPythonAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create a GitPythonAdapter instance."""
        from mcp_git.git.adapter_gitpython import GitPythonAdapter

        return GitPythonAdapter()

    @pytest.fixture
    def mock_repo(self, temp_dir):
        """Create a mock git repository."""
        import git

        repo_path = temp_dir / "test_repo"
        repo = git.Repo.init(str(repo_path))

        # Create a file with multiple lines
        test_file = repo_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

        # Add and commit
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")

        return repo_path, repo

    @pytest.mark.asyncio
    async def test_blame_returns_lines(self, adapter, mock_repo):
        """Test that blame returns blame lines."""
        repo_path, _ = mock_repo
        test_file = repo_path / "test.txt"

        # Call blame method
        result = await adapter.blame(test_file)

        # Verify result structure
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_blame_with_line_range(self, adapter, mock_repo):
        """Test blame with specific line range."""
        repo_path, _ = mock_repo
        test_file = repo_path / "test.txt"

        from mcp_git.git.adapter import BlameOptions

        options = BlameOptions(
            path=test_file,
            start_line=1,
            end_line=3,
        )

        result = await adapter.blame(test_file, options=options)

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_blame_nonexistent_file(self, adapter, temp_dir):
        """Test blame on non-existent file."""
        nonexistent = temp_dir / "nonexistent.txt"

        # Should raise an error or return empty list
        with pytest.raises(Exception):
            await adapter.blame(nonexistent)

    @pytest.mark.asyncio
    async def test_blame_not_a_git_repo(self, adapter, temp_dir):
        """Test blame on directory that's not a git repository."""
        # Create a regular file
        test_file = temp_dir / "regular.txt"
        test_file.write_text("Some content\n")

        # Should raise an error
        with pytest.raises(Exception):
            await adapter.blame(test_file)


class TestBlameData:
    """Tests for blame data structures."""

    def test_blame_line_structure(self):
        """Test BlameLine data structure."""
        from mcp_git.storage.models import BlameLine

        blame_line = BlameLine(
            line_number=1,
            commit_hash="abc123def456",
            author="Test User",
            author_email="test@example.com",
            date="2024-01-01",
            content="Sample line content",
        )

        assert blame_line.line_number == 1
        assert blame_line.commit_hash == "abc123def456"
        assert blame_line.author == "Test User"

    def test_blame_line_optional_fields(self):
        """Test BlameLine with optional fields."""
        from mcp_git.storage.models import BlameLine

        # Create with minimal fields
        blame_line = BlameLine(
            line_number=1,
            commit_hash="abc123",
            author="Test",
            author_email="test@test.com",
            date="2024-01-01",
            content="Content",
        )

        # All required fields should be set
        assert blame_line.line_number is not None
        assert blame_line.commit_hash is not None
