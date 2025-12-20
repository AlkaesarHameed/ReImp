"""
Validation Result Models for Claims Validation Engine.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Stores validation results, claim rejections, and rejection evidence
for audit trail and historical reference.
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
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimeStampedModel, UUIDModel


class ValidationStatus(str, Enum):
    """Validation rule execution status."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"
    PENDING_REVIEW = "pending_review"


class RejectionCategory(str, Enum):
    """Categories of claim rejection reasons."""

    FRAUD = "fraud"
    MEDICAL_NECESSITY = "medical_necessity"
    COVERAGE = "coverage"
    CODING_ERROR = "coding_error"
    DOCUMENTATION = "documentation"
    DUPLICATE = "duplicate"
    ELIGIBILITY = "eligibility"
    AUTHORIZATION = "authorization"
    TIMELY_FILING = "timely_filing"
    OTHER = "other"


class EvidenceSeverity(str, Enum):
    """Severity levels for rejection evidence."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AppealStatus(str, Enum):
    """Status of appeal for a rejection."""

    NONE = "none"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"


class ValidationResult(Base, UUIDModel):
    """
    Individual validation rule execution result.

    Stores the result of each validation rule applied to a claim
    for audit trail and analysis.

    Source: Design Document Section 6.5 - Database Schema
    """

    __tablename__ = "validation_results"

    # Foreign key to claim
    claim_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Rule identification
    rule_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        doc="Rule identifier (e.g., 'rule_3', 'rule_4')",
    )

    rule_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Human-readable rule name",
    )

    # Result
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        doc="Validation status (passed, failed, warning, etc.)",
    )

    confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        doc="Confidence score (0.0-1.0) for LLM-based validations",
    )

    # Details
    details: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Detailed validation results as JSON",
    )

    evidence: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Supporting evidence as JSON",
    )

    # Performance
    execution_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Rule execution time in milliseconds",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationship to claim
    claim = relationship("Claim", back_populates="validation_results")

    def __repr__(self) -> str:
        return (
            f"<ValidationResult(claim_id={self.claim_id}, "
            f"rule={self.rule_id}, status={self.status})>"
        )


class ClaimRejection(Base, UUIDModel, TimeStampedModel):
    """
    Claim rejection record with comprehensive reasoning.

    Stores the full rejection details including human-readable reasoning,
    evidence references, and appeal information.

    Source: Design Document Section 3.3.1 - Rejection Display Structure
    """

    __tablename__ = "claim_rejections"

    # Foreign key to claim
    claim_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Rejection identification
    rejection_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        doc="Unique rejection identifier (e.g., 'REJ-2025-00123')",
    )

    rejection_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Category and scoring
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Rejection category (fraud, medical_necessity, etc.)",
    )

    risk_score: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        doc="Overall risk score (0.0-1.0)",
    )

    # Human-readable reasoning
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Brief summary of rejection reason",
    )

    reasoning: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="Detailed reasoning as list of points",
    )

    # Triggered rules
    triggered_rules: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        doc="List of validation rules that triggered rejection",
    )

    # Appeal information
    appeal_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Deadline for submitting appeal",
    )

    appeal_status: Mapped[str] = mapped_column(
        String(20),
        default="none",
        nullable=False,
        doc="Current appeal status",
    )

    appeal_submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    appeal_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Audit
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    reviewed_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    claim = relationship("Claim", back_populates="rejections")
    evidence_items = relationship(
        "RejectionEvidence",
        back_populates="rejection",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<ClaimRejection(rejection_id={self.rejection_id}, "
            f"category={self.category}, claim_id={self.claim_id})>"
        )


class RejectionEvidence(Base, UUIDModel):
    """
    Individual evidence item supporting a rejection.

    Each rejection can have multiple evidence items from different
    sources (documents, validation rules, forensic analysis).

    Source: Design Document Section 3.3.2 - Rejection Reasoning Data Model
    """

    __tablename__ = "rejection_evidence"

    # Foreign key to rejection
    rejection_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("claim_rejections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Evidence identification
    signal_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Type of signal (metadata_mismatch, font_inconsistency, etc.)",
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Severity level (critical, high, medium, low, info)",
    )

    confidence: Mapped[float] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        doc="Confidence in this evidence (0.0-1.0)",
    )

    # Human-readable content
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Brief title for the evidence",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Detailed description of the evidence",
    )

    # Technical details
    details: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="Technical details as JSON",
    )

    # Document reference
    document_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    document_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Name of the referenced document",
    )

    page_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Page number in the document",
    )

    # External reference
    reference_source: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="External reference source (CMS, NCCI, etc.)",
    )

    reference_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="URL to external reference",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    rejection = relationship("ClaimRejection", back_populates="evidence_items")
    document = relationship("Document")

    def __repr__(self) -> str:
        return (
            f"<RejectionEvidence(rejection_id={self.rejection_id}, "
            f"signal={self.signal_type}, severity={self.severity})>"
        )
