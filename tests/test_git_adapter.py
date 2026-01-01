"""Git adapter tests for mcp-git."""

from pathlib import Path

import pytest


class TestGitAdapterInterface:
    """Tests for GitAdapter interface."""

    def test_adapter_is_abc(self):
        """Test that GitAdapter is an abstract base class."""
        from mcp_git.git.adapter import GitAdapter

        # Can't instantiate directly
        with pytest.raises(TypeError):
            GitAdapter()

    def test_clone_options_defaults(self):
        """Test CloneOptions default values."""
        from mcp_git.git.adapter import CloneOptions

        options = CloneOptions()

        assert options.depth is None
        assert options.single_branch is False
        assert options.branch is None
        assert options.bare is False
        assert options.mirror is False

    def test_commit_options_defaults(self):
        """Test CommitOptions default values."""
        from mcp_git.git.adapter import CommitOptions

        options = CommitOptions(message="Test commit")

        assert options.message == "Test commit"
        assert options.author_name is None
        assert options.author_email is None
        assert options.amend is False
        assert options.allow_empty is False

    def test_push_options_defaults(self):
        """Test PushOptions default values."""
        from mcp_git.git.adapter import PushOptions

        options = PushOptions()

        assert options.remote == "origin"
        assert options.branch is None
        assert options.force is False
        assert options.force_with_lease is False

    def test_pull_options_defaults(self):
        """Test PullOptions default values."""
        from mcp_git.git.adapter import PullOptions

        options = PullOptions()

        assert options.remote == "origin"
        assert options.branch is None
        assert options.rebase is False

    def test_merge_options_defaults(self):
        """Test MergeOptions default values."""
        from mcp_git.git.adapter import MergeOptions

        options = MergeOptions(source_branch="feature")

        assert options.source_branch == "feature"
        assert options.fast_forward is True
        assert options.commit is True

    def test_diff_options_defaults(self):
        """Test DiffOptions default values."""
        from mcp_git.git.adapter import DiffOptions

        options = DiffOptions()

        assert options.cached is False
        assert options.unstaged is False
        assert options.commit_oid is None
        assert options.path is None
        assert options.unified == 3

    def test_log_options_defaults(self):
        """Test LogOptions default values."""
        from mcp_git.git.adapter import LogOptions

        options = LogOptions()

        assert options.max_count is None
        assert options.skip == 0
        assert options.author is None
        assert options.since is None
        assert options.until is None
        assert options.path is None
        assert options.all is False

    def test_checkout_options_defaults(self):
        """Test CheckoutOptions default values."""
        from mcp_git.git.adapter import CheckoutOptions

        options = CheckoutOptions(branch="main")

        assert options.branch == "main"
        assert options.create_new is False
        assert options.force is False

    def test_rebase_options_defaults(self):
        """Test RebaseOptions default values."""
        from mcp_git.git.adapter import RebaseOptions

        options = RebaseOptions()

        assert options.branch is None
        assert options.interactive is False
        assert options.abort is False
        assert options.continue_rebase is False

    def test_stash_options_defaults(self):
        """Test StashOptions default values."""
        from mcp_git.git.adapter import StashOptions

        options = StashOptions()

        assert options.save is False
        assert options.pop is False
        assert options.apply is False
        assert options.drop is False
        assert options.list is False
        assert options.message is None
        assert options.include_untracked is False
        assert options.stash_index is None

    def test_tag_options_defaults(self):
        """Test TagOptions default values."""
        from mcp_git.git.adapter import TagOptions

        options = TagOptions(name="v1.0.0")

        assert options.name == "v1.0.0"
        assert options.create is False
        assert options.delete is False
        assert options.message is None
        assert options.force is False

    def test_merge_result_enum(self):
        """Test MergeResult enum values."""
        from mcp_git.git.adapter import MergeResult

        assert MergeResult.ALREADY_UP_TO_DATE.value == "already_up_to_date"
        assert MergeResult.FAST_FORWARD.value == "fast_forward"
        assert MergeResult.MERGED.value == "merged"
        assert MergeResult.CONFLICTED.value == "conflicted"
        assert MergeResult.FAILED.value == "failed"


class TestGitPythonAdapter:
    """Tests for GitPythonAdapter implementation."""

    @pytest.mark.asyncio
    async def test_adapter_initialization(self):
        """Test adapter initialization."""
        from mcp_git.git.adapter_gitpython import GitPythonAdapter

        adapter = GitPythonAdapter()

        assert adapter._credential_manager is None

    @pytest.mark.asyncio
    async def test_set_credential_manager(self):
        """Test setting credential manager."""
        from mcp_git.git.adapter_gitpython import GitPythonAdapter
        from mcp_git.service.credential_manager import CredentialManager

        adapter = GitPythonAdapter()
        cred_manager = CredentialManager()

        adapter.set_credential_manager(cred_manager)

        assert adapter._credential_manager is cred_manager

    @pytest.mark.asyncio
    async def test_is_repository_valid(self, temp_dir: Path):
        """Test is_repository with valid repo."""
        # Create a git repo
        import git

        from mcp_git.git.adapter_gitpython import GitPythonAdapter

        repo_path = temp_dir / "test_repo"
        git.Repo.init(str(repo_path))

        adapter = GitPythonAdapter()
        is_valid = await adapter.is_repository(repo_path)

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_is_repository_invalid(self, temp_dir: Path):
        """Test is_repository with invalid path."""
        from mcp_git.git.adapter_gitpython import GitPythonAdapter

        adapter = GitPythonAdapter()
        is_valid = await adapter.is_repository(temp_dir)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_init_repository(self, temp_dir: Path):
        """Test initializing a repository."""
        from mcp_git.git.adapter_gitpython import GitPythonAdapter

        repo_path = temp_dir / "new_repo"
        adapter = GitPythonAdapter()

        await adapter.init(repo_path)

        assert (repo_path / ".git").exists()

    @pytest.mark.asyncio
    async def test_init_bare_repository(self, temp_dir: Path):
        """Test initializing a bare repository."""
        from mcp_git.git.adapter_gitpython import GitPythonAdapter

        repo_path = temp_dir / "bare_repo.git"
        adapter = GitPythonAdapter()

        await adapter.init(repo_path, bare=True)

        # Bare repos have no working tree
        assert (repo_path / "HEAD").exists()

    @pytest.mark.asyncio
    async def test_get_current_branch(self, temp_dir: Path):
        """Test getting current branch name."""
        import git

        from mcp_git.git.adapter_gitpython import GitPythonAdapter

        # Create and configure repo
        repo_path = temp_dir / "test_repo"
        repo = git.Repo.init(str(repo_path))

        # Create a file and commit
        test_file = repo_path / "test.txt"
        test_file.write_text("test content")
        repo.index.add(["test.txt"])
        commit = repo.index.commit("Initial commit")

        # Create and checkout develop branch
        repo.create_head("develop")
        repo.heads.develop.checkout()

        adapter = GitPythonAdapter()
        branch = await adapter.get_current_branch(repo_path)

        assert branch == "develop"

    @pytest.mark.asyncio
    async def test_get_current_branch_detached_head(self, temp_dir: Path):
        """Test getting branch when in detached HEAD state."""
        import git

        from mcp_git.git.adapter_gitpython import GitPythonAdapter

        # Create and configure repo with a commit
        repo_path = temp_dir / "test_repo"
        repo = git.Repo.init(str(repo_path))

        # Create a file and commit
        test_file = repo_path / "test.txt"
        test_file.write_text("test content")
        repo.index.add(["test.txt"])
        commit = repo.index.commit("Initial commit")

        # Detach HEAD by checking out the commit directly
        repo.head.reference = commit

        adapter = GitPythonAdapter()
        branch = await adapter.get_current_branch(repo_path)

        assert branch is None

    @pytest.mark.asyncio
    async def test_get_head_commit(self, temp_dir: Path):
        """Test getting HEAD commit info."""
        import git

        from mcp_git.git.adapter_gitpython import GitPythonAdapter

        # Create and configure repo with a commit
        repo_path = temp_dir / "test_repo"
        repo = git.Repo.init(str(repo_path))

        # Create a file and commit
        test_file = repo_path / "test.txt"
        test_file.write_text("Hello")
        repo.index.add(["test.txt"])
        commit = repo.index.commit("Initial commit")

        adapter = GitPythonAdapter()
        head_commit = await adapter.get_head_commit(repo_path)

        assert head_commit is not None
        assert head_commit.oid == commit.hexsha
        assert "Initial commit" in head_commit.message

    @pytest.mark.asyncio
    async def test_count_commits(self, temp_dir: Path):
        """Test counting commits."""
        import git

        from mcp_git.git.adapter_gitpython import GitPythonAdapter

        # Create and configure repo with commits
        repo_path = temp_dir / "test_repo"
        repo = git.Repo.init(str(repo_path))

        for i in range(3):
            test_file = repo_path / f"file_{i}.txt"
            test_file.write_text(f"Content {i}")
            repo.index.add([f"file_{i}.txt"])
            repo.index.commit(f"Commit {i}")

        adapter = GitPythonAdapter()
        count = await adapter.count_commits(repo_path)

        assert count == 3

    @pytest.mark.asyncio
    async def test_is_merged(self, temp_dir: Path):
        """Test checking if branch is merged."""
        import subprocess

        import git

        from mcp_git.git.adapter_gitpython import GitPythonAdapter

        # Create and configure repo with initial commit
        repo_path = temp_dir / "test_repo"
        repo = git.Repo.init(str(repo_path))

        # Create initial commit on main (or master)
        main_file = repo_path / "main.txt"
        main_file.write_text("main content")
        repo.index.add(["main.txt"])
        initial_commit = repo.index.commit("Initial commit")

        # Get the actual default branch name
        default_branch = "master" if "master" in repo.heads else "main"

        # Create feature branch and make another commit
        repo.create_head("feature")
        repo.heads.feature.checkout()
        test_file = repo_path / "feature.txt"
        test_file.write_text("Feature")
        repo.index.add(["feature.txt"])
        feature_commit = repo.index.commit("Feature commit")

        # Switch back to default branch
        repo.heads[default_branch].checkout()

        adapter = GitPythonAdapter()

        # Feature is not yet merged
        is_merged = await adapter.is_merged(repo_path, "feature", default_branch)
        assert is_merged is False

        # Merge feature into default_branch using git command
        subprocess.run(
            ["git", "-C", str(repo_path), "merge", "--no-ff", "-m", "Merge feature", "feature"],
            check=True,
        )

        is_merged = await adapter.is_merged(repo_path, "feature", default_branch)
        assert is_merged is True


class TestGitAdapterDataClasses:
    """Tests for GitAdapter data classes."""

    def test_blame_options_creation(self):
        """Test BlameOptions creation."""
        from mcp_git.git.adapter import BlameOptions

        options = BlameOptions(
            path=Path("/test/file.py"),
            start_line=1,
            end_line=10,
        )

        assert options.path == Path("/test/file.py")
        assert options.start_line == 1
        assert options.end_line == 10

    def test_branch_options_creation(self):
        """Test BranchOptions creation."""
        from mcp_git.git.adapter import BranchOptions

        options = BranchOptions(
            name="feature",
            create=True,
        )

        assert options.name == "feature"
        assert options.create is True

    def test_transfer_progress_callback(self):
        """Test TransferProgressCallback protocol."""

        # Function that matches the protocol
        def progress_callback(progress: int, total: int, bytes_transferred: int) -> None:
            pass

        # Should be callable as TransferProgressCallback
        assert callable(progress_callback)
