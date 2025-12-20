"""
Pydantic Schemas for Healthcare Provider Management.
Source: Design Document 01_configurable_claims_processing_design.md Section 11.4.2
Verified: 2025-12-18
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.core.enums import NetworkTier, ProviderNetworkStatus, ProviderType, Specialty


class ProviderBase(BaseModel):
    """Base provider schema with common fields."""

    npi: str = Field(
        ...,
        min_length=10,
        max_length=10,
        pattern=r"^\d{10}$",
        description="National Provider Identifier (10 digits)",
    )
    tax_id: str = Field(..., min_length=1, max_length=20, description="Tax ID")
    name: str = Field(..., min_length=1, max_length=255, description="Provider name")
    provider_type: ProviderType = Field(..., description="Type of provider")
    specialty: Optional[Specialty] = Field(None, description="Medical specialty")


class ProviderAddressBase(BaseModel):
    """Address fields for provider."""

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
    phone: str = Field(..., min_length=1, max_length=20, description="Phone number")
    fax: Optional[str] = Field(None, max_length=20, description="Fax number")
    email: Optional[EmailStr] = Field(None, description="Email address")


class ProviderCreate(ProviderBase, ProviderAddressBase):
    """Schema for creating a healthcare provider."""

    internal_id: Optional[str] = Field(
        None, max_length=50, description="Internal provider ID"
    )
    secondary_specialties: Optional[list[str]] = Field(
        None, description="Secondary specialties"
    )
    network_tier: NetworkTier = Field(
        default=NetworkTier.IN_NETWORK, description="Network tier"
    )
    effective_date: date = Field(..., description="Network effective date")
    termination_date: Optional[date] = Field(
        None, description="Network termination date"
    )
    license_number: str = Field(..., max_length=50, description="Medical license number")
    license_state: str = Field(..., max_length=2, description="State of licensure")
    license_expiry: date = Field(..., description="License expiration date")
    board_certified: bool = Field(default=False, description="Board certified status")
    board_certifications: Optional[list[str]] = Field(
        None, description="Board certifications"
    )
    dea_number: Optional[str] = Field(
        None, max_length=20, description="DEA registration number"
    )
    dea_expiry: Optional[date] = Field(None, description="DEA expiration date")
    contracted_rate_multiplier: Decimal = Field(
        default=Decimal("1.0"),
        ge=0,
        le=5,
        description="Rate multiplier (% of Medicare)",
    )
    accepts_assignment: bool = Field(
        default=True, description="Accepts insurance assignment"
    )
    service_codes: Optional[list[str]] = Field(
        None, description="Procedure codes this provider performs"
    )

    @field_validator("license_expiry")
    @classmethod
    def license_not_expired(cls, v: date) -> date:
        """Warn if license is expired."""
        # Note: We don't reject expired licenses, but may want to flag them
        return v


class ProviderUpdate(BaseModel):
    """Schema for updating a healthcare provider."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    provider_type: Optional[ProviderType] = None
    specialty: Optional[Specialty] = None
    secondary_specialties: Optional[list[str]] = None
    address_line1: Optional[str] = Field(None, min_length=1, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, min_length=1, max_length=50)
    zip_code: Optional[str] = Field(None, min_length=1, max_length=20)
    country: Optional[str] = Field(None, max_length=2)
    phone: Optional[str] = Field(None, min_length=1, max_length=20)
    fax: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    network_tier: Optional[NetworkTier] = None
    status: Optional[ProviderNetworkStatus] = None
    termination_date: Optional[date] = None
    license_number: Optional[str] = Field(None, max_length=50)
    license_state: Optional[str] = Field(None, max_length=2)
    license_expiry: Optional[date] = None
    board_certified: Optional[bool] = None
    board_certifications: Optional[list[str]] = None
    dea_number: Optional[str] = Field(None, max_length=20)
    dea_expiry: Optional[date] = None
    contracted_rate_multiplier: Optional[Decimal] = Field(None, ge=0, le=5)
    accepts_assignment: Optional[bool] = None
    is_excluded: Optional[bool] = None
    exclusion_date: Optional[date] = None
    exclusion_reason: Optional[str] = Field(None, max_length=255)
    service_codes: Optional[list[str]] = None
    notes: Optional[str] = None


class ProviderResponse(ProviderBase, ProviderAddressBase):
    """Schema for provider response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    internal_id: Optional[str] = None
    secondary_specialties: Optional[list[str]] = None
    network_tier: NetworkTier
    status: ProviderNetworkStatus
    effective_date: date
    termination_date: Optional[date] = None
    license_number: str
    license_state: str
    license_expiry: date
    board_certified: bool
    board_certifications: Optional[list[str]] = None
    dea_number: Optional[str] = None
    dea_expiry: Optional[date] = None
    contracted_rate_multiplier: Decimal
    accepts_assignment: bool
    is_excluded: bool
    exclusion_date: Optional[date] = None
    exclusion_reason: Optional[str] = None
    service_codes: Optional[list[str]] = None
    notes: Optional[str] = None
    additional_info: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    # Computed properties
    is_active_in_network: bool
    is_in_network: bool
    is_license_valid: bool


class ProviderListResponse(BaseModel):
    """Schema for listing providers."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    npi: str
    name: str
    provider_type: ProviderType
    specialty: Optional[Specialty] = None
    city: str
    state: str
    network_tier: NetworkTier
    status: ProviderNetworkStatus
    is_active_in_network: bool


class ProviderBulkUpload(BaseModel):
    """Schema for bulk provider upload."""

    npi: str
    tax_id: str
    name: str
    provider_type: str
    specialty: Optional[str] = None
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    network_tier: str = "in_network"
    license_number: str
    license_state: str


class NPIVerifyRequest(BaseModel):
    """Schema for NPI verification request."""

    npi: str = Field(
        ...,
        min_length=10,
        max_length=10,
        pattern=r"^\d{10}$",
        description="NPI to verify",
    )


class NPIVerifyResponse(BaseModel):
    """Schema for NPI verification response."""

    valid: bool
    npi: str
    name: Optional[str] = None
    provider_type: Optional[str] = None
    specialty: Optional[str] = None
    address: Optional[dict] = None
    enumeration_date: Optional[date] = None
    last_update: Optional[date] = None
