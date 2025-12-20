"""
X12 835 Remittance Advice Generator.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Generates X12 835 remittance advice from adjudication results.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import logging

from src.services.edi.x12_base import (
    format_x12_date,
    format_x12_time,
    format_x12_amount,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class PaymentMethod(str, Enum):
    """Payment method code (BPR01)."""

    CHECK = "C"  # Payment via check
    ACH_CCD = "ACH"  # ACH Corporate Credit or Debit
    NON_PAYMENT = "NON"  # Non-payment (zero pay)


class ClaimStatus(str, Enum):
    """Claim status code (CLP02)."""

    PROCESSED_PRIMARY = "1"  # Processed as primary
    PROCESSED_SECONDARY = "2"  # Processed as secondary
    PROCESSED_TERTIARY = "3"  # Processed as tertiary
    DENIED = "4"  # Denied
    PROCESSED_FORWARDED = "22"  # Processed, forwarded to payer
    REVERSAL = "R"  # Reversal of previous payment


class AdjustmentGroup(str, Enum):
    """Claim adjustment group code (CAS01)."""

    CO = "CO"  # Contractual Obligations
    CR = "CR"  # Corrections and Reversals
    OA = "OA"  # Other Adjustments
    PI = "PI"  # Payor Initiated Reductions
    PR = "PR"  # Patient Responsibility


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class PayerInfo:
    """Payer information for 835 remittance."""

    name: str
    payer_id: str
    address_line1: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    contact_name: str = ""
    contact_phone: str = ""


@dataclass
class PayeeInfo:
    """Payee (provider) information for 835 remittance."""

    name: str
    npi: str
    tax_id: str = ""
    address_line1: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""


@dataclass
class AdjustmentReason:
    """
    Claim/service adjustment.

    Uses CARC (Claim Adjustment Reason Code) and RARC (Remittance Advice Remark Code).
    """

    group_code: AdjustmentGroup
    reason_code: str  # CARC code (e.g., "45" for charges exceed)
    amount: Decimal
    quantity: Optional[Decimal] = None


@dataclass
class ServicePayment:
    """
    Service line payment information.

    Maps to Loop 2110 in X12 835.
    """

    # Procedure identification
    procedure_code: str
    procedure_modifiers: List[str] = field(default_factory=list)

    # Amounts
    billed_amount: Decimal = Decimal("0")
    allowed_amount: Decimal = Decimal("0")
    paid_amount: Decimal = Decimal("0")

    # Units
    billed_units: Decimal = Decimal("1")
    paid_units: Decimal = Decimal("1")

    # Revenue code (institutional)
    revenue_code: Optional[str] = None

    # Adjustments
    adjustments: List[AdjustmentReason] = field(default_factory=list)

    # Service dates
    service_date: Optional[date] = None
    service_date_end: Optional[date] = None

    # Reference
    line_item_control_number: Optional[str] = None


@dataclass
class ClaimPayment:
    """
    Claim-level payment information.

    Maps to Loop 2100 in X12 835.
    """

    # Claim identification
    claim_id: str  # Patient control number
    claim_status: ClaimStatus

    # Amounts
    total_billed: Decimal = Decimal("0")
    total_allowed: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")
    patient_responsibility: Decimal = Decimal("0")

    # Claim adjustments
    adjustments: List[AdjustmentReason] = field(default_factory=list)

    # Service lines
    service_payments: List[ServicePayment] = field(default_factory=list)

    # Patient/Subscriber
    patient_last_name: str = ""
    patient_first_name: str = ""
    patient_id: str = ""  # Member ID

    # Provider
    rendering_provider_npi: Optional[str] = None

    # Filing
    claim_filing_indicator: str = "MC"  # Medicare

    # Reference numbers
    payer_claim_number: Optional[str] = None
    facility_code: Optional[str] = None


@dataclass
class RemittanceAdvice:
    """
    Complete remittance advice data.

    Contains all data needed to generate X12 835.
    """

    # Transaction identification
    transaction_id: str
    check_eft_number: str

    # Payment information
    payment_method: PaymentMethod
    payment_amount: Decimal
    payment_date: date

    # Payer information
    payer_name: str
    payer_id: str

    # Payee information (required fields)
    payee_name: str
    payee_npi: str

    # Optional payer details
    payer_address_line1: str = ""
    payer_city: str = ""
    payer_state: str = ""
    payer_zip: str = ""
    payer_contact_name: str = ""
    payer_contact_phone: str = ""

    # Optional payee details
    payee_tax_id: str = ""
    payee_address_line1: str = ""
    payee_city: str = ""
    payee_state: str = ""
    payee_zip: str = ""

    # Claims
    claim_payments: List[ClaimPayment] = field(default_factory=list)

    # Control numbers
    interchange_control_number: str = "000000001"
    group_control_number: str = "1"
    transaction_control_number: str = "0001"


# =============================================================================
# Generator
# =============================================================================


class X12835Generator:
    """
    Generator for X12 835 Remittance Advice.

    Generates 5010 version 835 transactions from adjudication results.

    Usage:
        generator = X12835Generator()
        edi_content = generator.generate(remittance_advice)
    """

    def __init__(
        self,
        element_separator: str = "*",
        segment_terminator: str = "~",
        component_separator: str = ":",
    ):
        self.element_sep = element_separator
        self.segment_term = segment_terminator
        self.component_sep = component_separator

    def generate(self, remittance: RemittanceAdvice) -> str:
        """
        Generate X12 835 from remittance advice data.

        Args:
            remittance: RemittanceAdvice with payment information

        Returns:
            X12 835 EDI content as string
        """
        segments = []

        # Interchange Control Header (ISA)
        segments.append(self._build_isa(remittance))

        # Functional Group Header (GS)
        segments.append(self._build_gs(remittance))

        # Transaction Set Header (ST)
        segments.append(self._build_st(remittance))

        # Financial Information (BPR)
        segments.append(self._build_bpr(remittance))

        # Reassociation Trace Number (TRN)
        segments.append(self._build_trn(remittance))

        # Reference Identification (REF) - Receiver ID
        segments.append(self._build_ref("EV", remittance.payer_id))

        # Production Date (DTM)
        segments.append(self._build_dtm("405", remittance.payment_date))

        # Loop 1000A - Payer Identification
        segments.extend(self._build_loop_1000a(remittance))

        # Loop 1000B - Payee Identification
        segments.extend(self._build_loop_1000b(remittance))

        # Loop 2000 - Header Number
        segments.append(self._build_lx("1"))

        # Loop 2100 - Claim Payment Information (per claim)
        for claim in remittance.claim_payments:
            segments.extend(self._build_loop_2100(claim))

        # Transaction Set Trailer (SE)
        segment_count = len(segments) + 1  # +1 for SE itself
        segments.append(self._build_se(segment_count, remittance.transaction_control_number))

        # Functional Group Trailer (GE)
        segments.append(self._build_ge(remittance))

        # Interchange Control Trailer (IEA)
        segments.append(self._build_iea(remittance))

        # Join segments with terminator
        return self.segment_term.join(segments) + self.segment_term

    def _build_segment(self, segment_id: str, *elements) -> str:
        """Build a segment from ID and elements."""
        all_elements = [segment_id] + [str(e) if e is not None else "" for e in elements]
        return self.element_sep.join(all_elements)

    def _build_isa(self, rem: RemittanceAdvice) -> str:
        """Build ISA (Interchange Control Header) segment."""
        now = datetime.now()
        return self._build_segment(
            "ISA",
            "00",  # Authorization qualifier
            " " * 10,  # Authorization info
            "00",  # Security qualifier
            " " * 10,  # Security info
            "ZZ",  # Sender qualifier
            rem.payer_id.ljust(15),  # Sender ID
            "ZZ",  # Receiver qualifier
            rem.payee_npi.ljust(15),  # Receiver ID
            now.strftime("%y%m%d"),  # Date
            now.strftime("%H%M"),  # Time
            "^",  # Repetition separator
            "00501",  # Version
            rem.interchange_control_number.zfill(9),  # Control number
            "0",  # Ack requested
            "P",  # Usage indicator (P=Production)
            self.component_sep,  # Component separator
        )

    def _build_gs(self, rem: RemittanceAdvice) -> str:
        """Build GS (Functional Group Header) segment."""
        now = datetime.now()
        return self._build_segment(
            "GS",
            "HP",  # Functional ID (HP=Health Care Claim Payment)
            rem.payer_id,  # Sender
            rem.payee_npi,  # Receiver
            now.strftime("%Y%m%d"),  # Date
            now.strftime("%H%M"),  # Time
            rem.group_control_number,  # Control number
            "X",  # Responsible agency
            "005010X221A1",  # Version
        )

    def _build_st(self, rem: RemittanceAdvice) -> str:
        """Build ST (Transaction Set Header) segment."""
        return self._build_segment(
            "ST",
            "835",  # Transaction set ID
            rem.transaction_control_number,  # Control number
            "005010X221A1",  # Version
        )

    def _build_bpr(self, rem: RemittanceAdvice) -> str:
        """Build BPR (Financial Information) segment."""
        return self._build_segment(
            "BPR",
            rem.payment_method.value,  # Payment method
            format_x12_amount(float(rem.payment_amount)),  # Amount
            "C",  # Credit/Debit
            "CHK" if rem.payment_method == PaymentMethod.CHECK else "ACH",  # Payment format
            "",  # DFI ID qualifier (bank)
            "",  # DFI ID
            "",  # Account number qualifier
            "",  # Account number
            "",  # Originating company ID
            "",  # Originating company supplemental
            "",  # DFI ID qualifier (receiver)
            "",  # DFI ID (receiver)
            "",  # Account number qualifier (receiver)
            "",  # Account number (receiver)
            format_x12_date(rem.payment_date),  # Payment date
        )

    def _build_trn(self, rem: RemittanceAdvice) -> str:
        """Build TRN (Reassociation Trace Number) segment."""
        return self._build_segment(
            "TRN",
            "1",  # Trace type (1=Current Transaction)
            rem.check_eft_number,  # Check/EFT number
            rem.payer_id,  # Originating company ID
        )

    def _build_ref(self, qualifier: str, value: str) -> str:
        """Build REF (Reference Identification) segment."""
        return self._build_segment("REF", qualifier, value)

    def _build_dtm(self, qualifier: str, dt: date) -> str:
        """Build DTM (Date/Time Reference) segment."""
        return self._build_segment("DTM", qualifier, format_x12_date(dt))

    def _build_loop_1000a(self, rem: RemittanceAdvice) -> List[str]:
        """Build Loop 1000A - Payer Identification."""
        segments = []

        # N1 - Payer Name
        segments.append(self._build_segment(
            "N1",
            "PR",  # Payer
            rem.payer_name,
            "XV",  # ID qualifier (Health Care Provider Taxonomy)
            rem.payer_id,
        ))

        # N3 - Payer Address
        if rem.payer_address_line1:
            segments.append(self._build_segment("N3", rem.payer_address_line1))

        # N4 - Payer City/State/Zip
        if rem.payer_city:
            segments.append(self._build_segment(
                "N4",
                rem.payer_city,
                rem.payer_state,
                rem.payer_zip,
            ))

        # PER - Payer Contact
        if rem.payer_contact_name:
            segments.append(self._build_segment(
                "PER",
                "CX",  # Contact function (Payer's Claims Office)
                rem.payer_contact_name,
                "TE",  # Phone
                rem.payer_contact_phone,
            ))

        return segments

    def _build_loop_1000b(self, rem: RemittanceAdvice) -> List[str]:
        """Build Loop 1000B - Payee Identification."""
        segments = []

        # N1 - Payee Name
        segments.append(self._build_segment(
            "N1",
            "PE",  # Payee
            rem.payee_name,
            "XX",  # ID qualifier (NPI)
            rem.payee_npi,
        ))

        # N3 - Payee Address
        if rem.payee_address_line1:
            segments.append(self._build_segment("N3", rem.payee_address_line1))

        # N4 - Payee City/State/Zip
        if rem.payee_city:
            segments.append(self._build_segment(
                "N4",
                rem.payee_city,
                rem.payee_state,
                rem.payee_zip,
            ))

        # REF - Tax ID
        if rem.payee_tax_id:
            segments.append(self._build_segment("REF", "TJ", rem.payee_tax_id))

        return segments

    def _build_lx(self, number: str) -> str:
        """Build LX (Header Number) segment."""
        return self._build_segment("LX", number)

    def _build_loop_2100(self, claim: ClaimPayment) -> List[str]:
        """Build Loop 2100 - Claim Payment Information."""
        segments = []

        # CLP - Claim Payment Information
        segments.append(self._build_segment(
            "CLP",
            claim.claim_id,  # Patient control number
            claim.claim_status.value,  # Status code
            format_x12_amount(float(claim.total_billed)),  # Billed
            format_x12_amount(float(claim.total_paid)),  # Paid
            format_x12_amount(float(claim.patient_responsibility)),  # Patient responsibility
            claim.claim_filing_indicator,  # Filing indicator
            claim.payer_claim_number or "",  # Payer claim number
            claim.facility_code or "",  # Facility code
        ))

        # CAS - Claim Adjustments
        for adj in claim.adjustments:
            segments.append(self._build_cas(adj))

        # NM1 - Patient Name
        segments.append(self._build_segment(
            "NM1",
            "QC",  # Patient
            "1",  # Person
            claim.patient_last_name,
            claim.patient_first_name,
            "",  # Middle
            "",  # Prefix
            "",  # Suffix
            "MI",  # ID qualifier (Member ID)
            claim.patient_id,
        ))

        # NM1 - Rendering Provider (if different)
        if claim.rendering_provider_npi:
            segments.append(self._build_segment(
                "NM1",
                "82",  # Rendering Provider
                "1",  # Person
                "",  # Last name
                "",  # First name
                "",  # Middle
                "",  # Prefix
                "",  # Suffix
                "XX",  # NPI
                claim.rendering_provider_npi,
            ))

        # Loop 2110 - Service Payment Information
        for service in claim.service_payments:
            segments.extend(self._build_loop_2110(service))

        return segments

    def _build_loop_2110(self, service: ServicePayment) -> List[str]:
        """Build Loop 2110 - Service Payment Information."""
        segments = []

        # Build procedure composite
        proc_parts = ["HC", service.procedure_code]
        proc_parts.extend(service.procedure_modifiers[:4])
        procedure_composite = self.component_sep.join(proc_parts)

        # SVC - Service Payment Information
        segments.append(self._build_segment(
            "SVC",
            procedure_composite,
            format_x12_amount(float(service.billed_amount)),
            format_x12_amount(float(service.paid_amount)),
            service.revenue_code or "",
            "",  # Composite medical procedure ID (2)
            str(service.paid_units) if service.paid_units else "",
        ))

        # DTM - Service Date
        if service.service_date:
            if service.service_date_end and service.service_date != service.service_date_end:
                # Date range
                date_range = f"{format_x12_date(service.service_date)}-{format_x12_date(service.service_date_end)}"
                segments.append(self._build_segment("DTM", "472", date_range))
            else:
                segments.append(self._build_dtm("472", service.service_date))

        # CAS - Service Adjustments
        for adj in service.adjustments:
            segments.append(self._build_cas(adj))

        # REF - Line Item Control Number
        if service.line_item_control_number:
            segments.append(self._build_ref("6R", service.line_item_control_number))

        # AMT - Service Amount (Allowed)
        if service.allowed_amount:
            segments.append(self._build_segment(
                "AMT",
                "B6",  # Allowed - Actual
                format_x12_amount(float(service.allowed_amount)),
            ))

        return segments

    def _build_cas(self, adj: AdjustmentReason) -> str:
        """Build CAS (Claim Adjustment) segment."""
        elements = [
            "CAS",
            adj.group_code.value,
            adj.reason_code,
            format_x12_amount(float(adj.amount)),
        ]
        if adj.quantity:
            elements.append(str(adj.quantity))
        return self.element_sep.join(elements)

    def _build_se(self, segment_count: int, control_number: str) -> str:
        """Build SE (Transaction Set Trailer) segment."""
        return self._build_segment("SE", str(segment_count), control_number)

    def _build_ge(self, rem: RemittanceAdvice) -> str:
        """Build GE (Functional Group Trailer) segment."""
        return self._build_segment("GE", "1", rem.group_control_number)

    def _build_iea(self, rem: RemittanceAdvice) -> str:
        """Build IEA (Interchange Control Trailer) segment."""
        return self._build_segment("IEA", "1", rem.interchange_control_number.zfill(9))


# =============================================================================
# Helper Functions
# =============================================================================


def create_remittance_from_adjudication(
    adjudication_result: Dict,
    payer_info: Dict,
    payee_info: Dict,
) -> RemittanceAdvice:
    """
    Create RemittanceAdvice from adjudication result.

    Helper function to convert adjudication engine output to 835 input.
    """
    from datetime import date as dt
    from uuid import uuid4

    # Create claim payment
    claim_payment = ClaimPayment(
        claim_id=adjudication_result.get("claim_id", ""),
        claim_status=ClaimStatus.PROCESSED_PRIMARY if adjudication_result.get("decision") == "approved" else ClaimStatus.DENIED,
        total_billed=Decimal(str(adjudication_result.get("total_billed", 0))),
        total_allowed=Decimal(str(adjudication_result.get("total_allowed", 0))),
        total_paid=Decimal(str(adjudication_result.get("total_plan_payment", 0))),
        patient_responsibility=Decimal(str(adjudication_result.get("total_member_responsibility", 0))),
        patient_last_name=adjudication_result.get("patient_last_name", ""),
        patient_first_name=adjudication_result.get("patient_first_name", ""),
        patient_id=adjudication_result.get("member_id", ""),
        rendering_provider_npi=adjudication_result.get("provider_npi"),
    )

    # Add adjustments
    pricing_details = adjudication_result.get("pricing_details", [])
    for pricing in pricing_details:
        for adj in pricing.get("adjustments", []):
            claim_payment.adjustments.append(AdjustmentReason(
                group_code=AdjustmentGroup.CO,
                reason_code=adj.get("reason", "45"),
                amount=Decimal(str(adj.get("amount", 0))),
            ))

    # Add service lines
    for pricing in pricing_details:
        service = ServicePayment(
            procedure_code=pricing.get("cpt_code", ""),
            billed_amount=Decimal(str(pricing.get("billed_amount", 0))),
            allowed_amount=Decimal(str(pricing.get("allowed_amount", 0))),
            paid_amount=Decimal(str(pricing.get("paid_amount", 0))),
            billed_units=Decimal(str(pricing.get("units", 1))),
        )
        claim_payment.service_payments.append(service)

    # Build remittance
    return RemittanceAdvice(
        transaction_id=str(uuid4()),
        check_eft_number=str(uuid4().int)[:10],
        payment_method=PaymentMethod.CHECK,
        payment_amount=claim_payment.total_paid,
        payment_date=dt.today(),
        payer_name=payer_info.get("name", ""),
        payer_id=payer_info.get("id", ""),
        payer_address_line1=payer_info.get("address", ""),
        payer_city=payer_info.get("city", ""),
        payer_state=payer_info.get("state", ""),
        payer_zip=payer_info.get("zip", ""),
        payee_name=payee_info.get("name", ""),
        payee_npi=payee_info.get("npi", ""),
        payee_tax_id=payee_info.get("tax_id", ""),
        payee_address_line1=payee_info.get("address", ""),
        payee_city=payee_info.get("city", ""),
        payee_state=payee_info.get("state", ""),
        payee_zip=payee_info.get("zip", ""),
        claim_payments=[claim_payment],
    )
