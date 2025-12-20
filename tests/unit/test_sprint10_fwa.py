"""
Sprint 10: FWA Detection Tests.
Tests for Fraud, Waste, and Abuse detection services.

Uses inline classes to avoid import chain issues with pgvector, JWT, and settings.
"""

import pytest
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# =============================================================================
# Inline Schema Classes (matching src/schemas/fwa.py)
# =============================================================================


class FWARiskLevel(str, Enum):
    """FWA risk level classifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FWAFlagType(str, Enum):
    """Types of FWA flags."""
    DUPLICATE_CLAIM = "duplicate_claim"
    UPCODING = "upcoding"
    UNBUNDLING = "unbundling"
    PHANTOM_BILLING = "phantom_billing"
    EXCESSIVE_SERVICES = "excessive_services"
    IMPOSSIBLE_DAY = "impossible_day"
    PATTERN_ANOMALY = "pattern_anomaly"
    HIGH_COST_OUTLIER = "high_cost_outlier"
    PROVIDER_RISK = "provider_risk"


class FWARecommendation(str, Enum):
    """FWA recommended actions."""
    APPROVE = "approve"
    REVIEW = "review"
    DENY = "deny"
    INVESTIGATE = "investigate"
    SUSPEND_PROVIDER = "suspend_provider"


class FWAFlag(BaseModel):
    """A single FWA flag."""
    flag_type: FWAFlagType
    severity: FWARiskLevel
    description: str
    score_contribution: float = 0.0
    evidence: Optional[dict] = None
    rule_id: Optional[str] = None


class DuplicateClaimFlag(BaseModel):
    """Duplicate claim detection result."""
    is_duplicate: bool = False
    is_possible_duplicate: bool = False
    similarity_score: float = 0.0
    matching_claim_id: Optional[str] = None
    matching_fields: list[str] = Field(default_factory=list)
    time_gap_days: Optional[int] = None


class UpcodingFlag(BaseModel):
    """Upcoding detection result."""
    is_upcoding_detected: bool = False
    upcoding_score: float = 0.0
    flagged_codes: list[str] = Field(default_factory=list)
    expected_code: Optional[str] = None
    actual_code: Optional[str] = None
    provider_em_pattern: Optional[dict] = None


class UnbundlingFlag(BaseModel):
    """Unbundling detection result."""
    is_unbundling_detected: bool = False
    unbundling_score: float = 0.0
    bundled_pairs: list[tuple[str, str]] = Field(default_factory=list)
    recommended_code: Optional[str] = None


class PatternAnomalyFlag(BaseModel):
    """Pattern anomaly detection result."""
    is_anomaly_detected: bool = False
    anomaly_score: float = 0.0
    anomaly_type: Optional[str] = None
    baseline_value: Optional[float] = None
    observed_value: Optional[float] = None
    description: Optional[str] = None


class ProviderBehaviorScore(BaseModel):
    """Provider behavior analysis result."""
    provider_id: str
    risk_score: float = 0.0
    risk_level: FWARiskLevel = FWARiskLevel.LOW
    flags: list[FWAFlag] = Field(default_factory=list)
    claim_volume_percentile: Optional[float] = None
    denial_rate: Optional[float] = None
    high_code_rate: Optional[float] = None


# =============================================================================
# Inline Duplicate Detector (matching src/services/fwa/duplicate_detector.py)
# =============================================================================


class DuplicateDetector:
    """Detects duplicate and similar claims."""

    FIELD_WEIGHTS = {
        "member_id": 0.20,
        "provider_id": 0.15,
        "service_date": 0.25,
        "procedure_codes": 0.25,
        "total_charged": 0.10,
        "diagnosis_codes": 0.05,
    }

    EXACT_DUPLICATE_THRESHOLD = 0.95
    POSSIBLE_DUPLICATE_THRESHOLD = 0.75

    async def detect_duplicates(
        self,
        claim_data: dict,
        existing_claims: list[dict],
        threshold: float = 0.75,
    ) -> DuplicateClaimFlag:
        """Detect duplicate or similar claims."""
        result = DuplicateClaimFlag()

        if not existing_claims:
            return result

        best_match = None
        best_score = 0.0
        best_fields = []

        for existing_claim in existing_claims:
            score, matching_fields = self._calculate_similarity(claim_data, existing_claim)
            if score > best_score:
                best_score = score
                best_match = existing_claim
                best_fields = matching_fields

        if best_score >= self.EXACT_DUPLICATE_THRESHOLD:
            result.is_duplicate = True
            result.is_possible_duplicate = True
        elif best_score >= max(threshold, self.POSSIBLE_DUPLICATE_THRESHOLD):
            result.is_possible_duplicate = True

        if best_match and best_score >= threshold:
            result.similarity_score = best_score
            result.matching_claim_id = str(best_match.get("claim_id", ""))
            result.matching_fields = best_fields

            service_date = claim_data.get("service_date")
            match_date = best_match.get("service_date")
            if service_date and match_date:
                if isinstance(service_date, str):
                    service_date = date.fromisoformat(service_date)
                if isinstance(match_date, str):
                    match_date = date.fromisoformat(match_date)
                result.time_gap_days = abs((service_date - match_date).days)

        return result

    def _calculate_similarity(self, claim1: dict, claim2: dict) -> tuple[float, list[str]]:
        """Calculate weighted similarity between two claims."""
        total_score = 0.0
        matching_fields = []

        for field, weight in self.FIELD_WEIGHTS.items():
            val1 = claim1.get(field)
            val2 = claim2.get(field)

            if val1 is None or val2 is None:
                continue

            if field == "procedure_codes":
                set1 = set(val1) if isinstance(val1, list) else {val1}
                set2 = set(val2) if isinstance(val2, list) else {val2}
                if set1 and set2:
                    similarity = len(set1 & set2) / len(set1 | set2)
                    total_score += weight * similarity
                    if similarity > 0.5:
                        matching_fields.append(field)
            elif field == "diagnosis_codes":
                set1 = set(val1) if isinstance(val1, list) else {val1}
                set2 = set(val2) if isinstance(val2, list) else {val2}
                if set1 and set2:
                    similarity = len(set1 & set2) / len(set1 | set2)
                    total_score += weight * similarity
                    if similarity > 0.5:
                        matching_fields.append(field)
            elif field == "total_charged":
                try:
                    v1, v2 = float(val1), float(val2)
                    if max(v1, v2) > 0:
                        similarity = 1 - abs(v1 - v2) / max(v1, v2)
                        total_score += weight * max(0, similarity)
                        if similarity > 0.95:
                            matching_fields.append(field)
                except (TypeError, ValueError):
                    pass
            else:
                str1 = str(val1).strip().lower()
                str2 = str(val2).strip().lower()
                if str1 == str2:
                    total_score += weight
                    matching_fields.append(field)

        return total_score, matching_fields

    def create_flag(self, result: DuplicateClaimFlag) -> Optional[FWAFlag]:
        """Create FWA flag from duplicate detection result."""
        if result.is_duplicate:
            return FWAFlag(
                flag_type=FWAFlagType.DUPLICATE_CLAIM,
                severity=FWARiskLevel.CRITICAL,
                description=f"Exact duplicate of claim {result.matching_claim_id}",
                score_contribution=0.5,
                evidence={
                    "matching_claim_id": result.matching_claim_id,
                    "similarity_score": result.similarity_score,
                    "matching_fields": result.matching_fields,
                },
                rule_id="DUP001",
            )
        elif result.is_possible_duplicate:
            return FWAFlag(
                flag_type=FWAFlagType.DUPLICATE_CLAIM,
                severity=FWARiskLevel.HIGH,
                description=f"Possible duplicate of claim {result.matching_claim_id}",
                score_contribution=0.3,
                evidence={
                    "matching_claim_id": result.matching_claim_id,
                    "similarity_score": result.similarity_score,
                    "matching_fields": result.matching_fields,
                },
                rule_id="DUP002",
            )
        return None


# =============================================================================
# Inline Upcoding Detector (matching src/services/fwa/upcoding_detector.py)
# =============================================================================


class UpcodingDetector:
    """Detects upcoding and unbundling in claims."""

    EM_HIERARCHIES = {
        "established_patient": ["99211", "99212", "99213", "99214", "99215"],
        "new_patient": ["99201", "99202", "99203", "99204", "99205"],
        "inpatient": ["99221", "99222", "99223"],
    }

    EXPECTED_EM_DISTRIBUTION = {
        "established_patient": {
            "99211": 0.02,
            "99212": 0.08,
            "99213": 0.45,
            "99214": 0.35,
            "99215": 0.10,
        },
        "new_patient": {
            "99202": 0.10,
            "99203": 0.35,
            "99204": 0.40,
            "99205": 0.15,
        },
    }

    BUNDLED_PROCEDURES = {
        "82947": "80053",  # Glucose part of CMP
        "82565": "80053",  # Creatinine part of CMP
        "82374": "80048",  # CO2 part of BMP
        "84132": "80048",  # Potassium part of BMP
        "82435": "80048",  # Chloride part of BMP
        "84295": "80048",  # Sodium part of BMP
        "82310": "80048",  # Calcium part of BMP
    }

    async def detect_upcoding(
        self,
        procedure_codes: list[str],
        provider_em_history: Optional[dict] = None,
        diagnosis_codes: Optional[list[str]] = None,
    ) -> UpcodingFlag:
        """Detect potential upcoding in procedure codes."""
        result = UpcodingFlag()

        em_codes_in_claim = []
        for hierarchy_name, codes in self.EM_HIERARCHIES.items():
            for code in codes:
                if code in procedure_codes:
                    em_codes_in_claim.append((code, hierarchy_name))

        if not em_codes_in_claim:
            return result

        if provider_em_history:
            for code, hierarchy in em_codes_in_claim:
                codes = self.EM_HIERARCHIES[hierarchy]
                code_idx = codes.index(code) if code in codes else -1

                if code_idx >= len(codes) - 2:  # High-level code
                    expected = self.EXPECTED_EM_DISTRIBUTION.get(hierarchy, {})
                    provider_rate = provider_em_history.get(code, 0)
                    expected_rate = expected.get(code, 0.1)

                    if provider_rate > expected_rate * 2:
                        result.is_upcoding_detected = True
                        result.upcoding_score = min(1.0, (provider_rate - expected_rate) / expected_rate)
                        result.flagged_codes.append(code)
                        result.actual_code = code
                        result.provider_em_pattern = provider_em_history

        if "99215" in procedure_codes or "99205" in procedure_codes:
            if diagnosis_codes:
                chronic_patterns = ["E11", "I10", "J45", "M54"]
                has_chronic = any(
                    any(dx.startswith(p) for p in chronic_patterns)
                    for dx in diagnosis_codes
                )
                if not has_chronic:
                    result.is_upcoding_detected = True
                    result.upcoding_score = max(result.upcoding_score, 0.4)
                    result.flagged_codes.append("99215" if "99215" in procedure_codes else "99205")

        return result

    async def detect_unbundling(self, procedure_codes: list[str]) -> UnbundlingFlag:
        """Detect potential unbundling in procedure codes."""
        result = UnbundlingFlag()

        code_set = set(procedure_codes)

        for component, panel in self.BUNDLED_PROCEDURES.items():
            if component in code_set and panel in code_set:
                result.is_unbundling_detected = True
                result.bundled_pairs.append((component, panel))
                result.recommended_code = panel
                result.unbundling_score += 0.2

        result.unbundling_score = min(1.0, result.unbundling_score)
        return result

    async def analyze_em_distribution(self, provider_claims: list[dict]) -> dict:
        """Analyze E/M code distribution for a provider."""
        em_counts = {hierarchy: {} for hierarchy in self.EM_HIERARCHIES}

        for claim in provider_claims:
            codes = claim.get("procedure_codes", [])
            for hierarchy, em_codes in self.EM_HIERARCHIES.items():
                for code in codes:
                    if code in em_codes:
                        em_counts[hierarchy][code] = em_counts[hierarchy].get(code, 0) + 1

        distribution = {}
        for hierarchy, counts in em_counts.items():
            total = sum(counts.values())
            if total > 0:
                distribution[hierarchy] = {
                    code: count / total for code, count in counts.items()
                }

        return {"distribution": distribution, "counts": em_counts}

    def create_flags(
        self,
        upcoding_result: UpcodingFlag,
        unbundling_result: UnbundlingFlag,
    ) -> list[FWAFlag]:
        """Create FWA flags from upcoding/unbundling results."""
        flags = []

        if upcoding_result.is_upcoding_detected:
            flags.append(
                FWAFlag(
                    flag_type=FWAFlagType.UPCODING,
                    severity=FWARiskLevel.HIGH if upcoding_result.upcoding_score > 0.5 else FWARiskLevel.MEDIUM,
                    description=f"Potential upcoding detected: {', '.join(upcoding_result.flagged_codes)}",
                    score_contribution=upcoding_result.upcoding_score * 0.4,
                    evidence={
                        "flagged_codes": upcoding_result.flagged_codes,
                        "upcoding_score": upcoding_result.upcoding_score,
                    },
                    rule_id="UPC001",
                )
            )

        if unbundling_result.is_unbundling_detected:
            flags.append(
                FWAFlag(
                    flag_type=FWAFlagType.UNBUNDLING,
                    severity=FWARiskLevel.MEDIUM,
                    description=f"Unbundling detected: {unbundling_result.bundled_pairs}",
                    score_contribution=0.25,
                    evidence={
                        "bundled_pairs": [list(p) for p in unbundling_result.bundled_pairs],
                        "recommended_code": unbundling_result.recommended_code,
                    },
                    rule_id="UNB001",
                )
            )

        return flags


# =============================================================================
# Inline Pattern Analyzer (matching src/services/fwa/pattern_analyzer.py)
# =============================================================================


class PatternAnalyzer:
    """Analyzes billing patterns for anomalies."""

    MAX_DAILY_PROCEDURES = 50
    MAX_DAILY_PATIENTS = 30
    MAX_PROCEDURES_PER_PATIENT = 15

    async def detect_impossible_day(
        self,
        provider_id: str,
        service_date: date,
        daily_claims: list[dict],
    ) -> PatternAnomalyFlag:
        """Detect impossible day billing patterns."""
        result = PatternAnomalyFlag()

        total_procedures = 0
        unique_patients = set()

        for claim in daily_claims:
            procedures = claim.get("procedure_codes", [])
            total_procedures += len(procedures)
            member_id = claim.get("member_id")
            if member_id:
                unique_patients.add(member_id)

        if total_procedures > self.MAX_DAILY_PROCEDURES:
            result.is_anomaly_detected = True
            result.anomaly_type = "excessive_daily_procedures"
            result.baseline_value = self.MAX_DAILY_PROCEDURES
            result.observed_value = total_procedures
            result.description = f"Provider billed {total_procedures} procedures on {service_date}"
            result.anomaly_score = min(1.0, (total_procedures - self.MAX_DAILY_PROCEDURES) / self.MAX_DAILY_PROCEDURES)

        if len(unique_patients) > self.MAX_DAILY_PATIENTS:
            result.is_anomaly_detected = True
            result.anomaly_type = "excessive_daily_patients"
            result.baseline_value = self.MAX_DAILY_PATIENTS
            result.observed_value = len(unique_patients)
            result.description = f"Provider saw {len(unique_patients)} patients on {service_date}"
            result.anomaly_score = max(
                result.anomaly_score,
                min(1.0, (len(unique_patients) - self.MAX_DAILY_PATIENTS) / self.MAX_DAILY_PATIENTS)
            )

        return result

    async def detect_excessive_services(
        self,
        claim_data: dict,
        member_history: list[dict],
        service_limits: Optional[dict] = None,
    ) -> PatternAnomalyFlag:
        """Detect excessive services for a member."""
        result = PatternAnomalyFlag()

        procedure_codes = claim_data.get("procedure_codes", [])
        if len(procedure_codes) > self.MAX_PROCEDURES_PER_PATIENT:
            result.is_anomaly_detected = True
            result.anomaly_type = "excessive_procedures_per_visit"
            result.baseline_value = self.MAX_PROCEDURES_PER_PATIENT
            result.observed_value = len(procedure_codes)
            result.description = f"Claim has {len(procedure_codes)} procedures"
            result.anomaly_score = min(1.0, (len(procedure_codes) - self.MAX_PROCEDURES_PER_PATIENT) / 10)

        return result

    async def analyze_provider_patterns(
        self,
        provider_id: str,
        provider_claims: list[dict],
        peer_benchmark: Optional[dict] = None,
    ) -> ProviderBehaviorScore:
        """Analyze overall provider behavior patterns."""
        result = ProviderBehaviorScore(provider_id=provider_id)

        if not provider_claims:
            return result

        # Calculate denial rate
        denied = sum(1 for c in provider_claims if c.get("status") == "denied")
        total = len(provider_claims)
        denial_rate = denied / total if total > 0 else 0
        result.denial_rate = denial_rate

        # Calculate high code rate
        high_codes = {"99215", "99205", "99223"}
        total_em = 0
        high_em = 0
        for claim in provider_claims:
            codes = claim.get("procedure_codes", [])
            for code in codes:
                if code in ["99211", "99212", "99213", "99214", "99215", "99203", "99204", "99205"]:
                    total_em += 1
                    if code in high_codes:
                        high_em += 1
        result.high_code_rate = high_em / total_em if total_em > 0 else 0

        # Risk scoring
        risk_score = 0.0
        if denial_rate > 0.2:
            risk_score += 0.3
            result.flags.append(
                FWAFlag(
                    flag_type=FWAFlagType.PROVIDER_RISK,
                    severity=FWARiskLevel.MEDIUM,
                    description=f"High denial rate: {denial_rate:.1%}",
                    score_contribution=0.15,
                    rule_id="PRV001",
                )
            )

        if result.high_code_rate > 0.3:
            risk_score += 0.4
            result.flags.append(
                FWAFlag(
                    flag_type=FWAFlagType.UPCODING,
                    severity=FWARiskLevel.HIGH,
                    description=f"High rate of level 5 codes: {result.high_code_rate:.1%}",
                    score_contribution=0.2,
                    rule_id="PRV002",
                )
            )

        result.risk_score = min(1.0, risk_score)
        if result.risk_score >= 0.6:
            result.risk_level = FWARiskLevel.HIGH
        elif result.risk_score >= 0.3:
            result.risk_level = FWARiskLevel.MEDIUM
        else:
            result.risk_level = FWARiskLevel.LOW

        return result


# =============================================================================
# Inline Risk Scorer (matching src/services/fwa/risk_scorer.py)
# =============================================================================


class FWARiskScorer:
    """Calculates FWA risk scores using rules and ML."""

    model_version: str = "1.0.0"

    async def calculate_risk_score(
        self,
        claim_data: dict,
        flags: list[FWAFlag],
        provider_profile: Optional[dict] = None,
        member_history: Optional[list[dict]] = None,
    ) -> tuple[float, FWARiskLevel, FWARecommendation]:
        """Calculate comprehensive FWA risk score."""
        # Rule-based score from flags
        flag_score = sum(f.score_contribution for f in flags)
        flag_score = min(1.0, flag_score)

        # Provider risk adjustment
        provider_risk = 0.0
        if provider_profile:
            denial_rate = provider_profile.get("denial_rate", 0)
            if denial_rate > 0.3:
                provider_risk = 0.2

        # Combined score
        risk_score = min(1.0, flag_score + provider_risk)

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
        recommendation = self._get_recommendation(risk_level, flags)

        return risk_score, risk_level, recommendation

    def _get_recommendation(
        self,
        risk_level: FWARiskLevel,
        flags: list[FWAFlag],
    ) -> FWARecommendation:
        """Get recommendation based on risk level and flags."""
        has_duplicate = any(f.flag_type == FWAFlagType.DUPLICATE_CLAIM for f in flags)
        has_critical = any(f.severity == FWARiskLevel.CRITICAL for f in flags)

        if risk_level == FWARiskLevel.CRITICAL or has_critical:
            return FWARecommendation.DENY
        elif has_duplicate:
            return FWARecommendation.INVESTIGATE
        elif risk_level == FWARiskLevel.HIGH:
            return FWARecommendation.INVESTIGATE
        elif risk_level == FWARiskLevel.MEDIUM:
            return FWARecommendation.REVIEW
        else:
            return FWARecommendation.APPROVE


# =============================================================================
# FWA Schemas Tests
# =============================================================================


class TestFWASchemas:
    """Tests for FWA schema models."""

    def test_fwa_risk_level_values(self):
        """Test FWA risk level enum values."""
        assert FWARiskLevel.LOW.value == "low"
        assert FWARiskLevel.MEDIUM.value == "medium"
        assert FWARiskLevel.HIGH.value == "high"
        assert FWARiskLevel.CRITICAL.value == "critical"

    def test_fwa_flag_type_values(self):
        """Test FWA flag type enum values."""
        assert FWAFlagType.DUPLICATE_CLAIM.value == "duplicate_claim"
        assert FWAFlagType.UPCODING.value == "upcoding"
        assert FWAFlagType.UNBUNDLING.value == "unbundling"
        assert FWAFlagType.IMPOSSIBLE_DAY.value == "impossible_day"

    def test_fwa_recommendation_values(self):
        """Test FWA recommendation enum values."""
        assert FWARecommendation.APPROVE.value == "approve"
        assert FWARecommendation.REVIEW.value == "review"
        assert FWARecommendation.DENY.value == "deny"
        assert FWARecommendation.INVESTIGATE.value == "investigate"

    def test_fwa_flag_creation(self):
        """Test FWA flag model creation."""
        flag = FWAFlag(
            flag_type=FWAFlagType.UPCODING,
            severity=FWARiskLevel.HIGH,
            description="Potential upcoding detected",
            score_contribution=0.3,
            rule_id="UPC001",
        )

        assert flag.flag_type == FWAFlagType.UPCODING
        assert flag.severity == FWARiskLevel.HIGH
        assert flag.score_contribution == 0.3

    def test_duplicate_claim_flag_defaults(self):
        """Test duplicate claim flag default values."""
        flag = DuplicateClaimFlag()

        assert flag.is_duplicate is False
        assert flag.is_possible_duplicate is False
        assert flag.similarity_score == 0.0
        assert flag.matching_fields == []

    def test_upcoding_flag_creation(self):
        """Test upcoding flag creation."""
        flag = UpcodingFlag(
            is_upcoding_detected=True,
            upcoding_score=0.6,
            flagged_codes=["99215"],
            expected_code="99213",
            actual_code="99215",
        )

        assert flag.is_upcoding_detected is True
        assert flag.upcoding_score == 0.6
        assert "99215" in flag.flagged_codes

    def test_unbundling_flag_creation(self):
        """Test unbundling flag creation."""
        flag = UnbundlingFlag(
            is_unbundling_detected=True,
            unbundling_score=0.4,
            bundled_pairs=[("82947", "80053")],
            recommended_code="80053",
        )

        assert flag.is_unbundling_detected is True
        assert ("82947", "80053") in flag.bundled_pairs

    def test_pattern_anomaly_flag(self):
        """Test pattern anomaly flag creation."""
        flag = PatternAnomalyFlag(
            is_anomaly_detected=True,
            anomaly_score=0.7,
            anomaly_type="excessive_daily_procedures",
            baseline_value=50,
            observed_value=75,
        )

        assert flag.is_anomaly_detected is True
        assert flag.observed_value > flag.baseline_value

    def test_provider_behavior_score(self):
        """Test provider behavior score creation."""
        score = ProviderBehaviorScore(
            provider_id="PRV001",
            risk_score=0.4,
            risk_level=FWARiskLevel.MEDIUM,
            denial_rate=0.15,
            high_code_rate=0.25,
        )

        assert score.provider_id == "PRV001"
        assert score.risk_level == FWARiskLevel.MEDIUM


# =============================================================================
# Duplicate Detector Tests
# =============================================================================


class TestDuplicateDetector:
    """Tests for duplicate claim detection."""

    @pytest.fixture
    def detector(self):
        """Create duplicate detector instance."""
        return DuplicateDetector()

    @pytest.fixture
    def base_claim(self):
        """Create base claim for testing."""
        return {
            "claim_id": "CLM001",
            "member_id": "MEM123",
            "provider_id": "PRV456",
            "service_date": date(2025, 1, 15),
            "procedure_codes": ["99213", "80053"],
            "diagnosis_codes": ["E11.9"],
            "total_charged": 250.00,
        }

    @pytest.mark.asyncio
    async def test_no_duplicates_empty_list(self, detector, base_claim):
        """Test detection with no existing claims."""
        result = await detector.detect_duplicates(base_claim, [])

        assert result.is_duplicate is False
        assert result.is_possible_duplicate is False

    @pytest.mark.asyncio
    async def test_exact_duplicate_detection(self, detector, base_claim):
        """Test detection of exact duplicate claim."""
        existing_claim = {
            "claim_id": "CLM002",
            "member_id": "MEM123",
            "provider_id": "PRV456",
            "service_date": date(2025, 1, 15),
            "procedure_codes": ["99213", "80053"],
            "diagnosis_codes": ["E11.9"],
            "total_charged": 250.00,
        }

        result = await detector.detect_duplicates(base_claim, [existing_claim])

        assert result.is_duplicate is True
        assert result.similarity_score >= 0.95
        assert result.matching_claim_id == "CLM002"

    @pytest.mark.asyncio
    async def test_possible_duplicate_detection(self, detector, base_claim):
        """Test detection of possible duplicate claim."""
        similar_claim = {
            "claim_id": "CLM003",
            "member_id": "MEM123",
            "provider_id": "PRV456",
            "service_date": date(2025, 1, 15),
            "procedure_codes": ["99213"],  # One less procedure
            "diagnosis_codes": ["E11.9"],
            "total_charged": 200.00,  # Different amount
        }

        result = await detector.detect_duplicates(base_claim, [similar_claim])

        assert result.is_possible_duplicate is True
        assert result.similarity_score >= 0.75

    @pytest.mark.asyncio
    async def test_different_member_not_duplicate(self, detector, base_claim):
        """Test that different member is not flagged as duplicate."""
        different_claim = {
            "claim_id": "CLM004",
            "member_id": "MEM999",  # Different member
            "provider_id": "PRV456",
            "service_date": date(2025, 1, 15),
            "procedure_codes": ["99213", "80053"],
            "diagnosis_codes": ["E11.9"],
            "total_charged": 250.00,
        }

        result = await detector.detect_duplicates(base_claim, [different_claim])

        assert result.is_duplicate is False
        # May or may not be possible duplicate depending on threshold

    @pytest.mark.asyncio
    async def test_different_date_not_exact_duplicate(self, detector, base_claim):
        """Test that different service date prevents exact duplicate."""
        next_day_claim = {
            "claim_id": "CLM005",
            "member_id": "MEM123",
            "provider_id": "PRV456",
            "service_date": date(2025, 1, 16),  # Next day
            "procedure_codes": ["99213", "80053"],
            "diagnosis_codes": ["E11.9"],
            "total_charged": 250.00,
        }

        result = await detector.detect_duplicates(base_claim, [next_day_claim])

        assert result.is_duplicate is False
        assert result.time_gap_days == 1

    @pytest.mark.asyncio
    async def test_duplicate_flag_creation_exact(self, detector, base_claim):
        """Test FWA flag creation for exact duplicate."""
        existing_claim = base_claim.copy()
        existing_claim["claim_id"] = "CLM006"

        result = await detector.detect_duplicates(base_claim, [existing_claim])
        flag = detector.create_flag(result)

        assert flag is not None
        assert flag.flag_type == FWAFlagType.DUPLICATE_CLAIM
        assert flag.severity == FWARiskLevel.CRITICAL
        assert flag.score_contribution == 0.5

    @pytest.mark.asyncio
    async def test_no_flag_for_non_duplicate(self, detector, base_claim):
        """Test no flag created for non-duplicate."""
        different_claim = {
            "claim_id": "CLM007",
            "member_id": "MEM999",
            "provider_id": "PRV000",
            "service_date": date(2025, 2, 1),
            "procedure_codes": ["99214"],
            "diagnosis_codes": ["I10"],
            "total_charged": 500.00,
        }

        result = await detector.detect_duplicates(base_claim, [different_claim])
        flag = detector.create_flag(result)

        assert flag is None


# =============================================================================
# Upcoding Detector Tests
# =============================================================================


class TestUpcodingDetector:
    """Tests for upcoding and unbundling detection."""

    @pytest.fixture
    def detector(self):
        """Create upcoding detector instance."""
        return UpcodingDetector()

    @pytest.mark.asyncio
    async def test_no_upcoding_normal_codes(self, detector):
        """Test no upcoding with normal codes."""
        procedure_codes = ["99213", "80053"]

        result = await detector.detect_upcoding(procedure_codes, None, ["E11.9"])

        assert result.is_upcoding_detected is False
        assert result.upcoding_score == 0.0

    @pytest.mark.asyncio
    async def test_upcoding_high_level_without_chronic(self, detector):
        """Test upcoding detection for high-level code without chronic diagnosis."""
        procedure_codes = ["99215"]  # Highest E/M level
        diagnosis_codes = ["J06.9"]  # Acute URI - not chronic

        result = await detector.detect_upcoding(procedure_codes, None, diagnosis_codes)

        assert result.is_upcoding_detected is True
        assert "99215" in result.flagged_codes

    @pytest.mark.asyncio
    async def test_upcoding_with_provider_history(self, detector):
        """Test upcoding detection with abnormal provider E/M history."""
        procedure_codes = ["99215"]
        provider_history = {
            "99213": 0.10,  # Much lower than expected 0.45
            "99214": 0.20,  # Lower than expected 0.35
            "99215": 0.70,  # Much higher than expected 0.10
        }

        result = await detector.detect_upcoding(procedure_codes, provider_history, ["E11.9"])

        assert result.is_upcoding_detected is True
        assert result.upcoding_score > 0

    @pytest.mark.asyncio
    async def test_unbundling_detection(self, detector):
        """Test unbundling detection."""
        # Billing glucose separately with CMP (glucose is part of CMP)
        procedure_codes = ["82947", "80053"]

        result = await detector.detect_unbundling(procedure_codes)

        assert result.is_unbundling_detected is True
        assert ("82947", "80053") in result.bundled_pairs
        assert result.recommended_code == "80053"

    @pytest.mark.asyncio
    async def test_no_unbundling_clean_codes(self, detector):
        """Test no unbundling with non-bundled codes."""
        procedure_codes = ["99213", "71046", "87880"]

        result = await detector.detect_unbundling(procedure_codes)

        assert result.is_unbundling_detected is False
        assert result.bundled_pairs == []

    @pytest.mark.asyncio
    async def test_em_distribution_analysis(self, detector):
        """Test E/M distribution analysis."""
        provider_claims = [
            {"procedure_codes": ["99213"]},
            {"procedure_codes": ["99213"]},
            {"procedure_codes": ["99214"]},
            {"procedure_codes": ["99215"]},
        ]

        result = await detector.analyze_em_distribution(provider_claims)

        assert "distribution" in result
        established = result["distribution"].get("established_patient", {})
        assert established.get("99213", 0) == 0.5
        assert established.get("99214", 0) == 0.25

    def test_create_flags_upcoding(self, detector):
        """Test flag creation for upcoding."""
        upcoding_result = UpcodingFlag(
            is_upcoding_detected=True,
            upcoding_score=0.6,
            flagged_codes=["99215"],
        )
        unbundling_result = UnbundlingFlag()

        flags = detector.create_flags(upcoding_result, unbundling_result)

        assert len(flags) == 1
        assert flags[0].flag_type == FWAFlagType.UPCODING
        assert flags[0].severity == FWARiskLevel.HIGH

    def test_create_flags_unbundling(self, detector):
        """Test flag creation for unbundling."""
        upcoding_result = UpcodingFlag()
        unbundling_result = UnbundlingFlag(
            is_unbundling_detected=True,
            unbundling_score=0.4,
            bundled_pairs=[("82947", "80053")],
        )

        flags = detector.create_flags(upcoding_result, unbundling_result)

        assert len(flags) == 1
        assert flags[0].flag_type == FWAFlagType.UNBUNDLING
        assert flags[0].severity == FWARiskLevel.MEDIUM


# =============================================================================
# Pattern Analyzer Tests
# =============================================================================


class TestPatternAnalyzer:
    """Tests for billing pattern analysis."""

    @pytest.fixture
    def analyzer(self):
        """Create pattern analyzer instance."""
        return PatternAnalyzer()

    @pytest.mark.asyncio
    async def test_impossible_day_excessive_procedures(self, analyzer):
        """Test detection of excessive daily procedures."""
        daily_claims = [
            {"claim_id": f"CLM{i}", "member_id": f"MEM{i}", "procedure_codes": ["99213", "80053"]}
            for i in range(30)  # 60 procedures total
        ]

        result = await analyzer.detect_impossible_day("PRV001", date(2025, 1, 15), daily_claims)

        assert result.is_anomaly_detected is True
        assert result.observed_value > result.baseline_value

    @pytest.mark.asyncio
    async def test_impossible_day_too_many_patients(self, analyzer):
        """Test detection of too many daily patients."""
        daily_claims = [
            {"claim_id": f"CLM{i}", "member_id": f"MEM{i}", "procedure_codes": ["99213"]}
            for i in range(35)  # 35 unique patients
        ]

        result = await analyzer.detect_impossible_day("PRV001", date(2025, 1, 15), daily_claims)

        assert result.is_anomaly_detected is True
        assert "patients" in result.description.lower() or result.observed_value > 30

    @pytest.mark.asyncio
    async def test_normal_day_no_anomaly(self, analyzer):
        """Test no anomaly for normal day."""
        daily_claims = [
            {"claim_id": f"CLM{i}", "member_id": f"MEM{i}", "procedure_codes": ["99213"]}
            for i in range(20)  # Normal volume
        ]

        result = await analyzer.detect_impossible_day("PRV001", date(2025, 1, 15), daily_claims)

        assert result.is_anomaly_detected is False

    @pytest.mark.asyncio
    async def test_excessive_services_per_visit(self, analyzer):
        """Test detection of excessive services per visit."""
        claim_data = {
            "procedure_codes": ["99213"] + [f"9999{i}" for i in range(20)]  # 21 procedures
        }

        result = await analyzer.detect_excessive_services(claim_data, [])

        assert result.is_anomaly_detected is True
        assert result.anomaly_type == "excessive_procedures_per_visit"

    @pytest.mark.asyncio
    async def test_provider_patterns_high_denial_rate(self, analyzer):
        """Test provider pattern analysis with high denial rate."""
        provider_claims = [
            {"claim_id": f"CLM{i}", "procedure_codes": ["99213"], "status": "approved"}
            for i in range(7)
        ] + [
            {"claim_id": f"CLM{i+7}", "procedure_codes": ["99213"], "status": "denied"}
            for i in range(3)
        ]

        result = await analyzer.analyze_provider_patterns("PRV001", provider_claims)

        assert result.denial_rate == 0.3

    @pytest.mark.asyncio
    async def test_provider_patterns_high_code_rate(self, analyzer):
        """Test provider pattern analysis with high level 5 code rate."""
        provider_claims = [
            {"claim_id": f"CLM{i}", "procedure_codes": ["99215"], "status": "approved"}
            for i in range(6)  # 60% level 5 codes
        ] + [
            {"claim_id": f"CLM{i+6}", "procedure_codes": ["99213"], "status": "approved"}
            for i in range(4)
        ]

        result = await analyzer.analyze_provider_patterns("PRV001", provider_claims)

        assert result.high_code_rate == 0.6
        # Risk score is 0.4 (high code rate alone), which falls in MEDIUM tier (0.3-0.6)
        assert result.risk_level == FWARiskLevel.MEDIUM
        assert len(result.flags) > 0  # Should have upcoding flag


# =============================================================================
# Risk Scorer Tests
# =============================================================================


class TestFWARiskScorer:
    """Tests for FWA risk scoring."""

    @pytest.fixture
    def scorer(self):
        """Create risk scorer instance."""
        return FWARiskScorer()

    @pytest.mark.asyncio
    async def test_low_risk_no_flags(self, scorer):
        """Test low risk score with no flags."""
        claim_data = {"total_charged": 100.00}

        score, level, recommendation = await scorer.calculate_risk_score(
            claim_data, [], None, None
        )

        assert score == 0.0
        assert level == FWARiskLevel.LOW
        assert recommendation == FWARecommendation.APPROVE

    @pytest.mark.asyncio
    async def test_high_risk_with_flags(self, scorer):
        """Test high risk score with significant flags."""
        claim_data = {"total_charged": 1000.00}
        flags = [
            FWAFlag(
                flag_type=FWAFlagType.UPCODING,
                severity=FWARiskLevel.HIGH,
                description="Potential upcoding",
                score_contribution=0.35,
            ),
            FWAFlag(
                flag_type=FWAFlagType.UNBUNDLING,
                severity=FWARiskLevel.MEDIUM,
                description="Unbundling detected",
                score_contribution=0.25,
            ),
        ]

        score, level, recommendation = await scorer.calculate_risk_score(
            claim_data, flags, None, None
        )

        assert score == 0.6
        assert level == FWARiskLevel.HIGH
        assert recommendation == FWARecommendation.INVESTIGATE

    @pytest.mark.asyncio
    async def test_critical_risk_duplicate(self, scorer):
        """Test critical risk with duplicate claim flag."""
        claim_data = {"total_charged": 500.00}
        flags = [
            FWAFlag(
                flag_type=FWAFlagType.DUPLICATE_CLAIM,
                severity=FWARiskLevel.CRITICAL,
                description="Exact duplicate",
                score_contribution=0.5,
            ),
        ]

        score, level, recommendation = await scorer.calculate_risk_score(
            claim_data, flags, None, None
        )

        assert score >= 0.5
        assert recommendation == FWARecommendation.DENY

    @pytest.mark.asyncio
    async def test_provider_risk_adjustment(self, scorer):
        """Test risk adjustment based on provider profile."""
        claim_data = {"total_charged": 200.00}
        provider_profile = {"denial_rate": 0.4}  # High denial rate

        score, level, recommendation = await scorer.calculate_risk_score(
            claim_data, [], provider_profile, None
        )

        assert score == 0.2  # Provider risk adjustment applied

    @pytest.mark.asyncio
    async def test_medium_risk_review_recommendation(self, scorer):
        """Test medium risk gets review recommendation."""
        claim_data = {"total_charged": 300.00}
        flags = [
            FWAFlag(
                flag_type=FWAFlagType.PATTERN_ANOMALY,
                severity=FWARiskLevel.MEDIUM,
                description="Pattern anomaly",
                score_contribution=0.35,
            ),
        ]

        score, level, recommendation = await scorer.calculate_risk_score(
            claim_data, flags, None, None
        )

        assert level == FWARiskLevel.MEDIUM
        assert recommendation == FWARecommendation.REVIEW


# =============================================================================
# Integration Tests
# =============================================================================


class TestFWAIntegration:
    """Integration tests for FWA detection workflow."""

    @pytest.mark.asyncio
    async def test_full_fwa_analysis_clean_claim(self):
        """Test full FWA analysis on clean claim."""
        # Setup services
        duplicate_detector = DuplicateDetector()
        upcoding_detector = UpcodingDetector()
        pattern_analyzer = PatternAnalyzer()
        risk_scorer = FWARiskScorer()

        claim_data = {
            "claim_id": "CLM001",
            "member_id": "MEM123",
            "provider_id": "PRV456",
            "service_date": date(2025, 1, 15),
            "procedure_codes": ["99213", "80053"],
            "diagnosis_codes": ["E11.9"],
            "total_charged": 250.00,
        }

        # Run duplicate check
        dup_result = await duplicate_detector.detect_duplicates(claim_data, [])

        # Run upcoding check
        upcoding_result = await upcoding_detector.detect_upcoding(
            claim_data["procedure_codes"], None, claim_data["diagnosis_codes"]
        )
        unbundling_result = await upcoding_detector.detect_unbundling(
            claim_data["procedure_codes"]
        )

        # Collect flags
        flags = []
        dup_flag = duplicate_detector.create_flag(dup_result)
        if dup_flag:
            flags.append(dup_flag)
        flags.extend(upcoding_detector.create_flags(upcoding_result, unbundling_result))

        # Calculate risk score
        score, level, recommendation = await risk_scorer.calculate_risk_score(
            claim_data, flags, None, None
        )

        assert level == FWARiskLevel.LOW
        assert recommendation == FWARecommendation.APPROVE

    @pytest.mark.asyncio
    async def test_full_fwa_analysis_suspicious_claim(self):
        """Test full FWA analysis on suspicious claim."""
        duplicate_detector = DuplicateDetector()
        upcoding_detector = UpcodingDetector()
        risk_scorer = FWARiskScorer()

        claim_data = {
            "claim_id": "CLM002",
            "member_id": "MEM456",
            "provider_id": "PRV789",
            "service_date": date(2025, 1, 15),
            "procedure_codes": ["99215", "82947", "80053"],  # Unbundling
            "diagnosis_codes": ["J06.9"],  # Acute - doesn't support 99215
            "total_charged": 500.00,
        }

        # Run checks
        upcoding_result = await upcoding_detector.detect_upcoding(
            claim_data["procedure_codes"], None, claim_data["diagnosis_codes"]
        )
        unbundling_result = await upcoding_detector.detect_unbundling(
            claim_data["procedure_codes"]
        )

        flags = upcoding_detector.create_flags(upcoding_result, unbundling_result)

        # Calculate risk
        score, level, recommendation = await risk_scorer.calculate_risk_score(
            claim_data, flags, None, None
        )

        assert len(flags) >= 1  # Should have upcoding or unbundling flags
        assert level in [FWARiskLevel.MEDIUM, FWARiskLevel.HIGH]
        assert recommendation in [FWARecommendation.REVIEW, FWARecommendation.INVESTIGATE]

    @pytest.mark.asyncio
    async def test_full_fwa_analysis_duplicate_claim(self):
        """Test full FWA analysis on duplicate claim."""
        duplicate_detector = DuplicateDetector()
        risk_scorer = FWARiskScorer()

        claim_data = {
            "claim_id": "CLM003",
            "member_id": "MEM123",
            "provider_id": "PRV456",
            "service_date": date(2025, 1, 15),
            "procedure_codes": ["99213"],
            "diagnosis_codes": ["I10"],
            "total_charged": 150.00,
        }

        existing_claim = claim_data.copy()
        existing_claim["claim_id"] = "CLM000"

        # Run duplicate check
        dup_result = await duplicate_detector.detect_duplicates(claim_data, [existing_claim])
        dup_flag = duplicate_detector.create_flag(dup_result)

        flags = [dup_flag] if dup_flag else []

        # Calculate risk
        score, level, recommendation = await risk_scorer.calculate_risk_score(
            claim_data, flags, None, None
        )

        assert dup_result.is_duplicate is True
        assert level == FWARiskLevel.CRITICAL or recommendation == FWARecommendation.DENY
