"""
Demographic Validator (Rules 7-8).

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Validates that diagnoses and procedures are appropriate for:
- Patient age (Rule 7)
- Patient gender (Rule 8)
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from src.gateways.search_gateway import get_search_gateway, SearchGateway
from src.schemas.medical_codes import GenderRestriction

logger = logging.getLogger(__name__)


class DemographicIssueType(str, Enum):
    """Types of demographic validation issues."""

    AGE_TOO_YOUNG = "age_too_young"
    AGE_TOO_OLD = "age_too_old"
    AGE_OUT_OF_RANGE = "age_out_of_range"
    GENDER_MISMATCH = "gender_mismatch"
    PREGNANCY_MALE = "pregnancy_male"
    PEDIATRIC_ADULT = "pediatric_adult"
    NEWBORN_INVALID = "newborn_invalid"


class IssueSeverity(str, Enum):
    """Severity of the demographic issue."""

    CRITICAL = "critical"  # Definite error (male pregnancy)
    HIGH = "high"          # Likely error (age range violation)
    MEDIUM = "medium"      # Needs review
    LOW = "low"            # Minor inconsistency


@dataclass
class DemographicIssue:
    """Result of a demographic validation check."""

    has_issue: bool
    issue_type: Optional[DemographicIssueType]
    severity: IssueSeverity
    code: str
    code_type: str  # "diagnosis" or "procedure"
    message: str
    patient_value: Optional[str] = None  # Actual patient age/gender
    expected_value: Optional[str] = None  # Expected age range/gender
    resolution: Optional[str] = None
    reference: Optional[str] = None


@dataclass
class DemographicValidationResult:
    """Complete demographic validation result."""

    is_valid: bool
    issues: list[DemographicIssue]
    critical_issues: list[DemographicIssue]
    warnings: list[str]
    execution_time_ms: int
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical demographic issues."""
        return len(self.critical_issues) > 0

    def to_evidence_dict(self) -> dict[str, Any]:
        """Convert to evidence format for rejection."""
        return {
            "is_valid": self.is_valid,
            "issue_count": len(self.issues),
            "critical_count": len(self.critical_issues),
            "patient_age": self.patient_age,
            "patient_gender": self.patient_gender,
            "issues": [
                {
                    "type": i.issue_type.value if i.issue_type else None,
                    "severity": i.severity.value,
                    "code": i.code,
                    "code_type": i.code_type,
                    "message": i.message,
                    "patient_value": i.patient_value,
                    "expected_value": i.expected_value,
                    "resolution": i.resolution,
                }
                for i in self.issues
            ],
        }


# Age group definitions
class AgeGroup(str, Enum):
    """Standard age groups for medical coding."""

    NEWBORN = "newborn"        # 0-28 days
    INFANT = "infant"          # 29 days - 1 year
    CHILD = "child"            # 1-12 years
    ADOLESCENT = "adolescent"  # 13-17 years
    ADULT = "adult"            # 18-64 years
    ELDERLY = "elderly"        # 65+ years


def get_age_group(age_years: int, age_days: int = 0) -> AgeGroup:
    """Determine age group from age in years and days."""
    if age_years == 0:
        if age_days <= 28:
            return AgeGroup.NEWBORN
        return AgeGroup.INFANT
    elif age_years < 13:
        return AgeGroup.CHILD
    elif age_years < 18:
        return AgeGroup.ADOLESCENT
    elif age_years < 65:
        return AgeGroup.ADULT
    else:
        return AgeGroup.ELDERLY


# Age-specific code patterns
# Format: (pattern, min_age, max_age, description)
AGE_RESTRICTED_CODES = [
    # Newborn codes (P00-P96)
    (r"P[0-8][0-9]", 0, 0, "Perinatal conditions are only valid for newborns"),
    (r"P9[0-6]", 0, 0, "Perinatal conditions are only valid for newborns"),

    # Congenital conditions can be coded at any age but typically diagnosed early
    # (Z38 - Liveborn infants according to place of birth and type of delivery)
    (r"Z38\.", 0, 0, "Liveborn infant codes only valid at birth"),

    # Pediatric-only conditions
    (r"Q[0-9]", None, 18, "Congenital conditions typically diagnosed before age 18"),

    # Adult-onset conditions
    (r"F03\.9", 65, None, "Unspecified dementia typically in elderly"),

    # Pregnancy codes (age 10-55 typical, but we'll use 12-55 as strict)
    (r"O[0-9]", 12, 55, "Pregnancy-related conditions"),
    (r"Z3[2-7]\.", 12, 55, "Pregnancy-related encounter codes"),

    # Age-specific cancer screening
    (r"Z12\.31", 40, None, "Mammography screening typically age 40+"),
    (r"Z12\.11", 45, None, "Colonoscopy screening typically age 45+"),

    # Pediatric vaccines
    (r"Z23", None, None, "Vaccines - verify age-appropriate"),

    # Age-related macular degeneration
    (r"H35\.3", 50, None, "Age-related macular degeneration typically age 50+"),

    # Benign prostatic hyperplasia
    (r"N40\.", 40, None, "BPH typically in males age 40+"),

    # Menopause
    (r"N95\.", 40, None, "Menopausal conditions typically age 40+"),
]

# Gender-specific code patterns
# Format: (pattern, gender, description)
GENDER_RESTRICTED_CODES = [
    # Male-only conditions
    (r"N40\.", "M", "Benign prostatic hyperplasia - male only"),
    (r"N41\.", "M", "Inflammatory diseases of prostate - male only"),
    (r"N42\.", "M", "Other disorders of prostate - male only"),
    (r"N43\.", "M", "Hydrocele and spermatocele - male only"),
    (r"N44\.", "M", "Noninflammatory disorders of testis - male only"),
    (r"N45\.", "M", "Orchitis and epididymitis - male only"),
    (r"N46\.", "M", "Male infertility - male only"),
    (r"N47\.", "M", "Disorders of prepuce - male only"),
    (r"N48\.", "M", "Other disorders of penis - male only"),
    (r"N49\.", "M", "Inflammatory disorders of male genital organs - male only"),
    (r"N50\.", "M", "Other disorders of male genital organs - male only"),
    (r"C61", "M", "Malignant neoplasm of prostate - male only"),
    (r"C62\.", "M", "Malignant neoplasm of testis - male only"),
    (r"C63\.", "M", "Malignant neoplasm of other male genital organs - male only"),
    (r"D07\.5", "M", "Carcinoma in situ of prostate - male only"),
    (r"D29\.", "M", "Benign neoplasm of male genital organs - male only"),
    (r"D40\.", "M", "Neoplasm uncertain behavior male genital organs - male only"),

    # Female-only conditions
    (r"N70\.", "F", "Salpingitis and oophoritis - female only"),
    (r"N71\.", "F", "Inflammatory disease of uterus - female only"),
    (r"N72", "F", "Inflammatory disease of cervix uteri - female only"),
    (r"N73\.", "F", "Other female pelvic inflammatory diseases - female only"),
    (r"N74\.", "F", "Female pelvic inflammatory disorders - female only"),
    (r"N75\.", "F", "Diseases of Bartholin's gland - female only"),
    (r"N76\.", "F", "Other inflammation of vagina and vulva - female only"),
    (r"N77\.", "F", "Vulvovaginal ulceration - female only"),
    (r"N80\.", "F", "Endometriosis - female only"),
    (r"N81\.", "F", "Female genital prolapse - female only"),
    (r"N82\.", "F", "Fistulae involving female genital tract - female only"),
    (r"N83\.", "F", "Noninflammatory disorders of ovary - female only"),
    (r"N84\.", "F", "Polyp of female genital tract - female only"),
    (r"N85\.", "F", "Other noninflammatory disorders of uterus - female only"),
    (r"N86", "F", "Erosion and ectropion of cervix uteri - female only"),
    (r"N87\.", "F", "Dysplasia of cervix uteri - female only"),
    (r"N88\.", "F", "Other noninflammatory disorders of cervix - female only"),
    (r"N89\.", "F", "Other noninflammatory disorders of vagina - female only"),
    (r"N90\.", "F", "Other noninflammatory disorders of vulva - female only"),
    (r"N91\.", "F", "Absent, scanty and rare menstruation - female only"),
    (r"N92\.", "F", "Excessive, frequent menstruation - female only"),
    (r"N93\.", "F", "Other abnormal uterine bleeding - female only"),
    (r"N94\.", "F", "Pain associated with female genital organs - female only"),
    (r"N95\.", "F", "Menopausal and perimenopausal disorders - female only"),
    (r"N96", "F", "Recurrent pregnancy loss - female only"),
    (r"N97\.", "F", "Female infertility - female only"),
    (r"N98\.", "F", "Complications from artificial fertilization - female only"),
    (r"O[0-9]", "F", "Pregnancy, childbirth, puerperium - female only"),
    (r"C5[0-8]\.", "F", "Malignant neoplasm of female breast/genital organs - female only"),
    (r"D06\.", "F", "Carcinoma in situ of cervix uteri - female only"),
    (r"D07\.[0-3]", "F", "Carcinoma in situ of female genital organs - female only"),
    (r"D25\.", "F", "Leiomyoma of uterus - female only"),
    (r"D26\.", "F", "Other benign neoplasms of uterus - female only"),
    (r"D27\.", "F", "Benign neoplasm of ovary - female only"),
    (r"D28\.", "F", "Benign neoplasm of other female genital organs - female only"),
    (r"D39\.", "F", "Neoplasm uncertain behavior female genital organs - female only"),
    (r"Z30\.", "F", "Encounter for contraceptive management - typically female"),
    (r"Z3[2-7]\.", "F", "Pregnancy-related encounters - female only"),
]


class DemographicValidator:
    """
    Validates demographic appropriateness of diagnoses and procedures.

    Checks:
    1. Age appropriateness of diagnosis codes (Rule 7)
    2. Gender appropriateness of diagnosis codes (Rule 8)

    Source: Design Document Section 2.2 - Validation Rules (Rules 7-8)
    """

    def __init__(
        self,
        search_gateway: Optional[SearchGateway] = None,
    ):
        """
        Initialize the demographic validator.

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
        cpt_codes: Optional[list[str]] = None,
        patient_age_years: Optional[int] = None,
        patient_age_days: int = 0,
        patient_gender: Optional[str] = None,
    ) -> DemographicValidationResult:
        """
        Validate all codes against patient demographics.

        Args:
            icd_codes: List of ICD-10 diagnosis codes
            cpt_codes: Optional list of CPT procedure codes
            patient_age_years: Patient age in years
            patient_age_days: Additional days (for newborns)
            patient_gender: Patient gender ("M" or "F")

        Returns:
            DemographicValidationResult with all issues found
        """
        import time
        start_time = time.perf_counter()

        issues: list[DemographicIssue] = []
        warnings: list[str] = []
        cpt_codes = cpt_codes or []

        # Normalize codes
        icd_codes = [self._normalize_code(code) for code in icd_codes if code]
        cpt_codes = [code.upper().strip() for code in cpt_codes if code]

        # Normalize gender
        if patient_gender:
            patient_gender = patient_gender.upper().strip()
            if patient_gender not in ("M", "F"):
                warnings.append(f"Unknown gender value: {patient_gender}")
                patient_gender = None

        # Check for missing demographics
        if patient_age_years is None:
            warnings.append("Patient age not provided - age validation skipped")
        if patient_gender is None:
            warnings.append("Patient gender not provided - gender validation skipped")

        # Validate age appropriateness (Rule 7)
        if patient_age_years is not None:
            age_issues = self._validate_age_appropriateness(
                icd_codes, patient_age_years, patient_age_days
            )
            issues.extend(age_issues)

        # Validate gender appropriateness (Rule 8)
        if patient_gender:
            gender_issues = await self._validate_gender_appropriateness(
                icd_codes, cpt_codes, patient_gender
            )
            issues.extend(gender_issues)

        # Separate critical issues
        critical_issues = [
            i for i in issues
            if i.severity in (IssueSeverity.CRITICAL, IssueSeverity.HIGH)
        ]

        is_valid = len(critical_issues) == 0

        execution_time = int((time.perf_counter() - start_time) * 1000)

        result = DemographicValidationResult(
            is_valid=is_valid,
            issues=issues,
            critical_issues=critical_issues,
            warnings=warnings,
            execution_time_ms=execution_time,
            patient_age=patient_age_years,
            patient_gender=patient_gender,
        )

        logger.info(
            f"Demographic validation: valid={is_valid}, "
            f"issues={len(issues)}, critical={len(critical_issues)}, "
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

    def _validate_age_appropriateness(
        self,
        icd_codes: list[str],
        patient_age_years: int,
        patient_age_days: int,
    ) -> list[DemographicIssue]:
        """Validate age appropriateness of diagnosis codes."""
        issues = []
        age_group = get_age_group(patient_age_years, patient_age_days)

        for code in icd_codes:
            for pattern, min_age, max_age, description in AGE_RESTRICTED_CODES:
                if re.match(pattern, code):
                    # Check minimum age
                    if min_age is not None and patient_age_years < min_age:
                        severity = IssueSeverity.HIGH
                        if pattern.startswith("O") and patient_age_years < 10:
                            severity = IssueSeverity.CRITICAL

                        issues.append(DemographicIssue(
                            has_issue=True,
                            issue_type=DemographicIssueType.AGE_TOO_YOUNG,
                            severity=severity,
                            code=code,
                            code_type="diagnosis",
                            message=(
                                f"{description}: Patient age {patient_age_years} "
                                f"below minimum age {min_age}"
                            ),
                            patient_value=str(patient_age_years),
                            expected_value=f"Age >= {min_age}",
                            resolution="Verify patient age or review diagnosis code",
                            reference="ICD-10-CM Age Edit Guidelines",
                        ))
                        break

                    # Check maximum age
                    if max_age is not None and patient_age_years > max_age:
                        severity = IssueSeverity.HIGH
                        # Perinatal codes on non-newborns are critical
                        if pattern.startswith("P") or pattern.startswith("Z38"):
                            severity = IssueSeverity.CRITICAL

                        issues.append(DemographicIssue(
                            has_issue=True,
                            issue_type=DemographicIssueType.AGE_TOO_OLD,
                            severity=severity,
                            code=code,
                            code_type="diagnosis",
                            message=(
                                f"{description}: Patient age {patient_age_years} "
                                f"above maximum age {max_age}"
                            ),
                            patient_value=str(patient_age_years),
                            expected_value=f"Age <= {max_age}",
                            resolution="Verify patient age or review diagnosis code",
                            reference="ICD-10-CM Age Edit Guidelines",
                        ))
                        break

        # Check age-group specific validations
        issues.extend(self._validate_age_group_codes(icd_codes, age_group, patient_age_years))

        return issues

    def _validate_age_group_codes(
        self,
        icd_codes: list[str],
        age_group: AgeGroup,
        patient_age: int,
    ) -> list[DemographicIssue]:
        """Validate codes based on age groups."""
        issues = []

        for code in icd_codes:
            # Newborn-specific checks
            if age_group == AgeGroup.NEWBORN:
                # Adult-onset conditions on newborns
                if re.match(r"(N40|H35\.3|F03\.9)", code):
                    issues.append(DemographicIssue(
                        has_issue=True,
                        issue_type=DemographicIssueType.NEWBORN_INVALID,
                        severity=IssueSeverity.CRITICAL,
                        code=code,
                        code_type="diagnosis",
                        message=f"Adult-onset condition {code} invalid for newborn",
                        patient_value="Newborn",
                        expected_value="Adult",
                        resolution="Review diagnosis - condition not applicable to newborns",
                        reference="ICD-10-CM Age Edit Guidelines",
                    ))

            # Pediatric/adult checks
            if age_group in (AgeGroup.CHILD, AgeGroup.INFANT, AgeGroup.NEWBORN):
                # Check for adult-only procedures/conditions
                if re.match(r"N95\.", code):  # Menopausal disorders
                    issues.append(DemographicIssue(
                        has_issue=True,
                        issue_type=DemographicIssueType.PEDIATRIC_ADULT,
                        severity=IssueSeverity.CRITICAL,
                        code=code,
                        code_type="diagnosis",
                        message=f"Adult condition {code} invalid for pediatric patient age {patient_age}",
                        patient_value=str(patient_age),
                        expected_value="Age >= 40",
                        resolution="Review diagnosis - condition typically seen in adults",
                        reference="ICD-10-CM Age Edit Guidelines",
                    ))

        return issues

    async def _validate_gender_appropriateness(
        self,
        icd_codes: list[str],
        cpt_codes: list[str],
        patient_gender: str,
    ) -> list[DemographicIssue]:
        """Validate gender appropriateness of diagnosis and procedure codes."""
        issues = []

        # Check ICD codes against pattern rules
        for code in icd_codes:
            issue = self._check_gender_pattern(code, patient_gender, "diagnosis")
            if issue:
                issues.append(issue)

        # Check ICD codes against database gender restrictions
        for code in icd_codes:
            try:
                icd_info = await self.search_gateway.get_icd10_by_code(code)
                if icd_info and icd_info.gender_restriction != GenderRestriction.NONE:
                    required_gender = icd_info.gender_restriction.value
                    if patient_gender != required_gender:
                        # Critical if it's a definite mismatch
                        severity = IssueSeverity.CRITICAL
                        if code.startswith("O"):  # Pregnancy on male
                            message = f"Pregnancy code {code} invalid for male patient"
                        else:
                            gender_name = "male" if required_gender == "M" else "female"
                            message = f"Code {code} is {gender_name}-only condition"

                        issues.append(DemographicIssue(
                            has_issue=True,
                            issue_type=DemographicIssueType.GENDER_MISMATCH,
                            severity=severity,
                            code=code,
                            code_type="diagnosis",
                            message=message,
                            patient_value=patient_gender,
                            expected_value=required_gender,
                            resolution="Verify patient gender or review diagnosis code",
                            reference="ICD-10-CM Sex Edit Guidelines",
                        ))
            except Exception as e:
                logger.debug(f"Could not lookup code {code} for gender check: {e}")

        # Check CPT codes against database gender restrictions
        for code in cpt_codes:
            try:
                cpt_info = await self.search_gateway.get_cpt_by_code(code)
                if cpt_info and cpt_info.gender_restriction != GenderRestriction.NONE:
                    required_gender = cpt_info.gender_restriction.value
                    if patient_gender != required_gender:
                        gender_name = "male" if required_gender == "M" else "female"
                        issues.append(DemographicIssue(
                            has_issue=True,
                            issue_type=DemographicIssueType.GENDER_MISMATCH,
                            severity=IssueSeverity.CRITICAL,
                            code=code,
                            code_type="procedure",
                            message=f"Procedure {code} is {gender_name}-only",
                            patient_value=patient_gender,
                            expected_value=required_gender,
                            resolution="Verify patient gender or review procedure code",
                            reference="CPT Sex-Specific Edit Guidelines",
                        ))
            except Exception as e:
                logger.debug(f"Could not lookup CPT {code} for gender check: {e}")

        return issues

    def _check_gender_pattern(
        self,
        code: str,
        patient_gender: str,
        code_type: str,
    ) -> Optional[DemographicIssue]:
        """Check code against gender pattern rules."""
        for pattern, required_gender, description in GENDER_RESTRICTED_CODES:
            if re.match(pattern, code):
                if patient_gender != required_gender:
                    # Pregnancy codes on males are critical
                    if pattern.startswith("O") and patient_gender == "M":
                        issue_type = DemographicIssueType.PREGNANCY_MALE
                        severity = IssueSeverity.CRITICAL
                        message = f"Pregnancy code {code} cannot be assigned to male patient"
                    else:
                        issue_type = DemographicIssueType.GENDER_MISMATCH
                        severity = IssueSeverity.CRITICAL
                        gender_name = "male" if required_gender == "M" else "female"
                        message = f"{description} - patient is {patient_gender}"

                    return DemographicIssue(
                        has_issue=True,
                        issue_type=issue_type,
                        severity=severity,
                        code=code,
                        code_type=code_type,
                        message=message,
                        patient_value=patient_gender,
                        expected_value=required_gender,
                        resolution="Verify patient gender or review diagnosis code",
                        reference="ICD-10-CM Sex Edit Guidelines",
                    )

        return None

    async def validate_single_code(
        self,
        code: str,
        patient_age_years: Optional[int] = None,
        patient_gender: Optional[str] = None,
    ) -> list[DemographicIssue]:
        """
        Validate a single code against demographics.

        Convenience method for single-code validation.

        Args:
            code: ICD-10 or CPT code
            patient_age_years: Patient age in years
            patient_gender: Patient gender ("M" or "F")

        Returns:
            List of DemographicIssue if any issues found
        """
        result = await self.validate(
            icd_codes=[code],
            patient_age_years=patient_age_years,
            patient_gender=patient_gender,
        )
        return result.issues


# Singleton instance
_demographic_validator: Optional[DemographicValidator] = None


def get_demographic_validator() -> DemographicValidator:
    """Get or create the singleton demographic validator."""
    global _demographic_validator
    if _demographic_validator is None:
        _demographic_validator = DemographicValidator()
    return _demographic_validator
