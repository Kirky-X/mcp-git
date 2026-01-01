<div align="center">

# 🏗️ 架构设计

### 系统架构说明文档

[🏠 首页](../README.md) • [📖 用户指南](USER_GUIDE.md) • [📘 API 参考](API_REFERENCE.md) • [🤝 贡献指南](CONTRIBUTING.md)

---

</div>

## 目录

- [概述](#概述)
- [整体架构](#整体架构)
- [分层设计](#分层设计)
  - [MCP 协议层](#mcp-协议层)
  - [业务逻辑层](#业务逻辑层)
  - [执行层](#执行层)
  - [Git 操作层](#git-操作层)
  - [存储层](#存储层)
- [核心组件](#核心组件)
- [数据流](#数据流)
- [安全设计](#安全设计)
- [扩展性设计](#扩展性设计)

---

## 概述

<div align="center">

### 🎯 设计目标

</div>

**mcp-git** 是一个基于 Python 的 Git 操作 MCP（Model Context Protocol）服务器，其架构设计遵循以下原则：

<table>
<tr>
<td width="25%" align="center">
<img src="https://img.icons8.com/fluency/96/000000/layers.png" width="64"><br>
<b>分层架构</b><br>
清晰的分层设计
</td>
<td width="25%" align="center">
<img src="https://img.icons8.com/fluency/96/000000/handshake.png" width="64"><br>
<b>协议适配</b><br>
MCP 协议标准兼容
</td>
<td width="25%" align="center">
<img src="https://img.icons8.com/fluency/96/000000/circuit.png" width="64"><br>
<b>异步执行</b><br>
高效的异步处理
</td>
<td width="25%" align="center">
<img src="https://img.icons8.com/fluency/96/000000/ shield.png" width="64"><br>
<b>安全优先</b><br>
默认安全配置
</td>
</tr>
</table>

---

## 整体架构

<div align="center">

### 🏗️ 系统架构图

</div>

```
┌─────────────────────────────────────────────────────────────────┐
│                      MCP 客户端 (Claude, AI 应用等)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       MCP 协议层 (mcp_git/server)                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Server.py / main.py                     │  │
│  │              MCP 协议处理、工具注册、请求路由                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    业务逻辑层 (mcp_git/service)                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      Facade.py                             │  │
│  │              统一服务接口、任务编排、业务流程                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      执行层 (mcp_git/executor)                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              TaskManager: 任务队列、并发控制                 │  │
│  │              WorkerPool: 工作线程池管理                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Git 操作层 (mcp_git/git)                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   GitAdapter: Git 命令封装                  │  │
│  │               Repository: 仓库操作封装                      │  │
│  │                 Branch: 分支操作封装                        │  │
│  │                 Commit: 提交操作封装                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      存储层 (mcp_git/storage)                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              WorkspaceManager: 工作空间管理                 │  │
│  │              CredentialManager: 凭证管理                    │  │
│  │                    Config: 配置管理                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 分层设计

### MCP 协议层

<div align="center">

#### �� MCP 协议处理

</div>

**位置:** `mcp_git/server/`

**职责:**

- MCP 协议消息的解析和生成
- 工具（Tool）定义的注册和管理
- 请求路由和响应处理
- 与 MCP 客户端的通信管理

**核心组件:**

<table>
<tr>
<th>组件</th>
<th>职责</th>
</tr>
<tr>
<td><code>Server</code></td>
<td>MCP 服务器核心，处理协议握手、请求路由</td>
</tr>
<tr>
<td><code>tools.py</code></td>
<td>定义所有可用的 Git 操作工具</td>
</tr>
<tr>
<td><code>main.py</code></td>
<td>服务器入口点，负责初始化和启动</td>
</tr>
</table>

**工具定义示例:**

```python
from mcp.server import Server
from mcp.types import Tool

server = Server("mcp-git")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="git_clone",
            description="Clone a Git repository into a workspace.",
            inputSchema={...}
        ),
        # ... 其他工具
    ]
```

---

### 业务逻辑层

<div align="center">

#### 🎯 业务服务编排

</div>

**位置:** `mcp_git/service/`

**职责:**

- 提供统一的 Git 操作服务接口
- 协调各组件完成复杂业务流程
- 参数验证和错误处理
- 进度跟踪和回调

**核心组件:**

<table>
<tr>
<th>组件</th>
<th>职责</th>
</tr>
<tr>
<td><code>Facade</code></td>
<td>统一的门面类，封装所有 Git 操作</td>
</tr>
<tr>
<td><code>WorkspaceManager</code></td>
<td>工作空间的创建、删除、大小管理</td>
</tr>
<tr>
<td><code>CredentialManager</code></td>
<td>Git 凭证的安全管理</td>
</tr>
</table>

**Facade 服务接口:**

```python
class GitServiceFacade:
    """Git 操作统一服务门面"""

    async def clone(
        self,
        url: str,
        workspace_id: UUID,
        options: CloneOptions | None = None,
        progress_callback: TransferProgressCallback | None = None,
    ) -> dict[str, Any]:
        """克隆仓库到工作空间"""

    async def checkout(
        self,
        workspace_id: UUID,
        branch: str,
        create_branch: bool = False,
    ) -> dict[str, Any]:
        """切换分支或检出提交"""

    async def commit(
        self,
        workspace_id: UUID,
        message: str,
        author: Author | None = None,
    ) -> dict[str, Any]:
        """创建提交"""
```

---

### 执行层

<div align="center">

#### ⚡ 任务执行引擎

</div>

**位置:** `mcp_git/executor/`

**职责:**

- 任务队列管理
- 并发控制
- 工作线程池管理
- 任务优先级处理

**核心组件:**

<table>
<tr>
<th>组件</th>
<th>职责</th>
</tr>
<tr>
<td><code>TaskManager</code></td>
<td>任务队列管理、并发限制</td>
</tr>
<tr>
<td><code>WorkerPool</code></td>
<td>工作线程池管理</td>
</tr>
</table>

**设计特点:**

- 异步任务执行，提高吞吐量
- 可配置的并发限制，防止资源耗尽
- 任务优先级支持
- 优雅的关闭机制

```python
class TaskManager:
    """任务管理器"""

    def __init__(
        self,
        max_concurrent_tasks: int = DEFAULT_MAX_CONCURRENT_TASKS,
        max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE,
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_queue_size = max_queue_size
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
```

---

### Git 操作层

<div align="center">

#### 🔧 Git 命令封装

</div>

**位置:** `mcp_git/git/`

**职责:**

- 封装 Git 命令行操作
- 提供高级别的仓库操作接口
- 处理 Git 命令执行和错误
- 支持进度回调

**核心组件:**

<table>
<tr>
<th>组件</th>
<th>职责</th>
</tr>
<tr>
<td><code>GitAdapter</code></td>
<td>Git 命令适配器，底层执行</td>
</tr>
<tr>
<td><code>Repository</code></td>
<td>仓库级操作（克隆、初始化）</td>
</tr>
<tr>
<td><code>Branch</code></td>
<td>分支操作（列出、创建、删除）</td>
</tr>
<tr>
<td><code>Commit</code></td>
<td>提交操作（提交、查看历史）</td>
</tr>
</table>

**Git 操作封装示例:**

```python
class GitAdapter:
    """Git 命令适配器"""

    async def clone(
        self,
        url: str,
        path: Path,
        options: CloneOptions | None = None,
        progress_callback: TransferProgressCallback | None = None,
    ) -> CommitInfo:
        """执行 git clone 命令"""

    async def checkout(
        self,
        repo_path: Path,
        branch: str,
        create_branch: bool = False,
    ) -> None:
        """执行 git checkout 命令"""
```

---

### 存储层

<div align="center">

#### 💾 数据持久化

</div>

**位置:** `mcp_git/storage/`

**职责:**

- 工作空间元数据管理
- 配置持久化
- 凭证安全存储
- 缓存管理

**核心组件:**

<table>
<tr>
<th>组件</th>
<th>职责</th>
</tr>
<tr>
<td><code>WorkspaceManager</code></td>
<td>工作空间的生命周期管理</td>
</tr>
<tr>
<td><code>CredentialManager</code></td>
<td>凭证的安全存储和检索</td>
</tr>
<tr>
<td><code>Config</code></td>
<td>应用配置管理</td>
</tr>
</table>

**工作空间管理:**

```python
class WorkspaceManager:
    """工作空间管理器"""

    async def create_workspace(self, workspace_id: str) -> Workspace:
        """创建新的工作空间"""

    async def delete_workspace(self, workspace_id: str) -> None:
        """删除工作空间"""

    async def get_workspace(self, workspace_id: str) -> Workspace | None:
        """获取工作空间信息"""

    async def cleanup_expired_workspaces(self) -> int:
        """清理过期的工作空间"""
```

---

## 核心组件

<div align="center">

#### 🧩 组件关系图

</div>

```
                    ┌─────────────────┐
                    │   MCP Server    │
                    │  (协议层入口)    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  GitService     │
                    │     Facade      │
                    │  (业务逻辑层)    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │   GitAdapter │ │WorkspaceMgr  │ │CredentialMgr │
    │  (Git操作)   │ │ (工作空间)   │ │  (凭证管理)  │
    └──────────────┘ └──────────────┘ └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  TaskManager    │
                    │  (任务调度)     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  WorkerPool     │
                    │  (线程池)       │
                    └─────────────────┘
```

---

## 数据流

<div align="center">

#### 📊 数据流转图

</div>

### 典型操作流程

**克隆仓库流程:**

```
1. MCP 客户端发送 clone 请求
2. MCP 协议层解析请求参数
3. Facade 验证参数和工作空间
4. TaskManager 获取执行令牌
5. GitAdapter 执行 git clone
6. WorkspaceManager 更新工作空间
7. 返回克隆结果（commit info）
8. 释放执行令牌
```

---

## 安全设计

<div align="center">

#### 🔒 安全架构

</div>

### 凭证管理

<div align="center">

#### 🔑 凭证安全

</div>

**凭证存储:**

- 使用系统密钥环（Keyring）安全存储
- 支持多种后端：Windows 凭据管理器、macOS 钥匙串、Linux SecretService
- 凭证加密存储，内存中解密使用

```python
class CredentialManager:
    """凭证管理器"""

    async def get_credential(self, workspace_id: str) -> GitCredential | None:
        """安全获取凭证"""

    async def store_credential(
        self,
        workspace_id: str,
        credential: GitCredential,
    ) -> None:
        """安全存储凭证"""
```

### 输入验证

<div align="center">

#### ✅ 输入验证

</div>

- 所有输入参数使用 Pydantic 模型验证
- 远程 URL 消毒处理，防止注入攻击
- 路径验证，防止路径遍历攻击
- 命令参数转义，防止命令注入

```python
def sanitize_remote_url(url: str) -> str:
    """消毒远程 URL"""
    # 验证 URL 格式
    # 移除危险字符
    # 返回安全的 URL
```

---

## 扩展性设计

<div align="center">

#### 🚀 扩展能力

</div>

### 工作空间清理策略

<table>
<tr>
<th>策略</th>
<th>描述</th>
<th>适用场景</th>
</tr>
<tr>
<td><code>LRU</code></td>
<td>最近最少使用</td>
<td>交互式开发，保持活跃项目</td>
</tr>
<tr>
<td><code>FIFO</code></td>
<td>先进先出</td>
<td>批处理任务，公平清理</td>
</tr>
</table>

### 配置扩展

```python
class WorkspaceConfig(BaseModel):
    """工作空间配置"""
    path: Path = Field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "mcp-git" / "workspaces"
    )
    max_size_bytes: int = Field(default=10 * 1024 * 1024 * 1024, gt=0)  # 10GB
    retention_seconds: int = Field(default=3600, gt=0)  # 1小时
    cleanup_strategy: CleanupStrategy = CleanupStrategy.LRU
```

### 新工具扩展

通过注册新的 Tool 实例即可扩展功能：

```python
@server.list_tools()
async def list_tools():
    return [
        # 现有工具...
        Tool(
            name="git_custom_operation",
            description="Custom Git operation",
            inputSchema={...}
        ),
    ]
```

---

<div align="center">

### 📚 相关文档

- [🏠 首页](../README.md)
- [📖 用户指南](USER_GUIDE.md)
- [📘 API 参考](API_REFERENCE.md)
- [🤝 贡献指南](CONTRIBUTING.md)

</div>
