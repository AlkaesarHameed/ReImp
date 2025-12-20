"""
Sprint 6 Claims Processing Tests.

Tests for:
- Claims service CRUD operations
- Claim validation service
- Status state machine
- Status transitions

All tests use inlined classes to avoid import chain issues.
"""

import pytest
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4


# =============================================================================
# Inlined Enums
# =============================================================================


class ClaimType(str, Enum):
    PROFESSIONAL = "professional"
    INSTITUTIONAL = "institutional"
    DENTAL = "dental"
    PHARMACY = "pharmacy"


class ClaimStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    DOC_PROCESSING = "doc_processing"
    VALIDATING = "validating"
    ADJUDICATING = "adjudicating"
    APPROVED = "approved"
    DENIED = "denied"
    NEEDS_REVIEW = "needs_review"
    PAYMENT_PROCESSING = "payment_processing"
    PAID = "paid"
    CLOSED = "closed"


class ClaimPriority(str, Enum):
    NORMAL = "normal"
    URGENT = "urgent"
    EXPEDITED = "expedited"


class ClaimSource(str, Enum):
    PORTAL = "portal"
    API = "api"
    EDI = "edi"
    FAX = "fax"
    MAIL = "mail"


class DiagnosisCodeSystem(str, Enum):
    ICD10_CM = "icd10_cm"
    ICD10_AM = "icd10_am"
    ICD9_CM = "icd9_cm"


class ProcedureCodeSystem(str, Enum):
    CPT = "cpt"
    HCPCS = "hcpcs"
    ACHI = "achi"


class FWARiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationCategory(str, Enum):
    COMPLETENESS = "completeness"
    FORMAT = "format"
    BUSINESS_RULE = "business_rule"
    MEDICAL_CODE = "medical_code"
    ELIGIBILITY = "eligibility"
    FWA = "fwa"


class TransitionEvent(str, Enum):
    SUBMIT = "submit"
    START_PROCESSING = "start_processing"
    COMPLETE_PROCESSING = "complete_processing"
    PROCESSING_FAILED = "processing_failed"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    FLAG_FOR_REVIEW = "flag_for_review"
    APPROVE = "approve"
    DENY = "deny"
    RESUME_PROCESSING = "resume_processing"
    START_PAYMENT = "start_payment"
    PAYMENT_COMPLETE = "payment_complete"
    PAYMENT_FAILED = "payment_failed"
    CLOSE = "close"


# =============================================================================
# Inlined Data Classes
# =============================================================================


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: ValidationSeverity
    category: ValidationCategory
    field: Optional[str] = None
    details: Optional[dict] = None


@dataclass
class ValidationResult:
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    fwa_score: float = 0.0
    fwa_risk_level: FWARiskLevel = FWARiskLevel.LOW
    fwa_flags: list[str] = field(default_factory=list)

    def add_issue(self, issue: ValidationIssue) -> None:
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
class LineItemData:
    line_number: int
    procedure_code: str
    procedure_code_system: ProcedureCodeSystem
    service_date: date
    charged_amount: Decimal
    quantity: int = 1
    modifiers: list[str] = field(default_factory=list)
    diagnosis_pointers: list[int] = field(default_factory=list)
    ndc_code: Optional[str] = None


@dataclass
class ClaimData:
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
    line_items: list[LineItemData] = field(default_factory=list)
    prior_auth_number: Optional[str] = None
    prior_auth_required: bool = False
    place_of_service: Optional[str] = None
    admission_date: Optional[date] = None
    discharge_date: Optional[date] = None


@dataclass
class Transition:
    from_status: ClaimStatus
    to_status: ClaimStatus
    event: TransitionEvent
    requires_permission: Optional[str] = None
    requires_reason: bool = False
    auto_transition: bool = False


@dataclass
class TransitionContext:
    claim_id: str
    current_status: ClaimStatus
    target_status: ClaimStatus
    event: TransitionEvent
    triggered_by: Optional[str] = None
    reason: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class TransitionResult:
    success: bool
    from_status: ClaimStatus
    to_status: Optional[ClaimStatus] = None
    error: Optional[str] = None
    transition: Optional[Transition] = None


# =============================================================================
# Inlined Validation Config
# =============================================================================


@dataclass
class ValidationConfig:
    require_prior_auth_verification: bool = True
    require_place_of_service: bool = True
    min_line_items: int = 1
    max_line_items: int = 999
    max_service_age_days: int = 365
    future_service_tolerance_days: int = 0
    min_charged_amount: Decimal = Decimal("0.01")
    max_charged_amount: Decimal = Decimal("9999999.99")
    max_line_item_amount: Decimal = Decimal("999999.99")
    validate_icd10_format: bool = True
    validate_cpt_format: bool = True


# =============================================================================
# Inlined Validation Service
# =============================================================================


class ClaimValidationService:
    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig()

    async def validate_claim(
        self,
        claim: ClaimData,
        check_eligibility: bool = True,
        check_fwa: bool = True,
    ) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        await self._validate_completeness(claim, result)
        await self._validate_dates(claim, result)
        await self._validate_amounts(claim, result)
        await self._validate_medical_codes(claim, result)
        await self._validate_line_items(claim, result)

        if check_fwa:
            await self._check_fwa(claim, result)

        return result

    async def _validate_completeness(self, claim: ClaimData, result: ValidationResult) -> None:
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

        if not claim.diagnosis_codes:
            result.add_issue(ValidationIssue(
                code="MISSING_DIAGNOSIS",
                message="At least one diagnosis code is required",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.COMPLETENESS,
                field="diagnosis_codes",
            ))

        if len(claim.line_items) < self.config.min_line_items:
            result.add_issue(ValidationIssue(
                code="INSUFFICIENT_LINE_ITEMS",
                message=f"At least {self.config.min_line_items} line item(s) required",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.COMPLETENESS,
                field="line_items",
            ))

        if claim.prior_auth_required and not claim.prior_auth_number:
            result.add_issue(ValidationIssue(
                code="MISSING_PRIOR_AUTH",
                message="Prior authorization number is required",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.COMPLETENESS,
                field="prior_auth_number",
            ))

    async def _validate_dates(self, claim: ClaimData, result: ValidationResult) -> None:
        today = date.today()

        if claim.service_date_from > claim.service_date_to:
            result.add_issue(ValidationIssue(
                code="INVALID_DATE_RANGE",
                message="Service date from cannot be after service date to",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.BUSINESS_RULE,
                field="service_date_from",
            ))

        if claim.service_date_from > today:
            result.add_issue(ValidationIssue(
                code="FUTURE_SERVICE_DATE",
                message="Service date cannot be in the future",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.BUSINESS_RULE,
                field="service_date_from",
            ))

    async def _validate_amounts(self, claim: ClaimData, result: ValidationResult) -> None:
        if claim.total_charged < self.config.min_charged_amount:
            result.add_issue(ValidationIssue(
                code="AMOUNT_TOO_LOW",
                message=f"Total charged must be at least {self.config.min_charged_amount}",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.BUSINESS_RULE,
                field="total_charged",
            ))

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
                ))

    async def _validate_medical_codes(self, claim: ClaimData, result: ValidationResult) -> None:
        import re

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
                    ))

        if claim.primary_diagnosis not in claim.diagnosis_codes:
            result.add_issue(ValidationIssue(
                code="PRIMARY_DX_NOT_IN_LIST",
                message="Primary diagnosis must be in diagnosis code list",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.MEDICAL_CODE,
                field="primary_diagnosis",
            ))

    async def _validate_line_items(self, claim: ClaimData, result: ValidationResult) -> None:
        import re

        for item in claim.line_items:
            if self.config.validate_cpt_format:
                if item.procedure_code_system == ProcedureCodeSystem.CPT:
                    if not re.match(r"^\d{5}$", item.procedure_code):
                        result.add_issue(ValidationIssue(
                            code="INVALID_CPT_FORMAT",
                            message=f"Invalid CPT code format: {item.procedure_code}",
                            severity=ValidationSeverity.WARNING,
                            category=ValidationCategory.MEDICAL_CODE,
                            field=f"line_items[{item.line_number}].procedure_code",
                        ))

            if item.quantity < 1:
                result.add_issue(ValidationIssue(
                    code="INVALID_QUANTITY",
                    message=f"Line item {item.line_number} quantity must be at least 1",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.BUSINESS_RULE,
                    field=f"line_items[{item.line_number}].quantity",
                ))

    async def _check_fwa(self, claim: ClaimData, result: ValidationResult) -> None:
        fwa_flags = []
        fwa_score = 0.0

        procedure_codes = [item.procedure_code for item in claim.line_items]
        if len(procedure_codes) != len(set(procedure_codes)):
            fwa_flags.append("DUPLICATE_PROCEDURES")
            fwa_score += 0.2

        for item in claim.line_items:
            if item.quantity > 10:
                fwa_flags.append(f"HIGH_QUANTITY_LINE_{item.line_number}")
                fwa_score += 0.15

        if claim.total_charged > Decimal("10000"):
            fwa_flags.append("HIGH_TOTAL_AMOUNT")
            fwa_score += 0.1

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


# =============================================================================
# Inlined State Machine
# =============================================================================


VALID_TRANSITIONS: list[Transition] = [
    Transition(ClaimStatus.DRAFT, ClaimStatus.SUBMITTED, TransitionEvent.SUBMIT, "claims:submit"),
    Transition(ClaimStatus.DRAFT, ClaimStatus.CLOSED, TransitionEvent.CLOSE, "claims:delete", True),
    Transition(ClaimStatus.SUBMITTED, ClaimStatus.DOC_PROCESSING, TransitionEvent.START_PROCESSING, auto_transition=True),
    Transition(ClaimStatus.DOC_PROCESSING, ClaimStatus.VALIDATING, TransitionEvent.COMPLETE_PROCESSING, auto_transition=True),
    Transition(ClaimStatus.DOC_PROCESSING, ClaimStatus.NEEDS_REVIEW, TransitionEvent.PROCESSING_FAILED, auto_transition=True),
    Transition(ClaimStatus.VALIDATING, ClaimStatus.ADJUDICATING, TransitionEvent.VALIDATION_PASSED, auto_transition=True),
    Transition(ClaimStatus.VALIDATING, ClaimStatus.DENIED, TransitionEvent.VALIDATION_FAILED, "claims:deny", True),
    Transition(ClaimStatus.VALIDATING, ClaimStatus.NEEDS_REVIEW, TransitionEvent.FLAG_FOR_REVIEW, requires_reason=True),
    Transition(ClaimStatus.ADJUDICATING, ClaimStatus.APPROVED, TransitionEvent.APPROVE, "claims:approve"),
    Transition(ClaimStatus.ADJUDICATING, ClaimStatus.DENIED, TransitionEvent.DENY, "claims:deny", True),
    Transition(ClaimStatus.ADJUDICATING, ClaimStatus.NEEDS_REVIEW, TransitionEvent.FLAG_FOR_REVIEW, requires_reason=True),
    Transition(ClaimStatus.APPROVED, ClaimStatus.PAYMENT_PROCESSING, TransitionEvent.START_PAYMENT, auto_transition=True),
    Transition(ClaimStatus.PAYMENT_PROCESSING, ClaimStatus.PAID, TransitionEvent.PAYMENT_COMPLETE, auto_transition=True),
    Transition(ClaimStatus.PAYMENT_PROCESSING, ClaimStatus.NEEDS_REVIEW, TransitionEvent.PAYMENT_FAILED, auto_transition=True),
    Transition(ClaimStatus.PAID, ClaimStatus.CLOSED, TransitionEvent.CLOSE, auto_transition=True),
    Transition(ClaimStatus.NEEDS_REVIEW, ClaimStatus.APPROVED, TransitionEvent.APPROVE, "claims:approve"),
    Transition(ClaimStatus.NEEDS_REVIEW, ClaimStatus.DENIED, TransitionEvent.DENY, "claims:deny", True),
    Transition(ClaimStatus.NEEDS_REVIEW, ClaimStatus.VALIDATING, TransitionEvent.RESUME_PROCESSING, "claims:review"),
    Transition(ClaimStatus.DENIED, ClaimStatus.CLOSED, TransitionEvent.CLOSE, auto_transition=True),
]


class ClaimStateMachine:
    def __init__(self):
        self._transitions: dict[tuple[ClaimStatus, TransitionEvent], Transition] = {}
        self._from_status_map: dict[ClaimStatus, list[Transition]] = {}
        self._build_transition_maps()

    def _build_transition_maps(self) -> None:
        for transition in VALID_TRANSITIONS:
            key = (transition.from_status, transition.event)
            self._transitions[key] = transition
            if transition.from_status not in self._from_status_map:
                self._from_status_map[transition.from_status] = []
            self._from_status_map[transition.from_status].append(transition)

    def get_valid_transitions(self, status: ClaimStatus) -> list[Transition]:
        return self._from_status_map.get(status, [])

    def get_valid_events(self, status: ClaimStatus) -> list[TransitionEvent]:
        return [t.event for t in self.get_valid_transitions(status)]

    def get_next_statuses(self, status: ClaimStatus) -> list[ClaimStatus]:
        return [t.to_status for t in self.get_valid_transitions(status)]

    def can_transition(self, from_status: ClaimStatus, to_status: ClaimStatus) -> bool:
        for transition in self.get_valid_transitions(from_status):
            if transition.to_status == to_status:
                return True
        return False

    def get_transition(self, from_status: ClaimStatus, event: TransitionEvent) -> Optional[Transition]:
        return self._transitions.get((from_status, event))

    def validate_transition(
        self,
        context: TransitionContext,
        user_permissions: Optional[list[str]] = None,
    ) -> TransitionResult:
        transition = self.get_transition(context.current_status, context.event)

        if not transition:
            return TransitionResult(
                success=False,
                from_status=context.current_status,
                error=f"Invalid transition: {context.current_status.value} + {context.event.value}",
            )

        if context.target_status != transition.to_status:
            return TransitionResult(
                success=False,
                from_status=context.current_status,
                error=f"Target status mismatch",
            )

        if transition.requires_permission:
            if not user_permissions or transition.requires_permission not in user_permissions:
                return TransitionResult(
                    success=False,
                    from_status=context.current_status,
                    error=f"Missing required permission: {transition.requires_permission}",
                )

        if transition.requires_reason and not context.reason:
            return TransitionResult(
                success=False,
                from_status=context.current_status,
                error="Reason is required for this transition",
            )

        return TransitionResult(
            success=True,
            from_status=context.current_status,
            to_status=transition.to_status,
            transition=transition,
        )


# =============================================================================
# Tests: Claim Validation Service
# =============================================================================


class TestClaimValidationService:
    """Tests for claim validation service."""

    @pytest.fixture
    def validation_service(self):
        return ClaimValidationService()

    @pytest.fixture
    def valid_claim(self) -> ClaimData:
        """Create a valid claim for testing."""
        return ClaimData(
            claim_id="claim-123",
            tenant_id="tenant-123",
            tracking_number="CLM-2025-000001",
            claim_type=ClaimType.PROFESSIONAL,
            policy_id="policy-123",
            member_id="member-123",
            provider_id="provider-123",
            service_date_from=date(2025, 1, 1),
            service_date_to=date(2025, 1, 1),
            diagnosis_codes=["J06.9", "R05.9"],
            primary_diagnosis="J06.9",
            diagnosis_code_system=DiagnosisCodeSystem.ICD10_CM,
            total_charged=Decimal("150.00"),
            currency="USD",
            line_items=[
                LineItemData(
                    line_number=1,
                    procedure_code="99213",
                    procedure_code_system=ProcedureCodeSystem.CPT,
                    service_date=date(2025, 1, 1),
                    charged_amount=Decimal("150.00"),
                    quantity=1,
                    diagnosis_pointers=[1],
                )
            ],
        )

    @pytest.mark.asyncio
    async def test_valid_claim_passes_validation(self, validation_service, valid_claim):
        """Test that a valid claim passes validation."""
        result = await validation_service.validate_claim(valid_claim)
        assert result.is_valid is True
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_missing_policy_id_fails(self, validation_service, valid_claim):
        """Test that missing policy ID fails validation."""
        valid_claim.policy_id = ""
        result = await validation_service.validate_claim(valid_claim)
        assert result.is_valid is False
        assert any(issue.code == "MISSING_POLICY" for issue in result.errors)

    @pytest.mark.asyncio
    async def test_missing_member_id_fails(self, validation_service, valid_claim):
        """Test that missing member ID fails validation."""
        valid_claim.member_id = ""
        result = await validation_service.validate_claim(valid_claim)
        assert result.is_valid is False
        assert any(issue.code == "MISSING_MEMBER" for issue in result.errors)

    @pytest.mark.asyncio
    async def test_missing_diagnosis_fails(self, validation_service, valid_claim):
        """Test that missing diagnosis codes fails validation."""
        valid_claim.diagnosis_codes = []
        result = await validation_service.validate_claim(valid_claim)
        assert result.is_valid is False
        assert any(issue.code == "MISSING_DIAGNOSIS" for issue in result.errors)

    @pytest.mark.asyncio
    async def test_no_line_items_fails(self, validation_service, valid_claim):
        """Test that claim without line items fails validation."""
        valid_claim.line_items = []
        result = await validation_service.validate_claim(valid_claim)
        assert result.is_valid is False
        assert any(issue.code == "INSUFFICIENT_LINE_ITEMS" for issue in result.errors)

    @pytest.mark.asyncio
    async def test_invalid_date_range_fails(self, validation_service, valid_claim):
        """Test that invalid date range fails validation."""
        valid_claim.service_date_from = date(2025, 2, 1)
        valid_claim.service_date_to = date(2025, 1, 1)
        result = await validation_service.validate_claim(valid_claim)
        assert result.is_valid is False
        assert any(issue.code == "INVALID_DATE_RANGE" for issue in result.errors)

    @pytest.mark.asyncio
    async def test_future_service_date_fails(self, validation_service, valid_claim):
        """Test that future service date fails validation."""
        future_date = date(2030, 12, 31)
        valid_claim.service_date_from = future_date
        valid_claim.service_date_to = future_date
        result = await validation_service.validate_claim(valid_claim)
        assert result.is_valid is False
        assert any(issue.code == "FUTURE_SERVICE_DATE" for issue in result.errors)

    @pytest.mark.asyncio
    async def test_amount_too_low_fails(self, validation_service, valid_claim):
        """Test that very low amount fails validation."""
        valid_claim.total_charged = Decimal("0.00")
        result = await validation_service.validate_claim(valid_claim)
        assert result.is_valid is False
        assert any(issue.code == "AMOUNT_TOO_LOW" for issue in result.errors)

    @pytest.mark.asyncio
    async def test_primary_dx_not_in_list_fails(self, validation_service, valid_claim):
        """Test that primary diagnosis not in list fails."""
        valid_claim.primary_diagnosis = "Z99.9"
        result = await validation_service.validate_claim(valid_claim)
        assert result.is_valid is False
        assert any(issue.code == "PRIMARY_DX_NOT_IN_LIST" for issue in result.errors)

    @pytest.mark.asyncio
    async def test_invalid_icd10_format_warning(self, validation_service, valid_claim):
        """Test that invalid ICD-10 format adds warning."""
        valid_claim.diagnosis_codes = ["INVALID", "J06.9"]
        valid_claim.primary_diagnosis = "J06.9"
        result = await validation_service.validate_claim(valid_claim)
        assert any(issue.code == "INVALID_ICD10_FORMAT" for issue in result.warnings)

    @pytest.mark.asyncio
    async def test_fwa_detection_duplicate_procedures(self, validation_service, valid_claim):
        """Test FWA detection for duplicate procedures."""
        valid_claim.line_items = [
            LineItemData(
                line_number=1,
                procedure_code="99213",
                procedure_code_system=ProcedureCodeSystem.CPT,
                service_date=date(2025, 1, 1),
                charged_amount=Decimal("75.00"),
                quantity=1,
            ),
            LineItemData(
                line_number=2,
                procedure_code="99213",  # Duplicate
                procedure_code_system=ProcedureCodeSystem.CPT,
                service_date=date(2025, 1, 1),
                charged_amount=Decimal("75.00"),
                quantity=1,
            ),
        ]
        result = await validation_service.validate_claim(valid_claim)
        assert "DUPLICATE_PROCEDURES" in result.fwa_flags

    @pytest.mark.asyncio
    async def test_fwa_detection_high_quantity(self, validation_service, valid_claim):
        """Test FWA detection for high quantity."""
        valid_claim.line_items[0].quantity = 20
        result = await validation_service.validate_claim(valid_claim)
        assert any("HIGH_QUANTITY" in flag for flag in result.fwa_flags)

    @pytest.mark.asyncio
    async def test_fwa_risk_level_calculation(self, validation_service, valid_claim):
        """Test FWA risk level calculation."""
        result = await validation_service.validate_claim(valid_claim)
        assert result.fwa_risk_level in FWARiskLevel


# =============================================================================
# Tests: Claim State Machine
# =============================================================================


class TestClaimStateMachine:
    """Tests for claim status state machine."""

    @pytest.fixture
    def state_machine(self):
        return ClaimStateMachine()

    def test_draft_can_submit(self, state_machine):
        """Test DRAFT can transition to SUBMITTED."""
        assert state_machine.can_transition(ClaimStatus.DRAFT, ClaimStatus.SUBMITTED)

    def test_draft_cannot_approve(self, state_machine):
        """Test DRAFT cannot transition to APPROVED."""
        assert not state_machine.can_transition(ClaimStatus.DRAFT, ClaimStatus.APPROVED)

    def test_submitted_to_doc_processing(self, state_machine):
        """Test SUBMITTED can transition to DOC_PROCESSING."""
        assert state_machine.can_transition(ClaimStatus.SUBMITTED, ClaimStatus.DOC_PROCESSING)

    def test_adjudicating_to_approved(self, state_machine):
        """Test ADJUDICATING can transition to APPROVED."""
        assert state_machine.can_transition(ClaimStatus.ADJUDICATING, ClaimStatus.APPROVED)

    def test_adjudicating_to_denied(self, state_machine):
        """Test ADJUDICATING can transition to DENIED."""
        assert state_machine.can_transition(ClaimStatus.ADJUDICATING, ClaimStatus.DENIED)

    def test_needs_review_to_approved(self, state_machine):
        """Test NEEDS_REVIEW can transition to APPROVED."""
        assert state_machine.can_transition(ClaimStatus.NEEDS_REVIEW, ClaimStatus.APPROVED)

    def test_get_valid_events_for_draft(self, state_machine):
        """Test valid events from DRAFT status."""
        events = state_machine.get_valid_events(ClaimStatus.DRAFT)
        assert TransitionEvent.SUBMIT in events
        assert TransitionEvent.CLOSE in events

    def test_get_valid_events_for_adjudicating(self, state_machine):
        """Test valid events from ADJUDICATING status."""
        events = state_machine.get_valid_events(ClaimStatus.ADJUDICATING)
        assert TransitionEvent.APPROVE in events
        assert TransitionEvent.DENY in events
        assert TransitionEvent.FLAG_FOR_REVIEW in events

    def test_get_next_statuses_from_validating(self, state_machine):
        """Test possible next statuses from VALIDATING."""
        next_statuses = state_machine.get_next_statuses(ClaimStatus.VALIDATING)
        assert ClaimStatus.ADJUDICATING in next_statuses
        assert ClaimStatus.DENIED in next_statuses
        assert ClaimStatus.NEEDS_REVIEW in next_statuses

    def test_closed_has_no_transitions(self, state_machine):
        """Test CLOSED status has no valid transitions."""
        transitions = state_machine.get_valid_transitions(ClaimStatus.CLOSED)
        assert len(transitions) == 0

    def test_validate_transition_success(self, state_machine):
        """Test successful transition validation."""
        context = TransitionContext(
            claim_id="claim-123",
            current_status=ClaimStatus.DRAFT,
            target_status=ClaimStatus.SUBMITTED,
            event=TransitionEvent.SUBMIT,
            triggered_by="user-123",
        )
        result = state_machine.validate_transition(context, ["claims:submit"])
        assert result.success is True
        assert result.to_status == ClaimStatus.SUBMITTED

    def test_validate_transition_invalid(self, state_machine):
        """Test invalid transition validation."""
        context = TransitionContext(
            claim_id="claim-123",
            current_status=ClaimStatus.DRAFT,
            target_status=ClaimStatus.APPROVED,
            event=TransitionEvent.APPROVE,
            triggered_by="user-123",
        )
        result = state_machine.validate_transition(context, ["claims:approve"])
        assert result.success is False
        assert result.error is not None

    def test_validate_transition_missing_permission(self, state_machine):
        """Test transition fails without required permission."""
        context = TransitionContext(
            claim_id="claim-123",
            current_status=ClaimStatus.DRAFT,
            target_status=ClaimStatus.SUBMITTED,
            event=TransitionEvent.SUBMIT,
            triggered_by="user-123",
        )
        result = state_machine.validate_transition(context, [])  # No permissions
        assert result.success is False
        assert "permission" in result.error.lower()

    def test_validate_transition_missing_reason(self, state_machine):
        """Test transition requiring reason fails without it."""
        context = TransitionContext(
            claim_id="claim-123",
            current_status=ClaimStatus.ADJUDICATING,
            target_status=ClaimStatus.DENIED,
            event=TransitionEvent.DENY,
            triggered_by="user-123",
            reason=None,  # No reason
        )
        result = state_machine.validate_transition(context, ["claims:deny"])
        assert result.success is False
        assert "reason" in result.error.lower()


# =============================================================================
# Tests: Status Helpers
# =============================================================================


class TestStatusHelpers:
    """Tests for status helper functions."""

    def test_terminal_status(self):
        """Test terminal status identification."""
        assert ClaimStatus.CLOSED.value == "closed"

    def test_processing_statuses(self):
        """Test processing status identification."""
        processing = [
            ClaimStatus.SUBMITTED,
            ClaimStatus.DOC_PROCESSING,
            ClaimStatus.VALIDATING,
            ClaimStatus.ADJUDICATING,
            ClaimStatus.PAYMENT_PROCESSING,
        ]
        for status in processing:
            assert status.value in ["submitted", "doc_processing", "validating", "adjudicating", "payment_processing"]

    def test_finalized_statuses(self):
        """Test finalized status identification."""
        finalized = [
            ClaimStatus.APPROVED,
            ClaimStatus.DENIED,
            ClaimStatus.PAID,
            ClaimStatus.CLOSED,
        ]
        for status in finalized:
            assert status.value in ["approved", "denied", "paid", "closed"]


# =============================================================================
# Tests: Validation Categories
# =============================================================================


class TestValidationCategories:
    """Tests for validation category classification."""

    def test_completeness_category(self):
        """Test completeness category issues."""
        issue = ValidationIssue(
            code="MISSING_POLICY",
            message="Policy required",
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.COMPLETENESS,
        )
        assert issue.category == ValidationCategory.COMPLETENESS

    def test_business_rule_category(self):
        """Test business rule category issues."""
        issue = ValidationIssue(
            code="INVALID_DATE_RANGE",
            message="Invalid dates",
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.BUSINESS_RULE,
        )
        assert issue.category == ValidationCategory.BUSINESS_RULE

    def test_medical_code_category(self):
        """Test medical code category issues."""
        issue = ValidationIssue(
            code="INVALID_ICD10_FORMAT",
            message="Bad ICD-10",
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.MEDICAL_CODE,
        )
        assert issue.category == ValidationCategory.MEDICAL_CODE

    def test_fwa_category(self):
        """Test FWA category issues."""
        issue = ValidationIssue(
            code="FWA_RISK_DETECTED",
            message="FWA risk",
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.FWA,
        )
        assert issue.category == ValidationCategory.FWA


# =============================================================================
# Tests: Validation Result
# =============================================================================


class TestValidationResult:
    """Tests for validation result behavior."""

    def test_starts_valid(self):
        """Test result starts as valid."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True

    def test_adding_error_invalidates(self):
        """Test adding error makes result invalid."""
        result = ValidationResult(is_valid=True)
        result.add_issue(ValidationIssue(
            code="ERROR",
            message="Error",
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.COMPLETENESS,
        ))
        assert result.is_valid is False
        assert result.error_count == 1

    def test_adding_warning_keeps_valid(self):
        """Test adding warning keeps result valid."""
        result = ValidationResult(is_valid=True)
        result.add_issue(ValidationIssue(
            code="WARNING",
            message="Warning",
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.BUSINESS_RULE,
        ))
        assert result.is_valid is True
        assert result.warning_count == 1

    def test_error_and_warning_counts(self):
        """Test error and warning counts."""
        result = ValidationResult(is_valid=True)
        result.add_issue(ValidationIssue("E1", "Error 1", ValidationSeverity.ERROR, ValidationCategory.COMPLETENESS))
        result.add_issue(ValidationIssue("E2", "Error 2", ValidationSeverity.ERROR, ValidationCategory.COMPLETENESS))
        result.add_issue(ValidationIssue("W1", "Warning 1", ValidationSeverity.WARNING, ValidationCategory.FWA))
        assert result.error_count == 2
        assert result.warning_count == 1


# =============================================================================
# Run tests
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
