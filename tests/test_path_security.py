"""路径安全测试 - 验证路径遍历攻击防护和文件系统访问安全。

测试内容：
- 路径遍历攻击防护
- 绝对路径拒绝
- 合法路径访问验证
"""

import tempfile
from pathlib import Path

import pytest


class TestPathTraversalPrevention:
    """测试路径遍历攻击防护。"""

    @pytest.fixture
    def workspace_root(self):
        """创建测试用工作区根目录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_double_dot_traversal_attempt(self, workspace_root):
        """测试双点符路径遍历攻击防护。"""
        from mcp_git.utils import sanitize_path

        attack_path = Path("../../../etc/passwd")
        with pytest.raises(ValueError, match="traverse|outside"):
            sanitize_path(attack_path, workspace_root)

    def test_nested_traversal_attempt(self, workspace_root):
        """测试嵌套路径遍历攻击。"""
        from mcp_git.utils import sanitize_path

        attack_path = Path("a/../../../b/../../../c")
        with pytest.raises(ValueError):
            sanitize_path(attack_path, workspace_root)


class TestAbsolutePathAttackPrevention:
    """测试绝对路径攻击防护。"""

    @pytest.fixture
    def workspace_root(self):
        """创建测试用工作区根目录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_absolute_path_rejection(self, workspace_root):
        """测试绝对路径被拒绝。"""
        from mcp_git.utils import sanitize_path

        attack_path = Path("/etc/passwd")
        with pytest.raises(ValueError):
            sanitize_path(attack_path, workspace_root)


class TestValidPathAccess:
    """测试合法路径访问。"""

    @pytest.fixture
    def workspace_root(self):
        """创建测试用工作区根目录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_valid_relative_path(self, workspace_root):
        """测试合法相对路径。"""
        from mcp_git.utils import sanitize_path

        valid_path = Path("project/src/main.py")
        result = sanitize_path(valid_path, workspace_root)
        assert isinstance(result, Path)
        assert str(result).startswith(str(workspace_root))

    def test_nested_path_within_workspace(self, workspace_root):
        """测试工作区内嵌套路径。"""
        from mcp_git.utils import sanitize_path

        subdir = workspace_root / "project" / "src"
        subdir.mkdir(parents=True)

        valid_file = subdir / "main.py"
        valid_file.write_text("# Python code")

        result = sanitize_path(valid_file, workspace_root)
        assert isinstance(result, Path)
        assert result == valid_file.resolve()


class TestPathSecurityEdgeCases:
    """测试路径安全的边界情况。"""

    @pytest.fixture
    def workspace_root(self):
        """创建测试用工作区根目录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_empty_path(self, workspace_root):
        """测试空路径处理。"""
        from mcp_git.utils import sanitize_path

        # 空路径应该被处理，可能返回基础路径
        result = sanitize_path(Path(""), workspace_root)
        # 空路径可能返回基础路径本身
        assert result is not None

    def test_special_characters_in_path(self, workspace_root):
        """测试路径中的特殊字符。"""
        from mcp_git.utils import sanitize_path

        # 包含特殊字符但非攻击性的路径
        special_paths = [
            Path("file-with-dashes.txt"),
            Path("file_with_underscores.txt"),
        ]

        for path in special_paths:
            result = sanitize_path(path, workspace_root)
            assert result is not None


class TestPathSecurityIntegration:
    """测试路径安全的集成场景。"""

    @pytest.fixture
    def workspace_root(self):
        """创建测试用工作区根目录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_workspace_isolation(self, workspace_root):
        """测试工作区隔离。"""
        from mcp_git.utils import sanitize_path

        # 尝试访问其他工作区
        other_workspace = Path("/other/workspace/../../etc")
        with pytest.raises(ValueError):
            sanitize_path(other_workspace, workspace_root)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
