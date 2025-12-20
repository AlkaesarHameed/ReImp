"""
Pydantic Schemas for Permission and Role Management.

Provides request/response models for RBAC operations.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# Permission Schemas
# =============================================================================


class PermissionBase(BaseModel):
    """Base permission schema."""

    code: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-z_]+:[a-z_]+$")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)


class PermissionCreate(PermissionBase):
    """Schema for creating a new permission."""

    is_system: bool = False


class PermissionUpdate(BaseModel):
    """Schema for updating a permission."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PermissionResponse(PermissionBase):
    """Schema for permission response."""

    id: str
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PermissionListResponse(BaseModel):
    """Schema for paginated permission list."""

    items: list[PermissionResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Role Schemas
# =============================================================================


class RoleBase(BaseModel):
    """Base role schema."""

    code: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z_]+$")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    level: int = Field(default=0, ge=0, le=100)


class RoleCreate(RoleBase):
    """Schema for creating a new role."""

    tenant_id: Optional[str] = None  # NULL for system roles
    parent_role_id: Optional[str] = None
    permission_ids: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Schema for updating a role."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    level: Optional[int] = Field(None, ge=0, le=100)
    parent_role_id: Optional[str] = None
    is_active: Optional[bool] = None


class RolePermissionsUpdate(BaseModel):
    """Schema for updating role permissions."""

    add_permission_ids: list[str] = Field(default_factory=list)
    remove_permission_ids: list[str] = Field(default_factory=list)


class RoleResponse(RoleBase):
    """Schema for role response."""

    id: str
    tenant_id: Optional[str]
    parent_role_id: Optional[str]
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    permissions: list[PermissionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RoleListResponse(BaseModel):
    """Schema for paginated role list."""

    items: list[RoleResponse]
    total: int
    page: int
    page_size: int


class RoleSummary(BaseModel):
    """Minimal role summary for user context."""

    id: str
    code: str
    name: str
    level: int

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# User Role Assignment Schemas
# =============================================================================


class UserRoleAssign(BaseModel):
    """Schema for assigning a role to a user."""

    user_id: str
    role_id: str
    tenant_id: str
    expires_at: Optional[datetime] = None


class UserRoleResponse(BaseModel):
    """Schema for user role assignment response."""

    id: str
    user_id: str
    role_id: str
    tenant_id: str
    assigned_by: Optional[str]
    assigned_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    is_expired: bool
    is_valid: bool
    role: RoleSummary

    model_config = ConfigDict(from_attributes=True)


class UserRolesResponse(BaseModel):
    """Schema for user's roles in a tenant."""

    user_id: str
    tenant_id: str
    roles: list[UserRoleResponse]
    effective_permissions: list[str]


class UserPermissionsCheck(BaseModel):
    """Schema for checking user permissions."""

    user_id: str
    tenant_id: str
    permissions: list[str]


class UserPermissionsCheckResult(BaseModel):
    """Schema for permission check result."""

    user_id: str
    tenant_id: str
    results: dict[str, bool]  # permission_code -> has_permission
    all_granted: bool


# =============================================================================
# JWT Token Claims
# =============================================================================


class TokenClaims(BaseModel):
    """JWT token claims with tenant and RBAC info."""

    sub: str  # User ID
    tenant_id: str
    tenant_slug: str
    roles: list[str]  # Role codes
    permissions: list[str]  # Permission codes
    provider_preferences: dict[str, str] = Field(default_factory=dict)
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp


class TokenClaimsCreate(BaseModel):
    """Schema for creating token claims."""

    user_id: str
    tenant_id: str
    tenant_slug: str
    roles: list[str]
    permissions: list[str]
    provider_preferences: Optional[dict[str, str]] = None
    expires_in_minutes: int = Field(default=60, ge=1, le=1440)


# =============================================================================
# Permission Check Decorators Support
# =============================================================================


class RequiredPermission(BaseModel):
    """Schema for required permission specification."""

    permission: str
    all_of: Optional[list[str]] = None  # All permissions required
    any_of: Optional[list[str]] = None  # Any one permission sufficient
    resource: Optional[str] = None  # Resource-specific permission check
    resource_id: Optional[str] = None  # Specific resource ID


class PermissionDenied(BaseModel):
    """Schema for permission denied response."""

    detail: str = "Permission denied"
    required_permissions: list[str]
    user_permissions: list[str]
    resource: Optional[str] = None
    action: Optional[str] = None
