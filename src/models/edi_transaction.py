"""
EDI Transaction Models for X12 Processing.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Provides SQLAlchemy models for:
- EDI transactions (837/835 tracking)
- EDI transaction claims
- EDI transaction errors
- EDI remittances
- EDI trading partners
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimeStampedModel, UUIDModel

if TYPE_CHECKING:
    from src.models.claim import Claim
    from src.models.tenant import Tenant


# =============================================================================
# Enums
# =============================================================================


class EDITransactionType(str, PyEnum):
    """EDI transaction types."""
    CLAIM_837P = "837P"
    CLAIM_837I = "837I"
    REMIT_835 = "835"
    ELIGIBILITY_270 = "270"
    ELIGIBILITY_271 = "271"
    CLAIM_STATUS_276 = "276"
    CLAIM_STATUS_277 = "277"
    ACK_997 = "997"
    ACK_999 = "999"


class EDIDirection(str, PyEnum):
    """EDI transaction direction."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class EDITransactionStatus(str, PyEnum):
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


class EDIClaimStatus(str, PyEnum):
    """EDI claim processing status."""
    PARSED = "parsed"
    VALIDATED = "validated"
    CREATED = "created"
    MATCHED = "matched"
    REJECTED = "rejected"
    ERROR = "error"


class EDIErrorType(str, PyEnum):
    """EDI error types."""
    SYNTAX = "syntax"
    VALIDATION = "validation"
    BUSINESS = "business"
    SYSTEM = "system"


class EDIErrorSeverity(str, PyEnum):
    """EDI error severity levels."""
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class EDIPaymentMethod(str, PyEnum):
    """EDI payment methods."""
    ACH = "ACH"
    CHECK = "CHK"
    NON_PAYMENT = "NON"
    BOP = "BOP"


class EDIDeliveryStatus(str, PyEnum):
    """EDI delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class EDIPartnerType(str, PyEnum):
    """EDI trading partner types."""
    PAYER = "payer"
    PROVIDER = "provider"
    CLEARINGHOUSE = "clearinghouse"
    VENDOR = "vendor"


class EDIConnectionType(str, PyEnum):
    """EDI connection types."""
    SFTP = "sftp"
    AS2 = "as2"
    API = "api"
    MANUAL = "manual"


# =============================================================================
# EDI Transaction Model
# =============================================================================


class EDITransaction(Base, UUIDModel, TimeStampedModel):
    """
    EDI Transaction tracking model.

    Stores metadata for all X12 EDI transactions including
    837 claims, 835 remittances, and eligibility transactions.
    """

    __tablename__ = "edi_transactions"

    # Tenant
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Transaction identification
    transaction_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    control_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    functional_group_control: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    transaction_set_control: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )

    # Transaction type and direction
    transaction_type: Mapped[EDITransactionType] = mapped_column(
        Enum(EDITransactionType),
        nullable=False,
        index=True,
    )
    direction: Mapped[EDIDirection] = mapped_column(
        Enum(EDIDirection),
        nullable=False,
        index=True,
    )

    # Processing status
    status: Mapped[EDITransactionStatus] = mapped_column(
        Enum(EDITransactionStatus),
        default=EDITransactionStatus.RECEIVED,
        nullable=False,
        index=True,
    )

    # Sender/Receiver
    sender_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    receiver_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    receiver_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Content
    raw_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    segment_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Processing metadata
    source: Mapped[str] = mapped_column(
        String(50),
        default="api",
        nullable=False,
        index=True,
    )
    claims_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Error tracking
    has_errors: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Performance
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Acknowledgment
    ack_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ack_transaction_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    ack_generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Timestamps
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
    validated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    claims: Mapped[list["EDITransactionClaim"]] = relationship(
        "EDITransactionClaim",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )
    errors: Mapped[list["EDITransactionError"]] = relationship(
        "EDITransactionError",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )
    remittances: Mapped[list["EDIRemittance"]] = relationship(
        "EDIRemittance",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_edi_transactions_received", "received_at"),
    )


# =============================================================================
# EDI Transaction Claim Model
# =============================================================================


class EDITransactionClaim(Base, UUIDModel, TimeStampedModel):
    """
    Links EDI transactions to individual claims.

    Stores parsed claim data before claim record creation.
    """

    __tablename__ = "edi_transaction_claims"

    # Transaction reference
    transaction_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("edi_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Claim reference (null until claim is created)
    claim_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("claims.id"),
        nullable=True,
        index=True,
    )

    # Claim identification from EDI
    patient_control_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    claim_frequency_code: Mapped[Optional[str]] = mapped_column(
        String(5),
        nullable=True,
    )

    # Position in transaction
    claim_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    hl_id_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Claim data (parsed from EDI)
    claim_data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Processing status
    status: Mapped[EDIClaimStatus] = mapped_column(
        Enum(EDIClaimStatus),
        default=EDIClaimStatus.PARSED,
        nullable=False,
        index=True,
    )

    # Validation
    validation_passed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    validation_errors: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Matching
    matched_existing_claim_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("claims.id"),
        nullable=True,
    )
    match_confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )

    # Relationships
    transaction: Mapped["EDITransaction"] = relationship(
        "EDITransaction",
        back_populates="claims",
    )

    # Constraints
    __table_args__ = (
        Index(
            "uq_edi_transaction_claim_sequence",
            "transaction_id",
            "claim_sequence",
            unique=True,
        ),
    )


# =============================================================================
# EDI Transaction Error Model
# =============================================================================


class EDITransactionError(Base, UUIDModel):
    """
    Detailed error tracking for EDI transactions.
    """

    __tablename__ = "edi_transaction_errors"

    # References
    transaction_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("edi_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_claim_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("edi_transaction_claims.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Error classification
    error_type: Mapped[EDIErrorType] = mapped_column(
        Enum(EDIErrorType),
        nullable=False,
        index=True,
    )
    error_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )
    severity: Mapped[EDIErrorSeverity] = mapped_column(
        Enum(EDIErrorSeverity),
        default=EDIErrorSeverity.ERROR,
        nullable=False,
    )

    # Error location
    segment_id: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    element_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    loop_id: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Error details
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )

    # Relationships
    transaction: Mapped["EDITransaction"] = relationship(
        "EDITransaction",
        back_populates="errors",
    )


# =============================================================================
# EDI Remittance Model
# =============================================================================


class EDIRemittance(Base, UUIDModel, TimeStampedModel):
    """
    Generated X12 835 remittance advices.
    """

    __tablename__ = "edi_remittances"

    # References
    transaction_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("edi_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("claims.id"),
        nullable=False,
        index=True,
    )

    # Control numbers
    control_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    check_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    # Payer/Payee
    payer_id: Mapped[str] = mapped_column(String(50), nullable=False)
    payer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payee_npi: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    payee_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Payment amounts
    total_charged: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    total_allowed: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    total_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    patient_responsibility: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        nullable=False,
    )

    # Payment method
    payment_method: Mapped[Optional[EDIPaymentMethod]] = mapped_column(
        Enum(EDIPaymentMethod),
        nullable=True,
    )
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)

    # Content
    raw_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Delivery status
    delivery_status: Mapped[EDIDeliveryStatus] = mapped_column(
        Enum(EDIDeliveryStatus),
        default=EDIDeliveryStatus.PENDING,
        nullable=False,
        index=True,
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivery_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relationships
    transaction: Mapped["EDITransaction"] = relationship(
        "EDITransaction",
        back_populates="remittances",
    )


# =============================================================================
# EDI Control Numbers Model
# =============================================================================


class EDIControlNumber(Base, UUIDModel, TimeStampedModel):
    """
    Control number sequence tracking.
    """

    __tablename__ = "edi_control_numbers"

    # Tenant
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Control number tracking
    control_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    direction: Mapped[EDIDirection] = mapped_column(
        Enum(EDIDirection),
        nullable=False,
    )
    partner_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Counter
    last_number: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    # Constraints
    __table_args__ = (
        Index(
            "uq_edi_control_numbers",
            "tenant_id",
            "control_type",
            "direction",
            "partner_id",
            unique=True,
        ),
    )


# =============================================================================
# EDI Trading Partner Model
# =============================================================================


class EDITradingPartner(Base, UUIDModel, TimeStampedModel):
    """
    EDI trading partner configuration.
    """

    __tablename__ = "edi_trading_partners"

    # Tenant
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Partner identification
    partner_id: Mapped[str] = mapped_column(String(50), nullable=False)
    partner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    partner_type: Mapped[EDIPartnerType] = mapped_column(
        Enum(EDIPartnerType),
        nullable=False,
        index=True,
    )

    # ISA identifiers
    isa_qualifier: Mapped[str] = mapped_column(
        String(2),
        default="ZZ",
        nullable=False,
    )
    isa_id: Mapped[str] = mapped_column(String(15), nullable=False)

    # GS identifiers
    gs_id: Mapped[str] = mapped_column(String(15), nullable=False)

    # Supported transactions
    supported_transactions: Mapped[dict] = mapped_column(
        JSONB,
        default=["837P", "835"],
        nullable=False,
    )

    # Connection settings
    connection_type: Mapped[EDIConnectionType] = mapped_column(
        Enum(EDIConnectionType),
        default=EDIConnectionType.SFTP,
        nullable=False,
    )
    connection_settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_production: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Constraints
    __table_args__ = (
        Index(
            "uq_edi_trading_partner",
            "tenant_id",
            "partner_id",
            unique=True,
        ),
    )
