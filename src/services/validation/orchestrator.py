"""
Validation Orchestrator.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Coordinates all validation rules for comprehensive claim validation:
- Rule 1: Insured Data Extraction
- Rule 2: Code Extraction
- Rule 3: PDF Forensics
- Rule 4: ICD-CPT Crosswalk
- Rule 5: Clinical Necessity
- Rule 6: ICD×ICD Conflicts
- Rules 7-8: Demographics
- Rule 9: Documentation/Policy
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from src.schemas.validation_result import RuleValidationDetail
from src.services.validation.risk_scorer import RiskScorer, RiskAssessment

logger = logging.getLogger(__name__)


class ValidationPhase(str, Enum):
    """Validation execution phases."""

    DOCUMENT_PROCESSING = "document_processing"
    DATA_EXTRACTION = "data_extraction"
    FRAUD_DETECTION = "fraud_detection"
    MEDICAL_VALIDATION = "medical_validation"
    DOCUMENTATION_CHECK = "documentation_check"
    COVERAGE_VALIDATION = "coverage_validation"
    RESULT_AGGREGATION = "result_aggregation"


class ValidationDecision(str, Enum):
    """Overall validation decision."""

    APPROVED = "approved"                # All validations passed
    APPROVED_WITH_WARNINGS = "approved_with_warnings"  # Minor issues
    REQUIRES_REVIEW = "requires_review"  # Needs human review
    REJECTED = "rejected"                # Failed critical validations


@dataclass
class DocumentInfo:
    """Information about a document being validated."""

    document_id: Optional[str] = None
    filename: Optional[str] = None
    document_type: Optional[str] = None
    content: Optional[str] = None
    image_data: Optional[bytes] = None
    media_type: str = "image/png"
    page_count: int = 1


@dataclass
class ClaimValidationInput:
    """Input data for claim validation."""

    claim_id: str
    tenant_id: UUID
    documents: list[DocumentInfo] = field(default_factory=list)

    # Pre-extracted data (if available)
    icd_codes: list[str] = field(default_factory=list)
    cpt_codes: list[str] = field(default_factory=list)
    units_per_cpt: Optional[dict[str, int]] = None

    # Patient demographics
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    patient_dob: Optional[str] = None

    # Policy information
    policy_id: Optional[str] = None
    member_id: Optional[str] = None
    type_of_bill: Optional[str] = None
    prior_auth_number: Optional[str] = None
    claim_type: str = "professional"  # professional, institutional

    # Service information
    service_date: Optional[str] = None
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    place_of_service: str = "11"  # Office

    # Validation options
    run_llm_rules: bool = True
    run_forensics: bool = True
    skip_rules: list[str] = field(default_factory=list)


@dataclass
class PhaseResult:
    """Result from a validation phase."""

    phase: ValidationPhase
    success: bool
    rule_results: list[RuleValidationDetail] = field(default_factory=list)
    extracted_data: Optional[dict] = None
    execution_time_ms: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class ComprehensiveValidationResult:
    """Complete validation result from orchestrator."""

    claim_id: str
    decision: ValidationDecision
    is_valid: bool
    overall_confidence: float
    risk_assessment: Optional[RiskAssessment] = None

    # Phase results
    phases: list[PhaseResult] = field(default_factory=list)

    # Aggregated results
    rules_passed: int = 0
    rules_failed: int = 0
    rules_skipped: int = 0
    total_issues: int = 0
    critical_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # All rule details
    rule_results: list[RuleValidationDetail] = field(default_factory=list)

    # Extracted data summary
    extracted_data: Optional[dict] = None

    # Timing
    total_execution_time_ms: int = 0
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "claim_id": self.claim_id,
            "decision": self.decision.value,
            "is_valid": self.is_valid,
            "overall_confidence": self.overall_confidence,
            "risk_assessment": self.risk_assessment.to_dict() if self.risk_assessment else None,
            "rules_passed": self.rules_passed,
            "rules_failed": self.rules_failed,
            "rules_skipped": self.rules_skipped,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "rule_results": [
                {
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "status": r.status,
                    "confidence": r.confidence,
                    "issues_found": r.issues_found,
                    "execution_time_ms": r.execution_time_ms,
                }
                for r in self.rule_results
            ],
            "total_execution_time_ms": self.total_execution_time_ms,
            "validated_at": self.validated_at.isoformat(),
        }


class ValidationOrchestrator:
    """
    Orchestrates comprehensive claim validation.

    Execution flow:
    1. Document Processing (OCR + Classification)
    2. Data Extraction (Rules 1-2) - Sequential
    3. Fraud Detection (Rule 3) - Parallel with step 4
    4. Medical Validation (Rules 4-8) - Parallel
    5. Documentation Check (Rule 9) - After step 2
    6. Coverage Validation (Rules 11-12) - Parallel with step 4
    7. Result Aggregation + Risk Scoring

    Target: <2s total validation time
    """

    def __init__(self):
        """Initialize the orchestrator."""
        self._initialized = False
        self._risk_scorer = RiskScorer()

    async def initialize(self) -> None:
        """Initialize all validation services."""
        if self._initialized:
            return

        # Import and initialize services
        from src.gateways.search_gateway import initialize_search_gateway
        from src.services.validation.llm_validation_service import get_llm_validation_service

        try:
            await initialize_search_gateway()
            llm_service = get_llm_validation_service()
            await llm_service.initialize()
            self._initialized = True
            logger.info("Validation orchestrator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise

    async def validate_comprehensive(
        self,
        input_data: ClaimValidationInput,
    ) -> ComprehensiveValidationResult:
        """
        Perform comprehensive validation on a claim.

        Args:
            input_data: ClaimValidationInput with all claim data

        Returns:
            ComprehensiveValidationResult with all validation outcomes
        """
        import time
        start_time = time.perf_counter()

        if not self._initialized:
            await self.initialize()

        phases: list[PhaseResult] = []
        all_rule_results: list[RuleValidationDetail] = []
        extracted_data: dict = {}
        critical_issues: list[str] = []
        warnings: list[str] = []

        # Track which rules to run
        rules_to_run = self._determine_rules_to_run(input_data)

        # =====================================================================
        # Phase 1: Document Processing (if documents provided)
        # =====================================================================
        if input_data.documents:
            phase1_start = time.perf_counter()
            try:
                doc_result = await self._process_documents(input_data)
                phases.append(PhaseResult(
                    phase=ValidationPhase.DOCUMENT_PROCESSING,
                    success=True,
                    extracted_data=doc_result,
                    execution_time_ms=int((time.perf_counter() - phase1_start) * 1000),
                ))

                # Update extracted data
                if doc_result:
                    extracted_data.update(doc_result)

            except Exception as e:
                logger.error(f"Document processing failed: {e}")
                phases.append(PhaseResult(
                    phase=ValidationPhase.DOCUMENT_PROCESSING,
                    success=False,
                    errors=[str(e)],
                    execution_time_ms=int((time.perf_counter() - phase1_start) * 1000),
                ))
                warnings.append(f"Document processing failed: {str(e)}")

        # =====================================================================
        # Phase 2: Data Extraction (Rules 1-2) - if needed
        # =====================================================================
        if not input_data.icd_codes or not input_data.cpt_codes:
            phase2_start = time.perf_counter()
            try:
                extraction_results = await self._run_extraction_rules(
                    input_data, rules_to_run
                )
                all_rule_results.extend(extraction_results.rule_results)
                phases.append(PhaseResult(
                    phase=ValidationPhase.DATA_EXTRACTION,
                    success=True,
                    rule_results=extraction_results.rule_results,
                    extracted_data=extraction_results.extracted_data,
                    execution_time_ms=int((time.perf_counter() - phase2_start) * 1000),
                ))

                # Update input with extracted codes
                if extraction_results.extracted_data:
                    if "icd_codes" in extraction_results.extracted_data:
                        input_data.icd_codes = extraction_results.extracted_data["icd_codes"]
                    if "cpt_codes" in extraction_results.extracted_data:
                        input_data.cpt_codes = extraction_results.extracted_data["cpt_codes"]

            except Exception as e:
                logger.error(f"Data extraction failed: {e}")
                phases.append(PhaseResult(
                    phase=ValidationPhase.DATA_EXTRACTION,
                    success=False,
                    errors=[str(e)],
                    execution_time_ms=int((time.perf_counter() - phase2_start) * 1000),
                ))

        # =====================================================================
        # Phases 3-6: Run validation rules in parallel where possible
        # =====================================================================
        parallel_tasks = []

        # Phase 3: Fraud Detection (Rule 3)
        if input_data.run_forensics and "rule_3" in rules_to_run and input_data.documents:
            parallel_tasks.append(self._run_fraud_detection(input_data, rules_to_run))

        # Phase 4: Medical Validation (Rules 4-8)
        parallel_tasks.append(self._run_medical_validation(input_data, rules_to_run))

        # Phase 5: Documentation Check (Rule 9)
        if input_data.run_llm_rules and "rule_9" in rules_to_run:
            parallel_tasks.append(self._run_documentation_check(input_data, rules_to_run))

        # Execute parallel phases
        if parallel_tasks:
            parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)

            for result in parallel_results:
                if isinstance(result, Exception):
                    logger.error(f"Parallel validation phase failed: {result}")
                    warnings.append(f"Validation phase error: {str(result)}")
                elif isinstance(result, PhaseResult):
                    phases.append(result)
                    all_rule_results.extend(result.rule_results)

        # =====================================================================
        # Phase 7: Result Aggregation + Risk Scoring
        # =====================================================================
        phase7_start = time.perf_counter()

        # Collect all issues
        for rule_result in all_rule_results:
            if rule_result.status == "failed":
                if rule_result.issues_found > 0:
                    for detail_key in ["critical_issues", "issues"]:
                        if rule_result.details and detail_key in rule_result.details:
                            critical_issues.extend(rule_result.details[detail_key])
            elif rule_result.status == "warning":
                if rule_result.details and "warnings" in rule_result.details:
                    warnings.extend(rule_result.details["warnings"])

        # Count results
        rules_passed = len([r for r in all_rule_results if r.status == "passed"])
        rules_failed = len([r for r in all_rule_results if r.status == "failed"])
        rules_skipped = len([r for r in all_rule_results if r.status == "skipped"])
        total_issues = sum(r.issues_found for r in all_rule_results)

        # Calculate overall confidence
        if all_rule_results:
            overall_confidence = sum(r.confidence for r in all_rule_results) / len(all_rule_results)
        else:
            overall_confidence = 1.0

        # Calculate risk assessment
        risk_assessment = self._risk_scorer.calculate_risk(
            rule_results=all_rule_results,
            critical_issues=critical_issues,
            warnings=warnings,
        )

        # Determine decision
        decision = self._determine_decision(
            rules_failed=rules_failed,
            critical_issues=critical_issues,
            overall_confidence=overall_confidence,
            risk_assessment=risk_assessment,
        )

        phases.append(PhaseResult(
            phase=ValidationPhase.RESULT_AGGREGATION,
            success=True,
            execution_time_ms=int((time.perf_counter() - phase7_start) * 1000),
        ))

        total_execution_time = int((time.perf_counter() - start_time) * 1000)

        result = ComprehensiveValidationResult(
            claim_id=input_data.claim_id,
            decision=decision,
            is_valid=decision in (ValidationDecision.APPROVED, ValidationDecision.APPROVED_WITH_WARNINGS),
            overall_confidence=overall_confidence,
            risk_assessment=risk_assessment,
            phases=phases,
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            rules_skipped=rules_skipped,
            total_issues=total_issues,
            critical_issues=critical_issues[:10],  # Limit to top 10
            warnings=warnings[:20],  # Limit warnings
            rule_results=all_rule_results,
            extracted_data=extracted_data if extracted_data else None,
            total_execution_time_ms=total_execution_time,
        )

        logger.info(
            f"Claim {input_data.claim_id} validation complete: "
            f"decision={decision.value}, confidence={overall_confidence:.2f}, "
            f"time={total_execution_time}ms"
        )

        return result

    def _determine_rules_to_run(self, input_data: ClaimValidationInput) -> set[str]:
        """Determine which rules to run based on input and skip list."""
        all_rules = {
            "rule_1", "rule_2", "rule_3", "rule_4", "rule_5",
            "rule_6", "rule_7", "rule_8", "rule_9",
        }

        # Remove skipped rules
        rules_to_run = all_rules - set(input_data.skip_rules)

        # Skip extraction if codes already provided
        if input_data.icd_codes and input_data.cpt_codes:
            rules_to_run.discard("rule_1")
            rules_to_run.discard("rule_2")

        # Skip LLM rules if disabled
        if not input_data.run_llm_rules:
            rules_to_run.discard("rule_1")
            rules_to_run.discard("rule_2")
            rules_to_run.discard("rule_5")
            rules_to_run.discard("rule_9")

        # Skip forensics if disabled
        if not input_data.run_forensics:
            rules_to_run.discard("rule_3")

        return rules_to_run

    async def _process_documents(
        self,
        input_data: ClaimValidationInput,
    ) -> dict[str, Any]:
        """Process and classify documents."""
        # TODO: Implement OCR and document classification
        # For now, return empty dict
        return {}

    async def _run_extraction_rules(
        self,
        input_data: ClaimValidationInput,
        rules_to_run: set[str],
    ) -> PhaseResult:
        """Run data extraction rules (1-2)."""
        rule_results = []

        # Rule 1: Insured Data Extraction
        if "rule_1" in rules_to_run and input_data.documents:
            from src.services.extraction import get_insured_data_extractor

            extractor = get_insured_data_extractor()
            for doc in input_data.documents:
                if doc.content:
                    result = await extractor.extract_from_text(
                        doc.content, input_data.tenant_id
                    )
                    rule_results.append(RuleValidationDetail(
                        rule_id="rule_1",
                        rule_name="Insured Data Extraction",
                        status="passed" if result.success else "warning",
                        confidence=result.overall_confidence,
                        issues_found=len(result.errors),
                        details=result.to_evidence_dict(),
                        execution_time_ms=result.execution_time_ms,
                    ))

        # Rule 2: Code Extraction
        if "rule_2" in rules_to_run and input_data.documents:
            from src.services.extraction import get_code_extractor

            extractor = get_code_extractor()
            extracted_icd = []
            extracted_cpt = []

            for doc in input_data.documents:
                if doc.content:
                    result = await extractor.extract_from_text(
                        doc.content, input_data.tenant_id
                    )
                    extracted_icd.extend(result.all_icd_codes)
                    extracted_cpt.extend(result.all_cpt_codes)

                    rule_results.append(RuleValidationDetail(
                        rule_id="rule_2",
                        rule_name="Code Extraction",
                        status="passed" if result.success else "warning",
                        confidence=result.overall_confidence,
                        issues_found=len(result.errors),
                        details=result.to_evidence_dict(),
                        execution_time_ms=result.execution_time_ms,
                    ))

            return PhaseResult(
                phase=ValidationPhase.DATA_EXTRACTION,
                success=True,
                rule_results=rule_results,
                extracted_data={
                    "icd_codes": list(set(extracted_icd)),
                    "cpt_codes": list(set(extracted_cpt)),
                },
            )

        return PhaseResult(
            phase=ValidationPhase.DATA_EXTRACTION,
            success=True,
            rule_results=rule_results,
        )

    async def _run_fraud_detection(
        self,
        input_data: ClaimValidationInput,
        rules_to_run: set[str],
    ) -> PhaseResult:
        """Run fraud detection (Rule 3)."""
        import time
        start_time = time.perf_counter()
        rule_results = []

        if "rule_3" not in rules_to_run:
            return PhaseResult(
                phase=ValidationPhase.FRAUD_DETECTION,
                success=True,
            )

        from src.services.validation import get_pdf_forensics_service

        forensics = get_pdf_forensics_service()

        for doc in input_data.documents:
            if doc.image_data:
                try:
                    result = await forensics.analyze(
                        doc.image_data, doc.filename or "document.pdf"
                    )
                    rule_results.append(RuleValidationDetail(
                        rule_id="rule_3",
                        rule_name="PDF Forensics",
                        status="failed" if result.is_suspicious else "passed",
                        confidence=1.0 - result.fraud_score,
                        issues_found=len(result.signals),
                        details={
                            "fraud_score": result.fraud_score,
                            "signals": [s.to_dict() for s in result.signals],
                        },
                        execution_time_ms=result.execution_time_ms,
                    ))
                except Exception as e:
                    logger.error(f"Forensics analysis failed: {e}")

        return PhaseResult(
            phase=ValidationPhase.FRAUD_DETECTION,
            success=True,
            rule_results=rule_results,
            execution_time_ms=int((time.perf_counter() - start_time) * 1000),
        )

    async def _run_medical_validation(
        self,
        input_data: ClaimValidationInput,
        rules_to_run: set[str],
    ) -> PhaseResult:
        """Run medical validation rules (4-8)."""
        import time
        start_time = time.perf_counter()
        rule_results = []
        tasks = []

        # Rule 4: ICD-CPT Crosswalk
        if "rule_4" in rules_to_run and input_data.cpt_codes:
            tasks.append(self._validate_crosswalk(input_data))

        # Rule 5: Clinical Necessity
        if "rule_5" in rules_to_run and input_data.run_llm_rules:
            tasks.append(self._validate_clinical_necessity(input_data))

        # Rule 6: ICD×ICD Conflicts
        if "rule_6" in rules_to_run and input_data.icd_codes:
            tasks.append(self._validate_icd_conflicts(input_data))

        # Rules 7-8: Demographics
        if ("rule_7" in rules_to_run or "rule_8" in rules_to_run):
            tasks.append(self._validate_demographics(input_data))

        # Run all in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, RuleValidationDetail):
                    rule_results.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Medical validation error: {result}")

        return PhaseResult(
            phase=ValidationPhase.MEDICAL_VALIDATION,
            success=True,
            rule_results=rule_results,
            execution_time_ms=int((time.perf_counter() - start_time) * 1000),
        )

    async def _validate_crosswalk(
        self,
        input_data: ClaimValidationInput,
    ) -> RuleValidationDetail:
        """Validate ICD-CPT crosswalk (Rule 4)."""
        from src.services.validation import get_crosswalk_validator

        validator = get_crosswalk_validator()
        result = await validator.validate(
            input_data.icd_codes,
            input_data.cpt_codes,
            input_data.units_per_cpt,
        )

        return RuleValidationDetail(
            rule_id="rule_4",
            rule_name="ICD-CPT Crosswalk",
            status="passed" if result.is_valid else "failed",
            confidence=result.overall_confidence,
            issues_found=len(result.invalid_pairs),
            details=result.to_evidence_dict(),
            execution_time_ms=result.execution_time_ms,
        )

    async def _validate_clinical_necessity(
        self,
        input_data: ClaimValidationInput,
    ) -> RuleValidationDetail:
        """Validate clinical necessity (Rule 5)."""
        from src.services.validation import get_clinical_necessity_validator

        validator = get_clinical_necessity_validator()
        result = await validator.validate(
            icd_codes=input_data.icd_codes,
            cpt_codes=input_data.cpt_codes,
            patient_age=input_data.patient_age,
            patient_gender=input_data.patient_gender,
            place_of_service=input_data.place_of_service,
            tenant_id=input_data.tenant_id,
        )

        return RuleValidationDetail(
            rule_id="rule_5",
            rule_name="Clinical Necessity",
            status="passed" if result.is_valid else "failed",
            confidence=result.overall_confidence,
            issues_found=len(result.critical_issues),
            details=result.to_evidence_dict(),
            execution_time_ms=result.execution_time_ms,
        )

    async def _validate_icd_conflicts(
        self,
        input_data: ClaimValidationInput,
    ) -> RuleValidationDetail:
        """Validate ICD conflicts (Rule 6)."""
        from src.services.validation import get_icd_conflict_validator

        validator = get_icd_conflict_validator()
        result = await validator.validate(input_data.icd_codes)

        return RuleValidationDetail(
            rule_id="rule_6",
            rule_name="ICD×ICD Conflicts",
            status="passed" if result.is_valid else "failed",
            confidence=1.0 if result.is_valid else 0.5,
            issues_found=len(result.conflicts),
            details=result.to_evidence_dict(),
            execution_time_ms=result.execution_time_ms,
        )

    async def _validate_demographics(
        self,
        input_data: ClaimValidationInput,
    ) -> RuleValidationDetail:
        """Validate demographics (Rules 7-8)."""
        from src.services.validation import get_demographic_validator

        validator = get_demographic_validator()
        result = await validator.validate(
            icd_codes=input_data.icd_codes,
            cpt_codes=input_data.cpt_codes,
            patient_age_years=input_data.patient_age,
            patient_gender=input_data.patient_gender,
        )

        return RuleValidationDetail(
            rule_id="rule_7_8",
            rule_name="Demographics (Age/Gender)",
            status="passed" if result.is_valid else "failed",
            confidence=1.0 if result.is_valid else 0.5,
            issues_found=len(result.issues),
            details=result.to_evidence_dict(),
            execution_time_ms=result.execution_time_ms,
        )

    async def _run_documentation_check(
        self,
        input_data: ClaimValidationInput,
        rules_to_run: set[str],
    ) -> PhaseResult:
        """Run documentation check (Rule 9)."""
        import time
        start_time = time.perf_counter()
        rule_results = []

        if "rule_9" not in rules_to_run:
            return PhaseResult(
                phase=ValidationPhase.DOCUMENTATION_CHECK,
                success=True,
            )

        from src.services.validation import get_medical_report_validator

        validator = get_medical_report_validator()

        for doc in input_data.documents:
            if doc.content:
                result = await validator.validate(
                    document_content=doc.content,
                    service_dates=[input_data.service_date] if input_data.service_date else None,
                    diagnosis_codes=input_data.icd_codes,
                    procedure_codes=input_data.cpt_codes,
                    tenant_id=input_data.tenant_id,
                )

                rule_results.append(RuleValidationDetail(
                    rule_id="rule_9",
                    rule_name="Documentation Review",
                    status="passed" if result.is_valid else "failed",
                    confidence=result.overall_confidence,
                    issues_found=len(result.critical_issues),
                    details=result.to_evidence_dict(),
                    execution_time_ms=result.execution_time_ms,
                ))

        return PhaseResult(
            phase=ValidationPhase.DOCUMENTATION_CHECK,
            success=True,
            rule_results=rule_results,
            execution_time_ms=int((time.perf_counter() - start_time) * 1000),
        )

    def _determine_decision(
        self,
        rules_failed: int,
        critical_issues: list[str],
        overall_confidence: float,
        risk_assessment: RiskAssessment,
    ) -> ValidationDecision:
        """Determine overall validation decision."""
        # Reject if critical issues or high risk
        if len(critical_issues) > 0 or risk_assessment.risk_level == "critical":
            return ValidationDecision.REJECTED

        # Reject if multiple failures
        if rules_failed >= 3:
            return ValidationDecision.REJECTED

        # Requires review if high risk or low confidence
        if (
            risk_assessment.risk_level == "high"
            or overall_confidence < 0.7
            or rules_failed >= 2
        ):
            return ValidationDecision.REQUIRES_REVIEW

        # Approved with warnings if minor issues
        if rules_failed == 1 or risk_assessment.risk_level == "medium":
            return ValidationDecision.APPROVED_WITH_WARNINGS

        return ValidationDecision.APPROVED


# Singleton instance
_orchestrator: Optional[ValidationOrchestrator] = None


def get_validation_orchestrator() -> ValidationOrchestrator:
    """Get or create the singleton orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ValidationOrchestrator()
    return _orchestrator


async def validate_claim_comprehensive(
    input_data: ClaimValidationInput,
) -> ComprehensiveValidationResult:
    """Convenience function for comprehensive validation."""
    orchestrator = get_validation_orchestrator()
    return await orchestrator.validate_comprehensive(input_data)
