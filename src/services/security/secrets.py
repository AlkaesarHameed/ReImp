"""
Secret Management Service.
Source: Design Document Section 5.2 - Security Hardening
Verified: 2025-12-18

Provides secure secret storage and retrieval.
"""

import base64
import hashlib
import os
import secrets as py_secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SecretType(str, Enum):
    """Types of secrets."""

    API_KEY = "api_key"
    PASSWORD = "password"
    ENCRYPTION_KEY = "encryption_key"
    DATABASE_URL = "database_url"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    SSH_KEY = "ssh_key"
    GENERIC = "generic"


class SecretConfig(BaseModel):
    """Secret management configuration."""

    backend: str = "memory"  # memory, vault, aws_secrets, azure_keyvault
    vault_url: Optional[str] = None
    vault_token: Optional[str] = None
    encryption_key: Optional[str] = None
    cache_ttl: int = 300  # seconds
    rotation_days: int = 90


class Secret(BaseModel):
    """Secret value wrapper."""

    secret_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    secret_type: SecretType = SecretType.GENERIC
    value: str  # Encrypted in storage
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    rotation_due: Optional[datetime] = None
    metadata: dict[str, str] = Field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if secret is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def needs_rotation(self) -> bool:
        """Check if secret needs rotation."""
        if self.rotation_due is None:
            return False
        return datetime.utcnow() > self.rotation_due


class SecretAccessLog(BaseModel):
    """Log entry for secret access."""

    access_id: str = Field(default_factory=lambda: str(uuid4()))
    secret_name: str
    action: str  # get, set, delete, rotate
    user_id: Optional[str] = None
    source_ip: Optional[str] = None
    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SecretManager:
    """Secure secret management service."""

    def __init__(self, config: SecretConfig | None = None):
        """Initialize SecretManager."""
        self._config = config or SecretConfig()
        self._secrets: dict[str, Secret] = {}
        self._cache: dict[str, tuple[str, datetime]] = {}
        self._access_logs: list[SecretAccessLog] = []

        # Initialize encryption key
        if self._config.encryption_key:
            self._enc_key = base64.b64decode(self._config.encryption_key)
        else:
            self._enc_key = py_secrets.token_bytes(32)

    @property
    def config(self) -> SecretConfig:
        """Get configuration."""
        return self._config

    def _encrypt_value(self, value: str) -> str:
        """Encrypt secret value for storage."""
        # Simple encryption for demo - use proper encryption in production
        value_bytes = value.encode()
        stream = self._generate_stream(len(value_bytes))
        encrypted = bytes(v ^ s for v, s in zip(value_bytes, stream))
        return base64.b64encode(encrypted).decode()

    def _decrypt_value(self, encrypted: str) -> str:
        """Decrypt secret value."""
        encrypted_bytes = base64.b64decode(encrypted)
        stream = self._generate_stream(len(encrypted_bytes))
        decrypted = bytes(e ^ s for e, s in zip(encrypted_bytes, stream))
        return decrypted.decode()

    def _generate_stream(self, length: int) -> bytes:
        """Generate encryption stream."""
        stream = b""
        counter = 0
        while len(stream) < length:
            block = hashlib.sha256(self._enc_key + counter.to_bytes(4, "big")).digest()
            stream += block
            counter += 1
        return stream[:length]

    def _log_access(
        self,
        secret_name: str,
        action: str,
        success: bool = True,
        user_id: str | None = None,
    ) -> None:
        """Log secret access."""
        log = SecretAccessLog(
            secret_name=secret_name,
            action=action,
            user_id=user_id,
            success=success,
        )
        self._access_logs.append(log)

    def set_secret(
        self,
        name: str,
        value: str,
        secret_type: SecretType = SecretType.GENERIC,
        expires_in_days: int | None = None,
        metadata: dict[str, str] | None = None,
    ) -> Secret:
        """Store a secret.

        Args:
            name: Secret name/key
            value: Secret value
            secret_type: Type of secret
            expires_in_days: Optional expiration in days
            metadata: Optional metadata

        Returns:
            Created secret (without value)
        """
        now = datetime.utcnow()

        # Check if updating existing secret
        version = 1
        if name in self._secrets:
            version = self._secrets[name].version + 1

        expires_at = None
        if expires_in_days:
            expires_at = now + timedelta(days=expires_in_days)

        rotation_due = now + timedelta(days=self._config.rotation_days)

        secret = Secret(
            name=name,
            secret_type=secret_type,
            value=self._encrypt_value(value),
            version=version,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            rotation_due=rotation_due,
            metadata=metadata or {},
        )

        self._secrets[name] = secret
        self._invalidate_cache(name)
        self._log_access(name, "set")

        # Return copy without actual value
        return secret.model_copy(update={"value": "***"})

    def get_secret(self, name: str, user_id: str | None = None) -> Optional[str]:
        """Retrieve a secret value.

        Args:
            name: Secret name
            user_id: Optional user ID for audit

        Returns:
            Secret value or None
        """
        # Check cache first
        if name in self._cache:
            cached_value, cached_at = self._cache[name]
            if (datetime.utcnow() - cached_at).total_seconds() < self._config.cache_ttl:
                self._log_access(name, "get", user_id=user_id)
                return cached_value

        # Get from storage
        secret = self._secrets.get(name)
        if not secret:
            self._log_access(name, "get", success=False, user_id=user_id)
            return None

        if secret.is_expired():
            self._log_access(name, "get", success=False, user_id=user_id)
            return None

        # Decrypt and cache
        value = self._decrypt_value(secret.value)
        self._cache[name] = (value, datetime.utcnow())
        self._log_access(name, "get", user_id=user_id)

        return value

    def delete_secret(self, name: str) -> bool:
        """Delete a secret.

        Args:
            name: Secret name

        Returns:
            True if deleted
        """
        if name in self._secrets:
            del self._secrets[name]
            self._invalidate_cache(name)
            self._log_access(name, "delete")
            return True

        self._log_access(name, "delete", success=False)
        return False

    def rotate_secret(
        self,
        name: str,
        new_value: str,
    ) -> Optional[Secret]:
        """Rotate a secret with a new value.

        Args:
            name: Secret name
            new_value: New secret value

        Returns:
            Updated secret or None
        """
        existing = self._secrets.get(name)
        if not existing:
            return None

        updated = self.set_secret(
            name=name,
            value=new_value,
            secret_type=existing.secret_type,
            metadata=existing.metadata,
        )

        self._log_access(name, "rotate")
        return updated

    def list_secrets(self) -> list[dict[str, Any]]:
        """List all secrets (metadata only).

        Returns:
            List of secret metadata
        """
        return [
            {
                "name": s.name,
                "type": s.secret_type.value,
                "version": s.version,
                "created_at": s.created_at.isoformat(),
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                "needs_rotation": s.needs_rotation(),
            }
            for s in self._secrets.values()
        ]

    def get_secrets_needing_rotation(self) -> list[str]:
        """Get list of secrets needing rotation.

        Returns:
            List of secret names
        """
        return [
            s.name for s in self._secrets.values()
            if s.needs_rotation()
        ]

    def generate_api_key(self, prefix: str = "sk") -> str:
        """Generate a secure API key.

        Args:
            prefix: Key prefix

        Returns:
            Generated API key
        """
        random_part = py_secrets.token_urlsafe(32)
        return f"{prefix}_{random_part}"

    def generate_password(
        self,
        length: int = 32,
        include_special: bool = True,
    ) -> str:
        """Generate a secure random password.

        Args:
            length: Password length
            include_special: Include special characters

        Returns:
            Generated password
        """
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        if include_special:
            alphabet += "!@#$%^&*()-_=+"

        return "".join(py_secrets.choice(alphabet) for _ in range(length))

    def _invalidate_cache(self, name: str) -> None:
        """Invalidate cached secret."""
        if name in self._cache:
            del self._cache[name]

    def get_access_logs(self, limit: int = 100) -> list[SecretAccessLog]:
        """Get secret access logs.

        Args:
            limit: Maximum logs to return

        Returns:
            List of access logs
        """
        return self._access_logs[-limit:]

    def clear_all(self) -> None:
        """Clear all secrets and logs (for testing)."""
        self._secrets.clear()
        self._cache.clear()
        self._access_logs.clear()


# =============================================================================
# Environment Variable Integration
# =============================================================================


def load_secrets_from_env(
    manager: SecretManager,
    prefix: str = "SECRET_",
) -> int:
    """Load secrets from environment variables.

    Args:
        manager: SecretManager instance
        prefix: Environment variable prefix

    Returns:
        Number of secrets loaded
    """
    count = 0

    for key, value in os.environ.items():
        if key.startswith(prefix):
            secret_name = key[len(prefix):].lower()
            manager.set_secret(secret_name, value)
            count += 1

    return count


# =============================================================================
# Factory Functions
# =============================================================================


_secret_manager: SecretManager | None = None


def get_secret_manager(config: SecretConfig | None = None) -> SecretManager:
    """Get singleton SecretManager instance."""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager(config)
    return _secret_manager


def create_secret_manager(config: SecretConfig | None = None) -> SecretManager:
    """Create new SecretManager instance."""
    return SecretManager(config)
