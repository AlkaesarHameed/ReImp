"""
Document Model
Demonstrates pgvector for semantic search
Source: https://github.com/pgvector/pgvector
Verified: 2025-11-14
"""

from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.api.config import settings
from src.models.base import Base, TimeStampedModel, UUIDModel


class Document(Base, UUIDModel, TimeStampedModel):
    """
    Document model with vector embeddings for semantic search.

    Evidence: pgvector enables similarity search using vector embeddings
    Source: https://github.com/pgvector/pgvector#getting-started
    Verified: 2025-11-14
    """

    __tablename__ = "documents"

    # Foreign Keys
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Vector Embedding for Semantic Search
    # Dimension sourced from settings to keep DB schema aligned with embedding provider
    # Source: https://github.com/pgvector/pgvector-python
    embedding: Mapped[Vector | None] = mapped_column(Vector(settings.EMBEDDING_DIMENSIONS))

    # File Metadata
    file_path: Mapped[str | None] = mapped_column(Text)  # MinIO object path
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size: Mapped[int | None] = mapped_column(BigInteger)

    def __repr__(self) -> str:
        return f"<Document {self.title}>"
