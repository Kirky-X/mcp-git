"""Data model tests for mcp-git."""

from datetime import UTC, datetime
from uuid import uuid4


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_task_status_values(self):
        """Test TaskStatus enum values."""
        from mcp_git.storage.models import TaskStatus

        assert TaskStatus.QUEUED.value == "queued"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_from_value(self):
        """Test TaskStatus from value."""
        from mcp_git.storage.models import TaskStatus

        status = TaskStatus("running")
        assert status == TaskStatus.RUNNING


class TestGitOperation:
    """Tests for GitOperation enum."""

    def test_git_operation_values(self):
        """Test GitOperation enum values."""
        from mcp_git.storage.models import GitOperation

        assert GitOperation.CLONE.value == "clone"
        assert GitOperation.COMMIT.value == "commit"
        assert GitOperation.PUSH.value == "push"
        assert GitOperation.PULL.value == "pull"
        assert GitOperation.BRANCH.value == "branch"
        assert GitOperation.MERGE.value == "merge"

    def test_git_operation_from_value(self):
        """Test GitOperation from value."""
        from mcp_git.storage.models import GitOperation

        op = GitOperation("push")
        assert op == GitOperation.PUSH


class TestTask:
    """Tests for Task model."""

    def test_task_creation(self):
        """Test Task model creation."""
        from mcp_git.storage.models import GitOperation, Task, TaskStatus

        task = Task(
            id=uuid4(),
            operation=GitOperation.CLONE,
            status=TaskStatus.QUEUED,
            params={"url": "https://example.com/repo.git"},
        )

        assert task.operation == GitOperation.CLONE
        assert task.status == TaskStatus.QUEUED
        assert task.params["url"] == "https://example.com/repo.git"
        assert task.progress == 0
        assert task.result is None

    def test_task_defaults(self):
        """Test Task model defaults."""
        from mcp_git.storage.models import GitOperation, Task, TaskStatus

        task = Task(
            id=uuid4(),
            operation=GitOperation.COMMIT,
            status=TaskStatus.QUEUED,
            params={},
        )

        assert task.progress == 0
        assert task.error_message is None
        assert task.workspace_path is None
        assert task.created_at is not None  # Auto-set to current time
        assert task.started_at is None
        assert task.completed_at is None


class TestWorkspace:
    """Tests for Workspace model."""

    def test_workspace_creation(self):
        """Test Workspace model creation."""
        from pathlib import Path

        from mcp_git.storage.models import Workspace

        workspace = Workspace(
            id=uuid4(),
            path=Path("/tmp/mcp-git/workspaces/test"),
            size_bytes=1024,
        )

        assert workspace.size_bytes == 1024
        assert workspace.last_accessed_at is not None  # Auto-set to current time
        assert workspace.created_at is not None  # Auto-set to current time
        assert workspace.metadata == {}

    def test_workspace_defaults(self):
        """Test Workspace model defaults."""
        from pathlib import Path

        from mcp_git.storage.models import Workspace

        workspace = Workspace(
            id=uuid4(),
            path=Path("/tmp/test"),
        )

        assert workspace.size_bytes == 0
        assert workspace.metadata == {}


class TestTaskResult:
    """Tests for TaskResult model."""

    def test_task_result_creation(self):
        """Test TaskResult model creation."""
        from mcp_git.storage.models import TaskResult, TaskStatus

        result = TaskResult(
            task_id=uuid4(),
            status=TaskStatus.COMPLETED,
            result={"oid": "abc123"},
        )

        assert result.status == TaskStatus.COMPLETED
        assert result.result["oid"] == "abc123"
        assert result.error_message is None


class TestCommitInfo:
    """Tests for CommitInfo model."""

    def test_commit_info_creation(self):
        """Test CommitInfo model creation."""
        from mcp_git.storage.models import CommitInfo

        commit = CommitInfo(
            oid="abc123def456",
            message="Test commit",
            author_name="Test User",
            author_email="test@example.com",
            commit_time=datetime.now(UTC),
            parent_oids=["parent123"],
        )

        assert commit.oid == "abc123def456"
        assert commit.message == "Test commit"
        assert len(commit.parent_oids) == 1

    def test_commit_info_defaults(self):
        """Test CommitInfo model defaults."""
        from mcp_git.storage.models import CommitInfo

        commit = CommitInfo(
            oid="abc123",
            message="Test",
            author_name="Author",
            author_email="email@test.com",
            commit_time=datetime.now(UTC),
        )

        assert commit.parent_oids == []


class TestBranchInfo:
    """Tests for BranchInfo model."""

    def test_branch_info_creation(self):
        """Test BranchInfo model creation."""
        from mcp_git.storage.models import BranchInfo

        branch = BranchInfo(
            name="main",
            oid="abc123",
            is_local=True,
            is_remote=False,
        )

        assert branch.name == "main"
        assert branch.is_local is True
        assert branch.is_remote is False


class TestFileStatus:
    """Tests for FileStatus model."""

    def test_file_status_creation(self):
        """Test FileStatus model creation."""
        from mcp_git.storage.models import FileStatus

        status = FileStatus(
            path="src/main.py",
            status="modified",
        )

        assert status.path == "src/main.py"
        assert status.status == "modified"

    def test_file_status_values(self):
        """Test FileStatus status values."""
        from mcp_git.storage.models import FileStatus

        for status_str in ["modified", "added", "deleted", "staged", "untracked"]:
            status = FileStatus(path="test", status=status_str)
            assert status.status == status_str


class TestDiffInfo:
    """Tests for DiffInfo model."""

    def test_diff_info_creation(self):
        """Test DiffInfo model creation."""
        from mcp_git.storage.models import DiffInfo

        diff = DiffInfo(
            old_path="src/old.py",
            new_path="src/new.py",
            change_type="modified",
            diff_lines=["@@ -1,3 +1,3 @@", "-old line", "+new line"],
        )

        assert diff.old_path == "src/old.py"
        assert diff.new_path == "src/new.py"
        assert diff.change_type == "modified"
        assert len(diff.diff_lines) == 3


class TestBlameLine:
    """Tests for BlameLine model."""

    def test_blame_line_creation(self):
        """Test BlameLine model creation."""
        from mcp_git.storage.models import BlameLine

        blame = BlameLine(
            line_number=1,
            commit_oid="abc123",
            author="Test Author",
            date=datetime.now(UTC),
            summary="Fix bug",
        )

        assert blame.line_number == 1
        assert blame.commit_oid == "abc123"
        assert blame.author == "Test Author"


class TestCleanupStrategy:
    """Tests for CleanupStrategy enum."""

    def test_cleanup_strategy_values(self):
        """Test CleanupStrategy enum values."""
        from mcp_git.storage.models import CleanupStrategy

        assert CleanupStrategy.LRU.value == "lru"
        assert CleanupStrategy.FIFO.value == "fifo"

    def test_cleanup_strategy_from_value(self):
        """Test CleanupStrategy from value."""
        from mcp_git.storage.models import CleanupStrategy

        strategy = CleanupStrategy("lru")
        assert strategy == CleanupStrategy.LRU
