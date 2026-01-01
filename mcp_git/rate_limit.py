"""
Rate limiting module for mcp-git.

This module provides rate limiting functionality to prevent abuse and
ensure fair resource usage.
"""

import asyncio
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from loguru import logger


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    max_requests: int = 100  # Maximum requests per window
    window_seconds: int = 60  # Time window in seconds
    burst_limit: int = 10  # Maximum burst requests


class RateLimiter:
    """
    Token bucket rate limiter.

    This implementation uses the token bucket algorithm to provide
    smooth rate limiting with burst capability.
    """

    def __init__(self, config: RateLimitConfig | None = None):
        """
        Initialize the rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        self._tokens: dict[str, float] = defaultdict(float)
        self._last_update: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._max_tokens = self.config.max_requests

    async def acquire(self, identifier: str, tokens: int = 1) -> bool:
        """
        Attempt to acquire tokens from the bucket.

        Args:
            identifier: Unique identifier (e.g., client IP, user ID)
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False if rate limited
        """
        async with self._lock:
            now = time.time()

            # Initialize new identifiers with max tokens
            if identifier not in self._last_update:
                self._tokens[identifier] = self._max_tokens
                self._last_update[identifier] = now
            else:
                last_update = self._last_update[identifier]
                elapsed = now - last_update

                # Refill tokens based on elapsed time
                refill_rate = self.config.max_requests / self.config.window_seconds
                self._tokens[identifier] = min(
                    self._max_tokens,
                    self._tokens[identifier] + elapsed * refill_rate,
                )
                self._last_update[identifier] = now

            # Check if we have enough tokens
            if self._tokens[identifier] >= tokens:
                self._tokens[identifier] -= tokens
                return True

            logger.warning(
                "Rate limit exceeded",
                identifier=identifier,
                available=self._tokens[identifier],
                requested=tokens,
            )
            return False

    async def get_wait_time(self, identifier: str, tokens: int = 1) -> float:
        """
        Get the time to wait before next request.

        Args:
            identifier: Unique identifier
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds
        """
        async with self._lock:
            now = time.time()
            last_update = self._last_update.get(identifier, now)
            elapsed = now - last_update

            # Refill tokens based on elapsed time
            refill_rate = self.config.max_requests / self.config.window_seconds
            current = min(
                self._max_tokens,
                self._tokens[identifier] + elapsed * refill_rate,
            )

            if current >= tokens:
                return 0.0

            # Calculate time to refill needed tokens
            needed = tokens - current
            wait_time = needed / refill_rate
            return wait_time

    def reset(self, identifier: str) -> None:
        """
        Reset token bucket for an identifier.

        Args:
            identifier: Unique identifier to reset
        """
        self._tokens[identifier] = self._max_tokens
        self._last_update[identifier] = time.time()


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter.

    This implementation tracks requests in a sliding time window,
    providing more accurate rate limiting.
    """

    def __init__(self, config: RateLimitConfig | None = None):
        """
        Initialize the sliding window rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        self._requests: dict[str, deque] = defaultdict(lambda: deque())
        self._lock = asyncio.Lock()

    async def check(self, identifier: str) -> bool:
        """
        Check if request is allowed.

        Args:
            identifier: Unique identifier

        Returns:
            True if request is allowed, False if rate limited
        """
        async with self._lock:
            now = time.time()
            window_start = now - self.config.window_seconds

            # Get or create request queue for identifier
            requests = self._requests[identifier]

            # Remove requests outside the window
            while requests and requests[0] < window_start:
                requests.popleft()

            # Check if we're within the limit
            if len(requests) < self.config.max_requests:
                requests.append(now)
                return True

            logger.warning(
                "Rate limit exceeded",
                identifier=identifier,
                count=len(requests),
                limit=self.config.max_requests,
            )
            return False

    async def get_wait_time(self, identifier: str) -> float:
        """
        Get the time to wait before next request.

        Args:
            identifier: Unique identifier

        Returns:
            Wait time in seconds
        """
        async with self._lock:
            requests = self._requests[identifier]
            if not requests:
                return 0.0

            # Time until oldest request leaves the window
            oldest = requests[0]
            window_end = oldest + self.config.window_seconds
            wait_time = max(0.0, window_end - time.time())
            return wait_time  # type: ignore[no-any-return]

    def reset(self, identifier: str) -> None:
        """
        Reset request history for an identifier.

        Args:
            identifier: Unique identifier to reset
        """
        self._requests[identifier].clear()


class RateLimitMiddleware:
    """
    Rate limiting middleware for MCP server.

    This middleware applies rate limiting to incoming requests.
    """

    def __init__(
        self,
        limiter: RateLimiter | SlidingWindowRateLimiter | None = None,
        get_identifier: Callable[[Any], str] | None = None,
    ):
        """
        Initialize the rate limit middleware.

        Args:
            limiter: Rate limiter instance
            get_identifier: Function to extract identifier from request
        """
        self.limiter = limiter or SlidingWindowRateLimiter()
        self.get_identifier = get_identifier or self._default_identifier
        self._blocked_identifiers: set[str] = set()

    def _default_identifier(self, request: Any) -> str:
        """
        Default function to extract identifier from request.

        Args:
            request: Request object

        Returns:
            Identifier string
        """
        # Try to get IP address or use a default
        if hasattr(request, "client") and hasattr(request.client, "host"):
            return request.client.host  # type: ignore[no-any-return]
        return "default"  # type: ignore[no-any-return]

    async def before_request(self, request: Any) -> tuple[bool, str | None]:
        """
        Check rate limit before processing request.

        Args:
            request: Request object

        Returns:
            Tuple of (allowed, error_message)
        """
        identifier = self.get_identifier(request)

        # Check if identifier is blocked
        if identifier in self._blocked_identifiers:
            return False, "Request blocked due to repeated rate limit violations"

        # Check rate limit
        if isinstance(self.limiter, RateLimiter):
            allowed = await self.limiter.acquire(identifier)
        else:
            allowed = await self.limiter.check(identifier)

        if not allowed:
            # Track repeated violations
            # In production, you might want to block after N violations
            logger.warning("Rate limit violation", identifier=identifier)
            return False, "Rate limit exceeded. Please try again later."

        return True, None

    def unblock(self, identifier: str) -> None:
        """
        Unblock an identifier.

        Args:
            identifier: Identifier to unblock
        """
        self._blocked_identifiers.discard(identifier)
        if hasattr(self.limiter, "reset"):
            self.limiter.reset(identifier)


# Global rate limiter instance
_global_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """
    Get the global rate limiter instance.

    Returns:
        Global rate limiter
    """
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
    return _global_rate_limiter
