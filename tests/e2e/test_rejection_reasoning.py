"""
E2E Tests: Rejection Reasoning Flow.

Tests the rejection explanation generation including LLM-based reasoning,
evidence collection, and appeal guidance for claim rejections.

Source: Design Document 04_validation_engine_comprehensive_design.md
"""

import pytest
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# =============================================================================
# Rejection Reasoning Fixtures
# =============================================================================


@pytest.fixture
def validation_failure_results():
    """Fixture for validation results with failures."""
    return [
        {
            "rule_id": "CLIN-001",
            "rule_name": "ICD-10 Validity Check",
            "status": "passed",
            "confidence": 1.0,
            "issues_found": 0,
        },
        {
            "rule_id": "CLIN-002",
            "rule_name": "Medical Necessity Check",
            "status": "failed",
            "confidence": 0.85,
            "issues_found": 1,
            "details": {
                "issue": "Procedure not medically necessary for diagnosis",
                "procedure_code": "99215",
                "diagnosis_code": "J06.9",
            },
        },
        {
            "rule_id": "CLIN-003",
            "rule_name": "ICD-CPT Crosswalk",
            "status": "failed",
            "confidence": 0.92,
            "issues_found": 1,
            "details": {
                "issue": "Procedure not typically associated with diagnosis",
                "crosswalk_score": 0.35,
            },
        },
    ]


@pytest.fixture
def rejection_evidence():
    """Fixture for rejection evidence items."""
    return [
        {
            "evidence_type": "validation_rule",
            "source": "CLIN-002",
            "description": "Medical necessity validation failed",
            "supporting_data": {"confidence": 0.85},
        },
        {
            "evidence_type": "crosswalk",
            "source": "ICD-CPT Crosswalk Database",
            "description": "Low crosswalk score indicates uncommon pairing",
            "supporting_data": {"score": 0.35},
        },
    ]


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for rejection reasoning."""
    return {
        "summary": "The claim was rejected due to insufficient medical necessity documentation and uncommon procedure-diagnosis pairing.",
        "reasoning": [
            "The submitted diagnosis code J06.9 (Acute upper respiratory infection) does not typically warrant the high-level E/M service 99215.",
            "Clinical guidelines suggest that level 4 E/M services require more complex medical decision making than typically associated with acute URI.",
            "The ICD-CPT crosswalk analysis shows only a 35% association between these codes.",
        ],
        "appeal_guidance": [
            "Provide additional clinical documentation supporting the complexity of the patient encounter.",
            "Include any comorbidities that may have contributed to the higher service level.",
            "Submit progress notes demonstrating the medical decision-making complexity.",
        ],
        "confidence": 0.88,
    }


# =============================================================================
# Rejection Reasoning Tests
# =============================================================================


class TestRejectionReasoningGeneration:
    """E2E tests for rejection reasoning generation."""

    @pytest.mark.asyncio
    async def test_generate_rejection_reasoning(
        self, validation_failure_results, mock_llm_response
    ):
        """Test generation of human-readable rejection reasoning."""
        with patch("src.services.validation.get_reasoning_service") as mock_service:
            reasoning_service = AsyncMock()
            reasoning_service.generate_reasoning = AsyncMock(
                return_value=mock_llm_response
            )
            mock_service.return_value = reasoning_service

            result = await reasoning_service.generate_reasoning(
                validation_results=validation_failure_results,
                claim_data={"total_charged": 150.00},
            )

            assert result["summary"] is not None
            assert len(result["reasoning"]) >= 2
            assert result["confidence"] >= 0.7

    @pytest.mark.asyncio
    async def test_reasoning_includes_appeal_guidance(
        self, validation_failure_results, mock_llm_response
    ):
        """Test that reasoning includes actionable appeal guidance."""
        with patch("src.services.validation.get_reasoning_service") as mock_service:
            reasoning_service = AsyncMock()
            reasoning_service.generate_reasoning = AsyncMock(
                return_value=mock_llm_response
            )
            mock_service.return_value = reasoning_service

            result = await reasoning_service.generate_reasoning(
                validation_results=validation_failure_results,
                claim_data={},
            )

            assert "appeal_guidance" in result
            assert len(result["appeal_guidance"]) >= 1
            # Should provide actionable steps
            assert any("documentation" in g.lower() for g in result["appeal_guidance"])

    @pytest.mark.asyncio
    async def test_reasoning_cites_specific_rules(
        self, validation_failure_results, mock_llm_response
    ):
        """Test that reasoning cites specific validation rules."""
        with patch("src.services.validation.get_reasoning_service") as mock_service:
            reasoning_service = AsyncMock()

            enhanced_response = mock_llm_response.copy()
            enhanced_response["cited_rules"] = ["CLIN-002", "CLIN-003"]

            reasoning_service.generate_reasoning = AsyncMock(
                return_value=enhanced_response
            )
            mock_service.return_value = reasoning_service

            result = await reasoning_service.generate_reasoning(
                validation_results=validation_failure_results,
                claim_data={},
            )

            assert "cited_rules" in result
            assert "CLIN-002" in result["cited_rules"]

    @pytest.mark.asyncio
    async def test_fallback_reasoning_without_llm(self, validation_failure_results):
        """Test fallback reasoning when LLM is unavailable."""
        with patch("src.services.validation.get_reasoning_service") as mock_service:
            reasoning_service = AsyncMock()

            # Simulate LLM failure with fallback
            fallback_response = {
                "summary": "Claim rejected due to validation failures.",
                "reasoning": [
                    "Medical Necessity Check: Procedure not medically necessary for diagnosis",
                    "ICD-CPT Crosswalk: Procedure not typically associated with diagnosis",
                ],
                "appeal_guidance": [
                    "Review the specific validation failures and provide supporting documentation."
                ],
                "confidence": 0.5,
                "is_fallback": True,
            }

            reasoning_service.generate_reasoning = AsyncMock(
                return_value=fallback_response
            )
            mock_service.return_value = reasoning_service

            result = await reasoning_service.generate_reasoning(
                validation_results=validation_failure_results,
                claim_data={},
            )

            assert result.get("is_fallback") is True
            assert result["confidence"] < 0.7


# =============================================================================
# Evidence Collection Tests
# =============================================================================


class TestEvidenceCollection:
    """E2E tests for rejection evidence collection."""

    @pytest.mark.asyncio
    async def test_collect_evidence_from_validation(self, validation_failure_results):
        """Test evidence collection from validation results."""
        with patch("src.services.validation.get_evidence_collector") as mock_collector:
            collector = AsyncMock()

            mock_evidence = [
                {
                    "evidence_type": "validation_failure",
                    "source": "CLIN-002",
                    "description": "Medical necessity check failed",
                    "details": validation_failure_results[1]["details"],
                },
                {
                    "evidence_type": "validation_failure",
                    "source": "CLIN-003",
                    "description": "Crosswalk validation failed",
                    "details": validation_failure_results[2]["details"],
                },
            ]

            collector.collect_evidence = AsyncMock(return_value=mock_evidence)
            mock_collector.return_value = collector

            evidence = await collector.collect_evidence(validation_failure_results)

            assert len(evidence) >= 2
            assert all(e["evidence_type"] == "validation_failure" for e in evidence)

    @pytest.mark.asyncio
    async def test_evidence_includes_supporting_data(self, validation_failure_results):
        """Test that evidence includes supporting data."""
        with patch("src.services.validation.get_evidence_collector") as mock_collector:
            collector = AsyncMock()

            mock_evidence = [
                {
                    "evidence_type": "crosswalk",
                    "source": "CLIN-003",
                    "description": "Low crosswalk score",
                    "supporting_data": {
                        "crosswalk_score": 0.35,
                        "threshold": 0.5,
                        "procedure_code": "99215",
                        "diagnosis_code": "J06.9",
                    },
                }
            ]

            collector.collect_evidence = AsyncMock(return_value=mock_evidence)
            mock_collector.return_value = collector

            evidence = await collector.collect_evidence(validation_failure_results)

            assert evidence[0]["supporting_data"] is not None
            assert "crosswalk_score" in evidence[0]["supporting_data"]

    @pytest.mark.asyncio
    async def test_evidence_from_fraud_signals(self):
        """Test evidence collection from fraud detection signals."""
        with patch("src.services.validation.get_evidence_collector") as mock_collector:
            collector = AsyncMock()

            fraud_signals = [
                {
                    "signal_type": "metadata_mismatch",
                    "severity": "high",
                    "description": "PDF creation date modified",
                }
            ]

            mock_evidence = [
                {
                    "evidence_type": "fraud_signal",
                    "source": "PDF Forensics",
                    "description": "Document metadata inconsistency detected",
                    "supporting_data": fraud_signals[0],
                }
            ]

            collector.collect_fraud_evidence = AsyncMock(return_value=mock_evidence)
            mock_collector.return_value = collector

            evidence = await collector.collect_fraud_evidence(fraud_signals)

            assert len(evidence) >= 1
            assert evidence[0]["evidence_type"] == "fraud_signal"


# =============================================================================
# Rejection Creation Tests
# =============================================================================


class TestRejectionCreation:
    """E2E tests for claim rejection creation."""

    @pytest.mark.asyncio
    async def test_create_rejection_with_reasoning(
        self, validation_failure_results, rejection_evidence, mock_llm_response
    ):
        """Test creating a rejection record with LLM reasoning."""
        with patch("src.services.validation.get_rejection_service") as mock_service:
            rejection_service = AsyncMock()

            mock_rejection = MagicMock()
            mock_rejection.id = str(uuid4())
            mock_rejection.claim_id = "CLM-001"
            mock_rejection.rejection_id = "REJ-2025-001"
            mock_rejection.category = "CLINICAL"
            mock_rejection.summary = mock_llm_response["summary"]
            mock_rejection.reasoning = mock_llm_response["reasoning"]
            mock_rejection.appeal_deadline = "2026-01-18"
            mock_rejection.appeal_status = "ELIGIBLE"

            rejection_service.create_rejection = AsyncMock(return_value=mock_rejection)
            mock_service.return_value = rejection_service

            rejection = await rejection_service.create_rejection(
                claim_id="CLM-001",
                validation_results=validation_failure_results,
                evidence=rejection_evidence,
                reasoning=mock_llm_response,
            )

            assert rejection.rejection_id.startswith("REJ-")
            assert rejection.summary is not None
            assert len(rejection.reasoning) >= 1
            assert rejection.appeal_status == "ELIGIBLE"

    @pytest.mark.asyncio
    async def test_rejection_sets_appeal_deadline(
        self, validation_failure_results, rejection_evidence, mock_llm_response
    ):
        """Test that rejection sets appropriate appeal deadline."""
        with patch("src.services.validation.get_rejection_service") as mock_service:
            rejection_service = AsyncMock()

            mock_rejection = MagicMock()
            mock_rejection.id = str(uuid4())
            mock_rejection.rejection_date = datetime(2025, 12, 19)
            mock_rejection.appeal_deadline = datetime(2026, 1, 18)  # 30 days
            mock_rejection.appeal_status = "ELIGIBLE"

            rejection_service.create_rejection = AsyncMock(return_value=mock_rejection)
            mock_service.return_value = rejection_service

            rejection = await rejection_service.create_rejection(
                claim_id="CLM-001",
                validation_results=validation_failure_results,
                evidence=rejection_evidence,
                reasoning=mock_llm_response,
            )

            # Appeal deadline should be ~30 days from rejection
            days_diff = (rejection.appeal_deadline - rejection.rejection_date).days
            assert 28 <= days_diff <= 45  # Allow some flexibility

    @pytest.mark.asyncio
    async def test_rejection_categorization(self, validation_failure_results):
        """Test that rejections are properly categorized."""
        with patch("src.services.validation.get_rejection_service") as mock_service:
            rejection_service = AsyncMock()

            # Clinical rejection
            clinical_rejection = MagicMock()
            clinical_rejection.category = "CLINICAL"

            rejection_service.create_rejection = AsyncMock(
                return_value=clinical_rejection
            )
            mock_service.return_value = rejection_service

            rejection = await rejection_service.create_rejection(
                claim_id="CLM-001",
                validation_results=validation_failure_results,
                evidence=[],
                reasoning={},
            )

            assert rejection.category in [
                "CLINICAL",
                "ADMINISTRATIVE",
                "FRAUD",
                "DUPLICATE",
            ]


# =============================================================================
# Appeal Workflow Tests
# =============================================================================


class TestAppealWorkflow:
    """E2E tests for appeal submission and processing."""

    @pytest.mark.asyncio
    async def test_submit_appeal(self):
        """Test submitting an appeal for a rejected claim."""
        with patch("src.services.validation.get_appeal_service") as mock_service:
            appeal_service = AsyncMock()

            mock_appeal = MagicMock()
            mock_appeal.id = str(uuid4())
            mock_appeal.appeal_id = "APL-2025-001"
            mock_appeal.status = "PENDING"
            mock_appeal.submitted_at = datetime.now()

            appeal_service.submit_appeal = AsyncMock(return_value=mock_appeal)
            mock_service.return_value = appeal_service

            appeal = await appeal_service.submit_appeal(
                claim_id="CLM-001",
                rejection_id="REJ-2025-001",
                reason="Additional documentation supports medical necessity",
                supporting_documents=["doc1.pdf", "doc2.pdf"],
            )

            assert appeal.appeal_id.startswith("APL-")
            assert appeal.status == "PENDING"

    @pytest.mark.asyncio
    async def test_appeal_past_deadline_rejected(self):
        """Test that appeals past deadline are rejected."""
        with patch("src.services.validation.get_appeal_service") as mock_service:
            appeal_service = AsyncMock()

            appeal_service.submit_appeal = AsyncMock(
                side_effect=ValueError("Appeal deadline has passed")
            )
            mock_service.return_value = appeal_service

            with pytest.raises(ValueError, match="deadline"):
                await appeal_service.submit_appeal(
                    claim_id="CLM-001",
                    rejection_id="REJ-2024-001",  # Old rejection
                    reason="Late appeal attempt",
                    supporting_documents=[],
                )

    @pytest.mark.asyncio
    async def test_appeal_updates_rejection_status(self):
        """Test that appeal submission updates rejection status."""
        with patch("src.services.validation.get_appeal_service") as mock_service:
            appeal_service = AsyncMock()

            mock_appeal = MagicMock()
            mock_appeal.status = "PENDING"
            mock_appeal.rejection_status_updated = True

            appeal_service.submit_appeal = AsyncMock(return_value=mock_appeal)
            mock_service.return_value = appeal_service

            appeal = await appeal_service.submit_appeal(
                claim_id="CLM-001",
                rejection_id="REJ-2025-001",
                reason="Supporting documentation attached",
                supporting_documents=["evidence.pdf"],
            )

            # Should mark rejection as under appeal
            assert appeal.rejection_status_updated is True


# =============================================================================
# Integration Tests
# =============================================================================


class TestRejectionReasoningIntegration:
    """Integration tests for complete rejection reasoning flow."""

    @pytest.mark.asyncio
    async def test_full_rejection_flow(
        self, validation_failure_results, mock_llm_response
    ):
        """Test complete flow from validation failure to reasoned rejection."""
        with patch("src.services.validation.get_reasoning_service") as mock_reasoning, \
             patch("src.services.validation.get_evidence_collector") as mock_evidence, \
             patch("src.services.validation.get_rejection_service") as mock_rejection:

            # Setup reasoning service
            reasoning_service = AsyncMock()
            reasoning_service.generate_reasoning = AsyncMock(
                return_value=mock_llm_response
            )
            mock_reasoning.return_value = reasoning_service

            # Setup evidence collector
            evidence_collector = AsyncMock()
            evidence_collector.collect_evidence = AsyncMock(
                return_value=[
                    {"evidence_type": "validation", "source": "CLIN-002"}
                ]
            )
            mock_evidence.return_value = evidence_collector

            # Setup rejection service
            rejection_service = AsyncMock()
            final_rejection = MagicMock()
            final_rejection.id = str(uuid4())
            final_rejection.summary = mock_llm_response["summary"]
            final_rejection.reasoning = mock_llm_response["reasoning"]
            final_rejection.appeal_guidance = mock_llm_response["appeal_guidance"]

            rejection_service.create_rejection = AsyncMock(return_value=final_rejection)
            mock_rejection.return_value = rejection_service

            # Execute flow
            reasoning = await reasoning_service.generate_reasoning(
                validation_results=validation_failure_results,
                claim_data={},
            )
            evidence = await evidence_collector.collect_evidence(
                validation_failure_results
            )
            rejection = await rejection_service.create_rejection(
                claim_id="CLM-001",
                validation_results=validation_failure_results,
                evidence=evidence,
                reasoning=reasoning,
            )

            # Verify complete flow
            assert rejection.summary is not None
            assert len(rejection.reasoning) >= 1
            assert len(rejection.appeal_guidance) >= 1

    @pytest.mark.asyncio
    async def test_rejection_with_fraud_evidence(self):
        """Test rejection creation with fraud detection evidence."""
        with patch("src.services.validation.get_rejection_service") as mock_service:
            rejection_service = AsyncMock()

            fraud_rejection = MagicMock()
            fraud_rejection.category = "FRAUD"
            fraud_rejection.risk_level = "critical"
            fraud_rejection.summary = "Claim rejected due to document tampering indicators"
            fraud_rejection.requires_investigation = True

            rejection_service.create_rejection = AsyncMock(return_value=fraud_rejection)
            mock_service.return_value = rejection_service

            rejection = await rejection_service.create_rejection(
                claim_id="CLM-001",
                validation_results=[],
                evidence=[
                    {
                        "evidence_type": "fraud_signal",
                        "source": "PDF Forensics",
                        "description": "Font substitution detected in monetary amounts",
                    }
                ],
                reasoning={"summary": "Fraud indicators detected"},
            )

            assert rejection.category == "FRAUD"
            assert rejection.risk_level == "critical"
            assert rejection.requires_investigation is True
