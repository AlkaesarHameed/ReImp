"""
Policy Service Adapter.
Source: Design Document Section 4.4 - Demo Mode
Verified: 2025-12-18

Provides unified interface for policy data access in demo/live modes.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Any

from src.models.demo.policy import DemoPolicy, PolicyStatus
from src.services.adapters.base import BaseAdapter, AdapterMode


class PolicyAdapter(BaseAdapter[DemoPolicy]):
    """
    Adapter for policy data access.

    Supports both demo (in-memory) and live (database) modes.
    """

    def __init__(self, mode: AdapterMode = AdapterMode.DEMO):
        """Initialize PolicyAdapter."""
        super().__init__(mode)
        if mode == AdapterMode.DEMO:
            self._seed_default_policies()

    def _seed_default_policies(self) -> None:
        """Seed default demo policies."""
        policies = [
            DemoPolicy(
                policy_id="POL-001",
                policy_number="P2025001",
                group_id="GRP-ABC",
                group_name="ABC Corporation",
                plan_name="Gold Health Plan",
                plan_code="GOLD-001",
                deductible=Decimal("500.00"),
                oop_max=Decimal("5000.00"),
                in_network_coinsurance=80,
                pcp_copay=Decimal("20.00"),
                specialist_copay=Decimal("40.00"),
            ),
            DemoPolicy(
                policy_id="POL-002",
                policy_number="P2025002",
                group_id="GRP-XYZ",
                group_name="XYZ Industries",
                plan_name="Silver Health Plan",
                plan_code="SILVER-001",
                deductible=Decimal("1000.00"),
                oop_max=Decimal("7500.00"),
                in_network_coinsurance=70,
                pcp_copay=Decimal("30.00"),
                specialist_copay=Decimal("50.00"),
            ),
            DemoPolicy(
                policy_id="POL-003",
                policy_number="P2025003",
                plan_name="Bronze Health Plan",
                plan_code="BRONZE-001",
                deductible=Decimal("2500.00"),
                oop_max=Decimal("10000.00"),
                in_network_coinsurance=60,
                pcp_copay=Decimal("40.00"),
                specialist_copay=Decimal("60.00"),
            ),
        ]

        for policy in policies:
            self._demo_data[policy.policy_id] = policy

    async def get_by_id(self, entity_id: str) -> Optional[DemoPolicy]:
        """Get policy by ID."""
        if self.is_demo_mode():
            return self._demo_data.get(entity_id)
        # In live mode, query database
        # return await self._db_get_policy(entity_id)
        raise NotImplementedError("Live mode not yet implemented")

    async def get_by_policy_number(self, policy_number: str) -> Optional[DemoPolicy]:
        """Get policy by policy number."""
        if self.is_demo_mode():
            for policy in self._demo_data.values():
                if policy.policy_number == policy_number:
                    return policy
            return None
        raise NotImplementedError("Live mode not yet implemented")

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[DemoPolicy]:
        """List all policies with pagination and filtering."""
        if self.is_demo_mode():
            policies = list(self._demo_data.values())

            # Apply filters
            if filters:
                if "status" in filters:
                    policies = [p for p in policies if p.status == filters["status"]]
                if "group_id" in filters:
                    policies = [p for p in policies if p.group_id == filters["group_id"]]
                if "active_only" in filters and filters["active_only"]:
                    policies = [p for p in policies if p.is_active()]

            # Apply pagination
            return policies[offset:offset + limit]

        raise NotImplementedError("Live mode not yet implemented")

    async def create(self, entity: DemoPolicy) -> DemoPolicy:
        """Create a new policy."""
        if self.is_demo_mode():
            entity.created_at = datetime.utcnow()
            entity.updated_at = datetime.utcnow()
            self._demo_data[entity.policy_id] = entity
            return entity

        raise NotImplementedError("Live mode not yet implemented")

    async def update(self, entity_id: str, updates: dict[str, Any]) -> Optional[DemoPolicy]:
        """Update an existing policy."""
        if self.is_demo_mode():
            policy = self._demo_data.get(entity_id)
            if not policy:
                return None

            for key, value in updates.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)

            policy.updated_at = datetime.utcnow()
            return policy

        raise NotImplementedError("Live mode not yet implemented")

    async def delete(self, entity_id: str) -> bool:
        """Delete a policy."""
        if self.is_demo_mode():
            if entity_id in self._demo_data:
                del self._demo_data[entity_id]
                return True
            return False

        raise NotImplementedError("Live mode not yet implemented")

    async def get_active_policies(self, group_id: Optional[str] = None) -> list[DemoPolicy]:
        """Get all active policies, optionally filtered by group."""
        return await self.list_all(
            filters={"active_only": True, "group_id": group_id} if group_id else {"active_only": True}
        )

    async def check_eligibility(
        self,
        policy_id: str,
        service_date: date,
    ) -> dict[str, Any]:
        """Check member eligibility for a policy."""
        policy = await self.get_by_id(policy_id)

        if not policy:
            return {
                "is_eligible": False,
                "reason": "Policy not found",
            }

        if not policy.is_active_on_date(service_date):
            return {
                "is_eligible": False,
                "reason": "Policy not active on service date",
            }

        return {
            "is_eligible": True,
            "policy_id": policy.policy_id,
            "plan_name": policy.plan_name,
            "deductible_remaining": float(policy.remaining_deductible()),
            "oop_remaining": float(policy.remaining_oop()),
            "network_id": policy.network_id,
        }


# =============================================================================
# Factory Functions
# =============================================================================


_policy_adapter: Optional[PolicyAdapter] = None


def get_policy_adapter(mode: AdapterMode = AdapterMode.DEMO) -> PolicyAdapter:
    """Get singleton PolicyAdapter instance."""
    global _policy_adapter
    if _policy_adapter is None:
        _policy_adapter = PolicyAdapter(mode)
    return _policy_adapter


def create_policy_adapter(mode: AdapterMode = AdapterMode.DEMO) -> PolicyAdapter:
    """Create a new PolicyAdapter instance."""
    return PolicyAdapter(mode)
