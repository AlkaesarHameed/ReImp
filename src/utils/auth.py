"""
Authentication Utilities
JWT token generation and password hashing
Source: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
Verified: 2025-11-14
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from src.api.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash using bcrypt.

    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password (string format)

    Returns:
        True if password matches, False otherwise

    Evidence: Bcrypt is recommended for password hashing by OWASP
    Source: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
    Bcrypt implementation: https://pypi.org/project/bcrypt/
    Version: 5.0.0 (Latest - Nov 2025)
    Verified: 2025-11-14

    Note: Bcrypt handles passwords up to 72 bytes. Longer passwords are automatically
    truncated by bcrypt internally.
    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hashed password (string format)

    Evidence: Bcrypt with salt rounds 12 (default) provides good security/performance balance
    Source: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
    Bcrypt implementation: https://pypi.org/project/bcrypt/
    Version: 5.0.0 (Latest - Nov 2025)
    Verified: 2025-11-14

    Note: Bcrypt handles passwords up to 72 bytes. Longer passwords are automatically
    truncated by bcrypt internally.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Token payload data
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token

    Evidence: JWT for stateless authentication
    Source: https://jwt.io/introduction
    Verified: 2025-11-14

    Note: Uses timezone-aware datetime (Python 3.12+)
    Source: https://docs.python.org/3/library/datetime.html#datetime.datetime.now
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Token payload data

    Returns:
        Encoded JWT refresh token

    Evidence: Refresh tokens for better security
    Source: https://auth0.com/blog/refresh-tokens-what-are-they-and-when-to-use-them/
    Verified: 2025-11-14

    Note: Uses timezone-aware datetime (Python 3.12+)
    Source: https://docs.python.org/3/library/datetime.html#datetime.datetime.now
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict[Any, Any] | None:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token string

    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
