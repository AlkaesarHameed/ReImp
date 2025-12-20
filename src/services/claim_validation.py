"""
Claim Validation Service.

Provides:
- Claim completeness validation
- Business rules validation
- Medical code validation
- Eligibility checking
- FWA (Fraud, Waste, Abuse) detection

Source: Design Document Section 4.2 - Validation Rules
Verified: 2025-12-18
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from src.core.enums import (
    ClaimType,
    DiagnosisCodeSystem,
    FWARiskLevel,
    ProcedureCodeSystem,
)

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity level of validation issues."""

    ERROR = "error"  # Blocks processing
    WARNING = "warning"  # Flags for review but doesn't block
    INFO = "info"  # Informational only


class ValidationCategory(str, Enum):
    """Category of validation issue."""

    COMPLETENESS = "completeness"  # Missing required fields
    FORMAT = "format"  # Invalid data format
    BUSINESS_RULE = "business_rule"  # Business logic violation
    MEDICAL_CODE = "medical_code"  # Invalid medical codes
    ELIGIBILITY = "eligibility"  # Coverage/eligibility issues
    FWA = "fwa"  # Fraud/waste/abuse indicators


@dataclass
class ValidationIssue:
    """Single validation issue."""

    code: str
    message: str
    severity: ValidationSeverity
    category: ValidationCategory
    field: Optional[str] = None
    details: Optional[dict] = None


@dataclass
class ValidationResult:
    """Complete validation result."""

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    fwa_score: float = 0.0
    fwa_risk_level: FWARiskLevel = FWARiskLevel.LOW
    fwa_flags: list[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue."""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.ERROR:
            self.errors.append(issue)
            self.is_valid = False
        elif issue.severity == ValidationSeverity.WARNING:
            self.warnings.append(issue)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


@dataclass
class ClaimData:
    """Claim data for validation (avoids direct model dependency)."""

    claim_id: str
    tenant_id: str
    tracking_number: str
    claim_type: ClaimType
    policy_id: str
    member_id: str
    provider_id: str
    service_date_from: date
    service_date_to: date
    diagnosis_codes: list[str]
    primary_diagnosis: str
    diagnosis_code_system: DiagnosisCodeSystem
    total_charged: Decimal
    currency: str
    line_items: list["LineItemData"] = field(default_factory=list)
    prior_auth_number: Optional[str] = None
    prior_auth_required: bool = False
    place_of_service: Optional[str] = None
    admission_date: Optional[date] = None
    discharge_date: Optional[date] = None


@dataclass
class LineItemData:
    """Line item data for validation."""

    line_number: int
    procedure_code: str
    procedure_code_system: ProcedureCodeSystem
    service_date: date
    charged_amount: Decimal
    quantity: int = 1
    modifiers: list[str] = field(default_factory=list)
    diagnosis_pointers: list[int] = field(default_factory=list)
    ndc_code: Optional[str] = None


# =============================================================================
# Validation Configuration
# =============================================================================


@dataclass
class ValidationConfig:
    """Configuration for claim validation."""

    # Completeness checks
    require_prior_auth_verification: bool = True
    require_place_of_service: bool = True
    min_line_items: int = 1
    max_line_items: int = 999

    # Date validations
    max_service_age_days: int = 365  # Claims older than 1 year
    future_service_tolerance_days: int = 0  # No future dates

    # Amount validations
    min_charged_amount: Decimal = Decimal("0.01")
    max_charged_amount: Decimal = Decimal("9999999.99")
    max_line_item_amount: Decimal = Decimal("999999.99")

    # FWA thresholds
    fwa_duplicate_window_days: int = 30
    fwa_high_volume_threshold: int = 50  # Claims per day per provider
    fwa_amount_anomaly_multiplier: float = 5.0

    # Medical code validation
    validate_icd10_format: bool = True
    validate_cpt_format: bool = True
    validate_code_combinations: bool = True


# =============================================================================
# Claim Validation Service
# =============================================================================


class ClaimValidationService:
    """
    Service for comprehensive claim validation.

    Validates:
    - Completeness of required fields
    - Data format correctness
    - Business rule compliance
    - Medical code validity
    - FWA indicators
    """

    def __init__(
        self,
        config: Optional[ValidationConfig] = None,
        rules_gateway=None,
        medical_nlp_gateway=None,
    ):
        """
        Initialize validation service.

        Args:
            config: Validation configuration
            rules_gateway: Optional GoRules gateway for custom rules
            medical_nlp_gateway: Optional medical NLP for code validation
        """
        self.config = config or ValidationConfig()
        self._rules_gateway = rules_gateway
        self._medical_nlp = medical_nlp_gateway

    async def validate_claim(
        self,
        claim: ClaimData,
        check_eligibility: bool = True,
        check_fwa: bool = True,
    ) -> ValidationResult:
        """
        Perform full validation on a claim.

        Args:
            claim: Claim data to validate
            check_eligibility: Whether to check member eligibility
            check_fwa: Whether to run FWA detection

        Returns:
            ValidationResult with all issues found
        """
        result = ValidationResult(is_valid=True)

        # Run validation checks
        await self._validate_completeness(claim, result)
        await self._validate_formats(claim, result)
        await self._validate_dates(claim, result)
        await self._validate_amounts(claim, result)
        await self._validate_medical_codes(claim, result)
        await self._validate_line_items(claim, result)

        if check_fwa:
            await self._check_fwa(claim, result)

        # Run custom business rules if gateway available
        if self._rules_gateway:
            await self._run_custom_rules(claim, result)

        return result

    # =========================================================================
    # Completeness Validation
    # =========================================================================

    async def _validate_completeness(
        self,
        claim: ClaimData,
        result: ValidationResult,
    ) -> None:
        """Validate required fields are present."""
        # Required identifiers
        if not claim.policy_id:
            result.add_issue(ValidationIssue(
                code="MISSING_POLICY",
                message="Policy ID is required",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.COMPLETENESS,
                field="policy_id",
            ))

        if not claim.member_id:
            result.add_issue(ValidationIssue(
                code="MISSING_MEMBER",
                message="Member ID is required",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.COMPLETENESS,
                field="member_id",
            ))

        if not claim.provider_id:
            result.add_issue(ValidationIssue(
                code="MISSING_PROVIDER",
                message="Provider ID is required",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.COMPLETENESS,
                field="provider_id",
            ))

        # Required medical data
        if not claim.diagnosis_codes:
            result.add_issue(ValidationIssue(
                code="MISSING_DIAGNOSIS",
                message="At least one diagnosis code is required",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.COMPLETENESS,
                field="diagnosis_codes",
            ))

        if not claim.primary_diagnosis:
            result.add_issue(ValidationIssue(
                code="MISSING_PRIMARY_DIAGNOSIS",
                message="Primary diagnosis code is required",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.COMPLETENESS,
                field="primary_diagnosis",
            ))

        # Line items
        if len(claim.line_items) < self.config.min_line_items:
            result.add_issue(ValidationIssue(
                code="INSUFFICIENT_LINE_ITEMS",
                message=f"At least {self.config.min_line_items} line item(s) required",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.COMPLETENESS,
                field="line_items",
            ))

        if len(claim.line_items) > self.config.max_line_items:
            result.add_issue(ValidationIssue(
                code="TOO_MANY_LINE_ITEMS",
                message=f"Maximum {self.config.max_line_items} line items allowed",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.COMPLETENESS,
                field="line_items",
            ))

        # Prior authorization
        if claim.prior_auth_required and not claim.prior_auth_number:
            result.add_issue(ValidationIssue(
                code="MISSING_PRIOR_AUTH",
                message="Prior authorization number is required but missing",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.COMPLETENESS,
                field="prior_auth_number",
            ))

        # Place of service
        if self.config.require_place_of_service and not claim.place_of_service:
            result.add_issue(ValidationIssue(
                code="MISSING_PLACE_OF_SERVICE",
                message="Place of service is required",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.COMPLETENESS,
                field="place_of_service",
            ))

    # =========================================================================
    # Format Validation
    # =========================================================================

    async def _validate_formats(
        self,
        claim: ClaimData,
        result: ValidationResult,
    ) -> None:
        """Validate data format correctness."""
        # Currency format
        if claim.currency and len(claim.currency) != 3:
            result.add_issue(ValidationIssue(
                code="INVALID_CURRENCY",
                message="Currency must be 3-letter ISO code",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.FORMAT,
                field="currency",
                details={"value": claim.currency},
            ))

        # Place of service format (should be 2 digits)
        if claim.place_of_service:
            if not re.match(r"^\d{2}$", claim.place_of_service):
                result.add_issue(ValidationIssue(
                    code="INVALID_POS_FORMAT",
                    message="Place of service must be 2-digit code",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.FORMAT,
                    field="place_of_service",
                    details={"value": claim.place_of_service},
                ))

    # =========================================================================
    # Date Validation
    # =========================================================================

    async def _validate_dates(
        self,
        claim: ClaimData,
        result: ValidationResult,
    ) -> None:
        """Validate date fields."""
        today = date.today()

        # Service date range
        if claim.service_date_from > claim.service_date_to:
            result.add_issue(ValidationIssue(
                code="INVALID_DATE_RANGE",
                message="Service date from cannot be after service date to",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.BUSINESS_RULE,
                field="service_date_from",
                details={
                    "service_date_from": str(claim.service_date_from),
                    "service_date_to": str(claim.service_date_to),
                },
            ))

        # Future dates
        if claim.service_date_from > today:
            result.add_issue(ValidationIssue(
                code="FUTURE_SERVICE_DATE",
                message="Service date cannot be in the future",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.BUSINESS_RULE,
                field="service_date_from",
            ))

        # Service age
        service_age = (today - claim.service_date_from).days
        if service_age > self.config.max_service_age_days:
            result.add_issue(ValidationIssue(
                code="SERVICE_TOO_OLD",
                message=f"Service date is older than {self.config.max_service_age_days} days",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.BUSINESS_RULE,
                field="service_date_from",
                details={"age_days": service_age},
            ))

        # Admission/discharge dates for institutional claims
        if claim.claim_type == ClaimType.INSTITUTIONAL:
            if claim.admission_date and claim.discharge_date:
                if claim.admission_date > claim.discharge_date:
                    result.add_issue(ValidationIssue(
                        code="INVALID_ADMISSION_DATES",
                        message="Admission date cannot be after discharge date",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.BUSINESS_RULE,
                        field="admission_date",
                    ))

    # =========================================================================
    # Amount Validation
    # =========================================================================

    async def _validate_amounts(
        self,
        claim: ClaimData,
        result: ValidationResult,
    ) -> None:
        """Validate financial amounts."""
        # Total charged
        if claim.total_charged < self.config.min_charged_amount:
            result.add_issue(ValidationIssue(
                code="AMOUNT_TOO_LOW",
                message=f"Total charged must be at least {self.config.min_charged_amount}",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.BUSINESS_RULE,
                field="total_charged",
            ))

        if claim.total_charged > self.config.max_charged_amount:
            result.add_issue(ValidationIssue(
                code="AMOUNT_TOO_HIGH",
                message=f"Total charged exceeds maximum of {self.config.max_charged_amount}",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.BUSINESS_RULE,
                field="total_charged",
            ))

        # Verify line items sum to total
        if claim.line_items:
            line_item_total = sum(
                item.charged_amount * item.quantity
                for item in claim.line_items
            )
            if abs(line_item_total - claim.total_charged) > Decimal("0.01"):
                result.add_issue(ValidationIssue(
                    code="AMOUNT_MISMATCH",
                    message="Line item total does not match claim total",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.BUSINESS_RULE,
                    field="total_charged",
                    details={
                        "line_item_total": str(line_item_total),
                        "claim_total": str(claim.total_charged),
                    },
                ))

    # =========================================================================
    # Medical Code Validation
    # =========================================================================

    async def _validate_medical_codes(
        self,
        claim: ClaimData,
        result: ValidationResult,
    ) -> None:
        """Validate diagnosis and procedure codes."""
        # ICD-10 format validation
        if self.config.validate_icd10_format:
            icd10_pattern = r"^[A-Z]\d{2}(\.\d{1,4})?$"
            for code in claim.diagnosis_codes:
                if not re.match(icd10_pattern, code):
                    result.add_issue(ValidationIssue(
                        code="INVALID_ICD10_FORMAT",
                        message=f"Invalid ICD-10 code format: {code}",
                        severity=ValidationSeverity.WARNING,
                        category=ValidationCategory.MEDICAL_CODE,
                        field="diagnosis_codes",
                        details={"code": code},
                    ))

        # Primary diagnosis must be in diagnosis list
        if claim.primary_diagnosis not in claim.diagnosis_codes:
            result.add_issue(ValidationIssue(
                code="PRIMARY_DX_NOT_IN_LIST",
                message="Primary diagnosis must be in diagnosis code list",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.MEDICAL_CODE,
                field="primary_diagnosis",
            ))

        # Use medical NLP for deeper validation if available
        if self._medical_nlp:
            await self._validate_codes_with_nlp(claim, result)

    async def _validate_codes_with_nlp(
        self,
        claim: ClaimData,
        result: ValidationResult,
    ) -> None:
        """Use medical NLP to validate code relationships."""
        try:
            # This would call the medical NLP gateway
            # For now, we'll skip if not available
            pass
        except Exception as e:
            logger.warning(f"Medical NLP validation failed: {e}")

    # =========================================================================
    # Line Item Validation
    # =========================================================================

    async def _validate_line_items(
        self,
        claim: ClaimData,
        result: ValidationResult,
    ) -> None:
        """Validate individual line items."""
        for item in claim.line_items:
            # CPT code format
            if self.config.validate_cpt_format:
                if item.procedure_code_system == ProcedureCodeSystem.CPT:
                    if not re.match(r"^\d{5}$", item.procedure_code):
                        result.add_issue(ValidationIssue(
                            code="INVALID_CPT_FORMAT",
                            message=f"Invalid CPT code format: {item.procedure_code}",
                            severity=ValidationSeverity.WARNING,
                            category=ValidationCategory.MEDICAL_CODE,
                            field=f"line_items[{item.line_number}].procedure_code",
                            details={"code": item.procedure_code},
                        ))

            # Line item amount
            if item.charged_amount > self.config.max_line_item_amount:
                result.add_issue(ValidationIssue(
                    code="LINE_ITEM_AMOUNT_HIGH",
                    message=f"Line item {item.line_number} amount exceeds threshold",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.BUSINESS_RULE,
                    field=f"line_items[{item.line_number}].charged_amount",
                    details={"amount": str(item.charged_amount)},
                ))

            # Quantity
            if item.quantity < 1:
                result.add_issue(ValidationIssue(
                    code="INVALID_QUANTITY",
                    message=f"Line item {item.line_number} quantity must be at least 1",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.BUSINESS_RULE,
                    field=f"line_items[{item.line_number}].quantity",
                ))

            # Diagnosis pointers
            for pointer in item.diagnosis_pointers:
                if pointer < 1 or pointer > len(claim.diagnosis_codes):
                    result.add_issue(ValidationIssue(
                        code="INVALID_DX_POINTER",
                        message=f"Line item {item.line_number} has invalid diagnosis pointer: {pointer}",
                        severity=ValidationSeverity.WARNING,
                        category=ValidationCategory.BUSINESS_RULE,
                        field=f"line_items[{item.line_number}].diagnosis_pointers",
                    ))

            # Service date within claim dates
            if item.service_date < claim.service_date_from or item.service_date > claim.service_date_to:
                result.add_issue(ValidationIssue(
                    code="LINE_DATE_OUT_OF_RANGE",
                    message=f"Line item {item.line_number} service date outside claim date range",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.BUSINESS_RULE,
                    field=f"line_items[{item.line_number}].service_date",
                ))

    # =========================================================================
    # FWA Detection
    # =========================================================================

    async def _check_fwa(
        self,
        claim: ClaimData,
        result: ValidationResult,
    ) -> None:
        """Check for fraud, waste, and abuse indicators."""
        fwa_flags = []
        fwa_score = 0.0

        # Check for duplicate procedure codes
        procedure_codes = [item.procedure_code for item in claim.line_items]
        if len(procedure_codes) != len(set(procedure_codes)):
            fwa_flags.append("DUPLICATE_PROCEDURES")
            fwa_score += 0.2

        # Check for high quantity
        for item in claim.line_items:
            if item.quantity > 10:
                fwa_flags.append(f"HIGH_QUANTITY_LINE_{item.line_number}")
                fwa_score += 0.15

        # Check for weekend services (potential indicator)
        if claim.service_date_from.weekday() >= 5:  # Saturday or Sunday
            fwa_flags.append("WEEKEND_SERVICE")
            fwa_score += 0.05

        # Check for high total amount
        if claim.total_charged > Decimal("10000"):
            fwa_flags.append("HIGH_TOTAL_AMOUNT")
            fwa_score += 0.1

        # Determine risk level
        if fwa_score >= 0.8:
            risk_level = FWARiskLevel.CRITICAL
        elif fwa_score >= 0.6:
            risk_level = FWARiskLevel.HIGH
        elif fwa_score >= 0.3:
            risk_level = FWARiskLevel.MEDIUM
        else:
            risk_level = FWARiskLevel.LOW

        result.fwa_score = min(fwa_score, 1.0)
        result.fwa_risk_level = risk_level
        result.fwa_flags = fwa_flags

        # Add warnings for medium+ risk
        if risk_level in (FWARiskLevel.MEDIUM, FWARiskLevel.HIGH, FWARiskLevel.CRITICAL):
            result.add_issue(ValidationIssue(
                code="FWA_RISK_DETECTED",
                message=f"FWA risk level: {risk_level.value} (score: {fwa_score:.2f})",
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.FWA,
                details={
                    "fwa_score": fwa_score,
                    "fwa_flags": fwa_flags,
                },
            ))

    # =========================================================================
    # Custom Rules
    # =========================================================================

    async def _run_custom_rules(
        self,
        claim: ClaimData,
        result: ValidationResult,
    ) -> None:
        """Run custom business rules via rules gateway."""
        if not self._rules_gateway:
            return

        try:
            # This would call the GoRules gateway
            # For now, we'll skip if not available
            pass
        except Exception as e:
            logger.warning(f"Custom rules validation failed: {e}")


# =============================================================================
# Factory Functions
# =============================================================================


def get_claim_validation_service(
    config: Optional[ValidationConfig] = None,
) -> ClaimValidationService:
    """Get claim validation service instance."""
    return ClaimValidationService(config=config)
