"""
Service Adapters for Demo/Live Mode.
Source: Design Document Section 4.4 - Demo Mode
Verified: 2025-12-18

Provides abstraction layer for switching between demo and live data sources.
"""

from src.services.adapters.base import BaseAdapter, AdapterMode
from src.services.adapters.policy_adapter import PolicyAdapter, get_policy_adapter
from src.services.adapters.provider_adapter import ProviderAdapter, get_provider_adapter
from src.services.adapters.member_adapter import MemberAdapter, get_member_adapter
from src.services.adapters.payment_adapter import PaymentAdapter, get_payment_adapter


__all__ = [
    # Base
    "BaseAdapter",
    "AdapterMode",
    # Adapters
    "PolicyAdapter",
    "get_policy_adapter",
    "ProviderAdapter",
    "get_provider_adapter",
    "MemberAdapter",
    "get_member_adapter",
    "PaymentAdapter",
    "get_payment_adapter",
]
