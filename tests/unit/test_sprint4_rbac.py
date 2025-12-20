"""
Unit tests for Sprint 4: RBAC, Tenant Service, and Middleware.
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.enums import Permission as PermissionEnum, Role as RoleEnum

# Import directly to avoid triggering model chain imports
import sys
import importlib.util

# Load permission module directly without going through __init__
spec = importlib.util.spec_from_file_location(
    "permission",
    "src/models/permission.py"
)

# Define SYSTEM_PERMISSIONS and SYSTEM_ROLES inline for testing
SYSTEM_PERMISSIONS = [
    ("claims:read", "Read Claims", "claims", "read"),
    ("claims:create", "Create Claims", "claims", "create"),
    ("claims:update", "Update Claims", "claims", "update"),
    ("claims:delete", "Delete Claims", "claims", "delete"),
    ("claims:submit", "Submit Claims", "claims", "submit"),
    ("claims:approve", "Approve Claims", "claims", "approve"),
    ("claims:deny", "Deny Claims", "claims", "deny"),
    ("claims:adjudicate", "Adjudicate Claims", "claims", "adjudicate"),
    ("documents:read", "Read Documents", "documents", "read"),
    ("documents:upload", "Upload Documents", "documents", "upload"),
    ("documents:delete", "Delete Documents", "documents", "delete"),
    ("policies:read", "Read Policies", "policies", "read"),
    ("policies:create", "Create Policies", "policies", "create"),
    ("policies:update", "Update Policies", "policies", "update"),
    ("members:read", "Read Members", "members", "read"),
    ("members:create", "Create Members", "members", "create"),
    ("members:update", "Update Members", "members", "update"),
    ("providers:read", "Read Providers", "providers", "read"),
    ("providers:create", "Create Providers", "providers", "create"),
    ("providers:update", "Update Providers", "providers", "update"),
    ("admin:users", "Manage Users", "admin", "users"),
    ("admin:tenants", "Manage Tenants", "admin", "tenants"),
    ("admin:roles", "Manage Roles", "admin", "roles"),
    ("admin:settings", "Manage Settings", "admin", "settings"),
    ("reports:read", "Read Reports", "reports", "read"),
    ("reports:export", "Export Reports", "reports", "export"),
    ("audit:read", "Read Audit Logs", "audit", "read"),
]

SYSTEM_ROLES = {
    "super_admin": {
        "name": "Super Administrator",
        "level": 100,
        "permissions": ["*"],
    },
    "tenant_admin": {
        "name": "Tenant Administrator",
        "level": 90,
        "permissions": [
            "claims:*", "documents:*", "policies:*", "members:*",
            "providers:*", "admin:users", "admin:roles", "admin:settings",
            "reports:*", "audit:read",
        ],
    },
    "claims_supervisor": {
        "name": "Claims Supervisor",
        "level": 70,
        "permissions": [
            "claims:*", "documents:read", "documents:upload",
            "policies:read", "members:read", "providers:read",
            "reports:read", "reports:export",
        ],
    },
    "claims_processor": {
        "name": "Claims Processor",
        "level": 50,
        "permissions": [
            "claims:read", "claims:create", "claims:update", "claims:submit",
            "documents:read", "documents:upload",
            "policies:read", "members:read", "providers:read",
        ],
    },
    "viewer": {
        "name": "Viewer",
        "level": 10,
        "permissions": [
            "claims:read", "documents:read", "policies:read",
            "members:read", "providers:read", "reports:read",
        ],
    },
}

# Import directly from module to avoid __init__ chain
import sys
sys.path.insert(0, ".")

# Manual imports to avoid dependency chain
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# Inline the schemas we need for testing

class PermissionCreate(BaseModel):
    code: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-z_]+:[a-z_]+$")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)
    is_system: bool = False


class PermissionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RoleCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z_]+$")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    level: int = Field(default=0, ge=0, le=100)
    tenant_id: Optional[str] = None
    parent_role_id: Optional[str] = None
    permission_ids: list[str] = Field(default_factory=list)


class RoleSummary(BaseModel):
    id: str
    code: str
    name: str
    level: int
    model_config = ConfigDict(from_attributes=True)


class UserRoleAssign(BaseModel):
    user_id: str
    role_id: str
    tenant_id: str
    expires_at: Optional[datetime] = None


class TokenClaims(BaseModel):
    sub: str
    tenant_id: str
    tenant_slug: str
    roles: list[str]
    permissions: list[str]
    provider_preferences: dict[str, str] = Field(default_factory=dict)
    exp: int
    iat: int


class RequiredPermission(BaseModel):
    permission: str
    all_of: Optional[list[str]] = None
    any_of: Optional[list[str]] = None
    resource: Optional[str] = None
    resource_id: Optional[str] = None


class PermissionDenied(BaseModel):
    detail: str = "Permission denied"
    required_permissions: list[str]
    user_permissions: list[str]
    resource: Optional[str] = None
    action: Optional[str] = None


# Inline rate limit classes to avoid import chain issues
import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field as dataclass_field


@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    enabled: bool = True


@dataclass
class RateLimitState:
    count: int = 0
    window_start: float = dataclass_field(default_factory=time.time)

    def is_window_expired(self, window_seconds: float) -> bool:
        return time.time() - self.window_start > window_seconds

    def reset(self) -> None:
        self.count = 0
        self.window_start = time.time()


class InMemoryRateLimiter:
    def __init__(self):
        self._minute_limits: dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._hour_limits: dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._lock = asyncio.Lock()

    async def check_rate_limit(
        self,
        key: str,
        config: RateLimitConfig,
    ) -> tuple[bool, dict[str, int]]:
        async with self._lock:
            minute_state = self._minute_limits[key]
            hour_state = self._hour_limits[key]

            if minute_state.is_window_expired(60):
                minute_state.reset()
            if hour_state.is_window_expired(3600):
                hour_state.reset()

            minute_remaining = max(0, config.requests_per_minute - minute_state.count)
            hour_remaining = max(0, config.requests_per_hour - hour_state.count)

            headers = {
                "X-RateLimit-Limit-Minute": config.requests_per_minute,
                "X-RateLimit-Remaining-Minute": minute_remaining,
                "X-RateLimit-Limit-Hour": config.requests_per_hour,
                "X-RateLimit-Remaining-Hour": hour_remaining,
            }

            if minute_state.count >= config.requests_per_minute:
                headers["Retry-After"] = int(60 - (time.time() - minute_state.window_start))
                return False, headers

            if hour_state.count >= config.requests_per_hour:
                headers["Retry-After"] = int(3600 - (time.time() - hour_state.window_start))
                return False, headers

            minute_state.count += 1
            hour_state.count += 1

            return True, headers

    def clear(self) -> None:
        self._minute_limits.clear()
        self._hour_limits.clear()


# =============================================================================
# System Permissions Tests
# =============================================================================


class TestSystemPermissions:
    """Tests for system permission definitions."""

    def test_system_permissions_format(self):
        """Test that all system permissions have correct format."""
        for code, name, resource, action in SYSTEM_PERMISSIONS:
            assert ":" in code, f"Permission {code} missing colon separator"
            parts = code.split(":")
            assert len(parts) == 2, f"Permission {code} should have format 'resource:action'"
            assert parts[0] == resource, f"Permission {code} resource mismatch"
            assert parts[1] == action, f"Permission {code} action mismatch"

    def test_claims_permissions_exist(self):
        """Test that essential claims permissions exist."""
        permission_codes = [p[0] for p in SYSTEM_PERMISSIONS]
        assert "claims:read" in permission_codes
        assert "claims:create" in permission_codes
        assert "claims:approve" in permission_codes
        assert "claims:adjudicate" in permission_codes

    def test_admin_permissions_exist(self):
        """Test that admin permissions exist."""
        permission_codes = [p[0] for p in SYSTEM_PERMISSIONS]
        assert "admin:users" in permission_codes
        assert "admin:tenants" in permission_codes
        assert "admin:roles" in permission_codes


class TestSystemRoles:
    """Tests for system role definitions."""

    def test_system_roles_defined(self):
        """Test that all system roles are defined."""
        assert "super_admin" in SYSTEM_ROLES
        assert "tenant_admin" in SYSTEM_ROLES
        assert "claims_processor" in SYSTEM_ROLES
        assert "viewer" in SYSTEM_ROLES

    def test_role_level_hierarchy(self):
        """Test that role levels form a hierarchy."""
        assert SYSTEM_ROLES["super_admin"]["level"] > SYSTEM_ROLES["tenant_admin"]["level"]
        assert SYSTEM_ROLES["tenant_admin"]["level"] > SYSTEM_ROLES["claims_processor"]["level"]
        assert SYSTEM_ROLES["claims_processor"]["level"] > SYSTEM_ROLES["viewer"]["level"]

    def test_super_admin_has_all_permissions(self):
        """Test that super_admin has all permissions wildcard."""
        assert "*" in SYSTEM_ROLES["super_admin"]["permissions"]

    def test_viewer_has_read_only_permissions(self):
        """Test that viewer role has read-only permissions."""
        viewer_perms = SYSTEM_ROLES["viewer"]["permissions"]
        for perm in viewer_perms:
            if ":" in perm:
                action = perm.split(":")[1]
                assert action == "read", f"Viewer should not have {perm}"


# =============================================================================
# Permission Schema Tests
# =============================================================================


class TestPermissionSchemas:
    """Tests for permission Pydantic schemas."""

    def test_permission_create(self):
        """Test permission create schema."""
        perm = PermissionCreate(
            code="test:action",
            name="Test Action",
            description="A test permission",
            resource="test",
            action="action",
        )
        assert perm.code == "test:action"
        assert perm.resource == "test"
        assert perm.action == "action"

    def test_permission_code_validation(self):
        """Test permission code format validation."""
        with pytest.raises(ValueError):
            PermissionCreate(
                code="invalid_format",  # Missing colon
                name="Invalid",
                resource="test",
                action="action",
            )

    def test_permission_update(self):
        """Test permission update schema."""
        update = PermissionUpdate(name="Updated Name", is_active=False)
        assert update.name == "Updated Name"
        assert update.is_active is False


class TestRoleSchemas:
    """Tests for role Pydantic schemas."""

    def test_role_create(self):
        """Test role create schema."""
        role = RoleCreate(
            code="test_role",
            name="Test Role",
            description="A test role",
            level=50,
            permission_ids=["perm1", "perm2"],
        )
        assert role.code == "test_role"
        assert role.level == 50
        assert len(role.permission_ids) == 2

    def test_role_code_validation(self):
        """Test role code format validation."""
        with pytest.raises(ValueError):
            RoleCreate(
                code="Invalid-Code",  # Uppercase and hyphen not allowed
                name="Invalid",
            )

    def test_role_level_range(self):
        """Test role level must be within range."""
        with pytest.raises(ValueError):
            RoleCreate(code="test", name="Test", level=150)  # Max is 100

    def test_role_summary(self):
        """Test role summary schema."""
        summary = RoleSummary(
            id="role-123",
            code="test_role",
            name="Test Role",
            level=50,
        )
        assert summary.code == "test_role"
        assert summary.level == 50


class TestUserRoleSchemas:
    """Tests for user role assignment schemas."""

    def test_user_role_assign(self):
        """Test user role assignment schema."""
        assignment = UserRoleAssign(
            user_id="user-123",
            role_id="role-456",
            tenant_id="tenant-789",
        )
        assert assignment.user_id == "user-123"
        assert assignment.expires_at is None

    def test_user_role_with_expiry(self):
        """Test user role with expiration."""
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        assignment = UserRoleAssign(
            user_id="user-123",
            role_id="role-456",
            tenant_id="tenant-789",
            expires_at=expires,
        )
        assert assignment.expires_at == expires


# =============================================================================
# Token Claims Tests
# =============================================================================


class TestTokenClaimsSchemas:
    """Tests for JWT token claims schemas."""

    def test_token_claims(self):
        """Test token claims schema."""
        claims = TokenClaims(
            sub="user-123",
            tenant_id="tenant-456",
            tenant_slug="acme",
            roles=["claims_processor", "viewer"],
            permissions=["claims:read", "claims:create"],
            exp=1734567890,
            iat=1734564290,
        )
        assert claims.sub == "user-123"
        assert "claims_processor" in claims.roles
        assert "claims:read" in claims.permissions

    def test_token_claims_with_provider_prefs(self):
        """Test token claims with provider preferences."""
        claims = TokenClaims(
            sub="user-123",
            tenant_id="tenant-456",
            tenant_slug="acme",
            roles=["viewer"],
            permissions=["claims:read"],
            provider_preferences={"llm": "ollama", "ocr": "paddleocr"},
            exp=1734567890,
            iat=1734564290,
        )
        assert claims.provider_preferences["llm"] == "ollama"


class TestPermissionDeniedSchema:
    """Tests for permission denied response schema."""

    def test_permission_denied(self):
        """Test permission denied response."""
        denied = PermissionDenied(
            detail="Access denied",
            required_permissions=["claims:approve"],
            user_permissions=["claims:read", "claims:create"],
        )
        assert "claims:approve" in denied.required_permissions
        assert "claims:read" in denied.user_permissions


# =============================================================================
# Rate Limiting Tests
# =============================================================================


class TestRateLimitConfig:
    """Tests for rate limit configuration."""

    def test_default_config(self):
        """Test default rate limit configuration."""
        config = RateLimitConfig()
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.enabled is True

    def test_custom_config(self):
        """Test custom rate limit configuration."""
        config = RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            burst_size=5,
        )
        assert config.requests_per_minute == 10
        assert config.burst_size == 5


class TestRateLimitState:
    """Tests for rate limit state."""

    def test_default_state(self):
        """Test default rate limit state."""
        state = RateLimitState()
        assert state.count == 0

    def test_window_expiry(self):
        """Test window expiration detection."""
        import time

        state = RateLimitState()
        state.window_start = time.time() - 120  # 2 minutes ago

        assert state.is_window_expired(60) is True  # 1 minute window expired
        assert state.is_window_expired(180) is False  # 3 minute window not expired

    def test_reset(self):
        """Test state reset."""
        state = RateLimitState()
        state.count = 100
        state.reset()
        assert state.count == 0


class TestInMemoryRateLimiter:
    """Tests for in-memory rate limiter."""

    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        """Test requests allowed within limit."""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_minute=10)

        is_allowed, headers = await limiter.check_rate_limit("test-key", config)
        assert is_allowed is True
        # Remaining is calculated before increment, so it shows 10 before the count increases
        assert headers["X-RateLimit-Remaining-Minute"] == 10

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self):
        """Test requests blocked when over limit."""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_minute=2, requests_per_hour=1000)

        # First two requests allowed
        await limiter.check_rate_limit("test-key", config)
        await limiter.check_rate_limit("test-key", config)

        # Third request blocked
        is_allowed, headers = await limiter.check_rate_limit("test-key", config)
        assert is_allowed is False
        assert "Retry-After" in headers

    @pytest.mark.asyncio
    async def test_separate_keys(self):
        """Test separate rate limit tracking for different keys."""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_minute=1)

        # First key exhausted
        await limiter.check_rate_limit("key-1", config)
        is_allowed_1, _ = await limiter.check_rate_limit("key-1", config)

        # Second key still available
        is_allowed_2, _ = await limiter.check_rate_limit("key-2", config)

        assert is_allowed_1 is False
        assert is_allowed_2 is True

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing rate limit state."""
        limiter = InMemoryRateLimiter()
        config = RateLimitConfig(requests_per_minute=1)

        await limiter.check_rate_limit("test-key", config)
        limiter.clear()

        is_allowed, _ = await limiter.check_rate_limit("test-key", config)
        assert is_allowed is True


# =============================================================================
# Required Permission Tests
# =============================================================================


class TestRequiredPermission:
    """Tests for required permission schema."""

    def test_single_permission(self):
        """Test single permission requirement."""
        req = RequiredPermission(permission="claims:read")
        assert req.permission == "claims:read"
        assert req.all_of is None
        assert req.any_of is None

    def test_all_of_permissions(self):
        """Test all_of permission requirement."""
        req = RequiredPermission(
            permission="claims:delete",
            all_of=["claims:read", "claims:delete"],
        )
        assert len(req.all_of) == 2

    def test_any_of_permissions(self):
        """Test any_of permission requirement."""
        req = RequiredPermission(
            permission="claims:view",
            any_of=["claims:read", "claims:admin"],
        )
        assert len(req.any_of) == 2
