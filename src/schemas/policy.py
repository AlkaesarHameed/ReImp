"""
Pydantic Schemas for Policy Management.
Source: Design Document 01_configurable_claims_processing_design.md Section 11.4.1
Verified: 2025-12-18
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.enums import BenefitClass, CoverageType, NetworkType, PolicyStatus


class CoverageLimitBase(BaseModel):
    """Base schema for coverage limits."""

    coverage_type: CoverageType = Field(..., description="Type of coverage")
    annual_limit: Decimal = Field(..., gt=0, description="Annual limit for this coverage")
    per_visit_limit: Optional[Decimal] = Field(
        None, gt=0, description="Per-visit limit"
    )
    per_incident_limit: Optional[Decimal] = Field(
        None, gt=0, description="Per-incident limit"
    )
    copay_percentage: Decimal = Field(
        default=Decimal("0.20"),
        ge=0,
        le=1,
        description="Copay percentage (e.g., 0.20 = 20%)",
    )
    copay_fixed: Optional[Decimal] = Field(None, ge=0, description="Fixed copay amount")
    waiting_period_days: int = Field(default=0, ge=0, description="Waiting period in days")
    pre_authorization_required: bool = Field(
        default=False, description="Requires pre-authorization"
    )


class CoverageLimitCreate(CoverageLimitBase):
    """Schema for creating coverage limits."""

    pass


class CoverageLimitResponse(CoverageLimitBase):
    """Schema for coverage limit response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_id: UUID
    ytd_used: Decimal
    remaining_limit: Decimal


class PolicyBase(BaseModel):
    """Base policy schema with common fields."""

    policy_number: str = Field(
        ..., min_length=1, max_length=50, description="Policy number"
    )
    group_number: Optional[str] = Field(
        None, max_length=50, description="Group/employer number"
    )
    subscriber_id: str = Field(
        ..., min_length=1, max_length=50, description="Primary subscriber ID"
    )
    benefit_class: BenefitClass = Field(
        default=BenefitClass.SILVER, description="Benefit tier"
    )
    network_type: NetworkType = Field(
        default=NetworkType.PPO, description="Provider network type"
    )
    effective_date: date = Field(..., description="Policy effective date")
    expiry_date: date = Field(..., description="Policy expiration date")
    annual_limit: Decimal = Field(..., gt=0, description="Total annual coverage limit")
    deductible: Decimal = Field(
        default=Decimal("0"), ge=0, description="Annual deductible"
    )
    out_of_pocket_max: Decimal = Field(
        ..., gt=0, description="Maximum out-of-pocket expense"
    )
    in_network_coverage: Decimal = Field(
        default=Decimal("0.80"),
        ge=0,
        le=1,
        description="In-network coverage rate",
    )
    out_of_network_coverage: Decimal = Field(
        default=Decimal("0.60"),
        ge=0,
        le=1,
        description="Out-of-network coverage rate",
    )

    @field_validator("expiry_date")
    @classmethod
    def expiry_after_effective(cls, v: date, info) -> date:
        """Ensure expiry date is after effective date."""
        effective = info.data.get("effective_date")
        if effective and v <= effective:
            raise ValueError("Expiry date must be after effective date")
        return v


class PolicyCreate(PolicyBase):
    """Schema for creating a policy."""

    coverages: list[CoverageLimitCreate] = Field(
        default_factory=list, description="Coverage limits by type"
    )
    pre_existing_waiting_months: int = Field(
        default=12, ge=0, description="Pre-existing condition waiting period"
    )
    excluded_conditions: Optional[list[str]] = Field(
        None, description="Excluded condition codes"
    )
    excluded_procedures: Optional[list[str]] = Field(
        None, description="Excluded procedure codes"
    )


class PolicyUpdate(BaseModel):
    """Schema for updating a policy."""

    benefit_class: Optional[BenefitClass] = None
    status: Optional[PolicyStatus] = None
    network_type: Optional[NetworkType] = None
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    annual_limit: Optional[Decimal] = Field(None, gt=0)
    deductible: Optional[Decimal] = Field(None, ge=0)
    out_of_pocket_max: Optional[Decimal] = Field(None, gt=0)
    in_network_coverage: Optional[Decimal] = Field(None, ge=0, le=1)
    out_of_network_coverage: Optional[Decimal] = Field(None, ge=0, le=1)
    excluded_conditions: Optional[list[str]] = None
    excluded_procedures: Optional[list[str]] = None
    notes: Optional[str] = None


class PolicyResponse(PolicyBase):
    """Schema for policy response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    status: PolicyStatus
    pre_existing_waiting_months: int
    excluded_conditions: Optional[list[str]] = None
    excluded_procedures: Optional[list[str]] = None
    ytd_claims_paid: Decimal
    ytd_deductible_met: Decimal
    ytd_out_of_pocket: Decimal
    coverages: list[CoverageLimitResponse] = []
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Computed properties
    is_active: bool
    remaining_annual_limit: Decimal
    remaining_deductible: Decimal
    remaining_out_of_pocket: Decimal


class PolicyListResponse(BaseModel):
    """Schema for listing policies."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_number: str
    subscriber_id: str
    benefit_class: BenefitClass
    status: PolicyStatus
    effective_date: date
    expiry_date: date
    annual_limit: Decimal
    is_active: bool


class PolicyBulkUpload(BaseModel):
    """Schema for bulk policy upload from CSV/Excel."""

    policy_number: str
    member_id: str
    benefit_class: str
    effective_date: str  # YYYY-MM-DD
    expiry_date: str  # YYYY-MM-DD
    annual_limit: float
    deductible: float = 0
    out_of_pocket_max: float
    network_type: str = "ppo"


class PolicyUploadResult(BaseModel):
    """Schema for bulk upload result."""

    status: str = Field(..., description="success or error")
    records_processed: int
    records_created: int
    records_updated: int
    errors: list[dict] = Field(default_factory=list)
    warnings: list[dict] = Field(default_factory=list)
