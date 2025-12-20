"""
User Routes
User management endpoints
Source: https://fastapi.tiangolo.com/tutorial/sql-databases/
Verified: 2025-11-14
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_active_user, get_current_superuser
from src.db.connection import get_session
from src.models.user import User
from src.schemas.user import UserResponse, UserUpdate
from src.utils.errors import NotFoundError
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current user's profile.

    Evidence: Self-service user profile endpoint
    Source: https://restfulapi.net/resource-naming/
    Verified: 2025-11-14
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Update current user's profile.

    Evidence: PATCH for partial updates
    Source: https://datatracker.ietf.org/doc/html/rfc5789
    Verified: 2025-11-14
    """
    # Update only provided fields
    update_data = user_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    await session.commit()
    await session.refresh(current_user)

    logger.info(f"User profile updated: {current_user.username}")

    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: User = Depends(get_current_superuser),  # noqa: ARG001
) -> User:
    """
    Get user by ID.

    Evidence: Resource-based routing
    Source: https://restfulapi.net/resource-naming/
    Verified: 2025-11-14
    """
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundError("User not found")

    return user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete current user's account.

    Evidence: Self-service account deletion (GDPR right to be forgotten)
    Source: https://gdpr-info.eu/art-17-gdpr/
    Verified: 2025-11-14
    """
    await session.delete(current_user)
    await session.commit()

    logger.info(f"User account deleted: {current_user.username}")
