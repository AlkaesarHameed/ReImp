"""
Base Service Adapter.
Source: Design Document Section 4.4 - Demo Mode
Verified: 2025-12-18

Abstract base class for service adapters supporting demo/live modes.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Generic, TypeVar, Optional, Any

from pydantic import BaseModel


class AdapterMode(str, Enum):
    """Adapter operating mode."""

    DEMO = "demo"
    LIVE = "live"


T = TypeVar("T", bound=BaseModel)


class BaseAdapter(ABC, Generic[T]):
    """
    Abstract base class for service adapters.

    Provides a common interface for accessing data from either
    demo (in-memory) or live (database/external API) sources.
    """

    def __init__(self, mode: AdapterMode = AdapterMode.DEMO):
        """
        Initialize adapter.

        Args:
            mode: Operating mode (demo or live)
        """
        self._mode = mode
        self._demo_data: dict[str, T] = {}

    @property
    def mode(self) -> AdapterMode:
        """Get current operating mode."""
        return self._mode

    def set_mode(self, mode: AdapterMode) -> None:
        """Set operating mode."""
        self._mode = mode

    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self._mode == AdapterMode.DEMO

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def list_all(
        self,
        offset: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[T]:
        """List all entities with pagination and filtering."""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity."""
        pass

    @abstractmethod
    async def update(self, entity_id: str, updates: dict[str, Any]) -> Optional[T]:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        pass

    def clear_demo_data(self) -> None:
        """Clear all demo data."""
        self._demo_data.clear()

    def seed_demo_data(self, entities: list[T], id_field: str = "id") -> None:
        """
        Seed demo data.

        Args:
            entities: List of entities to seed
            id_field: Field name to use as key
        """
        for entity in entities:
            entity_id = getattr(entity, id_field, None)
            if entity_id:
                self._demo_data[entity_id] = entity

    def get_demo_count(self) -> int:
        """Get count of demo data entries."""
        return len(self._demo_data)
