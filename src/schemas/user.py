"""
User Schemas
Pydantic models for user API contracts
Source: https://docs.pydantic.dev/latest/
Verified: 2025-11-14
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Base user schema with common fields"""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: str | None = Field(None, max_length=255)


class UserCreate(UserBase):
    """
    Schema for user registration.

    Evidence: Password strength requirements follow OWASP guidelines
    - Minimum 12 characters (OWASP recommendation for 2025+)
    - Must contain uppercase, lowercase, digit, and special character
    Source: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
    Verified: 2025-11-14
    """

    password: str = Field(..., min_length=12, max_length=100, description="Password (min 12 chars)")

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """
        Validate password strength against OWASP recommendations.

        Requirements:
        - Minimum 12 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character

        Evidence: OWASP Password Storage Cheat Sheet
        Source: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
        """
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        # Check for special characters
        special_chars = set("!@#$%^&*()_+-=[]{}|;:,.<>?")
        if not any(c in special_chars for c in v):
            raise ValueError(
                "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)"
            )
        return v


class UserUpdate(BaseModel):
    """Schema for user profile updates"""

    email: EmailStr | None = None
    username: str | None = Field(None, min_length=3, max_length=100)
    full_name: str | None = Field(None, max_length=255)
    picture_url: str | None = None


class UserResponse(UserBase):
    """Schema for user responses (excludes password)"""

    id: UUID
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None

    model_config = {"from_attributes": True}


class UserInDB(UserResponse):
    """Schema for user in database (includes hashed password)"""

    hashed_password: str
