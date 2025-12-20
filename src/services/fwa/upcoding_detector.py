"""
Upcoding Detection Service.
Source: Design Document Section 4.2 - Fraud Detection
Verified: 2025-12-18

Detects upcoding - billing for more expensive services than provided.
"""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from src.schemas.fwa import (
    FWAFlag,
    FWAFlagType,
    FWARiskLevel,
    UnbundlingFlag,
    UpcodingFlag,
)


class UpcodingDetector:
    """
    Detects upcoding and unbundling in claims.

    Upcoding: Billing for higher-level service than provided
    Unbundling: Billing separately for bundled services
    """

    # E/M code hierarchies (lower to higher)
    EM_HIERARCHIES = {
        "established_patient": ["99211", "99212", "99213", "99214", "99215"],
        "new_patient": ["99201", "99202", "99203", "99204", "99205"],
        "er_visit": ["99281", "99282", "99283", "99284", "99285"],
        "hospital_inpatient": ["99221", "99222", "99223"],
    }

    # Expected distribution of E/M codes (percentage at each level)
    EXPECTED_EM_DISTRIBUTION = {
        "established_patient": {
            "99211": 0.02,  # 2%
            "99212": 0.08,  # 8%
            "99213": 0.45,  # 45%
            "99214": 0.35,  # 35%
            "99215": 0.10,  # 10%
        },
        "new_patient": {
            "99201": 0.02,
            "99202": 0.10,
            "99203": 0.40,
            "99204": 0.35,
            "99205": 0.13,
        },
    }

    # Bundled procedures (component -> bundle)
    BUNDLED_PROCEDURES = {
        # Lab panels
        "82947": "80053",  # Glucose bundled into CMP
        "82565": "80053",  # Creatinine bundled into CMP
        "82374": "80053",  # CO2 bundled into CMP
        "84443": "80053",  # TSH bundled into CMP
        "82465": "80061",  # Cholesterol bundled into lipid panel

        # Surgical
        "99213": "10060",  # E/M bundled into I&D
        "99214": "10060",  # E/M bundled into I&D
    }

    # High-value procedures that require extra scrutiny
    HIGH_VALUE_PROCEDURES = {
        "99215": "Highest-level established E/M",
        "99205": "Highest-level new patient E/M",
        "99285": "Highest-level ER visit",
        "99223": "Highest-level hospital admit",
        "27447": "Total knee replacement",
        "27130": "Total hip replacement",
    }

    def __init__(self):
        """Initialize UpcodingDetector."""
        pass

    async def detect_upcoding(
        self,
        procedure_codes: list[str],
        provider_em_history: Optional[dict] = None,
        diagnosis_codes: Optional[list[str]] = None,
    ) -> UpcodingFlag:
        """
        Detect upcoding in procedure codes.

        Args:
            procedure_codes: List of procedure codes on claim
            provider_em_history: Provider's historical E/M distribution
            diagnosis_codes: Diagnosis codes for severity validation

        Returns:
            UpcodingFlag with detection results
        """
        result = UpcodingFlag()

        # Check for high-level E/M codes
        high_em_codes = self._find_high_level_em(procedure_codes)
        if high_em_codes:
            # Check if provider over-uses high-level codes
            if provider_em_history:
                for category, codes in self.EM_HIERARCHIES.items():
                    if category in self.EXPECTED_EM_DISTRIBUTION:
                        expected = self.EXPECTED_EM_DISTRIBUTION[category]
                        for code in high_em_codes:
                            if code in expected:
                                provider_rate = provider_em_history.get(code, 0)
                                expected_rate = expected[code]

                                # Flag if provider rate is 2x+ expected
                                if provider_rate > expected_rate * 2:
                                    result.is_upcoding_detected = True
                                    result.suspected_codes.append(code)
                                    result.evidence.append(
                                        f"{code} used at {provider_rate:.1%} "
                                        f"vs expected {expected_rate:.1%}"
                                    )
                                    result.upcoding_score = max(
                                        result.upcoding_score,
                                        min(1.0, provider_rate / expected_rate - 1),
                                    )

            # Check diagnosis severity
            if diagnosis_codes:
                severity_check = self._check_diagnosis_severity(
                    high_em_codes, diagnosis_codes
                )
                if not severity_check["supports_high_level"]:
                    result.is_upcoding_detected = True
                    result.suspected_codes.extend(high_em_codes)
                    result.suggested_codes.extend(severity_check.get("suggested", []))
                    result.evidence.append(severity_check.get("reason", ""))

        return result

    async def detect_unbundling(
        self,
        procedure_codes: list[str],
    ) -> UnbundlingFlag:
        """
        Detect unbundling in procedure codes.

        Args:
            procedure_codes: List of procedure codes on claim

        Returns:
            UnbundlingFlag with detection results
        """
        result = UnbundlingFlag()

        code_set = set(procedure_codes)

        # Check for unbundled components
        for component, bundle in self.BUNDLED_PROCEDURES.items():
            if component in code_set and bundle in code_set:
                result.is_unbundling_detected = True
                result.unbundled_codes.append((component, bundle))
                result.bundled_code = bundle
                result.unbundling_score = max(result.unbundling_score, 0.5)

        # Check for multiple components without bundle
        component_count = sum(
            1 for code in code_set if code in self.BUNDLED_PROCEDURES
        )
        if component_count >= 3:
            # Multiple components billed separately
            result.is_unbundling_detected = True
            result.unbundling_score = max(result.unbundling_score, 0.3)

        return result

    async def analyze_em_distribution(
        self,
        provider_claims: list[dict],
    ) -> dict:
        """
        Analyze provider's E/M code distribution.

        Args:
            provider_claims: List of provider's claims

        Returns:
            Distribution analysis with anomaly indicators
        """
        result = {
            "distribution": {},
            "anomalies": [],
            "overall_score": 0.0,
        }

        if not provider_claims:
            return result

        # Count E/M codes
        em_counts = {}
        total_em = 0

        for claim in provider_claims:
            for code in claim.get("procedure_codes", []):
                for category, codes in self.EM_HIERARCHIES.items():
                    if code in codes:
                        em_counts[code] = em_counts.get(code, 0) + 1
                        total_em += 1

        if total_em == 0:
            return result

        # Calculate distribution
        for code, count in em_counts.items():
            result["distribution"][code] = count / total_em

        # Compare to expected
        for category, expected in self.EXPECTED_EM_DISTRIBUTION.items():
            for code, expected_rate in expected.items():
                actual_rate = result["distribution"].get(code, 0)

                # Flag if significantly different
                if actual_rate > expected_rate * 2:
                    result["anomalies"].append({
                        "code": code,
                        "actual_rate": actual_rate,
                        "expected_rate": expected_rate,
                        "ratio": actual_rate / expected_rate if expected_rate > 0 else 0,
                    })

        # Calculate overall score
        if result["anomalies"]:
            max_ratio = max(a["ratio"] for a in result["anomalies"])
            result["overall_score"] = min(1.0, (max_ratio - 1) / 2)

        return result

    def _find_high_level_em(self, procedure_codes: list[str]) -> list[str]:
        """Find high-level E/M codes in procedure list."""
        high_level_codes = []

        for code in procedure_codes:
            if code in self.HIGH_VALUE_PROCEDURES:
                high_level_codes.append(code)
            elif code in ["99214", "99215", "99204", "99205"]:
                high_level_codes.append(code)

        return high_level_codes

    def _check_diagnosis_severity(
        self,
        em_codes: list[str],
        diagnosis_codes: list[str],
    ) -> dict:
        """Check if diagnoses support high-level E/M."""
        result = {
            "supports_high_level": True,
            "suggested": [],
            "reason": "",
        }

        # Simple severity check based on diagnosis chapter
        # In production, use more sophisticated clinical rules

        # Low-complexity diagnoses
        low_complexity = {"J06.9", "J00", "B34.9", "R05"}  # URI, cold, viral, cough

        # Check if any high-level E/M with low-complexity diagnosis
        has_high_em = any(code in ["99215", "99205", "99285"] for code in em_codes)
        has_low_dx = any(dx in low_complexity for dx in diagnosis_codes)

        if has_high_em and has_low_dx:
            result["supports_high_level"] = False
            result["suggested"] = ["99213", "99203"]  # Lower-level alternatives
            result["reason"] = "Low-complexity diagnosis does not support high-level E/M"

        return result

    def create_flags(
        self,
        upcoding_result: UpcodingFlag,
        unbundling_result: UnbundlingFlag,
    ) -> list[FWAFlag]:
        """Create FWA flags from detection results."""
        flags = []

        if upcoding_result.is_upcoding_detected:
            flags.append(
                FWAFlag(
                    flag_type=FWAFlagType.UPCODING,
                    severity=FWARiskLevel.HIGH if upcoding_result.upcoding_score > 0.5 else FWARiskLevel.MEDIUM,
                    description=f"Suspected upcoding: {', '.join(upcoding_result.suspected_codes)}",
                    score_contribution=min(0.4, upcoding_result.upcoding_score * 0.5),
                    evidence={
                        "suspected_codes": upcoding_result.suspected_codes,
                        "suggested_codes": upcoding_result.suggested_codes,
                        "evidence": upcoding_result.evidence,
                    },
                    rule_id="UPC001",
                )
            )

        if unbundling_result.is_unbundling_detected:
            flags.append(
                FWAFlag(
                    flag_type=FWAFlagType.UNBUNDLING,
                    severity=FWARiskLevel.MEDIUM,
                    description=f"Suspected unbundling of procedures",
                    score_contribution=min(0.3, unbundling_result.unbundling_score * 0.4),
                    evidence={
                        "unbundled_codes": [
                            {"component": c, "bundle": b}
                            for c, b in unbundling_result.unbundled_codes
                        ],
                    },
                    rule_id="UNB001",
                )
            )

        return flags


# =============================================================================
# Factory Functions
# =============================================================================


_upcoding_detector: Optional[UpcodingDetector] = None


def get_upcoding_detector() -> UpcodingDetector:
    """Get singleton UpcodingDetector instance."""
    global _upcoding_detector
    if _upcoding_detector is None:
        _upcoding_detector = UpcodingDetector()
    return _upcoding_detector
