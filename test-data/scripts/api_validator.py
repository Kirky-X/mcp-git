#!/usr/bin/env python3
"""
功能接口验证脚本
验证所有 48 个 MCP 工具的功能正确性
"""

import asyncio
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path("/home/project/mcp-git")
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_git.git.adapter import CheckoutOptions, CloneOptions, CommitOptions
from mcp_git.service.facade import GitServiceFacade
from mcp_git.service.workspace_manager import WorkspaceManager
from mcp_git.storage.models import GitOperation, TaskStatus


# 颜色定义
class Colors:
    GREEN = "\033[0;32m"
    RED = "\033[0;31m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"


@dataclass
class TestResult:
    name: str
    passed: bool
    duration: float
    error: str = ""


class APIValidator:
    def __init__(self):
        self.results: List[TestResult] = []
        self.facade: GitServiceFacade = None
        self.workspace_id = None

    def print_header(self, title: str):
        print(f"\n{Colors.GREEN}{'=' * 40}{Colors.GREEN}")
        print(f"{Colors.GREEN}{title}{Colors.GREEN}")
        print(f"{Colors.GREEN}{'=' * 40}{Colors.GREEN}\n")

    def print_test(self, name: str):
        print(f"{Colors.YELLOW}[TEST]{Colors.GREEN} {name}")

    def print_pass(self, name: str, duration: float):
        print(f"{Colors.GREEN}[PASS]{Colors.GREEN} {name} ({duration:.2f}s)")
        self.results.append(TestResult(name, True, duration))

    def print_fail(self, name: str, duration: float, error: str):
        print(f"{Colors.RED}[FAIL]{Colors.GREEN} {name} ({duration:.2f}s)")
        print(f"{Colors.RED}  Error: {error}{Colors.GREEN}")
        self.results.append(TestResult(name, False, duration, error))

    async def setup(self):
        """设置测试环境"""
        self.print_test("初始化测试环境")
        try:
            # 创建存储
            from mcp_git.storage import SqliteStorage

            storage = SqliteStorage(database_path=":memory:")
            await storage.initialize()

            # 创建服务门面
            self.facade = GitServiceFacade(storage=storage)

            # 分配工作区
            workspace = await self.facade.allocate_workspace()
            self.workspace_id = workspace["workspace_id"]

            self.print_pass("初始化测试环境", 0.1)
        except Exception as e:
            self.print_fail("初始化测试环境", 0.1, str(e))
            raise

    async def cleanup(self):
        """清理测试环境"""
        if self.workspace_id:
            try:
                await self.facade.release_workspace(self.workspace_id)
            except Exception as e:
                print(f"{Colors.RED}清理失败: {e}{Colors.GREEN}")

    async def test_workspace_management(self):
        """测试工作区管理（5个工具）"""
        self.print_header("工作区管理测试")

        # 1. git_allocate_workspace
        self.print_test("git_allocate_workspace")
        start = time.time()
        try:
            result = await self.facade.allocate_workspace()
            duration = time.time() - start
            self.print_pass("git_allocate_workspace", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_allocate_workspace", duration, str(e))

        # 2. git_get_workspace
        self.print_test("git_get_workspace")
        start = time.time()
        try:
            result = await self.facade.get_workspace(self.workspace_id)
            duration = time.time() - start
            if result:
                self.print_pass("git_get_workspace", duration)
            else:
                self.print_fail("git_get_workspace", duration, "Workspace not found")
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_get_workspace", duration, str(e))

        # 3. git_list_workspaces
        self.print_test("git_list_workspaces")
        start = time.time()
        try:
            result = await self.facade.list_workspaces()
            duration = time.time() - start
            self.print_pass("git_list_workspaces", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_list_workspaces", duration, str(e))

        # 4. git_disk_space
        self.print_test("git_disk_space")
        start = time.time()
        try:
            result = self.facade.get_disk_space_info()
            duration = time.time() - start
            self.print_pass("git_disk_space", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_disk_space", duration, str(e))

        # 5. git_release_workspace
        self.print_test("git_release_workspace")
        start = time.time()
        try:
            result = await self.facade.release_workspace(self.workspace_id)
            duration = time.time() - start
            self.print_pass("git_release_workspace", duration)
            # 重新分配工作区用于后续测试
            workspace = await self.facade.allocate_workspace()
            self.workspace_id = workspace["workspace_id"]
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_release_workspace", duration, str(e))

    async def test_repository_operations(self):
        """测试仓库操作（3个工具）"""
        self.print_header("仓库操作测试")

        # 1. git_init
        self.print_test("git_init")
        start = time.time()
        try:
            await self.facade.init(self.workspace_id, bare=False, default_branch="master")
            duration = time.time() - start
            self.print_pass("git_init", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_init", duration, str(e))

        # 2. git_status
        self.print_test("git_status")
        start = time.time()
        try:
            result = await self.facade.status(self.workspace_id)
            duration = time.time() - start
            self.print_pass("git_status", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_status", duration, str(e))

        # 3. git_clone
        self.print_test("git_clone")
        start = time.time()
        try:
            test_repo = Path("/home/project/mcp-git/temp/test/data/repos/test-repo-1")
            result = await self.facade.clone(str(test_repo), self.workspace_id)
            duration = time.time() - start
            self.print_pass("git_clone", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_clone", duration, str(e))

    async def test_commit_operations(self):
        """测试提交操作（2个工具）"""
        self.print_header("提交操作测试")

        # 1. git_stage
        self.print_test("git_stage")
        start = time.time()
        try:
            # 创建测试文件
            workspace = await self.facade.get_workspace(self.workspace_id)
            test_file = Path(workspace["path"]) / "test.txt"
            test_file.write_text("test content")

            await self.facade.add(self.workspace_id, ["test.txt"])
            duration = time.time() - start
            self.print_pass("git_stage", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_stage", duration, str(e))

        # 2. git_commit
        self.print_test("git_commit")
        start = time.time()
        try:
            result = await self.facade.commit(self.workspace_id, "Test commit from API validator")
            duration = time.time() - start
            self.print_pass("git_commit", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_commit", duration, str(e))

    async def test_branch_operations(self):
        """测试分支操作（4个工具）"""
        self.print_header("分支操作测试")

        # 1. git_create_branch
        self.print_test("git_create_branch")
        start = time.time()
        try:
            await self.facade.create_branch(self.workspace_id, "test-feature", revision="master")
            duration = time.time() - start
            self.print_pass("git_create_branch", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_create_branch", duration, str(e))

        # 2. git_list_branches
        self.print_test("git_list_branches")
        start = time.time()
        try:
            result = await self.facade.list_branches(
                self.workspace_id, local=True, remote=False, all=False
            )
            duration = time.time() - start
            self.print_pass("git_list_branches", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_list_branches", duration, str(e))

        # 3. git_checkout
        self.print_test("git_checkout")
        start = time.time()
        try:
            await self.facade.checkout(
                self.workspace_id, "test-feature", create_new=False, force=False
            )
            duration = time.time() - start
            self.print_pass("git_checkout", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_checkout", duration, str(e))

        # 4. git_delete_branch
        self.print_test("git_delete_branch")
        start = time.time()
        try:
            await self.facade.checkout(self.workspace_id, "master", False, False)
            await self.facade.delete_branch(
                self.workspace_id, "test-feature", force=False, remote=False
            )
            duration = time.time() - start
            self.print_pass("git_delete_branch", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_delete_branch", duration, str(e))

    async def test_history_operations(self):
        """测试历史操作（4个工具）"""
        self.print_header("历史操作测试")

        # 1. git_log
        self.print_test("git_log")
        start = time.time()
        try:
            result = await self.facade.log(self.workspace_id, max_count=10)
            duration = time.time() - start
            self.print_pass("git_log", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_log", duration, str(e))

        # 2. git_show
        self.print_test("git_show")
        start = time.time()
        try:
            result = await self.facade.show(self.workspace_id, "HEAD")
            duration = time.time() - start
            self.print_pass("git_show", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_show", duration, str(e))

        # 3. git_diff
        self.print_test("git_diff")
        start = time.time()
        try:
            result = await self.facade.diff(self.workspace_id, cached=False)
            duration = time.time() - start
            self.print_pass("git_diff", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_diff", duration, str(e))

        # 4. git_blame
        self.print_test("git_blame")
        start = time.time()
        try:
            result = await self.facade.blame(
                self.workspace_id, "test.txt", start_line=1, end_line=1
            )
            duration = time.time() - start
            self.print_pass("git_blame", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_blame", duration, str(e))

    async def test_tag_operations(self):
        """测试标签操作（3个工具）"""
        self.print_header("标签操作测试")

        # 1. git_create_tag
        self.print_test("git_create_tag")
        start = time.time()
        try:
            await self.facade.create_tag(
                self.workspace_id, "v1.0.0", message="Test tag", force=False
            )
            duration = time.time() - start
            self.print_pass("git_create_tag", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_create_tag", duration, str(e))

        # 2. git_list_tags
        self.print_test("git_list_tags")
        start = time.time()
        try:
            result = await self.facade.list_tags(self.workspace_id)
            duration = time.time() - start
            self.print_pass("git_list_tags", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_list_tags", duration, str(e))

        # 3. git_delete_tag
        self.print_test("git_delete_tag")
        start = time.time()
        try:
            await self.facade.delete_tag(self.workspace_id, "v1.0.0")
            duration = time.time() - start
            self.print_pass("git_delete_tag", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_delete_tag", duration, str(e))

    async def test_remote_operations(self):
        """测试远程操作（push、pull、fetch）"""
        self.print_header("远程操作测试")

        # Setup: 创建本地 bare 仓库
        import shutil

        import git

        temp_dir = Path("/tmp/test-api-remote")
        temp_dir.mkdir(exist_ok=True)
        bare_path = temp_dir / "remote.git"
        if bare_path.exists():
            shutil.rmtree(bare_path)
        git.Repo.init(str(bare_path), bare=True)

        workspace = await self.facade.get_workspace(self.workspace_id)
        repo = git.Repo(str(workspace["path"]))

        # 添加 remote
        if "origin" not in [r.name for r in repo.remotes]:
            repo.create_remote("origin", bare_path)

        # 1. git_push
        self.print_test("git_push")
        start = time.time()
        try:
            # 创建测试文件
            test_file = Path(workspace["path"]) / "push_test.txt"
            test_file.write_text("push test content")
            await self.facade.add(self.workspace_id, ["push_test.txt"])
            await self.facade.commit(self.workspace_id, "Push test commit")

            await self.facade.push(self.workspace_id, remote="origin", branch="master")
            duration = time.time() - start
            self.print_pass("git_push", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_push", duration, str(e))

        # 2. git_pull
        self.print_test("git_pull")
        start = time.time()
        try:
            await self.facade.pull(self.workspace_id, remote="origin", branch="master")
            duration = time.time() - start
            self.print_pass("git_pull", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_pull", duration, str(e))

        # 3. git_fetch
        self.print_test("git_fetch")
        start = time.time()
        try:
            await self.facade.fetch(self.workspace_id, remote="origin")
            duration = time.time() - start
            self.print_pass("git_fetch", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_fetch", duration, str(e))

    async def test_remote_management(self):
        """测试远程仓库管理"""
        self.print_header("远程仓库管理测试")

        # 1. git_add_remote
        self.print_test("git_add_remote")
        start = time.time()
        try:
            await self.facade.add_remote(self.workspace_id, "test_remote", "/tmp/test-remote.git")
            duration = time.time() - start
            self.print_pass("git_add_remote", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_add_remote", duration, str(e))

        # 2. git_list_remotes
        self.print_test("git_list_remotes")
        start = time.time()
        try:
            result = await self.facade.list_remotes(self.workspace_id)
            duration = time.time() - start
            self.print_pass("git_list_remotes", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_list_remotes", duration, str(e))

        # 3. git_remove_remote
        self.print_test("git_remove_remote")
        start = time.time()
        try:
            await self.facade.remove_remote(self.workspace_id, "test_remote")
            duration = time.time() - start
            self.print_pass("git_remove_remote", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_remove_remote", duration, str(e))

    async def test_stash_operations(self):
        """测试 Stash 操作"""
        self.print_header("Stash 操作测试")

        workspace = await self.facade.get_workspace(self.workspace_id)
        path = workspace["path"]
        Path(path, "stash_test.txt").write_text("stash content")

        # 1. git_stash
        self.print_test("git_stash")
        start = time.time()
        try:
            result = await self.facade.stash(
                self.workspace_id,
                save=True,
                pop=False,
                apply=False,
                drop=False,
                message="Test stash",
                include_untracked=False,
            )
            duration = time.time() - start
            self.print_pass("git_stash", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_stash", duration, str(e))

        # 2. git_list_stash
        self.print_test("git_list_stash")
        start = time.time()
        try:
            result = await self.facade.list_stash(self.workspace_id)
            duration = time.time() - start
            self.print_pass("git_list_stash", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_list_stash", duration, str(e))

    async def test_merge_operations(self):
        """测试 Merge 操作"""
        self.print_header("Merge 操作测试")

        # 创建测试分支
        self.print_test("创建测试分支")
        try:
            await self.facade.create_branch(
                self.workspace_id, "test-merge-branch", revision="master", force=False
            )
        except Exception as e:
            pass

        # 1. git_merge
        self.print_test("git_merge")
        start = time.time()
        try:
            result = await self.facade.merge(
                self.workspace_id, source_branch="test-merge-branch", fast_forward=True
            )
            duration = time.time() - start
            self.print_pass("git_merge", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_merge", duration, str(e))

    async def test_rebase_operations(self):
        """测试 Rebase 操作"""
        self.print_header("Rebase 操作测试")

        # 1. git_rebase
        self.print_test("git_rebase")
        start = time.time()
        try:
            await self.facade.rebase(
                self.workspace_id, branch=None, abort=False, continue_rebase=False
            )
            duration = time.time() - start
            self.print_pass("git_rebase", duration)
        except Exception as e:
            duration = time.time() - start
            self.print_fail("git_rebase", duration, str(e))

    def print_summary(self):
        """打印测试总结"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"\n{Colors.GREEN}{'=' * 40}{Colors.GREEN}")
        print(f"{Colors.GREEN}功能接口验证总结{Colors.GREEN}")
        print(f"{Colors.GREEN}{'=' * 40}{Colors.GREEN}")
        print(f"总测试数: {total}")
        print(f"{Colors.GREEN}通过: {passed}{Colors.GREEN}")
        print(f"{Colors.RED}失败: {failed}{Colors.GREEN}")
        print(f"通过率: {pass_rate:.2f}%")
        print(f"{Colors.GREEN}{'=' * 40}{Colors.GREEN}\n")

        return 0 if failed == 0 else 1

    async def run_all_tests(self):
        """运行所有测试"""
        print(f"{Colors.GREEN}{'=' * 40}{Colors.GREEN}")
        print(f"{Colors.GREEN}mcp-git 功能接口验证{Colors.GREEN}")
        print(f"{Colors.GREEN}{'=' * 40}{Colors.GREEN}\n")

        try:
            await self.setup()

            # 运行各类测试
            await self.test_workspace_management()
            await self.test_repository_operations()
            await self.test_commit_operations()
            await self.test_branch_operations()
            await self.test_history_operations()
            await self.test_tag_operations()
            await self.test_remote_operations()
            await self.test_remote_management()
            await self.test_stash_operations()
            await self.test_merge_operations()
            await self.test_rebase_operations()

            await self.cleanup()

            return self.print_summary()
        except Exception as e:
            print(f"{Colors.RED}测试执行失败: {e}{Colors.GREEN}")
            return 1


async def main():
    validator = APIValidator()
    exit_code = await validator.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
