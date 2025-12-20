"""
Provider Gateway Module for Claims Processing System.

This module implements the Strategy Pattern for provider abstraction,
allowing seamless switching between open-source and commercial providers.
"""

from src.gateways.base import (
    BaseGateway,
    GatewayConfig,
    GatewayResult,
    GatewayError,
    ProviderHealth,
    ProviderUnavailableError,
    ProviderTimeoutError,
    ProviderRateLimitError,
)
from src.gateways.llm_gateway import (
    LLMGateway,
    LLMRequest,
    LLMResponse,
    LLMMessage,
    MessageRole,
    ImageContent,
    get_llm_gateway,
)
from src.gateways.ocr_gateway import (
    OCRGateway,
    OCRRequest,
    OCRResponse,
    OCRTextBlock,
    OCRBoundingBox,
    OCRTableData,
    OCRTableCell,
    get_ocr_gateway,
)
from src.gateways.translation_gateway import (
    TranslationGateway,
    TranslationRequest,
    TranslationResponse,
    get_translation_gateway,
)
from src.gateways.rules_gateway import (
    RulesGateway,
    RulesRequest,
    RulesResponse,
    RuleContext,
    RuleCategory,
    get_rules_gateway,
)
from src.gateways.medical_nlp_gateway import (
    MedicalNLPGateway,
    MedicalNLPRequest,
    MedicalNLPResponse,
    MedicalEntity,
    MedicalConcept,
    EntityType,
    CodeSystem,
    get_medical_nlp_gateway,
)
from src.gateways.currency_gateway import (
    CurrencyGateway,
    CurrencyRequest,
    CurrencyResponse,
    ExchangeRate,
    get_currency_gateway,
)

# Search Gateway (Typesense)
# Source: Design Document 04_validation_engine_comprehensive_design.md
from src.gateways.search_gateway import (
    SearchGateway,
    SearchConfig,
    SearchCollection,
    get_search_gateway,
    initialize_search_gateway,
)

__all__ = [
    # Base
    "BaseGateway",
    "GatewayConfig",
    "GatewayResult",
    "GatewayError",
    "ProviderHealth",
    "ProviderUnavailableError",
    "ProviderTimeoutError",
    "ProviderRateLimitError",
    # LLM
    "LLMGateway",
    "LLMRequest",
    "LLMResponse",
    "LLMMessage",
    "MessageRole",
    "ImageContent",
    "get_llm_gateway",
    # OCR
    "OCRGateway",
    "OCRRequest",
    "OCRResponse",
    "OCRTextBlock",
    "OCRBoundingBox",
    "OCRTableData",
    "OCRTableCell",
    "get_ocr_gateway",
    # Translation
    "TranslationGateway",
    "TranslationRequest",
    "TranslationResponse",
    "get_translation_gateway",
    # Rules
    "RulesGateway",
    "RulesRequest",
    "RulesResponse",
    "RuleContext",
    "RuleCategory",
    "get_rules_gateway",
    # Medical NLP
    "MedicalNLPGateway",
    "MedicalNLPRequest",
    "MedicalNLPResponse",
    "MedicalEntity",
    "MedicalConcept",
    "EntityType",
    "CodeSystem",
    "get_medical_nlp_gateway",
    # Currency
    "CurrencyGateway",
    "CurrencyRequest",
    "CurrencyResponse",
    "ExchangeRate",
    "get_currency_gateway",
    # Search (Typesense)
    "SearchGateway",
    "SearchConfig",
    "SearchCollection",
    "get_search_gateway",
    "initialize_search_gateway",
]
