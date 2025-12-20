"""
LCD/NCD Medical Necessity Service.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Provides CMS coverage determination validation:
- Local Coverage Determination (LCD) lookup
- National Coverage Determination (NCD) lookup
- Medical necessity validation
- Diagnosis-procedure compatibility checking
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any, Set
from uuid import UUID, uuid4
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class CoverageType(str, Enum):
    """Type of coverage determination."""
    LCD = "lcd"  # Local Coverage Determination
    NCD = "ncd"  # National Coverage Determination


class CoverageStatus(str, Enum):
    """Coverage determination status."""
    COVERED = "covered"
    NOT_COVERED = "not_covered"
    CONDITIONAL = "conditional"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class MACRegion(str, Enum):
    """Medicare Administrative Contractor regions."""
    REGION_A = "A"  # Noridian (AK, WA, OR, ID, AZ, MT, WY, ND, SD, UT, NV)
    REGION_B = "B"  # WPS (IA, KS, MO, NE, IN, MI)
    REGION_C = "C"  # CGS (KY, OH)
    REGION_D = "D"  # Novitas (AR, CO, NM, OK, TX, LA, MS)
    REGION_E = "E"  # Palmetto (NC, SC, VA, WV)
    REGION_F = "F"  # NGS (CT, IL, MA, ME, MN, NH, NY, RI, VT, WI)
    REGION_H = "H"  # Novitas (DC, DE, MD, NJ, PA)
    REGION_J = "J"  # First Coast (AL, FL, GA, TN)
    REGION_K = "K"  # Palmetto (CA - North)
    REGION_L = "L"  # Palmetto (CA - South, HI, NV, Guam)
    NATIONAL = "NATIONAL"  # For NCD


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class CoveragePolicy:
    """LCD/NCD coverage policy."""
    policy_id: str
    policy_type: CoverageType
    title: str
    contractor: Optional[str] = None
    mac_region: Optional[MACRegion] = None

    # Effective dates
    effective_date: Optional[date] = None
    end_date: Optional[date] = None
    revision_date: Optional[date] = None

    # Coverage details
    covered_codes: Set[str] = field(default_factory=set)  # CPT/HCPCS codes
    covered_diagnosis_codes: Set[str] = field(default_factory=set)  # ICD-10 codes
    excluded_codes: Set[str] = field(default_factory=set)

    # Diagnosis-procedure mapping
    code_diagnosis_map: Dict[str, Set[str]] = field(default_factory=dict)

    # Conditions and limitations
    conditions: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    documentation_requirements: List[str] = field(default_factory=list)

    # Metadata
    description: Optional[str] = None
    cms_url: Optional[str] = None
    is_active: bool = True


@dataclass
class CoverageDetermination:
    """Result of coverage determination check."""
    # Identification
    determination_id: str
    policy_id: Optional[str] = None
    policy_type: Optional[CoverageType] = None

    # Result
    status: CoverageStatus = CoverageStatus.UNKNOWN
    is_covered: bool = False

    # Codes checked
    procedure_code: str = ""
    diagnosis_codes: List[str] = field(default_factory=list)
    matching_diagnosis: Optional[str] = None

    # Details
    reason: Optional[str] = None
    conditions: List[str] = field(default_factory=list)
    documentation_required: List[str] = field(default_factory=list)

    # Policy info
    policy_title: Optional[str] = None
    effective_date: Optional[date] = None

    # Confidence
    confidence: float = 1.0

    # Errors
    errors: List[str] = field(default_factory=list)


@dataclass
class MedicalNecessityResult:
    """Complete medical necessity validation result."""
    # Identification
    validation_id: str
    claim_id: Optional[str] = None

    # Overall result
    is_medically_necessary: bool = False
    overall_status: CoverageStatus = CoverageStatus.UNKNOWN

    # Determinations per service line
    line_determinations: List[CoverageDetermination] = field(default_factory=list)

    # Summary
    covered_count: int = 0
    not_covered_count: int = 0
    conditional_count: int = 0

    # Policy references
    lcd_policies_checked: List[str] = field(default_factory=list)
    ncd_policies_checked: List[str] = field(default_factory=list)

    # Messages
    summary_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Performance
    processing_time_ms: int = 0
    checked_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# LCD/NCD Database (In-Memory for Demo)
# =============================================================================


class LCDNCDDatabase:
    """
    In-memory LCD/NCD policy database.

    In production, this would be backed by a database with
    regularly updated CMS policy data.
    """

    def __init__(self):
        self.policies: Dict[str, CoveragePolicy] = {}
        self._load_sample_policies()

    def _load_sample_policies(self) -> None:
        """Load sample LCD/NCD policies for demo."""

        # Sample NCD - Screening Mammography
        self.policies["NCD-210.10"] = CoveragePolicy(
            policy_id="NCD-210.10",
            policy_type=CoverageType.NCD,
            title="Screening Mammography",
            effective_date=date(2020, 1, 1),
            covered_codes={"77067", "G0202", "G0204", "G0206"},
            covered_diagnosis_codes={
                "Z12.31",  # Encounter for screening mammogram
                "Z80.3",   # Family history of breast cancer
                "Z85.3",   # Personal history of breast cancer
            },
            conditions=[
                "Annual screening for women age 40 and older",
                "Baseline mammogram for women 35-39",
            ],
            description="Coverage for screening mammography for early detection of breast cancer",
            cms_url="https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?NCDId=209",
            is_active=True,
        )

        # Sample NCD - Diabetes Self-Management Training
        self.policies["NCD-40.1"] = CoveragePolicy(
            policy_id="NCD-40.1",
            policy_type=CoverageType.NCD,
            title="Diabetes Self-Management Training (DSMT)",
            effective_date=date(2019, 1, 1),
            covered_codes={"G0108", "G0109"},
            covered_diagnosis_codes={
                "E10.9", "E10.65",  # Type 1 diabetes
                "E11.9", "E11.65",  # Type 2 diabetes
                "E13.9",  # Other specified diabetes
            },
            conditions=[
                "Must be ordered by treating physician",
                "Beneficiary must have diabetes diagnosis",
                "Training must be furnished by certified provider",
            ],
            documentation_requirements=[
                "Physician order for DSMT",
                "Documentation of diabetes diagnosis",
            ],
            is_active=True,
        )

        # Sample LCD - Physical Therapy
        self.policies["LCD-L33631"] = CoveragePolicy(
            policy_id="LCD-L33631",
            policy_type=CoverageType.LCD,
            title="Physical Therapy Services",
            contractor="Noridian",
            mac_region=MACRegion.REGION_A,
            effective_date=date(2021, 1, 1),
            covered_codes={
                "97110", "97112", "97116", "97140",  # Therapeutic procedures
                "97161", "97162", "97163",  # PT evaluation
            },
            covered_diagnosis_codes={
                "M54.5",  # Low back pain
                "M25.561", "M25.562",  # Knee pain
                "S83.511A", "S83.512A",  # ACL sprain
                "M79.3",  # Panniculitis
            },
            code_diagnosis_map={
                "97110": {"M54.5", "M25.561", "M25.562", "S83.511A", "S83.512A"},
                "97112": {"M54.5", "S83.511A", "S83.512A"},
                "97116": {"M25.561", "M25.562", "S83.511A", "S83.512A"},
            },
            conditions=[
                "Services must be medically reasonable and necessary",
                "Must show objective improvement",
                "Treatment plan must be established",
            ],
            documentation_requirements=[
                "Plan of care with measurable goals",
                "Progress notes for each visit",
                "Physician certification every 90 days",
            ],
            is_active=True,
        )

        # Sample LCD - Chiropractic Services
        self.policies["LCD-L34979"] = CoveragePolicy(
            policy_id="LCD-L34979",
            policy_type=CoverageType.LCD,
            title="Chiropractic Services",
            contractor="CGS",
            mac_region=MACRegion.REGION_C,
            effective_date=date(2020, 6, 1),
            covered_codes={"98940", "98941", "98942"},
            covered_diagnosis_codes={
                "M99.01", "M99.02", "M99.03", "M99.04", "M99.05",  # Subluxation
                "M54.2",  # Cervicalgia
                "M54.5",  # Low back pain
            },
            conditions=[
                "Only manual manipulation of spine to correct subluxation",
                "X-ray or clinical documentation of subluxation required",
            ],
            is_active=True,
        )

        # Sample LCD - Laboratory Tests
        self.policies["LCD-L36256"] = CoveragePolicy(
            policy_id="LCD-L36256",
            policy_type=CoverageType.LCD,
            title="Lipid Panel Testing",
            contractor="WPS",
            mac_region=MACRegion.REGION_B,
            effective_date=date(2022, 1, 1),
            covered_codes={"80061", "82465", "83718", "84478"},
            covered_diagnosis_codes={
                "E78.0", "E78.1", "E78.2", "E78.4", "E78.5",  # Hyperlipidemia
                "I25.10",  # Coronary artery disease
                "E11.9",  # Type 2 diabetes
                "Z83.42",  # Family history of cardiovascular disease
            },
            conditions=[
                "Annual screening covered for cardiovascular risk",
                "More frequent testing for documented hyperlipidemia",
            ],
            is_active=True,
        )

    def get_policy(self, policy_id: str) -> Optional[CoveragePolicy]:
        """Get a policy by ID."""
        return self.policies.get(policy_id)

    def find_policies_by_code(
        self,
        procedure_code: str,
        mac_region: Optional[MACRegion] = None,
    ) -> List[CoveragePolicy]:
        """Find policies that cover a procedure code."""
        matching = []
        for policy in self.policies.values():
            if not policy.is_active:
                continue

            # Check if code is covered
            if procedure_code not in policy.covered_codes:
                continue

            # Check region for LCDs
            if policy.policy_type == CoverageType.LCD:
                if mac_region and policy.mac_region != mac_region:
                    continue

            matching.append(policy)

        return matching

    def find_ncd_policies(self, procedure_code: str) -> List[CoveragePolicy]:
        """Find NCD policies for a procedure code."""
        return [
            p for p in self.policies.values()
            if p.policy_type == CoverageType.NCD
            and p.is_active
            and procedure_code in p.covered_codes
        ]


# =============================================================================
# Service
# =============================================================================


class LCDNCDService:
    """
    LCD/NCD Medical Necessity Service.

    Validates medical necessity by checking:
    - National Coverage Determinations (NCD)
    - Local Coverage Determinations (LCD)
    - Diagnosis-procedure compatibility

    Usage:
        service = LCDNCDService()
        result = await service.check_medical_necessity(
            procedure_codes=["97110", "97112"],
            diagnosis_codes=["M54.5"],
            mac_region=MACRegion.REGION_A,
        )
        if result.is_medically_necessary:
            print("Claim is medically necessary")
    """

    def __init__(
        self,
        db_session=None,
        cache_service=None,
    ):
        """
        Initialize LCD/NCD service.

        Args:
            db_session: Database session for policy lookup
            cache_service: Cache for performance
        """
        self.db = db_session
        self.cache = cache_service
        self.policy_db = LCDNCDDatabase()

    async def check_medical_necessity(
        self,
        procedure_codes: List[str],
        diagnosis_codes: List[str],
        mac_region: Optional[MACRegion] = None,
        service_date: Optional[date] = None,
        claim_id: Optional[str] = None,
    ) -> MedicalNecessityResult:
        """
        Check medical necessity for procedure codes.

        Args:
            procedure_codes: CPT/HCPCS codes to check
            diagnosis_codes: ICD-10 diagnosis codes
            mac_region: MAC region for LCD lookup
            service_date: Date of service
            claim_id: Optional claim ID for tracking

        Returns:
            MedicalNecessityResult with coverage determinations
        """
        start_time = datetime.utcnow()
        validation_id = str(uuid4())

        result = MedicalNecessityResult(
            validation_id=validation_id,
            claim_id=claim_id,
        )

        try:
            # Check each procedure code
            for proc_code in procedure_codes:
                determination = await self._check_procedure_coverage(
                    procedure_code=proc_code,
                    diagnosis_codes=diagnosis_codes,
                    mac_region=mac_region,
                    service_date=service_date,
                )
                result.line_determinations.append(determination)

                # Track policy references
                if determination.policy_type == CoverageType.LCD:
                    if determination.policy_id:
                        result.lcd_policies_checked.append(determination.policy_id)
                elif determination.policy_type == CoverageType.NCD:
                    if determination.policy_id:
                        result.ncd_policies_checked.append(determination.policy_id)

            # Calculate summary
            result.covered_count = sum(
                1 for d in result.line_determinations
                if d.status == CoverageStatus.COVERED
            )
            result.not_covered_count = sum(
                1 for d in result.line_determinations
                if d.status == CoverageStatus.NOT_COVERED
            )
            result.conditional_count = sum(
                1 for d in result.line_determinations
                if d.status == CoverageStatus.CONDITIONAL
            )

            # Determine overall status
            if result.not_covered_count > 0:
                result.overall_status = CoverageStatus.NOT_COVERED
                result.is_medically_necessary = False
            elif result.conditional_count > 0:
                result.overall_status = CoverageStatus.CONDITIONAL
                result.is_medically_necessary = True  # May need documentation
            elif result.covered_count == len(procedure_codes):
                result.overall_status = CoverageStatus.COVERED
                result.is_medically_necessary = True
            else:
                result.overall_status = CoverageStatus.UNKNOWN
                result.is_medically_necessary = False

            # Generate summary message
            result.summary_message = self._generate_summary(result)

        except Exception as e:
            logger.error(f"Medical necessity check failed: {e}", exc_info=True)
            result.errors.append(str(e))
            result.is_medically_necessary = False

        # Calculate processing time
        result.processing_time_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )

        return result

    async def _check_procedure_coverage(
        self,
        procedure_code: str,
        diagnosis_codes: List[str],
        mac_region: Optional[MACRegion],
        service_date: Optional[date],
    ) -> CoverageDetermination:
        """Check coverage for a single procedure code."""
        determination = CoverageDetermination(
            determination_id=str(uuid4()),
            procedure_code=procedure_code,
            diagnosis_codes=diagnosis_codes,
        )

        # First check NCDs (national take precedence)
        ncd_policies = self.policy_db.find_ncd_policies(procedure_code)
        for policy in ncd_policies:
            if self._check_policy_coverage(policy, procedure_code, diagnosis_codes, determination):
                return determination

        # Then check LCDs
        lcd_policies = self.policy_db.find_policies_by_code(procedure_code, mac_region)
        for policy in lcd_policies:
            if policy.policy_type == CoverageType.LCD:
                if self._check_policy_coverage(policy, procedure_code, diagnosis_codes, determination):
                    return determination

        # No matching policy found
        if not ncd_policies and not lcd_policies:
            determination.status = CoverageStatus.NOT_APPLICABLE
            determination.reason = f"No LCD/NCD policy found for procedure {procedure_code}"
            determination.is_covered = True  # No restriction means covered
        else:
            determination.status = CoverageStatus.NOT_COVERED
            determination.reason = f"Diagnosis codes do not support medical necessity for {procedure_code}"
            determination.is_covered = False

        return determination

    def _check_policy_coverage(
        self,
        policy: CoveragePolicy,
        procedure_code: str,
        diagnosis_codes: List[str],
        determination: CoverageDetermination,
    ) -> bool:
        """
        Check if procedure is covered under a policy.

        Returns True if determination is complete (covered or conditional).
        """
        determination.policy_id = policy.policy_id
        determination.policy_type = policy.policy_type
        determination.policy_title = policy.title
        determination.effective_date = policy.effective_date

        # Check if procedure is in excluded codes
        if procedure_code in policy.excluded_codes:
            determination.status = CoverageStatus.NOT_COVERED
            determination.reason = f"Procedure {procedure_code} is explicitly excluded"
            determination.is_covered = False
            return True

        # Check diagnosis code compatibility
        matching_dx = None

        # First check specific code-diagnosis mapping
        if policy.code_diagnosis_map and procedure_code in policy.code_diagnosis_map:
            required_dx = policy.code_diagnosis_map[procedure_code]
            for dx in diagnosis_codes:
                if dx in required_dx or self._diagnosis_matches(dx, required_dx):
                    matching_dx = dx
                    break
        else:
            # Check general covered diagnosis codes
            for dx in diagnosis_codes:
                if dx in policy.covered_diagnosis_codes or \
                   self._diagnosis_matches(dx, policy.covered_diagnosis_codes):
                    matching_dx = dx
                    break

        if matching_dx:
            determination.status = CoverageStatus.COVERED
            determination.is_covered = True
            determination.matching_diagnosis = matching_dx
            determination.reason = f"Covered under {policy.title}"
            determination.conditions = policy.conditions.copy()
            determination.documentation_required = policy.documentation_requirements.copy()

            # Mark as conditional if documentation is required
            if policy.documentation_requirements:
                determination.status = CoverageStatus.CONDITIONAL

            return True

        return False

    def _diagnosis_matches(self, diagnosis: str, valid_codes: Set[str]) -> bool:
        """
        Check if diagnosis matches any valid code.

        Supports partial matching for code ranges (e.g., E78.* matches E78.0, E78.1).
        """
        # Exact match
        if diagnosis in valid_codes:
            return True

        # Check for prefix matches (e.g., M99.0 matches M99.01)
        for valid in valid_codes:
            if diagnosis.startswith(valid.rstrip('.')):
                return True
            if valid.startswith(diagnosis.rstrip('.')):
                return True

        return False

    def _generate_summary(self, result: MedicalNecessityResult) -> str:
        """Generate summary message for result."""
        total = len(result.line_determinations)

        if result.overall_status == CoverageStatus.COVERED:
            return f"All {total} procedure(s) meet medical necessity requirements"
        elif result.overall_status == CoverageStatus.CONDITIONAL:
            return f"{result.conditional_count} of {total} procedure(s) covered with documentation requirements"
        elif result.overall_status == CoverageStatus.NOT_COVERED:
            return f"{result.not_covered_count} of {total} procedure(s) do not meet medical necessity requirements"
        else:
            return f"Unable to determine medical necessity for {total} procedure(s)"

    async def get_policy(self, policy_id: str) -> Optional[CoveragePolicy]:
        """Get a coverage policy by ID."""
        return self.policy_db.get_policy(policy_id)

    async def search_policies(
        self,
        procedure_code: Optional[str] = None,
        diagnosis_code: Optional[str] = None,
        policy_type: Optional[CoverageType] = None,
        mac_region: Optional[MACRegion] = None,
    ) -> List[CoveragePolicy]:
        """Search for coverage policies."""
        results = []

        for policy in self.policy_db.policies.values():
            if not policy.is_active:
                continue

            # Filter by type
            if policy_type and policy.policy_type != policy_type:
                continue

            # Filter by region
            if mac_region and policy.policy_type == CoverageType.LCD:
                if policy.mac_region != mac_region:
                    continue

            # Filter by procedure code
            if procedure_code:
                if procedure_code not in policy.covered_codes:
                    continue

            # Filter by diagnosis code
            if diagnosis_code:
                if diagnosis_code not in policy.covered_diagnosis_codes:
                    if not self._diagnosis_matches(diagnosis_code, policy.covered_diagnosis_codes):
                        continue

            results.append(policy)

        return results


# =============================================================================
# Factory Function
# =============================================================================


_lcd_ncd_service: Optional[LCDNCDService] = None


def get_lcd_ncd_service(
    db_session=None,
    cache_service=None,
) -> LCDNCDService:
    """
    Get or create LCD/NCD service instance.

    Args:
        db_session: Database session
        cache_service: Cache service

    Returns:
        LCDNCDService instance
    """
    global _lcd_ncd_service

    if _lcd_ncd_service is None:
        _lcd_ncd_service = LCDNCDService(
            db_session=db_session,
            cache_service=cache_service,
        )

    return _lcd_ncd_service
