"""
Database module for Claims Processing System.

Exports database connection utilities and tenant management.
"""

from src.db.connection import (
    check_db_connection,
    close_db_connection,
    get_engine,
    get_session,
    get_session_maker,
)
from src.db.tenant_manager import (
    TenantContext,
    TenantDatabaseManager,
    TenantSessionMiddleware,
    clear_current_tenant,
    execute_for_tenant,
    get_current_tenant,
    get_tenant_manager,
    get_tenant_session,
    require_tenant,
    set_current_tenant,
)

__all__ = [
    # Connection
    "get_engine",
    "get_session_maker",
    "get_session",
    "close_db_connection",
    "check_db_connection",
    # Tenant management
    "TenantContext",
    "TenantDatabaseManager",
    "TenantSessionMiddleware",
    "get_current_tenant",
    "set_current_tenant",
    "clear_current_tenant",
    "get_tenant_manager",
    "get_tenant_session",
    "execute_for_tenant",
    "require_tenant",
]
