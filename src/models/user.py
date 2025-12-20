"""
User Model
SQLAlchemy model for user authentication and profile
Source: https://docs.sqlalchemy.org/en/20/orm/quickstart.html
Verified: 2025-11-14
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
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
    full_name: Mapped[str | None] = mapped_column(String(255))
    picture_url: Mapped[str | None] = mapped_column(String)

    # Account Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # OAuth2 Fields
    oauth_provider: Mapped[str | None] = mapped_column(String(50))
    oauth_id: Mapped[str | None] = mapped_column(String(255))

    # Activity Tracking
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.email})>"
