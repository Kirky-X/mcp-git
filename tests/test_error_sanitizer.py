"""
Tests for error sanitization functionality.
"""

import pytest

from mcp_git.error_sanitizer import ErrorSanitizer, error_sanitizer


class TestErrorSanitizerPasswordAndTokens:
    """Test password and token sanitization."""

    def test_password_in_message(self):
        """Test that passwords are sanitized."""
        message = "Authentication failed: password=secret123"
        sanitized = error_sanitizer.sanitize(message)
        assert "secret123" not in sanitized
        assert "***" in sanitized

    def test_token_in_message(self):
        """Test that tokens are sanitized."""
        message = "Invalid token: token=abc123xyz"
        sanitized = error_sanitizer.sanitize(message)
        assert "abc123xyz" not in sanitized
        assert "***" in sanitized

    def test_secret_in_message(self):
        """Test that secrets are sanitized."""
        message = "Secret key: secret=mysecretkey"
        sanitized = error_sanitizer.sanitize(message)
        assert "mysecretkey" not in sanitized
        assert "***" in sanitized

    def test_api_key_in_message(self):
        """Test that API keys are sanitized."""
        message = "API key: api_key=sk-1234567890"
        sanitized = error_sanitizer.sanitize(message)
        assert "sk-1234567890" not in sanitized
        assert "***" in sanitized


class TestErrorSanitizerGitTokens:
    """Test Git token sanitization in URLs."""

    def test_git_token_in_https_url(self):
        """Test that Git tokens in HTTPS URLs are sanitized."""
        message = "Clone from https://user:secret123@github.com/repo.git"
        sanitized = error_sanitizer.sanitize(message)
        assert "secret123" not in sanitized
        assert "***" in sanitized

    def test_git_token_in_ssh_url(self):
        """Test that Git tokens in SSH URLs are sanitized."""
        message = "Clone from git@user:secret123@github.com:repo.git"
        sanitized = error_sanitizer.sanitize(message)
        assert "secret123" not in sanitized
        assert "***" in sanitized


class TestErrorSanitizerSSHKeys:
    """Test SSH key sanitization."""

    def test_rsa_private_key(self):
        """Test that RSA private keys are sanitized."""
        message = """Error loading key: -----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAz8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8
-----END RSA PRIVATE KEY-----"""
        sanitized = error_sanitizer.sanitize(message)
        assert "MIIEpAIBAAKCAQEA" not in sanitized
        assert "***" in sanitized

    def test_generic_private_key(self):
        """Test that generic private keys are sanitized."""
        message = """Error loading key: -----BEGIN PRIVATE KEY-----
MIIEpAIBAAKCAQEAz8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8
-----END PRIVATE KEY-----"""
        sanitized = error_sanitizer.sanitize(message)
        assert "MIIEpAIBAAKCAQEA" not in sanitized
        assert "***" in sanitized


class TestErrorSanitizerFilePaths:
    """Test file path sanitization."""

    def test_home_directory_path(self):
        """Test that home directory paths are sanitized."""
        message = "Error accessing /home/user123/repository"
        sanitized = error_sanitizer.sanitize(message)
        assert "user123" not in sanitized
        assert "/home/****/" in sanitized

    def test_root_directory_path(self):
        """Test that root directory paths are sanitized."""
        message = "Error accessing /root/.git"
        sanitized = error_sanitizer.sanitize(message)
        assert "/****/" in sanitized

    def test_users_directory_path(self):
        """Test that user directory paths are sanitized."""
        message = "Error accessing /Users/johndoe/workspace"
        sanitized = error_sanitizer.sanitize(message)
        assert "johndoe" not in sanitized
        assert "/Users/****/" in sanitized


class TestErrorSanitizerDatabaseStrings:
    """Test database connection string sanitization."""

    def test_mongodb_connection_string(self):
        """Test that MongoDB connection strings are sanitized."""
        message = "MongoDB connection failed: mongodb://user:pass123@localhost:27017"
        sanitized = error_sanitizer.sanitize(message)
        assert "pass123" not in sanitized
        assert "***" in sanitized

    def test_postgres_connection_string(self):
        """Test that PostgreSQL connection strings are sanitized."""
        message = "PostgreSQL connection failed: postgres://user:secret@localhost:5432"
        sanitized = error_sanitizer.sanitize(message)
        assert "secret" not in sanitized
        assert "***" in sanitized


class TestErrorSanitizerIPAddresses:
    """Test IP address sanitization."""

    def test_ipv4_address(self):
        """Test that IPv4 addresses are partially masked."""
        message = "Connection failed from 192.168.1.100"
        sanitized = error_sanitizer.sanitize(message)
        # Should mask middle octets
        assert "192.***.***.100" in sanitized


class TestErrorSanitizerContext:
    """Test context sanitization."""

    def test_context_with_parameters(self):
        """Test that parameters in context are sanitized."""
        message = 'Error: parameters: {"password": "secret123"}'
        context = {"parameters": {"password": "secret123"}}
        sanitized = error_sanitizer.sanitize(message, context)
        assert "secret123" not in sanitized
        assert "***" in sanitized

    def test_context_with_repo_path(self):
        """Test that repo paths in context are sanitized."""
        message = "Error in repository"
        context = {"repo_path": "/home/user/repo"}
        sanitized = error_sanitizer.sanitize(message, context)
        # Should not contain the full path
        assert "/home/user/repo" not in sanitized


class TestErrorSanitizerDict:
    """Test dictionary sanitization."""

    def test_sanitize_dict_with_sensitive_keys(self):
        """Test sanitizing specific keys in a dictionary."""
        data = {
            "username": "john",
            "password": "secret123",
            "email": "john@example.com",
        }
        sanitized = error_sanitizer.sanitize_dict(data, keys_to_sanitize=["password"])
        assert sanitized["password"] == "***"
        assert sanitized["username"] == "john"
        assert sanitized["email"] == "john@example.com"

    def test_sanitize_dict_all_keys(self):
        """Test sanitizing all string values in a dictionary."""
        data = {
            "username": "john",
            "password": "secret123",
            "token": "abc123",
        }
        sanitized = error_sanitizer.sanitize_dict(data)
        assert sanitized["password"] == "***"
        assert sanitized["token"] == "***"
        # Username doesn't match sensitive patterns, so it might be preserved
        # or sanitized depending on implementation


class TestErrorSanitizerEdgeCases:
    """Test edge cases."""

    def test_empty_message(self):
        """Test sanitizing an empty message."""
        message = ""
        sanitized = error_sanitizer.sanitize(message)
        assert sanitized == ""

    def test_none_message(self):
        """Test sanitizing a None message."""
        message = None
        sanitized = error_sanitizer.sanitize(message)
        assert sanitized is None

    def test_message_without_sensitive_info(self):
        """Test sanitizing a message without sensitive information."""
        message = "This is a normal error message"
        sanitized = error_sanitizer.sanitize(message)
        assert sanitized == message

    def test_multiple_sensitive_patterns(self):
        """Test sanitizing a message with multiple sensitive patterns."""
        message = "Error: password=secret123, token=abc123, https://user:pass@github.com"
        sanitized = error_sanitizer.sanitize(message)
        assert "secret123" not in sanitized
        assert "abc123" not in sanitized
        # "pass" is part of "password" and should be preserved
        assert "password" in sanitized
        assert sanitized.count("***") >= 3


class TestErrorSanitizerCaseInsensitive:
    """Test case-insensitive pattern matching."""

    def test_password_case_variations(self):
        """Test that password matching is case-insensitive."""
        message = "Password=secret123, PASSWORD=secret456, password=secret789"
        sanitized = error_sanitizer.sanitize(message)
        assert "secret123" not in sanitized
        assert "secret456" not in sanitized
        assert "secret789" not in sanitized

    def test_token_case_variations(self):
        """Test that token matching is case-insensitive."""
        message = "Token=abc123, TOKEN=def456, token=ghi789"
        sanitized = error_sanitizer.sanitize(message)
        assert "abc123" not in sanitized
        assert "def456" not in sanitized
        assert "ghi789" not in sanitized


class TestErrorSanitizerCustomInstance:
    """Test creating custom ErrorSanitizer instances."""

    def test_custom_instance(self):
        """Test creating and using a custom ErrorSanitizer instance."""
        custom_sanitizer = ErrorSanitizer()
        message = "Password: secret123"
        sanitized = custom_sanitizer.sanitize(message)
        assert "secret123" not in sanitized
        assert "***" in sanitized
