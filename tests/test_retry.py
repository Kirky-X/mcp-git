"""Tests for retry utilities in mcp-git."""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_git.retry import (
    RetryConfig,
    RetryPolicy,
    get_retry_policy,
    retry_async,
)


class TestRetryConfig:
    """Tests for RetryConfig class."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            initial_delay=0.5,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False,
        )
        assert config.max_retries == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_get_delay_first_attempt(self):
        """Test delay calculation for first attempt."""
        config = RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=False,
        )
        delay = config.get_delay(0)
        assert delay == 1.0  # initial_delay * 2^0

    def test_get_delay_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=False,
        )
        assert config.get_delay(0) == 1.0  # 1.0 * 2^0
        assert config.get_delay(1) == 2.0  # 1.0 * 2^1
        assert config.get_delay(2) == 4.0  # 1.0 * 2^2
        assert config.get_delay(3) == 8.0  # 1.0 * 2^3

    def test_get_delay_max_cap(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            max_retries=10,
            initial_delay=10.0,
            max_delay=50.0,
            exponential_base=2.0,
            jitter=False,
        )
        # At attempt 3: 10 * 2^3 = 80, should be capped at 50
        assert config.get_delay(3) == 50.0


class TestRetryPolicy:
    """Tests for predefined retry policies."""

    def test_conservative_policy(self):
        """Test conservative retry policy."""
        policy = RetryPolicy.CONSERVATIVE
        assert policy.max_retries == 2
        assert policy.initial_delay == 0.5
        assert policy.max_delay == 10.0

    def test_standard_policy(self):
        """Test standard retry policy."""
        policy = RetryPolicy.STANDARD
        assert policy.max_retries == 3
        assert policy.initial_delay == 1.0
        assert policy.max_delay == 60.0

    def test_aggressive_policy(self):
        """Test aggressive retry policy."""
        policy = RetryPolicy.AGGRESSIVE
        assert policy.max_retries == 5
        assert policy.initial_delay == 2.0
        assert policy.max_delay == 120.0

    def test_network_policy(self):
        """Test network-specific retry policy."""
        policy = RetryPolicy.NETWORK
        assert policy.max_retries == 3
        assert policy.initial_delay == 1.0
        assert policy.max_delay == 30.0

    def test_clone_policy(self):
        """Test clone-specific retry policy."""
        policy = RetryPolicy.CLONE
        assert policy.max_retries == 3
        assert policy.initial_delay == 2.0
        assert policy.max_delay == 120.0
        assert policy.jitter_factor == 0.2


class TestGetRetryPolicy:
    """Tests for get_retry_policy function."""

    def test_clone_policy(self):
        """Test getting clone policy."""
        policy = get_retry_policy("clone")
        assert policy == RetryPolicy.CLONE

    def test_push_policy(self):
        """Test getting push policy."""
        policy = get_retry_policy("push")
        assert policy == RetryPolicy.NETWORK

    def test_pull_policy(self):
        """Test getting pull policy."""
        policy = get_retry_policy("pull")
        assert policy == RetryPolicy.NETWORK

    def test_fetch_policy(self):
        """Test getting fetch policy."""
        policy = get_retry_policy("fetch")
        assert policy == RetryPolicy.NETWORK

    def test_default_policy(self):
        """Test getting default policy for unknown operation."""
        policy = get_retry_policy("unknown")
        assert policy == RetryPolicy.STANDARD


class TestRetryAsync:
    """Tests for retry_async function."""

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """Test retry when operation succeeds on first attempt."""
        mock_func = AsyncMock(return_value="success")

        result = await retry_async(mock_func)
        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry when operation fails then succeeds."""
        mock_func = AsyncMock(side_effect=[Exception("fail"), Exception("fail"), "success"])

        with patch("mcp_git.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await retry_async(mock_func, config=RetryConfig(max_retries=3))

        assert result == "success"
        assert mock_func.call_count == 3
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        """Test when all retries are exhausted."""
        mock_func = AsyncMock(side_effect=Exception("always fails"))

        with pytest.raises(Exception, match="always fails"):
            await retry_async(mock_func, config=RetryConfig(max_retries=2))

        assert mock_func.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_no_retries_on_success(self):
        """Test that delay is not called on successful operation."""
        mock_func = AsyncMock(return_value="success")

        with patch("mcp_git.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await retry_async(mock_func)

        assert result == "success"
        assert mock_sleep.call_count == 0


class TestRetryIntegration:
    """Integration tests for retry mechanism."""

    @pytest.mark.asyncio
    async def test_retry_with_config(self):
        """Test retry with custom configuration."""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return "success"

        config = RetryConfig(
            max_retries=3,
            initial_delay=0.01,  # Short delay for testing
            max_delay=0.1,
            jitter=False,
        )

        with patch("mcp_git.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await retry_async(failing_func, config=config)

        assert result == "success"
        assert call_count == 2
        assert mock_sleep.call_count == 1
        assert mock_sleep.call_args[0][0] == 0.01  # initial_delay

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test that delays follow exponential backoff."""
        call_count = 0
        delays = []

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("fail")
            return "success"

        async def mock_sleep(delay):
            delays.append(delay)

        with patch("mcp_git.retry.asyncio.sleep", side_effect=mock_sleep):
            await retry_async(
                failing_func,
                config=RetryConfig(
                    max_retries=3,
                    initial_delay=1.0,
                    exponential_base=2.0,
                    jitter=False,
                ),
            )

        assert call_count == 3
        assert len(delays) == 2
        assert delays[0] == 1.0  # First retry: 1.0 * 2^0
        assert delays[1] == 2.0  # Second retry: 1.0 * 2^1
