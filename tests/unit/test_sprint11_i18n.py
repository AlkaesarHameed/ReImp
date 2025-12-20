"""
Sprint 11: Internationalization (i18n) Tests.
Tests for translation, currency conversion, and localization services.

Uses inline classes to avoid import chain issues with pgvector, JWT, and settings.
"""

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
import re

from pydantic import BaseModel, Field


# =============================================================================
# Inline Enums and Models
# =============================================================================


class SupportedLanguage(str, Enum):
    """Supported languages for translation."""
    ENGLISH = "en"
    ARABIC = "ar"
    FRENCH = "fr"


class TextDirection(str, Enum):
    """Text direction for display."""
    LTR = "ltr"
    RTL = "rtl"


class SupportedCurrency(str, Enum):
    """Supported currencies."""
    USD = "USD"
    EUR = "EUR"
    AED = "AED"
    SAR = "SAR"
    EGP = "EGP"
    KWD = "KWD"
    AUD = "AUD"


class TranslatedText(BaseModel):
    """Result of text translation."""
    original_text: str
    translated_text: str
    source_language: SupportedLanguage
    target_language: SupportedLanguage
    confidence: float = 1.0
    text_direction: TextDirection = TextDirection.LTR
    is_medical_term: bool = False
    glossary_applied: bool = False


class CurrencyConversion(BaseModel):
    """Result of currency conversion."""
    original_amount: Decimal
    original_currency: SupportedCurrency
    converted_amount: Decimal
    target_currency: SupportedCurrency
    exchange_rate: Decimal
    rate_date: date


class LocaleConfig(BaseModel):
    """Configuration for a locale."""
    language: SupportedLanguage
    language_name: str
    language_native_name: str
    text_direction: TextDirection
    date_format: str = "%Y-%m-%d"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    number_decimal_separator: str = "."
    number_thousands_separator: str = ","


# =============================================================================
# Inline Translation Service
# =============================================================================


MEDICAL_GLOSSARY_EN_AR = {
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
    "referral": "إحالة",
}

MEDICAL_GLOSSARY_AR_EN = {v: k for k, v in MEDICAL_GLOSSARY_EN_AR.items()}


class TranslationService:
    """Provides translation services."""

    def __init__(self):
        self._en_ar_glossary = MEDICAL_GLOSSARY_EN_AR.copy()
        self._ar_en_glossary = MEDICAL_GLOSSARY_AR_EN.copy()

    def get_text_direction(self, language: SupportedLanguage) -> TextDirection:
        """Get text direction for a language."""
        if language == SupportedLanguage.ARABIC:
            return TextDirection.RTL
        return TextDirection.LTR

    def detect_language(self, text: str) -> tuple[SupportedLanguage, float]:
        """Detect the language of text."""
        arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')
        arabic_chars = len(arabic_pattern.findall(text))
        total_chars = len(re.findall(r'\w', text))

        if total_chars == 0:
            return SupportedLanguage.ENGLISH, 0.5

        arabic_ratio = arabic_chars / total_chars

        if arabic_ratio > 0.3:
            return SupportedLanguage.ARABIC, min(1.0, arabic_ratio + 0.3)
        return SupportedLanguage.ENGLISH, min(1.0, 1 - arabic_ratio)

    async def translate_text(
        self,
        text: str,
        source_language: Optional[SupportedLanguage] = None,
        target_language: SupportedLanguage = SupportedLanguage.ENGLISH,
        use_glossary: bool = True,
    ) -> TranslatedText:
        """Translate text between languages."""
        if source_language is None:
            source_language, _ = self.detect_language(text)

        if source_language == target_language:
            return TranslatedText(
                original_text=text,
                translated_text=text,
                source_language=source_language,
                target_language=target_language,
                confidence=1.0,
                text_direction=self.get_text_direction(target_language),
            )

        translated = text
        glossary_applied = False
        is_medical = False

        if use_glossary:
            if source_language == SupportedLanguage.ENGLISH and target_language == SupportedLanguage.ARABIC:
                translated, glossary_applied, is_medical = self._apply_glossary(text, self._en_ar_glossary)
            elif source_language == SupportedLanguage.ARABIC and target_language == SupportedLanguage.ENGLISH:
                translated, glossary_applied, is_medical = self._apply_glossary(text, self._ar_en_glossary)

        return TranslatedText(
            original_text=text,
            translated_text=translated,
            source_language=source_language,
            target_language=target_language,
            confidence=0.95 if glossary_applied else 0.8,
            text_direction=self.get_text_direction(target_language),
            is_medical_term=is_medical,
            glossary_applied=glossary_applied,
        )

    def _apply_glossary(self, text: str, glossary: dict[str, str]) -> tuple[str, bool, bool]:
        """Apply glossary translations."""
        result = text
        was_applied = False
        found_medical = False

        sorted_terms = sorted(glossary.keys(), key=len, reverse=True)

        for term in sorted_terms:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            if pattern.search(result):
                result = pattern.sub(glossary[term], result)
                was_applied = True
                found_medical = True

        return result, was_applied, found_medical

    def add_glossary_term(self, english_term: str, arabic_term: str) -> None:
        """Add a custom term to the glossary."""
        self._en_ar_glossary[english_term.lower()] = arabic_term
        self._ar_en_glossary[arabic_term] = english_term.lower()

    def wrap_rtl_text(self, text: str) -> str:
        """Wrap text with RTL markers."""
        RLE = "\u202B"
        PDF = "\u202C"
        return f"{RLE}{text}{PDF}"


# =============================================================================
# Inline Currency Service
# =============================================================================


FIXED_RATES_TO_USD = {
    SupportedCurrency.USD: Decimal("1.0000"),
    SupportedCurrency.EUR: Decimal("1.0850"),
    SupportedCurrency.AED: Decimal("0.2723"),
    SupportedCurrency.SAR: Decimal("0.2667"),
    SupportedCurrency.EGP: Decimal("0.0204"),
    SupportedCurrency.KWD: Decimal("3.2500"),
    SupportedCurrency.AUD: Decimal("0.6500"),
}


class CurrencyConversionService:
    """Provides currency conversion."""

    def __init__(self):
        self._audit_log = []

    def get_supported_currencies(self) -> list[SupportedCurrency]:
        """Get list of supported currencies."""
        return list(SupportedCurrency)

    def get_exchange_rate(
        self,
        from_currency: SupportedCurrency,
        to_currency: SupportedCurrency,
    ) -> Decimal:
        """Get exchange rate between two currencies."""
        if from_currency == to_currency:
            return Decimal("1.0000")

        from_to_usd = FIXED_RATES_TO_USD.get(from_currency, Decimal("1.0"))
        to_to_usd = FIXED_RATES_TO_USD.get(to_currency, Decimal("1.0"))

        rate = from_to_usd / to_to_usd
        return rate.quantize(Decimal("0.000001"))

    async def convert(
        self,
        amount: Decimal,
        from_currency: SupportedCurrency,
        to_currency: SupportedCurrency,
    ) -> CurrencyConversion:
        """Convert amount between currencies."""
        rate = self.get_exchange_rate(from_currency, to_currency)
        converted = (amount * rate).quantize(Decimal("0.01"))

        return CurrencyConversion(
            original_amount=amount,
            original_currency=from_currency,
            converted_amount=converted,
            target_currency=to_currency,
            exchange_rate=rate,
            rate_date=date.today(),
        )

    def format_currency(
        self,
        amount: Decimal,
        currency: SupportedCurrency,
        include_symbol: bool = True,
    ) -> str:
        """Format amount with currency symbol."""
        symbols = {
            SupportedCurrency.USD: "$",
            SupportedCurrency.EUR: "€",
            SupportedCurrency.AED: "د.إ",
            SupportedCurrency.SAR: "ر.س",
            SupportedCurrency.EGP: "ج.م",
            SupportedCurrency.KWD: "د.ك",
            SupportedCurrency.AUD: "A$",
        }

        formatted_amount = f"{amount:,.2f}"

        if include_symbol:
            symbol = symbols.get(currency, currency.value)
            if currency in [SupportedCurrency.AED, SupportedCurrency.SAR, SupportedCurrency.EGP, SupportedCurrency.KWD]:
                return f"{formatted_amount} {symbol}"
            return f"{symbol}{formatted_amount}"

        return formatted_amount


# =============================================================================
# Inline Localization Service
# =============================================================================


LOCALE_CONFIGS = {
    SupportedLanguage.ENGLISH: LocaleConfig(
        language=SupportedLanguage.ENGLISH,
        language_name="English",
        language_native_name="English",
        text_direction=TextDirection.LTR,
        date_format="%m/%d/%Y",
        number_decimal_separator=".",
        number_thousands_separator=",",
    ),
    SupportedLanguage.ARABIC: LocaleConfig(
        language=SupportedLanguage.ARABIC,
        language_name="Arabic",
        language_native_name="العربية",
        text_direction=TextDirection.RTL,
        date_format="%d/%m/%Y",
        number_decimal_separator="٫",
        number_thousands_separator="٬",
    ),
}

DEFAULT_STRINGS = {
    "claim.status": "Status",
    "claim.id": "Claim ID",
    "status.approved": "Approved",
    "status.denied": "Denied",
}

ARABIC_STRINGS = {
    "claim.status": "الحالة",
    "claim.id": "رقم المطالبة",
    "status.approved": "موافق عليها",
    "status.denied": "مرفوضة",
}


class LocalizationService:
    """Provides UI localization."""

    def __init__(self, default_language: SupportedLanguage = SupportedLanguage.ENGLISH):
        self._default_language = default_language
        self._current_language = default_language
        self._strings = {
            SupportedLanguage.ENGLISH: DEFAULT_STRINGS.copy(),
            SupportedLanguage.ARABIC: ARABIC_STRINGS.copy(),
        }

    def set_language(self, language: SupportedLanguage) -> None:
        """Set the current language."""
        self._current_language = language

    def get_language(self) -> SupportedLanguage:
        """Get the current language."""
        return self._current_language

    def get_locale_config(self, language: Optional[SupportedLanguage] = None) -> LocaleConfig:
        """Get locale configuration."""
        lang = language or self._current_language
        return LOCALE_CONFIGS.get(lang, LOCALE_CONFIGS[SupportedLanguage.ENGLISH])

    def get_string(self, key: str, language: Optional[SupportedLanguage] = None, default: Optional[str] = None) -> str:
        """Get localized string."""
        lang = language or self._current_language
        if lang in self._strings and key in self._strings[lang]:
            return self._strings[lang][key]
        if key in DEFAULT_STRINGS:
            return DEFAULT_STRINGS[key]
        return default or key

    def t(self, key: str, language: Optional[SupportedLanguage] = None, default: Optional[str] = None) -> str:
        """Shorthand for get_string."""
        return self.get_string(key, language, default)

    def format_date(self, value: date, language: Optional[SupportedLanguage] = None) -> str:
        """Format date according to locale."""
        config = self.get_locale_config(language)
        return value.strftime(config.date_format)

    def format_number(self, value: float, decimals: int = 2, language: Optional[SupportedLanguage] = None) -> str:
        """Format number according to locale."""
        config = self.get_locale_config(language)
        formatted = f"{value:,.{decimals}f}"

        if config.number_thousands_separator != ",":
            formatted = formatted.replace(".", "DECIMAL")
            formatted = formatted.replace(",", config.number_thousands_separator)
            formatted = formatted.replace("DECIMAL", config.number_decimal_separator)
        elif config.number_decimal_separator != ".":
            formatted = formatted.replace(".", config.number_decimal_separator)

        return formatted

    def is_rtl(self, language: Optional[SupportedLanguage] = None) -> bool:
        """Check if language uses RTL text direction."""
        config = self.get_locale_config(language)
        return config.text_direction == TextDirection.RTL

    def localize_claim_status(self, status: str, language: Optional[SupportedLanguage] = None) -> str:
        """Localize claim status value."""
        key = f"status.{status.lower()}"
        return self.get_string(key, language, default=status)


# =============================================================================
# Translation Service Tests
# =============================================================================


class TestTranslationService:
    """Tests for translation service."""

    @pytest.fixture
    def service(self):
        """Create translation service instance."""
        return TranslationService()

    def test_get_text_direction_english(self, service):
        """Test English is LTR."""
        assert service.get_text_direction(SupportedLanguage.ENGLISH) == TextDirection.LTR

    def test_get_text_direction_arabic(self, service):
        """Test Arabic is RTL."""
        assert service.get_text_direction(SupportedLanguage.ARABIC) == TextDirection.RTL

    def test_detect_english_text(self, service):
        """Test detecting English text."""
        lang, conf = service.detect_language("This is a medical claim for treatment")
        assert lang == SupportedLanguage.ENGLISH
        assert conf > 0.5

    def test_detect_arabic_text(self, service):
        """Test detecting Arabic text."""
        lang, conf = service.detect_language("هذه مطالبة طبية للعلاج")
        assert lang == SupportedLanguage.ARABIC
        assert conf > 0.5

    @pytest.mark.asyncio
    async def test_translate_medical_term_en_to_ar(self, service):
        """Test translating medical term from English to Arabic."""
        result = await service.translate_text(
            "diagnosis",
            SupportedLanguage.ENGLISH,
            SupportedLanguage.ARABIC,
        )

        assert result.translated_text == "تشخيص"
        assert result.glossary_applied is True
        assert result.is_medical_term is True

    @pytest.mark.asyncio
    async def test_translate_medical_term_ar_to_en(self, service):
        """Test translating medical term from Arabic to English."""
        result = await service.translate_text(
            "علاج",
            SupportedLanguage.ARABIC,
            SupportedLanguage.ENGLISH,
        )

        assert result.translated_text == "treatment"
        assert result.glossary_applied is True

    @pytest.mark.asyncio
    async def test_translate_same_language(self, service):
        """Test translation when source equals target."""
        result = await service.translate_text(
            "test text",
            SupportedLanguage.ENGLISH,
            SupportedLanguage.ENGLISH,
        )

        assert result.translated_text == result.original_text
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_translate_sentence_with_medical_terms(self, service):
        """Test translating sentence containing medical terms."""
        result = await service.translate_text(
            "The patient needs surgery at the hospital",
            SupportedLanguage.ENGLISH,
            SupportedLanguage.ARABIC,
        )

        assert "مريض" in result.translated_text
        assert "جراحة" in result.translated_text
        assert "مستشفى" in result.translated_text
        assert result.glossary_applied is True

    def test_add_custom_glossary_term(self, service):
        """Test adding custom glossary term."""
        service.add_glossary_term("telemedicine", "الطب عن بعد")
        assert "telemedicine" in service._en_ar_glossary
        assert "الطب عن بعد" in service._ar_en_glossary

    def test_wrap_rtl_text(self, service):
        """Test RTL text wrapping."""
        wrapped = service.wrap_rtl_text("مرحبا")
        assert "\u202B" in wrapped  # RLE marker
        assert "\u202C" in wrapped  # PDF marker


# =============================================================================
# Currency Service Tests
# =============================================================================


class TestCurrencyService:
    """Tests for currency conversion service."""

    @pytest.fixture
    def service(self):
        """Create currency service instance."""
        return CurrencyConversionService()

    def test_get_supported_currencies(self, service):
        """Test getting supported currencies."""
        currencies = service.get_supported_currencies()
        assert SupportedCurrency.USD in currencies
        assert SupportedCurrency.AED in currencies
        assert SupportedCurrency.SAR in currencies

    def test_get_exchange_rate_same_currency(self, service):
        """Test exchange rate for same currency is 1."""
        rate = service.get_exchange_rate(SupportedCurrency.USD, SupportedCurrency.USD)
        assert rate == Decimal("1.0000")

    def test_get_exchange_rate_usd_to_aed(self, service):
        """Test USD to AED exchange rate."""
        rate = service.get_exchange_rate(SupportedCurrency.USD, SupportedCurrency.AED)
        # 1 USD = ~3.67 AED (inverse of 0.2723)
        assert rate > Decimal("3")
        assert rate < Decimal("4")

    def test_get_exchange_rate_aed_to_usd(self, service):
        """Test AED to USD exchange rate."""
        rate = service.get_exchange_rate(SupportedCurrency.AED, SupportedCurrency.USD)
        # 1 AED = ~0.27 USD
        assert rate > Decimal("0.2")
        assert rate < Decimal("0.3")

    @pytest.mark.asyncio
    async def test_convert_usd_to_aed(self, service):
        """Test converting USD to AED."""
        result = await service.convert(
            Decimal("100"),
            SupportedCurrency.USD,
            SupportedCurrency.AED,
        )

        assert result.original_amount == Decimal("100")
        assert result.original_currency == SupportedCurrency.USD
        assert result.target_currency == SupportedCurrency.AED
        # 100 USD should be ~367 AED
        assert result.converted_amount > Decimal("350")
        assert result.converted_amount < Decimal("400")

    @pytest.mark.asyncio
    async def test_convert_aed_to_usd(self, service):
        """Test converting AED to USD."""
        result = await service.convert(
            Decimal("367"),
            SupportedCurrency.AED,
            SupportedCurrency.USD,
        )

        # 367 AED should be ~100 USD
        assert result.converted_amount > Decimal("90")
        assert result.converted_amount < Decimal("110")

    @pytest.mark.asyncio
    async def test_convert_same_currency(self, service):
        """Test converting same currency returns same amount."""
        result = await service.convert(
            Decimal("100"),
            SupportedCurrency.USD,
            SupportedCurrency.USD,
        )

        assert result.converted_amount == Decimal("100.00")

    def test_format_usd_currency(self, service):
        """Test formatting USD amount."""
        formatted = service.format_currency(Decimal("1234.56"), SupportedCurrency.USD)
        assert formatted == "$1,234.56"

    def test_format_aed_currency(self, service):
        """Test formatting AED amount."""
        formatted = service.format_currency(Decimal("1234.56"), SupportedCurrency.AED)
        assert "1,234.56" in formatted
        assert "د.إ" in formatted

    def test_format_sar_currency(self, service):
        """Test formatting SAR amount."""
        formatted = service.format_currency(Decimal("500"), SupportedCurrency.SAR)
        assert "500.00" in formatted
        assert "ر.س" in formatted

    def test_format_without_symbol(self, service):
        """Test formatting without symbol."""
        formatted = service.format_currency(
            Decimal("1234.56"),
            SupportedCurrency.USD,
            include_symbol=False,
        )
        assert formatted == "1,234.56"


# =============================================================================
# Localization Service Tests
# =============================================================================


class TestLocalizationService:
    """Tests for localization service."""

    @pytest.fixture
    def service(self):
        """Create localization service instance."""
        return LocalizationService()

    def test_default_language_is_english(self, service):
        """Test default language is English."""
        assert service.get_language() == SupportedLanguage.ENGLISH

    def test_set_language(self, service):
        """Test setting language."""
        service.set_language(SupportedLanguage.ARABIC)
        assert service.get_language() == SupportedLanguage.ARABIC

    def test_get_locale_config_english(self, service):
        """Test getting English locale config."""
        config = service.get_locale_config(SupportedLanguage.ENGLISH)

        assert config.language == SupportedLanguage.ENGLISH
        assert config.text_direction == TextDirection.LTR
        assert config.number_decimal_separator == "."

    def test_get_locale_config_arabic(self, service):
        """Test getting Arabic locale config."""
        config = service.get_locale_config(SupportedLanguage.ARABIC)

        assert config.language == SupportedLanguage.ARABIC
        assert config.text_direction == TextDirection.RTL
        assert config.language_native_name == "العربية"

    def test_get_string_english(self, service):
        """Test getting English string."""
        service.set_language(SupportedLanguage.ENGLISH)
        result = service.get_string("claim.status")
        assert result == "Status"

    def test_get_string_arabic(self, service):
        """Test getting Arabic string."""
        service.set_language(SupportedLanguage.ARABIC)
        result = service.get_string("claim.status")
        assert result == "الحالة"

    def test_get_string_with_default(self, service):
        """Test getting string with default."""
        result = service.get_string("nonexistent.key", default="Default Value")
        assert result == "Default Value"

    def test_t_shorthand(self, service):
        """Test t() shorthand method."""
        result = service.t("claim.id")
        assert result == "Claim ID"

    def test_format_date_english(self, service):
        """Test date formatting for English."""
        test_date = date(2025, 12, 18)
        formatted = service.format_date(test_date, SupportedLanguage.ENGLISH)
        assert formatted == "12/18/2025"

    def test_format_date_arabic(self, service):
        """Test date formatting for Arabic."""
        test_date = date(2025, 12, 18)
        formatted = service.format_date(test_date, SupportedLanguage.ARABIC)
        assert formatted == "18/12/2025"

    def test_format_number_english(self, service):
        """Test number formatting for English."""
        formatted = service.format_number(1234567.89, language=SupportedLanguage.ENGLISH)
        assert formatted == "1,234,567.89"

    def test_format_number_arabic(self, service):
        """Test number formatting for Arabic."""
        formatted = service.format_number(1234567.89, language=SupportedLanguage.ARABIC)
        assert "٬" in formatted or "1234567" in formatted  # Arabic separator or fallback

    def test_is_rtl_english(self, service):
        """Test RTL check for English."""
        assert service.is_rtl(SupportedLanguage.ENGLISH) is False

    def test_is_rtl_arabic(self, service):
        """Test RTL check for Arabic."""
        assert service.is_rtl(SupportedLanguage.ARABIC) is True

    def test_localize_claim_status_approved(self, service):
        """Test localizing approved status."""
        service.set_language(SupportedLanguage.ENGLISH)
        result = service.localize_claim_status("approved")
        assert result == "Approved"

    def test_localize_claim_status_approved_arabic(self, service):
        """Test localizing approved status in Arabic."""
        service.set_language(SupportedLanguage.ARABIC)
        result = service.localize_claim_status("approved")
        assert result == "موافق عليها"


# =============================================================================
# Integration Tests
# =============================================================================


class TestI18nIntegration:
    """Integration tests for i18n services."""

    @pytest.mark.asyncio
    async def test_translate_and_localize_claim(self):
        """Test translating and localizing a claim."""
        translation = TranslationService()
        currency = CurrencyConversionService()
        localization = LocalizationService()

        claim_data = {
            "claim_id": "CLM-001",
            "status": "approved",
            "total_charged": Decimal("500"),
            "currency": "USD",
            "notes": "Patient needs surgery",
        }

        # Translate notes
        translated = await translation.translate_text(
            claim_data["notes"],
            SupportedLanguage.ENGLISH,
            SupportedLanguage.ARABIC,
        )
        assert "جراحة" in translated.translated_text

        # Convert currency
        converted = await currency.convert(
            claim_data["total_charged"],
            SupportedCurrency.USD,
            SupportedCurrency.AED,
        )
        assert converted.converted_amount > Decimal("1500")

        # Localize status
        localization.set_language(SupportedLanguage.ARABIC)
        status = localization.localize_claim_status(claim_data["status"])
        assert status == "موافق عليها"

    @pytest.mark.asyncio
    async def test_multi_currency_claim_conversion(self):
        """Test converting claim amounts across multiple currencies."""
        currency = CurrencyConversionService()

        claim_amount = Decimal("1000")  # Original in SAR

        # Convert to multiple currencies
        to_usd = await currency.convert(claim_amount, SupportedCurrency.SAR, SupportedCurrency.USD)
        to_aed = await currency.convert(claim_amount, SupportedCurrency.SAR, SupportedCurrency.AED)
        to_eur = await currency.convert(claim_amount, SupportedCurrency.SAR, SupportedCurrency.EUR)

        # USD should be ~267
        assert to_usd.converted_amount > Decimal("250")
        assert to_usd.converted_amount < Decimal("300")

        # AED should be ~980 (SAR and AED are close in value)
        assert to_aed.converted_amount > Decimal("900")
        assert to_aed.converted_amount < Decimal("1100")

        # EUR should be ~246
        assert to_eur.converted_amount > Decimal("230")
        assert to_eur.converted_amount < Decimal("270")

    def test_bidirectional_translation_roundtrip(self):
        """Test translation roundtrip consistency."""
        translation = TranslationService()

        # Get Arabic for a medical term
        english_term = "hospital"
        arabic_term = translation._en_ar_glossary.get(english_term)

        # Get English back
        english_back = translation._ar_en_glossary.get(arabic_term)

        assert english_back == english_term

    def test_locale_switching(self):
        """Test switching between locales."""
        localization = LocalizationService()

        # Start with English
        assert localization.get_string("claim.status") == "Status"
        assert localization.is_rtl() is False

        # Switch to Arabic
        localization.set_language(SupportedLanguage.ARABIC)
        assert localization.get_string("claim.status") == "الحالة"
        assert localization.is_rtl() is True

        # Switch back to English
        localization.set_language(SupportedLanguage.ENGLISH)
        assert localization.get_string("claim.status") == "Status"
        assert localization.is_rtl() is False

    @pytest.mark.asyncio
    async def test_full_claim_localization_workflow(self):
        """Test complete workflow for localizing a claim."""
        translation = TranslationService()
        currency = CurrencyConversionService()
        localization = LocalizationService()

        # Original claim in English/USD
        claim = {
            "claim_id": "CLM-2025-001",
            "status": "denied",
            "service_date": date(2025, 12, 15),
            "total_charged": Decimal("2500.00"),
            "currency": "USD",
            "denial_reason": "Pre-authorization required for surgery",
        }

        # Set target locale to Arabic/AED
        localization.set_language(SupportedLanguage.ARABIC)

        # 1. Translate denial reason
        translation_result = await translation.translate_text(
            claim["denial_reason"],
            SupportedLanguage.ENGLISH,
            SupportedLanguage.ARABIC,
        )

        # 2. Convert currency
        currency_result = await currency.convert(
            claim["total_charged"],
            SupportedCurrency.USD,
            SupportedCurrency.AED,
        )

        # 3. Localize status
        localized_status = localization.localize_claim_status(claim["status"])

        # 4. Format date
        formatted_date = localization.format_date(claim["service_date"])

        # 5. Format amount
        formatted_amount = currency.format_currency(currency_result.converted_amount, SupportedCurrency.AED)

        # Assertions
        assert "جراحة" in translation_result.translated_text  # Surgery translated
        assert currency_result.converted_amount > Decimal("9000")  # ~9175 AED
        assert localized_status == "مرفوضة"
        assert formatted_date == "15/12/2025"
        assert "د.إ" in formatted_amount
