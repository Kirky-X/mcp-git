#!/bin/bash
# 创建测试仓库的脚本

set -e

BASE_DIR="/home/project/mcp-git/temp/test/data/repos"

echo "Creating test repositories..."

# 创建 test-repo-1（小型仓库）
echo "Creating test-repo-1..."
mkdir -p "$BASE_DIR/test-repo-1"
cd "$BASE_DIR/test-repo-1"
git init
git config user.name "Test User"
git config user.email "test@example.com"

echo "# Test Repository 1" > README.md
git add README.md
git commit -m "Initial commit"

mkdir -p src
echo "def main():" > src/main.py
echo "    print('Hello, World!')" >> src/main.py
git add src/main.py
git commit -m "Add main function"

echo "def utility():" > src/utils.py
echo "    return 'utility'" >> src/utils.py
git add src/utils.py
git commit -m "Add utility function"

git checkout -b develop
echo "# Development branch" >> README.md
git add README.md
git commit -m "Update README on develop"

git checkout master

# 创建 test-repo-2（中型仓库，包含冲突）
echo "Creating test-repo-2..."
mkdir -p "$BASE_DIR/test-repo-2"
cd "$BASE_DIR/test-repo-2"
git init
git config user.name "Test User"
git config user.email "test@example.com"

echo "# Test Repository 2" > README.md
git add README.md
git commit -m "Initial commit"

# 创建多个提交
for i in {1..20}; do
    echo "Commit $i" >> history.txt
    git add history.txt
    git commit -m "Commit $i"
done

# 创建冲突分支
git checkout -b feature-a
echo "Feature A content" > feature.txt
git add feature.txt
git commit -m "Add feature A"

git checkout master
git checkout -b feature-b
echo "Feature B content" > feature.txt
git add feature.txt
git commit -m "Add feature B"

git checkout master

# 创建 test-repo-lfs（LFS 测试仓库）
echo "Creating test-repo-lfs..."
mkdir -p "$BASE_DIR/test-repo-lfs"
cd "$BASE_DIR/test-repo-lfs"
git init
git config user.name "Test User"
git config user.email "test@example.com"

echo "# Test Repository with LFS" > README.md
git add README.md
git commit -m "Initial commit"

# 创建大文件
dd if=/dev/zero of=large-file.bin bs=1M count=5 2>/dev/null
echo "*.bin filter=lfs diff=lfs merge=lfs -text" > .gitattributes
git add .gitattributes
git commit -m "Configure LFS for binary files"

git lfs install
git lfs track "*.bin"
git add large-file.bin
git commit -m "Add large file with LFS"

echo "Test repositories created successfully!"
echo "Repositories:"
echo "  - $BASE_DIR/test-repo-1"
echo "  - $BASE_DIR/test-repo-2"
echo "  - $BASE_DIR/test-repo-lfs"