"""
PHI Protection Service.
Source: Design Document Section 5.2 - Security Hardening
Verified: 2025-12-18

Provides Protected Health Information (PHI) handling per HIPAA requirements.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SensitivityLevel(str, Enum):
    """Data sensitivity levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PHI = "phi"  # Protected Health Information
    PII = "pii"  # Personally Identifiable Information


class PHICategory(str, Enum):
    """HIPAA PHI categories (18 identifiers)."""

    NAME = "name"
    ADDRESS = "address"
    DATES = "dates"  # Except year
    PHONE = "phone"
    FAX = "fax"
    EMAIL = "email"
    SSN = "ssn"
    MEDICAL_RECORD = "medical_record"
    HEALTH_PLAN = "health_plan"
    ACCOUNT = "account"
    LICENSE = "license"
    VEHICLE = "vehicle"
    DEVICE = "device"
    URL = "url"
    IP_ADDRESS = "ip_address"
    BIOMETRIC = "biometric"
    PHOTO = "photo"
    OTHER_UNIQUE = "other_unique"


class PHIField(BaseModel):
    """Definition of a PHI field."""

    name: str
    category: PHICategory
    sensitivity: SensitivityLevel = SensitivityLevel.PHI
    requires_encryption: bool = True
    requires_masking: bool = True
    mask_pattern: Optional[str] = None  # e.g., "***-**-{last4}"
    retention_days: Optional[int] = None


class PHIConfig(BaseModel):
    """PHI protection configuration."""

    encrypt_at_rest: bool = True
    encrypt_in_transit: bool = True
    mask_in_logs: bool = True
    audit_access: bool = True
    minimum_necessary: bool = True  # HIPAA minimum necessary rule
    retention_policy_days: int = 2555  # ~7 years per HIPAA


# Standard PHI field definitions
STANDARD_PHI_FIELDS: dict[str, PHIField] = {
    "ssn": PHIField(
        name="ssn",
        category=PHICategory.SSN,
        mask_pattern="***-**-{last4}",
    ),
    "first_name": PHIField(
        name="first_name",
        category=PHICategory.NAME,
        mask_pattern="{first1}****",
    ),
    "last_name": PHIField(
        name="last_name",
        category=PHICategory.NAME,
        mask_pattern="{first1}****",
    ),
    "date_of_birth": PHIField(
        name="date_of_birth",
        category=PHICategory.DATES,
        mask_pattern="****-**-**",
    ),
    "address": PHIField(
        name="address",
        category=PHICategory.ADDRESS,
        mask_pattern="****",
    ),
    "phone": PHIField(
        name="phone",
        category=PHICategory.PHONE,
        mask_pattern="(***) ***-{last4}",
    ),
    "email": PHIField(
        name="email",
        category=PHICategory.EMAIL,
        mask_pattern="{first2}****@****",
    ),
    "medical_record_number": PHIField(
        name="medical_record_number",
        category=PHICategory.MEDICAL_RECORD,
        mask_pattern="MRN-****{last4}",
    ),
    "member_id": PHIField(
        name="member_id",
        category=PHICategory.HEALTH_PLAN,
        mask_pattern="****{last4}",
    ),
    "policy_number": PHIField(
        name="policy_number",
        category=PHICategory.HEALTH_PLAN,
        mask_pattern="****{last4}",
    ),
}


class AccessContext(BaseModel):
    """Context for PHI access control."""

    user_id: str
    role: str
    purpose: str  # Treatment, Payment, Operations
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    request_id: Optional[str] = None


class PHIAccessLog(BaseModel):
    """Log entry for PHI access."""

    access_id: str
    context: AccessContext
    field_accessed: str
    action: str  # view, update, delete
    data_subject_id: str  # Member/patient ID
    masked_value: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PHIProtectionService:
    """Service for PHI protection and compliance."""

    def __init__(self, config: PHIConfig | None = None):
        """Initialize PHIProtectionService."""
        self._config = config or PHIConfig()
        self._field_definitions = STANDARD_PHI_FIELDS.copy()
        self._access_logs: list[PHIAccessLog] = []

    @property
    def config(self) -> PHIConfig:
        """Get configuration."""
        return self._config

    def register_field(self, field: PHIField) -> None:
        """Register a custom PHI field definition."""
        self._field_definitions[field.name] = field

    def get_field_definition(self, field_name: str) -> Optional[PHIField]:
        """Get field definition by name."""
        return self._field_definitions.get(field_name)

    def is_phi_field(self, field_name: str) -> bool:
        """Check if a field contains PHI."""
        return field_name in self._field_definitions

    def mask_value(self, field_name: str, value: str) -> str:
        """Mask a PHI value for display/logging.

        Args:
            field_name: Name of the field
            value: Original value

        Returns:
            Masked value
        """
        if not value:
            return value

        field_def = self._field_definitions.get(field_name)
        if not field_def or not field_def.mask_pattern:
            # Default masking - show first and last char
            if len(value) <= 2:
                return "*" * len(value)
            return value[0] + "*" * (len(value) - 2) + value[-1]

        # Apply custom mask pattern
        pattern = field_def.mask_pattern

        # Replace placeholders
        if "{last4}" in pattern:
            last4 = value[-4:] if len(value) >= 4 else value
            pattern = pattern.replace("{last4}", last4)

        if "{first1}" in pattern:
            pattern = pattern.replace("{first1}", value[0] if value else "*")

        if "{first2}" in pattern:
            first2 = value[:2] if len(value) >= 2 else value
            pattern = pattern.replace("{first2}", first2)

        return pattern

    def mask_dict(self, data: dict, fields: list[str] | None = None) -> dict:
        """Mask PHI fields in a dictionary.

        Args:
            data: Dictionary containing PHI
            fields: Specific fields to mask (or all PHI fields if None)

        Returns:
            Dictionary with masked values
        """
        result = data.copy()
        fields_to_mask = fields or list(self._field_definitions.keys())

        for field in fields_to_mask:
            if field in result and result[field] is not None:
                result[field] = self.mask_value(field, str(result[field]))

        return result

    def detect_phi(self, text: str) -> list[tuple[str, str, int, int]]:
        """Detect potential PHI in unstructured text.

        Args:
            text: Text to scan

        Returns:
            List of (category, matched_text, start, end) tuples
        """
        findings = []

        # SSN pattern
        ssn_pattern = r"\b\d{3}-\d{2}-\d{4}\b"
        for match in re.finditer(ssn_pattern, text):
            findings.append(("ssn", match.group(), match.start(), match.end()))

        # Phone pattern
        phone_pattern = r"\b(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b"
        for match in re.finditer(phone_pattern, text):
            findings.append(("phone", match.group(), match.start(), match.end()))

        # Email pattern
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        for match in re.finditer(email_pattern, text):
            findings.append(("email", match.group(), match.start(), match.end()))

        # Date pattern (MM/DD/YYYY or YYYY-MM-DD)
        date_pattern = r"\b(?:\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})\b"
        for match in re.finditer(date_pattern, text):
            findings.append(("date", match.group(), match.start(), match.end()))

        return findings

    def redact_text(self, text: str) -> str:
        """Redact PHI from unstructured text.

        Args:
            text: Text containing potential PHI

        Returns:
            Text with PHI redacted
        """
        findings = self.detect_phi(text)

        # Sort by position descending to replace from end
        findings.sort(key=lambda x: x[2], reverse=True)

        result = text
        for category, _, start, end in findings:
            redaction = f"[{category.upper()}_REDACTED]"
            result = result[:start] + redaction + result[end:]

        return result

    def log_access(
        self,
        context: AccessContext,
        field_name: str,
        action: str,
        data_subject_id: str,
        value: str | None = None,
    ) -> PHIAccessLog:
        """Log PHI access for audit trail.

        Args:
            context: Access context
            field_name: Field being accessed
            action: Type of access
            data_subject_id: ID of the data subject (patient/member)
            value: Optional value (will be masked)

        Returns:
            Access log entry
        """
        from uuid import uuid4

        masked_value = self.mask_value(field_name, value) if value else None

        log_entry = PHIAccessLog(
            access_id=str(uuid4()),
            context=context,
            field_accessed=field_name,
            action=action,
            data_subject_id=data_subject_id,
            masked_value=masked_value,
        )

        if self._config.audit_access:
            self._access_logs.append(log_entry)

        return log_entry

    def get_access_logs(
        self,
        data_subject_id: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[PHIAccessLog]:
        """Get PHI access logs.

        Args:
            data_subject_id: Filter by data subject
            user_id: Filter by user who accessed
            limit: Maximum number of logs to return

        Returns:
            List of access log entries
        """
        logs = self._access_logs.copy()

        if data_subject_id:
            logs = [l for l in logs if l.data_subject_id == data_subject_id]

        if user_id:
            logs = [l for l in logs if l.context.user_id == user_id]

        return logs[-limit:]

    def validate_minimum_necessary(
        self,
        requested_fields: list[str],
        purpose: str,
    ) -> tuple[bool, list[str]]:
        """Validate minimum necessary rule.

        Args:
            requested_fields: Fields being requested
            purpose: Purpose of the request

        Returns:
            Tuple of (is_valid, allowed_fields)
        """
        # Define allowed fields per purpose
        purpose_allowances = {
            "treatment": ["first_name", "last_name", "date_of_birth", "medical_record_number"],
            "payment": ["first_name", "last_name", "member_id", "policy_number"],
            "operations": ["member_id", "policy_number"],
            "audit": list(self._field_definitions.keys()),  # Auditors can see all
        }

        allowed = purpose_allowances.get(purpose.lower(), [])
        filtered = [f for f in requested_fields if f in allowed or f not in self._field_definitions]

        is_valid = len(filtered) == len(requested_fields)

        return is_valid, filtered

    def clear_logs(self) -> None:
        """Clear access logs (for testing)."""
        self._access_logs.clear()


# =============================================================================
# Factory Functions
# =============================================================================


_phi_service: PHIProtectionService | None = None


def get_phi_service(config: PHIConfig | None = None) -> PHIProtectionService:
    """Get singleton PHIProtectionService instance."""
    global _phi_service
    if _phi_service is None:
        _phi_service = PHIProtectionService(config)
    return _phi_service


def create_phi_service(config: PHIConfig | None = None) -> PHIProtectionService:
    """Create new PHIProtectionService instance."""
    return PHIProtectionService(config)
