# 错误码参考文档

本文档描述了 mcp-git 中所有可能的错误码、错误含义、原因分析及解决方案。

## 错误码概览

| 错误码 | 名称 | 类别 | 严重程度 |
|--------|------|------|----------|
| 40001-40099 | 参数验证错误 | PARAMETER_VALIDATION | 🟡 中等 |
| 40100-40199 | Git 操作错误 | GIT_OPERATION | 🟡 中等 |
| 40200-40299 | 仓库访问错误 | REPOSITORY_ACCESS | 🔴 高 |
| 40300-40399 | 网络错误 | NETWORK | 🟡 中等 |
| 40400-40499 | 系统错误 | SYSTEM | 🔴 高 |
| 40500-40599 | 任务执行错误 | TASK_EXECUTION | 🟡 中等 |

---

## 参数验证错误 (40001-40099)

### 40001 - INVALID_REPO_PATH

**含义**: 无效的仓库路径

**原因**: 提供的仓库路径不存在或格式不正确

**示例响应**:
```json
{
  "error": {
    "code": 40001,
    "message": "Invalid repository path: /nonexistent/path",
    "details": "Path does not exist",
    "suggestion": "Verify the path exists and is accessible"
  }
}
```

**解决方案**:
- 检查路径是否正确
- 确认路径具有读/写权限
- 使用绝对路径

---

### 40002 - INVALID_REMOTE_URL

**含义**: 无效的远程仓库 URL

**原因**: 提供的 URL 格式不正确或无法解析

**示例响应**:
```json
{
  "error": {
    "code": 40002,
    "message": "Invalid remote URL: not-a-url",
    "details": "URL must start with https://, git@, or file://",
    "suggestion": "Use a valid Git URL format"
  }
}
```

**解决方案**:
- 使用正确的 URL 格式 (https://github.com/user/repo.git 或 git@github.com:user/repo.git)
- 检查 URL 是否包含特殊字符需要编码

---

### 40003 - INVALID_BRANCH_NAME

**含义**: 无效的分支名称

**原因**: 分支名称格式不正确

**示例响应**:
```json
{
  "error": {
    "code": 40003,
    "message": "Invalid branch name: feature/../../../etc/passwd",
    "details": "Branch name contains path traversal characters",
    "suggestion": "Use a valid branch name without special characters"
  }
}
```

**解决方案**:
- 分支名称不能包含 `..`, `/`, 空格等特殊字符
- 遵循 Git 分支命名规范

---

### 40004 - INVALID_COMMIT_MESSAGE

**含义**: 无效的提交消息

**原因**: 提交消息为空或格式不正确

**解决方案**:
- 提供非空的提交消息
- 提交消息建议遵循Conventional Commits格式

---

### 40005 - INVALID_TIMEOUT

**含义**: 无效的超时值

**原因**: 超时值必须是正整数

---

### 40006 - INVALID_TARGET_PATH

**含义**: 无效的目标路径

**原因**: 目标路径不在工作区内或格式不正确

---

### 40007 - MISSING_REQUIRED_PARAM

**含义**: 缺少必需参数

**原因**: 必填参数未提供

**示例响应**:
```json
{
  "error": {
    "code": 40007,
    "message": "Missing required parameter: workspace_id",
    "details": "workspace_id is required for this operation",
    "suggestion": "Provide the required parameter"
  }
}
```

---

### 40008 - PARAMETER_CONFLICT

**含义**: 参数冲突

**原因**: 提供的参数组合不合法

---

## Git 操作错误 (40100-40199)

### 40100 - GIT_COMMAND_FAILED

**含义**: Git 命令执行失败

**原因**: Git 操作返回非零退出码

**示例响应**:
```json
{
  "error": {
    "code": 40100,
    "message": "Git command failed: git commit",
    "details": "fatal: nothing to commit, working tree clean",
    "suggestion": "Make some changes before committing"
  }
}
```

**解决方案**:
- 查看详细信息了解具体错误
- 检查是否有未暂存的更改

---

### 40101 - GIT_NOT_A_REPO

**含义**: 目录不是 Git 仓库

**原因**: 指定的路径不是有效的 Git 仓库

**解决方案**:
- 使用 `git_init` 初始化仓库
- 或检查路径是否正确

---

### 40102 - GIT_NO_CHANGES

**含义**: 没有可提交的更改

**原因**: 工作区没有更改需要提交

---

### 40103 - GIT_DETACHED_HEAD

**含义**: 处于分离头状态 (detached HEAD)

**原因**: 当前不在任何分支上

**解决方案**:
- 使用 `git_checkout` 切换到分支
- 或创建新分支

---

### 40104 - GIT_MERGE_CONFLICT

**含义**: 合并冲突

**原因**: 合并操作遇到冲突

**示例响应**:
```json
{
  "error": {
    "code": 40104,
    "message": "Merge conflict in files: src/main.py, tests/test.py",
    "details": "Conflicting changes in files that need manual resolution",
    "suggestion": "Resolve conflicts manually, then stage and commit"
  }
}
```

**解决方案**:
1. 查看冲突文件: `git status`, `git diff`
2. 手动解决冲突 (保留需要的更改)
3. 暂存解决后的文件: `git add <files>`
4. 完成提交: `git commit`

---

### 40105 - GIT_REBASE_CONFLICT

**含义**: 变基冲突

**原因**: 变基操作遇到冲突

**解决方案**:
- 使用 `git_rebase --abort` 中止变基
- 或手动解决冲突后使用 `git rebase --continue`

---

### 40106 - GIT_UP_TO_DATE

**含义**: 已经是最新状态

**原因**: 远程分支没有新提交,无需更新

---

### 40107 - GIT_PUSH_REJECTED

**含义**: 推送被拒绝

**原因**: 远程分支有新的提交,需要先拉取

**示例响应**:
```json
{
  "error": {
    "code": 40107,
    "message": "Push rejected: remote has new changes",
    "details": "Updates were rejected because the remote contains work that you do not have locally",
    "suggestion": "Pull the remote changes first (git_pull), then push again"
  }
}
```

**解决方案**:
- 先执行 `git_pull` 拉取远程更改
- 或使用 `force: true` 强制推送 (会覆盖远程历史)

---

## 仓库访问错误 (40200-40299)

### 40200 - REPO_ACCESS_DENIED

**含义**: 仓库访问被拒绝

**原因**: 没有权限访问仓库

**示例响应**:
```json
{
  "error": {
    "code": 40200,
    "message": "Access denied to repository: https://github.com/private/repo.git",
    "details": "Authentication failed or insufficient permissions",
    "suggestion": "Check your credentials and ensure you have access to the repository"
  }
}
```

**解决方案**:
- 检查 Git Token 是否正确设置
- 确认 Token 具有访问该仓库的权限
- 对于私有仓库,确保使用正确的认证方式

---

### 40201 - REPO_NOT_FOUND

**含义**: 仓库不存在

**原因**: 指定的仓库 URL 不存在或不可访问

**示例响应**:
```json
{
  "error": {
    "code": 40201,
    "message": "Repository not found: https://github.com/user/nonexistent.git",
    "details": "The repository may have been deleted or renamed",
    "suggestion": "Verify the repository URL is correct"
  }
}
```

**解决方案**:
- 检查 URL 是否正确
- 确认仓库确实存在
- 检查网络连接

---

### 40202 - REPO_LOCKED

**含义**: 仓库被锁定

**原因**: 仓库正在被其他操作锁定

---

## 网络错误 (40300-40399)

### 40300 - NETWORK_ERROR

**含义**: 网络错误

**原因**: 网络连接失败

**示例响应**:
```json
{
  "error": {
    "code": 40300,
    "message": "Network error occurred",
    "details": "Connection timeout after 30 seconds",
    "suggestion": "Check your network connection and try again"
  }
}
```

**解决方案**:
- 检查网络连接
- 稍后重试
- 检查防火墙设置

---

### 40301 - TIMEOUT

**含义**: 操作超时

**原因**: 操作在规定时间内未完成

**示例响应**:
```json
{
  "error": {
    "code": 40301,
    "message": "Operation timed out after 300 seconds",
    "details": "Clone operation did not complete within the timeout period",
    "suggestion": "Try again with a shorter clone depth or increase timeout"
  }
}
```

**解决方案**:
- 使用浅克隆 (`depth: 1`) 减少数据传输
- 增加 `MCP_GIT_TASK_TIMEOUT` 配置
- 检查网络速度

---

### 40302 - AUTH_FAILED

**含义**: 认证失败

**原因**: 提供的凭证无效

**解决方案**:
- 检查 `GIT_TOKEN` 是否正确
- 确认 Token 未过期
- 检查 SSH 密钥配置

---

## 系统错误 (40400-40499)

### 40400 - SYSTEM_ERROR

**含义**: 系统错误

**原因**: 发生未知系统错误

---

### 40401 - PERMISSION_DENIED

**含义**: 权限被拒绝

**原因**: 没有执行操作的权限

**解决方案**:
- 检查文件/目录权限
- 确认工作区路径可写

---

### 40402 - RESOURCE_EXHAUSTED

**含义**: 资源耗尽

**原因**: 磁盘空间不足或其他资源限制

**示例响应**:
```json
{
  "error": {
    "code": 40402,
    "message": "Resource exhausted: disk space low",
    "details": "Available disk space is less than 1GB",
    "suggestion": "Clean up workspace directory or increase disk space"
  }
}
```

**解决方案**:
- 清理工作区: 释放不使用的 workspace
- 清理磁盘空间
- 增加 `MCP_GIT_MAX_WORKSPACE_SIZE` 配置

---

## 任务执行错误 (40500-40599)

### 40501 - TASK_NOT_FOUND

**含义**: 任务不存在

**原因**: 提供的任务 ID 无效或已过期

**示例响应**:
```json
{
  "error": {
    "code": 40501,
    "message": "Task not found: 550e8400-e29b-41d4-a716-446655440000",
    "details": "Task may have expired or ID is incorrect",
    "suggestion": "Verify the task_id is correct"
  }
}
```

**解决方案**:
- 检查任务 ID 是否正确
- 确认任务未过期 (默认1小时后清理)

---

### 40502 - TASK_CANCELLED

**含义**: 任务已取消

**原因**: 任务被手动取消

---

### 40503 - TASK_TIMEOUT

**含义**: 任务超时

**原因**: 任务执行时间超过配置的超时时间

**解决方案**:
- 增加 `MCP_GIT_TASK_TIMEOUT` 配置
- 对于大型仓库,使用浅克隆

---

### 40504 - TASK_EXECUTOR_ERROR

**含义**: 任务执行器错误

**原因**: 任务执行过程中发生内部错误

---

## 可重试错误

以下错误可以安全地重试:

| 错误码 | 名称 |
|--------|------|
| 40300 | NETWORK_ERROR |
| 40301 | TIMEOUT |
| 40302 | AUTH_FAILED |
| 40107 | GIT_PUSH_REJECTED |

使用 `is_retryable_error()` 函数可以检查错误是否可重试。

---

## 错误处理最佳实践

### 1. 捕获特定错误

```python
from mcp_git.error import (
    McpGitError,
    RepositoryNotFoundError,
    AuthenticationError,
    MergeConflictError,
)

try:
    await git_clone(...)
except RepositoryNotFoundError as e:
    print(f"Repository not found: {e.context.repo_path}")
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
except MergeConflictError as e:
    print(f"Conflicted files: {e.details}")
except McpGitError as e:
    print(f"Git error: {e.message}")
```

### 2. 检查是否可重试

```python
from mcp_git.error import is_retryable_error, McpGitError

try:
    await git_clone(...)
except McpGitError as e:
    if is_retryable_error(e):
        print("Can retry this operation")
    else:
        print("Cannot retry, fix the issue first")
```

### 3. 获取用户友好消息

```python
from mcp_git.error import get_user_friendly_message

try:
    await git_clone(...)
except McpGitError as e:
    print(get_user_friendly_message(e))
```

---

## 联系与支持

如果遇到文档未覆盖的错误,请:

1. 检查 [API 文档](API.md) 中的工具说明
2. 查看 [配置文档](configuration.md) 确保配置正确
3. 在 GitHub Issues 中搜索类似问题
4. 创建新的 Issue 报告错误
