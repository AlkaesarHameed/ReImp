"""
Claims Processing Configuration
Extended settings for the Reimbursement Claims Management System.
Source: Design Document 01_configurable_claims_processing_design.md
Verified: 2025-12-18
"""

from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.enums import (
    CodingStandard,
    CurrencyProvider,
    IntegrationMode,
    LLMProvider,
    MedicalNLPProvider,
    NetworkType,
    OCRProvider,
    RulesEngineProvider,
    TranslationProvider,
)


class ClaimsSettings(BaseSettings):
    """
    Claims processing configuration settings.

    Extends the base application settings with claims-specific configuration.
    Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
    Verified: 2025-12-18
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="CLAIMS_",  # All claims settings prefixed with CLAIMS_
    )

    # =========================================================================
    # Integration Mode
    # =========================================================================
    INTEGRATION_MODE: IntegrationMode = Field(
        default=IntegrationMode.DEMO,
        description="Integration mode: demo (local DB) or live (external systems)",
    )

    # =========================================================================
    # LLM Provider Configuration
    # =========================================================================
    LLM_PRIMARY_PROVIDER: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        description="Primary LLM provider for document parsing",
    )
    LLM_FALLBACK_PROVIDER: Optional[LLMProvider] = Field(
        default=LLMProvider.OLLAMA,
        description="Fallback LLM provider when primary fails or low confidence",
    )
    LLM_CONFIDENCE_THRESHOLD: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to accept LLM result without fallback",
    )
    LLM_FALLBACK_ON_ERROR: bool = Field(
        default=True,
        description="Automatically fallback on provider error",
    )

    # Ollama-specific settings
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL",
    )
    OLLAMA_MODEL: str = Field(
        default="llama3.2",
        description="Ollama model for vision/document tasks",
    )
    OLLAMA_MEDICAL_MODEL: str = Field(
        default="llama3.2",
        description="Ollama model for medical NLP tasks",
    )

    # OpenAI-specific settings (primary provider)
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key for GPT models",
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o",
        description="OpenAI model for document parsing",
    )

    # Anthropic-specific settings (for Claude)
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None,
        description="Anthropic API key for Claude",
    )

    # Azure OpenAI-specific settings
    AZURE_OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="Azure OpenAI API key",
    )
    AZURE_OPENAI_ENDPOINT: Optional[str] = Field(
        default=None,
        description="Azure OpenAI endpoint URL",
    )
    AZURE_OPENAI_API_VERSION: str = Field(
        default="2024-02-15-preview",
        description="Azure OpenAI API version",
    )

    # =========================================================================
    # OCR Provider Configuration
    # =========================================================================
    OCR_PRIMARY_PROVIDER: OCRProvider = Field(
        default=OCRProvider.PADDLEOCR,
        description="Primary OCR provider (uses HTTP service when library unavailable)",
    )
    OCR_FALLBACK_PROVIDER: Optional[OCRProvider] = Field(
        default=OCRProvider.TESSERACT,
        description="Fallback OCR provider",
    )
    OCR_CONFIDENCE_THRESHOLD: float = Field(
        default=0.90,
        ge=0.0,
        le=1.0,
        description="Minimum OCR confidence to accept without fallback",
    )
    OCR_FALLBACK_ON_ERROR: bool = Field(
        default=True,
        description="Automatically fallback on OCR error",
    )

    # PaddleOCR settings
    PADDLEOCR_LANGUAGES: str = Field(
        default="en,ar",
        description="Comma-separated language codes for PaddleOCR",
    )
    PADDLEOCR_USE_GPU: bool = Field(
        default=True,
        description="Use GPU acceleration for PaddleOCR",
    )
    PADDLEOCR_HTTP_URL: Optional[str] = Field(
        default="http://localhost:9091",
        description="PaddleOCR HTTP service URL (used when library not installed)",
    )

    # Azure Document Intelligence settings
    AZURE_DI_ENDPOINT: Optional[str] = Field(
        default=None,
        description="Azure Document Intelligence endpoint",
    )
    AZURE_DI_KEY: Optional[str] = Field(
        default=None,
        description="Azure Document Intelligence API key",
    )

    # =========================================================================
    # Translation Provider Configuration
    # =========================================================================
    TRANSLATION_PRIMARY_PROVIDER: TranslationProvider = Field(
        default=TranslationProvider.LIBRETRANSLATE,
        description="Primary translation provider",
    )
    TRANSLATION_FALLBACK_PROVIDER: Optional[TranslationProvider] = Field(
        default=TranslationProvider.AZURE_TRANSLATOR,
        description="Fallback translation provider",
    )

    # LibreTranslate settings
    LIBRETRANSLATE_URL: str = Field(
        default="http://localhost:5000",
        description="LibreTranslate API URL",
    )
    LIBRETRANSLATE_API_KEY: Optional[str] = Field(
        default=None,
        description="LibreTranslate API key (if required)",
    )

    # Azure Translator settings
    AZURE_TRANSLATOR_ENDPOINT: Optional[str] = Field(
        default=None,
        description="Azure Translator endpoint",
    )
    AZURE_TRANSLATOR_KEY: Optional[str] = Field(
        default=None,
        description="Azure Translator API key",
    )
    AZURE_TRANSLATOR_REGION: str = Field(
        default="eastus",
        description="Azure Translator region",
    )

    # =========================================================================
    # Rules Engine Configuration
    # =========================================================================
    RULES_ENGINE_PROVIDER: RulesEngineProvider = Field(
        default=RulesEngineProvider.ZEN,
        description="Rules engine provider",
    )
    RULES_DIRECTORY: str = Field(
        default="rules",
        description="Directory containing rule definition files",
    )

    # =========================================================================
    # Medical NLP Configuration
    # =========================================================================
    MEDICAL_NLP_PRIMARY_PROVIDER: MedicalNLPProvider = Field(
        default=MedicalNLPProvider.MEDCAT,
        description="Primary medical NLP provider",
    )
    MEDICAL_NLP_FALLBACK_PROVIDER: Optional[MedicalNLPProvider] = Field(
        default=MedicalNLPProvider.MEDSPACY,
        description="Fallback medical NLP provider (non-UMLS)",
    )

    # Medical NLP fallback settings
    MEDICAL_NLP_FALLBACK_ON_ERROR: bool = Field(
        default=True,
        description="Automatically fallback on Medical NLP error",
    )
    MEDICAL_NLP_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="Maximum time for Medical NLP processing",
    )
    MEDICAL_NLP_CONFIDENCE_THRESHOLD: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for Medical NLP results",
    )

    # MedCAT settings
    MEDCAT_MODEL_PATH: Optional[str] = Field(
        default=None,
        description="Path to MedCAT model pack",
    )
    UMLS_API_KEY: Optional[str] = Field(
        default=None,
        description="UMLS API key for MedCAT",
    )

    # =========================================================================
    # Currency Configuration
    # =========================================================================
    CURRENCY_PRIMARY_PROVIDER: CurrencyProvider = Field(
        default=CurrencyProvider.FAWAZAHMED,
        description="Primary currency conversion provider",
    )
    CURRENCY_FALLBACK_PROVIDER: Optional[CurrencyProvider] = Field(
        default=CurrencyProvider.FIXER,
        description="Fallback currency provider",
    )
    CURRENCY_CACHE_TTL_SECONDS: int = Field(
        default=3600,
        description="Currency rate cache TTL in seconds",
    )
    DEFAULT_CURRENCY: str = Field(
        default="USD",
        description="Default currency for claims",
    )

    # Fixer.io settings
    FIXER_API_KEY: Optional[str] = Field(
        default=None,
        description="Fixer.io API key",
    )

    # =========================================================================
    # Claims Processing Configuration
    # =========================================================================
    DEFAULT_CODING_STANDARD: CodingStandard = Field(
        default=CodingStandard.US,
        description="Default medical coding standard (US or AU)",
    )
    DEFAULT_NETWORK_TYPE: NetworkType = Field(
        default=NetworkType.PPO,
        description="Default provider network type",
    )
    AUTO_ADJUDICATION_ENABLED: bool = Field(
        default=True,
        description="Enable automatic claim adjudication",
    )
    FWA_DETECTION_ENABLED: bool = Field(
        default=True,
        description="Enable fraud/waste/abuse detection",
    )
    FWA_RISK_THRESHOLD: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="FWA risk score threshold for manual review",
    )

    # Processing timeouts
    DOCUMENT_PROCESSING_TIMEOUT_SECONDS: int = Field(
        default=300,
        description="Maximum time for document processing (5 min)",
    )
    CLAIM_PROCESSING_TIMEOUT_SECONDS: int = Field(
        default=60,
        description="Maximum time for claim processing (1 min)",
    )
    OCR_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="Maximum time for OCR per page",
    )
    LLM_TIMEOUT_SECONDS: int = Field(
        default=300,
        description="Maximum time for LLM processing (5 minutes for vision models)",
    )

    # =========================================================================
    # Demo Mode Configuration
    # =========================================================================
    DEMO_DATABASE_URL: Optional[str] = Field(
        default=None,
        description="Separate database URL for demo mode",
    )
    AUTO_LOAD_DEMO_DATA: bool = Field(
        default=True,
        description="Auto-load sample data on demo startup",
    )
    DEMO_DATA_PATH: str = Field(
        default="demo_data",
        description="Path to demo data files",
    )

    # Payment simulation
    PAYMENT_SIMULATION_ENABLED: bool = Field(
        default=True,
        description="Enable payment simulation in demo mode",
    )
    PAYMENT_SIMULATION_DELAY_MS: int = Field(
        default=5000,
        description="Simulated payment processing delay",
    )
    PAYMENT_SIMULATION_FAILURE_RATE: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Simulated payment failure rate (2%)",
    )

    # =========================================================================
    # Admin Portal Configuration
    # =========================================================================
    ADMIN_PORTAL_ENABLED: bool = Field(
        default=True,
        description="Enable Streamlit admin portal",
    )
    ADMIN_PORTAL_PORT: int = Field(
        default=8501,
        description="Admin portal port",
    )

    # =========================================================================
    # Typesense Search Configuration
    # Source: Design Document 04_validation_engine_comprehensive_design.md
    # =========================================================================
    TYPESENSE_HOST: str = Field(
        default="localhost",
        description="Typesense server host",
    )
    TYPESENSE_PORT: int = Field(
        default=8108,
        description="Typesense server port",
    )
    TYPESENSE_PROTOCOL: str = Field(
        default="http",
        description="Typesense protocol (http or https)",
    )
    TYPESENSE_API_KEY: str = Field(
        default="claims-typesense-dev-key",
        description="Typesense API key",
    )
    TYPESENSE_CONNECTION_TIMEOUT: int = Field(
        default=5,
        description="Typesense connection timeout in seconds",
    )
    TYPESENSE_SEARCH_TIMEOUT_MS: int = Field(
        default=50,
        description="Target search latency in milliseconds",
    )

    # =========================================================================
    # Validation Engine Configuration
    # Source: Design Document 04_validation_engine_comprehensive_design.md
    # =========================================================================
    VALIDATION_CACHE_TTL_SECONDS: int = Field(
        default=300,
        description="Validation result cache TTL (5 min per Q3 decision)",
    )
    VALIDATION_PERSIST_RESULTS: bool = Field(
        default=True,
        description="Persist validation results to database after cache TTL",
    )
    VALIDATION_HUMAN_REVIEW_THRESHOLD: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for human review (per Q4 decision)",
    )
    FRAUD_DETECTION_ENABLED: bool = Field(
        default=True,
        description="Enable PDF forensics fraud detection (Rule 3)",
    )
    FRAUD_RISK_THRESHOLD: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Risk score threshold for fraud rejection",
    )

    # =========================================================================
    # Cache Configuration
    # =========================================================================
    POLICY_CACHE_TTL_SECONDS: int = Field(
        default=300,
        description="Policy data cache TTL (5 min)",
    )
    BENEFIT_CACHE_TTL_SECONDS: int = Field(
        default=600,
        description="Benefit table cache TTL (10 min)",
    )
    OCR_RESULT_CACHE_TTL_SECONDS: int = Field(
        default=86400,
        description="OCR result cache TTL (24 hours)",
    )
    PROVIDER_HEALTH_CACHE_TTL_SECONDS: int = Field(
        default=30,
        description="Provider health status cache TTL",
    )
    CROSSWALK_CACHE_TTL_SECONDS: int = Field(
        default=3600,
        description="ICD-CPT crosswalk cache TTL (1 hour)",
    )
    PROVIDER_LOOKUP_CACHE_TTL_SECONDS: int = Field(
        default=1800,
        description="Provider NPI lookup cache TTL (30 min)",
    )

    # =========================================================================
    # Audit Configuration
    # =========================================================================
    AUDIT_ENABLED: bool = Field(
        default=True,
        description="Enable audit logging",
    )
    AUDIT_RETENTION_YEARS: int = Field(
        default=7,
        description="Audit log retention period (HIPAA: 7 years)",
    )
    AUDIT_PHI_REDACTION: bool = Field(
        default=True,
        description="Redact PHI in audit logs",
    )

    # =========================================================================
    # Validators
    # =========================================================================
    @field_validator("PADDLEOCR_LANGUAGES")
    @classmethod
    def validate_languages(cls, v: str) -> str:
        """Validate language codes are comma-separated."""
        languages = [lang.strip() for lang in v.split(",")]
        valid_codes = {"en", "ar", "ch", "fr", "de", "es", "it", "ja", "ko", "pt", "ru"}
        for lang in languages:
            if lang not in valid_codes:
                # Log warning but don't fail - PaddleOCR may support more
                pass
        return v

    @property
    def paddleocr_languages_list(self) -> list[str]:
        """Get languages as a list."""
        return [lang.strip() for lang in self.PADDLEOCR_LANGUAGES.split(",")]

    @property
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self.INTEGRATION_MODE == IntegrationMode.DEMO

    @property
    def is_live_mode(self) -> bool:
        """Check if running in live mode."""
        return self.INTEGRATION_MODE == IntegrationMode.LIVE


# Singleton instance
_claims_settings: Optional[ClaimsSettings] = None


def get_claims_settings() -> ClaimsSettings:
    """
    Get cached claims settings instance.

    Returns:
        ClaimsSettings instance
    """
    global _claims_settings
    if _claims_settings is None:
        _claims_settings = ClaimsSettings()
    return _claims_settings


# Convenience export
claims_settings = get_claims_settings()
