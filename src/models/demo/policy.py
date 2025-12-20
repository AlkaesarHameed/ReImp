"""
Demo Policy Model.
Source: Design Document Section 4.4 - Demo Mode
Verified: 2025-12-18

In-memory policy model for demo/testing.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class PolicyStatus(str, Enum):
    """Policy status values."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    PENDING = "pending"


class CoverageType(str, Enum):
    """Coverage type values."""

    INDIVIDUAL = "individual"
    FAMILY = "family"
    EMPLOYEE = "employee"
    EMPLOYEE_SPOUSE = "employee_spouse"
    EMPLOYEE_CHILDREN = "employee_children"
    EMPLOYEE_FAMILY = "employee_family"


class PlanType(str, Enum):
    """Plan type values."""

    HMO = "hmo"
    PPO = "ppo"
    EPO = "epo"
    POS = "pos"
    HDHP = "hdhp"
    INDEMNITY = "indemnity"


class DemoPolicy(BaseModel):
    """In-memory policy model for demo mode."""

    policy_id: str = Field(default_factory=lambda: f"POL-{uuid4().hex[:8].upper()}")
    policy_number: str = Field(default_factory=lambda: f"P{uuid4().hex[:10].upper()}")
    policy_name: str = "Default Policy"
    group_id: Optional[str] = None
    group_name: Optional[str] = None

    # Status
    status: PolicyStatus = PolicyStatus.ACTIVE

    # Dates
    effective_date: date = Field(default_factory=date.today)
    termination_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Coverage
    coverage_type: CoverageType = CoverageType.INDIVIDUAL
    plan_type: PlanType = PlanType.PPO
    plan_name: str = "Standard Health Plan"
    plan_code: str = "STD-001"

    # Financial limits
    deductible: Decimal = Decimal("500.00")
    deductible_met: Decimal = Decimal("0.00")
    oop_max: Decimal = Decimal("5000.00")
    oop_met: Decimal = Decimal("0.00")
    lifetime_max: Optional[Decimal] = None
    lifetime_used: Decimal = Decimal("0.00")

    # Coinsurance
    in_network_coinsurance: int = 80  # Payer pays 80%
    out_of_network_coinsurance: int = 60

    # Copays
    pcp_copay: Decimal = Decimal("20.00")
    specialist_copay: Decimal = Decimal("40.00")
    urgent_care_copay: Decimal = Decimal("50.00")
    er_copay: Decimal = Decimal("150.00")
    rx_copay_generic: Decimal = Decimal("10.00")
    rx_copay_brand: Decimal = Decimal("30.00")

    # Network
    network_id: str = "NET-001"
    network_name: str = "Standard Network"

    # Flags
    requires_prior_auth: bool = True
    requires_referral: bool = False

    # Additional metadata
    payer_id: Optional[str] = None
    payer_name: str = "Demo Insurance Co"
    metadata: dict = Field(default_factory=dict)

    # Property aliases for UI compatibility
    @property
    def out_of_pocket_max(self) -> Decimal:
        """Alias for oop_max."""
        return self.oop_max

    @property
    def out_of_pocket_met(self) -> Decimal:
        """Alias for oop_met."""
        return self.oop_met

    @property
    def coinsurance_percent(self) -> int:
        """Alias for in_network_coinsurance."""
        return self.in_network_coinsurance

    def is_active(self) -> bool:
        """Check if policy is active on current date."""
        today = date.today()
        if self.status != PolicyStatus.ACTIVE:
            return False
        if self.effective_date > today:
            return False
        if self.termination_date and self.termination_date < today:
            return False
        return True

    def is_active_on_date(self, check_date: date) -> bool:
        """Check if policy is active on a specific date."""
        if self.status != PolicyStatus.ACTIVE:
            return False
        if self.effective_date > check_date:
            return False
        if self.termination_date and self.termination_date < check_date:
            return False
        return True

    def remaining_deductible(self) -> Decimal:
        """Calculate remaining deductible."""
        return max(Decimal("0.00"), self.deductible - self.deductible_met)

    def remaining_oop(self) -> Decimal:
        """Calculate remaining out-of-pocket max."""
        return max(Decimal("0.00"), self.oop_max - self.oop_met)

    def apply_deductible(self, amount: Decimal) -> Decimal:
        """Apply amount to deductible, return amount applied."""
        remaining = self.remaining_deductible()
        applied = min(amount, remaining)
        self.deductible_met += applied
        self.updated_at = datetime.utcnow()
        return applied

    def apply_oop(self, amount: Decimal) -> Decimal:
        """Apply amount to OOP, return amount applied."""
        remaining = self.remaining_oop()
        applied = min(amount, remaining)
        self.oop_met += applied
        self.updated_at = datetime.utcnow()
        return applied

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "policy_id": self.policy_id,
            "policy_number": self.policy_number,
            "group_id": self.group_id,
            "group_name": self.group_name,
            "status": self.status.value,
            "effective_date": self.effective_date.isoformat(),
            "termination_date": self.termination_date.isoformat() if self.termination_date else None,
            "coverage_type": self.coverage_type.value,
            "plan_name": self.plan_name,
            "plan_code": self.plan_code,
            "deductible": float(self.deductible),
            "deductible_met": float(self.deductible_met),
            "oop_max": float(self.oop_max),
            "oop_met": float(self.oop_met),
            "in_network_coinsurance": self.in_network_coinsurance,
            "out_of_network_coinsurance": self.out_of_network_coinsurance,
            "network_id": self.network_id,
            "network_name": self.network_name,
            "payer_name": self.payer_name,
            "is_active": self.is_active(),
        }
