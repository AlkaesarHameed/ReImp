"""
LCD/NCD Medical Necessity API Endpoints.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Provides:
- Medical necessity validation against LCD/NCD policies
- Coverage determination lookups
- Policy search and information
"""

import logging
from datetime import date
from typing import Optional, List
from uuid import UUID

from fastapi import (
    APIRouter,
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
from src.services.medical.lcd_ncd_service import (
    LCDNCDService,
    CoverageType,
    CoverageStatus,
    MACRegion,
    get_lcd_ncd_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/medical-necessity",
    tags=["medical-necessity"],
)


# =============================================================================
# Request/Response Schemas
# =============================================================================


class MedicalNecessityCheckRequest(BaseModel):
    """Request for medical necessity check."""

    procedure_codes: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="CPT/HCPCS procedure codes to validate",
    )
    diagnosis_codes: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="ICD-10 diagnosis codes",
    )
    mac_region: Optional[str] = Field(
        None,
        description="MAC region (e.g., 'MAC_A', 'MAC_B')",
    )
    service_date: Optional[date] = Field(
        None,
        description="Date of service",
    )
    claim_id: Optional[str] = Field(
        None,
        description="Associated claim ID for tracking",
    )


class CoverageDeterminationResponse(BaseModel):
    """Coverage determination for a procedure."""

    procedure_code: str
    policy_id: Optional[str] = None
    policy_title: Optional[str] = None
    coverage_type: Optional[str] = None
    is_covered: bool
    status: str
    covered_diagnoses: List[str] = Field(default_factory=list)
    required_conditions: List[str] = Field(default_factory=list)
    documentation_requirements: List[str] = Field(default_factory=list)
    frequency_limits: Optional[str] = None
    message: Optional[str] = None


class MedicalNecessityResponse(BaseModel):
    """Response for medical necessity check."""

    is_medically_necessary: bool
    overall_status: str
    claim_id: Optional[str] = None

    # Determination details
    determinations: List[CoverageDeterminationResponse] = Field(default_factory=list)

    # Summary
    covered_procedures: List[str] = Field(default_factory=list)
    non_covered_procedures: List[str] = Field(default_factory=list)
    procedures_needing_review: List[str] = Field(default_factory=list)

    # Issues and recommendations
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # Metadata
    policies_checked: int = 0
    mac_region: Optional[str] = None
    service_date: Optional[date] = None


class PolicySearchRequest(BaseModel):
    """Request for policy search."""

    procedure_code: Optional[str] = Field(None, description="CPT/HCPCS code")
    diagnosis_code: Optional[str] = Field(None, description="ICD-10 code")
    keyword: Optional[str] = Field(None, description="Keyword search")
    coverage_type: Optional[str] = Field(None, description="LCD or NCD")
    mac_region: Optional[str] = Field(None, description="MAC region filter")
    active_only: bool = Field(True, description="Only active policies")


class PolicyResponse(BaseModel):
    """Policy information response."""

    policy_id: str
    title: str
    coverage_type: str
    status: str
    effective_date: Optional[date] = None
    termination_date: Optional[date] = None
    mac_region: Optional[str] = None
    contractor_name: Optional[str] = None
    covered_codes: List[str] = Field(default_factory=list)
    covered_diagnoses: List[str] = Field(default_factory=list)
    summary: Optional[str] = None


class PolicyListResponse(BaseModel):
    """Paginated list of policies."""

    items: List[PolicyResponse]
    total: int
    page: int
    page_size: int


class BatchNecessityRequest(BaseModel):
    """Request for batch medical necessity checks."""

    requests: List[MedicalNecessityCheckRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of necessity check requests",
    )


class BatchNecessityResponse(BaseModel):
    """Response for batch medical necessity checks."""

    total: int
    medically_necessary_count: int
    not_necessary_count: int
    review_needed_count: int
    results: List[MedicalNecessityResponse]


# =============================================================================
# Helper Functions
# =============================================================================


def convert_mac_region(region_str: Optional[str]) -> Optional[MACRegion]:
    """Convert string to MACRegion enum."""
    if not region_str:
        return None
    try:
        return MACRegion(region_str)
    except ValueError:
        return None


def build_response(result) -> MedicalNecessityResponse:
    """Convert service result to API response."""
    determinations = []
    for det in result.determinations:
        determinations.append(CoverageDeterminationResponse(
            procedure_code=det.procedure_code,
            policy_id=det.policy.policy_id if det.policy else None,
            policy_title=det.policy.title if det.policy else None,
            coverage_type=det.policy.coverage_type.value if det.policy else None,
            is_covered=det.is_covered,
            status=det.status.value,
            covered_diagnoses=det.covered_diagnoses,
            required_conditions=det.required_conditions,
            documentation_requirements=det.documentation_requirements,
            frequency_limits=det.frequency_limits,
            message=det.message,
        ))

    return MedicalNecessityResponse(
        is_medically_necessary=result.is_medically_necessary,
        overall_status=result.overall_status.value,
        claim_id=result.claim_id,
        determinations=determinations,
        covered_procedures=result.covered_procedures,
        non_covered_procedures=result.non_covered_procedures,
        procedures_needing_review=result.procedures_needing_review,
        issues=result.issues,
        recommendations=result.recommendations,
        policies_checked=result.policies_checked,
        mac_region=result.mac_region.value if result.mac_region else None,
        service_date=result.service_date,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/check",
    response_model=MedicalNecessityResponse,
    dependencies=[Depends(require_permission("medical_necessity:check"))],
)
async def check_medical_necessity(
    request: MedicalNecessityCheckRequest,
    session: AsyncSession = Depends(get_session),
) -> MedicalNecessityResponse:
    """
    Check medical necessity against LCD/NCD policies.

    Validates procedure codes against diagnosis codes using
    CMS LCD (Local Coverage Determination) and NCD (National
    Coverage Determination) policies.

    Returns:
        Medical necessity determination with coverage details.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        service = get_lcd_ncd_service()
        mac_region = convert_mac_region(request.mac_region)

        result = await service.check_medical_necessity(
            procedure_codes=request.procedure_codes,
            diagnosis_codes=request.diagnosis_codes,
            mac_region=mac_region,
            service_date=request.service_date,
            claim_id=request.claim_id,
        )

        return build_response(result)

    except Exception as e:
        logger.error(f"Medical necessity check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Medical necessity check failed: {str(e)}",
        )


@router.post(
    "/check/batch",
    response_model=BatchNecessityResponse,
    dependencies=[Depends(require_permission("medical_necessity:check"))],
)
async def batch_medical_necessity_check(
    request: BatchNecessityRequest,
    session: AsyncSession = Depends(get_session),
) -> BatchNecessityResponse:
    """
    Check medical necessity for multiple procedure sets.

    Processes up to 100 medical necessity checks.

    Returns:
        Batch results with determination for each request.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        service = get_lcd_ncd_service()
        results = []

        for req in request.requests:
            mac_region = convert_mac_region(req.mac_region)
            result = await service.check_medical_necessity(
                procedure_codes=req.procedure_codes,
                diagnosis_codes=req.diagnosis_codes,
                mac_region=mac_region,
                service_date=req.service_date,
                claim_id=req.claim_id,
            )
            results.append(result)

        responses = [build_response(r) for r in results]

        medically_necessary = sum(1 for r in results if r.is_medically_necessary)
        review_needed = sum(1 for r in results if r.procedures_needing_review)

        return BatchNecessityResponse(
            total=len(results),
            medically_necessary_count=medically_necessary,
            not_necessary_count=len(results) - medically_necessary - review_needed,
            review_needed_count=review_needed,
            results=responses,
        )

    except Exception as e:
        logger.error(f"Batch medical necessity check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch medical necessity check failed: {str(e)}",
        )


@router.get(
    "/policies",
    response_model=PolicyListResponse,
    dependencies=[Depends(require_permission("medical_necessity:read"))],
)
async def search_policies(
    procedure_code: Optional[str] = Query(None, description="CPT/HCPCS code"),
    diagnosis_code: Optional[str] = Query(None, description="ICD-10 code"),
    keyword: Optional[str] = Query(None, description="Keyword search"),
    coverage_type: Optional[str] = Query(None, description="LCD or NCD"),
    mac_region: Optional[str] = Query(None, description="MAC region"),
    active_only: bool = Query(True, description="Only active policies"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
) -> PolicyListResponse:
    """
    Search LCD/NCD policies.

    Returns paginated list of coverage policies matching criteria.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        service = get_lcd_ncd_service()

        # Get all policies and filter
        all_policies = list(service.database.policies.values())

        # Apply filters
        filtered = []
        for policy in all_policies:
            # Coverage type filter
            if coverage_type:
                try:
                    ct = CoverageType(coverage_type)
                    if policy.coverage_type != ct:
                        continue
                except ValueError:
                    pass

            # MAC region filter
            if mac_region:
                mac = convert_mac_region(mac_region)
                if mac and policy.mac_region != mac:
                    continue

            # Active only filter
            if active_only and policy.status != CoverageStatus.ACTIVE:
                continue

            # Procedure code filter
            if procedure_code and procedure_code not in policy.covered_codes:
                continue

            # Diagnosis code filter
            if diagnosis_code:
                if not any(diagnosis_code.startswith(d.replace("*", ""))
                          for d in policy.covered_diagnoses):
                    continue

            # Keyword filter
            if keyword:
                keyword_lower = keyword.lower()
                if (keyword_lower not in policy.title.lower() and
                    keyword_lower not in (policy.summary or "").lower()):
                    continue

            filtered.append(policy)

        # Pagination
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = filtered[start:end]

        # Build response
        items = []
        for policy in page_items:
            items.append(PolicyResponse(
                policy_id=policy.policy_id,
                title=policy.title,
                coverage_type=policy.coverage_type.value,
                status=policy.status.value,
                effective_date=policy.effective_date,
                termination_date=policy.termination_date,
                mac_region=policy.mac_region.value if policy.mac_region else None,
                contractor_name=policy.contractor_name,
                covered_codes=policy.covered_codes,
                covered_diagnoses=policy.covered_diagnoses,
                summary=policy.summary,
            ))

        return PolicyListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error(f"Policy search error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Policy search failed: {str(e)}",
        )


@router.get(
    "/policies/{policy_id}",
    response_model=PolicyResponse,
    dependencies=[Depends(require_permission("medical_necessity:read"))],
)
async def get_policy(
    policy_id: str,
    session: AsyncSession = Depends(get_session),
) -> PolicyResponse:
    """
    Get policy details by ID.

    Returns full details of an LCD/NCD policy.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        service = get_lcd_ncd_service()
        policy = service.database.get_policy(policy_id)

        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy {policy_id} not found",
            )

        return PolicyResponse(
            policy_id=policy.policy_id,
            title=policy.title,
            coverage_type=policy.coverage_type.value,
            status=policy.status.value,
            effective_date=policy.effective_date,
            termination_date=policy.termination_date,
            mac_region=policy.mac_region.value if policy.mac_region else None,
            contractor_name=policy.contractor_name,
            covered_codes=policy.covered_codes,
            covered_diagnoses=policy.covered_diagnoses,
            summary=policy.summary,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get policy error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get policy failed: {str(e)}",
        )


@router.get(
    "/coverage/{procedure_code}",
    response_model=List[CoverageDeterminationResponse],
    dependencies=[Depends(require_permission("medical_necessity:read"))],
)
async def get_coverage_for_procedure(
    procedure_code: str,
    mac_region: Optional[str] = Query(None, description="MAC region"),
    session: AsyncSession = Depends(get_session),
) -> List[CoverageDeterminationResponse]:
    """
    Get all coverage policies for a procedure code.

    Returns list of LCD/NCD policies that cover the procedure.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        service = get_lcd_ncd_service()
        mac = convert_mac_region(mac_region)

        policies = service.database.find_policies_for_code(
            procedure_code,
            mac_region=mac,
        )

        results = []
        for policy in policies:
            results.append(CoverageDeterminationResponse(
                procedure_code=procedure_code,
                policy_id=policy.policy_id,
                policy_title=policy.title,
                coverage_type=policy.coverage_type.value,
                is_covered=True,
                status=policy.status.value,
                covered_diagnoses=policy.covered_diagnoses,
                required_conditions=policy.required_conditions,
                documentation_requirements=policy.documentation_requirements,
                frequency_limits=policy.frequency_limits,
                message=None,
            ))

        return results

    except Exception as e:
        logger.error(f"Get coverage error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get coverage failed: {str(e)}",
        )
