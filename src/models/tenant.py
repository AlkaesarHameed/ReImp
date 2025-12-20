"""
Tenant Model for Multi-Tenancy Support.
Source: Design Document 01_configurable_claims_processing_design.md Section 3.5
Verified: 2025-12-18
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.enums import CodingStandard, NetworkType, TenantStatus
from src.models.base import Base, TimeStampedModel, UUIDModel

if TYPE_CHECKING:
    from src.models.claim import Claim
    from src.models.member import Member
    from src.models.policy import Policy
    from src.models.provider import HealthcareProvider


class Tenant(Base, UUIDModel, TimeStampedModel):
    """
    Tenant model for multi-tenant isolation.

    Each tenant represents an insurance company or organization
    with complete data isolation (database-per-tenant pattern).

    Evidence: HIPAA requires complete data isolation between covered entities
    Source: https://www.hhs.gov/hipaa/for-professionals/privacy/index.html
    Verified: 2025-12-18
    """

    __tablename__ = "tenants"

    # Basic Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Organization name",
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="URL-safe identifier (e.g., 'acme-insurance')",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Organization description",
    )

    # Status
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus),
        default=TenantStatus.PENDING,
        nullable=False,
        index=True,
        comment="Tenant account status",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Quick check for active status",
    )

    # Configuration
    coding_standard: Mapped[CodingStandard] = mapped_column(
        Enum(CodingStandard),
        default=CodingStandard.US,
        nullable=False,
        comment="Medical coding standard (US or AU)",
    )
    default_network_type: Mapped[NetworkType] = mapped_column(
        Enum(NetworkType),
        default=NetworkType.PPO,
        nullable=False,
        comment="Default provider network type",
    )
    default_currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
        comment="Default currency code (ISO 4217)",
    )
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        nullable=False,
        comment="Default timezone",
    )

    # Provider Preferences (which AI/ML providers to use)
    provider_config: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Provider preferences (LLM, OCR, etc.)",
    )

    # Feature Flags
    features_enabled: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Enabled features for this tenant",
    )

    # Contact Information
    contact_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Primary contact email",
    )
    contact_phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Primary contact phone",
    )

    # Billing Information
    billing_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Billing contact email",
    )

    # Database Configuration (for database-per-tenant)
    database_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        comment="Tenant-specific database name",
    )
    database_schema: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Schema name (if using schema-per-tenant)",
    )

    # Usage Metering
    monthly_claim_limit: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Maximum claims per month (null = unlimited)",
    )
    monthly_claims_used: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Claims processed this month",
    )

    # Audit Fields
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When tenant was activated",
    )
    suspended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When tenant was suspended",
    )

    # Relationships (will be populated as models are created)
    # claims: Mapped[list["Claim"]] = relationship(back_populates="tenant")
    # policies: Mapped[list["Policy"]] = relationship(back_populates="tenant")
    # providers: Mapped[list["HealthcareProvider"]] = relationship(back_populates="tenant")
    # members: Mapped[list["Member"]] = relationship(back_populates="tenant")

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name='{self.name}', slug='{self.slug}')>"

    @property
    def is_within_claim_limit(self) -> bool:
        """Check if tenant is within monthly claim limit."""
        if self.monthly_claim_limit is None:
            return True
        return self.monthly_claims_used < self.monthly_claim_limit

    def get_provider_preference(self, provider_type: str) -> Optional[str]:
        """
        Get preferred provider for a given type.

        Args:
            provider_type: Type of provider (llm, ocr, translation, etc.)

        Returns:
            Provider name or None if not configured
        """
        if self.provider_config is None:
            return None
        return self.provider_config.get(provider_type)


class TenantSettings(Base, UUIDModel, TimeStampedModel):
    """
    Extended settings for a tenant.

    Separates frequently-changed settings from core tenant data.
    """

    __tablename__ = "tenant_settings"

    # Foreign Key
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Associated tenant ID",
    )

    # Claim Processing Settings
    auto_adjudication_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Enable automatic claim adjudication",
    )
    fwa_detection_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Enable fraud/waste/abuse detection",
    )
    fwa_risk_threshold: Mapped[float] = mapped_column(
        default=0.6,
        nullable=False,
        comment="FWA risk threshold for manual review",
    )

    # Document Processing Settings
    ocr_confidence_threshold: Mapped[float] = mapped_column(
        default=0.90,
        nullable=False,
        comment="Minimum OCR confidence threshold",
    )
    llm_confidence_threshold: Mapped[float] = mapped_column(
        default=0.85,
        nullable=False,
        comment="Minimum LLM confidence threshold",
    )

    # Notification Settings
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Enable email/webhook notifications",
    )
    webhook_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Webhook URL for claim status updates",
    )

    # Custom Rules
    custom_rules_config: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Tenant-specific rule overrides",
    )

    # Branding
    logo_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Custom logo URL",
    )
    primary_color: Mapped[Optional[str]] = mapped_column(
        String(7),
        nullable=True,
        comment="Primary brand color (hex)",
    )

    def __repr__(self) -> str:
        return f"<TenantSettings(tenant_id={self.tenant_id})>"
