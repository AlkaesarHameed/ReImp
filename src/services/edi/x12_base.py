"""
X12 EDI Base Parser and Models.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Provides core X12 parsing functionality:
- Tokenizer for segment/element parsing
- Data models for X12 structures
- Validation utilities
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from datetime import datetime, date
import re
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class TransactionType(str, Enum):
    """X12 transaction set types."""

    CLAIM_837P = "837P"  # Professional Claims
    CLAIM_837I = "837I"  # Institutional Claims
    CLAIM_837D = "837D"  # Dental Claims
    REMIT_835 = "835"  # Remittance Advice
    ELIG_270 = "270"  # Eligibility Request
    ELIG_271 = "271"  # Eligibility Response
    ACK_999 = "999"  # Acknowledgment
    ACK_TA1 = "TA1"  # Interchange Acknowledgment


class SegmentID(str, Enum):
    """Common X12 segment identifiers."""

    # Envelope
    ISA = "ISA"  # Interchange Control Header
    IEA = "IEA"  # Interchange Control Trailer
    GS = "GS"  # Functional Group Header
    GE = "GE"  # Functional Group Trailer
    ST = "ST"  # Transaction Set Header
    SE = "SE"  # Transaction Set Trailer

    # Header
    BHT = "BHT"  # Beginning of Hierarchical Transaction

    # Hierarchical
    HL = "HL"  # Hierarchical Level

    # Names and Identification
    NM1 = "NM1"  # Individual or Organizational Name
    N3 = "N3"  # Party Location (Address)
    N4 = "N4"  # Geographic Location
    REF = "REF"  # Reference Information
    PER = "PER"  # Administrative Communications Contact

    # Dates
    DTP = "DTP"  # Date/Time Period
    DMG = "DMG"  # Demographic Information

    # Claim
    CLM = "CLM"  # Claim Information
    HI = "HI"  # Health Care Information Codes (Diagnoses)
    SBR = "SBR"  # Subscriber Information
    PAT = "PAT"  # Patient Information
    PRV = "PRV"  # Provider Information

    # Service Line
    SV1 = "SV1"  # Professional Service
    SV2 = "SV2"  # Institutional Service
    LX = "LX"  # Service Line Number

    # Amounts
    AMT = "AMT"  # Monetary Amount
    QTY = "QTY"  # Quantity

    # 835 Specific
    BPR = "BPR"  # Financial Information
    TRN = "TRN"  # Reassociation Trace Number
    CLP = "CLP"  # Claim Payment Information
    SVC = "SVC"  # Service Payment Information
    CAS = "CAS"  # Claim Adjustment


# =============================================================================
# Exceptions
# =============================================================================


class X12ValidationError(Exception):
    """X12 validation error with detailed context."""

    def __init__(
        self,
        message: str,
        segment_id: Optional[str] = None,
        segment_position: Optional[int] = None,
        element_position: Optional[int] = None,
        raw_segment: Optional[str] = None,
    ):
        self.message = message
        self.segment_id = segment_id
        self.segment_position = segment_position
        self.element_position = element_position
        self.raw_segment = raw_segment
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = [self.message]
        if self.segment_id:
            parts.append(f"Segment: {self.segment_id}")
        if self.segment_position is not None:
            parts.append(f"Position: {self.segment_position}")
        if self.element_position is not None:
            parts.append(f"Element: {self.element_position}")
        return " | ".join(parts)


class X12ParseError(X12ValidationError):
    """Error during X12 parsing."""

    pass


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class X12Segment:
    """
    Represents a single X12 segment.

    Example: NM1*IL*1*DOE*JOHN****MI*12345~
    - segment_id: NM1
    - elements: ['IL', '1', 'DOE', 'JOHN', '', '', '', 'MI', '12345']
    """

    segment_id: str
    elements: List[str]
    position: int = 0

    def get_element(self, index: int, default: str = "") -> str:
        """Get element at index (0-based after segment ID)."""
        if 0 <= index < len(self.elements):
            return self.elements[index]
        return default

    def get_element_int(self, index: int, default: int = 0) -> int:
        """Get element as integer."""
        value = self.get_element(index)
        if value:
            try:
                return int(value)
            except ValueError:
                return default
        return default

    def get_element_float(self, index: int, default: float = 0.0) -> float:
        """Get element as float."""
        value = self.get_element(index)
        if value:
            try:
                return float(value)
            except ValueError:
                return default
        return default

    def get_composite(self, index: int, separator: str = ":") -> List[str]:
        """Get composite element as list of sub-elements."""
        value = self.get_element(index)
        if value:
            return value.split(separator)
        return []

    def get_sub_elements(self, index: int, separator: str = ":") -> List[str]:
        """Alias for get_composite for backward compatibility."""
        return self.get_composite(index, separator)

    def __str__(self) -> str:
        return f"{self.segment_id}*{'*'.join(self.elements)}"


@dataclass
class X12Loop:
    """
    Represents an X12 loop (group of related segments).

    Loops are hierarchical structures that group related data.
    """

    loop_id: str
    segments: List[X12Segment] = field(default_factory=list)
    sub_loops: List["X12Loop"] = field(default_factory=list)

    def find_segment(self, segment_id: str) -> Optional[X12Segment]:
        """Find first segment with given ID."""
        for segment in self.segments:
            if segment.segment_id == segment_id:
                return segment
        return None

    def find_segments(self, segment_id: str) -> List[X12Segment]:
        """Find all segments with given ID."""
        return [s for s in self.segments if s.segment_id == segment_id]

    def find_loop(self, loop_id: str) -> Optional["X12Loop"]:
        """Find first sub-loop with given ID."""
        for loop in self.sub_loops:
            if loop.loop_id == loop_id:
                return loop
        return None

    def find_loops(self, loop_id: str) -> List["X12Loop"]:
        """Find all sub-loops with given ID."""
        return [l for l in self.sub_loops if l.loop_id == loop_id]


@dataclass
class X12Envelope:
    """
    X12 interchange envelope (ISA/IEA).

    Contains control information for the interchange.
    """

    sender_id: str
    sender_qualifier: str
    receiver_id: str
    receiver_qualifier: str
    control_number: str
    date: str
    time: str
    version: str = "00501"
    acknowledgment_requested: str = "0"
    usage_indicator: str = "P"  # P=Production, T=Test

    @classmethod
    def from_isa_segment(cls, segment: X12Segment) -> "X12Envelope":
        """Parse ISA segment into envelope."""
        return cls(
            sender_qualifier=segment.get_element(4),
            sender_id=segment.get_element(5).strip(),
            receiver_qualifier=segment.get_element(6),
            receiver_id=segment.get_element(7).strip(),
            date=segment.get_element(8),
            time=segment.get_element(9),
            version=segment.get_element(11),
            control_number=segment.get_element(12),
            acknowledgment_requested=segment.get_element(13),
            usage_indicator=segment.get_element(14),
        )


@dataclass
class X12FunctionalGroup:
    """
    X12 functional group (GS/GE).

    Groups related transaction sets.
    """

    functional_id: str  # HC=Health Care Claim, HP=Health Care Payment
    sender_id: str
    receiver_id: str
    date: str
    time: str
    control_number: str
    responsible_agency: str = "X"
    version: str = "005010X222A1"

    @classmethod
    def from_gs_segment(cls, segment: X12Segment) -> "X12FunctionalGroup":
        """Parse GS segment into functional group."""
        return cls(
            functional_id=segment.get_element(0),
            sender_id=segment.get_element(1),
            receiver_id=segment.get_element(2),
            date=segment.get_element(3),
            time=segment.get_element(4),
            control_number=segment.get_element(5),
            responsible_agency=segment.get_element(6),
            version=segment.get_element(7),
        )


@dataclass
class X12Transaction:
    """
    Complete X12 transaction.

    Contains envelope, functional group, and transaction content.
    """

    envelope: X12Envelope
    functional_group: X12FunctionalGroup
    transaction_type: TransactionType
    control_number: str
    segments: List[X12Segment] = field(default_factory=list)
    loops: List[X12Loop] = field(default_factory=list)

    def get_transaction_type_code(self) -> str:
        """Get the 3-digit transaction type code."""
        return self.transaction_type.value[:3]


# =============================================================================
# Tokenizer
# =============================================================================


class X12Tokenizer:
    """
    X12 EDI tokenizer.

    Handles parsing of raw X12 content into segments and elements.
    Automatically detects delimiters from ISA segment.
    """

    # Default delimiters
    DEFAULT_ELEMENT_SEPARATOR = "*"
    DEFAULT_SEGMENT_TERMINATOR = "~"
    DEFAULT_COMPONENT_SEPARATOR = ":"
    DEFAULT_REPETITION_SEPARATOR = "^"

    def __init__(
        self,
        content: Optional[str] = None,
        element_separator: Optional[str] = None,
        segment_terminator: Optional[str] = None,
        component_separator: Optional[str] = None,
        repetition_separator: Optional[str] = None,
    ):
        self._content = content
        self.element_separator = element_separator or self.DEFAULT_ELEMENT_SEPARATOR
        self.segment_terminator = segment_terminator or self.DEFAULT_SEGMENT_TERMINATOR
        self.component_separator = component_separator or self.DEFAULT_COMPONENT_SEPARATOR
        self.repetition_separator = repetition_separator or self.DEFAULT_REPETITION_SEPARATOR

        # Auto-detect delimiters if content is provided
        if content and content.startswith("ISA"):
            (
                self.element_separator,
                self.segment_terminator,
                self.component_separator,
                self.repetition_separator,
            ) = self.detect_delimiters(content)

    @property
    def sub_element_separator(self) -> str:
        """Alias for component_separator for backward compatibility."""
        return self.component_separator

    def detect_delimiters(self, content: str) -> Tuple[str, str, str, str]:
        """
        Detect delimiters from ISA segment.

        ISA is always 106 characters with fixed positions:
        - Element separator: position 3
        - Component separator: position 104
        - Segment terminator: position 105
        """
        if not content.startswith("ISA"):
            raise X12ParseError("Content must start with ISA segment")

        if len(content) < 106:
            raise X12ParseError("ISA segment must be at least 106 characters")

        element_sep = content[3]
        # Component separator is at position 104 (after ISA16)
        component_sep = content[104]
        # Segment terminator is at position 105
        segment_term = content[105]

        # Repetition separator is ISA11 (position 82-83)
        isa_elements = content[:105].split(element_sep)
        if len(isa_elements) >= 12:
            rep_sep = isa_elements[11]
        else:
            rep_sep = self.DEFAULT_REPETITION_SEPARATOR

        return element_sep, segment_term, component_sep, rep_sep

    def tokenize(self, content: Optional[str] = None, auto_detect: bool = True) -> List[X12Segment]:
        """
        Tokenize X12 content into segments.

        Args:
            content: Raw X12 EDI content (uses constructor content if not provided)
            auto_detect: Automatically detect delimiters from ISA

        Returns:
            List of X12Segment objects
        """
        # Use stored content if not provided
        if content is None:
            content = self._content
        if content is None:
            raise X12ParseError("No content provided to tokenize")

        # Clean content
        content = content.strip()

        # Auto-detect delimiters
        if auto_detect and content.startswith("ISA"):
            (
                self.element_separator,
                self.segment_terminator,
                self.component_separator,
                self.repetition_separator,
            ) = self.detect_delimiters(content)

        # Split into raw segments
        raw_segments = content.split(self.segment_terminator)

        segments = []
        for position, raw in enumerate(raw_segments):
            raw = raw.strip()
            if not raw:
                continue

            # Handle newlines within segments
            raw = raw.replace("\n", "").replace("\r", "")

            # Split into elements
            elements = raw.split(self.element_separator)

            if not elements:
                continue

            segment = X12Segment(
                segment_id=elements[0],
                elements=elements[1:] if len(elements) > 1 else [],
                position=position,
            )
            segments.append(segment)

        return segments

    def parse_envelope(
        self, segments: List[X12Segment]
    ) -> Tuple[X12Envelope, X12FunctionalGroup, List[X12Segment]]:
        """
        Parse ISA/GS envelope from segments.

        Returns:
            Tuple of (envelope, functional_group, remaining_segments)
        """
        if not segments:
            raise X12ParseError("No segments to parse")

        # Find ISA
        isa_segment = None
        gs_segment = None
        content_start = 0

        for i, segment in enumerate(segments):
            if segment.segment_id == "ISA":
                isa_segment = segment
            elif segment.segment_id == "GS":
                gs_segment = segment
                content_start = i + 1
                break

        if not isa_segment:
            raise X12ParseError("Missing ISA segment")
        if not gs_segment:
            raise X12ParseError("Missing GS segment")

        envelope = X12Envelope.from_isa_segment(isa_segment)
        functional_group = X12FunctionalGroup.from_gs_segment(gs_segment)

        # Find content end (before GE/IEA)
        content_end = len(segments)
        for i in range(len(segments) - 1, -1, -1):
            if segments[i].segment_id in ("GE", "IEA"):
                content_end = i
            elif segments[i].segment_id == "SE":
                content_end = i
                break

        return envelope, functional_group, segments[content_start:content_end]

    def get_transaction_type(
        self, segments: List[X12Segment]
    ) -> Tuple[TransactionType, str]:
        """
        Determine transaction type from ST segment.

        Returns:
            Tuple of (TransactionType, control_number)
        """
        for segment in segments:
            if segment.segment_id == "ST":
                code = segment.get_element(0)
                control = segment.get_element(1)

                # Map transaction code to type
                type_map = {
                    "837": None,  # Need to determine P/I from BHT
                    "835": TransactionType.REMIT_835,
                    "270": TransactionType.ELIG_270,
                    "271": TransactionType.ELIG_271,
                    "999": TransactionType.ACK_999,
                }

                if code == "837":
                    # Determine professional vs institutional from BHT
                    for seg in segments:
                        if seg.segment_id == "BHT":
                            structure_code = seg.get_element(1)
                            # 0019 = Professional, 0011 = Institutional
                            if structure_code == "0019":
                                return TransactionType.CLAIM_837P, control
                            elif structure_code == "0011":
                                return TransactionType.CLAIM_837I, control
                    # Default to professional
                    return TransactionType.CLAIM_837P, control

                if code in type_map and type_map[code]:
                    return type_map[code], control

        raise X12ParseError("Unable to determine transaction type")


# =============================================================================
# Utility Functions
# =============================================================================


def parse_x12_date(date_str: str) -> Optional[date]:
    """
    Parse X12 date format (CCYYMMDD or YYMMDD).

    Args:
        date_str: Date string in X12 format

    Returns:
        Python date object or None
    """
    if not date_str:
        return None

    try:
        if len(date_str) == 8:
            return datetime.strptime(date_str, "%Y%m%d").date()
        elif len(date_str) == 6:
            # Assume 20xx for 2-digit year
            year = int(date_str[:2])
            if year < 50:
                year += 2000
            else:
                year += 1900
            return date(year, int(date_str[2:4]), int(date_str[4:6]))
    except ValueError:
        pass

    return None


def format_x12_date(d: date) -> str:
    """Format date as X12 CCYYMMDD."""
    return d.strftime("%Y%m%d")


def parse_x12_time(time_str: str) -> Optional[str]:
    """
    Parse X12 time format (HHMM or HHMMSS).

    Returns time as HH:MM:SS string.
    """
    if not time_str:
        return None

    try:
        if len(time_str) >= 4:
            hours = int(time_str[:2])
            minutes = int(time_str[2:4])
            seconds = int(time_str[4:6]) if len(time_str) >= 6 else 0
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except ValueError:
        pass

    return None


def format_x12_time(t: datetime) -> str:
    """Format time as X12 HHMM."""
    return t.strftime("%H%M")


def parse_x12_amount(amount_str: str) -> float:
    """Parse X12 monetary amount."""
    if not amount_str:
        return 0.0
    try:
        return float(amount_str)
    except ValueError:
        return 0.0


def format_x12_amount(amount: float) -> str:
    """Format amount for X12 (2 decimal places)."""
    return f"{amount:.2f}"


def validate_npi(npi: str) -> bool:
    """
    Validate NPI using Luhn algorithm.

    NPI is a 10-digit identifier for healthcare providers.
    """
    if not npi or len(npi) != 10:
        return False

    if not npi.isdigit():
        return False

    # Apply Luhn algorithm with healthcare prefix (80840)
    prefix = "80840"
    full_number = prefix + npi

    total = 0
    for i, digit in enumerate(reversed(full_number)):
        d = int(digit)
        if i % 2 == 0:
            total += d
        else:
            doubled = d * 2
            total += doubled if doubled < 10 else doubled - 9

    return total % 10 == 0
