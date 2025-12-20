"""
Demo Provider Model.
Source: Design Document Section 4.4 - Demo Mode
Verified: 2025-12-18

In-memory provider model for demo/testing.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ProviderStatus(str, Enum):
    """Provider status values."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class ProviderType(str, Enum):
    """Provider type values."""

    PHYSICIAN = "physician"
    HOSPITAL = "hospital"
    CLINIC = "clinic"
    LABORATORY = "laboratory"
    PHARMACY = "pharmacy"
    DME = "dme"  # Durable Medical Equipment
    AMBULANCE = "ambulance"
    HOME_HEALTH = "home_health"


class NetworkStatus(str, Enum):
    """Network participation status."""

    IN_NETWORK = "in_network"
    OUT_OF_NETWORK = "out_of_network"
    PREFERRED = "preferred"
    NON_PARTICIPATING = "non_participating"


class DemoProvider(BaseModel):
    """In-memory provider model for demo mode."""

    provider_id: str = Field(default_factory=lambda: f"PRV-{uuid4().hex[:8].upper()}")
    npi: str = Field(default_factory=lambda: f"1{uuid4().hex[:9]}"[:10])
    tax_id: Optional[str] = None

    # Basic info
    name: str = "Demo Provider"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    organization_name: Optional[str] = None

    # Type and status
    provider_type: ProviderType = ProviderType.PHYSICIAN
    status: ProviderStatus = ProviderStatus.ACTIVE

    # Specialty
    specialty: str = "General Practice"
    specialty_code: str = "207Q00000X"

    # Address
    address_line1: str = "123 Medical Center Dr"
    address_line2: Optional[str] = None
    city: str = "Healthcare City"
    state: str = "CA"
    zip_code: str = "90210"
    country: str = "US"

    # Contact
    phone: str = "(555) 123-4567"
    fax: Optional[str] = None
    email: Optional[str] = None

    # Network participation
    network_status: NetworkStatus = NetworkStatus.IN_NETWORK
    network_ids: list[str] = Field(default_factory=lambda: ["NET-001"])
    contracted_rate_percent: int = 100  # % of fee schedule

    # Dates
    effective_date: date = Field(default_factory=date.today)
    termination_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Credentials
    license_number: Optional[str] = None
    license_state: Optional[str] = None
    license_expiry: Optional[date] = None
    board_certified: bool = False

    # Additional metadata
    metadata: dict = Field(default_factory=dict)
    is_active: bool = True  # Active flag for UI compatibility

    # Property aliases for UI compatibility
    @property
    def provider_name(self) -> str:
        """Alias for name."""
        return self.name

    @property
    def address(self) -> str:
        """Alias for address_line1."""
        return self.address_line1

    def is_active_check(self) -> bool:
        """Check if provider is active."""
        if self.status != ProviderStatus.ACTIVE:
            return False
        today = date.today()
        if self.effective_date > today:
            return False
        if self.termination_date and self.termination_date < today:
            return False
        return True

    def is_in_network(self, network_id: str = "NET-001") -> bool:
        """Check if provider is in a specific network."""
        if not self.is_active:
            return False
        if self.network_status == NetworkStatus.OUT_OF_NETWORK:
            return False
        if self.network_status == NetworkStatus.NON_PARTICIPATING:
            return False
        return network_id in self.network_ids

    def get_display_name(self) -> str:
        """Get display name for provider."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.organization_name:
            return self.organization_name
        return self.name

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "provider_id": self.provider_id,
            "npi": self.npi,
            "name": self.get_display_name(),
            "provider_type": self.provider_type.value,
            "status": self.status.value,
            "specialty": self.specialty,
            "specialty_code": self.specialty_code,
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
            "network_status": self.network_status.value,
            "network_ids": self.network_ids,
            "is_active": self.is_active,
            "is_in_network": self.is_in_network(),
        }
