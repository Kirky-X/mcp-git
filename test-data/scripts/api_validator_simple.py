#!/usr/bin/env python3
"""
简化的 API 验证脚本
只测试基本功能，避免兼容性问题
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path = [p for p in sys.path if '/home/dev/mcps' not in p]

from mcp_git.storage import SqliteStorage
from mcp_git.service.facade import GitServiceFacade


class SimpleAPIValidator:
    """简化的 API 验证器"""
    
    def __init__(self):
        self.facade = None
        self.workspace_id = None
        self.passed = 0
        self.failed = 0
    
    def print_test(self, name):
        print(f"[TEST] {name}")
    
    def print_pass(self, name, duration=None):
        duration_str = f" ({duration:.2f}s)" if duration else ""
        print(f"[PASS] {name}{duration_str}")
        self.passed += 1
    
    def print_fail(self, name, error):
        print(f"[FAIL] {name}: {error}")
        self.failed += 1
    
    async def setup(self):
        """设置测试环境"""
        self.print_test("初始化测试环境")
        try:
            storage = SqliteStorage(database_path=":memory:")
            await storage.initialize()
            self.facade = GitServiceFacade(storage=storage)
            
            workspace = await self.facade.allocate_workspace()
            self.workspace_id = workspace["workspace_id"]
            
            self.print_pass("初始化测试环境")
        except Exception as e:
            self.print_fail("初始化测试环境", str(e))
            raise
    
    async def cleanup(self):
        """清理测试环境"""
        if self.workspace_id:
            try:
                await self.facade.release_workspace(self.workspace_id)
            except Exception as e:
                print(f"清理失败: {e}")
    
    async def test_basic_operations(self):
        """测试基本操作"""
        print("\n=== 基本操作测试 ===\n")
        
        # 1. get_workspace
        self.print_test("git_get_workspace")
        try:
            workspace = await self.facade.get_workspace(self.workspace_id)
            if workspace:
                self.print_pass("git_get_workspace")
            else:
                self.print_fail("git_get_workspace", "Workspace not found")
        except Exception as e:
            self.print_fail("git_get_workspace", str(e))
        
        # 2. list_workspaces
        self.print_test("git_list_workspaces")
        try:
            workspaces = await self.facade.list_workspaces()
            if workspaces:
                self.print_pass("git_list_workspaces")
            else:
                self.print_fail("git_list_workspaces", "No workspaces")
        except Exception as e:
            self.print_fail("git_list_workspaces", str(e))
        
        # 3. get_disk_space_info
        self.print_test("git_disk_space_info")
        try:
            info = self.facade.get_disk_space_info()
            if info:
                self.print_pass("git_disk_space_info")
            else:
                self.print_fail("git_disk_space_info", "No info")
        except Exception as e:
            self.print_fail("git_disk_space_info", str(e))
        
        # 4. release_workspace
        self.print_test("git_release_workspace")
        try:
            await self.facade.release_workspace(self.workspace_id)
            self.print_pass("git_release_workspace")
            
            # 重新分配工作区
            workspace = await self.facade.allocate_workspace()
            self.workspace_id = workspace["workspace_id"]
        except Exception as e:
            self.print_fail("git_release_workspace", str(e))
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 40)
        print("mcp-git 简化 API 验证")
        print("=" * 40)
        
        try:
            await self.setup()
            await self.test_basic_operations()
            await self.cleanup()
            
            # 打印总结
            total = self.passed + self.failed
            print("\n" + "=" * 40)
            print("API 验证总结")
            print("=" * 40)
            print(f"总测试数: {total}")
            print(f"通过: {self.passed}")
            print(f"失败: {self.failed}")
            print(f"通过率: {(self.passed / total * 100):.2f}%")
            print("=" * 40)
            
            return 0 if self.failed == 0 else 1
        except Exception as e:
            print(f"测试执行失败: {e}")
            return 1


async def main():
    validator = SimpleAPIValidator()
    exit_code = await validator.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())