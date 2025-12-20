"""
Provider Service Adapter.
Source: Design Document Section 4.4 - Demo Mode
Verified: 2025-12-18

Provides unified interface for provider data access in demo/live modes.
"""

from datetime import datetime
from typing import Optional, Any

from src.models.demo.provider import DemoProvider, ProviderStatus, ProviderType, NetworkStatus
from src.services.adapters.base import BaseAdapter, AdapterMode


class ProviderAdapter(BaseAdapter[DemoProvider]):
    """Adapter for provider data access."""

    def __init__(self, mode: AdapterMode = AdapterMode.DEMO):
        """Initialize ProviderAdapter."""
        super().__init__(mode)
        if mode == AdapterMode.DEMO:
            self._seed_default_providers()

    def _seed_default_providers(self) -> None:
        """Seed default demo providers."""
        providers = [
            DemoProvider(
                provider_id="PRV-001",
                npi="1234567890",
                name="Dr. Jane Smith",
                first_name="Jane",
                last_name="Smith",
                provider_type=ProviderType.PHYSICIAN,
                specialty="Internal Medicine",
                specialty_code="207R00000X",
                city="Los Angeles",
                state="CA",
            ),
            DemoProvider(
                provider_id="PRV-002",
                npi="2345678901",
                name="Metro General Hospital",
                organization_name="Metro General Hospital",
                provider_type=ProviderType.HOSPITAL,
                specialty="General Acute Care Hospital",
                specialty_code="282N00000X",
                city="New York",
                state="NY",
            ),
            DemoProvider(
                provider_id="PRV-003",
                npi="3456789012",
                name="Dr. Robert Johnson",
                first_name="Robert",
                last_name="Johnson",
                provider_type=ProviderType.PHYSICIAN,
                specialty="Cardiology",
                specialty_code="207RC0000X",
                city="Chicago",
                state="IL",
            ),
            DemoProvider(
                provider_id="PRV-OON",
                npi="9999999999",
                name="Out of Network Clinic",
                organization_name="Out of Network Clinic",
                provider_type=ProviderType.CLINIC,
                network_status=NetworkStatus.OUT_OF_NETWORK,
                network_ids=[],
            ),
        ]

        for provider in providers:
            self._demo_data[provider.provider_id] = provider

    async def get_by_id(self, entity_id: str) -> Optional[DemoProvider]:
        """Get provider by ID."""
        if self.is_demo_mode():
            return self._demo_data.get(entity_id)
        raise NotImplementedError("Live mode not yet implemented")

    async def get_by_npi(self, npi: str) -> Optional[DemoProvider]:
        """Get provider by NPI."""
        if self.is_demo_mode():
            for provider in self._demo_data.values():
                if provider.npi == npi:
                    return provider
            return None
        raise NotImplementedError("Live mode not yet implemented")

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[DemoProvider]:
        """List all providers with pagination and filtering."""
        if self.is_demo_mode():
            providers = list(self._demo_data.values())

            if filters:
                if "status" in filters:
                    providers = [p for p in providers if p.status == filters["status"]]
                if "provider_type" in filters:
                    providers = [p for p in providers if p.provider_type == filters["provider_type"]]
                if "specialty" in filters:
                    providers = [p for p in providers if filters["specialty"].lower() in p.specialty.lower()]
                if "in_network" in filters and filters["in_network"]:
                    providers = [p for p in providers if p.is_in_network()]

            return providers[offset:offset + limit]

        raise NotImplementedError("Live mode not yet implemented")

    async def create(self, entity: DemoProvider) -> DemoProvider:
        """Create a new provider."""
        if self.is_demo_mode():
            entity.created_at = datetime.utcnow()
            entity.updated_at = datetime.utcnow()
            self._demo_data[entity.provider_id] = entity
            return entity
        raise NotImplementedError("Live mode not yet implemented")

    async def update(self, entity_id: str, updates: dict[str, Any]) -> Optional[DemoProvider]:
        """Update an existing provider."""
        if self.is_demo_mode():
            provider = self._demo_data.get(entity_id)
            if not provider:
                return None
            for key, value in updates.items():
                if hasattr(provider, key):
                    setattr(provider, key, value)
            provider.updated_at = datetime.utcnow()
            return provider
        raise NotImplementedError("Live mode not yet implemented")

    async def delete(self, entity_id: str) -> bool:
        """Delete a provider."""
        if self.is_demo_mode():
            if entity_id in self._demo_data:
                del self._demo_data[entity_id]
                return True
            return False
        raise NotImplementedError("Live mode not yet implemented")

    async def search_providers(
        self,
        specialty: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        in_network_only: bool = True,
    ) -> list[DemoProvider]:
        """Search for providers by criteria."""
        filters = {}
        if specialty:
            filters["specialty"] = specialty
        if in_network_only:
            filters["in_network"] = True

        providers = await self.list_all(filters=filters)

        if city:
            providers = [p for p in providers if p.city.lower() == city.lower()]
        if state:
            providers = [p for p in providers if p.state.upper() == state.upper()]

        return providers


# =============================================================================
# Factory Functions
# =============================================================================


_provider_adapter: Optional[ProviderAdapter] = None


def get_provider_adapter(mode: AdapterMode = AdapterMode.DEMO) -> ProviderAdapter:
    """Get singleton ProviderAdapter instance."""
    global _provider_adapter
    if _provider_adapter is None:
        _provider_adapter = ProviderAdapter(mode)
    return _provider_adapter


def create_provider_adapter(mode: AdapterMode = AdapterMode.DEMO) -> ProviderAdapter:
    """Create a new ProviderAdapter instance."""
    return ProviderAdapter(mode)
