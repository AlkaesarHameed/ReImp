"""
Unit Tests for Eligibility Verification.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Tests:
- X12 270 generation
- X12 271 parsing
- Eligibility service orchestration
- Caching behavior
"""

import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from src.services.edi.x12_270_generator import (
    X12270Generator,
    EligibilityInquiry,
    InquirySubscriber,
    InquiryProvider,
    InquiryPayer,
    InquiryDependent,
    ServiceTypeCode,
)
from src.services.edi.x12_271_parser import (
    X12271Parser,
    EligibilityResponse,
    EligibilityStatus,
    BenefitInfo,
    CoverageLevel,
    InsuranceType,
)
from src.services.edi.eligibility_service import (
    EligibilityService,
    EligibilityRequest,
    EligibilityCheckResult,
    EligibilityCheckStatus,
    EligibilityResultType,
    get_eligibility_service,
)


# =============================================================================
# Sample X12 271 Content
# =============================================================================


SAMPLE_271_ELIGIBLE = """ISA*00*          *00*          *ZZ*PAYER          *ZZ*PROVIDER       *231220*1200*^*00501*000000001*0*P*:~
GS*HB*PAYER*PROVIDER*20231220*1200*1*X*005010X279A1~
ST*271*0001*005010X279A1~
BHT*0022*11*TRN123456*20231220*1200~
HL*1**20*1~
NM1*PR*2*DEMO INSURANCE CO*****PI*DEMOPAYER~
HL*2*1*21*1~
NM1*1P*2*DEMO PROVIDER*****XX*1234567890~
HL*3*2*22*0~
TRN*1*TRACE123*9DEMOID~
NM1*IL*1*DOE*JOHN*M***MI*MEM123456~
DMG*D8*19800115*M~
DTP*346*D8*20230101~
DTP*347*D8*20251231~
EB*1*IND*30**STANDARD PPO PLAN~
EB*C*IND*30***23*500.00~
EB*G*IND*30***23*3000.00~
EB*A*IND*30***23**20~
EB*B*IND*30***23*30~
MSG*MEMBER IS ELIGIBLE FOR STANDARD BENEFITS~
SE*20*0001~
GE*1*1~
IEA*1*000000001~"""


SAMPLE_271_NOT_ELIGIBLE = """ISA*00*          *00*          *ZZ*PAYER          *ZZ*PROVIDER       *231220*1200*^*00501*000000002*0*P*:~
GS*HB*PAYER*PROVIDER*20231220*1200*1*X*005010X279A1~
ST*271*0001*005010X279A1~
BHT*0022*11*TRN789*20231220*1200~
HL*1**20*1~
NM1*PR*2*DEMO INSURANCE CO*****PI*DEMOPAYER~
HL*2*1*21*1~
NM1*1P*2*DEMO PROVIDER*****XX*1234567890~
HL*3*2*22*0~
TRN*1*TRACE789*9DEMOID~
NM1*IL*1*SMITH*JANE****MI*MEM789~
DMG*D8*19900520*F~
EB*6*IND*30**COVERAGE TERMINATED~
DTP*347*D8*20231201~
MSG*COVERAGE WAS TERMINATED ON 12/01/2023~
SE*15*0001~
GE*1*1~
IEA*1*000000002~"""


SAMPLE_271_MEMBER_NOT_FOUND = """ISA*00*          *00*          *ZZ*PAYER          *ZZ*PROVIDER       *231220*1200*^*00501*000000003*0*P*:~
GS*HB*PAYER*PROVIDER*20231220*1200*1*X*005010X279A1~
ST*271*0001*005010X279A1~
BHT*0022*11*TRN000*20231220*1200~
HL*1**20*1~
NM1*PR*2*DEMO INSURANCE CO*****PI*DEMOPAYER~
AAA*N**72~
SE*7*0001~
GE*1*1~
IEA*1*000000003~"""


# =============================================================================
# X12 270 Generator Tests
# =============================================================================


class TestX12270Generator:
    """Test 270 eligibility inquiry generation."""

    def test_generator_initialization(self):
        """Test generator initializes correctly."""
        generator = X12270Generator()
        assert generator is not None
        assert generator.element_sep == "*"
        assert generator.segment_term == "~"

    def test_generate_basic_inquiry(self):
        """Test generating basic eligibility inquiry."""
        generator = X12270Generator()

        inquiry = EligibilityInquiry(
            subscriber=InquirySubscriber(
                member_id="MEM123456",
                first_name="John",
                last_name="Doe",
                date_of_birth=date(1980, 1, 15),
                gender="M",
            ),
            provider=InquiryProvider(
                npi="1234567890",
                name="Demo Provider",
            ),
            payer=InquiryPayer(
                payer_id="DEMOPAYER",
                name="Demo Insurance Co",
            ),
            service_date=date(2023, 12, 20),
        )

        content = generator.generate(inquiry)

        # Should start with ISA
        assert content.startswith("ISA*")

        # Should contain required segments
        assert "GS*HS*" in content  # Functional group (HS for 270/271)
        assert "ST*270*" in content  # Transaction set
        assert "BHT*0022*13*" in content  # Beginning of transaction
        assert "NM1*PR*2*Demo Insurance Co" in content  # Payer
        assert "NM1*1P*2*Demo Provider" in content  # Provider
        assert "NM1*IL*1*Doe*John" in content  # Subscriber
        assert "EQ*30" in content  # Eligibility inquiry
        assert "IEA*" in content  # End of interchange

    def test_generate_with_dependent(self):
        """Test generating inquiry with dependent."""
        generator = X12270Generator()

        inquiry = EligibilityInquiry(
            subscriber=InquirySubscriber(
                member_id="MEM123456",
                first_name="John",
                last_name="Doe",
            ),
            provider=InquiryProvider(
                npi="1234567890",
                name="Provider",
            ),
            payer=InquiryPayer(
                payer_id="PAYER1",
                name="Payer",
            ),
            service_date=date(2023, 12, 20),
            dependent=InquiryDependent(
                first_name="Jane",
                last_name="Doe",
                date_of_birth=date(2010, 5, 1),
            ),
        )

        content = generator.generate(inquiry)

        # Should contain dependent info
        assert "NM1*03*1*Doe*Jane" in content  # Dependent NM1

    def test_generate_with_multiple_service_types(self):
        """Test generating inquiry with multiple service types."""
        generator = X12270Generator()

        inquiry = EligibilityInquiry(
            subscriber=InquirySubscriber(
                member_id="MEM123",
                first_name="Test",
                last_name="Member",
            ),
            provider=InquiryProvider(npi="1234567890", name="Provider"),
            payer=InquiryPayer(payer_id="PAYER", name="Payer"),
            service_date=date(2023, 12, 20),
            service_type_codes=[
                ServiceTypeCode.HEALTH_BENEFIT_PLAN_COVERAGE,
                ServiceTypeCode.MEDICAL_CARE,
                ServiceTypeCode.MENTAL_HEALTH,
            ],
        )

        content = generator.generate(inquiry)

        # Should contain multiple EQ segments
        assert "EQ*30" in content  # Health benefit plan coverage
        assert "EQ*1" in content  # Medical care
        assert "EQ*MH" in content  # Mental health


# =============================================================================
# X12 271 Parser Tests
# =============================================================================


class TestX12271Parser:
    """Test 271 eligibility response parsing."""

    def test_parser_initialization(self):
        """Test parser initializes correctly."""
        parser = X12271Parser()
        assert parser is not None

    def test_parse_eligible_response(self):
        """Test parsing response with eligible status."""
        parser = X12271Parser()
        response = parser.parse(SAMPLE_271_ELIGIBLE)

        assert response.is_eligible is True
        assert response.coverage_active is True
        assert response.eligibility_status == EligibilityStatus.ACTIVE

        # Check subscriber info
        assert response.subscriber is not None
        assert response.subscriber.member_id == "MEM123456"
        assert response.subscriber.first_name == "JOHN"
        assert response.subscriber.last_name == "DOE"

        # Check payer info
        assert response.payer is not None
        assert response.payer.name == "DEMO INSURANCE CO"

    def test_parse_not_eligible_response(self):
        """Test parsing response with terminated coverage."""
        parser = X12271Parser()
        response = parser.parse(SAMPLE_271_NOT_ELIGIBLE)

        assert response.is_eligible is False
        assert response.coverage_active is False
        assert response.eligibility_status == EligibilityStatus.INACTIVE

    def test_parse_member_not_found(self):
        """Test parsing response with AAA rejection."""
        parser = X12271Parser()
        response = parser.parse(SAMPLE_271_MEMBER_NOT_FOUND)

        assert response.is_eligible is False
        assert len(response.aaa_segments) > 0
        assert len(response.errors) > 0

    def test_parse_extracts_benefits(self):
        """Test parsing extracts benefit information."""
        parser = X12271Parser()
        response = parser.parse(SAMPLE_271_ELIGIBLE)

        assert len(response.benefits) > 0

        # Find deductible benefit
        deductible_benefits = [
            b for b in response.benefits
            if b.status == EligibilityStatus.DEDUCTIBLE
        ]
        assert len(deductible_benefits) > 0

    def test_parse_extracts_dates(self):
        """Test parsing extracts date information."""
        parser = X12271Parser()
        response = parser.parse(SAMPLE_271_ELIGIBLE)

        # Should have plan dates
        assert response.plan_begin_date is not None
        assert response.plan_end_date is not None


# =============================================================================
# Eligibility Service Tests
# =============================================================================


class TestEligibilityService:
    """Test eligibility service orchestration."""

    @pytest.fixture
    def eligibility_service(self):
        """Create eligibility service instance."""
        return EligibilityService()

    @pytest.mark.asyncio
    async def test_check_eligibility_success(self, eligibility_service):
        """Test successful eligibility check."""
        request = EligibilityRequest(
            member_id="MEM123456",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1980, 1, 15),
            payer_id="DEMOPAYER",
            payer_name="Demo Insurance",
            service_date=date.today(),
        )

        result = await eligibility_service.check_eligibility(
            request=request,
            tenant_id=uuid4(),
            use_cache=False,
        )

        assert result.status == EligibilityCheckStatus.COMPLETED
        assert result.is_eligible is True
        assert result.member_id == "MEM123456"
        assert result.payer_id == "DEMOPAYER"

    @pytest.mark.asyncio
    async def test_check_eligibility_caching(self, eligibility_service):
        """Test eligibility result caching."""
        request = EligibilityRequest(
            member_id="CACHE_TEST_123",
            first_name="Cache",
            last_name="Test",
            payer_id="PAYER1",
            service_date=date.today(),
        )

        # First call - should not be cached
        result1 = await eligibility_service.check_eligibility(
            request=request,
            tenant_id=uuid4(),
            use_cache=True,
        )
        assert result1.cached is False

        # Second call - should be cached
        result2 = await eligibility_service.check_eligibility(
            request=request,
            tenant_id=uuid4(),
            use_cache=True,
        )
        assert result2.cached is True

    @pytest.mark.asyncio
    async def test_check_eligibility_batch(self, eligibility_service):
        """Test batch eligibility check."""
        requests = [
            EligibilityRequest(
                member_id=f"MEM{i}",
                first_name=f"Test{i}",
                last_name="Member",
                payer_id="PAYER1",
                service_date=date.today(),
            )
            for i in range(3)
        ]

        results = await eligibility_service.check_eligibility_batch(
            requests=requests,
            tenant_id=uuid4(),
            concurrency=2,
        )

        assert len(results) == 3
        for result in results:
            assert result.status == EligibilityCheckStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_verify_for_claim(self, eligibility_service):
        """Test quick eligibility verification for claim."""
        result = await eligibility_service.verify_for_claim(
            member_id="MEM123",
            payer_id="PAYER1",
            service_date=date.today(),
            tenant_id=uuid4(),
        )

        assert result is not None
        assert result.member_id == "MEM123"
        assert result.payer_id == "PAYER1"

    def test_clear_cache(self, eligibility_service):
        """Test clearing eligibility cache."""
        # Add something to cache
        eligibility_service._memory_cache["test_key"] = "test_value"
        assert len(eligibility_service._memory_cache) > 0

        # Clear cache
        eligibility_service.clear_cache()
        assert len(eligibility_service._memory_cache) == 0


# =============================================================================
# Data Model Tests
# =============================================================================


class TestDataModels:
    """Test eligibility data models."""

    def test_inquiry_subscriber(self):
        """Test InquirySubscriber model."""
        subscriber = InquirySubscriber(
            member_id="MEM123",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1980, 1, 15),
            gender="M",
        )

        assert subscriber.member_id == "MEM123"
        assert subscriber.first_name == "John"
        assert subscriber.date_of_birth == date(1980, 1, 15)

    def test_eligibility_inquiry(self):
        """Test EligibilityInquiry model."""
        inquiry = EligibilityInquiry(
            subscriber=InquirySubscriber(
                member_id="MEM123",
                first_name="John",
                last_name="Doe",
            ),
            provider=InquiryProvider(npi="1234567890", name="Provider"),
            payer=InquiryPayer(payer_id="PAYER", name="Payer"),
            service_date=date(2023, 12, 20),
        )

        assert inquiry.subscriber.member_id == "MEM123"
        assert inquiry.provider.npi == "1234567890"
        assert inquiry.service_date == date(2023, 12, 20)

    def test_benefit_info(self):
        """Test BenefitInfo model."""
        benefit = BenefitInfo(
            status=EligibilityStatus.ACTIVE,
            coverage_level=CoverageLevel.INDIVIDUAL,
            service_type_code="30",
            monetary_amount=Decimal("500.00"),
            authorization_required=False,
        )

        assert benefit.status == EligibilityStatus.ACTIVE
        assert benefit.monetary_amount == Decimal("500.00")

    def test_eligibility_request(self):
        """Test EligibilityRequest model."""
        request = EligibilityRequest(
            member_id="MEM123",
            first_name="John",
            last_name="Doe",
            payer_id="PAYER1",
            service_date=date.today(),
        )

        assert request.member_id == "MEM123"
        assert request.payer_id == "PAYER1"
        assert request.service_date == date.today()


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_parse_empty_content(self):
        """Test parsing empty content."""
        parser = X12271Parser()

        with pytest.raises(Exception):
            parser.parse("")

    def test_parse_invalid_content(self):
        """Test parsing invalid X12 content."""
        parser = X12271Parser()

        with pytest.raises(Exception):
            parser.parse("INVALID CONTENT")

    def test_service_type_code_enum(self):
        """Test ServiceTypeCode enum values."""
        assert ServiceTypeCode.MEDICAL_CARE.value == "1"
        assert ServiceTypeCode.HEALTH_BENEFIT_PLAN_COVERAGE.value == "30"
        assert ServiceTypeCode.MENTAL_HEALTH.value == "MH"

    def test_eligibility_status_enum(self):
        """Test EligibilityStatus enum values."""
        assert EligibilityStatus.ACTIVE.value == "1"
        assert EligibilityStatus.INACTIVE.value == "6"
        assert EligibilityStatus.DEDUCTIBLE.value == "C"
        assert EligibilityStatus.COPAYMENT.value == "B"

    @pytest.mark.asyncio
    async def test_service_handles_exception(self):
        """Test service handles exceptions gracefully."""
        service = EligibilityService()

        # Create request with minimal info
        request = EligibilityRequest(
            member_id="TEST",
            first_name="Test",
            last_name="User",
            payer_id="INVALID",
        )

        # Should not raise, should return failed result
        result = await service.check_eligibility(
            request=request,
            tenant_id=uuid4(),
            use_cache=False,
        )

        # Result should be returned even if processing had issues
        assert result is not None
        assert result.member_id == "TEST"


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """Test factory functions."""

    def test_get_eligibility_service(self):
        """Test getting eligibility service singleton."""
        service1 = get_eligibility_service()
        service2 = get_eligibility_service()

        assert service1 is service2  # Same instance
        assert isinstance(service1, EligibilityService)
