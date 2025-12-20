"""
Member Model for Insurance Member/Patient Management.
Source: Design Document 01_configurable_claims_processing_design.md Section 11.4.3
Verified: 2025-12-18
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.enums import Gender, MemberStatus, Relationship
from src.models.base import Base, TimeStampedModel, UUIDModel

if TYPE_CHECKING:
    from src.models.claim import Claim
    from src.models.policy import Policy
    from src.models.provider import HealthcareProvider
    from src.models.tenant import Tenant


class Member(Base, UUIDModel, TimeStampedModel):
    """
    Insurance member (patient) model.

    Represents individuals covered under an insurance policy,
    including the subscriber and their dependents.

    Evidence: Member data structure based on HIPAA standards
    Source: ASC X12N 834 - Benefit Enrollment and Maintenance
    Verified: 2025-12-18
    """

    __tablename__ = "members"

    # Multi-tenant Foreign Key
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owning tenant ID",
    )

    # Policy Foreign Key
    policy_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated policy ID",
    )

    # Member Identification
    member_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Unique member identifier",
    )
    subscriber_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Subscriber/primary member ID",
    )

    # Personal Information
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="First name",
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Last name",
    )
    middle_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Middle name",
    )
    date_of_birth: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date of birth",
    )
    gender: Mapped[Gender] = mapped_column(
        Enum(Gender),
        nullable=False,
        comment="Gender",
    )
    ssn_last_four: Mapped[Optional[str]] = mapped_column(
        String(4),
        nullable=True,
        comment="Last 4 digits of SSN (for verification)",
    )

    # Relationship to Subscriber
    relationship: Mapped[Relationship] = mapped_column(
        Enum(Relationship),
        default=Relationship.SELF,
        nullable=False,
        comment="Relationship to subscriber",
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
        comment="City",
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
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
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Primary phone number",
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Email address",
    )

    # Eligibility Status
    status: Mapped[MemberStatus] = mapped_column(
        Enum(MemberStatus),
        default=MemberStatus.ACTIVE,
        nullable=False,
        index=True,
        comment="Enrollment status",
    )
    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Coverage effective date",
    )
    termination_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Coverage termination date",
    )

    # Primary Care Physician (for HMO plans)
    pcp_provider_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("healthcare_providers.id", ondelete="SET NULL"),
        nullable=True,
        comment="Primary care physician ID",
    )

    # Special Flags
    requires_pre_auth: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Requires pre-authorization for all services",
    )
    has_secondary_insurance: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Has secondary insurance coverage",
    )
    secondary_insurance_info: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Secondary insurance details (if applicable)",
    )

    # Language Preferences
    preferred_language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False,
        comment="Preferred language code",
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes",
    )

    # Relationships
    # tenant: Mapped["Tenant"] = relationship(back_populates="members")
    # policy: Mapped["Policy"] = relationship(back_populates="members")
    # pcp: Mapped[Optional["HealthcareProvider"]] = relationship()
    # claims: Mapped[list["Claim"]] = relationship(back_populates="member")

    # Indexes
    __table_args__ = (
        Index("ix_members_tenant_member_id", "tenant_id", "member_id"),
        Index("ix_members_tenant_subscriber_id", "tenant_id", "subscriber_id"),
        Index("ix_members_tenant_last_name", "tenant_id", "last_name"),
        Index("ix_members_policy_status", "policy_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Member(id={self.id}, member_id='{self.member_id}', name='{self.full_name}')>"

    @property
    def full_name(self) -> str:
        """Get member's full name."""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int:
        """Calculate member's current age."""
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )

    @property
    def is_eligible(self) -> bool:
        """Check if member is currently eligible for coverage."""
        if self.status != MemberStatus.ACTIVE:
            return False
        today = date.today()
        if today < self.effective_date:
            return False
        if self.termination_date and today > self.termination_date:
            return False
        return True

    @property
    def is_subscriber(self) -> bool:
        """Check if member is the primary subscriber."""
        return self.relationship == Relationship.SELF

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
