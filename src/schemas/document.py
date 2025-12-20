"""
Document Schemas
Pydantic models for document API contracts
Source: https://docs.pydantic.dev/latest/
Verified: 2025-11-14
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Base document schema"""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)


class DocumentCreate(DocumentBase):
    """Schema for document creation"""

    pass


class DocumentUpdate(BaseModel):
    """Schema for document updates"""

    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = Field(None, min_length=1)


class DocumentResponse(DocumentBase):
    """Schema for document responses"""

    id: UUID
    user_id: UUID | None
    file_path: str | None
    mime_type: str | None
    file_size: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentWithEmbedding(DocumentResponse):
    """Schema including embedding vector"""

    embedding: list[float] | None = None


class DocumentSearchQuery(BaseModel):
    """Schema for semantic search queries"""

    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
