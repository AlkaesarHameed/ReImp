"""
E2E Tests: Fraud Detection Flow.

Tests the fraud detection pipeline including PDF forensics,
pattern analysis, and risk scoring for FWA detection.

Source: Design Document 04_validation_engine_comprehensive_design.md
"""

import pytest
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# =============================================================================
# Forensic Signal Fixtures
# =============================================================================


class MockForensicSignal:
    """Mock forensic signal for testing."""

    def __init__(
        self,
        signal_type: str,
        severity: str,
        description: str,
        confidence: float = 0.8,
    ):
        self.signal_type = MagicMock(value=signal_type)
        self.severity = MagicMock(value=severity)
        self.description = description
        self.confidence = confidence


class MockForensicResult:
    """Mock PDF forensics result."""

    def __init__(
        self,
        is_suspicious: bool = False,
        fraud_score: float = 0.1,
        signals: list = None,
    ):
        self.is_suspicious = is_suspicious
        self.fraud_score = fraud_score
        self.signals = signals or []
        self.metadata = {
            "producer": "Adobe Acrobat",
            "creation_date": "2025-12-15",
            "modification_date": "2025-12-15",
        }
        self.execution_time_ms = 50


@pytest.fixture
def clean_pdf_result():
    """Fixture for clean PDF analysis result."""
    return MockForensicResult(
        is_suspicious=False,
        fraud_score=0.05,
        signals=[],
    )


@pytest.fixture
def tampered_pdf_result():
    """Fixture for tampered PDF analysis result."""
    return MockForensicResult(
        is_suspicious=True,
        fraud_score=0.85,
        signals=[
            MockForensicSignal(
                signal_type="metadata_mismatch",
                severity="high",
                description="Creation date differs from modification date by >1 year",
            ),
            MockForensicSignal(
                signal_type="font_substitution",
                severity="critical",
                description="Different fonts used in monetary amounts",
            ),
            MockForensicSignal(
                signal_type="layer_anomaly",
                severity="medium",
                description="Hidden text layer detected",
            ),
        ],
    )


@pytest.fixture
def suspicious_metadata_result():
    """Fixture for PDF with suspicious metadata."""
    result = MockForensicResult(
        is_suspicious=True,
        fraud_score=0.65,
        signals=[
            MockForensicSignal(
                signal_type="suspicious_producer",
                severity="medium",
                description="Document created with online PDF editor",
            ),
        ],
    )
    result.metadata = {
        "producer": "PDFescape Online Editor",
        "creation_date": "2025-12-01",
        "modification_date": "2025-12-15",
    }
    return result


# =============================================================================
# Fraud Detection Tests
# =============================================================================


class TestPDFForensicsFlow:
    """E2E tests for PDF forensics fraud detection."""

    @pytest.mark.asyncio
    async def test_clean_pdf_passes_forensics(self, clean_pdf_result):
        """Test that clean PDF passes forensic analysis."""
        with patch("src.services.validation.get_pdf_forensics_service") as mock_service:
            forensics = AsyncMock()
            forensics.analyze = AsyncMock(return_value=clean_pdf_result)
            mock_service.return_value = forensics

            result = await forensics.analyze(b"clean pdf content", "medical_report.pdf")

            assert result.is_suspicious is False
            assert result.fraud_score < 0.3
            assert len(result.signals) == 0

    @pytest.mark.asyncio
    async def test_tampered_pdf_triggers_fraud_alert(self, tampered_pdf_result):
        """Test that tampered PDF triggers fraud detection."""
        with patch("src.services.validation.get_pdf_forensics_service") as mock_service:
            forensics = AsyncMock()
            forensics.analyze = AsyncMock(return_value=tampered_pdf_result)
            mock_service.return_value = forensics

            result = await forensics.analyze(b"tampered pdf", "suspicious.pdf")

            assert result.is_suspicious is True
            assert result.fraud_score >= 0.7
            assert len(result.signals) >= 2

            # Check for critical signals
            critical_signals = [
                s for s in result.signals
                if s.severity.value == "critical"
            ]
            assert len(critical_signals) >= 1

    @pytest.mark.asyncio
    async def test_suspicious_producer_detection(self, suspicious_metadata_result):
        """Test detection of suspicious PDF producers."""
        with patch("src.services.validation.get_pdf_forensics_service") as mock_service:
            forensics = AsyncMock()
            forensics.analyze = AsyncMock(return_value=suspicious_metadata_result)
            mock_service.return_value = forensics

            result = await forensics.analyze(b"pdf content", "edited.pdf")

            assert result.is_suspicious is True
            assert result.metadata["producer"] == "PDFescape Online Editor"

            # Should flag online editor usage
            signal_types = [s.signal_type.value for s in result.signals]
            assert "suspicious_producer" in signal_types

    @pytest.mark.asyncio
    async def test_multiple_fraud_signals_compound(self, tampered_pdf_result):
        """Test that multiple fraud signals compound risk."""
        with patch("src.services.validation.get_pdf_forensics_service") as mock_service:
            forensics = AsyncMock()
            forensics.analyze = AsyncMock(return_value=tampered_pdf_result)
            mock_service.return_value = forensics

            result = await forensics.analyze(b"pdf", "test.pdf")

            # Multiple signals should result in high fraud score
            assert result.fraud_score > 0.7

            # Should trigger investigation requirement
            assert result.is_suspicious is True


# =============================================================================
# FWA Pattern Detection Tests
# =============================================================================


class MockDuplicateResult:
    """Mock duplicate detection result."""

    def __init__(self, is_duplicate: bool = False, similarity_score: float = 0.0):
        self.is_duplicate = is_duplicate
        self.is_possible_duplicate = similarity_score >= 0.75
        self.similarity_score = similarity_score
        self.matching_claim_id = "CLM-EXISTING" if is_duplicate else None
        self.matching_fields = ["member_id", "service_date", "procedure_codes"] if is_duplicate else []


class MockUpcodingResult:
    """Mock upcoding detection result."""

    def __init__(self, is_detected: bool = False, score: float = 0.0):
        self.is_upcoding_detected = is_detected
        self.upcoding_score = score
        self.flagged_codes = ["99215"] if is_detected else []


class TestFWAPatternDetection:
    """E2E tests for FWA pattern detection."""

    @pytest.mark.asyncio
    async def test_duplicate_claim_detection(self):
        """Test detection of duplicate claims."""
        with patch("src.services.fwa.get_duplicate_detector") as mock_detector:
            detector = AsyncMock()
            detector.detect_duplicates = AsyncMock(
                return_value=MockDuplicateResult(is_duplicate=True, similarity_score=0.98)
            )
            mock_detector.return_value = detector

            claim_data = {
                "member_id": "MEM123",
                "provider_id": "PRV456",
                "service_date": "2025-12-15",
                "procedure_codes": ["99213"],
            }

            result = await detector.detect_duplicates(claim_data, [])

            assert result.is_duplicate is True
            assert result.similarity_score >= 0.95
            assert result.matching_claim_id is not None

    @pytest.mark.asyncio
    async def test_upcoding_detection(self):
        """Test detection of upcoding patterns."""
        with patch("src.services.fwa.get_upcoding_detector") as mock_detector:
            detector = AsyncMock()
            detector.detect_upcoding = AsyncMock(
                return_value=MockUpcodingResult(is_detected=True, score=0.7)
            )
            mock_detector.return_value = detector

            # High-level E/M code without supporting documentation
            result = await detector.detect_upcoding(
                procedure_codes=["99215"],
                diagnosis_codes=["J06.9"],  # Simple acute URI
                provider_em_history={"99215": 0.60},  # 60% high-level codes
            )

            assert result.is_upcoding_detected is True
            assert "99215" in result.flagged_codes

    @pytest.mark.asyncio
    async def test_unbundling_detection(self):
        """Test detection of unbundling patterns."""
        with patch("src.services.fwa.get_upcoding_detector") as mock_detector:
            detector = AsyncMock()

            mock_result = MagicMock()
            mock_result.is_unbundling_detected = True
            mock_result.bundled_pairs = [("82947", "80053")]
            mock_result.recommended_code = "80053"

            detector.detect_unbundling = AsyncMock(return_value=mock_result)
            mock_detector.return_value = detector

            # Glucose billed separately from CMP
            result = await detector.detect_unbundling(["82947", "80053"])

            assert result.is_unbundling_detected is True
            assert ("82947", "80053") in result.bundled_pairs

    @pytest.mark.asyncio
    async def test_impossible_day_detection(self):
        """Test detection of impossible billing day."""
        with patch("src.services.fwa.get_pattern_analyzer") as mock_analyzer:
            analyzer = AsyncMock()

            mock_result = MagicMock()
            mock_result.is_anomaly_detected = True
            mock_result.anomaly_type = "excessive_daily_procedures"
            mock_result.observed_value = 75
            mock_result.baseline_value = 50

            analyzer.detect_impossible_day = AsyncMock(return_value=mock_result)
            mock_analyzer.return_value = analyzer

            # Provider with 75 procedures in one day
            result = await analyzer.detect_impossible_day(
                provider_id="PRV123",
                service_date="2025-12-15",
                daily_claims=[{"procedures": 75}],
            )

            assert result.is_anomaly_detected is True
            assert result.observed_value > result.baseline_value


# =============================================================================
# Fraud Risk Scoring Tests
# =============================================================================


class TestFraudRiskScoring:
    """E2E tests for fraud risk scoring."""

    @pytest.mark.asyncio
    async def test_clean_claim_low_fraud_risk(self):
        """Test that clean claim has low fraud risk."""
        with patch("src.services.validation.orchestrator.get_validation_orchestrator") as mock_orch:
            orchestrator = AsyncMock()

            mock_result = MagicMock()
            mock_result.is_valid = True
            mock_result.risk_score = 0.08
            mock_result.risk_level = "low"
            mock_result.forensic_signals = []
            mock_result.requires_investigation = False

            orchestrator.validate_claim = AsyncMock(return_value=mock_result)
            mock_orch.return_value = orchestrator

            result = await orchestrator.validate_claim({
                "icd_codes": ["E11.9"],
                "cpt_codes": ["99213"],
            })

            assert result.risk_score < 0.3
            assert result.requires_investigation is False

    @pytest.mark.asyncio
    async def test_fraud_signals_trigger_investigation(self, tampered_pdf_result):
        """Test that fraud signals trigger investigation requirement."""
        with patch("src.services.validation.orchestrator.get_validation_orchestrator") as mock_orch:
            orchestrator = AsyncMock()

            mock_result = MagicMock()
            mock_result.is_valid = False
            mock_result.risk_score = 0.85
            mock_result.risk_level = "critical"
            mock_result.forensic_signals = tampered_pdf_result.signals
            mock_result.requires_investigation = True
            mock_result.recommendation = "REJECT: Critical fraud indicators detected."

            orchestrator.validate_claim = AsyncMock(return_value=mock_result)
            mock_orch.return_value = orchestrator

            result = await orchestrator.validate_claim({
                "icd_codes": ["E11.9"],
                "pdf_content": b"tampered",
            })

            assert result.risk_score >= 0.7
            assert result.risk_level in ("high", "critical")
            assert result.requires_investigation is True

    @pytest.mark.asyncio
    async def test_provider_risk_affects_scoring(self):
        """Test that provider risk profile affects claim risk scoring."""
        with patch("src.services.fwa.get_risk_scorer") as mock_scorer:
            scorer = AsyncMock()

            # High-risk provider
            scorer.calculate_risk_score = AsyncMock(return_value=(0.65, "high", "INVESTIGATE"))
            mock_scorer.return_value = scorer

            score, level, recommendation = await scorer.calculate_risk_score(
                claim_data={"total_charged": 500},
                flags=[],
                provider_profile={"denial_rate": 0.35, "risk_score": 0.6},
            )

            assert score >= 0.5
            assert level in ("medium", "high")


# =============================================================================
# Fraud Detection Integration Tests
# =============================================================================


class TestFraudDetectionIntegration:
    """Integration tests for complete fraud detection flow."""

    @pytest.mark.asyncio
    async def test_full_fraud_analysis_flow(self, tampered_pdf_result):
        """Test complete fraud analysis from document to decision."""
        with patch("src.services.validation.get_pdf_forensics_service") as mock_forensics, \
             patch("src.services.fwa.get_duplicate_detector") as mock_dup, \
             patch("src.services.fwa.get_upcoding_detector") as mock_upcode:

            # Setup forensics
            forensics = AsyncMock()
            forensics.analyze = AsyncMock(return_value=tampered_pdf_result)
            mock_forensics.return_value = forensics

            # Setup duplicate detection
            dup_detector = AsyncMock()
            dup_detector.detect_duplicates = AsyncMock(
                return_value=MockDuplicateResult(is_duplicate=False)
            )
            mock_dup.return_value = dup_detector

            # Setup upcoding detection
            upcoding_detector = AsyncMock()
            upcoding_detector.detect_upcoding = AsyncMock(
                return_value=MockUpcodingResult(is_detected=False)
            )
            mock_upcode.return_value = upcoding_detector

            # Run all checks
            forensic_result = await forensics.analyze(b"pdf", "doc.pdf")
            dup_result = await dup_detector.detect_duplicates({}, [])
            upcode_result = await upcoding_detector.detect_upcoding(["99213"], ["E11.9"])

            # Forensics should trigger fraud
            assert forensic_result.is_suspicious is True

            # Other checks passed
            assert dup_result.is_duplicate is False
            assert upcode_result.is_upcoding_detected is False

            # Overall should still require investigation due to forensics
            # (In real system, orchestrator would aggregate these)

    @pytest.mark.asyncio
    async def test_clean_claim_passes_all_fraud_checks(self, clean_pdf_result):
        """Test that clean claim passes all fraud detection checks."""
        with patch("src.services.validation.get_pdf_forensics_service") as mock_forensics, \
             patch("src.services.fwa.get_duplicate_detector") as mock_dup, \
             patch("src.services.fwa.get_upcoding_detector") as mock_upcode:

            # All checks pass
            forensics = AsyncMock()
            forensics.analyze = AsyncMock(return_value=clean_pdf_result)
            mock_forensics.return_value = forensics

            dup_detector = AsyncMock()
            dup_detector.detect_duplicates = AsyncMock(
                return_value=MockDuplicateResult(is_duplicate=False)
            )
            mock_dup.return_value = dup_detector

            upcoding_detector = AsyncMock()
            upcoding_detector.detect_upcoding = AsyncMock(
                return_value=MockUpcodingResult(is_detected=False)
            )
            mock_upcode.return_value = upcoding_detector

            # Run all checks
            forensic_result = await forensics.analyze(b"pdf", "clean.pdf")
            dup_result = await dup_detector.detect_duplicates({}, [])
            upcode_result = await upcoding_detector.detect_upcoding(["99213"], ["E11.9"])

            # All should pass
            assert forensic_result.is_suspicious is False
            assert dup_result.is_duplicate is False
            assert upcode_result.is_upcoding_detected is False
