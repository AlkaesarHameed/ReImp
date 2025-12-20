"""
EDI Service - Orchestrates X12 EDI processing.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Provides high-level EDI operations:
- Parse incoming 837 claims
- Generate 835 remittances
- Track EDI transactions
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
import logging

from src.services.edi.x12_base import (
    TransactionType,
    X12ParseError,
    X12ValidationError,
)
from src.services.edi.x12_837_parser import (
    X12837Parser,
    ParsedClaim837,
)
from src.services.edi.x12_835_generator import (
    X12835Generator,
    RemittanceAdvice,
    create_remittance_from_adjudication,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Models
# =============================================================================


class EDITransactionStatus(str, Enum):
    """EDI transaction processing status."""

    RECEIVED = "received"  # Just received
    VALIDATING = "validating"  # Syntax validation in progress
    VALIDATED = "validated"  # Syntax validation passed
    PARSING = "parsing"  # Content parsing in progress
    PARSED = "parsed"  # Successfully parsed
    PROCESSING = "processing"  # Claims being processed
    COMPLETED = "completed"  # All claims processed
    FAILED = "failed"  # Processing failed
    REJECTED = "rejected"  # Rejected due to errors


class EDIDirection(str, Enum):
    """EDI transaction direction."""

    INBOUND = "inbound"  # Received from external
    OUTBOUND = "outbound"  # Sent to external


@dataclass
class EDITransactionResult:
    """Result of EDI transaction processing."""

    transaction_id: str
    control_number: str
    transaction_type: TransactionType
    direction: EDIDirection
    status: EDITransactionStatus
    claims_count: int = 0
    claims_parsed: List[ParsedClaim837] = None
    errors: List[str] = None
    warnings: List[str] = None
    processing_time_ms: int = 0
    created_at: datetime = None

    def __post_init__(self):
        if self.claims_parsed is None:
            self.claims_parsed = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class EDI835Result:
    """Result of 835 generation."""

    transaction_id: str
    claim_id: str
    content: str
    control_number: str
    status: EDITransactionStatus
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


# =============================================================================
# Service
# =============================================================================


class EDIService:
    """
    EDI Service for X12 transaction processing.

    Handles:
    - 837P/837I claim parsing
    - 835 remittance generation
    - Transaction logging and tracking
    - Validation and error handling

    Usage:
        service = EDIService()
        result = await service.process_837(edi_content, tenant_id)
        claims = result.claims_parsed

        remittance = await service.generate_835(adjudication_result, payer, payee)
    """

    def __init__(
        self,
        db_session=None,
        cache_service=None,
    ):
        """
        Initialize EDI service.

        Args:
            db_session: Database session for transaction logging
            cache_service: Cache service for performance
        """
        self.db = db_session
        self.cache = cache_service
        self.parser_837 = X12837Parser()
        self.generator_835 = X12835Generator()

    async def process_837(
        self,
        content: str,
        tenant_id: UUID,
        source: str = "api",
    ) -> EDITransactionResult:
        """
        Process incoming X12 837 claim file.

        Args:
            content: Raw X12 837 EDI content
            tenant_id: Tenant ID for multi-tenancy
            source: Source identifier (api, sftp, etc.)

        Returns:
            EDITransactionResult with parsed claims
        """
        start_time = datetime.utcnow()
        transaction_id = str(uuid4())
        errors = []
        warnings = []
        claims = []

        try:
            logger.info(f"Processing 837 transaction {transaction_id}")

            # Validate basic structure
            if not content or not content.strip().startswith("ISA"):
                raise X12ValidationError("Invalid X12 content - must start with ISA segment")

            # Parse claims
            claims = self.parser_837.parse(content)

            # Validate parsed claims
            for claim in claims:
                claim_warnings = self._validate_claim(claim)
                warnings.extend(claim_warnings)

            # Determine transaction type from first claim
            trans_type = claims[0].claim_type if claims else TransactionType.CLAIM_837P

            # Extract control number from content
            control_number = self._extract_control_number(content)

            # Log transaction to database
            if self.db:
                await self._log_transaction(
                    transaction_id=transaction_id,
                    tenant_id=tenant_id,
                    transaction_type=trans_type,
                    direction=EDIDirection.INBOUND,
                    control_number=control_number,
                    raw_content=content,
                    claims_count=len(claims),
                    status=EDITransactionStatus.PARSED,
                    source=source,
                )

            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            logger.info(
                f"Successfully parsed {len(claims)} claims from transaction {transaction_id}"
            )

            return EDITransactionResult(
                transaction_id=transaction_id,
                control_number=control_number,
                transaction_type=trans_type,
                direction=EDIDirection.INBOUND,
                status=EDITransactionStatus.PARSED,
                claims_count=len(claims),
                claims_parsed=claims,
                errors=errors,
                warnings=warnings,
                processing_time_ms=processing_time,
            )

        except X12ParseError as e:
            logger.error(f"Parse error in transaction {transaction_id}: {e}")
            errors.append(str(e))

            return EDITransactionResult(
                transaction_id=transaction_id,
                control_number="",
                transaction_type=TransactionType.CLAIM_837P,
                direction=EDIDirection.INBOUND,
                status=EDITransactionStatus.FAILED,
                claims_count=0,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            logger.exception(f"Unexpected error in transaction {transaction_id}")
            errors.append(f"Unexpected error: {str(e)}")

            return EDITransactionResult(
                transaction_id=transaction_id,
                control_number="",
                transaction_type=TransactionType.CLAIM_837P,
                direction=EDIDirection.INBOUND,
                status=EDITransactionStatus.FAILED,
                errors=errors,
            )

    async def generate_835(
        self,
        adjudication_result: Dict[str, Any],
        payer_info: Dict[str, Any],
        payee_info: Dict[str, Any],
        tenant_id: UUID,
    ) -> EDI835Result:
        """
        Generate X12 835 remittance advice.

        Args:
            adjudication_result: Adjudication engine output
            payer_info: Payer identification info
            payee_info: Payee (provider) identification info
            tenant_id: Tenant ID for multi-tenancy

        Returns:
            EDI835Result with generated content
        """
        transaction_id = str(uuid4())
        claim_id = adjudication_result.get("claim_id", "")

        try:
            logger.info(f"Generating 835 for claim {claim_id}")

            # Create remittance from adjudication
            remittance = create_remittance_from_adjudication(
                adjudication_result,
                payer_info,
                payee_info,
            )

            # Set control numbers
            remittance.interchange_control_number = transaction_id[:9]
            remittance.transaction_control_number = "0001"

            # Generate 835 content
            content = self.generator_835.generate(remittance)

            # Log transaction
            if self.db:
                await self._log_transaction(
                    transaction_id=transaction_id,
                    tenant_id=tenant_id,
                    transaction_type=TransactionType.REMIT_835,
                    direction=EDIDirection.OUTBOUND,
                    control_number=remittance.interchange_control_number,
                    raw_content=content,
                    claims_count=1,
                    status=EDITransactionStatus.COMPLETED,
                    source="adjudication",
                )

            logger.info(f"Successfully generated 835 for claim {claim_id}")

            return EDI835Result(
                transaction_id=transaction_id,
                claim_id=claim_id,
                content=content,
                control_number=remittance.interchange_control_number,
                status=EDITransactionStatus.COMPLETED,
            )

        except Exception as e:
            logger.exception(f"Error generating 835 for claim {claim_id}")

            return EDI835Result(
                transaction_id=transaction_id,
                claim_id=claim_id,
                content="",
                control_number="",
                status=EDITransactionStatus.FAILED,
                errors=[str(e)],
            )

    async def validate_837(self, content: str) -> Dict[str, Any]:
        """
        Validate X12 837 syntax without processing.

        Args:
            content: Raw X12 837 content

        Returns:
            Validation result with errors and warnings
        """
        errors = []
        warnings = []

        try:
            # Basic structure check
            if not content.strip().startswith("ISA"):
                errors.append("Content must start with ISA segment")
                return {"valid": False, "errors": errors, "warnings": warnings}

            # Check for required segments
            required_segments = ["ISA", "GS", "ST", "BHT", "HL", "NM1", "CLM", "SE", "GE", "IEA"]
            for seg_id in required_segments:
                if f"{seg_id}*" not in content and f"{seg_id}~" not in content.replace("*", "~"):
                    errors.append(f"Missing required segment: {seg_id}")

            # Check segment terminator consistency
            if "~\n" in content or "~\r" in content:
                warnings.append("Segment terminators followed by line breaks (acceptable but not standard)")

            # Try parsing to catch structural issues
            try:
                self.parser_837.parse(content)
            except X12ParseError as e:
                errors.append(str(e))

            is_valid = len(errors) == 0

            return {
                "valid": is_valid,
                "errors": errors,
                "warnings": warnings,
            }

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return {"valid": False, "errors": errors, "warnings": warnings}

    def _validate_claim(self, claim: ParsedClaim837) -> List[str]:
        """Validate a parsed claim and return warnings."""
        warnings = []

        # Check required fields
        if not claim.billing_provider.npi:
            warnings.append(f"Claim {claim.claim_id}: Missing billing provider NPI")

        if not claim.subscriber.member_id:
            warnings.append(f"Claim {claim.claim_id}: Missing subscriber member ID")

        if not claim.diagnoses:
            warnings.append(f"Claim {claim.claim_id}: No diagnoses found")

        if not claim.service_lines:
            warnings.append(f"Claim {claim.claim_id}: No service lines found")

        # Validate amounts
        line_total = sum(line.charge_amount for line in claim.service_lines)
        if line_total != claim.total_charge:
            warnings.append(
                f"Claim {claim.claim_id}: Line item total ({line_total}) "
                f"doesn't match claim total ({claim.total_charge})"
            )

        return warnings

    def _extract_control_number(self, content: str) -> str:
        """Extract interchange control number from ISA segment."""
        try:
            # ISA control number is at position 13 (0-indexed element 12)
            isa_end = content.find("~")
            if isa_end > 0:
                isa_segment = content[:isa_end]
                elements = isa_segment.split("*")
                if len(elements) >= 14:
                    return elements[13].strip()
        except Exception:
            pass
        return ""

    async def _log_transaction(
        self,
        transaction_id: str,
        tenant_id: UUID,
        transaction_type: TransactionType,
        direction: EDIDirection,
        control_number: str,
        raw_content: str,
        claims_count: int,
        status: EDITransactionStatus,
        source: str,
    ) -> None:
        """Log EDI transaction to database."""
        # This would use the database session to insert a record
        # Implementation depends on your database model
        logger.debug(
            f"Logging EDI transaction: {transaction_id} "
            f"type={transaction_type.value} "
            f"direction={direction.value} "
            f"claims={claims_count}"
        )

    async def get_transaction(
        self, transaction_id: str, tenant_id: UUID
    ) -> Optional[Dict]:
        """Get EDI transaction by ID."""
        # Implementation would query database
        return None

    async def get_transactions(
        self,
        tenant_id: UUID,
        transaction_type: Optional[TransactionType] = None,
        status: Optional[EDITransactionStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """Get EDI transactions with filters."""
        # Implementation would query database
        return []


# =============================================================================
# Factory Function
# =============================================================================


_edi_service: Optional[EDIService] = None


def get_edi_service(
    db_session=None,
    cache_service=None,
) -> EDIService:
    """
    Get or create EDI service instance.

    Args:
        db_session: Database session
        cache_service: Cache service

    Returns:
        EDIService instance
    """
    global _edi_service

    if _edi_service is None:
        _edi_service = EDIService(
            db_session=db_session,
            cache_service=cache_service,
        )

    return _edi_service
