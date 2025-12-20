"""
Validation Services for Claims Validation Engine.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Provides validation rule implementations:
- Rule 3: PDF Forensics (fraud detection)
- Rule 4: ICD-CPT Crosswalk
- Rule 5: Clinical Necessity (LLM-based)
- Rule 6: ICD×ICD Conflict Detection
- Rules 7-8: Demographic Validation
- Rule 9: Policy and Coverage Validation
"""

from src.services.validation.pdf_forensics import (
    PDFForensicsService,
    ForensicSignal,
    ForensicResult,
    get_pdf_forensics_service,
)
from src.services.validation.icd_cpt_crosswalk import (
    ICDCPTCrosswalkValidator,
    CrosswalkValidationResult,
    get_crosswalk_validator,
)
from src.services.validation.icd_conflict_validator import (
    ICDConflictValidator,
    ConflictResult,
    ConflictType,
    get_icd_conflict_validator,
)
from src.services.validation.demographic_validator import (
    DemographicValidator,
    DemographicValidationResult,
    get_demographic_validator,
)
from src.services.validation.llm_validation_service import (
    LLMValidationService,
    ValidationLLMResult,
    get_llm_validation_service,
)
from src.services.validation.clinical_necessity_validator import (
    ClinicalNecessityValidator,
    ClinicalNecessityResult,
    NecessityLevel,
    get_clinical_necessity_validator,
)
from src.services.validation.policy_validator import (
    PolicyValidator,
    PolicyValidationResult,
    CoverageStatus,
    get_policy_validator,
)
from src.services.validation.medical_report_validator import (
    MedicalReportValidator,
    MedicalReportValidationResult,
    ComplianceLevel,
    SectionAnalysis,
    get_medical_report_validator,
)
from src.services.validation.risk_scorer import (
    RiskScorer,
    RiskAssessment,
    RiskFactor,
    RiskLevel,
    RiskCategory,
    get_risk_scorer,
)
from src.services.validation.orchestrator import (
    ValidationOrchestrator,
    ClaimValidationInput,
    ComprehensiveValidationResult,
    ValidationDecision,
    ValidationPhase,
    get_validation_orchestrator,
    validate_claim_comprehensive,
)
from src.services.validation.performance import (
    ValidationPerformanceConfig,
    ValidationCacheService,
    ValidationPerformanceMonitor,
    BatchProcessor,
    ParallelExecutor,
    BatchResult,
    get_validation_cache,
    get_batch_processor,
    get_validation_performance_monitor,
    get_parallel_executor,
    monitor_validation,
    cache_code_lookup,
)

__all__ = [
    # PDF Forensics (Rule 3)
    "PDFForensicsService",
    "ForensicSignal",
    "ForensicResult",
    "get_pdf_forensics_service",
    # ICD-CPT Crosswalk (Rule 4)
    "ICDCPTCrosswalkValidator",
    "CrosswalkValidationResult",
    "get_crosswalk_validator",
    # Clinical Necessity (Rule 5)
    "ClinicalNecessityValidator",
    "ClinicalNecessityResult",
    "NecessityLevel",
    "get_clinical_necessity_validator",
    # ICD Conflict (Rule 6)
    "ICDConflictValidator",
    "ConflictResult",
    "ConflictType",
    "get_icd_conflict_validator",
    # Demographic (Rules 7-8)
    "DemographicValidator",
    "DemographicValidationResult",
    "get_demographic_validator",
    # Policy Validator (Rule 9)
    "PolicyValidator",
    "PolicyValidationResult",
    "CoverageStatus",
    "get_policy_validator",
    # LLM Validation Service
    "LLMValidationService",
    "ValidationLLMResult",
    "get_llm_validation_service",
    # Medical Report Validator (Rule 9 - Documentation)
    "MedicalReportValidator",
    "MedicalReportValidationResult",
    "ComplianceLevel",
    "SectionAnalysis",
    "get_medical_report_validator",
    # Risk Scorer
    "RiskScorer",
    "RiskAssessment",
    "RiskFactor",
    "RiskLevel",
    "RiskCategory",
    "get_risk_scorer",
    # Orchestrator
    "ValidationOrchestrator",
    "ClaimValidationInput",
    "ComprehensiveValidationResult",
    "ValidationDecision",
    "ValidationPhase",
    "get_validation_orchestrator",
    "validate_claim_comprehensive",
    # Performance (Phase 5.4)
    "ValidationPerformanceConfig",
    "ValidationCacheService",
    "ValidationPerformanceMonitor",
    "BatchProcessor",
    "ParallelExecutor",
    "BatchResult",
    "get_validation_cache",
    "get_batch_processor",
    "get_validation_performance_monitor",
    "get_parallel_executor",
    "monitor_validation",
    "cache_code_lookup",
]
