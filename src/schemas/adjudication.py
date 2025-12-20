"""
Pydantic Schemas for Claim Adjudication.
Source: Design Document Section 3.4 - Claim Adjudication Pipeline
Verified: 2025-12-18
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdjudicationDecision(str, Enum):
    """Final adjudication decision."""

    APPROVED = "approved"
    DENIED = "denied"
    PARTIAL = "partial"
    PENDING_REVIEW = "pending_review"
    PENDING_INFO = "pending_info"


class AdjudicationType(str, Enum):
    """Type of adjudication processing."""

    AUTO = "auto"  # Fully automated
    ASSISTED = "assisted"  # Auto with manual review
    MANUAL = "manual"  # Fully manual
    ESCALATED = "escalated"  # Escalated to supervisor


class DenialReason(str, Enum):
    """Standardized denial reason codes."""

    # Eligibility
    NOT_ELIGIBLE = "not_eligible"
    COVERAGE_TERMINATED = "coverage_terminated"
    NOT_COVERED_MEMBER = "not_covered_member"

    # Policy
    POLICY_INACTIVE = "policy_inactive"
    POLICY_EXPIRED = "policy_expired"
    BENEFIT_EXHAUSTED = "benefit_exhausted"

    # Coverage
    NOT_COVERED_SERVICE = "not_covered_service"
    EXCLUDED_PROCEDURE = "excluded_procedure"
    EXCLUDED_DIAGNOSIS = "excluded_diagnosis"
    COSMETIC_PROCEDURE = "cosmetic_procedure"
    EXPERIMENTAL = "experimental"

    # Authorization
    NO_PRIOR_AUTH = "no_prior_auth"
    PRIOR_AUTH_EXPIRED = "prior_auth_expired"
    PRIOR_AUTH_DENIED = "prior_auth_denied"

    # Network
    OUT_OF_NETWORK = "out_of_network"
    PROVIDER_NOT_ENROLLED = "provider_not_enrolled"

    # Medical Necessity
    NOT_MEDICALLY_NECESSARY = "not_medically_necessary"
    FREQUENCY_EXCEEDED = "frequency_exceeded"

    # Documentation
    MISSING_DOCUMENTATION = "missing_documentation"
    INVALID_DOCUMENTATION = "invalid_documentation"

    # Duplicate/Timing
    DUPLICATE_CLAIM = "duplicate_claim"
    TIMELY_FILING_EXCEEDED = "timely_filing_exceeded"

    # Other
    FWA_FLAGGED = "fwa_flagged"
    COORDINATION_OF_BENEFITS = "cob_primary_payer"
    OTHER = "other"


class ValidationStatus(str, Enum):
    """Status of a validation check."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


# =============================================================================
# Validation Result Schemas
# =============================================================================


class ValidationCheck(BaseModel):
    """Result of a single validation check."""

    check_name: str = Field(..., description="Name of the validation check")
    status: ValidationStatus = Field(..., description="Check result status")
    message: Optional[str] = Field(None, description="Status message")
    code: Optional[str] = Field(None, description="Validation code")
    details: dict = Field(default_factory=dict, description="Additional details")


class PolicyValidationResult(BaseModel):
    """Result of policy validation."""

    is_valid: bool = True
    policy_id: Optional[UUID] = None
    policy_status: Optional[str] = None

    # Policy checks
    policy_active: bool = True
    policy_effective: bool = True
    benefit_available: bool = True

    # Coverage checks
    service_covered: bool = True
    procedure_not_excluded: bool = True
    diagnosis_not_excluded: bool = True

    # Details
    checks: list[ValidationCheck] = Field(default_factory=list)
    denial_reason: Optional[DenialReason] = None
    denial_message: Optional[str] = None


class EligibilityValidationResult(BaseModel):
    """Result of member eligibility validation."""

    is_eligible: bool = True
    member_id: Optional[UUID] = None

    # Eligibility checks
    member_active: bool = True
    coverage_effective: bool = True
    within_waiting_period: bool = False

    # Benefit accumulator status
    deductible_remaining: Decimal = Decimal("0")
    oop_remaining: Decimal = Decimal("0")
    benefit_remaining: Decimal = Decimal("0")

    # Details
    checks: list[ValidationCheck] = Field(default_factory=list)
    denial_reason: Optional[DenialReason] = None
    denial_message: Optional[str] = None


class NetworkValidationResult(BaseModel):
    """Result of provider network validation."""

    is_valid: bool = True
    provider_id: Optional[UUID] = None

    # Network checks
    provider_enrolled: bool = True
    provider_in_network: bool = True
    provider_active: bool = True
    specialty_allowed: bool = True

    # Network details
    network_status: str = "in_network"  # in_network, out_of_network, non_participating
    network_tier: Optional[str] = None
    effective_date: Optional[date] = None

    # Details
    checks: list[ValidationCheck] = Field(default_factory=list)
    denial_reason: Optional[DenialReason] = None
    denial_message: Optional[str] = None


class PriorAuthValidationResult(BaseModel):
    """Result of prior authorization validation."""

    is_valid: bool = True
    auth_required: bool = False

    # Authorization details
    auth_number: Optional[str] = None
    auth_status: Optional[str] = None  # approved, denied, pending, expired
    auth_effective_date: Optional[date] = None
    auth_expiry_date: Optional[date] = None
    authorized_units: Optional[int] = None
    used_units: int = 0

    # Details
    checks: list[ValidationCheck] = Field(default_factory=list)
    denial_reason: Optional[DenialReason] = None
    denial_message: Optional[str] = None


class MedicalNecessityResult(BaseModel):
    """Result of medical necessity validation."""

    is_valid: bool = True

    # Medical necessity checks
    diagnosis_supports_procedure: bool = True
    frequency_within_limits: bool = True
    age_appropriate: bool = True
    gender_appropriate: bool = True

    # Medical coding
    icd10_valid: bool = True
    cpt_valid: bool = True
    code_combination_valid: bool = True

    # Details
    checks: list[ValidationCheck] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    denial_reason: Optional[DenialReason] = None
    denial_message: Optional[str] = None


class DuplicateCheckResult(BaseModel):
    """Result of duplicate claim check."""

    is_duplicate: bool = False
    possible_duplicate: bool = False

    # Duplicate details
    original_claim_id: Optional[UUID] = None
    original_tracking_number: Optional[str] = None
    similarity_score: float = 0.0

    # Match details
    matching_fields: list[str] = Field(default_factory=list)

    # Details
    checks: list[ValidationCheck] = Field(default_factory=list)


class TimelyFilingResult(BaseModel):
    """Result of timely filing check."""

    is_timely: bool = True

    # Filing details
    service_date: Optional[date] = None
    submission_date: Optional[date] = None
    days_elapsed: int = 0
    filing_limit_days: int = 365

    # Details
    checks: list[ValidationCheck] = Field(default_factory=list)
    denial_reason: Optional[DenialReason] = None


# =============================================================================
# Adjudication Schemas
# =============================================================================


class AdjudicationContext(BaseModel):
    """Context for claim adjudication."""

    claim_id: UUID
    tenant_id: UUID

    # Claim details
    claim_type: str
    service_date: date
    submission_date: datetime
    total_charged: Decimal

    # References
    policy_id: UUID
    member_id: UUID
    provider_id: UUID

    # Options
    skip_eligibility: bool = False
    skip_network: bool = False
    skip_prior_auth: bool = False
    skip_medical_necessity: bool = False
    skip_duplicate_check: bool = False
    skip_fwa_check: bool = False

    # Auto-adjudication settings
    auto_approve_threshold: Decimal = Decimal("5000.00")
    fwa_threshold: float = 0.6
    confidence_threshold: float = 0.8


class LineItemAdjudication(BaseModel):
    """Adjudication result for a single line item."""

    line_number: int
    procedure_code: str

    # Decision
    decision: AdjudicationDecision = AdjudicationDecision.APPROVED

    # Amounts
    charged_amount: Decimal
    allowed_amount: Decimal = Decimal("0")
    paid_amount: Decimal = Decimal("0")
    patient_responsibility: Decimal = Decimal("0")

    # Breakdown
    deductible_applied: Decimal = Decimal("0")
    copay_amount: Decimal = Decimal("0")
    coinsurance_amount: Decimal = Decimal("0")
    adjustment_amount: Decimal = Decimal("0")

    # Codes
    adjustment_codes: list[str] = Field(default_factory=list)
    remark_codes: list[str] = Field(default_factory=list)

    # Denial
    denial_reason: Optional[DenialReason] = None
    denial_message: Optional[str] = None


class AdjudicationResult(BaseModel):
    """Complete adjudication result for a claim."""

    claim_id: UUID
    adjudication_timestamp: datetime

    # Decision
    decision: AdjudicationDecision
    adjudication_type: AdjudicationType = AdjudicationType.AUTO

    # Line item results
    line_results: list[LineItemAdjudication] = Field(default_factory=list)

    # Totals
    total_charged: Decimal = Decimal("0")
    total_allowed: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")
    total_patient_responsibility: Decimal = Decimal("0")
    total_adjustment: Decimal = Decimal("0")

    # Breakdown
    total_deductible: Decimal = Decimal("0")
    total_copay: Decimal = Decimal("0")
    total_coinsurance: Decimal = Decimal("0")

    # Validation results
    policy_validation: Optional[PolicyValidationResult] = None
    eligibility_validation: Optional[EligibilityValidationResult] = None
    network_validation: Optional[NetworkValidationResult] = None
    prior_auth_validation: Optional[PriorAuthValidationResult] = None
    medical_necessity: Optional[MedicalNecessityResult] = None
    duplicate_check: Optional[DuplicateCheckResult] = None
    timely_filing: Optional[TimelyFilingResult] = None

    # FWA
    fwa_score: Optional[float] = None
    fwa_flags: list[str] = Field(default_factory=list)

    # Processing details
    processing_notes: list[str] = Field(default_factory=list)
    requires_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)

    # Denial (if applicable)
    primary_denial_reason: Optional[DenialReason] = None
    denial_codes: list[str] = Field(default_factory=list)

    # Timing
    processing_time_ms: int = 0

    def calculate_totals(self) -> None:
        """Calculate totals from line results."""
        self.total_charged = sum(r.charged_amount for r in self.line_results)
        self.total_allowed = sum(r.allowed_amount for r in self.line_results)
        self.total_paid = sum(r.paid_amount for r in self.line_results)
        self.total_patient_responsibility = sum(
            r.patient_responsibility for r in self.line_results
        )
        self.total_adjustment = sum(r.adjustment_amount for r in self.line_results)
        self.total_deductible = sum(r.deductible_applied for r in self.line_results)
        self.total_copay = sum(r.copay_amount for r in self.line_results)
        self.total_coinsurance = sum(r.coinsurance_amount for r in self.line_results)


# =============================================================================
# EOB (Explanation of Benefits) Schemas
# =============================================================================


class EOBLineItem(BaseModel):
    """Line item for EOB."""

    line_number: int
    service_date: date
    procedure_code: str
    procedure_description: Optional[str] = None

    # Provider
    provider_name: Optional[str] = None

    # Amounts
    charged_amount: Decimal
    allowed_amount: Decimal
    plan_paid: Decimal
    your_responsibility: Decimal

    # Breakdown
    deductible: Decimal = Decimal("0")
    copay: Decimal = Decimal("0")
    coinsurance: Decimal = Decimal("0")
    not_covered: Decimal = Decimal("0")

    # Status
    status: str = "processed"  # processed, denied, pending
    remark: Optional[str] = None


class EOBSummary(BaseModel):
    """Summary section of EOB."""

    # Amounts
    total_charges: Decimal
    total_allowed: Decimal
    plan_paid: Decimal
    your_responsibility: Decimal

    # Breakdown
    applied_to_deductible: Decimal = Decimal("0")
    copay_amount: Decimal = Decimal("0")
    coinsurance_amount: Decimal = Decimal("0")
    not_covered_amount: Decimal = Decimal("0")

    # Accumulator status
    deductible_status: str = ""  # e.g., "$750 of $1,500 met"
    oop_status: str = ""  # e.g., "$2,000 of $6,000 met"


class ExplanationOfBenefits(BaseModel):
    """Complete Explanation of Benefits document."""

    model_config = ConfigDict(from_attributes=True)

    # Identifiers
    eob_number: str
    claim_tracking_number: str
    claim_id: UUID

    # Dates
    generated_date: date
    service_date_from: date
    service_date_to: date
    payment_date: Optional[date] = None

    # Member info
    member_name: str
    member_id_display: str  # Masked member ID
    group_number: Optional[str] = None

    # Provider info
    provider_name: str
    provider_address: Optional[str] = None

    # Line items
    line_items: list[EOBLineItem] = Field(default_factory=list)

    # Summary
    summary: EOBSummary

    # Messages
    messages: list[str] = Field(default_factory=list)
    appeal_instructions: Optional[str] = None

    # Status
    claim_status: str = "processed"
