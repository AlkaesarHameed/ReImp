"""
Fraud, Waste, and Abuse (FWA) Detection API Endpoints.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Provides:
- ML-based FWA risk scoring
- Anomaly detection
- Claim analysis
- Batch FWA screening
"""

import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any
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
from src.schemas.fwa import (
    FWAAnalysisContext,
    FWAResult,
    FWARiskLevel,
    FWARecommendation,
    ProviderHistory,
)
from src.services.fwa import (
    FWAService,
    get_fwa_service,
)
from src.services.fwa.ml_models import (
    MLAnomalyEnsemble,
    ClaimFeatures,
    AnomalyScore,
    AnomalyType,
    get_ml_ensemble,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/fwa",
    tags=["fwa"],
)


# =============================================================================
# Request/Response Schemas
# =============================================================================


class ClaimDataRequest(BaseModel):
    """Basic claim data for FWA analysis."""

    claim_id: str = Field(..., description="Claim identifier")
    member_id: str = Field(..., description="Member identifier")
    provider_id: str = Field(..., description="Provider identifier")
    service_date: date = Field(..., description="Date of service")
    total_charged: float = Field(..., ge=0, description="Total amount charged")
    procedure_codes: List[str] = Field(default_factory=list, description="CPT/HCPCS codes")
    diagnosis_codes: List[str] = Field(default_factory=list, description="ICD-10 codes")
    claim_type: Optional[str] = Field(None, description="Claim type (professional, institutional)")


class ProviderProfileRequest(BaseModel):
    """Provider profile for risk assessment."""

    provider_id: str = Field(..., description="Provider NPI")
    total_claims: int = Field(0, ge=0, description="Total claims submitted")
    avg_claim_amount: float = Field(0, ge=0, description="Average claim amount")
    denial_rate: float = Field(0, ge=0, le=1, description="Claim denial rate")
    specialty_risk: float = Field(0, ge=0, le=1, description="Specialty risk score")
    flags: List[str] = Field(default_factory=list, description="Existing flags")


class FWAAnalysisRequest(BaseModel):
    """Full FWA analysis request."""

    claim: ClaimDataRequest
    provider_profile: Optional[ProviderProfileRequest] = None
    member_claim_history: Optional[List[ClaimDataRequest]] = None
    existing_claims: Optional[List[ClaimDataRequest]] = None
    auto_approve_threshold: float = Field(5000.0, description="Auto-approve threshold")
    duplicate_threshold: float = Field(0.8, description="Duplicate detection threshold")


class FWAFlagResponse(BaseModel):
    """FWA flag in response."""

    flag_type: str
    severity: str
    description: str
    score_contribution: float
    rule_id: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None


class FWAAnalysisResponse(BaseModel):
    """Response for FWA analysis."""

    claim_id: str
    risk_score: float
    risk_level: str
    recommendation: str
    flags: List[FWAFlagResponse] = Field(default_factory=list)
    is_duplicate: bool = False
    is_upcoding: bool = False
    is_unbundling: bool = False
    rules_evaluated: int = 0
    processing_time_ms: int = 0
    model_version: str = "1.0.0"
    notes: List[str] = Field(default_factory=list)


class MLAnomalyRequest(BaseModel):
    """Request for ML anomaly detection."""

    claim: ClaimDataRequest
    provider_profile: Optional[ProviderProfileRequest] = None
    member_claim_history: Optional[List[ClaimDataRequest]] = None


class AnomalyScoreResponse(BaseModel):
    """ML anomaly detection response."""

    claim_id: str
    is_anomaly: bool
    anomaly_score: float
    anomaly_type: Optional[str] = None
    confidence: float
    contributing_factors: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None


class MLAnalysisResponse(BaseModel):
    """Response for ML-based analysis."""

    claim_id: str
    ensemble_score: AnomalyScoreResponse
    model_scores: List[AnomalyScoreResponse]
    features_used: Dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: int = 0


class BatchFWARequest(BaseModel):
    """Request for batch FWA screening."""

    claims: List[ClaimDataRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Claims to screen (max 100)",
    )
    provider_profiles: Optional[Dict[str, ProviderProfileRequest]] = None
    threshold: float = Field(0.5, description="Risk threshold for flagging")


class BatchFWAResponse(BaseModel):
    """Response for batch FWA screening."""

    total: int
    flagged_count: int
    high_risk_count: int
    low_risk_count: int
    results: List[FWAAnalysisResponse]


class QuickScreenRequest(BaseModel):
    """Quick FWA screening request."""

    claim_id: str
    member_id: str
    provider_id: str
    total_charged: float
    procedure_codes: List[str] = Field(default_factory=list)


class QuickScreenResponse(BaseModel):
    """Quick FWA screening response."""

    claim_id: str
    risk_score: float
    risk_level: str
    recommendation: str
    flag_count: int


# =============================================================================
# Helper Functions
# =============================================================================


def convert_claim_to_context(request: FWAAnalysisRequest) -> FWAAnalysisContext:
    """Convert API request to FWAAnalysisContext."""
    provider_history = None
    if request.provider_profile:
        provider_history = ProviderHistory(
            total_claims=request.provider_profile.total_claims,
            denial_rate=request.provider_profile.denial_rate,
            avg_claim_amount=request.provider_profile.avg_claim_amount,
            flags=request.provider_profile.flags,
        )

    member_history = None
    if request.member_claim_history:
        member_history = [
            {
                "claim_id": c.claim_id,
                "service_date": c.service_date,
                "total_charged": c.total_charged,
                "procedure_codes": c.procedure_codes,
                "diagnosis_codes": c.diagnosis_codes,
                "provider_id": c.provider_id,
            }
            for c in request.member_claim_history
        ]

    return FWAAnalysisContext(
        claim_id=request.claim.claim_id,
        member_id=request.claim.member_id,
        provider_id=request.claim.provider_id,
        service_date=request.claim.service_date,
        total_charged=request.claim.total_charged,
        procedure_codes=request.claim.procedure_codes,
        diagnosis_codes=request.claim.diagnosis_codes,
        claim_type=request.claim.claim_type or "professional",
        provider_history=provider_history,
        member_claim_history=member_history,
        auto_approve_threshold=request.auto_approve_threshold,
        duplicate_threshold=request.duplicate_threshold,
    )


def convert_result_to_response(result: FWAResult) -> FWAAnalysisResponse:
    """Convert FWAResult to API response."""
    flags = []
    for flag in result.flags:
        flags.append(FWAFlagResponse(
            flag_type=flag.flag_type.value,
            severity=flag.severity.value,
            description=flag.description,
            score_contribution=flag.score_contribution,
            rule_id=flag.rule_id,
            evidence=flag.evidence,
        ))

    return FWAAnalysisResponse(
        claim_id=result.claim_id,
        risk_score=result.risk_score,
        risk_level=result.risk_level.value,
        recommendation=result.recommendation.value,
        flags=flags,
        is_duplicate=result.duplicate_check.is_duplicate if result.duplicate_check else False,
        is_upcoding=result.upcoding_check.is_upcoding if result.upcoding_check else False,
        is_unbundling=result.unbundling_check.is_unbundling if result.unbundling_check else False,
        rules_evaluated=result.rules_evaluated,
        processing_time_ms=result.processing_time_ms,
        model_version=result.model_version,
        notes=result.notes,
    )


def convert_anomaly_score(score: AnomalyScore) -> AnomalyScoreResponse:
    """Convert AnomalyScore to API response."""
    return AnomalyScoreResponse(
        claim_id=score.claim_id,
        is_anomaly=score.is_anomaly,
        anomaly_score=score.anomaly_score,
        anomaly_type=score.anomaly_type.value if score.anomaly_type else None,
        confidence=score.confidence,
        contributing_factors=score.contributing_factors,
        explanation=score.explanation,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/analyze",
    response_model=FWAAnalysisResponse,
    dependencies=[Depends(require_permission("fwa:analyze"))],
)
async def analyze_claim(
    request: FWAAnalysisRequest,
    session: AsyncSession = Depends(get_session),
) -> FWAAnalysisResponse:
    """
    Comprehensive FWA analysis for a claim.

    Performs:
    - Duplicate detection
    - Upcoding/unbundling detection
    - Pattern analysis
    - ML-based risk scoring

    Returns:
        Complete FWA analysis with risk score and flags.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        service = get_fwa_service()
        context = convert_claim_to_context(request)

        # Convert existing claims if provided
        existing_claims = None
        if request.existing_claims:
            existing_claims = [
                {
                    "claim_id": c.claim_id,
                    "member_id": c.member_id,
                    "provider_id": c.provider_id,
                    "service_date": c.service_date,
                    "total_charged": c.total_charged,
                    "procedure_codes": c.procedure_codes,
                    "diagnosis_codes": c.diagnosis_codes,
                }
                for c in request.existing_claims
            ]

        result = await service.analyze_claim(
            context=context,
            existing_claims=existing_claims,
        )

        return convert_result_to_response(result)

    except Exception as e:
        logger.error(f"FWA analysis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"FWA analysis failed: {str(e)}",
        )


@router.post(
    "/ml/detect",
    response_model=MLAnalysisResponse,
    dependencies=[Depends(require_permission("fwa:analyze"))],
)
async def ml_anomaly_detection(
    request: MLAnomalyRequest,
    session: AsyncSession = Depends(get_session),
) -> MLAnalysisResponse:
    """
    ML-based anomaly detection for a claim.

    Uses ensemble of:
    - Isolation Forest model
    - Statistical anomaly detection

    Returns:
        ML anomaly scores and contributing factors.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        import time
        start_time = time.time()

        ensemble = get_ml_ensemble()

        # Prepare data
        claim_data = {
            "claim_id": request.claim.claim_id,
            "member_id": request.claim.member_id,
            "provider_id": request.claim.provider_id,
            "service_date": request.claim.service_date,
            "total_charged": request.claim.total_charged,
            "procedure_codes": request.claim.procedure_codes,
            "diagnosis_codes": request.claim.diagnosis_codes,
        }

        provider_profile = None
        if request.provider_profile:
            provider_profile = {
                "total_claims": request.provider_profile.total_claims,
                "avg_claim_amount": request.provider_profile.avg_claim_amount,
                "denial_rate": request.provider_profile.denial_rate,
                "specialty_risk": request.provider_profile.specialty_risk,
            }

        member_history = None
        if request.member_claim_history:
            member_history = [
                {
                    "claim_id": c.claim_id,
                    "service_date": c.service_date,
                    "total_charged": c.total_charged,
                    "procedure_codes": c.procedure_codes,
                    "provider_id": c.provider_id,
                }
                for c in request.member_claim_history
            ]

        # Get predictions
        combined_score, individual_scores = ensemble.predict(
            claim_data, provider_profile, member_history
        )

        # Extract features for response
        features = ensemble.feature_engineer.extract_features(
            claim_data, provider_profile, member_history
        )

        processing_time = int((time.time() - start_time) * 1000)

        return MLAnalysisResponse(
            claim_id=request.claim.claim_id,
            ensemble_score=convert_anomaly_score(combined_score),
            model_scores=[convert_anomaly_score(s) for s in individual_scores],
            features_used={
                "total_charged": features.total_charged,
                "num_procedures": features.num_procedures,
                "num_diagnoses": features.num_diagnoses,
                "is_weekend": features.is_weekend,
                "provider_denial_rate": features.provider_denial_rate,
                "member_claim_count_30d": features.member_claim_count_30d,
                "has_high_value_procedure": features.has_high_value_procedure,
                "procedure_complexity": features.procedure_complexity,
            },
            processing_time_ms=processing_time,
        )

    except Exception as e:
        logger.error(f"ML anomaly detection error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML detection failed: {str(e)}",
        )


@router.post(
    "/screen",
    response_model=QuickScreenResponse,
    dependencies=[Depends(require_permission("fwa:screen"))],
)
async def quick_screen(
    request: QuickScreenRequest,
    session: AsyncSession = Depends(get_session),
) -> QuickScreenResponse:
    """
    Quick FWA screening for high-volume scenarios.

    Lightweight check for basic fraud indicators.

    Returns:
        Quick risk assessment.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        service = get_fwa_service()

        claim_data = {
            "claim_id": request.claim_id,
            "member_id": request.member_id,
            "provider_id": request.provider_id,
            "total_charged": request.total_charged,
            "procedure_codes": request.procedure_codes,
            "diagnosis_codes": [],
        }

        risk_score, risk_level, recommendation = await service.quick_check(claim_data)

        # Estimate flag count from score
        flag_count = 0
        if risk_score >= 0.3:
            flag_count = int(risk_score * 5)

        return QuickScreenResponse(
            claim_id=request.claim_id,
            risk_score=risk_score,
            risk_level=risk_level.value,
            recommendation=recommendation.value,
            flag_count=flag_count,
        )

    except Exception as e:
        logger.error(f"Quick screen error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quick screen failed: {str(e)}",
        )


@router.post(
    "/batch",
    response_model=BatchFWAResponse,
    dependencies=[Depends(require_permission("fwa:analyze"))],
)
async def batch_screen(
    request: BatchFWARequest,
    session: AsyncSession = Depends(get_session),
) -> BatchFWAResponse:
    """
    Batch FWA screening for multiple claims.

    Processes up to 100 claims with quick screening.

    Returns:
        Batch results with risk counts.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    try:
        service = get_fwa_service()
        results = []

        for claim in request.claims:
            claim_data = {
                "claim_id": claim.claim_id,
                "member_id": claim.member_id,
                "provider_id": claim.provider_id,
                "total_charged": claim.total_charged,
                "procedure_codes": claim.procedure_codes,
                "diagnosis_codes": claim.diagnosis_codes,
                "service_date": claim.service_date,
            }

            risk_score, risk_level, recommendation = await service.quick_check(claim_data)

            results.append(FWAAnalysisResponse(
                claim_id=claim.claim_id,
                risk_score=risk_score,
                risk_level=risk_level.value,
                recommendation=recommendation.value,
                flags=[],
                rules_evaluated=3,
                processing_time_ms=0,
            ))

        # Calculate summary
        flagged = sum(1 for r in results if r.risk_score >= request.threshold)
        high_risk = sum(1 for r in results if r.risk_level in ["critical", "high"])
        low_risk = sum(1 for r in results if r.risk_level == "low")

        return BatchFWAResponse(
            total=len(results),
            flagged_count=flagged,
            high_risk_count=high_risk,
            low_risk_count=low_risk,
            results=results,
        )

    except Exception as e:
        logger.error(f"Batch screen error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch screen failed: {str(e)}",
        )


@router.get(
    "/model/info",
    dependencies=[Depends(require_permission("fwa:read"))],
)
async def get_model_info() -> Dict[str, Any]:
    """
    Get ML model information.

    Returns:
        Model version and capabilities.
    """
    ensemble = get_ml_ensemble()

    return {
        "model_version": "1.0.0",
        "is_fitted": ensemble.is_fitted,
        "models": [
            {
                "name": "IsolationForest",
                "type": "anomaly_detection",
                "n_estimators": ensemble.isolation_forest.n_estimators,
                "is_fitted": ensemble.isolation_forest.is_fitted,
            },
            {
                "name": "StatisticalAnomalyModel",
                "type": "statistical",
                "z_threshold": ensemble.statistical_model.z_threshold,
                "is_fitted": ensemble.statistical_model.is_fitted,
            },
        ],
        "feature_count": 18,
        "supported_anomaly_types": [t.value for t in AnomalyType],
    }


@router.get(
    "/statistics",
    dependencies=[Depends(require_permission("fwa:read"))],
)
async def get_fwa_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Get FWA detection statistics.

    Returns:
        Detection statistics and trends.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    # In production, query from database
    # For demo, return sample statistics
    return {
        "period_days": days,
        "total_claims_analyzed": 0,
        "flagged_count": 0,
        "flagged_percentage": 0.0,
        "by_risk_level": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        },
        "by_flag_type": {
            "duplicate_claim": 0,
            "upcoding": 0,
            "unbundling": 0,
            "pattern_anomaly": 0,
        },
        "average_risk_score": 0.0,
        "model_version": "1.0.0",
    }
