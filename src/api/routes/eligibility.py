"""
Eligibility Verification API Endpoints.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Provides:
- Real-time eligibility verification
- Batch eligibility checks
- Eligibility history
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware.tenant import (
    get_current_tenant_id,
    require_permission,
)
from src.db.connection import get_session
from src.services.edi.eligibility_service import (
    EligibilityService,
    EligibilityRequest,
    EligibilityCheckResult,
    EligibilityCheckStatus,
    EligibilityResultType,
    get_eligibility_service,
)
from src.services.edi.x12_270_generator import ServiceTypeCode

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/eligibility",
    tags=["eligibility"],
)


# =============================================================================
# Request/Response Schemas
# =============================================================================


class EligibilityCheckRequest(BaseModel):
    """Request for eligibility verification."""

    # Member identification (required)
    member_id: str = Field(..., min_length=1, max_length=50, description="Member ID")
    first_name: str = Field(..., min_length=1, max_length=50, description="First name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Last name")

    # Member details (optional but recommended)
    date_of_birth: Optional[date] = Field(None, description="Date of birth")
    gender: Optional[str] = Field(None, pattern="^[MFU]$", description="Gender (M/F/U)")
    group_number: Optional[str] = Field(None, max_length=50, description="Group number")

    # Payer (required)
    payer_id: str = Field(..., min_length=1, max_length=50, description="Payer ID")
    payer_name: Optional[str] = Field(None, max_length=100, description="Payer name")

    # Provider (optional)
    provider_npi: Optional[str] = Field(None, pattern=r"^\d{10}$", description="Provider NPI")
    provider_name: Optional[str] = Field(None, max_length=100, description="Provider name")

    # Service details
    service_date: date = Field(default_factory=date.today, description="Date of service")
    service_types: Optional[List[str]] = Field(
        None,
        description="Service type codes (e.g., '30' for health benefit plan)",
    )

    # Dependent (optional)
    dependent_first_name: Optional[str] = Field(None, max_length=50)
    dependent_last_name: Optional[str] = Field(None, max_length=50)
    dependent_dob: Optional[date] = Field(None)
    dependent_gender: Optional[str] = Field(None, pattern="^[MFU]$")


class CoverageDetailResponse(BaseModel):
    """Coverage detail in response."""

    service_type: str
    service_description: Optional[str] = None
    covered: bool = True
    in_network: Optional[bool] = None
    authorization_required: bool = False
    deductible: Optional[float] = None
    copay: Optional[float] = None
    coinsurance_percent: Optional[float] = None


class EligibilityCheckResponse(BaseModel):
    """Response for eligibility verification."""

    # Identification
    check_id: str
    member_id: str
    payer_id: str

    # Status
    status: str
    result_type: str
    is_eligible: bool

    # Coverage dates
    coverage_start: Optional[date] = None
    coverage_end: Optional[date] = None
    is_coverage_active: bool = False

    # Member info
    subscriber_name: Optional[str] = None
    group_number: Optional[str] = None
    plan_name: Optional[str] = None

    # Benefits summary
    deductible: Optional[float] = None
    deductible_met: Optional[float] = None
    out_of_pocket_max: Optional[float] = None
    out_of_pocket_met: Optional[float] = None

    # Coverage details
    coverage_details: List[CoverageDetailResponse] = Field(default_factory=list)

    # Messages
    payer_message: Optional[str] = None
    errors: List[str] = Field(default_factory=list)

    # Metadata
    checked_at: str
    cached: bool = False
    processing_time_ms: int = 0


class BatchEligibilityRequest(BaseModel):
    """Request for batch eligibility checks."""

    requests: List[EligibilityCheckRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of eligibility requests (max 100)",
    )


class BatchEligibilityResponse(BaseModel):
    """Response for batch eligibility checks."""

    total: int
    eligible_count: int
    not_eligible_count: int
    error_count: int
    results: List[EligibilityCheckResponse]


class QuickEligibilityRequest(BaseModel):
    """Simplified request for quick eligibility check."""

    member_id: str = Field(..., description="Member ID")
    payer_id: str = Field(..., description="Payer ID")
    service_date: Optional[date] = Field(None, description="Date of service")


class EligibilityHistoryResponse(BaseModel):
    """Historical eligibility check record."""

    check_id: str
    member_id: str
    payer_id: str
    result_type: str
    is_eligible: bool
    checked_at: str


class EligibilityHistoryListResponse(BaseModel):
    """Paginated list of eligibility history."""

    items: List[EligibilityHistoryResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Helper Functions
# =============================================================================


def convert_result_to_response(result: EligibilityCheckResult) -> EligibilityCheckResponse:
    """Convert service result to API response."""
    coverage_details = []
    for detail in result.coverage_details:
        coverage_details.append(CoverageDetailResponse(
            service_type=detail.service_type,
            service_description=detail.service_description,
            covered=detail.covered,
            in_network=detail.in_network,
            authorization_required=detail.authorization_required,
            deductible=float(detail.deductible) if detail.deductible else None,
            copay=float(detail.copay) if detail.copay else None,
            coinsurance_percent=float(detail.coinsurance_percent) if detail.coinsurance_percent else None,
        ))

    return EligibilityCheckResponse(
        check_id=result.check_id,
        member_id=result.member_id,
        payer_id=result.payer_id,
        status=result.status.value,
        result_type=result.result_type.value,
        is_eligible=result.is_eligible,
        coverage_start=result.coverage_start,
        coverage_end=result.coverage_end,
        is_coverage_active=result.is_coverage_active,
        subscriber_name=result.subscriber_name,
        group_number=result.group_number,
        plan_name=result.plan_name,
        deductible=float(result.deductible) if result.deductible else None,
        deductible_met=float(result.deductible_met) if result.deductible_met else None,
        out_of_pocket_max=float(result.out_of_pocket_max) if result.out_of_pocket_max else None,
        out_of_pocket_met=float(result.out_of_pocket_met) if result.out_of_pocket_met else None,
        coverage_details=coverage_details,
        payer_message=result.payer_message,
        errors=result.errors,
        checked_at=result.checked_at.isoformat(),
        cached=result.cached,
        processing_time_ms=result.processing_time_ms,
    )


def build_service_request(request: EligibilityCheckRequest) -> EligibilityRequest:
    """Build service request from API request."""
    service_types = []
    if request.service_types:
        for st in request.service_types:
            try:
                service_types.append(ServiceTypeCode(st))
            except ValueError:
                pass

    if not service_types:
        service_types = [ServiceTypeCode.HEALTH_BENEFIT_PLAN_COVERAGE]

    return EligibilityRequest(
        member_id=request.member_id,
        first_name=request.first_name,
        last_name=request.last_name,
        date_of_birth=request.date_of_birth,
        gender=request.gender,
        group_number=request.group_number,
        provider_npi=request.provider_npi or "",
        provider_name=request.provider_name or "",
        payer_id=request.payer_id,
        payer_name=request.payer_name or "",
        service_date=request.service_date,
        service_type_codes=service_types,
        dependent_first_name=request.dependent_first_name,
        dependent_last_name=request.dependent_last_name,
        dependent_dob=request.dependent_dob,
        dependent_gender=request.dependent_gender,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/check",
    response_model=EligibilityCheckResponse,
    dependencies=[Depends(require_permission("eligibility:check"))],
)
async def check_eligibility(
    request: EligibilityCheckRequest,
    use_cache: bool = Query(True, description="Use cached results"),
    session: AsyncSession = Depends(get_session),
) -> EligibilityCheckResponse:
    """
    Verify member eligibility.

    Sends X12 270 inquiry to payer and returns 271 response
    with eligibility status and benefit information.

    Returns:
        Eligibility status and coverage details.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        service = get_eligibility_service()
        service_request = build_service_request(request)

        result = await service.check_eligibility(
            request=service_request,
            tenant_id=UUID(tenant_id),
            use_cache=use_cache,
        )

        return convert_result_to_response(result)

    except Exception as e:
        logger.error(f"Eligibility check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Eligibility check failed: {str(e)}",
        )


@router.post(
    "/check/quick",
    response_model=EligibilityCheckResponse,
    dependencies=[Depends(require_permission("eligibility:check"))],
)
async def quick_eligibility_check(
    request: QuickEligibilityRequest,
    session: AsyncSession = Depends(get_session),
) -> EligibilityCheckResponse:
    """
    Quick eligibility check with minimal information.

    Uses member ID and payer ID to lookup member details
    from database and perform eligibility check.

    Returns:
        Eligibility status.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        service = get_eligibility_service()

        result = await service.verify_for_claim(
            member_id=request.member_id,
            payer_id=request.payer_id,
            service_date=request.service_date or date.today(),
            tenant_id=UUID(tenant_id),
        )

        return convert_result_to_response(result)

    except Exception as e:
        logger.error(f"Quick eligibility check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Eligibility check failed: {str(e)}",
        )


@router.post(
    "/check/batch",
    response_model=BatchEligibilityResponse,
    dependencies=[Depends(require_permission("eligibility:check"))],
)
async def batch_eligibility_check(
    request: BatchEligibilityRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> BatchEligibilityResponse:
    """
    Check eligibility for multiple members.

    Processes up to 100 eligibility requests in parallel.

    Returns:
        Batch results with eligibility status for each member.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        service = get_eligibility_service()

        service_requests = [
            build_service_request(req) for req in request.requests
        ]

        results = await service.check_eligibility_batch(
            requests=service_requests,
            tenant_id=UUID(tenant_id),
            concurrency=10,
        )

        responses = [convert_result_to_response(r) for r in results]

        eligible_count = sum(1 for r in results if r.is_eligible)
        error_count = sum(1 for r in results if r.status == EligibilityCheckStatus.FAILED)

        return BatchEligibilityResponse(
            total=len(results),
            eligible_count=eligible_count,
            not_eligible_count=len(results) - eligible_count - error_count,
            error_count=error_count,
            results=responses,
        )

    except Exception as e:
        logger.error(f"Batch eligibility check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch eligibility check failed: {str(e)}",
        )


@router.get(
    "/history",
    response_model=EligibilityHistoryListResponse,
    dependencies=[Depends(require_permission("eligibility:read"))],
)
async def get_eligibility_history(
    member_id: Optional[str] = Query(None, description="Filter by member ID"),
    payer_id: Optional[str] = Query(None, description="Filter by payer ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
) -> EligibilityHistoryListResponse:
    """
    Get eligibility check history.

    Returns paginated list of historical eligibility checks.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    # In production, query from database
    # For demo, return empty list
    return EligibilityHistoryListResponse(
        items=[],
        total=0,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/history/{check_id}",
    response_model=EligibilityCheckResponse,
    dependencies=[Depends(require_permission("eligibility:read"))],
)
async def get_eligibility_check(
    check_id: str,
    session: AsyncSession = Depends(get_session),
) -> EligibilityCheckResponse:
    """
    Get specific eligibility check details.

    Returns full details of a historical eligibility check.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    # In production, fetch from database
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Eligibility check {check_id} not found",
    )


@router.delete(
    "/cache",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("eligibility:admin"))],
)
async def clear_eligibility_cache() -> None:
    """
    Clear eligibility cache.

    Clears all cached eligibility results.
    """
    service = get_eligibility_service()
    service.clear_cache()
