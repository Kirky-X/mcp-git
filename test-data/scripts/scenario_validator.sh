#!/bin/bash
# 场景测试脚本
# 模拟真实使用场景的端到端测试

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 统计变量
TOTAL_SCENARIOS=0
PASSED_SCENARIOS=0
FAILED_SCENARIOS=0

# 打印函数
print_header() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}\n"
}

print_scenario() {
    echo -e "${YELLOW}[SCENARIO]${NC} $1"
    TOTAL_SCENARIOS=$((TOTAL_SCENARIOS + 1)) || true
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    PASSED_SCENARIOS=$((PASSED_SCENARIOS + 1)) || true
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    FAILED_SCENARIOS=$((FAILED_SCENARIOS + 1)) || true
}

print_summary() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}场景测试总结${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "总场景数: $TOTAL_SCENARIOS"
    echo -e "${GREEN}通过: $PASSED_SCENARIOS${NC}"
    echo -e "${RED}失败: $FAILED_SCENARIOS${NC}"
    echo -e "通过率: $(awk "BEGIN {printf \"%.2f\", ($PASSED_SCENARIOS/$TOTAL_SCENARIOS)*100}")%"
    echo -e "${GREEN}========================================${NC}\n"

    if [ $FAILED_SCENARIOS -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# 场景 1: AI 代码审查助手
scenario_ai_code_review() {
    print_scenario "场景 1: AI 代码审查助手"

    cd /tmp
    rm -rf ai-review-test
    mkdir ai-review-test
    cd ai-review-test

    # 初始化仓库
    git init > /dev/null 2>&1
    git config user.name "AI Reviewer"
    git config user.email "ai@example.com"

    # 创建初始代码
    cat > main.py << 'EOF'
def calculate(a, b):
    return a + b
EOF
    git add main.py
    git commit -m "Initial implementation" > /dev/null 2>&1

    # 模拟 AI 审查：查看历史
    if git log --oneline > /dev/null 2>&1; then
        print_pass "查看提交历史"
    else
        print_fail "查看提交历史"
        return 1
    fi

    # 模拟 AI 审查：查看差异
    echo "def calculate(a, b):" > main.py
    echo "    result = a + b" >> main.py
    echo "    return result" >> main.py
    git diff main.py > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        print_pass "查看代码差异"
    else
        print_fail "查看代码差异"
        return 1
    fi

    # 模拟 AI 审查：查看 blame
    git add main.py
    git commit -m "Refactor calculate function" > /dev/null 2>&1
    if git blame main.py > /dev/null 2>&1; then
        print_pass "查看代码 blame"
    else
        print_fail "查看代码 blame"
        return 1
    fi

    print_pass "AI 代码审查助手场景完成"
}

# 场景 2: 自动化 Bug 修复
scenario_automated_bug_fix() {
    print_scenario "场景 2: 自动化 Bug 修复"

    cd /tmp
    rm -rf bug-fix-test
    mkdir bug-fix-test
    cd bug-fix-test

    # 初始化仓库
    git init > /dev/null 2>&1
    git config user.name "Bug Fixer"
    git config user.email "fixer@example.com"

    # 创建有 bug 的代码
    cat > app.py << 'EOF'
def divide(a, b):
    return a / b  # Bug: 没有处理除零
EOF
    git add app.py
    git commit -m "Add divide function" > /dev/null 2>&1

    # 切换到修复分支
    if git checkout -b fix/divide-bug > /dev/null 2>&1; then
        print_pass "创建修复分支"
    else
        print_fail "创建修复分支"
        return 1
    fi

    # 修复 bug
    cat > app.py << 'EOF'
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
EOF
    if git add app.py && git commit -m "Fix: Add zero division check" > /dev/null 2>&1; then
        print_pass "提交修复"
    else
        print_fail "提交修复"
        return 1
    fi

    # 切换回主分支
    if git checkout master > /dev/null 2>&1; then
        print_pass "切换回主分支"
    else
        print_fail "切换回主分支"
        return 1
    fi

    # 合并修复
    if git merge fix/divide-bug > /dev/null 2>&1; then
        print_pass "合并修复分支"
    else
        print_fail "合并修复分支"
        return 1
    fi

    print_pass "自动化 Bug 修复场景完成"
}

# 场景 3: 多仓库同步
scenario_multi_repo_sync() {
    print_scenario "场景 3: 多仓库同步"

    cd /tmp
    rm -rf repo-sync-main repo-sync-fork repo-sync-work
    mkdir repo-sync-main repo-sync-fork

    # 创建 bare 主仓库
    cd repo-sync-main
    git init --bare > /dev/null 2>&1

    # 创建第一个工作副本（开发者 1）
    cd /tmp
    git clone repo-sync-main repo-sync-work > /dev/null 2>&1
    cd repo-sync-work
    git config user.name "Developer 1"
    git config user.email "dev1@example.com"

    echo "# Main Repository" > README.md
    git add README.md
    git commit -m "Initial commit" > /dev/null 2>&1
    git push origin master > /dev/null 2>&1

    # 创建 fork（开发者 2）
    cd /tmp/repo-sync-fork
    git init > /dev/null 2>&1
    git config user.name "Fork Repo"
    git config user.email "fork@example.com"

    # 从主仓库获取
    if git fetch /tmp/repo-sync-main master > /dev/null 2>&1; then
        print_pass "从主仓库获取"
    else
        print_fail "从主仓库获取"
        return 1
    fi

    # 合并主仓库的更改
    if git merge FETCH_HEAD > /dev/null 2>&1; then
        print_pass "合并主仓库更改"
    else
        print_fail "合并主仓库更改"
        return 1
    fi

    # 在 fork 中添加更改
    echo "# Fork Repository" >> README.md
    git add README.md
    git commit -m "Update README in fork" > /dev/null 2>&1

    # 推送更改到主仓库
    if git push /tmp/repo-sync-main master > /dev/null 2>&1; then
        print_pass "推送更改到主仓库"
    else
        print_fail "推送更改到主仓库"
        return 1
    fi

    print_pass "多仓库同步场景完成"
}

# 场景 4: 团队协作
scenario_team_collaboration() {
    print_scenario "场景 4: 团队协作"

    cd /tmp
    rm -rf team-collab-test
    mkdir team-collab-test
    cd team-collab-test

    # 初始化共享仓库
    git init --bare shared.git > /dev/null 2>&1

    # 开发者 A 克隆并初始化仓库
    cd /tmp
    git clone shared.git dev-a 2>/dev/null || (
        # 如果克隆失败（空仓库），手动初始化
        mkdir dev-a
        cd dev-a
        git init
        git remote add origin /tmp/team-collab-test/shared.git
    )
    cd dev-a
    git config user.name "Developer A"
    git config user.email "dev-a@example.com"

    # 创建初始提交（如果仓库为空）
    if ! git log -1 > /dev/null 2>&1; then
        echo "# Team Project" > README.md
        git add README.md
        git commit -m "Initial commit" > /dev/null 2>&1
        git push -u origin master > /dev/null 2>&1 || git push origin master > /dev/null 2>&1
    fi

    if git checkout -b feature/login > /dev/null 2>&1; then
        print_pass "开发者 A 创建功能分支"
    else
        print_fail "开发者 A 创建功能分支"
        return 1
    fi

    # 开发者 A 提交代码
    cat > login.py << 'EOF'
def login(username, password):
    return True
EOF
    git add login.py
    git commit -m "Add login feature" > /dev/null 2>&1

    # 开发者 A 推送代码
    if git push origin feature/login > /dev/null 2>&1; then
        print_pass "开发者 A 推送代码"
    else
        print_fail "开发者 A 推送代码"
        return 1
    fi

    # 开发者 B 克隆并创建分支
    cd /tmp
    git clone /tmp/team-collab-test/shared.git dev-b > /dev/null 2>&1
    cd dev-b
    git config user.name "Developer B"
    git config user.email "dev-b@example.com"

    if git checkout -b feature/auth > /dev/null 2>&1; then
        print_pass "开发者 B 创建功能分支"
    else
        print_fail "开发者 B 创建功能分支"
        return 1
    fi

    # 开发者 B 提交代码
    cat > auth.py << 'EOF'
def authenticate(token):
    return True
EOF
    git add auth.py
    git commit -m "Add auth feature" > /dev/null 2>&1

    # 开发者 B 推送代码
    if git push origin feature/auth > /dev/null 2>&1; then
        print_pass "开发者 B 推送代码"
    else
        print_fail "开发者 B 推送代码"
        return 1
    fi

    # 开发者 A 拉取其他开发者的更改
    cd /tmp/dev-a
    if git fetch origin > /dev/null 2>&1; then
        print_pass "开发者 A 拉取远程更改"
    else
        print_fail "开发者 A 拉取远程更改"
        return 1
    fi

    print_pass "团队协作场景完成"
}

# 主执行流程
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}mcp-git 场景测试${NC}"
echo -e "${GREEN}========================================${NC}\n"

# 执行所有场景
scenario_ai_code_review
scenario_automated_bug_fix
scenario_multi_repo_sync
scenario_team_collaboration

# 打印总结
print_summary