"""
Medical Validation Orchestrator Service.
Source: Design Document Section 4.1 - Medical Validation
Verified: 2025-12-18

Orchestrates all medical validation services for comprehensive claim validation.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from src.services.medical.code_validator import (
    CodeSystem,
    CodeValidationResult,
    MedicalCodeValidator,
    get_code_validator,
)
from src.services.medical.code_mapper import (
    DiagnosisProcedureMapper,
    MappingResult,
    get_code_mapper,
)
from src.services.medical.necessity import (
    MedicalNecessityService,
    NecessityResult,
    NecessityStatus,
    get_necessity_service,
)
from src.services.medical.compatibility import (
    CompatibilityResult,
    ProcedureCompatibilityChecker,
    get_compatibility_checker,
)


class MedicalValidationStatus(str, Enum):
    """Overall medical validation status."""

    VALID = "valid"
    VALID_WITH_WARNINGS = "valid_with_warnings"
    REQUIRES_REVIEW = "requires_review"
    INVALID = "invalid"


class MedicalValidationResult(BaseModel):
    """Comprehensive medical validation result."""

    # Overall status
    status: MedicalValidationStatus = MedicalValidationStatus.VALID
    is_valid: bool = True
    confidence_score: float = 1.0

    # Input codes
    diagnosis_codes: list[str] = Field(default_factory=list)
    procedure_codes: list[str] = Field(default_factory=list)
    country: str = "US"

    # Code validation results
    diagnosis_validation: list[CodeValidationResult] = Field(default_factory=list)
    procedure_validation: list[CodeValidationResult] = Field(default_factory=list)

    # Mapping validation
    mapping_result: Optional[dict] = None

    # Medical necessity
    necessity_result: Optional[NecessityResult] = None

    # Procedure compatibility
    compatibility_result: Optional[CompatibilityResult] = None

    # Clinically implausible check
    implausibility_check: Optional[dict] = None

    # Summary
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    # Processing details
    checks_performed: list[str] = Field(default_factory=list)


class MedicalValidationService:
    """
    Orchestrates comprehensive medical validation for claims.

    Performs:
    1. Code format and database validation
    2. Diagnosis-procedure mapping validation
    3. Medical necessity validation
    4. Procedure compatibility checking
    5. Clinically implausible detection
    """

    def __init__(
        self,
        code_validator: Optional[MedicalCodeValidator] = None,
        code_mapper: Optional[DiagnosisProcedureMapper] = None,
        necessity_service: Optional[MedicalNecessityService] = None,
        compatibility_checker: Optional[ProcedureCompatibilityChecker] = None,
    ):
        """
        Initialize MedicalValidationService.

        Args:
            code_validator: MedicalCodeValidator instance
            code_mapper: DiagnosisProcedureMapper instance
            necessity_service: MedicalNecessityService instance
            compatibility_checker: ProcedureCompatibilityChecker instance
        """
        self.code_validator = code_validator or get_code_validator()
        self.code_mapper = code_mapper or get_code_mapper()
        self.necessity_service = necessity_service or get_necessity_service()
        self.compatibility_checker = compatibility_checker or get_compatibility_checker()

    async def validate_claim(
        self,
        diagnosis_codes: list[str],
        procedure_codes: list[str],
        member_age: Optional[int] = None,
        member_gender: Optional[str] = None,
        procedure_history: Optional[dict[str, int]] = None,
        modifiers: Optional[dict[str, list[str]]] = None,
        country: str = "US",
        skip_code_validation: bool = False,
        skip_mapping_validation: bool = False,
        skip_necessity_check: bool = False,
        skip_compatibility_check: bool = False,
        skip_implausibility_check: bool = False,
    ) -> MedicalValidationResult:
        """
        Perform comprehensive medical validation on a claim.

        Args:
            diagnosis_codes: List of ICD-10 diagnosis codes
            procedure_codes: List of CPT/ACHI procedure codes
            member_age: Member age in years
            member_gender: Member gender (M/F)
            procedure_history: Dict of procedure_code: count_this_year
            modifiers: Dict of procedure_code: list of modifiers
            country: Country code (US or AU)
            skip_code_validation: Skip code format/database validation
            skip_mapping_validation: Skip diagnosis-procedure mapping
            skip_necessity_check: Skip medical necessity validation
            skip_compatibility_check: Skip procedure compatibility check
            skip_implausibility_check: Skip clinically implausible detection

        Returns:
            MedicalValidationResult with comprehensive validation details
        """
        result = MedicalValidationResult(
            diagnosis_codes=diagnosis_codes,
            procedure_codes=procedure_codes,
            country=country,
        )

        confidence_scores = []

        # Step 1: Validate code formats and existence
        if not skip_code_validation:
            result.checks_performed.append("code_validation")

            # Validate diagnosis codes
            dx_system = CodeSystem.ICD10_AM if country.upper() == "AU" else CodeSystem.ICD10_CM
            result.diagnosis_validation = self.code_validator.validate_codes(
                diagnosis_codes, dx_system
            )

            for dv in result.diagnosis_validation:
                if not dv.is_valid:
                    result.errors.append(f"Invalid diagnosis code: {dv.code} - {dv.error_message}")
                elif dv.warnings:
                    result.warnings.extend(dv.warnings)

            # Validate procedure codes
            px_system = CodeSystem.ACHI if country.upper() == "AU" else CodeSystem.CPT
            result.procedure_validation = self.code_validator.validate_codes(
                procedure_codes, px_system
            )

            for pv in result.procedure_validation:
                if not pv.is_valid:
                    result.errors.append(f"Invalid procedure code: {pv.code} - {pv.error_message}")
                elif pv.warnings:
                    result.warnings.extend(pv.warnings)

            # Calculate code validation confidence
            all_valid = all(dv.is_valid for dv in result.diagnosis_validation) and \
                       all(pv.is_valid for pv in result.procedure_validation)
            confidence_scores.append(1.0 if all_valid else 0.3)

        # Step 2: Validate diagnosis-procedure mapping
        if not skip_mapping_validation:
            result.checks_performed.append("mapping_validation")

            mapping_result = self.code_mapper.validate_claim_codes(
                diagnosis_codes, procedure_codes, country
            )
            result.mapping_result = mapping_result

            if not mapping_result["is_valid"]:
                result.errors.extend(mapping_result.get("warnings", []))
            else:
                result.warnings.extend(mapping_result.get("warnings", []))

            result.recommendations.extend(mapping_result.get("suggestions", []))
            confidence_scores.append(mapping_result.get("overall_confidence", 1.0))

        # Step 3: Medical necessity validation
        if not skip_necessity_check:
            result.checks_performed.append("necessity_validation")

            result.necessity_result = self.necessity_service.validate_necessity(
                diagnosis_codes,
                procedure_codes,
                member_age,
                member_gender,
                procedure_history,
                country,
            )

            if not result.necessity_result.is_medically_necessary:
                result.errors.extend(result.necessity_result.issues)
            else:
                result.warnings.extend(result.necessity_result.warnings)

            result.recommendations.extend(result.necessity_result.recommendations)
            confidence_scores.append(result.necessity_result.confidence_score)

        # Step 4: Procedure compatibility check
        if not skip_compatibility_check:
            result.checks_performed.append("compatibility_check")

            result.compatibility_result = self.compatibility_checker.check_compatibility(
                procedure_codes, modifiers, same_day=True
            )

            if not result.compatibility_result.is_compatible:
                for issue in result.compatibility_result.issues:
                    if issue.is_blocking:
                        result.errors.append(issue.description)
                    else:
                        result.warnings.append(issue.description)

            result.warnings.extend(result.compatibility_result.warnings)
            result.recommendations.extend(result.compatibility_result.recommendations)

            if not result.compatibility_result.is_compatible:
                confidence_scores.append(0.2)
            else:
                confidence_scores.append(1.0)

        # Step 5: Clinically implausible detection
        if not skip_implausibility_check and member_age is not None:
            result.checks_performed.append("implausibility_check")

            result.implausibility_check = self.necessity_service.check_clinically_implausible(
                diagnosis_codes, procedure_codes, member_age, member_gender
            )

            if result.implausibility_check["is_implausible"]:
                for flag in result.implausibility_check["flags"]:
                    if result.implausibility_check["severity"] == "high":
                        result.errors.append(f"Clinically implausible: {flag}")
                    else:
                        result.warnings.append(f"Possible issue: {flag}")

                severity_scores = {"high": 0.1, "medium": 0.4, "low": 0.7, "none": 1.0}
                confidence_scores.append(
                    severity_scores.get(result.implausibility_check["severity"], 1.0)
                )

        # Calculate overall status
        result.confidence_score = min(confidence_scores) if confidence_scores else 1.0

        has_errors = len(result.errors) > 0
        has_warnings = len(result.warnings) > 0

        if has_errors:
            result.is_valid = False
            result.status = MedicalValidationStatus.INVALID
        elif result.confidence_score < 0.5:
            result.is_valid = True
            result.status = MedicalValidationStatus.REQUIRES_REVIEW
        elif has_warnings:
            result.is_valid = True
            result.status = MedicalValidationStatus.VALID_WITH_WARNINGS
        else:
            result.is_valid = True
            result.status = MedicalValidationStatus.VALID

        return result

    async def quick_validate(
        self,
        diagnosis_codes: list[str],
        procedure_codes: list[str],
        country: str = "US",
    ) -> bool:
        """
        Quick validation without full details.

        Args:
            diagnosis_codes: List of diagnosis codes
            procedure_codes: List of procedure codes
            country: Country code

        Returns:
            True if claim passes basic validation
        """
        # Quick code format check
        dx_system = CodeSystem.ICD10_AM if country.upper() == "AU" else CodeSystem.ICD10_CM
        px_system = CodeSystem.ACHI if country.upper() == "AU" else CodeSystem.CPT

        for dx in diagnosis_codes:
            if not self.code_validator.is_valid_format(dx, dx_system):
                return False

        for px in procedure_codes:
            if not self.code_validator.is_valid_format(px, px_system):
                return False

        # Quick compatibility check
        compat_result = self.compatibility_checker.check_compatibility(procedure_codes)
        if not compat_result.is_compatible:
            return False

        return True

    def get_supported_code_systems(self) -> list[str]:
        """Get list of supported code systems."""
        return [cs.value for cs in CodeSystem]


# =============================================================================
# Factory Functions
# =============================================================================


_medical_validation_service: Optional[MedicalValidationService] = None


def get_medical_validation_service(
    code_validator: Optional[MedicalCodeValidator] = None,
    code_mapper: Optional[DiagnosisProcedureMapper] = None,
    necessity_service: Optional[MedicalNecessityService] = None,
    compatibility_checker: Optional[ProcedureCompatibilityChecker] = None,
) -> MedicalValidationService:
    """Get singleton MedicalValidationService instance."""
    global _medical_validation_service
    if _medical_validation_service is None:
        _medical_validation_service = MedicalValidationService(
            code_validator, code_mapper, necessity_service, compatibility_checker
        )
    return _medical_validation_service


def create_medical_validation_service(
    code_validator: Optional[MedicalCodeValidator] = None,
    code_mapper: Optional[DiagnosisProcedureMapper] = None,
    necessity_service: Optional[MedicalNecessityService] = None,
    compatibility_checker: Optional[ProcedureCompatibilityChecker] = None,
) -> MedicalValidationService:
    """Create a new MedicalValidationService instance."""
    return MedicalValidationService(
        code_validator, code_mapper, necessity_service, compatibility_checker
    )
