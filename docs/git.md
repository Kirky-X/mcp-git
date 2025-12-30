以下是Git常用命令的表格整理，按功能分类：

### 配置相关
> **特性**: `config` - 提供配置管理功能，支持全局和本地配置的操作
| 命令 | 说明 |
|------|------|
| `git config --global user.name "名字"` | 设置全局用户名 |
| `git config --global user.email "邮箱"` | 设置全局邮箱 |
| `git config --list` | 查看所有配置 |
| `git config --global credential.helper store` | 保存密码凭证 |

### 仓库操作
> **特性**: `repository` - 提供仓库生命周期管理，支持初始化、克隆、状态查询和历史追溯
| 命令 | 说明 |
|------|------|
| `git init` | 初始化本地仓库 |
| `git clone <地址>` | 克隆远程仓库 |
| `git status` | 查看文件状态 |
| `git log` | 查看提交历史 |
| `git log --oneline` | 简洁查看提交历史 |
| `git reflog` | 查看操作记录 |

### 文件操作
> **特性**: `file` - 提供文件级别的版本控制操作，支持暂存、恢复、删除和重命名
| 命令 | 说明 |
|------|------|
| `git add <文件名>` | 添加文件到暂存区 |
| `git add .` | 添加所有修改到暂存区 |
| `git rm <文件名>` | 删除文件并暂存 |
| `git mv <旧名> <新名>` | 重命名文件 |
| `git checkout -- <文件名>` | 撤销工作区修改 |
| `git restore <文件名>` | 恢复文件（Git 2.23+） |

### 提交操作
> **特性**: `commit` - 提供提交管理功能，支持创建、修改和回滚提交
| 命令 | 说明 |
|------|------|
| `git commit -m "说明"` | 提交暂存区内容 |
| `git commit -am "说明"` | 跳过暂存区直接提交 |
| `git commit --amend` | 修改最后一次提交 |
| `git reset HEAD <文件名>` | 取消暂存文件 |

### 分支操作
> **特性**: `branch` - 提供分支管理功能，支持创建、切换、合并和删除分支
| 命令 | 说明 |
|------|------|
| `git branch` | 查看本地分支 |
| `git branch -a` | 查看所有分支 |
| `git branch <分支名>` | 创建新分支 |
| `git checkout <分支名>` | 切换分支 |
| `git checkout -b <分支名>` | 创建并切换分支 |
| `git merge <分支名>` | 合并分支 |
| `git branch -d <分支名>` | 删除分支 |
| `git branch -D <分支名>` | 强制删除分支 |

### 远程协作
> **特性**: `remote` - 提供远程仓库管理功能，支持远程操作、同步和推送拉取
| 命令 | 说明 |
|------|------|
| `git remote -v` | 查看远程仓库 |
| `git remote add <别名> <地址>` | 添加远程仓库 |
| `git fetch <远程名>` | 获取远程更新 |
| `git pull` | 拉取并合并远程更新 |
| `git push` | 推送本地更新 |
| `git push -u <远程名> <分支名>` | 推送新分支并设置上游 |
| `git push --force` | 强制推送 |

### 标签操作
> **特性**: `tag` - 提供标签管理功能，支持创建、列出和推送标签
| 命令 | 说明 |
|------|------|
| `git tag` | 查看所有标签 |
| `git tag <标签名>` | 创建轻量标签 |
| `git tag -a <标签名> -m "说明"` | 创建附注标签 |
| `git push --tags` | 推送所有标签 |

### 储藏与清理
> **特性**: `stash` - 提供工作区暂存功能，支持保存、恢复和清理工作进度
| 命令 | 说明 |
|------|------|
| `git stash` | 储藏当前修改 |
| `git stash list` | 查看储藏列表 |
| `git stash pop` | 恢复并删除储藏 |
| `git stash apply` | 恢复但不删除储藏 |
| `git clean -fd` | 清理未跟踪文件 |

### 高级操作
> **特性**: `advanced` - 提供高级版本控制操作，包括变基、差异比较、撤销和追溯
| 命令 | 说明 |
|------|------|
| `git rebase <分支名>` | 变基操作 |
| `git cherry-pick <提交ID>` | 挑选提交 |
| `git revert <提交ID>` | 撤销提交 |
| `git diff` | 查看工作区差异 |
| `git diff --cached` | 查看暂存区差异 |
| `git blame <文件名>` | 查看文件修改记录 |
