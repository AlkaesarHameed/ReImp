"""
Pydantic Schemas for Fraud, Waste, and Abuse (FWA) Detection.
Source: Design Document Section 4.2 - Fraud Detection
Verified: 2025-12-18
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FWARiskLevel(str, Enum):
    """FWA risk level classification."""

    LOW = "low"  # 0.0 - 0.3
    MEDIUM = "medium"  # 0.3 - 0.6
    HIGH = "high"  # 0.6 - 0.8
    CRITICAL = "critical"  # 0.8 - 1.0


class FWAFlagType(str, Enum):
    """Types of FWA flags."""

    DUPLICATE_CLAIM = "duplicate_claim"
    UPCODING = "upcoding"
    UNBUNDLING = "unbundling"
    PHANTOM_BILLING = "phantom_billing"
    EXCESSIVE_SERVICES = "excessive_services"
    IMPOSSIBLE_DAY = "impossible_day"
    PATTERN_ANOMALY = "pattern_anomaly"
    PROVIDER_ANOMALY = "provider_anomaly"
    MEMBER_ANOMALY = "member_anomaly"
    HIGH_COST_OUTLIER = "high_cost_outlier"
    FREQUENCY_ABUSE = "frequency_abuse"
    KICKBACK_INDICATOR = "kickback_indicator"


class FWARecommendation(str, Enum):
    """FWA processing recommendation."""

    APPROVE = "approve"
    REVIEW = "review"
    DENY = "deny"
    INVESTIGATE = "investigate"
    SUSPEND_PROVIDER = "suspend_provider"


# =============================================================================
# FWA Flag Schemas
# =============================================================================


class FWAFlag(BaseModel):
    """Individual FWA flag."""

    flag_type: FWAFlagType
    severity: FWARiskLevel
    description: str
    score_contribution: float = Field(ge=0.0, le=1.0)
    evidence: dict = Field(default_factory=dict)
    rule_id: Optional[str] = None


class DuplicateClaimFlag(BaseModel):
    """Duplicate claim detection result."""

    is_duplicate: bool = False
    is_possible_duplicate: bool = False
    original_claim_id: Optional[UUID] = None
    original_tracking_number: Optional[str] = None
    similarity_score: float = 0.0
    matching_fields: list[str] = Field(default_factory=list)
    days_apart: int = 0


class UpcodingFlag(BaseModel):
    """Upcoding detection result."""

    is_upcoding_detected: bool = False
    suspected_codes: list[str] = Field(default_factory=list)
    suggested_codes: list[str] = Field(default_factory=list)
    upcoding_score: float = 0.0
    evidence: list[str] = Field(default_factory=list)


class UnbundlingFlag(BaseModel):
    """Unbundling detection result."""

    is_unbundling_detected: bool = False
    unbundled_codes: list[tuple[str, str]] = Field(default_factory=list)
    bundled_code: Optional[str] = None
    unbundling_score: float = 0.0


class PatternAnomalyFlag(BaseModel):
    """Billing pattern anomaly detection result."""

    is_anomaly_detected: bool = False
    anomaly_type: Optional[str] = None
    baseline_value: Optional[float] = None
    observed_value: Optional[float] = None
    deviation_score: float = 0.0
    description: Optional[str] = None


# =============================================================================
# Provider Analysis Schemas
# =============================================================================


class ProviderHistory(BaseModel):
    """Provider claims history for FWA analysis."""

    provider_id: UUID
    total_claims: int = 0
    total_billed: Decimal = Decimal("0")
    avg_claim_amount: Decimal = Decimal("0")
    denial_rate: float = 0.0
    claim_dates: list[date] = Field(default_factory=list)


class ProviderProfile(BaseModel):
    """Provider billing profile for FWA analysis."""

    provider_id: UUID
    specialty: Optional[str] = None

    # Volume metrics
    total_claims: int = 0
    total_billed: Decimal = Decimal("0")
    avg_claim_amount: Decimal = Decimal("0")

    # Pattern metrics
    denial_rate: float = 0.0
    duplicate_rate: float = 0.0
    upcoding_rate: float = 0.0

    # Comparison metrics
    peer_avg_claim_amount: Decimal = Decimal("0")
    peer_denial_rate: float = 0.0

    # Risk indicators
    risk_score: float = 0.0
    flags: list[str] = Field(default_factory=list)

    # Time period
    analysis_period_start: Optional[date] = None
    analysis_period_end: Optional[date] = None


class ProviderBehaviorScore(BaseModel):
    """Provider behavior scoring result."""

    provider_id: UUID
    overall_score: float = Field(ge=0.0, le=1.0, default=0.0)
    risk_level: FWARiskLevel = FWARiskLevel.LOW

    # Component scores
    billing_pattern_score: float = 0.0
    denial_pattern_score: float = 0.0
    peer_comparison_score: float = 0.0
    temporal_pattern_score: float = 0.0

    # Flags
    flags: list[FWAFlag] = Field(default_factory=list)
    recommendation: FWARecommendation = FWARecommendation.APPROVE


# =============================================================================
# FWA Analysis Schemas
# =============================================================================


class FWAAnalysisContext(BaseModel):
    """Context for FWA analysis."""

    claim_id: UUID
    tenant_id: UUID

    # Claim details
    claim_type: str
    service_date: date
    submission_date: datetime
    total_charged: Decimal

    # Codes
    diagnosis_codes: list[str] = Field(default_factory=list)
    procedure_codes: list[str] = Field(default_factory=list)

    # Parties
    provider_id: UUID
    member_id: UUID

    # Historical context
    provider_history: Optional[ProviderProfile] = None
    member_claim_history: list[dict] = Field(default_factory=list)

    # Thresholds
    duplicate_threshold: float = 0.9
    upcoding_threshold: float = 0.7
    pattern_threshold: float = 0.6


class FWAResult(BaseModel):
    """Complete FWA analysis result."""

    claim_id: UUID
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Overall scoring
    risk_score: float = Field(ge=0.0, le=1.0, default=0.0)
    risk_level: FWARiskLevel = FWARiskLevel.LOW
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)

    # Recommendation
    recommendation: FWARecommendation = FWARecommendation.APPROVE

    # Detection results
    duplicate_check: Optional[DuplicateClaimFlag] = None
    upcoding_check: Optional[UpcodingFlag] = None
    unbundling_check: Optional[UnbundlingFlag] = None
    pattern_anomaly: Optional[PatternAnomalyFlag] = None

    # All flags
    flags: list[FWAFlag] = Field(default_factory=list)

    # Provider analysis
    provider_score: Optional[ProviderBehaviorScore] = None

    # Processing details
    rules_evaluated: int = 0
    processing_time_ms: int = 0
    model_version: str = "1.0.0"

    # Notes
    notes: list[str] = Field(default_factory=list)

    def add_flag(self, flag: FWAFlag) -> None:
        """Add a flag and update risk score."""
        self.flags.append(flag)
        self._recalculate_risk()

    def _recalculate_risk(self) -> None:
        """Recalculate risk score from flags."""
        if not self.flags:
            self.risk_score = 0.0
            self.risk_level = FWARiskLevel.LOW
            return

        # Weighted sum of flag contributions
        total_score = sum(f.score_contribution for f in self.flags)
        # Cap at 1.0
        self.risk_score = min(1.0, total_score)

        # Determine risk level
        if self.risk_score >= 0.8:
            self.risk_level = FWARiskLevel.CRITICAL
        elif self.risk_score >= 0.6:
            self.risk_level = FWARiskLevel.HIGH
        elif self.risk_score >= 0.3:
            self.risk_level = FWARiskLevel.MEDIUM
        else:
            self.risk_level = FWARiskLevel.LOW


# =============================================================================
# ML Model Schemas
# =============================================================================


class FWAModelInput(BaseModel):
    """Input features for FWA ML model."""

    # Claim features
    total_charged: float
    num_procedures: int
    num_diagnoses: int
    claim_type_code: int  # Encoded claim type

    # Provider features
    provider_denial_rate: float
    provider_avg_claim: float
    provider_claim_count: int
    provider_specialty_code: int  # Encoded specialty

    # Member features
    member_claim_count_30d: int
    member_total_charged_30d: float
    member_provider_count_30d: int

    # Pattern features
    is_weekend: int  # 0 or 1
    is_month_end: int  # 0 or 1
    days_since_last_claim: int
    same_provider_last_7d: int

    # Code features
    has_high_value_procedure: int  # 0 or 1
    procedure_complexity_score: float


class FWAModelOutput(BaseModel):
    """Output from FWA ML model."""

    fraud_probability: float = Field(ge=0.0, le=1.0)
    waste_probability: float = Field(ge=0.0, le=1.0)
    abuse_probability: float = Field(ge=0.0, le=1.0)
    combined_score: float = Field(ge=0.0, le=1.0)

    # Feature importance for explainability
    top_contributing_features: list[tuple[str, float]] = Field(default_factory=list)


# =============================================================================
# Alert Schemas
# =============================================================================


class FWAAlert(BaseModel):
    """FWA alert for investigation."""

    alert_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Subject
    claim_id: Optional[UUID] = None
    provider_id: Optional[UUID] = None
    member_id: Optional[UUID] = None

    # Alert details
    alert_type: FWAFlagType
    severity: FWARiskLevel
    title: str
    description: str

    # Evidence
    risk_score: float
    flags: list[FWAFlag] = Field(default_factory=list)
    evidence_summary: dict = Field(default_factory=dict)

    # Status
    status: str = "open"  # open, investigating, resolved, dismissed
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
