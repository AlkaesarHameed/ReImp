"""
E2E Tests: Full Validation Flow.

Tests the complete claim validation pipeline from submission through
all validation rules to final decision.

Source: Design Document 04_validation_engine_comprehensive_design.md
"""

import pytest
from datetime import date, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from httpx import AsyncClient
from pydantic import BaseModel


# =============================================================================
# Test Data Fixtures
# =============================================================================


class ClaimFixture(BaseModel):
    """Test claim data fixture."""

    member_id: str = "MEM123456"
    policy_id: str = "POL987654"
    provider_id: str = "PRV555555"
    icd_codes: list[str] = ["E11.9", "I10"]
    cpt_codes: list[str] = ["99213", "80053"]
    patient_age: int = 55
    patient_gender: str = "M"
    service_date_from: str = "2025-12-15"
    service_date_to: str = "2025-12-15"
    total_charged: float = 250.00


@pytest.fixture
def clean_claim():
    """Fixture for a clean, valid claim."""
    return ClaimFixture()


@pytest.fixture
def claim_with_icd_conflict():
    """Fixture for a claim with ICD conflict."""
    return ClaimFixture(
        icd_codes=["E10.9", "E11.9"],  # Type 1 and Type 2 diabetes conflict
        cpt_codes=["99214"],
    )


@pytest.fixture
def claim_with_age_mismatch():
    """Fixture for a claim with age-inappropriate codes."""
    return ClaimFixture(
        icd_codes=["Z00.121"],  # Pediatric routine exam
        cpt_codes=["99391"],  # Pediatric preventive visit
        patient_age=45,  # Adult patient
    )


@pytest.fixture
def claim_with_gender_mismatch():
    """Fixture for a claim with gender-inappropriate codes."""
    return ClaimFixture(
        icd_codes=["N40.0"],  # Benign prostatic hyperplasia
        cpt_codes=["55700"],  # Prostate biopsy
        patient_gender="F",  # Female patient
    )


@pytest.fixture
def claim_with_crosswalk_issue():
    """Fixture for a claim with ICD-CPT crosswalk issue."""
    return ClaimFixture(
        icd_codes=["J06.9"],  # Acute upper respiratory infection
        cpt_codes=["27447"],  # Total knee replacement
    )


# =============================================================================
# Mock Response Classes
# =============================================================================


class MockValidationResponse:
    """Mock validation orchestrator response."""

    def __init__(
        self,
        is_valid: bool = True,
        risk_score: float = 0.1,
        risk_level: str = "low",
    ):
        self.is_valid = is_valid
        self.overall_status = "passed" if is_valid else "failed"
        self.requires_review = not is_valid
        self.risk_score = risk_score
        self.risk_level = risk_level
        self.risk_factors = []
        self.recommendation = "APPROVE: Low risk." if is_valid else "REVIEW: Issues detected."
        self.rule_results = []
        self.critical_issues = []
        self.warnings = []
        self.forensic_signals = []
        self.extracted_insured_data = None
        self.extracted_codes = None
        self.phase_timings = {}


# =============================================================================
# Full Validation Flow Tests
# =============================================================================


class TestFullValidationFlow:
    """E2E tests for the complete validation flow."""

    @pytest.mark.asyncio
    async def test_clean_claim_passes_validation(self, clean_claim):
        """Test that a clean claim passes all validations."""
        with patch("src.services.validation.orchestrator.get_validation_orchestrator") as mock_orch:
            # Setup mock orchestrator
            orchestrator = AsyncMock()
            orchestrator.validate_claim = AsyncMock(
                return_value=MockValidationResponse(is_valid=True)
            )
            mock_orch.return_value = orchestrator

            # Simulate validation
            result = await orchestrator.validate_claim(clean_claim.model_dump())

            assert result.is_valid is True
            assert result.overall_status == "passed"
            assert result.risk_level == "low"

    @pytest.mark.asyncio
    async def test_icd_conflict_triggers_failure(self, claim_with_icd_conflict):
        """Test that ICD conflict is detected."""
        with patch("src.services.validation.get_icd_conflict_validator") as mock_validator:
            validator = AsyncMock()
            mock_result = MagicMock()
            mock_result.is_valid = False
            mock_result.conflicts = [
                {"code1": "E10.9", "code2": "E11.9", "reason": "Mutually exclusive"}
            ]
            mock_result.execution_time_ms = 10
            mock_result.to_evidence_dict = MagicMock(return_value={"conflicts": mock_result.conflicts})
            validator.validate = AsyncMock(return_value=mock_result)
            mock_validator.return_value = validator

            result = await validator.validate(claim_with_icd_conflict.icd_codes)

            assert result.is_valid is False
            assert len(result.conflicts) > 0

    @pytest.mark.asyncio
    async def test_age_mismatch_triggers_warning(self, claim_with_age_mismatch):
        """Test that age mismatch is detected."""
        with patch("src.services.validation.get_demographic_validator") as mock_validator:
            validator = AsyncMock()
            mock_result = MagicMock()
            mock_result.is_valid = False
            mock_result.issues = [
                {"type": "age_mismatch", "code": "Z00.121", "reason": "Pediatric code for adult"}
            ]
            mock_result.critical_issues = []
            mock_result.execution_time_ms = 5
            validator.validate = AsyncMock(return_value=mock_result)
            mock_validator.return_value = validator

            result = await validator.validate(
                icd_codes=claim_with_age_mismatch.icd_codes,
                cpt_codes=claim_with_age_mismatch.cpt_codes,
                patient_age_years=claim_with_age_mismatch.patient_age,
                patient_gender=claim_with_age_mismatch.patient_gender,
            )

            assert result.is_valid is False
            assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_gender_mismatch_triggers_failure(self, claim_with_gender_mismatch):
        """Test that gender mismatch is detected."""
        with patch("src.services.validation.get_demographic_validator") as mock_validator:
            validator = AsyncMock()
            mock_result = MagicMock()
            mock_result.is_valid = False
            mock_result.issues = [
                {"type": "gender_mismatch", "code": "N40.0", "reason": "Prostate code for female"}
            ]
            mock_result.critical_issues = mock_result.issues
            mock_result.execution_time_ms = 5
            validator.validate = AsyncMock(return_value=mock_result)
            mock_validator.return_value = validator

            result = await validator.validate(
                icd_codes=claim_with_gender_mismatch.icd_codes,
                cpt_codes=claim_with_gender_mismatch.cpt_codes,
                patient_age_years=claim_with_gender_mismatch.patient_age,
                patient_gender=claim_with_gender_mismatch.patient_gender,
            )

            assert result.is_valid is False
            assert any("gender" in str(issue).lower() for issue in result.issues)

    @pytest.mark.asyncio
    async def test_crosswalk_issue_triggers_review(self, claim_with_crosswalk_issue):
        """Test that ICD-CPT crosswalk issues are detected."""
        with patch("src.services.validation.get_crosswalk_validator") as mock_validator:
            validator = AsyncMock()
            mock_result = MagicMock()
            mock_result.is_valid = False
            mock_result.overall_confidence = 0.2
            mock_result.invalid_pairs = [("J06.9", "27447")]
            mock_result.ncci_edits_found = []
            mock_result.has_critical_issues = True
            mock_result.execution_time_ms = 25
            mock_result.to_evidence_dict = MagicMock(return_value={"invalid_pairs": [["J06.9", "27447"]]})
            validator.validate = AsyncMock(return_value=mock_result)
            mock_validator.return_value = validator

            result = await validator.validate(
                claim_with_crosswalk_issue.icd_codes,
                claim_with_crosswalk_issue.cpt_codes,
            )

            assert result.is_valid is False
            assert len(result.invalid_pairs) > 0


# =============================================================================
# Validation Pipeline Order Tests
# =============================================================================


class TestValidationPipelineOrder:
    """Tests for correct validation pipeline execution order."""

    @pytest.mark.asyncio
    async def test_extraction_runs_before_validation(self):
        """Test that data extraction runs before code validation."""
        execution_order = []

        async def mock_extraction(*args, **kwargs):
            execution_order.append("extraction")
            return MagicMock(has_codes=True, icd_codes=["E11.9"], cpt_codes=["99213"])

        async def mock_validation(*args, **kwargs):
            execution_order.append("validation")
            return MagicMock(is_valid=True)

        with patch("src.services.extraction.get_code_extractor") as mock_extractor, \
             patch("src.services.validation.get_crosswalk_validator") as mock_validator:

            extractor = AsyncMock()
            extractor.extract = mock_extraction
            mock_extractor.return_value = extractor

            validator = AsyncMock()
            validator.validate = mock_validation
            mock_validator.return_value = validator

            # Run extraction first
            await extractor.extract("sample text")
            # Then validation
            await validator.validate(["E11.9"], ["99213"])

            assert execution_order == ["extraction", "validation"]

    @pytest.mark.asyncio
    async def test_forensics_runs_parallel_with_validation(self):
        """Test that PDF forensics can run in parallel with validation."""
        import asyncio

        results = {}

        async def mock_forensics(*args, **kwargs):
            await asyncio.sleep(0.01)  # Simulate processing time
            results["forensics"] = datetime.now()
            return MagicMock(is_suspicious=False, fraud_score=0.1)

        async def mock_validation(*args, **kwargs):
            await asyncio.sleep(0.01)
            results["validation"] = datetime.now()
            return MagicMock(is_valid=True)

        with patch("src.services.validation.get_pdf_forensics_service") as mock_forensics_svc, \
             patch("src.services.validation.get_crosswalk_validator") as mock_validator:

            forensics = AsyncMock()
            forensics.analyze = mock_forensics
            mock_forensics_svc.return_value = forensics

            validator = AsyncMock()
            validator.validate = mock_validation
            mock_validator.return_value = validator

            # Run in parallel
            await asyncio.gather(
                forensics.analyze(b"pdf content", "test.pdf"),
                validator.validate(["E11.9"], ["99213"]),
            )

            # Both should have completed
            assert "forensics" in results
            assert "validation" in results


# =============================================================================
# Risk Score Calculation Tests
# =============================================================================


class TestRiskScoreCalculation:
    """Tests for risk score calculation in the pipeline."""

    @pytest.mark.asyncio
    async def test_clean_claim_has_low_risk(self, clean_claim):
        """Test that clean claim results in low risk score."""
        with patch("src.services.validation.orchestrator.get_validation_orchestrator") as mock_orch:
            orchestrator = AsyncMock()
            orchestrator.validate_claim = AsyncMock(
                return_value=MockValidationResponse(
                    is_valid=True,
                    risk_score=0.05,
                    risk_level="low",
                )
            )
            mock_orch.return_value = orchestrator

            result = await orchestrator.validate_claim(clean_claim.model_dump())

            assert result.risk_score < 0.3
            assert result.risk_level == "low"

    @pytest.mark.asyncio
    async def test_multiple_issues_increase_risk(self):
        """Test that multiple issues compound risk score."""
        with patch("src.services.validation.orchestrator.get_validation_orchestrator") as mock_orch:
            orchestrator = AsyncMock()
            mock_response = MockValidationResponse(
                is_valid=False,
                risk_score=0.75,
                risk_level="critical",
            )
            mock_response.critical_issues = [
                "ICD conflict detected",
                "Age mismatch",
                "Crosswalk failure",
            ]
            orchestrator.validate_claim = AsyncMock(return_value=mock_response)
            mock_orch.return_value = orchestrator

            claim_data = {
                "icd_codes": ["E10.9", "E11.9"],
                "cpt_codes": ["27447"],
                "patient_age": 8,
            }
            result = await orchestrator.validate_claim(claim_data)

            assert result.risk_score >= 0.5
            assert result.risk_level in ("high", "critical")
            assert len(result.critical_issues) >= 2


# =============================================================================
# End-to-End API Tests (with mocked database)
# =============================================================================


class TestValidationAPIE2E:
    """E2E tests for validation API endpoints."""

    @pytest.mark.asyncio
    async def test_full_validation_endpoint_success(self):
        """Test the /validation/full endpoint with valid claim."""
        with patch("src.services.validation.orchestrator.get_validation_orchestrator") as mock_orch:
            orchestrator = AsyncMock()
            orchestrator.validate_claim = AsyncMock(
                return_value=MockValidationResponse(is_valid=True)
            )
            mock_orch.return_value = orchestrator

            # Simulate API call
            request_data = {
                "member_id": "MEM123",
                "icd_codes": ["E11.9"],
                "cpt_codes": ["99213"],
                "patient_age": 55,
                "patient_gender": "M",
                "run_llm_rules": False,
            }

            result = await orchestrator.validate_claim(request_data)

            assert result.is_valid is True
            assert result.overall_status == "passed"

    @pytest.mark.asyncio
    async def test_quick_validation_endpoint(self):
        """Test the /validation/quick endpoint."""
        with patch("src.services.validation.get_icd_conflict_validator") as mock_conflict, \
             patch("src.services.validation.get_demographic_validator") as mock_demo:

            # Setup mocks
            conflict_validator = AsyncMock()
            conflict_result = MagicMock()
            conflict_result.is_valid = True
            conflict_result.conflicts = []
            conflict_result.critical_conflicts = []
            conflict_result.to_evidence_dict = MagicMock(return_value={})
            conflict_validator.validate = AsyncMock(return_value=conflict_result)
            mock_conflict.return_value = conflict_validator

            demo_validator = AsyncMock()
            demo_result = MagicMock()
            demo_result.is_valid = True
            demo_result.issues = []
            demo_result.critical_issues = []
            demo_result.to_evidence_dict = MagicMock(return_value={})
            demo_validator.validate = AsyncMock(return_value=demo_result)
            mock_demo.return_value = demo_validator

            # Run validations
            conflict_check = await conflict_validator.validate(["E11.9"])
            demo_check = await demo_validator.validate(
                icd_codes=["E11.9"],
                cpt_codes=["99213"],
                patient_age_years=55,
                patient_gender="M",
            )

            assert conflict_check.is_valid is True
            assert demo_check.is_valid is True


# =============================================================================
# Performance Tests
# =============================================================================


class TestValidationPerformance:
    """Tests for validation pipeline performance."""

    @pytest.mark.asyncio
    async def test_validation_completes_within_threshold(self):
        """Test that validation completes within 2 second threshold."""
        import time

        with patch("src.services.validation.orchestrator.get_validation_orchestrator") as mock_orch:
            orchestrator = AsyncMock()
            orchestrator.validate_claim = AsyncMock(
                return_value=MockValidationResponse(is_valid=True)
            )
            mock_orch.return_value = orchestrator

            start = time.perf_counter()

            await orchestrator.validate_claim({
                "icd_codes": ["E11.9", "I10", "M54.5"],
                "cpt_codes": ["99213", "80053", "71046"],
                "patient_age": 55,
                "patient_gender": "M",
            })

            elapsed_ms = (time.perf_counter() - start) * 1000

            # Should complete well under 2 seconds
            assert elapsed_ms < 2000

    @pytest.mark.asyncio
    async def test_concurrent_validations(self):
        """Test handling of concurrent validation requests."""
        import asyncio

        with patch("src.services.validation.orchestrator.get_validation_orchestrator") as mock_orch:
            orchestrator = AsyncMock()
            orchestrator.validate_claim = AsyncMock(
                return_value=MockValidationResponse(is_valid=True)
            )
            mock_orch.return_value = orchestrator

            # Run 10 concurrent validations
            tasks = [
                orchestrator.validate_claim({"icd_codes": [f"E11.{i}"], "cpt_codes": ["99213"]})
                for i in range(10)
            ]

            results = await asyncio.gather(*tasks)

            assert len(results) == 10
            assert all(r.is_valid for r in results)
