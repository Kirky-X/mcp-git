"""Utility functions for mcp-git."""

import os
import re
from pathlib import Path
from typing import Optional

# Maximum allowed input length
MAX_INPUT_LENGTH = 1000


def sanitize_path(path: Path, base_path: Path | None = None) -> Path:
    """
    Sanitize a path to prevent path traversal attacks.

    Args:
        path: The path to sanitize
        base_path: Optional base path to resolve against

    Returns:
        Sanitized absolute path

    Raises:
        ValueError: If the path would traverse outside the base path
    """
    # Resolve to absolute path
    if base_path:
        # Resolve base path first
        base_path = base_path.resolve()

        # Handle relative paths
        if not path.is_absolute():
            path = base_path / path

    # Resolve the full path
    resolved = path.resolve()

    # If base path is provided, ensure the resolved path is within it
    if base_path:
        try:
            resolved.relative_to(base_path)
        except ValueError:
            raise ValueError(
                f"Path '{path}' would traverse outside allowed directory '{base_path}'"
            )

    return resolved


def sanitize_input(input_str: str) -> str:
    """Sanitize user input to prevent command injection.

    This function removes or escapes potentially dangerous characters
    and patterns from user input.

    Args:
        input_str: The input string to sanitize

    Returns:
        Sanitized input string
    """
    if not input_str:
        return input_str

    # Truncate to max length
    result = input_str[:MAX_INPUT_LENGTH]

    # Remove shell metacharacters
    shell_metacharacters = r'[;&|`$(){}[\]<>\\"\']'
    result = re.sub(shell_metacharacters, "", result)

    # Remove newlines and null bytes
    result = re.sub(r"[\n\r\0]", "", result)

    # Remove dangerous command patterns (including common flag patterns)
    # This handles patterns like "rm -rf", "cat /etc/passwd", etc.
    dangerous_patterns = [
        # Remove rm command with any flags and paths
        r"\brm\b[^\s;]*\s*(?:-[a-z]+|--[a-z-]+)?\s*[^\s;]*",
        # Remove cat command with file paths
        r"\bcat\b\s+/etc/[^\s;]*",
        r"\bcat\b\s+/root/[^\s;]*",
        # Remove passwd command with file paths
        r"\bpasswd\b\s+/etc/[^\s;]*",
        # Remove sudo commands with arguments
        r"\bsudo\b\s+-[a-z]+\s+[^\s;]*",
        # Remove chmod commands
        r"\bchmod\b\s+[0-7]{3,4}\s+[^\s;]*",
        r"\bchown\b\s+[^\s;]+:[^\s;]*\s+[^\s;]*",
        # Remove wget/curl with URLs
        r"\bwget\b\s+https?://[^\s;]*",
        r"\bcurl\b\s+https?://[^\s;]*",
        # Remove nc/netcat with command execution
        r"\bnc\b\s+-[lc]\s+[^\s;]*",
        # Remove bash/sh with -c
        r"\bbash\b\s+-c\s+[^\s;]*",
        r"\bsh\b\s+-c\s+[^\s;]*",
        # Remove python/perl with code execution
        r"\bpython\b\s+-[cE]\s+[^\s;]*",
        r"\bperl\s+-e\s+[^\s;]*",
        # Remove file paths to sensitive locations
        r"/etc/passwd",
        r"/etc/shadow",
        r"/etc/sudoers",
        r"/root/",
        r"/home/",
        # Remove variable expansion
        r"\$",
        r"`",
    ]

    for pattern in dangerous_patterns:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)

    # Remove standalone hyphens that are likely command flags
    result = re.sub(r"(?<!\w)-(?!\w)", "", result)

    # Remove multiple spaces
    result = re.sub(r"\s+", " ", result)

    # Strip leading/trailing whitespace
    result = result.strip()

    return result


def create_workspace_id() -> str:
    """Generate a unique workspace ID."""
    import uuid

    return str(uuid.uuid4())


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


def parse_file_size(size_str: str) -> int:
    """Parse human-readable file size to bytes."""
    size_str = size_str.strip().upper()

    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4,
    }

    for unit, mult in multipliers.items():
        if size_str.endswith(unit):
            try:
                return int(float(size_str[: -len(unit)]) * mult)
            except ValueError:
                pass

    # Try to parse as plain bytes
    try:
        return int(size_str)
    except ValueError:
        raise ValueError(f"Invalid file size: {size_str}")
