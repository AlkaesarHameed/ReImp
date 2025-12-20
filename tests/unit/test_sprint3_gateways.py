"""
Unit tests for Sprint 3 gateways (Translation, Rules, Medical NLP, Currency).
"""

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.enums import (
    TranslationProvider,
    RulesEngineProvider,
    MedicalNLPProvider,
    CurrencyProvider,
)
from src.gateways.translation_gateway import (
    TranslationGateway,
    TranslationRequest,
    TranslationResponse,
    MEDICAL_GLOSSARY,
)
from src.gateways.rules_gateway import (
    RulesGateway,
    RulesRequest,
    RulesResponse,
    RuleContext,
    RuleCategory,
    RuleType,
    RuleTrace,
)
from src.gateways.medical_nlp_gateway import (
    MedicalNLPGateway,
    MedicalNLPRequest,
    MedicalNLPResponse,
    MedicalEntity,
    MedicalConcept,
    EntityType,
    CodeSystem,
)
from src.gateways.currency_gateway import (
    CurrencyGateway,
    CurrencyRequest,
    CurrencyResponse,
    ExchangeRate,
    RateCache,
    SUPPORTED_CURRENCIES,
)


# ============== Translation Gateway Tests ==============


class TestTranslationRequest:
    """Tests for TranslationRequest class."""

    def test_basic_request(self):
        """Test basic translation request."""
        request = TranslationRequest(
            text="Hello World",
            source_language="en",
            target_language="ar",
        )
        assert request.text == "Hello World"
        assert request.source_language == "en"
        assert request.target_language == "ar"

    def test_auto_detect_request(self):
        """Test request with auto language detection."""
        request = TranslationRequest(
            text="مرحبا",
            target_language="en",
        )
        assert request.source_language is None
        assert request.target_language == "en"

    def test_batch_creation(self):
        """Test batch request creation."""
        texts = ["Hello", "World", "Test"]
        requests = TranslationRequest.batch(texts, "en", "ar")
        assert len(requests) == 3
        assert all(r.source_language == "en" for r in requests)


class TestTranslationResponse:
    """Tests for TranslationResponse class."""

    def test_response_creation(self):
        """Test response creation."""
        response = TranslationResponse(
            translated_text="مرحبا",
            source_language="en",
            target_language="ar",
            confidence=0.95,
        )
        assert response.translated_text == "مرحبا"
        assert response.confidence == 0.95


class TestMedicalGlossary:
    """Tests for medical terminology glossary."""

    def test_english_to_arabic_terms(self):
        """Test English to Arabic medical terms."""
        glossary = MEDICAL_GLOSSARY.get("en-ar", {})
        assert "diagnosis" in glossary
        assert "treatment" in glossary
        assert "patient" in glossary

    def test_arabic_to_english_terms(self):
        """Test Arabic to English medical terms."""
        glossary = MEDICAL_GLOSSARY.get("ar-en", {})
        assert "تشخيص" in glossary
        assert glossary["تشخيص"] == "diagnosis"


# ============== Rules Gateway Tests ==============


class TestRuleContext:
    """Tests for RuleContext class."""

    def test_empty_context(self):
        """Test empty rule context."""
        context = RuleContext()
        result = context.to_dict()
        assert result == {}

    def test_full_context(self):
        """Test context with all fields."""
        context = RuleContext(
            claim={"id": "CLM001", "amount": 1000},
            member={"id": "MBR001", "status": "active"},
            policy={"id": "POL001", "type": "gold"},
        )
        result = context.to_dict()
        assert "claim" in result
        assert "member" in result
        assert "policy" in result
        assert result["claim"]["id"] == "CLM001"

    def test_custom_context(self):
        """Test context with custom fields."""
        context = RuleContext(custom={"custom_field": "custom_value"})
        result = context.to_dict()
        assert result["custom_field"] == "custom_value"


class TestRulesRequest:
    """Tests for RulesRequest class."""

    def test_basic_request(self):
        """Test basic rules request."""
        context = RuleContext(claim={"id": "CLM001"})
        request = RulesRequest(
            rule_id="eligibility_check",
            context=context,
            rule_category=RuleCategory.ELIGIBILITY,
        )
        assert request.rule_id == "eligibility_check"
        assert request.rule_category == RuleCategory.ELIGIBILITY


class TestRulesResponse:
    """Tests for RulesResponse class."""

    def test_approved_decision(self):
        """Test approved decision detection."""
        response = RulesResponse(
            result={"decision": "approve"},
            rule_id="test_rule",
            decision="approve",
        )
        assert response.approved is True
        assert response.denied is False

    def test_denied_decision(self):
        """Test denied decision detection."""
        response = RulesResponse(
            result={"decision": "deny"},
            rule_id="test_rule",
            decision="deny",
        )
        assert response.approved is False
        assert response.denied is True


class TestRuleCategoryEnum:
    """Tests for RuleCategory enum."""

    def test_rule_categories(self):
        """Test all rule categories exist."""
        assert RuleCategory.ADJUDICATION == "adjudication"
        assert RuleCategory.ELIGIBILITY == "eligibility"
        assert RuleCategory.FWA_DETECTION == "fwa_detection"
        assert RuleCategory.PRIOR_AUTH == "prior_authorization"


# ============== Medical NLP Gateway Tests ==============


class TestMedicalEntity:
    """Tests for MedicalEntity class."""

    def test_entity_creation(self):
        """Test entity creation."""
        entity = MedicalEntity(
            text="diabetes mellitus",
            entity_type=EntityType.DIAGNOSIS,
            start_offset=10,
            end_offset=28,
            confidence=0.95,
            codes={CodeSystem.ICD10_CM.value: "E11.9"},
        )
        assert entity.text == "diabetes mellitus"
        assert entity.entity_type == EntityType.DIAGNOSIS
        assert entity.confidence == 0.95

    def test_entity_to_dict(self):
        """Test entity serialization."""
        entity = MedicalEntity(
            text="aspirin",
            entity_type=EntityType.MEDICATION,
            start_offset=0,
            end_offset=7,
            confidence=0.9,
        )
        result = entity.to_dict()
        assert result["text"] == "aspirin"
        assert result["entity_type"] == "medication"

    def test_negated_entity(self):
        """Test negated entity."""
        entity = MedicalEntity(
            text="chest pain",
            entity_type=EntityType.SYMPTOM,
            start_offset=0,
            end_offset=10,
            confidence=0.9,
            negated=True,
        )
        assert entity.negated is True


class TestMedicalConcept:
    """Tests for MedicalConcept class."""

    def test_concept_creation(self):
        """Test concept creation."""
        concept = MedicalConcept(
            cui="C0011849",
            preferred_name="Diabetes Mellitus",
            semantic_types=["T047"],
            synonyms=["DM", "Sugar diabetes"],
        )
        assert concept.cui == "C0011849"
        assert concept.preferred_name == "Diabetes Mellitus"


class TestMedicalNLPRequest:
    """Tests for MedicalNLPRequest class."""

    def test_basic_request(self):
        """Test basic NLP request."""
        request = MedicalNLPRequest(text="Patient has type 2 diabetes")
        assert request.detect_entities is True
        assert request.link_concepts is True


class TestMedicalNLPResponse:
    """Tests for MedicalNLPResponse class."""

    def test_get_diagnoses(self):
        """Test filtering diagnosis entities."""
        entities = [
            MedicalEntity(
                text="diabetes",
                entity_type=EntityType.DIAGNOSIS,
                start_offset=0, end_offset=8, confidence=0.9,
            ),
            MedicalEntity(
                text="aspirin",
                entity_type=EntityType.MEDICATION,
                start_offset=20, end_offset=27, confidence=0.9,
            ),
        ]
        response = MedicalNLPResponse(
            entities=entities,
            concepts=[],
            text="test",
            confidence=0.9,
        )
        diagnoses = response.get_diagnoses()
        assert len(diagnoses) == 1
        assert diagnoses[0].text == "diabetes"

    def test_get_icd10_codes(self):
        """Test extracting ICD-10 codes."""
        entities = [
            MedicalEntity(
                text="diabetes",
                entity_type=EntityType.DIAGNOSIS,
                start_offset=0, end_offset=8, confidence=0.9,
                codes={CodeSystem.ICD10_CM.value: "E11.9"},
            ),
            MedicalEntity(
                text="hypertension",
                entity_type=EntityType.DIAGNOSIS,
                start_offset=20, end_offset=32, confidence=0.9,
                codes={CodeSystem.ICD10_CM.value: "I10"},
            ),
        ]
        response = MedicalNLPResponse(
            entities=entities,
            concepts=[],
            text="test",
            confidence=0.9,
        )
        codes = response.get_icd10_codes()
        assert "E11.9" in codes
        assert "I10" in codes


class TestEntityType:
    """Tests for EntityType enum."""

    def test_entity_types(self):
        """Test all entity types exist."""
        assert EntityType.DIAGNOSIS == "diagnosis"
        assert EntityType.PROCEDURE == "procedure"
        assert EntityType.MEDICATION == "medication"
        assert EntityType.ANATOMY == "anatomy"


class TestCodeSystem:
    """Tests for CodeSystem enum."""

    def test_code_systems(self):
        """Test all code systems exist."""
        assert CodeSystem.ICD10_CM == "icd10_cm"
        assert CodeSystem.CPT == "cpt"
        assert CodeSystem.SNOMED_CT == "snomed_ct"
        assert CodeSystem.HCPCS == "hcpcs"


# ============== Currency Gateway Tests ==============


class TestExchangeRate:
    """Tests for ExchangeRate class."""

    def test_rate_creation(self):
        """Test exchange rate creation."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            timestamp=datetime.now(timezone.utc),
            source="test",
        )
        assert rate.from_currency == "USD"
        assert rate.to_currency == "EUR"
        assert rate.rate == Decimal("0.85")

    def test_convert(self):
        """Test currency conversion."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            timestamp=datetime.now(timezone.utc),
            source="test",
        )
        result = rate.convert(Decimal("100"))
        assert result == Decimal("85.00")

    def test_convert_inverse(self):
        """Test inverse currency conversion."""
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            timestamp=datetime.now(timezone.utc),
            source="test",
            inverse_rate=Decimal("1.1765"),
        )
        result = rate.convert_inverse(Decimal("100"))
        assert result == Decimal("117.65")


class TestCurrencyRequest:
    """Tests for CurrencyRequest class."""

    def test_basic_request(self):
        """Test basic currency request."""
        request = CurrencyRequest(
            amount=Decimal("100"),
            from_currency="USD",
            to_currency="AED",
        )
        assert request.amount == Decimal("100")
        assert request.from_currency == "USD"
        assert request.to_currency == "AED"

    def test_historical_request(self):
        """Test historical rate request."""
        request = CurrencyRequest(
            amount=Decimal("100"),
            from_currency="USD",
            to_currency="EUR",
            rate_date=date(2024, 1, 15),
        )
        assert request.rate_date == date(2024, 1, 15)


class TestCurrencyResponse:
    """Tests for CurrencyResponse class."""

    def test_response_creation(self):
        """Test response creation."""
        response = CurrencyResponse(
            original_amount=Decimal("100"),
            converted_amount=Decimal("367.50"),
            from_currency="USD",
            to_currency="AED",
            exchange_rate=Decimal("3.675"),
            rate_date=date.today(),
            provider="test",
        )
        assert response.original_amount == Decimal("100")
        assert response.converted_amount == Decimal("367.50")


class TestRateCache:
    """Tests for RateCache class."""

    def test_cache_set_get(self):
        """Test cache set and get."""
        cache = RateCache(ttl_seconds=3600)
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            timestamp=datetime.now(timezone.utc),
            source="test",
        )
        cache.set("usd_eur", rate)
        result = cache.get("usd_eur")
        assert result is not None
        assert result.rate == Decimal("0.85")

    def test_cache_miss(self):
        """Test cache miss."""
        cache = RateCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_clear(self):
        """Test cache clear."""
        cache = RateCache()
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            timestamp=datetime.now(timezone.utc),
            source="test",
        )
        cache.set("usd_eur", rate)
        cache.clear()
        result = cache.get("usd_eur")
        assert result is None


class TestSupportedCurrencies:
    """Tests for supported currencies."""

    def test_usd_supported(self):
        """Test USD is supported."""
        assert "USD" in SUPPORTED_CURRENCIES

    def test_mena_currencies(self):
        """Test MENA region currencies are supported."""
        mena_currencies = ["AED", "SAR", "EGP", "KWD", "BHD", "OMR", "QAR"]
        for currency in mena_currencies:
            assert currency in SUPPORTED_CURRENCIES


class TestCurrencyProviderEnum:
    """Tests for CurrencyProvider enum."""

    def test_provider_values(self):
        """Test currency provider enum values."""
        assert CurrencyProvider.FAWAZAHMED == "fawazahmed"
        assert CurrencyProvider.EXCHANGERATE == "exchangerate"
        assert CurrencyProvider.FIXER == "fixer"
