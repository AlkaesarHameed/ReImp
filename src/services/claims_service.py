"""
Claims Service for Insurance Claims Management.

Provides:
- Claim CRUD operations with tenant isolation
- Claim submission workflow
- Line item management
- Status tracking and history
- Tracking number generation

Source: Design Document Section 4.1 - Claims Processing
Verified: 2025-12-18
"""

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.enums import (
    ClaimPriority,
    ClaimSource,
    ClaimStatus,
    ClaimType,
    DiagnosisCodeSystem,
    ProcedureCodeSystem,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class ClaimsServiceError(Exception):
    """Base exception for claims service errors."""

    pass


class ClaimNotFoundError(ClaimsServiceError):
    """Raised when claim is not found."""

    pass


class ClaimValidationError(ClaimsServiceError):
    """Raised when claim validation fails."""

    def __init__(self, message: str, errors: Optional[list[str]] = None):
        super().__init__(message)
        self.errors = errors or []


class ClaimStatusTransitionError(ClaimsServiceError):
    """Raised when invalid status transition is attempted."""

    pass


# =============================================================================
# Data Transfer Objects
# =============================================================================


class ClaimCreateDTO:
    """Data transfer object for creating a claim."""

    def __init__(
        self,
        tenant_id: str,
        policy_id: str,
        member_id: str,
        provider_id: str,
        claim_type: ClaimType,
        service_date_from: date,
        service_date_to: date,
        diagnosis_codes: list[str],
        primary_diagnosis: str,
        total_charged: Decimal,
        currency: str = "USD",
        source: ClaimSource = ClaimSource.PORTAL,
        priority: ClaimPriority = ClaimPriority.NORMAL,
        billing_provider_id: Optional[str] = None,
        referring_provider_id: Optional[str] = None,
        diagnosis_code_system: DiagnosisCodeSystem = DiagnosisCodeSystem.ICD10_CM,
        place_of_service: Optional[str] = None,
        prior_auth_number: Optional[str] = None,
        external_claim_id: Optional[str] = None,
        admission_date: Optional[date] = None,
        discharge_date: Optional[date] = None,
    ):
        self.tenant_id = tenant_id
        self.policy_id = policy_id
        self.member_id = member_id
        self.provider_id = provider_id
        self.claim_type = claim_type
        self.service_date_from = service_date_from
        self.service_date_to = service_date_to
        self.diagnosis_codes = diagnosis_codes
        self.primary_diagnosis = primary_diagnosis
        self.total_charged = total_charged
        self.currency = currency
        self.source = source
        self.priority = priority
        self.billing_provider_id = billing_provider_id
        self.referring_provider_id = referring_provider_id
        self.diagnosis_code_system = diagnosis_code_system
        self.place_of_service = place_of_service
        self.prior_auth_number = prior_auth_number
        self.external_claim_id = external_claim_id
        self.admission_date = admission_date
        self.discharge_date = discharge_date


class LineItemDTO:
    """Data transfer object for claim line items."""

    def __init__(
        self,
        procedure_code: str,
        service_date: date,
        charged_amount: Decimal,
        quantity: int = 1,
        procedure_code_system: ProcedureCodeSystem = ProcedureCodeSystem.CPT,
        modifiers: Optional[list[str]] = None,
        description: Optional[str] = None,
        diagnosis_pointers: Optional[list[int]] = None,
        unit_type: str = "UN",
        ndc_code: Optional[str] = None,
    ):
        self.procedure_code = procedure_code
        self.service_date = service_date
        self.charged_amount = charged_amount
        self.quantity = quantity
        self.procedure_code_system = procedure_code_system
        self.modifiers = modifiers or []
        self.description = description
        self.diagnosis_pointers = diagnosis_pointers or [1]
        self.unit_type = unit_type
        self.ndc_code = ndc_code


class ClaimUpdateDTO:
    """Data transfer object for updating a claim."""

    def __init__(
        self,
        priority: Optional[ClaimPriority] = None,
        diagnosis_codes: Optional[list[str]] = None,
        primary_diagnosis: Optional[str] = None,
        place_of_service: Optional[str] = None,
        prior_auth_number: Optional[str] = None,
        internal_notes: Optional[str] = None,
        member_notes: Optional[str] = None,
    ):
        self.priority = priority
        self.diagnosis_codes = diagnosis_codes
        self.primary_diagnosis = primary_diagnosis
        self.place_of_service = place_of_service
        self.prior_auth_number = prior_auth_number
        self.internal_notes = internal_notes
        self.member_notes = member_notes


# =============================================================================
# Claims Service
# =============================================================================


class ClaimsService:
    """
    Service for claims management operations.

    Handles:
    - Claim CRUD with tenant isolation
    - Line item management
    - Status transitions
    - Tracking number generation
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # Tracking Number Generation
    # =========================================================================

    async def _generate_tracking_number(self, tenant_id: str) -> str:
        """
        Generate unique tracking number for a claim.

        Format: CLM-{YEAR}-{SEQUENCE:06d}
        Example: CLM-2025-000001
        """
        year = datetime.now(timezone.utc).year

        # Get the max sequence number for this year to avoid duplicates
        # This handles failed transactions that may have created gaps
        from src.models.claim import Claim

        result = await self.session.execute(
            select(func.max(Claim.tracking_number)).where(
                Claim.tracking_number.like(f"CLM-{year}-%")
            )
        )
        max_tracking = result.scalar_one_or_none()

        if max_tracking:
            # Extract sequence number from last tracking number
            try:
                seq = int(max_tracking.split("-")[-1])
                next_seq = seq + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1

        return f"CLM-{year}-{next_seq:06d}"

    # =========================================================================
    # Create Operations
    # =========================================================================

    async def create_claim(
        self,
        claim_data: ClaimCreateDTO,
        line_items: Optional[list[LineItemDTO]] = None,
        created_by: Optional[str] = None,
    ) -> "Claim":
        """
        Create a new claim with optional line items.

        Args:
            claim_data: Claim creation data
            line_items: Optional list of line items
            created_by: User ID creating the claim

        Returns:
            Created Claim object
        """
        from src.models.claim import Claim, ClaimLineItem, ClaimStatusHistory

        # Generate tracking number
        tracking_number = await self._generate_tracking_number(claim_data.tenant_id)

        # Create claim
        claim = Claim(
            id=uuid4(),
            tenant_id=claim_data.tenant_id,
            tracking_number=tracking_number,
            external_claim_id=claim_data.external_claim_id,
            claim_type=claim_data.claim_type,
            source=claim_data.source,
            priority=claim_data.priority,
            status=ClaimStatus.DRAFT,
            policy_id=claim_data.policy_id,
            member_id=claim_data.member_id,
            provider_id=claim_data.provider_id,
            billing_provider_id=claim_data.billing_provider_id,
            referring_provider_id=claim_data.referring_provider_id,
            service_date_from=claim_data.service_date_from,
            service_date_to=claim_data.service_date_to,
            admission_date=claim_data.admission_date,
            discharge_date=claim_data.discharge_date,
            diagnosis_codes=claim_data.diagnosis_codes,
            primary_diagnosis=claim_data.primary_diagnosis,
            diagnosis_code_system=claim_data.diagnosis_code_system,
            total_charged=claim_data.total_charged,
            currency=claim_data.currency,
            place_of_service=claim_data.place_of_service,
            prior_auth_number=claim_data.prior_auth_number,
            prior_auth_required=claim_data.prior_auth_number is not None,
        )

        self.session.add(claim)
        await self.session.flush()

        # Add line items
        if line_items:
            for i, item_data in enumerate(line_items, start=1):
                line_item = ClaimLineItem(
                    id=uuid4(),
                    claim_id=claim.id,
                    line_number=i,
                    procedure_code=item_data.procedure_code,
                    procedure_code_system=item_data.procedure_code_system,
                    modifiers=item_data.modifiers,
                    description=item_data.description,
                    diagnosis_pointers=item_data.diagnosis_pointers,
                    service_date=item_data.service_date,
                    quantity=item_data.quantity,
                    unit_type=item_data.unit_type,
                    charged_amount=item_data.charged_amount,
                    ndc_code=item_data.ndc_code,
                )
                self.session.add(line_item)

        # Record initial status
        # Convert created_by to UUID if valid
        from uuid import UUID as PyUUID
        created_by_uuid = None
        if created_by:
            try:
                created_by_uuid = PyUUID(created_by)
            except (ValueError, TypeError):
                created_by_uuid = None

        status_history = ClaimStatusHistory(
            id=uuid4(),
            claim_id=claim.id,
            previous_status=None,
            new_status=ClaimStatus.DRAFT,
            changed_by=created_by_uuid,
            actor_type="user" if created_by else "system",
            reason="Claim created",
        )
        self.session.add(status_history)

        await self.session.commit()

        # Re-query to get fully loaded claim with relationships
        claim_with_relations = await self.get_claim(str(claim.id), include_line_items=True)

        logger.info(f"Created claim {tracking_number} (ID: {claim.id})")
        return claim_with_relations

    async def add_line_item(
        self,
        claim_id: str,
        item_data: LineItemDTO,
    ) -> "ClaimLineItem":
        """Add a line item to an existing claim."""
        from src.models.claim import Claim, ClaimLineItem

        claim = await self.get_claim(claim_id)
        if not claim:
            raise ClaimNotFoundError(f"Claim not found: {claim_id}")

        if claim.status not in (ClaimStatus.DRAFT, ClaimStatus.NEEDS_REVIEW):
            raise ClaimStatusTransitionError(
                f"Cannot add line items to claim in {claim.status} status"
            )

        # Get next line number
        line_number = len(claim.line_items) + 1 if claim.line_items else 1

        line_item = ClaimLineItem(
            id=uuid4(),
            claim_id=claim_id,
            line_number=line_number,
            procedure_code=item_data.procedure_code,
            procedure_code_system=item_data.procedure_code_system,
            modifiers=item_data.modifiers,
            description=item_data.description,
            diagnosis_pointers=item_data.diagnosis_pointers,
            service_date=item_data.service_date,
            quantity=item_data.quantity,
            unit_type=item_data.unit_type,
            charged_amount=item_data.charged_amount,
            ndc_code=item_data.ndc_code,
        )

        self.session.add(line_item)

        # Recalculate totals
        claim.calculate_totals()

        await self.session.commit()
        await self.session.refresh(line_item)

        return line_item

    # =========================================================================
    # Read Operations
    # =========================================================================

    async def get_claim(
        self,
        claim_id: str,
        include_line_items: bool = True,
        include_documents: bool = False,
        include_history: bool = False,
    ) -> Optional["Claim"]:
        """Get claim by ID with optional related data."""
        from src.models.claim import Claim

        options = []
        if include_line_items:
            options.append(selectinload(Claim.line_items))
        if include_documents:
            options.append(selectinload(Claim.documents))
        if include_history:
            options.append(selectinload(Claim.status_history))

        query = select(Claim).where(Claim.id == claim_id)
        if options:
            query = query.options(*options)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_claim_by_tracking_number(
        self,
        tracking_number: str,
        tenant_id: str,
    ) -> Optional["Claim"]:
        """Get claim by tracking number within a tenant."""
        from src.models.claim import Claim

        result = await self.session.execute(
            select(Claim)
            .where(
                and_(
                    Claim.tracking_number == tracking_number,
                    Claim.tenant_id == tenant_id,
                )
            )
            .options(selectinload(Claim.line_items))
        )
        return result.scalar_one_or_none()

    async def list_claims(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ClaimStatus] = None,
        member_id: Optional[str] = None,
        provider_id: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        priority: Optional[ClaimPriority] = None,
    ) -> tuple[list["Claim"], int]:
        """
        List claims with pagination and filters.

        Returns:
            Tuple of (claims list, total count)
        """
        from src.models.claim import Claim

        # Base query
        query = select(Claim).where(Claim.tenant_id == tenant_id)

        # Apply filters
        if status:
            query = query.where(Claim.status == status)
        if member_id:
            query = query.where(Claim.member_id == member_id)
        if provider_id:
            query = query.where(Claim.provider_id == provider_id)
        if date_from:
            query = query.where(Claim.service_date_from >= date_from)
        if date_to:
            query = query.where(Claim.service_date_to <= date_to)
        if priority:
            query = query.where(Claim.priority == priority)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar_one()

        # Get paginated results
        query = (
            query.options(selectinload(Claim.line_items))
            .offset(skip)
            .limit(limit)
            .order_by(Claim.created_at.desc())
        )
        result = await self.session.execute(query)

        return list(result.scalars().all()), total

    async def search_claims(
        self,
        tenant_id: str,
        search_term: str,
        limit: int = 20,
    ) -> list["Claim"]:
        """
        Search claims by tracking number, external ID, or member ID.
        """
        from src.models.claim import Claim

        result = await self.session.execute(
            select(Claim)
            .where(
                and_(
                    Claim.tenant_id == tenant_id,
                    or_(
                        Claim.tracking_number.ilike(f"%{search_term}%"),
                        Claim.external_claim_id.ilike(f"%{search_term}%"),
                    ),
                )
            )
            .limit(limit)
            .order_by(Claim.created_at.desc())
        )
        return list(result.scalars().all())

    # =========================================================================
    # Update Operations
    # =========================================================================

    async def update_claim(
        self,
        claim_id: str,
        update_data: ClaimUpdateDTO,
        updated_by: Optional[str] = None,
    ) -> "Claim":
        """Update claim details."""
        claim = await self.get_claim(claim_id)
        if not claim:
            raise ClaimNotFoundError(f"Claim not found: {claim_id}")

        if claim.is_finalized:
            raise ClaimStatusTransitionError(
                f"Cannot update finalized claim in {claim.status} status"
            )

        # Apply updates
        if update_data.priority is not None:
            claim.priority = update_data.priority
        if update_data.diagnosis_codes is not None:
            claim.diagnosis_codes = update_data.diagnosis_codes
        if update_data.primary_diagnosis is not None:
            claim.primary_diagnosis = update_data.primary_diagnosis
        if update_data.place_of_service is not None:
            claim.place_of_service = update_data.place_of_service
        if update_data.prior_auth_number is not None:
            claim.prior_auth_number = update_data.prior_auth_number
            claim.prior_auth_required = True
        if update_data.internal_notes is not None:
            claim.internal_notes = update_data.internal_notes
        if update_data.member_notes is not None:
            claim.member_notes = update_data.member_notes

        claim.updated_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(claim)

        return claim

    # =========================================================================
    # Status Transitions
    # =========================================================================

    async def submit_claim(
        self,
        claim_id: str,
        submitted_by: str,
    ) -> "Claim":
        """
        Submit a draft claim for processing.

        Transitions: DRAFT -> SUBMITTED
        """
        claim = await self.get_claim(claim_id, include_line_items=True)
        if not claim:
            raise ClaimNotFoundError(f"Claim not found: {claim_id}")

        if claim.status != ClaimStatus.DRAFT:
            raise ClaimStatusTransitionError(
                f"Can only submit claims in DRAFT status, current: {claim.status}"
            )

        # Validate claim has line items
        if not claim.line_items:
            raise ClaimValidationError(
                "Cannot submit claim without line items",
                errors=["At least one line item is required"],
            )

        # Recalculate totals
        claim.calculate_totals()

        # Update status
        await self._transition_status(
            claim,
            ClaimStatus.SUBMITTED,
            submitted_by,
            "Claim submitted for processing",
        )

        claim.submitted_at = datetime.now(timezone.utc)
        # Convert submitted_by to UUID if valid, otherwise set to None
        try:
            from uuid import UUID as PyUUID
            claim.submitted_by = PyUUID(submitted_by) if submitted_by else None
        except (ValueError, TypeError):
            claim.submitted_by = None

        await self.session.commit()
        await self.session.refresh(claim)

        logger.info(f"Claim {claim.tracking_number} submitted")
        return claim

    async def start_processing(
        self,
        claim_id: str,
    ) -> "Claim":
        """
        Start document processing for a claim.

        Transitions: SUBMITTED -> DOC_PROCESSING
        """
        claim = await self.get_claim(claim_id)
        if not claim:
            raise ClaimNotFoundError(f"Claim not found: {claim_id}")

        if claim.status != ClaimStatus.SUBMITTED:
            raise ClaimStatusTransitionError(
                f"Can only start processing for SUBMITTED claims, current: {claim.status}"
            )

        await self._transition_status(
            claim,
            ClaimStatus.DOC_PROCESSING,
            None,
            "Document processing started",
        )

        claim.processing_started_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(claim)

        return claim

    async def complete_processing(
        self,
        claim_id: str,
        ocr_confidence: Optional[float] = None,
        llm_confidence: Optional[float] = None,
        providers_used: Optional[dict] = None,
    ) -> "Claim":
        """
        Complete document processing and move to validation.

        Transitions: DOC_PROCESSING -> VALIDATING
        """
        claim = await self.get_claim(claim_id)
        if not claim:
            raise ClaimNotFoundError(f"Claim not found: {claim_id}")

        if claim.status != ClaimStatus.DOC_PROCESSING:
            raise ClaimStatusTransitionError(
                f"Can only complete processing for DOC_PROCESSING claims, current: {claim.status}"
            )

        # Update processing metrics
        if ocr_confidence is not None:
            claim.ocr_confidence = Decimal(str(round(ocr_confidence, 3)))
        if llm_confidence is not None:
            claim.llm_confidence = Decimal(str(round(llm_confidence, 3)))
        if providers_used:
            claim.providers_used = providers_used

        await self._transition_status(
            claim,
            ClaimStatus.VALIDATING,
            None,
            "Document processing complete, validating",
        )

        await self.session.commit()
        await self.session.refresh(claim)

        return claim

    async def flag_for_review(
        self,
        claim_id: str,
        reason: str,
        flagged_by: Optional[str] = None,
    ) -> "Claim":
        """
        Flag a claim for manual review.

        Transitions: Any pending status -> NEEDS_REVIEW
        """
        claim = await self.get_claim(claim_id)
        if not claim:
            raise ClaimNotFoundError(f"Claim not found: {claim_id}")

        if claim.is_finalized:
            raise ClaimStatusTransitionError(
                f"Cannot flag finalized claim in {claim.status} status"
            )

        await self._transition_status(
            claim,
            ClaimStatus.NEEDS_REVIEW,
            flagged_by,
            reason,
        )

        await self.session.commit()
        await self.session.refresh(claim)

        return claim

    async def approve_claim(
        self,
        claim_id: str,
        approved_by: str,
        total_allowed: Optional[Decimal] = None,
        total_paid: Optional[Decimal] = None,
        patient_responsibility: Optional[Decimal] = None,
    ) -> "Claim":
        """
        Approve a claim after validation/review.

        Transitions: VALIDATING/ADJUDICATING/NEEDS_REVIEW -> APPROVED
        """
        claim = await self.get_claim(claim_id)
        if not claim:
            raise ClaimNotFoundError(f"Claim not found: {claim_id}")

        valid_statuses = (
            ClaimStatus.VALIDATING,
            ClaimStatus.ADJUDICATING,
            ClaimStatus.NEEDS_REVIEW,
        )
        if claim.status not in valid_statuses:
            raise ClaimStatusTransitionError(
                f"Can only approve claims in {valid_statuses}, current: {claim.status}"
            )

        # Set financial amounts
        if total_allowed is not None:
            claim.total_allowed = total_allowed
        if total_paid is not None:
            claim.total_paid = total_paid
        if patient_responsibility is not None:
            claim.patient_responsibility = patient_responsibility

        claim.adjudication_date = datetime.now(timezone.utc)
        claim.adjudicator_id = approved_by
        claim.adjudication_type = "manual" if claim.status == ClaimStatus.NEEDS_REVIEW else "auto"

        await self._transition_status(
            claim,
            ClaimStatus.APPROVED,
            approved_by,
            "Claim approved",
        )

        await self.session.commit()
        await self.session.refresh(claim)

        logger.info(f"Claim {claim.tracking_number} approved by {approved_by}")
        return claim

    async def deny_claim(
        self,
        claim_id: str,
        denied_by: str,
        denial_reason: str,
        denial_codes: Optional[list[str]] = None,
    ) -> "Claim":
        """
        Deny a claim.

        Transitions: VALIDATING/ADJUDICATING/NEEDS_REVIEW -> DENIED
        """
        claim = await self.get_claim(claim_id)
        if not claim:
            raise ClaimNotFoundError(f"Claim not found: {claim_id}")

        valid_statuses = (
            ClaimStatus.VALIDATING,
            ClaimStatus.ADJUDICATING,
            ClaimStatus.NEEDS_REVIEW,
        )
        if claim.status not in valid_statuses:
            raise ClaimStatusTransitionError(
                f"Can only deny claims in {valid_statuses}, current: {claim.status}"
            )

        claim.denial_reason = denial_reason
        claim.denial_codes = denial_codes or []
        claim.adjudication_date = datetime.now(timezone.utc)
        claim.adjudicator_id = denied_by

        await self._transition_status(
            claim,
            ClaimStatus.DENIED,
            denied_by,
            denial_reason,
        )

        await self.session.commit()
        await self.session.refresh(claim)

        logger.info(f"Claim {claim.tracking_number} denied: {denial_reason}")
        return claim

    async def _transition_status(
        self,
        claim: "Claim",
        new_status: ClaimStatus,
        changed_by: Optional[str],
        reason: str,
        details: Optional[dict] = None,
    ) -> None:
        """Record status transition in history."""
        from src.models.claim import ClaimStatusHistory
        from uuid import UUID as PyUUID

        previous_status = claim.status
        claim.status = new_status

        # Convert changed_by to UUID if valid
        changed_by_uuid = None
        if changed_by:
            try:
                changed_by_uuid = PyUUID(changed_by)
            except (ValueError, TypeError):
                changed_by_uuid = None

        history = ClaimStatusHistory(
            id=uuid4(),
            claim_id=claim.id,
            previous_status=previous_status,
            new_status=new_status,
            changed_by=changed_by_uuid,
            actor_type="user" if changed_by else "system",
            reason=reason,
            details=details,
        )
        self.session.add(history)

    # =========================================================================
    # Delete Operations
    # =========================================================================

    async def delete_claim(
        self,
        claim_id: str,
        soft_delete: bool = True,
    ) -> bool:
        """
        Delete a claim (only allowed for DRAFT status).
        """
        claim = await self.get_claim(claim_id)
        if not claim:
            raise ClaimNotFoundError(f"Claim not found: {claim_id}")

        if claim.status != ClaimStatus.DRAFT:
            raise ClaimStatusTransitionError(
                f"Can only delete claims in DRAFT status, current: {claim.status}"
            )

        if soft_delete:
            # Move to CLOSED status
            await self._transition_status(
                claim,
                ClaimStatus.CLOSED,
                None,
                "Claim deleted (soft delete)",
            )
            await self.session.commit()
        else:
            await self.session.delete(claim)
            await self.session.commit()

        logger.info(f"Deleted claim {claim_id} (soft={soft_delete})")
        return True

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_claims_stats(
        self,
        tenant_id: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> dict:
        """Get claims statistics for a tenant."""
        from src.models.claim import Claim

        query = select(
            Claim.status,
            func.count(Claim.id).label("count"),
            func.sum(Claim.total_charged).label("total_charged"),
            func.sum(Claim.total_paid).label("total_paid"),
        ).where(Claim.tenant_id == tenant_id)

        if date_from:
            query = query.where(Claim.created_at >= date_from)
        if date_to:
            query = query.where(Claim.created_at <= date_to)

        query = query.group_by(Claim.status)

        result = await self.session.execute(query)
        rows = result.fetchall()

        stats = {
            "by_status": {},
            "total_claims": 0,
            "total_charged": Decimal("0"),
            "total_paid": Decimal("0"),
        }

        for row in rows:
            status_name = row.status.value if row.status else "unknown"
            stats["by_status"][status_name] = {
                "count": row.count,
                "total_charged": float(row.total_charged or 0),
                "total_paid": float(row.total_paid or 0),
            }
            stats["total_claims"] += row.count
            stats["total_charged"] += row.total_charged or Decimal("0")
            stats["total_paid"] += row.total_paid or Decimal("0")

        stats["total_charged"] = float(stats["total_charged"])
        stats["total_paid"] = float(stats["total_paid"])

        return stats


# =============================================================================
# Factory Functions
# =============================================================================


async def get_claims_service(session: AsyncSession) -> ClaimsService:
    """Get claims service instance."""
    return ClaimsService(session)
