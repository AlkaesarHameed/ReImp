"""
Permission and Role Models for RBAC.

Implements role-based access control with:
- Granular permissions (resource:action format)
- Hierarchical roles with permission inheritance
- Tenant-scoped role assignments
- Audit trail for permission changes
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDModel, TimeStampedModel
from src.core.enums import Permission as PermissionEnum, Role as RoleEnum

if TYPE_CHECKING:
    from src.models.tenant import Tenant
    from src.models.user import User


class Permission(Base, UUIDModel, TimeStampedModel):
    """
    Individual permission definition.

    Permissions follow the format: resource:action
    Examples: claims:read, claims:create, documents:upload
    """

    __tablename__ = "permissions"

    # Permission identity
    code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Permission categorization
    resource: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g., claims, documents, users
    action: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., read, create, update, delete

    # System permission flag (cannot be deleted)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
    )

    def __repr__(self) -> str:
        return f"<Permission {self.code}>"

    @classmethod
    def from_enum(cls, perm: PermissionEnum) -> "Permission":
        """Create permission from enum."""
        parts = perm.value.split(":")
        return cls(
            code=perm.value,
            name=perm.value.replace(":", " ").title(),
            resource=parts[0] if len(parts) > 0 else "unknown",
            action=parts[1] if len(parts) > 1 else "unknown",
            is_system=True,
        )


class Role(Base, UUIDModel, TimeStampedModel):
    """
    Role definition with associated permissions.

    Supports:
    - System roles (cannot be modified)
    - Tenant-specific custom roles
    - Permission inheritance through role hierarchy
    """

    __tablename__ = "roles"

    # Role identity
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Tenant scope (NULL = global/system role)
    tenant_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Role hierarchy
    parent_role_id: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Role level for hierarchy (higher = more permissions)
    level: Mapped[int] = mapped_column(Integer, default=0)

    # System role flag
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    tenant: Mapped[Optional["Tenant"]] = relationship(
        "Tenant", back_populates="custom_roles"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
    )
    parent_role: Mapped[Optional["Role"]] = relationship(
        "Role", remote_side="Role.id", back_populates="child_roles"
    )
    child_roles: Mapped[list["Role"]] = relationship(
        "Role", back_populates="parent_role"
    )
    user_assignments: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role"
    )

    __table_args__ = (
        UniqueConstraint("code", "tenant_id", name="uq_role_code_tenant"),
        Index("ix_role_tenant_code", "tenant_id", "code"),
    )

    def __repr__(self) -> str:
        return f"<Role {self.code} (tenant={self.tenant_id})>"

    @property
    def all_permissions(self) -> set[str]:
        """Get all permissions including inherited from parent roles."""
        perms = {p.code for p in self.permissions}
        if self.parent_role:
            perms.update(self.parent_role.all_permissions)
        return perms

    def has_permission(self, permission_code: str) -> bool:
        """Check if role has a specific permission."""
        return permission_code in self.all_permissions

    @classmethod
    def from_enum(cls, role: RoleEnum) -> "Role":
        """Create role from enum."""
        return cls(
            code=role.value,
            name=role.value.replace("_", " ").title(),
            is_system=True,
        )


class RolePermission(Base):
    """Association table for role-permission many-to-many relationship."""

    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    granted_by: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class UserRole(Base, UUIDModel, TimeStampedModel):
    """
    User-Role assignment with tenant scope.

    Supports:
    - Multiple roles per user
    - Tenant-specific role assignments
    - Time-limited role assignments
    """

    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Assignment metadata
    assigned_by: Mapped[Optional[str]] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Time-limited assignments
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    role: Mapped["Role"] = relationship("Role", back_populates="user_assignments")
    tenant: Mapped["Tenant"] = relationship("Tenant")
    assigner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_by])

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "tenant_id", name="uq_user_role_tenant"),
        Index("ix_user_role_tenant", "user_id", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<UserRole user={self.user_id} role={self.role_id} tenant={self.tenant_id}>"

    @property
    def is_expired(self) -> bool:
        """Check if role assignment has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if role assignment is currently valid."""
        return self.is_active and not self.is_expired


# Default system permissions to create on startup
SYSTEM_PERMISSIONS = [
    # Claims permissions
    ("claims:read", "Read Claims", "claims", "read"),
    ("claims:create", "Create Claims", "claims", "create"),
    ("claims:update", "Update Claims", "claims", "update"),
    ("claims:delete", "Delete Claims", "claims", "delete"),
    ("claims:submit", "Submit Claims", "claims", "submit"),
    ("claims:approve", "Approve Claims", "claims", "approve"),
    ("claims:deny", "Deny Claims", "claims", "deny"),
    ("claims:adjudicate", "Adjudicate Claims", "claims", "adjudicate"),
    # Document permissions
    ("documents:read", "Read Documents", "documents", "read"),
    ("documents:upload", "Upload Documents", "documents", "upload"),
    ("documents:delete", "Delete Documents", "documents", "delete"),
    # Policy permissions
    ("policies:read", "Read Policies", "policies", "read"),
    ("policies:create", "Create Policies", "policies", "create"),
    ("policies:update", "Update Policies", "policies", "update"),
    # Member permissions
    ("members:read", "Read Members", "members", "read"),
    ("members:create", "Create Members", "members", "create"),
    ("members:update", "Update Members", "members", "update"),
    # Provider permissions
    ("providers:read", "Read Providers", "providers", "read"),
    ("providers:create", "Create Providers", "providers", "create"),
    ("providers:update", "Update Providers", "providers", "update"),
    # Admin permissions
    ("admin:users", "Manage Users", "admin", "users"),
    ("admin:tenants", "Manage Tenants", "admin", "tenants"),
    ("admin:roles", "Manage Roles", "admin", "roles"),
    ("admin:settings", "Manage Settings", "admin", "settings"),
    # Reports permissions
    ("reports:read", "Read Reports", "reports", "read"),
    ("reports:export", "Export Reports", "reports", "export"),
    # Audit permissions
    ("audit:read", "Read Audit Logs", "audit", "read"),
]

# Default system roles with their permissions
SYSTEM_ROLES = {
    "super_admin": {
        "name": "Super Administrator",
        "level": 100,
        "permissions": ["*"],  # All permissions
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
