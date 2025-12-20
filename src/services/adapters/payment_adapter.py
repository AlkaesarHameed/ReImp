"""
Payment Service Adapter.
Source: Design Document Section 4.4 - Demo Mode
Verified: 2025-12-18

Provides payment simulation for demo mode.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field

from src.services.adapters.base import AdapterMode


class PaymentStatus(str, Enum):
    """Payment status values."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    """Payment method values."""

    ACH = "ach"
    CHECK = "check"
    WIRE = "wire"
    VIRTUAL_CARD = "virtual_card"


class Payment(BaseModel):
    """Payment record."""

    payment_id: str = Field(default_factory=lambda: f"PAY-{uuid4().hex[:8].upper()}")
    claim_id: str
    payee_id: str  # Provider or member ID
    payee_type: str = "provider"  # provider or member

    amount: Decimal
    currency: str = "USD"

    payment_method: PaymentMethod = PaymentMethod.ACH
    status: PaymentStatus = PaymentStatus.PENDING

    # Bank/payment details
    bank_account_last4: Optional[str] = None
    check_number: Optional[str] = None
    trace_number: Optional[str] = None

    # Dates
    payment_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Remittance info
    remittance_id: Optional[str] = None
    remittance_data: dict = Field(default_factory=dict)

    # Metadata
    notes: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class PaymentAdapter:
    """Adapter for payment processing."""

    def __init__(self, mode: AdapterMode = AdapterMode.DEMO):
        """Initialize PaymentAdapter."""
        self._mode = mode
        self._payments: dict[str, Payment] = {}
        self._payment_history: list[dict] = []

    @property
    def mode(self) -> AdapterMode:
        """Get current operating mode."""
        return self._mode

    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self._mode == AdapterMode.DEMO

    async def create_payment(
        self,
        claim_id: str,
        payee_id: str,
        amount: Decimal,
        payee_type: str = "provider",
        payment_method: PaymentMethod = PaymentMethod.ACH,
    ) -> Payment:
        """Create a new payment."""
        payment = Payment(
            claim_id=claim_id,
            payee_id=payee_id,
            payee_type=payee_type,
            amount=amount,
            payment_method=payment_method,
            status=PaymentStatus.PENDING,
        )

        self._payments[payment.payment_id] = payment
        self._log_payment_event(payment, "created")

        return payment

    async def process_payment(self, payment_id: str) -> Payment:
        """Process a pending payment (simulation)."""
        payment = self._payments.get(payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        if payment.status != PaymentStatus.PENDING:
            raise ValueError(f"Payment is not pending: {payment.status}")

        # Simulate processing
        payment.status = PaymentStatus.PROCESSING
        payment.updated_at = datetime.utcnow()
        self._log_payment_event(payment, "processing")

        # Simulate completion
        payment.status = PaymentStatus.COMPLETED
        payment.payment_date = date.today()
        payment.trace_number = f"TRACE-{uuid4().hex[:12].upper()}"
        payment.updated_at = datetime.utcnow()
        self._log_payment_event(payment, "completed")

        return payment

    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        return self._payments.get(payment_id)

    async def get_payments_for_claim(self, claim_id: str) -> list[Payment]:
        """Get all payments for a claim."""
        return [p for p in self._payments.values() if p.claim_id == claim_id]

    async def get_payments_for_payee(self, payee_id: str) -> list[Payment]:
        """Get all payments for a payee."""
        return [p for p in self._payments.values() if p.payee_id == payee_id]

    async def cancel_payment(self, payment_id: str, reason: str = "") -> Payment:
        """Cancel a pending payment."""
        payment = self._payments.get(payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        if payment.status not in [PaymentStatus.PENDING, PaymentStatus.PROCESSING]:
            raise ValueError(f"Cannot cancel payment in status: {payment.status}")

        payment.status = PaymentStatus.CANCELLED
        payment.notes = reason
        payment.updated_at = datetime.utcnow()
        self._log_payment_event(payment, "cancelled")

        return payment

    async def generate_remittance(
        self,
        payment_ids: list[str],
    ) -> dict[str, Any]:
        """Generate remittance advice for payments."""
        payments = [self._payments.get(pid) for pid in payment_ids if pid in self._payments]
        completed = [p for p in payments if p and p.status == PaymentStatus.COMPLETED]

        if not completed:
            return {"error": "No completed payments found"}

        remittance_id = f"REM-{uuid4().hex[:8].upper()}"
        total_amount = sum(p.amount for p in completed)

        remittance = {
            "remittance_id": remittance_id,
            "generated_at": datetime.utcnow().isoformat(),
            "payment_count": len(completed),
            "total_amount": float(total_amount),
            "payments": [
                {
                    "payment_id": p.payment_id,
                    "claim_id": p.claim_id,
                    "amount": float(p.amount),
                    "payment_date": p.payment_date.isoformat() if p.payment_date else None,
                }
                for p in completed
            ],
        }

        # Update payments with remittance ID
        for payment in completed:
            payment.remittance_id = remittance_id
            payment.remittance_data = remittance

        return remittance

    def _log_payment_event(self, payment: Payment, event: str) -> None:
        """Log payment event for audit."""
        self._payment_history.append({
            "payment_id": payment.payment_id,
            "event": event,
            "status": payment.status.value,
            "amount": float(payment.amount),
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_payment_history(self, payment_id: Optional[str] = None) -> list[dict]:
        """Get payment history."""
        if payment_id:
            return [e for e in self._payment_history if e["payment_id"] == payment_id]
        return self._payment_history.copy()

    def clear_all(self) -> None:
        """Clear all payment data."""
        self._payments.clear()
        self._payment_history.clear()


# =============================================================================
# Factory Functions
# =============================================================================


_payment_adapter: Optional[PaymentAdapter] = None


def get_payment_adapter(mode: AdapterMode = AdapterMode.DEMO) -> PaymentAdapter:
    """Get singleton PaymentAdapter instance."""
    global _payment_adapter
    if _payment_adapter is None:
        _payment_adapter = PaymentAdapter(mode)
    return _payment_adapter


def create_payment_adapter(mode: AdapterMode = AdapterMode.DEMO) -> PaymentAdapter:
    """Create a new PaymentAdapter instance."""
    return PaymentAdapter(mode)
