"""
E2E Test Fixtures Package.

Contains reusable test fixtures for E2E testing including:
- Sample claims with various validation scenarios
- Mock documents for PDF forensics testing
- Provider and member profile data
"""

from .sample_claims import (
    VALID_CLAIM,
    INVALID_CLAIM_ICD_CONFLICT,
    CLAIM_WITH_AGE_MISMATCH,
    CLAIM_WITH_GENDER_MISMATCH,
    CLAIM_WITH_CROSSWALK_FAILURE,
    DUPLICATE_CLAIM,
    UPCODING_CLAIM,
    UNBUNDLING_CLAIM,
    HIGH_RISK_CLAIM,
    CLEAN_CLAIM_FULL,
)

from .sample_providers import (
    CLEAN_PROVIDER_PROFILE,
    HIGH_RISK_PROVIDER_PROFILE,
    NEW_PROVIDER_PROFILE,
)

from .sample_documents import (
    CLEAN_PDF_METADATA,
    TAMPERED_PDF_METADATA,
    SUSPICIOUS_PDF_METADATA,
)

__all__ = [
    # Claims
    "VALID_CLAIM",
    "INVALID_CLAIM_ICD_CONFLICT",
    "CLAIM_WITH_AGE_MISMATCH",
    "CLAIM_WITH_GENDER_MISMATCH",
    "CLAIM_WITH_CROSSWALK_FAILURE",
    "DUPLICATE_CLAIM",
    "UPCODING_CLAIM",
    "UNBUNDLING_CLAIM",
    "HIGH_RISK_CLAIM",
    "CLEAN_CLAIM_FULL",
    # Providers
    "CLEAN_PROVIDER_PROFILE",
    "HIGH_RISK_PROVIDER_PROFILE",
    "NEW_PROVIDER_PROFILE",
    # Documents
    "CLEAN_PDF_METADATA",
    "TAMPERED_PDF_METADATA",
    "SUSPICIOUS_PDF_METADATA",
]
