"""
Fee Schedule Model for Procedure Pricing.
Source: Design Document Section 3.3 - Benefit Calculation Engine
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
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimeStampedModel, UUIDModel

if TYPE_CHECKING:
    from src.models.tenant import Tenant


class FeeSchedule(Base, UUIDModel, TimeStampedModel):
    """
    Fee schedule for procedure pricing.

    Contains allowed amounts for procedures based on
    contracts with providers/networks.

    Evidence: Fee schedule structure based on CMS Medicare Fee Schedule
    Source: https://www.cms.gov/Medicare/Medicare-Fee-for-Service-Payment/PhysicianFeeSched
    Verified: 2025-12-18
    """

    __tablename__ = "fee_schedules"

    # Multi-tenant Foreign Key
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owning tenant ID",
    )

    # Fee Schedule Identification
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Fee schedule name",
    )
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Fee schedule code",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Description",
    )

    # Effective Dates
    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Effective date",
    )
    expiry_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Expiry date",
    )

    # Settings
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Is default fee schedule for tenant",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Is active",
    )

    # Relationships
    entries: Mapped[list["FeeScheduleEntry"]] = relationship(
        back_populates="fee_schedule",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_fee_schedules_tenant_code", "tenant_id", "code", unique=True),
        Index("ix_fee_schedules_tenant_default", "tenant_id", "is_default"),
        Index("ix_fee_schedules_effective", "effective_date", "expiry_date"),
    )

    def __repr__(self) -> str:
        return f"<FeeSchedule(id={self.id}, code='{self.code}')>"

    @property
    def is_current(self) -> bool:
        """Check if fee schedule is currently effective."""
        today = date.today()
        if not self.is_active:
            return False
        if self.effective_date > today:
            return False
        if self.expiry_date and self.expiry_date < today:
            return False
        return True


class FeeScheduleEntry(Base, UUIDModel, TimeStampedModel):
    """
    Individual fee schedule entry for a procedure.

    Contains the allowed amount for a specific procedure code.
    """

    __tablename__ = "fee_schedule_entries"

    # Foreign Key
    fee_schedule_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("fee_schedules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated fee schedule ID",
    )

    # Procedure Information
    procedure_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Procedure code (CPT/HCPCS)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Procedure description",
    )

    # Pricing
    allowed_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Base allowed amount",
    )

    # Facility vs Non-Facility (for professional services)
    facility_allowed: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Facility allowed amount",
    )
    non_facility_allowed: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Non-facility allowed amount",
    )

    # Modifier Factors
    modifier_26_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("0.26"),
        nullable=False,
        comment="Professional component (modifier 26) factor",
    )
    modifier_tc_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("0.74"),
        nullable=False,
        comment="Technical component (modifier TC) factor",
    )
    modifier_50_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("1.50"),
        nullable=False,
        comment="Bilateral procedure (modifier 50) factor",
    )

    # Effective Dates (can override parent)
    effective_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Entry effective date (overrides parent if set)",
    )
    expiry_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Entry expiry date",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Is active",
    )

    # Relationship
    fee_schedule: Mapped["FeeSchedule"] = relationship(back_populates="entries")

    # Indexes
    __table_args__ = (
        Index(
            "ix_fee_schedule_entries_schedule_code",
            "fee_schedule_id",
            "procedure_code",
            unique=True,
        ),
        Index("ix_fee_schedule_entries_procedure", "procedure_code"),
    )

    def __repr__(self) -> str:
        return f"<FeeScheduleEntry(code='{self.procedure_code}', amount={self.allowed_amount})>"

    def get_allowed_amount(
        self,
        modifiers: Optional[list[str]] = None,
        is_facility: Optional[bool] = None,
    ) -> Decimal:
        """
        Get allowed amount with modifier adjustments.

        Args:
            modifiers: List of modifiers (e.g., ['26', 'LT'])
            is_facility: True for facility setting, False for non-facility

        Returns:
            Adjusted allowed amount
        """
        # Start with base amount or facility/non-facility
        if is_facility is True and self.facility_allowed:
            base = self.facility_allowed
        elif is_facility is False and self.non_facility_allowed:
            base = self.non_facility_allowed
        else:
            base = self.allowed_amount

        if not modifiers:
            return base

        factor = Decimal("1.0")

        for mod in modifiers:
            mod_upper = mod.upper()

            if mod_upper == "26":
                # Professional component only
                factor *= self.modifier_26_factor
            elif mod_upper == "TC":
                # Technical component only
                factor *= self.modifier_tc_factor
            elif mod_upper == "50":
                # Bilateral procedure
                factor *= self.modifier_50_factor
            elif mod_upper in ("LT", "RT"):
                # Left/Right - no pricing impact
                pass
            elif mod_upper in ("51",):
                # Multiple procedures - typically reduced
                factor *= Decimal("0.50")
            elif mod_upper in ("52",):
                # Reduced services
                factor *= Decimal("0.50")
            elif mod_upper in ("53",):
                # Discontinued procedure
                factor *= Decimal("0.50")
            elif mod_upper in ("59", "XE", "XS", "XP", "XU"):
                # Distinct/separate - no pricing impact
                pass

        return base * factor
