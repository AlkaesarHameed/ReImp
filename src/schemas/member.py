"""
Pydantic Schemas for Member/Patient Management.
Source: Design Document 01_configurable_claims_processing_design.md Section 11.4.3
Verified: 2025-12-18
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.core.enums import Gender, MemberStatus, Relationship


class MemberBase(BaseModel):
    """Base member schema with common fields."""

    member_id: str = Field(
        ..., min_length=1, max_length=50, description="Unique member identifier"
    )
    subscriber_id: str = Field(
        ..., min_length=1, max_length=50, description="Subscriber/primary member ID"
    )
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    middle_name: Optional[str] = Field(None, max_length=100, description="Middle name")
    date_of_birth: date = Field(..., description="Date of birth")
    gender: Gender = Field(..., description="Gender")
    relationship: Relationship = Field(
        default=Relationship.SELF, description="Relationship to subscriber"
    )

    @field_validator("date_of_birth")
    @classmethod
    def dob_not_future(cls, v: date) -> date:
        """Ensure date of birth is not in the future."""
        if v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return v


class MemberAddressBase(BaseModel):
    """Address fields for member."""

    address_line1: str = Field(
        ..., min_length=1, max_length=255, description="Street address line 1"
    )
    address_line2: Optional[str] = Field(
        None, max_length=255, description="Street address line 2"
    )
    city: str = Field(..., min_length=1, max_length=100, description="City")
    state: str = Field(..., min_length=1, max_length=50, description="State/Province")
    zip_code: str = Field(..., min_length=1, max_length=20, description="Postal/ZIP code")
    country: str = Field(default="US", max_length=2, description="Country code")


class MemberCreate(MemberBase, MemberAddressBase):
    """Schema for creating a member."""

    policy_id: UUID = Field(..., description="Associated policy ID")
    ssn_last_four: Optional[str] = Field(
        None, min_length=4, max_length=4, pattern=r"^\d{4}$", description="Last 4 of SSN"
    )
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    effective_date: date = Field(..., description="Coverage effective date")
    termination_date: Optional[date] = Field(
        None, description="Coverage termination date"
    )
    pcp_provider_id: Optional[UUID] = Field(
        None, description="Primary care physician ID"
    )
    requires_pre_auth: bool = Field(
        default=False, description="Requires pre-authorization for all services"
    )
    has_secondary_insurance: bool = Field(
        default=False, description="Has secondary insurance"
    )
    secondary_insurance_info: Optional[dict] = Field(
        None, description="Secondary insurance details"
    )
    preferred_language: str = Field(default="en", description="Preferred language code")

    @field_validator("termination_date")
    @classmethod
    def termination_after_effective(cls, v: Optional[date], info) -> Optional[date]:
        """Ensure termination date is after effective date."""
        if v is None:
            return v
        effective = info.data.get("effective_date")
        if effective and v < effective:
            raise ValueError("Termination date must be on or after effective date")
        return v


class MemberUpdate(BaseModel):
    """Schema for updating a member."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    gender: Optional[Gender] = None
    address_line1: Optional[str] = Field(None, min_length=1, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, min_length=1, max_length=50)
    zip_code: Optional[str] = Field(None, min_length=1, max_length=20)
    country: Optional[str] = Field(None, max_length=2)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    status: Optional[MemberStatus] = None
    termination_date: Optional[date] = None
    pcp_provider_id: Optional[UUID] = None
    requires_pre_auth: Optional[bool] = None
    has_secondary_insurance: Optional[bool] = None
    secondary_insurance_info: Optional[dict] = None
    preferred_language: Optional[str] = None
    notes: Optional[str] = None


class MemberResponse(MemberBase, MemberAddressBase):
    """Schema for member response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    policy_id: UUID
    ssn_last_four: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    status: MemberStatus
    effective_date: date
    termination_date: Optional[date] = None
    pcp_provider_id: Optional[UUID] = None
    requires_pre_auth: bool
    has_secondary_insurance: bool
    secondary_insurance_info: Optional[dict] = None
    preferred_language: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Computed properties
    full_name: str
    age: int
    is_eligible: bool
    is_subscriber: bool


class MemberListResponse(BaseModel):
    """Schema for listing members."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: str
    subscriber_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    relationship: Relationship
    status: MemberStatus
    is_eligible: bool


class MemberBulkUpload(BaseModel):
    """Schema for bulk member upload."""

    member_id: str
    subscriber_id: str
    first_name: str
    last_name: str
    date_of_birth: str  # YYYY-MM-DD
    gender: str
    relationship: str = "self"
    address: str
    city: str
    state: str
    zip_code: str
    policy_id: str
    effective_date: str


class EligibilityCheckRequest(BaseModel):
    """Schema for eligibility check request."""

    member_id: str = Field(..., description="Member ID to check")
    service_date: date = Field(..., description="Date of service")
    procedure_codes: Optional[list[str]] = Field(
        None, description="Procedure codes to verify coverage"
    )


class EligibilityCheckResponse(BaseModel):
    """Schema for eligibility check response."""

    member_id: str
    is_eligible: bool
    eligibility_date: date
    policy_status: str
    benefit_class: str
    coverage_active: bool
    messages: list[str] = Field(default_factory=list)

    # Coverage summary
    remaining_deductible: float
    remaining_out_of_pocket: float
    remaining_annual_limit: float

    # Procedure-specific (if requested)
    procedure_coverage: Optional[list[dict]] = None
