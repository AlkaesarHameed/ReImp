"""
Unit tests for claims processing configuration.
"""

import pytest
from decimal import Decimal

from src.core.config import ClaimsSettings, get_claims_settings
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


class TestClaimsSettingsDefaults:
    """Tests for default configuration values."""

    def test_default_integration_mode(self):
        """Test default integration mode is demo."""
        settings = ClaimsSettings()
        assert settings.INTEGRATION_MODE == IntegrationMode.DEMO

    def test_default_llm_provider(self):
        """Test default LLM provider is Ollama."""
        settings = ClaimsSettings()
        assert settings.LLM_PRIMARY_PROVIDER == LLMProvider.OLLAMA
        assert settings.LLM_FALLBACK_PROVIDER == LLMProvider.OPENAI

    def test_default_ocr_provider(self):
        """Test default OCR provider is PaddleOCR."""
        settings = ClaimsSettings()
        assert settings.OCR_PRIMARY_PROVIDER == OCRProvider.PADDLEOCR
        assert settings.OCR_FALLBACK_PROVIDER == OCRProvider.AZURE_DI

    def test_default_translation_provider(self):
        """Test default translation provider is LibreTranslate."""
        settings = ClaimsSettings()
        assert settings.TRANSLATION_PRIMARY_PROVIDER == TranslationProvider.LIBRETRANSLATE

    def test_default_rules_engine(self):
        """Test default rules engine is ZEN."""
        settings = ClaimsSettings()
        assert settings.RULES_ENGINE_PROVIDER == RulesEngineProvider.ZEN

    def test_default_medical_nlp(self):
        """Test default medical NLP provider is MedCAT."""
        settings = ClaimsSettings()
        assert settings.MEDICAL_NLP_PRIMARY_PROVIDER == MedicalNLPProvider.MEDCAT

    def test_default_currency_provider(self):
        """Test default currency provider is fawazahmed."""
        settings = ClaimsSettings()
        assert settings.CURRENCY_PRIMARY_PROVIDER == CurrencyProvider.FAWAZAHMED

    def test_default_coding_standard(self):
        """Test default coding standard is US."""
        settings = ClaimsSettings()
        assert settings.DEFAULT_CODING_STANDARD == CodingStandard.US

    def test_default_network_type(self):
        """Test default network type is PPO."""
        settings = ClaimsSettings()
        assert settings.DEFAULT_NETWORK_TYPE == NetworkType.PPO


class TestConfidenceThresholds:
    """Tests for confidence threshold configuration."""

    def test_llm_confidence_threshold_default(self):
        """Test default LLM confidence threshold."""
        settings = ClaimsSettings()
        assert settings.LLM_CONFIDENCE_THRESHOLD == 0.85

    def test_ocr_confidence_threshold_default(self):
        """Test default OCR confidence threshold."""
        settings = ClaimsSettings()
        assert settings.OCR_CONFIDENCE_THRESHOLD == 0.90

    def test_fwa_risk_threshold_default(self):
        """Test default FWA risk threshold."""
        settings = ClaimsSettings()
        assert settings.FWA_RISK_THRESHOLD == 0.6


class TestTimeoutConfiguration:
    """Tests for timeout configuration."""

    def test_document_processing_timeout(self):
        """Test document processing timeout default."""
        settings = ClaimsSettings()
        assert settings.DOCUMENT_PROCESSING_TIMEOUT_SECONDS == 300

    def test_claim_processing_timeout(self):
        """Test claim processing timeout default."""
        settings = ClaimsSettings()
        assert settings.CLAIM_PROCESSING_TIMEOUT_SECONDS == 60

    def test_ocr_timeout(self):
        """Test OCR timeout default."""
        settings = ClaimsSettings()
        assert settings.OCR_TIMEOUT_SECONDS == 30

    def test_llm_timeout(self):
        """Test LLM timeout default."""
        settings = ClaimsSettings()
        assert settings.LLM_TIMEOUT_SECONDS == 60


class TestCacheConfiguration:
    """Tests for cache TTL configuration."""

    def test_policy_cache_ttl(self):
        """Test policy cache TTL default."""
        settings = ClaimsSettings()
        assert settings.POLICY_CACHE_TTL_SECONDS == 300

    def test_benefit_cache_ttl(self):
        """Test benefit cache TTL default."""
        settings = ClaimsSettings()
        assert settings.BENEFIT_CACHE_TTL_SECONDS == 600

    def test_ocr_result_cache_ttl(self):
        """Test OCR result cache TTL default."""
        settings = ClaimsSettings()
        assert settings.OCR_RESULT_CACHE_TTL_SECONDS == 86400

    def test_currency_cache_ttl(self):
        """Test currency cache TTL default."""
        settings = ClaimsSettings()
        assert settings.CURRENCY_CACHE_TTL_SECONDS == 3600


class TestDemoModeConfiguration:
    """Tests for demo mode configuration."""

    def test_auto_load_demo_data_default(self):
        """Test auto-load demo data default."""
        settings = ClaimsSettings()
        assert settings.AUTO_LOAD_DEMO_DATA is True

    def test_demo_data_path_default(self):
        """Test demo data path default."""
        settings = ClaimsSettings()
        assert settings.DEMO_DATA_PATH == "demo_data"

    def test_payment_simulation_enabled_default(self):
        """Test payment simulation enabled default."""
        settings = ClaimsSettings()
        assert settings.PAYMENT_SIMULATION_ENABLED is True

    def test_payment_simulation_delay_default(self):
        """Test payment simulation delay default."""
        settings = ClaimsSettings()
        assert settings.PAYMENT_SIMULATION_DELAY_MS == 5000

    def test_payment_simulation_failure_rate_default(self):
        """Test payment simulation failure rate default."""
        settings = ClaimsSettings()
        assert settings.PAYMENT_SIMULATION_FAILURE_RATE == 0.02


class TestAuditConfiguration:
    """Tests for audit configuration."""

    def test_audit_enabled_default(self):
        """Test audit enabled default."""
        settings = ClaimsSettings()
        assert settings.AUDIT_ENABLED is True

    def test_audit_retention_years_default(self):
        """Test audit retention years default (HIPAA: 7 years)."""
        settings = ClaimsSettings()
        assert settings.AUDIT_RETENTION_YEARS == 7

    def test_audit_phi_redaction_default(self):
        """Test audit PHI redaction default."""
        settings = ClaimsSettings()
        assert settings.AUDIT_PHI_REDACTION is True


class TestComputedProperties:
    """Tests for computed properties."""

    def test_is_demo_mode_property(self):
        """Test is_demo_mode computed property."""
        settings = ClaimsSettings()
        assert settings.is_demo_mode is True
        assert settings.is_live_mode is False

    def test_paddleocr_languages_list_property(self):
        """Test paddleocr_languages_list computed property."""
        settings = ClaimsSettings()
        languages = settings.paddleocr_languages_list
        assert isinstance(languages, list)
        assert "en" in languages
        assert "ar" in languages


class TestProviderConfiguration:
    """Tests for AI/ML provider configuration."""

    def test_ollama_base_url_default(self):
        """Test Ollama base URL default."""
        settings = ClaimsSettings()
        assert settings.OLLAMA_BASE_URL == "http://localhost:11434"

    def test_ollama_model_default(self):
        """Test Ollama model default."""
        settings = ClaimsSettings()
        assert settings.OLLAMA_MODEL == "qwen2.5-vl:7b"

    def test_ollama_medical_model_default(self):
        """Test Ollama medical model default."""
        settings = ClaimsSettings()
        assert settings.OLLAMA_MEDICAL_MODEL == "biomistral:7b"

    def test_libretranslate_url_default(self):
        """Test LibreTranslate URL default."""
        settings = ClaimsSettings()
        assert settings.LIBRETRANSLATE_URL == "http://localhost:5000"

    def test_fallback_on_error_defaults(self):
        """Test fallback on error defaults are enabled."""
        settings = ClaimsSettings()
        assert settings.LLM_FALLBACK_ON_ERROR is True
        assert settings.OCR_FALLBACK_ON_ERROR is True


class TestFeatureFlags:
    """Tests for feature flag configuration."""

    def test_auto_adjudication_enabled_default(self):
        """Test auto-adjudication enabled default."""
        settings = ClaimsSettings()
        assert settings.AUTO_ADJUDICATION_ENABLED is True

    def test_fwa_detection_enabled_default(self):
        """Test FWA detection enabled default."""
        settings = ClaimsSettings()
        assert settings.FWA_DETECTION_ENABLED is True

    def test_admin_portal_enabled_default(self):
        """Test admin portal enabled default."""
        settings = ClaimsSettings()
        assert settings.ADMIN_PORTAL_ENABLED is True

    def test_admin_portal_port_default(self):
        """Test admin portal port default."""
        settings = ClaimsSettings()
        assert settings.ADMIN_PORTAL_PORT == 8501
