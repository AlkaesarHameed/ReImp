"""
FWA Risk Scoring Service.
Source: Design Document Section 4.2 - Fraud Detection
Verified: 2025-12-18

Provides ML-based risk scoring for fraud, waste, and abuse detection.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from src.schemas.fwa import (
    FWAFlag,
    FWAFlagType,
    FWAModelInput,
    FWAModelOutput,
    FWARecommendation,
    FWARiskLevel,
)


class FWARiskScorer:
    """
    ML-based risk scoring for FWA detection.

    Uses a combination of rule-based scoring and ML model predictions
    to generate comprehensive risk scores.
    """

    # Risk thresholds
    LOW_RISK_THRESHOLD = 0.3
    MEDIUM_RISK_THRESHOLD = 0.6
    HIGH_RISK_THRESHOLD = 0.8

    # Feature weights for rule-based scoring
    FEATURE_WEIGHTS = {
        "claim_amount": 0.15,
        "provider_history": 0.20,
        "member_history": 0.15,
        "pattern_score": 0.20,
        "duplicate_score": 0.15,
        "upcoding_score": 0.15,
    }

    # High-value procedure codes
    HIGH_VALUE_PROCEDURES = {
        "27447", "27130", "63030", "47562", "19301",
        "33533", "35301", "43239", "44140",
    }

    def __init__(self, model_version: str = "1.0.0"):
        """
        Initialize FWARiskScorer.

        Args:
            model_version: Version of the scoring model
        """
        self.model_version = model_version
        # In production, load actual ML model here
        # self.model = joblib.load("ml/models/fwa_xgboost_v1.joblib")

    async def calculate_risk_score(
        self,
        claim_data: dict,
        flags: list[FWAFlag],
        provider_profile: Optional[dict] = None,
        member_history: Optional[list[dict]] = None,
    ) -> tuple[float, FWARiskLevel, FWARecommendation]:
        """
        Calculate comprehensive risk score.

        Args:
            claim_data: Current claim data
            flags: FWA flags detected
            provider_profile: Provider history and metrics
            member_history: Member's claim history

        Returns:
            Tuple of (risk_score, risk_level, recommendation)
        """
        # Start with flag-based score
        flag_score = self._calculate_flag_score(flags)

        # Add rule-based components
        claim_score = self._score_claim_characteristics(claim_data)
        provider_score = self._score_provider(provider_profile) if provider_profile else 0.0
        member_score = self._score_member(member_history) if member_history else 0.0

        # Weighted combination
        combined_score = (
            flag_score * 0.40
            + claim_score * 0.25
            + provider_score * 0.20
            + member_score * 0.15
        )

        # Apply ML model adjustment (simulated)
        ml_adjustment = await self._get_ml_adjustment(claim_data, provider_profile)
        final_score = min(1.0, combined_score * (1 + ml_adjustment))

        # Determine risk level
        risk_level = self._get_risk_level(final_score)

        # Determine recommendation
        recommendation = self._get_recommendation(final_score, flags)

        return final_score, risk_level, recommendation

    async def prepare_model_input(
        self,
        claim_data: dict,
        provider_profile: Optional[dict] = None,
        member_history: Optional[list[dict]] = None,
    ) -> FWAModelInput:
        """
        Prepare input features for ML model.

        Args:
            claim_data: Current claim data
            provider_profile: Provider metrics
            member_history: Member claim history

        Returns:
            FWAModelInput with engineered features
        """
        # Claim features
        total_charged = float(claim_data.get("total_charged", 0))
        procedure_codes = claim_data.get("procedure_codes", [])
        diagnosis_codes = claim_data.get("diagnosis_codes", [])

        # Provider features
        provider_denial_rate = 0.0
        provider_avg_claim = 0.0
        provider_claim_count = 0
        if provider_profile:
            provider_denial_rate = provider_profile.get("denial_rate", 0.0)
            provider_avg_claim = float(provider_profile.get("avg_claim_amount", 0))
            provider_claim_count = provider_profile.get("total_claims", 0)

        # Member features (last 30 days)
        member_claim_count_30d = len(member_history) if member_history else 0
        member_total_charged_30d = sum(
            float(c.get("total_charged", 0)) for c in (member_history or [])
        )
        member_provider_count_30d = len(
            set(c.get("provider_id") for c in (member_history or []))
        )

        # Pattern features
        service_date = claim_data.get("service_date")
        if isinstance(service_date, str):
            service_date = date.fromisoformat(service_date)
        is_weekend = 1 if service_date and service_date.weekday() >= 5 else 0
        is_month_end = 1 if service_date and service_date.day >= 28 else 0

        # Code features
        has_high_value = 1 if any(
            code in self.HIGH_VALUE_PROCEDURES for code in procedure_codes
        ) else 0

        # Complexity score based on number of procedures and diagnoses
        complexity = min(1.0, (len(procedure_codes) + len(diagnosis_codes)) / 10)

        return FWAModelInput(
            total_charged=total_charged,
            num_procedures=len(procedure_codes),
            num_diagnoses=len(diagnosis_codes),
            claim_type_code=0,  # Would be encoded in production
            provider_denial_rate=provider_denial_rate,
            provider_avg_claim=provider_avg_claim,
            provider_claim_count=provider_claim_count,
            provider_specialty_code=0,  # Would be encoded in production
            member_claim_count_30d=member_claim_count_30d,
            member_total_charged_30d=member_total_charged_30d,
            member_provider_count_30d=member_provider_count_30d,
            is_weekend=is_weekend,
            is_month_end=is_month_end,
            days_since_last_claim=0,  # Would calculate in production
            same_provider_last_7d=0,  # Would calculate in production
            has_high_value_procedure=has_high_value,
            procedure_complexity_score=complexity,
        )

    async def predict(self, model_input: FWAModelInput) -> FWAModelOutput:
        """
        Run ML model prediction.

        Args:
            model_input: Prepared model input features

        Returns:
            FWAModelOutput with predictions
        """
        # Simulated ML prediction
        # In production, use actual model:
        # features = model_input.model_dump()
        # prediction = self.model.predict_proba([list(features.values())])[0]

        # Rule-based simulation of ML output
        fraud_prob = 0.0
        waste_prob = 0.0
        abuse_prob = 0.0

        # High claim amount increases fraud probability
        if model_input.total_charged > 10000:
            fraud_prob += 0.1

        # High provider denial rate increases waste probability
        if model_input.provider_denial_rate > 0.2:
            waste_prob += 0.15

        # Many claims from member increases abuse probability
        if model_input.member_claim_count_30d > 10:
            abuse_prob += 0.1

        # Weekend billing increases fraud probability
        if model_input.is_weekend:
            fraud_prob += 0.05

        # High-value procedures increase scrutiny
        if model_input.has_high_value_procedure:
            fraud_prob += 0.08

        # Cap probabilities
        fraud_prob = min(0.9, fraud_prob)
        waste_prob = min(0.9, waste_prob)
        abuse_prob = min(0.9, abuse_prob)

        combined = (fraud_prob + waste_prob + abuse_prob) / 3

        # Feature importance (simulated)
        top_features = [
            ("total_charged", fraud_prob * 0.3),
            ("provider_denial_rate", waste_prob * 0.4),
            ("member_claim_count_30d", abuse_prob * 0.3),
        ]

        return FWAModelOutput(
            fraud_probability=fraud_prob,
            waste_probability=waste_prob,
            abuse_probability=abuse_prob,
            combined_score=combined,
            top_contributing_features=sorted(top_features, key=lambda x: -x[1]),
        )

    def _calculate_flag_score(self, flags: list[FWAFlag]) -> float:
        """Calculate score from flags."""
        if not flags:
            return 0.0

        total = sum(f.score_contribution for f in flags)
        return min(1.0, total)

    def _score_claim_characteristics(self, claim_data: dict) -> float:
        """Score claim based on characteristics."""
        score = 0.0

        # High amount
        total_charged = Decimal(str(claim_data.get("total_charged", 0)))
        if total_charged > Decimal("10000"):
            score += 0.2
        elif total_charged > Decimal("5000"):
            score += 0.1

        # Many procedures
        procedures = claim_data.get("procedure_codes", [])
        if len(procedures) > 10:
            score += 0.2
        elif len(procedures) > 5:
            score += 0.1

        # High-value procedures
        if any(code in self.HIGH_VALUE_PROCEDURES for code in procedures):
            score += 0.15

        return min(1.0, score)

    def _score_provider(self, provider_profile: dict) -> float:
        """Score based on provider history."""
        score = 0.0

        # High denial rate
        denial_rate = provider_profile.get("denial_rate", 0)
        if denial_rate > 0.3:
            score += 0.3
        elif denial_rate > 0.2:
            score += 0.2

        # Existing risk flags
        flags = provider_profile.get("flags", [])
        if flags:
            score += min(0.3, len(flags) * 0.1)

        return min(1.0, score)

    def _score_member(self, member_history: list[dict]) -> float:
        """Score based on member history."""
        score = 0.0

        if not member_history:
            return score

        # Many recent claims
        if len(member_history) > 20:
            score += 0.3
        elif len(member_history) > 10:
            score += 0.15

        # Many providers
        providers = set(c.get("provider_id") for c in member_history)
        if len(providers) > 10:
            score += 0.2

        return min(1.0, score)

    async def _get_ml_adjustment(
        self,
        claim_data: dict,
        provider_profile: Optional[dict],
    ) -> float:
        """Get ML model adjustment factor."""
        # In production, run actual ML model
        # For now, return small adjustment based on simple rules
        adjustment = 0.0

        # Adjust based on claim complexity
        procedures = claim_data.get("procedure_codes", [])
        diagnoses = claim_data.get("diagnosis_codes", [])

        if len(procedures) > 5 and len(diagnoses) > 3:
            adjustment += 0.1

        return adjustment

    def _get_risk_level(self, score: float) -> FWARiskLevel:
        """Determine risk level from score."""
        if score >= self.HIGH_RISK_THRESHOLD:
            return FWARiskLevel.CRITICAL
        elif score >= self.MEDIUM_RISK_THRESHOLD:
            return FWARiskLevel.HIGH
        elif score >= self.LOW_RISK_THRESHOLD:
            return FWARiskLevel.MEDIUM
        else:
            return FWARiskLevel.LOW

    def _get_recommendation(
        self,
        score: float,
        flags: list[FWAFlag],
    ) -> FWARecommendation:
        """Determine recommendation based on score and flags."""
        # Check for critical flags
        has_critical = any(f.severity == FWARiskLevel.CRITICAL for f in flags)
        has_duplicate = any(f.flag_type == FWAFlagType.DUPLICATE_CLAIM for f in flags)

        if has_critical or score >= 0.9:
            return FWARecommendation.DENY
        elif score >= 0.7 or has_duplicate:
            return FWARecommendation.INVESTIGATE
        elif score >= 0.5:
            return FWARecommendation.REVIEW
        else:
            return FWARecommendation.APPROVE


# =============================================================================
# Factory Functions
# =============================================================================


_risk_scorer: Optional[FWARiskScorer] = None


def get_risk_scorer(model_version: str = "1.0.0") -> FWARiskScorer:
    """Get singleton FWARiskScorer instance."""
    global _risk_scorer
    if _risk_scorer is None:
        _risk_scorer = FWARiskScorer(model_version)
    return _risk_scorer
