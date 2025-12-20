"""
API Middleware for Claims Processing System.

Provides:
- Tenant context injection
- Rate limiting per tenant
- Request logging
- Security headers
"""

from src.api.middleware.tenant import (
    TenantContextMiddleware,
    get_current_tenant_id,
    get_current_user_permissions,
    require_permission,
    require_any_permission,
    require_all_permissions,
)
from src.api.middleware.rate_limit import (
    RateLimitMiddleware,
    rate_limit,
)

__all__ = [
    # Tenant
    "TenantContextMiddleware",
    "get_current_tenant_id",
    "get_current_user_permissions",
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    # Rate Limit
    "RateLimitMiddleware",
    "rate_limit",
]
