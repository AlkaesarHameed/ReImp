"""
Claim Model for Insurance Claims Management.
Source: Design Document 01_configurable_claims_processing_design.md Section 4.1
Verified: 2025-12-18
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.enums import (
    ClaimPriority,
    ClaimSource,
    ClaimStatus,
    ClaimType,
    DiagnosisCodeSystem,
    FWARiskLevel,
    ProcedureCodeSystem,
)
from src.models.base import Base, TimeStampedModel, UUIDModel

if TYPE_CHECKING:
    from src.models.healthcare_provider import HealthcareProvider
    from src.models.member import Member
    from src.models.person import Person
    from src.models.policy import Policy
    from src.models.tenant import Tenant
    from src.models.validation_result import ClaimRejection, ValidationResult


class Claim(Base, UUIDModel, TimeStampedModel):
    """
    Insurance claim model.

    Represents a healthcare claim submitted for reimbursement,
    including all associated line items, documents, and adjudication data.

    Evidence: Claim structure based on HIPAA X12 837 transaction set
    Source: https://www.cms.gov/Regulations-and-Guidance/Administrative-Simplification/Transactions
    Verified: 2025-12-18
    """

    __tablename__ = "claims"

    # Multi-tenant Foreign Key
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owning tenant ID",
    )

    # Claim Identification
    tracking_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Human-readable tracking number (e.g., CLM-2025-000001)",
    )
    external_claim_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="External system claim ID (for EDI integration)",
    )

    # Claim Type and Source
    claim_type: Mapped[ClaimType] = mapped_column(
        Enum(ClaimType),
        nullable=False,
        index=True,
        comment="Type of claim (professional, institutional, etc.)",
    )
    source: Mapped[ClaimSource] = mapped_column(
        Enum(ClaimSource),
        default=ClaimSource.PORTAL,
        nullable=False,
        comment="Source of claim submission",
    )
    priority: Mapped[ClaimPriority] = mapped_column(
        Enum(ClaimPriority),
        default=ClaimPriority.NORMAL,
        nullable=False,
        comment="Processing priority",
    )

    # Status
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus),
        default=ClaimStatus.DRAFT,
        nullable=False,
        index=True,
        comment="Current claim status",
    )

    # Foreign Keys (nullable to support document-first workflow)
    # Policy/member/provider can be resolved later during processing
    policy_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("policies.id", ondelete="RESTRICT"),
        nullable=True,  # Allow NULL for document-first workflow
        index=True,
        comment="Associated policy ID (resolved from documents or manual entry)",
    )
    member_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="RESTRICT"),
        nullable=True,  # Allow NULL for document-first workflow
        index=True,
        comment="Patient/member ID (resolved from documents or manual entry)",
    )
    provider_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("healthcare_providers.id", ondelete="RESTRICT"),
        nullable=True,  # Allow NULL for document-first workflow
        index=True,
        comment="Rendering provider ID (resolved from documents or manual entry)",
    )
    billing_provider_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("healthcare_providers.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Billing provider ID (if different)",
    )
    referring_provider_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("healthcare_providers.id", ondelete="SET NULL"),
        nullable=True,
        comment="Referring provider ID",
    )

    # Service Dates
    service_date_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Service start date",
    )
    service_date_to: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Service end date",
    )
    admission_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Admission date (institutional claims)",
    )
    discharge_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Discharge date (institutional claims)",
    )

    # Diagnosis Information
    diagnosis_codes: Mapped[list] = mapped_column(
        ARRAY(String),
        nullable=False,
        comment="List of ICD-10 diagnosis codes",
    )
    primary_diagnosis: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Primary diagnosis code",
    )
    diagnosis_code_system: Mapped[DiagnosisCodeSystem] = mapped_column(
        Enum(DiagnosisCodeSystem),
        default=DiagnosisCodeSystem.ICD10_CM,
        nullable=False,
        comment="Diagnosis coding system",
    )

    # Financial Summary
    total_charged: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Total charges submitted",
    )
    total_allowed: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Total allowed amount (after adjudication)",
    )
    total_paid: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Total amount paid by insurance",
    )
    patient_responsibility: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Total patient responsibility",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
        comment="Currency code (ISO 4217)",
    )

    # Place of Service
    place_of_service: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
        comment="Place of service code",
    )
    facility_type: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Facility type code",
    )

    # Prior Authorization
    prior_auth_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Prior authorization number",
    )
    prior_auth_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Prior auth was required",
    )

    # Adjudication Information
    adjudication_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Adjudication type: auto, manual, escalated",
    )
    adjudication_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When claim was adjudicated",
    )
    adjudicator_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        comment="ID of adjudicator (for manual review)",
    )
    denial_reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Denial reason code/description",
    )
    denial_codes: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="List of denial reason codes",
    )

    # FWA (Fraud, Waste, Abuse) Analysis
    fwa_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(4, 3),
        nullable=True,
        comment="FWA risk score (0.000 - 1.000)",
    )
    fwa_risk_level: Mapped[Optional[FWARiskLevel]] = mapped_column(
        Enum(FWARiskLevel),
        nullable=True,
        comment="FWA risk classification",
    )
    fwa_flags: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="List of FWA flags",
    )

    # Medical Review
    medical_necessity_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Medical necessity verified",
    )
    medical_review_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Medical review notes",
    )

    # Document Processing
    ocr_confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(4, 3),
        nullable=True,
        comment="OCR extraction confidence score",
    )
    llm_confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(4, 3),
        nullable=True,
        comment="LLM parsing confidence score",
    )

    # Processing Metrics
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When processing started",
    )
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When processing completed",
    )
    total_processing_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total processing time in milliseconds",
    )

    # Provider Usage Tracking
    providers_used: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="AI/ML providers used for processing",
    )

    # Submission Information
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When claim was submitted",
    )
    submitted_by: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        comment="User who submitted the claim",
    )

    # Notes
    internal_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal processing notes",
    )
    member_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notes for member EOB",
    )

    # Original Claim (for adjustments/corrections)
    original_claim_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="SET NULL"),
        nullable=True,
        comment="Original claim ID (for adjustments)",
    )
    adjustment_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Adjustment type: correction, void, replacement",
    )

    # Relationships
    line_items: Mapped[list["ClaimLineItem"]] = relationship(
        back_populates="claim",
        cascade="all, delete-orphan",
        order_by="ClaimLineItem.line_number",
    )
    documents: Mapped[list["ClaimDocument"]] = relationship(
        back_populates="claim",
        cascade="all, delete-orphan",
    )
    status_history: Mapped[list["ClaimStatusHistory"]] = relationship(
        back_populates="claim",
        cascade="all, delete-orphan",
        order_by="ClaimStatusHistory.changed_at.desc()",
    )
    validation_results: Mapped[list["ValidationResult"]] = relationship(
        "ValidationResult",
        back_populates="claim",
        cascade="all, delete-orphan",
        order_by="ValidationResult.created_at.desc()",
    )
    rejections: Mapped[list["ClaimRejection"]] = relationship(
        "ClaimRejection",
        back_populates="claim",
        cascade="all, delete-orphan",
        order_by="ClaimRejection.created_at.desc()",
    )
    # policy: Mapped["Policy"] = relationship(back_populates="claims")
    # member: Mapped["Member"] = relationship(back_populates="claims")
    # provider: Mapped["HealthcareProvider"] = relationship(back_populates="claims", foreign_keys=[provider_id])

    # Indexes
    __table_args__ = (
        Index("ix_claims_tenant_tracking", "tenant_id", "tracking_number"),
        Index("ix_claims_tenant_status", "tenant_id", "status"),
        Index("ix_claims_tenant_member", "tenant_id", "member_id"),
        Index("ix_claims_tenant_provider", "tenant_id", "provider_id"),
        Index("ix_claims_tenant_service_date", "tenant_id", "service_date_from"),
        Index("ix_claims_tenant_submitted", "tenant_id", "submitted_at"),
        Index("ix_claims_fwa_risk", "fwa_risk_level", "fwa_score"),
    )

    def __repr__(self) -> str:
        return f"<Claim(id={self.id}, tracking='{self.tracking_number}', status='{self.status}')>"

    @property
    def is_pending(self) -> bool:
        """Check if claim is in a pending state."""
        return self.status in (
            ClaimStatus.SUBMITTED,
            ClaimStatus.DOC_PROCESSING,
            ClaimStatus.VALIDATING,
            ClaimStatus.ADJUDICATING,
        )

    @property
    def is_finalized(self) -> bool:
        """Check if claim processing is complete."""
        return self.status in (
            ClaimStatus.APPROVED,
            ClaimStatus.DENIED,
            ClaimStatus.PAID,
            ClaimStatus.CLOSED,
        )

    @property
    def requires_review(self) -> bool:
        """Check if claim requires manual review."""
        return self.status == ClaimStatus.NEEDS_REVIEW

    @property
    def line_item_count(self) -> int:
        """Get number of line items."""
        return len(self.line_items) if self.line_items else 0

    def calculate_totals(self) -> None:
        """Calculate total amounts from line items."""
        if not self.line_items:
            return

        self.total_charged = sum(
            item.charged_amount for item in self.line_items
        )
        self.total_allowed = sum(
            item.allowed_amount or Decimal("0") for item in self.line_items
        )
        self.total_paid = sum(
            item.paid_amount or Decimal("0") for item in self.line_items
        )
        self.patient_responsibility = sum(
            item.patient_responsibility or Decimal("0") for item in self.line_items
        )


class ClaimLineItem(Base, UUIDModel, TimeStampedModel):
    """
    Individual line item within a claim.

    Represents a single service/procedure billed on the claim.
    """

    __tablename__ = "claim_line_items"

    # Foreign Key
    claim_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated claim ID",
    )

    # Line Item Identification
    line_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Line item number (1-based)",
    )

    # Procedure Information
    procedure_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Procedure code (CPT/HCPCS/ACHI)",
    )
    procedure_code_system: Mapped[ProcedureCodeSystem] = mapped_column(
        Enum(ProcedureCodeSystem),
        default=ProcedureCodeSystem.CPT,
        nullable=False,
        comment="Procedure coding system",
    )
    modifiers: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Procedure modifiers",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Procedure description",
    )

    # Diagnosis Link
    diagnosis_pointers: Mapped[list] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        default=list,
        comment="Links to diagnosis codes (1-based indexes)",
    )

    # Service Details
    service_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date of service",
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Service units/quantity",
    )
    unit_type: Mapped[str] = mapped_column(
        String(10),
        default="UN",
        nullable=False,
        comment="Unit type (UN=unit, MJ=minute, etc.)",
    )

    # Financial Information
    charged_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Charged amount",
    )
    allowed_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Allowed amount",
    )
    paid_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Insurance paid amount",
    )
    patient_responsibility: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Patient responsibility",
    )

    # Deductions/Adjustments Breakdown
    deductible_applied: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Deductible amount applied",
    )
    copay_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Copay amount",
    )
    coinsurance_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Coinsurance amount",
    )

    # Adjustment Codes
    adjustment_codes: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Adjustment reason codes",
    )
    remark_codes: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Remark codes",
    )

    # Status
    denied: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Line item denied",
    )
    denial_reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Denial reason",
    )

    # NDC (for pharmacy claims)
    ndc_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="National Drug Code",
    )

    # Relationship
    claim: Mapped["Claim"] = relationship(back_populates="line_items")

    # Indexes
    __table_args__ = (
        Index("ix_claim_line_items_claim_line", "claim_id", "line_number"),
        Index("ix_claim_line_items_procedure", "procedure_code"),
    )

    def __repr__(self) -> str:
        return f"<ClaimLineItem(claim_id={self.claim_id}, line={self.line_number}, code='{self.procedure_code}')>"


class ClaimDocument(Base, UUIDModel, TimeStampedModel):
    """
    Document attached to a claim.

    Stores metadata about uploaded documents and their processing status.
    """

    __tablename__ = "claim_documents"

    # Foreign Key
    claim_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated claim ID",
    )

    # Document Information
    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Document type (claim_form, invoice, etc.)",
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename",
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="MIME type",
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="File size in bytes",
    )

    # Storage
    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Storage path (MinIO/S3)",
    )
    storage_bucket: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Storage bucket name",
    )

    # Processing
    processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="OCR/processing completed",
    )
    ocr_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Extracted OCR text",
    )
    ocr_confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(4, 3),
        nullable=True,
        comment="OCR confidence score",
    )
    extracted_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Structured data extracted from document",
    )

    # Hash for duplicate detection
    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 hash of file content",
    )

    # Relationships
    claim: Mapped["Claim"] = relationship(back_populates="documents")
    persons: Mapped[list["Person"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        foreign_keys="Person.document_id",
    )

    # Indexes
    __table_args__ = (
        Index("ix_claim_documents_claim_type", "claim_id", "document_type"),
    )

    def __repr__(self) -> str:
        return f"<ClaimDocument(claim_id={self.claim_id}, type='{self.document_type}')>"


class ClaimStatusHistory(Base, UUIDModel):
    """
    Status change history for a claim.

    Provides complete audit trail of claim status changes.
    """

    __tablename__ = "claim_status_history"

    # Foreign Key
    claim_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated claim ID",
    )

    # Status Change
    previous_status: Mapped[Optional[ClaimStatus]] = mapped_column(
        Enum(ClaimStatus),
        nullable=True,
        comment="Previous status",
    )
    new_status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus),
        nullable=False,
        comment="New status",
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="When status changed",
    )

    # Actor
    changed_by: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        comment="User who changed status",
    )
    actor_type: Mapped[str] = mapped_column(
        String(20),
        default="system",
        nullable=False,
        comment="Actor type: system, user, api",
    )

    # Details
    reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Reason for status change",
    )
    details: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional details about the change",
    )

    # Relationship
    claim: Mapped["Claim"] = relationship(back_populates="status_history")

    # Indexes
    __table_args__ = (
        Index("ix_claim_status_history_claim_changed", "claim_id", "changed_at"),
    )

    def __repr__(self) -> str:
        return f"<ClaimStatusHistory(claim_id={self.claim_id}, {self.previous_status} -> {self.new_status})>"
