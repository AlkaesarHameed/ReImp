"""
Healthcare Provider Model for Provider Network Management.
Source: Design Document 01_configurable_claims_processing_design.md Section 11.4.2
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
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.enums import NetworkTier, ProviderNetworkStatus, ProviderType, Specialty
from src.models.base import Base, TimeStampedModel, UUIDModel

if TYPE_CHECKING:
    from src.models.claim import Claim
    from src.models.tenant import Tenant


class HealthcareProvider(Base, UUIDModel, TimeStampedModel):
    """
    Healthcare provider model.

    Represents healthcare providers (physicians, hospitals, clinics)
    in the provider network.

    Evidence: Provider data based on CMS NPI standards
    Source: https://npiregistry.cms.hhs.gov/
    Verified: 2025-12-18
    """

    __tablename__ = "healthcare_providers"

    # Multi-tenant Foreign Key
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owning tenant ID",
    )

    # Provider Identification
    npi: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="National Provider Identifier (10 digits)",
    )
    tax_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Tax Identification Number",
    )
    internal_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Internal provider ID",
    )

    # Provider Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Provider name (individual or organization)",
    )
    provider_type: Mapped[ProviderType] = mapped_column(
        Enum(ProviderType),
        nullable=False,
        index=True,
        comment="Type of provider",
    )
    specialty: Mapped[Optional[Specialty]] = mapped_column(
        Enum(Specialty),
        nullable=True,
        index=True,
        comment="Medical specialty",
    )
    secondary_specialties: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Secondary specialties",
    )

    # Contact Information
    address_line1: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Street address line 1",
    )
    address_line2: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Street address line 2",
    )
    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="City",
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="State/Province",
    )
    zip_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Postal/ZIP code",
    )
    country: Mapped[str] = mapped_column(
        String(2),
        default="US",
        nullable=False,
        comment="Country code (ISO 3166-1 alpha-2)",
    )
    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Primary phone number",
    )
    fax: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Fax number",
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Email address",
    )

    # Network Status
    network_tier: Mapped[NetworkTier] = mapped_column(
        Enum(NetworkTier),
        default=NetworkTier.IN_NETWORK,
        nullable=False,
        index=True,
        comment="Network tier",
    )
    status: Mapped[ProviderNetworkStatus] = mapped_column(
        Enum(ProviderNetworkStatus),
        default=ProviderNetworkStatus.ACTIVE,
        nullable=False,
        index=True,
        comment="Network participation status",
    )
    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Network effective date",
    )
    termination_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Network termination date",
    )

    # Credentials
    license_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Medical license number",
    )
    license_state: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        comment="State of licensure",
    )
    license_expiry: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="License expiration date",
    )
    board_certified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Board certified status",
    )
    board_certifications: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="List of board certifications",
    )

    # DEA Information (for prescribers)
    dea_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="DEA registration number",
    )
    dea_expiry: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="DEA expiration date",
    )

    # Contract Details
    contracted_rate_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("1.0"),
        nullable=False,
        comment="Rate multiplier (% of Medicare)",
    )
    accepts_assignment: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Accepts insurance assignment",
    )

    # Exclusion Status
    is_excluded: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Excluded from federal programs (OIG/SAM)",
    )
    exclusion_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date of exclusion",
    )
    exclusion_reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Reason for exclusion",
    )

    # Service Capabilities
    service_codes: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Procedure codes this provider performs",
    )

    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes",
    )
    additional_info: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional provider information",
    )

    # Relationships
    # tenant: Mapped["Tenant"] = relationship(back_populates="providers")
    # claims: Mapped[list["Claim"]] = relationship(back_populates="provider")

    # Indexes
    __table_args__ = (
        Index("ix_providers_tenant_npi", "tenant_id", "npi"),
        Index("ix_providers_tenant_name", "tenant_id", "name"),
        Index("ix_providers_tenant_specialty", "tenant_id", "specialty"),
        Index("ix_providers_tenant_city_state", "tenant_id", "city", "state"),
        Index("ix_providers_network_status", "network_tier", "status"),
    )

    def __repr__(self) -> str:
        return f"<HealthcareProvider(id={self.id}, npi='{self.npi}', name='{self.name}')>"

    @property
    def is_active_in_network(self) -> bool:
        """Check if provider is currently active in network."""
        if self.status != ProviderNetworkStatus.ACTIVE:
            return False
        if self.is_excluded:
            return False
        today = date.today()
        if today < self.effective_date:
            return False
        if self.termination_date and today > self.termination_date:
            return False
        return True

    @property
    def is_in_network(self) -> bool:
        """Check if provider is in-network (not out-of-network)."""
        return self.network_tier in (NetworkTier.PREFERRED, NetworkTier.IN_NETWORK)

    @property
    def is_license_valid(self) -> bool:
        """Check if medical license is currently valid."""
        return date.today() < self.license_expiry

    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        lines = [self.address_line1]
        if self.address_line2:
            lines.append(self.address_line2)
        lines.append(f"{self.city}, {self.state} {self.zip_code}")
        if self.country != "US":
            lines.append(self.country)
        return "\n".join(lines)

    def can_perform_procedure(self, procedure_code: str) -> bool:
        """Check if provider can perform a specific procedure."""
        if not self.service_codes:
            return True  # No restrictions
        return procedure_code in self.service_codes
