"""
Authentication Routes
JWT-based authentication endpoints
Source: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
Verified: 2025-11-14
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import get_session
from src.models.user import User
from src.schemas.auth import LoginRequest, RefreshTokenRequest, Token
from src.schemas.user import UserCreate, UserResponse
from src.utils.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from src.utils.errors import AuthenticationError, ConflictError
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Register a new user.

    Evidence: User registration best practices
    Source: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
    Verified: 2025-11-14
    """
    # Check if email already exists
    result = await session.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise ConflictError("Email already registered")

    # Check if username already exists
    result = await session.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise ConflictError("Username already taken")

    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
        is_verified=False,
        is_superuser=False,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    logger.info(f"New user registered: {user.username} ({user.email})")

    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> Token:
    """
    Login with email and password.

    Evidence: OAuth2 password flow
    Source: https://datatracker.ietf.org/doc/html/rfc6749#section-4.3
    Verified: 2025-11-14
    """
    # Find user by email (username field actually contains email)
    result = await session.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    # Verify credentials
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise AuthenticationError("Incorrect email or password")

    if not user.is_active:
        raise AuthenticationError("Account is inactive")

    # Update last login
    user.last_login = datetime.now(UTC)
    await session.commit()

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    logger.info(f"User logged in: {user.username}")

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",  # nosec B106
    )


@router.post("/login/json", response_model=Token)
async def login_json(
    login_data: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> Token:
    """
    Login with JSON body (alternative to form data).

    Evidence: REST API best practices
    Source: https://restfulapi.net/http-methods/
    Verified: 2025-11-14
    """
    # Find user by email
    result = await session.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()

    # Verify credentials
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise AuthenticationError("Incorrect email or password")

    if not user.is_active:
        raise AuthenticationError("Account is inactive")

    # Update last login
    user.last_login = datetime.now(UTC)
    await session.commit()

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    logger.info(f"User logged in: {user.username}")

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",  # nosec B106
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
) -> Token:
    """
    Refresh access token using refresh token.

    Evidence: Token rotation for better security
    Source: https://auth0.com/blog/refresh-tokens-what-are-they-and-when-to-use-them/
    Verified: 2025-11-14
    """
    # Decode refresh token
    payload = decode_token(refresh_data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise AuthenticationError("Invalid refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload")

    # Verify user exists and is active
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    # Create new tokens
    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    logger.info(f"Tokens refreshed for user: {user.username}")

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",  # nosec B106
    )
