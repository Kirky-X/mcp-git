"""
Retry utilities for mcp-git.

This module provides automatic retry functionality for network operations
with exponential backoff and jitter.
"""

import asyncio
import random
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, TypeVar

from mcp_git.error import (
    ErrorCode,
    McpGitError,
    is_retryable_error,
)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1  # +/- 10% random variation

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = self.initial_delay * (self.exponential_base**attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            variation = delay * self.jitter_factor
            delay = delay + random.uniform(-variation, variation)

        return max(0, delay)


class RetryableError(McpGitError):
    """Error that should trigger a retry."""

    def __init__(
        self,
        message: str,
        details: str | None = None,
        suggestion: str | None = None,
        context: Any | None = None,
    ):
        super().__init__(
            code=ErrorCode.NETWORK_ERROR,
            message=message,
            details=details,
            suggestion=suggestion,
            context=context,
        )


async def retry_async(
    func: Callable[..., T],
    *args,
    config: RetryConfig | None = None,
    **kwargs,
) -> T:
    """Execute a function with automatic retry on failure.

    Args:
        func: Async function to execute
        *args: Positional arguments for the function
        config: Retry configuration (uses default if not provided)
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function

    Raises:
        McpGitError: If all retries fail
    """
    config = config or RetryConfig()

    last_error = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)

        except McpGitError as e:
            last_error = e

            # Check if error is retryable
            if not is_retryable_error(e):
                # Don't retry non-retryable errors
                raise

            # Check if we've exhausted retries
            if attempt >= config.max_retries:
                raise

            # Calculate and apply delay
            delay = config.get_delay(attempt)
            if delay > 0:
                await asyncio.sleep(delay)

            # Log retry attempt
            # (In production, this would use proper logging)
            # print(f"Retry {attempt + 1}/{config.max_retries} after {delay:.2f}s: {e.message}")

        except Exception as e:
            # For unexpected errors, decide whether to retry
            last_error = McpGitError(
                code=ErrorCode.NETWORK_ERROR,
                message=f"Unexpected error: {str(e)}",
                details=str(type(e).__name__),
            )

            if attempt >= config.max_retries:
                raise last_error

            delay = config.get_delay(attempt)
            if delay > 0:
                await asyncio.sleep(delay)

    # Should not reach here, but just in case
    if last_error:
        raise last_error
    raise McpGitError(
        code=ErrorCode.NETWORK_ERROR,
        message="Retry mechanism failed",
    )


def with_retry(config: RetryConfig | None = None) -> Callable:
    """Decorator to add retry behavior to an async function.

    Args:
        config: Retry configuration (uses default if not provided)

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, Any, **kwargs) -> T:
            return await retry_async(func, *args, config=config, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, Any, **kwargs) -> T:
            # For sync functions, run in executor
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(retry_async(func, *args, config=config, **kwargs))
            finally:
                loop.close()

        # Return async version
        return wrapper

    return decorator


class RetryPolicy:
    """Predefined retry policies for common scenarios."""

    # Conservative policy - fewer retries, shorter delays
    CONSERVATIVE = RetryConfig(
        max_retries=2,
        initial_delay=0.5,
        max_delay=10.0,
        exponential_base=2.0,
        jitter_factor=0.05,
    )

    # Standard policy - balanced retries and delays
    STANDARD = RetryConfig(
        max_retries=3,
        initial_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter_factor=0.1,
    )

    # Aggressive policy - more retries, longer delays
    AGGRESSIVE = RetryConfig(
        max_retries=5,
        initial_delay=2.0,
        max_delay=120.0,
        exponential_base=2.0,
        jitter_factor=0.15,
    )

    # Network-only policy - specifically for network operations
    NETWORK = RetryConfig(
        max_retries=3,
        initial_delay=1.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter_factor=0.1,
    )

    # Clone-specific policy - optimized for clone operations
    CLONE = RetryConfig(
        max_retries=3,
        initial_delay=2.0,
        max_delay=120.0,
        exponential_base=2.0,
        jitter_factor=0.2,
    )


def get_retry_policy(operation: str) -> RetryConfig:
    """Get an appropriate retry policy for an operation type.

    Args:
        operation: Type of operation (clone, push, pull, fetch, etc.)

    Returns:
        RetryConfig instance
    """
    policies = {
        "clone": RetryPolicy.CLONE,
        "push": RetryPolicy.NETWORK,
        "pull": RetryPolicy.NETWORK,
        "fetch": RetryPolicy.NETWORK,
    }

    return policies.get(operation.lower(), RetryPolicy.STANDARD)
