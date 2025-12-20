"""
X12 837 Claim Parser.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Parses X12 837P (Professional) and 837I (Institutional) claims
into normalized claim models for processing.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import date
from decimal import Decimal
from enum import Enum
import logging

from src.services.edi.x12_base import (
    X12Segment,
    X12Loop,
    X12Transaction,
    X12Tokenizer,
    TransactionType,
    X12ParseError,
    X12Envelope,
    X12FunctionalGroup,
    parse_x12_date,
    parse_x12_amount,
    validate_npi,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


class ClaimFrequency(str, Enum):
    """Claim frequency type code."""

    ORIGINAL = "1"  # Original claim
    CORRECTED = "7"  # Replacement of prior claim
    VOID = "8"  # Void/cancel prior claim


class ProviderType(str, Enum):
    """Provider type in claim."""

    BILLING = "billing"
    RENDERING = "rendering"
    REFERRING = "referring"
    SUPERVISING = "supervising"
    FACILITY = "facility"


@dataclass
class ProviderInfo:
    """Healthcare provider information."""

    provider_type: ProviderType
    npi: str
    name: str
    first_name: Optional[str] = None
    taxonomy_code: Optional[str] = None
    tax_id: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None


@dataclass
class SubscriberInfo:
    """Insurance subscriber/patient information."""

    member_id: str
    last_name: str
    first_name: str
    middle_name: Optional[str] = None
    suffix: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None  # M, F, U
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    relationship_code: str = "18"  # 18=Self
    payer_name: Optional[str] = None
    payer_id: Optional[str] = None
    group_number: Optional[str] = None
    plan_name: Optional[str] = None


@dataclass
class DiagnosisInfo:
    """Diagnosis code information."""

    code: str
    code_type: str = "ABK"  # ABK=ICD-10-CM, ABF=ICD-10-PCS
    sequence: int = 1
    is_principal: bool = False
    present_on_admission: Optional[str] = None  # Y, N, U, W


@dataclass
class ServiceLine837:
    """Service line from 837 claim."""

    line_number: int
    procedure_code: str
    procedure_modifiers: List[str] = field(default_factory=list)
    revenue_code: Optional[str] = None  # For institutional
    charge_amount: Decimal = Decimal("0")
    units: Decimal = Decimal("1")
    unit_type: str = "UN"  # UN=Unit
    service_date: Optional[date] = None
    service_date_end: Optional[date] = None
    place_of_service: Optional[str] = None
    diagnosis_pointers: List[int] = field(default_factory=list)
    rendering_provider_npi: Optional[str] = None
    description: Optional[str] = None
    # NDC information
    ndc_code: Optional[str] = None
    ndc_quantity: Optional[Decimal] = None
    ndc_unit: Optional[str] = None


@dataclass
class ParsedClaim837:
    """
    Parsed 837 claim data.

    Normalized representation of either 837P or 837I claim.
    """

    # Transaction info
    transaction_control_number: str
    claim_type: TransactionType  # 837P or 837I

    # Submitter info
    submitter_name: str
    submitter_id: str

    # Receiver info
    receiver_name: str
    receiver_id: str

    # Billing provider
    billing_provider: ProviderInfo

    # Subscriber/Patient
    subscriber: SubscriberInfo

    # Claim header
    claim_id: str  # Patient control number

    # Optional patient (if different from subscriber)
    patient: Optional[SubscriberInfo] = None
    total_charge: Decimal = Decimal("0")
    place_of_service: Optional[str] = None
    facility_code: Optional[str] = None
    claim_frequency: ClaimFrequency = ClaimFrequency.ORIGINAL
    provider_signature: bool = True
    assignment_of_benefits: bool = True
    release_of_information: str = "Y"

    # Dates
    statement_from_date: Optional[date] = None
    statement_to_date: Optional[date] = None
    admission_date: Optional[date] = None
    discharge_date: Optional[date] = None

    # Diagnoses
    diagnoses: List[DiagnosisInfo] = field(default_factory=list)

    # Service lines
    service_lines: List[ServiceLine837] = field(default_factory=list)

    # Additional providers
    rendering_provider: Optional[ProviderInfo] = None
    referring_provider: Optional[ProviderInfo] = None
    facility: Optional[ProviderInfo] = None

    # Prior authorization
    prior_auth_number: Optional[str] = None

    # Reference numbers
    original_claim_number: Optional[str] = None  # For replacement claims
    medical_record_number: Optional[str] = None

    # Raw data for debugging
    raw_segments: List[str] = field(default_factory=list)


# =============================================================================
# Parser
# =============================================================================


class X12837Parser:
    """
    Parser for X12 837P and 837I claims.

    Supports:
    - 837P (Professional) - 5010 version
    - 837I (Institutional) - 5010 version

    Usage:
        parser = X12837Parser()
        claims = parser.parse(edi_content)
    """

    def __init__(self):
        self.tokenizer = X12Tokenizer()

    def parse(self, content: str) -> List[ParsedClaim837]:
        """
        Parse X12 837 content into claims.

        Args:
            content: Raw X12 837 EDI content

        Returns:
            List of ParsedClaim837 objects
        """
        # Tokenize
        segments = self.tokenizer.tokenize(content)

        if not segments:
            raise X12ParseError("No segments found in content")

        # Parse envelope
        envelope, func_group, content_segments = self.tokenizer.parse_envelope(segments)

        # Determine transaction type
        trans_type, control_number = self.tokenizer.get_transaction_type(content_segments)

        if trans_type not in (TransactionType.CLAIM_837P, TransactionType.CLAIM_837I):
            raise X12ParseError(f"Expected 837P or 837I, got {trans_type}")

        # Parse claims from hierarchical structure
        claims = self._parse_claims(
            content_segments, envelope, func_group, trans_type, control_number
        )

        return claims

    def _parse_claims(
        self,
        segments: List[X12Segment],
        envelope: X12Envelope,
        func_group: X12FunctionalGroup,
        trans_type: TransactionType,
        control_number: str,
    ) -> List[ParsedClaim837]:
        """Parse individual claims from 837 segments."""
        claims = []

        # Track current context
        current_hl_level = None
        current_provider: Optional[ProviderInfo] = None
        current_subscriber: Optional[SubscriberInfo] = None
        current_patient: Optional[SubscriberInfo] = None
        current_claim: Optional[Dict] = None
        current_service_lines: List[ServiceLine837] = []
        current_diagnoses: List[DiagnosisInfo] = []

        # Segment index for iteration
        i = 0
        while i < len(segments):
            segment = segments[i]

            # Hierarchical Level
            if segment.segment_id == "HL":
                hl_id = segment.get_element(0)
                parent_id = segment.get_element(1)
                level_code = segment.get_element(2)

                if level_code == "20":
                    # Billing Provider level
                    current_provider = self._parse_billing_provider(segments, i)
                    current_hl_level = "provider"

                elif level_code == "22":
                    # Subscriber level
                    current_subscriber = self._parse_subscriber(segments, i)
                    current_patient = None  # Reset patient
                    current_hl_level = "subscriber"

                elif level_code == "23":
                    # Patient level (if different from subscriber)
                    current_patient = self._parse_patient(segments, i)
                    current_hl_level = "patient"

            # Claim header
            elif segment.segment_id == "CLM":
                # Save previous claim if exists
                if current_claim:
                    claim = self._build_claim(
                        current_claim,
                        current_diagnoses,
                        current_service_lines,
                        envelope,
                        func_group,
                        trans_type,
                        control_number,
                        current_provider,
                        current_subscriber,
                        current_patient,
                        segments,
                    )
                    claims.append(claim)

                # Start new claim
                current_claim = self._parse_claim_header(segment)
                current_service_lines = []
                current_diagnoses = []

            # Diagnoses (HI segment)
            elif segment.segment_id == "HI" and current_claim:
                diags = self._parse_diagnoses(segment)
                current_diagnoses.extend(diags)

            # Service line (837P)
            elif segment.segment_id == "SV1" and current_claim:
                line = self._parse_service_line_professional(
                    segments, i, len(current_service_lines) + 1
                )
                current_service_lines.append(line)

            # Service line (837I)
            elif segment.segment_id == "SV2" and current_claim:
                line = self._parse_service_line_institutional(
                    segments, i, len(current_service_lines) + 1
                )
                current_service_lines.append(line)

            # Line number marker
            elif segment.segment_id == "LX":
                # Service line number - next SV1/SV2 will use this
                pass

            # Dates
            elif segment.segment_id == "DTP" and current_claim:
                self._parse_claim_date(segment, current_claim)

            # Reference numbers
            elif segment.segment_id == "REF" and current_claim:
                self._parse_claim_reference(segment, current_claim)

            i += 1

        # Don't forget last claim
        if current_claim:
            claim = self._build_claim(
                current_claim,
                current_diagnoses,
                current_service_lines,
                envelope,
                func_group,
                trans_type,
                control_number,
                current_provider,
                current_subscriber,
                current_patient,
                segments,
            )
            claims.append(claim)

        return claims

    def _parse_billing_provider(
        self, segments: List[X12Segment], start_idx: int
    ) -> ProviderInfo:
        """Parse billing provider from Loop 2010AA."""
        provider = ProviderInfo(
            provider_type=ProviderType.BILLING,
            npi="",
            name="",
        )

        for i in range(start_idx + 1, len(segments)):
            seg = segments[i]

            if seg.segment_id == "HL":
                break

            if seg.segment_id == "NM1":
                entity_code = seg.get_element(0)
                if entity_code == "85":  # Billing Provider
                    provider.name = seg.get_element(2)
                    provider.first_name = seg.get_element(3)
                    id_qualifier = seg.get_element(7)
                    if id_qualifier == "XX":
                        provider.npi = seg.get_element(8)

            elif seg.segment_id == "N3":
                provider.address_line1 = seg.get_element(0)
                provider.address_line2 = seg.get_element(1)

            elif seg.segment_id == "N4":
                provider.city = seg.get_element(0)
                provider.state = seg.get_element(1)
                provider.zip_code = seg.get_element(2)

            elif seg.segment_id == "REF":
                ref_qualifier = seg.get_element(0)
                if ref_qualifier == "EI":  # Tax ID
                    provider.tax_id = seg.get_element(1)

            elif seg.segment_id == "PER":
                provider.phone = seg.get_element(3)

            elif seg.segment_id == "PRV":
                provider.taxonomy_code = seg.get_element(2)

        return provider

    def _parse_subscriber(
        self, segments: List[X12Segment], start_idx: int
    ) -> SubscriberInfo:
        """Parse subscriber from Loop 2010BA."""
        subscriber = SubscriberInfo(
            member_id="",
            last_name="",
            first_name="",
        )

        for i in range(start_idx + 1, len(segments)):
            seg = segments[i]

            if seg.segment_id == "HL":
                break

            if seg.segment_id == "SBR":
                subscriber.relationship_code = seg.get_element(1)
                subscriber.group_number = seg.get_element(2)
                subscriber.plan_name = seg.get_element(3)

            elif seg.segment_id == "NM1":
                entity_code = seg.get_element(0)
                if entity_code == "IL":  # Insured/Subscriber
                    subscriber.last_name = seg.get_element(2)
                    subscriber.first_name = seg.get_element(3)
                    subscriber.middle_name = seg.get_element(4)
                    subscriber.suffix = seg.get_element(6)
                    id_qualifier = seg.get_element(7)
                    if id_qualifier == "MI":  # Member ID
                        subscriber.member_id = seg.get_element(8)
                elif entity_code == "PR":  # Payer
                    subscriber.payer_name = seg.get_element(2)
                    subscriber.payer_id = seg.get_element(8)

            elif seg.segment_id == "N3":
                subscriber.address_line1 = seg.get_element(0)
                subscriber.address_line2 = seg.get_element(1)

            elif seg.segment_id == "N4":
                subscriber.city = seg.get_element(0)
                subscriber.state = seg.get_element(1)
                subscriber.zip_code = seg.get_element(2)

            elif seg.segment_id == "DMG":
                date_str = seg.get_element(1)
                subscriber.date_of_birth = parse_x12_date(date_str)
                subscriber.gender = seg.get_element(2)

        return subscriber

    def _parse_patient(
        self, segments: List[X12Segment], start_idx: int
    ) -> SubscriberInfo:
        """Parse patient (if different from subscriber) from Loop 2010CA."""
        patient = SubscriberInfo(
            member_id="",
            last_name="",
            first_name="",
        )

        for i in range(start_idx + 1, len(segments)):
            seg = segments[i]

            if seg.segment_id == "HL" or seg.segment_id == "CLM":
                break

            if seg.segment_id == "PAT":
                patient.relationship_code = seg.get_element(0)

            elif seg.segment_id == "NM1":
                entity_code = seg.get_element(0)
                if entity_code == "QC":  # Patient
                    patient.last_name = seg.get_element(2)
                    patient.first_name = seg.get_element(3)
                    patient.middle_name = seg.get_element(4)
                    patient.suffix = seg.get_element(6)

            elif seg.segment_id == "N3":
                patient.address_line1 = seg.get_element(0)
                patient.address_line2 = seg.get_element(1)

            elif seg.segment_id == "N4":
                patient.city = seg.get_element(0)
                patient.state = seg.get_element(1)
                patient.zip_code = seg.get_element(2)

            elif seg.segment_id == "DMG":
                date_str = seg.get_element(1)
                patient.date_of_birth = parse_x12_date(date_str)
                patient.gender = seg.get_element(2)

        return patient

    def _parse_claim_header(self, segment: X12Segment) -> Dict[str, Any]:
        """Parse CLM segment into claim header dict."""
        # CLM*claim_id*total_charge*empty*empty*place:facility:frequency*...
        claim_id = segment.get_element(0)
        total_charge = Decimal(str(parse_x12_amount(segment.get_element(1))))

        # Parse composite element 5 (place:facility:frequency)
        composite = segment.get_composite(4)
        place_of_service = composite[0] if len(composite) > 0 else None
        facility_code = composite[1] if len(composite) > 1 else None
        frequency = composite[2] if len(composite) > 2 else "1"

        return {
            "claim_id": claim_id,
            "total_charge": total_charge,
            "place_of_service": place_of_service,
            "facility_code": facility_code,
            "claim_frequency": ClaimFrequency(frequency) if frequency else ClaimFrequency.ORIGINAL,
            "provider_signature": segment.get_element(5) == "Y",
            "assignment_of_benefits": segment.get_element(6) in ("Y", "A", "B"),
            "release_of_information": segment.get_element(7) or "Y",
        }

    def _parse_diagnoses(self, segment: X12Segment) -> List[DiagnosisInfo]:
        """Parse HI segment into diagnosis list."""
        diagnoses = []

        for i, element in enumerate(segment.elements):
            if not element:
                continue

            # Parse composite (qualifier:code:...)
            parts = element.split(":")
            if len(parts) >= 2:
                qualifier = parts[0]
                code = parts[1]

                # Determine code type
                code_type = "ABK"  # Default ICD-10-CM
                if qualifier in ("ABK", "ABJ"):
                    code_type = "ABK"  # ICD-10-CM
                elif qualifier in ("ABF",):
                    code_type = "ABF"  # ICD-10-PCS

                diag = DiagnosisInfo(
                    code=code,
                    code_type=code_type,
                    sequence=i + 1,
                    is_principal=(i == 0),  # First diagnosis is principal
                    present_on_admission=parts[3] if len(parts) > 3 else None,
                )
                diagnoses.append(diag)

        return diagnoses

    def _parse_service_line_professional(
        self, segments: List[X12Segment], start_idx: int, line_num: int
    ) -> ServiceLine837:
        """Parse SV1 (professional service) into service line."""
        segment = segments[start_idx]

        # SV1*composite_procedure*charge*unit_type*units*place*...*diagnosis_pointers
        composite = segment.get_composite(0)
        procedure_code = composite[1] if len(composite) > 1 else ""
        modifiers = composite[2:6] if len(composite) > 2 else []
        modifiers = [m for m in modifiers if m]  # Remove empty

        line = ServiceLine837(
            line_number=line_num,
            procedure_code=procedure_code,
            procedure_modifiers=modifiers,
            charge_amount=Decimal(str(parse_x12_amount(segment.get_element(1)))),
            unit_type=segment.get_element(2) or "UN",
            units=Decimal(str(parse_x12_amount(segment.get_element(3) or "1"))),
            place_of_service=segment.get_element(4),
        )

        # Parse diagnosis pointers (element 6)
        pointers_str = segment.get_element(6)
        if pointers_str:
            # Pointers are like "1:2:3" or "1234"
            if ":" in pointers_str:
                line.diagnosis_pointers = [int(p) for p in pointers_str.split(":") if p.isdigit()]
            else:
                line.diagnosis_pointers = [int(c) for c in pointers_str if c.isdigit()]

        # Look for associated segments
        for i in range(start_idx + 1, min(start_idx + 10, len(segments))):
            seg = segments[i]

            if seg.segment_id in ("SV1", "SV2", "LX", "SE"):
                break

            if seg.segment_id == "DTP":
                qualifier = seg.get_element(0)
                if qualifier == "472":  # Service date
                    date_range = seg.get_element(2)
                    if "-" in date_range:
                        dates = date_range.split("-")
                        line.service_date = parse_x12_date(dates[0])
                        line.service_date_end = parse_x12_date(dates[1])
                    else:
                        line.service_date = parse_x12_date(date_range)

            elif seg.segment_id == "REF":
                qualifier = seg.get_element(0)
                if qualifier == "XZ":  # NDC
                    line.ndc_code = seg.get_element(1)

            elif seg.segment_id == "NM1":
                entity = seg.get_element(0)
                if entity == "82":  # Rendering provider
                    id_qual = seg.get_element(7)
                    if id_qual == "XX":
                        line.rendering_provider_npi = seg.get_element(8)

        return line

    def _parse_service_line_institutional(
        self, segments: List[X12Segment], start_idx: int, line_num: int
    ) -> ServiceLine837:
        """Parse SV2 (institutional service) into service line."""
        segment = segments[start_idx]

        # SV2*revenue_code*composite_procedure*charge*units*...
        line = ServiceLine837(
            line_number=line_num,
            revenue_code=segment.get_element(0),
            procedure_code="",
            charge_amount=Decimal(str(parse_x12_amount(segment.get_element(2)))),
            units=Decimal(str(parse_x12_amount(segment.get_element(3) or "1"))),
        )

        # Parse procedure composite
        composite = segment.get_composite(1)
        if len(composite) > 1:
            line.procedure_code = composite[1]
            line.procedure_modifiers = [m for m in composite[2:6] if m]

        # Look for associated segments (same as professional)
        for i in range(start_idx + 1, min(start_idx + 10, len(segments))):
            seg = segments[i]

            if seg.segment_id in ("SV1", "SV2", "LX", "SE"):
                break

            if seg.segment_id == "DTP":
                qualifier = seg.get_element(0)
                if qualifier == "472":
                    date_range = seg.get_element(2)
                    if "-" in date_range:
                        dates = date_range.split("-")
                        line.service_date = parse_x12_date(dates[0])
                        line.service_date_end = parse_x12_date(dates[1])
                    else:
                        line.service_date = parse_x12_date(date_range)

        return line

    def _parse_claim_date(self, segment: X12Segment, claim: Dict) -> None:
        """Parse DTP segment into claim dates."""
        qualifier = segment.get_element(0)
        date_format = segment.get_element(1)
        date_value = segment.get_element(2)

        parsed_date = None
        end_date = None

        if date_format == "D8":
            parsed_date = parse_x12_date(date_value)
        elif date_format == "RD8" and "-" in date_value:
            dates = date_value.split("-")
            parsed_date = parse_x12_date(dates[0])
            end_date = parse_x12_date(dates[1])

        if qualifier == "434":  # Statement dates
            claim["statement_from_date"] = parsed_date
            claim["statement_to_date"] = end_date or parsed_date
        elif qualifier == "435":  # Admission date
            claim["admission_date"] = parsed_date
        elif qualifier == "096":  # Discharge date
            claim["discharge_date"] = parsed_date

    def _parse_claim_reference(self, segment: X12Segment, claim: Dict) -> None:
        """Parse REF segment into claim references."""
        qualifier = segment.get_element(0)
        value = segment.get_element(1)

        if qualifier == "G1":  # Prior auth
            claim["prior_auth_number"] = value
        elif qualifier == "F8":  # Original claim
            claim["original_claim_number"] = value
        elif qualifier == "EA":  # Medical record
            claim["medical_record_number"] = value

    def _build_claim(
        self,
        claim_data: Dict,
        diagnoses: List[DiagnosisInfo],
        service_lines: List[ServiceLine837],
        envelope: X12Envelope,
        func_group: X12FunctionalGroup,
        trans_type: TransactionType,
        control_number: str,
        provider: Optional[ProviderInfo],
        subscriber: Optional[SubscriberInfo],
        patient: Optional[SubscriberInfo],
        segments: List[X12Segment],
    ) -> ParsedClaim837:
        """Build final ParsedClaim837 from parsed data."""

        return ParsedClaim837(
            transaction_control_number=control_number,
            claim_type=trans_type,
            submitter_name=func_group.sender_id,
            submitter_id=func_group.sender_id,
            receiver_name=func_group.receiver_id,
            receiver_id=func_group.receiver_id,
            billing_provider=provider or ProviderInfo(
                provider_type=ProviderType.BILLING, npi="", name="Unknown"
            ),
            subscriber=subscriber or SubscriberInfo(
                member_id="", last_name="Unknown", first_name=""
            ),
            patient=patient,
            claim_id=claim_data.get("claim_id", ""),
            total_charge=claim_data.get("total_charge", Decimal("0")),
            place_of_service=claim_data.get("place_of_service"),
            facility_code=claim_data.get("facility_code"),
            claim_frequency=claim_data.get("claim_frequency", ClaimFrequency.ORIGINAL),
            provider_signature=claim_data.get("provider_signature", True),
            assignment_of_benefits=claim_data.get("assignment_of_benefits", True),
            release_of_information=claim_data.get("release_of_information", "Y"),
            statement_from_date=claim_data.get("statement_from_date"),
            statement_to_date=claim_data.get("statement_to_date"),
            admission_date=claim_data.get("admission_date"),
            discharge_date=claim_data.get("discharge_date"),
            diagnoses=diagnoses,
            service_lines=service_lines,
            prior_auth_number=claim_data.get("prior_auth_number"),
            original_claim_number=claim_data.get("original_claim_number"),
            medical_record_number=claim_data.get("medical_record_number"),
            raw_segments=[str(s) for s in segments[:50]],  # First 50 for debug
        )
