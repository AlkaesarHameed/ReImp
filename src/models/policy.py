"""
Policy Model for Insurance Policy Management.
Source: Design Document 01_configurable_claims_processing_design.md Section 11.4.1
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

from src.core.enums import BenefitClass, CoverageType, NetworkType, PolicyStatus
from src.models.base import Base, TimeStampedModel, UUIDModel

if TYPE_CHECKING:
    from src.models.claim import Claim
    from src.models.member import Member
    from src.models.tenant import Tenant


class Policy(Base, UUIDModel, TimeStampedModel):
    """
    Insurance policy model.

    Represents an insurance policy with coverage limits, benefits,
    and associated members.

    Evidence: Policy data structure based on industry standards
    Source: HIPAA Transaction Sets (ASC X12N 834/837)
    Verified: 2025-12-18
    """

    __tablename__ = "policies"

    # Multi-tenant Foreign Key
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owning tenant ID",
    )

    # Policy Identification
    policy_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Human-readable policy number",
    )
    group_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Group/employer number",
    )
    subscriber_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Primary subscriber ID",
    )

    # Policy Details
    benefit_class: Mapped[BenefitClass] = mapped_column(
        Enum(BenefitClass),
        default=BenefitClass.SILVER,
        nullable=False,
        index=True,
        comment="Benefit tier (bronze, silver, gold, etc.)",
    )
    status: Mapped[PolicyStatus] = mapped_column(
        Enum(PolicyStatus),
        default=PolicyStatus.ACTIVE,
        nullable=False,
        index=True,
        comment="Policy lifecycle status",
    )
    network_type: Mapped[NetworkType] = mapped_column(
        Enum(NetworkType),
        default=NetworkType.PPO,
        nullable=False,
        comment="Provider network type",
    )

    # Effective Dates
    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Policy effective date",
    )
    expiry_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Policy expiration date",
    )

    # Coverage Limits (using Numeric for precision)
    annual_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Total annual coverage limit",
    )
    deductible: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Annual deductible amount",
    )
    out_of_pocket_max: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Maximum out-of-pocket expense",
    )

    # Network Coverage Rates
    in_network_coverage: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("0.80"),
        nullable=False,
        comment="In-network coverage rate (e.g., 0.80 = 80%)",
    )
    out_of_network_coverage: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("0.60"),
        nullable=False,
        comment="Out-of-network coverage rate",
    )

    # Waiting Periods
    pre_existing_waiting_months: Mapped[int] = mapped_column(
        default=12,
        nullable=False,
        comment="Pre-existing condition waiting period (months)",
    )

    # Exclusions (stored as JSON arrays)
    excluded_conditions: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="List of excluded condition codes",
    )
    excluded_procedures: Mapped[Optional[list]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="List of excluded procedure codes",
    )

    # Year-to-Date Tracking (for benefit calculations)
    ytd_claims_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Year-to-date claims paid",
    )
    ytd_deductible_met: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Year-to-date deductible met",
    )
    ytd_out_of_pocket: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Year-to-date out-of-pocket spending",
    )

    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes",
    )

    # Relationships
    # tenant: Mapped["Tenant"] = relationship(back_populates="policies")
    coverages: Mapped[list["CoverageLimit"]] = relationship(
        back_populates="policy",
        cascade="all, delete-orphan",
    )
    # members: Mapped[list["Member"]] = relationship(back_populates="policy")
    # claims: Mapped[list["Claim"]] = relationship(back_populates="policy")

    # Indexes
    __table_args__ = (
        Index("ix_policies_tenant_policy_number", "tenant_id", "policy_number"),
        Index("ix_policies_tenant_status", "tenant_id", "status"),
        Index("ix_policies_effective_expiry", "effective_date", "expiry_date"),
    )

    def __repr__(self) -> str:
        return f"<Policy(id={self.id}, number='{self.policy_number}', class='{self.benefit_class}')>"

    @property
    def is_active(self) -> bool:
        """Check if policy is currently active."""
        if self.status != PolicyStatus.ACTIVE:
            return False
        today = date.today()
        return self.effective_date <= today <= self.expiry_date

    @property
    def remaining_annual_limit(self) -> Decimal:
        """Calculate remaining annual benefit limit."""
        return self.annual_limit - self.ytd_claims_paid

    @property
    def remaining_deductible(self) -> Decimal:
        """Calculate remaining deductible."""
        return max(Decimal("0"), self.deductible - self.ytd_deductible_met)

    @property
    def remaining_out_of_pocket(self) -> Decimal:
        """Calculate remaining out-of-pocket maximum."""
        return max(Decimal("0"), self.out_of_pocket_max - self.ytd_out_of_pocket)

    def is_procedure_excluded(self, procedure_code: str) -> bool:
        """Check if a procedure code is excluded."""
        if not self.excluded_procedures:
            return False
        return procedure_code in self.excluded_procedures

    def is_condition_excluded(self, diagnosis_code: str) -> bool:
        """Check if a diagnosis code is excluded."""
        if not self.excluded_conditions:
            return False
        return diagnosis_code in self.excluded_conditions


class CoverageLimit(Base, UUIDModel, TimeStampedModel):
    """
    Coverage limits per coverage type within a policy.

    Allows granular control over different types of coverage
    (inpatient, outpatient, dental, etc.).
    """

    __tablename__ = "coverage_limits"

    # Foreign Key
    policy_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated policy ID",
    )

    # Coverage Type
    coverage_type: Mapped[CoverageType] = mapped_column(
        Enum(CoverageType),
        nullable=False,
        comment="Type of coverage",
    )

    # Limits
    annual_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Annual limit for this coverage type",
    )
    per_visit_limit: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Per-visit limit (if applicable)",
    )
    per_incident_limit: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Per-incident limit (if applicable)",
    )

    # Cost Sharing
    copay_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("0.20"),
        nullable=False,
        comment="Copay percentage (e.g., 0.20 = 20%)",
    )
    copay_fixed: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Fixed copay amount (if applicable)",
    )

    # Waiting Period
    waiting_period_days: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Waiting period in days",
    )

    # Authorization Requirements
    pre_authorization_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Requires pre-authorization",
    )

    # Year-to-Date Usage
    ytd_used: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        nullable=False,
        comment="Year-to-date usage for this coverage type",
    )

    # Relationship
    policy: Mapped["Policy"] = relationship(back_populates="coverages")

    # Indexes
    __table_args__ = (
        Index("ix_coverage_limits_policy_type", "policy_id", "coverage_type"),
    )

    def __repr__(self) -> str:
        return f"<CoverageLimit(policy_id={self.policy_id}, type='{self.coverage_type}')>"

    @property
    def remaining_limit(self) -> Decimal:
        """Calculate remaining limit for this coverage type."""
        return self.annual_limit - self.ytd_used
