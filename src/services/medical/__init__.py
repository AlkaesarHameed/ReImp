"""
Medical Validation Services.
Source: Design Document Section 4.1 - Medical Validation
Verified: 2025-12-18

Provides medical code validation, entity extraction, and clinical compatibility checking.
"""

from src.services.medical.code_validator import (
    MedicalCodeValidator,
    CodeValidationResult,
    CodeSystem,
    get_code_validator,
)
from src.services.medical.code_mapper import (
    DiagnosisProcedureMapper,
    CodeMapping,
    MappingResult,
    get_code_mapper,
)
from src.services.medical.necessity import (
    MedicalNecessityService,
    NecessityResult,
    get_necessity_service,
)
from src.services.medical.compatibility import (
    ProcedureCompatibilityChecker,
    CompatibilityResult,
    CompatibilityIssue,
    get_compatibility_checker,
)
from src.services.medical.service import (
    MedicalValidationService,
    MedicalValidationResult,
    get_medical_validation_service,
    create_medical_validation_service,
)
from src.services.medical.lcd_ncd_service import (
    LCDNCDService,
    LCDNCDDatabase,
    CoveragePolicy,
    CoverageDetermination,
    MedicalNecessityResult,
    CoverageType,
    CoverageStatus,
    MACRegion,
    get_lcd_ncd_service,
)

__all__ = [
    # Code Validator
    "MedicalCodeValidator",
    "CodeValidationResult",
    "CodeSystem",
    "get_code_validator",
    # Code Mapper
    "DiagnosisProcedureMapper",
    "CodeMapping",
    "MappingResult",
    "get_code_mapper",
    # Necessity
    "MedicalNecessityService",
    "NecessityResult",
    "get_necessity_service",
    # Compatibility
    "ProcedureCompatibilityChecker",
    "CompatibilityResult",
    "CompatibilityIssue",
    "get_compatibility_checker",
    # Orchestrator
    "MedicalValidationService",
    "MedicalValidationResult",
    "get_medical_validation_service",
    "create_medical_validation_service",
    # LCD/NCD Service
    "LCDNCDService",
    "LCDNCDDatabase",
    "CoveragePolicy",
    "CoverageDetermination",
    "MedicalNecessityResult",
    "CoverageType",
    "CoverageStatus",
    "MACRegion",
    "get_lcd_ncd_service",
]
