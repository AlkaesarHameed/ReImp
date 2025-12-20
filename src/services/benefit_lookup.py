"""
Benefit Lookup Service.

Provides lookup functionality for:
- Member eligibility
- Policy benefits and limits
- Fee schedule amounts
- Coverage details

Source: Design Document Section 3.3 - Benefit Calculation Engine
Verified: 2025-12-18
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from src.core.enums import CoverageType, PolicyStatus
from src.schemas.benefit import (
    CoverageLookup,
    FeeScheduleLookup,
    MemberEligibility,
)

logger = logging.getLogger(__name__)


class BenefitLookupService:
    """
    Service for looking up benefit-related information.

    Provides cached lookups for eligibility, fee schedules,
    and coverage details during claim processing.
    """

    def __init__(self):
        """Initialize benefit lookup service."""
        # In-memory caches for demo mode
        self._fee_schedule_cache: dict[tuple[UUID, str], FeeScheduleLookup] = {}
        self._eligibility_cache: dict[UUID, MemberEligibility] = {}

        # Default fee schedule for demo mode
        self._demo_fee_schedule: dict[str, Decimal] = {}
        self._load_demo_fee_schedule()

    def _load_demo_fee_schedule(self) -> None:
        """Load demo fee schedule data."""
        # Common procedure codes with typical allowed amounts
        self._demo_fee_schedule = {
            # Evaluation and Management (E/M)
            "99201": Decimal("45.00"),
            "99202": Decimal("75.00"),
            "99203": Decimal("110.00"),
            "99204": Decimal("170.00"),
            "99205": Decimal("215.00"),
            "99211": Decimal("25.00"),
            "99212": Decimal("50.00"),
            "99213": Decimal("80.00"),
            "99214": Decimal("120.00"),
            "99215": Decimal("175.00"),
            # Hospital Visits
            "99221": Decimal("150.00"),
            "99222": Decimal("200.00"),
            "99223": Decimal("250.00"),
            "99231": Decimal("45.00"),
            "99232": Decimal("80.00"),
            "99233": Decimal("120.00"),
            # Emergency Department
            "99281": Decimal("35.00"),
            "99282": Decimal("60.00"),
            "99283": Decimal("100.00"),
            "99284": Decimal("175.00"),
            "99285": Decimal("275.00"),
            # Consultations
            "99241": Decimal("65.00"),
            "99242": Decimal("110.00"),
            "99243": Decimal("160.00"),
            "99244": Decimal("215.00"),
            "99245": Decimal("280.00"),
            # Common Procedures
            "10060": Decimal("150.00"),  # I&D abscess
            "10061": Decimal("225.00"),  # I&D abscess complicated
            "11100": Decimal("125.00"),  # Skin biopsy
            "12001": Decimal("175.00"),  # Simple repair 2.5cm or less
            "12002": Decimal("250.00"),  # Simple repair 2.6-7.5cm
            "17000": Decimal("75.00"),   # Destruction lesion
            "17003": Decimal("15.00"),   # Additional lesion
            "20610": Decimal("110.00"),  # Joint injection major
            "20605": Decimal("90.00"),   # Joint injection intermediate
            "36415": Decimal("5.00"),    # Venipuncture
            "36416": Decimal("5.00"),    # Capillary blood draw
            # Lab Codes
            "80048": Decimal("15.00"),   # Basic metabolic panel
            "80053": Decimal("25.00"),   # Comprehensive metabolic panel
            "80061": Decimal("20.00"),   # Lipid panel
            "85025": Decimal("12.00"),   # CBC with differential
            "85027": Decimal("10.00"),   # CBC automated
            "81001": Decimal("5.00"),    # Urinalysis automated
            "87880": Decimal("15.00"),   # Strep A rapid test
            # Radiology
            "71046": Decimal("45.00"),   # Chest X-ray 2 views
            "71047": Decimal("55.00"),   # Chest X-ray 3 views
            "72100": Decimal("70.00"),   # Spine X-ray 2-3 views
            "73030": Decimal("50.00"),   # Shoulder X-ray
            "73560": Decimal("45.00"),   # Knee X-ray 2 views
            "73610": Decimal("40.00"),   # Ankle X-ray
            # CT Scans
            "70450": Decimal("250.00"),  # CT head without contrast
            "70460": Decimal("325.00"),  # CT head with contrast
            "71250": Decimal("300.00"),  # CT chest without contrast
            "71260": Decimal("375.00"),  # CT chest with contrast
            "74150": Decimal("275.00"),  # CT abdomen without contrast
            "74160": Decimal("350.00"),  # CT abdomen with contrast
            # MRI
            "70551": Decimal("475.00"),  # MRI brain without contrast
            "70553": Decimal("625.00"),  # MRI brain with/without contrast
            "72141": Decimal("500.00"),  # MRI cervical spine without
            "72148": Decimal("500.00"),  # MRI lumbar spine without
            # EKG/ECG
            "93000": Decimal("35.00"),   # ECG with interpretation
            "93005": Decimal("25.00"),   # ECG tracing only
            "93010": Decimal("15.00"),   # ECG interpretation only
        }

    async def lookup_eligibility(
        self,
        member_id: UUID,
        policy_id: UUID,
        service_date: date,
    ) -> MemberEligibility:
        """
        Look up member eligibility for a given date.

        In production, this would query the database.
        For demo mode, returns simulated eligibility data.

        Args:
            member_id: Member UUID
            policy_id: Policy UUID
            service_date: Date of service

        Returns:
            MemberEligibility with coverage details
        """
        # Check cache first
        cache_key = (member_id, policy_id)
        if cache_key in self._eligibility_cache:
            cached = self._eligibility_cache[cache_key]
            # Verify date range
            if cached.eligibility_start <= service_date:
                if cached.eligibility_end is None or cached.eligibility_end >= service_date:
                    return cached

        # Demo mode - return simulated eligibility
        eligibility = MemberEligibility(
            member_id=member_id,
            policy_id=policy_id,
            is_eligible=True,
            eligibility_start=date(2025, 1, 1),
            eligibility_end=date(2025, 12, 31),
            policy_status=PolicyStatus.ACTIVE.value,
            benefit_class="silver",
            network_type="ppo",
            # 80% in-network, 60% out-of-network
            in_network_rate=Decimal("0.80"),
            out_of_network_rate=Decimal("0.60"),
            # $1,500 deductible
            annual_deductible=Decimal("1500.00"),
            deductible_met=Decimal("750.00"),
            remaining_deductible=Decimal("750.00"),
            # $6,000 out-of-pocket max
            out_of_pocket_max=Decimal("6000.00"),
            out_of_pocket_met=Decimal("1500.00"),
            remaining_out_of_pocket=Decimal("4500.00"),
            # $100,000 annual limit
            annual_limit=Decimal("100000.00"),
            limit_used=Decimal("5000.00"),
            remaining_limit=Decimal("95000.00"),
            # No pre-existing waiting
            pre_existing_waiting_ends=None,
            # No exclusions in demo
            excluded_procedures=[],
            excluded_conditions=[],
        )

        # Cache the result
        self._eligibility_cache[cache_key] = eligibility

        logger.debug(f"Eligibility lookup: member={member_id}, eligible={eligibility.is_eligible}")

        return eligibility

    async def lookup_fee_schedule(
        self,
        procedure_code: str,
        tenant_id: UUID,
        fee_schedule_id: Optional[UUID] = None,
        modifiers: Optional[list[str]] = None,
        is_facility: Optional[bool] = None,
    ) -> FeeScheduleLookup:
        """
        Look up allowed amount from fee schedule.

        Args:
            procedure_code: CPT/HCPCS procedure code
            tenant_id: Tenant UUID
            fee_schedule_id: Optional specific fee schedule
            modifiers: List of modifiers
            is_facility: True for facility setting

        Returns:
            FeeScheduleLookup with allowed amount
        """
        # Check cache
        cache_key = (tenant_id, procedure_code)
        if cache_key in self._fee_schedule_cache:
            cached = self._fee_schedule_cache[cache_key]
            # Apply modifiers to cached amount
            return self._apply_modifiers(cached, modifiers, is_facility)

        # Look up in demo fee schedule
        base_amount = self._demo_fee_schedule.get(procedure_code, Decimal("0"))
        found = base_amount > 0

        # If not found, estimate based on code range
        if not found:
            base_amount = self._estimate_amount(procedure_code)
            found = base_amount > 0

        lookup = FeeScheduleLookup(
            procedure_code=procedure_code,
            found=found,
            allowed_amount=base_amount,
            facility_amount=base_amount * Decimal("0.85") if found else None,
            non_facility_amount=base_amount if found else None,
            modifier_factor=Decimal("1.0"),
            adjusted_amount=base_amount,
            fee_schedule_name="Demo Fee Schedule" if found else "",
            fee_schedule_id=fee_schedule_id,
        )

        # Cache the base lookup
        self._fee_schedule_cache[cache_key] = lookup

        # Apply modifiers
        return self._apply_modifiers(lookup, modifiers, is_facility)

    def _apply_modifiers(
        self,
        lookup: FeeScheduleLookup,
        modifiers: Optional[list[str]],
        is_facility: Optional[bool],
    ) -> FeeScheduleLookup:
        """Apply modifier adjustments to fee schedule lookup."""
        if not lookup.found:
            return lookup

        # Start with appropriate base
        if is_facility and lookup.facility_amount:
            base = lookup.facility_amount
        elif is_facility is False and lookup.non_facility_amount:
            base = lookup.non_facility_amount
        else:
            base = lookup.allowed_amount

        factor = Decimal("1.0")

        if modifiers:
            for mod in modifiers:
                mod_upper = mod.upper()

                if mod_upper == "26":
                    # Professional component
                    factor *= Decimal("0.26")
                elif mod_upper == "TC":
                    # Technical component
                    factor *= Decimal("0.74")
                elif mod_upper == "50":
                    # Bilateral
                    factor *= Decimal("1.50")
                elif mod_upper == "51":
                    # Multiple procedures
                    factor *= Decimal("0.50")
                elif mod_upper in ("52", "53"):
                    # Reduced/discontinued
                    factor *= Decimal("0.50")

        # Create adjusted lookup
        return FeeScheduleLookup(
            procedure_code=lookup.procedure_code,
            found=lookup.found,
            allowed_amount=lookup.allowed_amount,
            facility_amount=lookup.facility_amount,
            non_facility_amount=lookup.non_facility_amount,
            modifier_factor=factor,
            adjusted_amount=base * factor,
            fee_schedule_name=lookup.fee_schedule_name,
            fee_schedule_id=lookup.fee_schedule_id,
        )

    def _estimate_amount(self, procedure_code: str) -> Decimal:
        """
        Estimate allowed amount for unknown codes based on code range.

        This provides reasonable defaults for demo purposes.
        """
        try:
            # Extract numeric portion
            if procedure_code.startswith(("A", "C", "G", "J", "K", "L", "Q", "S", "T")):
                # HCPCS Level II codes
                code_num = int(procedure_code[1:])

                # J codes (drugs) - estimate based on typical costs
                if procedure_code.startswith("J"):
                    return Decimal("50.00")
                # A codes (supplies) - typically lower cost
                if procedure_code.startswith("A"):
                    return Decimal("25.00")
                # G codes (procedures) - moderate cost
                if procedure_code.startswith("G"):
                    return Decimal("75.00")

                return Decimal("50.00")

            # CPT codes (numeric)
            code_num = int(procedure_code)

            # E/M codes (99xxx)
            if 99000 <= code_num <= 99499:
                return Decimal("100.00")

            # Anesthesia (00100-01999)
            if 100 <= code_num <= 1999:
                return Decimal("200.00")

            # Surgery (10000-69999)
            if 10000 <= code_num <= 69999:
                if 10000 <= code_num <= 19999:
                    return Decimal("150.00")  # Integumentary
                if 20000 <= code_num <= 29999:
                    return Decimal("300.00")  # Musculoskeletal
                if 30000 <= code_num <= 39999:
                    return Decimal("250.00")  # Respiratory
                if 40000 <= code_num <= 49999:
                    return Decimal("275.00")  # Digestive
                if 50000 <= code_num <= 59999:
                    return Decimal("350.00")  # Urinary
                if 60000 <= code_num <= 69999:
                    return Decimal("400.00")  # Nervous

            # Radiology (70000-79999)
            if 70000 <= code_num <= 79999:
                if 70000 <= code_num <= 76999:
                    return Decimal("100.00")  # Diagnostic
                return Decimal("50.00")  # Radiation oncology

            # Pathology/Lab (80000-89999)
            if 80000 <= code_num <= 89999:
                return Decimal("15.00")

            # Medicine (90000-99999)
            if 90000 <= code_num <= 99999:
                return Decimal("75.00")

        except (ValueError, IndexError):
            pass

        # Default fallback
        return Decimal("50.00")

    async def lookup_coverage(
        self,
        coverage_type: CoverageType,
        policy_id: UUID,
        service_date: date,
    ) -> CoverageLookup:
        """
        Look up coverage details for a specific coverage type.

        Args:
            coverage_type: Type of coverage to look up
            policy_id: Policy UUID
            service_date: Date of service

        Returns:
            CoverageLookup with coverage details
        """
        # Demo mode - return simulated coverage
        # In production, this would query CoverageLimit table

        # Default coverage settings by type
        coverage_defaults = {
            CoverageType.INPATIENT: {
                "annual_limit": Decimal("50000.00"),
                "copay_percentage": Decimal("0.20"),
                "requires_prior_auth": True,
            },
            CoverageType.OUTPATIENT: {
                "annual_limit": Decimal("25000.00"),
                "per_visit_limit": Decimal("500.00"),
                "copay_percentage": Decimal("0.20"),
                "copay_fixed": Decimal("50.00"),
            },
            CoverageType.EMERGENCY: {
                "annual_limit": Decimal("100000.00"),
                "copay_fixed": Decimal("250.00"),
                "copay_percentage": Decimal("0.10"),
            },
            CoverageType.PRESCRIPTION: {
                "annual_limit": Decimal("10000.00"),
                "per_visit_limit": Decimal("200.00"),
                "copay_fixed": Decimal("20.00"),
            },
            CoverageType.MENTAL_HEALTH: {
                "annual_limit": Decimal("15000.00"),
                "per_visit_limit": Decimal("200.00"),
                "copay_percentage": Decimal("0.20"),
            },
            CoverageType.DENTAL: {
                "annual_limit": Decimal("2000.00"),
                "per_visit_limit": Decimal("500.00"),
                "copay_percentage": Decimal("0.50"),
            },
            CoverageType.VISION: {
                "annual_limit": Decimal("500.00"),
                "copay_fixed": Decimal("25.00"),
            },
            CoverageType.MATERNITY: {
                "annual_limit": Decimal("25000.00"),
                "copay_percentage": Decimal("0.20"),
                "requires_prior_auth": True,
            },
            CoverageType.PREVENTIVE: {
                "annual_limit": Decimal("5000.00"),
                "copay_percentage": Decimal("0.00"),  # 100% covered
            },
            CoverageType.REHABILITATION: {
                "annual_limit": Decimal("10000.00"),
                "per_visit_limit": Decimal("150.00"),
                "copay_percentage": Decimal("0.20"),
            },
            CoverageType.LAB: {
                "annual_limit": Decimal("5000.00"),
                "copay_percentage": Decimal("0.10"),
            },
            CoverageType.RADIOLOGY: {
                "annual_limit": Decimal("10000.00"),
                "copay_percentage": Decimal("0.20"),
            },
            CoverageType.DME: {
                "annual_limit": Decimal("3000.00"),
                "copay_percentage": Decimal("0.30"),
            },
        }

        defaults = coverage_defaults.get(coverage_type, {
            "annual_limit": Decimal("10000.00"),
            "copay_percentage": Decimal("0.20"),
        })

        return CoverageLookup(
            coverage_type=coverage_type.value,
            is_covered=True,
            requires_prior_auth=defaults.get("requires_prior_auth", False),
            annual_limit=defaults.get("annual_limit", Decimal("10000.00")),
            per_visit_limit=defaults.get("per_visit_limit"),
            per_incident_limit=defaults.get("per_incident_limit"),
            remaining_limit=defaults.get("annual_limit", Decimal("10000.00")) * Decimal("0.90"),
            copay_fixed=defaults.get("copay_fixed"),
            copay_percentage=defaults.get("copay_percentage", Decimal("0.20")),
            waiting_period_days=0,
            waiting_period_met=True,
        )

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._fee_schedule_cache.clear()
        self._eligibility_cache.clear()

    def update_demo_fee_schedule(
        self,
        procedure_code: str,
        amount: Decimal,
    ) -> None:
        """Update demo fee schedule with custom amount."""
        self._demo_fee_schedule[procedure_code] = amount
        # Clear cache for this code
        keys_to_remove = [k for k in self._fee_schedule_cache if k[1] == procedure_code]
        for key in keys_to_remove:
            del self._fee_schedule_cache[key]


# =============================================================================
# Singleton Instance
# =============================================================================


_benefit_lookup_service: Optional[BenefitLookupService] = None


def get_benefit_lookup_service() -> BenefitLookupService:
    """Get singleton benefit lookup service instance."""
    global _benefit_lookup_service
    if _benefit_lookup_service is None:
        _benefit_lookup_service = BenefitLookupService()
    return _benefit_lookup_service
