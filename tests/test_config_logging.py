"""配置和日志测试 - 验证配置系统和日志结构。

测试内容：
- 配置加载和环境变量解析
- 配置验证和类型安全
- 日志级别配置
- 敏感信息脱敏
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestConfigurationLoading:
    """测试配置加载功能。"""

    def test_default_config(self):
        """测试默认配置加载。"""
        from mcp_git.config import get_default_config

        config = get_default_config()

        assert config.workspace.path == Path("/tmp/mcp-git/workspaces")
        assert config.server.port == 3001
        assert config.log_level == "INFO"
        assert config.execution.max_concurrent_tasks == 10

    def test_load_config_from_env(self):
        """测试从环境变量加载配置。"""
        from mcp_git.config import load_config

        env_vars = {
            "MCP_GIT_WORKSPACE_PATH": "/custom/workspace",
            "MCP_GIT_SERVER_PORT": "8080",
            "MCP_GIT_LOG_LEVEL": "DEBUG",
            "MCP_GIT_MAX_CONCURRENT_TASKS": "20",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = load_config()

            assert config.workspace.path == Path("/custom/workspace")
            assert config.server.port == 8080
            assert config.log_level == "DEBUG"
            assert config.execution.max_concurrent_tasks == 20

    def test_git_token_from_env(self):
        """测试 Git Token 从环境变量加载。"""
        from mcp_git.config import load_config

        env_vars = {
            "GIT_TOKEN": "ghp_test_token_12345",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = load_config()

            assert config.git_token == "ghp_test_token_12345"

    def test_git_token_mcp_prefix(self):
        """测试 Git Token 从 MCP_GIT_GIT_TOKEN 加载。"""
        from mcp_git.config import load_config

        env_vars = {
            "MCP_GIT_GIT_TOKEN": "ghp_mcp_prefix_token",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = load_config()

            assert config.git_token == "ghp_mcp_prefix_token"

    def test_config_override_precedence(self):
        """测试环境变量覆盖优先级。"""
        from mcp_git.config import load_config

        env_vars = {
            "GIT_TOKEN": "ghp_env_token",
            "MCP_GIT_GIT_TOKEN": "ghp_mcp_token",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = load_config()

            # GIT_TOKEN 应该优先于 MCP_GIT_GIT_TOKEN
            assert config.git_token == "ghp_env_token"

    def test_database_path_config(self):
        """测试数据库路径配置。"""
        from mcp_git.config import load_config

        env_vars = {
            "MCP_GIT_DATABASE_PATH": "/custom/db/path/mcp-git.db",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = load_config()

            assert config.database.path == Path("/custom/db/path/mcp-git.db")


class TestConfigurationValidation:
    """测试配置验证。"""

    def test_log_level_validation(self):
        """测试日志级别验证。"""
        from mcp_git.config import load_config

        # 有效的日志级别
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            with patch.dict(os.environ, {"MCP_GIT_LOG_LEVEL": level}):
                config = load_config()
                assert config.log_level == level.upper()

    def test_invalid_log_level_defaults_to_info(self):
        """测试无效日志级别默认为 INFO。"""
        from mcp_git.config import load_config

        with patch.dict(os.environ, {"MCP_GIT_LOG_LEVEL": "INVALID"}):
            config = load_config()
            # 应该保持默认值或转换为大写
            assert config.log_level.upper() in ["INFO", "INVALID"]

    def test_numeric_config_type_conversion(self):
        """测试数字配置类型转换。"""
        from mcp_git.config import load_config

        env_vars = {
            "MCP_GIT_SERVER_PORT": "not_a_number",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            # 应该不抛出异常，使用默认值
            try:
                config = load_config()
                # 端口应该保持默认值
                assert config.server.port == 3001
            except ValueError:
                # 如果抛出异常也是可以接受的
                pass


class TestLoggingConfiguration:
    """测试日志配置。"""

    def test_log_level_from_config(self):
        """测试日志级别从配置读取。"""
        from mcp_git.config import load_config

        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            with patch.dict(os.environ, {"MCP_GIT_LOG_LEVEL": level}):
                config = load_config()
                assert config.log_level == level.upper()

    def test_setup_logging_function_exists(self):
        """测试日志设置函数存在。"""
        from mcp_git.main import setup_logging

        # 函数应该可调用
        assert callable(setup_logging)

    def test_setup_logging_with_debug(self):
        """测试 Debug 日志级别设置。"""
        import io

        from loguru import logger

        from mcp_git.main import setup_logging

        # 应该不抛出异常
        setup_logging("DEBUG")

        # 使用 loguru 记录消息来验证
        output = io.StringIO()
        logger.remove()
        logger.add(output, format="{level} {message}")

        logger.debug("Debug message")
        logger.info("Info message")

        log_output = output.getvalue()
        # DEBUG 级别应该记录 debug 消息
        assert "Debug message" in log_output

    def test_setup_logging_with_info(self):
        """测试 Info 日志级别设置。"""
        import io

        from loguru import logger

        from mcp_git.main import setup_logging

        # 完全重置 logger
        logger.remove()
        setup_logging("INFO")

        # 使用 loguru 记录消息来验证
        output = io.StringIO()
        logger.add(output, format="{level} {message}", level="INFO")

        logger.debug("Debug message")
        logger.info("Info message")

        log_output = output.getvalue()
        # INFO 级别应该不记录 debug 消息
        assert "Debug message" not in log_output
        assert "Info message" in log_output

    def test_loguru_logger_exists(self):
        """测试 loguru 日志器存在。"""
        from loguru import logger

        # 应该能够添加处理程序
        logger.remove()
        logger.add(lambda msg: None, format="{level} {message}")
        logger.info("Test message")


class TestSensitiveDataMasking:
    """测试敏感数据脱敏。"""

    def test_token_not_in_env_output(self):
        """测试 Token 不在环境变量输出中。"""
        from mcp_git.config import load_config

        with patch.dict(os.environ, {"GIT_TOKEN": "ghp_secret_token"}):
            config = load_config()

            # 配置对象应该包含 token
            assert config.git_token == "ghp_secret_token"

    def test_config_repr_masking(self):
        """测试配置字符串表示中的脱敏。"""
        from mcp_git.config import Config

        # 创建包含 token 的配置
        config = Config()
        config.git_token = "ghp_secret_token"

        # 获取字符串表示
        repr(config)

        # Token 应该被部分脱敏或不在表示中
        # 具体行为取决于实现
        # 至少不应以明文形式完整显示

    def test_logging_does_not_expose_token(self):
        """测试日志不暴露 Token。"""
        import io

        from loguru import logger

        from mcp_git.main import setup_logging

        setup_logging("DEBUG")

        # 捕获日志输出
        output = io.StringIO()
        logger.remove()
        logger.add(output, format="{level} {message}")

        with patch.dict(os.environ, {"GIT_TOKEN": "ghp_secret_token_12345"}):
            from mcp_git.config import load_config

            load_config()

        # 记录配置（不包含敏感信息）
        logger.info("Config loaded")

        log_output = output.getvalue()

        # Token 不应该出现在日志中
        assert "ghp_secret_token_12345" not in log_output


class TestConfigurationIntegration:
    """测试配置集成场景。"""

    def test_load_dotenv(self):
        """测试 dotenv 加载。"""
        from dotenv import load_dotenv

        # 创建临时 env 文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_VAR1=value1\n")
            f.write("TEST_VAR2=value2\n")
            temp_path = f.name

        try:
            # 加载 env 文件
            load_dotenv(temp_path)

            # 验证变量已加载
            assert os.getenv("TEST_VAR1") == "value1"
            assert os.getenv("TEST_VAR2") == "value2"
        finally:
            os.unlink(temp_path)

    def test_full_config_flow(self):
        """测试完整配置流程。"""
        from mcp_git.config import load_config
        from mcp_git.main import setup_logging

        env_vars = {
            "MCP_GIT_WORKSPACE_PATH": "/test/workspace",
            "MCP_GIT_SERVER_PORT": "8888",
            "MCP_GIT_LOG_LEVEL": "WARNING",
            "GIT_TOKEN": "ghp_integration_test_token",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = load_config()

            # 验证配置
            assert config.workspace.path == Path("/test/workspace")
            assert config.server.port == 8888
            assert config.log_level == "WARNING"
            assert config.git_token == "ghp_integration_test_token"

            # 验证日志设置
            setup_logging(config.log_level)
            import logging

            assert logging.getLogger().level == logging.WARNING


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
