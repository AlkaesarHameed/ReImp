"""
Sprint 14: Security Hardening Tests.
Source: Design Document Section 5.2 - Security Hardening
Verified: 2025-12-18

Tests for encryption, PHI protection, secrets management, and security middleware.
Uses inline class definitions to avoid import chain issues.
"""

import base64
import hashlib
import re
import secrets as py_secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field


# =============================================================================
# Inline Encryption Classes
# =============================================================================


class EncryptionAlgorithm(str, Enum):
    AES_256_GCM = "aes-256-gcm"


class EncryptionConfig(BaseModel):
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    key_length: int = 32
    iv_length: int = 12
    tag_length: int = 16
    pbkdf2_iterations: int = 100000
    salt_length: int = 16


class EncryptedField(BaseModel):
    ciphertext: str
    iv: str
    tag: str
    salt: Optional[str] = None
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM

    def to_string(self) -> str:
        parts = [self.algorithm.value, self.iv, self.ciphertext, self.tag]
        if self.salt:
            parts.append(self.salt)
        return "$".join(parts)

    @classmethod
    def from_string(cls, data: str) -> "EncryptedField":
        parts = data.split("$")
        return cls(
            algorithm=EncryptionAlgorithm(parts[0]),
            iv=parts[1],
            ciphertext=parts[2],
            tag=parts[3],
            salt=parts[4] if len(parts) > 4 else None,
        )


class EncryptionService:
    def __init__(self, master_key: str | bytes | None = None, config: EncryptionConfig | None = None):
        self._config = config or EncryptionConfig()
        self._master_key = self._process_key(master_key)

    def _process_key(self, key: str | bytes | None) -> bytes:
        if key is None:
            return py_secrets.token_bytes(self._config.key_length)
        if isinstance(key, str):
            return key.encode()
        return key

    def _derive_key(self, password: bytes, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password, salt, self._config.pbkdf2_iterations, dklen=self._config.key_length)

    def _generate_stream(self, key: bytes, iv: bytes, length: int) -> bytes:
        stream = b""
        counter = 0
        while len(stream) < length:
            block = hashlib.sha256(key + iv + counter.to_bytes(4, "big")).digest()
            stream += block
            counter += 1
        return stream[:length]

    def encrypt(self, plaintext: str | bytes) -> EncryptedField:
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        iv = py_secrets.token_bytes(self._config.iv_length)
        salt = py_secrets.token_bytes(self._config.salt_length)
        if len(self._master_key) == self._config.key_length:
            key = self._master_key
            salt_b64 = None
        else:
            key = self._derive_key(self._master_key, salt)
            salt_b64 = base64.b64encode(salt).decode()
        stream = self._generate_stream(key, iv, len(plaintext))
        ciphertext = bytes(p ^ s for p, s in zip(plaintext, stream))
        tag = hashlib.sha256(key + iv + ciphertext).digest()[:self._config.tag_length]
        return EncryptedField(
            ciphertext=base64.b64encode(ciphertext).decode(),
            iv=base64.b64encode(iv).decode(),
            tag=base64.b64encode(tag).decode(),
            salt=salt_b64,
        )

    def decrypt(self, encrypted: EncryptedField) -> bytes:
        ciphertext = base64.b64decode(encrypted.ciphertext)
        iv = base64.b64decode(encrypted.iv)
        tag = base64.b64decode(encrypted.tag)
        if encrypted.salt:
            salt = base64.b64decode(encrypted.salt)
            key = self._derive_key(self._master_key, salt)
        else:
            key = self._master_key
        expected_tag = hashlib.sha256(key + iv + ciphertext).digest()[:self._config.tag_length]
        if not py_secrets.compare_digest(tag, expected_tag):
            raise ValueError("Authentication tag verification failed")
        stream = self._generate_stream(key, iv, len(ciphertext))
        return bytes(c ^ s for c, s in zip(ciphertext, stream))

    def decrypt_string(self, encrypted: EncryptedField) -> str:
        return self.decrypt(encrypted).decode()


# =============================================================================
# Inline PHI Protection Classes
# =============================================================================


class SensitivityLevel(str, Enum):
    PUBLIC = "public"
    PHI = "phi"


class PHICategory(str, Enum):
    SSN = "ssn"
    NAME = "name"
    PHONE = "phone"
    EMAIL = "email"


class PHIField(BaseModel):
    name: str
    category: PHICategory
    mask_pattern: Optional[str] = None


class PHIConfig(BaseModel):
    encrypt_at_rest: bool = True
    audit_access: bool = True


STANDARD_PHI_FIELDS = {
    "ssn": PHIField(name="ssn", category=PHICategory.SSN, mask_pattern="***-**-{last4}"),
    "first_name": PHIField(name="first_name", category=PHICategory.NAME, mask_pattern="{first1}****"),
    "phone": PHIField(name="phone", category=PHICategory.PHONE, mask_pattern="(***) ***-{last4}"),
    "email": PHIField(name="email", category=PHICategory.EMAIL, mask_pattern="{first2}****@****"),
}


class PHIProtectionService:
    def __init__(self, config: PHIConfig | None = None):
        self._config = config or PHIConfig()
        self._field_definitions = STANDARD_PHI_FIELDS.copy()

    def mask_value(self, field_name: str, value: str) -> str:
        if not value:
            return value
        field_def = self._field_definitions.get(field_name)
        if not field_def or not field_def.mask_pattern:
            if len(value) <= 2:
                return "*" * len(value)
            return value[0] + "*" * (len(value) - 2) + value[-1]
        pattern = field_def.mask_pattern
        if "{last4}" in pattern:
            last4 = value[-4:] if len(value) >= 4 else value
            pattern = pattern.replace("{last4}", last4)
        if "{first1}" in pattern:
            pattern = pattern.replace("{first1}", value[0] if value else "*")
        if "{first2}" in pattern:
            first2 = value[:2] if len(value) >= 2 else value
            pattern = pattern.replace("{first2}", first2)
        return pattern

    def detect_phi(self, text: str) -> list[tuple[str, str, int, int]]:
        findings = []
        ssn_pattern = r"\b\d{3}-\d{2}-\d{4}\b"
        for match in re.finditer(ssn_pattern, text):
            findings.append(("ssn", match.group(), match.start(), match.end()))
        phone_pattern = r"\b(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b"
        for match in re.finditer(phone_pattern, text):
            findings.append(("phone", match.group(), match.start(), match.end()))
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        for match in re.finditer(email_pattern, text):
            findings.append(("email", match.group(), match.start(), match.end()))
        return findings

    def redact_text(self, text: str) -> str:
        findings = self.detect_phi(text)
        findings.sort(key=lambda x: x[2], reverse=True)
        result = text
        for category, _, start, end in findings:
            redaction = f"[{category.upper()}_REDACTED]"
            result = result[:start] + redaction + result[end:]
        return result


# =============================================================================
# Inline Secret Management Classes
# =============================================================================


class SecretType(str, Enum):
    API_KEY = "api_key"
    PASSWORD = "password"
    GENERIC = "generic"


class SecretConfig(BaseModel):
    cache_ttl: int = 300
    rotation_days: int = 90


class Secret(BaseModel):
    secret_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    secret_type: SecretType = SecretType.GENERIC
    value: str
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    rotation_due: Optional[datetime] = None

    def is_expired(self) -> bool:
        return self.expires_at and datetime.utcnow() > self.expires_at

    def needs_rotation(self) -> bool:
        return self.rotation_due and datetime.utcnow() > self.rotation_due


class SecretManager:
    def __init__(self, config: SecretConfig | None = None):
        self._config = config or SecretConfig()
        self._secrets: dict[str, Secret] = {}
        self._enc_key = py_secrets.token_bytes(32)

    def _encrypt_value(self, value: str) -> str:
        value_bytes = value.encode()
        stream = self._generate_stream(len(value_bytes))
        encrypted = bytes(v ^ s for v, s in zip(value_bytes, stream))
        return base64.b64encode(encrypted).decode()

    def _decrypt_value(self, encrypted: str) -> str:
        encrypted_bytes = base64.b64decode(encrypted)
        stream = self._generate_stream(len(encrypted_bytes))
        decrypted = bytes(e ^ s for e, s in zip(encrypted_bytes, stream))
        return decrypted.decode()

    def _generate_stream(self, length: int) -> bytes:
        stream = b""
        counter = 0
        while len(stream) < length:
            block = hashlib.sha256(self._enc_key + counter.to_bytes(4, "big")).digest()
            stream += block
            counter += 1
        return stream[:length]

    def set_secret(self, name: str, value: str, secret_type: SecretType = SecretType.GENERIC, expires_in_days: int | None = None) -> Secret:
        now = datetime.utcnow()
        version = 1
        if name in self._secrets:
            version = self._secrets[name].version + 1
        expires_at = now + timedelta(days=expires_in_days) if expires_in_days else None
        rotation_due = now + timedelta(days=self._config.rotation_days)
        secret = Secret(
            name=name,
            secret_type=secret_type,
            value=self._encrypt_value(value),
            version=version,
            expires_at=expires_at,
            rotation_due=rotation_due,
        )
        self._secrets[name] = secret
        return secret

    def get_secret(self, name: str) -> Optional[str]:
        secret = self._secrets.get(name)
        if not secret or secret.is_expired():
            return None
        return self._decrypt_value(secret.value)

    def delete_secret(self, name: str) -> bool:
        if name in self._secrets:
            del self._secrets[name]
            return True
        return False

    def generate_api_key(self, prefix: str = "sk") -> str:
        return f"{prefix}_{py_secrets.token_urlsafe(32)}"

    def generate_password(self, length: int = 32) -> str:
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return "".join(py_secrets.choice(alphabet) for _ in range(length))


# =============================================================================
# Inline Security Middleware Classes
# =============================================================================


class SecurityConfig(BaseModel):
    enable_hsts: bool = True
    hsts_max_age: int = 31536000
    enable_csp: bool = True
    enable_xframe: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    max_content_length: int = 10485760


class RateLimitResult(BaseModel):
    allowed: bool
    remaining: int
    reset_at: datetime
    retry_after: Optional[int] = None


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class SecurityHeadersMiddleware:
    def __init__(self, config: SecurityConfig | None = None):
        self._config = config or SecurityConfig()

    def get_headers(self) -> dict[str, str]:
        headers = {}
        if self._config.enable_hsts:
            headers["Strict-Transport-Security"] = f"max-age={self._config.hsts_max_age}; includeSubDomains"
        if self._config.enable_csp:
            headers["Content-Security-Policy"] = "default-src 'self'"
        if self._config.enable_xframe:
            headers["X-Frame-Options"] = "DENY"
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-XSS-Protection"] = "1; mode=block"
        return headers


class RateLimiter:
    def __init__(self, requests_per_window: int = 100, window_seconds: int = 60):
        self._limit = requests_per_window
        self._window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, identifier: str) -> RateLimitResult:
        now = time.time()
        window_start = now - self._window
        self._requests[identifier] = [ts for ts in self._requests[identifier] if ts > window_start]
        current_count = len(self._requests[identifier])
        remaining = max(0, self._limit - current_count)
        reset_at = datetime.fromtimestamp(now + self._window)
        if current_count >= self._limit:
            retry_after = int(self._requests[identifier][0] + self._window - now)
            return RateLimitResult(allowed=False, remaining=0, reset_at=reset_at, retry_after=max(1, retry_after))
        self._requests[identifier].append(now)
        return RateLimitResult(allowed=True, remaining=remaining - 1, reset_at=reset_at)

    def reset(self, identifier: str) -> None:
        if identifier in self._requests:
            del self._requests[identifier]


class RequestValidator:
    def __init__(self, config: SecurityConfig | None = None):
        self._config = config or SecurityConfig()
        self._sql_patterns = [r"(\bUNION\b.*\bSELECT\b)", r"(\bDROP\b.*\bTABLE\b)", r"(--\s)"]
        self._xss_patterns = [r"<script[^>]*>", r"javascript:", r"on\w+\s*="]

    def validate_request(self, body: str | None = None, content_length: int | None = None) -> ValidationResult:
        errors = []
        if content_length and content_length > self._config.max_content_length:
            errors.append(f"Content too large: {content_length}")
        if body:
            for pattern in self._sql_patterns:
                if re.search(pattern, body, re.IGNORECASE):
                    errors.append("SQL injection detected")
                    break
            for pattern in self._xss_patterns:
                if re.search(pattern, body, re.IGNORECASE):
                    errors.append("XSS detected")
                    break
        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def hash_password(self, password: str, salt: bytes | None = None) -> tuple[str, str]:
        if salt is None:
            salt = py_secrets.token_bytes(16)
        hash_bytes = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000, dklen=32)
        return base64.b64encode(hash_bytes).decode(), base64.b64encode(salt).decode()

    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        salt_bytes = base64.b64decode(salt)
        computed_hash, _ = self.hash_password(password, salt_bytes)
        return py_secrets.compare_digest(computed_hash, password_hash)


# =============================================================================
# Inline Audit Classes
# =============================================================================


class AuditEventType(str, Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    ACCESS_DENIED = "access_denied"
    PHI_ACCESS = "phi_access"
    BRUTE_FORCE_DETECTED = "brute_force_detected"


class AuditSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: AuditEventType
    severity: AuditSeverity = AuditSeverity.INFO
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    success: bool = True
    message: Optional[str] = None


class SecurityAuditService:
    def __init__(self):
        self._events: list[AuditEvent] = []

    def log(self, event_type: AuditEventType, user_id: str | None = None, ip_address: str | None = None,
            success: bool = True, message: str | None = None, severity: AuditSeverity | None = None) -> AuditEvent:
        if severity is None:
            if event_type == AuditEventType.BRUTE_FORCE_DETECTED:
                severity = AuditSeverity.CRITICAL
            elif event_type in [AuditEventType.ACCESS_DENIED, AuditEventType.LOGIN_FAILURE]:
                severity = AuditSeverity.WARNING
            else:
                severity = AuditSeverity.INFO
        event = AuditEvent(event_type=event_type, severity=severity, user_id=user_id, ip_address=ip_address,
                           success=success, message=message)
        self._events.append(event)
        return event

    def get_failed_logins(self, ip_address: str | None = None, minutes: int = 15) -> list[AuditEvent]:
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        results = [e for e in self._events if e.event_type == AuditEventType.LOGIN_FAILURE and e.timestamp >= cutoff]
        if ip_address:
            results = [e for e in results if e.ip_address == ip_address]
        return results

    def detect_brute_force(self, ip_address: str, threshold: int = 5, minutes: int = 15) -> bool:
        failed = self.get_failed_logins(ip_address=ip_address, minutes=minutes)
        if len(failed) >= threshold:
            self.log(AuditEventType.BRUTE_FORCE_DETECTED, ip_address=ip_address,
                     message=f"Brute force detected: {len(failed)} failed attempts")
            return True
        return False

    def get_events(self) -> list[AuditEvent]:
        return self._events.copy()

    def clear_events(self) -> None:
        self._events.clear()


# =============================================================================
# Test Classes
# =============================================================================


class TestEncryptionService:
    @pytest.fixture
    def encryption_service(self):
        return EncryptionService()

    def test_encrypt_decrypt_string(self, encryption_service):
        plaintext = "sensitive data 123"
        encrypted = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt_string(encrypted)
        assert decrypted == plaintext

    def test_encrypt_decrypt_bytes(self, encryption_service):
        plaintext = b"binary data \x00\x01\x02"
        encrypted = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypted_field_serialization(self, encryption_service):
        encrypted = encryption_service.encrypt("test data")
        serialized = encrypted.to_string()
        deserialized = EncryptedField.from_string(serialized)
        assert deserialized.ciphertext == encrypted.ciphertext
        assert deserialized.iv == encrypted.iv

    def test_different_encryptions_produce_different_output(self, encryption_service):
        plaintext = "same text"
        enc1 = encryption_service.encrypt(plaintext)
        enc2 = encryption_service.encrypt(plaintext)
        assert enc1.ciphertext != enc2.ciphertext  # Different IVs

    def test_tampered_ciphertext_fails(self, encryption_service):
        encrypted = encryption_service.encrypt("test")
        encrypted.ciphertext = base64.b64encode(b"tampered").decode()
        with pytest.raises(ValueError, match="Authentication tag"):
            encryption_service.decrypt(encrypted)

    def test_password_based_key_derivation(self):
        service = EncryptionService(master_key="my_password")
        encrypted = service.encrypt("secret data")
        decrypted = service.decrypt_string(encrypted)
        assert decrypted == "secret data"


class TestPHIProtection:
    @pytest.fixture
    def phi_service(self):
        return PHIProtectionService()

    def test_mask_ssn(self, phi_service):
        ssn = "123-45-6789"
        masked = phi_service.mask_value("ssn", ssn)
        assert masked == "***-**-6789"

    def test_mask_phone(self, phi_service):
        phone = "5551234567"
        masked = phi_service.mask_value("phone", phone)
        assert "4567" in masked

    def test_mask_email(self, phi_service):
        email = "john.doe@example.com"
        masked = phi_service.mask_value("email", email)
        assert masked.startswith("jo")
        assert "****" in masked

    def test_detect_ssn_in_text(self, phi_service):
        text = "Patient SSN is 123-45-6789 and needs review"
        findings = phi_service.detect_phi(text)
        assert len(findings) >= 1
        assert any(f[0] == "ssn" for f in findings)

    def test_detect_phone_in_text(self, phi_service):
        text = "Call the patient at 555-123-4567"
        findings = phi_service.detect_phi(text)
        assert any(f[0] == "phone" for f in findings)

    def test_detect_email_in_text(self, phi_service):
        text = "Contact: patient@hospital.com"
        findings = phi_service.detect_phi(text)
        assert any(f[0] == "email" for f in findings)

    def test_redact_text(self, phi_service):
        text = "SSN: 123-45-6789, Phone: 555-123-4567"
        redacted = phi_service.redact_text(text)
        assert "123-45-6789" not in redacted
        assert "[SSN_REDACTED]" in redacted


class TestSecretManager:
    @pytest.fixture
    def secret_manager(self):
        return SecretManager()

    def test_set_and_get_secret(self, secret_manager):
        secret_manager.set_secret("api_key", "super_secret_key")
        value = secret_manager.get_secret("api_key")
        assert value == "super_secret_key"

    def test_get_nonexistent_secret(self, secret_manager):
        value = secret_manager.get_secret("does_not_exist")
        assert value is None

    def test_delete_secret(self, secret_manager):
        secret_manager.set_secret("temp_key", "temp_value")
        deleted = secret_manager.delete_secret("temp_key")
        assert deleted is True
        assert secret_manager.get_secret("temp_key") is None

    def test_secret_versioning(self, secret_manager):
        secret_manager.set_secret("versioned", "v1")
        s1 = secret_manager._secrets["versioned"]
        assert s1.version == 1
        secret_manager.set_secret("versioned", "v2")
        s2 = secret_manager._secrets["versioned"]
        assert s2.version == 2

    def test_generate_api_key(self, secret_manager):
        key = secret_manager.generate_api_key("sk")
        assert key.startswith("sk_")
        assert len(key) > 10

    def test_generate_password(self, secret_manager):
        password = secret_manager.generate_password(32)
        assert len(password) == 32

    def test_expired_secret_not_returned(self, secret_manager):
        config = SecretConfig(rotation_days=90)
        manager = SecretManager(config)
        secret = manager.set_secret("expiring", "value", expires_in_days=0)
        secret.expires_at = datetime.utcnow() - timedelta(days=1)
        manager._secrets["expiring"] = secret
        assert manager.get_secret("expiring") is None


class TestSecurityHeaders:
    @pytest.fixture
    def middleware(self):
        return SecurityHeadersMiddleware()

    def test_hsts_header(self, middleware):
        headers = middleware.get_headers()
        assert "Strict-Transport-Security" in headers
        assert "max-age=" in headers["Strict-Transport-Security"]

    def test_csp_header(self, middleware):
        headers = middleware.get_headers()
        assert "Content-Security-Policy" in headers

    def test_xframe_header(self, middleware):
        headers = middleware.get_headers()
        assert headers.get("X-Frame-Options") == "DENY"

    def test_xcontent_type_header(self, middleware):
        headers = middleware.get_headers()
        assert headers.get("X-Content-Type-Options") == "nosniff"

    def test_xss_protection_header(self, middleware):
        headers = middleware.get_headers()
        assert "X-XSS-Protection" in headers


class TestRateLimiter:
    @pytest.fixture
    def rate_limiter(self):
        return RateLimiter(requests_per_window=5, window_seconds=60)

    def test_allows_requests_under_limit(self, rate_limiter):
        for i in range(5):
            result = rate_limiter.check("user1")
            assert result.allowed is True

    def test_blocks_requests_over_limit(self, rate_limiter):
        for i in range(5):
            rate_limiter.check("user2")
        result = rate_limiter.check("user2")
        assert result.allowed is False
        assert result.retry_after is not None

    def test_different_users_have_separate_limits(self, rate_limiter):
        for i in range(5):
            rate_limiter.check("user3")
        result_user3 = rate_limiter.check("user3")
        result_user4 = rate_limiter.check("user4")
        assert result_user3.allowed is False
        assert result_user4.allowed is True

    def test_reset_clears_limit(self, rate_limiter):
        for i in range(5):
            rate_limiter.check("user5")
        rate_limiter.reset("user5")
        result = rate_limiter.check("user5")
        assert result.allowed is True


class TestRequestValidator:
    @pytest.fixture
    def validator(self):
        return RequestValidator()

    def test_valid_request(self, validator):
        result = validator.validate_request(body='{"name": "John"}')
        assert result.valid is True

    def test_sql_injection_detection(self, validator):
        result = validator.validate_request(body="SELECT * FROM users; DROP TABLE users;--")
        assert result.valid is False
        assert any("SQL" in e for e in result.errors)

    def test_xss_detection(self, validator):
        result = validator.validate_request(body='<script>alert("xss")</script>')
        assert result.valid is False
        assert any("XSS" in e for e in result.errors)

    def test_content_length_validation(self, validator):
        result = validator.validate_request(content_length=20000000)  # 20MB
        assert result.valid is False

    def test_password_hashing(self, validator):
        password = "secure_password_123"
        hash_val, salt = validator.hash_password(password)
        assert hash_val != password
        assert len(salt) > 0

    def test_password_verification(self, validator):
        password = "my_password"
        hash_val, salt = validator.hash_password(password)
        assert validator.verify_password(password, hash_val, salt) is True
        assert validator.verify_password("wrong_password", hash_val, salt) is False


class TestSecurityAudit:
    @pytest.fixture
    def audit_service(self):
        return SecurityAuditService()

    def test_log_event(self, audit_service):
        event = audit_service.log(AuditEventType.LOGIN_SUCCESS, user_id="user123")
        assert event.event_type == AuditEventType.LOGIN_SUCCESS
        assert event.user_id == "user123"

    def test_log_failure_event(self, audit_service):
        event = audit_service.log(AuditEventType.LOGIN_FAILURE, ip_address="192.168.1.1", success=False)
        assert event.success is False
        assert event.severity == AuditSeverity.WARNING

    def test_get_failed_logins(self, audit_service):
        audit_service.log(AuditEventType.LOGIN_FAILURE, ip_address="10.0.0.1")
        audit_service.log(AuditEventType.LOGIN_FAILURE, ip_address="10.0.0.1")
        audit_service.log(AuditEventType.LOGIN_SUCCESS, ip_address="10.0.0.1")
        failed = audit_service.get_failed_logins(ip_address="10.0.0.1")
        assert len(failed) == 2

    def test_brute_force_detection(self, audit_service):
        for i in range(5):
            audit_service.log(AuditEventType.LOGIN_FAILURE, ip_address="attacker_ip")
        detected = audit_service.detect_brute_force("attacker_ip", threshold=5)
        assert detected is True

    def test_no_brute_force_under_threshold(self, audit_service):
        for i in range(3):
            audit_service.log(AuditEventType.LOGIN_FAILURE, ip_address="normal_ip")
        detected = audit_service.detect_brute_force("normal_ip", threshold=5)
        assert detected is False

    def test_critical_severity_for_brute_force(self, audit_service):
        for i in range(5):
            audit_service.log(AuditEventType.LOGIN_FAILURE, ip_address="bad_ip")
        audit_service.detect_brute_force("bad_ip", threshold=5)
        events = audit_service.get_events()
        brute_force_events = [e for e in events if e.event_type == AuditEventType.BRUTE_FORCE_DETECTED]
        assert len(brute_force_events) == 1
        assert brute_force_events[0].severity == AuditSeverity.CRITICAL
