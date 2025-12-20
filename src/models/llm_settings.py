"""
LLM Settings Model for Multi-Tenant Configuration.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Stores per-tenant, per-task LLM provider and model configuration.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimeStampedModel, UUIDModel


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    AZURE = "azure"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    VLLM = "vllm"


class LLMTaskType(str, Enum):
    """Task types that can have separate LLM configurations."""

    EXTRACTION = "extraction"          # Rules 1-2: Data extraction
    VALIDATION = "validation"          # Rule 5: Clinical necessity
    NECESSITY = "necessity"            # Medical necessity review
    SUMMARIZATION = "summarization"    # Report summarization
    TRANSLATION = "translation"        # Document translation
    FRAUD_REVIEW = "fraud_review"      # Fraud case review


class LLMSettings(Base, UUIDModel, TimeStampedModel):
    """
    LLM configuration settings per tenant and task type.

    Supports per-task configuration allowing different providers/models
    for extraction vs validation tasks.

    Source: Design Document Section 4.3 - LLM Settings API
    """

    __tablename__ = "llm_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "task_type", name="uq_llm_settings_tenant_task"),
    )

    # Foreign key to tenant
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Task type this configuration applies to
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Primary provider configuration
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="LLM provider (azure, openai, anthropic, ollama, vllm)",
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Model name/identifier for the provider",
    )

    api_endpoint: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Custom API endpoint URL (for Azure, Ollama, vLLM)",
    )

    # Model parameters
    temperature: Mapped[float] = mapped_column(
        Numeric(3, 2),
        default=0.1,
        nullable=False,
        doc="Model temperature (0.0-2.0)",
    )

    max_tokens: Mapped[int] = mapped_column(
        Integer,
        default=4096,
        nullable=False,
        doc="Maximum tokens in response",
    )

    # Fallback configuration
    fallback_provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Fallback LLM provider when primary fails",
    )

    fallback_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Fallback model name",
    )

    # Rate limiting
    rate_limit_rpm: Mapped[int] = mapped_column(
        Integer,
        default=60,
        nullable=False,
        doc="Rate limit: requests per minute",
    )

    rate_limit_tpm: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Rate limit: tokens per minute",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this configuration is active",
    )

    # Relationship to tenant
    tenant = relationship("Tenant", back_populates="llm_settings")

    def __repr__(self) -> str:
        return (
            f"<LLMSettings(tenant_id={self.tenant_id}, "
            f"task={self.task_type}, provider={self.provider}, "
            f"model={self.model_name})>"
        )


class LLMUsageLog(Base, UUIDModel):
    """
    LLM usage tracking for cost monitoring and analytics.

    Tracks token usage, latency, and cost per request.
    """

    __tablename__ = "llm_usage_logs"

    # Foreign keys
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    settings_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("llm_settings.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Request details
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Token usage
    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Performance metrics
    latency_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Request latency in milliseconds",
    )

    # Cost (estimated)
    estimated_cost_usd: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 6),
        nullable=True,
        doc="Estimated cost in USD",
    )

    # Status
    success: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    fallback_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<LLMUsageLog(tenant_id={self.tenant_id}, "
            f"task={self.task_type}, tokens={self.total_tokens})>"
        )
