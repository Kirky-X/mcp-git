"""
Input validation utilities for mcp-git.

Provides decorators and utilities for validating input arguments
to prevent security issues and ensure data integrity.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from loguru import logger
from pydantic import BaseModel, ValidationError


def validate_args(schema: type[BaseModel]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to validate function arguments using a Pydantic schema.

    Args:
        schema: A Pydantic BaseModel class for validation

    Returns:
        Decorator function

    Example:
        @dataclass
        class CloneOptions(BaseModel):
            url: str
            branch: str | None = None

        @validate_args(CloneOptions)
        async def clone_repository(url: str, branch: str | None = None):
            # implementation
            pass
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                # Validate arguments against schema
                schema(**kwargs)
                return await func(*args, **kwargs)
            except ValidationError as e:
                logger.error(f"Validation error for {func.__name__}: {e}")
                raise ValueError(f"Invalid arguments: {e}") from e

        return wrapper

    return decorator


def validate_length(field_name: str, max_length: int) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to validate that a string field does not exceed maximum length.

    Args:
        field_name: Name of the field to validate
        max_length: Maximum allowed length

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            value = kwargs.get(field_name)
            if value and isinstance(value, str) and len(value) > max_length:
                raise ValueError(
                    f"{field_name} exceeds maximum length of {max_length} characters"
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def validate_not_empty(field_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to validate that a field is not empty.

    Args:
        field_name: Name of the field to validate

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            value = kwargs.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"{field_name} cannot be empty")
            return await func(*args, **kwargs)

        return wrapper

    return decorator
