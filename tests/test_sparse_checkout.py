"""
Git sparse checkout tests for mcp-git.

This module tests Git sparse checkout operations including setting,
updating, and disabling sparse checkout paths.
"""

import tempfile
from pathlib import Path

import pytest


class TestSparseCheckoutIntegration:
    """Integration tests for Git sparse checkout operations."""

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
    def repo_with_structure(self, temp_dir):
        """Create a repository with directory structure for sparse checkout tests."""
        import git

        repo_path = temp_dir / "sparse_repo"
        repo = git.Repo.init(str(repo_path))

        # Create directory structure
        (repo_path / "src" / "component_a").mkdir(parents=True)
        (repo_path / "src" / "component_b").mkdir(parents=True)
        (repo_path / "lib" / "utils").mkdir(parents=True)
        (repo_path / "docs").mkdir(parents=True)

        # Create files
        (repo_path / "src" / "component_a" / "main.py").write_text("# Component A")
        (repo_path / "src" / "component_b" / "main.py").write_text("# Component B")
        (repo_path / "lib" / "utils" / "helper.py").write_text("# Helper")
        (repo_path / "README.md").write_text("# Root README")
        (repo_path / "docs" / "index.md").write_text("# Docs")

        # Add and commit
        repo.index.add(
            [
                "src/component_a/main.py",
                "src/component_b/main.py",
                "lib/utils/helper.py",
                "README.md",
                "docs/index.md",
            ]
        )
        repo.index.commit("Initial structure")

        return repo_path

    @pytest.mark.asyncio
    async def test_sparse_checkout_replace_mode(self, repo_with_structure, adapter):
        """Test sparse checkout with replace mode."""
        from mcp_git.git.adapter import SparseCheckoutOptions

        repo_path = repo_with_structure

        # Set sparse checkout to only include src/component_a
        options = SparseCheckoutOptions(paths=["src/component_a"], mode="replace")
        result = await adapter.sparse_checkout(repo_path, options)

        assert result == ["src/component_a"]

        # Verify sparse-checkout file
        sparse_file = repo_path / ".git" / "info" / "sparse-checkout"
        assert sparse_file.exists()
        content = sparse_file.read_text()
        assert "src/component_a" in content

    @pytest.mark.asyncio
    async def test_sparse_checkout_add_mode(self, repo_with_structure, adapter):
        """Test sparse checkout with add mode."""
        from mcp_git.git.adapter import SparseCheckoutOptions

        repo_path = repo_with_structure

        # First set sparse checkout to include src/component_a
        options = SparseCheckoutOptions(paths=["src/component_a"], mode="replace")
        await adapter.sparse_checkout(repo_path, options)

        # Then add src/component_b
        options = SparseCheckoutOptions(paths=["src/component_b"], mode="add")
        result = await adapter.sparse_checkout(repo_path, options)

        assert "src/component_a" in result
        assert "src/component_b" in result
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_sparse_checkout_remove_mode(self, repo_with_structure, adapter):
        """Test sparse checkout with remove mode."""
        from mcp_git.git.adapter import SparseCheckoutOptions

        repo_path = repo_with_structure

        # First set sparse checkout to include multiple paths
        options = SparseCheckoutOptions(
            paths=["src/component_a", "src/component_b"],
            mode="replace",
        )
        await adapter.sparse_checkout(repo_path, options)

        # Then remove src/component_b
        options = SparseCheckoutOptions(paths=["src/component_b"], mode="remove")
        result = await adapter.sparse_checkout(repo_path, options)

        assert "src/component_a" in result
        assert "src/component_b" not in result
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_sparse_checkout_disable(self, repo_with_structure, adapter):
        """Test disabling sparse checkout by setting empty paths."""
        from mcp_git.git.adapter import SparseCheckoutOptions

        repo_path = repo_with_structure

        # First set sparse checkout
        options = SparseCheckoutOptions(paths=["src/component_a"], mode="replace")
        await adapter.sparse_checkout(repo_path, options)

        # Then disable by setting empty paths
        options = SparseCheckoutOptions(paths=[], mode="replace")
        result = await adapter.sparse_checkout(repo_path, options)

        assert result == []

    @pytest.mark.asyncio
    async def test_sparse_checkout_preserves_existing_paths(self, repo_with_structure, adapter):
        """Test that add mode preserves existing paths."""
        from mcp_git.git.adapter import SparseCheckoutOptions

        repo_path = repo_with_structure

        # Add first path
        options = SparseCheckoutOptions(paths=["lib/utils"], mode="add")
        result1 = await adapter.sparse_checkout(repo_path, options)
        assert result1 == ["lib/utils"]

        # Add second path
        options = SparseCheckoutOptions(paths=["docs"], mode="add")
        result2 = await adapter.sparse_checkout(repo_path, options)

        assert "lib/utils" in result2
        assert "docs" in result2
        assert len(result2) == 2

    @pytest.mark.asyncio
    async def test_sparse_checkout_no_duplicate_paths(self, repo_with_structure, adapter):
        """Test that adding same path twice doesn't create duplicates."""
        from mcp_git.git.adapter import SparseCheckoutOptions

        repo_path = repo_with_structure

        # Add a path
        options = SparseCheckoutOptions(paths=["src/component_a"], mode="add")
        await adapter.sparse_checkout(repo_path, options)

        # Add same path again
        options = SparseCheckoutOptions(paths=["src/component_a"], mode="add")
        result2 = await adapter.sparse_checkout(repo_path, options)

        # Should still be only one entry
        assert result2.count("src/component_a") == 1


class TestSparseCheckoutOptions:
    """Unit tests for SparseCheckoutOptions dataclass."""

    def test_default_mode_is_replace(self):
        """Test that default mode is 'replace'."""
        from mcp_git.git.adapter import SparseCheckoutOptions

        options = SparseCheckoutOptions(paths=["src"])
        assert options.mode == "replace"

    def test_custom_mode(self):
        """Test custom mode values."""
        from mcp_git.git.adapter import SparseCheckoutOptions

        options_add = SparseCheckoutOptions(paths=["src"], mode="add")
        assert options_add.mode == "add"

        options_remove = SparseCheckoutOptions(paths=["src"], mode="remove")
        assert options_remove.mode == "remove"

    def test_paths_list(self):
        """Test paths as list of strings."""
        from mcp_git.git.adapter import SparseCheckoutOptions

        options = SparseCheckoutOptions(
            paths=["src/component_a", "lib/utils", "README.md"],
            mode="replace",
        )
        assert len(options.paths) == 3
