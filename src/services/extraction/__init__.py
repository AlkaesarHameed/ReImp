"""
Data Extraction Services for Claims Validation Engine.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Provides LLM-based data extraction from medical documents:
- Rule 1: Insured Data Extraction (patient, member, provider info)
- Rule 2: Medical Code Extraction (ICD-10, CPT, HCPCS, NDC)
"""

from src.services.extraction.insured_data_extractor import (
    InsuredDataExtractor,
    InsuredDataResult,
    PatientInfo,
    ProviderInfo,
    PolicyInfo,
    get_insured_data_extractor,
)
from src.services.extraction.code_extractor import (
    CodeExtractor,
    CodeExtractionResult,
    ExtractedCode,
    CodeType,
    get_code_extractor,
)

__all__ = [
    # Insured Data Extraction (Rule 1)
    "InsuredDataExtractor",
    "InsuredDataResult",
    "PatientInfo",
    "ProviderInfo",
    "PolicyInfo",
    "get_insured_data_extractor",
    # Code Extraction (Rule 2)
    "CodeExtractor",
    "CodeExtractionResult",
    "ExtractedCode",
    "CodeType",
    "get_code_extractor",
]
