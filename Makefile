.PHONY: help install dev test lint format check clean serve docs sync

help:
	@echo "mcp-git 开发命令"
	@echo ""
	@echo "使用方法:"
	@echo "  make <command>"
	@echo ""
	@echo "可用命令:"
	@echo "  make install   - 安装生产依赖"
	@echo "  make dev       - 安装开发依赖"
	@echo "  make sync      - 同步依赖（uv sync）"
	@echo "  make test      - 运行所有测试"
	@echo "  make test-cov  - 运行测试并生成覆盖率报告"
	@echo "  make lint      - 运行代码检查（ruff + mypy）"
	@echo "  make format    - 格式化代码（ruff format）"
	@echo "  make check     - 运行预提交检查脚本"
	@echo "  make serve     - 启动 MCP 服务器"
	@echo "  make docs      - 构建文档"
	@echo "  make clean     - 清理临时文件和缓存"
	@echo ""
	@echo "示例:"
	@echo "  make dev && make test"

install:
	uv sync

dev:
	uv sync --extra dev --extra test
	@echo "✓ 开发依赖已安装"

sync:
	uv sync
	@echo "✓ 依赖已同步"

test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ --cov=mcp_git --cov-report=html --cov-report=term
	@echo "✓ 覆盖率报告已生成: htmlcov/index.html"

lint:
	@echo "运行代码检查..."
	uv run ruff check mcp_git/
	uv run mypy mcp_git/
	@echo "✓ 代码检查通过"

format:
	@echo "格式化代码..."
	uv run ruff format .
	@echo "✓ 代码已格式化"

check:
	@echo "运行预提交检查..."
	bash scripts/pre-commit-check.sh

serve:
	@echo "启动 MCP 服务器..."
	uv run mcp-git

docs:
	@echo "构建文档..."
	cd docs && make html
	@echo "✓ 文档已构建: docs/_build/html/index.html"

clean:
	@echo "清理临时文件和缓存..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .benchmarks -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "✓ 清理完成"

# 快捷命令别名
.PHONY: ci
ci: lint test
	@echo "✓ CI 检查通过"

.PHONY: quick
quick: format lint
	@echo "✓ 快速检查完成"
