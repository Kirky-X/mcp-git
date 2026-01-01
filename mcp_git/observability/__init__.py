"""
Observability module for mcp-git.

This module provides observability features including tracing and metrics.
"""

from mcp_git.observability.tracing import (
    Span,
    Tracer,
    add_span_tag,
    get_tracer,
    set_span_status,
    trace,
    trace_async,
    trace_sync,
)

__all__ = [
    "Span",
    "Tracer",
    "get_tracer",
    "trace",
    "trace_async",
    "trace_sync",
    "add_span_tag",
    "set_span_status",
]
