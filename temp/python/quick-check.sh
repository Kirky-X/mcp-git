#!/bin/bash

# Python 项目快速 CI 预检脚本
# 使用方法: ./quick-check.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 统计
FAILED=0

# Python 命令
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  ⚡ 快速 CI 预检 (Python)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 1. 格式检查
echo -ne "${BLUE}[1/5]${NC} 格式检查... "
if command -v ruff &> /dev/null; then
    if ruff format --check . > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
    fi
elif command -v black &> /dev/null; then
    if black --check . > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW}⊘${NC} (未安装)"
fi

# 2. Import 排序
echo -ne "${BLUE}[2/5]${NC} Import 排序... "
if command -v ruff &> /dev/null; then
    if ruff check --select I . > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
    fi
elif command -v isort &> /dev/null; then
    if isort --check-only . > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW}⊘${NC} (未安装)"
fi

# 3. Lint 检查
echo -ne "${BLUE}[3/5]${NC} Lint 检查... "
if command -v ruff &> /dev/null; then
    if ruff check . > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
    fi
elif command -v flake8 &> /dev/null; then
    if flake8 . > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW}⊘${NC} (未安装)"
fi

# 4. 类型检查
echo -ne "${BLUE}[4/5]${NC} 类型检查... "
if command -v mypy &> /dev/null; then
    if mypy . > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW}⊘${NC} (未安装)"
fi

# 5. 测试
echo -ne "${BLUE}[5/5]${NC} 运行测试... "
if command -v pytest &> /dev/null; then
    if pytest > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW}⊘${NC} (未安装)"
fi

echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✨ 所有检查通过！${NC}"
    exit 0
else
    echo -e "${RED}⚠️  ${FAILED} 项检查失败${NC}"
    echo ""
    echo "运行详细检查脚本查看问题："
    echo -e "  ${YELLOW}./pre-commit-check.sh${NC}"
    echo ""
    echo "或运行自动修复："
    echo -e "  ${YELLOW}./fix-issues.sh${NC}"
    exit 1
fi
