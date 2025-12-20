"""
Claim Status State Machine.

Provides:
- Valid status transitions
- Transition validation
- Status workflow management
- Event-driven state changes

Source: Design Document Section 4.1 - Claim Lifecycle
Verified: 2025-12-18

State Diagram:
    DRAFT -> SUBMITTED
    SUBMITTED -> DOC_PROCESSING
    DOC_PROCESSING -> VALIDATING | NEEDS_REVIEW
    VALIDATING -> ADJUDICATING | DENIED | NEEDS_REVIEW
    ADJUDICATING -> APPROVED | DENIED | NEEDS_REVIEW
    APPROVED -> PAYMENT_PROCESSING
    PAYMENT_PROCESSING -> PAID | NEEDS_REVIEW
    PAID -> CLOSED
    NEEDS_REVIEW -> APPROVED | DENIED | VALIDATING
    DENIED -> CLOSED
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional

from src.core.enums import ClaimStatus

logger = logging.getLogger(__name__)


class TransitionEvent(str, Enum):
    """Events that trigger state transitions."""

    SUBMIT = "submit"
    START_PROCESSING = "start_processing"
    COMPLETE_PROCESSING = "complete_processing"
    PROCESSING_FAILED = "processing_failed"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    FLAG_FOR_REVIEW = "flag_for_review"
    APPROVE = "approve"
    DENY = "deny"
    RESUME_PROCESSING = "resume_processing"
    START_PAYMENT = "start_payment"
    PAYMENT_COMPLETE = "payment_complete"
    PAYMENT_FAILED = "payment_failed"
    CLOSE = "close"


@dataclass
class Transition:
    """Represents a valid state transition."""

    from_status: ClaimStatus
    to_status: ClaimStatus
    event: TransitionEvent
    requires_permission: Optional[str] = None
    requires_reason: bool = False
    auto_transition: bool = False  # Triggered automatically by system


@dataclass
class TransitionContext:
    """Context for a transition attempt."""

    claim_id: str
    current_status: ClaimStatus
    target_status: ClaimStatus
    event: TransitionEvent
    triggered_by: Optional[str] = None
    reason: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TransitionResult:
    """Result of a transition attempt."""

    success: bool
    from_status: ClaimStatus
    to_status: Optional[ClaimStatus] = None
    error: Optional[str] = None
    transition: Optional[Transition] = None


# =============================================================================
# Valid Transitions Definition
# =============================================================================


VALID_TRANSITIONS: list[Transition] = [
    # From DRAFT
    Transition(
        from_status=ClaimStatus.DRAFT,
        to_status=ClaimStatus.SUBMITTED,
        event=TransitionEvent.SUBMIT,
        requires_permission="claims:submit",
    ),
    Transition(
        from_status=ClaimStatus.DRAFT,
        to_status=ClaimStatus.CLOSED,
        event=TransitionEvent.CLOSE,
        requires_permission="claims:delete",
        requires_reason=True,
    ),

    # From SUBMITTED
    Transition(
        from_status=ClaimStatus.SUBMITTED,
        to_status=ClaimStatus.DOC_PROCESSING,
        event=TransitionEvent.START_PROCESSING,
        auto_transition=True,
    ),

    # From DOC_PROCESSING
    Transition(
        from_status=ClaimStatus.DOC_PROCESSING,
        to_status=ClaimStatus.VALIDATING,
        event=TransitionEvent.COMPLETE_PROCESSING,
        auto_transition=True,
    ),
    Transition(
        from_status=ClaimStatus.DOC_PROCESSING,
        to_status=ClaimStatus.NEEDS_REVIEW,
        event=TransitionEvent.PROCESSING_FAILED,
        auto_transition=True,
    ),
    Transition(
        from_status=ClaimStatus.DOC_PROCESSING,
        to_status=ClaimStatus.NEEDS_REVIEW,
        event=TransitionEvent.FLAG_FOR_REVIEW,
        requires_reason=True,
    ),

    # From VALIDATING
    Transition(
        from_status=ClaimStatus.VALIDATING,
        to_status=ClaimStatus.ADJUDICATING,
        event=TransitionEvent.VALIDATION_PASSED,
        auto_transition=True,
    ),
    Transition(
        from_status=ClaimStatus.VALIDATING,
        to_status=ClaimStatus.DENIED,
        event=TransitionEvent.VALIDATION_FAILED,
        requires_permission="claims:deny",
        requires_reason=True,
    ),
    Transition(
        from_status=ClaimStatus.VALIDATING,
        to_status=ClaimStatus.NEEDS_REVIEW,
        event=TransitionEvent.FLAG_FOR_REVIEW,
        requires_reason=True,
    ),

    # From ADJUDICATING
    Transition(
        from_status=ClaimStatus.ADJUDICATING,
        to_status=ClaimStatus.APPROVED,
        event=TransitionEvent.APPROVE,
        requires_permission="claims:approve",
    ),
    Transition(
        from_status=ClaimStatus.ADJUDICATING,
        to_status=ClaimStatus.DENIED,
        event=TransitionEvent.DENY,
        requires_permission="claims:deny",
        requires_reason=True,
    ),
    Transition(
        from_status=ClaimStatus.ADJUDICATING,
        to_status=ClaimStatus.NEEDS_REVIEW,
        event=TransitionEvent.FLAG_FOR_REVIEW,
        requires_reason=True,
    ),

    # From APPROVED
    Transition(
        from_status=ClaimStatus.APPROVED,
        to_status=ClaimStatus.PAYMENT_PROCESSING,
        event=TransitionEvent.START_PAYMENT,
        auto_transition=True,
    ),

    # From PAYMENT_PROCESSING
    Transition(
        from_status=ClaimStatus.PAYMENT_PROCESSING,
        to_status=ClaimStatus.PAID,
        event=TransitionEvent.PAYMENT_COMPLETE,
        auto_transition=True,
    ),
    Transition(
        from_status=ClaimStatus.PAYMENT_PROCESSING,
        to_status=ClaimStatus.NEEDS_REVIEW,
        event=TransitionEvent.PAYMENT_FAILED,
        auto_transition=True,
    ),

    # From PAID
    Transition(
        from_status=ClaimStatus.PAID,
        to_status=ClaimStatus.CLOSED,
        event=TransitionEvent.CLOSE,
        auto_transition=True,
    ),

    # From NEEDS_REVIEW
    Transition(
        from_status=ClaimStatus.NEEDS_REVIEW,
        to_status=ClaimStatus.APPROVED,
        event=TransitionEvent.APPROVE,
        requires_permission="claims:approve",
    ),
    Transition(
        from_status=ClaimStatus.NEEDS_REVIEW,
        to_status=ClaimStatus.DENIED,
        event=TransitionEvent.DENY,
        requires_permission="claims:deny",
        requires_reason=True,
    ),
    Transition(
        from_status=ClaimStatus.NEEDS_REVIEW,
        to_status=ClaimStatus.VALIDATING,
        event=TransitionEvent.RESUME_PROCESSING,
        requires_permission="claims:review",
    ),

    # From DENIED
    Transition(
        from_status=ClaimStatus.DENIED,
        to_status=ClaimStatus.CLOSED,
        event=TransitionEvent.CLOSE,
        auto_transition=True,
    ),
]


# =============================================================================
# State Machine
# =============================================================================


class ClaimStateMachine:
    """
    State machine for claim status transitions.

    Manages valid status transitions and validates transition requests.
    """

    def __init__(self):
        """Initialize state machine with transition map."""
        self._transitions: dict[tuple[ClaimStatus, TransitionEvent], Transition] = {}
        self._from_status_map: dict[ClaimStatus, list[Transition]] = {}
        self._callbacks: dict[TransitionEvent, list[Callable]] = {}

        self._build_transition_maps()

    def _build_transition_maps(self) -> None:
        """Build lookup maps for transitions."""
        for transition in VALID_TRANSITIONS:
            key = (transition.from_status, transition.event)
            self._transitions[key] = transition

            if transition.from_status not in self._from_status_map:
                self._from_status_map[transition.from_status] = []
            self._from_status_map[transition.from_status].append(transition)

    def get_valid_transitions(self, status: ClaimStatus) -> list[Transition]:
        """Get all valid transitions from a given status."""
        return self._from_status_map.get(status, [])

    def get_valid_events(self, status: ClaimStatus) -> list[TransitionEvent]:
        """Get all valid events for a given status."""
        return [t.event for t in self.get_valid_transitions(status)]

    def get_next_statuses(self, status: ClaimStatus) -> list[ClaimStatus]:
        """Get all possible next statuses from current status."""
        return [t.to_status for t in self.get_valid_transitions(status)]

    def can_transition(
        self,
        from_status: ClaimStatus,
        to_status: ClaimStatus,
    ) -> bool:
        """Check if transition from one status to another is valid."""
        for transition in self.get_valid_transitions(from_status):
            if transition.to_status == to_status:
                return True
        return False

    def get_transition(
        self,
        from_status: ClaimStatus,
        event: TransitionEvent,
    ) -> Optional[Transition]:
        """Get transition for a status and event combination."""
        return self._transitions.get((from_status, event))

    def validate_transition(
        self,
        context: TransitionContext,
        user_permissions: Optional[list[str]] = None,
    ) -> TransitionResult:
        """
        Validate a transition attempt.

        Args:
            context: Transition context with all details
            user_permissions: User's permission list

        Returns:
            TransitionResult indicating success/failure
        """
        transition = self.get_transition(context.current_status, context.event)

        if not transition:
            return TransitionResult(
                success=False,
                from_status=context.current_status,
                error=f"Invalid transition: {context.current_status.value} + {context.event.value}",
            )

        # Verify target status matches
        if context.target_status != transition.to_status:
            return TransitionResult(
                success=False,
                from_status=context.current_status,
                error=f"Target status mismatch. Expected {transition.to_status.value}, got {context.target_status.value}",
            )

        # Check permission
        if transition.requires_permission:
            if not user_permissions or transition.requires_permission not in user_permissions:
                return TransitionResult(
                    success=False,
                    from_status=context.current_status,
                    error=f"Missing required permission: {transition.requires_permission}",
                )

        # Check reason requirement
        if transition.requires_reason and not context.reason:
            return TransitionResult(
                success=False,
                from_status=context.current_status,
                error="Reason is required for this transition",
            )

        return TransitionResult(
            success=True,
            from_status=context.current_status,
            to_status=transition.to_status,
            transition=transition,
        )

    def execute_transition(
        self,
        context: TransitionContext,
        user_permissions: Optional[list[str]] = None,
    ) -> TransitionResult:
        """
        Execute a state transition.

        Validates the transition and triggers callbacks.
        """
        # Validate first
        result = self.validate_transition(context, user_permissions)
        if not result.success:
            logger.warning(
                f"Transition failed for claim {context.claim_id}: {result.error}"
            )
            return result

        # Execute callbacks
        callbacks = self._callbacks.get(context.event, [])
        for callback in callbacks:
            try:
                callback(context, result)
            except Exception as e:
                logger.error(f"Transition callback error: {e}")

        logger.info(
            f"Claim {context.claim_id} transitioned: "
            f"{context.current_status.value} -> {result.to_status.value} "
            f"(event: {context.event.value})"
        )

        return result

    def register_callback(
        self,
        event: TransitionEvent,
        callback: Callable[[TransitionContext, TransitionResult], None],
    ) -> None:
        """Register a callback for a transition event."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def unregister_callback(
        self,
        event: TransitionEvent,
        callback: Callable,
    ) -> None:
        """Unregister a callback."""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)


# =============================================================================
# Status Helpers
# =============================================================================


def is_terminal_status(status: ClaimStatus) -> bool:
    """Check if status is terminal (no further transitions)."""
    return status == ClaimStatus.CLOSED


def is_processing_status(status: ClaimStatus) -> bool:
    """Check if claim is in active processing."""
    return status in (
        ClaimStatus.SUBMITTED,
        ClaimStatus.DOC_PROCESSING,
        ClaimStatus.VALIDATING,
        ClaimStatus.ADJUDICATING,
        ClaimStatus.PAYMENT_PROCESSING,
    )


def is_pending_status(status: ClaimStatus) -> bool:
    """Check if claim needs action."""
    return status in (
        ClaimStatus.NEEDS_REVIEW,
        ClaimStatus.DRAFT,
    )


def is_finalized_status(status: ClaimStatus) -> bool:
    """Check if claim is finalized."""
    return status in (
        ClaimStatus.APPROVED,
        ClaimStatus.DENIED,
        ClaimStatus.PAID,
        ClaimStatus.CLOSED,
    )


def get_status_display_name(status: ClaimStatus) -> str:
    """Get human-readable status name."""
    display_names = {
        ClaimStatus.DRAFT: "Draft",
        ClaimStatus.SUBMITTED: "Submitted",
        ClaimStatus.DOC_PROCESSING: "Processing Documents",
        ClaimStatus.VALIDATING: "Validating",
        ClaimStatus.ADJUDICATING: "Under Review",
        ClaimStatus.APPROVED: "Approved",
        ClaimStatus.DENIED: "Denied",
        ClaimStatus.NEEDS_REVIEW: "Needs Review",
        ClaimStatus.PAYMENT_PROCESSING: "Processing Payment",
        ClaimStatus.PAID: "Paid",
        ClaimStatus.CLOSED: "Closed",
    }
    return display_names.get(status, status.value)


def get_status_color(status: ClaimStatus) -> str:
    """Get status color for UI."""
    colors = {
        ClaimStatus.DRAFT: "gray",
        ClaimStatus.SUBMITTED: "blue",
        ClaimStatus.DOC_PROCESSING: "blue",
        ClaimStatus.VALIDATING: "blue",
        ClaimStatus.ADJUDICATING: "yellow",
        ClaimStatus.APPROVED: "green",
        ClaimStatus.DENIED: "red",
        ClaimStatus.NEEDS_REVIEW: "orange",
        ClaimStatus.PAYMENT_PROCESSING: "blue",
        ClaimStatus.PAID: "green",
        ClaimStatus.CLOSED: "gray",
    }
    return colors.get(status, "gray")


# =============================================================================
# Singleton Instance
# =============================================================================


_state_machine: Optional[ClaimStateMachine] = None


def get_claim_state_machine() -> ClaimStateMachine:
    """Get singleton state machine instance."""
    global _state_machine
    if _state_machine is None:
        _state_machine = ClaimStateMachine()
    return _state_machine
