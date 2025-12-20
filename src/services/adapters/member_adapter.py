"""
Member Service Adapter.
Source: Design Document Section 4.4 - Demo Mode
Verified: 2025-12-18

Provides unified interface for member data access in demo/live modes.
"""

from datetime import date, datetime
from typing import Optional, Any

from src.models.demo.member import DemoMember, MemberStatus, Gender
from src.services.adapters.base import BaseAdapter, AdapterMode


class MemberAdapter(BaseAdapter[DemoMember]):
    """Adapter for member data access."""

    def __init__(self, mode: AdapterMode = AdapterMode.DEMO):
        """Initialize MemberAdapter."""
        super().__init__(mode)
        if mode == AdapterMode.DEMO:
            self._seed_default_members()

    def _seed_default_members(self) -> None:
        """Seed default demo members."""
        members = [
            DemoMember(
                member_id="MEM-001",
                first_name="John",
                last_name="Doe",
                date_of_birth=date(1980, 5, 15),
                gender=Gender.MALE,
                policy_id="POL-001",
                pcp_provider_id="PRV-001",
                pcp_name="Dr. Jane Smith",
            ),
            DemoMember(
                member_id="MEM-002",
                first_name="Jane",
                last_name="Doe",
                date_of_birth=date(1982, 8, 22),
                gender=Gender.FEMALE,
                policy_id="POL-001",
                subscriber_id="MEM-001",
            ),
            DemoMember(
                member_id="MEM-003",
                first_name="Robert",
                last_name="Smith",
                date_of_birth=date(1975, 3, 10),
                gender=Gender.MALE,
                policy_id="POL-002",
            ),
            DemoMember(
                member_id="MEM-004",
                first_name="Emily",
                last_name="Johnson",
                date_of_birth=date(1990, 11, 30),
                gender=Gender.FEMALE,
                policy_id="POL-003",
            ),
        ]

        for member in members:
            self._demo_data[member.member_id] = member

    async def get_by_id(self, entity_id: str) -> Optional[DemoMember]:
        """Get member by ID."""
        if self.is_demo_mode():
            return self._demo_data.get(entity_id)
        raise NotImplementedError("Live mode not yet implemented")

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[DemoMember]:
        """List all members with pagination and filtering."""
        if self.is_demo_mode():
            members = list(self._demo_data.values())

            if filters:
                if "status" in filters:
                    members = [m for m in members if m.status == filters["status"]]
                if "policy_id" in filters:
                    members = [m for m in members if m.policy_id == filters["policy_id"]]
                if "active_only" in filters and filters["active_only"]:
                    members = [m for m in members if m.is_active()]

            return members[offset:offset + limit]

        raise NotImplementedError("Live mode not yet implemented")

    async def create(self, entity: DemoMember) -> DemoMember:
        """Create a new member."""
        if self.is_demo_mode():
            entity.created_at = datetime.utcnow()
            entity.updated_at = datetime.utcnow()
            self._demo_data[entity.member_id] = entity
            return entity
        raise NotImplementedError("Live mode not yet implemented")

    async def update(self, entity_id: str, updates: dict[str, Any]) -> Optional[DemoMember]:
        """Update an existing member."""
        if self.is_demo_mode():
            member = self._demo_data.get(entity_id)
            if not member:
                return None
            for key, value in updates.items():
                if hasattr(member, key):
                    setattr(member, key, value)
            member.updated_at = datetime.utcnow()
            return member
        raise NotImplementedError("Live mode not yet implemented")

    async def delete(self, entity_id: str) -> bool:
        """Delete a member."""
        if self.is_demo_mode():
            if entity_id in self._demo_data:
                del self._demo_data[entity_id]
                return True
            return False
        raise NotImplementedError("Live mode not yet implemented")

    async def get_by_policy(self, policy_id: str) -> list[DemoMember]:
        """Get all members for a policy."""
        return await self.list_all(filters={"policy_id": policy_id})

    async def check_eligibility(
        self,
        member_id: str,
        service_date: date,
    ) -> dict[str, Any]:
        """Check member eligibility."""
        member = await self.get_by_id(member_id)

        if not member:
            return {
                "is_eligible": False,
                "reason": "Member not found",
            }

        if not member.is_active_on_date(service_date):
            return {
                "is_eligible": False,
                "reason": "Member not active on service date",
            }

        return {
            "is_eligible": True,
            "member_id": member.member_id,
            "member_name": member.get_full_name(),
            "policy_id": member.policy_id,
            "age": member.get_age(),
            "gender": member.gender.value,
        }


# =============================================================================
# Factory Functions
# =============================================================================


_member_adapter: Optional[MemberAdapter] = None


def get_member_adapter(mode: AdapterMode = AdapterMode.DEMO) -> MemberAdapter:
    """Get singleton MemberAdapter instance."""
    global _member_adapter
    if _member_adapter is None:
        _member_adapter = MemberAdapter(mode)
    return _member_adapter


def create_member_adapter(mode: AdapterMode = AdapterMode.DEMO) -> MemberAdapter:
    """Create a new MemberAdapter instance."""
    return MemberAdapter(mode)
