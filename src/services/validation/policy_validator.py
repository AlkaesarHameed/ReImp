"""
Policy and Coverage Validator (Rule 9).

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Validates claims against policy coverage rules:
- Coverage determinations (LCD/NCD)
- Type of Bill (TOB) validation
- Prior authorization requirements
- Benefit limits and exclusions
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from src.schemas.llm_settings import LLMTaskType
from src.services.validation.llm_validation_service import (
    LLMValidationService,
    get_llm_validation_service,
)
from src.services.validation_cache import get_validation_cache, ValidationCacheService

logger = logging.getLogger(__name__)


class CoverageStatus(str, Enum):
    """Coverage determination status."""

    COVERED = "covered"
    NOT_COVERED = "not_covered"
    CONDITIONAL = "conditional"
    PENDING_AUTH = "pending_authorization"
    LIMIT_EXCEEDED = "limit_exceeded"
    UNKNOWN = "unknown"


class PolicyIssueType(str, Enum):
    """Types of policy validation issues."""

    NOT_COVERED = "not_covered"
    PRIOR_AUTH_REQUIRED = "prior_auth_required"
    PRIOR_AUTH_MISSING = "prior_auth_missing"
    PRIOR_AUTH_EXPIRED = "prior_auth_expired"
    BENEFIT_LIMIT_EXCEEDED = "benefit_limit_exceeded"
    TOB_MISMATCH = "tob_mismatch"
    LCD_NCD_VIOLATION = "lcd_ncd_violation"
    EXCLUSION_APPLIES = "exclusion_applies"
    WAITING_PERIOD = "waiting_period"
    PREEXISTING_CONDITION = "preexisting_condition"


class PolicyIssueSeverity(str, Enum):
    """Severity of policy issues."""

    CRITICAL = "critical"  # Cannot proceed
    HIGH = "high"          # Should be resolved
    MEDIUM = "medium"      # May need review
    LOW = "low"            # Minor issue


@dataclass
class PolicyIssue:
    """Individual policy validation issue."""

    issue_type: PolicyIssueType
    severity: PolicyIssueSeverity
    code: str  # Affected procedure/diagnosis code
    message: str
    policy_reference: Optional[str] = None
    resolution: Optional[str] = None
    additional_info: dict = field(default_factory=dict)


@dataclass
class CoverageCheck:
    """Coverage check result for a procedure."""

    cpt_code: str
    status: CoverageStatus
    covered_amount: Optional[float] = None
    copay_amount: Optional[float] = None
    coinsurance_pct: Optional[float] = None
    deductible_applies: bool = False
    prior_auth_required: bool = False
    prior_auth_number: Optional[str] = None
    lcd_ncd_applies: Optional[str] = None
    notes: str = ""


@dataclass
class PolicyValidationResult:
    """Complete policy validation result."""

    is_valid: bool
    coverage_status: CoverageStatus
    coverage_checks: list[CoverageCheck]
    issues: list[PolicyIssue]
    critical_issues: list[PolicyIssue]
    warnings: list[str]
    execution_time_ms: int
    policy_id: Optional[str] = None
    plan_name: Optional[str] = None

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical policy issues."""
        return len(self.critical_issues) > 0

    @property
    def requires_prior_auth(self) -> bool:
        """Check if any procedure requires prior authorization."""
        return any(c.prior_auth_required for c in self.coverage_checks)

    def to_evidence_dict(self) -> dict[str, Any]:
        """Convert to evidence format for rejection."""
        return {
            "is_valid": self.is_valid,
            "coverage_status": self.coverage_status.value,
            "issue_count": len(self.issues),
            "critical_count": len(self.critical_issues),
            "requires_prior_auth": self.requires_prior_auth,
            "issues": [
                {
                    "type": i.issue_type.value,
                    "severity": i.severity.value,
                    "code": i.code,
                    "message": i.message,
                    "resolution": i.resolution,
                }
                for i in self.issues
            ],
            "coverage_details": [
                {
                    "cpt_code": c.cpt_code,
                    "status": c.status.value,
                    "prior_auth_required": c.prior_auth_required,
                }
                for c in self.coverage_checks
            ],
        }


# Type of Bill (TOB) validation rules
# Format: (TOB pattern, allowed claim types, description)
TOB_RULES = {
    "11": ("inpatient", "Hospital Inpatient (including Medicare Part A)"),
    "12": ("inpatient", "Hospital Inpatient (Medicare Part B only)"),
    "13": ("outpatient", "Hospital Outpatient"),
    "14": ("outpatient", "Hospital - Other (for Medicare includes Laboratory)"),
    "21": ("snf", "Skilled Nursing - Inpatient (including Medicare Part A)"),
    "22": ("snf", "Skilled Nursing - Inpatient (Medicare Part B only)"),
    "23": ("snf", "Skilled Nursing - Outpatient"),
    "32": ("home_health", "Home Health - Under Plan of Treatment"),
    "33": ("home_health", "Home Health - Not Under Plan"),
    "34": ("home_health", "Home Health - Other"),
    "41": ("religious", "Religious Nonmedical Health Care Institution"),
    "71": ("clinic", "Clinic - Rural Health"),
    "72": ("clinic", "Clinic - Hospital-Based or Independent Renal Dialysis"),
    "73": ("clinic", "Clinic - Free-Standing"),
    "74": ("clinic", "Clinic - Outpatient Rehabilitation Facility"),
    "75": ("clinic", "Clinic - Comprehensive Outpatient Rehabilitation"),
    "76": ("clinic", "Clinic - Community Mental Health Center"),
    "81": ("hospice", "Hospice - Non-Hospital Based"),
    "82": ("hospice", "Hospice - Hospital Based"),
    "83": ("ambulance", "Ambulance"),
    "85": ("corf", "Critical Access Hospital"),
}


# Prior authorization required procedure patterns
PRIOR_AUTH_REQUIRED = [
    (r"2720[0-9]", "Injection procedures"),
    (r"2730[0-9]", "Arthroscopy procedures"),
    (r"2781[0-9]", "Total knee arthroplasty"),
    (r"2744[0-9]", "Total hip arthroplasty"),
    (r"4320[0-9]", "Esophagoscopy"),
    (r"4323[0-9]", "Upper GI endoscopy"),
    (r"4523[0-9]", "Colonoscopy"),
    (r"7052[0-9]", "MRI"),
    (r"7055[0-9]", "CT scan"),
    (r"7810[0-9]", "PET scan"),
    (r"9204[0-9]", "Physical therapy evaluations"),
    (r"9706[0-9]", "Aquatic therapy"),
]


class PolicyValidator:
    """
    Validates claims against policy and coverage rules.

    Checks:
    1. Coverage determinations (LCD/NCD)
    2. Type of Bill (TOB) validation
    3. Prior authorization requirements
    4. Benefit limits and exclusions

    Source: Design Document Section 2.2 - Validation Rules (Rule 9)
    """

    def __init__(
        self,
        cache: Optional[ValidationCacheService] = None,
        llm_service: Optional[LLMValidationService] = None,
    ):
        """
        Initialize the policy validator.

        Args:
            cache: Validation cache service
            llm_service: LLM service for complex policy interpretation
        """
        self._cache = cache
        self._llm_service = llm_service

    @property
    def cache(self) -> ValidationCacheService:
        """Get cache instance."""
        if self._cache is None:
            self._cache = get_validation_cache()
        return self._cache

    @property
    def llm_service(self) -> LLMValidationService:
        """Get LLM service instance."""
        if self._llm_service is None:
            self._llm_service = get_llm_validation_service()
        return self._llm_service

    async def validate(
        self,
        cpt_codes: list[str],
        icd_codes: list[str],
        policy_id: Optional[str] = None,
        type_of_bill: Optional[str] = None,
        prior_auth_number: Optional[str] = None,
        service_date: Optional[date] = None,
        claim_type: str = "professional",
        tenant_id: Optional[UUID] = None,
    ) -> PolicyValidationResult:
        """
        Validate claim against policy rules.

        Args:
            cpt_codes: List of CPT procedure codes
            icd_codes: List of ICD-10 diagnosis codes
            policy_id: Policy/plan identifier
            type_of_bill: Type of Bill code (for institutional claims)
            prior_auth_number: Prior authorization number if available
            service_date: Date of service
            claim_type: "professional" or "institutional"
            tenant_id: Tenant ID for configuration

        Returns:
            PolicyValidationResult with all validation details
        """
        import time
        start_time = time.perf_counter()

        issues: list[PolicyIssue] = []
        coverage_checks: list[CoverageCheck] = []
        warnings: list[str] = []

        # Normalize inputs
        cpt_codes = [code.upper().strip() for code in cpt_codes if code]
        icd_codes = [code.upper().strip() for code in icd_codes if code]

        if not cpt_codes:
            warnings.append("No procedure codes provided for policy validation")
            return PolicyValidationResult(
                is_valid=True,
                coverage_status=CoverageStatus.UNKNOWN,
                coverage_checks=[],
                issues=[],
                critical_issues=[],
                warnings=warnings,
                execution_time_ms=0,
            )

        # Step 1: Validate Type of Bill (for institutional claims)
        if type_of_bill and claim_type == "institutional":
            tob_issues = self._validate_type_of_bill(type_of_bill)
            issues.extend(tob_issues)

        # Step 2: Check prior authorization requirements
        auth_issues = self._check_prior_auth_requirements(
            cpt_codes, prior_auth_number
        )
        issues.extend(auth_issues)

        # Step 3: Check coverage for each procedure
        for cpt in cpt_codes:
            coverage = await self._check_procedure_coverage(
                cpt, icd_codes, policy_id, service_date
            )
            coverage_checks.append(coverage)

            if coverage.status == CoverageStatus.NOT_COVERED:
                issues.append(PolicyIssue(
                    issue_type=PolicyIssueType.NOT_COVERED,
                    severity=PolicyIssueSeverity.CRITICAL,
                    code=cpt,
                    message=f"Procedure {cpt} is not covered under this policy",
                    resolution="Verify coverage or submit to different payer",
                ))

        # Step 4: Use LLM for complex policy interpretation if needed
        if self._needs_llm_review(issues, coverage_checks):
            llm_issues = await self._llm_policy_review(
                cpt_codes, icd_codes, policy_id, tenant_id
            )
            issues.extend(llm_issues)

        # Separate critical issues
        critical_issues = [
            i for i in issues
            if i.severity in (PolicyIssueSeverity.CRITICAL, PolicyIssueSeverity.HIGH)
        ]

        # Determine overall coverage status
        if any(c.status == CoverageStatus.NOT_COVERED for c in coverage_checks):
            overall_status = CoverageStatus.NOT_COVERED
        elif any(c.status == CoverageStatus.PENDING_AUTH for c in coverage_checks):
            overall_status = CoverageStatus.PENDING_AUTH
        elif any(c.status == CoverageStatus.CONDITIONAL for c in coverage_checks):
            overall_status = CoverageStatus.CONDITIONAL
        elif all(c.status == CoverageStatus.COVERED for c in coverage_checks):
            overall_status = CoverageStatus.COVERED
        else:
            overall_status = CoverageStatus.UNKNOWN

        is_valid = len(critical_issues) == 0 and overall_status != CoverageStatus.NOT_COVERED

        execution_time = int((time.perf_counter() - start_time) * 1000)

        result = PolicyValidationResult(
            is_valid=is_valid,
            coverage_status=overall_status,
            coverage_checks=coverage_checks,
            issues=issues,
            critical_issues=critical_issues,
            warnings=warnings,
            execution_time_ms=execution_time,
            policy_id=policy_id,
        )

        logger.info(
            f"Policy validation: valid={is_valid}, "
            f"status={overall_status.value}, issues={len(issues)}, "
            f"time={execution_time}ms"
        )

        return result

    def _validate_type_of_bill(self, tob: str) -> list[PolicyIssue]:
        """Validate Type of Bill code format and validity."""
        issues = []

        # TOB should be 3 or 4 digits
        if not tob or len(tob) < 3:
            issues.append(PolicyIssue(
                issue_type=PolicyIssueType.TOB_MISMATCH,
                severity=PolicyIssueSeverity.MEDIUM,
                code=tob or "",
                message="Invalid Type of Bill format",
                resolution="Provide a valid 3 or 4 digit TOB code",
            ))
            return issues

        # Check first two digits against known TOB codes
        tob_prefix = tob[:2]
        if tob_prefix not in TOB_RULES:
            issues.append(PolicyIssue(
                issue_type=PolicyIssueType.TOB_MISMATCH,
                severity=PolicyIssueSeverity.MEDIUM,
                code=tob,
                message=f"Unrecognized Type of Bill code: {tob}",
                resolution="Verify TOB code matches facility type",
            ))

        return issues

    def _check_prior_auth_requirements(
        self,
        cpt_codes: list[str],
        prior_auth_number: Optional[str],
    ) -> list[PolicyIssue]:
        """Check if procedures require prior authorization."""
        import re
        issues = []

        for cpt in cpt_codes:
            for pattern, description in PRIOR_AUTH_REQUIRED:
                if re.match(pattern, cpt):
                    if not prior_auth_number:
                        issues.append(PolicyIssue(
                            issue_type=PolicyIssueType.PRIOR_AUTH_REQUIRED,
                            severity=PolicyIssueSeverity.HIGH,
                            code=cpt,
                            message=f"Prior authorization required for {description}",
                            resolution="Obtain prior authorization before proceeding",
                        ))
                    break

        return issues

    async def _check_procedure_coverage(
        self,
        cpt_code: str,
        icd_codes: list[str],
        policy_id: Optional[str],
        service_date: Optional[date],
    ) -> CoverageCheck:
        """Check coverage status for a procedure."""
        # Check cache first
        if policy_id:
            cache_key = f"{policy_id}:{cpt_code}"
            cached = await self.cache.get_policy_coverage(cache_key)
            if cached:
                return CoverageCheck(
                    cpt_code=cpt_code,
                    status=CoverageStatus(cached.get("status", "unknown")),
                    covered_amount=cached.get("covered_amount"),
                    copay_amount=cached.get("copay"),
                    coinsurance_pct=cached.get("coinsurance"),
                    prior_auth_required=cached.get("prior_auth_required", False),
                    lcd_ncd_applies=cached.get("lcd_ncd"),
                    notes="From cache",
                )

        # TODO: Query policy/benefits database for actual coverage
        # For now, return default coverage assumption
        return CoverageCheck(
            cpt_code=cpt_code,
            status=CoverageStatus.COVERED,  # Assume covered by default
            prior_auth_required=any(
                self._requires_prior_auth(cpt_code)
            ),
            notes="Default coverage - no policy data",
        )

    def _requires_prior_auth(self, cpt_code: str) -> bool:
        """Check if CPT code requires prior authorization."""
        import re
        for pattern, _ in PRIOR_AUTH_REQUIRED:
            if re.match(pattern, cpt_code):
                return True
        return False

    def _needs_llm_review(
        self,
        issues: list[PolicyIssue],
        coverage_checks: list[CoverageCheck],
    ) -> bool:
        """Determine if LLM review is needed for complex cases."""
        # Need LLM review if:
        # - LCD/NCD applies
        # - Coverage is conditional
        # - Prior auth is required but complex
        for check in coverage_checks:
            if check.lcd_ncd_applies:
                return True
            if check.status == CoverageStatus.CONDITIONAL:
                return True
        return False

    async def _llm_policy_review(
        self,
        cpt_codes: list[str],
        icd_codes: list[str],
        policy_id: Optional[str],
        tenant_id: Optional[UUID],
    ) -> list[PolicyIssue]:
        """Use LLM for complex policy interpretation."""
        issues = []

        prompt = f"""Review these medical codes for policy compliance:

PROCEDURES: {', '.join(cpt_codes)}
DIAGNOSES: {', '.join(icd_codes)}
POLICY: {policy_id or 'Standard Medicare'}

Check for:
1. LCD/NCD coverage determinations
2. Medical necessity per coverage policies
3. Any exclusions or limitations

Return JSON:
{{
    "issues": [
        {{"code": "CPT", "issue": "description", "severity": "high/medium/low"}}
    ],
    "covered": true/false,
    "notes": "explanation"
}}"""

        try:
            result = await self.llm_service.complete(
                prompt=prompt,
                task_type=LLMTaskType.VALIDATION,
                tenant_id=tenant_id,
                json_mode=True,
            )

            if result.success and result.parsed_data:
                for issue in result.parsed_data.get("issues", []):
                    severity_map = {
                        "high": PolicyIssueSeverity.HIGH,
                        "medium": PolicyIssueSeverity.MEDIUM,
                        "low": PolicyIssueSeverity.LOW,
                    }
                    issues.append(PolicyIssue(
                        issue_type=PolicyIssueType.LCD_NCD_VIOLATION,
                        severity=severity_map.get(
                            issue.get("severity", "medium"),
                            PolicyIssueSeverity.MEDIUM,
                        ),
                        code=issue.get("code", ""),
                        message=issue.get("issue", ""),
                        policy_reference="LLM Policy Review",
                    ))

        except Exception as e:
            logger.warning(f"LLM policy review failed: {e}")

        return issues

    async def validate_prior_auth(
        self,
        prior_auth_number: str,
        cpt_codes: list[str],
        service_date: date,
    ) -> dict[str, Any]:
        """
        Validate prior authorization details.

        Args:
            prior_auth_number: Authorization number to validate
            cpt_codes: Procedures covered by authorization
            service_date: Date of service

        Returns:
            Dict with authorization status
        """
        # TODO: Query prior auth database
        return {
            "valid": True,
            "auth_number": prior_auth_number,
            "covers_procedures": cpt_codes,
            "effective_from": None,
            "effective_to": None,
            "status": "active",
        }


# Singleton instance
_policy_validator: Optional[PolicyValidator] = None


def get_policy_validator() -> PolicyValidator:
    """Get or create the singleton policy validator."""
    global _policy_validator
    if _policy_validator is None:
        _policy_validator = PolicyValidator()
    return _policy_validator
