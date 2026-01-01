# mcp-git 验证测试目录

本目录包含 mcp-git 项目的完整验证测试体系，用于验证所有功能和接口的正确性。

## 目录结构

```
temp/test/
├── README.md                    # 本文档
├── run_all.sh                   # 主运行器（执行所有验证）
├── scripts/
│   ├── uat_validator.sh         # UAT 验证脚本
│   ├── api_validator.py         # 功能接口验证脚本
│   ├── scenario_validator.sh    # 场景测试脚本
│   └── create_test_repos.sh     # 测试仓库创建脚本
├── data/
│   ├── repos/                   # 测试仓库
│   │   ├── test-repo-1/         # 小型测试仓库
│   │   ├── test-repo-2/         # 中型测试仓库
│   │   └── test-repo-lfs/       # LFS 测试仓库
│   └── fixtures/                # 测试固件
│       ├── commits.json         # 测试提交数据
│       └── branches.json        # 测试分支数据
└── configs/
    ├── uat_config.yaml          # UAT 配置
    └── test_config.yaml         # 通用测试配置
```

## 快速开始

### 运行所有验证

```bash
cd /home/project/mcp-git/temp/test
chmod +x run_all.sh
./run_all.sh
```

### 运行单个验证

```bash
# UAT 验证
bash scripts/uat_validator.sh

# 功能接口验证
python3 scripts/api_validator.py

# 场景测试
bash scripts/scenario_validator.sh
```

### 重新创建测试仓库

```bash
bash scripts/create_test_repos.sh
```

## 验证类型

### 1. 用户验收测试（UAT）

基于 `docs/uat.md` 的要求进行验证：

**P0 功能验收**（9个测试）：
- Clone、Init、Status、Add、Commit、Push、Pull、Checkout、Merge

**P1 功能验收**（4个测试）：
- Branch、Tag、Stash、Log

**开发工作流场景**（5个测试）：
- 创建仓库 → 提交 → 推送 → 拉取 → 合并

**性能指标验证**（3个测试）：
- 响应时间 < 2s
- 内存占用 < 100MB
- 并发操作

### 2. 功能接口验证

验证所有 48 个 MCP 工具：

**工作区管理**（5个）：
- allocate_workspace、get_workspace、release_workspace、list_workspaces、disk_space

**仓库操作**（3个）：
- clone、init、status

**提交操作**（2个）：
- add、commit

**分支操作**（4个）：
- create_branch、list_branches、checkout、delete_branch

**历史操作**（4个）：
- log、show、diff、blame

**标签操作**（3个）：
- create_tag、list_tags、delete_tag

### 3. 场景测试

模拟真实使用场景：

**场景 1：AI 代码审查助手**
- Clone → Log → Diff → Blame

**场景 2：自动化 Bug 修复**
- Checkout → Modify → Add → Commit → Push

**场景 3：多仓库同步**
- Clone → Fetch → Merge → Push

**场景 4：团队协作**
- 分支创建 → 并行开发 → 合并请求

## 测试数据

### 测试仓库

1. **test-repo-1**：小型仓库
   - 4 个提交
   - 2 个分支（master、develop）
   - 基础功能测试

2. **test-repo-2**：中型仓库
   - 20 个提交
   - 3 个分支（master、feature-a、feature-b）
   - 包含冲突场景

3. **test-repo-lfs**：LFS 测试仓库
   - 包含大文件（5MB）
   - 配置了 Git LFS
   - 用于测试 LFS 功能

### 测试固件

- `commits.json`：预定义的提交数据
- `branches.json`：预定义的分支数据

## 配置文件

### uat_config.yaml

UAT 验证配置，包括：
- P0/P1 功能列表
- 性能指标阈值
- 工作流场景定义

### test_config.yaml

通用测试配置，包括：
- 测试数据路径
- 功能接口测试配置
- 场景测试配置
- 输出格式配置

## 输出格式

所有验证脚本使用控制台输出，包括：

- 测试进度
- 通过/失败状态
- 错误信息（如果失败）
- 测试耗时
- 总结报告（通过率、失败数、总耗时）

## 注意事项

1. **依赖项**：
   - Python 3.10+
   - Git
   - pytest（用于 API 验证）

2. **权限**：
   - 确保有权限创建临时目录
   - 确保有权限执行 shell 脚本

3. **清理**：
   - 主运行器会自动清理临时文件
   - 也可以手动清理 `/tmp/test-*` 目录

4. **环境**：
   - 测试在 `/tmp` 目录下创建临时文件
   - 不会影响项目主目录

## 故障排除

### UAT 验证失败

如果 UAT 验证失败，检查：
- Git 命令是否可用
- 是否有足够的磁盘空间
- 是否有执行权限

### API 验证失败

如果 API 验证失败，检查：
- Python 环境是否正确
- mcp_git 模块是否可导入
- 依赖项是否已安装

### 场景测试失败

如果场景测试失败，检查：
- 测试仓库是否已创建
- Git 配置是否正确
- 是否有足够的权限

## 扩展

### 添加新的验证

1. 在 `scripts/` 目录下创建新的验证脚本
2. 在 `run_all.sh` 中添加调用
3. 更新本文档

### 添加新的测试数据

1. 在 `data/repos/` 目录下创建新的测试仓库
2. 在 `data/fixtures/` 目录下添加新的固件数据
3. 更新配置文件

## 维护

### 更新测试仓库

```bash
cd /home/project/mcp-git/temp/test
rm -rf data/repos/*
bash scripts/create_test_repos.sh
```

### 更新配置

编辑 `configs/` 目录下的配置文件。

## 联系方式

如有问题，请参考：
- 项目文档：`docs/`
- 测试文档：`docs/test.md`
- UAT 文档：`docs/uat.md`