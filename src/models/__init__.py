"""
SQLAlchemy Models for Claims Processing System.

This module exports all database models for the application.
"""

from src.models.base import Base, TimeStampedModel, UUIDModel
from src.models.user import User
from src.models.document import Document

# Claims Processing Models
from src.models.tenant import Tenant, TenantSettings
from src.models.policy import Policy, CoverageLimit
from src.models.member import Member
from src.models.healthcare_provider import HealthcareProvider
from src.models.claim import (
    Claim,
    ClaimLineItem,
    ClaimDocument,
    ClaimStatusHistory,
)
from src.models.audit import (
    AuditLog,
    PHIAccessLog,
    ProviderUsageLog,
)
from src.models.permission import (
    Permission,
    Role,
    RolePermission,
    UserRole,
    SYSTEM_PERMISSIONS,
    SYSTEM_ROLES,
)

# Validation Engine Models
# Source: Design Document 04_validation_engine_comprehensive_design.md
from src.models.llm_settings import (
    LLMSettings,
    LLMUsageLog,
)
from src.models.validation_result import (
    ValidationResult,
    ClaimRejection,
    RejectionEvidence,
)

# EDI Models
# Source: Design Document 06_high_value_enhancements_design.md
from src.models.edi_transaction import (
    EDITransaction,
    EDITransactionClaim,
    EDITransactionError,
    EDIRemittance,
    EDIControlNumber,
    EDITradingPartner,
    EDITransactionType,
    EDITransactionStatus,
    EDIDirection,
)

__all__ = [
    # Base classes
    "Base",
    "TimeStampedModel",
    "UUIDModel",
    # User models
    "User",
    "Document",
    # Tenant models
    "Tenant",
    "TenantSettings",
    # Policy models
    "Policy",
    "CoverageLimit",
    # Member models
    "Member",
    # Provider models
    "HealthcareProvider",
    # Claim models
    "Claim",
    "ClaimLineItem",
    "ClaimDocument",
    "ClaimStatusHistory",
    # Audit models
    "AuditLog",
    "PHIAccessLog",
    "ProviderUsageLog",
    # RBAC models
    "Permission",
    "Role",
    "RolePermission",
    "UserRole",
    "SYSTEM_PERMISSIONS",
    "SYSTEM_ROLES",
    # Validation Engine models
    "LLMSettings",
    "LLMUsageLog",
    "ValidationResult",
    "ClaimRejection",
    "RejectionEvidence",
    # EDI models
    "EDITransaction",
    "EDITransactionClaim",
    "EDITransactionError",
    "EDIRemittance",
    "EDIControlNumber",
    "EDITradingPartner",
    "EDITransactionType",
    "EDITransactionStatus",
    "EDIDirection",
]
