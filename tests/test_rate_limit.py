"""
Tests for rate limiting module.
"""

import pytest
import time

from mcp_git.rate_limit import (
    RateLimitConfig,
    RateLimiter,
    SlidingWindowRateLimiter,
    RateLimitMiddleware,
)


class TestRateLimitConfig:
    """Test RateLimitConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = RateLimitConfig()
        assert config.max_requests == 100
        assert config.window_seconds == 60
        assert config.burst_limit == 10

    def test_custom_config(self):
        """Test custom configuration."""
        config = RateLimitConfig(max_requests=50, window_seconds=30, burst_limit=5)
        assert config.max_requests == 50
        assert config.window_seconds == 30
        assert config.burst_limit == 5


class TestRateLimiter:
    """Test RateLimiter (token bucket algorithm)."""

    @pytest.mark.asyncio
    async def test_acquire_success(self):
        """Test successful token acquisition."""
        limiter = RateLimiter(RateLimitConfig(max_requests=10, window_seconds=60))
        # Use unique identifier to avoid interference with other tests
        assert await limiter.acquire("test_acquire_success") is True

    @pytest.mark.asyncio
    async def test_acquire_multiple(self):
        """Test multiple token acquisitions."""
        limiter = RateLimiter(RateLimitConfig(max_requests=10, window_seconds=60))
        for _ in range(10):
            assert await limiter.acquire("test_acquire_multiple") is True

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test rate limit exceeded."""
        limiter = RateLimiter(RateLimitConfig(max_requests=5, window_seconds=60))
        for _ in range(5):
            await limiter.acquire("test_rate_limit_exceeded")

        # Should be rate limited
        assert await limiter.acquire("test_rate_limit_exceeded") is False

    @pytest.mark.asyncio
    async def test_token_refill(self):
        """Test token refill over time."""
        config = RateLimitConfig(max_requests=10, window_seconds=1)  # 1 second window
        limiter = RateLimiter(config)

        # Use all tokens
        for _ in range(10):
            await limiter.acquire("test_1767269139")

        # Should be rate limited
        assert await limiter.acquire("test_1767269139") is False

        # Wait for refill
        time.sleep(1.1)

        # Should be able to acquire again
        assert await limiter.acquire("test_1767269139") is True

    @pytest.mark.asyncio
    async def test_different_identifiers(self):
        """Test rate limiting for different identifiers."""
        limiter = RateLimiter(RateLimitConfig(max_requests=5, window_seconds=60))

        # User A uses all tokens
        for _ in range(5):
            await limiter.acquire("user_a")

        # User A should be rate limited
        assert await limiter.acquire("user_a") is False

        # User B should still be able to acquire
        assert await limiter.acquire("user_b") is True

    @pytest.mark.asyncio
    async def test_get_wait_time(self):
        """Test getting wait time."""
        limiter = RateLimiter(RateLimitConfig(max_requests=10, window_seconds=1))

        # Use all tokens
        for _ in range(10):
            await limiter.acquire("test_1767269139")

        # Get wait time
        wait_time = await limiter.get_wait_time("test_1767269139")
        assert wait_time > 0

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test resetting token bucket."""
        limiter = RateLimiter(RateLimitConfig(max_requests=5, window_seconds=60))

        # Use all tokens
        for _ in range(5):
            await limiter.acquire("test_1767269139")

        # Should be rate limited
        assert await limiter.acquire("test_1767269139") is False

        # Reset
        limiter.reset("test_1767269139")

        # Should be able to acquire again
        assert await limiter.acquire("test_1767269139") is True


class TestSlidingWindowRateLimiter:
    """Test SlidingWindowRateLimiter."""

    @pytest.mark.asyncio
    async def test_check_success(self):
        """Test successful request check."""
        limiter = SlidingWindowRateLimiter(RateLimitConfig(max_requests=10, window_seconds=60))
        assert await limiter.check("test_1767269139") is True

    @pytest.mark.asyncio
    async def test_check_multiple(self):
        """Test multiple request checks."""
        limiter = SlidingWindowRateLimiter(RateLimitConfig(max_requests=10, window_seconds=60))
        for _ in range(10):
            assert await limiter.check("test_1767269139") is True

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test rate limit exceeded."""
        limiter = SlidingWindowRateLimiter(RateLimitConfig(max_requests=5, window_seconds=60))
        for _ in range(5):
            await limiter.check("test_1767269139")

        # Should be rate limited
        assert await limiter.check("test_1767269139") is False

    @pytest.mark.asyncio
    async def test_window_sliding(self):
        """Test sliding window behavior."""
        config = RateLimitConfig(max_requests=5, window_seconds=1)  # 1 second window
        limiter = SlidingWindowRateLimiter(config)

        # Make 5 requests
        for _ in range(5):
            await limiter.check("test_1767269139")

        # Should be rate limited
        assert await limiter.check("test_1767269139") is False

        # Wait for window to slide
        time.sleep(1.1)

        # Should be able to make requests again
        assert await limiter.check("test_1767269139") is True

    @pytest.mark.asyncio
    async def test_different_identifiers(self):
        """Test rate limiting for different identifiers."""
        limiter = SlidingWindowRateLimiter(RateLimitConfig(max_requests=5, window_seconds=60))

        # User A makes 5 requests
        for _ in range(5):
            await limiter.check("user_a")

        # User A should be rate limited
        assert await limiter.check("user_a") is False

        # User B should still be able to make requests
        assert await limiter.check("user_b") is True

    @pytest.mark.asyncio
    async def test_get_wait_time(self):
        """Test getting wait time."""
        limiter = SlidingWindowRateLimiter(RateLimitConfig(max_requests=5, window_seconds=1))

        # Make 5 requests
        for _ in range(5):
            await limiter.check("test_1767269139")

        # Get wait time
        wait_time = await limiter.get_wait_time("test_1767269139")
        assert wait_time > 0

    def test_reset(self):
        """Test resetting request history."""
        limiter = SlidingWindowRateLimiter(RateLimitConfig(max_requests=5, window_seconds=60))

        # Make 5 requests
        for _ in range(5):
            limiter._requests["test_1767269139"].append(time.time())

        # Reset
        limiter.reset("test_1767269139")

        # Should have no requests
        assert len(limiter._requests["test_1767269139"]) == 0


class TestRateLimitMiddleware:
    """Test RateLimitMiddleware."""

    @pytest.mark.asyncio
    async def test_before_request_allowed(self):
        """Test request allowed."""
        limiter = RateLimiter(RateLimitConfig(max_requests=10, window_seconds=60))
        middleware = RateLimitMiddleware(limiter)

        class MockRequest:
            client = type("Client", (), {"host": "127.0.0.1"})()

        allowed, error = await middleware.before_request(MockRequest())
        assert allowed is True
        assert error is None

    @pytest.mark.asyncio
    async def test_before_request_rate_limited(self):
        """Test request rate limited."""
        limiter = RateLimiter(RateLimitConfig(max_requests=5, window_seconds=60))
        middleware = RateLimitMiddleware(limiter)

        class MockRequest:
            client = type("Client", (), {"host": "127.0.0.1"})()

        # Make 5 requests
        for _ in range(5):
            await middleware.before_request(MockRequest())

        # Should be rate limited
        allowed, error = await middleware.before_request(MockRequest())
        assert allowed is False
        assert error is not None

    @pytest.mark.asyncio
    async def test_unblock(self):
        """Test unblocking an identifier."""
        limiter = RateLimiter(RateLimitConfig(max_requests=5, window_seconds=60))
        middleware = RateLimitMiddleware(limiter)

        class MockRequest:
            client = type("Client", (), {"host": "127.0.0.1"})()

        # Block the identifier
        middleware._blocked_identifiers.add("127.0.0.1")

        # Should be blocked
        allowed, _ = await middleware.before_request(MockRequest())
        assert allowed is False

        # Unblock
        middleware.unblock("127.0.0.1")

        # Should be allowed again
        allowed, _ = await middleware.before_request(MockRequest())
        assert allowed is True


class TestGlobalRateLimiter:
    """Test global rate limiter."""

    def test_get_rate_limiter(self):
        """Test getting global rate limiter."""
        from mcp_git.rate_limit import get_rate_limiter

        limiter = get_rate_limiter()
        assert limiter is not None
        assert isinstance(limiter, RateLimiter)

    def test_get_rate_limiter_singleton(self):
        """Test that global rate limiter is a singleton."""
        from mcp_git.rate_limit import get_rate_limiter

        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2