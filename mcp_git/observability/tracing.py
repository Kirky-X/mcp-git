"""
Distributed tracing module for mcp-git.

This module provides distributed tracing functionality for observability.
"""

import contextvars
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator
from uuid import UUID

from loguru import logger


# Context variable for current span
current_span: contextvars.ContextVar[Span | None] = contextvars.ContextVar("current_span", default=None)


@dataclass
class Span:
    """A span in a distributed trace."""

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: str | None = None
    operation_name: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    tags: dict[str, Any] = field(default_factory=dict)
    status_code: int = 0
    status_message: str = ""
    children: list["Span"] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Get span duration in milliseconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration,
            "tags": self.tags,
            "status_code": self.status_code,
            "status_message": self.status_message,
            "children": [child.to_dict() for child in self.children],
        }


class Tracer:
    """
    Distributed tracer.

    This tracer manages spans and provides distributed tracing functionality.
    """

    def __init__(self):
        """Initialize the tracer."""
        self._spans: dict[str, Span] = {}
        self._root_spans: list[Span] = []

    def start_span(
        self,
        operation_name: str,
        parent_span_id: str | None = None,
        tags: dict[str, Any] | None = None,
    ) -> Span:
        """
        Start a new span.

        Args:
            operation_name: Name of the operation
            parent_span_id: Parent span ID
            tags: Span tags

        Returns:
            Started span
        """
        span = Span(
            operation_name=operation_name,
            parent_span_id=parent_span_id,
            tags=tags or {},
        )

        # Inherit trace ID from parent
        if parent_span_id:
            parent = self._spans.get(parent_span_id)
            if parent:
                span.trace_id = parent.trace_id
                parent.children.append(span)

        self._spans[span.span_id] = span

        # If no parent, this is a root span
        if parent_span_id is None:
            self._root_spans.append(span)

        # Set as current span
        current_span.set(span)

        logger.debug(
            "Span started",
            trace_id=span.trace_id,
            span_id=span.span_id,
            operation=operation_name,
        )

        return span

    def finish_span(
        self,
        span_id: str,
        status_code: int = 0,
        status_message: str = "",
    ) -> None:
        """
        Finish a span.

        Args:
            span_id: Span ID
            status_code: Status code
            status_message: Status message
        """
        span = self._spans.get(span_id)
        if span:
            span.end_time = time.time()
            span.status_code = status_code
            span.status_message = status_message

            logger.debug(
                "Span finished",
                trace_id=span.trace_id,
                span_id=span.span_id,
                duration_ms=span.duration,
                status_code=status_code,
            )

    def get_current_span(self) -> Span | None:
        """Get the current span."""
        return current_span.get()

    def get_trace(self, trace_id: str) -> list[Span]:
        """
        Get all spans in a trace.

        Args:
            trace_id: Trace ID

        Returns:
            List of spans in the trace
        """
        return [span for span in self._spans.values() if span.trace_id == trace_id]

    def get_root_spans(self) -> list[Span]:
        """Get all root spans."""
        return self._root_spans

    def clear(self) -> None:
        """Clear all spans."""
        self._spans.clear()
        self._root_spans.clear()
        current_span.set(None)


# Global tracer instance
_global_tracer: Tracer | None = None


def get_tracer() -> Tracer:
    """
    Get the global tracer instance.

    Returns:
        Global tracer
    """
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = Tracer()
    return _global_tracer


@asynccontextmanager
async def trace(
    operation_name: str,
    tags: dict[str, Any] | None = None,
) -> AsyncGenerator[Span, None]:
    """
    Context manager for tracing an operation.

    Args:
        operation_name: Name of the operation
        tags: Span tags

    Yields:
        The span
    """
    tracer = get_tracer()
    parent_span = tracer.get_current_span()
    parent_span_id = parent_span.span_id if parent_span else None

    span = tracer.start_span(
        operation_name=operation_name,
        parent_span_id=parent_span_id,
        tags=tags,
    )

    try:
        yield span
        tracer.finish_span(span.span_id, status_code=0, status_message="OK")
    except Exception as e:
        tracer.finish_span(span.span_id, status_code=1, status_message=str(e))
        raise


def trace_sync(
    operation_name: str,
    tags: dict[str, Any] | None = None,
):
    """
    Decorator for tracing synchronous functions.

    Args:
        operation_name: Name of the operation
        tags: Span tags

    Returns:
        Decorator function
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            parent_span = tracer.get_current_span()
            parent_span_id = parent_span.span_id if parent_span else None

            span = tracer.start_span(
                operation_name=operation_name,
                parent_span_id=parent_span_id,
                tags=tags,
            )

            try:
                result = func(*args, **kwargs)
                tracer.finish_span(span.span_id, status_code=0, status_message="OK")
                return result
            except Exception as e:
                tracer.finish_span(span.span_id, status_code=1, status_message=str(e))
                raise

        return wrapper

    return decorator


def trace_async(
    operation_name: str,
    tags: dict[str, Any] | None = None,
):
    """
    Decorator for tracing asynchronous functions.

    Args:
        operation_name: Name of the operation
        tags: Span tags

    Returns:
        Decorator function
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            parent_span = tracer.get_current_span()
            parent_span_id = parent_span.span_id if parent_span else None

            span = tracer.start_span(
                operation_name=operation_name,
                parent_span_id=parent_span_id,
                tags=tags,
            )

            try:
                result = await func(*args, **kwargs)
                tracer.finish_span(span.span_id, status_code=0, status_message="OK")
                return result
            except Exception as e:
                tracer.finish_span(span.span_id, status_code=1, status_message=str(e))
                raise

        return wrapper

    return decorator


def add_span_tag(key: str, value: Any) -> None:
    """
    Add a tag to the current span.

    Args:
        key: Tag key
        value: Tag value
    """
    span = current_span.get()
    if span:
        span.tags[key] = value


def set_span_status(status_code: int, status_message: str) -> None:
    """
    Set the status of the current span.

    Args:
        status_code: Status code
        status_message: Status message
    """
    span = current_span.get()
    if span:
        span.status_code = status_code
        span.status_message = status_message