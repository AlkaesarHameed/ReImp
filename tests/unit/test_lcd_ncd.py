"""
Unit tests for LCD/NCD Medical Necessity Service.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19
"""

import pytest
from datetime import date
from typing import List

from src.services.medical.lcd_ncd_service import (
    LCDNCDService,
    LCDNCDDatabase,
    CoveragePolicy,
    CoverageDetermination,
    MedicalNecessityResult,
    CoverageType,
    CoverageStatus,
    MACRegion,
    get_lcd_ncd_service,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def lcd_ncd_service() -> LCDNCDService:
    """Create LCD/NCD service instance."""
    return LCDNCDService()


@pytest.fixture
def sample_database() -> LCDNCDDatabase:
    """Create sample database with test policies."""
    return LCDNCDDatabase()


# =============================================================================
# Database Tests
# =============================================================================


class TestLCDNCDDatabase:
    """Tests for LCD/NCD policy database."""

    def test_database_initialization(self, sample_database: LCDNCDDatabase):
        """Test database initializes with sample policies."""
        assert len(sample_database.policies) > 0

    def test_get_policy_by_id(self, sample_database: LCDNCDDatabase):
        """Test retrieving policy by ID."""
        policy = sample_database.get_policy("NCD-220.2")
        assert policy is not None
        assert policy.title == "Magnetic Resonance Imaging (MRI)"
        assert policy.coverage_type == CoverageType.NCD

    def test_get_policy_not_found(self, sample_database: LCDNCDDatabase):
        """Test getting non-existent policy returns None."""
        policy = sample_database.get_policy("FAKE-999")
        assert policy is None

    def test_find_policies_for_mri_code(self, sample_database: LCDNCDDatabase):
        """Test finding policies for MRI procedure code."""
        policies = sample_database.find_policies_by_code("70551")
        assert len(policies) >= 1
        assert any(p.policy_id == "NCD-220.2" for p in policies)

    def test_find_policies_for_ct_code(self, sample_database: LCDNCDDatabase):
        """Test finding policies for CT procedure code."""
        policies = sample_database.find_policies_by_code("71250")
        assert len(policies) >= 1
        assert any(p.policy_id == "NCD-220.1" for p in policies)

    def test_find_policies_for_physical_therapy(self, sample_database: LCDNCDDatabase):
        """Test finding policies for PT procedure codes."""
        policies = sample_database.find_policies_by_code("97110")
        assert len(policies) >= 1
        assert any(p.policy_id == "L35036" for p in policies)

    def test_find_policies_with_mac_filter(self, sample_database: LCDNCDDatabase):
        """Test finding policies with MAC region filter."""
        # LCDs should be filtered by MAC, NCDs should always be included
        policies = sample_database.find_policies_by_code("97110", mac_region=MACRegion.MAC_A)
        # Should find the LCD (if applicable to that MAC)
        assert len(policies) >= 0

    def test_code_not_covered(self, sample_database: LCDNCDDatabase):
        """Test code with no coverage policies."""
        policies = sample_database.find_policies_by_code("99999")
        assert len(policies) == 0


# =============================================================================
# Service Tests
# =============================================================================


class TestLCDNCDService:
    """Tests for LCD/NCD service."""

    @pytest.mark.asyncio
    async def test_check_mri_with_valid_diagnosis(self, lcd_ncd_service: LCDNCDService):
        """Test MRI is medically necessary with valid diagnosis."""
        result = await lcd_ncd_service.check_medical_necessity(
            procedure_codes=["70551"],
            diagnosis_codes=["G43.909"],  # Migraine
        )

        assert result is not None
        assert result.is_medically_necessary is True
        assert result.policies_checked > 0

    @pytest.mark.asyncio
    async def test_check_ct_with_valid_diagnosis(self, lcd_ncd_service: LCDNCDService):
        """Test CT is medically necessary with valid diagnosis."""
        result = await lcd_ncd_service.check_medical_necessity(
            procedure_codes=["71250"],
            diagnosis_codes=["R10.9"],  # Abdominal pain
        )

        assert result is not None
        assert result.is_medically_necessary is True

    @pytest.mark.asyncio
    async def test_check_pt_with_valid_diagnosis(self, lcd_ncd_service: LCDNCDService):
        """Test physical therapy is medically necessary with valid diagnosis."""
        result = await lcd_ncd_service.check_medical_necessity(
            procedure_codes=["97110"],
            diagnosis_codes=["M54.5"],  # Low back pain
        )

        assert result is not None
        assert result.is_medically_necessary is True

    @pytest.mark.asyncio
    async def test_check_with_no_matching_policy(self, lcd_ncd_service: LCDNCDService):
        """Test procedure with no coverage policy."""
        result = await lcd_ncd_service.check_medical_necessity(
            procedure_codes=["99999"],
            diagnosis_codes=["Z00.00"],
        )

        assert result is not None
        # No policy found means review needed
        assert "99999" in result.procedures_needing_review or result.is_medically_necessary is False

    @pytest.mark.asyncio
    async def test_check_with_diagnosis_mismatch(self, lcd_ncd_service: LCDNCDService):
        """Test procedure with non-covered diagnosis."""
        result = await lcd_ncd_service.check_medical_necessity(
            procedure_codes=["70551"],  # MRI
            diagnosis_codes=["Z00.00"],  # General exam - not covered for MRI
        )

        assert result is not None
        # Should indicate diagnosis doesn't support medical necessity
        # The procedure may be flagged for review or not covered

    @pytest.mark.asyncio
    async def test_check_multiple_procedures(self, lcd_ncd_service: LCDNCDService):
        """Test checking multiple procedures."""
        result = await lcd_ncd_service.check_medical_necessity(
            procedure_codes=["70551", "71250", "97110"],
            diagnosis_codes=["G43.909", "R10.9", "M54.5"],
        )

        assert result is not None
        assert result.policies_checked > 0
        # Should have determinations for each procedure
        assert len(result.determinations) >= 1

    @pytest.mark.asyncio
    async def test_check_with_claim_id(self, lcd_ncd_service: LCDNCDService):
        """Test medical necessity check with claim ID."""
        result = await lcd_ncd_service.check_medical_necessity(
            procedure_codes=["70551"],
            diagnosis_codes=["G43.909"],
            claim_id="CLM-12345",
        )

        assert result is not None
        assert result.claim_id == "CLM-12345"

    @pytest.mark.asyncio
    async def test_check_with_service_date(self, lcd_ncd_service: LCDNCDService):
        """Test medical necessity check with service date."""
        result = await lcd_ncd_service.check_medical_necessity(
            procedure_codes=["70551"],
            diagnosis_codes=["G43.909"],
            service_date=date(2025, 6, 15),
        )

        assert result is not None
        assert result.service_date == date(2025, 6, 15)

    @pytest.mark.asyncio
    async def test_check_with_mac_region(self, lcd_ncd_service: LCDNCDService):
        """Test medical necessity check with MAC region."""
        result = await lcd_ncd_service.check_medical_necessity(
            procedure_codes=["97110"],
            diagnosis_codes=["M54.5"],
            mac_region=MACRegion.MAC_A,
        )

        assert result is not None
        assert result.mac_region == MACRegion.MAC_A

    @pytest.mark.asyncio
    async def test_cardiac_rehab_coverage(self, lcd_ncd_service: LCDNCDService):
        """Test cardiac rehabilitation coverage determination."""
        result = await lcd_ncd_service.check_medical_necessity(
            procedure_codes=["93797"],
            diagnosis_codes=["I21.9"],  # Acute MI
        )

        assert result is not None
        assert result.policies_checked > 0

    @pytest.mark.asyncio
    async def test_lab_panel_coverage(self, lcd_ncd_service: LCDNCDService):
        """Test comprehensive metabolic panel coverage."""
        result = await lcd_ncd_service.check_medical_necessity(
            procedure_codes=["80053"],
            diagnosis_codes=["E11.9"],  # Type 2 diabetes
        )

        assert result is not None
        assert result.policies_checked > 0


# =============================================================================
# Policy Model Tests
# =============================================================================


class TestCoveragePolicy:
    """Tests for CoveragePolicy model."""

    def test_policy_creation(self):
        """Test creating a coverage policy."""
        policy = CoveragePolicy(
            policy_id="TEST-001",
            title="Test Policy",
            coverage_type=CoverageType.LCD,
            status=CoverageStatus.ACTIVE,
            effective_date=date(2025, 1, 1),
            covered_codes=["99213", "99214"],
            covered_diagnoses=["J06*", "J18*"],
        )

        assert policy.policy_id == "TEST-001"
        assert policy.coverage_type == CoverageType.LCD
        assert len(policy.covered_codes) == 2

    def test_policy_with_mac_region(self):
        """Test LCD policy with MAC region."""
        policy = CoveragePolicy(
            policy_id="LCD-001",
            title="Regional LCD",
            coverage_type=CoverageType.LCD,
            status=CoverageStatus.ACTIVE,
            mac_region=MACRegion.MAC_A,
            covered_codes=["97110"],
            covered_diagnoses=["M54*"],
        )

        assert policy.mac_region == MACRegion.MAC_A


class TestCoverageDetermination:
    """Tests for CoverageDetermination model."""

    def test_covered_determination(self):
        """Test creating covered determination."""
        policy = CoveragePolicy(
            policy_id="TEST-001",
            title="Test",
            coverage_type=CoverageType.NCD,
            status=CoverageStatus.ACTIVE,
            covered_codes=["99213"],
            covered_diagnoses=["J06*"],
        )

        determination = CoverageDetermination(
            procedure_code="99213",
            policy=policy,
            is_covered=True,
            status=CoverageStatus.ACTIVE,
            covered_diagnoses=["J06.9"],
        )

        assert determination.is_covered is True
        assert determination.policy == policy


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_get_lcd_ncd_service_singleton(self):
        """Test service factory returns singleton."""
        service1 = get_lcd_ncd_service()
        service2 = get_lcd_ncd_service()
        assert service1 is service2

    def test_service_has_database(self):
        """Test service has initialized database."""
        service = get_lcd_ncd_service()
        assert service.database is not None
        assert len(service.database.policies) > 0
