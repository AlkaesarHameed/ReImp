"""
Medical Code Schemas for Validation Engine.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

These schemas define the structure for medical codes stored in Typesense
and used throughout the validation engine.
"""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ICD10Category(str, Enum):
    """ICD-10 code categories."""

    INFECTIOUS = "A00-B99"
    NEOPLASMS = "C00-D49"
    BLOOD = "D50-D89"
    ENDOCRINE = "E00-E89"
    MENTAL = "F01-F99"
    NERVOUS = "G00-G99"
    EYE = "H00-H59"
    EAR = "H60-H95"
    CIRCULATORY = "I00-I99"
    RESPIRATORY = "J00-J99"
    DIGESTIVE = "K00-K95"
    SKIN = "L00-L99"
    MUSCULOSKELETAL = "M00-M99"
    GENITOURINARY = "N00-N99"
    PREGNANCY = "O00-O9A"
    PERINATAL = "P00-P96"
    CONGENITAL = "Q00-Q99"
    ABNORMAL_FINDINGS = "R00-R99"
    INJURY = "S00-T88"
    EXTERNAL_CAUSES = "V00-Y99"
    FACTORS = "Z00-Z99"


class GenderRestriction(str, Enum):
    """Gender restrictions for medical codes."""

    MALE = "M"
    FEMALE = "F"
    NONE = "N"


class ICD10Code(BaseModel):
    """
    ICD-10-CM/PCS code schema.

    Used for diagnosis and procedure code lookups.
    """

    code: str = Field(..., description="ICD-10 code (e.g., 'E11.9')")
    description: str = Field(..., description="Full description of the code")
    short_description: Optional[str] = Field(None, description="Short description")
    category: str = Field(..., description="Category range (e.g., 'E00-E89')")
    chapter: Optional[str] = Field(None, description="Chapter name")
    is_billable: bool = Field(True, description="Whether code is billable")
    is_header: bool = Field(False, description="Whether code is a header/category")
    min_age: Optional[int] = Field(None, description="Minimum patient age")
    max_age: Optional[int] = Field(None, description="Maximum patient age")
    gender_restriction: GenderRestriction = Field(
        GenderRestriction.NONE, description="Gender restriction"
    )
    effective_date: Optional[date] = Field(None, description="Code effective date")
    termination_date: Optional[date] = Field(None, description="Code termination date")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "E11.9",
                "description": "Type 2 diabetes mellitus without complications",
                "short_description": "Type 2 diabetes w/o complications",
                "category": "E00-E89",
                "chapter": "Endocrine, nutritional and metabolic diseases",
                "is_billable": True,
                "is_header": False,
                "gender_restriction": "N",
            }
        }


class CPTCategory(str, Enum):
    """CPT code categories."""

    EVALUATION_MANAGEMENT = "E/M"
    ANESTHESIA = "Anesthesia"
    SURGERY = "Surgery"
    RADIOLOGY = "Radiology"
    PATHOLOGY = "Pathology"
    MEDICINE = "Medicine"
    CATEGORY_II = "Category II"
    CATEGORY_III = "Category III"


class CPTCode(BaseModel):
    """
    CPT/HCPCS code schema.

    Used for procedure code lookups and billing.
    """

    code: str = Field(..., description="CPT/HCPCS code (e.g., '99213')")
    description: str = Field(..., description="Full description of the code")
    short_description: Optional[str] = Field(None, description="Short description")
    category: str = Field(..., description="Code category")
    subcategory: Optional[str] = Field(None, description="Subcategory")
    work_rvu: Optional[float] = Field(None, description="Work RVU value")
    facility_pe_rvu: Optional[float] = Field(None, description="Facility PE RVU")
    non_facility_pe_rvu: Optional[float] = Field(None, description="Non-facility PE RVU")
    mp_rvu: Optional[float] = Field(None, description="Malpractice RVU")
    status: str = Field("A", description="Code status (A=Active, I=Inactive)")
    min_age: Optional[int] = Field(None, description="Minimum patient age")
    max_age: Optional[int] = Field(None, description="Maximum patient age")
    gender_restriction: GenderRestriction = Field(
        GenderRestriction.NONE, description="Gender restriction"
    )
    global_period: Optional[int] = Field(None, description="Global surgery period in days")
    modifier_allowed: bool = Field(True, description="Whether modifiers are allowed")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "99213",
                "description": "Office or other outpatient visit for the evaluation and management of an established patient",
                "short_description": "Office visit, est patient, low",
                "category": "E/M",
                "work_rvu": 1.30,
                "status": "A",
            }
        }


class NCCIEditType(str, Enum):
    """NCCI edit types."""

    PTP = "PTP"  # Procedure to Procedure
    MUE = "MUE"  # Medically Unlikely Edit


class ModifierIndicator(str, Enum):
    """NCCI modifier indicators."""

    NOT_ALLOWED = "0"  # No modifier allowed to bypass edit
    ALLOWED = "1"  # Modifier allowed to bypass edit
    N_A = "9"  # Not applicable


class NCCIEdit(BaseModel):
    """
    NCCI (National Correct Coding Initiative) edit schema.

    Used for procedure-to-procedure edits and bundling checks.
    """

    column1_code: str = Field(..., description="Column 1 CPT code (comprehensive)")
    column2_code: str = Field(..., description="Column 2 CPT code (component)")
    modifier_indicator: ModifierIndicator = Field(
        ..., description="Whether modifier can bypass edit"
    )
    effective_date: date = Field(..., description="Edit effective date")
    deletion_date: Optional[date] = Field(None, description="Edit deletion date")
    edit_type: NCCIEditType = Field(NCCIEditType.PTP, description="Type of edit")
    rationale: Optional[str] = Field(None, description="Edit rationale")

    class Config:
        json_schema_extra = {
            "example": {
                "column1_code": "43239",
                "column2_code": "43235",
                "modifier_indicator": "1",
                "effective_date": "2024-01-01",
                "edit_type": "PTP",
                "rationale": "Column 2 code is component of Column 1",
            }
        }


class MUEAdjudicator(str, Enum):
    """MUE adjudicator indicators."""

    CLAIM = "1"  # Claim line edit
    DAY = "2"  # Date of service edit
    POLICY = "3"  # Policy edit


class MUELimit(BaseModel):
    """
    MUE (Medically Unlikely Edit) limit schema.

    Defines maximum units of service per claim/day.
    """

    cpt_code: str = Field(..., description="CPT/HCPCS code")
    practitioner_limit: int = Field(..., description="Practitioner services limit")
    facility_limit: int = Field(..., description="Outpatient hospital limit")
    dme_limit: Optional[int] = Field(None, description="DME supplier limit")
    adjudicator: MUEAdjudicator = Field(..., description="Adjudicator indicator")
    effective_date: date = Field(..., description="Effective date")
    rationale: Optional[str] = Field(None, description="MUE rationale")

    class Config:
        json_schema_extra = {
            "example": {
                "cpt_code": "99213",
                "practitioner_limit": 1,
                "facility_limit": 1,
                "adjudicator": "2",
                "effective_date": "2024-01-01",
                "rationale": "One E/M service per date of service",
            }
        }


class CrosswalkResult(BaseModel):
    """
    ICD-CPT crosswalk validation result.

    Indicates whether a procedure is medically appropriate for given diagnoses.
    """

    icd_code: str = Field(..., description="ICD-10 diagnosis code")
    cpt_code: str = Field(..., description="CPT procedure code")
    is_valid: bool = Field(..., description="Whether pairing is valid")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    evidence: Optional[str] = Field(None, description="Supporting evidence/rationale")
    source: str = Field("CMS", description="Data source (CMS, LCD, etc.)")


class SearchResult(BaseModel):
    """Generic search result wrapper."""

    query: str = Field(..., description="Original search query")
    total_hits: int = Field(..., description="Total matching results")
    search_time_ms: int = Field(..., description="Search time in milliseconds")
    results: list = Field(default_factory=list, description="Search results")


class ICD10SearchResult(SearchResult):
    """ICD-10 code search result."""

    results: list[ICD10Code] = Field(default_factory=list)


class CPTSearchResult(SearchResult):
    """CPT code search result."""

    results: list[CPTCode] = Field(default_factory=list)
