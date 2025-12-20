"""
Demo Fee Schedule Model.
Source: Design Document Section 4.4 - Demo Mode
Verified: 2025-12-18

In-memory fee schedule model for demo/testing.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class FeeScheduleType(str, Enum):
    """Fee schedule type values."""

    MEDICARE = "medicare"
    MEDICAID = "medicaid"
    COMMERCIAL = "commercial"
    WORKERS_COMP = "workers_comp"
    CUSTOM = "custom"


class FeeScheduleEntry(BaseModel):
    """A single fee schedule entry for a procedure."""

    procedure_code: str
    procedure_description: str = ""
    allowed_amount: Decimal
    modifier_adjustments: dict[str, Decimal] = Field(default_factory=dict)

    # Optional fields
    revenue_code: Optional[str] = None
    place_of_service: Optional[str] = None
    category: Optional[str] = None

    # RVU components (for Medicare-based schedules)
    work_rvu: Optional[Decimal] = None
    pe_rvu: Optional[Decimal] = None
    mp_rvu: Optional[Decimal] = None
    total_rvu: Optional[Decimal] = None
    conversion_factor: Optional[Decimal] = None

    def get_allowed_amount(self, modifiers: Optional[list[str]] = None) -> Decimal:
        """Get allowed amount with modifier adjustments."""
        amount = self.allowed_amount

        if modifiers and self.modifier_adjustments:
            for modifier in modifiers:
                if modifier in self.modifier_adjustments:
                    # Modifier adjustments are percentages (e.g., 0.50 for 50%)
                    adjustment = self.modifier_adjustments[modifier]
                    if adjustment <= 1:
                        amount = amount * adjustment
                    else:
                        amount = amount + adjustment

        return amount.quantize(Decimal("0.01"))


class DemoFeeSchedule(BaseModel):
    """In-memory fee schedule model for demo mode."""

    schedule_id: str = Field(default_factory=lambda: f"FS-{uuid4().hex[:8].upper()}")
    schedule_name: str = "Standard Fee Schedule"
    schedule_type: FeeScheduleType = FeeScheduleType.COMMERCIAL

    # Dates
    effective_date: date = Field(default_factory=date.today)
    termination_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Network/region
    network_id: Optional[str] = None
    region_code: Optional[str] = None

    # Entries
    entries: dict[str, FeeScheduleEntry] = Field(default_factory=dict)

    # Default conversion factor for RVU-based calculations
    conversion_factor: Decimal = Decimal("33.8872")  # 2024 Medicare CF

    # Metadata
    metadata: dict = Field(default_factory=dict)

    def add_entry(
        self,
        procedure_code: str,
        allowed_amount: Decimal,
        description: str = "",
        modifiers: Optional[dict[str, Decimal]] = None,
    ) -> None:
        """Add a fee schedule entry."""
        entry = FeeScheduleEntry(
            procedure_code=procedure_code,
            procedure_description=description,
            allowed_amount=allowed_amount,
            modifier_adjustments=modifiers or {},
        )
        self.entries[procedure_code] = entry
        self.updated_at = datetime.utcnow()

    def get_allowed_amount(
        self,
        procedure_code: str,
        modifiers: Optional[list[str]] = None,
    ) -> Optional[Decimal]:
        """Get allowed amount for a procedure code."""
        entry = self.entries.get(procedure_code)
        if entry:
            return entry.get_allowed_amount(modifiers)
        return None

    def has_procedure(self, procedure_code: str) -> bool:
        """Check if procedure is in fee schedule."""
        return procedure_code in self.entries

    def get_entry(self, procedure_code: str) -> Optional[FeeScheduleEntry]:
        """Get fee schedule entry for a procedure."""
        return self.entries.get(procedure_code)

    def is_active(self) -> bool:
        """Check if fee schedule is active."""
        today = date.today()
        if self.effective_date > today:
            return False
        if self.termination_date and self.termination_date < today:
            return False
        return True

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "schedule_id": self.schedule_id,
            "schedule_name": self.schedule_name,
            "schedule_type": self.schedule_type.value,
            "effective_date": self.effective_date.isoformat(),
            "termination_date": self.termination_date.isoformat() if self.termination_date else None,
            "network_id": self.network_id,
            "entry_count": len(self.entries),
            "is_active": self.is_active(),
        }


# =============================================================================
# Default Fee Schedule Data
# =============================================================================


def create_default_fee_schedule() -> DemoFeeSchedule:
    """Create a default fee schedule with common CPT codes."""
    schedule = DemoFeeSchedule(
        schedule_id="FS-DEFAULT",
        schedule_name="Demo Standard Fee Schedule",
        network_id="NET-001",
    )

    # E/M codes - Office visits
    schedule.add_entry("99213", Decimal("76.15"), "Office visit, established, low complexity")
    schedule.add_entry("99214", Decimal("110.43"), "Office visit, established, moderate complexity")
    schedule.add_entry("99215", Decimal("148.33"), "Office visit, established, high complexity")
    schedule.add_entry("99203", Decimal("103.38"), "Office visit, new patient, low complexity")
    schedule.add_entry("99204", Decimal("167.10"), "Office visit, new patient, moderate complexity")
    schedule.add_entry("99205", Decimal("211.12"), "Office visit, new patient, high complexity")

    # Lab codes
    schedule.add_entry("80053", Decimal("14.49"), "Comprehensive metabolic panel")
    schedule.add_entry("80048", Decimal("11.49"), "Basic metabolic panel")
    schedule.add_entry("85025", Decimal("10.56"), "CBC with differential")
    schedule.add_entry("80061", Decimal("18.39"), "Lipid panel")
    schedule.add_entry("83036", Decimal("13.77"), "Hemoglobin A1C")
    schedule.add_entry("82947", Decimal("7.08"), "Glucose, blood")

    # Imaging
    schedule.add_entry("71046", Decimal("31.25"), "Chest X-ray, 2 views")
    schedule.add_entry("73560", Decimal("27.72"), "X-ray knee, 3 views")
    schedule.add_entry("72148", Decimal("241.53"), "MRI lumbar spine without contrast")
    schedule.add_entry("70553", Decimal("396.82"), "MRI brain with and without contrast")

    # Procedures
    schedule.add_entry("99385", Decimal("167.84"), "Preventive visit, 18-39 years")
    schedule.add_entry("99386", Decimal("190.38"), "Preventive visit, 40-64 years")
    schedule.add_entry("99387", Decimal("210.62"), "Preventive visit, 65+ years")
    schedule.add_entry("90471", Decimal("25.53"), "Immunization administration")
    schedule.add_entry("36415", Decimal("3.00"), "Venipuncture")

    # Surgical
    schedule.add_entry("27447", Decimal("1421.88"), "Total knee replacement")
    schedule.add_entry("27130", Decimal("1493.25"), "Total hip replacement")
    schedule.add_entry("47562", Decimal("629.50"), "Laparoscopic cholecystectomy")

    return schedule
