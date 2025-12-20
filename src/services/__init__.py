"""
Services Layer for Claims Processing System.

Exports document processing, benefit calculation, and tenant management services.
"""

from src.services.tenant_service import (
    TenantService,
    TenantServiceError,
    TenantNotFoundError,
    TenantExistsError,
    get_tenant_service,
)
from src.services.document_storage import (
    DocumentStorageService,
    StorageConfig,
    UploadResult,
    DownloadResult,
    get_document_storage_service,
    create_document_storage_service,
)
from src.services.ocr_pipeline import (
    OCRPipelineService,
    OCRPipelineConfig,
    OCRPipelineResult,
    PageOCRResult,
    OCRQuality,
    get_ocr_pipeline,
    create_ocr_pipeline,
)
from src.services.llm_parser import (
    LLMParserService,
    LLMParserConfig,
    ClaimExtractionResult,
    ExtractionConfidence,
    get_llm_parser,
    create_llm_parser,
)
from src.services.document_processor import (
    DocumentProcessor,
    ProcessorConfig,
    DocumentProcessingResult,
    ProcessingStage,
    get_document_processor,
    create_document_processor,
)
from src.services.benefit_lookup import (
    BenefitLookupService,
    get_benefit_lookup_service,
)
from src.services.benefit_calculator import (
    BenefitCalculator,
    PatientShareCalculator,
    get_benefit_calculator,
)
from src.services.benefit_rules_engine import (
    BenefitRulesEngine,
    BenefitRule,
    RuleContext,
    RuleResult,
    RuleOutcome,
    get_benefit_rules_engine,
)
from src.services.adjudication_validators import (
    PolicyValidator,
    EligibilityValidator,
    NetworkValidator,
    PriorAuthValidator,
    MedicalNecessityValidator,
    DuplicateClaimChecker,
    TimelyFilingChecker,
    get_policy_validator,
    get_eligibility_validator,
    get_network_validator,
    get_prior_auth_validator,
    get_medical_necessity_validator,
    get_duplicate_checker,
    get_timely_filing_checker,
)
from src.services.adjudication_service import (
    AdjudicationService,
    AdjudicationServiceError,
    get_adjudication_service,
    create_adjudication_service,
)
from src.services.eob_generator import (
    EOBGenerator,
    EOBGeneratorError,
    get_eob_generator,
    create_eob_generator,
)

# EDI Services
# Source: Design Document 06_high_value_enhancements_design.md
from src.services.edi import (
    EDIService,
    get_edi_service,
    X12837Parser,
    X12835Generator,
    X12Tokenizer,
    TransactionType,
    X12ParseError,
    X12ValidationError,
    # Eligibility
    EligibilityService,
    EligibilityRequest,
    EligibilityCheckResult,
    get_eligibility_service,
)

__all__ = [
    # Tenant Service
    "TenantService",
    "TenantServiceError",
    "TenantNotFoundError",
    "TenantExistsError",
    "get_tenant_service",
    # Document Storage
    "DocumentStorageService",
    "StorageConfig",
    "UploadResult",
    "DownloadResult",
    "get_document_storage_service",
    "create_document_storage_service",
    # OCR Pipeline
    "OCRPipelineService",
    "OCRPipelineConfig",
    "OCRPipelineResult",
    "PageOCRResult",
    "OCRQuality",
    "get_ocr_pipeline",
    "create_ocr_pipeline",
    # LLM Parser
    "LLMParserService",
    "LLMParserConfig",
    "ClaimExtractionResult",
    "ExtractionConfidence",
    "get_llm_parser",
    "create_llm_parser",
    # Document Processor
    "DocumentProcessor",
    "ProcessorConfig",
    "DocumentProcessingResult",
    "ProcessingStage",
    "get_document_processor",
    "create_document_processor",
    # Benefit Lookup
    "BenefitLookupService",
    "get_benefit_lookup_service",
    # Benefit Calculator
    "BenefitCalculator",
    "PatientShareCalculator",
    "get_benefit_calculator",
    # Benefit Rules Engine
    "BenefitRulesEngine",
    "BenefitRule",
    "RuleContext",
    "RuleResult",
    "RuleOutcome",
    "get_benefit_rules_engine",
    # Adjudication Validators
    "PolicyValidator",
    "EligibilityValidator",
    "NetworkValidator",
    "PriorAuthValidator",
    "MedicalNecessityValidator",
    "DuplicateClaimChecker",
    "TimelyFilingChecker",
    "get_policy_validator",
    "get_eligibility_validator",
    "get_network_validator",
    "get_prior_auth_validator",
    "get_medical_necessity_validator",
    "get_duplicate_checker",
    "get_timely_filing_checker",
    # Adjudication Service
    "AdjudicationService",
    "AdjudicationServiceError",
    "get_adjudication_service",
    "create_adjudication_service",
    # EOB Generator
    "EOBGenerator",
    "EOBGeneratorError",
    "get_eob_generator",
    "create_eob_generator",
    # EDI Services
    "EDIService",
    "get_edi_service",
    "X12837Parser",
    "X12835Generator",
    "X12Tokenizer",
    "TransactionType",
    "X12ParseError",
    "X12ValidationError",
    # Eligibility Services
    "EligibilityService",
    "EligibilityRequest",
    "EligibilityCheckResult",
    "get_eligibility_service",
]
