"""
Tenant Context Middleware for Multi-Tenant Isolation.

Provides:
- Tenant identification from JWT token
- Tenant context injection for requests
- Permission checking decorators
- Tenant isolation enforcement
"""

import logging
from contextvars import ContextVar
from functools import wraps
from typing import Callable, Optional, Any

from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import jwt

from src.api.config import get_settings
from src.schemas.permission import TokenClaims, PermissionDenied

logger = logging.getLogger(__name__)

# Context variables for tenant isolation
_current_tenant_id: ContextVar[Optional[str]] = ContextVar("current_tenant_id", default=None)
_current_user_id: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)
_current_permissions: ContextVar[list[str]] = ContextVar("current_permissions", default=[])
_current_roles: ContextVar[list[str]] = ContextVar("current_roles", default=[])

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


def get_current_tenant_id() -> Optional[str]:
    """Get current tenant ID from context."""
    return _current_tenant_id.get()


def get_current_user_id() -> Optional[str]:
    """Get current user ID from context."""
    return _current_user_id.get()


def get_current_user_permissions() -> list[str]:
    """Get current user's permissions from context."""
    return _current_permissions.get()


def get_current_user_roles() -> list[str]:
    """Get current user's roles from context."""
    return _current_roles.get()


def set_tenant_context(
    tenant_id: Optional[str],
    user_id: Optional[str] = None,
    permissions: Optional[list[str]] = None,
    roles: Optional[list[str]] = None,
) -> None:
    """Set tenant context for current request."""
    _current_tenant_id.set(tenant_id)
    _current_user_id.set(user_id)
    _current_permissions.set(permissions or [])
    _current_roles.set(roles or [])


def clear_tenant_context() -> None:
    """Clear tenant context after request."""
    _current_tenant_id.set(None)
    _current_user_id.set(None)
    _current_permissions.set([])
    _current_roles.set([])


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and set tenant context from JWT token.

    Extracts tenant_id, user_id, roles, and permissions from the JWT
    and makes them available via context variables.
    """

    def __init__(self, app, exclude_paths: Optional[list[str]] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
        ]
        # URL patterns that don't require authentication (matched with 'in' check)
        # These endpoints are accessed via browser img src which doesn't send auth headers
        self.exclude_patterns = [
            "/page/",  # Page images: /api/v1/documents/{id}/page/{num}/image
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and set tenant context."""
        # Skip excluded paths (exact prefix match)
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Skip excluded patterns (contains match for browser-loaded resources)
        if any(pattern in request.url.path for pattern in self.exclude_patterns):
            return await call_next(request)

        settings = get_settings()

        # Development mode: Accept X-Dev-User header for mock authentication
        # Use valid UUIDs for dev tenant/user to match database UUID columns
        DEV_TENANT_UUID = "00000000-0000-0000-0000-000000000001"
        DEV_USER_UUID = "00000000-0000-0000-0000-000000000002"
        if settings.ENVIRONMENT == "development":
            dev_user = request.headers.get("X-Dev-User")
            if dev_user:
                logger.debug(f"Development mode: Setting tenant context for dev user '{dev_user}'")
                set_tenant_context(
                    tenant_id=DEV_TENANT_UUID,
                    user_id=DEV_USER_UUID,
                    permissions=[
                        "claims:read", "claims:write", "claims:create", "claims:update", "claims:approve",
                        "documents:read", "documents:write", "documents:upload", "documents:delete",
                        "admin:users", "admin:settings", "admin:access",
                        "reports:view", "reports:export",
                        "eligibility:check", "eligibility:batch",
                    ],
                    roles=["administrator"],
                )
                # Store mock claims in request state
                request.state.token_claims = TokenClaims(
                    sub=DEV_USER_UUID,
                    tenant_id=DEV_TENANT_UUID,
                    tenant_slug="development",
                    roles=["administrator"],
                    permissions=[
                        "claims:read", "claims:write", "claims:create", "claims:update", "claims:approve",
                        "documents:read", "documents:write", "documents:upload", "documents:delete",
                        "admin:users", "admin:settings", "admin:access",
                        "reports:view", "reports:export",
                        "eligibility:check", "eligibility:batch",
                    ],
                    provider_preferences={},
                    exp=9999999999,
                    iat=0,
                )
                try:
                    response = await call_next(request)
                    return response
                finally:
                    clear_tenant_context()

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                claims = self._decode_token(token)
                set_tenant_context(
                    tenant_id=claims.tenant_id,
                    user_id=claims.sub,
                    permissions=claims.permissions,
                    roles=claims.roles,
                )
                # Store claims in request state for route handlers
                request.state.token_claims = claims
            except jwt.ExpiredSignatureError:
                logger.warning("Expired JWT token")
                clear_tenant_context()
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid JWT token: {e}")
                clear_tenant_context()
        else:
            clear_tenant_context()

        try:
            response = await call_next(request)
            return response
        finally:
            clear_tenant_context()

    def _decode_token(self, token: str) -> TokenClaims:
        """Decode and validate JWT token."""
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return TokenClaims(
            sub=payload.get("sub"),
            tenant_id=payload.get("tenant_id"),
            tenant_slug=payload.get("tenant_slug", ""),
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
            provider_preferences=payload.get("provider_preferences", {}),
            exp=payload.get("exp", 0),
            iat=payload.get("iat", 0),
        )


# =============================================================================
# Permission Dependency Functions
# =============================================================================


async def get_token_claims(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenClaims:
    """
    Dependency to get and validate token claims.

    Raises HTTPException if token is missing or invalid.

    In development mode, accepts X-Dev-User header for mock authentication.
    """
    settings = get_settings()

    # Development mode: Accept mock auth header
    # Use valid UUIDs for dev tenant/user to match database UUID columns
    DEV_TENANT_UUID = "00000000-0000-0000-0000-000000000001"
    DEV_USER_UUID = "00000000-0000-0000-0000-000000000002"
    if settings.ENVIRONMENT == "development":
        dev_user = request.headers.get("X-Dev-User")
        if dev_user:
            # Return mock claims with full permissions for development
            logger.debug(f"Development mode: Using mock auth for user '{dev_user}'")
            return TokenClaims(
                sub=DEV_USER_UUID,
                tenant_id=DEV_TENANT_UUID,
                tenant_slug="development",
                roles=["administrator"],
                permissions=[
                    "claims:read", "claims:write", "claims:create", "claims:update", "claims:approve",
                    "documents:read", "documents:write", "documents:upload", "documents:delete",
                    "admin:users", "admin:settings", "admin:access",
                    "reports:view", "reports:export",
                    "eligibility:check", "eligibility:batch",
                ],
                provider_preferences={},
                exp=9999999999,  # Far future expiry for dev
                iat=0,
            )

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return TokenClaims(
            sub=payload.get("sub"),
            tenant_id=payload.get("tenant_id"),
            tenant_slug=payload.get("tenant_slug", ""),
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
            provider_preferences=payload.get("provider_preferences", {}),
            exp=payload.get("exp", 0),
            iat=payload.get("iat", 0),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permission(permission: str) -> Callable:
    """
    Dependency factory to require a specific permission.

    Usage:
        @router.get("/claims", dependencies=[Depends(require_permission("claims:read"))])
        async def list_claims():
            ...
    """

    async def permission_checker(
        claims: TokenClaims = Depends(get_token_claims),
    ) -> TokenClaims:
        if permission not in claims.permissions:
            raise HTTPException(
                status_code=403,
                detail=PermissionDenied(
                    detail=f"Permission denied: {permission} required",
                    required_permissions=[permission],
                    user_permissions=claims.permissions,
                ).model_dump(),
            )
        return claims

    return permission_checker


def require_any_permission(*permissions: str) -> Callable:
    """
    Dependency factory to require any one of the specified permissions.

    Usage:
        @router.get("/claims", dependencies=[Depends(require_any_permission("claims:read", "claims:admin"))])
        async def list_claims():
            ...
    """

    async def permission_checker(
        claims: TokenClaims = Depends(get_token_claims),
    ) -> TokenClaims:
        if not any(p in claims.permissions for p in permissions):
            raise HTTPException(
                status_code=403,
                detail=PermissionDenied(
                    detail=f"Permission denied: one of {permissions} required",
                    required_permissions=list(permissions),
                    user_permissions=claims.permissions,
                ).model_dump(),
            )
        return claims

    return permission_checker


def require_all_permissions(*permissions: str) -> Callable:
    """
    Dependency factory to require all specified permissions.

    Usage:
        @router.delete("/claims/{id}", dependencies=[Depends(require_all_permissions("claims:read", "claims:delete"))])
        async def delete_claim():
            ...
    """

    async def permission_checker(
        claims: TokenClaims = Depends(get_token_claims),
    ) -> TokenClaims:
        missing = [p for p in permissions if p not in claims.permissions]
        if missing:
            raise HTTPException(
                status_code=403,
                detail=PermissionDenied(
                    detail=f"Permission denied: missing {missing}",
                    required_permissions=list(permissions),
                    user_permissions=claims.permissions,
                ).model_dump(),
            )
        return claims

    return permission_checker


def require_role(role: str) -> Callable:
    """
    Dependency factory to require a specific role.

    Usage:
        @router.post("/tenants", dependencies=[Depends(require_role("super_admin"))])
        async def create_tenant():
            ...
    """

    async def role_checker(
        claims: TokenClaims = Depends(get_token_claims),
    ) -> TokenClaims:
        if role not in claims.roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role required: {role}",
            )
        return claims

    return role_checker


def require_tenant_admin() -> Callable:
    """Require tenant admin or super admin role."""
    return require_any_permission("admin:tenants", "admin:users")


def require_super_admin() -> Callable:
    """Require super admin role."""
    return require_role("super_admin")


# =============================================================================
# Permission Decorator (for non-dependency usage)
# =============================================================================


def check_permission(permission: str):
    """
    Decorator to check permission on route handler.

    Usage:
        @router.get("/claims")
        @check_permission("claims:read")
        async def list_claims(request: Request):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            permissions = get_current_user_permissions()
            if permission not in permissions:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission} required",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# Tenant Enforcement
# =============================================================================


async def enforce_tenant_isolation(
    resource_tenant_id: str,
    claims: TokenClaims = Depends(get_token_claims),
) -> None:
    """
    Enforce that the current user can only access resources in their tenant.

    Raises HTTPException if user tries to access another tenant's resources.
    """
    # Super admins can access all tenants
    if "super_admin" in claims.roles:
        return

    if claims.tenant_id != resource_tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: resource belongs to different tenant",
        )


def tenant_scoped(func: Callable) -> Callable:
    """
    Decorator to ensure function only operates on current tenant's data.

    Automatically adds tenant_id filter to queries.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise HTTPException(
                status_code=401,
                detail="Tenant context required",
            )
        # Inject tenant_id into kwargs if not present
        if "tenant_id" not in kwargs:
            kwargs["tenant_id"] = tenant_id
        return await func(*args, **kwargs)

    return wrapper
