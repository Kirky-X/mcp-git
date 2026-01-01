#!/usr/bin/env python3
"""
验证脚本：测试所有新创建的模块功能
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))


def test_error_sanitizer():
    """测试错误信息脱敏功能"""
    print("测试错误信息脱敏功能...")

    from mcp_git.error_sanitizer import error_sanitizer

    # 测试密码脱敏
    message = "Authentication failed: password=secret123"
    sanitized = error_sanitizer.sanitize(message)
    assert "secret123" not in sanitized, "密码应该被脱敏"
    assert "***" in sanitized, "应该包含脱敏标记"

    # 测试 Git token 脱敏
    message = "Clone from https://user:secret123@github.com/repo.git"
    sanitized = error_sanitizer.sanitize(message)
    assert "secret123" not in sanitized, "Git token 应该被脱敏"

    # 测试 SSH 密钥脱敏
    message = """Error loading key: -----BEGIN PRIVATE KEY-----
MIIEpAIBAAKCAQEAz8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8
-----END PRIVATE KEY-----"""
    sanitized = error_sanitizer.sanitize(message)
    assert "MIIEpAIBAAKCAQEA" not in sanitized, "SSH 密钥应该被脱敏"

    print("✓ 错误信息脱敏功能测试通过")
    return True


def test_credential_manager():
    """测试凭证管理功能"""
    print("测试凭证管理功能...")

    from pydantic import SecretStr

    from mcp_git.service.credential_manager import AuthType, Credential, CredentialManager

    # 创建凭证管理器
    manager = CredentialManager()

    # 设置凭证
    credential = Credential(
        auth_type=AuthType.TOKEN,
        token=SecretStr("test_token_123"),
        username="test_user",
    )
    manager.set_credential(credential)

    # 获取凭证
    retrieved = manager.get_credential()
    assert retrieved is not None, "应该能够获取凭证"
    assert retrieved.auth_type == AuthType.TOKEN, "认证类型应该匹配"
    assert retrieved.get_username() == "test_user", "用户名应该匹配"

    # 获取凭证统计信息
    stats = manager.get_credential_stats()
    assert stats is not None, "应该能够获取凭证统计信息"
    assert "access_count" in stats, "统计信息应该包含访问计数"

    # 清除凭证
    manager.clear_credential()
    assert manager.get_credential() is None, "凭证应该被清除"

    print("✓ 凭证管理功能测试通过")
    return True


def test_audit_logger():
    """测试审计日志功能"""
    print("测试审计日志功能...")

    from mcp_git.audit import AuditEvent, AuditEventType, AuditLogger, AuditSeverity

    # 创建审计日志记录器
    logger = AuditLogger()

    # 创建审计事件
    event = AuditEvent(
        event_type=AuditEventType.GIT_CLONE,
        severity=AuditSeverity.INFO,
        user_id="test_user",
        details={"repo_url": "https://github.com/user/repo.git"},
    )

    # 记录事件
    logger.log_event(event)

    # 查询事件
    events = logger.query_events(event_type=AuditEventType.GIT_CLONE)
    assert len(events) == 1, "应该能够查询到事件"
    assert events[0]["event_type"] == "git_clone", "事件类型应该匹配"

    # 获取统计信息
    stats = logger.get_statistics()
    assert stats["total_events"] == 1, "统计信息应该显示 1 个事件"

    # 获取安全事件
    security_events = logger.get_security_events(hours=24)
    assert isinstance(security_events, list), "安全事件应该是一个列表"

    print("✓ 审计日志功能测试通过")
    return True


def test_metrics():
    """测试指标收集功能"""
    print("测试指标收集功能...")

    from mcp_git.metrics import MetricsCollector

    # 创建指标收集器
    collector = MetricsCollector()

    # 记录任务开始
    collector.record_task_start("task-1", "clone")
    assert "task-1" in collector._task_start_times, "任务应该被记录"

    # 记录任务完成
    import time

    time.sleep(0.1)
    collector.record_task_complete("task-1", "success")
    assert "task-1" not in collector._task_start_times, "任务完成后应该被移除"

    # 跟踪 Git 操作
    collector.record_git_operation("clone", "success")

    print("✓ 指标收集功能测试通过")
    return True


def test_validation():
    """测试输入验证功能"""
    print("测试输入验证功能...")

    import asyncio

    from mcp_git.validation import BaseModel, ValidationError, validate_args

    # 创建验证 schema
    class UserInput(BaseModel):
        name: str
        email: str

    # 创建验证装饰器
    @validate_args(UserInput)
    async def process_user(name: str, email: str) -> str:
        return f"Processing user {name} with email {email}"

    # 测试有效输入
    result = asyncio.run(process_user(name="test", email="test@example.com"))
    assert "test" in result, "应该能够处理有效输入"

    print("✓ 输入验证功能测试通过")
    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("开始验证所有新创建的模块功能")
    print("=" * 60)
    print()

    tests = [
        ("错误信息脱敏", test_error_sanitizer),
        ("凭证管理", test_credential_manager),
        ("审计日志", test_audit_logger),
        ("指标收集", test_metrics),
        ("输入验证", test_validation),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"✗ {name}测试失败")
        except Exception as e:
            failed += 1
            print(f"✗ {name}测试失败: {e}")
            import traceback

            traceback.print_exc()

    print()
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed == 0:
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print(f"\n✗ 有 {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
