"""
Security Middleware.
Source: Design Document Section 5.2 - Security Hardening
Verified: 2025-12-18

Provides security headers, rate limiting, and request validation.
"""

import hashlib
import re
import time
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field


class SecurityLevel(str, Enum):
    """Security strictness levels."""

    PERMISSIVE = "permissive"
    STANDARD = "standard"
    STRICT = "strict"


class SecurityConfig(BaseModel):
    """Security configuration."""

    level: SecurityLevel = SecurityLevel.STANDARD

    # Headers
    enable_hsts: bool = True
    hsts_max_age: int = 31536000  # 1 year
    enable_csp: bool = True
    csp_directives: dict[str, str] = Field(default_factory=lambda: {
        "default-src": "'self'",
        "script-src": "'self'",
        "style-src": "'self' 'unsafe-inline'",
        "img-src": "'self' data:",
        "font-src": "'self'",
        "connect-src": "'self'",
        "frame-ancestors": "'none'",
    })
    enable_xframe: bool = True
    xframe_option: str = "DENY"
    enable_xcontent_type: bool = True
    enable_referrer_policy: bool = True
    referrer_policy: str = "strict-origin-when-cross-origin"

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Request validation
    max_content_length: int = 10485760  # 10MB
    allowed_content_types: list[str] = Field(default_factory=lambda: [
        "application/json",
        "multipart/form-data",
        "application/x-www-form-urlencoded",
    ])


class SecurityHeaders(BaseModel):
    """Security headers to add to responses."""

    headers: dict[str, str] = Field(default_factory=dict)


class RateLimitResult(BaseModel):
    """Result of rate limit check."""

    allowed: bool
    remaining: int
    reset_at: datetime
    retry_after: Optional[int] = None


class ValidationResult(BaseModel):
    """Result of request validation."""

    valid: bool
    errors: list[str] = Field(default_factory=list)


class SecurityHeadersMiddleware:
    """Middleware for adding security headers."""

    def __init__(self, config: SecurityConfig | None = None):
        """Initialize SecurityHeadersMiddleware."""
        self._config = config or SecurityConfig()

    @property
    def config(self) -> SecurityConfig:
        """Get configuration."""
        return self._config

    def get_headers(self) -> dict[str, str]:
        """Generate security headers based on configuration.

        Returns:
            Dictionary of header name -> value
        """
        headers = {}

        # HSTS (HTTP Strict Transport Security)
        if self._config.enable_hsts:
            headers["Strict-Transport-Security"] = (
                f"max-age={self._config.hsts_max_age}; includeSubDomains"
            )

        # CSP (Content Security Policy)
        if self._config.enable_csp:
            csp_parts = [
                f"{directive} {value}"
                for directive, value in self._config.csp_directives.items()
            ]
            headers["Content-Security-Policy"] = "; ".join(csp_parts)

        # X-Frame-Options
        if self._config.enable_xframe:
            headers["X-Frame-Options"] = self._config.xframe_option

        # X-Content-Type-Options
        if self._config.enable_xcontent_type:
            headers["X-Content-Type-Options"] = "nosniff"

        # Referrer Policy
        if self._config.enable_referrer_policy:
            headers["Referrer-Policy"] = self._config.referrer_policy

        # Additional security headers
        headers["X-XSS-Protection"] = "1; mode=block"
        headers["X-Permitted-Cross-Domain-Policies"] = "none"
        headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        headers["Cross-Origin-Opener-Policy"] = "same-origin"
        headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Permissions Policy (formerly Feature-Policy)
        headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        return headers

    def apply_headers(self, response_headers: dict[str, str]) -> dict[str, str]:
        """Apply security headers to existing response headers.

        Args:
            response_headers: Existing response headers

        Returns:
            Updated headers with security headers added
        """
        result = response_headers.copy()
        security_headers = self.get_headers()

        for key, value in security_headers.items():
            if key not in result:  # Don't override existing headers
                result[key] = value

        return result


class RateLimiter:
    """Rate limiting service."""

    def __init__(
        self,
        requests_per_window: int = 100,
        window_seconds: int = 60,
    ):
        """Initialize RateLimiter.

        Args:
            requests_per_window: Maximum requests allowed per window
            window_seconds: Window duration in seconds
        """
        self._limit = requests_per_window
        self._window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, identifier: str) -> RateLimitResult:
        """Check if request is allowed.

        Args:
            identifier: Client identifier (IP, user ID, API key)

        Returns:
            RateLimitResult indicating if request is allowed
        """
        now = time.time()
        window_start = now - self._window

        # Clean old requests
        self._requests[identifier] = [
            ts for ts in self._requests[identifier]
            if ts > window_start
        ]

        current_count = len(self._requests[identifier])
        remaining = max(0, self._limit - current_count)

        # Calculate reset time
        if self._requests[identifier]:
            oldest = min(self._requests[identifier])
            reset_at = datetime.fromtimestamp(oldest + self._window)
        else:
            reset_at = datetime.fromtimestamp(now + self._window)

        if current_count >= self._limit:
            retry_after = int(self._requests[identifier][0] + self._window - now)
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=reset_at,
                retry_after=max(1, retry_after),
            )

        # Record this request
        self._requests[identifier].append(now)

        return RateLimitResult(
            allowed=True,
            remaining=remaining - 1,
            reset_at=reset_at,
        )

    def get_headers(self, result: RateLimitResult) -> dict[str, str]:
        """Get rate limit headers for response.

        Args:
            result: Rate limit check result

        Returns:
            Headers to add to response
        """
        headers = {
            "X-RateLimit-Limit": str(self._limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(int(result.reset_at.timestamp())),
        }

        if result.retry_after:
            headers["Retry-After"] = str(result.retry_after)

        return headers

    def reset(self, identifier: str) -> None:
        """Reset rate limit for identifier."""
        if identifier in self._requests:
            del self._requests[identifier]

    def reset_all(self) -> None:
        """Reset all rate limits."""
        self._requests.clear()


class RequestValidator:
    """Request validation service."""

    def __init__(self, config: SecurityConfig | None = None):
        """Initialize RequestValidator."""
        self._config = config or SecurityConfig()

        # SQL injection patterns
        self._sql_patterns = [
            r"(\bUNION\b.*\bSELECT\b)",
            r"(\bSELECT\b.*\bFROM\b)",
            r"(\bINSERT\b.*\bINTO\b)",
            r"(\bDELETE\b.*\bFROM\b)",
            r"(\bDROP\b.*\bTABLE\b)",
            r"(--\s)",
            r"(/\*.*\*/)",
            r"(\bOR\b\s+\d+\s*=\s*\d+)",
            r"(\bAND\b\s+\d+\s*=\s*\d+)",
        ]

        # XSS patterns
        self._xss_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
        ]

        # Path traversal patterns
        self._path_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%2e%2e/",
            r"\.%2e/",
        ]

    def validate_request(
        self,
        content_type: str | None = None,
        content_length: int | None = None,
        body: str | bytes | None = None,
        path: str | None = None,
        query_params: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Validate incoming request.

        Args:
            content_type: Request content type
            content_length: Request content length
            body: Request body
            path: Request path
            query_params: Query parameters

        Returns:
            ValidationResult
        """
        errors = []

        # Validate content type
        if content_type:
            base_type = content_type.split(";")[0].strip()
            if base_type not in self._config.allowed_content_types:
                errors.append(f"Content type not allowed: {base_type}")

        # Validate content length
        if content_length and content_length > self._config.max_content_length:
            errors.append(
                f"Content length {content_length} exceeds maximum "
                f"{self._config.max_content_length}"
            )

        # Validate body for injection attacks
        if body:
            body_str = body if isinstance(body, str) else body.decode("utf-8", errors="ignore")

            sql_result = self._check_sql_injection(body_str)
            if sql_result:
                errors.append(f"Potential SQL injection detected: {sql_result}")

            xss_result = self._check_xss(body_str)
            if xss_result:
                errors.append(f"Potential XSS attack detected: {xss_result}")

        # Validate path
        if path:
            path_result = self._check_path_traversal(path)
            if path_result:
                errors.append(f"Path traversal attempt detected: {path_result}")

        # Validate query parameters
        if query_params:
            for key, value in query_params.items():
                if isinstance(value, str):
                    sql_result = self._check_sql_injection(value)
                    if sql_result:
                        errors.append(f"SQL injection in param '{key}'")

                    xss_result = self._check_xss(value)
                    if xss_result:
                        errors.append(f"XSS in param '{key}'")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def _check_sql_injection(self, value: str) -> Optional[str]:
        """Check for SQL injection patterns."""
        for pattern in self._sql_patterns:
            match = re.search(pattern, value, re.IGNORECASE)
            if match:
                return match.group(0)[:50]
        return None

    def _check_xss(self, value: str) -> Optional[str]:
        """Check for XSS patterns."""
        for pattern in self._xss_patterns:
            match = re.search(pattern, value, re.IGNORECASE)
            if match:
                return match.group(0)[:50]
        return None

    def _check_path_traversal(self, path: str) -> Optional[str]:
        """Check for path traversal patterns."""
        for pattern in self._path_patterns:
            match = re.search(pattern, path, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def sanitize_input(self, value: str) -> str:
        """Sanitize input string.

        Args:
            value: Input to sanitize

        Returns:
            Sanitized string
        """
        # HTML encode special characters
        replacements = {
            "<": "&lt;",
            ">": "&gt;",
            "&": "&amp;",
            '"': "&quot;",
            "'": "&#x27;",
            "/": "&#x2F;",
        }

        result = value
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)

        return result

    def hash_password(self, password: str, salt: bytes | None = None) -> tuple[str, str]:
        """Hash a password securely.

        Args:
            password: Password to hash
            salt: Optional salt (generated if not provided)

        Returns:
            Tuple of (hash, salt) as base64 strings
        """
        import secrets as py_secrets

        if salt is None:
            salt = py_secrets.token_bytes(16)

        # Use PBKDF2 with SHA-256
        hash_bytes = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            iterations=100000,
            dklen=32,
        )

        import base64
        return (
            base64.b64encode(hash_bytes).decode(),
            base64.b64encode(salt).decode(),
        )

    def verify_password(
        self,
        password: str,
        password_hash: str,
        salt: str,
    ) -> bool:
        """Verify a password against its hash.

        Args:
            password: Password to verify
            password_hash: Stored hash (base64)
            salt: Stored salt (base64)

        Returns:
            True if password matches
        """
        import base64
        import secrets as py_secrets

        salt_bytes = base64.b64decode(salt)
        computed_hash, _ = self.hash_password(password, salt_bytes)

        return py_secrets.compare_digest(computed_hash, password_hash)


# =============================================================================
# Factory Functions
# =============================================================================


def create_security_middleware(config: SecurityConfig | None = None) -> SecurityHeadersMiddleware:
    """Create SecurityHeadersMiddleware instance."""
    return SecurityHeadersMiddleware(config)


def create_rate_limiter(
    requests_per_window: int = 100,
    window_seconds: int = 60,
) -> RateLimiter:
    """Create RateLimiter instance."""
    return RateLimiter(requests_per_window, window_seconds)


def create_request_validator(config: SecurityConfig | None = None) -> RequestValidator:
    """Create RequestValidator instance."""
    return RequestValidator(config)
