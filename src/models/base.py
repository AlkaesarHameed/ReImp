"""
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
    Verified: 2025-11-14
    """

    pass


class TimeStampedModel:
    """
    Mixin for models with created_at and updated_at timestamps.

    Evidence: Audit trail pattern
    Source: https://docs.sqlalchemy.org/en/20/orm/mapped_attributes.html#simple-validators
    Verified: 2025-11-14
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
    Verified: 2025-11-14
    """

    id: Mapped[UUID] = mapped_column(  # type: ignore[type-arg]
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
