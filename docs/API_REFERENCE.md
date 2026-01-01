<div align="center">

# 📘 API 参考文档

### 完整的 API 文档

[🏠 首页](../README.md) • [📖 用户指南](USER_GUIDE.md) • [🏗️ 架构设计](ARCHITECTURE.md)

---

</div>

## 📋 目录

- [概述](#概述)
- [核心 API](#核心-api)
  - [工作空间管理](#工作空间管理)
  - [仓库操作](#仓库操作)
  - [分支操作](#分支操作)
  - [提交操作](#提交操作)
- [错误处理](#错误处理)
- [类型定义](#类型定义)
- [示例](#示例)

---

## 概述

<div align="center">

### 🎯 API 设计原则

</div>

<table>
<tr>
<td width="25%" align="center">
<img src="https://img.icons8.com/fluency/96/000000/easy.png" width="64"><br>
<b>简单</b><br>
直观易用
</td>
<td width="25%" align="center">
<img src="https://img.icons8.com/fluency/96/000000/security-checked.png" width="64"><br>
<b>安全</b><br>
默认安全配置
</td>
<td width="25%" align="center">
<img src="https://img.icons8.com/fluency/96/000000/module.png" width="64"><br>
<b>可组合</b><br>
轻松构建复杂工作流
</td>
<td width="25%" align="center">
<img src="https://img.icons8.com/fluency/96/000000/documentation.png" width="64"><br>
<b>文档完善</b><br>
全面的文档支持
</td>
</tr>
</table>

**mcp-git** 是一个基于 Python 的 Git 操作 MCP（Model Context Protocol）服务器，提供通过 MCP 协议与 Git 仓库交互的能力。

---

## 核心 API

### 工作空间管理

<div align="center">

#### 🚀 工作空间管理工具

</div>

---

#### `create_workspace`

创建新的工作空间用于存放仓库。

<table>
<tr>
<td width="30%"><b>签名</b></td>
<td width="70%">

```json
{
    "name": "git_create_workspace",
    "description": "Create a new workspace for repository operations.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace identifier"
            }
        },
        "required": ["workspace_id"]
    }
}
```

</td>
</tr>
<tr>
<td><b>描述</b></td>
<td>创建新的工作空间，用于后续的仓库操作。工作空间是隔离的目录环境，用于管理 Git 仓库。</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `workspace_id: string` - 工作空间唯一标识符

</td>
</tr>
<tr>
<td><b>返回</b></td>
<td><code>dict</code> - 创建结果信息</td>
</tr>
</table>

**示例:**

```json
{
    "tool": "git_create_workspace",
    "arguments": {
        "workspace_id": "project-alpha"
    }
}
```

---

#### `delete_workspace`

删除工作空间及其所有内容。

<table>
<tr>
<td width="30%"><b>签名</b></td>
<td width="70%">

```json
{
    "name": "git_delete_workspace",
    "description": "Delete a workspace and all its contents.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace identifier"
            },
            "force": {
                "type": "boolean",
                "description": "Force deletion even if repo has uncommitted changes"
            }
        },
        "required": ["workspace_id"]
    }
}
```

</td>
</tr>
<tr>
<td><b>描述</b></td>
<td>删除指定的工作空间及其中的所有内容，包括仓库文件和工作目录。</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `workspace_id: string` - 工作空间标识符
- `force: boolean` - 是否强制删除（即使有未提交的更改）

</td>
</tr>
<tr>
<td><b>错误</b></td>
<td>

- `ValueError` - 工作空间不存在
- `RuntimeError` - 无法删除工作空间

</td>
</tr>
</table>

---

### 仓库操作

<div align="center">

#### 📦 仓库克隆与管理

</div>

---

#### `clone`

克隆 Git 仓库到工作空间。

<table>
<tr>
<td width="30%"><b>签名</b></td>
<td width="70%">

```json
{
    "name": "git_clone",
    "description": "Clone a Git repository into a workspace. Supports shallow clones with depth limit and branch selection.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Repository URL (HTTPS or SSH)"
            },
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID"
            },
            "branch": {
                "type": "string",
                "description": "Optional branch to clone"
            },
            "depth": {
                "type": "integer",
                "description": "Shallow clone depth (faster for large repos)"
            }
        },
        "required": ["url", "workspace_id"]
    }
}
```

</td>
</tr>
<tr>
<td><b>描述</b></td>
<td>将 Git 仓库克隆到指定工作空间。支持浅克隆和分支选择，适用于大型仓库的快速克隆。</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `url: string` - 仓库 URL（支持 HTTPS 或 SSH）
- `workspace_id: string` - 工作空间标识符
- `branch: string` - 可选的克隆分支
- `depth: integer` - 浅克隆深度（用于加速大型仓库克隆）

</td>
</tr>
<tr>
<td><b>返回</b></td>
<td><code>dict</code> - 包含提交信息的字典：oid, message, author_name, author_email, commit_time</td>
</tr>
<tr>
<td><b>错误</b></td>
<td>

- `ValueError` - 无效的 URL 或工作空间不存在
- `RuntimeError` - 克隆操作失败

</td>
</tr>
</table>

**示例:**

```json
{
    "tool": "git_clone",
    "arguments": {
        "url": "https://github.com/example/repo.git",
        "workspace_id": "project-alpha",
        "branch": "main",
        "depth": 1
    }
}
```

---

#### `checkout`

检出特定分支或提交。

<table>
<tr>
<td width="30%"><b>签名</b></td>
<td width="70%">

```json
{
    "name": "git_checkout",
    "description": "Checkout a specific branch or commit in a repository.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID"
            },
            "branch": {
                "type": "string",
                "description": "Branch or commit SHA to checkout"
            },
            "create_branch": {
                "type": "boolean",
                "description": "Create new branch if it doesn't exist"
            }
        },
        "required": ["workspace_id", "branch"]
    }
}
```

</td>
</tr>
<tr>
<td><b>描述</b></td>
<td>在仓库中检出指定的分支或提交。可以选择创建新分支（如果不存在）。</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `workspace_id: string` - 工作空间标识符
- `branch: string` - 要检出的分支名或提交 SHA
- `create_branch: boolean` - 是否在不存在时创建新分支

</td>
</tr>
</table>

---

### 分支操作

<div align="center">

#### 🔀 分支管理操作

</div>

---

#### `branch`

列出仓库中的所有分支。

<table>
<tr>
<td width="30%"><b>签名</b></td>
<td width="70%">

```json
{
    "name": "git_branch",
    "description": "List all branches in a repository.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID"
            },
            "remotes": {
                "type": "boolean",
                "description": "Include remote branches"
            }
        },
        "required": ["workspace_id"]
    }
}
```

</td>
</tr>
<tr>
<td><b>描述</b></td>
<td>列出仓库中的所有本地分支，可选择包含远程分支。</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `workspace_id: string` - 工作空间标识符
- `remotes: boolean` - 是否包含远程分支

</td>
</tr>
<tr>
<td><b>返回</b></td>
<td><code>dict</code> - 分支列表信息</td>
</tr>
</table>

---

#### `push`

推送本地更改到远程仓库。

<table>
<tr>
<td width="30%"><b>签名</b></td>
<td width="70%">

```json
{
    "name": "git_push",
    "description": "Push local changes to remote repository.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID"
            },
            "remote": {
                "type": "string",
                "description": "Remote name (default: origin)"
            },
            "branch": {
                "type": "string",
                "description": "Branch to push"
            }
        },
        "required": ["workspace_id"]
    }
}
```

</td>
</tr>
<tr>
<td><b>描述</b></td>
<td>将本地分支的更改推送到远程仓库。</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `workspace_id: string` - 工作空间标识符
- `remote: string` - 远程仓库名称（默认：origin）
- `branch: string` - 要推送的分支

</td>
</tr>
<tr>
<td><b>错误</b></td>
<td>

- `RuntimeError` - 推送失败

</td>
</tr>
</table>

---

#### `pull`

从远程仓库拉取更改。

<table>
<tr>
<td width="30%"><b>签名</b></td>
<td width="70%">

```json
{
    "name": "git_pull",
    "description": "Pull changes from remote repository.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID"
            },
            "remote": {
                "type": "string",
                "description": "Remote name (default: origin)"
            },
            "branch": {
                "type": "string",
                "description": "Branch to pull"
            }
        },
        "required": ["workspace_id"]
    }
}
```

</td>
</tr>
<tr>
<td><b>描述</b></td>
<td>从远程仓库拉取并合并更改到当前分支。</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `workspace_id: string` - 工作空间标识符
- `remote: string` - 远程仓库名称（默认：origin）
- `branch: string` - 要拉取的分支

</td>
</tr>
</table>

---

### 提交操作

<div align="center">

#### 📝 提交历史与操作

</div>

---

#### `commit`

创建新的提交。

<table>
<tr>
<td width="30%"><b>签名</b></td>
<td width="70%">

```json
{
    "name": "git_commit",
    "description": "Create a new commit with staged changes.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID"
            },
            "message": {
                "type": "string",
                "description": "Commit message"
            },
            "author": {
                "type": "object",
                "description": "Commit author",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"}
                }
            }
        },
        "required": ["workspace_id", "message"]
    }
}
```

</td>
</tr>
<tr>
<td><b>描述</b></td>
<td>使用暂存的更改创建新的提交。</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `workspace_id: string` - 工作空间标识符
- `message: string` - 提交消息
- `author: object` - 提交作者（包含 name 和 email）

</td>
</tr>
<tr>
<td><b>错误</b></td>
<td>

- `RuntimeError` - 提交失败（可能是没有暂存的更改）

</td>
</tr>
</table>

---

#### `log`

显示提交历史。

<table>
<tr>
<td width="30%"><b>签名</b></td>
<td width="70%">

```json
{
    "name": "git_log",
    "description": "Show commit history.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID"
            },
            "max_count": {
                "type": "integer",
                "description": "Maximum number of commits to show"
            },
            "format": {
                "type": "string",
                "description": "Output format"
            }
        },
        "required": ["workspace_id"]
    }
}
```

</td>
</tr>
<tr>
<td><b>描述</b></td>
<td>显示仓库的提交历史记录。</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `workspace_id: string` - 工作空间标识符
- `max_count: integer` - 最大显示提交数
- `format: string` - 输出格式

</td>
</tr>
</table>

---

#### `status`

显示仓库状态。

<table>
<tr>
<td width="30%"><b>签名</b></td>
<td width="70%">

```json
{
    "name": "git_status",
    "description": "Show repository status.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID"
            },
            "short": {
                "type": "boolean",
                "description": "Use short format"
            }
        },
        "required": ["workspace_id"]
    }
}
```

</td>
</tr>
<tr>
<td><b>描述</b></td>
<td>显示工作树的状态，包括已修改、已暂存和未跟踪的文件。</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `workspace_id: string` - 工作空间标识符
- `short: boolean` - 使用简短格式

</td>
</tr>
</table>

---

### 添加与暂存

<div align="center">

#### 📋 文件暂存操作

</div>

---

#### `add`

暂存文件更改。

<table>
<tr>
<td width="30%"><b>签名</b></td>
<td width="70%">

```json
{
    "name": "git_add",
    "description": "Stage file changes.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID"
            },
            "file_pattern": {
                "type": "string",
                "description": "File pattern to stage (e.g., '*' for all)"
            }
        },
        "required": ["workspace_id", "file_pattern"]
    }
}
```

</td>
</tr>
<tr>
<td><b>描述</b></td>
<td>将文件更改添加到暂存区，准备提交。</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `workspace_id: string` - 工作空间标识符
- `file_pattern: string` - 要暂存的文件模式（如 '*' 表示所有文件）

</td>
</tr>
</table>

---

## 错误处理

<div align="center">

#### ⚠️ 错误处理指南

</div>

所有 API 调用都使用标准的异常机制处理错误：

<table>
<tr>
<th>错误类型</th>
<th>描述</th>
<th>处理建议</th>
</tr>
<tr>
<td><code>ValueError</code></td>
<td>参数验证错误</td>
<td>检查并修正输入参数</td>
</tr>
<tr>
<td><code>RuntimeError</code></td>
<td>Git 操作执行失败</td>
<td>检查 Git 仓库状态和权限</td>
</tr>
<tr>
<td><code>FileNotFoundError</code></td>
<td>文件或目录不存在</td>
<td>确认工作空间和路径正确</td>
</tr>
</table>

---

## 类型定义

<div align="center">

#### 📦 核心类型定义

</div>

### 工作空间配置

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

### 清理策略

```python
from enum import Enum

class CleanupStrategy(Enum):
    """工作空间清理策略"""
    LRU = "lru"  # 最近最少使用
    FIFO = "fifo"  # 先进先出
```

---

## 示例

<div align="center">

#### 💡 完整使用示例

</div>

**基本工作流程：**

```python
# 1. 创建工作空间
await workspace_manager.create_workspace("project-alpha")

# 2. 克隆仓库
result = await facade.clone(
    url="https://github.com/example/repo.git",
    workspace_id="project-alpha",
    branch="main"
)
print(f"克隆完成: {result['oid']}")

# 3. 切换分支
await facade.checkout(
    workspace_id="project-alpha",
    branch="develop"
)

# 4. 查看状态
status = await facade.status(workspace_id="project-alpha")

# 5. 提交更改
await facade.add(workspace_id="project-alpha", file_pattern="*")
await facade.commit(
    workspace_id="project-alpha",
    message="更新功能",
    author={"name": "开发者", "email": "dev@example.com"}
)

# 6. 推送更改
await facade.push(
    workspace_id="project-alpha",
    remote="origin",
    branch="develop"
)

# 7. 清理工作空间
await workspace_manager.delete_workspace("project-alpha")
```

---

<div align="center">

### 📚 相关文档

- [🏠 首页](../README.md)
- [📖 用户指南](USER_GUIDE.md)
- [🏗️ 架构设计](ARCHITECTURE.md)
- [🤝 贡献指南](CONTRIBUTING.md)

</div>
