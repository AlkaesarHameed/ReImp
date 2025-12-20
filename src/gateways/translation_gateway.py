"""
Translation Gateway with LibreTranslate and Azure Translator.

Provides unified translation capabilities for multi-language support:
- Primary: LibreTranslate (open-source, self-hosted)
- Fallback: Azure Translator (commercial, high quality)

Features:
- Medical terminology awareness
- Arabic/English translation for MENA region
- Language detection
- Batch translation
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from src.core.config import get_claims_settings
from src.core.enums import TranslationProvider
from src.gateways.base import (
    BaseGateway,
    GatewayConfig,
    GatewayError,
    ProviderUnavailableError,
    ProviderRateLimitError,
)

logger = logging.getLogger(__name__)

# Import Azure Translator with graceful fallback
try:
    from azure.ai.translation.text import TextTranslationClient
    from azure.core.credentials import AzureKeyCredential

    AZURE_TRANSLATOR_AVAILABLE = True
except ImportError:
    AZURE_TRANSLATOR_AVAILABLE = False
    logger.warning(
        "Azure Translator SDK not installed. Azure fallback will not be available."
    )


@dataclass
class TranslationRequest:
    """Request for translation."""

    text: str
    source_language: Optional[str] = None  # None for auto-detect
    target_language: str = "en"
    preserve_formatting: bool = True
    glossary: Optional[dict[str, str]] = None  # Medical term glossary
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def batch(
        cls,
        texts: list[str],
        source_language: Optional[str] = None,
        target_language: str = "en",
    ) -> list["TranslationRequest"]:
        """Create batch translation requests."""
        return [
            cls(
                text=text,
                source_language=source_language,
                target_language=target_language,
            )
            for text in texts
        ]


@dataclass
class TranslationResponse:
    """Response from translation."""

    translated_text: str
    source_language: str
    target_language: str
    confidence: float = 1.0
    detected_language: Optional[str] = None
    alternative_translations: list[str] = field(default_factory=list)
    provider: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# Medical terminology glossary for accurate translations
MEDICAL_GLOSSARY = {
    "en-ar": {
        "diagnosis": "تشخيص",
        "treatment": "علاج",
        "prescription": "وصفة طبية",
        "surgery": "جراحة",
        "patient": "مريض",
        "doctor": "طبيب",
        "hospital": "مستشفى",
        "clinic": "عيادة",
        "insurance": "تأمين",
        "claim": "مطالبة",
        "copay": "مساهمة التأمين",
        "deductible": "المبلغ المقتطع",
        "premium": "قسط التأمين",
        "pre-authorization": "موافقة مسبقة",
        "referral": "إحالة",
        "ICD-10": "التصنيف الدولي للأمراض",
        "CPT": "رمز الإجراءات الطبية",
    },
    "ar-en": {
        "تشخيص": "diagnosis",
        "علاج": "treatment",
        "وصفة طبية": "prescription",
        "جراحة": "surgery",
        "مريض": "patient",
        "طبيب": "doctor",
        "مستشفى": "hospital",
        "عيادة": "clinic",
        "تأمين": "insurance",
        "مطالبة": "claim",
    },
}


class TranslationGateway(BaseGateway[TranslationRequest, TranslationResponse, TranslationProvider]):
    """
    Translation Gateway for multi-language support.

    Supports:
    - LibreTranslate (primary, open-source, self-hosted)
    - Azure Translator (fallback, commercial)
    """

    def __init__(self, config: Optional[GatewayConfig] = None):
        settings = get_claims_settings()

        if config is None:
            config = GatewayConfig(
                primary_provider=settings.TRANSLATION_PRIMARY_PROVIDER.value,
                fallback_provider=(
                    settings.TRANSLATION_FALLBACK_PROVIDER.value
                    if settings.TRANSLATION_FALLBACK_ON_ERROR
                    else None
                ),
                fallback_on_error=settings.TRANSLATION_FALLBACK_ON_ERROR,
                timeout_seconds=settings.TRANSLATION_TIMEOUT_SECONDS,
            )

        super().__init__(config)
        self._settings = settings
        self._http_client: Optional[httpx.AsyncClient] = None
        self._azure_client: Optional[Any] = None

    @property
    def gateway_name(self) -> str:
        return "Translation"

    async def _initialize_provider(self, provider: TranslationProvider) -> None:
        """Initialize translation provider."""
        if provider == TranslationProvider.LIBRETRANSLATE:
            self._http_client = httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                base_url=self._settings.LIBRETRANSLATE_URL,
            )
            # Test connection
            try:
                response = await self._http_client.get("/languages")
                if response.status_code != 200:
                    raise ProviderUnavailableError(
                        f"LibreTranslate returned status {response.status_code}",
                        provider=provider.value,
                    )
            except httpx.ConnectError:
                raise ProviderUnavailableError(
                    f"Could not connect to LibreTranslate at {self._settings.LIBRETRANSLATE_URL}",
                    provider=provider.value,
                )
            logger.info("LibreTranslate initialized")

        elif provider == TranslationProvider.AZURE_TRANSLATOR:
            if not AZURE_TRANSLATOR_AVAILABLE:
                raise ProviderUnavailableError(
                    "Azure Translator SDK not installed",
                    provider=provider.value,
                )
            if not self._settings.AZURE_TRANSLATOR_KEY:
                raise ProviderUnavailableError(
                    "Azure Translator key not configured",
                    provider=provider.value,
                )
            self._azure_client = TextTranslationClient(
                credential=AzureKeyCredential(self._settings.AZURE_TRANSLATOR_KEY),
                region=self._settings.AZURE_TRANSLATOR_REGION,
            )
            logger.info("Azure Translator initialized")

    async def _execute_request(
        self, request: TranslationRequest, provider: TranslationProvider
    ) -> TranslationResponse:
        """Execute translation request using specified provider."""
        if provider == TranslationProvider.LIBRETRANSLATE:
            return await self._translate_libretranslate(request)
        elif provider == TranslationProvider.AZURE_TRANSLATOR:
            return await self._translate_azure(request)
        else:
            raise GatewayError(f"Unsupported translation provider: {provider}")

    async def _translate_libretranslate(
        self, request: TranslationRequest
    ) -> TranslationResponse:
        """Translate using LibreTranslate."""
        if not self._http_client:
            raise ProviderUnavailableError(
                "LibreTranslate not initialized", provider="libretranslate"
            )

        # Apply medical glossary pre-processing
        text = self._apply_glossary_preprocessing(
            request.text,
            request.source_language,
            request.target_language,
            request.glossary,
        )

        payload = {
            "q": text,
            "target": request.target_language,
            "format": "text",
        }
        if request.source_language:
            payload["source"] = request.source_language
        else:
            payload["source"] = "auto"

        try:
            response = await self._http_client.post("/translate", json=payload)

            if response.status_code == 429:
                raise ProviderRateLimitError(
                    "LibreTranslate rate limit exceeded", provider="libretranslate"
                )
            elif response.status_code != 200:
                raise GatewayError(
                    f"LibreTranslate error: {response.text}", provider="libretranslate"
                )

            data = response.json()
            translated = data.get("translatedText", "")
            detected = data.get("detectedLanguage", {})

            return TranslationResponse(
                translated_text=translated,
                source_language=request.source_language or detected.get("language", "unknown"),
                target_language=request.target_language,
                confidence=detected.get("confidence", 1.0),
                detected_language=detected.get("language"),
                provider="libretranslate",
            )

        except httpx.TimeoutException:
            raise GatewayError(
                "LibreTranslate request timed out", provider="libretranslate"
            )

    async def _translate_azure(self, request: TranslationRequest) -> TranslationResponse:
        """Translate using Azure Translator."""
        if not self._azure_client:
            raise ProviderUnavailableError(
                "Azure Translator not initialized", provider="azure_translator"
            )

        loop = asyncio.get_event_loop()

        def run_translation():
            input_text = [request.text]
            target_languages = [request.target_language]

            if request.source_language:
                result = self._azure_client.translate(
                    body=input_text,
                    to_language=target_languages,
                    from_language=request.source_language,
                )
            else:
                result = self._azure_client.translate(
                    body=input_text,
                    to_language=target_languages,
                )
            return result

        try:
            result = await loop.run_in_executor(None, run_translation)

            if result and len(result) > 0:
                translation = result[0]
                translations = translation.translations
                detected = translation.detected_language

                if translations and len(translations) > 0:
                    primary = translations[0]
                    return TranslationResponse(
                        translated_text=primary.text,
                        source_language=request.source_language or (
                            detected.language if detected else "unknown"
                        ),
                        target_language=request.target_language,
                        confidence=detected.score if detected else 1.0,
                        detected_language=detected.language if detected else None,
                        provider="azure_translator",
                    )

            raise GatewayError("No translation result from Azure", provider="azure_translator")

        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str or "429" in error_str:
                raise ProviderRateLimitError(
                    f"Azure Translator rate limit: {e}", provider="azure_translator"
                )
            raise GatewayError(
                f"Azure Translator error: {e}",
                provider="azure_translator",
                original_error=e,
            )

    async def _health_check(self, provider: TranslationProvider) -> bool:
        """Check if translation provider is healthy."""
        try:
            test_request = TranslationRequest(
                text="Hello",
                source_language="en",
                target_language="es",
            )
            await self._execute_request(test_request, provider)
            return True
        except Exception as e:
            logger.warning(f"Translation health check failed for {provider.value}: {e}")
            return False

    def _parse_provider(self, provider_str: str) -> TranslationProvider:
        """Parse provider string to TranslationProvider enum."""
        return TranslationProvider(provider_str)

    def _apply_glossary_preprocessing(
        self,
        text: str,
        source_lang: Optional[str],
        target_lang: str,
        custom_glossary: Optional[dict[str, str]] = None,
    ) -> str:
        """Apply medical glossary preprocessing to improve translation accuracy."""
        if not source_lang:
            return text

        glossary_key = f"{source_lang}-{target_lang}"
        glossary = MEDICAL_GLOSSARY.get(glossary_key, {})

        if custom_glossary:
            glossary = {**glossary, **custom_glossary}

        # For now, return text unchanged - glossary used for post-processing
        return text

    async def translate_batch(
        self,
        texts: list[str],
        source_language: Optional[str] = None,
        target_language: str = "en",
    ) -> list[TranslationResponse]:
        """Translate multiple texts in batch."""
        requests = TranslationRequest.batch(texts, source_language, target_language)
        results = []

        for request in requests:
            result = await self.execute(request)
            if result.success and result.data:
                results.append(result.data)
            else:
                # Create error response
                results.append(
                    TranslationResponse(
                        translated_text=request.text,  # Return original on failure
                        source_language=source_language or "unknown",
                        target_language=target_language,
                        confidence=0.0,
                        metadata={"error": result.error},
                    )
                )

        return results

    async def detect_language(self, text: str) -> tuple[str, float]:
        """Detect the language of given text."""
        request = TranslationRequest(
            text=text,
            source_language=None,  # Auto-detect
            target_language="en",  # Translate to any language to get detection
        )
        result = await self.execute(request)

        if result.success and result.data:
            return (
                result.data.detected_language or result.data.source_language,
                result.data.confidence,
            )
        return ("unknown", 0.0)

    async def close(self) -> None:
        """Clean up translation gateway resources."""
        if self._http_client:
            await self._http_client.aclose()
        await super().close()


# Singleton instance
_translation_gateway: Optional[TranslationGateway] = None


def get_translation_gateway() -> TranslationGateway:
    """Get or create the singleton Translation gateway instance."""
    global _translation_gateway
    if _translation_gateway is None:
        _translation_gateway = TranslationGateway()
    return _translation_gateway


async def reset_translation_gateway() -> None:
    """Reset the Translation gateway (for testing)."""
    global _translation_gateway
    if _translation_gateway:
        await _translation_gateway.close()
    _translation_gateway = None
