"""
Procedure Compatibility Checker Service.
Source: Design Document Section 4.1 - Medical Validation
Verified: 2025-12-18

Checks for incompatible or mutually exclusive procedure combinations.
Implements CCI (Correct Coding Initiative) style edits.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from src.services.medical.code_validator import CodeSystem, MedicalCodeValidator, get_code_validator


class CompatibilityType(str, Enum):
    """Type of compatibility issue."""

    MUTUALLY_EXCLUSIVE = "mutually_exclusive"  # Can't bill both
    BUNDLED = "bundled"  # One is included in the other
    MODIFIER_REQUIRED = "modifier_required"  # Can bill with modifier
    DUPLICATE = "duplicate"  # Same service billed twice
    SAME_DAY_CONFLICT = "same_day_conflict"  # Can't both on same day


class CompatibilityIssue(BaseModel):
    """A compatibility issue between procedures."""

    procedure_code_1: str
    procedure_code_2: str
    issue_type: CompatibilityType
    is_blocking: bool = True  # If true, claim should be denied
    modifier_exception: Optional[str] = None  # Modifier that allows both
    description: str
    edit_code: Optional[str] = None  # CCI edit code


class CompatibilityResult(BaseModel):
    """Result of procedure compatibility check."""

    is_compatible: bool = True
    procedure_codes: list[str] = Field(default_factory=list)
    issues: list[CompatibilityIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ProcedureCompatibilityChecker:
    """
    Checks for incompatible procedure combinations.

    Implements CCI (Correct Coding Initiative) style edits:
    - Column 1/Column 2 edits (bundled procedures)
    - Mutually exclusive edits
    - Modifier exceptions
    """

    # Column 1/Column 2 edits (procedure1 bundles procedure2)
    # Format: (column_1, column_2, modifier_exception)
    BUNDLING_EDITS = [
        # E/M bundling - can't bill 99213 with 99214 same day
        ("99215", "99214", None),
        ("99215", "99213", None),
        ("99214", "99213", None),
        ("99205", "99204", None),
        ("99205", "99203", None),
        ("99204", "99203", None),

        # Lab panel bundling
        ("80053", "80048", None),  # Comprehensive includes basic metabolic
        ("80053", "82565", None),  # Comprehensive includes creatinine
        ("80053", "82947", None),  # Comprehensive includes glucose
        ("80061", "82465", None),  # Lipid panel includes cholesterol

        # Surgical bundling
        ("27447", "27446", None),  # Total knee includes partial
        ("27130", "27125", None),  # Total hip includes hemiarthroplasty
        ("47562", "47563", None),  # Lap chole with cholangiography bundles basic

        # Imaging bundling
        ("71046", "71045", None),  # 2 view chest includes single view
        ("70553", "70552", None),  # MRI with contrast includes without

        # Injection bundling
        ("90471", "90472", "59"),  # First injection bundles subsequent (unless distinct)
    ]

    # Mutually exclusive edits (can't do both on same patient)
    MUTUALLY_EXCLUSIVE = [
        # Bilateral procedures
        ("27447", "27446", "Can't bill total and partial knee same patient"),
        ("27130", "27125", "Can't bill total and hemiarthroplasty same hip"),

        # Conflicting approaches
        ("47562", "47600", "Can't bill laparoscopic and open cholecystectomy"),
        ("43239", "43235", "Can't bill EGD with and without biopsy same session"),

        # Contradictory services
        ("93000", "93010", "Can't bill complete ECG and rhythm strip"),
    ]

    # Procedures that can't be billed on same day
    SAME_DAY_CONFLICTS = [
        # Global surgery conflicts
        ("99213", "10060", "E/M included in minor procedure global"),
        ("99214", "10060", "E/M included in minor procedure global"),

        # Multiple of same category
        ("99385", "99386", "Only one preventive visit per day"),
        ("99385", "99387", "Only one preventive visit per day"),
        ("99386", "99387", "Only one preventive visit per day"),
    ]

    def __init__(self, code_validator: Optional[MedicalCodeValidator] = None):
        """
        Initialize ProcedureCompatibilityChecker.

        Args:
            code_validator: MedicalCodeValidator instance
        """
        self.code_validator = code_validator or get_code_validator()

    def check_compatibility(
        self,
        procedure_codes: list[str],
        modifiers: Optional[dict[str, list[str]]] = None,
        same_day: bool = True,
    ) -> CompatibilityResult:
        """
        Check compatibility of procedure codes.

        Args:
            procedure_codes: List of procedure codes to check
            modifiers: Dict of procedure_code: list of modifiers
            same_day: Whether procedures are on the same day

        Returns:
            CompatibilityResult with issues found
        """
        result = CompatibilityResult(procedure_codes=procedure_codes)

        if modifiers is None:
            modifiers = {}

        # Check for duplicates
        duplicates = self._check_duplicates(procedure_codes)
        result.issues.extend(duplicates)

        # Check bundling edits
        bundling_issues = self._check_bundling(procedure_codes, modifiers)
        result.issues.extend(bundling_issues)

        # Check mutually exclusive
        exclusive_issues = self._check_mutually_exclusive(procedure_codes)
        result.issues.extend(exclusive_issues)

        # Check same day conflicts
        if same_day:
            same_day_issues = self._check_same_day_conflicts(procedure_codes, modifiers)
            result.issues.extend(same_day_issues)

        # Check for suspicious patterns
        pattern_warnings = self._check_suspicious_patterns(procedure_codes)
        result.warnings.extend(pattern_warnings)

        # Determine overall compatibility
        blocking_issues = [i for i in result.issues if i.is_blocking]
        result.is_compatible = len(blocking_issues) == 0

        # Generate recommendations
        for issue in result.issues:
            if issue.modifier_exception:
                result.recommendations.append(
                    f"Add modifier {issue.modifier_exception} to {issue.procedure_code_2} "
                    f"to allow billing with {issue.procedure_code_1}"
                )

        return result

    def _check_duplicates(self, procedure_codes: list[str]) -> list[CompatibilityIssue]:
        """Check for duplicate procedure codes."""
        issues = []
        seen = {}

        for code in procedure_codes:
            if code in seen:
                issues.append(
                    CompatibilityIssue(
                        procedure_code_1=code,
                        procedure_code_2=code,
                        issue_type=CompatibilityType.DUPLICATE,
                        is_blocking=True,
                        description=f"Procedure {code} billed multiple times",
                        edit_code="DUP01",
                    )
                )
            seen[code] = True

        return issues

    def _check_bundling(
        self,
        procedure_codes: list[str],
        modifiers: dict[str, list[str]],
    ) -> list[CompatibilityIssue]:
        """Check for bundling (column 1/column 2) issues."""
        issues = []
        code_set = set(procedure_codes)

        for col1, col2, mod_exception in self.BUNDLING_EDITS:
            if col1 in code_set and col2 in code_set:
                # Check if modifier exception applies
                has_exception = False
                if mod_exception:
                    col2_modifiers = modifiers.get(col2, [])
                    if mod_exception in col2_modifiers:
                        has_exception = True

                if not has_exception:
                    issues.append(
                        CompatibilityIssue(
                            procedure_code_1=col1,
                            procedure_code_2=col2,
                            issue_type=CompatibilityType.BUNDLED,
                            is_blocking=True,
                            modifier_exception=mod_exception,
                            description=f"Procedure {col2} is bundled into {col1}",
                            edit_code="CCI01",
                        )
                    )

        return issues

    def _check_mutually_exclusive(
        self,
        procedure_codes: list[str],
    ) -> list[CompatibilityIssue]:
        """Check for mutually exclusive procedure pairs."""
        issues = []
        code_set = set(procedure_codes)

        for code1, code2, reason in self.MUTUALLY_EXCLUSIVE:
            if code1 in code_set and code2 in code_set:
                issues.append(
                    CompatibilityIssue(
                        procedure_code_1=code1,
                        procedure_code_2=code2,
                        issue_type=CompatibilityType.MUTUALLY_EXCLUSIVE,
                        is_blocking=True,
                        description=reason,
                        edit_code="MUE01",
                    )
                )

        return issues

    def _check_same_day_conflicts(
        self,
        procedure_codes: list[str],
        modifiers: dict[str, list[str]],
    ) -> list[CompatibilityIssue]:
        """Check for same day billing conflicts."""
        issues = []
        code_set = set(procedure_codes)

        for code1, code2, reason in self.SAME_DAY_CONFLICTS:
            if code1 in code_set and code2 in code_set:
                # Check for modifier 25 (significant, separately identifiable E/M)
                code1_mods = modifiers.get(code1, [])
                if "25" not in code1_mods:
                    issues.append(
                        CompatibilityIssue(
                            procedure_code_1=code1,
                            procedure_code_2=code2,
                            issue_type=CompatibilityType.SAME_DAY_CONFLICT,
                            is_blocking=True,
                            modifier_exception="25",
                            description=reason,
                            edit_code="SDC01",
                        )
                    )

        return issues

    def _check_suspicious_patterns(self, procedure_codes: list[str]) -> list[str]:
        """Check for suspicious billing patterns."""
        warnings = []

        # Too many procedures in one visit
        if len(procedure_codes) > 10:
            warnings.append(
                f"Unusually high number of procedures ({len(procedure_codes)}) - "
                "may warrant review"
            )

        # Multiple high-RVU procedures
        high_rvu_procedures = {
            "27447", "27130", "63030", "47562", "19301"
        }
        high_rvu_count = sum(1 for code in procedure_codes if code in high_rvu_procedures)
        if high_rvu_count > 1:
            warnings.append(
                f"Multiple major surgical procedures ({high_rvu_count}) on same claim - "
                "verify appropriate modifiers"
            )

        # Multiple E/M codes
        em_codes = {"99213", "99214", "99215", "99203", "99204", "99205"}
        em_count = sum(1 for code in procedure_codes if code in em_codes)
        if em_count > 1:
            warnings.append(
                f"Multiple E/M codes ({em_count}) on same claim - verify legitimacy"
            )

        return warnings

    def suggest_corrections(
        self,
        result: CompatibilityResult,
    ) -> list[str]:
        """
        Suggest corrections for compatibility issues.

        Args:
            result: CompatibilityResult with issues

        Returns:
            List of suggested corrections
        """
        suggestions = []

        for issue in result.issues:
            if issue.issue_type == CompatibilityType.BUNDLED:
                if issue.modifier_exception:
                    suggestions.append(
                        f"Option 1: Remove {issue.procedure_code_2} (bundled into {issue.procedure_code_1})"
                    )
                    suggestions.append(
                        f"Option 2: Add modifier {issue.modifier_exception} to {issue.procedure_code_2} "
                        f"if service is distinct"
                    )
                else:
                    suggestions.append(
                        f"Remove {issue.procedure_code_2} - bundled into {issue.procedure_code_1}"
                    )

            elif issue.issue_type == CompatibilityType.MUTUALLY_EXCLUSIVE:
                suggestions.append(
                    f"Remove either {issue.procedure_code_1} or {issue.procedure_code_2} - "
                    f"mutually exclusive procedures"
                )

            elif issue.issue_type == CompatibilityType.DUPLICATE:
                suggestions.append(
                    f"Remove duplicate {issue.procedure_code_1} or add appropriate modifier (76, 77)"
                )

            elif issue.issue_type == CompatibilityType.SAME_DAY_CONFLICT:
                if issue.modifier_exception:
                    suggestions.append(
                        f"Add modifier {issue.modifier_exception} to E/M code to indicate "
                        f"significant, separately identifiable service"
                    )

        return suggestions


# =============================================================================
# Factory Functions
# =============================================================================


_compatibility_checker: Optional[ProcedureCompatibilityChecker] = None


def get_compatibility_checker(
    code_validator: Optional[MedicalCodeValidator] = None,
) -> ProcedureCompatibilityChecker:
    """Get singleton ProcedureCompatibilityChecker instance."""
    global _compatibility_checker
    if _compatibility_checker is None:
        _compatibility_checker = ProcedureCompatibilityChecker(code_validator)
    return _compatibility_checker


def create_compatibility_checker(
    code_validator: Optional[MedicalCodeValidator] = None,
) -> ProcedureCompatibilityChecker:
    """Create a new ProcedureCompatibilityChecker instance."""
    return ProcedureCompatibilityChecker(code_validator)
