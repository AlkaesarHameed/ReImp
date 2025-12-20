"""
X12 271 Eligibility Response Parser.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Parses HIPAA 5010 compliant X12 271 eligibility response transactions.
Extracts eligibility status, coverage details, and benefit information.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from enum import Enum

from src.services.edi.x12_base import (
    X12Tokenizer,
    X12Segment,
    X12ParseError,
    parse_x12_date,
    parse_x12_amount,
)


# =============================================================================
# Enums
# =============================================================================


class EligibilityStatus(str, Enum):
    """Eligibility status codes from EB01."""
    ACTIVE = "1"  # Active Coverage
    ACTIVE_FULL_RISK = "2"  # Active - Full Risk Capitation
    ACTIVE_SERVICES = "3"  # Active - Services Capitated
    ACTIVE_SERVICES_PRIMARY = "4"  # Active - Services Capitated Primary Care
    ACTIVE_PENDING = "5"  # Active - Pending Investigation
    INACTIVE = "6"  # Inactive
    INACTIVE_PENDING = "7"  # Inactive - Pending Eligibility Update
    INACTIVE_PENDING_INVESTIGATION = "8"  # Inactive - Pending Investigation
    COINSURANCE = "A"
    COPAYMENT = "B"
    DEDUCTIBLE = "C"
    BENEFIT_DESCRIPTION = "CB"
    COVERAGE_BASIS = "D"
    EXCLUSIONS = "E"
    LIMITATIONS = "F"
    OUT_OF_POCKET_STOP_LOSS = "G"
    UNLIMITED = "H"
    NON_COVERED = "I"
    COST_CONTAINMENT = "J"
    RESERVE = "K"
    PRIMARY_CARE_PROVIDER = "L"
    PRE_EXISTING_CONDITION = "M"
    SERVICES_RESTRICTED = "MC"
    MANAGED_CARE_COORDINATOR = "N"
    NOT_DEEMED_MEDICAL_NECESSITY = "O"
    BENEFIT_DISCLAIMER = "P"
    SECOND_SURGICAL_OPINION = "Q"
    OTHER_UNLISTED = "R"
    PRIOR_YEAR_HISTORY = "S"
    CARD_REPORTED_LOST = "T"
    CONTACT_PAYER = "U"
    CANNOT_PROCESS = "V"
    RESERVED_NATIONAL = "W"
    HEALTH_CARE_FACILITY = "X"
    SPEND_DOWN = "Y"


class CoverageLevel(str, Enum):
    """Coverage level codes from EB03."""
    CHILDREN_ONLY = "CHD"
    DEPENDENTS_ONLY = "DEP"
    EMPLOYEE_AND_CHILDREN = "ECH"
    EMPLOYEE_ONLY = "EMP"
    EMPLOYEE_AND_SPOUSE = "ESP"
    FAMILY = "FAM"
    INDIVIDUAL = "IND"
    SPOUSE_AND_CHILDREN = "SPC"
    SPOUSE_ONLY = "SPO"


class InsuranceType(str, Enum):
    """Insurance type codes from EB04."""
    MEDICARE_SECONDARY_WORKING = "12"
    MEDICARE_SECONDARY_ESRD = "13"
    MEDICARE_SECONDARY_AUTO = "14"
    MEDICARE_SECONDARY_WORKERS_COMP = "15"
    MEDICARE_SECONDARY_BLACK_LUNG = "16"
    MEDICARE_SECONDARY_VA = "41"
    MEDICARE_SECONDARY_DISABLED = "42"
    MEDICARE_SECONDARY_OTHER = "43"
    MEDICARE_PART_A = "MA"
    MEDICARE_PART_B = "MB"
    MEDICAID = "MC"
    CHAMPUS = "CH"
    COMMERCIAL = "C1"
    HMO = "HM"
    PPO = "PR"
    POS = "PS"
    EPO = "EP"
    INDEMNITY = "IN"
    HMO_MEDICARE_RISK = "HN"
    MEDICARE_SUPPLEMENTAL = "MP"
    OTHER = "OT"


class TimePeriod(str, Enum):
    """Time period qualifier from EB06."""
    HOUR = "1"
    DAY = "6"
    WEEK = "7"
    MONTH = "21"
    YEAR = "22"
    VISIT = "23"
    LIFETIME = "24"
    ADMISSION = "25"
    EPISODE = "27"
    CALENDAR_YEAR = "29"
    PLAN_YEAR = "32"
    SERVICE_YEAR = "33"
    REMAINING = "35"


class QuantityQualifier(str, Enum):
    """Quantity qualifier from EB09."""
    MINIMUM = "99"
    MAXIMUM = "VS"
    COVERED = "CA"
    DEDUCTIBLE_BLOOD = "CE"
    VISITS = "DB"
    UNITS = "DY"
    NUMBER_PROVIDERS = "HS"
    YEARS = "LA"
    LIFETIME_RESERVE_ACTUAL = "LE"
    MONTH = "MN"
    NOT_REPLACED_BLOOD = "P6"
    PINTS = "QA"
    TRUE_OUT_OF_POCKET = "S7"
    OUTLIER_DAYS = "S8"


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class BenefitAmount:
    """Monetary benefit information."""
    amount: Decimal
    time_period: Optional[TimePeriod] = None
    in_network: bool = True
    description: Optional[str] = None


@dataclass
class BenefitQuantity:
    """Quantity-based benefit information."""
    quantity: Decimal
    qualifier: Optional[QuantityQualifier] = None
    time_period: Optional[TimePeriod] = None
    description: Optional[str] = None


@dataclass
class BenefitInfo:
    """Individual benefit/eligibility information from EB segment."""
    status: EligibilityStatus
    coverage_level: Optional[CoverageLevel] = None
    insurance_type: Optional[InsuranceType] = None
    service_type_code: Optional[str] = None
    service_type_description: Optional[str] = None
    time_period: Optional[TimePeriod] = None

    # Amounts
    monetary_amount: Optional[Decimal] = None
    percent: Optional[Decimal] = None

    # Quantities
    quantity: Optional[Decimal] = None
    quantity_qualifier: Optional[QuantityQualifier] = None

    # Additional info
    authorization_required: bool = False
    in_plan_network: Optional[bool] = None
    procedure_codes: List[str] = field(default_factory=list)
    diagnosis_codes: List[str] = field(default_factory=list)

    # Raw message
    message: Optional[str] = None


@dataclass
class SubscriberInfo271:
    """Subscriber information from 271 response."""
    member_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    group_number: Optional[str] = None
    group_name: Optional[str] = None
    plan_number: Optional[str] = None
    relationship_code: Optional[str] = None


@dataclass
class PayerInfo271:
    """Payer information from 271 response."""
    payer_id: str
    name: str
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None


@dataclass
class ProviderInfo271:
    """Provider information from 271 response."""
    npi: Optional[str] = None
    name: Optional[str] = None
    entity_type: str = "2"


@dataclass
class EligibilityDate:
    """Date information from DTP segment."""
    qualifier: str
    date_value: Optional[date] = None
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    description: Optional[str] = None


@dataclass
class EligibilityResponse:
    """Complete parsed 271 eligibility response."""
    # Transaction info
    transaction_id: str
    trace_number: Optional[str] = None
    control_number: str = ""

    # Status
    is_eligible: bool = False
    eligibility_status: Optional[EligibilityStatus] = None

    # Parties
    subscriber: Optional[SubscriberInfo271] = None
    dependent: Optional[SubscriberInfo271] = None
    payer: Optional[PayerInfo271] = None
    provider: Optional[ProviderInfo271] = None

    # Benefits and Coverage
    benefits: List[BenefitInfo] = field(default_factory=list)
    dates: List[EligibilityDate] = field(default_factory=list)

    # Summary
    plan_begin_date: Optional[date] = None
    plan_end_date: Optional[date] = None
    coverage_active: bool = False

    # Errors/Rejections
    errors: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    aaa_segments: List[Dict[str, Any]] = field(default_factory=list)

    # Raw data for debugging
    raw_segments: List[str] = field(default_factory=list)


# =============================================================================
# Parser
# =============================================================================


class X12271Parser:
    """
    X12 271 Eligibility Response Parser.

    Parses HIPAA 5010 compliant 271 transactions containing
    eligibility status and benefit information.

    Usage:
        parser = X12271Parser()
        response = parser.parse(x12_content)
        if response.is_eligible:
            print(f"Member {response.subscriber.member_id} is eligible")
    """

    def __init__(self):
        self.tokenizer = None
        self.segments = []
        self.current_idx = 0

    def parse(self, content: str) -> EligibilityResponse:
        """
        Parse X12 271 eligibility response.

        Args:
            content: Raw X12 271 content

        Returns:
            EligibilityResponse with parsed eligibility data

        Raises:
            ValueError: If content is empty or not valid X12 format
        """
        # Validate input
        if not content or not content.strip():
            raise ValueError("Empty content provided")

        if not content.strip().startswith("ISA"):
            raise ValueError("Invalid X12 content: must start with ISA segment")

        # Tokenize
        self.tokenizer = X12Tokenizer(content)
        self.segments = self.tokenizer.tokenize()
        self.current_idx = 0

        # Validate we have segments
        if not self.segments:
            raise ValueError("Invalid X12 content: no segments parsed")

        response = EligibilityResponse(
            transaction_id="",
            raw_segments=[str(s) for s in self.segments[:10]],  # First 10 for debug
        )

        try:
            # Parse envelope
            self._parse_envelope(response)

            # Parse transaction
            self._parse_transaction(response)

            # Determine overall eligibility
            self._determine_eligibility(response)

        except Exception as e:
            response.errors.append(f"Parse error: {str(e)}")

        return response

    def _parse_envelope(self, response: EligibilityResponse) -> None:
        """Parse ISA/GS envelope.

        Note: X12Segment uses 0-based indexing for elements.
        ISA13 = elements[12], ST02 = elements[1], ST03 = elements[2]
        """
        for seg in self.segments:
            if seg.segment_id == "ISA":
                response.control_number = seg.get_element(12, "").strip()  # ISA13 - Interchange Control Number
            elif seg.segment_id == "ST":
                response.transaction_id = seg.get_element(2, "")  # ST03 - Implementation Convention Reference

    def _parse_transaction(self, response: EligibilityResponse) -> None:
        """Parse the main transaction content.

        Note: X12Segment uses 0-based indexing for elements.
        For HL segment: HL01=index 0, HL02=index 1, HL03=index 2, HL04=index 3
        For TRN segment: TRN01=index 0, TRN02=index 1, TRN03=index 2
        """
        current_level = None  # Current HL level (HL01)
        current_level_code = None  # Level code (HL03)

        for idx, seg in enumerate(self.segments):
            try:
                if seg.segment_id == "BHT":
                    self._parse_bht(seg, response)

                elif seg.segment_id == "HL":
                    current_level = seg.get_element(0)  # HL01 - Hierarchical ID Number
                    current_level_code = seg.get_element(2)  # HL03 - Hierarchical Level Code (20=Info Source, 21=Receiver, 22=Subscriber)

                elif seg.segment_id == "TRN":
                    response.trace_number = seg.get_element(1)  # TRN02 - Reference Identification

                elif seg.segment_id == "NM1":
                    self._parse_nm1(seg, current_level_code, response)

                elif seg.segment_id == "N3":
                    pass  # Address line - skip for now

                elif seg.segment_id == "N4":
                    pass  # City/State/Zip - skip for now

                elif seg.segment_id == "PER":
                    self._parse_per(seg, response)

                elif seg.segment_id == "AAA":
                    self._parse_aaa(seg, response)

                elif seg.segment_id == "DMG":
                    self._parse_dmg(seg, current_level_code, response)

                elif seg.segment_id == "INS":
                    self._parse_ins(seg, response)

                elif seg.segment_id == "REF":
                    self._parse_ref(seg, current_level_code, response)

                elif seg.segment_id == "DTP":
                    self._parse_dtp(seg, response)

                elif seg.segment_id == "EB":
                    self._parse_eb(seg, response)

                elif seg.segment_id == "MSG":
                    self._parse_msg(seg, response)

            except Exception as e:
                response.errors.append(f"Error parsing {seg.segment_id}: {str(e)}")

    def _parse_bht(self, seg: X12Segment, response: EligibilityResponse) -> None:
        """Parse BHT segment."""
        # BHT*0022*11*TRACE*DATE*TIME
        pass  # Trace info already in TRN

    def _parse_nm1(self, seg: X12Segment, level_code: str, response: EligibilityResponse) -> None:
        """Parse NM1 segment based on context.

        Note: X12Segment uses 0-based indexing for elements.
        NM101 = elements[0], NM102 = elements[1], etc.
        """
        entity_code = seg.get_element(0)  # NM101 - Entity Identifier Code
        entity_type = seg.get_element(1)  # NM102 - Entity Type Qualifier (1=Person, 2=Org)

        if entity_code == "PR":
            # Payer
            response.payer = PayerInfo271(
                payer_id=seg.get_element(8, ""),  # NM109 - Identification Code
                name=seg.get_element(2, ""),  # NM103 - Name Last or Organization Name
            )
        elif entity_code == "1P":
            # Provider
            response.provider = ProviderInfo271(
                npi=seg.get_element(8),  # NM109 - Identification Code (NPI)
                name=seg.get_element(2),  # NM103 - Name
                entity_type=entity_type,
            )
        elif entity_code == "IL":
            # Subscriber
            response.subscriber = SubscriberInfo271(
                member_id=seg.get_element(8, ""),  # NM109 - Identification Code
                last_name=seg.get_element(2),  # NM103 - Name Last
                first_name=seg.get_element(3),  # NM104 - Name First
            )
        elif entity_code == "03":
            # Dependent
            response.dependent = SubscriberInfo271(
                member_id=seg.get_element(8, ""),  # NM109 - Identification Code
                last_name=seg.get_element(2),  # NM103 - Name Last
                first_name=seg.get_element(3),  # NM104 - Name First
            )

    def _parse_per(self, seg: X12Segment, response: EligibilityResponse) -> None:
        """Parse PER segment for contact info.

        Note: X12Segment uses 0-based indexing for elements.
        PER01 = elements[0], PER02 = elements[1], etc.
        """
        if response.payer:
            response.payer.contact_name = seg.get_element(1)  # PER02 - Contact Name
            comm_qualifier = seg.get_element(2)  # PER03 - Communication Number Qualifier
            comm_value = seg.get_element(3)  # PER04 - Communication Number

            if comm_qualifier == "TE":
                response.payer.contact_phone = comm_value
            elif comm_qualifier == "EM":
                response.payer.contact_email = comm_value

    def _parse_aaa(self, seg: X12Segment, response: EligibilityResponse) -> None:
        """Parse AAA segment for request validation errors.

        Note: X12Segment uses 0-based indexing for elements.
        AAA01 = elements[0], AAA02 = elements[1], etc.
        """
        valid_request = seg.get_element(0)  # AAA01 - Yes/No Condition or Response Code
        reject_reason = seg.get_element(2)  # AAA03 - Reject Reason Code
        follow_up = seg.get_element(3)  # AAA04 - Follow-up Action Code

        aaa_info = {
            "valid": valid_request == "Y",
            "reject_reason_code": reject_reason,
            "follow_up_code": follow_up,
        }

        response.aaa_segments.append(aaa_info)

        if valid_request == "N":
            response.errors.append(f"Request rejected: {reject_reason}")
            response.rejection_reason = reject_reason

    def _parse_dmg(self, seg: X12Segment, level_code: str, response: EligibilityResponse) -> None:
        """Parse DMG segment for demographics.

        Note: X12Segment uses 0-based indexing for elements.
        DMG01 = elements[0], DMG02 = elements[1], etc.
        """
        dob_str = seg.get_element(1)  # DMG02 - Date of Birth
        gender = seg.get_element(2)  # DMG03 - Gender Code

        dob = parse_x12_date(dob_str) if dob_str else None

        # Apply to subscriber or dependent based on context
        if level_code == "22" and response.subscriber:
            response.subscriber.date_of_birth = dob
            response.subscriber.gender = gender
        elif level_code == "23" and response.dependent:
            response.dependent.date_of_birth = dob
            response.dependent.gender = gender

    def _parse_ins(self, seg: X12Segment, response: EligibilityResponse) -> None:
        """Parse INS segment for insurance info.

        Note: X12Segment uses 0-based indexing for elements.
        INS01 = elements[0], INS02 = elements[1], etc.
        """
        response_code = seg.get_element(0)  # INS01 - Yes/No (Y=Subscriber, N=Dependent)
        relationship = seg.get_element(1)  # INS02 - Individual Relationship Code

        if response.subscriber:
            response.subscriber.relationship_code = relationship

    def _parse_ref(self, seg: X12Segment, level_code: str, response: EligibilityResponse) -> None:
        """Parse REF segment for reference numbers.

        Note: X12Segment uses 0-based indexing for elements.
        REF01 = elements[0], REF02 = elements[1], etc.
        """
        qualifier = seg.get_element(0)  # REF01 - Reference Identification Qualifier
        value = seg.get_element(1)  # REF02 - Reference Identification

        if qualifier == "6P" and response.subscriber:
            # Group Number
            response.subscriber.group_number = value
        elif qualifier == "18" and response.subscriber:
            # Plan Number
            response.subscriber.plan_number = value

    def _parse_dtp(self, seg: X12Segment, response: EligibilityResponse) -> None:
        """Parse DTP segment for dates.

        Note: X12Segment uses 0-based indexing for elements.
        DTP01 = elements[0], DTP02 = elements[1], etc.
        """
        qualifier = seg.get_element(0)  # DTP01 - Date/Time Qualifier
        format_code = seg.get_element(1)  # DTP02 - Date/Time Period Format Qualifier
        date_value = seg.get_element(2)  # DTP03 - Date/Time Period

        elig_date = EligibilityDate(qualifier=qualifier)

        if format_code == "D8":
            # Single date
            elig_date.date_value = parse_x12_date(date_value)
        elif format_code == "RD8":
            # Date range
            parts = date_value.split("-")
            if len(parts) == 2:
                elig_date.date_range_start = parse_x12_date(parts[0])
                elig_date.date_range_end = parse_x12_date(parts[1])

        # Special handling for plan dates
        if qualifier == "291":  # Plan
            elig_date.description = "Plan Period"
        elif qualifier == "307":  # Eligibility
            elig_date.description = "Eligibility"
            if elig_date.date_range_start:
                response.plan_begin_date = elig_date.date_range_start
            if elig_date.date_range_end:
                response.plan_end_date = elig_date.date_range_end
        elif qualifier == "346":  # Plan Begin
            response.plan_begin_date = elig_date.date_value
            elig_date.description = "Plan Begin"
        elif qualifier == "347":  # Plan End
            response.plan_end_date = elig_date.date_value
            elig_date.description = "Plan End"

        response.dates.append(elig_date)

    def _parse_eb(self, seg: X12Segment, response: EligibilityResponse) -> None:
        """Parse EB segment for eligibility/benefit information.

        Note: X12Segment uses 0-based indexing for elements.
        EB01 = elements[0], EB02 = elements[1], etc.
        """
        # EB01 - Eligibility or Benefit Information Code (0-based index)
        status_code = seg.get_element(0)
        benefit = BenefitInfo(
            status=EligibilityStatus(status_code) if status_code else EligibilityStatus.OTHER_UNLISTED,
        )

        # Coverage Level (EB02 = index 1)
        coverage = seg.get_element(1)
        if coverage:
            try:
                benefit.coverage_level = CoverageLevel(coverage)
            except ValueError:
                pass

        # Service Type Code (EB03 = index 2)
        benefit.service_type_code = seg.get_element(2)

        # Insurance Type (EB04 = index 3)
        ins_type = seg.get_element(3)
        if ins_type:
            try:
                benefit.insurance_type = InsuranceType(ins_type)
            except ValueError:
                pass

        # Plan Coverage Description (EB05 = index 4)
        benefit.service_type_description = seg.get_element(4)

        # Time Period Qualifier (EB06 = index 5)
        time_period = seg.get_element(5)
        if time_period:
            try:
                benefit.time_period = TimePeriod(time_period)
            except ValueError:
                pass

        # Monetary Amount (EB07 = index 6)
        amount = seg.get_element(6)
        if amount:
            benefit.monetary_amount = parse_x12_amount(amount)

        # Percent (EB08 = index 7)
        percent = seg.get_element(7)
        if percent:
            benefit.percent = parse_x12_amount(percent)

        # Quantity Qualifier (EB09 = index 8)
        qty_qual = seg.get_element(8)
        if qty_qual:
            try:
                benefit.quantity_qualifier = QuantityQualifier(qty_qual)
            except ValueError:
                pass

        # Quantity (EB10 = index 9)
        quantity = seg.get_element(9)
        if quantity:
            benefit.quantity = parse_x12_amount(quantity)

        # Authorization Required (EB11 = index 10)
        auth_required = seg.get_element(10)
        benefit.authorization_required = auth_required == "Y"

        # In Plan Network (EB12 = index 11)
        in_network = seg.get_element(11)
        if in_network:
            benefit.in_plan_network = in_network == "Y"

        response.benefits.append(benefit)

    def _parse_msg(self, seg: X12Segment, response: EligibilityResponse) -> None:
        """Parse MSG segment for free-form message.

        Note: X12Segment uses 0-based indexing for elements.
        MSG01 = elements[0], MSG02 = elements[1], etc.
        """
        message = seg.get_element(0)  # MSG01 - Free-Form Message Text
        if message and response.benefits:
            # Attach to last benefit
            response.benefits[-1].message = message

    def _determine_eligibility(self, response: EligibilityResponse) -> None:
        """Determine overall eligibility status from benefits."""
        # Check for active coverage
        active_statuses = {
            EligibilityStatus.ACTIVE,
            EligibilityStatus.ACTIVE_FULL_RISK,
            EligibilityStatus.ACTIVE_SERVICES,
            EligibilityStatus.ACTIVE_SERVICES_PRIMARY,
            EligibilityStatus.ACTIVE_PENDING,
        }

        inactive_statuses = {
            EligibilityStatus.INACTIVE,
            EligibilityStatus.INACTIVE_PENDING,
            EligibilityStatus.INACTIVE_PENDING_INVESTIGATION,
        }

        for benefit in response.benefits:
            if benefit.status in active_statuses:
                response.is_eligible = True
                response.coverage_active = True
                response.eligibility_status = benefit.status
                break
            elif benefit.status in inactive_statuses:
                response.is_eligible = False
                response.coverage_active = False
                response.eligibility_status = benefit.status

        # Check for rejection
        if response.aaa_segments:
            for aaa in response.aaa_segments:
                if not aaa.get("valid", True):
                    response.is_eligible = False
                    break
