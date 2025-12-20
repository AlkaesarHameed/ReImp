"""
Authentication Schemas
Pydantic models for authentication endpoints
Source: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
Verified: 2025-11-14
"""

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """
    JWT token response.

    Evidence: OAuth2 token format
    Source: https://datatracker.ietf.org/doc/html/rfc6749#section-5.1
    Verified: 2025-11-14
    """

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


class TokenResponse(BaseModel):
    """
    Token response schema for API responses.

    Evidence: OAuth2 token response format
    Source: https://datatracker.ietf.org/doc/html/rfc6749#section-5.1
    Verified: 2025-12-18
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes in seconds


class UserLogin(BaseModel):
    """User login request schema."""

    email: EmailStr
    password: str


class UserRegister(BaseModel):
    """User registration request schema."""

    email: EmailStr
    password: str
    username: str
    first_name: str | None = None
    last_name: str | None = None
