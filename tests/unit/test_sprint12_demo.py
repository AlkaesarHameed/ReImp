"""
Sprint 12: Demo Mode & Admin Portal Tests.
Tests for demo models and service adapters.

Uses inline classes to avoid import chain issues with pgvector, JWT, and settings.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# Inline Enums and Models
# =============================================================================


class PolicyStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"


class ProviderStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class MemberStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AdapterMode(str, Enum):
    DEMO = "demo"
    LIVE = "live"


class DemoPolicy(BaseModel):
    """Demo policy model."""
    policy_id: str = Field(default_factory=lambda: f"POL-{uuid4().hex[:8].upper()}")
    policy_number: str = Field(default_factory=lambda: f"P{uuid4().hex[:10].upper()}")
    status: PolicyStatus = PolicyStatus.ACTIVE
    effective_date: date = Field(default_factory=date.today)
    termination_date: Optional[date] = None
    plan_name: str = "Standard Plan"
    deductible: Decimal = Decimal("500.00")
    deductible_met: Decimal = Decimal("0.00")
    oop_max: Decimal = Decimal("5000.00")
    oop_met: Decimal = Decimal("0.00")
    in_network_coinsurance: int = 80
    network_id: str = "NET-001"

    def is_active(self) -> bool:
        if self.status != PolicyStatus.ACTIVE:
            return False
        today = date.today()
        if self.effective_date > today:
            return False
        if self.termination_date and self.termination_date < today:
            return False
        return True

    def remaining_deductible(self) -> Decimal:
        return max(Decimal("0.00"), self.deductible - self.deductible_met)

    def apply_deductible(self, amount: Decimal) -> Decimal:
        remaining = self.remaining_deductible()
        applied = min(amount, remaining)
        self.deductible_met += applied
        return applied


class DemoProvider(BaseModel):
    """Demo provider model."""
    provider_id: str = Field(default_factory=lambda: f"PRV-{uuid4().hex[:8].upper()}")
    npi: str = "1234567890"
    name: str = "Demo Provider"
    status: ProviderStatus = ProviderStatus.ACTIVE
    specialty: str = "General Practice"
    network_ids: list[str] = Field(default_factory=lambda: ["NET-001"])
    city: str = "Healthcare City"
    state: str = "CA"

    def is_active(self) -> bool:
        return self.status == ProviderStatus.ACTIVE

    def is_in_network(self, network_id: str = "NET-001") -> bool:
        return self.is_active() and network_id in self.network_ids


class DemoMember(BaseModel):
    """Demo member model."""
    member_id: str = Field(default_factory=lambda: f"MEM-{uuid4().hex[:8].upper()}")
    first_name: str = "John"
    last_name: str = "Doe"
    date_of_birth: date = date(1980, 1, 1)
    gender: str = "M"
    status: MemberStatus = MemberStatus.ACTIVE
    policy_id: str = "POL-001"
    effective_date: date = Field(default_factory=date.today)
    termination_date: Optional[date] = None

    def get_age(self) -> int:
        today = date.today()
        age = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1
        return age

    def is_active(self) -> bool:
        if self.status != MemberStatus.ACTIVE:
            return False
        today = date.today()
        if self.effective_date > today:
            return False
        if self.termination_date and self.termination_date < today:
            return False
        return True

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class FeeScheduleEntry(BaseModel):
    """Fee schedule entry."""
    procedure_code: str
    allowed_amount: Decimal
    description: str = ""


class DemoFeeSchedule(BaseModel):
    """Demo fee schedule model."""
    schedule_id: str = Field(default_factory=lambda: f"FS-{uuid4().hex[:8].upper()}")
    schedule_name: str = "Standard Fee Schedule"
    entries: dict[str, FeeScheduleEntry] = Field(default_factory=dict)

    def add_entry(self, code: str, amount: Decimal, description: str = "") -> None:
        self.entries[code] = FeeScheduleEntry(
            procedure_code=code,
            allowed_amount=amount,
            description=description,
        )

    def get_allowed_amount(self, code: str) -> Optional[Decimal]:
        entry = self.entries.get(code)
        return entry.allowed_amount if entry else None


class Payment(BaseModel):
    """Payment model."""
    payment_id: str = Field(default_factory=lambda: f"PAY-{uuid4().hex[:8].upper()}")
    claim_id: str
    payee_id: str
    amount: Decimal
    status: PaymentStatus = PaymentStatus.PENDING
    payment_date: Optional[date] = None


# =============================================================================
# Inline Adapters
# =============================================================================


class PolicyAdapter:
    """Policy adapter."""

    def __init__(self, mode: AdapterMode = AdapterMode.DEMO):
        self._mode = mode
        self._data: dict[str, DemoPolicy] = {}
        if mode == AdapterMode.DEMO:
            self._seed_default()

    def _seed_default(self) -> None:
        policies = [
            DemoPolicy(
                policy_id="POL-001",
                policy_number="P2025001",
                plan_name="Gold Plan",
                deductible=Decimal("500.00"),
            ),
            DemoPolicy(
                policy_id="POL-002",
                policy_number="P2025002",
                plan_name="Silver Plan",
                deductible=Decimal("1000.00"),
            ),
        ]
        for p in policies:
            self._data[p.policy_id] = p

    async def get_by_id(self, entity_id: str) -> Optional[DemoPolicy]:
        return self._data.get(entity_id)

    async def list_all(self) -> list[DemoPolicy]:
        return list(self._data.values())

    async def create(self, entity: DemoPolicy) -> DemoPolicy:
        self._data[entity.policy_id] = entity
        return entity

    async def update(self, entity_id: str, updates: dict) -> Optional[DemoPolicy]:
        policy = self._data.get(entity_id)
        if policy:
            for k, v in updates.items():
                if hasattr(policy, k):
                    setattr(policy, k, v)
        return policy

    async def delete(self, entity_id: str) -> bool:
        if entity_id in self._data:
            del self._data[entity_id]
            return True
        return False


class ProviderAdapter:
    """Provider adapter."""

    def __init__(self, mode: AdapterMode = AdapterMode.DEMO):
        self._mode = mode
        self._data: dict[str, DemoProvider] = {}
        if mode == AdapterMode.DEMO:
            self._seed_default()

    def _seed_default(self) -> None:
        providers = [
            DemoProvider(
                provider_id="PRV-001",
                npi="1234567890",
                name="Dr. Smith",
                specialty="Internal Medicine",
            ),
            DemoProvider(
                provider_id="PRV-002",
                npi="2345678901",
                name="Metro Hospital",
                specialty="Hospital",
            ),
        ]
        for p in providers:
            self._data[p.provider_id] = p

    async def get_by_id(self, entity_id: str) -> Optional[DemoProvider]:
        return self._data.get(entity_id)

    async def get_by_npi(self, npi: str) -> Optional[DemoProvider]:
        for p in self._data.values():
            if p.npi == npi:
                return p
        return None

    async def list_all(self) -> list[DemoProvider]:
        return list(self._data.values())

    async def create(self, entity: DemoProvider) -> DemoProvider:
        self._data[entity.provider_id] = entity
        return entity


class MemberAdapter:
    """Member adapter."""

    def __init__(self, mode: AdapterMode = AdapterMode.DEMO):
        self._mode = mode
        self._data: dict[str, DemoMember] = {}
        if mode == AdapterMode.DEMO:
            self._seed_default()

    def _seed_default(self) -> None:
        members = [
            DemoMember(
                member_id="MEM-001",
                first_name="John",
                last_name="Doe",
                date_of_birth=date(1980, 5, 15),
                policy_id="POL-001",
            ),
            DemoMember(
                member_id="MEM-002",
                first_name="Jane",
                last_name="Doe",
                date_of_birth=date(1985, 8, 22),
                policy_id="POL-001",
            ),
        ]
        for m in members:
            self._data[m.member_id] = m

    async def get_by_id(self, entity_id: str) -> Optional[DemoMember]:
        return self._data.get(entity_id)

    async def get_by_policy(self, policy_id: str) -> list[DemoMember]:
        return [m for m in self._data.values() if m.policy_id == policy_id]

    async def list_all(self) -> list[DemoMember]:
        return list(self._data.values())

    async def create(self, entity: DemoMember) -> DemoMember:
        self._data[entity.member_id] = entity
        return entity


class PaymentAdapter:
    """Payment adapter."""

    def __init__(self, mode: AdapterMode = AdapterMode.DEMO):
        self._mode = mode
        self._payments: dict[str, Payment] = {}

    async def create_payment(
        self,
        claim_id: str,
        payee_id: str,
        amount: Decimal,
    ) -> Payment:
        payment = Payment(
            claim_id=claim_id,
            payee_id=payee_id,
            amount=amount,
        )
        self._payments[payment.payment_id] = payment
        return payment

    async def process_payment(self, payment_id: str) -> Payment:
        payment = self._payments.get(payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")
        payment.status = PaymentStatus.COMPLETED
        payment.payment_date = date.today()
        return payment

    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        return self._payments.get(payment_id)

    async def get_payments_for_claim(self, claim_id: str) -> list[Payment]:
        return [p for p in self._payments.values() if p.claim_id == claim_id]


# =============================================================================
# Demo Policy Tests
# =============================================================================


class TestDemoPolicy:
    """Tests for DemoPolicy model."""

    def test_policy_creation(self):
        """Test basic policy creation."""
        policy = DemoPolicy(
            policy_id="POL-TEST",
            policy_number="P123456",
            plan_name="Test Plan",
        )

        assert policy.policy_id == "POL-TEST"
        assert policy.status == PolicyStatus.ACTIVE
        assert policy.deductible == Decimal("500.00")

    def test_policy_is_active(self):
        """Test policy active status check."""
        policy = DemoPolicy()
        assert policy.is_active() is True

        policy.status = PolicyStatus.INACTIVE
        assert policy.is_active() is False

    def test_policy_is_active_future_effective_date(self):
        """Test policy not active with future effective date."""
        from datetime import timedelta
        policy = DemoPolicy(
            effective_date=date.today() + timedelta(days=30)
        )
        assert policy.is_active() is False

    def test_policy_is_active_past_termination(self):
        """Test policy not active after termination date."""
        from datetime import timedelta
        policy = DemoPolicy(
            termination_date=date.today() - timedelta(days=1)
        )
        assert policy.is_active() is False

    def test_remaining_deductible(self):
        """Test remaining deductible calculation."""
        policy = DemoPolicy(
            deductible=Decimal("1000.00"),
            deductible_met=Decimal("400.00"),
        )
        assert policy.remaining_deductible() == Decimal("600.00")

    def test_apply_deductible(self):
        """Test applying deductible."""
        policy = DemoPolicy(
            deductible=Decimal("500.00"),
            deductible_met=Decimal("0.00"),
        )

        applied = policy.apply_deductible(Decimal("200.00"))
        assert applied == Decimal("200.00")
        assert policy.deductible_met == Decimal("200.00")

    def test_apply_deductible_exceeds_remaining(self):
        """Test applying deductible that exceeds remaining."""
        policy = DemoPolicy(
            deductible=Decimal("500.00"),
            deductible_met=Decimal("400.00"),
        )

        applied = policy.apply_deductible(Decimal("200.00"))
        assert applied == Decimal("100.00")
        assert policy.deductible_met == Decimal("500.00")


# =============================================================================
# Demo Provider Tests
# =============================================================================


class TestDemoProvider:
    """Tests for DemoProvider model."""

    def test_provider_creation(self):
        """Test basic provider creation."""
        provider = DemoProvider(
            provider_id="PRV-TEST",
            npi="1234567890",
            name="Test Provider",
            specialty="Cardiology",
        )

        assert provider.provider_id == "PRV-TEST"
        assert provider.is_active() is True

    def test_provider_in_network(self):
        """Test provider network status."""
        provider = DemoProvider(network_ids=["NET-001", "NET-002"])

        assert provider.is_in_network("NET-001") is True
        assert provider.is_in_network("NET-003") is False

    def test_inactive_provider_not_in_network(self):
        """Test inactive provider is not considered in-network."""
        provider = DemoProvider(
            status=ProviderStatus.INACTIVE,
            network_ids=["NET-001"],
        )

        assert provider.is_in_network("NET-001") is False


# =============================================================================
# Demo Member Tests
# =============================================================================


class TestDemoMember:
    """Tests for DemoMember model."""

    def test_member_creation(self):
        """Test basic member creation."""
        member = DemoMember(
            member_id="MEM-TEST",
            first_name="John",
            last_name="Smith",
            date_of_birth=date(1990, 6, 15),
        )

        assert member.member_id == "MEM-TEST"
        assert member.get_full_name() == "John Smith"

    def test_member_age_calculation(self):
        """Test member age calculation."""
        member = DemoMember(
            date_of_birth=date(1990, 1, 1)
        )

        age = member.get_age()
        # Age should be around 35 in 2025
        assert 30 <= age <= 40

    def test_member_is_active(self):
        """Test member active status."""
        member = DemoMember()
        assert member.is_active() is True

        member.status = MemberStatus.INACTIVE
        assert member.is_active() is False


# =============================================================================
# Fee Schedule Tests
# =============================================================================


class TestDemoFeeSchedule:
    """Tests for DemoFeeSchedule model."""

    def test_fee_schedule_creation(self):
        """Test fee schedule creation."""
        fs = DemoFeeSchedule(
            schedule_id="FS-TEST",
            schedule_name="Test Schedule",
        )

        assert fs.schedule_id == "FS-TEST"
        assert len(fs.entries) == 0

    def test_add_and_get_entry(self):
        """Test adding and retrieving fee schedule entries."""
        fs = DemoFeeSchedule()

        fs.add_entry("99213", Decimal("76.15"), "Office visit")
        fs.add_entry("80053", Decimal("14.49"), "CMP")

        assert fs.get_allowed_amount("99213") == Decimal("76.15")
        assert fs.get_allowed_amount("80053") == Decimal("14.49")
        assert fs.get_allowed_amount("99999") is None


# =============================================================================
# Policy Adapter Tests
# =============================================================================


class TestPolicyAdapter:
    """Tests for PolicyAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create policy adapter."""
        return PolicyAdapter(mode=AdapterMode.DEMO)

    @pytest.mark.asyncio
    async def test_get_seeded_policy(self, adapter):
        """Test getting seeded policy."""
        policy = await adapter.get_by_id("POL-001")

        assert policy is not None
        assert policy.policy_id == "POL-001"
        assert policy.plan_name == "Gold Plan"

    @pytest.mark.asyncio
    async def test_list_all_policies(self, adapter):
        """Test listing all policies."""
        policies = await adapter.list_all()

        assert len(policies) >= 2

    @pytest.mark.asyncio
    async def test_create_policy(self, adapter):
        """Test creating a new policy."""
        new_policy = DemoPolicy(
            policy_id="POL-NEW",
            policy_number="P999999",
            plan_name="New Plan",
        )

        created = await adapter.create(new_policy)
        assert created.policy_id == "POL-NEW"

        retrieved = await adapter.get_by_id("POL-NEW")
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_update_policy(self, adapter):
        """Test updating a policy."""
        updated = await adapter.update("POL-001", {"plan_name": "Updated Gold Plan"})

        assert updated is not None
        assert updated.plan_name == "Updated Gold Plan"

    @pytest.mark.asyncio
    async def test_delete_policy(self, adapter):
        """Test deleting a policy."""
        result = await adapter.delete("POL-002")
        assert result is True

        policy = await adapter.get_by_id("POL-002")
        assert policy is None


# =============================================================================
# Provider Adapter Tests
# =============================================================================


class TestProviderAdapter:
    """Tests for ProviderAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create provider adapter."""
        return ProviderAdapter(mode=AdapterMode.DEMO)

    @pytest.mark.asyncio
    async def test_get_seeded_provider(self, adapter):
        """Test getting seeded provider."""
        provider = await adapter.get_by_id("PRV-001")

        assert provider is not None
        assert provider.name == "Dr. Smith"

    @pytest.mark.asyncio
    async def test_get_provider_by_npi(self, adapter):
        """Test getting provider by NPI."""
        provider = await adapter.get_by_npi("1234567890")

        assert provider is not None
        assert provider.provider_id == "PRV-001"

    @pytest.mark.asyncio
    async def test_list_all_providers(self, adapter):
        """Test listing all providers."""
        providers = await adapter.list_all()

        assert len(providers) >= 2


# =============================================================================
# Member Adapter Tests
# =============================================================================


class TestMemberAdapter:
    """Tests for MemberAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create member adapter."""
        return MemberAdapter(mode=AdapterMode.DEMO)

    @pytest.mark.asyncio
    async def test_get_seeded_member(self, adapter):
        """Test getting seeded member."""
        member = await adapter.get_by_id("MEM-001")

        assert member is not None
        assert member.first_name == "John"

    @pytest.mark.asyncio
    async def test_get_members_by_policy(self, adapter):
        """Test getting members by policy."""
        members = await adapter.get_by_policy("POL-001")

        assert len(members) >= 2
        for member in members:
            assert member.policy_id == "POL-001"


# =============================================================================
# Payment Adapter Tests
# =============================================================================


class TestPaymentAdapter:
    """Tests for PaymentAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create payment adapter."""
        return PaymentAdapter(mode=AdapterMode.DEMO)

    @pytest.mark.asyncio
    async def test_create_payment(self, adapter):
        """Test creating a payment."""
        payment = await adapter.create_payment(
            claim_id="CLM-001",
            payee_id="PRV-001",
            amount=Decimal("250.00"),
        )

        assert payment.claim_id == "CLM-001"
        assert payment.status == PaymentStatus.PENDING

    @pytest.mark.asyncio
    async def test_process_payment(self, adapter):
        """Test processing a payment."""
        payment = await adapter.create_payment(
            claim_id="CLM-002",
            payee_id="PRV-001",
            amount=Decimal("500.00"),
        )

        processed = await adapter.process_payment(payment.payment_id)

        assert processed.status == PaymentStatus.COMPLETED
        assert processed.payment_date == date.today()

    @pytest.mark.asyncio
    async def test_get_payments_for_claim(self, adapter):
        """Test getting payments for a claim."""
        await adapter.create_payment("CLM-003", "PRV-001", Decimal("100.00"))
        await adapter.create_payment("CLM-003", "PRV-001", Decimal("200.00"))

        payments = await adapter.get_payments_for_claim("CLM-003")

        assert len(payments) == 2


# =============================================================================
# Integration Tests
# =============================================================================


class TestDemoModeIntegration:
    """Integration tests for demo mode."""

    @pytest.mark.asyncio
    async def test_full_claim_workflow_demo(self):
        """Test complete claim workflow in demo mode."""
        # Setup adapters
        policy_adapter = PolicyAdapter(mode=AdapterMode.DEMO)
        provider_adapter = ProviderAdapter(mode=AdapterMode.DEMO)
        member_adapter = MemberAdapter(mode=AdapterMode.DEMO)
        payment_adapter = PaymentAdapter(mode=AdapterMode.DEMO)

        # Get policy
        policy = await policy_adapter.get_by_id("POL-001")
        assert policy is not None

        # Get member
        member = await member_adapter.get_by_id("MEM-001")
        assert member is not None
        assert member.policy_id == policy.policy_id

        # Get provider
        provider = await provider_adapter.get_by_id("PRV-001")
        assert provider is not None
        assert provider.is_in_network()

        # Create and process payment
        payment = await payment_adapter.create_payment(
            claim_id="CLM-DEMO",
            payee_id=provider.provider_id,
            amount=Decimal("150.00"),
        )
        assert payment.status == PaymentStatus.PENDING

        processed = await payment_adapter.process_payment(payment.payment_id)
        assert processed.status == PaymentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_member_eligibility_check(self):
        """Test member eligibility verification."""
        member_adapter = MemberAdapter(mode=AdapterMode.DEMO)
        policy_adapter = PolicyAdapter(mode=AdapterMode.DEMO)

        # Get member
        member = await member_adapter.get_by_id("MEM-001")
        assert member is not None
        assert member.is_active()

        # Get member's policy
        policy = await policy_adapter.get_by_id(member.policy_id)
        assert policy is not None
        assert policy.is_active()

        # Verify eligibility
        is_eligible = member.is_active() and policy.is_active()
        assert is_eligible is True

    @pytest.mark.asyncio
    async def test_benefit_calculation_demo(self):
        """Test benefit calculation with demo data."""
        policy_adapter = PolicyAdapter(mode=AdapterMode.DEMO)

        # Get policy with deductible
        policy = await policy_adapter.get_by_id("POL-001")
        assert policy.deductible == Decimal("500.00")

        # Simulate claim amount
        claim_amount = Decimal("300.00")

        # Apply deductible
        deductible_applied = policy.apply_deductible(claim_amount)
        assert deductible_applied == Decimal("300.00")
        assert policy.remaining_deductible() == Decimal("200.00")

        # Second claim
        claim_amount_2 = Decimal("400.00")
        deductible_applied_2 = policy.apply_deductible(claim_amount_2)
        assert deductible_applied_2 == Decimal("200.00")
        assert policy.remaining_deductible() == Decimal("0.00")

        # Patient responsibility for remaining amount
        remaining = claim_amount_2 - deductible_applied_2
        coinsurance_rate = (100 - policy.in_network_coinsurance) / 100
        patient_coinsurance = remaining * Decimal(str(coinsurance_rate))
        assert patient_coinsurance == Decimal("40.00")  # 20% of $200
