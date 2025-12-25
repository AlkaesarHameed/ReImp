"""
Claims Processing API Endpoints.

Provides:
- Claim CRUD operations
- Claim submission and workflow
- Line item management
- Status transitions
- Statistics

Source: Design Document Section 4.1 - Claims Processing
Verified: 2025-12-25
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware.tenant import (
    get_current_tenant_id,
    require_permission,
)
from src.api.middleware.rate_limit import moderate_rate_limit
from src.core.enums import (
    ClaimPriority,
    ClaimSource,
    ClaimStatus,
    ClaimType,
    DiagnosisCodeSystem,
    ProcedureCodeSystem,
)
from src.db.connection import get_session

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/claims",
    tags=["claims"],
)


# =============================================================================
# Request/Response Schemas
# =============================================================================


class LineItemCreate(BaseModel):
    """
    Schema for creating a line item.

    Supports both standard procedure codes and SAC/invoice line items.
    Field validations are relaxed to support document-first workflow.

    Source: Design Document Section 4.1 - Line Items
    Verified: 2025-12-25
    """

    procedure_code: str = Field(..., min_length=1, max_length=100)  # Allow longer for descriptions
    service_date: Optional[date] = None  # Optional for document-first
    charged_amount: Decimal = Field(..., ge=0)  # Allow 0 for line items without amounts
    quantity: int = Field(default=1, ge=1)
    procedure_code_system: Optional[str] = "CPT"  # Made string to support "CPT-4", "HCPCS", "SAC"
    modifiers: Optional[list[str]] = Field(default_factory=list)
    modifier_codes: Optional[list[str]] = None  # Alias for frontend compatibility
    description: Optional[str] = Field(None, max_length=500)
    diagnosis_pointers: list[int] = Field(default_factory=lambda: [1])
    unit_type: str = Field(default="UN", max_length=10)
    ndc_code: Optional[str] = Field(None, max_length=20)
    unit_price: Optional[Decimal] = None  # Frontend sends this


class PatientInfoCreate(BaseModel):
    """Patient information for claim submission (document-first workflow)."""

    member_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    relationship: Optional[str] = None


class ProviderInfoCreate(BaseModel):
    """Provider information for claim submission (document-first workflow)."""

    npi: Optional[str] = None
    name: Optional[str] = None
    tax_id: Optional[str] = None


class ClaimCreate(BaseModel):
    """
    Schema for creating a claim.

    Supports document-first workflow where policy/member/provider IDs may not
    be known upfront. These can be resolved later during processing.

    Source: Design Document Section 4.1 - Document-First Claims Processing
    Verified: 2025-12-25
    """

    # Optional references for document-first workflow
    policy_id: Optional[str] = None
    member_id: Optional[str] = None
    provider_id: Optional[str] = None

    # Embedded patient/provider info (for document-first workflow)
    patient: Optional[PatientInfoCreate] = None
    provider: Optional[ProviderInfoCreate] = None
    billing_provider: Optional[ProviderInfoCreate] = None
    referring_provider: Optional[ProviderInfoCreate] = None

    # Required fields
    claim_type: ClaimType
    service_date_from: date
    service_date_to: date
    # Allow empty diagnosis_codes for document-first workflow (can be populated later)
    diagnosis_codes: list[str] = Field(default_factory=list)
    primary_diagnosis: str = ""  # Allow empty for document-first workflow
    total_charged: Decimal = Field(default=Decimal("0"), ge=0)  # Allow 0 for draft claims

    # Optional fields
    currency: str = Field(default="USD", max_length=3)
    source: ClaimSource = ClaimSource.PORTAL
    priority: ClaimPriority = ClaimPriority.NORMAL
    billing_provider_id: Optional[str] = None
    referring_provider_id: Optional[str] = None
    diagnosis_code_system: DiagnosisCodeSystem = DiagnosisCodeSystem.ICD10_CM
    place_of_service: Optional[str] = Field(None, max_length=2)
    prior_auth_number: Optional[str] = Field(None, max_length=50)
    external_claim_id: Optional[str] = Field(None, max_length=100)
    admission_date: Optional[date] = None
    discharge_date: Optional[date] = None
    line_items: list[LineItemCreate] = Field(default_factory=list)


class ClaimUpdate(BaseModel):
    """Schema for updating a claim."""

    priority: Optional[ClaimPriority] = None
    diagnosis_codes: Optional[list[str]] = None
    primary_diagnosis: Optional[str] = None
    place_of_service: Optional[str] = Field(None, max_length=2)
    prior_auth_number: Optional[str] = Field(None, max_length=50)
    internal_notes: Optional[str] = None
    member_notes: Optional[str] = None


class LineItemResponse(BaseModel):
    """Schema for line item response."""

    id: str
    line_number: int
    procedure_code: str
    procedure_code_system: str
    service_date: date
    quantity: int
    charged_amount: Decimal
    allowed_amount: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    modifiers: list[str] = []
    description: Optional[str] = None
    denied: bool = False
    denial_reason: Optional[str] = None


class ClaimResponse(BaseModel):
    """Schema for claim response."""

    id: str
    tracking_number: str
    external_claim_id: Optional[str] = None
    claim_type: str
    source: str
    priority: str
    status: str
    policy_id: Optional[str] = None
    member_id: Optional[str] = None
    provider_id: Optional[str] = None
    service_date_from: date
    service_date_to: date
    diagnosis_codes: list[str]
    primary_diagnosis: str
    total_charged: Decimal
    total_allowed: Optional[Decimal] = None
    total_paid: Optional[Decimal] = None
    patient_responsibility: Optional[Decimal] = None
    currency: str
    place_of_service: Optional[str] = None
    prior_auth_number: Optional[str] = None
    fwa_score: Optional[Decimal] = None
    fwa_risk_level: Optional[str] = None
    ocr_confidence: Optional[Decimal] = None
    llm_confidence: Optional[Decimal] = None
    line_items: list[LineItemResponse] = []
    created_at: str
    updated_at: str
    submitted_at: Optional[str] = None


class ClaimListResponse(BaseModel):
    """Paginated claim list response."""

    items: list[ClaimResponse]
    total: int
    page: int
    size: int  # Changed from page_size to match frontend PaginatedResponse interface


class ClaimSubmitResponse(BaseModel):
    """Response after submitting a claim."""

    claim_id: str
    tracking_number: str
    status: str
    message: str


class ClaimActionRequest(BaseModel):
    """Request for claim actions (approve/deny)."""

    reason: Optional[str] = Field(None, max_length=500)
    denial_codes: Optional[list[str]] = None
    total_allowed: Optional[Decimal] = None
    total_paid: Optional[Decimal] = None
    patient_responsibility: Optional[Decimal] = None


class ClaimStatsResponse(BaseModel):
    """Claim statistics response."""

    by_status: dict
    total_claims: int
    total_charged: float
    total_paid: float


class ValidationIssueResponse(BaseModel):
    """Single validation issue."""

    code: str
    message: str
    severity: str
    category: str
    field: Optional[str] = None


class ValidationResultResponse(BaseModel):
    """Claim validation result."""

    is_valid: bool
    error_count: int
    warning_count: int
    issues: list[ValidationIssueResponse]
    fwa_score: float
    fwa_risk_level: str
    fwa_flags: list[str]


# =============================================================================
# Helper Functions
# =============================================================================


def _claim_to_response(claim) -> ClaimResponse:
    """Convert claim model to response schema."""
    line_items = []
    if claim.line_items:
        for item in claim.line_items:
            line_items.append(LineItemResponse(
                id=str(item.id),
                line_number=item.line_number,
                procedure_code=item.procedure_code,
                procedure_code_system=item.procedure_code_system.value,
                service_date=item.service_date,
                quantity=item.quantity,
                charged_amount=item.charged_amount,
                allowed_amount=item.allowed_amount,
                paid_amount=item.paid_amount,
                modifiers=item.modifiers or [],
                description=item.description,
                denied=item.denied,
                denial_reason=item.denial_reason,
            ))

    return ClaimResponse(
        id=str(claim.id),
        tracking_number=claim.tracking_number,
        external_claim_id=claim.external_claim_id,
        claim_type=claim.claim_type.value,
        source=claim.source.value,
        priority=claim.priority.value,
        status=claim.status.value,
        policy_id=str(claim.policy_id) if claim.policy_id else None,
        member_id=str(claim.member_id) if claim.member_id else None,
        provider_id=str(claim.provider_id) if claim.provider_id else None,
        service_date_from=claim.service_date_from,
        service_date_to=claim.service_date_to,
        diagnosis_codes=claim.diagnosis_codes,
        primary_diagnosis=claim.primary_diagnosis,
        total_charged=claim.total_charged,
        total_allowed=claim.total_allowed,
        total_paid=claim.total_paid,
        patient_responsibility=claim.patient_responsibility,
        currency=claim.currency,
        place_of_service=claim.place_of_service,
        prior_auth_number=claim.prior_auth_number,
        fwa_score=claim.fwa_score,
        fwa_risk_level=claim.fwa_risk_level.value if claim.fwa_risk_level else None,
        ocr_confidence=claim.ocr_confidence,
        llm_confidence=claim.llm_confidence,
        line_items=line_items,
        created_at=claim.created_at.isoformat(),
        updated_at=claim.updated_at.isoformat(),
        submitted_at=claim.submitted_at.isoformat() if claim.submitted_at else None,
    )


# =============================================================================
# CRUD Endpoints
# =============================================================================


@router.post(
    "/",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("claims:create"))],
)
async def create_claim(
    claim_data: ClaimCreate,
    session: AsyncSession = Depends(get_session),
) -> ClaimResponse:
    """
    Create a new claim in DRAFT status.

    The claim will need to be submitted separately to begin processing.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        from src.services.claims_service import (
            ClaimsService,
            ClaimCreateDTO,
            LineItemDTO,
        )

        service = ClaimsService(session)

        # Convert to DTOs
        create_dto = ClaimCreateDTO(
            tenant_id=tenant_id,
            policy_id=claim_data.policy_id,
            member_id=claim_data.member_id,
            provider_id=claim_data.provider_id,
            claim_type=claim_data.claim_type,
            service_date_from=claim_data.service_date_from,
            service_date_to=claim_data.service_date_to,
            diagnosis_codes=claim_data.diagnosis_codes,
            primary_diagnosis=claim_data.primary_diagnosis,
            total_charged=claim_data.total_charged,
            currency=claim_data.currency,
            source=claim_data.source,
            priority=claim_data.priority,
            billing_provider_id=claim_data.billing_provider_id,
            referring_provider_id=claim_data.referring_provider_id,
            diagnosis_code_system=claim_data.diagnosis_code_system,
            place_of_service=claim_data.place_of_service,
            prior_auth_number=claim_data.prior_auth_number,
            external_claim_id=claim_data.external_claim_id,
            admission_date=claim_data.admission_date,
            discharge_date=claim_data.discharge_date,
        )

        line_items = []
        for item in claim_data.line_items:
            # Normalize procedure_code_system to lowercase for enum matching
            # Frontend may send 'HCPCS' (uppercase) but enum expects 'hcpcs'
            proc_system = item.procedure_code_system
            if proc_system and isinstance(proc_system, str):
                proc_system_lower = proc_system.lower()
                # Try to convert to enum, default to CPT if not recognized
                try:
                    proc_system = ProcedureCodeSystem(proc_system_lower)
                except ValueError:
                    proc_system = ProcedureCodeSystem.CPT
            elif proc_system is None:
                proc_system = ProcedureCodeSystem.CPT

            line_items.append(
                LineItemDTO(
                    procedure_code=item.procedure_code,
                    service_date=item.service_date,
                    charged_amount=item.charged_amount,
                    quantity=item.quantity,
                    procedure_code_system=proc_system,
                    modifiers=item.modifiers or item.modifier_codes,  # Support both field names
                    description=item.description,
                    diagnosis_pointers=item.diagnosis_pointers,
                    unit_type=item.unit_type,
                    ndc_code=item.ndc_code,
                )
            )

        claim = await service.create_claim(create_dto, line_items)
        return _claim_to_response(claim)

    except Exception as e:
        logger.error(f"Claim creation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=ClaimListResponse,
    dependencies=[Depends(require_permission("claims:read"))],
)
async def list_claims(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[ClaimStatus] = Query(None, alias="status"),
    member_id: Optional[str] = None,
    provider_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    priority: Optional[ClaimPriority] = None,
    session: AsyncSession = Depends(get_session),
) -> ClaimListResponse:
    """List claims with pagination and filters."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        from src.services.claims_service import ClaimsService

        service = ClaimsService(session)
        skip = (page - 1) * page_size

        claims, total = await service.list_claims(
            tenant_id=tenant_id,
            skip=skip,
            limit=page_size,
            status=status_filter,
            member_id=member_id,
            provider_id=provider_id,
            date_from=date_from,
            date_to=date_to,
            priority=priority,
        )

        return ClaimListResponse(
            items=[_claim_to_response(c) for c in claims],
            total=total,
            page=page,
            size=page_size,  # Changed to match frontend PaginatedResponse interface
        )

    except Exception as e:
        logger.error(f"Claim list error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/{claim_id}",
    response_model=ClaimResponse,
    dependencies=[Depends(require_permission("claims:read"))],
)
async def get_claim(
    claim_id: str,
    session: AsyncSession = Depends(get_session),
) -> ClaimResponse:
    """Get a specific claim by ID."""
    try:
        from src.services.claims_service import ClaimsService, ClaimNotFoundError

        service = ClaimsService(session)
        claim = await service.get_claim(
            claim_id,
            include_line_items=True,
            include_documents=False,
            include_history=False,
        )

        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim not found: {claim_id}",
            )

        return _claim_to_response(claim)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get claim error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.patch(
    "/{claim_id}",
    response_model=ClaimResponse,
    dependencies=[Depends(require_permission("claims:update"))],
)
async def update_claim(
    claim_id: str,
    update_data: ClaimUpdate,
    session: AsyncSession = Depends(get_session),
) -> ClaimResponse:
    """Update a claim (only allowed for DRAFT/NEEDS_REVIEW status)."""
    try:
        from src.services.claims_service import (
            ClaimsService,
            ClaimNotFoundError,
            ClaimStatusTransitionError,
            ClaimUpdateDTO,
        )

        service = ClaimsService(session)

        update_dto = ClaimUpdateDTO(
            priority=update_data.priority,
            diagnosis_codes=update_data.diagnosis_codes,
            primary_diagnosis=update_data.primary_diagnosis,
            place_of_service=update_data.place_of_service,
            prior_auth_number=update_data.prior_auth_number,
            internal_notes=update_data.internal_notes,
            member_notes=update_data.member_notes,
        )

        claim = await service.update_claim(claim_id, update_dto)
        return _claim_to_response(claim)

    except ClaimNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim not found: {claim_id}",
        )
    except ClaimStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Update claim error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete(
    "/{claim_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("claims:delete"))],
)
async def delete_claim(
    claim_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a claim (only allowed for DRAFT status)."""
    try:
        from src.services.claims_service import (
            ClaimsService,
            ClaimNotFoundError,
            ClaimStatusTransitionError,
        )

        service = ClaimsService(session)
        await service.delete_claim(claim_id, soft_delete=True)

    except ClaimNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim not found: {claim_id}",
        )
    except ClaimStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


# =============================================================================
# Workflow Endpoints
# =============================================================================


@router.post(
    "/{claim_id}/submit",
    response_model=ClaimSubmitResponse,
    dependencies=[Depends(require_permission("claims:submit"))],
)
async def submit_claim(
    claim_id: str,
    session: AsyncSession = Depends(get_session),
) -> ClaimSubmitResponse:
    """
    Submit a DRAFT claim for processing.

    Transitions: DRAFT -> SUBMITTED
    """
    from src.api.middleware.tenant import get_current_user_id

    user_id = get_current_user_id()

    try:
        from src.services.claims_service import (
            ClaimsService,
            ClaimNotFoundError,
            ClaimStatusTransitionError,
            ClaimValidationError,
        )

        service = ClaimsService(session)
        claim = await service.submit_claim(claim_id, user_id or "system")

        return ClaimSubmitResponse(
            claim_id=str(claim.id),
            tracking_number=claim.tracking_number,
            status=claim.status.value,
            message="Claim submitted successfully",
        )

    except ClaimNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim not found: {claim_id}",
        )
    except ClaimValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(e), "errors": e.errors},
        )
    except ClaimStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/{claim_id}/approve",
    response_model=ClaimResponse,
    dependencies=[Depends(require_permission("claims:approve"))],
)
async def approve_claim(
    claim_id: str,
    action_data: ClaimActionRequest,
    session: AsyncSession = Depends(get_session),
) -> ClaimResponse:
    """
    Approve a claim.

    Valid from: VALIDATING, ADJUDICATING, NEEDS_REVIEW
    """
    from src.api.middleware.tenant import get_current_user_id

    user_id = get_current_user_id()

    try:
        from src.services.claims_service import (
            ClaimsService,
            ClaimNotFoundError,
            ClaimStatusTransitionError,
        )

        service = ClaimsService(session)
        claim = await service.approve_claim(
            claim_id=claim_id,
            approved_by=user_id or "system",
            total_allowed=action_data.total_allowed,
            total_paid=action_data.total_paid,
            patient_responsibility=action_data.patient_responsibility,
        )

        return _claim_to_response(claim)

    except ClaimNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim not found: {claim_id}",
        )
    except ClaimStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/{claim_id}/deny",
    response_model=ClaimResponse,
    dependencies=[Depends(require_permission("claims:deny"))],
)
async def deny_claim(
    claim_id: str,
    action_data: ClaimActionRequest,
    session: AsyncSession = Depends(get_session),
) -> ClaimResponse:
    """
    Deny a claim.

    Valid from: VALIDATING, ADJUDICATING, NEEDS_REVIEW
    Requires reason.
    """
    if not action_data.reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Denial reason is required",
        )

    from src.api.middleware.tenant import get_current_user_id

    user_id = get_current_user_id()

    try:
        from src.services.claims_service import (
            ClaimsService,
            ClaimNotFoundError,
            ClaimStatusTransitionError,
        )

        service = ClaimsService(session)
        claim = await service.deny_claim(
            claim_id=claim_id,
            denied_by=user_id or "system",
            denial_reason=action_data.reason,
            denial_codes=action_data.denial_codes,
        )

        return _claim_to_response(claim)

    except ClaimNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim not found: {claim_id}",
        )
    except ClaimStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/{claim_id}/flag-review",
    response_model=ClaimResponse,
    dependencies=[Depends(require_permission("claims:review"))],
)
async def flag_for_review(
    claim_id: str,
    action_data: ClaimActionRequest,
    session: AsyncSession = Depends(get_session),
) -> ClaimResponse:
    """Flag a claim for manual review."""
    if not action_data.reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Review reason is required",
        )

    from src.api.middleware.tenant import get_current_user_id

    user_id = get_current_user_id()

    try:
        from src.services.claims_service import (
            ClaimsService,
            ClaimNotFoundError,
            ClaimStatusTransitionError,
        )

        service = ClaimsService(session)
        claim = await service.flag_for_review(
            claim_id=claim_id,
            reason=action_data.reason,
            flagged_by=user_id,
        )

        return _claim_to_response(claim)

    except ClaimNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim not found: {claim_id}",
        )
    except ClaimStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


# =============================================================================
# Validation Endpoint
# =============================================================================


@router.post(
    "/{claim_id}/validate",
    response_model=ValidationResultResponse,
    dependencies=[Depends(require_permission("claims:read"))],
)
async def validate_claim(
    claim_id: str,
    session: AsyncSession = Depends(get_session),
) -> ValidationResultResponse:
    """
    Validate a claim without changing its status.

    Returns validation issues and FWA analysis.
    """
    try:
        from src.services.claims_service import ClaimsService, ClaimNotFoundError
        from src.services.claim_validation import (
            ClaimValidationService,
            ClaimData,
            LineItemData,
        )

        claims_service = ClaimsService(session)
        claim = await claims_service.get_claim(claim_id, include_line_items=True)

        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim not found: {claim_id}",
            )

        # Convert to validation data
        line_items = [
            LineItemData(
                line_number=item.line_number,
                procedure_code=item.procedure_code,
                procedure_code_system=item.procedure_code_system,
                service_date=item.service_date,
                charged_amount=item.charged_amount,
                quantity=item.quantity,
                modifiers=item.modifiers or [],
                diagnosis_pointers=item.diagnosis_pointers or [1],
                ndc_code=item.ndc_code,
            )
            for item in claim.line_items
        ]

        claim_data = ClaimData(
            claim_id=str(claim.id),
            tenant_id=str(claim.tenant_id),
            tracking_number=claim.tracking_number,
            claim_type=claim.claim_type,
            policy_id=str(claim.policy_id),
            member_id=str(claim.member_id),
            provider_id=str(claim.provider_id),
            service_date_from=claim.service_date_from,
            service_date_to=claim.service_date_to,
            diagnosis_codes=claim.diagnosis_codes,
            primary_diagnosis=claim.primary_diagnosis,
            diagnosis_code_system=claim.diagnosis_code_system,
            total_charged=claim.total_charged,
            currency=claim.currency,
            line_items=line_items,
            prior_auth_number=claim.prior_auth_number,
            prior_auth_required=claim.prior_auth_required,
            place_of_service=claim.place_of_service,
        )

        validation_service = ClaimValidationService()
        result = await validation_service.validate_claim(claim_data)

        return ValidationResultResponse(
            is_valid=result.is_valid,
            error_count=result.error_count,
            warning_count=result.warning_count,
            issues=[
                ValidationIssueResponse(
                    code=issue.code,
                    message=issue.message,
                    severity=issue.severity.value,
                    category=issue.category.value,
                    field=issue.field,
                )
                for issue in result.issues
            ],
            fwa_score=result.fwa_score,
            fwa_risk_level=result.fwa_risk_level.value,
            fwa_flags=result.fwa_flags,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# =============================================================================
# Statistics Endpoint
# =============================================================================


@router.get(
    "/stats/summary",
    response_model=ClaimStatsResponse,
    dependencies=[Depends(require_permission("claims:read"))],
)
async def get_claims_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    session: AsyncSession = Depends(get_session),
) -> ClaimStatsResponse:
    """Get claims statistics for the tenant."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        from src.services.claims_service import ClaimsService

        service = ClaimsService(session)
        stats = await service.get_claims_stats(
            tenant_id=tenant_id,
            date_from=date_from,
            date_to=date_to,
        )

        return ClaimStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Stats error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# =============================================================================
# Validation History & Rejection Endpoints
# =============================================================================


class ValidationResultItem(BaseModel):
    """Single validation result item."""

    id: str
    rule_id: str
    rule_name: str
    status: str
    confidence: Optional[float] = None
    issues_found: int = 0
    details: Optional[dict] = None
    execution_time_ms: Optional[int] = None
    created_at: str


class ValidationHistoryResponse(BaseModel):
    """Validation history for a claim."""

    claim_id: str
    total_validations: int
    latest_validation_at: Optional[str] = None
    overall_status: str
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    results: list[ValidationResultItem]


class RejectionEvidenceItem(BaseModel):
    """Evidence item for a rejection."""

    id: str
    signal_type: str
    severity: str
    confidence: float
    title: str
    description: str
    document_name: Optional[str] = None
    page_number: Optional[int] = None
    reference_source: Optional[str] = None


class RejectionDetailResponse(BaseModel):
    """Detailed rejection information."""

    id: str
    claim_id: str
    rejection_id: str
    rejection_date: str
    category: str
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    summary: str
    reasoning: list[str]
    triggered_rules: list[str]
    evidence: list[RejectionEvidenceItem]
    appeal_deadline: Optional[str] = None
    appeal_status: str
    can_appeal: bool
    created_at: str


class AppealRequest(BaseModel):
    """Request to submit an appeal."""

    reason: str = Field(..., min_length=10, max_length=2000)
    supporting_documents: list[str] = Field(default_factory=list)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class AppealResponse(BaseModel):
    """Response after submitting an appeal."""

    appeal_id: str
    claim_id: str
    rejection_id: str
    status: str
    submitted_at: str
    estimated_review_date: Optional[str] = None
    message: str


@router.get(
    "/{claim_id}/validation-results",
    response_model=ValidationHistoryResponse,
    dependencies=[Depends(require_permission("claims:read"))],
)
async def get_validation_results(
    claim_id: str,
    session: AsyncSession = Depends(get_session),
) -> ValidationHistoryResponse:
    """
    Get validation history for a claim.

    Returns all validation results including:
    - Individual rule results
    - Overall status and risk assessment
    - Execution timestamps
    """
    from sqlalchemy import select
    from uuid import UUID

    try:
        claim_uuid = UUID(claim_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid claim ID format",
        )

    try:
        # Check claim exists and user has access
        from src.services.claims_service import ClaimsService, ClaimNotFoundError

        claims_service = ClaimsService(session)
        claim = await claims_service.get_claim(claim_id)

        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim not found: {claim_id}",
            )

        # Get validation results from database
        from src.models.validation_result import ValidationResult, ClaimRejection, RejectionEvidence

        result = await session.execute(
            select(ValidationResult)
            .where(ValidationResult.claim_id == claim_uuid)
            .order_by(ValidationResult.created_at.desc())
        )
        validation_results = result.scalars().all()

        # Determine overall status
        if not validation_results:
            overall_status = "not_validated"
            risk_score = None
            risk_level = None
        else:
            failed_count = sum(1 for r in validation_results if r.status == "failed")
            warning_count = sum(1 for r in validation_results if r.status == "warning")

            if failed_count > 0:
                overall_status = "failed"
            elif warning_count > 0:
                overall_status = "warning"
            else:
                overall_status = "passed"

            # Get risk from claim
            risk_score = float(claim.fwa_score) if claim.fwa_score else None
            risk_level = claim.fwa_risk_level.value if claim.fwa_risk_level else None

        return ValidationHistoryResponse(
            claim_id=claim_id,
            total_validations=len(validation_results),
            latest_validation_at=validation_results[0].created_at.isoformat() if validation_results else None,
            overall_status=overall_status,
            risk_score=risk_score,
            risk_level=risk_level,
            results=[
                ValidationResultItem(
                    id=str(r.id),
                    rule_id=r.rule_id,
                    rule_name=r.rule_name,
                    status=r.status,
                    confidence=float(r.confidence) if r.confidence else None,
                    issues_found=r.details.get("issues_found", 0) if r.details else 0,
                    details=r.details,
                    execution_time_ms=r.execution_time_ms,
                    created_at=r.created_at.isoformat(),
                )
                for r in validation_results
            ],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get validation results error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/{claim_id}/rejection",
    response_model=RejectionDetailResponse,
    dependencies=[Depends(require_permission("claims:read"))],
)
async def get_rejection_details(
    claim_id: str,
    session: AsyncSession = Depends(get_session),
) -> RejectionDetailResponse:
    """
    Get rejection details for a claim.

    Returns comprehensive rejection information including:
    - Rejection category and reasoning
    - Evidence references
    - Appeal status and deadline
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from uuid import UUID
    from datetime import datetime, timezone

    try:
        claim_uuid = UUID(claim_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid claim ID format",
        )

    try:
        from src.models.validation_result import ClaimRejection

        # Get rejection with evidence
        result = await session.execute(
            select(ClaimRejection)
            .options(selectinload(ClaimRejection.evidence_items))
            .where(ClaimRejection.claim_id == claim_uuid)
            .order_by(ClaimRejection.created_at.desc())
        )
        rejection = result.scalars().first()

        if not rejection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No rejection found for claim: {claim_id}",
            )

        # Determine if appeal is still possible
        now = datetime.now(timezone.utc)
        can_appeal = (
            rejection.appeal_status in ("none", "denied")
            and rejection.appeal_deadline
            and rejection.appeal_deadline > now
        )

        return RejectionDetailResponse(
            id=str(rejection.id),
            claim_id=claim_id,
            rejection_id=rejection.rejection_id,
            rejection_date=rejection.rejection_date.isoformat(),
            category=rejection.category,
            risk_score=float(rejection.risk_score) if rejection.risk_score else None,
            risk_level=rejection.risk_level,
            summary=rejection.summary,
            reasoning=rejection.reasoning if isinstance(rejection.reasoning, list) else [],
            triggered_rules=rejection.triggered_rules if rejection.triggered_rules else [],
            evidence=[
                RejectionEvidenceItem(
                    id=str(e.id),
                    signal_type=e.signal_type,
                    severity=e.severity,
                    confidence=float(e.confidence),
                    title=e.title,
                    description=e.description,
                    document_name=e.document_name,
                    page_number=e.page_number,
                    reference_source=e.reference_source,
                )
                for e in (rejection.evidence_items or [])
            ],
            appeal_deadline=rejection.appeal_deadline.isoformat() if rejection.appeal_deadline else None,
            appeal_status=rejection.appeal_status or "none",
            can_appeal=can_appeal,
            created_at=rejection.created_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get rejection details error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/{claim_id}/appeal",
    response_model=AppealResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("claims:appeal"))],
)
async def submit_appeal(
    claim_id: str,
    appeal_request: AppealRequest,
    session: AsyncSession = Depends(get_session),
) -> AppealResponse:
    """
    Submit an appeal for a rejected claim.

    Requirements:
    - Claim must have a rejection
    - Appeal deadline must not have passed
    - Previous appeal must not be pending
    """
    from sqlalchemy import select
    from uuid import UUID, uuid4
    from datetime import datetime, timezone, timedelta

    try:
        claim_uuid = UUID(claim_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid claim ID format",
        )

    try:
        from src.models.validation_result import ClaimRejection

        # Get the rejection
        result = await session.execute(
            select(ClaimRejection)
            .where(ClaimRejection.claim_id == claim_uuid)
            .order_by(ClaimRejection.created_at.desc())
        )
        rejection = result.scalars().first()

        if not rejection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No rejection found for claim: {claim_id}",
            )

        # Check if appeal is allowed
        now = datetime.now(timezone.utc)

        if rejection.appeal_status == "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An appeal is already pending for this rejection",
            )

        if rejection.appeal_status == "under_review":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An appeal is currently under review",
            )

        if rejection.appeal_deadline and rejection.appeal_deadline < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Appeal deadline has passed",
            )

        # Update rejection with appeal
        rejection.appeal_status = "pending"
        rejection.appeal_notes = appeal_request.reason
        rejection.updated_at = now

        await session.commit()

        # Generate appeal ID
        appeal_id = f"APL-{uuid4().hex[:12].upper()}"

        # Estimated review date (10 business days)
        estimated_review = now + timedelta(days=14)

        logger.info(f"Appeal submitted for claim {claim_id}, rejection {rejection.rejection_id}")

        return AppealResponse(
            appeal_id=appeal_id,
            claim_id=claim_id,
            rejection_id=rejection.rejection_id,
            status="pending",
            submitted_at=now.isoformat(),
            estimated_review_date=estimated_review.isoformat(),
            message="Appeal submitted successfully. You will be notified of the decision.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Submit appeal error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
