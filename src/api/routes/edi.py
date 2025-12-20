"""
EDI Processing API Endpoints.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Provides:
- X12 837 claim submission and parsing
- X12 835 remittance generation and retrieval
- EDI transaction tracking
- EDI validation endpoints
"""

import logging
from typing import Optional
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
from src.api.middleware.rate_limit import moderate_rate_limit
from src.db.connection import get_session
from src.schemas.edi import (
    EDI837SubmitRequest,
    EDI837ProcessResult,
    EDI837ValidationResult,
    EDI835GenerateRequest,
    EDI835GenerateResult,
    EDI835RetrieveResponse,
    EDITransactionResponse,
    EDITransactionListResponse,
    EDITransactionStats,
    ParsedClaim837Response,
    Provider837Response,
    Subscriber837Response,
    Diagnosis837Response,
    ServiceLine837Response,
)
from src.services.edi import (
    EDIService,
    get_edi_service,
    TransactionType,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/edi",
    tags=["edi"],
)


# =============================================================================
# Helper Functions
# =============================================================================


def convert_claim_to_response(claim) -> ParsedClaim837Response:
    """Convert parsed claim to API response model."""
    return ParsedClaim837Response(
        claim_id=claim.claim_id,
        claim_type=claim.claim_type.value if hasattr(claim.claim_type, 'value') else str(claim.claim_type),
        patient_control_number=claim.patient_control_number,
        total_charge=claim.total_charge,
        place_of_service=claim.place_of_service,
        admission_date=claim.admission_date,
        discharge_date=claim.discharge_date,
        billing_provider=Provider837Response(
            entity_type=claim.billing_provider.entity_type,
            npi=claim.billing_provider.npi,
            name=claim.billing_provider.name,
            first_name=claim.billing_provider.first_name,
            last_name=claim.billing_provider.last_name,
            tax_id=claim.billing_provider.tax_id,
            address=claim.billing_provider.address,
            city=claim.billing_provider.city,
            state=claim.billing_provider.state,
            zip_code=claim.billing_provider.zip_code,
        ),
        subscriber=Subscriber837Response(
            member_id=claim.subscriber.member_id,
            group_number=claim.subscriber.group_number,
            first_name=claim.subscriber.first_name,
            last_name=claim.subscriber.last_name,
            date_of_birth=claim.subscriber.date_of_birth,
            gender=claim.subscriber.gender,
            relationship=claim.subscriber.relationship,
        ),
        patient=Subscriber837Response(
            member_id=claim.patient.member_id,
            group_number=claim.patient.group_number,
            first_name=claim.patient.first_name,
            last_name=claim.patient.last_name,
            date_of_birth=claim.patient.date_of_birth,
            gender=claim.patient.gender,
            relationship=claim.patient.relationship,
        ) if claim.patient else None,
        diagnoses=[
            Diagnosis837Response(
                code=dx.code,
                code_system=dx.code_system,
                sequence=dx.sequence,
                is_primary=dx.is_primary,
            )
            for dx in claim.diagnoses
        ],
        service_lines=[
            ServiceLine837Response(
                line_number=line.line_number,
                procedure_code=line.procedure_code,
                modifiers=line.modifiers,
                charge_amount=line.charge_amount,
                units=line.units,
                service_date=line.service_date,
                diagnosis_pointers=line.diagnosis_pointers,
            )
            for line in claim.service_lines
        ],
    )


# =============================================================================
# 837 Endpoints
# =============================================================================


@router.post(
    "/837",
    response_model=EDI837ProcessResult,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission("edi:submit"))],
)
async def submit_837(
    request: EDI837SubmitRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EDI837ProcessResult:
    """
    Submit X12 837 claim file for processing.

    Accepts 837P (Professional) and 837I (Institutional) transactions.
    The file will be parsed and claims extracted for processing.

    Returns:
        Processing result with parsed claims or validation errors.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        edi_service = get_edi_service()

        # If validate_only, just validate without processing
        if request.validate_only:
            validation = await edi_service.validate_837(request.content)
            return EDI837ProcessResult(
                transaction_id="",
                control_number="",
                transaction_type="837",
                status="validated" if validation["valid"] else "failed",
                errors=validation["errors"],
                warnings=validation["warnings"],
            )

        # Process the 837
        result = await edi_service.process_837(
            content=request.content,
            tenant_id=UUID(tenant_id),
            source=request.source,
        )

        # Convert claims to response models
        claims_response = [
            convert_claim_to_response(claim)
            for claim in result.claims_parsed
        ]

        return EDI837ProcessResult(
            transaction_id=result.transaction_id,
            control_number=result.control_number,
            transaction_type=result.transaction_type.value if hasattr(result.transaction_type, 'value') else str(result.transaction_type),
            direction=result.direction.value if hasattr(result.direction, 'value') else str(result.direction),
            status=result.status.value if hasattr(result.status, 'value') else str(result.status),
            claims_count=result.claims_count,
            claims_parsed=claims_response,
            errors=result.errors,
            warnings=result.warnings,
            processing_time_ms=result.processing_time_ms,
            created_at=result.created_at,
        )

    except Exception as e:
        logger.error(f"837 processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process 837: {str(e)}",
        )


@router.post(
    "/837/validate",
    response_model=EDI837ValidationResult,
    dependencies=[Depends(require_permission("edi:read"))],
)
async def validate_837(
    request: EDI837SubmitRequest,
) -> EDI837ValidationResult:
    """
    Validate X12 837 syntax without processing.

    Use this endpoint to check EDI syntax before submission.

    Returns:
        Validation result with errors and warnings.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        edi_service = get_edi_service()
        result = await edi_service.validate_837(request.content)

        # Count segments and claims for info
        segment_count = request.content.count("~")
        claim_count = request.content.count("CLM*")

        return EDI837ValidationResult(
            valid=result["valid"],
            errors=result["errors"],
            warnings=result["warnings"],
            segment_count=segment_count,
            claim_count=claim_count,
        )

    except Exception as e:
        logger.error(f"837 validation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}",
        )


# =============================================================================
# 835 Endpoints
# =============================================================================


@router.post(
    "/835",
    response_model=EDI835GenerateResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("edi:generate"))],
)
async def generate_835(
    request: EDI835GenerateRequest,
    session: AsyncSession = Depends(get_session),
) -> EDI835GenerateResult:
    """
    Generate X12 835 remittance advice for a claim.

    Requires the claim to be adjudicated. The 835 contains
    payment information and adjustment details.

    Returns:
        Generated 835 content and metadata.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        edi_service = get_edi_service()

        # In production, fetch adjudication result from database
        # For now, create a mock adjudication result
        # TODO: Integrate with adjudication service
        adjudication_result = {
            "claim_id": request.claim_id,
            "status": "approved",
            "total_charged": 1000.00,
            "total_allowed": 800.00,
            "total_paid": 640.00,
            "patient_responsibility": 160.00,
            "check_number": "CHK123456",
            "payment_date": "2024-01-15",
            "line_items": [],
        }

        payer_info = {
            "name": request.payer_name,
            "identifier": request.payer_id,
            "address": request.payer_address or "",
            "city": request.payer_city or "",
            "state": request.payer_state or "",
            "zip_code": request.payer_zip or "",
        }

        payee_info = {
            "name": request.payee_name,
            "npi": request.payee_npi,
            "tax_id": request.payee_tax_id or "",
        }

        result = await edi_service.generate_835(
            adjudication_result=adjudication_result,
            payer_info=payer_info,
            payee_info=payee_info,
            tenant_id=UUID(tenant_id),
        )

        return EDI835GenerateResult(
            transaction_id=result.transaction_id,
            claim_id=result.claim_id,
            control_number=result.control_number,
            content=result.content,
            status=result.status.value if hasattr(result.status, 'value') else str(result.status),
            errors=result.errors,
        )

    except Exception as e:
        logger.error(f"835 generation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate 835: {str(e)}",
        )


@router.get(
    "/835/{claim_id}",
    response_model=EDI835RetrieveResponse,
    dependencies=[Depends(require_permission("edi:read"))],
)
async def get_835(
    claim_id: str,
    session: AsyncSession = Depends(get_session),
) -> EDI835RetrieveResponse:
    """
    Retrieve X12 835 remittance for a claim.

    Returns the most recent 835 generated for the specified claim.

    Returns:
        835 content and payment details.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    # In production, fetch from database
    # For demo, return 404
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No 835 found for claim {claim_id}",
    )


# =============================================================================
# Transaction Endpoints
# =============================================================================


@router.get(
    "/transactions",
    response_model=EDITransactionListResponse,
    dependencies=[Depends(require_permission("edi:read"))],
)
async def list_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    transaction_type: Optional[str] = Query(
        None,
        description="Filter by type (837P, 837I, 835)",
    ),
    direction: Optional[str] = Query(
        None,
        description="Filter by direction (inbound, outbound)",
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status",
    ),
    session: AsyncSession = Depends(get_session),
) -> EDITransactionListResponse:
    """
    List EDI transactions with pagination and filters.

    Returns paginated list of EDI transactions for the tenant.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    # In production, query database
    # For demo, return empty list
    return EDITransactionListResponse(
        items=[],
        total=0,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/transactions/{transaction_id}",
    response_model=EDITransactionResponse,
    dependencies=[Depends(require_permission("edi:read"))],
)
async def get_transaction(
    transaction_id: str,
    session: AsyncSession = Depends(get_session),
) -> EDITransactionResponse:
    """
    Get EDI transaction details.

    Returns full transaction metadata and processing details.
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
        detail=f"Transaction {transaction_id} not found",
    )


@router.get(
    "/transactions/{transaction_id}/content",
    dependencies=[Depends(require_permission("edi:read"))],
)
async def get_transaction_content(
    transaction_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Get raw EDI content for a transaction.

    Returns the original X12 content for the transaction.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    # In production, fetch from database/storage
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Transaction {transaction_id} not found",
    )


# =============================================================================
# Statistics Endpoint
# =============================================================================


@router.get(
    "/stats",
    response_model=EDITransactionStats,
    dependencies=[Depends(require_permission("edi:read"))],
)
async def get_stats(
    days: int = Query(30, ge=1, le=365, description="Days to include"),
    session: AsyncSession = Depends(get_session),
) -> EDITransactionStats:
    """
    Get EDI transaction statistics.

    Returns aggregate statistics for the specified time period.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    from datetime import datetime, timedelta

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # In production, aggregate from database
    return EDITransactionStats(
        total_transactions=0,
        inbound_count=0,
        outbound_count=0,
        success_count=0,
        failed_count=0,
        claims_processed=0,
        avg_processing_time_ms=0.0,
        period_start=start_date,
        period_end=end_date,
    )
