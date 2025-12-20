"""
X12 270 Eligibility Inquiry Generator.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Generates HIPAA 5010 compliant X12 270 eligibility inquiry transactions.
Used to request eligibility and benefit information from payers.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from enum import Enum

from src.services.edi.x12_base import format_x12_date


# =============================================================================
# Enums
# =============================================================================


class ServiceTypeCode(str, Enum):
    """X12 service type codes for eligibility inquiry."""
    MEDICAL_CARE = "1"
    SURGICAL = "2"
    CONSULTATION = "3"
    DIAGNOSTIC_XRAY = "4"
    DIAGNOSTIC_LAB = "5"
    RADIATION_THERAPY = "6"
    ANESTHESIA = "7"
    SURGICAL_ASSISTANCE = "8"
    HOSPITAL_INPATIENT = "48"
    HOSPITAL_OUTPATIENT = "50"
    EMERGENCY_SERVICES = "86"
    URGENT_CARE = "UC"
    PHARMACY = "88"
    MENTAL_HEALTH = "MH"
    VISION = "VIS"
    DENTAL = "35"
    HEALTH_BENEFIT_PLAN_COVERAGE = "30"


class EligibilityInquiryType(str, Enum):
    """Type of eligibility inquiry."""
    ELIGIBILITY_ONLY = "eligibility"
    BENEFITS = "benefits"
    BOTH = "both"


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class InquirySubscriber:
    """Subscriber information for eligibility inquiry."""
    member_id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None  # M, F, U
    group_number: Optional[str] = None
    ssn: Optional[str] = None  # Last 4 digits only for matching


@dataclass
class InquiryDependent:
    """Dependent information for eligibility inquiry."""
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    relationship: Optional[str] = None  # 01=Spouse, 19=Child, etc.


@dataclass
class InquiryProvider:
    """Provider information for eligibility inquiry."""
    npi: str
    name: str
    tax_id: Optional[str] = None
    entity_type: str = "2"  # 1=Person, 2=Organization


@dataclass
class InquiryPayer:
    """Payer information for eligibility inquiry."""
    payer_id: str
    name: str


@dataclass
class EligibilityInquiry:
    """Complete eligibility inquiry request."""
    # Required
    subscriber: InquirySubscriber
    provider: InquiryProvider
    payer: InquiryPayer
    service_date: date

    # Optional
    dependent: Optional[InquiryDependent] = None
    service_type_codes: List[ServiceTypeCode] = field(default_factory=lambda: [ServiceTypeCode.HEALTH_BENEFIT_PLAN_COVERAGE])
    inquiry_type: EligibilityInquiryType = EligibilityInquiryType.BOTH

    # Control numbers (auto-generated if not provided)
    interchange_control_number: Optional[str] = None
    group_control_number: Optional[str] = None
    transaction_control_number: Optional[str] = None

    # Trace
    trace_number: Optional[str] = None


# =============================================================================
# Generator
# =============================================================================


class X12270Generator:
    """
    X12 270 Eligibility Inquiry Generator.

    Generates HIPAA 5010 compliant 270 transactions for
    requesting member eligibility and benefit information.

    Usage:
        generator = X12270Generator()
        inquiry = EligibilityInquiry(
            subscriber=InquirySubscriber(...),
            provider=InquiryProvider(...),
            payer=InquiryPayer(...),
            service_date=date.today(),
        )
        content = generator.generate(inquiry)
    """

    def __init__(
        self,
        element_separator: str = "*",
        segment_terminator: str = "~",
        sub_element_separator: str = ":",
    ):
        self.element_sep = element_separator
        self.segment_term = segment_terminator
        self.sub_element_sep = sub_element_separator

    def generate(self, inquiry: EligibilityInquiry) -> str:
        """
        Generate X12 270 eligibility inquiry.

        Args:
            inquiry: EligibilityInquiry object with all required data

        Returns:
            X12 270 content string
        """
        segments = []

        # Generate control numbers if not provided
        isa_control = inquiry.interchange_control_number or self._generate_control_number()
        gs_control = inquiry.group_control_number or "1"
        st_control = inquiry.transaction_control_number or "0001"

        # ISA - Interchange Control Header
        segments.append(self._build_isa(inquiry, isa_control))

        # GS - Functional Group Header
        segments.append(self._build_gs(inquiry, gs_control))

        # ST - Transaction Set Header
        segments.append(self._build_st(st_control))

        # BHT - Beginning of Hierarchical Transaction
        segments.append(self._build_bht(inquiry))

        # HL*1 - Information Source Level (Payer)
        segments.append(self._segment("HL", "1", "", "20", "1"))

        # Loop 2100A - Information Source Name (Payer)
        segments.append(self._build_payer_nm1(inquiry.payer))

        # HL*2 - Information Receiver Level (Provider)
        segments.append(self._segment("HL", "2", "1", "21", "1"))

        # Loop 2100B - Information Receiver Name (Provider)
        segments.extend(self._build_provider_loop(inquiry.provider))

        # HL*3 - Subscriber Level
        has_dependent = inquiry.dependent is not None
        segments.append(self._segment("HL", "3", "2", "22", "1" if has_dependent else "0"))

        # TRN - Trace (optional)
        if inquiry.trace_number:
            segments.append(self._segment("TRN", "1", inquiry.trace_number, "9ORIGINID"))

        # Loop 2100C - Subscriber Name
        segments.extend(self._build_subscriber_loop(inquiry.subscriber))

        # EQ - Eligibility or Benefit Inquiry
        for service_type in inquiry.service_type_codes:
            segments.append(self._segment("EQ", service_type.value))

        # DTP - Service Date
        segments.append(self._segment("DTP", "291", "D8", format_x12_date(inquiry.service_date)))

        # Dependent Level (if present)
        if inquiry.dependent:
            segments.append(self._segment("HL", "4", "3", "23", "0"))
            segments.extend(self._build_dependent_loop(inquiry.dependent))

            # EQ for dependent
            for service_type in inquiry.service_type_codes:
                segments.append(self._segment("EQ", service_type.value))

            segments.append(self._segment("DTP", "291", "D8", format_x12_date(inquiry.service_date)))

        # SE - Transaction Set Trailer
        segment_count = len(segments) + 1  # +1 for SE itself
        segments.append(self._segment("SE", str(segment_count), st_control))

        # GE - Functional Group Trailer
        segments.append(self._segment("GE", "1", gs_control))

        # IEA - Interchange Control Trailer
        segments.append(self._segment("IEA", "1", isa_control.zfill(9)))

        return self.segment_term.join(segments) + self.segment_term

    def _segment(self, *elements) -> str:
        """Build a segment from elements."""
        return self.element_sep.join(elements)

    def _build_isa(self, inquiry: EligibilityInquiry, control_number: str) -> str:
        """Build ISA segment."""
        now = datetime.now()
        return self._segment(
            "ISA",
            "00",  # Authorization Info Qualifier
            " " * 10,  # Authorization Info
            "00",  # Security Info Qualifier
            " " * 10,  # Security Info
            "ZZ",  # Sender ID Qualifier
            inquiry.provider.npi.ljust(15),  # Sender ID
            "ZZ",  # Receiver ID Qualifier
            inquiry.payer.payer_id.ljust(15),  # Receiver ID
            now.strftime("%y%m%d"),  # Date
            now.strftime("%H%M"),  # Time
            "^",  # Repetition Separator
            "00501",  # Version
            control_number.zfill(9),  # Control Number
            "0",  # Acknowledgment Requested
            "P",  # Usage Indicator (P=Production, T=Test)
            self.sub_element_sep,  # Sub-element Separator
        )

    def _build_gs(self, inquiry: EligibilityInquiry, control_number: str) -> str:
        """Build GS segment."""
        now = datetime.now()
        return self._segment(
            "GS",
            "HS",  # Functional ID Code (HS=270/271)
            inquiry.provider.npi,  # Sender Code
            inquiry.payer.payer_id,  # Receiver Code
            now.strftime("%Y%m%d"),  # Date
            now.strftime("%H%M"),  # Time
            control_number,  # Group Control Number
            "X",  # Responsible Agency Code
            "005010X279A1",  # Version
        )

    def _build_st(self, control_number: str) -> str:
        """Build ST segment."""
        return self._segment(
            "ST",
            "270",  # Transaction Set ID
            control_number,  # Control Number
            "005010X279A1",  # Implementation Convention Reference
        )

    def _build_bht(self, inquiry: EligibilityInquiry) -> str:
        """Build BHT segment."""
        now = datetime.now()
        return self._segment(
            "BHT",
            "0022",  # Hierarchical Structure Code
            "13",  # Transaction Set Purpose Code (13=Request)
            inquiry.trace_number or f"TRN{now.strftime('%Y%m%d%H%M%S')}",  # Reference ID
            now.strftime("%Y%m%d"),  # Date
            now.strftime("%H%M"),  # Time
        )

    def _build_payer_nm1(self, payer: InquiryPayer) -> str:
        """Build payer NM1 segment."""
        return self._segment(
            "NM1",
            "PR",  # Entity ID Code (Payer)
            "2",  # Entity Type (Organization)
            payer.name[:60],  # Name
            "",  # First Name (empty for org)
            "",  # Middle Name
            "",  # Prefix
            "",  # Suffix
            "PI",  # ID Code Qualifier
            payer.payer_id,  # ID Code
        )

    def _build_provider_loop(self, provider: InquiryProvider) -> List[str]:
        """Build provider loop segments."""
        segments = []

        # NM1 - Provider Name
        if provider.entity_type == "1":
            # Person
            name_parts = provider.name.split(" ", 1)
            last_name = name_parts[0] if name_parts else provider.name
            first_name = name_parts[1] if len(name_parts) > 1 else ""
            segments.append(self._segment(
                "NM1",
                "1P",  # Provider
                "1",  # Person
                last_name[:60],
                first_name[:35],
                "",  # Middle
                "",  # Prefix
                "",  # Suffix
                "XX",  # NPI
                provider.npi,
            ))
        else:
            # Organization
            segments.append(self._segment(
                "NM1",
                "1P",  # Provider
                "2",  # Organization
                provider.name[:60],
                "",  # First Name
                "",  # Middle
                "",  # Prefix
                "",  # Suffix
                "XX",  # NPI
                provider.npi,
            ))

        return segments

    def _build_subscriber_loop(self, subscriber: InquirySubscriber) -> List[str]:
        """Build subscriber loop segments."""
        segments = []

        # NM1 - Subscriber Name
        segments.append(self._segment(
            "NM1",
            "IL",  # Insured/Subscriber
            "1",  # Person
            subscriber.last_name[:60],
            subscriber.first_name[:35],
            "",  # Middle
            "",  # Prefix
            "",  # Suffix
            "MI",  # Member ID
            subscriber.member_id,
        ))

        # DMG - Demographic Information (optional but recommended)
        if subscriber.date_of_birth or subscriber.gender:
            dob = format_x12_date(subscriber.date_of_birth) if subscriber.date_of_birth else ""
            gender = subscriber.gender or ""
            segments.append(self._segment("DMG", "D8", dob, gender))

        return segments

    def _build_dependent_loop(self, dependent: InquiryDependent) -> List[str]:
        """Build dependent loop segments."""
        segments = []

        # NM1 - Dependent Name
        segments.append(self._segment(
            "NM1",
            "03",  # Dependent
            "1",  # Person
            dependent.last_name[:60],
            dependent.first_name[:35],
            "",  # Middle
            "",  # Prefix
            "",  # Suffix
        ))

        # DMG - Demographic Information
        if dependent.date_of_birth or dependent.gender:
            dob = format_x12_date(dependent.date_of_birth) if dependent.date_of_birth else ""
            gender = dependent.gender or ""
            segments.append(self._segment("DMG", "D8", dob, gender))

        return segments

    def _generate_control_number(self) -> str:
        """Generate a unique control number."""
        from uuid import uuid4
        return str(uuid4().int)[:9]
