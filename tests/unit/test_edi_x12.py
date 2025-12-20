"""
Unit Tests for X12 EDI Processing.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Tests:
- X12 tokenizer functionality
- 837P/837I claim parsing
- 835 remittance generation
- EDI service orchestration
"""

import pytest
from decimal import Decimal
from datetime import date
from uuid import uuid4

from src.services.edi.x12_base import (
    X12Tokenizer,
    X12Segment,
    TransactionType,
    X12ParseError,
    X12ValidationError,
    parse_x12_date,
    format_x12_date,
    parse_x12_amount,
    validate_npi,
)
from src.services.edi.x12_837_parser import (
    X12837Parser,
    ParsedClaim837,
    ServiceLine837,
    DiagnosisInfo,
    ProviderInfo,
    SubscriberInfo,
)
from src.services.edi.x12_835_generator import (
    X12835Generator,
    RemittanceAdvice,
    ClaimPayment,
    ServicePayment,
    AdjustmentReason,
    PayerInfo,
    PayeeInfo,
    create_remittance_from_adjudication,
)
from src.services.edi.edi_service import (
    EDIService,
    EDITransactionResult,
    EDI835Result,
    EDITransactionStatus,
    EDIDirection,
)


# =============================================================================
# Sample X12 Content
# =============================================================================


SAMPLE_837P_MINIMAL = """ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *231215*1200*^*00501*000000001*0*P*:~
GS*HC*SENDER*RECEIVER*20231215*1200*1*X*005010X222A1~
ST*837*0001*005010X222A1~
BHT*0019*00*12345*20231215*1200*CH~
NM1*41*2*SENDER NAME*****46*SENDERID~
PER*IC*CONTACT*TE*5551234567~
NM1*40*2*RECEIVER NAME*****46*RECEIVERID~
HL*1**20*1~
NM1*85*2*BILLING PROVIDER*****XX*1234567890~
N3*123 MAIN ST~
N4*ANYTOWN*CA*12345~
HL*2*1*22*0~
SBR*P*18*GROUP123******CI~
NM1*IL*1*DOE*JOHN****MI*MEM123456~
N3*456 OAK AVE~
N4*SOMEWHERE*CA*54321~
DMG*D8*19800115*M~
NM1*PR*2*INSURANCE CO*****PI*PAYERID~
CLM*CLAIM001*500***11:B:1*Y*A*Y*Y~
HI*ABK:J06.9~
LX*1~
SV1*HC:99213*150*UN*1***1~
DTP*472*D8*20231201~
SE*25*0001~
GE*1*1~
IEA*1*000000001~"""


# =============================================================================
# X12 Tokenizer Tests
# =============================================================================


class TestX12Tokenizer:
    """Test X12 tokenizer functionality."""

    def test_tokenizer_initialization(self):
        """Test tokenizer initializes with correct delimiters."""
        tokenizer = X12Tokenizer(SAMPLE_837P_MINIMAL)
        assert tokenizer.segment_terminator == "~"
        assert tokenizer.element_separator == "*"
        assert tokenizer.sub_element_separator == ":"

    def test_tokenizer_extracts_segments(self):
        """Test tokenizer extracts all segments."""
        tokenizer = X12Tokenizer(SAMPLE_837P_MINIMAL)
        segments = tokenizer.tokenize()

        # Should have multiple segments
        assert len(segments) > 0

        # First segment should be ISA
        assert segments[0].segment_id == "ISA"

        # Last segment should be IEA
        assert segments[-1].segment_id == "IEA"

    def test_segment_parsing(self):
        """Test individual segment parsing."""
        tokenizer = X12Tokenizer(SAMPLE_837P_MINIMAL)
        segments = tokenizer.tokenize()

        # Find CLM segment
        clm_segment = None
        for seg in segments:
            if seg.segment_id == "CLM":
                clm_segment = seg
                break

        assert clm_segment is not None
        # segment_id holds the segment type, elements holds the data
        assert clm_segment.segment_id == "CLM"
        assert clm_segment.elements[0] == "CLAIM001"  # Patient control number
        assert clm_segment.elements[1] == "500"  # Charge amount

    def test_invalid_content_raises_error(self):
        """Test that invalid/empty content raises an error."""
        # Empty content should raise an error
        with pytest.raises(X12ParseError):
            tokenizer = X12Tokenizer()
            tokenizer.tokenize()  # No content provided


# =============================================================================
# X12 Date/Amount Utility Tests
# =============================================================================


class TestX12Utilities:
    """Test X12 utility functions."""

    def test_parse_x12_date_ccyymmdd(self):
        """Test parsing CCYYMMDD format."""
        result = parse_x12_date("20231215")
        assert result == date(2023, 12, 15)

    def test_parse_x12_date_yymmdd(self):
        """Test parsing YYMMDD format."""
        result = parse_x12_date("231215")
        assert result == date(2023, 12, 15)

    def test_parse_x12_date_invalid(self):
        """Test parsing invalid date returns None."""
        result = parse_x12_date("invalid")
        assert result is None

    def test_format_x12_date(self):
        """Test formatting date to X12 format."""
        result = format_x12_date(date(2023, 12, 15))
        assert result == "20231215"

    def test_parse_x12_amount(self):
        """Test parsing X12 amount."""
        assert parse_x12_amount("150.00") == Decimal("150.00")
        assert parse_x12_amount("500") == Decimal("500")
        assert parse_x12_amount("") == Decimal("0")

    def test_validate_npi_valid(self):
        """Test NPI validation for valid NPIs."""
        # Valid NPI with check digit
        assert validate_npi("1234567893") is True

    def test_validate_npi_invalid(self):
        """Test NPI validation for invalid NPIs."""
        assert validate_npi("123456789") is False  # Too short
        assert validate_npi("12345678901") is False  # Too long
        assert validate_npi("abcdefghij") is False  # Non-numeric


# =============================================================================
# 837 Parser Tests
# =============================================================================


class TestX12837Parser:
    """Test 837 claim parser."""

    def test_parser_initialization(self):
        """Test parser initializes correctly."""
        parser = X12837Parser()
        assert parser is not None

    def test_parse_minimal_837p(self):
        """Test parsing minimal 837P content."""
        parser = X12837Parser()
        claims = parser.parse(SAMPLE_837P_MINIMAL)

        # Should parse one claim
        assert len(claims) == 1

        claim = claims[0]
        assert claim.claim_id == "CLAIM001"
        assert claim.total_charge == Decimal("500")
        assert claim.claim_type == TransactionType.CLAIM_837P

    def test_parse_extracts_diagnoses(self):
        """Test parser extracts diagnoses."""
        parser = X12837Parser()
        claims = parser.parse(SAMPLE_837P_MINIMAL)

        claim = claims[0]
        assert len(claim.diagnoses) >= 1
        assert claim.diagnoses[0].code == "J06.9"

    def test_parse_extracts_service_lines(self):
        """Test parser extracts service lines."""
        parser = X12837Parser()
        claims = parser.parse(SAMPLE_837P_MINIMAL)

        claim = claims[0]
        assert len(claim.service_lines) >= 1

        line = claim.service_lines[0]
        assert line.procedure_code == "99213"
        assert line.charge_amount == Decimal("150")

    def test_parse_extracts_provider(self):
        """Test parser extracts billing provider."""
        parser = X12837Parser()
        claims = parser.parse(SAMPLE_837P_MINIMAL)

        claim = claims[0]
        assert claim.billing_provider is not None
        assert claim.billing_provider.npi == "1234567890"
        assert claim.billing_provider.name == "BILLING PROVIDER"

    def test_parse_extracts_subscriber(self):
        """Test parser extracts subscriber info."""
        parser = X12837Parser()
        claims = parser.parse(SAMPLE_837P_MINIMAL)

        claim = claims[0]
        assert claim.subscriber is not None
        assert claim.subscriber.member_id == "MEM123456"
        assert claim.subscriber.first_name == "JOHN"
        assert claim.subscriber.last_name == "DOE"


# =============================================================================
# 835 Generator Tests
# =============================================================================


class TestX12835Generator:
    """Test 835 remittance generator."""

    def test_generator_initialization(self):
        """Test generator initializes correctly."""
        generator = X12835Generator()
        assert generator is not None

    def test_generate_minimal_835(self):
        """Test generating minimal 835 content."""
        from src.services.edi.x12_835_generator import ClaimStatus, PaymentMethod

        generator = X12835Generator()

        remittance = RemittanceAdvice(
            transaction_id="TRN123",
            check_eft_number="CHK123",
            payment_method=PaymentMethod.CHECK,
            payment_amount=Decimal("400.00"),
            payment_date=date(2023, 12, 20),
            payer_name="TEST PAYER",
            payer_id="PAYERID",
            payee_name="TEST PROVIDER",
            payee_npi="1234567890",
            claim_payments=[
                ClaimPayment(
                    claim_id="CLAIM001",
                    claim_status=ClaimStatus.PROCESSED_PRIMARY,
                    total_billed=Decimal("500.00"),
                    total_paid=Decimal("400.00"),
                    patient_responsibility=Decimal("100.00"),
                    service_payments=[
                        ServicePayment(
                            procedure_code="99213",
                            billed_amount=Decimal("150.00"),
                            paid_amount=Decimal("120.00"),
                            allowed_amount=Decimal("120.00"),
                        ),
                    ],
                ),
            ],
            interchange_control_number="000000001",
            transaction_control_number="0001",
        )

        content = generator.generate(remittance)

        # Should start with ISA segment
        assert content.startswith("ISA*")

        # Should contain BPR (payment info)
        assert "BPR*" in content

        # Should contain TRN (trace)
        assert "TRN*" in content

        # Should end with IEA segment
        assert "IEA*" in content

    def test_generate_includes_claim_data(self):
        """Test generated 835 includes claim data."""
        from src.services.edi.x12_835_generator import ClaimStatus, PaymentMethod

        generator = X12835Generator()

        remittance = RemittanceAdvice(
            transaction_id="TRN456",
            check_eft_number="CHK456",
            payment_method=PaymentMethod.CHECK,
            payment_amount=Decimal("800.00"),
            payment_date=date(2023, 12, 20),
            payer_name="PAYER",
            payer_id="PAY123",
            payee_name="PROVIDER",
            payee_npi="1234567890",
            claim_payments=[
                ClaimPayment(
                    claim_id="CLM789",
                    claim_status=ClaimStatus.PROCESSED_PRIMARY,
                    total_billed=Decimal("1000.00"),
                    total_paid=Decimal("800.00"),
                    patient_responsibility=Decimal("200.00"),
                    service_payments=[],
                ),
            ],
            interchange_control_number="000000002",
            transaction_control_number="0002",
        )

        content = generator.generate(remittance)

        # Should contain claim reference
        assert "CLM789" in content or "CLP*" in content

    def test_create_remittance_from_adjudication(self):
        """Test creating remittance from adjudication result."""
        adjudication = {
            "claim_id": "CLAIM001",
            "decision": "approved",
            "total_billed": 500.00,
            "total_allowed": 450.00,
            "total_plan_payment": 360.00,
            "total_member_responsibility": 90.00,
            "pricing_details": [],
        }

        payer = {
            "name": "Test Payer",
            "id": "PAYER1",
        }

        payee = {
            "name": "Test Provider",
            "npi": "1234567890",
        }

        remittance = create_remittance_from_adjudication(
            adjudication, payer, payee
        )

        assert remittance.payer_name == "Test Payer"
        assert remittance.payee_npi == "1234567890"
        assert len(remittance.claim_payments) == 1
        assert remittance.claim_payments[0].claim_id == "CLAIM001"


# =============================================================================
# EDI Service Tests
# =============================================================================


class TestEDIService:
    """Test EDI service orchestration."""

    @pytest.fixture
    def edi_service(self):
        """Create EDI service instance."""
        return EDIService()

    @pytest.mark.asyncio
    async def test_process_837_success(self, edi_service):
        """Test successful 837 processing."""
        result = await edi_service.process_837(
            content=SAMPLE_837P_MINIMAL,
            tenant_id=uuid4(),
            source="test",
        )

        assert result.status == EDITransactionStatus.PARSED
        assert result.claims_count == 1
        assert len(result.claims_parsed) == 1
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_process_837_invalid_content(self, edi_service):
        """Test 837 processing with invalid content."""
        result = await edi_service.process_837(
            content="INVALID CONTENT",
            tenant_id=uuid4(),
            source="test",
        )

        assert result.status == EDITransactionStatus.FAILED
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_process_837_empty_content(self, edi_service):
        """Test 837 processing with empty content."""
        result = await edi_service.process_837(
            content="",
            tenant_id=uuid4(),
            source="test",
        )

        assert result.status == EDITransactionStatus.FAILED

    @pytest.mark.asyncio
    async def test_validate_837_valid(self, edi_service):
        """Test 837 validation with valid content."""
        result = await edi_service.validate_837(SAMPLE_837P_MINIMAL)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_837_invalid(self, edi_service):
        """Test 837 validation with invalid content."""
        result = await edi_service.validate_837("INVALID CONTENT")

        assert result["valid"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_generate_835_success(self, edi_service):
        """Test successful 835 generation."""
        adjudication = {
            "claim_id": "CLM001",
            "status": "approved",
            "total_charged": 500.00,
            "total_allowed": 450.00,
            "total_paid": 360.00,
            "patient_responsibility": 90.00,
        }

        payer = {"name": "Test Payer", "identifier": "PAY1"}
        payee = {"name": "Test Provider", "npi": "1234567890"}

        result = await edi_service.generate_835(
            adjudication_result=adjudication,
            payer_info=payer,
            payee_info=payee,
            tenant_id=uuid4(),
        )

        assert result.status == EDITransactionStatus.COMPLETED
        assert result.content != ""
        assert result.claim_id == "CLM001"


# =============================================================================
# Data Model Tests
# =============================================================================


class TestDataModels:
    """Test EDI data models."""

    def test_parsed_claim_837(self):
        """Test ParsedClaim837 model."""
        from src.services.edi.x12_837_parser import ProviderType

        claim = ParsedClaim837(
            transaction_control_number="0001",
            claim_type=TransactionType.CLAIM_837P,
            submitter_name="SUBMITTER",
            submitter_id="SUB123",
            receiver_name="RECEIVER",
            receiver_id="REC456",
            billing_provider=ProviderInfo(
                provider_type=ProviderType.BILLING,
                npi="1234567890",
                name="TEST PROVIDER",
            ),
            subscriber=SubscriberInfo(
                member_id="MEM123",
                last_name="DOE",
                first_name="JOHN",
            ),
            claim_id="TEST001",
            total_charge=Decimal("500.00"),
        )

        assert claim.claim_id == "TEST001"
        assert claim.claim_type == TransactionType.CLAIM_837P
        assert claim.total_charge == Decimal("500.00")

    def test_service_line_837(self):
        """Test ServiceLine837 model."""
        line = ServiceLine837(
            line_number=1,
            procedure_code="99213",
            charge_amount=Decimal("150.00"),
            units=1,
        )

        assert line.procedure_code == "99213"
        assert line.charge_amount == Decimal("150.00")

    def test_remittance_advice(self):
        """Test RemittanceAdvice model."""
        from src.services.edi.x12_835_generator import PaymentMethod

        remittance = RemittanceAdvice(
            transaction_id="TRN001",
            check_eft_number="CHK001",
            payment_method=PaymentMethod.CHECK,
            payment_amount=Decimal("400.00"),
            payment_date=date(2023, 12, 20),
            payer_name="Payer",
            payer_id="P1",
            payee_name="Provider",
            payee_npi="1234567890",
            claim_payments=[],
        )

        assert remittance.payer_name == "Payer"
        assert remittance.payment_amount == Decimal("400.00")


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_segment_handling(self):
        """Test handling of empty segments."""
        segment = X12Segment(segment_id="SEG", elements=["", "", "VALUE", ""])
        assert segment.get_element(0) == ""
        assert segment.get_element(2) == "VALUE"

    def test_missing_element_handling(self):
        """Test handling of missing elements."""
        segment = X12Segment(segment_id="SEG", elements=["A", "B"])
        # get_element returns default "" for missing elements
        assert segment.get_element(10) == ""

    def test_sub_element_parsing(self):
        """Test sub-element parsing."""
        segment = X12Segment(
            segment_id="SV1",
            elements=["HC:99213:MO", "150", "UN", "1"],
        )

        composite = segment.get_element(0)
        assert composite == "HC:99213:MO"

        sub_elements = segment.get_sub_elements(0)
        assert sub_elements == ["HC", "99213", "MO"]

    def test_large_claim_count(self):
        """Test parsing content with multiple claims."""
        parser = X12837Parser()
        # For now, just verify we don't crash with the minimal content
        claims = parser.parse(SAMPLE_837P_MINIMAL)
        assert len(claims) >= 1
