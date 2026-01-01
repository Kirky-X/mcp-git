#!/bin/bash

# Python 项目本地 CI 预检脚本
# 在提交前运行所有 CI 检查，确保流水线能够通过
# 使用方法: ./pre-commit-check.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 图标
CHECK="✓"
CROSS="✗"
ARROW="→"

# 统计变量
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# 开始时间
START_TIME=$(date +%s)

# 打印标题
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  🐍 Python 项目本地 CI 预检${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# 打印步骤
print_step() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    echo -e "${BLUE}[${TOTAL_CHECKS}/${EXPECTED_CHECKS}]${NC} ${ARROW} $1..."
}

# 打印成功
print_success() {
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    echo -e "${GREEN}  ${CHECK} $1${NC}"
    echo ""
}

# 打印失败
print_error() {
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
    echo -e "${RED}  ${CROSS} $1${NC}"
    echo ""
}

# 打印警告
print_warning() {
    echo -e "${YELLOW}  ⚠ $1${NC}"
    echo ""
}

# 打印信息
print_info() {
    echo -e "  ℹ $1"
}

# 打印分隔线
print_separator() {
    echo -e "${BLUE}────────────────────────────────────────────────────────${NC}"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

# 总检查数
EXPECTED_CHECKS=8

# 打印标题
print_header

# 检查是否在 git 仓库中
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "当前目录不是 git 仓库"
    exit 1
fi

# 检查是否在 Python 项目中
if [ ! -f "pyproject.toml" ] && [ ! -f "setup.py" ] && [ ! -f "setup.cfg" ]; then
    print_error "未找到 pyproject.toml、setup.py 或 setup.cfg，请在 Python 项目根目录运行此脚本"
    exit 1
fi

# 检查 Python
if ! check_command python && ! check_command python3; then
    print_error "未安装 Python"
    exit 1
fi

# 使用 python3 或 python
PYTHON_CMD="python3"
if ! check_command python3; then
    PYTHON_CMD="python"
fi

echo -e "${GREEN}环境检查通过 ${CHECK}${NC}"
echo -e "  Python: $($PYTHON_CMD --version)"
echo ""
print_separator
echo ""

# ============================================================================
# 1. 依赖安装检查
# ============================================================================
print_step "检查并安装依赖"

if [ -f "pyproject.toml" ]; then
    if $PYTHON_CMD -m pip install -e ".[dev,test]" > /tmp/pip_install.log 2>&1; then
        print_success "依赖安装成功"
    else
        print_error "依赖安装失败"
        tail -20 /tmp/pip_install.log
        echo ""
    fi
elif [ -f "requirements.txt" ]; then
    if $PYTHON_CMD -m pip install -r requirements.txt > /tmp/pip_install.log 2>&1; then
        print_success "依赖安装成功"
    else
        print_error "依赖安装失败"
        tail -20 /tmp/pip_install.log
        echo ""
    fi
else
    print_warning "未找到依赖配置文件，跳过依赖安装"
fi

# ============================================================================
# 2. 代码格式检查 (ruff format 或 black)
# ============================================================================
print_step "检查代码格式"

if check_command ruff; then
    if ruff format --check . > /tmp/ruff_format.log 2>&1; then
        print_success "代码格式检查通过 (ruff)"
    else
        print_error "代码格式检查失败 (ruff)"
        print_info "运行以下命令修复格式问题："
        echo -e "  ${YELLOW}ruff format .${NC}"
        echo ""
        head -20 /tmp/ruff_format.log
        echo ""
    fi
elif check_command black; then
    if black --check . > /tmp/black.log 2>&1; then
        print_success "代码格式检查通过 (black)"
    else
        print_error "代码格式检查失败 (black)"
        print_info "运行以下命令修复格式问题："
        echo -e "  ${YELLOW}black .${NC}"
        echo ""
        head -20 /tmp/black.log
        echo ""
    fi
else
    print_warning "未安装 ruff 或 black，跳过格式检查"
    print_info "安装命令: pip install ruff 或 pip install black"
fi

# ============================================================================
# 3. Import 排序检查 (ruff 或 isort)
# ============================================================================
print_step "检查 import 排序"

if check_command ruff; then
    if ruff check --select I . > /tmp/ruff_isort.log 2>&1; then
        print_success "Import 排序检查通过 (ruff)"
    else
        print_error "Import 排序检查失败 (ruff)"
        print_info "运行以下命令修复："
        echo -e "  ${YELLOW}ruff check --select I --fix .${NC}"
        echo ""
    fi
elif check_command isort; then
    if isort --check-only . > /tmp/isort.log 2>&1; then
        print_success "Import 排序检查通过 (isort)"
    else
        print_error "Import 排序检查失败 (isort)"
        print_info "运行以下命令修复："
        echo -e "  ${YELLOW}isort .${NC}"
        echo ""
    fi
else
    print_warning "未安装 ruff 或 isort，跳过 import 排序检查"
fi

# ============================================================================
# 4. Linting 检查 (ruff 或 flake8)
# ============================================================================
print_step "运行 Lint 检查"

if check_command ruff; then
    echo "  (这可能需要一些时间...)"
    if ruff check . > /tmp/ruff_check.log 2>&1; then
        print_success "Ruff lint 检查通过"
    else
        print_error "Ruff lint 发现问题"
        print_info "运行以下命令查看详细信息："
        echo -e "  ${YELLOW}ruff check .${NC}"
        echo ""
        echo "前 20 个问题："
        head -20 /tmp/ruff_check.log
        echo ""
    fi
elif check_command flake8; then
    if flake8 . > /tmp/flake8.log 2>&1; then
        print_success "Flake8 检查通过"
    else
        print_error "Flake8 发现问题"
        head -20 /tmp/flake8.log
        echo ""
    fi
else
    print_warning "未安装 ruff 或 flake8，跳过 lint 检查"
    print_info "安装命令: pip install ruff 或 pip install flake8"
fi

# ============================================================================
# 5. 类型检查 (mypy)
# ============================================================================
print_step "运行类型检查 (mypy)"

if check_command mypy; then
    echo "  (这可能需要一些时间...)"
    if mypy . > /tmp/mypy.log 2>&1; then
        print_success "MyPy 类型检查通过"
    else
        print_error "MyPy 发现类型问题"
        print_info "运行以下命令查看详细信息："
        echo -e "  ${YELLOW}mypy .${NC}"
        echo ""
        echo "前 20 个问题："
        head -20 /tmp/mypy.log
        echo ""
    fi
else
    print_warning "未安装 mypy，跳过类型检查"
    print_info "安装命令: pip install mypy"
fi

# ============================================================================
# 6. 运行测试
# ============================================================================
print_step "运行所有测试"

if check_command pytest; then
    echo "  (这可能需要一些时间...)"
    if pytest -v > /tmp/pytest.log 2>&1; then
        # 提取测试统计
        TEST_STATS=$(grep -E "passed|failed" /tmp/pytest.log | tail -1)
        print_success "所有测试通过"
        if [ -n "$TEST_STATS" ]; then
            print_info "$TEST_STATS"
            echo ""
        fi
    else
        print_error "部分测试失败"
        echo ""
        echo "失败的测试："
        grep -A 10 "FAILED" /tmp/pytest.log | head -30
        echo ""
        print_info "运行以下命令查看详细信息："
        echo -e "  ${YELLOW}pytest -v${NC}"
        echo ""
    fi
else
    print_warning "未安装 pytest，跳过测试"
    print_info "安装命令: pip install pytest"
fi

# ============================================================================
# 7. 安全检查
# ============================================================================
print_step "运行安全检查"

SECURITY_ISSUES=0

# Safety check
if check_command safety; then
    if safety check > /tmp/safety.log 2>&1; then
        print_success "Safety 安全检查通过"
    else
        print_error "Safety 发现安全漏洞"
        SECURITY_ISSUES=1
        head -20 /tmp/safety.log
        echo ""
    fi
else
    print_warning "未安装 safety，跳过依赖安全检查"
    print_info "安装命令: pip install safety"
fi

# Bandit check
if check_command bandit; then
    if bandit -r . -ll > /tmp/bandit.log 2>&1; then
        print_success "Bandit 安全扫描通过"
    else
        if [ $SECURITY_ISSUES -eq 0 ]; then
            print_error "Bandit 发现安全问题"
        fi
        SECURITY_ISSUES=1
        head -20 /tmp/bandit.log
        echo ""
    fi
else
    print_warning "未安装 bandit，跳过代码安全扫描"
    print_info "安装命令: pip install bandit"
fi

# ============================================================================
# 8. 代码覆盖率 (可选)
# ============================================================================
print_step "计算代码覆盖率 (可选)"

if check_command pytest && $PYTHON_CMD -c "import pytest_cov" 2>/dev/null; then
    echo "  (这可能需要较长时间...)"
    echo "  (可以按 Ctrl+C 跳过此步骤)"
    if timeout 300 pytest --cov=. --cov-report=term > /tmp/coverage.log 2>&1; then
        COVERAGE=$(grep -oP '\d+%' /tmp/coverage.log | tail -1)
        if [ -n "$COVERAGE" ]; then
            print_success "代码覆盖率: $COVERAGE"
        else
            print_success "覆盖率计算完成"
        fi
        echo ""
        grep -A 10 "TOTAL" /tmp/coverage.log || true
        echo ""
    else
        if [ $? -eq 124 ]; then
            print_warning "覆盖率计算超时（5分钟），已跳过"
        else
            print_warning "覆盖率计算失败或被跳过"
        fi
    fi
else
    print_warning "未安装 pytest-cov，跳过覆盖率检查"
    print_info "安装命令: pip install pytest-cov"
fi

# ============================================================================
# 总结
# ============================================================================
echo ""
print_separator
echo ""

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo -e "${BLUE}📊 检查结果总结${NC}"
echo ""
echo -e "  总检查数: ${BLUE}${TOTAL_CHECKS}${NC}"
echo -e "  通过: ${GREEN}${PASSED_CHECKS}${NC}"
echo -e "  失败: ${RED}${FAILED_CHECKS}${NC}"
echo -e "  耗时: ${BLUE}${DURATION}${NC} 秒"
echo ""

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✨ 所有检查通过！可以安全提交代码${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}推荐的提交流程：${NC}"
    echo -e "  1. ${YELLOW}git add .${NC}"
    echo -e "  2. ${YELLOW}git commit -m \"your message\"${NC}"
    echo -e "  3. ${YELLOW}git push${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  ⚠️  发现 ${FAILED_CHECKS} 个问题，请修复后再提交${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}修复建议：${NC}"
    echo ""
    
    echo -e "  ${YELLOW}1.${NC} 自动修复格式和 lint 问题："
    echo -e "     ${YELLOW}./fix-issues.sh${NC}"
    echo ""
    
    echo -e "  ${YELLOW}2.${NC} 手动修复其他问题后重新运行检查"
    echo ""
    exit 1
fi
