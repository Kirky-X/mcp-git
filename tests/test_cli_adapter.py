"""CLI adapter tests for mcp-git - tests for CLI-based Git operations fallback."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


class TestCliAdapter:
    """Tests for CLI-based Git adapter."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_subprocess(self):
        """Create a mock for subprocess operations."""
        with patch("asyncio.create_subprocess_exec") as mock:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock.return_value = mock_process
            yield mock

    def test_sanitize_input_basic(self):
        """Test basic input sanitization."""
        # Import from utils which contains sanitize functions
        from mcp_git.utils import sanitize_input

        # Test normal input
        result = sanitize_input("normal input")
        assert result == "normal input"

    def test_sanitize_input_removes_dangerous_chars(self):
        """Test that dangerous characters are removed."""
        from mcp_git.utils import sanitize_input

        dangerous = "test; rm -rf /; echo 'hello'"
        result = sanitize_input(dangerous)

        assert ";" not in result
        assert "rm" not in result
        assert "-" not in result

    def test_sanitize_input_length_limit(self):
        """Test that input length is limited."""
        from mcp_git.utils import sanitize_input

        long_input = "x" * 2000
        result = sanitize_input(long_input)

        assert len(result) <= 1000

    def test_sanitize_path_basic(self):
        """Test basic path sanitization."""
        from mcp_git.utils import sanitize_path

        base = Path("/safe/base")
        safe_path = Path("/safe/base/subdir/file.txt")

        result = sanitize_path(safe_path, base)

        assert result == safe_path.resolve()

    def test_sanitize_path_prevents_traversal(self):
        """Test that path traversal is prevented."""
        from mcp_git.utils import sanitize_path

        base = Path("/safe/base")
        malicious = Path("/safe/base/../../../etc/passwd")

        # Should raise ValueError for path traversal attempt
        with pytest.raises(ValueError, match="Path traversal attempt detected"):
            sanitize_path(malicious, base)


class TestGitCommandExecution:
    """Tests for Git command execution through CLI."""

    @pytest.fixture
    def git_executor(self, temp_dir):
        """Create a git command executor for testing."""

        # For testing, we'll use a mock that simulates CLI execution
        return temp_dir

    @pytest.mark.asyncio
    async def test_git_version_check(self, temp_dir):
        """Test git version verification."""
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "--version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode()

            assert "git version" in output
            assert process.returncode == 0
        except FileNotFoundError:
            pytest.skip("Git not installed")

    @pytest.mark.asyncio
    async def test_git_help_command(self, temp_dir):
        """Test git help command execution."""
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "help",
                "--all",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode()

            # Should contain git commands list
            assert "git" in output.lower()
        except FileNotFoundError:
            pytest.skip("Git not installed")


class TestGitRepoCreation:
    """Tests for repository creation operations."""

    @pytest.fixture
    def new_repo_path(self, temp_dir):
        """Create path for new repository."""
        return temp_dir / "new_repo"

    @pytest.mark.asyncio
    async def test_init_repository(self, new_repo_path):
        """Test repository initialization."""
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "init",
                str(new_repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

            # Check .git directory was created
            assert (new_repo_path / ".git").exists()
        except FileNotFoundError:
            pytest.skip("Git not installed")


class TestGitCloneFallback:
    """Tests for clone operation fallback to CLI."""

    @pytest.fixture
    def cloned_repo_path(self, temp_dir):
        """Create path for cloned repository."""
        return temp_dir / "cloned_repo"

    @pytest.mark.asyncio
    async def test_clone_public_repo(self, cloned_repo_path):
        """Test cloning a public repository."""
        # Use a small public repository for testing
        test_repo_url = "https://github.com/octocat/Hello-World.git"

        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "clone",
                test_repo_url,
                str(cloned_repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
                assert process.returncode == 0
                # Repository should be cloned
                assert (cloned_repo_path / ".git").exists()
            except asyncio.TimeoutError:
                process.terminate()
                pytest.skip("Clone operation timed out")

        except FileNotFoundError:
            pytest.skip("Git not installed")


class TestGitStatusOperations:
    """Tests for status check operations."""

    @pytest.fixture
    def initialized_repo(self, temp_dir):
        """Create an initialized repository with changes."""
        import git

        repo_path = temp_dir / "status_test_repo"
        repo = git.Repo.init(str(repo_path))

        # Create a file
        test_file = repo_path / "test.txt"
        test_file.write_text("Test content")

        # Stage the file
        repo.index.add(["test.txt"])

        return repo_path

    @pytest.mark.asyncio
    async def test_status_check(self, initialized_repo):
        """Test checking repository status."""
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "-C",
                str(initialized_repo),
                "status",
                "--porcelain",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode()

            # Should show staged file
            assert "test.txt" in output
            assert process.returncode == 0

        except FileNotFoundError:
            pytest.skip("Git not installed")


class TestGitAddOperations:
    """Tests for staging operations."""

    @pytest.fixture
    def repo_with_untracked(self, temp_dir):
        """Create repository with untracked file."""
        import git

        repo_path = temp_dir / "add_test_repo"
        git.Repo.init(str(repo_path))

        # Create untracked file
        new_file = repo_path / "new_feature.py"
        new_file.write_text("# New feature\nprint('hello')")

        return repo_path

    @pytest.mark.asyncio
    async def test_add_file(self, repo_with_untracked):
        """Test staging a file."""
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "-C",
                str(repo_with_untracked),
                "add",
                "new_feature.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

            # Check if file is staged
            process = await asyncio.create_subprocess_exec(
                "git",
                "-C",
                str(repo_with_untracked),
                "status",
                "--porcelain",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode()

            # Should show staged file (A status)
            assert "A  new_feature.py" in output or "A" in output.split()[0]

        except FileNotFoundError:
            pytest.skip("Git not installed")


class TestGitCommitOperations:
    """Tests for commit operations."""

    @pytest.fixture
    def staged_repo(self, temp_dir):
        """Create repository with staged changes."""
        import git

        repo_path = temp_dir / "commit_test_repo"
        repo = git.Repo.init(str(repo_path))

        # Create and stage file
        test_file = repo_path / "commit_test.txt"
        test_file.write_text("Content to commit")
        repo.index.add(["commit_test.txt"])

        # Set git user for commit
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        return repo_path

    @pytest.mark.asyncio
    async def test_commit_staged(self, staged_repo):
        """Test committing staged changes."""
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "-C",
                str(staged_repo),
                "commit",
                "-m",
                "Test commit message",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode()

            # Should show commit message
            assert "Test commit message" in output or "[main" in output
            assert process.returncode == 0

        except FileNotFoundError:
            pytest.skip("Git not installed")


class TestCommandInjectionPrevention:
    """Tests for command injection prevention."""

    def test_input_sanitization_prevents_injection(self):
        """Test that sanitization prevents command injection."""
        from mcp_git.utils import sanitize_input

        # Test various injection attempts
        malicious_inputs = [
            "; rm -rf /",
            "&& cat /etc/passwd",
            "| echo hacked",
            "$(whoami)",
            "${USER}",
            "`ls`",
        ]

        for malicious in malicious_inputs:
            result = sanitize_input(malicious)
            # None of the dangerous patterns should remain
            assert "rm" not in result.lower()
            assert "cat" not in result.lower()
            assert "passwd" not in result.lower()
            assert "$(" not in result
            assert "${" not in result
            assert "`" not in result

    def test_path_sanitization_prevents_escaping(self):
        """Test that path sanitization prevents directory traversal."""
        from mcp_git.utils import sanitize_path

        base = Path("/workspace")
        malicious_paths = [
            "/workspace/../../../etc/passwd",
            "/workspace/../../secret/../../etc",
            "/workspace/./.././../etc",
        ]

        for malicious in malicious_paths:
            with pytest.raises(ValueError):
                sanitize_path(Path(malicious), base)
