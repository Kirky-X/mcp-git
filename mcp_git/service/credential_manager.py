"""
Credential management for Git operations.

This module provides secure handling of Git credentials including
tokens, SSH keys, and passwords.
"""

import os
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from loguru import logger
from pydantic import BaseModel, SecretStr


class AuthType(str, Enum):
    """Authentication type."""

    TOKEN = "token"  # nosec: B105 - Not a password, auth type identifier
    SSH_KEY = "ssh_key"  # nosec: B105 - Not a password, auth type identifier
    SSH_AGENT = "ssh_agent"  # nosec: B105 - Not a password, auth type identifier
    USERNAME_PASSWORD = "username_password"  # nosec: B105 - Not a password, auth type identifier


class Credential(BaseModel):
    """Git credential information."""

    auth_type: AuthType
    token: SecretStr | None = None
    username: str | None = None
    password: SecretStr | None = None
    ssh_key_path: Path | None = None
    ssh_key_passphrase: SecretStr | None = None

    def get_username(self) -> str | None:
        """Get username for authentication."""
        if self.username:
            return self.username
        if self.auth_type == AuthType.TOKEN and self.token:
            # GitHub tokens often don't need username
            return "git"
        return None

    def get_password(self) -> SecretStr | None:
        """Get password for authentication."""
        if self.password:
            return self.password
        if self.auth_type == AuthType.TOKEN and self.token:
            return self.token
        return None


class CredentialManager:
    """Manager for Git credentials with security best practices."""

    # Environment variable names for credentials
    ENV_TOKEN = "GIT_TOKEN"  # nosec: B105 - Not a password, environment variable name
    ENV_GITHUB_TOKEN = "GITHUB_TOKEN"  # nosec: B105 - Not a password, environment variable name
    ENV_USERNAME = "GIT_USERNAME"  # nosec: B105 - Not a password, environment variable name
    ENV_PASSWORD = "GIT_PASSWORD"  # nosec: B105 - Not a password, environment variable name
    ENV_SSH_KEY_PATH = "SSH_KEY_PATH"  # nosec: B105 - Not a password, environment variable name
    ENV_SSH_KEY = "SSH_KEY"  # nosec: B105 - Not a password, environment variable name
    ENV_SSH_PASSPHRASE = "SSH_PASSPHRASE"  # nosec: B105 - Not a password, environment variable name

    def __init__(self, audit_log_path: Path | None = None) -> None:
        """
        Initialize the credential manager.

        Args:
            audit_log_path: Optional path to audit log file
        """
        self._cached_credential: Credential | None = None
        self._credential_id: str | None = None
        self._created_at: float | None = None
        self._last_accessed: float | None = None
        self._access_count: int = 0
        self._audit_log_path = audit_log_path

    def _log_audit_event(self, event_type: str, details: dict[str, Any]) -> None:
        """
        Log an audit event for credential operations.

        Args:
            event_type: Type of event (created, accessed, cleared, rotated)
            details: Additional event details
        """
        timestamp = datetime.now().isoformat()
        event = {
            "timestamp": timestamp,
            "event_type": event_type,
            "credential_id": self._credential_id,
            "details": details,
        }

        # Log to file if configured
        if self._audit_log_path:
            try:
                import json

                with open(self._audit_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event) + "\n")
            except (IOError, OSError, PermissionError) as e:
                    logger.error(f"Failed to write to audit log: {e}")
                    logger.debug(f"Audit log path: {self._audit_log_path}")
        # Log to application logger
        logger.info(f"Credential audit event: {event_type}", extra={"audit_event": event})

    def _clear_sensitive_memory(self, secret_str: SecretStr | None) -> None:
        """
        Clear sensitive data from memory by overwriting it.

        Args:
            secret_str: SecretStr to clear
        """
        if secret_str:
            try:
                # Get the secret value
                secret_value = secret_str.get_secret_value()

                # Overwrite with zeros
                zeros = "\x00" * len(secret_value)

                # Access the internal value and overwrite it
                # Note: This is a best-effort approach and may not guarantee
                # complete memory clearing due to Python's memory management
                for _ in range(3):  # Multiple passes
                    secret_str._secret_value = zeros  # type: ignore[attr-defined]

                logger.debug("Sensitive memory cleared")
            except Exception as e:
                logger.warning(f"Failed to clear sensitive memory: {e}")

    def load_credential(self) -> Credential | None:
        """
        Load credential from environment variables.

        Returns:
            Credential if found, None otherwise
        """
        # Check for GitHub token (priority)
        token = os.getenv(self.ENV_GITHUB_TOKEN) or os.getenv(self.ENV_TOKEN)
        if token:
            return Credential(
                auth_type=AuthType.TOKEN,
                token=SecretStr(token),
                username=os.getenv(self.ENV_USERNAME),
            )

        # Check for SSH key path
        ssh_key_path = os.getenv(self.ENV_SSH_KEY_PATH)
        if ssh_key_path:
            ssh_key_file = Path(ssh_key_path)
            if ssh_key_file.exists():
                return Credential(
                    auth_type=AuthType.SSH_KEY,
                    ssh_key_path=ssh_key_file,
                    ssh_key_passphrase=(
                        SecretStr(os.getenv(self.ENV_SSH_PASSPHRASE) or "")
                        if os.getenv(self.ENV_SSH_PASSPHRASE)
                        else None
                    ),
                )

        # Check for SSH Agent (inferred)
        if os.getenv("SSH_AUTH_SOCK"):
            return Credential(auth_type=AuthType.SSH_AGENT)

        # Check for username/password
        username = os.getenv(self.ENV_USERNAME)
        password = os.getenv(self.ENV_PASSWORD)
        if username and password:
            return Credential(
                auth_type=AuthType.USERNAME_PASSWORD,
                username=username,
                password=SecretStr(password),
            )

        return None

    def get_credential(self, force_refresh: bool = False) -> Credential | None:
        """
        Get credential, using cache if available.

        Args:
            force_refresh: Force reload from environment

        Returns:
            Credential if found
        """
        if force_refresh or self._cached_credential is None:
            self._cached_credential = self.load_credential()
            if self._cached_credential:
                self._credential_id = str(uuid4())
                self._created_at = time.time()
                self._log_audit_event(
                    "created",
                    {
                        "auth_type": self._cached_credential.auth_type.value,
                        "username": self._cached_credential.get_username(),
                    },
                )

        if self._cached_credential:
            self._last_accessed = time.time()
            self._access_count += 1
            self._log_audit_event(
                "accessed",
                {
                    "credential_id": self._credential_id,
                    "access_count": self._access_count,
                    "auth_type": self._cached_credential.auth_type.value,
                },
            )

        return self._cached_credential

    def set_credential(self, credential: Credential) -> None:
        """
        Set credential directly.

        Args:
            credential: Credential to set
        """
        self._cached_credential = credential
        self._credential_id = str(uuid4())
        self._created_at = time.time()
        self._access_count = 0

        self._log_audit_event(
            "set",
            {
                "credential_id": self._credential_id,
                "auth_type": credential.auth_type.value,
                "username": credential.get_username(),
            },
        )

    def clear_credential(self) -> None:
        """Clear cached credential with secure memory cleanup."""
        if self._cached_credential:
            # Clear sensitive data from memory
            self._clear_sensitive_memory(self._cached_credential.token)
            self._clear_sensitive_memory(self._cached_credential.password)
            self._clear_sensitive_memory(self._cached_credential.ssh_key_passphrase)

            self._log_audit_event(
                "cleared",
                {
                    "credential_id": self._credential_id,
                    "auth_type": self._cached_credential.auth_type.value,
                    "access_count": self._access_count,
                    "age_seconds": time.time() - (self._created_at or 0),
                },
            )

        self._cached_credential = None
        self._credential_id = None
        self._created_at = None
        self._last_accessed = None
        self._access_count = 0

    def is_authenticated(self) -> bool:
        """Check if credentials are available."""
        return self.load_credential() is not None

    def get_auth_type(self) -> AuthType | None:
        """Get the current authentication type."""
        credential = self.load_credential()
        return credential.auth_type if credential else None

    def rotate_credential(self, new_credential: Credential) -> None:
        """
        Rotate to a new credential with secure cleanup of the old one.

        Args:
            new_credential: New credential to use
        """
        old_credential = self._cached_credential
        old_id = self._credential_id

        # Clear old credential securely
        if old_credential:
            self._clear_sensitive_memory(old_credential.token)
            self._clear_sensitive_memory(old_credential.password)
            self._clear_sensitive_memory(old_credential.ssh_key_passphrase)

        # Set new credential
        self._cached_credential = new_credential
        self._credential_id = str(uuid4())
        self._created_at = time.time()
        self._access_count = 0

        self._log_audit_event(
            "rotated",
            {
                "old_credential_id": old_id,
                "new_credential_id": self._credential_id,
                "auth_type": new_credential.auth_type.value,
                "username": new_credential.get_username(),
            },
        )

    def get_credential_age(self) -> float | None:
        """
        Get the age of the current credential in seconds.

        Returns:
            Age in seconds, or None if no credential is loaded
        """
        if self._created_at is None:
            return None
        return time.time() - self._created_at

    def get_credential_stats(self) -> dict[str, Any]:
        """
        Get statistics about the current credential.

        Returns:
            Dictionary with credential statistics
        """
        return {
            "credential_id": self._credential_id,
            "auth_type": self._cached_credential.auth_type.value if self._cached_credential else None,
            "created_at": self._created_at,
            "last_accessed": self._last_accessed,
            "access_count": self._access_count,
            "age_seconds": self.get_credential_age(),
        }


class CredentialCallback:
    """
    Callback for Git operations to provide credentials.

    This class provides methods that GitPython can use
    to get credentials during operations.
    """

    def __init__(self, credential_manager: CredentialManager):
        """
        Initialize the callback.

        Args:
            credential_manager: Credential manager to use
        """
        self.credential_manager = credential_manager

    def __call__(
        self,
        url: str,
        username: str | None,
        credential_type: str,
    ) -> tuple[str | None, str | None]:
        """
        Provide credentials for Git operations.

        Args:
            url: Repository URL
            username: Username (if provided)
            credential_type: Type of credential being requested

        Returns:
            Tuple of (username, password/token)
        """
        credential = self.credential_manager.get_credential()

        if credential is None:
            # No credentials available
            return None, None

        username = credential.get_username() or username
        password = credential.get_password()

        return username, password.get_secret_value() if password else None  # type: ignore[attr-defined]

    def get_ssh_key_path(self) -> Path | None:
        """Get SSH key path for SSH authentication."""
        credential = self.credential_manager.get_credential()

        if credential and credential.auth_type == AuthType.SSH_KEY:
            return credential.ssh_key_path

        # Check environment variable
        ssh_key_path = os.getenv(CredentialManager.ENV_SSH_KEY_PATH)
        if ssh_key_path:
            return Path(ssh_key_path)

        # Check common locations
        common_paths = [
            Path.home() / ".ssh" / "id_rsa",
            Path.home() / ".ssh" / "id_ed25519",
            Path.home() / ".ssh" / "id_ecdsa",
        ]

        for path in common_paths:
            if path.exists():
                return path

        return None

    def get_ssh_key_passphrase(self) -> str | None:
        """Get SSH key passphrase."""
        credential = self.credential_manager.get_credential()

        if credential and credential.auth_type == AuthType.SSH_KEY:
            if credential.ssh_key_passphrase:
                return credential.ssh_key_passphrase.get_secret_value()  # type: ignore[attr-defined]

        return os.getenv(CredentialManager.ENV_SSH_PASSPHRASE)
