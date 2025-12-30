# mcp-git API Reference

## Tool Reference

This document provides detailed documentation for all MCP tools available in mcp-git.

---

## Workspace Management Tools

### git_allocate_workspace

Allocate a new workspace for Git operations.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {}
}
```

**Response:**
```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "path": "/tmp/mcp-git/workspaces/550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Codes:**
- `201`: Workspace allocated successfully

---

### git_get_workspace

Get information about a workspace.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "The workspace ID"
    }
  }
}
```

**Response:**
```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "path": "/tmp/mcp-git/workspaces/550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-15T10:30:00Z",
  "last_used_at": "2024-01-15T10:35:00Z"
}
```

---

### git_release_workspace

Release a workspace and clean up resources.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "The workspace ID to release"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Workspace released successfully"
}
```

---

### git_list_workspaces

List all allocated workspaces.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {}
}
```

**Response:**
```json
{
  "workspaces": [
    {
      "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
      "path": "/tmp/mcp-git/workspaces/550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## Repository Operations

### git_clone

Clone a Git repository into a workspace.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["repo_url"],
  "properties": {
    "repo_url": {
      "type": "string",
      "description": "URL of the repository to clone"
    },
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID (optional, will allocate if not provided)"
    },
    "branch": {
      "type": "string",
      "description": "Branch to clone (default: repository's default branch)"
    },
    "depth": {
      "type": "integer",
      "description": "Depth for shallow clone (default: 1)",
      "minimum": 1
    },
    "single_branch": {
      "type": "boolean",
      "description": "Clone only one branch (default: false)"
    },
    "filter": {
      "type": "string",
      "description": "Partial clone filter (e.g., 'blob:none')"
    }
  }
}
```

**Response:**
```json
{
  "task_id": "task-uuid",
  "status": "queued",
  "message": "Clone task created successfully"
}
```

**Status Codes:**
- `202`: Task queued for async processing
- `400`: Invalid repository URL
- `401`: Authentication required
- `404`: Repository not found

---

### git_init

Initialize a new Git repository.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "bare": {
      "type": "boolean",
      "description": "Create a bare repository (default: false)"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "path": "/tmp/mcp-git/workspaces/workspace-id"
}
```

---

### git_status

Get repository status.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    }
  }
}
```

**Response:**
```json
{
  "modified": ["file1.txt", "file2.py"],
  "staged": ["file3.py"],
  "untracked": ["new_feature.py"],
  "ahead": 2,
  "behind": 0
}
```

---

## Commit Operations

### git_stage

Stage files for commit.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "files"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "files": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Files to stage (use ['.'] for all)"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "staged_files": ["file1.txt"]
}
```

---

### git_commit

Create a new commit.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "message"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "message": {
      "type": "string",
      "description": "Commit message"
    },
    "author_name": {
      "type": "string",
      "description": "Author name"
    },
    "author_email": {
      "type": "string",
      "description": "Author email"
    },
    "amend": {
      "type": "boolean",
      "description": "Amend previous commit (default: false)"
    },
    "allow_empty": {
      "type": "boolean",
      "description": "Allow empty commit (default: false)"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "commit_oid": "abc123def456789",
  "message": "Commit message"
}
```

---

## Remote Operations

### git_push

Push commits to remote.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "remote": {
      "type": "string",
      "description": "Remote name (default: 'origin')"
    },
    "branch": {
      "type": "string",
      "description": "Branch to push"
    },
    "force": {
      "type": "boolean",
      "description": "Force push (default: false)"
    }
  }
}
```

**Response:**
```json
{
  "task_id": "task-uuid",
  "status": "queued",
  "message": "Push task created successfully"
}
```

**Status Codes:**
- `202`: Task queued for async processing
- `403`: Push rejected (would overwrite remote changes)

---

### git_pull

Pull changes from remote.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "remote": {
      "type": "string",
      "description": "Remote name (default: 'origin')"
    },
    "branch": {
      "type": "string",
      "description": "Branch to pull"
    },
    "rebase": {
      "type": "boolean",
      "description": "Use rebase instead of merge (default: false)"
    }
  }
}
```

**Response:**
```json
{
  "task_id": "task-uuid",
  "status": "queued",
  "message": "Pull task created successfully"
}
```

---

### git_fetch

Fetch from remote.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "remote": {
      "type": "string",
      "description": "Remote name (default: 'origin')"
    },
    "prune": {
      "type": "boolean",
      "description": "Prune remote-tracking references (default: false)"
    }
  }
}
```

**Response:**
```json
{
  "task_id": "task-uuid",
  "status": "queued",
  "message": "Fetch task created successfully"
}
```

---

## Branch Operations

### git_checkout

Checkout a branch or commit.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "branch"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "branch": {
      "type": "string",
      "description": "Branch name or commit hash"
    },
    "create_new": {
      "type": "boolean",
      "description": "Create new branch if not exists (default: false)"
    },
    "force": {
      "type": "boolean",
      "description": "Force checkout, discard local changes (default: false)"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "current_branch": "feature-branch"
}
```

---

### git_list_branches

List branches.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "all": {
      "type": "boolean",
      "description": "Include remote branches (default: false)"
    }
  }
}
```

**Response:**
```json
{
  "current_branch": "main",
  "branches": ["main", "develop", "feature/new-feature"]
}
```

---

### git_create_branch

Create a new branch.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "name"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "name": {
      "type": "string",
      "description": "Branch name"
    },
    "start_point": {
      "type": "string",
      "description": "Starting point (branch or commit)"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "branch": "feature/new-feature"
}
```

---

### git_delete_branch

Delete a branch.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "name"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "name": {
      "type": "string",
      "description": "Branch name to delete"
    },
    "force": {
      "type": "boolean",
      "description": "Force delete unmerged branch (default: false)"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Branch deleted successfully"
}
```

---

## Merge and Rebase

### git_merge

Merge a branch into current branch.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "source_branch"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "source_branch": {
      "type": "string",
      "description": "Branch to merge"
    },
    "fast_forward": {
      "type": "boolean",
      "description": "Allow fast-forward (default: true)"
    },
    "no_ff": {
      "type": "boolean",
      "description": "Create merge commit even with fast-forward (default: false)"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "result": "merged",
  "commit_oid": "abc123def456789"
}
```

**Merge Results:**
- `already_up_to_date`: Already up to date with source
- `fast_forward`: Fast-forward merge
- `merged`: Merge commit created
- `conflicted`: Merge has conflicts
- `failed`: Merge failed

---

### git_rebase

Rebase current branch.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "branch": {
      "type": "string",
      "description": "Branch to rebase onto"
    },
    "interactive": {
      "type": "boolean",
      "description": "Interactive rebase (default: false)"
    },
    "abort": {
      "type": "boolean",
      "description": "Abort ongoing rebase (default: false)"
    },
    "continue_rebase": {
      "type": "boolean",
      "description": "Continue after resolving conflicts (default: false)"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Rebase completed successfully"
}
```

---

## History Operations

### git_log

View commit history.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "max_count": {
      "type": "integer",
      "description": "Limit number of commits"
    },
    "skip": {
      "type": "integer",
      "description": "Skip N commits"
    },
    "author": {
      "type": "string",
      "description": "Filter by author"
    },
    "since": {
      "type": "string",
      "description": "Since date (ISO format)"
    },
    "until": {
      "type": "string",
      "description": "Until date (ISO format)"
    },
    "path": {
      "type": "string",
      "description": "Filter by file path"
    }
  }
}
```

**Response:**
```json
{
  "commits": [
    {
      "oid": "abc123def456789",
      "message": "Fix bug in login",
      "author": "Developer <dev@example.com>",
      "author_time": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

### git_diff

Show differences.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "cached": {
      "type": "boolean",
      "description": "Show staged changes (default: false)"
    },
    "commit_oid": {
      "type": "string",
      "description": "Compare with specific commit"
    },
    "path": {
      "type": "string",
      "description": "Limit to specific file"
    },
    "unified": {
      "type": "integer",
      "description": "Number of context lines (default: 3)"
    }
  }
}
```

**Response:**
```json
{
  "diff": "diff --git a/file.txt b/file.txt\n--- a/file.txt\n+++ b/file.txt\n@@ -1 +1 @@\n-old content\n+new content"
}
```

---

### git_blame

Show blame information for a file.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "path"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "path": {
      "type": "string",
      "description": "File path"
    },
    "start_line": {
      "type": "integer",
      "description": "Start line number"
    },
    "end_line": {
      "type": "integer",
      "description": "End line number"
    }
  }
}
```

**Response:**
```json
{
  "blame": [
    {
      "line": 1,
      "commit": "abc123def456789",
      "author": "Developer",
      "time": "2024-01-10",
      "content": "import os"
    }
  ]
}
```

---

## Stash Operations

### git_stash

Stash changes.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "save": {
      "type": "boolean",
      "description": "Save changes to stash (default: true)"
    },
    "message": {
      "type": "string",
      "description": "Stash message"
    },
    "include_untracked": {
      "type": "boolean",
      "description": "Include untracked files (default: false)"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "stash_id": 0
}
```

---

### git_list_stash

List stash entries.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    }
  }
}
```

**Response:**
```json
{
  "stashes": [
    {
      "stash_id": 0,
      "message": "WIP on feature-branch"
    }
  ]
}
```

---

### git_stash_pop

Apply and remove stash entry.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "stash_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "stash_id": {
      "type": "integer",
      "description": "Stash entry ID"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Stash applied successfully"
}
```

---

## Tag Operations

### git_list_tags

List tags.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    }
  }
}
```

**Response:**
```json
{
  "tags": ["v1.0.0", "v1.1.0", "v2.0.0"]
}
```

---

### git_create_tag

Create a tag.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "name"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "name": {
      "type": "string",
      "description": "Tag name"
    },
    "message": {
      "type": "string",
      "description": "Annotated tag message"
    },
    "force": {
      "type": "boolean",
      "description": "Force overwrite existing tag (default: false)"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "tag": "v1.0.0"
}
```

---

### git_delete_tag

Delete a tag.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "name"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "name": {
      "type": "string",
      "description": "Tag name to delete"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Tag deleted successfully"
}
```

---

## Remote Operations

### git_list_remotes

List remotes.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    }
  }
}
```

**Response:**
```json
{
  "remotes": [
    {
      "name": "origin",
      "url": "https://github.com/example/repo.git"
    }
  ]
}
```

---

### git_add_remote

Add a remote.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "name", "url"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "name": {
      "type": "string",
      "description": "Remote name"
    },
    "url": {
      "type": "string",
      "description": "Remote URL"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "remote": "origin"
}
```

---

### git_remove_remote

Remove a remote.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "name"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "name": {
      "type": "string",
      "description": "Remote name"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Remote removed successfully"
}
```

---

## Task Operations

### git_get_task

Get task information.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["task_id"],
  "properties": {
    "task_id": {
      "type": "string",
      "description": "Task ID"
    }
  }
}
```

**Response:**
```json
{
  "task_id": "task-uuid",
  "status": "completed",
  "operation": "clone",
  "progress": 100,
  "result": {
    "oid": "abc123"
  }
}
```

**Task Status:**
- `queued`: Task is queued
- `running`: Task is in progress
- `completed`: Task completed successfully
- `failed`: Task failed
- `cancelled`: Task was cancelled

---

### git_list_tasks

List tasks.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "description": "Filter by status"
    },
    "limit": {
      "type": "integer",
      "description": "Maximum number of tasks to return"
    }
  }
}
```

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "task-uuid",
      "status": "completed",
      "operation": "clone",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

### git_cancel_task

Cancel a task.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["task_id"],
  "properties": {
    "task_id": {
      "type": "string",
      "description": "Task ID"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Task cancelled successfully"
}
```

---

## Git LFS Tools

### git_lfs_init

Initialize Git LFS in a repository.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    }
  }
}
```

---

### git_lfs_track

Track files with Git LFS.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "patterns"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "patterns": {
      "type": "array",
      "items": {"type": "string"},
      "description": "File patterns to track (e.g., ['*.zip', '*.psd'])"
    },
    "lockable": {
      "type": "boolean",
      "description": "Make files lockable",
      "default": false
    }
  }
}
```

**Response:**
```json
{
  "tracked_patterns": ["*.zip", "*.psd"]
}
```

---

### git_lfs_untrack

Stop tracking files with Git LFS.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "patterns"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "patterns": {
      "type": "array",
      "items": {"type": "string"},
      "description": "File patterns to untrack"
    }
  }
}
```

---

### git_lfs_status

Show Git LFS status and tracked files.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    }
  }
}
```

**Response:**
```json
{
  "lfs_files": [
    {
      "name": "large-file.zip",
      "path": "data/large-file.zip",
      "size": 52428800,
      "oid": "sha256:abc123...",
      "tracked": true
    }
  ]
}
```

---

### git_lfs_pull

Download LFS files from the remote repository.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "objects": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Specific objects to pull (optional)"
    },
    "all": {
      "type": "boolean",
      "description": "Pull all LFS objects",
      "default": true
    }
  }
}
```

---

### git_lfs_push

Push LFS objects to the remote repository.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "remote": {
      "type": "string",
      "description": "Remote name",
      "default": "origin"
    },
    "all": {
      "type": "boolean",
      "description": "Push all LFS objects",
      "default": true
    }
  }
}
```

---

### git_lfs_fetch

Fetch LFS objects from the remote without merging.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "objects": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Specific objects to fetch (optional)"
    }
  }
}
```

---

### git_lfs_install

Install Git LFS hooks in the repository.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    }
  }
}
```

---

## Submodule Tools

### git_submodule_add

Add a submodule to the repository.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id", "path", "url"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "path": {
      "type": "string",
      "description": "Path where the submodule should be placed"
    },
    "url": {
      "type": "string",
      "description": "URL of the submodule repository"
    },
    "name": {
      "type": "string",
      "description": "Optional name for the submodule"
    },
    "branch": {
      "type": "string",
      "description": "Branch to track (default: HEAD)"
    },
    "depth": {
      "type": "integer",
      "description": "Shallow clone depth for submodule"
    }
  }
}
```

---

### git_submodule_update

Update submodules to their latest committed state.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "name": {
      "type": "string",
      "description": "Optional submodule name/path (updates all if not specified)"
    },
    "init": {
      "type": "boolean",
      "description": "Initialize submodules if not already",
      "default": true
    }
  }
}
```

---

### git_submodule_deinit

Deinitialize a submodule.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    },
    "name": {
      "type": "string",
      "description": "Optional submodule name/path (deinits all if not specified)"
    },
    "force": {
      "type": "boolean",
      "description": "Force deinitialization even with local changes",
      "default": false
    }
  }
}
```

---

### git_submodule_list

List all submodules in the repository.

**Input Schema:**
```json
{
  "type": "object",
  "required": ["workspace_id"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "description": "Workspace ID"
    }
  }
}
```

**Response:**
```json
{
  "submodules": [
    {
      "name": "submodule-name",
      "path": "path/to/submodule",
      "url": "https://github.com/user/submodule.git",
      "branch": "main",
      "commit_oid": "abc123...",
      "status": "clean"
    }
  ]
}
```

---

## Health and Metrics

### git_get_health

Health check endpoint.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {}
}
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### git_get_metrics

Get performance metrics.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {}
}
```

**Response:**
```json
{
  "active_tasks": 2,
  "queued_tasks": 5,
  "completed_tasks": 100,
  "failed_tasks": 2,
  "average_task_duration_seconds": 12.5
}
```

---

## Error Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `REPO_NOT_FOUND` | Repository not found | The specified repository URL is invalid or not accessible |
| `GIT_AUTH` | Authentication failed | Credentials are invalid or insufficient |
| `GIT_CONFLICT` | Merge/Conflict detected | Merge conflict in files |
| `GIT_TIMEOUT` | Operation timeout | Git operation exceeded timeout |
| `WORKSPACE_FULL` | Workspace full | Workspace disk space exhausted |
| `TASK_NOT_FOUND` | Task not found | Task ID is invalid |
| `TASK_CANCELLED` | Task cancelled | Task was cancelled before completion |
| `INVALID_PARAMS` | Invalid parameters | Request parameters are invalid |
