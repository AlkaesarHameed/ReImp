"""
Medical Necessity Validation Service.
Source: Design Document Section 4.1 - Medical Validation
Verified: 2025-12-18

Validates medical necessity based on diagnosis, procedure, and patient demographics.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from src.services.medical.code_validator import CodeSystem, MedicalCodeValidator, get_code_validator
from src.services.medical.code_mapper import DiagnosisProcedureMapper, get_code_mapper


class NecessityStatus(str, Enum):
    """Medical necessity determination status."""

    MEDICALLY_NECESSARY = "medically_necessary"
    NOT_MEDICALLY_NECESSARY = "not_medically_necessary"
    REQUIRES_REVIEW = "requires_review"
    INSUFFICIENT_INFO = "insufficient_info"


class NecessityResult(BaseModel):
    """Result of medical necessity validation."""

    is_medically_necessary: bool = True
    status: NecessityStatus = NecessityStatus.MEDICALLY_NECESSARY
    confidence_score: float = 1.0

    # Validation details
    diagnosis_supports_procedure: bool = True
    age_appropriate: bool = True
    gender_appropriate: bool = True
    frequency_appropriate: bool = True

    # Issues and warnings
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    # Context
    diagnosis_codes: list[str] = Field(default_factory=list)
    procedure_codes: list[str] = Field(default_factory=list)


class MedicalNecessityService:
    """
    Validates medical necessity for claim procedures.

    Checks:
    - Diagnosis supports procedure
    - Age appropriateness
    - Gender appropriateness
    - Frequency limits
    - Clinical guidelines
    """

    # Frequency limits (procedure: max per year)
    FREQUENCY_LIMITS = {
        "77067": 1,  # Screening mammography - 1 per year
        "99385": 1,  # Preventive visit 18-39 - 1 per year
        "99386": 1,  # Preventive visit 40-64 - 1 per year
        "99387": 1,  # Preventive visit 65+ - 1 per year
        "83036": 4,  # HbA1c - up to 4 per year for diabetics
        "80061": 1,  # Lipid panel - 1 per year routine
        "45378": 1,  # Colonoscopy - every 10 years (simplified)
    }

    # Procedures requiring specific diagnoses
    REQUIRED_DIAGNOSES = {
        "27447": ["M17.11", "M17.12"],  # Total knee requires knee OA
        "27130": ["M16.11", "M16.12"],  # Total hip requires hip OA
        "77067": ["Z12.31", "C50.911", "C50.912"],  # Mammogram requires screening/breast dx
        "43239": ["K21.0", "K21.9", "K20.0"],  # EGD requires GI diagnosis
    }

    def __init__(
        self,
        code_validator: Optional[MedicalCodeValidator] = None,
        code_mapper: Optional[DiagnosisProcedureMapper] = None,
    ):
        """
        Initialize MedicalNecessityService.

        Args:
            code_validator: MedicalCodeValidator instance
            code_mapper: DiagnosisProcedureMapper instance
        """
        self.code_validator = code_validator or get_code_validator()
        self.code_mapper = code_mapper or get_code_mapper()

    def validate_necessity(
        self,
        diagnosis_codes: list[str],
        procedure_codes: list[str],
        member_age: Optional[int] = None,
        member_gender: Optional[str] = None,
        procedure_history: Optional[dict[str, int]] = None,
        country: str = "US",
    ) -> NecessityResult:
        """
        Validate medical necessity for claim procedures.

        Args:
            diagnosis_codes: List of ICD-10 diagnosis codes
            procedure_codes: List of CPT/ACHI procedure codes
            member_age: Member age in years
            member_gender: Member gender (M/F)
            procedure_history: Dict of procedure_code: count_this_year
            country: Country code (US or AU)

        Returns:
            NecessityResult with validation details
        """
        result = NecessityResult(
            diagnosis_codes=diagnosis_codes,
            procedure_codes=procedure_codes,
        )

        # Validate each procedure
        for procedure_code in procedure_codes:
            # Check diagnosis supports procedure
            dx_support_result = self._check_diagnosis_supports_procedure(
                diagnosis_codes, procedure_code, country
            )
            if not dx_support_result["supported"]:
                result.diagnosis_supports_procedure = False
                result.issues.extend(dx_support_result.get("issues", []))

            # Check age appropriateness
            if member_age is not None:
                age_result = self._check_age_appropriate(procedure_code, member_age, country)
                if not age_result["appropriate"]:
                    result.age_appropriate = False
                    result.issues.extend(age_result.get("issues", []))

            # Check gender appropriateness
            if member_gender is not None:
                gender_result = self._check_gender_appropriate(
                    procedure_code, member_gender, country
                )
                if not gender_result["appropriate"]:
                    result.gender_appropriate = False
                    result.issues.extend(gender_result.get("issues", []))

            # Check frequency
            if procedure_history:
                freq_result = self._check_frequency(procedure_code, procedure_history)
                if not freq_result["appropriate"]:
                    result.frequency_appropriate = False
                    result.issues.extend(freq_result.get("issues", []))
                    result.warnings.extend(freq_result.get("warnings", []))

        # Determine overall necessity status
        result.is_medically_necessary = all([
            result.diagnosis_supports_procedure,
            result.age_appropriate,
            result.gender_appropriate,
            result.frequency_appropriate,
        ])

        if result.is_medically_necessary:
            result.status = NecessityStatus.MEDICALLY_NECESSARY
            result.confidence_score = 1.0
        elif not result.diagnosis_supports_procedure:
            result.status = NecessityStatus.NOT_MEDICALLY_NECESSARY
            result.confidence_score = 0.2
        elif not result.age_appropriate or not result.gender_appropriate:
            result.status = NecessityStatus.NOT_MEDICALLY_NECESSARY
            result.confidence_score = 0.1
        elif not result.frequency_appropriate:
            result.status = NecessityStatus.REQUIRES_REVIEW
            result.confidence_score = 0.5
            result.recommendations.append("Manual review for frequency exception")

        return result

    def _check_diagnosis_supports_procedure(
        self,
        diagnosis_codes: list[str],
        procedure_code: str,
        country: str,
    ) -> dict:
        """Check if any diagnosis supports the procedure."""
        result = {"supported": False, "issues": []}

        # Check required diagnoses first
        required_dx = self.REQUIRED_DIAGNOSES.get(procedure_code)
        if required_dx:
            if any(dx in diagnosis_codes for dx in required_dx):
                result["supported"] = True
                return result
            else:
                result["issues"].append(
                    f"Procedure {procedure_code} requires one of: {', '.join(required_dx)}"
                )
                return result

        # Check via code mapper
        for dx_code in diagnosis_codes:
            mapping_result = self.code_mapper.validate_combination(
                dx_code, procedure_code, country
            )
            if mapping_result.is_valid_combination and mapping_result.confidence_score >= 0.5:
                result["supported"] = True
                return result

        # No strong mapping found, but may still be valid
        result["supported"] = True  # Default to supported with warning
        result["issues"].append(
            f"No established diagnosis-procedure relationship. "
            f"Diagnoses: {diagnosis_codes}, Procedure: {procedure_code}"
        )

        return result

    def _check_age_appropriate(
        self,
        procedure_code: str,
        member_age: int,
        country: str,
    ) -> dict:
        """Check if procedure is age-appropriate."""
        result = {"appropriate": True, "issues": []}

        px_system = CodeSystem.ACHI if country.upper() == "AU" else CodeSystem.CPT
        age_restrictions = self.code_validator.get_age_restrictions(procedure_code, px_system)

        if age_restrictions:
            min_age, max_age = age_restrictions
            if not (min_age <= member_age <= max_age):
                result["appropriate"] = False
                result["issues"].append(
                    f"Procedure {procedure_code} requires age {min_age}-{max_age}, "
                    f"member age is {member_age}"
                )

        # Additional age-specific checks
        age_specific_rules = {
            "77067": (40, 999, "Screening mammography"),
            "84153": (50, 999, "PSA screening"),
            "99385": (18, 39, "Preventive visit 18-39"),
            "99386": (40, 64, "Preventive visit 40-64"),
            "99387": (65, 999, "Preventive visit 65+"),
        }

        rule = age_specific_rules.get(procedure_code)
        if rule:
            min_age, max_age, name = rule
            if not (min_age <= member_age <= max_age):
                result["appropriate"] = False
                result["issues"].append(
                    f"{name} ({procedure_code}) requires age {min_age}-{max_age}, "
                    f"member age is {member_age}"
                )

        return result

    def _check_gender_appropriate(
        self,
        procedure_code: str,
        member_gender: str,
        country: str,
    ) -> dict:
        """Check if procedure is gender-appropriate."""
        result = {"appropriate": True, "issues": []}

        px_system = CodeSystem.ACHI if country.upper() == "AU" else CodeSystem.CPT
        gender_specific = self.code_validator.get_gender_specific(procedure_code, px_system)

        if gender_specific:
            if member_gender.upper() != gender_specific:
                result["appropriate"] = False
                result["issues"].append(
                    f"Procedure {procedure_code} is gender-specific for {gender_specific}, "
                    f"member gender is {member_gender}"
                )

        # Additional gender-specific checks
        gender_specific_rules = {
            "77067": ("F", "Screening mammography"),
            "G0101": ("F", "Pelvic exam"),
            "84153": ("M", "PSA"),
            "55700": ("M", "Prostate biopsy"),
            "76872": ("M", "Transrectal ultrasound"),
            "19301": ("F", "Partial mastectomy"),
            "19120": ("F", "Breast excision"),
        }

        rule = gender_specific_rules.get(procedure_code)
        if rule:
            required_gender, name = rule
            if member_gender.upper() != required_gender:
                result["appropriate"] = False
                result["issues"].append(
                    f"{name} ({procedure_code}) is gender-specific for {required_gender}, "
                    f"member gender is {member_gender}"
                )

        return result

    def _check_frequency(
        self,
        procedure_code: str,
        procedure_history: dict[str, int],
    ) -> dict:
        """Check if procedure frequency is within limits."""
        result = {"appropriate": True, "issues": [], "warnings": []}

        limit = self.FREQUENCY_LIMITS.get(procedure_code)
        if limit is not None:
            current_count = procedure_history.get(procedure_code, 0)
            if current_count >= limit:
                result["appropriate"] = False
                result["issues"].append(
                    f"Procedure {procedure_code} exceeds frequency limit. "
                    f"Limit: {limit}/year, Current: {current_count}"
                )
            elif current_count == limit - 1:
                result["warnings"].append(
                    f"This will use the final allowed {procedure_code} for the year"
                )

        return result

    def check_clinically_implausible(
        self,
        diagnosis_codes: list[str],
        procedure_codes: list[str],
        member_age: Optional[int] = None,
        member_gender: Optional[str] = None,
    ) -> dict:
        """
        Check for clinically implausible combinations.

        Args:
            diagnosis_codes: List of diagnosis codes
            procedure_codes: List of procedure codes
            member_age: Member age
            member_gender: Member gender

        Returns:
            Dict with implausibility findings
        """
        result = {
            "is_implausible": False,
            "flags": [],
            "severity": "none",  # none, low, medium, high
        }

        # Pediatric diagnoses on adults
        pediatric_dx = {"P", "Q"}  # Perinatal, congenital
        if member_age and member_age > 18:
            for dx in diagnosis_codes:
                if dx[0] in pediatric_dx:
                    result["is_implausible"] = True
                    result["flags"].append(f"Pediatric diagnosis {dx} on adult patient")
                    result["severity"] = "medium"

        # Pregnancy diagnosis on male
        if member_gender and member_gender.upper() == "M":
            for dx in diagnosis_codes:
                if dx.startswith("O"):  # Pregnancy chapter
                    result["is_implausible"] = True
                    result["flags"].append(f"Pregnancy diagnosis {dx} on male patient")
                    result["severity"] = "high"

        # Gender-specific cancer mismatches
        if member_gender:
            gender = member_gender.upper()
            for dx in diagnosis_codes:
                # Prostate cancer on female
                if dx.startswith("C61") and gender == "F":
                    result["is_implausible"] = True
                    result["flags"].append("Prostate cancer diagnosis on female patient")
                    result["severity"] = "high"
                # Ovarian cancer on male
                if dx.startswith("C56") and gender == "M":
                    result["is_implausible"] = True
                    result["flags"].append("Ovarian cancer diagnosis on male patient")
                    result["severity"] = "high"

        # Age-implausible diagnoses
        if member_age:
            # Senile dementia in young patient
            if member_age < 40:
                for dx in diagnosis_codes:
                    if dx.startswith("F01") or dx.startswith("F03"):
                        result["is_implausible"] = True
                        result["flags"].append(f"Dementia diagnosis {dx} on patient under 40")
                        result["severity"] = "medium"

            # Pediatric developmental on elderly
            if member_age > 65:
                for dx in diagnosis_codes:
                    if dx.startswith("F80") or dx.startswith("F81"):  # Developmental disorders
                        result["flags"].append(
                            f"Developmental diagnosis {dx} on elderly patient (unusual)"
                        )
                        if result["severity"] == "none":
                            result["severity"] = "low"

        return result


# =============================================================================
# Factory Functions
# =============================================================================


_necessity_service: Optional[MedicalNecessityService] = None


def get_necessity_service(
    code_validator: Optional[MedicalCodeValidator] = None,
    code_mapper: Optional[DiagnosisProcedureMapper] = None,
) -> MedicalNecessityService:
    """Get singleton MedicalNecessityService instance."""
    global _necessity_service
    if _necessity_service is None:
        _necessity_service = MedicalNecessityService(code_validator, code_mapper)
    return _necessity_service


def create_necessity_service(
    code_validator: Optional[MedicalCodeValidator] = None,
    code_mapper: Optional[DiagnosisProcedureMapper] = None,
) -> MedicalNecessityService:
    """Create a new MedicalNecessityService instance."""
    return MedicalNecessityService(code_validator, code_mapper)
