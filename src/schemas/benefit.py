"""
Pydantic Schemas for Benefit Calculation.
Source: Design Document Section 3.3 - Benefit Calculation Engine
Verified: 2025-12-18
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdjustmentCategory(str, Enum):
    """Categories of claim adjustments."""

    CONTRACTUAL = "contractual"  # Fee schedule adjustment
    DEDUCTIBLE = "deductible"  # Applied to deductible
    COPAY = "copay"  # Fixed copay
    COINSURANCE = "coinsurance"  # Percentage coinsurance
    NON_COVERED = "non_covered"  # Not covered by plan
    EXCEEDED_LIMIT = "exceeded_limit"  # Exceeded benefit limit
    BUNDLED = "bundled"  # Bundled into another code
    DUPLICATE = "duplicate"  # Duplicate charge
    NOT_MEDICALLY_NECESSARY = "not_medically_necessary"  # Medical necessity
    PRIOR_AUTH_REQUIRED = "prior_auth_required"  # Missing prior auth


class BenefitDecision(str, Enum):
    """Decision outcome for a line item."""

    PAY = "pay"  # Pay full allowed amount
    PAY_PARTIAL = "pay_partial"  # Pay partial amount
    DENY = "deny"  # Deny line item
    PEND = "pend"  # Requires review


# =============================================================================
# Fee Schedule Schemas
# =============================================================================


class FeeScheduleEntryBase(BaseModel):
    """Base schema for fee schedule entry."""

    procedure_code: str = Field(..., description="CPT/HCPCS procedure code")
    description: Optional[str] = Field(None, description="Procedure description")
    allowed_amount: Decimal = Field(..., ge=0, description="Allowed amount")
    effective_date: date = Field(..., description="Effective date")
    expiry_date: Optional[date] = Field(None, description="Expiry date")

    # Modifiers affect pricing
    modifier_1_factor: Decimal = Field(default=Decimal("1.0"), description="Modifier 1 factor")
    modifier_2_factor: Decimal = Field(default=Decimal("1.0"), description="Modifier 2 factor")

    # Place of service adjustments
    facility_allowed: Optional[Decimal] = Field(None, description="Facility allowed amount")
    non_facility_allowed: Optional[Decimal] = Field(None, description="Non-facility allowed amount")


class FeeScheduleEntryCreate(FeeScheduleEntryBase):
    """Schema for creating fee schedule entry."""

    pass


class FeeScheduleEntryResponse(FeeScheduleEntryBase):
    """Schema for fee schedule entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    fee_schedule_id: UUID
    created_at: datetime
    updated_at: datetime


class FeeScheduleBase(BaseModel):
    """Base schema for fee schedule."""

    name: str = Field(..., min_length=1, max_length=100, description="Fee schedule name")
    code: str = Field(..., min_length=1, max_length=50, description="Fee schedule code")
    description: Optional[str] = Field(None, description="Description")
    effective_date: date = Field(..., description="Effective date")
    expiry_date: Optional[date] = Field(None, description="Expiry date")
    is_default: bool = Field(default=False, description="Is default fee schedule")


class FeeScheduleCreate(FeeScheduleBase):
    """Schema for creating fee schedule."""

    entries: list[FeeScheduleEntryCreate] = Field(
        default_factory=list,
        description="Fee schedule entries"
    )


class FeeScheduleResponse(FeeScheduleBase):
    """Schema for fee schedule response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    entry_count: int = 0
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Benefit Lookup Schemas
# =============================================================================


class MemberEligibility(BaseModel):
    """Member eligibility information."""

    member_id: UUID
    policy_id: UUID
    is_eligible: bool = True
    eligibility_start: date
    eligibility_end: Optional[date] = None

    # Policy details
    policy_status: str
    benefit_class: str
    network_type: str

    # Coverage info
    in_network_rate: Decimal
    out_of_network_rate: Decimal

    # Deductible tracking
    annual_deductible: Decimal
    deductible_met: Decimal
    remaining_deductible: Decimal

    # Out-of-pocket tracking
    out_of_pocket_max: Decimal
    out_of_pocket_met: Decimal
    remaining_out_of_pocket: Decimal

    # Annual limit
    annual_limit: Decimal
    limit_used: Decimal
    remaining_limit: Decimal

    # Pre-existing conditions
    pre_existing_waiting_ends: Optional[date] = None

    # Exclusions
    excluded_procedures: list[str] = Field(default_factory=list)
    excluded_conditions: list[str] = Field(default_factory=list)


class CoverageLookup(BaseModel):
    """Coverage lookup result for a service type."""

    coverage_type: str
    is_covered: bool = True
    requires_prior_auth: bool = False

    # Limits
    annual_limit: Decimal
    per_visit_limit: Optional[Decimal] = None
    per_incident_limit: Optional[Decimal] = None
    remaining_limit: Decimal

    # Cost sharing
    copay_fixed: Optional[Decimal] = None
    copay_percentage: Decimal = Decimal("0.20")

    # Waiting period
    waiting_period_days: int = 0
    waiting_period_met: bool = True


class FeeScheduleLookup(BaseModel):
    """Fee schedule lookup result."""

    procedure_code: str
    found: bool = True

    allowed_amount: Decimal = Decimal("0")
    facility_amount: Optional[Decimal] = None
    non_facility_amount: Optional[Decimal] = None

    # Modifier adjustments
    modifier_factor: Decimal = Decimal("1.0")
    adjusted_amount: Decimal = Decimal("0")

    fee_schedule_name: str = ""
    fee_schedule_id: Optional[UUID] = None


# =============================================================================
# Benefit Calculation Schemas
# =============================================================================


class Adjustment(BaseModel):
    """Individual adjustment applied to a line item."""

    category: AdjustmentCategory
    amount: Decimal = Field(..., ge=0, description="Adjustment amount")
    code: Optional[str] = Field(None, description="Adjustment reason code")
    description: Optional[str] = Field(None, description="Human-readable description")


class LineItemBenefitResult(BaseModel):
    """Benefit calculation result for a single line item."""

    line_number: int
    procedure_code: str

    # Input amounts
    charged_amount: Decimal
    quantity: int = 1

    # Fee schedule
    fee_schedule_amount: Decimal

    # Calculation steps
    allowed_amount: Decimal

    # Patient responsibility breakdown
    deductible_applied: Decimal = Decimal("0")
    copay_amount: Decimal = Decimal("0")
    coinsurance_amount: Decimal = Decimal("0")
    non_covered_amount: Decimal = Decimal("0")

    # Final amounts
    benefit_paid: Decimal = Decimal("0")
    patient_responsibility: Decimal = Decimal("0")

    # Adjustments applied
    adjustments: list[Adjustment] = Field(default_factory=list)

    # Decision
    decision: BenefitDecision = BenefitDecision.PAY
    denial_reason: Optional[str] = None

    # Codes
    adjustment_codes: list[str] = Field(default_factory=list)
    remark_codes: list[str] = Field(default_factory=list)

    def add_adjustment(
        self,
        category: AdjustmentCategory,
        amount: Decimal,
        code: Optional[str] = None,
        description: Optional[str] = None
    ) -> None:
        """Add an adjustment to this line item."""
        self.adjustments.append(Adjustment(
            category=category,
            amount=amount,
            code=code,
            description=description,
        ))
        if code:
            self.adjustment_codes.append(code)


class ClaimBenefitResult(BaseModel):
    """Complete benefit calculation result for a claim."""

    claim_id: UUID
    calculation_timestamp: datetime

    # Line item results
    line_results: list[LineItemBenefitResult] = Field(default_factory=list)

    # Totals
    total_charged: Decimal = Decimal("0")
    total_allowed: Decimal = Decimal("0")
    total_benefit_paid: Decimal = Decimal("0")
    total_patient_responsibility: Decimal = Decimal("0")

    # Breakdown
    total_deductible_applied: Decimal = Decimal("0")
    total_copay: Decimal = Decimal("0")
    total_coinsurance: Decimal = Decimal("0")
    total_non_covered: Decimal = Decimal("0")
    total_contractual_adjustment: Decimal = Decimal("0")

    # Updated accumulator values
    new_deductible_met: Decimal = Decimal("0")
    new_out_of_pocket_met: Decimal = Decimal("0")
    new_annual_limit_used: Decimal = Decimal("0")

    # Decision
    all_lines_approved: bool = True
    has_denied_lines: bool = False
    requires_review: bool = False

    # Rules applied
    rules_applied: list[str] = Field(default_factory=list)

    # Processing info
    calculation_time_ms: int = 0
    fee_schedule_used: Optional[str] = None

    def calculate_totals(self) -> None:
        """Calculate totals from line results."""
        self.total_charged = sum(r.charged_amount for r in self.line_results)
        self.total_allowed = sum(r.allowed_amount for r in self.line_results)
        self.total_benefit_paid = sum(r.benefit_paid for r in self.line_results)
        self.total_patient_responsibility = sum(r.patient_responsibility for r in self.line_results)

        self.total_deductible_applied = sum(r.deductible_applied for r in self.line_results)
        self.total_copay = sum(r.copay_amount for r in self.line_results)
        self.total_coinsurance = sum(r.coinsurance_amount for r in self.line_results)
        self.total_non_covered = sum(r.non_covered_amount for r in self.line_results)

        # Contractual adjustment = charged - allowed
        self.total_contractual_adjustment = self.total_charged - self.total_allowed

        # Check for denied lines
        self.has_denied_lines = any(
            r.decision == BenefitDecision.DENY for r in self.line_results
        )
        self.all_lines_approved = not self.has_denied_lines
        self.requires_review = any(
            r.decision == BenefitDecision.PEND for r in self.line_results
        )


# =============================================================================
# Calculation Context
# =============================================================================


class BenefitCalculationContext(BaseModel):
    """Context for benefit calculation."""

    claim_id: UUID
    tenant_id: UUID

    # Policy info
    policy_id: UUID
    member_id: UUID
    provider_id: UUID

    # Service details
    service_date: date
    place_of_service: Optional[str] = None
    is_in_network: bool = True

    # Eligibility (pre-populated)
    eligibility: Optional[MemberEligibility] = None

    # Fee schedule to use
    fee_schedule_id: Optional[UUID] = None

    # Options
    apply_deductible: bool = True
    apply_coinsurance: bool = True
    apply_copay: bool = True
    check_limits: bool = True
    check_exclusions: bool = True

    # Running accumulators (updated during calculation)
    running_deductible_applied: Decimal = Decimal("0")
    running_out_of_pocket: Decimal = Decimal("0")
    running_benefit_used: Decimal = Decimal("0")


class LineItemInput(BaseModel):
    """Input for a single line item benefit calculation."""

    line_number: int
    procedure_code: str
    modifiers: list[str] = Field(default_factory=list)

    charged_amount: Decimal
    quantity: int = 1
    unit_type: str = "UN"

    service_date: date
    diagnosis_codes: list[str] = Field(default_factory=list)

    # Optional override for allowed amount
    override_allowed_amount: Optional[Decimal] = None
