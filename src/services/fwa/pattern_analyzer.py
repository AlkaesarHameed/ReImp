"""
Billing Pattern Analysis Service.
Source: Design Document Section 4.2 - Fraud Detection
Verified: 2025-12-18

Analyzes billing patterns to detect anomalies and suspicious behavior.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from src.schemas.fwa import (
    FWAFlag,
    FWAFlagType,
    FWARiskLevel,
    PatternAnomalyFlag,
    ProviderBehaviorScore,
    ProviderProfile,
)


class PatternAnalyzer:
    """
    Analyzes billing patterns for FWA indicators.

    Detects:
    - Impossible day billing (too many services)
    - Excessive services patterns
    - Provider behavior anomalies
    - Temporal billing patterns
    - Geographic impossibilities
    """

    # Thresholds
    MAX_DAILY_PROCEDURES = 50  # Max procedures per provider per day
    MAX_DAILY_PATIENTS = 30  # Max patients per provider per day
    HIGH_VOLUME_THRESHOLD = 2.0  # Standard deviations above mean
    WEEKEND_BILLING_THRESHOLD = 0.3  # Max % of claims on weekends

    def __init__(self):
        """Initialize PatternAnalyzer."""
        pass

    async def analyze_provider_patterns(
        self,
        provider_id: UUID,
        provider_claims: list[dict],
        peer_benchmark: Optional[dict] = None,
    ) -> ProviderBehaviorScore:
        """
        Analyze provider billing patterns.

        Args:
            provider_id: Provider UUID
            provider_claims: List of provider's claims
            peer_benchmark: Benchmark data for peer comparison

        Returns:
            ProviderBehaviorScore with analysis results
        """
        result = ProviderBehaviorScore(provider_id=provider_id)
        flags = []

        if not provider_claims:
            return result

        # Build provider profile
        profile = self._build_provider_profile(provider_id, provider_claims)

        # Check billing volume patterns
        volume_score, volume_flags = self._check_billing_volume(
            provider_claims, peer_benchmark
        )
        result.billing_pattern_score = volume_score
        flags.extend(volume_flags)

        # Check denial patterns
        denial_score, denial_flags = self._check_denial_patterns(
            provider_claims, peer_benchmark
        )
        result.denial_pattern_score = denial_score
        flags.extend(denial_flags)

        # Check peer comparison
        peer_score, peer_flags = self._check_peer_comparison(profile, peer_benchmark)
        result.peer_comparison_score = peer_score
        flags.extend(peer_flags)

        # Check temporal patterns
        temporal_score, temporal_flags = self._check_temporal_patterns(provider_claims)
        result.temporal_pattern_score = temporal_score
        flags.extend(temporal_flags)

        # Calculate overall score
        result.flags = flags
        result.overall_score = (
            result.billing_pattern_score * 0.3
            + result.denial_pattern_score * 0.25
            + result.peer_comparison_score * 0.25
            + result.temporal_pattern_score * 0.2
        )

        # Determine risk level
        if result.overall_score >= 0.8:
            result.risk_level = FWARiskLevel.CRITICAL
        elif result.overall_score >= 0.6:
            result.risk_level = FWARiskLevel.HIGH
        elif result.overall_score >= 0.3:
            result.risk_level = FWARiskLevel.MEDIUM
        else:
            result.risk_level = FWARiskLevel.LOW

        return result

    async def detect_impossible_day(
        self,
        provider_id: UUID,
        service_date: date,
        daily_claims: list[dict],
    ) -> PatternAnomalyFlag:
        """
        Detect impossible day billing.

        Args:
            provider_id: Provider UUID
            service_date: Date to analyze
            daily_claims: Claims for the provider on that date

        Returns:
            PatternAnomalyFlag with detection results
        """
        result = PatternAnomalyFlag()

        total_procedures = sum(
            len(claim.get("procedure_codes", [])) for claim in daily_claims
        )
        unique_patients = len(set(claim.get("member_id") for claim in daily_claims))

        # Check procedure count
        if total_procedures > self.MAX_DAILY_PROCEDURES:
            result.is_anomaly_detected = True
            result.anomaly_type = "impossible_day_procedures"
            result.baseline_value = float(self.MAX_DAILY_PROCEDURES)
            result.observed_value = float(total_procedures)
            result.deviation_score = min(
                1.0, (total_procedures - self.MAX_DAILY_PROCEDURES) / self.MAX_DAILY_PROCEDURES
            )
            result.description = (
                f"Provider billed {total_procedures} procedures on {service_date}, "
                f"exceeding maximum of {self.MAX_DAILY_PROCEDURES}"
            )
            return result

        # Check patient count
        if unique_patients > self.MAX_DAILY_PATIENTS:
            result.is_anomaly_detected = True
            result.anomaly_type = "impossible_day_patients"
            result.baseline_value = float(self.MAX_DAILY_PATIENTS)
            result.observed_value = float(unique_patients)
            result.deviation_score = min(
                1.0, (unique_patients - self.MAX_DAILY_PATIENTS) / self.MAX_DAILY_PATIENTS
            )
            result.description = (
                f"Provider saw {unique_patients} patients on {service_date}, "
                f"exceeding maximum of {self.MAX_DAILY_PATIENTS}"
            )

        return result

    async def detect_excessive_services(
        self,
        claim_data: dict,
        member_history: list[dict],
        service_limits: Optional[dict] = None,
    ) -> PatternAnomalyFlag:
        """
        Detect excessive services for a member.

        Args:
            claim_data: Current claim data
            member_history: Member's claim history
            service_limits: Optional service frequency limits

        Returns:
            PatternAnomalyFlag with detection results
        """
        result = PatternAnomalyFlag()

        if service_limits is None:
            service_limits = {
                "office_visit_30d": 10,
                "er_visit_30d": 3,
                "imaging_30d": 5,
            }

        # Count services in last 30 days
        service_date = claim_data.get("service_date")
        if isinstance(service_date, str):
            service_date = date.fromisoformat(service_date)

        cutoff_date = service_date - timedelta(days=30)

        recent_claims = [
            c for c in member_history
            if self._get_claim_date(c) >= cutoff_date
        ]

        # Check for excessive office visits
        office_visits = sum(
            1 for c in recent_claims
            if any(
                code in c.get("procedure_codes", [])
                for code in ["99213", "99214", "99215", "99203", "99204", "99205"]
            )
        )

        if office_visits > service_limits.get("office_visit_30d", 10):
            result.is_anomaly_detected = True
            result.anomaly_type = "excessive_office_visits"
            result.baseline_value = float(service_limits["office_visit_30d"])
            result.observed_value = float(office_visits)
            result.deviation_score = min(
                1.0,
                (office_visits - service_limits["office_visit_30d"])
                / service_limits["office_visit_30d"],
            )
            result.description = (
                f"Member had {office_visits} office visits in 30 days, "
                f"exceeding limit of {service_limits['office_visit_30d']}"
            )

        return result

    def _build_provider_profile(
        self,
        provider_id: UUID,
        claims: list[dict],
    ) -> ProviderProfile:
        """Build provider profile from claims."""
        profile = ProviderProfile(provider_id=provider_id)

        if not claims:
            return profile

        profile.total_claims = len(claims)

        # Calculate totals
        total_billed = sum(
            Decimal(str(c.get("total_charged", 0))) for c in claims
        )
        profile.total_billed = total_billed

        if profile.total_claims > 0:
            profile.avg_claim_amount = total_billed / profile.total_claims

        # Calculate denial rate
        denied_claims = sum(1 for c in claims if c.get("status") == "denied")
        if profile.total_claims > 0:
            profile.denial_rate = denied_claims / profile.total_claims

        return profile

    def _check_billing_volume(
        self,
        claims: list[dict],
        peer_benchmark: Optional[dict],
    ) -> tuple[float, list[FWAFlag]]:
        """Check billing volume patterns."""
        flags = []
        score = 0.0

        if not claims:
            return score, flags

        # Calculate daily averages
        claims_by_date = {}
        for claim in claims:
            claim_date = self._get_claim_date(claim)
            if claim_date:
                date_str = str(claim_date)
                if date_str not in claims_by_date:
                    claims_by_date[date_str] = []
                claims_by_date[date_str].append(claim)

        # Check for high-volume days
        for date_str, daily_claims in claims_by_date.items():
            if len(daily_claims) > self.MAX_DAILY_PATIENTS:
                score += 0.3
                flags.append(
                    FWAFlag(
                        flag_type=FWAFlagType.EXCESSIVE_SERVICES,
                        severity=FWARiskLevel.MEDIUM,
                        description=f"High volume day: {len(daily_claims)} claims on {date_str}",
                        score_contribution=0.15,
                        rule_id="PAT001",
                    )
                )

        return min(1.0, score), flags

    def _check_denial_patterns(
        self,
        claims: list[dict],
        peer_benchmark: Optional[dict],
    ) -> tuple[float, list[FWAFlag]]:
        """Check denial rate patterns."""
        flags = []
        score = 0.0

        if not claims:
            return score, flags

        # Calculate denial rate
        denied = sum(1 for c in claims if c.get("status") == "denied")
        denial_rate = denied / len(claims) if claims else 0

        # Compare to peer benchmark
        peer_denial_rate = 0.1  # Default 10%
        if peer_benchmark:
            peer_denial_rate = peer_benchmark.get("denial_rate", 0.1)

        if denial_rate > peer_denial_rate * 2:  # More than 2x peer rate
            score = 0.5
            flags.append(
                FWAFlag(
                    flag_type=FWAFlagType.PROVIDER_ANOMALY,
                    severity=FWARiskLevel.MEDIUM,
                    description=f"High denial rate: {denial_rate:.1%} vs peer {peer_denial_rate:.1%}",
                    score_contribution=0.2,
                    evidence={
                        "provider_denial_rate": denial_rate,
                        "peer_denial_rate": peer_denial_rate,
                    },
                    rule_id="PAT002",
                )
            )

        return score, flags

    def _check_peer_comparison(
        self,
        profile: ProviderProfile,
        peer_benchmark: Optional[dict],
    ) -> tuple[float, list[FWAFlag]]:
        """Compare provider to peers."""
        flags = []
        score = 0.0

        if not peer_benchmark:
            return score, flags

        # Compare average claim amount
        peer_avg = Decimal(str(peer_benchmark.get("avg_claim_amount", 0)))
        if peer_avg > 0 and profile.avg_claim_amount > peer_avg * Decimal("2.0"):
            score = 0.4
            flags.append(
                FWAFlag(
                    flag_type=FWAFlagType.PROVIDER_ANOMALY,
                    severity=FWARiskLevel.MEDIUM,
                    description=(
                        f"Average claim ${profile.avg_claim_amount:.2f} "
                        f"is 2x+ peer average ${peer_avg:.2f}"
                    ),
                    score_contribution=0.15,
                    rule_id="PAT003",
                )
            )

        return score, flags

    def _check_temporal_patterns(
        self,
        claims: list[dict],
    ) -> tuple[float, list[FWAFlag]]:
        """Check temporal billing patterns."""
        flags = []
        score = 0.0

        if not claims:
            return score, flags

        # Check weekend billing ratio
        weekend_claims = sum(
            1 for c in claims
            if self._is_weekend(self._get_claim_date(c))
        )
        weekend_ratio = weekend_claims / len(claims) if claims else 0

        if weekend_ratio > self.WEEKEND_BILLING_THRESHOLD:
            score = 0.3
            flags.append(
                FWAFlag(
                    flag_type=FWAFlagType.PATTERN_ANOMALY,
                    severity=FWARiskLevel.LOW,
                    description=f"High weekend billing: {weekend_ratio:.1%} of claims",
                    score_contribution=0.1,
                    rule_id="PAT004",
                )
            )

        return score, flags

    def _get_claim_date(self, claim: dict) -> Optional[date]:
        """Extract date from claim."""
        claim_date = claim.get("service_date")
        if claim_date is None:
            return None
        if isinstance(claim_date, str):
            return date.fromisoformat(claim_date)
        return claim_date

    def _is_weekend(self, d: Optional[date]) -> bool:
        """Check if date is a weekend."""
        if d is None:
            return False
        return d.weekday() >= 5


# =============================================================================
# Factory Functions
# =============================================================================


_pattern_analyzer: Optional[PatternAnalyzer] = None


def get_pattern_analyzer() -> PatternAnalyzer:
    """Get singleton PatternAnalyzer instance."""
    global _pattern_analyzer
    if _pattern_analyzer is None:
        _pattern_analyzer = PatternAnalyzer()
    return _pattern_analyzer
