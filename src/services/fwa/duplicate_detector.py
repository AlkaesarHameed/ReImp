"""
Duplicate Claim Detection Service.
Source: Design Document Section 4.2 - Fraud Detection
Verified: 2025-12-18

Detects duplicate and near-duplicate claims using fuzzy matching.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from src.schemas.fwa import DuplicateClaimFlag, FWAFlag, FWAFlagType, FWARiskLevel


class DuplicateDetector:
    """
    Detects duplicate and near-duplicate claims.

    Uses weighted field matching to identify:
    - Exact duplicates (same claim resubmitted)
    - Near duplicates (similar claims, possible rebilling)
    - Related claims (same service, different dates)
    """

    # Field weights for similarity calculation
    FIELD_WEIGHTS = {
        "member_id": 0.20,
        "provider_id": 0.15,
        "service_date": 0.25,
        "procedure_codes": 0.25,
        "total_charged": 0.10,
        "diagnosis_codes": 0.05,
    }

    # Thresholds
    EXACT_DUPLICATE_THRESHOLD = 0.95
    POSSIBLE_DUPLICATE_THRESHOLD = 0.75
    DATE_TOLERANCE_DAYS = 3

    def __init__(self):
        """Initialize DuplicateDetector."""
        pass

    async def detect_duplicates(
        self,
        claim_data: dict,
        existing_claims: list[dict],
        threshold: float = 0.75,
    ) -> DuplicateClaimFlag:
        """
        Detect duplicate claims against existing claims.

        Args:
            claim_data: Current claim data
            existing_claims: List of existing claims to check against
            threshold: Minimum similarity threshold

        Returns:
            DuplicateClaimFlag with detection results
        """
        result = DuplicateClaimFlag()

        if not existing_claims:
            return result

        best_match = None
        best_score = 0.0
        best_matching_fields = []

        for existing in existing_claims:
            # Skip if same claim ID
            if claim_data.get("claim_id") == existing.get("claim_id"):
                continue

            score, matching_fields = self._calculate_similarity(claim_data, existing)

            if score > best_score:
                best_score = score
                best_match = existing
                best_matching_fields = matching_fields

        result.similarity_score = best_score
        result.matching_fields = best_matching_fields

        if best_score >= self.EXACT_DUPLICATE_THRESHOLD:
            result.is_duplicate = True
            result.original_claim_id = best_match.get("claim_id")
            result.original_tracking_number = best_match.get("tracking_number")
        elif best_score >= self.POSSIBLE_DUPLICATE_THRESHOLD:
            result.is_possible_duplicate = True
            result.original_claim_id = best_match.get("claim_id")
            result.original_tracking_number = best_match.get("tracking_number")

        # Calculate days apart
        if best_match:
            claim_date = claim_data.get("service_date")
            existing_date = best_match.get("service_date")
            if claim_date and existing_date:
                if isinstance(claim_date, str):
                    claim_date = date.fromisoformat(claim_date)
                if isinstance(existing_date, str):
                    existing_date = date.fromisoformat(existing_date)
                result.days_apart = abs((claim_date - existing_date).days)

        return result

    def _calculate_similarity(
        self,
        claim1: dict,
        claim2: dict,
    ) -> tuple[float, list[str]]:
        """Calculate similarity score between two claims."""
        total_score = 0.0
        matching_fields = []

        # Member ID match
        if claim1.get("member_id") == claim2.get("member_id"):
            total_score += self.FIELD_WEIGHTS["member_id"]
            matching_fields.append("member_id")

        # Provider ID match
        if claim1.get("provider_id") == claim2.get("provider_id"):
            total_score += self.FIELD_WEIGHTS["provider_id"]
            matching_fields.append("provider_id")

        # Service date match (with tolerance)
        date_score = self._compare_dates(
            claim1.get("service_date"),
            claim2.get("service_date"),
        )
        if date_score > 0:
            total_score += self.FIELD_WEIGHTS["service_date"] * date_score
            if date_score == 1.0:
                matching_fields.append("service_date")

        # Procedure codes match
        proc_score = self._compare_code_lists(
            claim1.get("procedure_codes", []),
            claim2.get("procedure_codes", []),
        )
        if proc_score > 0:
            total_score += self.FIELD_WEIGHTS["procedure_codes"] * proc_score
            if proc_score >= 0.8:
                matching_fields.append("procedure_codes")

        # Diagnosis codes match
        diag_score = self._compare_code_lists(
            claim1.get("diagnosis_codes", []),
            claim2.get("diagnosis_codes", []),
        )
        if diag_score > 0:
            total_score += self.FIELD_WEIGHTS["diagnosis_codes"] * diag_score
            if diag_score >= 0.8:
                matching_fields.append("diagnosis_codes")

        # Total charged match
        amount_score = self._compare_amounts(
            claim1.get("total_charged"),
            claim2.get("total_charged"),
        )
        if amount_score > 0:
            total_score += self.FIELD_WEIGHTS["total_charged"] * amount_score
            if amount_score >= 0.95:
                matching_fields.append("total_charged")

        return total_score, matching_fields

    def _compare_dates(
        self,
        date1: Optional[date],
        date2: Optional[date],
    ) -> float:
        """Compare two dates with tolerance."""
        if date1 is None or date2 is None:
            return 0.0

        if isinstance(date1, str):
            date1 = date.fromisoformat(date1)
        if isinstance(date2, str):
            date2 = date.fromisoformat(date2)

        days_diff = abs((date1 - date2).days)

        if days_diff == 0:
            return 1.0
        elif days_diff <= self.DATE_TOLERANCE_DAYS:
            return 1.0 - (days_diff / (self.DATE_TOLERANCE_DAYS + 1))
        else:
            return 0.0

    def _compare_code_lists(
        self,
        codes1: list[str],
        codes2: list[str],
    ) -> float:
        """Compare two code lists using Jaccard similarity."""
        if not codes1 or not codes2:
            return 0.0

        set1 = set(codes1)
        set2 = set(codes2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union == 0:
            return 0.0

        return intersection / union

    def _compare_amounts(
        self,
        amount1: Optional[Decimal],
        amount2: Optional[Decimal],
    ) -> float:
        """Compare two monetary amounts."""
        if amount1 is None or amount2 is None:
            return 0.0

        if isinstance(amount1, (int, float)):
            amount1 = Decimal(str(amount1))
        if isinstance(amount2, (int, float)):
            amount2 = Decimal(str(amount2))

        if amount1 == amount2:
            return 1.0

        # Calculate percentage difference
        max_amount = max(amount1, amount2)
        if max_amount == 0:
            return 1.0

        diff_pct = abs(amount1 - amount2) / max_amount

        if diff_pct <= 0.01:  # Within 1%
            return 0.95
        elif diff_pct <= 0.05:  # Within 5%
            return 0.8
        elif diff_pct <= 0.10:  # Within 10%
            return 0.5
        else:
            return 0.0

    def create_flag(self, result: DuplicateClaimFlag) -> Optional[FWAFlag]:
        """Create FWA flag from duplicate detection result."""
        if result.is_duplicate:
            return FWAFlag(
                flag_type=FWAFlagType.DUPLICATE_CLAIM,
                severity=FWARiskLevel.HIGH,
                description=f"Exact duplicate of claim {result.original_tracking_number}",
                score_contribution=0.5,
                evidence={
                    "similarity_score": result.similarity_score,
                    "matching_fields": result.matching_fields,
                    "original_claim_id": str(result.original_claim_id),
                },
                rule_id="DUP001",
            )
        elif result.is_possible_duplicate:
            return FWAFlag(
                flag_type=FWAFlagType.DUPLICATE_CLAIM,
                severity=FWARiskLevel.MEDIUM,
                description=f"Possible duplicate of claim {result.original_tracking_number}",
                score_contribution=0.25,
                evidence={
                    "similarity_score": result.similarity_score,
                    "matching_fields": result.matching_fields,
                    "days_apart": result.days_apart,
                },
                rule_id="DUP002",
            )
        return None


# =============================================================================
# Factory Functions
# =============================================================================


_duplicate_detector: Optional[DuplicateDetector] = None


def get_duplicate_detector() -> DuplicateDetector:
    """Get singleton DuplicateDetector instance."""
    global _duplicate_detector
    if _duplicate_detector is None:
        _duplicate_detector = DuplicateDetector()
    return _duplicate_detector
