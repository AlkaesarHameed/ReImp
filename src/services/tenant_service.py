"""
Tenant Service for Multi-Tenant Management.

Provides:
- Tenant onboarding and provisioning
- Tenant configuration management
- Tenant-specific database setup
- Role and permission management per tenant
"""

import logging
import secrets
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import get_claims_settings
from src.core.enums import TenantStatus
from src.models.tenant import Tenant, TenantSettings
from src.models.permission import (
    Permission,
    Role,
    RolePermission,
    UserRole,
    SYSTEM_PERMISSIONS,
    SYSTEM_ROLES,
)
from src.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantStatusUpdate,
    TenantSettingsUpdate,
)
from src.schemas.permission import (
    RoleCreate,
    RoleResponse,
    UserRoleAssign,
    UserRolesResponse,
)

logger = logging.getLogger(__name__)


class TenantServiceError(Exception):
    """Base exception for tenant service errors."""

    pass


class TenantNotFoundError(TenantServiceError):
    """Raised when tenant is not found."""

    pass


class TenantExistsError(TenantServiceError):
    """Raised when tenant already exists."""

    pass


class TenantService:
    """
    Service for tenant management operations.

    Handles:
    - Tenant CRUD operations
    - Tenant provisioning and setup
    - Default role/permission seeding
    - Tenant configuration management
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_claims_settings()

    # =========================================================================
    # Tenant CRUD Operations
    # =========================================================================

    async def create_tenant(
        self,
        tenant_data: TenantCreate,
        created_by: Optional[str] = None,
    ) -> Tenant:
        """
        Create a new tenant with full provisioning.

        Steps:
        1. Validate tenant doesn't exist
        2. Create tenant record
        3. Create tenant settings
        4. Seed default roles and permissions
        5. Create tenant database schema (if separate DBs)
        """
        # Check if tenant slug already exists
        existing = await self.get_tenant_by_slug(tenant_data.slug)
        if existing:
            raise TenantExistsError(f"Tenant with slug '{tenant_data.slug}' already exists")

        # Create tenant
        tenant = Tenant(
            id=str(uuid4()),
            name=tenant_data.name,
            slug=tenant_data.slug,
            status=TenantStatus.PENDING,
            domain=tenant_data.domain,
            contact_email=tenant_data.contact_email,
            contact_phone=tenant_data.contact_phone,
            address=tenant_data.address,
            provider_config=tenant_data.provider_config,
            feature_flags=tenant_data.feature_flags or {},
            metadata={"created_by": created_by} if created_by else {},
        )

        self.session.add(tenant)
        await self.session.flush()

        # Create default tenant settings
        settings = TenantSettings(
            id=str(uuid4()),
            tenant_id=tenant.id,
            timezone=tenant_data.timezone or "UTC",
            date_format="%Y-%m-%d",
            currency="USD",
            language="en",
        )
        self.session.add(settings)

        # Seed default roles for this tenant
        await self._seed_tenant_roles(tenant.id)

        # Activate tenant
        tenant.status = TenantStatus.ACTIVE

        await self.session.commit()
        await self.session.refresh(tenant)

        logger.info(f"Created tenant: {tenant.slug} (ID: {tenant.id})")
        return tenant

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        result = await self.session.execute(
            select(Tenant)
            .where(Tenant.id == tenant_id)
            .options(selectinload(Tenant.settings))
        )
        return result.scalar_one_or_none()

    async def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug."""
        result = await self.session.execute(
            select(Tenant)
            .where(Tenant.slug == slug)
            .options(selectinload(Tenant.settings))
        )
        return result.scalar_one_or_none()

    async def list_tenants(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[TenantStatus] = None,
    ) -> tuple[list[Tenant], int]:
        """List tenants with pagination."""
        query = select(Tenant)

        if status:
            query = query.where(Tenant.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar_one()

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(Tenant.created_at.desc())
        result = await self.session.execute(query)

        return list(result.scalars().all()), total

    async def update_tenant(
        self,
        tenant_id: str,
        tenant_data: TenantUpdate,
    ) -> Tenant:
        """Update tenant details."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant not found: {tenant_id}")

        update_data = tenant_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)

        tenant.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(tenant)

        return tenant

    async def update_tenant_status(
        self,
        tenant_id: str,
        status_update: TenantStatusUpdate,
    ) -> Tenant:
        """Update tenant status."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant not found: {tenant_id}")

        tenant.status = status_update.status
        tenant.updated_at = datetime.now(timezone.utc)

        if status_update.status == TenantStatus.SUSPENDED:
            tenant.metadata["suspended_at"] = datetime.now(timezone.utc).isoformat()
            tenant.metadata["suspension_reason"] = status_update.reason

        await self.session.commit()
        await self.session.refresh(tenant)

        logger.info(f"Updated tenant {tenant_id} status to {status_update.status}")
        return tenant

    async def delete_tenant(self, tenant_id: str, soft_delete: bool = True) -> bool:
        """Delete or deactivate a tenant."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant not found: {tenant_id}")

        if soft_delete:
            tenant.status = TenantStatus.CANCELLED
            tenant.deleted_at = datetime.now(timezone.utc)
            await self.session.commit()
        else:
            await self.session.delete(tenant)
            await self.session.commit()

        logger.info(f"Deleted tenant {tenant_id} (soft={soft_delete})")
        return True

    # =========================================================================
    # Tenant Settings
    # =========================================================================

    async def get_tenant_settings(self, tenant_id: str) -> Optional[TenantSettings]:
        """Get tenant settings."""
        result = await self.session.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update_tenant_settings(
        self,
        tenant_id: str,
        settings_data: TenantSettingsUpdate,
    ) -> TenantSettings:
        """Update tenant settings."""
        settings = await self.get_tenant_settings(tenant_id)
        if not settings:
            raise TenantNotFoundError(f"Tenant settings not found: {tenant_id}")

        update_data = settings_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)

        settings.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(settings)

        return settings

    # =========================================================================
    # Role Management
    # =========================================================================

    async def _seed_tenant_roles(self, tenant_id: str) -> None:
        """Seed default roles for a new tenant."""
        # Get all system permissions
        perm_result = await self.session.execute(
            select(Permission).where(Permission.is_system == True)
        )
        permissions = {p.code: p for p in perm_result.scalars().all()}

        # If no permissions exist, create them first
        if not permissions:
            await self._seed_system_permissions()
            perm_result = await self.session.execute(
                select(Permission).where(Permission.is_system == True)
            )
            permissions = {p.code: p for p in perm_result.scalars().all()}

        # Create roles for this tenant based on system role templates
        for role_code, role_config in SYSTEM_ROLES.items():
            role = Role(
                id=str(uuid4()),
                code=role_code,
                name=role_config["name"],
                tenant_id=tenant_id,
                level=role_config["level"],
                is_system=True,
            )
            self.session.add(role)
            await self.session.flush()

            # Assign permissions
            role_perms = role_config.get("permissions", [])
            for perm_pattern in role_perms:
                if perm_pattern == "*":
                    # All permissions
                    for perm in permissions.values():
                        await self._add_role_permission(role.id, perm.id)
                elif perm_pattern.endswith(":*"):
                    # Resource wildcard (e.g., "claims:*")
                    resource = perm_pattern.split(":")[0]
                    for perm_code, perm in permissions.items():
                        if perm_code.startswith(f"{resource}:"):
                            await self._add_role_permission(role.id, perm.id)
                elif perm_pattern in permissions:
                    await self._add_role_permission(role.id, permissions[perm_pattern].id)

        logger.debug(f"Seeded roles for tenant {tenant_id}")

    async def _seed_system_permissions(self) -> None:
        """Seed system permissions if they don't exist."""
        for code, name, resource, action in SYSTEM_PERMISSIONS:
            existing = await self.session.execute(
                select(Permission).where(Permission.code == code)
            )
            if not existing.scalar_one_or_none():
                perm = Permission(
                    id=str(uuid4()),
                    code=code,
                    name=name,
                    resource=resource,
                    action=action,
                    is_system=True,
                )
                self.session.add(perm)

        await self.session.flush()
        logger.info("Seeded system permissions")

    async def _add_role_permission(self, role_id: str, permission_id: str) -> None:
        """Add permission to role."""
        role_perm = RolePermission(
            role_id=role_id,
            permission_id=permission_id,
            granted_at=datetime.now(timezone.utc),
        )
        self.session.add(role_perm)

    async def get_tenant_roles(self, tenant_id: str) -> list[Role]:
        """Get all roles for a tenant."""
        result = await self.session.execute(
            select(Role)
            .where(Role.tenant_id == tenant_id)
            .options(selectinload(Role.permissions))
            .order_by(Role.level.desc())
        )
        return list(result.scalars().all())

    async def create_custom_role(
        self,
        tenant_id: str,
        role_data: RoleCreate,
        created_by: Optional[str] = None,
    ) -> Role:
        """Create a custom role for a tenant."""
        # Verify tenant exists
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant not found: {tenant_id}")

        # Check if role code already exists for this tenant
        existing = await self.session.execute(
            select(Role).where(
                Role.tenant_id == tenant_id,
                Role.code == role_data.code,
            )
        )
        if existing.scalar_one_or_none():
            raise TenantServiceError(
                f"Role '{role_data.code}' already exists for tenant"
            )

        role = Role(
            id=str(uuid4()),
            code=role_data.code,
            name=role_data.name,
            description=role_data.description,
            tenant_id=tenant_id,
            parent_role_id=role_data.parent_role_id,
            level=role_data.level,
            is_system=False,
        )
        self.session.add(role)
        await self.session.flush()

        # Add permissions
        for perm_id in role_data.permission_ids:
            await self._add_role_permission(role.id, perm_id)

        await self.session.commit()
        await self.session.refresh(role)

        return role

    # =========================================================================
    # User Role Management
    # =========================================================================

    async def assign_user_role(
        self,
        assignment: UserRoleAssign,
        assigned_by: Optional[str] = None,
    ) -> UserRole:
        """Assign a role to a user for a specific tenant."""
        # Verify role exists and belongs to tenant
        role_result = await self.session.execute(
            select(Role).where(
                Role.id == assignment.role_id,
                Role.tenant_id == assignment.tenant_id,
            )
        )
        role = role_result.scalar_one_or_none()
        if not role:
            raise TenantServiceError("Role not found for this tenant")

        # Check if assignment already exists
        existing = await self.session.execute(
            select(UserRole).where(
                UserRole.user_id == assignment.user_id,
                UserRole.role_id == assignment.role_id,
                UserRole.tenant_id == assignment.tenant_id,
            )
        )
        if existing.scalar_one_or_none():
            raise TenantServiceError("User already has this role for this tenant")

        user_role = UserRole(
            id=str(uuid4()),
            user_id=assignment.user_id,
            role_id=assignment.role_id,
            tenant_id=assignment.tenant_id,
            assigned_by=assigned_by,
            assigned_at=datetime.now(timezone.utc),
            expires_at=assignment.expires_at,
        )
        self.session.add(user_role)
        await self.session.commit()
        await self.session.refresh(user_role)

        return user_role

    async def revoke_user_role(
        self,
        user_id: str,
        role_id: str,
        tenant_id: str,
    ) -> bool:
        """Revoke a role from a user."""
        result = await self.session.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
                UserRole.tenant_id == tenant_id,
            )
        )
        user_role = result.scalar_one_or_none()
        if not user_role:
            return False

        user_role.is_active = False
        await self.session.commit()
        return True

    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: str,
    ) -> UserRolesResponse:
        """Get all roles and effective permissions for a user in a tenant."""
        result = await self.session.execute(
            select(UserRole)
            .where(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id,
                UserRole.is_active == True,
            )
            .options(
                selectinload(UserRole.role).selectinload(Role.permissions)
            )
        )
        user_roles = list(result.scalars().all())

        # Collect effective permissions
        effective_permissions: set[str] = set()
        for ur in user_roles:
            if ur.is_valid:
                effective_permissions.update(ur.role.all_permissions)

        return UserRolesResponse(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=user_roles,
            effective_permissions=sorted(effective_permissions),
        )

    async def check_user_permission(
        self,
        user_id: str,
        tenant_id: str,
        permission: str,
    ) -> bool:
        """Check if a user has a specific permission in a tenant."""
        user_roles = await self.get_user_roles(user_id, tenant_id)
        return permission in user_roles.effective_permissions


# Factory function for dependency injection
async def get_tenant_service(session: AsyncSession) -> TenantService:
    """Get tenant service instance."""
    return TenantService(session)
