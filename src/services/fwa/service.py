"""
FWA Detection Orchestrator Service.
Source: Design Document Section 4.2 - Fraud Detection
Verified: 2025-12-18

Orchestrates comprehensive FWA detection across all detection services.
"""

import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.schemas.fwa import (
    FWAAnalysisContext,
    FWAFlag,
    FWAFlagType,
    FWARecommendation,
    FWAResult,
    FWARiskLevel,
)
from src.services.fwa.duplicate_detector import DuplicateDetector, get_duplicate_detector
from src.services.fwa.pattern_analyzer import PatternAnalyzer, get_pattern_analyzer
from src.services.fwa.upcoding_detector import UpcodingDetector, get_upcoding_detector
from src.services.fwa.risk_scorer import FWARiskScorer, get_risk_scorer


class FWAService:
    """
    Orchestrates comprehensive FWA detection.

    Coordinates:
    1. Duplicate claim detection
    2. Upcoding detection
    3. Unbundling detection
    4. Pattern analysis
    5. Provider behavior scoring
    6. ML-based risk scoring
    """

    def __init__(
        self,
        duplicate_detector: Optional[DuplicateDetector] = None,
        pattern_analyzer: Optional[PatternAnalyzer] = None,
        upcoding_detector: Optional[UpcodingDetector] = None,
        risk_scorer: Optional[FWARiskScorer] = None,
    ):
        """
        Initialize FWAService.

        Args:
            duplicate_detector: DuplicateDetector instance
            pattern_analyzer: PatternAnalyzer instance
            upcoding_detector: UpcodingDetector instance
            risk_scorer: FWARiskScorer instance
        """
        self.duplicate_detector = duplicate_detector or get_duplicate_detector()
        self.pattern_analyzer = pattern_analyzer or get_pattern_analyzer()
        self.upcoding_detector = upcoding_detector or get_upcoding_detector()
        self.risk_scorer = risk_scorer or get_risk_scorer()

    async def analyze_claim(
        self,
        context: FWAAnalysisContext,
        existing_claims: Optional[list[dict]] = None,
        provider_claims: Optional[list[dict]] = None,
        skip_duplicate_check: bool = False,
        skip_upcoding_check: bool = False,
        skip_pattern_check: bool = False,
        skip_ml_scoring: bool = False,
    ) -> FWAResult:
        """
        Perform comprehensive FWA analysis on a claim.

        Args:
            context: FWA analysis context with claim details
            existing_claims: Historical claims for duplicate detection
            provider_claims: Provider's claims for pattern analysis
            skip_duplicate_check: Skip duplicate detection
            skip_upcoding_check: Skip upcoding/unbundling detection
            skip_pattern_check: Skip pattern analysis
            skip_ml_scoring: Skip ML-based scoring

        Returns:
            FWAResult with comprehensive analysis
        """
        start_time = time.time()

        result = FWAResult(
            claim_id=context.claim_id,
            analysis_timestamp=datetime.utcnow(),
            model_version=self.risk_scorer.model_version,
        )

        # Build claim data dict for detectors
        claim_data = {
            "claim_id": context.claim_id,
            "member_id": context.member_id,
            "provider_id": context.provider_id,
            "service_date": context.service_date,
            "total_charged": context.total_charged,
            "procedure_codes": context.procedure_codes,
            "diagnosis_codes": context.diagnosis_codes,
        }

        rules_evaluated = 0

        try:
            # Step 1: Duplicate Detection
            if not skip_duplicate_check and existing_claims:
                result.duplicate_check = await self.duplicate_detector.detect_duplicates(
                    claim_data,
                    existing_claims,
                    threshold=context.duplicate_threshold,
                )
                rules_evaluated += 1

                # Create flag if duplicate detected
                dup_flag = self.duplicate_detector.create_flag(result.duplicate_check)
                if dup_flag:
                    result.flags.append(dup_flag)

            # Step 2: Upcoding Detection
            if not skip_upcoding_check:
                # Get provider E/M history if available
                provider_em_history = None
                if provider_claims:
                    em_analysis = await self.upcoding_detector.analyze_em_distribution(
                        provider_claims
                    )
                    provider_em_history = em_analysis.get("distribution")

                result.upcoding_check = await self.upcoding_detector.detect_upcoding(
                    context.procedure_codes,
                    provider_em_history,
                    context.diagnosis_codes,
                )
                rules_evaluated += 1

                # Unbundling detection
                result.unbundling_check = await self.upcoding_detector.detect_unbundling(
                    context.procedure_codes
                )
                rules_evaluated += 1

                # Create flags
                upcoding_flags = self.upcoding_detector.create_flags(
                    result.upcoding_check,
                    result.unbundling_check,
                )
                result.flags.extend(upcoding_flags)

            # Step 3: Pattern Analysis
            if not skip_pattern_check:
                # Check for impossible day billing
                if provider_claims:
                    daily_claims = [
                        c for c in provider_claims
                        if c.get("service_date") == context.service_date
                    ]
                    if daily_claims:
                        result.pattern_anomaly = await self.pattern_analyzer.detect_impossible_day(
                            context.provider_id,
                            context.service_date,
                            daily_claims,
                        )
                        rules_evaluated += 1

                        if result.pattern_anomaly.is_anomaly_detected:
                            result.flags.append(
                                FWAFlag(
                                    flag_type=FWAFlagType.IMPOSSIBLE_DAY,
                                    severity=FWARiskLevel.HIGH,
                                    description=result.pattern_anomaly.description or "Impossible day detected",
                                    score_contribution=0.4,
                                    evidence={
                                        "baseline": result.pattern_anomaly.baseline_value,
                                        "observed": result.pattern_anomaly.observed_value,
                                    },
                                    rule_id="PAT005",
                                )
                            )

                    # Provider behavior scoring
                    result.provider_score = await self.pattern_analyzer.analyze_provider_patterns(
                        context.provider_id,
                        provider_claims,
                        context.provider_history.__dict__ if context.provider_history else None,
                    )
                    rules_evaluated += 1

                    # Add provider flags
                    result.flags.extend(result.provider_score.flags)

                # Check for excessive services
                if context.member_claim_history:
                    excessive_result = await self.pattern_analyzer.detect_excessive_services(
                        claim_data,
                        context.member_claim_history,
                    )
                    rules_evaluated += 1

                    if excessive_result.is_anomaly_detected:
                        result.flags.append(
                            FWAFlag(
                                flag_type=FWAFlagType.EXCESSIVE_SERVICES,
                                severity=FWARiskLevel.MEDIUM,
                                description=excessive_result.description or "Excessive services detected",
                                score_contribution=0.2,
                                rule_id="PAT006",
                            )
                        )

            # Step 4: Additional rule-based checks
            additional_flags = self._run_additional_checks(context)
            result.flags.extend(additional_flags)
            rules_evaluated += len(additional_flags) > 0

            # Step 5: Calculate final risk score
            if not skip_ml_scoring:
                risk_score, risk_level, recommendation = await self.risk_scorer.calculate_risk_score(
                    claim_data,
                    result.flags,
                    context.provider_history.__dict__ if context.provider_history else None,
                    context.member_claim_history,
                )
                result.risk_score = risk_score
                result.risk_level = risk_level
                result.recommendation = recommendation
                rules_evaluated += 1
            else:
                # Calculate score from flags only
                result._recalculate_risk()
                result.recommendation = self._get_recommendation_from_flags(result.flags)

            result.rules_evaluated = rules_evaluated

        except Exception as e:
            result.notes.append(f"Error during FWA analysis: {str(e)}")
            result.risk_level = FWARiskLevel.MEDIUM
            result.recommendation = FWARecommendation.REVIEW

        result.processing_time_ms = int((time.time() - start_time) * 1000)
        return result

    async def quick_check(
        self,
        claim_data: dict,
        existing_claims: Optional[list[dict]] = None,
    ) -> tuple[float, FWARiskLevel, FWARecommendation]:
        """
        Quick FWA check for high-volume scenarios.

        Args:
            claim_data: Basic claim data
            existing_claims: Claims to check for duplicates

        Returns:
            Tuple of (risk_score, risk_level, recommendation)
        """
        flags = []

        # Quick duplicate check
        if existing_claims:
            dup_result = await self.duplicate_detector.detect_duplicates(
                claim_data, existing_claims
            )
            dup_flag = self.duplicate_detector.create_flag(dup_result)
            if dup_flag:
                flags.append(dup_flag)

        # Quick upcoding check
        procedure_codes = claim_data.get("procedure_codes", [])
        diagnosis_codes = claim_data.get("diagnosis_codes", [])

        upcoding_result = await self.upcoding_detector.detect_upcoding(
            procedure_codes, None, diagnosis_codes
        )
        unbundling_result = await self.upcoding_detector.detect_unbundling(procedure_codes)

        upcoding_flags = self.upcoding_detector.create_flags(upcoding_result, unbundling_result)
        flags.extend(upcoding_flags)

        # Calculate score
        risk_score = sum(f.score_contribution for f in flags)
        risk_score = min(1.0, risk_score)

        # Determine level
        if risk_score >= 0.8:
            risk_level = FWARiskLevel.CRITICAL
        elif risk_score >= 0.6:
            risk_level = FWARiskLevel.HIGH
        elif risk_score >= 0.3:
            risk_level = FWARiskLevel.MEDIUM
        else:
            risk_level = FWARiskLevel.LOW

        # Recommendation
        recommendation = self._get_recommendation_from_flags(flags)

        return risk_score, risk_level, recommendation

    def _run_additional_checks(self, context: FWAAnalysisContext) -> list[FWAFlag]:
        """Run additional rule-based checks."""
        flags = []

        # High cost outlier check
        if context.total_charged > context.auto_approve_threshold * 2:
            flags.append(
                FWAFlag(
                    flag_type=FWAFlagType.HIGH_COST_OUTLIER,
                    severity=FWARiskLevel.MEDIUM,
                    description=f"Claim amount ${context.total_charged:.2f} is unusually high",
                    score_contribution=0.15,
                    rule_id="ADD001",
                )
            )

        # Weekend service check (for non-emergency claims)
        if context.service_date.weekday() >= 5 and context.claim_type not in ["emergency", "urgent"]:
            flags.append(
                FWAFlag(
                    flag_type=FWAFlagType.PATTERN_ANOMALY,
                    severity=FWARiskLevel.LOW,
                    description="Service date is on weekend",
                    score_contribution=0.05,
                    rule_id="ADD002",
                )
            )

        # Many procedures check
        if len(context.procedure_codes) > 10:
            flags.append(
                FWAFlag(
                    flag_type=FWAFlagType.EXCESSIVE_SERVICES,
                    severity=FWARiskLevel.MEDIUM,
                    description=f"Claim has {len(context.procedure_codes)} procedures",
                    score_contribution=0.1,
                    rule_id="ADD003",
                )
            )

        return flags

    def _get_recommendation_from_flags(self, flags: list[FWAFlag]) -> FWARecommendation:
        """Get recommendation based on flags alone."""
        if not flags:
            return FWARecommendation.APPROVE

        has_critical = any(f.severity == FWARiskLevel.CRITICAL for f in flags)
        has_high = any(f.severity == FWARiskLevel.HIGH for f in flags)
        has_duplicate = any(f.flag_type == FWAFlagType.DUPLICATE_CLAIM for f in flags)

        if has_critical:
            return FWARecommendation.DENY
        elif has_duplicate and any(
            f.flag_type == FWAFlagType.DUPLICATE_CLAIM and f.score_contribution >= 0.4
            for f in flags
        ):
            return FWARecommendation.DENY
        elif has_high or has_duplicate:
            return FWARecommendation.INVESTIGATE
        elif flags:
            return FWARecommendation.REVIEW
        else:
            return FWARecommendation.APPROVE


# =============================================================================
# Factory Functions
# =============================================================================


_fwa_service: Optional[FWAService] = None


def get_fwa_service() -> FWAService:
    """Get singleton FWAService instance."""
    global _fwa_service
    if _fwa_service is None:
        _fwa_service = FWAService()
    return _fwa_service


def create_fwa_service(
    duplicate_detector: Optional[DuplicateDetector] = None,
    pattern_analyzer: Optional[PatternAnalyzer] = None,
    upcoding_detector: Optional[UpcodingDetector] = None,
    risk_scorer: Optional[FWARiskScorer] = None,
) -> FWAService:
    """Create a new FWAService instance."""
    return FWAService(
        duplicate_detector,
        pattern_analyzer,
        upcoding_detector,
        risk_scorer,
    )
