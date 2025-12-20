"""
Audit Logging Model for HIPAA Compliance.
Source: Design Document 01_configurable_claims_processing_design.md Section 6.5
Verified: 2025-12-18

Uses TimescaleDB hypertable for efficient time-series storage and querying.
Note: TimescaleDB extension must be installed on PostgreSQL.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Enum, Index, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.enums import AuditAction, AuditResourceType
from src.models.base import Base


class AuditLog(Base):
    """
    Audit log entry for compliance and security tracking.

    HIPAA requires:
    - All access to PHI must be logged
    - Logs must be retained for 7 years
    - Logs must include who, what, when, where

    Evidence: HIPAA Security Rule - 45 CFR 164.312(b)
    Source: https://www.hhs.gov/hipaa/for-professionals/security/index.html
    Verified: 2025-12-18

    Note: This table should be converted to a TimescaleDB hypertable
    after creation for optimal time-series performance.

    SQL to convert (run after migrations):
    ```sql
    SELECT create_hypertable('audit_logs', 'timestamp');
    SELECT add_retention_policy('audit_logs', INTERVAL '7 years');
    ```
    """

    __tablename__ = "audit_logs"

    # Primary key with timestamp for TimescaleDB
    # Note: TimescaleDB requires timestamp in primary key for hypertables
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Auto-incrementing ID",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="When the action occurred",
    )

    # Tenant Context
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Tenant ID",
    )

    # Actor Information
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="User ID (null for system actions)",
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Username at time of action",
    )
    actor_type: Mapped[str] = mapped_column(
        String(50),
        default="user",
        nullable=False,
        comment="Actor type: user, system, api_client, webhook",
    )

    # Action Information
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction),
        nullable=False,
        index=True,
        comment="Type of action performed",
    )
    resource_type: Mapped[AuditResourceType] = mapped_column(
        Enum(AuditResourceType),
        nullable=False,
        index=True,
        comment="Type of resource affected",
    )
    resource_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="ID of affected resource",
    )
    resource_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Human-readable resource identifier",
    )

    # Change Details
    changes: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="JSON diff of changes (old/new values)",
    )
    details: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional context about the action",
    )

    # Request Context
    ip_address: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
        comment="Client IP address",
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Client user agent string",
    )
    request_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Request/correlation ID for tracing",
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Session ID",
    )

    # Result
    success: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether action was successful",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if action failed",
    )

    # PHI Indicator
    contains_phi: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether this log entry involves PHI access",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_audit_logs_tenant_timestamp", "tenant_id", "timestamp"),
        Index("ix_audit_logs_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_action_timestamp", "action", "timestamp"),
        # Composite index for compliance queries
        Index(
            "ix_audit_logs_compliance",
            "tenant_id",
            "action",
            "resource_type",
            "timestamp",
        ),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action='{self.action}', resource='{self.resource_type}')>"


class PHIAccessLog(Base):
    """
    Specialized log for Protected Health Information access.

    HIPAA requires detailed tracking of all PHI access.
    This is a separate table for easier compliance reporting.
    """

    __tablename__ = "phi_access_logs"

    # Primary key with timestamp
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Auto-incrementing ID",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="When access occurred",
    )

    # Context
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Tenant ID",
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="User who accessed PHI",
    )

    # Patient/Member Information
    member_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Member whose PHI was accessed",
    )
    member_identifier: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Member ID at time of access (for historical records)",
    )

    # Access Details
    access_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: view, export, print, transmit",
    )
    phi_categories: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        comment="Categories of PHI accessed (demographics, diagnosis, etc.)",
    )
    access_reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Business reason for access",
    )

    # Related Resource
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Resource type containing PHI",
    )
    resource_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        comment="ID of resource containing PHI",
    )

    # Request Context
    ip_address: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
        comment="Client IP address",
    )
    request_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        comment="Request ID for correlation",
    )

    # Indexes
    __table_args__ = (
        Index("ix_phi_access_tenant_member", "tenant_id", "member_id"),
        Index("ix_phi_access_user_timestamp", "user_id", "timestamp"),
        Index("ix_phi_access_member_timestamp", "member_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<PHIAccessLog(user_id={self.user_id}, member_id={self.member_id})>"


class ProviderUsageLog(Base):
    """
    Log of AI/ML provider usage for cost tracking and optimization.

    Tracks which providers were used, response times, and outcomes.
    """

    __tablename__ = "provider_usage_logs"

    # Primary key with timestamp
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Auto-incrementing ID",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="When provider was called",
    )

    # Context
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Tenant ID",
    )
    claim_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Associated claim ID (if applicable)",
    )

    # Provider Information
    gateway_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Gateway type: llm, ocr, translation, rules, medical_nlp, currency",
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Provider used (e.g., ollama, paddleocr, azure)",
    )
    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Specific model used (e.g., qwen2.5-vl:7b)",
    )

    # Request Details
    operation: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Operation performed (e.g., parse_document, extract_text)",
    )
    input_size: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Input size (tokens, bytes, pages, etc.)",
    )
    output_size: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Output size",
    )

    # Performance Metrics
    latency_ms: Mapped[int] = mapped_column(
        nullable=False,
        comment="Total latency in milliseconds",
    )
    queue_time_ms: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Time spent in queue (if applicable)",
    )

    # Outcome
    success: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether call was successful",
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Confidence score of result",
    )
    fallback_used: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether fallback provider was used",
    )
    fallback_reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Reason for fallback (error, low_confidence, timeout)",
    )

    # Cost Tracking
    estimated_cost: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Estimated cost in USD",
    )
    tokens_used: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Tokens used (for LLM calls)",
    )

    # Error Information
    error_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Error code if failed",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if failed",
    )

    # Indexes
    __table_args__ = (
        Index("ix_provider_usage_tenant_gateway", "tenant_id", "gateway_type"),
        Index("ix_provider_usage_provider_timestamp", "provider", "timestamp"),
        Index("ix_provider_usage_claim", "claim_id"),
    )

    def __repr__(self) -> str:
        return f"<ProviderUsageLog(gateway='{self.gateway_type}', provider='{self.provider}')>"
