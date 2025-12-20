"""
Sample Claims Fixtures for E2E Testing.

Contains predefined claim data for various validation scenarios.
"""

from datetime import date, datetime
from uuid import uuid4


# =============================================================================
# Valid Claims
# =============================================================================

VALID_CLAIM = {
    "id": str(uuid4()),
    "claim_number": "CLM-2025-001",
    "member_id": "MEM-123456",
    "provider_id": "PRV-789012",
    "service_date": "2025-12-15",
    "date_of_birth": "1980-05-15",  # 45 years old
    "gender": "M",
    "icd_codes": ["E11.9"],  # Type 2 diabetes without complications
    "cpt_codes": ["99213"],  # Office visit, level 3
    "total_charged": 150.00,
    "units": 1,
    "place_of_service": "11",  # Office
    "status": "pending",
}

CLEAN_CLAIM_FULL = {
    "id": str(uuid4()),
    "claim_number": "CLM-2025-002",
    "member_id": "MEM-234567",
    "provider_id": "PRV-890123",
    "service_date": "2025-12-10",
    "date_of_birth": "1965-03-20",  # 60 years old
    "gender": "F",
    "icd_codes": ["I10"],  # Essential hypertension
    "cpt_codes": ["99214"],  # Office visit, level 4
    "total_charged": 200.00,
    "units": 1,
    "place_of_service": "11",
    "status": "pending",
    "provider_npi": "1234567890",
    "diagnosis_pointers": ["1"],
    "modifiers": [],
}


# =============================================================================
# Claims with Validation Failures
# =============================================================================

INVALID_CLAIM_ICD_CONFLICT = {
    "id": str(uuid4()),
    "claim_number": "CLM-2025-003",
    "member_id": "MEM-345678",
    "provider_id": "PRV-901234",
    "service_date": "2025-12-15",
    "date_of_birth": "1990-08-25",
    "gender": "M",
    "icd_codes": ["E10.9", "E11.9"],  # Type 1 AND Type 2 diabetes - conflict
    "cpt_codes": ["99213"],
    "total_charged": 150.00,
    "units": 1,
    "place_of_service": "11",
    "status": "pending",
}

CLAIM_WITH_AGE_MISMATCH = {
    "id": str(uuid4()),
    "claim_number": "CLM-2025-004",
    "member_id": "MEM-456789",
    "provider_id": "PRV-012345",
    "service_date": "2025-12-15",
    "date_of_birth": "2020-01-15",  # 5 years old
    "gender": "M",
    "icd_codes": ["N40.0"],  # Benign prostatic hyperplasia - adult condition
    "cpt_codes": ["52601"],  # TURP - prostate surgery
    "total_charged": 5000.00,
    "units": 1,
    "place_of_service": "21",  # Inpatient hospital
    "status": "pending",
}

CLAIM_WITH_GENDER_MISMATCH = {
    "id": str(uuid4()),
    "claim_number": "CLM-2025-005",
    "member_id": "MEM-567890",
    "provider_id": "PRV-123456",
    "service_date": "2025-12-15",
    "date_of_birth": "1985-06-10",
    "gender": "M",  # Male patient
    "icd_codes": ["O80"],  # Normal delivery - female only
    "cpt_codes": ["59400"],  # Routine obstetric care
    "total_charged": 3500.00,
    "units": 1,
    "place_of_service": "21",
    "status": "pending",
}

CLAIM_WITH_CROSSWALK_FAILURE = {
    "id": str(uuid4()),
    "claim_number": "CLM-2025-006",
    "member_id": "MEM-678901",
    "provider_id": "PRV-234567",
    "service_date": "2025-12-15",
    "date_of_birth": "1970-11-30",
    "gender": "F",
    "icd_codes": ["J06.9"],  # Acute upper respiratory infection
    "cpt_codes": ["99215"],  # High-level office visit - not warranted for simple URI
    "total_charged": 350.00,
    "units": 1,
    "place_of_service": "11",
    "status": "pending",
}


# =============================================================================
# FWA-Related Claims
# =============================================================================

DUPLICATE_CLAIM = {
    "id": str(uuid4()),
    "claim_number": "CLM-2025-007",
    "member_id": "MEM-123456",  # Same member as VALID_CLAIM
    "provider_id": "PRV-789012",  # Same provider as VALID_CLAIM
    "service_date": "2025-12-15",  # Same date as VALID_CLAIM
    "date_of_birth": "1980-05-15",
    "gender": "M",
    "icd_codes": ["E11.9"],  # Same diagnosis
    "cpt_codes": ["99213"],  # Same procedure
    "total_charged": 150.00,
    "units": 1,
    "place_of_service": "11",
    "status": "pending",
}

UPCODING_CLAIM = {
    "id": str(uuid4()),
    "claim_number": "CLM-2025-008",
    "member_id": "MEM-789012",
    "provider_id": "PRV-HIGHRISK",  # Known high-upcoding provider
    "service_date": "2025-12-15",
    "date_of_birth": "1995-04-20",
    "gender": "F",
    "icd_codes": ["J06.9"],  # Simple acute URI
    "cpt_codes": ["99215"],  # Highest level office visit
    "total_charged": 350.00,
    "units": 1,
    "place_of_service": "11",
    "status": "pending",
    "provider_em_history": {
        "99211": 0.02,
        "99212": 0.05,
        "99213": 0.15,
        "99214": 0.28,
        "99215": 0.50,  # 50% highest level - suspicious
    },
}

UNBUNDLING_CLAIM = {
    "id": str(uuid4()),
    "claim_number": "CLM-2025-009",
    "member_id": "MEM-890123",
    "provider_id": "PRV-345678",
    "service_date": "2025-12-15",
    "date_of_birth": "1960-09-05",
    "gender": "M",
    "icd_codes": ["E11.9", "I10"],
    "cpt_codes": ["82947", "80053"],  # Glucose billed separately from CMP
    "total_charged": 75.00,
    "units": 1,
    "place_of_service": "11",
    "status": "pending",
}

HIGH_RISK_CLAIM = {
    "id": str(uuid4()),
    "claim_number": "CLM-2025-010",
    "member_id": "MEM-HIGHRISK",
    "provider_id": "PRV-HIGHRISK",
    "service_date": "2025-12-15",
    "date_of_birth": "1975-07-12",
    "gender": "M",
    "icd_codes": ["E11.9", "E10.9"],  # Conflicting diabetes types
    "cpt_codes": ["99215", "99215"],  # Duplicate high-level codes
    "total_charged": 700.00,
    "units": 2,
    "place_of_service": "11",
    "status": "pending",
    "risk_indicators": [
        "high_risk_provider",
        "icd_conflict",
        "duplicate_procedure",
        "excessive_charge",
    ],
}


# =============================================================================
# Claim Collections
# =============================================================================

ALL_VALID_CLAIMS = [VALID_CLAIM, CLEAN_CLAIM_FULL]

ALL_INVALID_CLAIMS = [
    INVALID_CLAIM_ICD_CONFLICT,
    CLAIM_WITH_AGE_MISMATCH,
    CLAIM_WITH_GENDER_MISMATCH,
    CLAIM_WITH_CROSSWALK_FAILURE,
]

ALL_FWA_CLAIMS = [
    DUPLICATE_CLAIM,
    UPCODING_CLAIM,
    UNBUNDLING_CLAIM,
    HIGH_RISK_CLAIM,
]


# =============================================================================
# Helper Functions
# =============================================================================


def create_claim_with_icd(icd_codes: list[str], **overrides) -> dict:
    """Create a claim with specified ICD codes."""
    claim = VALID_CLAIM.copy()
    claim["id"] = str(uuid4())
    claim["claim_number"] = f"CLM-TEST-{uuid4().hex[:8].upper()}"
    claim["icd_codes"] = icd_codes
    claim.update(overrides)
    return claim


def create_claim_with_cpt(cpt_codes: list[str], **overrides) -> dict:
    """Create a claim with specified CPT codes."""
    claim = VALID_CLAIM.copy()
    claim["id"] = str(uuid4())
    claim["claim_number"] = f"CLM-TEST-{uuid4().hex[:8].upper()}"
    claim["cpt_codes"] = cpt_codes
    claim.update(overrides)
    return claim


def create_claim_for_age(age: int, **overrides) -> dict:
    """Create a claim for a patient of specified age."""
    claim = VALID_CLAIM.copy()
    claim["id"] = str(uuid4())
    claim["claim_number"] = f"CLM-TEST-{uuid4().hex[:8].upper()}"
    birth_year = date.today().year - age
    claim["date_of_birth"] = f"{birth_year}-01-15"
    claim.update(overrides)
    return claim


def create_claim_for_gender(gender: str, **overrides) -> dict:
    """Create a claim for a patient of specified gender."""
    claim = VALID_CLAIM.copy()
    claim["id"] = str(uuid4())
    claim["claim_number"] = f"CLM-TEST-{uuid4().hex[:8].upper()}"
    claim["gender"] = gender
    claim.update(overrides)
    return claim
