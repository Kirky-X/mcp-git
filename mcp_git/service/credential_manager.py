"""
Credential management for Git operations.

This module provides secure handling of Git credentials including
tokens, SSH keys, and passwords.
"""

import os
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, SecretStr


class AuthType(str, Enum):
    """Authentication type."""

    TOKEN = "token"
    SSH_KEY = "ssh_key"
    SSH_AGENT = "ssh_agent"
    USERNAME_PASSWORD = "username_password"


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
    ENV_TOKEN = "GIT_TOKEN"
    ENV_GITHUB_TOKEN = "GITHUB_TOKEN"
    ENV_USERNAME = "GIT_USERNAME"
    ENV_PASSWORD = "GIT_PASSWORD"
    ENV_SSH_KEY_PATH = "SSH_KEY_PATH"
    ENV_SSH_KEY = "SSH_KEY"
    ENV_SSH_PASSPHRASE = "SSH_PASSPHRASE"

    def __init__(self):
        """Initialize the credential manager."""
        self._cached_credential: Credential | None = None

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
            ssh_key_path = Path(ssh_key_path)
            if ssh_key_path.exists():
                return Credential(
                    auth_type=AuthType.SSH_KEY,
                    ssh_key_path=ssh_key_path,
                    ssh_key_passphrase=(
                        SecretStr(os.getenv(self.ENV_SSH_PASSPHRASE))
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

        return self._cached_credential

    def set_credential(self, credential: Credential) -> None:
        """
        Set credential directly.

        Args:
            credential: Credential to set
        """
        self._cached_credential = credential

    def clear_credential(self) -> None:
        """Clear cached credential."""
        self._cached_credential = None

    def is_authenticated(self) -> bool:
        """Check if credentials are available."""
        return self.load_credential() is not None

    def get_auth_type(self) -> AuthType | None:
        """Get the current authentication type."""
        credential = self.load_credential()
        return credential.auth_type if credential else None


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

        return username, password.expose_secret() if password else None

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
                return credential.ssh_key_passphrase.expose_secret()

        return os.getenv(CredentialManager.ENV_SSH_PASSPHRASE)
