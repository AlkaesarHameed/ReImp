"""
Pydantic Schemas for Tenant Management.
Source: Design Document 01_configurable_claims_processing_design.md
Verified: 2025-12-18
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, EmailStr

from src.core.enums import CodingStandard, NetworkType, TenantStatus


class TenantBase(BaseModel):
    """Base tenant schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    description: Optional[str] = Field(None, description="Organization description")
    coding_standard: CodingStandard = Field(
        default=CodingStandard.US,
        description="Medical coding standard (US or AU)",
    )
    default_network_type: NetworkType = Field(
        default=NetworkType.PPO,
        description="Default provider network type",
    )
    default_currency: str = Field(
        default="USD",
        max_length=3,
        description="Default currency code (ISO 4217)",
    )
    timezone: str = Field(default="UTC", max_length=50, description="Default timezone")
    contact_email: Optional[EmailStr] = Field(None, description="Primary contact email")
    contact_phone: Optional[str] = Field(
        None, max_length=50, description="Primary contact phone"
    )


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""

    slug: str = Field(
        ...,
        min_length=3,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="URL-safe identifier (lowercase, alphanumeric, hyphens only)",
    )
    billing_email: Optional[EmailStr] = Field(None, description="Billing contact email")


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    coding_standard: Optional[CodingStandard] = None
    default_network_type: Optional[NetworkType] = None
    default_currency: Optional[str] = Field(None, max_length=3)
    timezone: Optional[str] = Field(None, max_length=50)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=50)
    billing_email: Optional[EmailStr] = None
    provider_config: Optional[dict] = Field(
        None, description="Provider preferences (LLM, OCR, etc.)"
    )
    features_enabled: Optional[dict] = Field(
        None, description="Enabled features for this tenant"
    )


class TenantStatusUpdate(BaseModel):
    """Schema for updating tenant status."""

    status: TenantStatus
    reason: Optional[str] = Field(None, description="Reason for status change")


class TenantResponse(TenantBase):
    """Schema for tenant response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    status: TenantStatus
    is_active: bool
    provider_config: Optional[dict] = None
    features_enabled: Optional[dict] = None
    billing_email: Optional[EmailStr] = None
    database_name: Optional[str] = None
    monthly_claim_limit: Optional[int] = None
    monthly_claims_used: int
    activated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TenantListResponse(BaseModel):
    """Schema for listing tenants."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    status: TenantStatus
    coding_standard: CodingStandard
    default_currency: str
    monthly_claims_used: int
    created_at: datetime


class TenantSettingsBase(BaseModel):
    """Base tenant settings schema."""

    auto_adjudication_enabled: bool = Field(
        default=True, description="Enable automatic claim adjudication"
    )
    fwa_detection_enabled: bool = Field(
        default=True, description="Enable fraud/waste/abuse detection"
    )
    fwa_risk_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0, description="FWA risk threshold for manual review"
    )
    ocr_confidence_threshold: float = Field(
        default=0.90, ge=0.0, le=1.0, description="Minimum OCR confidence threshold"
    )
    llm_confidence_threshold: float = Field(
        default=0.85, ge=0.0, le=1.0, description="Minimum LLM confidence threshold"
    )
    notifications_enabled: bool = Field(
        default=True, description="Enable email/webhook notifications"
    )
    webhook_url: Optional[str] = Field(
        None, max_length=500, description="Webhook URL for status updates"
    )


class TenantSettingsUpdate(BaseModel):
    """Schema for updating tenant settings."""

    auto_adjudication_enabled: Optional[bool] = None
    fwa_detection_enabled: Optional[bool] = None
    fwa_risk_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    ocr_confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    llm_confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    notifications_enabled: Optional[bool] = None
    webhook_url: Optional[str] = Field(None, max_length=500)
    custom_rules_config: Optional[dict] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TenantSettingsResponse(TenantSettingsBase):
    """Schema for tenant settings response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    custom_rules_config: Optional[dict] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    created_at: datetime
    updated_at: datetime
