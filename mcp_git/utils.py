"""
Utility functions for mcp-git.

This module provides common utility functions for input sanitization,
path validation, and other helper functions used throughout the application.
"""

import re
import unicodedata
from pathlib import Path

from loguru import logger

# Maximum allowed input length
MAX_INPUT_LENGTH = 1000

# Maximum allowed lengths for specific inputs
MAX_BRANCH_NAME_LENGTH = 255
MAX_COMMIT_MESSAGE_LENGTH = 10000
MAX_REMOTE_URL_LENGTH = 2048
MAX_REPO_PATH_LENGTH = 4096

# Dangerous command patterns to block
DANGEROUS_PATTERNS = [
    r"\brm\b",  # Remove commands
    r"\bcat\b",  # Read commands
    r"\bpasswd\b",  # Password files
    r"\betc\b",  # System files
    r"\bsudo\b",  # Privilege escalation
    r"\bchmod\b",  # Permission changes
    r"\bchown\b",  # Ownership changes
    r"\bmkdir\b",  # Directory creation
    r"\brmdir\b",  # Directory removal
    r"\bwget\b",  # Download commands
    r"\bcurl\b",  # HTTP requests
    r"\bnc\b",  # Netcat
    r"\bncat\b",  # Netcat alternatives
    r"\bbash\b",  # Shell execution
    r"\bsh\b",  # Shell execution
    r"\bpython\b",  # Python execution
    r"\bperl\b",  # Perl execution
    r"\bruby\b",  # Ruby execution
    r"\bnpm\b",  # Package manager
    r"\byarn\b",  # Package manager
    r"\bpip\b",  # Python package manager
]


def sanitize_input(input_str: str) -> str:
    """Sanitize user input to prevent command injection.

    This function removes or escapes potentially dangerous characters
    and patterns from user input.

    Args:
        input_str: The input string to sanitize

    Returns:
        Sanitized input string

    Examples:
        >>> sanitize_input("normal input")
        'normal input'
        >>> sanitize_input("test; rm -rf /")
        'test  '
    """
    if not input_str:
        return input_str

    # Unicode normalization to prevent homograph attacks
    result = unicodedata.normalize("NFKC", input_str)

    # Truncate to max length
    result = result[:MAX_INPUT_LENGTH]

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


def sanitize_path(path: Path, base: Path) -> Path:
    """Sanitize and validate a path against a base directory.

    This function ensures that the provided path is within the allowed
    base directory and prevents path traversal attacks, including
    protection against symlink-based attacks.

    Args:
        path: The path to sanitize
        base: The base directory that the path must be within

    Returns:
        The resolved path if it's within the base directory

    Raises:
        ValueError: If the path would traverse outside the base directory

    Examples:
        >>> from pathlib import Path
        >>> sanitize_path(Path("/safe/base/file.txt"), Path("/safe/base"))
        PosixPath('/safe/base/file.txt')
        >>> sanitize_path(Path("/safe/base/../../../etc/passwd"), Path("/safe/base"))
        Traceback (most recent call last):
            ...
        ValueError: Path traversal attempt detected
    """
    # Resolve base to absolute path (no symlinks)
    base = base.resolve(strict=False)

    # Convert path to absolute without resolving symlinks
    if not path.is_absolute():
        path = (base / path).absolute()

    # Check for suspicious patterns before resolving
    path_str = str(path)
    suspicious_patterns = [
        (r"\.\./", "Path traversal attempt detected"),  # Directory traversal
        (r"/\./", "Suspicious path pattern detected"),  # Current directory reference
        (
            r"//",
            "Suspicious path pattern detected",
        ),  # Double slashes (except at start for absolute paths)
    ]

    for pattern, error_msg in suspicious_patterns:
        if re.search(pattern, path_str) and not (pattern == r"//" and path_str.startswith("//")):
            raise ValueError(error_msg)

    # Check if any component is a symlink (security check)
    for parent in path.parents:
        if parent == Path("/"):
            break
        if parent.exists() and parent.is_symlink():
            raise ValueError(f"Symlink detected in path: {parent}")

    # Now resolve to get the actual location (this will follow symlinks)
    try:
        target = path.resolve(strict=False)
    except FileNotFoundError:
        # Path doesn't exist yet (for new files), resolve parent
        parent = path.parent.resolve(strict=False)
        target = parent / path.name

    # Check if the resolved path is within the base directory
    try:
        target.relative_to(base)
    except ValueError as e:
        raise ValueError(f"Path traversal attempt detected: {path} is outside {base}") from e

    return target


def sanitize_branch_name(name: str) -> str:
    """Sanitize a Git branch name.

    Args:
        name: The branch name to sanitize

    Returns:
        Sanitized branch name

    Raises:
        ValueError: If the branch name is invalid
    """
    if not name:
        raise ValueError("Branch name cannot be empty")

    # Check length before processing
    if len(name) > MAX_BRANCH_NAME_LENGTH:
        raise ValueError(
            f"Branch name too long: {len(name)} characters (max {MAX_BRANCH_NAME_LENGTH})"
        )

    # Remove any shell metacharacters
    result = re.sub(r'[;&|`$(){}[\]<>\\"\']', "", name)

    # Remove leading/trailing whitespace
    result = result.strip()

    if not result:
        raise ValueError("Branch name contains only invalid characters")

    # Check for reserved names
    reserved = ["HEAD", "FETCH_HEAD", "ORIG_HEAD", "ORIGIN_HEAD"]
    if result in reserved:
        raise ValueError(f"Reserved branch name: {result}")

    return result


def sanitize_commit_message(message: str) -> str:
    """Sanitize a Git commit message.

    Args:
        message: The commit message to sanitize

    Returns:
        Sanitized commit message
    """
    # Remove null bytes
    result = message.replace("\0", "")

    # Limit length (Git hard limit is 72 chars for body, but we allow more)
    result = result[:10000]

    return result.strip()


def sanitize_remote_url(url: str) -> str:
    """Sanitize and validate a Git remote URL.

    This function validates Git URLs against a strict protocol whitelist
    to prevent SSRF (Server-Side Request Forgery) and other attacks.

    Args:
        url: The remote URL to sanitize

    Returns:
        Sanitized remote URL

    Raises:
        ValueError: If the URL is invalid or uses an unsupported protocol
    """
    # Check length before processing
    if len(url) > MAX_REMOTE_URL_LENGTH:
        raise ValueError(
            f"Remote URL too long: {len(url)} characters (max {MAX_REMOTE_URL_LENGTH})"
        )

    # Check for obvious injection patterns
    dangerous_patterns = [
        r'[;&|`$(){}[\]<>\\"\']',
        r"\n",
        r"\r",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, url):
            raise ValueError(f"Invalid characters in URL: {url}")

    # Basic URL validation
    url = url.strip()

    if not url:
        raise ValueError("URL cannot be empty")

    # Strict protocol whitelist for security
    # Only allow secure protocols and standard Git protocols
    ALLOWED_PROTOCOLS = [
        "https://",  # HTTPS (recommended)
        "http://",  # HTTP (less secure but common)
        "git://",  # Git protocol
        "ssh://",  # SSH protocol
        "git@",  # SSH shorthand (git@github.com:user/repo.git)
        "/",  # Local file path
    ]

    url_lower = url.lower()
    if not any(url_lower.startswith(prefix) for prefix in ALLOWED_PROTOCOLS):
        raise ValueError(
            f"Invalid URL format or unsupported protocol: {url}. "
            f"Allowed protocols: {', '.join(ALLOWED_PROTOCOLS)}"
        )

    # Additional validation for HTTP/HTTPS URLs
    if url_lower.startswith(("http://", "https://")):
        # Prevent SSRF by blocking localhost and private IPs
        import ipaddress
        import socket
        from urllib.parse import urlparse

        # Extract hostname from URL
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname

            if hostname:
                # Block localhost variants including obfuscated forms
                localhost_patterns = [
                    "localhost",
                    "127.0.0.1",
                    "::1",
                    "0.0.0.0",
                    "127.0.0.2",  # Other loopback addresses
                    "127.1",
                    "127.1.1.1",
                    "127.0.0.1",
                    "0177.0.0.1",  # Octal
                    "0x7f.0.0.1",  # Hex
                    "2130706433",  # Decimal
                ]

                hostname_lower = hostname.lower()
                if hostname_lower in localhost_patterns:
                    raise ValueError(f"Localhost URLs are not allowed for security reasons: {url}")

                # Block private IP ranges
                try:
                    ip = ipaddress.ip_address(hostname)
                    if ip.is_loopback or ip.is_link_local or ip.is_private or ip.is_reserved:
                        raise ValueError(f"Private/local IP addresses are not allowed: {hostname}")
                except ValueError:
                    # Not an IP address, might be a hostname - resolve to check for DNS rebinding
                    try:
                        # Resolve both IPv4 and IPv6
                        addr_info = socket.getaddrinfo(hostname, None)
                        for addr in addr_info:
                            try:
                                ip = ipaddress.ip_address(addr[4][0])
                                if ip.is_loopback or ip.is_link_local or ip.is_private or ip.is_reserved:
                                    raise ValueError(
                                        f"Hostname resolves to private/local IP: {hostname} -> {ip}"
                                    )
                            except (ValueError, IndexError):
                                continue
                    except socket.gaierror:
                        # DNS resolution failed, but hostname might be valid
                        pass

                # Block file:// protocol explicitly
                if parsed.scheme == "file":
                    raise ValueError(f"file:// protocol is not allowed: {url}")

        except Exception as e:
            logger.warning(f"Failed to parse URL hostname: {e}")
            raise ValueError(f"Invalid URL: {e}") from e

    return url


def escape_git_output(output: str) -> str:
    """Escape special characters in Git output for safe display.

    Args:
        output: The Git output to escape

    Returns:
        Escaped output safe for display
    """
    # Replace potentially dangerous characters
    result = output.replace("\x00", "")
    return result


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """Truncate text to a maximum length.

    Args:
        text: The text to truncate
        max_length: Maximum length of the result
        suffix: Suffix to add when truncating

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def format_bytes(size: int | float) -> str:
    """Format bytes into human-readable format.

    Args:
        size: Size in bytes

    Returns:
        Formatted size string
    """
    size = float(size)  # Ensure size is a float for division
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

    return f"{size:.2f} PB"
