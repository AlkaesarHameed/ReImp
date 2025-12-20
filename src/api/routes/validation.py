"""
Validation Engine API Routes.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Provides validation endpoints for claims processing.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from src.api.deps import get_current_user, get_tenant_id
from src.models.user import User
from src.schemas.validation_result import (
    ComprehensiveValidationRequest,
    ComprehensiveValidationResponse,
    RuleValidationDetail,
    ValidationRuleInfo,
    VALIDATION_RULES,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/validation",
    tags=["Validation"],
    responses={404: {"description": "Not found"}},
)


class QuickValidationRequest(BaseModel):
    """Request for quick code validation."""

    icd_codes: list[str] = Field(..., description="ICD-10 diagnosis codes")
    cpt_codes: list[str] = Field(default=[], description="CPT procedure codes")
    patient_age: Optional[int] = Field(None, description="Patient age in years")
    patient_gender: Optional[str] = Field(None, description="Patient gender (M/F)")


class QuickValidationResponse(BaseModel):
    """Response from quick validation."""

    is_valid: bool
    issues_found: int
    critical_issues: int
    results: dict[str, Any]
    execution_time_ms: int


@router.get("/rules", response_model=list[ValidationRuleInfo])
async def list_validation_rules() -> list[ValidationRuleInfo]:
    """
    List all available validation rules.

    Returns information about each rule including:
    - Rule ID and name
    - Description
    - Whether it uses LLM
    - Enabled status
    """
    return VALIDATION_RULES


@router.post("/quick", response_model=QuickValidationResponse)
async def quick_validation(
    request: QuickValidationRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
) -> QuickValidationResponse:
    """
    Perform quick validation on codes without full claim context.

    Validates:
    - ICD×ICD conflicts (Rule 6)
    - Age/Gender appropriateness (Rules 7-8)
    - ICD-CPT crosswalk if CPT codes provided (Rule 4)
    """
    import time
    start_time = time.perf_counter()

    results: dict[str, Any] = {}
    total_issues = 0
    critical_issues = 0

    # ICD×ICD Conflict Validation (Rule 6)
    from src.services.validation import get_icd_conflict_validator

    conflict_validator = get_icd_conflict_validator()
    conflict_result = await conflict_validator.validate(request.icd_codes)
    results["icd_conflicts"] = conflict_result.to_evidence_dict()
    total_issues += len(conflict_result.conflicts)
    critical_issues += len(conflict_result.critical_conflicts)

    # Demographic Validation (Rules 7-8)
    from src.services.validation import get_demographic_validator

    demographic_validator = get_demographic_validator()
    demographic_result = await demographic_validator.validate(
        icd_codes=request.icd_codes,
        cpt_codes=request.cpt_codes,
        patient_age_years=request.patient_age,
        patient_gender=request.patient_gender,
    )
    results["demographics"] = demographic_result.to_evidence_dict()
    total_issues += len(demographic_result.issues)
    critical_issues += len(demographic_result.critical_issues)

    # ICD-CPT Crosswalk (Rule 4)
    if request.cpt_codes:
        from src.services.validation import get_crosswalk_validator

        crosswalk_validator = get_crosswalk_validator()
        crosswalk_result = await crosswalk_validator.validate(
            request.icd_codes, request.cpt_codes
        )
        results["crosswalk"] = crosswalk_result.to_evidence_dict()
        total_issues += len(crosswalk_result.invalid_pairs) + len(crosswalk_result.ncci_edits_found)
        if crosswalk_result.has_critical_issues:
            critical_issues += len(crosswalk_result.invalid_pairs)

    execution_time = int((time.perf_counter() - start_time) * 1000)

    is_valid = critical_issues == 0

    return QuickValidationResponse(
        is_valid=is_valid,
        issues_found=total_issues,
        critical_issues=critical_issues,
        results=results,
        execution_time_ms=execution_time,
    )


@router.post("/comprehensive", response_model=ComprehensiveValidationResponse)
async def comprehensive_validation(
    request: ComprehensiveValidationRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
) -> ComprehensiveValidationResponse:
    """
    Perform comprehensive validation using all applicable rules.

    Runs all enabled validation rules and returns detailed results.
    """
    import time
    from datetime import datetime, timezone

    start_time = time.perf_counter()
    rule_results: list[RuleValidationDetail] = []
    warnings: list[str] = []

    # Rule 4: ICD-CPT Crosswalk
    if request.cpt_codes:
        from src.services.validation import get_crosswalk_validator

        validator = get_crosswalk_validator()
        result = await validator.validate(
            request.icd_codes,
            request.cpt_codes,
            request.units_per_cpt,
        )
        rule_results.append(RuleValidationDetail(
            rule_id="rule_4",
            rule_name="ICD-CPT Crosswalk",
            status="passed" if result.is_valid else "failed",
            confidence=result.overall_confidence,
            issues_found=len(result.invalid_pairs),
            details=result.to_evidence_dict(),
            execution_time_ms=result.execution_time_ms,
        ))

    # Rule 5: Clinical Necessity (LLM)
    if request.run_llm_rules:
        from src.services.validation import get_clinical_necessity_validator

        validator = get_clinical_necessity_validator()
        result = await validator.validate(
            icd_codes=request.icd_codes,
            cpt_codes=request.cpt_codes,
            patient_age=request.patient_age,
            patient_gender=request.patient_gender,
            tenant_id=tenant_id,
        )
        rule_results.append(RuleValidationDetail(
            rule_id="rule_5",
            rule_name="Clinical Necessity",
            status="passed" if result.is_valid else "failed",
            confidence=result.overall_confidence,
            issues_found=len(result.critical_issues),
            details=result.to_evidence_dict(),
            execution_time_ms=result.execution_time_ms,
        ))

    # Rule 6: ICD×ICD Conflicts
    from src.services.validation import get_icd_conflict_validator

    validator = get_icd_conflict_validator()
    result = await validator.validate(request.icd_codes)
    rule_results.append(RuleValidationDetail(
        rule_id="rule_6",
        rule_name="ICD×ICD Conflicts",
        status="passed" if result.is_valid else "failed",
        confidence=1.0 if result.is_valid else 0.0,
        issues_found=len(result.conflicts),
        details=result.to_evidence_dict(),
        execution_time_ms=result.execution_time_ms,
    ))

    # Rules 7-8: Demographics
    from src.services.validation import get_demographic_validator

    validator = get_demographic_validator()
    result = await validator.validate(
        icd_codes=request.icd_codes,
        cpt_codes=request.cpt_codes,
        patient_age_years=request.patient_age,
        patient_gender=request.patient_gender,
    )
    rule_results.append(RuleValidationDetail(
        rule_id="rule_7_8",
        rule_name="Demographics (Age/Gender)",
        status="passed" if result.is_valid else "failed",
        confidence=1.0 if result.is_valid else 0.5,
        issues_found=len(result.issues),
        details=result.to_evidence_dict(),
        execution_time_ms=result.execution_time_ms,
    ))

    # Rule 9: Policy Validation
    if request.policy_id or request.type_of_bill:
        from src.services.validation import get_policy_validator

        validator = get_policy_validator()
        result = await validator.validate(
            cpt_codes=request.cpt_codes,
            icd_codes=request.icd_codes,
            policy_id=request.policy_id,
            type_of_bill=request.type_of_bill,
            prior_auth_number=request.prior_auth_number,
            claim_type=request.claim_type or "professional",
            tenant_id=tenant_id,
        )
        rule_results.append(RuleValidationDetail(
            rule_id="rule_9",
            rule_name="Policy Coverage",
            status="passed" if result.is_valid else "failed",
            confidence=0.9 if result.is_valid else 0.5,
            issues_found=len(result.issues),
            details=result.to_evidence_dict(),
            execution_time_ms=result.execution_time_ms,
        ))

    # Calculate totals
    total_issues = sum(r.issues_found for r in rule_results)
    failed_rules = [r for r in rule_results if r.status == "failed"]
    is_valid = len(failed_rules) == 0

    # Calculate overall confidence
    if rule_results:
        overall_confidence = sum(r.confidence for r in rule_results) / len(rule_results)
    else:
        overall_confidence = 1.0

    execution_time = int((time.perf_counter() - start_time) * 1000)

    return ComprehensiveValidationResponse(
        is_valid=is_valid,
        overall_confidence=overall_confidence,
        rules_passed=len([r for r in rule_results if r.status == "passed"]),
        rules_failed=len(failed_rules),
        total_issues=total_issues,
        rule_results=rule_results,
        warnings=warnings,
        execution_time_ms=execution_time,
        validated_at=datetime.now(timezone.utc),
    )


@router.post("/pdf-forensics")
async def validate_pdf_forensics(
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Perform PDF forensic analysis for fraud detection.

    Analyzes:
    - Metadata consistency
    - Font usage patterns
    - Layer analysis
    - Modification history
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF",
        )

    content = await file.read()

    from src.services.validation import get_pdf_forensics_service

    service = get_pdf_forensics_service()
    result = await service.analyze(content, file.filename)

    return {
        "is_valid": not result.is_suspicious,
        "is_suspicious": result.is_suspicious,
        "fraud_score": result.fraud_score,
        "signals": [
            {
                "type": s.signal_type.value,
                "severity": s.severity.value,
                "description": s.description,
                "confidence": s.confidence,
            }
            for s in result.signals
        ],
        "metadata": result.metadata,
        "execution_time_ms": result.execution_time_ms,
    }


@router.post("/clinical-necessity")
async def validate_clinical_necessity(
    request: QuickValidationRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Validate clinical/medical necessity of procedures.

    Uses LLM to assess whether procedures are medically justified
    based on diagnoses and clinical guidelines.
    """
    from src.services.validation import get_clinical_necessity_validator

    validator = get_clinical_necessity_validator()
    result = await validator.validate(
        icd_codes=request.icd_codes,
        cpt_codes=request.cpt_codes,
        patient_age=request.patient_age,
        patient_gender=request.patient_gender,
        tenant_id=tenant_id,
    )

    return result.to_evidence_dict() | {
        "requires_review": result.requires_review,
        "llm_provider_used": result.llm_provider_used,
        "execution_time_ms": result.execution_time_ms,
    }


class FullValidationRequest(BaseModel):
    """Request for full claim validation with documents."""

    claim_id: Optional[UUID] = Field(None, description="Existing claim ID to validate")
    member_id: Optional[str] = Field(None, description="Member ID")
    policy_id: Optional[str] = Field(None, description="Policy ID")
    provider_id: Optional[str] = Field(None, description="Provider ID")
    icd_codes: list[str] = Field(default_factory=list, description="Pre-populated ICD codes")
    cpt_codes: list[str] = Field(default_factory=list, description="Pre-populated CPT codes")
    patient_age: Optional[int] = Field(None, description="Patient age")
    patient_gender: Optional[str] = Field(None, description="Patient gender M/F")
    service_date_from: Optional[str] = Field(None, description="Service start date")
    service_date_to: Optional[str] = Field(None, description="Service end date")
    skip_rules: list[str] = Field(default_factory=list, description="Rules to skip")
    run_llm_rules: bool = Field(True, description="Whether to run LLM-based rules")


class FullValidationResponse(BaseModel):
    """Response from full validation with orchestrator."""

    validation_id: str
    claim_id: Optional[UUID] = None

    # Overall status
    overall_status: str
    is_valid: bool
    requires_review: bool

    # Risk assessment
    risk_score: float
    risk_level: str
    risk_factors: list[dict[str, Any]] = Field(default_factory=list)
    recommendation: str

    # Rule results
    rules_passed: int
    rules_failed: int
    rules_warning: int
    rules_skipped: int
    rule_details: list[dict[str, Any]] = Field(default_factory=list)

    # Extracted data (from Rules 1-2)
    extracted_insured_data: Optional[dict[str, Any]] = None
    extracted_codes: Optional[dict[str, Any]] = None

    # Issues
    critical_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    # Forensic signals
    forensic_signals: list[dict[str, Any]] = Field(default_factory=list)

    # Performance
    total_execution_time_ms: int
    phase_timings: dict[str, int] = Field(default_factory=dict)


@router.post("/full", response_model=FullValidationResponse)
async def full_validation(
    request: FullValidationRequest,
    documents: list[UploadFile] = File(default=[]),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
) -> FullValidationResponse:
    """
    Perform full validation using the ValidationOrchestrator.

    This endpoint runs all enabled validation rules including:
    - Document processing (PDF extraction, forensics)
    - Data extraction (Rules 1-2)
    - Medical validation (Rules 4-8)
    - Documentation validation (Rule 9)
    - Risk scoring and FWA detection

    Files can be uploaded as part of the request for PDF validation.
    """
    import time
    from datetime import date
    from uuid import uuid4

    from src.services.validation.orchestrator import (
        get_validation_orchestrator,
        ClaimValidationInput,
        PDFDocument,
    )

    start_time = time.perf_counter()
    validation_id = f"VAL-{uuid4().hex[:12].upper()}"

    # Read uploaded documents
    pdf_documents: list[PDFDocument] = []
    for doc in documents:
        if doc.filename and doc.filename.lower().endswith(".pdf"):
            content = await doc.read()
            pdf_documents.append(PDFDocument(
                filename=doc.filename,
                content=content,
            ))

    # Parse dates
    service_from = None
    service_to = None
    if request.service_date_from:
        try:
            service_from = date.fromisoformat(request.service_date_from)
        except ValueError:
            pass
    if request.service_date_to:
        try:
            service_to = date.fromisoformat(request.service_date_to)
        except ValueError:
            pass

    # Create orchestrator input
    validation_input = ClaimValidationInput(
        claim_id=str(request.claim_id) if request.claim_id else None,
        tenant_id=str(tenant_id),
        member_id=request.member_id,
        policy_id=request.policy_id,
        provider_id=request.provider_id,
        pdf_documents=pdf_documents,
        pre_extracted_icd_codes=request.icd_codes,
        pre_extracted_cpt_codes=request.cpt_codes,
        patient_age=request.patient_age,
        patient_gender=request.patient_gender,
        service_date_from=service_from,
        service_date_to=service_to,
        skip_rules=request.skip_rules,
        run_llm_rules=request.run_llm_rules,
    )

    # Run validation
    orchestrator = get_validation_orchestrator()
    result = await orchestrator.validate_claim(validation_input)

    total_time = int((time.perf_counter() - start_time) * 1000)

    # Extract rule status counts
    rules_passed = sum(1 for r in result.rule_results if r.status == "passed")
    rules_failed = sum(1 for r in result.rule_results if r.status == "failed")
    rules_warning = sum(1 for r in result.rule_results if r.status == "warning")
    rules_skipped = sum(1 for r in result.rule_results if r.status == "skipped")

    return FullValidationResponse(
        validation_id=validation_id,
        claim_id=request.claim_id,
        overall_status=result.overall_status,
        is_valid=result.is_valid,
        requires_review=result.requires_review,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        risk_factors=[f.to_dict() for f in result.risk_factors] if result.risk_factors else [],
        recommendation=result.recommendation,
        rules_passed=rules_passed,
        rules_failed=rules_failed,
        rules_warning=rules_warning,
        rules_skipped=rules_skipped,
        rule_details=[
            {
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "status": r.status,
                "confidence": r.confidence,
                "issues_found": r.issues_found,
                "execution_time_ms": r.execution_time_ms,
            }
            for r in result.rule_results
        ],
        extracted_insured_data=result.extracted_insured_data,
        extracted_codes=result.extracted_codes,
        critical_issues=result.critical_issues,
        warnings=result.warnings,
        forensic_signals=[
            {
                "type": s.signal_type.value,
                "severity": s.severity.value,
                "description": s.description,
                "confidence": s.confidence,
            }
            for s in result.forensic_signals
        ] if result.forensic_signals else [],
        total_execution_time_ms=total_time,
        phase_timings=result.phase_timings,
    )
