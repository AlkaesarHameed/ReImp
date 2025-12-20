"""
Security Services.
Source: Design Document Section 5.2 - Security Hardening
Verified: 2025-12-18

Provides encryption, secret management, and security middleware.
"""

from src.services.security.encryption import (
    EncryptionService,
    EncryptionConfig,
    EncryptedField,
    get_encryption_service,
)
from src.services.security.phi_protection import (
    PHIProtectionService,
    PHIConfig,
    PHIField,
    SensitivityLevel,
    get_phi_service,
)
from src.services.security.secrets import (
    SecretManager,
    SecretConfig,
    Secret,
    get_secret_manager,
)
from src.services.security.middleware import (
    SecurityHeadersMiddleware,
    SecurityConfig,
    RateLimiter,
    RequestValidator,
)
from src.services.security.audit import (
    SecurityAuditService,
    AuditEvent,
    AuditEventType,
    get_audit_service,
)


__all__ = [
    # Encryption
    "EncryptionService",
    "EncryptionConfig",
    "EncryptedField",
    "get_encryption_service",
    # PHI Protection
    "PHIProtectionService",
    "PHIConfig",
    "PHIField",
    "SensitivityLevel",
    "get_phi_service",
    # Secrets
    "SecretManager",
    "SecretConfig",
    "Secret",
    "get_secret_manager",
    # Middleware
    "SecurityHeadersMiddleware",
    "SecurityConfig",
    "RateLimiter",
    "RequestValidator",
    # Audit
    "SecurityAuditService",
    "AuditEvent",
    "AuditEventType",
    "get_audit_service",
]
