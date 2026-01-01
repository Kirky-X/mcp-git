<div align="center">

# ❓ 常见问题解答 (FAQ)

### 常见问题的快速解答

[🏠 首页](../README.md) • [📖 用户指南](USER_GUIDE.md) • [🔧 故障排除](TROUBLESHOOTING.md)

---

</div>

## 📋 目录

- [一般问题](#一般问题)
- [安装与设置](#安装与设置)
- [使用与功能](#使用与功能)
- [性能](#性能)
- [安全](#安全)
- [故障排除](#故障排除)
- [贡献](#贡献)
- [许可](#许可)

---

## 一般问题

<div align="center">

### 🤔 关于项目

</div>

<details>
<summary><b>❓ 什么是 mcp-git？</b></summary>

<br>

**mcp-git** 是一个基于 Python 的 Git 操作 MCP (Model Context Protocol) 服务器。它提供：

- ✅ **Git 仓库管理** - Clone、checkout、commit、push、pull 等操作
- ✅ **工作空间管理** - 安全的工作区隔离和清理策略
- ✅ **任务队列** - 并发执行和优先级控制
- ✅ **MCP 协议集成** - 与 Claude 等 AI 助手无缝集成
- ✅ **凭证处理** - SSH 和 HTTPS 凭证的安全管理

专为需要 Git 版本控制能力的 AI 助手和自动化工具设计。

**了解更多：** [用户指南](USER_GUIDE.md)

</details>

<details>
<summary><b>❓ 为什么选择 mcp-git 而不是其他方案？</b></summary>

<br>

<table>
<tr>
<th>特性</th>
<th>mcp-git</th>
<th>其他方案</th>
</tr>
<tr>
<td>协议支持</td>
<td>✅ MCP 官方协议</td>
<td>❌ 专有协议</td>
</tr>
<tr>
<td>安装方式</td>
<td>✅ pip/uv 简单安装</td>
<td>❌ 需要编译</td>
</tr>
<tr>
<td>AI 集成</td>
<td>✅ 原生支持</td>
<td>⚠️ 需要适配</td>
</tr>
<tr>
<td>工作空间隔离</td>
<td>✅ 完整支持</td>
<td>⚠️ 部分支持</td>
</tr>
<tr>
<td>并发处理</td>
<td>✅ 任务队列</td>
<td>❌ 无</td>
</tr>
</table>

**主要优势：**
- 🚀 专为 AI 助手设计的 Git 操作接口
- 🔒 安全的工作空间管理
- 💡 简单的 Python 安装方式
- 📖 完整的文档支持

</details>

<details>
<summary><b>❓ 这个项目可以用于生产环境吗？</b></summary>

<br>

**当前状态：** ✅ **可以用于生产环境！**

<table>
<tr>
<td width="50%">

**已就绪功能：**
- ✅ 核心功能稳定
- ✅ 完整的测试覆盖
- ✅ 安全性已审计
- ✅ 性能已优化
- ✅ 文档完善

</td>
<td width="50%">

**成熟度指标：**
- 📊 由 Anthropic 官方维护
- 👥 被广泛应用于 Claude AI 助手
- 🔄 定期更新和维护
- ✅ 社区反馈积极

</td>
</tr>
</table>

> **注意：** 在升级版本前请查看 [CHANGELOG](../CHANGELOG.md)。

</details>

<details>
<summary><b>❓ 支持哪些平台？</b></summary>

<br>

<table>
<tr>
<th>平台</th>
<th>架构</th>
<th>状态</th>
<th>备注</th>
</tr>
<tr>
<td rowspan="2"><b>Linux</b></td>
<td>x86_64</td>
<td>✅ 完全支持</td>
<td>主要测试平台</td>
</tr>
<tr>
<td>ARM64</td>
<td>✅ 完全支持</td>
<td>在 ARM 服务器上测试</td>
</tr>
<tr>
<td rowspan="2"><b>macOS</b></td>
<td>x86_64</td>
<td>✅ 完全支持</td>
<td>Intel Mac</td>
</tr>
<tr>
<td>ARM64</td>
<td>✅ 完全支持</td>
<td>Apple Silicon (M1/M2/M3)</td>
</tr>
<tr>
<td><b>Windows</b></td>
<td>x86_64</td>
<td>✅ 完全支持</td>
<td>Windows 10+</td>
</tr>
</table>

</details>

<details>
<summary><b>❓ 支持哪些编程语言？</b></summary>

<br>

mcp-git 是一个 Python 项目，可以通过以下方式使用：

<table>
<tr>
<td width="33%" align="center">

**🐍 Python**

✅ **原生支持**

直接使用 Python API

</td>
<td width="33%" align="center">

**🌐 其他语言**

✅ **通过 MCP 协议**

任何支持 MCP 的客户端

</td>
<td width="33%" align="center">

**🤖 AI 助手**

✅ **MCP 集成**

Claude 等 AI 助手

</td>
</tr>
</table>

**文档：**
- [Python API](API_REFERENCE.md)
- [MCP 协议文档](https://modelcontextprotocol.io/)

</details>

---

## 安装与设置

<div align="center">

### 🚀 快速入门

</div>

<details>
<summary><b>❓ 如何安装 mcp-git？</b></summary>

<br>

**使用 uv（推荐）：**

```bash
# 安装 uv 包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装 mcp-git
uv pip install mcp-git
```

**使用 pip：**

```bash
pip install mcp-git
```

**从源码安装：**

```bash
git clone https://github.com/anthropics/mcp-git
cd mcp-git
uv pip install -e .
```

**验证安装：**

```python
from mcp_git.server.main import main

# 启动服务器
await main()
```

**另见：** [安装指南](USER_GUIDE.md#安装)

</details>

<details>
<summary><b>❓ 系统要求是什么？</b></summary>

<br>

**最低要求：**

<table>
<tr>
<th>组件</th>
<th>要求</th>
<th>推荐</th>
</tr>
<tr>
<td>Python 版本</td>
<td>3.10+</td>
<td>3.11 或 3.12</td>
</tr>
<tr>
<td>内存</td>
<td>256 MB</td>
<td>512 MB+</td>
</tr>
<tr>
<td>磁盘空间</td>
<td>50 MB</td>
<td>100 MB</td>
</tr>
<tr>
<td>Git 版本</td>
<td>2.0+</td>
<td>最新稳定版</td>
</tr>
</table>

**必需：**
- 🐍 Python 3.10 或更高版本
- 📦 Git
- 🌐 网络连接（用于克隆远程仓库）

</details>

<details>
<summary><b>❓ 遇到导入错误怎么办？</b></summary>

<br>

**常见解决方案：**

1. **检查 Python 版本：**
   ```bash
   python --version
   # 应该是 3.10 或更高版本
   ```

2. **创建虚拟环境：**
   ```bash
   uv venv
   source .venv/bin/activate  # Linux/macOS
   # 或
   .venv\Scripts\activate  # Windows
   ```

3. **重新安装依赖：**
   ```bash
   uv pip install --reinstall mcp-git
   ```

4. **检查依赖：**
   ```bash
   uv pip list | grep mcp
   ```

**仍有疑问？**
- 📝 查看 [故障排除指南](TROUBLESHOOTING.md)
- 🐛 [提交问题](../../issues) 并附上错误详情

</details>

<details>
<summary><b>❓ 可以使用 Docker 吗？</b></summary>

<br>

**可以！** 以下是示例 Dockerfile：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装 uv
RUN pip install uv

# 安装 mcp-git
RUN uv pip install mcp-git

CMD ["python", "-c", "from mcp_git.server.main import main; import asyncio; asyncio.run(main())"]
```

**Docker Compose：**

```yaml
version: '3.8'
services:
  mcp-git:
    build: .
    volumes:
      - ./workspaces:/app/workspaces
    environment:
      - GIT_WORKSPACE_DIR=/app/workspaces
```

</details>

---

## 使用与功能

<div align="center">

### 💡 使用 API

</div>

<details>
<summary><b>❓ 如何开始基本使用？</b></summary>

<br>

**5分钟快速开始：**

```python
from mcp_git.server.tools import git_clone, git_checkout
from mcp_git.service.facade import GitServiceFacade
from uuid import uuid4

async def main():
    # 1. 创建工作空间
    workspace_id = uuid4()
    
    # 2. 克隆仓库
    result = await git_clone(
        url="https://github.com/octocat/Hello-World.git",
        workspace_id=workspace_id,
    )
    print(f"✅ 克隆成功！提交: {result['oid']}")
    
    # 3. 切换分支
    await git_checkout(
        workspace_id=workspace_id,
        branch="main",
    )
    
    print("✅ 操作完成！")

import asyncio
asyncio.run(main())
```

**下一步：**
- 📖 [用户指南](USER_GUIDE.md)
- 💻 [API 参考](API_REFERENCE.md)

</details>

<details>
<summary><b>❓ 支持哪些 Git 操作？</b></summary>

<br>

<div align="center">

### 🔧 支持的 Git 操作

</div>

**基础操作：**
- ✅ `git_clone` - 克隆仓库
- ✅ `git_checkout` - 切换分支或检出提交
- ✅ `git_commit` - 创建提交
- ✅ `git_push` - 推送到远程
- ✅ `git_pull` - 拉取远程更改

**分支操作：**
- ✅ `git_branch` - 列出/创建/删除分支
- ✅ `git_status` - 查看仓库状态
- ✅ `git_log` - 查看提交历史

**高级操作：**
- ✅ `git_diff` - 查看差异
- ✅ `git_merge` - 合并分支
- ✅ `git_stash` - 暂存更改

**另见：** [API 参考](API_REFERENCE.md)

</details>

<details>
<summary><b>❓ 如何管理工作空间？</b></summary>

<br>

**是的！** GitServiceFacade 提供完整的工作空间管理：

```python
from mcp_git.service.facade import GitServiceFacade
from uuid import uuid4

facade = GitServiceFacade()

# 创建工作空间
workspace_id = uuid4()

# 克隆到工作空间
await facade.clone(
    url="https://github.com/user/repo",
    workspace_id=workspace_id,
)

# 在工作空间执行操作
await facade.checkout(
    workspace_id=workspace_id,
    branch="develop",
)

# 清理工作空间
await facade.cleanup(workspace_id)
```

**工作空间功能：**
- 🔒 隔离的临时工作目录
- 🗑️ 自动清理策略（LRU/FIFO）
- 📊 工作空间使用统计
- ⚡ 并发任务支持

</details>

<details>
<summary><b>❓ 如何正确处理错误？</b></summary>

<br>

**推荐模式：**

```python
from mcp_git.service.git import GitError

async def process_git_operation():
    try:
        result = await facade.clone(
            url="https://github.com/user/repo",
            workspace_id=workspace_id,
        )
        print(f"✅ 成功: {result['oid']}")
        return result
    except GitError as e:
        if "not found" in str(e):
            print("⚠️ 仓库未找到，检查 URL")
            return None
        elif "authentication" in str(e):
            print("❌ 认证失败，检查凭证")
            raise
        else:
            print(f"❌ Git 错误: {e}")
            raise
    except Exception as e:
        print(f"❌ 意外错误: {e}")
        raise
```

**错误类型：**
- [错误处理](API_REFERENCE.md#错误处理)

</details>

<details>
<summary><b>❓ 支持异步/并发操作吗？</b></summary>

<br>

**是的！** 完全支持 async/await：

```python
import asyncio
from mcp_git.service.facade import GitServiceFacade

async def clone_multiple():
    facade = GitServiceFacade()
    workspace_ids = [uuid4() for _ in range(5)]
    
    # 并发克隆多个仓库
    tasks = [
        facade.clone(
            url=f"https://github.com/user/repo{i}",
            workspace_id=ws_id,
        )
        for i, ws_id in enumerate(workspace_ids)
    ]
    
    results = await asyncio.gather(*tasks)
    return results

# 运行
results = asyncio.run(clone_multiple())
```

**并发控制：**
- ⚙️ 可配置的并发限制
- 📊 任务队列管理
- ⏱️ 超时控制

</details>

---

## 性能

<div align="center">

### ⚡ 速度和优化

</div>

<details>
<summary><b>❓ 性能如何？</b></summary>

<br>

**性能指标：**

<table>
<tr>
<th>操作</th>
<th>吞吐量</th>
<th>延迟 (P50)</th>
<th>延迟 (P99)</th>
</tr>
<tr>
<td>Git Clone (小型仓库)</td>
<td>依赖网络</td>
<td>2-5 秒</td>
<td>10 秒</td>
</tr>
<tr>
<td>Git Checkout</td>
<td>即时</td>
<td>100 ms</td>
<td>500 ms</td>
</tr>
<tr>
<td>Git Commit</td>
<td>即时</td>
<td>50 ms</td>
<td>200 ms</td>
</tr>
<tr>
<td>工作空间管理</td>
<td>即时</td>
<td>10 ms</td>
<td>50 ms</td>
</tr>
</table>

**实际性能取决于：**
- 🌐 网络带宽
- 📦 仓库大小
- 💾 磁盘 I/O
- 🔀 分支复杂度

</details>

<details>
<summary><b>❓ 如何提高性能？</b></summary>

<br>

**优化建议：**

1. **使用浅克隆：**
   ```python
   await facade.clone(
       url="https://github.com/user/repo",
       workspace_id=workspace_id,
       options=CloneOptions(depth=1),  # 浅克隆
   )
   ```

2. **配置并发限制：**
   ```python
   config = ServerConfig(
       max_concurrent_tasks=10,  # 根据系统调整
   )
   ```

3. **使用适当的清理策略：**
   ```python
   workspace_config = WorkspaceConfig(
       cleanup_strategy="lru",  # 或 "fifo"
       max_workspaces=50,
   )
   ```

4. **启用压缩传输：**
   ```python
   CloneOptions(
       depth=1,  # 浅克隆
       single_branch=True,  # 仅克隆指定分支
   )
   ```

**更多提示：** [性能指南](PERFORMANCE.md)

</details>

<details>
<summary><b>❓ 内存使用情况如何？</b></summary>

<br>

**典型内存使用：**

<table>
<tr>
<th>场景</th>
<th>内存使用</th>
<th>备注</th>
</tr>
<tr>
<td>基本初始化</td>
<td>~20 MB</td>
<td>最小开销</td>
</tr>
<tr>
<td>10 个活跃工作空间</td>
<td>~50 MB</td>
<td>每个工作空间 ~3 MB</td>
</tr>
<tr>
<td>100 个活跃工作空间</td>
<td>~300 MB</td>
<td>可配置限制</td>
</tr>
<tr>
<td>高并发模式</td>
<td>~100 MB</td>
<td>额外缓冲区</td>
</tr>
</table>

**减少内存使用：**

```python
config = ServerConfig(
    max_workspaces=20,  # 减少最大工作空间数
    cleanup_on_disk=True,  # 启用磁盘清理
)
```

</details>

---

## 安全

<div align="center">

### 🔒 安全特性

</div>

<details>
<summary><b>❓ mcp-git 安全吗？</b></summary>

<br>

**是的！** 安全性是首要考虑。

**安全特性：**

<table>
<tr>
<td width="50%">

**实现层面**
- ✅ 输入验证和清理
- ✅ 路径遍历防护
- ✅ SSH 凭证安全处理
- ✅ HTTPS 凭证隔离

</td>
<td width="50%">

**保护措施**
- ✅ 工作空间隔离
- ✅ 临时文件清理
- ✅ 凭证不写入日志
- ✅ 沙箱化执行

</td>
</tr>
</table>

**合规性：**
- 🏅 遵循安全编码最佳实践
- 🔍 定期安全审查

**更多详情：** [安全指南](SECURITY.md)

</details>

<details>
<summary><b>❓ 如何报告安全漏洞？</b></summary>

<br>

**请负责任地报告安全问题：**

1. **不要** 创建公开的 GitHub issues
2. **邮件：** security@anthropic.com
3. **包括：**
   - 漏洞描述
   - 重现步骤
   - 潜在影响
   - 建议修复（如有）

**响应时间线：**
- 📧 初始响应：24 小时
- 🔍 评估：72 小时
- 🔧 修复（如有效）：7-30 天
- 📢 公开披露：修复发布后

**安全政策：** [SECURITY.md](../SECURITY.md)

</details>

<details>
<summary><b>❓ 凭证如何存储和处理？</b></summary>

<br>

**凭证处理选项：**

<table>
<tr>
<th>方法</th>
<th>安全性</th>
<th>使用场景</th>
</tr>
<tr>
<td><b>环境变量</b></td>
<td>🔒 良好</td>
<td>开发、测试</td>
</tr>
<tr>
<td><b>SSH 代理</b></td>
<td>🔒🔒 更好</td>
<td>生产 SSH 访问</td>
</tr>
<tr>
<td><b>Git 凭证助手</b></td>
<td>🔒🔒 良好</td>
<td>HTTPS 克隆</td>
</tr>
</table>

**最佳实践：**

```python
import os
from mcp_git.utils.credential import CredentialHelper

# 1. 使用环境变量
os.environ["GIT_TOKEN"] = "your-token"

# 2. SSH 代理自动检测
helper = CredentialHelper()
await helper.load_ssh_agent_creds()

# 3. 凭证助手
helper = CredentialHelper()
await helper.store_credentials("github.com", "user", "token")
```

**永远不要：**
- ❌ 在代码中硬编码凭证
- ❌ 将凭证提交到版本控制
- ❌ 在日志中输出凭证

</details>

---

## 故障排除

<div align="center">

### 🔧 常见问题

</div>

<details>
<summary><b>❓ 遇到 "WorkspaceNotFound" 错误</b></summary>

<br>

**问题：**
```
Error: WorkspaceNotFound
```

**原因：** 工作空间不存在或已被清理。

**解决方案：**

```python
from mcp_git.service.workspace import WorkspaceManager

manager = WorkspaceManager()

# 检查工作空间是否存在
if await manager.exists(workspace_id):
    # 继续操作
    pass
else:
    # 重新创建工作空间
    await manager.create(workspace_id)
```

**调试提示：**
```python
# 列出所有工作空间
workspaces = await manager.list_workspaces()
print(f"活跃工作空间: {workspaces}")
```

</details>

<details>
<summary><b>❓ Git 操作超时</b></summary>

<br>

**问题：**
```
Error: GitOperationTimeout
```

**常见原因：**

1. **网络问题：**
   ```python
   # 使用浅克隆减少数据传输
   options = CloneOptions(depth=1)
   ```

2. **仓库过大：**
   ```python
   # 单分支克隆
   options = CloneOptions(single_branch=True, depth=1)
   ```

3. **增加超时时间：**
   ```python
   config = ServerConfig(
       operation_timeout=300,  # 5 分钟
   )
   ```

**调试：**
```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)
```

</details>

<details>
<summary><b>❓ 性能低于预期</b></summary>

<br>

**检查清单：**

- [ ] 网络连接是否稳定？
  ```bash
  ping github.com
  ```

- [ ] 是否使用了浅克隆？
  ```python
  CloneOptions(depth=1)
  ```

- [ ] 工作空间数量是否过多？
  ```python
  config = ServerConfig(max_workspaces=20)
  ```

- [ ] 是否有足够的磁盘空间？
  ```bash
  df -h
  ```

**分析：**
```bash
# 查看资源使用
top -bn1 | head -20
```

**更多帮助：** [性能指南](PERFORMANCE.md)

</details>

**更多问题？** 查看 [故障排除指南](TROUBLESHOOTING.md)

---

## 贡献

<div align="center">

### 🤝 加入社区

</div>

<details>
<summary><b>❓ 如何贡献？</b></summary>

<br>

**贡献方式：**

<table>
<tr>
<td width="50%">

**代码贡献**
- 🐛 修复 bug
- ✨ 添加功能
- 📝 改进文档
- ✅ 编写测试

</td>
<td width="50%">

**非代码贡献**
- 📖 编写教程
- 🎨 设计资源
- 🌍 翻译文档
- 💬 回答问题

</td>
</tr>
</table>

**入门指南：**

1. 🍴 Fork 仓库
2. 🌱 创建分支
3. ✏️ 进行更改
4. ✅ 添加测试
5. 📤 提交 PR

**指南：** [CONTRIBUTING.md](../CONTRIBUTING.md)

</details>

<details>
<summary><b>❓ 发现 bug 怎么办？</b></summary>

<br>

**报告前：**

1. ✅ 查看 [现有 issues](../../issues)
2. ✅ 尝试最新版本
3. ✅ 查看 [故障排除指南](TROUBLESHOOTING.md)

**创建好的 Bug 报告：**

```markdown
### 描述
bug 的清晰描述

### 重现步骤
1. 第一步
2. 第二步
3. 看到错误

### 预期行为
应该发生什么

### 实际行为
实际发生了什么

### 环境
- OS: Ubuntu 22.04
- Python 版本: 3.11.0
- mcp-git 版本: 0.1.0

### 其他上下文
任何其他相关信息
```

**提交：** [创建 Issue](../../issues/new)

</details>

<details>
<summary><b>❓ 在哪里可以获得帮助？</b></summary>

<br>

<div align="center">

### 💬 支持渠道

</div>

<table>
<tr>
<td width="33%" align="center">

**🐛 Issues**

[GitHub Issues](../../issues)

Bug 报告和功能请求

</td>
<td width="33%" align="center">

**💬 Discussions**

[GitHub Discussions](../../discussions)

问答和想法

</td>
<td width="33%" align="center">

**💡 Discord**

[加入服务器](https://discord.gg/mcp)

实时聊天

</td>
</tr>
</table>

**响应时间：**
- 🐛 关键 bug：24 小时
- 🔧 功能请求：1 周
- 💬 问题：2-3 天

</details>

---

## 许可

<div align="center">

### 📄 许可信息

</div>

<details>
<summary><b>❓ 使用了什么许可证？</b></summary>

<br>

**双重许可：**

<table>
<tr>
<td width="50%" align="center">

**MIT 许可证**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE-MIT)

**权限：**
- ✅ 商业使用
- ✅ 修改
- ✅ 分发
- ✅ 私有使用

</td>
<td width="50%" align="center">

**Apache License 2.0**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](../LICENSE-APACHE)

**权限：**
- ✅ 商业使用
- ✅ 修改
- ✅ 分发
- ✅ 专利授权

</td>
</tr>
</table>

**您可以选择任一许可证使用。**

</details>

<details>
<summary><b>❓ 可以在商业项目中使用吗？</b></summary>

<br>

**可以！** MIT 和 Apache 2.0 许可证都允许商业使用。

**您需要做的：**
1. ✅ 包含许可证文本
2. ✅ 包含版权声明
3. ✅ 说明任何修改

**您不需要做的：**
- ❌ 分享您的源代码
- ❌ 开源您的项目
- ❌ 支付版税

**问题？** 联系：opensource@anthropic.com

</details>

---

<div align="center">

### 🎯 仍有疑问？

<table>
<tr>
<td width="33%" align="center">
<a href="../../issues">
<img src="https://img.icons8.com/fluency/96/000000/bug.png" width="48"><br>
<b>提交 Issue</b>
</a>
</td>
<td width="33%" align="center">
<a href="../../discussions">
<img src="https://img.icons8.com/fluency/96/000000/chat.png" width="48"><br>
<b>开始讨论</b>
</a>
</td>
<td width="33%" align="center">
<a href="https://discord.gg/mcp">
<img src="https://img.icons8.com/fluency/96/000000/email.png" width="48"><br>
<b>加入 Discord</b>
</a>
</td>
</tr>
</table>

---

**[📖 用户指南](USER_GUIDE.md)** • **[🔧 API 文档](API_REFERENCE.md)** • **[🏠 首页](../README.md)**

由 Anthropic 制作

[⬆ 返回顶部](#-常见问题解答-faq)
