<div align="center">

# 📖 用户指南

### 掌握 mcp-git 的完整指南

[🏠 首页](../README.md) • [🔧 API 参考](API_REFERENCE.md) • [❓ FAQ](FAQ.md) • [🔧 故障排除](TROUBLESHOOTING.md)

---

</div>

## 目录

- [简介](#简介)
- [安装](#安装)
- [核心概念](#核心概念)
- [基础用法](#基础用法)
- [高级用法](#高级用法)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)

---

## 简介

<div align="center">

### 什么是 mcp-git？

</div>

**mcp-git** 是一个基于 Python 的 Git 操作 MCP (Model Context Protocol) 服务器，专为需要 Git 版本控制能力的 AI 助手和自动化工具设计。它提供了完整的 Git 操作接口，包括仓库克隆、分支管理、提交操作、远程同步等功能。

**核心特性：**

- ✅ **完整的 Git 操作** - 支持所有常用 Git 操作
- ✅ **MCP 协议集成** - 与 Claude 等 AI 助手无缝对接
- ✅ **工作空间管理** - 安全隔离的临时工作区
- ✅ **任务队列** - 支持并发执行和优先级控制
- ✅ **凭证管理** - SSH 和 HTTPS 凭证安全处理
- ✅ **Python 原生** - 简洁的 Python API 设计

**适用场景：**

- 🤖 AI 助手代码仓库操作
- 🔄 CI/CD 自动化脚本
- 📦 部署工具中的 Git 操作
- 🔧 开发工具中的版本控制

**版本信息：**

- 当前版本：查看 [CHANGELOG](../CHANGELOG.md)
- 许可证：MIT / Apache 2.0
- 作者：Anthropic

---

## 安装

<div align="center">

### 🚀 开始安装

</div>

### 系统要求

在安装之前，请确保您的系统满足以下要求：

**必需组件：**

| 组件 | 要求 | 说明 |
|------|------|------|
| Python | 3.10+ | 编程语言环境 |
| Git | 2.0+ | 版本控制系统 |
| pip/uv | 最新版本 | Python 包管理器 |

**推荐环境：**

| 组件 | 推荐版本 | 说明 |
|------|----------|------|
| Python | 3.11 或 3.12 | 最佳性能和稳定性 |
| uv | 最新版本 | 快速包管理器 |
| Git | 最新稳定版 | 完整功能支持 |

**平台支持：**

- ✅ Linux (x86_64, ARM64)
- ✅ macOS (Intel, Apple Silicon)
- ✅ Windows 10+

---

### 安装方式

<div align="center">

#### 选择您的安装方式

</div>

<table>
<tr>
<td width="50%">

**📦 使用 uv（推荐）**

uv 是一个现代的 Python 包管理器，速度比 pip 快很多。

```bash
# 安装 uv（如果尚未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装 mcp-git
uv pip install mcp-git
```

**优点：**
- �� 安装速度极快
- 📦 依赖管理更好
- 🔄 环境隔离更佳

</td>
<td width="50%">

**🐍 使用 pip**

如果您熟悉传统的 Python 包管理，可以选择 pip。

```bash
# 使用 pip 安装
pip install mcp-git

# 或升级到最新版本
pip install --upgrade mcp-git
```

**优点：**
- 📖 简单熟悉
- 🔧 广泛的兼容性
- 🌍 适合所有 Python 环境

</td>
</tr>
</table>

---

### 从源码安装

如果您需要开发版本或想要安装最新功能，可以从源码安装：

**步骤：**

```bash
# 克隆仓库
git clone https://github.com/anthropics/mcp-git.git
cd mcp-git

# 创建虚拟环境
uv venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

# 安装依赖并安装包
uv pip install -e .

# 验证安装
python -c "import mcp_git; print('安装成功！')"
```

---

### Docker 安装

如果您使用 Docker，可以直接使用官方镜像或构建自己的镜像：

**使用官方镜像：**

```bash
# 拉取官方镜像
docker pull ghcr.io/anthropics/mcp-git:latest

# 运行容器
docker run -v $(pwd)/workspaces:/app/workspaces \
  -e GIT_WORKSPACE_DIR=/app/workspaces \
  ghcr.io/anthropics/mcp-git:latest
```

**构建自定义镜像：**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install uv && \
    uv pip install mcp-git

CMD ["python", "-c", "from mcp_git.server.main import main; import asyncio; asyncio.run(main())"]
```

**Docker Compose：**

```yaml
version: '3.8'
services:
  mcp-git:
    image: ghcr.io/anthropics/mcp-git:latest
    volumes:
      - ./workspaces:/app/workspaces
    environment:
      - GIT_WORKSPACE_DIR=/app/workspaces
    ports:
      - "8080:8080"
```

---

### 验证安装

安装完成后，运行以下命令验证安装是否成功：

**Python 验证：**

```python
# 检查导入
python -c "
import mcp_git
from mcp_git.server.main import main
from mcp_git.service.facade import GitServiceFacade
print('✅ mcp-git 导入成功！')
print(f'版本: {mcp_git.__version__}')
"

# 测试服务器启动
python -c "
import asyncio
from mcp_git.server.main import main

async def test():
    try:
        await main()
    except SystemExit:
        pass

asyncio.run(test())
"
```

**CLI 验证：**

```bash
# 如果提供了 CLI 工具
mcp-git --version
mcp-git --help
```

---

### 故障排除

如果在安装过程中遇到问题，请参考以下常见解决方案：

**问题 1：Python 版本不兼容**

```bash
# 检查 Python 版本
python --version

# 如果版本低于 3.10，请升级
# macOS: brew install python@3.11
# Ubuntu: sudo apt install python3.11
# Windows: 从 python.org 下载安装
```

**问题 2：权限错误**

```bash
# Linux/macOS: 使用 --user 或创建虚拟环境
pip install --user mcp-git

# 或使用 uv（推荐）
uv pip install mcp-git
```

**问题 3：依赖安装失败**

```bash
# 创建新的虚拟环境
uv venv myenv
source myenv/bin/activate

# 重新安装
uv pip install mcp-git
```

**更多问题：** 查看 [FAQ](FAQ.md) 或 [故障排除指南](TROUBLESHOOTING.md)

---

## 核心概念

<div align="center">

### 🧠 理解 mcp-git

</div>

### GitServiceFacade

`GitServiceFacade` 是 mcp-git 的核心门面类，它统一了所有 Git 操作，提供了简洁的 API 入口：

```python
from mcp_git.service.facade import GitServiceFacade

# 创建门面实例
facade = GitServiceFacade()

# 执行 Git 操作
await facade.clone(url="https://github.com/user/repo", workspace_id=workspace_id)
await facade.checkout(workspace_id=workspace_id, branch="main")
await facade.commit(workspace_id=workspace_id, message="更新内容")
await facade.push(workspace_id=workspace_id)
```

**设计原则：**

- 🔒 **单一职责** - 每个方法专注于一个操作
- 📦 **统一接口** - 隐藏内部复杂性
- ⚡ **异步优先** - 所有操作都是异步的

---

### 工作空间

工作空间是 mcp-git 管理 Git 仓库的核心概念，提供了安全的隔离环境：

**工作空间特性：**

| 特性 | 说明 |
|------|------|
| 隔离性 | 每个工作空间有独立的临时目录 |
| 生命周期 | 支持创建、检查、清理 |
| 自动管理 | LRU/FIFO 清理策略 |
| 统计信息 | 跟踪使用情况和资源占用 |

**基本用法：**

```python
from uuid import uuid4
from mcp_git.service.workspace import WorkspaceManager

manager = WorkspaceManager()

# 创建工作空间
workspace_id = uuid4()
await manager.create(workspace_id)

# 检查是否存在
exists = await manager.exists(workspace_id)

# 获取工作空间路径
path = await manager.get_path(workspace_id)

# 清理工作空间
await manager.cleanup(workspace_id)
```

---

### 任务队列

mcp-git 实现了任务队列机制，支持并发执行和优先级控制：

```python
from mcp_git.service.task import TaskQueue, TaskPriority

queue = TaskQueue(max_concurrent=5)

# 添加任务
task_id = await queue.add_task(
    func=git_clone,
    args={"url": "...", "workspace_id": "..."},
    priority=TaskPriority.HIGH
)

# 检查任务状态
status = await queue.get_status(task_id)

# 取消任务
await queue.cancel(task_id)
```

**任务优先级：**

| 优先级 | 值 | 使用场景 |
|--------|-----|----------|
| CRITICAL | 0 | 紧急操作 |
| HIGH | 1 | 重要任务 |
| NORMAL | 2 | 默认优先级 |
| LOW | 3 | 后台任务 |

---

### 凭证管理

mcp-git 提供了安全的凭证管理机制，支持多种认证方式：

**凭证类型：**

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| SSH 代理 | 通过 SSH 代理获取凭证 | SSH 协议仓库 |
| 环境变量 | 从环境变量读取令牌 | CI/CD 环境 |
| 凭证助手 | Git 凭证助手 | HTTPS 协议仓库 |

**基本用法：**

```python
from mcp_git.utils.credential import CredentialHelper

helper = CredentialHelper()

# 从 SSH 代理加载凭证
await helper.load_ssh_agent_creds()

# 存储凭证
await helper.store_credentials("github.com", "user", "token")

# 获取凭证
credentials = await helper.get_credentials("github.com")

# 清除凭证
await helper.clear_credentials("github.com")
```

**安全提示：**

- ⚠️ 永远不要在代码中硬编码凭证
- ⚠️ 确保凭证文件权限正确
- ⚠️ 定期轮换凭证

---

### 事件系统

mcp-git 提供了事件系统，用于监控操作进度和状态变化：

```python
from mcp_git.utils.events import EventEmitter, GitEvents

emitter = EventEmitter()

# 监听事件
emitter.on(GitEvents.CLONE_PROGRESS, lambda data: print(f"进度: {data}%"))

# 触发事件
await emitter.emit(GitEvents.CLONE_PROGRESS, {"progress": 50})
```

**可用事件：**

| 事件 | 说明 |
|------|------|
| CLONE_STARTED | 克隆开始 |
| CLONE_PROGRESS | 克隆进度 |
| CLONE_COMPLETED | 克隆完成 |
| PUSH_STARTED | 推送开始 |
| PUSH_PROGRESS | 推送进度 |
| PUSH_COMPLETED | 推送完成 |
| ERROR | 操作错误 |

---

### 配置管理

mcp-git 提供了灵活的配置系统，支持多种配置方式：

**配置选项：**

```python
from mcp_git.config import ServerConfig, WorkspaceConfig

# 服务器配置
server_config = ServerConfig(
    host="0.0.0.0",
    port=8080,
    max_concurrent_tasks=10,
    task_timeout=300,
)

# 工作空间配置
workspace_config = WorkspaceConfig(
    root_dir="/path/to/workspaces",
    max_workspaces=100,
    cleanup_strategy="lru",
    cleanup_interval=3600,
)
```

**配置优先级：**

1. 环境变量
2. 配置文件
3. 代码配置
4. 默认值

---

## 基础用法

<div align="center">

### 💡 开始使用

</div>

### 快速开始

以下是一个完整的示例，展示如何执行基本的 Git 操作：

```python
import asyncio
from uuid import uuid4
from mcp_git.service.facade import GitServiceFacade
from mcp_git.types import CloneOptions

async def main():
    # 1. 创建门面实例
    facade = GitServiceFacade()
    
    # 2. 创建工作空间标识
    workspace_id = uuid4()
    
    # 3. 克隆仓库
    print("开始克隆仓库...")
    clone_result = await facade.clone(
        url="https://github.com/octocat/Hello-World.git",
        workspace_id=workspace_id,
        options=CloneOptions(depth=1),
    )
    print(f"✅ 克隆成功！提交: {clone_result['oid']}")
    
    # 4. 查看仓库状态
    status = await facade.status(workspace_id=workspace_id)
    print(f"📊 当前分支: {status['branch']}")
    print(f"📝 修改文件数: {len(status['modified'])}")
    
    # 5. 切换分支
    await facade.checkout(workspace_id=workspace_id, branch="main")
    print("✅ 已切换到 main 分支")
    
    # 6. 清理工作空间
    await facade.cleanup(workspace_id)
    print("🧹 工作空间已清理")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 克隆仓库

克隆是 Git 操作中最常用的功能之一：

```python
from mcp_git.service.facade import GitServiceFacade
from mcp_git.types import CloneOptions
from uuid import uuid4

async def clone_examples():
    facade = GitServiceFacade()
    
    # 基本克隆
    workspace_id = uuid4()
    result = await facade.clone(
        url="https://github.com/user/repo.git",
        workspace_id=workspace_id,
    )
    
    # 浅克隆（更快，适合大型仓库）
    workspace_id = uuid4()
    result = await facade.clone(
        url="https://github.com/user/large-repo.git",
        workspace_id=workspace_id,
        options=CloneOptions(depth=1),
    )
    
    # 指定分支克隆
    workspace_id = uuid4()
    result = await facade.clone(
        url="https://github.com/user/repo.git",
        workspace_id=workspace_id,
        options=CloneOptions(branch="develop"),
    )
    
    # 单分支浅克隆（最快）
    workspace_id = uuid4()
    result = await facade.clone(
        url="https://github.com/user/repo.git",
        workspace_id=workspace_id,
        options=CloneOptions(
            depth=1,
            single_branch=True,
            branch="feature/new-feature",
        ),
    )
```

**克隆选项：**

| 选项 | 类型 | 说明 |
|------|------|------|
| depth | int | 浅克隆深度，1 表示仅最新提交 |
| branch | str | 指定克隆的分支 |
| single_branch | bool | 是否仅克隆指定分支 |
| recursive | bool | 是否递归克隆子模块 |

---

### 分支操作

管理 Git 分支是日常开发的重要部分：

```python
async def branch_examples():
    facade = GitServiceFacade()
    workspace_id = uuid4()
    
    # 确保仓库已克隆
    await facade.clone(url="https://github.com/user/repo.git", workspace_id=workspace_id)
    
    # 1. 列出所有分支
    branches = await facade.branch_list(workspace_id=workspace_id)
    print(f"📋 分支列表: {branches['branches']}")
    
    # 2. 切换到已有分支
    await facade.checkout(workspace_id=workspace_id, branch="develop")
    print("✅ 已切换到 develop 分支")
    
    # 3. 创建新分支
    await facade.checkout(workspace_id=workspace_id, branch="feature/new-feature", create_branch=True)
    print("✅ 已创建并切换到新分支")
    
    # 4. 删除分支
    await facade.branch_delete(workspace_id=workspace_id, branch="old-feature")
    print("✅ 已删除 old-feature 分支")
```

---

### 提交操作

创建和管理 Git 提交：

```python
async def commit_examples():
    facade = GitServiceFacade()
    workspace_id = uuid4()
    
    await facade.clone(url="https://github.com/user/repo.git", workspace_id=workspace_id)
    
    # 1. 查看仓库状态
    status = await facade.status(workspace_id=workspace_id)
    print(f"修改文件: {status['modified']}")
    print(f"未跟踪文件: {status['untracked']}")
    
    # 2. 添加文件到暂存区
    await facade.add(workspace_id=workspace_id, files=["new_file.py"])
    
    # 3. 创建提交
    commit_result = await facade.commit(
        workspace_id=workspace_id,
        message="添加新功能",
        description="详细描述提交内容",
    )
    print(f"✅ 提交成功！SHA: {commit_result['oid']}")
    
    # 4. 查看提交历史
    commits = await facade.log(workspace_id=workspace_id, limit=10)
    for commit in commits:
        print(f"- {commit['oid'][:8]}: {commit['message']}")
```

---

### 远程操作

与远程仓库同步：

```python
async def remote_examples():
    facade = GitServiceFacade()
    workspace_id = uuid4()
    
    await facade.clone(url="https://github.com/user/repo.git", workspace_id=workspace_id)
    
    # 1. 拉取远程更改
    print("拉取远程更改...")
    await facade.pull(workspace_id=workspace_id)
    print("✅ 拉取完成")
    
    # 2. 推送到远程
    await facade.push(workspace_id=workspace_id)
    print("✅ 推送完成")
    
    # 3. 指定远程和分支
    await facade.push(
        workspace_id=workspace_id,
        remote="origin",
        branch="feature/new-feature",
    )
    
    # 4. 获取远程信息
    remote_info = await facade.remote_info(workspace_id=workspace_id)
    print(f"远程: {remote_info['name']}")
    print(f"URL: {remote_info['url']}")
```

---

### 查看仓库信息

获取仓库的详细信息：

```python
async def info_examples():
    facade = GitServiceFacade()
    workspace_id = uuid4()
    
    await facade.clone(url="https://github.com/user/repo.git", workspace_id=workspace_id)
    
    # 1. 查看仓库状态
    status = await facade.status(workspace_id=workspace_id)
    print(f"当前分支: {status['branch']}")
    print(f"远程分支: {status['remote_branches']}")
    print(f"本地修改: {len(status['modified'])} 个文件")
    print(f"未跟踪文件: {len(status['untracked'])} 个文件")
    
    # 2. 查看提交历史
    log = await facade.log(workspace_id=workspace_id, limit=5)
    for commit in log:
        print(f"\n提交: {commit['oid']}")
        print(f"作者: {commit['author']}")
        print(f"日期: {commit['date']}")
        print(f"消息: {commit['message']}")
    
    # 3. 查看差异
    diff = await facade.diff(workspace_id=workspace_id)
    print(f"\n差异统计:")
    print(f"  新增: {diff['additions']} 行")
    print(f"  删除: {diff['deletions']} 行")
    
    # 4. 查看分支差异
    diff_branch = await facade.diff_branch(
        workspace_id=workspace_id,
        source_branch="main",
        target_branch="develop",
    )
```

---

## 高级用法

<div align="center">

### 🚀 高级功能

</div>

### 并发操作

mcp-git 支持并发执行多个 Git 操作：

```python
import asyncio
from uuid import uuid4
from mcp_git.service.facade import GitServiceFacade

async def concurrent_clone():
    facade = GitServiceFacade()
    
    # 准备多个仓库配置
    repos = [
        ("https://github.com/user/repo1.git", uuid4()),
        ("https://github.com/user/repo2.git", uuid4()),
        ("https://github.com/user/repo3.git", uuid4()),
    ]
    
    # 并发克隆
    tasks = [
        facade.clone(url=url, workspace_id=ws_id)
        for url, ws_id in repos
    ]
    
    results = await asyncio.gather(*tasks)
    
    for i, result in enumerate(results):
        print(f"✅ 仓库 {i+1} 克隆完成: {result['oid']}")
    
    return results

async def concurrent_operations():
    facade = GitServiceFacade()
    workspace_id = uuid4()
    
    await facade.clone(url="https://github.com/user/repo.git", workspace_id=workspace_id)
    
    # 并发执行多个操作
    tasks = [
        facade.status(workspace_id=workspace_id),
        facade.log(workspace_id=workspace_id, limit=5),
        facade.branch_list(workspace_id=workspace_id),
    ]
    
    results = await asyncio.gather(*tasks)
    
    status, log, branches = results
    print(f"📊 状态: {status['branch']}")
    print(f"📝 提交数: {len(log)}")
    print(f"🌿 分支数: {len(branches['branches'])}")
```

---

### 自定义配置

根据需求自定义 mcp-git 的行为：

```python
from mcp_git.config import ServerConfig, WorkspaceConfig
from mcp_git.service.facade import GitServiceFacade

# 自定义服务器配置
server_config = ServerConfig(
    host="127.0.0.1",           # 绑定地址
    port=8080,                   # 端口号
    max_concurrent_tasks=10,     # 最大并发任务数
    task_timeout=600,            # 任务超时时间（秒）
    log_level="DEBUG",           # 日志级别
)

# 自定义工作空间配置
workspace_config = WorkspaceConfig(
    root_dir="/custom/workspaces",    # 工作空间根目录
    max_workspaces=50,                # 最大工作空间数
    cleanup_strategy="lru",           # 清理策略: lru 或 fifo
    cleanup_interval=1800,            # 清理间隔（秒）
    auto_cleanup=True,                # 是否自动清理
)

# 使用自定义配置创建门面
facade = GitServiceFacade(
    server_config=server_config,
    workspace_config=workspace_config,
)
```

---

### 事件处理

监听和响应 Git 操作事件：

```python
from mcp_git.utils.events import EventEmitter, GitEvents

async def event_handling():
    facade = GitServiceFacade()
    emitter = EventEmitter()
    
    # 注册事件处理器
    def on_clone_start(data):
        print(f"🚀 开始克隆: {data['url']}")
    
    def on_clone_progress(data):
        print(f"📊 克隆进度: {data['progress']}%")
    
    def on_clone_complete(data):
        print(f"✅ 克隆完成！提交: {data['oid']}")
    
    def on_error(data):
        print(f"❌ 错误: {data['message']}")
    
    emitter.on(GitEvents.CLONE_STARTED, on_clone_start)
    emitter.on(GitEvents.CLONE_PROGRESS, on_clone_progress)
    emitter.on(GitEvents.CLONE_COMPLETED, on_clone_complete)
    emitter.on(GitEvents.ERROR, on_error)
    
    # 执行克隆（事件会被自动触发）
    await facade.clone(
        url="https://github.com/user/repo.git",
        workspace_id=uuid4(),
        event_emitter=emitter,
    )
```

---

### 错误处理

优雅地处理各种错误情况：

```python
from mcp_git.service.git import GitError, GitNotFoundError, GitAuthError
from mcp_git.service.workspace import WorkspaceError

async def error_handling():
    facade = GitServiceFacade()
    
    try:
        # 尝试克隆不存在的仓库
        await facade.clone(
            url="https://github.com/user/nonexistent.git",
            workspace_id=uuid4(),
        )
    except GitNotFoundError as e:
        print(f"⚠️ 仓库未找到: {e.url}")
        # 处理未找到错误
        
    except GitAuthError as e:
        print(f"🔐 认证失败: {e.message}")
        # 处理认证错误，可能需要更新凭证
        
    except GitError as e:
        print(f"❌ Git 错误: {e.message}")
        # 处理其他 Git 错误
        
    except WorkspaceError as e:
        print(f"📁 工作空间错误: {e.message}")
        # 处理工作空间错误
        
    except Exception as e:
        print(f"💥 未知错误: {e}")
        # 处理未知错误

# 自定义错误处理
async def custom_error_handling():
    try:
        result = await facade.clone(...)
    except GitError as e:
        # 记录错误日志
        logger.error(f"Git 操作失败: {e}")
        
        # 根据错误类型采取不同措施
        if isinstance(e, GitNotFoundError):
            # 仓库不存在，可能需要检查 URL
            await handle_not_found(e.url)
        elif isinstance(e, GitAuthError):
            # 认证问题，可能需要刷新凭证
            await refresh_credentials()
        else:
            # 其他错误，可能需要重试
            await retry_operation()
```

---

### 进度监控

监控长时间运行操作的进度：

```python
async def progress_monitoring():
    facade = GitServiceFacade()
    
    def progress_callback(progress):
        """进度回调函数"""
        print(f"\r📦 进度: {progress.percent}% ", end="", flush=True)
        if progress.status == "cloning":
            print(f"- 正在克隆: {progress.received_objects}/{progress.total_objects}")
        elif progress.status == "compressing":
            print(f"- 压缩: {progress.percent}%")
    
    # 执行带进度监控的克隆
    result = await facade.clone(
        url="https://github.com/user/large-repo.git",
        workspace_id=uuid4(),
        progress_callback=progress_callback,
    )
    
    print(f"\n✅ 克隆完成！最终提交: {result['oid']}")
```

---

### 自定义 Git 选项

为不同的 Git 操作提供自定义选项：

```python
from mcp_git.types import (
    CloneOptions,
    CommitOptions,
    PushOptions,
    MergeOptions,
)

async def custom_options():
    facade = GitServiceFacade()
    workspace_id = uuid4()
    
    # 自定义克隆选项
    clone_opts = CloneOptions(
        depth=1,                    # 浅克隆
        single_branch=True,         # 仅当前分支
        branch="main",              # 指定分支
        no_checkout=False,          # 克隆后检出
        recursive=False,            # 包含子模块
    )
    await facade.clone(
        url="https://github.com/user/repo.git",
        workspace_id=workspace_id,
        options=clone_opts,
    )
    
    # 自定义提交选项
    commit_opts = CommitOptions(
        all=True,                   # 自动暂存所有修改
        amend=False,                # 修改上次提交
        no_verify=False,            # 跳过钩子验证
    )
    
    # 自定义推送选项
    push_opts = PushOptions(
        force=False,                # 强制推送
        tags=False,                 # 推送标签
        prune=False,                # 清理远程引用
    )
```

---

## 最佳实践

<div align="center">

### ✨ 优化建议

</div>

### 代码组织

```python
# ❌ 不推荐的写法
async def bad_example():
    facade = GitServiceFacade()
    # 所有操作挤在一个函数中
    ws1 = uuid4()
    ws2 = uuid4()
    await facade.clone(url1, ws1)
    await facade.clone(url2, ws2)
    # ... 更多代码

# ✅ 推荐的写法
class GitRepositoryManager:
    def __init__(self):
        self.facade = GitServiceFacade()
        self.workspaces = {}
    
    async def add_repository(self, repo_id: str, url: str):
        workspace_id = uuid4()
        result = await self.facade.clone(url=url, workspace_id=workspace_id)
        self.workspaces[repo_id] = workspace_id
        return result
    
    async def get_status(self, repo_id: str):
        workspace_id = self.workspaces.get(repo_id)
        if workspace_id:
            return await self.facade.status(workspace_id=workspace_id)
        return None
    
    async def cleanup_repo(self, repo_id: str):
        workspace_id = self.workspaces.pop(repo_id, None)
        if workspace_id:
            await self.facade.cleanup(workspace_id)
```

---

### 错误处理策略

```python
import asyncio
from mcp_git.service.git import GitError
from mcp_git.utils.retry import retry

# 使用重试装饰器处理临时错误
@retry(max_attempts=3, delay=1, backoff=2)
async def robust_clone(url: str, workspace_id):
    try:
        return await facade.clone(url=url, workspace_id=workspace_id)
    except GitError as e:
        if "connection" in str(e).lower():
            print(f"网络问题，重试中: {e}")
            raise  # 触发重试
        raise  # 其他错误不重试

# 批量操作中的错误处理
async def batch_clone(urls: list[str]):
    results = []
    errors = []
    
    for url in urls:
        try:
            result = await robust_clone(url, uuid4())
            results.append({"url": url, "result": result})
        except Exception as e:
            errors.append({"url": url, "error": str(e)})
    
    print(f"✅ 成功: {len(results)}")
    print(f"❌ 失败: {len(errors)}")
    
    return results, errors
```

---

### 性能优化

```python
# ✅ 性能优化建议

# 1. 使用浅克隆
async def optimize_clone():
    await facade.clone(
        url="https://github.com/user/large-repo.git",
        workspace_id=workspace_id,
        options=CloneOptions(depth=1),
    )

# 2. 使用单分支克隆
async def optimize_single_branch():
    await facade.clone(
        url="https://github.com/user/repo.git",
        workspace_id=workspace_id,
        options=CloneOptions(
            depth=1,
            single_branch=True,
            branch="main",
        ),
    )

# 3. 复用工作空间
class WorkspacePool:
    def __init__(self, max_size=10):
        self.pool = asyncio.Queue(max_size)
        self.used = set()
    
    async def acquire(self, url):
        # 尝试从池中获取
        try:
            workspace_id = self.pool.get_nowait()
            if await self.facade.is_valid(workspace_id):
                return workspace_id
        except asyncio.QueueEmpty:
            pass
        
        # 创建新的
        workspace_id = uuid4()
        await self.facade.clone(url, workspace_id)
        return workspace_id
    
    async def release(self, workspace_id):
        if self.used_count < self.max_size:
            await self.pool.put(workspace_id)
        else:
            await self.facade.cleanup(workspace_id)
```

---

### 安全管理凭证

```python
# ✅ 凭证安全最佳实践

from mcp_git.utils.credential import CredentialHelper
import os

class SecureCredentialManager:
    def __init__(self):
        self.helper = CredentialHelper()
    
    async def get_github_token(self):
        # 优先使用环境变量
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token
        
        # 尝试从 SSH 代理获取
        creds = await self.helper.load_ssh_agent_creds()
        for key in creds:
            if "github" in key.host:
                return key.private_key
        
        raise ValueError("未找到有效的 GitHub 凭证")

# ❌ 永远不要这样做
BAD_EXAMPLE_TOKEN = "ghp_your_actual_token_here"  # 绝不在代码中硬编码！

# ✅ 正确做法
async def clone_with_credentials():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("请设置 GITHUB_TOKEN 环境变量")
    
    url = f"https://x-access-token:{token}@github.com/user/repo.git"
    await facade.clone(url=url, workspace_id=workspace_id)
```

---

### 资源清理

```python
# ✅ 资源清理最佳实践

class GitOperationContext:
    def __init__(self):
        self.facade = GitServiceFacade()
        self.workspaces = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 确保所有工作空间被清理
        for ws_id in self.workspaces:
            try:
                await self.facade.cleanup(workspace_id=ws_id)
            except Exception:
                pass  # 忽略清理错误
    
    async def clone(self, url: str):
        workspace_id = uuid4()
        self.workspaces.append(workspace_id)
        return await self.facade.clone(url=url, workspace_id=workspace_id)

# 使用上下文管理器
async def example():
    async with GitOperationContext() as manager:
        await manager.clone("https://github.com/user/repo1.git")
        await manager.clone("https://github.com/user/repo2.git")
        # 退出时自动清理所有工作空间
```

---

## 故障排除

<div align="center">

### 🔧 常见问题

</div>

### 克隆问题

**问题：克隆超时**

```python
# 解决方案：使用浅克隆减少数据传输
await facade.clone(
    url="https://github.com/user/large-repo.git",
    workspace_id=workspace_id,
    options=CloneOptions(depth=1),
)
```

**问题：认证失败**

```python
# 解决方案：检查并更新凭证
from mcp_git.utils.credential import CredentialHelper

helper = CredentialHelper()
await helper.load_ssh_agent_creds()

# 或使用环境变量
import os
os.environ["GITHUB_TOKEN"] = "your-token"
```

**问题：仓库不存在**

```python
# 解决方案：检查 URL 拼写
url = "https://github.com/user/repo.git"  # 确认 URL 正确

# 验证仓库存在
import httpx
response = httpx.head(url)
if response.status_code != 200:
    print(f"仓库可能不存在: {url}")
```

---

### 性能问题

**问题：操作缓慢**

```python
# 诊断步骤
import psutil

# 1. 检查系统资源
print(f"CPU 使用率: {psutil.cpu_percent()}")
print(f"内存使用率: {psutil.virtual_memory().percent}")

# 2. 检查磁盘空间
import shutil
print(f"磁盘空间: {shutil.disk_usage('/').free / (1024**3):.2f} GB")

# 3. 检查网络连接
import socket
socket.create_connection(("github.com", 443), timeout=5)
print("网络连接正常")
```

---

### 工作空间问题

**问题：工作空间耗尽**

```python
# 解决方案：增加工作空间限制或启用自动清理
from mcp_git.config import WorkspaceConfig

config = WorkspaceConfig(
    max_workspaces=100,  # 增加限制
    cleanup_strategy="lru",  # 使用 LRU 策略
    auto_cleanup=True,  # 启用自动清理
)
```

**问题：工作空间被意外删除**

```python
# 解决方案：检查并重新创建
from mcp_git.service.workspace import WorkspaceManager

manager = WorkspaceManager()

if not await manager.exists(workspace_id):
    await manager.create(workspace_id)
    await facade.clone(url, workspace_id)
```

---

### 寻求帮助

如果以上方法都不能解决您的问题，请通过以下渠道寻求帮助：

| 渠道 | 链接 | 用途 |
|------|------|------|
| GitHub Issues | [提交问题](../../issues/new) | Bug 报告和功能请求 |
| GitHub Discussions | [开始讨论](../../discussions) | 问答和想法 |
| Discord | [加入服务器](https://discord.gg/mcp) | 实时聊天 |
| 邮件 | 查看 README | 安全问题报告 |

**提交问题时请包含：**

- 错误信息完整截图或文本
- 复现步骤
- 环境信息（操作系统、Python 版本、mcp-git 版本）
- 相关代码片段

---

<div align="center">

### 📚 继续探索

</div>

<table>
<tr>
<td width="33%" align="center">

**🔧 API 参考**

[查看详细 API 文档](API_REFERENCE.md)

函数签名和使用示例

</td>
<td width="33%" align="center">

**❓ 常见问题**

[查看 FAQ](FAQ.md)

更多问题解答

</td>
<td width="33%" align="center">

**🔧 故障排除**

[查看故障排除指南](TROUBLESHOOTING.md)

问题解决方案

</td>
</tr>
</table>

---

<div align="center">

**[🏠 首页](../README.md)** • **[🔧 API 参考](API_REFERENCE.md)** • **[❓ FAQ](FAQ.md)**

由 Anthropic 制作

[⬆ 返回顶部](#-用户指南)
