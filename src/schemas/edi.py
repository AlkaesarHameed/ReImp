"""
Pydantic Schemas for EDI Processing.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Provides request/response models for X12 EDI operations:
- 837 claim submission
- 835 remittance retrieval
- Transaction tracking
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.services.edi.x12_base import TransactionType


# =============================================================================
# Enums
# =============================================================================


class EDITransactionStatus(str):
    """EDI transaction processing status."""
    RECEIVED = "received"
    VALIDATING = "validating"
    VALIDATED = "validated"
    PARSING = "parsing"
    PARSED = "parsed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class EDIDirection(str):
    """EDI transaction direction."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


# =============================================================================
# 837 Request/Response Schemas
# =============================================================================


class EDI837SubmitRequest(BaseModel):
    """Request schema for 837 submission."""

    content: str = Field(
        ...,
        min_length=100,
        description="Raw X12 837 EDI content",
    )
    source: str = Field(
        default="api",
        max_length=50,
        description="Source identifier (api, sftp, etc.)",
    )
    validate_only: bool = Field(
        default=False,
        description="Validate without processing",
    )


class EDI837ValidationResult(BaseModel):
    """Result of 837 validation."""

    valid: bool = Field(..., description="Whether the EDI is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")
    segment_count: int = Field(default=0, description="Number of segments")
    claim_count: int = Field(default=0, description="Number of claims detected")


class ServiceLine837Response(BaseModel):
    """Parsed service line from 837."""

    line_number: int
    procedure_code: str
    modifiers: list[str] = Field(default_factory=list)
    charge_amount: Decimal
    units: int
    service_date: Optional[date] = None
    diagnosis_pointers: list[int] = Field(default_factory=list)


class Diagnosis837Response(BaseModel):
    """Parsed diagnosis from 837."""

    code: str
    code_system: str = "ICD10"
    sequence: int
    is_primary: bool = False


class Provider837Response(BaseModel):
    """Parsed provider from 837."""

    entity_type: str
    npi: Optional[str] = None
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class Subscriber837Response(BaseModel):
    """Parsed subscriber from 837."""

    member_id: str
    group_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    relationship: Optional[str] = None


class ParsedClaim837Response(BaseModel):
    """Parsed claim from 837."""

    claim_id: str
    claim_type: str
    patient_control_number: Optional[str] = None
    total_charge: Decimal
    place_of_service: Optional[str] = None
    admission_date: Optional[date] = None
    discharge_date: Optional[date] = None
    billing_provider: Provider837Response
    subscriber: Subscriber837Response
    patient: Optional[Subscriber837Response] = None
    diagnoses: list[Diagnosis837Response] = Field(default_factory=list)
    service_lines: list[ServiceLine837Response] = Field(default_factory=list)


class EDI837ProcessResult(BaseModel):
    """Result of 837 processing."""

    transaction_id: str = Field(..., description="Unique transaction identifier")
    control_number: str = Field(..., description="ISA control number")
    transaction_type: str = Field(..., description="837P or 837I")
    direction: str = Field(default="inbound")
    status: str = Field(..., description="Processing status")
    claims_count: int = Field(default=0, description="Number of claims parsed")
    claims_parsed: list[ParsedClaim837Response] = Field(
        default_factory=list,
        description="Parsed claim data",
    )
    errors: list[str] = Field(default_factory=list, description="Processing errors")
    warnings: list[str] = Field(default_factory=list, description="Processing warnings")
    processing_time_ms: int = Field(default=0, description="Processing time")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# 835 Request/Response Schemas
# =============================================================================


class EDI835GenerateRequest(BaseModel):
    """Request to generate 835 remittance."""

    claim_id: str = Field(..., description="Claim ID to generate 835 for")
    payer_name: str = Field(..., max_length=255)
    payer_id: str = Field(..., max_length=20)
    payer_address: Optional[str] = None
    payer_city: Optional[str] = None
    payer_state: Optional[str] = None
    payer_zip: Optional[str] = None
    payee_name: str = Field(..., max_length=255)
    payee_npi: str = Field(..., pattern=r"^\d{10}$")
    payee_tax_id: Optional[str] = None


class ServiceAdjustment835Response(BaseModel):
    """Service-level adjustment in 835."""

    group_code: str
    reason_code: str
    amount: Decimal
    quantity: Optional[int] = None


class ServicePayment835Response(BaseModel):
    """Service line payment in 835."""

    line_number: int
    procedure_code: str
    modifiers: list[str] = Field(default_factory=list)
    charged_amount: Decimal
    paid_amount: Decimal
    allowed_amount: Decimal
    patient_responsibility: Decimal
    adjustments: list[ServiceAdjustment835Response] = Field(default_factory=list)


class ClaimPayment835Response(BaseModel):
    """Claim-level payment in 835."""

    claim_id: str
    claim_status: str
    total_charged: Decimal
    total_paid: Decimal
    patient_responsibility: Decimal
    service_payments: list[ServicePayment835Response] = Field(default_factory=list)


class EDI835GenerateResult(BaseModel):
    """Result of 835 generation."""

    transaction_id: str = Field(..., description="Unique transaction identifier")
    claim_id: str = Field(..., description="Source claim ID")
    control_number: str = Field(..., description="ISA control number")
    content: str = Field(..., description="Generated X12 835 content")
    status: str = Field(..., description="Generation status")
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EDI835RetrieveResponse(BaseModel):
    """Response for 835 retrieval."""

    transaction_id: str
    claim_id: str
    control_number: str
    content: str
    payment_amount: Decimal
    payment_date: Optional[date] = None
    check_number: Optional[str] = None
    claim_payment: Optional[ClaimPayment835Response] = None
    created_at: datetime


# =============================================================================
# Transaction Schemas
# =============================================================================


class EDITransactionResponse(BaseModel):
    """EDI transaction record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    transaction_type: str
    direction: str
    status: str
    control_number: str
    claims_count: int
    source: str
    errors: Optional[list[str]] = None
    warnings: Optional[list[str]] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class EDITransactionListResponse(BaseModel):
    """Paginated list of EDI transactions."""

    items: list[EDITransactionResponse]
    total: int
    page: int
    page_size: int


class EDITransactionStats(BaseModel):
    """EDI transaction statistics."""

    total_transactions: int
    inbound_count: int
    outbound_count: int
    success_count: int
    failed_count: int
    claims_processed: int
    avg_processing_time_ms: float
    period_start: datetime
    period_end: datetime
