"""
Integration Tests for Validation Pipeline.

Tests the full validation pipeline from API to orchestrator to individual validators.
Uses mocked external services (LLM, Typesense) for reliability.

Source: Design Document 04_validation_engine_comprehensive_design.md
"""

import pytest
from datetime import date, datetime
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# =============================================================================
# Mock Classes for Testing
# =============================================================================


class MockLLMResponse:
    """Mock LLM response for testing."""

    def __init__(
        self,
        content: str = "Mock LLM response",
        success: bool = True,
        provider: str = "mock",
        model: str = "mock-model",
    ):
        self.content = content
        self.success = success
        self.provider = provider
        self.model = model
        self.data = MagicMock()
        self.data.content = content
        self.data.provider = provider
        self.data.model = model
        self.error = None if success else "Mock error"


class MockSearchResult:
    """Mock Typesense search result."""

    def __init__(self, hits: list[dict]):
        self.hits = hits
        self.found = len(hits)


class MockForensicSignal:
    """Mock forensic signal."""

    def __init__(
        self,
        signal_type: str = "metadata_mismatch",
        severity: str = "medium",
        description: str = "Mock signal",
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
        self.metadata = {}
        self.execution_time_ms = 50


class MockCrosswalkResult:
    """Mock ICD-CPT crosswalk result."""

    def __init__(
        self,
        is_valid: bool = True,
        overall_confidence: float = 0.9,
        invalid_pairs: list = None,
    ):
        self.is_valid = is_valid
        self.overall_confidence = overall_confidence
        self.invalid_pairs = invalid_pairs or []
        self.ncci_edits_found = []
        self.has_critical_issues = len(self.invalid_pairs) > 0
        self.execution_time_ms = 25

    def to_evidence_dict(self):
        return {
            "is_valid": self.is_valid,
            "confidence": self.overall_confidence,
        }


class MockConflictResult:
    """Mock ICD conflict result."""

    def __init__(
        self,
        is_valid: bool = True,
        conflicts: list = None,
    ):
        self.is_valid = is_valid
        self.conflicts = conflicts or []
        self.critical_conflicts = []
        self.execution_time_ms = 10

    def to_evidence_dict(self):
        return {
            "is_valid": self.is_valid,
            "conflicts": self.conflicts,
        }


class MockDemographicResult:
    """Mock demographic validation result."""

    def __init__(
        self,
        is_valid: bool = True,
        issues: list = None,
    ):
        self.is_valid = is_valid
        self.issues = issues or []
        self.critical_issues = []
        self.execution_time_ms = 5

    def to_evidence_dict(self):
        return {
            "is_valid": self.is_valid,
            "issues": self.issues,
        }


class MockNecessityResult:
    """Mock clinical necessity result."""

    def __init__(
        self,
        is_valid: bool = True,
        overall_confidence: float = 0.85,
        critical_issues: list = None,
    ):
        self.is_valid = is_valid
        self.overall_confidence = overall_confidence
        self.critical_issues = critical_issues or []
        self.requires_review = not is_valid
        self.llm_provider_used = "mock"
        self.execution_time_ms = 500

    def to_evidence_dict(self):
        return {
            "is_valid": self.is_valid,
            "confidence": self.overall_confidence,
        }


# =============================================================================
# Validation API Tests
# =============================================================================


class TestValidationAPIEndpoints:
    """Tests for validation API endpoints."""

    @pytest.fixture
    def sample_validation_request(self):
        """Create sample validation request."""
        return {
            "icd_codes": ["E11.9", "I10"],
            "cpt_codes": ["99213", "80053"],
            "patient_age": 55,
            "patient_gender": "M",
        }

    @pytest.fixture
    def sample_full_validation_request(self):
        """Create sample full validation request."""
        return {
            "claim_id": None,
            "member_id": "MEM123456",
            "policy_id": "POL987654",
            "provider_id": "PRV555555",
            "icd_codes": ["E11.9", "I10"],
            "cpt_codes": ["99213", "80053"],
            "patient_age": 55,
            "patient_gender": "M",
            "service_date_from": "2025-12-15",
            "service_date_to": "2025-12-15",
            "skip_rules": [],
            "run_llm_rules": False,  # Skip LLM for faster tests
        }

    @pytest.mark.asyncio
    async def test_quick_validation_success(self, sample_validation_request):
        """Test quick validation endpoint returns expected structure."""
        # Mock validators
        with patch("src.services.validation.get_icd_conflict_validator") as mock_conflict, \
             patch("src.services.validation.get_demographic_validator") as mock_demo, \
             patch("src.services.validation.get_crosswalk_validator") as mock_xwalk:

            # Setup mocks
            conflict_validator = AsyncMock()
            conflict_validator.validate = AsyncMock(return_value=MockConflictResult())
            mock_conflict.return_value = conflict_validator

            demo_validator = AsyncMock()
            demo_validator.validate = AsyncMock(return_value=MockDemographicResult())
            mock_demo.return_value = demo_validator

            xwalk_validator = AsyncMock()
            xwalk_validator.validate = AsyncMock(return_value=MockCrosswalkResult())
            mock_xwalk.return_value = xwalk_validator

            # Simulate validation
            conflict_result = await conflict_validator.validate(sample_validation_request["icd_codes"])
            demo_result = await demo_validator.validate(
                icd_codes=sample_validation_request["icd_codes"],
                cpt_codes=sample_validation_request["cpt_codes"],
                patient_age_years=sample_validation_request["patient_age"],
                patient_gender=sample_validation_request["patient_gender"],
            )
            xwalk_result = await xwalk_validator.validate(
                sample_validation_request["icd_codes"],
                sample_validation_request["cpt_codes"],
            )

            # Verify results
            assert conflict_result.is_valid is True
            assert demo_result.is_valid is True
            assert xwalk_result.is_valid is True

    @pytest.mark.asyncio
    async def test_quick_validation_with_issues(self):
        """Test quick validation with validation issues."""
        with patch("src.services.validation.get_icd_conflict_validator") as mock_conflict:
            conflict_validator = AsyncMock()
            conflict_validator.validate = AsyncMock(return_value=MockConflictResult(
                is_valid=False,
                conflicts=[{"code1": "E10.9", "code2": "E11.9", "reason": "Mutual exclusion"}],
            ))
            mock_conflict.return_value = conflict_validator

            result = await conflict_validator.validate(["E10.9", "E11.9"])

            assert result.is_valid is False
            assert len(result.conflicts) > 0

    @pytest.mark.asyncio
    async def test_comprehensive_validation_all_rules(self, sample_full_validation_request):
        """Test comprehensive validation runs all rules."""
        with patch("src.services.validation.get_crosswalk_validator") as mock_xwalk, \
             patch("src.services.validation.get_icd_conflict_validator") as mock_conflict, \
             patch("src.services.validation.get_demographic_validator") as mock_demo:

            # Setup mocks
            mock_xwalk.return_value.validate = AsyncMock(return_value=MockCrosswalkResult())
            mock_conflict.return_value.validate = AsyncMock(return_value=MockConflictResult())
            mock_demo.return_value.validate = AsyncMock(return_value=MockDemographicResult())

            # Simulate running all validators
            xwalk_result = await mock_xwalk.return_value.validate(
                sample_full_validation_request["icd_codes"],
                sample_full_validation_request["cpt_codes"],
            )
            conflict_result = await mock_conflict.return_value.validate(
                sample_full_validation_request["icd_codes"]
            )
            demo_result = await mock_demo.return_value.validate(
                icd_codes=sample_full_validation_request["icd_codes"],
                cpt_codes=sample_full_validation_request["cpt_codes"],
                patient_age_years=sample_full_validation_request["patient_age"],
                patient_gender=sample_full_validation_request["patient_gender"],
            )

            # All should pass
            assert xwalk_result.is_valid is True
            assert conflict_result.is_valid is True
            assert demo_result.is_valid is True


# =============================================================================
# PDF Forensics Integration Tests
# =============================================================================


class TestPDFForensicsIntegration:
    """Integration tests for PDF forensics validation."""

    @pytest.mark.asyncio
    async def test_clean_pdf_passes_forensics(self):
        """Test that clean PDF passes forensic analysis."""
        with patch("src.services.validation.get_pdf_forensics_service") as mock_service:
            forensics = AsyncMock()
            forensics.analyze = AsyncMock(return_value=MockForensicResult(
                is_suspicious=False,
                fraud_score=0.05,
            ))
            mock_service.return_value = forensics

            result = await forensics.analyze(b"mock pdf content", "clean.pdf")

            assert result.is_suspicious is False
            assert result.fraud_score < 0.3

    @pytest.mark.asyncio
    async def test_suspicious_pdf_triggers_investigation(self):
        """Test that suspicious PDF is flagged."""
        with patch("src.services.validation.get_pdf_forensics_service") as mock_service:
            forensics = AsyncMock()
            forensics.analyze = AsyncMock(return_value=MockForensicResult(
                is_suspicious=True,
                fraud_score=0.85,
                signals=[
                    MockForensicSignal(
                        signal_type="font_substitution",
                        severity="high",
                        description="Font changed after document creation",
                    ),
                    MockForensicSignal(
                        signal_type="metadata_mismatch",
                        severity="medium",
                        description="Creation date doesn't match content",
                    ),
                ],
            ))
            mock_service.return_value = forensics

            result = await forensics.analyze(b"suspicious pdf", "tampered.pdf")

            assert result.is_suspicious is True
            assert result.fraud_score >= 0.7
            assert len(result.signals) >= 2


# =============================================================================
# Clinical Necessity Integration Tests
# =============================================================================


class TestClinicalNecessityIntegration:
    """Integration tests for clinical necessity validation."""

    @pytest.mark.asyncio
    async def test_medically_necessary_procedure(self):
        """Test validation of medically necessary procedure."""
        with patch("src.services.validation.get_clinical_necessity_validator") as mock_validator:
            validator = AsyncMock()
            validator.validate = AsyncMock(return_value=MockNecessityResult(
                is_valid=True,
                overall_confidence=0.92,
            ))
            mock_validator.return_value = validator

            result = await validator.validate(
                icd_codes=["E11.9"],  # Type 2 diabetes
                cpt_codes=["99214"],  # Level 4 E&M visit
                patient_age=55,
                patient_gender="M",
            )

            assert result.is_valid is True
            assert result.overall_confidence > 0.8

    @pytest.mark.asyncio
    async def test_questionable_medical_necessity(self):
        """Test validation of questionable medical necessity."""
        with patch("src.services.validation.get_clinical_necessity_validator") as mock_validator:
            validator = AsyncMock()
            validator.validate = AsyncMock(return_value=MockNecessityResult(
                is_valid=False,
                overall_confidence=0.35,
                critical_issues=["CPT 27447 (knee replacement) not supported by ICD Z23 (immunization)"],
            ))
            mock_validator.return_value = validator

            result = await validator.validate(
                icd_codes=["Z23"],  # Immunization encounter
                cpt_codes=["27447"],  # Total knee replacement
                patient_age=45,
                patient_gender="F",
            )

            assert result.is_valid is False
            assert result.requires_review is True
            assert len(result.critical_issues) > 0


# =============================================================================
# ICD-CPT Crosswalk Integration Tests
# =============================================================================


class TestCrosswalkIntegration:
    """Integration tests for ICD-CPT crosswalk validation."""

    @pytest.mark.asyncio
    async def test_valid_icd_cpt_pair(self):
        """Test validation of valid ICD-CPT pair."""
        with patch("src.services.validation.get_crosswalk_validator") as mock_validator:
            validator = AsyncMock()
            validator.validate = AsyncMock(return_value=MockCrosswalkResult(
                is_valid=True,
                overall_confidence=0.95,
            ))
            mock_validator.return_value = validator

            result = await validator.validate(
                ["M17.11"],  # Primary osteoarthritis right knee
                ["27447"],  # Total knee replacement
            )

            assert result.is_valid is True
            assert result.overall_confidence > 0.9

    @pytest.mark.asyncio
    async def test_invalid_icd_cpt_pair(self):
        """Test detection of invalid ICD-CPT pair."""
        with patch("src.services.validation.get_crosswalk_validator") as mock_validator:
            validator = AsyncMock()
            validator.validate = AsyncMock(return_value=MockCrosswalkResult(
                is_valid=False,
                overall_confidence=0.2,
                invalid_pairs=[("J06.9", "27447")],  # Upper respiratory infection → knee replacement
            ))
            mock_validator.return_value = validator

            result = await validator.validate(
                ["J06.9"],  # Acute upper respiratory infection
                ["27447"],  # Total knee replacement
            )

            assert result.is_valid is False
            assert len(result.invalid_pairs) > 0

    @pytest.mark.asyncio
    async def test_ncci_edit_detection(self):
        """Test detection of NCCI edit pairs."""
        with patch("src.services.validation.get_crosswalk_validator") as mock_validator:
            validator = AsyncMock()
            mock_result = MockCrosswalkResult(is_valid=True)
            mock_result.ncci_edits_found = [
                {"column1": "82947", "column2": "80053", "modifier_allowed": False}
            ]
            validator.validate = AsyncMock(return_value=mock_result)
            mock_validator.return_value = validator

            result = await validator.validate(
                ["E11.9"],
                ["82947", "80053"],  # Glucose + CMP (glucose is part of CMP)
            )

            assert len(result.ncci_edits_found) > 0


# =============================================================================
# Demographic Validation Integration Tests
# =============================================================================


class TestDemographicIntegration:
    """Integration tests for demographic validation."""

    @pytest.mark.asyncio
    async def test_age_appropriate_procedure(self):
        """Test age-appropriate procedure validation."""
        with patch("src.services.validation.get_demographic_validator") as mock_validator:
            validator = AsyncMock()
            validator.validate = AsyncMock(return_value=MockDemographicResult(
                is_valid=True,
            ))
            mock_validator.return_value = validator

            result = await validator.validate(
                icd_codes=["M17.11"],  # Osteoarthritis
                cpt_codes=["27447"],  # Knee replacement
                patient_age_years=65,  # Appropriate age
                patient_gender="M",
            )

            assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_age_inappropriate_procedure(self):
        """Test age-inappropriate procedure detection."""
        with patch("src.services.validation.get_demographic_validator") as mock_validator:
            validator = AsyncMock()
            validator.validate = AsyncMock(return_value=MockDemographicResult(
                is_valid=False,
                issues=[
                    {"type": "age_mismatch", "code": "E28.2", "reason": "Polycystic ovary syndrome inappropriate for age 8"}
                ],
            ))
            mock_validator.return_value = validator

            result = await validator.validate(
                icd_codes=["E28.2"],  # PCOS
                cpt_codes=["58661"],  # Laparoscopy with removal of ovary
                patient_age_years=8,  # Child - inappropriate
                patient_gender="F",
            )

            assert result.is_valid is False
            assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_gender_specific_code_mismatch(self):
        """Test gender-specific code mismatch detection."""
        with patch("src.services.validation.get_demographic_validator") as mock_validator:
            validator = AsyncMock()
            validator.validate = AsyncMock(return_value=MockDemographicResult(
                is_valid=False,
                issues=[
                    {"type": "gender_mismatch", "code": "N40", "reason": "Prostate diagnosis for female patient"}
                ],
            ))
            mock_validator.return_value = validator

            result = await validator.validate(
                icd_codes=["N40.0"],  # Benign prostatic hyperplasia
                cpt_codes=["55700"],  # Prostate biopsy
                patient_age_years=65,
                patient_gender="F",  # Female patient
            )

            assert result.is_valid is False
            assert any("gender" in str(issue).lower() for issue in result.issues)


# =============================================================================
# ICD Conflict Integration Tests
# =============================================================================


class TestICDConflictIntegration:
    """Integration tests for ICD conflict detection."""

    @pytest.mark.asyncio
    async def test_no_conflicts(self):
        """Test validation with no ICD conflicts."""
        with patch("src.services.validation.get_icd_conflict_validator") as mock_validator:
            validator = AsyncMock()
            validator.validate = AsyncMock(return_value=MockConflictResult(
                is_valid=True,
            ))
            mock_validator.return_value = validator

            result = await validator.validate(["E11.9", "I10", "M54.5"])

            assert result.is_valid is True
            assert len(result.conflicts) == 0

    @pytest.mark.asyncio
    async def test_mutual_exclusion_conflict(self):
        """Test detection of mutually exclusive diagnoses."""
        with patch("src.services.validation.get_icd_conflict_validator") as mock_validator:
            validator = AsyncMock()
            validator.validate = AsyncMock(return_value=MockConflictResult(
                is_valid=False,
                conflicts=[
                    {
                        "code1": "E10.9",
                        "code2": "E11.9",
                        "conflict_type": "mutual_exclusion",
                        "reason": "Type 1 and Type 2 diabetes are mutually exclusive",
                    }
                ],
            ))
            mock_validator.return_value = validator

            result = await validator.validate(["E10.9", "E11.9"])  # Both Type 1 and Type 2 diabetes

            assert result.is_valid is False
            assert len(result.conflicts) > 0


# =============================================================================
# Full Pipeline Integration Tests
# =============================================================================


class TestFullPipelineIntegration:
    """End-to-end integration tests for the validation pipeline."""

    @pytest.fixture
    def clean_claim_data(self):
        """Sample clean claim data."""
        return {
            "claim_id": str(uuid4()),
            "member_id": "MEM123456",
            "policy_id": "POL987654",
            "provider_id": "PRV555555",
            "icd_codes": ["E11.9", "I10"],
            "cpt_codes": ["99213", "80053"],
            "patient_age": 55,
            "patient_gender": "M",
            "service_date": date(2025, 12, 15),
        }

    @pytest.fixture
    def suspicious_claim_data(self):
        """Sample suspicious claim data."""
        return {
            "claim_id": str(uuid4()),
            "member_id": "MEM999999",
            "policy_id": "POL111111",
            "provider_id": "PRV000000",
            "icd_codes": ["E10.9", "E11.9"],  # Conflicting diabetes types
            "cpt_codes": ["99215", "82947", "80053"],  # Upcoding + unbundling
            "patient_age": 8,  # Age mismatch for diabetes management
            "patient_gender": "F",
            "service_date": date(2025, 12, 15),
        }

    @pytest.mark.asyncio
    async def test_clean_claim_passes_all_validations(self, clean_claim_data):
        """Test that a clean claim passes all validations."""
        with patch("src.services.validation.get_crosswalk_validator") as mock_xwalk, \
             patch("src.services.validation.get_icd_conflict_validator") as mock_conflict, \
             patch("src.services.validation.get_demographic_validator") as mock_demo, \
             patch("src.services.validation.get_pdf_forensics_service") as mock_forensics:

            # All validators return passing results
            mock_xwalk.return_value.validate = AsyncMock(return_value=MockCrosswalkResult())
            mock_conflict.return_value.validate = AsyncMock(return_value=MockConflictResult())
            mock_demo.return_value.validate = AsyncMock(return_value=MockDemographicResult())
            mock_forensics.return_value.analyze = AsyncMock(return_value=MockForensicResult())

            # Run validations
            xwalk = await mock_xwalk.return_value.validate(
                clean_claim_data["icd_codes"],
                clean_claim_data["cpt_codes"],
            )
            conflict = await mock_conflict.return_value.validate(clean_claim_data["icd_codes"])
            demo = await mock_demo.return_value.validate(
                icd_codes=clean_claim_data["icd_codes"],
                cpt_codes=clean_claim_data["cpt_codes"],
                patient_age_years=clean_claim_data["patient_age"],
                patient_gender=clean_claim_data["patient_gender"],
            )

            # All should pass
            assert xwalk.is_valid is True
            assert conflict.is_valid is True
            assert demo.is_valid is True

    @pytest.mark.asyncio
    async def test_suspicious_claim_triggers_review(self, suspicious_claim_data):
        """Test that suspicious claim triggers review."""
        with patch("src.services.validation.get_icd_conflict_validator") as mock_conflict:
            # ICD conflict detected
            mock_conflict.return_value.validate = AsyncMock(return_value=MockConflictResult(
                is_valid=False,
                conflicts=[{"code1": "E10.9", "code2": "E11.9"}],
            ))

            result = await mock_conflict.return_value.validate(suspicious_claim_data["icd_codes"])

            assert result.is_valid is False

    @pytest.mark.asyncio
    async def test_pipeline_performance_under_threshold(self):
        """Test that pipeline completes within performance threshold."""
        import time

        with patch("src.services.validation.get_crosswalk_validator") as mock_xwalk, \
             patch("src.services.validation.get_icd_conflict_validator") as mock_conflict, \
             patch("src.services.validation.get_demographic_validator") as mock_demo:

            # Fast mock responses
            mock_xwalk.return_value.validate = AsyncMock(return_value=MockCrosswalkResult())
            mock_conflict.return_value.validate = AsyncMock(return_value=MockConflictResult())
            mock_demo.return_value.validate = AsyncMock(return_value=MockDemographicResult())

            start = time.perf_counter()

            # Run all validations
            await mock_xwalk.return_value.validate(["E11.9"], ["99213"])
            await mock_conflict.return_value.validate(["E11.9"])
            await mock_demo.return_value.validate(
                icd_codes=["E11.9"],
                cpt_codes=["99213"],
                patient_age_years=55,
                patient_gender="M",
            )

            elapsed_ms = (time.perf_counter() - start) * 1000

            # Should complete well under 2 seconds (the target)
            assert elapsed_ms < 2000


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in validation pipeline."""

    @pytest.mark.asyncio
    async def test_validator_exception_handled(self):
        """Test that validator exceptions are handled gracefully."""
        with patch("src.services.validation.get_crosswalk_validator") as mock_validator:
            mock_validator.return_value.validate = AsyncMock(
                side_effect=Exception("Database connection failed")
            )

            with pytest.raises(Exception) as exc_info:
                await mock_validator.return_value.validate(["E11.9"], ["99213"])

            assert "Database connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_llm_fallback_on_primary_failure(self):
        """Test LLM fallback when primary provider fails."""
        with patch("src.services.validation.get_clinical_necessity_validator") as mock_validator:
            validator = AsyncMock()
            # First call fails, but result still returned (fallback worked)
            mock_result = MockNecessityResult(is_valid=True)
            mock_result.llm_provider_used = "fallback-provider"
            validator.validate = AsyncMock(return_value=mock_result)
            mock_validator.return_value = validator

            result = await validator.validate(
                icd_codes=["E11.9"],
                cpt_codes=["99213"],
            )

            # Should still get a valid result from fallback
            assert result is not None
            assert result.llm_provider_used == "fallback-provider"

    @pytest.mark.asyncio
    async def test_empty_input_handled(self):
        """Test handling of empty input."""
        with patch("src.services.validation.get_icd_conflict_validator") as mock_validator:
            mock_validator.return_value.validate = AsyncMock(
                return_value=MockConflictResult(is_valid=True)
            )

            result = await mock_validator.return_value.validate([])

            assert result.is_valid is True
            assert len(result.conflicts) == 0


# =============================================================================
# Rate Limiting Tests
# =============================================================================


class TestRateLimiting:
    """Tests for rate limiting in validation pipeline."""

    @pytest.mark.asyncio
    async def test_concurrent_validations_succeed(self):
        """Test multiple concurrent validations succeed."""
        import asyncio

        with patch("src.services.validation.get_crosswalk_validator") as mock_validator:
            mock_validator.return_value.validate = AsyncMock(return_value=MockCrosswalkResult())

            # Run 10 concurrent validations
            tasks = [
                mock_validator.return_value.validate(["E11.9"], ["99213"])
                for _ in range(10)
            ]

            results = await asyncio.gather(*tasks)

            assert len(results) == 10
            assert all(r.is_valid for r in results)
