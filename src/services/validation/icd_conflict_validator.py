"""
ICD×ICD Conflict Validator (Rule 6).

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Detects invalid combinations of ICD-10 diagnosis codes:
- Mutually exclusive diagnoses
- Manifestation codes without etiology
- Sequencing errors
- Logical inconsistencies
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from src.gateways.search_gateway import get_search_gateway, SearchGateway

logger = logging.getLogger(__name__)


class ConflictType(str, Enum):
    """Types of ICD-10 code conflicts."""

    MUTUALLY_EXCLUSIVE = "mutually_exclusive"
    MANIFESTATION_WITHOUT_ETIOLOGY = "manifestation_without_etiology"
    ETIOLOGY_WITHOUT_MANIFESTATION = "etiology_without_manifestation"
    SEQUENCING_ERROR = "sequencing_error"
    DUPLICATE_CODE = "duplicate_code"
    GENDER_CONFLICT = "gender_conflict"
    AGE_CONFLICT = "age_conflict"
    LOGICAL_INCONSISTENCY = "logical_inconsistency"


class ConflictSeverity(str, Enum):
    """Severity of the conflict."""

    CRITICAL = "critical"  # Must be resolved
    HIGH = "high"          # Should be reviewed
    MEDIUM = "medium"      # May need clarification
    LOW = "low"            # Minor issue


@dataclass
class ConflictResult:
    """Result of a conflict check between codes."""

    has_conflict: bool
    conflict_type: Optional[ConflictType]
    severity: ConflictSeverity
    code1: str
    code2: Optional[str]  # May be None for single-code issues
    message: str
    resolution: Optional[str] = None
    reference: Optional[str] = None


@dataclass
class ICDConflictValidationResult:
    """Complete ICD conflict validation result."""

    is_valid: bool
    conflicts: list[ConflictResult]
    critical_conflicts: list[ConflictResult]
    warnings: list[str]
    execution_time_ms: int

    @property
    def has_critical_conflicts(self) -> bool:
        """Check if there are critical conflicts."""
        return len(self.critical_conflicts) > 0

    def to_evidence_dict(self) -> dict[str, Any]:
        """Convert to evidence format for rejection."""
        return {
            "is_valid": self.is_valid,
            "conflict_count": len(self.conflicts),
            "critical_count": len(self.critical_conflicts),
            "conflicts": [
                {
                    "type": c.conflict_type.value if c.conflict_type else None,
                    "severity": c.severity.value,
                    "codes": [c.code1, c.code2] if c.code2 else [c.code1],
                    "message": c.message,
                    "resolution": c.resolution,
                }
                for c in self.conflicts
            ],
        }


# Mutually exclusive code pairs
# Format: (code1_pattern, code2_pattern, message)
MUTUALLY_EXCLUSIVE_PAIRS = [
    # Type 1 and Type 2 diabetes are mutually exclusive
    (r"E10\.", r"E11\.", "Type 1 and Type 2 diabetes cannot coexist"),
    (r"E10\.", r"E13\.", "Type 1 and other specified diabetes cannot coexist"),
    (r"E11\.", r"E13\.", "Type 2 and other specified diabetes cannot coexist"),

    # Acute and chronic conditions that are mutually exclusive
    (r"J03\.", r"J35\.0", "Acute and chronic tonsillitis cannot coexist"),
    (r"K35\.", r"K36", "Acute appendicitis and other appendicitis cannot coexist"),

    # Left and right eye for same condition
    (r"H40\.11", r"H40\.12", "Primary open-angle glaucoma cannot affect both eyes differently"),

    # Pregnancy and non-pregnancy conditions
    (r"O[0-8]", r"Z33\.1", "Cannot have both pregnancy complication and non-pregnant state"),

    # Living and deceased status
    (r"Z76\.0", r"R99", "Cannot have both encounter for aftercare and unspecified death"),
]

# Manifestation codes that require etiology codes
# Format: (manifestation_pattern, required_etiology_patterns, message)
MANIFESTATION_REQUIREMENTS = [
    # Diabetic manifestations require diabetes code
    (r"E08\.3[0-9]", [r"E08\."], "Diabetic eye complications require underlying diabetes code"),
    (r"E09\.3[0-9]", [r"E09\."], "Drug-induced diabetic eye complications require underlying code"),
    (r"E10\.3[0-9]", [r"E10\."], "Type 1 diabetic eye complications require underlying diabetes code"),
    (r"E11\.3[0-9]", [r"E11\."], "Type 2 diabetic eye complications require underlying diabetes code"),

    # Neurological manifestations
    (r"G63", [r"E08\.", r"E09\.", r"E10\.", r"E11\.", r"E13\."], "Polyneuropathy in diseases requires underlying condition"),

    # Infectious manifestations
    (r"B20", [r"B97\."], "HIV disease requires viral agent code"),
]

# Sequencing rules (first code must come before second)
SEQUENCING_RULES = [
    # Etiology before manifestation
    (r"E1[0-3]\.", r"G63", "Diabetes codes should be sequenced before polyneuropathy"),
    (r"A[0-4]", r"B9[0-7]", "Infectious disease codes should precede organism codes"),

    # External cause after injury
    (r"V\d", r"S\d", "External cause codes should follow injury codes"),
    (r"W\d", r"S\d", "External cause codes should follow injury codes"),
    (r"X\d", r"S\d", "External cause codes should follow injury codes"),
]


class ICDConflictValidator:
    """
    Validates ICD-10 code combinations for conflicts.

    Checks:
    1. Mutually exclusive diagnoses
    2. Manifestation codes without required etiology
    3. Sequencing errors
    4. Logical inconsistencies

    Source: Design Document Section 2.2 - Validation Rules (Rule 6)
    """

    def __init__(
        self,
        search_gateway: Optional[SearchGateway] = None,
    ):
        """
        Initialize the conflict validator.

        Args:
            search_gateway: Typesense search gateway for code lookups
        """
        self._search_gateway = search_gateway

    @property
    def search_gateway(self) -> SearchGateway:
        """Get search gateway instance."""
        if self._search_gateway is None:
            self._search_gateway = get_search_gateway()
        return self._search_gateway

    async def validate(
        self,
        icd_codes: list[str],
    ) -> ICDConflictValidationResult:
        """
        Validate all ICD-10 codes for conflicts.

        Args:
            icd_codes: List of ICD-10 diagnosis codes

        Returns:
            ICDConflictValidationResult with all conflicts found
        """
        import time
        start_time = time.perf_counter()

        conflicts: list[ConflictResult] = []
        warnings: list[str] = []

        # Normalize codes
        icd_codes = [self._normalize_code(code) for code in icd_codes if code]

        if not icd_codes:
            warnings.append("No ICD-10 codes provided for conflict validation")
            return ICDConflictValidationResult(
                is_valid=True,
                conflicts=[],
                critical_conflicts=[],
                warnings=warnings,
                execution_time_ms=0,
            )

        # Check for duplicates
        duplicates = self._check_duplicates(icd_codes)
        conflicts.extend(duplicates)

        # Check mutually exclusive pairs
        exclusive_conflicts = self._check_mutually_exclusive(icd_codes)
        conflicts.extend(exclusive_conflicts)

        # Check manifestation requirements
        manifestation_conflicts = self._check_manifestation_requirements(icd_codes)
        conflicts.extend(manifestation_conflicts)

        # Check sequencing (if order matters)
        sequencing_conflicts = self._check_sequencing(icd_codes)
        conflicts.extend(sequencing_conflicts)

        # Check logical inconsistencies
        logical_conflicts = await self._check_logical_inconsistencies(icd_codes)
        conflicts.extend(logical_conflicts)

        # Separate critical conflicts
        critical_conflicts = [
            c for c in conflicts
            if c.severity in (ConflictSeverity.CRITICAL, ConflictSeverity.HIGH)
        ]

        is_valid = len(critical_conflicts) == 0

        execution_time = int((time.perf_counter() - start_time) * 1000)

        result = ICDConflictValidationResult(
            is_valid=is_valid,
            conflicts=conflicts,
            critical_conflicts=critical_conflicts,
            warnings=warnings,
            execution_time_ms=execution_time,
        )

        logger.info(
            f"ICD conflict validation: valid={is_valid}, "
            f"conflicts={len(conflicts)}, critical={len(critical_conflicts)}, "
            f"time={execution_time}ms"
        )

        return result

    def _normalize_code(self, code: str) -> str:
        """Normalize ICD-10 code format."""
        code = code.upper().strip()
        # Add decimal if missing
        if len(code) > 3 and "." not in code:
            code = f"{code[:3]}.{code[3:]}"
        return code

    def _check_duplicates(self, codes: list[str]) -> list[ConflictResult]:
        """Check for duplicate codes."""
        conflicts = []
        seen = set()

        for code in codes:
            if code in seen:
                conflicts.append(ConflictResult(
                    has_conflict=True,
                    conflict_type=ConflictType.DUPLICATE_CODE,
                    severity=ConflictSeverity.MEDIUM,
                    code1=code,
                    code2=None,
                    message=f"Duplicate diagnosis code: {code}",
                    resolution="Remove duplicate code",
                ))
            seen.add(code)

        return conflicts

    def _check_mutually_exclusive(self, codes: list[str]) -> list[ConflictResult]:
        """Check for mutually exclusive code pairs."""
        conflicts = []

        for i, code1 in enumerate(codes):
            for code2 in codes[i+1:]:
                for pattern1, pattern2, message in MUTUALLY_EXCLUSIVE_PAIRS:
                    if (
                        (re.match(pattern1, code1) and re.match(pattern2, code2)) or
                        (re.match(pattern2, code1) and re.match(pattern1, code2))
                    ):
                        conflicts.append(ConflictResult(
                            has_conflict=True,
                            conflict_type=ConflictType.MUTUALLY_EXCLUSIVE,
                            severity=ConflictSeverity.CRITICAL,
                            code1=code1,
                            code2=code2,
                            message=f"{message}: {code1} and {code2}",
                            resolution="Review diagnoses and remove one of the conflicting codes",
                            reference="ICD-10-CM Official Guidelines",
                        ))
                        break

        return conflicts

    def _check_manifestation_requirements(self, codes: list[str]) -> list[ConflictResult]:
        """Check that manifestation codes have required etiology codes."""
        conflicts = []

        for code in codes:
            for manifest_pattern, etiology_patterns, message in MANIFESTATION_REQUIREMENTS:
                if re.match(manifest_pattern, code):
                    # Check if any required etiology is present
                    has_etiology = any(
                        any(re.match(etio_pattern, c) for c in codes)
                        for etio_pattern in etiology_patterns
                    )

                    if not has_etiology:
                        conflicts.append(ConflictResult(
                            has_conflict=True,
                            conflict_type=ConflictType.MANIFESTATION_WITHOUT_ETIOLOGY,
                            severity=ConflictSeverity.HIGH,
                            code1=code,
                            code2=None,
                            message=f"{message}: {code} missing required underlying condition",
                            resolution="Add the underlying condition code",
                            reference="ICD-10-CM Official Guidelines Section I.A.13",
                        ))

        return conflicts

    def _check_sequencing(self, codes: list[str]) -> list[ConflictResult]:
        """Check code sequencing order."""
        conflicts = []

        for first_pattern, second_pattern, message in SEQUENCING_RULES:
            first_indices = [
                i for i, c in enumerate(codes) if re.match(first_pattern, c)
            ]
            second_indices = [
                i for i, c in enumerate(codes) if re.match(second_pattern, c)
            ]

            # Check if any "second" code comes before "first" code
            for second_idx in second_indices:
                for first_idx in first_indices:
                    if second_idx < first_idx:
                        conflicts.append(ConflictResult(
                            has_conflict=True,
                            conflict_type=ConflictType.SEQUENCING_ERROR,
                            severity=ConflictSeverity.MEDIUM,
                            code1=codes[first_idx],
                            code2=codes[second_idx],
                            message=f"{message}: {codes[first_idx]} should precede {codes[second_idx]}",
                            resolution="Reorder codes according to coding guidelines",
                            reference="ICD-10-CM Official Guidelines",
                        ))

        return conflicts

    async def _check_logical_inconsistencies(
        self,
        codes: list[str],
    ) -> list[ConflictResult]:
        """Check for logical inconsistencies using code metadata."""
        conflicts = []

        # Check gender conflicts
        male_codes = []
        female_codes = []

        for code in codes:
            try:
                icd_info = await self.search_gateway.get_icd10_by_code(code)
                if icd_info:
                    if icd_info.gender_restriction.value == "M":
                        male_codes.append(code)
                    elif icd_info.gender_restriction.value == "F":
                        female_codes.append(code)
            except Exception as e:
                logger.debug(f"Could not lookup code {code}: {e}")

        if male_codes and female_codes:
            conflicts.append(ConflictResult(
                has_conflict=True,
                conflict_type=ConflictType.GENDER_CONFLICT,
                severity=ConflictSeverity.CRITICAL,
                code1=male_codes[0],
                code2=female_codes[0],
                message=(
                    f"Gender-specific conflict: {male_codes[0]} (male-only) "
                    f"and {female_codes[0]} (female-only) cannot both apply"
                ),
                resolution="Verify patient gender and remove incorrect diagnosis",
                reference="ICD-10-CM Official Guidelines",
            ))

        return conflicts

    async def validate_pair(
        self,
        code1: str,
        code2: str,
    ) -> Optional[ConflictResult]:
        """
        Validate a single pair of codes for conflicts.

        Args:
            code1: First ICD-10 code
            code2: Second ICD-10 code

        Returns:
            ConflictResult if conflict found, None otherwise
        """
        result = await self.validate([code1, code2])
        return result.conflicts[0] if result.conflicts else None


# Singleton instance
_icd_conflict_validator: Optional[ICDConflictValidator] = None


def get_icd_conflict_validator() -> ICDConflictValidator:
    """Get or create the singleton ICD conflict validator."""
    global _icd_conflict_validator
    if _icd_conflict_validator is None:
        _icd_conflict_validator = ICDConflictValidator()
    return _icd_conflict_validator
