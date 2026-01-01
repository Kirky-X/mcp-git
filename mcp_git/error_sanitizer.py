"""
Error message sanitization for mcp-git.

Provides functionality to remove sensitive information from error messages
before they are logged or returned to users.
"""

import re
from typing import Any


class ErrorSanitizer:
    """Sanitizes error messages to remove sensitive information."""

    # Patterns for sensitive information
    SENSITIVE_PATTERNS = [
        # Passwords and tokens
        (r'(password[=:]\s*)\S+', r'\1***'),
        (r'(token[=:]\s*)\S+', r'\1***'),
        (r'(secret[=:]\s*)\S+', r'\1***'),
        (r'(api[_-]?key[=:]\s*)\S+', r'\1***'),
        (r'(access[_-]?token[=:]\s*)\S+', r'\1***'),

        # Git tokens in URLs
        (r'(https?://)[^:]+:(.+?)@', r'\1***:***@'),
        (r'(git@)[^:]+:(.+?)@', r'\1***:***@'),

        # SSH keys
        (r'(-----BEGIN\s+.*?PRIVATE\s+KEY-----).+?(-----END\s+.*?PRIVATE\s+KEY-----)', r'\1***\2'),

        # File paths with sensitive directories
        (r'/home/[^/\s]+/', r'/home/****/'),
        (r'/root/', r'/****/'),
        (r'/Users/[^/\s]+/', r'/Users/****/'),

        # Database connection strings
        (r'(mongodb://)[^:]+:[^@]+@', r'\1***:***@'),
        (r'(postgres://)[^:]+:[^@]+@', r'\1***:***@'),

        # Environment variables
        (r'(ENV\[)[^\]]+\]', r'\1***'),

        # IP addresses (partial masking)
        (r'(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})', r'\1.***.***.\4'),
        (r'(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})', r'\1.***.***.\4'),
    ]

    def __init__(self) -> None:
        """Initialize the error sanitizer."""
        self._compiled_patterns = []
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            # Use re.DOTALL for SSH key patterns to match across multiple lines
            flags = re.IGNORECASE
            if r'PRIVATE\s+KEY-----' in pattern:
                flags |= re.DOTALL
            self._compiled_patterns.append(
                (re.compile(pattern, flags=flags), replacement)
            )

    def sanitize(self, message: str, context: dict[str, Any] | None = None) -> str:
        """
        Sanitize an error message to remove sensitive information.

        Args:
            message: The error message to sanitize
            context: Optional context dictionary for additional sanitization

        Returns:
            The sanitized error message
        """
        if not message:
            return message

        sanitized = message

        # Apply all patterns
        for pattern, replacement in self._compiled_patterns:
            sanitized = pattern.sub(replacement, sanitized)

        # Sanitize context if provided
        if context:
            sanitized = self._sanitize_context(sanitized, context)

        return sanitized

    def _sanitize_context(self, message: str, context: dict[str, Any]) -> str:
        """
        Sanitize sensitive information in context dictionary.

        Args:
            message: The error message
            context: Context dictionary

        Returns:
            Sanitized message with context information removed
        """
        # Remove parameter values from error messages
        if 'parameters' in context:
            # Match parameters: followed by JSON-like structure
            message = re.sub(r'parameters:\s*\{.*?\}', 'parameters: ***', message, flags=re.DOTALL)

        # Remove repo paths
        if 'repo_path' in context and context['repo_path']:
            path = str(context['repo_path'])
            # Mask username in path if present
            message = message.replace(path, '/****/')

        return message

    def sanitize_dict(self, data: dict[str, Any], keys_to_sanitize: list[str] | None = None) -> dict[str, Any]:
        """
        Sanitize specific keys in a dictionary.

        Args:
            data: Dictionary to sanitize
            keys_to_sanitize: List of keys to sanitize (if None, sanitizes all string values)

        Returns:
            Sanitized dictionary
        """
        # Sensitive key patterns that should always be fully masked
        sensitive_key_patterns = [
            'password', 'passwd', 'pwd',
            'token', 'access_token', 'refresh_token',
            'secret', 'api_key', 'apikey',
            'private_key', 'ssh_key',
        ]

        if keys_to_sanitize is None:
            keys_to_sanitize = list(data.keys())

        result = {}
        for key, value in data.items():
            if key in keys_to_sanitize and isinstance(value, str):
                # Check if key name is sensitive
                key_lower = key.lower()
                is_sensitive_key = any(pattern in key_lower for pattern in sensitive_key_patterns)

                if is_sensitive_key:
                    # Fully mask sensitive key values
                    result[key] = '***'
                else:
                    # Apply normal sanitization for non-sensitive keys
                    result[key] = self.sanitize(value)
            else:
                result[key] = value

        return result


# Global error sanitizer instance
error_sanitizer = ErrorSanitizer()
