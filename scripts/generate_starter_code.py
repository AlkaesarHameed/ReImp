#!/usr/bin/env python3
"""
Python Project Starter - Code Generator
Generates all application code files from templates
Evidence: Don't Repeat Yourself (DRY) principle
Source: https://en.wikipedia.org/wiki/Don%27t_repeat_yourself
Verified: 2025-11-14

Usage:
    python scripts/generate_starter_code.py
    python scripts/generate_starter_code.py --components auth,services,mcp
    python scripts/generate_starter_code.py --overwrite
"""

import argparse
from pathlib import Path

# ==========================================================================
# File Templates
# ==========================================================================

TEMPLATES = {
    # Base Model
    "src/models/base.py": '''"""
SQLAlchemy Base Model
Source: https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html
Verified: 2025-11-14
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Evidence: Declarative base for type-safe ORM
    Source: https://docs.sqlalchemy.org/en/20/orm/mapping_styles.html#orm-declarative-mapping
    """
    pass


class TimeStampedModel:
    """
    Mixin for models with created_at and updated_at timestamps.

    Evidence: Audit trail pattern
    Source: https://docs.sqlalchemy.org/en/20/orm/mapped_attributes.html#simple-validators
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDModel:
    """
    Mixin for models with UUID primary key.

    Evidence: UUIDs prevent enumeration attacks and simplify distributed systems
    Source: https://www.postgresql.org/docs/17/datatype-uuid.html
    """

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
''',
    # User Model
    "src/models/user.py": '''"""
User Model
SQLAlchemy model for user authentication and profile
Source: https://docs.sqlalchemy.org/en/20/orm/quickstart.html
Verified: 2025-11-14
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from src.models.base import Base, TimeStampedModel, UUIDModel


class User(Base, UUIDModel, TimeStampedModel):
    """
    User model with JWT authentication and OAuth2 support.

    Evidence: Follows security best practices
    - Passwords are hashed (never stored plain text)
    - Email validation enforced
    - Account status tracking (active, verified)
    Source: OWASP Authentication Cheat Sheet
    https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
    Verified: 2025-11-14
    """

    __tablename__ = "users"

    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    picture_url: Mapped[Optional[str]] = mapped_column(String)

    # Account Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # OAuth2 Fields
    oauth_provider: Mapped[Optional[str]] = mapped_column(String(50))
    oauth_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Activity Tracking
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.email})>"
''',
    # User Schemas
    "src/schemas/user.py": '''"""
User Schemas
Pydantic models for user API contracts
Source: https://docs.pydantic.dev/latest/
Verified: 2025-11-14
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """
        Validate password strength.

        Evidence: OWASP password requirements
        Source: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html#implement-proper-password-strength-controls
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """Schema for user profile updates"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    picture_url: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user responses (excludes password)"""
    id: UUID
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserInDB(UserResponse):
    """Schema for user in database (includes hashed password)"""
    hashed_password: str
''',
    # Auth Schemas
    "src/schemas/auth.py": '''"""
Authentication Schemas
Pydantic models for authentication endpoints
Source: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
Verified: 2025-11-14
"""

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT token payload data"""
    user_id: str
    username: str


class LoginRequest(BaseModel):
    """Login credentials"""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str
''',
    # Auth Utils
    "src/utils/auth.py": '''"""
Authentication Utilities
JWT token generation and password hashing
Source: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
Verified: 2025-11-14
"""

from datetime import datetime, timedelta
from typing import Optional
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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
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
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Token payload data

    Returns:
        Encoded JWT refresh token

    Evidence: Refresh tokens for better security
    Source: https://auth0.com/blog/refresh-tokens-what-are-they-and-when-to-use-them/
    Verified: 2025-11-14
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
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
''',
}


def generate_code(components: list[str] | None = None, overwrite: bool = False) -> None:
    """
    Generate application code files from templates.

    Args:
        components: List of components to generate (None = all)
        overwrite: Whether to overwrite existing files
    """
    root_dir = Path(__file__).parent.parent
    generated_count = 0
    skipped_count = 0

    print("=" * 70)
    print("Python Project Starter - Code Generator")
    print("=" * 70)
    print()

    for file_path, content in TEMPLATES.items():
        # Check if we should generate this file
        if components and not any(comp in file_path for comp in components):
            continue

        full_path = root_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file exists
        if full_path.exists() and not overwrite:
            print(f"⏭️  SKIP: {file_path} (already exists)")
            skipped_count += 1
            continue

        # Write file
        full_path.write_text(content)
        print(f"✅ CREATE: {file_path}")
        generated_count += 1

    print()
    print("=" * 70)
    print(f"Generated: {generated_count} files")
    print(f"Skipped: {skipped_count} files")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Review generated files")
    print("2. Customize as needed")
    print("3. Run: docker-compose up --build")
    print()


def main():
    parser = argparse.ArgumentParser(description="Generate Python starter template code")
    parser.add_argument(
        "--components",
        help="Comma-separated list of components to generate (auth,services,mcp)",
        type=str,
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files",
    )

    args = parser.parse_args()

    components = None
    if args.components:
        components = [c.strip() for c in args.components.split(",")]

    generate_code(components=components, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
