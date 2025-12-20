"""
Sample Provider Fixtures for E2E Testing.

Contains predefined provider profiles for various risk scenarios.
"""

from uuid import uuid4


# =============================================================================
# Clean Provider Profile
# =============================================================================

CLEAN_PROVIDER_PROFILE = {
    "id": str(uuid4()),
    "provider_id": "PRV-CLEAN-001",
    "npi": "1234567890",
    "name": "Dr. Sarah Johnson",
    "specialty": "Internal Medicine",
    "taxonomy_code": "207R00000X",
    "practice_address": {
        "street": "123 Medical Center Dr",
        "city": "Springfield",
        "state": "IL",
        "zip": "62701",
    },
    "risk_score": 0.15,
    "risk_level": "low",
    "denial_rate": 0.08,
    "em_code_distribution": {
        "99211": 0.10,
        "99212": 0.20,
        "99213": 0.40,
        "99214": 0.25,
        "99215": 0.05,  # Normal distribution
    },
    "average_claim_amount": 175.00,
    "claims_per_month": 450,
    "years_in_practice": 15,
    "board_certifications": ["Internal Medicine", "Geriatric Medicine"],
    "fraud_alerts": [],
    "investigation_history": [],
    "sanctions": [],
    "is_active": True,
    "created_at": "2020-01-15T00:00:00Z",
    "updated_at": "2025-12-01T00:00:00Z",
}


# =============================================================================
# High Risk Provider Profile
# =============================================================================

HIGH_RISK_PROVIDER_PROFILE = {
    "id": str(uuid4()),
    "provider_id": "PRV-HIGHRISK",
    "npi": "9876543210",
    "name": "Dr. John Smith",
    "specialty": "Family Medicine",
    "taxonomy_code": "207Q00000X",
    "practice_address": {
        "street": "456 Suspicious Blvd",
        "city": "Metropolis",
        "state": "NY",
        "zip": "10001",
    },
    "risk_score": 0.72,
    "risk_level": "high",
    "denial_rate": 0.35,  # 35% denial rate - very high
    "em_code_distribution": {
        "99211": 0.02,
        "99212": 0.05,
        "99213": 0.13,
        "99214": 0.30,
        "99215": 0.50,  # 50% highest level - suspicious
    },
    "average_claim_amount": 425.00,  # Above average
    "claims_per_month": 1200,  # Very high volume
    "years_in_practice": 5,
    "board_certifications": ["Family Medicine"],
    "fraud_alerts": [
        {
            "alert_id": "ALT-001",
            "alert_type": "upcoding_pattern",
            "severity": "high",
            "description": "Excessive high-level E/M codes",
            "detected_at": "2025-06-15T00:00:00Z",
        },
        {
            "alert_id": "ALT-002",
            "alert_type": "impossible_day",
            "severity": "medium",
            "description": "Multiple days with 60+ procedures",
            "detected_at": "2025-08-20T00:00:00Z",
        },
    ],
    "investigation_history": [
        {
            "investigation_id": "INV-001",
            "status": "closed",
            "outcome": "substantiated",
            "finding": "Systematic upcoding identified",
            "period": "2024-Q3",
            "recovery_amount": 45000.00,
        },
    ],
    "sanctions": [],
    "is_active": True,
    "created_at": "2019-03-10T00:00:00Z",
    "updated_at": "2025-12-10T00:00:00Z",
}


# =============================================================================
# New Provider Profile
# =============================================================================

NEW_PROVIDER_PROFILE = {
    "id": str(uuid4()),
    "provider_id": "PRV-NEW-001",
    "npi": "5555555555",
    "name": "Dr. Emily Chen",
    "specialty": "Pediatrics",
    "taxonomy_code": "208000000X",
    "practice_address": {
        "street": "789 New Practice Way",
        "city": "Austin",
        "state": "TX",
        "zip": "78701",
    },
    "risk_score": 0.35,  # Elevated due to limited history
    "risk_level": "medium",
    "denial_rate": 0.12,
    "em_code_distribution": {
        "99211": 0.15,
        "99212": 0.25,
        "99213": 0.35,
        "99214": 0.20,
        "99215": 0.05,
    },
    "average_claim_amount": 165.00,
    "claims_per_month": 120,  # Lower volume - new practice
    "years_in_practice": 1,
    "board_certifications": ["Pediatrics"],
    "fraud_alerts": [],
    "investigation_history": [],
    "sanctions": [],
    "is_active": True,
    "is_new_provider": True,
    "probation_period_ends": "2026-06-01",
    "created_at": "2025-06-01T00:00:00Z",
    "updated_at": "2025-12-01T00:00:00Z",
}


# =============================================================================
# Excluded Provider Profile
# =============================================================================

EXCLUDED_PROVIDER_PROFILE = {
    "id": str(uuid4()),
    "provider_id": "PRV-EXCLUDED",
    "npi": "1111111111",
    "name": "Dr. Robert Fraud",
    "specialty": "Internal Medicine",
    "taxonomy_code": "207R00000X",
    "practice_address": {
        "street": "000 Excluded Rd",
        "city": "Nowhere",
        "state": "CA",
        "zip": "90000",
    },
    "risk_score": 1.0,
    "risk_level": "excluded",
    "denial_rate": 1.0,  # All claims denied
    "em_code_distribution": {},
    "average_claim_amount": 0,
    "claims_per_month": 0,
    "years_in_practice": 20,
    "board_certifications": [],  # Revoked
    "fraud_alerts": [
        {
            "alert_id": "ALT-CRITICAL",
            "alert_type": "exclusion",
            "severity": "critical",
            "description": "Provider on OIG Exclusion List",
            "detected_at": "2024-01-15T00:00:00Z",
        },
    ],
    "investigation_history": [
        {
            "investigation_id": "INV-FINAL",
            "status": "closed",
            "outcome": "exclusion",
            "finding": "Healthcare fraud conviction",
            "period": "2023-2024",
            "recovery_amount": 500000.00,
        },
    ],
    "sanctions": [
        {
            "sanction_id": "SAN-001",
            "type": "OIG Exclusion",
            "effective_date": "2024-01-15",
            "end_date": None,  # Indefinite
            "reason": "Healthcare fraud",
        },
    ],
    "is_active": False,
    "exclusion_date": "2024-01-15",
    "exclusion_reason": "Healthcare fraud conviction - 18 U.S.C. § 1347",
    "created_at": "2010-05-20T00:00:00Z",
    "updated_at": "2024-01-15T00:00:00Z",
}


# =============================================================================
# Provider Collections
# =============================================================================

ALL_PROVIDER_PROFILES = [
    CLEAN_PROVIDER_PROFILE,
    HIGH_RISK_PROVIDER_PROFILE,
    NEW_PROVIDER_PROFILE,
    EXCLUDED_PROVIDER_PROFILE,
]

ACTIVE_PROVIDERS = [
    CLEAN_PROVIDER_PROFILE,
    HIGH_RISK_PROVIDER_PROFILE,
    NEW_PROVIDER_PROFILE,
]

HIGH_RISK_PROVIDERS = [
    HIGH_RISK_PROVIDER_PROFILE,
    EXCLUDED_PROVIDER_PROFILE,
]


# =============================================================================
# Helper Functions
# =============================================================================


def create_provider_with_risk(risk_score: float, **overrides) -> dict:
    """Create a provider profile with specified risk score."""
    profile = CLEAN_PROVIDER_PROFILE.copy()
    profile["id"] = str(uuid4())
    profile["provider_id"] = f"PRV-TEST-{uuid4().hex[:8].upper()}"
    profile["risk_score"] = risk_score

    if risk_score < 0.3:
        profile["risk_level"] = "low"
    elif risk_score < 0.6:
        profile["risk_level"] = "medium"
    elif risk_score < 0.9:
        profile["risk_level"] = "high"
    else:
        profile["risk_level"] = "critical"

    profile.update(overrides)
    return profile


def create_provider_with_denial_rate(denial_rate: float, **overrides) -> dict:
    """Create a provider profile with specified denial rate."""
    profile = CLEAN_PROVIDER_PROFILE.copy()
    profile["id"] = str(uuid4())
    profile["provider_id"] = f"PRV-TEST-{uuid4().hex[:8].upper()}"
    profile["denial_rate"] = denial_rate
    profile.update(overrides)
    return profile


def create_provider_with_em_distribution(distribution: dict, **overrides) -> dict:
    """Create a provider with specified E/M code distribution."""
    profile = CLEAN_PROVIDER_PROFILE.copy()
    profile["id"] = str(uuid4())
    profile["provider_id"] = f"PRV-TEST-{uuid4().hex[:8].upper()}"
    profile["em_code_distribution"] = distribution
    profile.update(overrides)
    return profile
