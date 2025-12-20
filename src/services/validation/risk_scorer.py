"""
Risk Scorer for Claims Validation.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Calculates overall risk score based on validation results.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from src.schemas.validation_result import RuleValidationDetail

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk level classification."""

    LOW = "low"           # 0.0-0.3
    MEDIUM = "medium"     # 0.3-0.5
    HIGH = "high"         # 0.5-0.7
    CRITICAL = "critical" # 0.7-1.0


class RiskCategory(str, Enum):
    """Risk categories for FWA detection."""

    FRAUD = "fraud"
    WASTE = "waste"
    ABUSE = "abuse"
    CODING_ERROR = "coding_error"
    DOCUMENTATION = "documentation"
    ELIGIBILITY = "eligibility"
    MEDICAL_NECESSITY = "medical_necessity"


@dataclass
class RiskFactor:
    """Individual risk factor contributing to overall score."""

    category: RiskCategory
    source: str  # rule_id or signal type
    severity: float  # 0.0-1.0
    confidence: float  # 0.0-1.0
    description: str
    evidence: Optional[str] = None

    @property
    def weighted_score(self) -> float:
        """Calculate weighted score (severity * confidence)."""
        return self.severity * self.confidence

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "source": self.source,
            "severity": self.severity,
            "confidence": self.confidence,
            "description": self.description,
            "evidence": self.evidence,
            "weighted_score": self.weighted_score,
        }


@dataclass
class RiskAssessment:
    """Complete risk assessment result."""

    risk_score: float  # 0.0-1.0
    risk_level: str
    risk_factors: list[RiskFactor] = field(default_factory=list)
    primary_category: Optional[RiskCategory] = None
    recommendation: str = ""
    requires_investigation: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "risk_score": round(self.risk_score, 3),
            "risk_level": self.risk_level,
            "primary_category": self.primary_category.value if self.primary_category else None,
            "risk_factors": [f.to_dict() for f in self.risk_factors],
            "recommendation": self.recommendation,
            "requires_investigation": self.requires_investigation,
        }


class RiskScorer:
    """
    Calculates risk scores for claims based on validation results.

    Risk scoring methodology:
    1. Each failed rule contributes to risk based on severity
    2. Fraud signals have highest weight
    3. Multiple failures compound the risk
    4. Low confidence increases risk for review
    """

    # Rule severity weights (0.0-1.0)
    RULE_WEIGHTS = {
        "rule_1": 0.3,  # Data extraction - low (process issue)
        "rule_2": 0.3,  # Code extraction - low (process issue)
        "rule_3": 0.9,  # PDF forensics - critical (fraud)
        "rule_4": 0.6,  # ICD-CPT crosswalk - medium (coding)
        "rule_5": 0.7,  # Clinical necessity - high (abuse)
        "rule_6": 0.5,  # ICD conflicts - medium (coding)
        "rule_7": 0.4,  # Age validation - low-medium
        "rule_8": 0.4,  # Gender validation - low-medium
        "rule_7_8": 0.4, # Combined demographics
        "rule_9": 0.6,  # Documentation - medium (compliance)
    }

    # Rule to risk category mapping
    RULE_CATEGORIES = {
        "rule_1": RiskCategory.DOCUMENTATION,
        "rule_2": RiskCategory.DOCUMENTATION,
        "rule_3": RiskCategory.FRAUD,
        "rule_4": RiskCategory.CODING_ERROR,
        "rule_5": RiskCategory.MEDICAL_NECESSITY,
        "rule_6": RiskCategory.CODING_ERROR,
        "rule_7": RiskCategory.ELIGIBILITY,
        "rule_8": RiskCategory.ELIGIBILITY,
        "rule_7_8": RiskCategory.ELIGIBILITY,
        "rule_9": RiskCategory.DOCUMENTATION,
    }

    def calculate_risk(
        self,
        rule_results: list[RuleValidationDetail],
        critical_issues: list[str],
        warnings: list[str],
    ) -> RiskAssessment:
        """
        Calculate overall risk assessment.

        Args:
            rule_results: List of validation rule results
            critical_issues: List of critical issues
            warnings: List of warnings

        Returns:
            RiskAssessment with overall score and factors
        """
        risk_factors: list[RiskFactor] = []
        category_scores: dict[RiskCategory, float] = {}

        # Process each rule result
        for result in rule_results:
            if result.status == "failed":
                weight = self.RULE_WEIGHTS.get(result.rule_id, 0.5)
                category = self.RULE_CATEGORIES.get(result.rule_id, RiskCategory.CODING_ERROR)

                # Calculate severity based on issues found
                severity = min(weight * (1 + result.issues_found * 0.1), 1.0)
                confidence = result.confidence if result.confidence > 0 else 0.5

                factor = RiskFactor(
                    category=category,
                    source=result.rule_id,
                    severity=severity,
                    confidence=confidence,
                    description=f"{result.rule_name} failed with {result.issues_found} issues",
                )
                risk_factors.append(factor)

                # Aggregate by category
                if category not in category_scores:
                    category_scores[category] = 0.0
                category_scores[category] += factor.weighted_score

            elif result.status == "warning":
                # Warnings contribute less to risk
                weight = self.RULE_WEIGHTS.get(result.rule_id, 0.3) * 0.3
                category = self.RULE_CATEGORIES.get(result.rule_id, RiskCategory.DOCUMENTATION)

                factor = RiskFactor(
                    category=category,
                    source=result.rule_id,
                    severity=weight,
                    confidence=result.confidence if result.confidence > 0 else 0.3,
                    description=f"{result.rule_name} warning",
                )
                risk_factors.append(factor)

        # Add critical issues as risk factors
        for issue in critical_issues[:5]:  # Limit to top 5
            risk_factors.append(RiskFactor(
                category=RiskCategory.FRAUD,
                source="critical_issue",
                severity=0.8,
                confidence=0.9,
                description=issue[:200],
            ))

        # Calculate overall risk score
        if not risk_factors:
            risk_score = 0.0
        else:
            # Weighted average with compounding for multiple factors
            total_weighted = sum(f.weighted_score for f in risk_factors)
            factor_count = len(risk_factors)

            # Base score from weighted average
            base_score = total_weighted / max(factor_count, 1)

            # Compound multiplier for multiple failures
            if factor_count > 1:
                compound_multiplier = 1 + (factor_count - 1) * 0.1
                risk_score = min(base_score * compound_multiplier, 1.0)
            else:
                risk_score = base_score

        # Determine risk level
        risk_level = self._determine_risk_level(risk_score)

        # Find primary risk category
        primary_category = None
        if category_scores:
            primary_category = max(category_scores, key=category_scores.get)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            risk_level, primary_category, len(critical_issues)
        )

        # Determine if investigation required
        requires_investigation = (
            risk_level in ("high", "critical")
            or primary_category == RiskCategory.FRAUD
            or len(critical_issues) > 0
        )

        return RiskAssessment(
            risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=sorted(risk_factors, key=lambda f: f.weighted_score, reverse=True),
            primary_category=primary_category,
            recommendation=recommendation,
            requires_investigation=requires_investigation,
        )

    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level from score."""
        if score >= 0.7:
            return "critical"
        elif score >= 0.5:
            return "high"
        elif score >= 0.3:
            return "medium"
        else:
            return "low"

    def _generate_recommendation(
        self,
        risk_level: str,
        primary_category: Optional[RiskCategory],
        critical_count: int,
    ) -> str:
        """Generate recommendation based on risk assessment."""
        if risk_level == "critical":
            return "REJECT: Critical risk detected. Manual investigation required before processing."

        if risk_level == "high":
            if primary_category == RiskCategory.FRAUD:
                return "HOLD: Suspected fraud indicators. Route to SIU for investigation."
            elif primary_category == RiskCategory.MEDICAL_NECESSITY:
                return "REVIEW: Medical necessity concerns. Route to clinical reviewer."
            else:
                return "REVIEW: High risk detected. Requires supervisor review before processing."

        if risk_level == "medium":
            if primary_category == RiskCategory.CODING_ERROR:
                return "REVIEW: Potential coding issues. Verify codes before processing."
            elif primary_category == RiskCategory.DOCUMENTATION:
                return "REVIEW: Documentation concerns. Request additional documentation."
            else:
                return "PROCESS WITH CAUTION: Minor issues detected. Note for audit."

        return "APPROVE: Low risk. Standard processing."

    def calculate_fraud_score(
        self,
        forensic_signals: list[dict],
        pattern_matches: list[dict],
    ) -> float:
        """
        Calculate specific fraud score based on forensic signals.

        Args:
            forensic_signals: PDF forensics signals
            pattern_matches: Historical pattern matches

        Returns:
            Fraud score 0.0-1.0
        """
        if not forensic_signals and not pattern_matches:
            return 0.0

        # Weight forensic signals
        signal_scores = []
        for signal in forensic_signals:
            severity = signal.get("severity", "low")
            confidence = signal.get("confidence", 0.5)

            severity_weight = {
                "low": 0.2,
                "medium": 0.5,
                "high": 0.8,
                "critical": 1.0,
            }.get(severity, 0.3)

            signal_scores.append(severity_weight * confidence)

        # Weight pattern matches
        pattern_scores = []
        for pattern in pattern_matches:
            match_score = pattern.get("match_score", 0.5)
            pattern_severity = pattern.get("severity", 0.5)
            pattern_scores.append(match_score * pattern_severity)

        # Combine scores
        all_scores = signal_scores + pattern_scores
        if not all_scores:
            return 0.0

        # Use max score with bonus for multiple signals
        max_score = max(all_scores)
        if len(all_scores) > 1:
            bonus = min(len(all_scores) * 0.05, 0.3)
            return min(max_score + bonus, 1.0)

        return max_score


# Singleton instance
_risk_scorer: Optional[RiskScorer] = None


def get_risk_scorer() -> RiskScorer:
    """Get or create the singleton risk scorer."""
    global _risk_scorer
    if _risk_scorer is None:
        _risk_scorer = RiskScorer()
    return _risk_scorer
