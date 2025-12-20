"""
FastAPI Dependencies
Dependency injection for authentication and database sessions
Source: https://fastapi.tiangolo.com/tutorial/dependencies/
Verified: 2025-11-14
"""

from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import get_session
from src.models.user import User
from src.utils.auth import decode_token
from src.utils.errors import AuthenticationError

# HTTP Bearer token security scheme
# Evidence: Bearer token authentication for REST APIs
# Source: https://swagger.io/docs/specification/authentication/bearer-authentication/
# Verified: 2025-11-14
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials
        session: Database session

    Returns:
        User object

    Raises:
        AuthenticationError: If token is invalid or user not found

    Evidence: Dependency injection pattern for authentication
    Source: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#get-the-current-user
    Verified: 2025-11-14
    """
    token = credentials.credentials

    # Decode token
    payload = decode_token(token)
    if payload is None:
        raise AuthenticationError("Invalid token")

    # Check token type
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")

    # Get user ID from token
    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        raise AuthenticationError("Invalid token payload")

    try:
        user_id = UUID(user_id_str)
    except ValueError as err:
        raise AuthenticationError("Invalid user ID in token") from err

    # Get user from database
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("User not found")

    if not user.is_active:
        raise AuthenticationError("User account is inactive")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user.

    Args:
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        AuthenticationError: If user is not active
    """
    if not current_user.is_active:
        raise AuthenticationError("User account is inactive")
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current superuser.

    Args:
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        AuthenticationError: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise AuthenticationError("Superuser access required")
    return current_user


async def get_optional_current_user(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """
    Get current user if token is provided, otherwise return None.

    Useful for optional authentication on public endpoints.

    Args:
        authorization: Authorization header
        session: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)

    if payload is None:
        return None

    user_id_str = payload.get("sub")
    if not user_id_str:
        return None

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        return None

    result = await session.execute(select(User).where(User.id == user_id, User.is_active))
    return result.scalar_one_or_none()


# Alias for backward compatibility
async def get_db() -> AsyncSession:
    """
    Get database session dependency.
    Alias for get_session for backward compatibility.
    """
    async for session in get_session():
        yield session


async def get_tenant_id(
    current_user: User = Depends(get_current_user),
) -> UUID | None:
    """
    Get current tenant ID from user.

    Args:
        current_user: Current authenticated user

    Returns:
        Tenant ID if available, None otherwise
    """
    # For now, return a default tenant ID or None
    # In a full multi-tenant setup, this would come from the user's tenant
    return getattr(current_user, 'tenant_id', None)
