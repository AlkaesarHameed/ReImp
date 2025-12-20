"""
Internationalization Orchestrator Service.
Source: Design Document Section 4.3 - Internationalization
Verified: 2025-12-18

Orchestrates translation, currency conversion, and localization.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.services.i18n.translation import (
    SupportedLanguage,
    TextDirection,
    TranslationService,
    TranslatedText,
    DocumentTranslation,
    get_translation_service,
)
from src.services.i18n.currency import (
    SupportedCurrency,
    CurrencyConversion,
    CurrencyConversionService,
    get_currency_service,
)
from src.services.i18n.localization import (
    LocalizationService,
    LocaleConfig,
    get_localization_service,
)


class LocalizedClaim(BaseModel):
    """A fully localized claim for display."""

    claim_id: str
    display_language: SupportedLanguage
    text_direction: TextDirection

    # Localized status
    status: str
    status_localized: str

    # Dates in locale format
    service_date: str
    submission_date: Optional[str] = None

    # Amounts in display currency
    total_charged: str
    allowed_amount: Optional[str] = None
    paid_amount: Optional[str] = None
    patient_responsibility: Optional[str] = None

    # Currency info
    display_currency: SupportedCurrency
    original_currency: Optional[SupportedCurrency] = None
    currency_converted: bool = False

    # Localized strings
    labels: dict[str, str] = Field(default_factory=dict)

    # Original data
    original_data: dict = Field(default_factory=dict)


class I18nService:
    """
    Orchestrates internationalization services.

    Coordinates:
    1. Translation for text/documents
    2. Currency conversion for amounts
    3. Localization for UI strings and formatting
    """

    def __init__(
        self,
        translation_service: Optional[TranslationService] = None,
        currency_service: Optional[CurrencyConversionService] = None,
        localization_service: Optional[LocalizationService] = None,
    ):
        """
        Initialize I18nService.

        Args:
            translation_service: TranslationService instance
            currency_service: CurrencyConversionService instance
            localization_service: LocalizationService instance
        """
        self.translation = translation_service or get_translation_service()
        self.currency = currency_service or get_currency_service()
        self.localization = localization_service or get_localization_service()

    def set_locale(self, language: SupportedLanguage) -> None:
        """
        Set the current locale for all services.

        Args:
            language: Language to set
        """
        self.localization.set_language(language)

    def get_locale(self) -> SupportedLanguage:
        """Get current locale."""
        return self.localization.get_language()

    def get_locale_config(self) -> LocaleConfig:
        """Get current locale configuration."""
        return self.localization.get_locale_config()

    async def localize_claim(
        self,
        claim_data: dict,
        display_language: SupportedLanguage = SupportedLanguage.ENGLISH,
        display_currency: SupportedCurrency = SupportedCurrency.USD,
    ) -> LocalizedClaim:
        """
        Fully localize a claim for display.

        Args:
            claim_data: Raw claim data
            display_language: Language for UI display
            display_currency: Currency for amounts

        Returns:
            LocalizedClaim ready for display
        """
        self.set_locale(display_language)

        # Get text direction
        text_direction = self.localization.get_text_direction()

        # Localize status
        status = claim_data.get("status", "unknown")
        status_localized = self.localization.localize_claim_status(status)

        # Format dates
        service_date = claim_data.get("service_date")
        if isinstance(service_date, str):
            service_date = date.fromisoformat(service_date)
        service_date_formatted = (
            self.localization.format_date(service_date)
            if service_date else ""
        )

        submission_date = claim_data.get("submission_date")
        if submission_date:
            if isinstance(submission_date, str):
                submission_date = datetime.fromisoformat(submission_date)
            if isinstance(submission_date, datetime):
                submission_date_formatted = self.localization.format_datetime(submission_date)
            else:
                submission_date_formatted = self.localization.format_date(submission_date)
        else:
            submission_date_formatted = None

        # Convert and format amounts
        original_currency_str = claim_data.get("currency", "USD")
        try:
            original_currency = SupportedCurrency(original_currency_str)
        except ValueError:
            original_currency = SupportedCurrency.USD

        currency_converted = original_currency != display_currency

        # Format amounts
        async def format_amount(value: Any) -> Optional[str]:
            if value is None:
                return None
            amount = Decimal(str(value))
            if currency_converted:
                conversion = await self.currency.convert(
                    amount,
                    original_currency,
                    display_currency,
                )
                amount = conversion.converted_amount
            return self.currency.format_currency(amount, display_currency)

        total_charged = await format_amount(claim_data.get("total_charged"))
        allowed_amount = await format_amount(claim_data.get("allowed_amount"))
        paid_amount = await format_amount(claim_data.get("paid_amount"))
        patient_resp = await format_amount(claim_data.get("patient_responsibility"))

        # Get localized labels
        labels = {
            "claim_id": self.localization.t("claim.id"),
            "status": self.localization.t("claim.status"),
            "service_date": self.localization.t("claim.date"),
            "total_charged": self.localization.t("financial.charged"),
            "allowed_amount": self.localization.t("financial.allowed"),
            "paid_amount": self.localization.t("financial.paid"),
            "patient_responsibility": self.localization.t("financial.patient_resp"),
            "provider": self.localization.t("claim.provider"),
            "member": self.localization.t("claim.member"),
        }

        return LocalizedClaim(
            claim_id=claim_data.get("claim_id", ""),
            display_language=display_language,
            text_direction=text_direction,
            status=status,
            status_localized=status_localized,
            service_date=service_date_formatted,
            submission_date=submission_date_formatted,
            total_charged=total_charged or "",
            allowed_amount=allowed_amount,
            paid_amount=paid_amount,
            patient_responsibility=patient_resp,
            display_currency=display_currency,
            original_currency=original_currency if currency_converted else None,
            currency_converted=currency_converted,
            labels=labels,
            original_data=claim_data,
        )

    async def translate_claim_notes(
        self,
        claim_data: dict,
        target_language: SupportedLanguage = SupportedLanguage.ARABIC,
    ) -> dict:
        """
        Translate claim notes and remarks.

        Args:
            claim_data: Claim data with text fields
            target_language: Target language for translation

        Returns:
            Claim data with translated fields
        """
        result = claim_data.copy()

        # Fields to translate
        text_fields = [
            "notes",
            "remarks",
            "denial_reason",
            "review_comments",
            "provider_notes",
        ]

        for field in text_fields:
            if field in result and result[field]:
                translation = await self.translation.translate_text(
                    result[field],
                    target_language=target_language,
                )
                result[f"{field}_translated"] = translation.translated_text
                result[f"{field}_original"] = result[field]

        return result

    async def prepare_claim_for_export(
        self,
        claim_data: dict,
        target_language: SupportedLanguage = SupportedLanguage.ENGLISH,
        target_currency: SupportedCurrency = SupportedCurrency.USD,
        include_translations: bool = True,
    ) -> dict:
        """
        Prepare claim for export with full localization.

        Args:
            claim_data: Raw claim data
            target_language: Language for export
            target_currency: Currency for amounts
            include_translations: Whether to include translated text

        Returns:
            Fully prepared claim data
        """
        result = claim_data.copy()

        # Convert currency
        if target_currency:
            result = await self.currency.convert_claim_amounts(
                result,
                target_currency,
            )

        # Translate if needed
        if include_translations:
            result = await self.translate_claim_notes(result, target_language)

        # Add metadata
        result["export_language"] = target_language.value
        result["export_currency"] = target_currency.value
        result["export_timestamp"] = datetime.utcnow().isoformat()

        return result

    def get_supported_languages(self) -> list[dict]:
        """Get list of supported languages."""
        return self.localization.get_available_languages()

    def get_supported_currencies(self) -> list[dict]:
        """Get list of supported currencies."""
        currencies = []
        for curr in self.currency.get_supported_currencies():
            info = self.currency.get_currency_info(curr)
            currencies.append(info)
        return currencies

    async def detect_document_language(
        self,
        content: str,
    ) -> tuple[SupportedLanguage, float]:
        """
        Detect the language of document content.

        Args:
            content: Document text

        Returns:
            Tuple of (detected_language, confidence)
        """
        return self.translation.detect_language(content)

    async def translate_document(
        self,
        content: str,
        source_language: Optional[SupportedLanguage] = None,
        target_language: SupportedLanguage = SupportedLanguage.ENGLISH,
    ) -> DocumentTranslation:
        """
        Translate document content.

        Args:
            content: Document text
            source_language: Source language (auto-detect if None)
            target_language: Target language

        Returns:
            DocumentTranslation result
        """
        return await self.translation.translate_document(
            content,
            source_language,
            target_language,
        )

    def get_ui_strings(
        self,
        language: Optional[SupportedLanguage] = None,
    ) -> dict[str, str]:
        """
        Get all UI strings for a language.

        Args:
            language: Language to get strings for

        Returns:
            Dictionary of UI strings
        """
        return self.localization.get_all_strings(language)

    def format_amount(
        self,
        amount: Decimal,
        currency: SupportedCurrency,
    ) -> str:
        """
        Format currency amount for display.

        Args:
            amount: Amount to format
            currency: Currency to use

        Returns:
            Formatted amount string
        """
        return self.currency.format_currency(amount, currency)

    def format_date(self, value: date) -> str:
        """Format date according to current locale."""
        return self.localization.format_date(value)

    def format_datetime(self, value: datetime) -> str:
        """Format datetime according to current locale."""
        return self.localization.format_datetime(value)

    def format_number(self, value: float | int | Decimal, decimals: int = 2) -> str:
        """Format number according to current locale."""
        return self.localization.format_number(value, decimals)


# =============================================================================
# Factory Functions
# =============================================================================


_i18n_service: Optional[I18nService] = None


def get_i18n_service() -> I18nService:
    """Get singleton I18nService instance."""
    global _i18n_service
    if _i18n_service is None:
        _i18n_service = I18nService()
    return _i18n_service


def create_i18n_service(
    translation_service: Optional[TranslationService] = None,
    currency_service: Optional[CurrencyConversionService] = None,
    localization_service: Optional[LocalizationService] = None,
) -> I18nService:
    """Create a new I18nService instance."""
    return I18nService(
        translation_service,
        currency_service,
        localization_service,
    )
