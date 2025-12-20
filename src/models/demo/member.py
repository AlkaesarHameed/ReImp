"""
Demo Member Model.
Source: Design Document Section 4.4 - Demo Mode
Verified: 2025-12-18

In-memory member model for demo/testing.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MemberStatus(str, Enum):
    """Member status values."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    PENDING = "pending"


class Gender(str, Enum):
    """Gender values."""

    MALE = "M"
    FEMALE = "F"
    OTHER = "O"
    UNKNOWN = "U"


class RelationshipCode(str, Enum):
    """Relationship to subscriber."""

    SELF = "self"
    SPOUSE = "spouse"
    CHILD = "child"
    OTHER = "other"


class RelationshipType(str, Enum):
    """Extended relationship type values."""

    SELF = "self"
    SPOUSE = "spouse"
    CHILD = "child"
    DEPENDENT = "dependent"
    PARENT = "parent"
    DOMESTIC_PARTNER = "domestic_partner"
    OTHER = "other"


class DemoMember(BaseModel):
    """In-memory member model for demo mode."""

    member_id: str = Field(default_factory=lambda: f"MEM-{uuid4().hex[:8].upper()}")
    subscriber_id: Optional[str] = None  # If dependent, links to subscriber

    # Personal info
    first_name: str = "John"
    last_name: str = "Doe"
    middle_name: Optional[str] = None
    date_of_birth: date = Field(default_factory=lambda: date(1985, 1, 15))
    gender: Gender = Gender.MALE
    ssn_last_four: Optional[str] = None

    # Status
    status: MemberStatus = MemberStatus.ACTIVE
    relationship: RelationshipCode = RelationshipCode.SELF

    # Address
    address_line1: str = "456 Member Lane"
    address_line2: Optional[str] = None
    city: str = "Patient City"
    state: str = "CA"
    zip_code: str = "90211"
    country: str = "US"

    # Contact
    phone: str = "(555) 987-6543"
    email: Optional[str] = None

    # Policy info
    policy_id: str = "POL-DEFAULT"
    group_id: Optional[str] = None

    # Dates
    effective_date: date = Field(default_factory=date.today)
    termination_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # PCP assignment
    pcp_provider_id: Optional[str] = None
    pcp_name: Optional[str] = None

    # Additional metadata
    metadata: dict = Field(default_factory=dict)
    is_eligible: bool = True  # Eligibility flag for UI

    # Property aliases for UI compatibility
    @property
    def ssn_last4(self) -> Optional[str]:
        """Alias for ssn_last_four."""
        return self.ssn_last_four

    @property
    def address(self) -> str:
        """Alias for address_line1."""
        return self.address_line1

    def age(self) -> int:
        """Alias for get_age."""
        return self.get_age()

    def get_age(self) -> int:
        """Calculate member age."""
        today = date.today()
        age = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1
        return age

    def is_active(self) -> bool:
        """Check if member is active."""
        if self.status != MemberStatus.ACTIVE:
            return False
        today = date.today()
        if self.effective_date > today:
            return False
        if self.termination_date and self.termination_date < today:
            return False
        return True

    def is_active_on_date(self, check_date: date) -> bool:
        """Check if member is active on a specific date."""
        if self.status != MemberStatus.ACTIVE:
            return False
        if self.effective_date > check_date:
            return False
        if self.termination_date and self.termination_date < check_date:
            return False
        return True

    def get_full_name(self) -> str:
        """Get member full name."""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "member_id": self.member_id,
            "subscriber_id": self.subscriber_id,
            "name": self.get_full_name(),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": self.date_of_birth.isoformat(),
            "age": self.get_age(),
            "gender": self.gender.value,
            "status": self.status.value,
            "relationship": self.relationship.value,
            "address": {
                "line1": self.address_line1,
                "line2": self.address_line2,
                "city": self.city,
                "state": self.state,
                "zip": self.zip_code,
                "country": self.country,
            },
            "phone": self.phone,
            "email": self.email,
            "policy_id": self.policy_id,
            "effective_date": self.effective_date.isoformat(),
            "termination_date": self.termination_date.isoformat() if self.termination_date else None,
            "pcp_provider_id": self.pcp_provider_id,
            "is_active": self.is_active(),
        }
