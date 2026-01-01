"""
MCP Tool definitions for mcp-git.

This module defines all available MCP tools for Git operations.
"""

from mcp.types import Tool

# Workspace management tools
WORKSPACE_ALLOCATE = Tool(
    name="git_allocate_workspace",
    description=(
        "Allocate a new workspace for Git operations. "
        "Returns a workspace ID and path for use with other tools."
    ),
    inputSchema={
        "type": "object",
        "properties": {},
        "required": [],
    },
)

WORKSPACE_GET = Tool(
    name="git_get_workspace",
    description=("Get information about a workspace."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
        },
        "required": ["workspace_id"],
    },
)

WORKSPACE_RELEASE = Tool(
    name="git_release_workspace",
    description=("Release a workspace and clean up resources."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
        },
        "required": ["workspace_id"],
    },
)

WORKSPACE_LIST = Tool(
    name="git_list_workspaces",
    description=("List all allocated workspaces."),
    inputSchema={
        "type": "object",
        "properties": {},
        "required": [],
    },
)

# Disk space monitoring
DISK_SPACE = Tool(
    name="git_disk_space",
    description=(
        "Check disk space usage and get warnings when disk space is low. "
        "Returns disk space information and a warning flag if space is below the threshold."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "warning_threshold": {
                "type": "number",
                "description": "Percentage of free space below which to warn",
                "default": 20.0,
            },
        },
        "required": [],
    },
)

# Repository operations
CLONE = Tool(
    name="git_clone",
    description=(
        "Clone a Git repository into a workspace. "
        "Supports shallow clones with depth limit and branch selection."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Repository URL (HTTPS or SSH)",
            },
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "branch": {
                "type": "string",
                "description": "Optional branch to clone",
            },
            "depth": {
                "type": "integer",
                "description": "Shallow clone depth (faster for large repos)",
            },
        },
        "required": ["url", "workspace_id"],
    },
)

INIT_REPOSITORY = Tool(
    name="git_init",
    description=("Initialize a new Git repository in a workspace."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "bare": {
                "type": "boolean",
                "description": "Create a bare repository",
            },
            "default_branch": {
                "type": "string",
                "description": "Default branch name",
                "default": "main",
            },
        },
        "required": ["workspace_id"],
    },
)

GET_STATUS = Tool(
    name="git_status",
    description=(
        "Get the current status of the working directory. "
        "Shows staged, unstaged, and untracked files."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
        },
        "required": ["workspace_id"],
    },
)

# Commit operations
STAGE = Tool(
    name="git_stage",
    description=(
        "Stage files for commit. Accepts file paths, patterns (glob), or '.' for all files."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Files to stage",
            },
        },
        "required": ["workspace_id", "files"],
    },
)

COMMIT = Tool(
    name="git_commit",
    description=("Create a new commit with staged changes."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "message": {
                "type": "string",
                "description": "Commit message",
            },
            "author_name": {
                "type": "string",
                "description": "Author name (optional)",
            },
            "author_email": {
                "type": "string",
                "description": "Author email (optional)",
            },
        },
        "required": ["workspace_id", "message"],
    },
)

# Remote operations
PUSH = Tool(
    name="git_push",
    description=("Push commits to a remote repository."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "remote": {
                "type": "string",
                "description": "Remote name",
                "default": "origin",
            },
            "branch": {
                "type": "string",
                "description": "Branch to push",
            },
            "force": {
                "type": "boolean",
                "description": "Force push",
            },
        },
        "required": ["workspace_id"],
    },
)

PULL = Tool(
    name="git_pull",
    description=("Pull changes from a remote repository."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "remote": {
                "type": "string",
                "description": "Remote name",
                "default": "origin",
            },
            "branch": {
                "type": "string",
                "description": "Branch to pull",
            },
            "rebase": {
                "type": "boolean",
                "description": "Rebase instead of merge",
            },
        },
        "required": ["workspace_id"],
    },
)

FETCH = Tool(
    name="git_fetch",
    description=("Fetch changes from a remote repository."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "remote": {
                "type": "string",
                "description": "Remote name",
            },
            "tags": {
                "type": "boolean",
                "description": "Fetch all tags",
            },
        },
        "required": ["workspace_id"],
    },
)

# Branch operations
CHECKOUT = Tool(
    name="git_checkout",
    description=("Checkout a branch or commit."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "branch": {
                "type": "string",
                "description": "Branch or commit to checkout",
            },
            "create_new": {
                "type": "boolean",
                "description": "Create new branch if it doesn't exist",
            },
            "force": {
                "type": "boolean",
                "description": "Force checkout, discard local changes",
            },
        },
        "required": ["workspace_id", "branch"],
    },
)

LIST_BRANCHES = Tool(
    name="git_list_branches",
    description=("List branches in the repository."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "local": {
                "type": "boolean",
                "description": "Include local branches",
                "default": True,
            },
            "remote": {
                "type": "boolean",
                "description": "Include remote branches",
            },
            "all": {
                "type": "boolean",
                "description": "Include all branches",
            },
        },
        "required": ["workspace_id"],
    },
)

CREATE_BRANCH = Tool(
    name="git_create_branch",
    description=("Create a new branch."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "name": {
                "type": "string",
                "description": "Branch name",
            },
            "revision": {
                "type": "string",
                "description": "Starting revision",
            },
            "force": {
                "type": "boolean",
                "description": "Overwrite existing branch",
            },
        },
        "required": ["workspace_id", "name"],
    },
)

DELETE_BRANCH = Tool(
    name="git_delete_branch",
    description=("Delete a branch."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "name": {
                "type": "string",
                "description": "Branch name",
            },
            "force": {
                "type": "boolean",
                "description": "Force delete unmerged branch",
            },
            "remote": {
                "type": "boolean",
                "description": "Delete remote branch",
            },
        },
        "required": ["workspace_id", "name"],
    },
)

# Merge and rebase
MERGE = Tool(
    name="git_merge",
    description=("Merge a branch into the current branch."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "source_branch": {
                "type": "string",
                "description": "Branch to merge",
            },
            "fast_forward": {
                "type": "boolean",
                "description": "Fast-forward only",
                "default": True,
            },
        },
        "required": ["workspace_id", "source_branch"],
    },
)

REBASE = Tool(
    name="git_rebase",
    description=("Rebase the current branch onto another branch."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "branch": {
                "type": "string",
                "description": "Branch to rebase onto",
            },
            "abort": {
                "type": "boolean",
                "description": "Abort ongoing rebase",
            },
            "continue_rebase": {
                "type": "boolean",
                "description": "Continue ongoing rebase",
            },
        },
        "required": ["workspace_id"],
    },
)

# History operations
LOG = Tool(
    name="git_log",
    description=("View commit history."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "max_count": {
                "type": "integer",
                "description": "Maximum number of commits",
            },
            "author": {
                "type": "string",
                "description": "Filter by author",
            },
            "all": {
                "type": "boolean",
                "description": "Show all branches",
            },
        },
        "required": ["workspace_id"],
    },
)

SHOW = Tool(
    name="git_show",
    description=("Show a specific commit."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "revision": {
                "type": "string",
                "description": "Commit revision (SHA, branch, tag)",
            },
        },
        "required": ["workspace_id", "revision"],
    },
)

DIFF = Tool(
    name="git_diff",
    description=("Show differences between commits, commit and working tree, etc."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "cached": {
                "type": "boolean",
                "description": "Show staged changes",
            },
            "commit_oid": {
                "type": "string",
                "description": "Compare with specific commit",
            },
        },
        "required": ["workspace_id"],
    },
)

BLAME = Tool(
    name="git_blame",
    description=("Show which revision and author last modified each line of a file."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "path": {
                "type": "string",
                "description": "File path",
            },
        },
        "required": ["workspace_id", "path"],
    },
)

# Stash operations
STASH = Tool(
    name="git_stash",
    description=("Stash changes in the working directory."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "save": {
                "type": "boolean",
                "description": "Save changes to stash",
            },
            "pop": {
                "type": "boolean",
                "description": "Apply and remove stash",
            },
            "apply": {
                "type": "boolean",
                "description": "Apply stash without removing",
            },
            "drop": {
                "type": "boolean",
                "description": "Remove stash entry",
            },
            "message": {
                "type": "string",
                "description": "Stash message",
            },
            "include_untracked": {
                "type": "boolean",
                "description": "Include untracked files",
            },
        },
        "required": ["workspace_id"],
    },
)

LIST_STASH = Tool(
    name="git_list_stash",
    description=("List stash entries."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
        },
        "required": ["workspace_id"],
    },
)

# Tag operations
LIST_TAGS = Tool(
    name="git_list_tags",
    description=("List all tags in the repository."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
        },
        "required": ["workspace_id"],
    },
)

CREATE_TAG = Tool(
    name="git_create_tag",
    description=("Create a new tag."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "name": {
                "type": "string",
                "description": "Tag name",
            },
            "message": {
                "type": "string",
                "description": "Tag message (for annotated tags)",
            },
            "force": {
                "type": "boolean",
                "description": "Overwrite existing tag",
            },
        },
        "required": ["workspace_id", "name"],
    },
)

DELETE_TAG = Tool(
    name="git_delete_tag",
    description=("Delete a tag."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "name": {
                "type": "string",
                "description": "Tag name",
            },
        },
        "required": ["workspace_id", "name"],
    },
)

# Remote operations
LIST_REMOTES = Tool(
    name="git_list_remotes",
    description=("List remote repositories."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
        },
        "required": ["workspace_id"],
    },
)

ADD_REMOTE = Tool(
    name="git_add_remote",
    description=("Add a remote repository."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "name": {
                "type": "string",
                "description": "Remote name",
            },
            "url": {
                "type": "string",
                "description": "Remote URL",
            },
        },
        "required": ["workspace_id", "name", "url"],
    },
)

REMOVE_REMOTE = Tool(
    name="git_remove_remote",
    description=("Remove a remote repository."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "name": {
                "type": "string",
                "description": "Remote name",
            },
        },
        "required": ["workspace_id", "name"],
    },
)

# Git LFS operations
LFS_INIT = Tool(
    name="git_lfs_init",
    description=(
        "Initialize Git LFS (Large File Storage) in a repository. "
        "This enables tracking and managing large binary files efficiently."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
        },
        "required": ["workspace_id"],
    },
)

LFS_TRACK = Tool(
    name="git_lfs_track",
    description=(
        "Track files with Git LFS. "
        "Specify file patterns (e.g., '*.zip', '*.psd') to track with LFS."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "File patterns to track (e.g., ['*.zip', '*.psd'])",
            },
            "lockable": {
                "type": "boolean",
                "description": "Make files lockable",
                "default": False,
            },
        },
        "required": ["workspace_id", "patterns"],
    },
)

LFS_UNTRACK = Tool(
    name="git_lfs_untrack",
    description=("Stop tracking files with Git LFS."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "File patterns to untrack",
            },
        },
        "required": ["workspace_id", "patterns"],
    },
)

LFS_STATUS = Tool(
    name="git_lfs_status",
    description=("Show Git LFS status and tracked files."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
        },
        "required": ["workspace_id"],
    },
)

LFS_PULL = Tool(
    name="git_lfs_pull",
    description=("Download LFS files from the remote repository."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "objects": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific objects to pull (optional)",
            },
            "all": {
                "type": "boolean",
                "description": "Pull all LFS objects",
                "default": True,
            },
        },
        "required": ["workspace_id"],
    },
)

LFS_PUSH = Tool(
    name="git_lfs_push",
    description=("Push LFS objects to the remote repository."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "remote": {
                "type": "string",
                "description": "Remote name",
                "default": "origin",
            },
            "all": {
                "type": "boolean",
                "description": "Push all LFS objects",
                "default": True,
            },
        },
        "required": ["workspace_id"],
    },
)

LFS_FETCH = Tool(
    name="git_lfs_fetch",
    description=("Fetch LFS objects from the remote without merging."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "objects": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific objects to fetch (optional)",
            },
        },
        "required": ["workspace_id"],
    },
)

LFS_INSTALL = Tool(
    name="git_lfs_install",
    description=("Install Git LFS hooks in the repository."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
        },
        "required": ["workspace_id"],
    },
)

SPARSE_CHECKOUT = Tool(
    name="git_sparse_checkout",
    description=(
        "Configure sparse checkout for a repository. "
        "Sparse checkout allows you to only checkout specific paths in a repository, "
        "reducing disk usage for large repositories. "
        "Use mode='replace' to set new paths (overwrites existing), "
        "mode='add' to add to existing paths, "
        "or mode='remove' to remove specific paths. "
        "To disable sparse checkout, set paths=[] with mode='replace'."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Paths to include in checkout (e.g., ['src/', 'README.md'])",
            },
            "mode": {
                "type": "string",
                "description": "Operation mode: 'replace' (default), 'add', or 'remove'",
                "enum": ["replace", "add", "remove"],
                "default": "replace",
            },
        },
        "required": ["workspace_id", "paths"],
    },
)

# Submodule operations
SUBMODULE_ADD = Tool(
    name="git_submodule_add",
    description=(
        "Add a submodule to the repository. "
        "This adds a reference to another repository as a subdirectory."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "path": {
                "type": "string",
                "description": "Path where the submodule should be placed",
            },
            "url": {
                "type": "string",
                "description": "URL of the submodule repository",
            },
            "name": {
                "type": "string",
                "description": "Optional name for the submodule",
            },
            "branch": {
                "type": "string",
                "description": "Branch to track (default: HEAD)",
            },
            "depth": {
                "type": "integer",
                "description": "Shallow clone depth for submodule",
            },
        },
        "required": ["workspace_id", "path", "url"],
    },
)

SUBMODULE_UPDATE = Tool(
    name="git_submodule_update",
    description=(
        "Update submodules to their latest committed state. "
        "This fetches and checks out the commit specified by the superproject."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "name": {
                "type": "string",
                "description": "Optional submodule name/path (updates all if not specified)",
            },
            "init": {
                "type": "boolean",
                "description": "Initialize submodules if not already",
                "default": True,
            },
        },
        "required": ["workspace_id"],
    },
)

SUBMODULE_DEINIT = Tool(
    name="git_submodule_deinit",
    description=(
        "Deinitialize a submodule. "
        "This removes the submodule's working tree and gitlink from the superproject."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
            "name": {
                "type": "string",
                "description": "Optional submodule name/path (deinits all if not specified)",
            },
            "force": {
                "type": "boolean",
                "description": "Force deinitialization even with local changes",
                "default": False,
            },
        },
        "required": ["workspace_id"],
    },
)

SUBMODULE_LIST = Tool(
    name="git_submodule_list",
    description=("List all submodules in the repository."),
    inputSchema={
        "type": "object",
        "properties": {
            "workspace_id": {
                "type": "string",
                "description": "Workspace ID",
            },
        },
        "required": ["workspace_id"],
    },
)

# Task operations
GET_TASK = Tool(
    name="git_get_task",
    description=("Get task information."),
    inputSchema={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "Task ID",
            },
        },
        "required": ["task_id"],
    },
)

LIST_TASKS = Tool(
    name="git_list_tasks",
    description=("List tasks with optional status filter."),
    inputSchema={
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Filter by status (queued, running, completed, failed, cancelled)",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of tasks",
                "default": 100,
            },
        },
        "required": [],
    },
)

CANCEL_TASK = Tool(
    name="git_cancel_task",
    description=("Cancel a running task."),
    inputSchema={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "Task ID",
            },
        },
        "required": ["task_id"],
    },
)

# All tools list
ALL_TOOLS = [
    # Workspace
    WORKSPACE_ALLOCATE,
    WORKSPACE_GET,
    WORKSPACE_RELEASE,
    WORKSPACE_LIST,
    DISK_SPACE,
    # Repository
    CLONE,
    INIT_REPOSITORY,
    GET_STATUS,
    # Commit
    STAGE,
    COMMIT,
    # Remote
    PUSH,
    PULL,
    FETCH,
    # Branch
    CHECKOUT,
    LIST_BRANCHES,
    CREATE_BRANCH,
    DELETE_BRANCH,
    # Merge/Rebase
    MERGE,
    REBASE,
    # History
    LOG,
    SHOW,
    DIFF,
    BLAME,
    # Stash
    STASH,
    LIST_STASH,
    # Tags
    LIST_TAGS,
    CREATE_TAG,
    DELETE_TAG,
    # Remotes
    LIST_REMOTES,
    ADD_REMOTE,
    REMOVE_REMOTE,
    # Git LFS
    LFS_INIT,
    LFS_TRACK,
    LFS_UNTRACK,
    LFS_STATUS,
    LFS_PULL,
    LFS_PUSH,
    LFS_FETCH,
    LFS_INSTALL,
    SPARSE_CHECKOUT,
    # Submodules
    SUBMODULE_ADD,
    SUBMODULE_UPDATE,
    SUBMODULE_DEINIT,
    SUBMODULE_LIST,
    # Tasks
    GET_TASK,
    LIST_TASKS,
    CANCEL_TASK,
]
