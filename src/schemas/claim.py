"""
Pydantic Schemas for Claims Management.
Source: Design Document 01_configurable_claims_processing_design.md Section 4.1
Verified: 2025-12-18
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.enums import (
    ClaimPriority,
    ClaimSource,
    ClaimStatus,
    ClaimType,
    DiagnosisCodeSystem,
    DocumentType,
    FWARiskLevel,
    ProcedureCodeSystem,
)


# =============================================================================
# Line Item Schemas
# =============================================================================


class ClaimLineItemBase(BaseModel):
    """Base schema for claim line items."""

    procedure_code: str = Field(
        ..., min_length=1, max_length=20, description="Procedure code (CPT/HCPCS/ACHI)"
    )
    procedure_code_system: ProcedureCodeSystem = Field(
        default=ProcedureCodeSystem.CPT, description="Procedure coding system"
    )
    modifiers: Optional[list[str]] = Field(None, description="Procedure modifiers")
    description: Optional[str] = Field(
        None, max_length=500, description="Procedure description"
    )
    diagnosis_pointers: list[int] = Field(
        ..., min_length=1, description="Links to diagnosis codes (1-based)"
    )
    service_date: date = Field(..., description="Date of service")
    quantity: int = Field(default=1, ge=1, description="Service units/quantity")
    unit_type: str = Field(default="UN", max_length=10, description="Unit type")
    charged_amount: Decimal = Field(..., gt=0, description="Charged amount")
    ndc_code: Optional[str] = Field(None, max_length=20, description="NDC code (pharmacy)")


class ClaimLineItemCreate(ClaimLineItemBase):
    """Schema for creating a claim line item."""

    line_number: Optional[int] = Field(
        None, description="Line number (auto-assigned if not provided)"
    )


class ClaimLineItemUpdate(BaseModel):
    """Schema for updating a claim line item."""

    procedure_code: Optional[str] = Field(None, min_length=1, max_length=20)
    modifiers: Optional[list[str]] = None
    description: Optional[str] = Field(None, max_length=500)
    diagnosis_pointers: Optional[list[int]] = Field(None, min_length=1)
    service_date: Optional[date] = None
    quantity: Optional[int] = Field(None, ge=1)
    charged_amount: Optional[Decimal] = Field(None, gt=0)


class ClaimLineItemResponse(ClaimLineItemBase):
    """Schema for claim line item response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    claim_id: UUID
    line_number: int
    allowed_amount: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    patient_responsibility: Optional[Decimal] = None
    deductible_applied: Optional[Decimal] = None
    copay_amount: Optional[Decimal] = None
    coinsurance_amount: Optional[Decimal] = None
    adjustment_codes: Optional[list[str]] = None
    remark_codes: Optional[list[str]] = None
    denied: bool
    denial_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Document Schemas
# =============================================================================


class ClaimDocumentBase(BaseModel):
    """Base schema for claim documents."""

    document_type: DocumentType = Field(..., description="Document type")
    filename: str = Field(..., max_length=255, description="Original filename")


class ClaimDocumentUpload(ClaimDocumentBase):
    """Schema for document upload metadata."""

    content_type: str = Field(..., max_length=100, description="MIME type")
    file_size: int = Field(..., gt=0, description="File size in bytes")


class ClaimDocumentResponse(ClaimDocumentBase):
    """Schema for claim document response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    claim_id: UUID
    content_type: str
    file_size: int
    storage_path: str
    processed: bool
    ocr_confidence: Optional[Decimal] = None
    file_hash: str
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Status History Schemas
# =============================================================================


class ClaimStatusHistoryResponse(BaseModel):
    """Schema for claim status history."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    previous_status: Optional[ClaimStatus]
    new_status: ClaimStatus
    changed_at: datetime
    changed_by: Optional[UUID] = None
    actor_type: str
    reason: Optional[str] = None
    details: Optional[dict] = None


# =============================================================================
# Patient Schemas (for submission)
# =============================================================================


class PatientInfo(BaseModel):
    """Patient information for claim submission.

    Member ID is optional - claims can be submitted with document-extracted
    patient data without requiring member network verification.
    """

    member_id: Optional[str] = Field(None, description="Member ID (optional)")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None
    relationship: Optional[str] = Field(default="self")


class ProviderInfo(BaseModel):
    """Provider information for claim submission.

    NPI is optional - claims can be submitted with document-extracted
    provider data without requiring provider network verification.
    """

    npi: Optional[str] = Field(
        None,
        min_length=10,
        max_length=10,
        pattern=r"^\d{10}$",
        description="National Provider Identifier (optional)",
    )
    name: Optional[str] = Field(None, max_length=255)
    tax_id: Optional[str] = Field(None, max_length=20)


# =============================================================================
# Main Claim Schemas
# =============================================================================


class ClaimBase(BaseModel):
    """Base claim schema with common fields."""

    claim_type: ClaimType = Field(..., description="Type of claim")
    service_date_from: date = Field(..., description="Service start date")
    service_date_to: date = Field(..., description="Service end date")
    diagnosis_codes: list[str] = Field(
        ..., min_length=1, description="ICD-10 diagnosis codes"
    )
    primary_diagnosis: str = Field(..., description="Primary diagnosis code")
    diagnosis_code_system: DiagnosisCodeSystem = Field(
        default=DiagnosisCodeSystem.ICD10_CM, description="Diagnosis coding system"
    )
    place_of_service: Optional[str] = Field(None, max_length=2)
    prior_auth_number: Optional[str] = Field(None, max_length=50)
    currency: str = Field(default="USD", max_length=3)

    @field_validator("service_date_to")
    @classmethod
    def end_date_after_start(cls, v: date, info) -> date:
        """Ensure end date is on or after start date."""
        start = info.data.get("service_date_from")
        if start and v < start:
            raise ValueError("Service end date must be on or after start date")
        return v

    @field_validator("primary_diagnosis")
    @classmethod
    def primary_in_list(cls, v: str, info) -> str:
        """Ensure primary diagnosis is in the diagnosis codes list."""
        codes = info.data.get("diagnosis_codes", [])
        if codes and v not in codes:
            raise ValueError("Primary diagnosis must be in diagnosis codes list")
        return v


class ClaimCreate(ClaimBase):
    """Schema for creating a claim (API submission).

    Patient and provider are optional to support document-first workflow
    where claims are submitted from extracted document data without
    requiring member/provider network verification upfront.
    """

    # References - optional for document-first workflow
    patient: Optional[PatientInfo] = Field(
        None, description="Patient information (optional - can be extracted from documents)"
    )
    provider: Optional[ProviderInfo] = Field(
        None, description="Rendering provider (optional - can be extracted from documents)"
    )
    billing_provider: Optional[ProviderInfo] = Field(
        None, description="Billing provider (if different)"
    )
    referring_provider: Optional[ProviderInfo] = Field(
        None, description="Referring provider"
    )

    # Line items
    line_items: list[ClaimLineItemCreate] = Field(
        ..., min_length=1, description="Claim line items"
    )

    # Optional fields
    source: ClaimSource = Field(default=ClaimSource.PORTAL)
    priority: ClaimPriority = Field(default=ClaimPriority.NORMAL)
    admission_date: Optional[date] = Field(None, description="Admission date")
    discharge_date: Optional[date] = Field(None, description="Discharge date")
    facility_type: Optional[str] = Field(None, max_length=10)
    prior_auth_required: bool = Field(default=False)


class ClaimUpdate(BaseModel):
    """Schema for updating a claim (limited fields)."""

    priority: Optional[ClaimPriority] = None
    internal_notes: Optional[str] = None
    member_notes: Optional[str] = None


class ClaimAdjudicate(BaseModel):
    """Schema for manual adjudication."""

    decision: str = Field(
        ..., pattern=r"^(approve|deny|review)$", description="Adjudication decision"
    )
    reason: Optional[str] = Field(None, max_length=500, description="Decision reason")
    denial_codes: Optional[list[str]] = Field(None, description="Denial reason codes")
    line_item_adjustments: Optional[list[dict]] = Field(
        None, description="Per-line item adjustments"
    )
    notes: Optional[str] = None


class ClaimResponse(ClaimBase):
    """Schema for claim response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    tracking_number: str
    external_claim_id: Optional[str] = None
    source: ClaimSource
    priority: ClaimPriority
    status: ClaimStatus

    # Foreign keys
    policy_id: UUID
    member_id: UUID
    provider_id: UUID
    billing_provider_id: Optional[UUID] = None
    referring_provider_id: Optional[UUID] = None

    # Dates
    admission_date: Optional[date] = None
    discharge_date: Optional[date] = None

    # Financial totals
    total_charged: Decimal
    total_allowed: Optional[Decimal] = None
    total_paid: Optional[Decimal] = None
    patient_responsibility: Optional[Decimal] = None

    # Adjudication
    adjudication_type: Optional[str] = None
    adjudication_date: Optional[datetime] = None
    adjudicator_id: Optional[UUID] = None
    denial_reason: Optional[str] = None
    denial_codes: Optional[list[str]] = None

    # FWA
    fwa_score: Optional[Decimal] = None
    fwa_risk_level: Optional[FWARiskLevel] = None
    fwa_flags: Optional[list[str]] = None

    # Medical review
    medical_necessity_verified: bool
    medical_review_notes: Optional[str] = None

    # Processing info
    ocr_confidence: Optional[Decimal] = None
    llm_confidence: Optional[Decimal] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    total_processing_time_ms: Optional[int] = None
    providers_used: Optional[dict] = None

    # Submission info
    submitted_at: Optional[datetime] = None
    submitted_by: Optional[UUID] = None

    # Notes
    internal_notes: Optional[str] = None
    member_notes: Optional[str] = None

    # Adjustment reference
    original_claim_id: Optional[UUID] = None
    adjustment_type: Optional[str] = None

    # Nested data
    line_items: list[ClaimLineItemResponse] = []
    documents: list[ClaimDocumentResponse] = []
    status_history: list[ClaimStatusHistoryResponse] = []

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Computed
    is_pending: bool
    is_finalized: bool
    requires_review: bool
    line_item_count: int


class ClaimListResponse(BaseModel):
    """Schema for listing claims."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tracking_number: str
    claim_type: ClaimType
    status: ClaimStatus
    priority: ClaimPriority
    service_date_from: date
    service_date_to: date
    total_charged: Decimal
    total_paid: Optional[Decimal] = None
    fwa_risk_level: Optional[FWARiskLevel] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime


class ClaimSubmitResponse(BaseModel):
    """Schema for claim submission response."""

    claim_id: UUID
    tracking_number: str
    status: ClaimStatus
    estimated_processing_time: str = Field(default="30 seconds")
    links: dict = Field(default_factory=dict)


class ClaimStatusResponse(BaseModel):
    """Schema for claim status response."""

    claim_id: UUID
    tracking_number: str
    status: ClaimStatus
    status_history: list[ClaimStatusHistoryResponse]
    processing_metrics: Optional[dict] = None


# =============================================================================
# Processing Result Schemas
# =============================================================================


class AdjudicationResult(BaseModel):
    """Schema for adjudication result details."""

    decision: str  # approved, denied, needs_review
    decision_date: datetime
    adjudication_type: str  # auto, manual
    line_items: list[dict]
    totals: dict
    denial_reason: Optional[str] = None
    denial_codes: Optional[list[str]] = None


class MedicalReviewResult(BaseModel):
    """Schema for medical review result."""

    necessity_validated: bool
    diagnosis_procedure_match: bool
    coding_standard: str
    entities_extracted: list[dict]
    warnings: list[str] = Field(default_factory=list)


class FWAAnalysisResult(BaseModel):
    """Schema for FWA analysis result."""

    risk_score: float
    risk_level: FWARiskLevel
    flags: list[str]
    duplicate_found: bool
    upcoding_detected: bool
    pattern_anomalies: list[str]
    recommendation: str  # approve, review, deny
    model_version: str
    confidence: float


class ClaimProcessingResult(BaseModel):
    """Schema for complete claim processing result."""

    claim_id: UUID
    tracking_number: str
    status: ClaimStatus
    adjudication: Optional[AdjudicationResult] = None
    medical_review: Optional[MedicalReviewResult] = None
    fraud_analysis: Optional[FWAAnalysisResult] = None
    processing_time_ms: int
    providers_used: dict
    created_at: datetime
