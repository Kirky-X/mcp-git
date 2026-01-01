#!/bin/bash
# 主运行器：执行所有验证脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 打印函数
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 清理函数
cleanup() {
    print_info "清理临时文件..."
    rm -rf /tmp/test-clone /tmp/test-init /tmp/workflow-test /tmp/ai-review-test /tmp/bug-fix-test /tmp/repo-sync-main /tmp/repo-sync-fork /tmp/team-collab-test
    print_success "清理完成"
}

# 主流程
main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}mcp-git 全面验证${NC}"
    echo -e "${GREEN}========================================${NC}\n"

    # 记录开始时间
    START_TIME=$(date +%s)

    # 1. UAT 验证
    print_header "1. 用户验收测试（UAT）"
    if bash "$SCRIPT_DIR/scripts/uat_validator.sh"; then
        print_success "UAT 验证通过"
        UAT_STATUS=0
    else
        print_error "UAT 验证失败"
        UAT_STATUS=1
    fi

    # 2. 功能接口验证
    print_header "2. 功能接口验证"
    if PYTHONPATH=/home/project/mcp-git python3 "$SCRIPT_DIR/scripts/api_validator_simple.py"; then
        print_success "功能接口验证通过"
        API_STATUS=0
    else
        print_error "功能接口验证失败"
        API_STATUS=1
    fi

    # 3. 场景测试
    print_header "3. 场景测试"
    if bash "$SCRIPT_DIR/scripts/scenario_validator.sh"; then
        print_success "场景测试通过"
        SCENARIO_STATUS=0
    else
        print_error "场景测试失败"
        SCENARIO_STATUS=1
    fi

    # 清理临时文件
    cleanup

    # 计算总耗时
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # 打印最终总结
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}全面验证总结${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "总耗时: ${DURATION}s"
    echo -e ""
    echo -e "UAT 验证: $([ $UAT_STATUS -eq 0 ] && echo "${GREEN}通过${NC}" || echo "${RED}失败${NC}")"
    echo -e "功能接口验证: $([ $API_STATUS -eq 0 ] && echo "${GREEN}通过${NC}" || echo "${RED}失败${NC}")"
    echo -e "场景测试: $([ $SCENARIO_STATUS -eq 0 ] && echo "${GREEN}通过${NC}" || echo "${RED}失败${NC}")"
    echo -e ""

    # 判断整体状态
    if [ $UAT_STATUS -eq 0 ] && [ $API_STATUS -eq 0 ] && [ $SCENARIO_STATUS -eq 0 ]; then
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}所有验证通过！${NC}"
        echo -e "${GREEN}========================================${NC}\n"
        exit 0
    else
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}部分验证失败，请检查上述输出${NC}"
        echo -e "${RED}========================================${NC}\n"
        exit 1
    fi
}

# 执行主流程
main