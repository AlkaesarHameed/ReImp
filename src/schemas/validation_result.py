"""
Validation Result Schemas for API validation.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


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


# ============================================================================
# Validation Result Schemas
# ============================================================================

class ValidationResultBase(BaseModel):
    """Base schema for validation result."""

    rule_id: str = Field(..., description="Rule identifier")
    rule_name: str = Field(..., description="Human-readable rule name")
    status: ValidationStatus = Field(..., description="Validation status")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    details: Optional[dict[str, Any]] = Field(None, description="Detailed results")
    evidence: Optional[dict[str, Any]] = Field(None, description="Supporting evidence")
    execution_time_ms: Optional[int] = Field(None, description="Execution time")


class ValidationResultCreate(ValidationResultBase):
    """Schema for creating validation result."""

    claim_id: UUID


class ValidationResultResponse(ValidationResultBase):
    """Schema for validation result response."""

    id: UUID
    claim_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ValidationSummary(BaseModel):
    """Summary of all validation results for a claim."""

    claim_id: UUID
    total_rules: int
    passed: int
    failed: int
    warnings: int
    skipped: int
    errors: int
    pending_review: int
    overall_status: ValidationStatus
    risk_score: float = Field(..., ge=0.0, le=1.0)
    can_submit: bool
    requires_review: bool
    results: list[ValidationResultResponse]


# ============================================================================
# Rejection Evidence Schemas
# ============================================================================

class EvidenceReferenceBase(BaseModel):
    """Base schema for evidence reference."""

    signal_type: str = Field(..., description="Type of signal")
    severity: EvidenceSeverity = Field(..., description="Severity level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence")
    title: str = Field(..., max_length=255, description="Brief title")
    description: str = Field(..., description="Detailed description")
    details: dict[str, Any] = Field(..., description="Technical details")
    document_name: Optional[str] = Field(None, description="Document name")
    document_id: Optional[UUID] = Field(None, description="Document ID")
    page_number: Optional[int] = Field(None, description="Page number")
    reference_source: Optional[str] = Field(None, description="Reference source")
    reference_url: Optional[str] = Field(None, description="Reference URL")


class EvidenceReferenceCreate(EvidenceReferenceBase):
    """Schema for creating evidence reference."""

    pass


class EvidenceReferenceResponse(EvidenceReferenceBase):
    """Schema for evidence reference response."""

    id: UUID
    rejection_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Claim Rejection Schemas
# ============================================================================

class ClaimRejectionBase(BaseModel):
    """Base schema for claim rejection."""

    category: RejectionCategory = Field(..., description="Rejection category")
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Risk score")
    summary: str = Field(..., description="Brief summary")
    reasoning: list[str] = Field(..., description="Detailed reasoning points")
    triggered_rules: Optional[list[str]] = Field(None, description="Triggered rules")
    appeal_deadline: Optional[datetime] = Field(None, description="Appeal deadline")


class ClaimRejectionCreate(ClaimRejectionBase):
    """Schema for creating claim rejection."""

    claim_id: UUID
    evidence_items: Optional[list[EvidenceReferenceCreate]] = Field(
        None, description="Evidence items"
    )


class ClaimRejectionResponse(ClaimRejectionBase):
    """Schema for claim rejection response."""

    id: UUID
    claim_id: UUID
    rejection_id: str
    rejection_date: datetime
    appeal_status: AppealStatus
    appeal_submitted_at: Optional[datetime]
    appeal_notes: Optional[str]
    evidence_items: list[EvidenceReferenceResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RejectionDetailResponse(BaseModel):
    """
    Comprehensive rejection detail response.

    Source: Design Document Section 3.3.1 - Rejection Display Structure
    """

    # Header Information
    claim_id: UUID
    rejection_id: str
    status: str = "REJECTED"
    rejection_date: datetime
    category: RejectionCategory
    category_display: str = Field(..., description="Human-readable category")
    risk_score: float

    # Reasoning
    summary: str
    reasoning_points: list[str]

    # Evidence
    evidence_references: list[EvidenceReferenceResponse]
    evidence_by_severity: dict[str, list[EvidenceReferenceResponse]]

    # Triggered Rules
    triggered_rules: list[dict[str, Any]]

    # Appeal Information
    appeal_deadline: Optional[datetime]
    appeal_status: AppealStatus
    appeal_instructions: list[str]
    can_appeal: bool

    # Audit
    created_at: datetime
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]


# ============================================================================
# Comprehensive Validation Schemas
# ============================================================================

class ComprehensiveValidationRequest(BaseModel):
    """Request for comprehensive claim validation."""

    claim_id: Optional[UUID] = Field(None, description="Existing claim ID")
    document_ids: list[UUID] = Field(..., description="Documents to validate")
    skip_rules: Optional[list[str]] = Field(None, description="Rules to skip")
    force_revalidate: bool = Field(False, description="Force re-validation")


class ComprehensiveValidationResponse(BaseModel):
    """
    Response from comprehensive claim validation.

    Source: Design Document Section 3.2 - Component Interactions
    """

    claim_id: UUID
    validation_id: str

    # Extracted Data (Rules 1-2)
    extracted_data: dict[str, Any] = Field(..., description="Data extracted from documents")

    # Validation Results
    validation_results: list[ValidationResultResponse]
    validation_summary: ValidationSummary

    # Decision
    can_submit: bool = Field(..., description="Whether claim can be submitted")
    requires_review: bool = Field(..., description="Whether human review required")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Overall risk score")

    # Issues
    errors: list[dict[str, Any]] = Field(default_factory=list, description="Critical errors")
    warnings: list[dict[str, Any]] = Field(default_factory=list, description="Warnings")

    # Performance
    total_execution_time_ms: int
    validation_timestamp: datetime


class ValidationRuleInfo(BaseModel):
    """Information about a validation rule."""

    rule_id: str
    rule_name: str
    description: str
    category: str  # extraction, fraud, medical, coverage
    priority: str  # P0, P1, P2
    is_llm_based: bool
    estimated_time_ms: int


class ValidationRulesResponse(BaseModel):
    """Response containing all validation rules."""

    rules: list[ValidationRuleInfo]
    total_rules: int
    llm_based_rules: int
    deterministic_rules: int


class RuleValidationDetail(BaseModel):
    """Detail of a single rule validation result for risk scoring."""

    rule_id: str = Field(..., description="Rule identifier")
    rule_name: str = Field(..., description="Human-readable rule name")
    status: str = Field(..., description="Validation status: passed, failed, warning, skipped")
    issues_found: int = Field(0, description="Number of issues found")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score")
    details: Optional[dict[str, Any]] = Field(None, description="Additional details")


# Rule information constants
VALIDATION_RULES = [
    ValidationRuleInfo(
        rule_id="rule_1",
        rule_name="Insured Data Extraction",
        description="Extract member/policy information from documents",
        category="extraction",
        priority="P0",
        is_llm_based=True,
        estimated_time_ms=2000,
    ),
    ValidationRuleInfo(
        rule_id="rule_2",
        rule_name="Code/Service Extraction",
        description="Extract ICD-10, CPT, medications from documents",
        category="extraction",
        priority="P0",
        is_llm_based=True,
        estimated_time_ms=3000,
    ),
    ValidationRuleInfo(
        rule_id="rule_3",
        rule_name="Fraud Detection",
        description="Detect computer-edited/forged documents",
        category="fraud",
        priority="P0",
        is_llm_based=False,
        estimated_time_ms=500,
    ),
    ValidationRuleInfo(
        rule_id="rule_4",
        rule_name="ICD-CPT Crosswalk",
        description="Validate procedures support diagnoses",
        category="medical",
        priority="P0",
        is_llm_based=False,
        estimated_time_ms=100,
    ),
    ValidationRuleInfo(
        rule_id="rule_5",
        rule_name="Clinical Necessity",
        description="LLM-based medical necessity review",
        category="medical",
        priority="P1",
        is_llm_based=True,
        estimated_time_ms=5000,
    ),
    ValidationRuleInfo(
        rule_id="rule_6",
        rule_name="ICD×ICD Validation",
        description="Detect invalid diagnosis combinations",
        category="medical",
        priority="P0",
        is_llm_based=False,
        estimated_time_ms=50,
    ),
    ValidationRuleInfo(
        rule_id="rule_7",
        rule_name="Diagnosis Demographics",
        description="Age/gender validation for diagnoses",
        category="medical",
        priority="P0",
        is_llm_based=False,
        estimated_time_ms=20,
    ),
    ValidationRuleInfo(
        rule_id="rule_8",
        rule_name="Procedure Demographics",
        description="Age/gender validation for procedures",
        category="medical",
        priority="P0",
        is_llm_based=False,
        estimated_time_ms=20,
    ),
    ValidationRuleInfo(
        rule_id="rule_9",
        rule_name="Medical Reports",
        description="Validate supporting documentation",
        category="medical",
        priority="P1",
        is_llm_based=True,
        estimated_time_ms=3000,
    ),
    ValidationRuleInfo(
        rule_id="rule_10",
        rule_name="Rejection Reasons",
        description="Explain and validate rejection codes",
        category="medical",
        priority="P1",
        is_llm_based=False,
        estimated_time_ms=100,
    ),
    ValidationRuleInfo(
        rule_id="rule_11",
        rule_name="Policy/TOB Coverage",
        description="Validate against Table of Benefits",
        category="coverage",
        priority="P0",
        is_llm_based=False,
        estimated_time_ms=50,
    ),
    ValidationRuleInfo(
        rule_id="rule_12",
        rule_name="Network Coverage",
        description="Validate provider network status",
        category="coverage",
        priority="P1",
        is_llm_based=False,
        estimated_time_ms=100,
    ),
]
