"""
Localization Service.
Source: Design Document Section 4.3 - Internationalization
Verified: 2025-12-18

Provides UI localization and locale management for claims processing.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.services.i18n.translation import SupportedLanguage, TextDirection


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
    currency_position: str = "before"  # before or after


# Predefined locale configurations
LOCALE_CONFIGS = {
    SupportedLanguage.ENGLISH: LocaleConfig(
        language=SupportedLanguage.ENGLISH,
        language_name="English",
        language_native_name="English",
        text_direction=TextDirection.LTR,
        date_format="%m/%d/%Y",
        datetime_format="%m/%d/%Y %I:%M %p",
        number_decimal_separator=".",
        number_thousands_separator=",",
        currency_position="before",
    ),
    SupportedLanguage.ARABIC: LocaleConfig(
        language=SupportedLanguage.ARABIC,
        language_name="Arabic",
        language_native_name="العربية",
        text_direction=TextDirection.RTL,
        date_format="%d/%m/%Y",
        datetime_format="%d/%m/%Y %H:%M",
        number_decimal_separator="٫",  # Arabic decimal separator
        number_thousands_separator="٬",  # Arabic thousands separator
        currency_position="after",
    ),
    SupportedLanguage.FRENCH: LocaleConfig(
        language=SupportedLanguage.FRENCH,
        language_name="French",
        language_native_name="Français",
        text_direction=TextDirection.LTR,
        date_format="%d/%m/%Y",
        datetime_format="%d/%m/%Y %H:%M",
        number_decimal_separator=",",
        number_thousands_separator=" ",
        currency_position="after",
    ),
}


# Default UI strings - English
DEFAULT_STRINGS = {
    # Common
    "app.name": "Claims Processing System",
    "app.welcome": "Welcome",
    "app.logout": "Logout",
    "app.save": "Save",
    "app.cancel": "Cancel",
    "app.submit": "Submit",
    "app.delete": "Delete",
    "app.edit": "Edit",
    "app.view": "View",
    "app.search": "Search",
    "app.filter": "Filter",
    "app.loading": "Loading...",
    "app.error": "Error",
    "app.success": "Success",

    # Claims
    "claim.title": "Claim",
    "claim.claims": "Claims",
    "claim.new": "New Claim",
    "claim.id": "Claim ID",
    "claim.status": "Status",
    "claim.date": "Service Date",
    "claim.amount": "Amount",
    "claim.provider": "Provider",
    "claim.member": "Member",
    "claim.diagnosis": "Diagnosis",
    "claim.procedure": "Procedure",
    "claim.submit": "Submit Claim",
    "claim.approve": "Approve",
    "claim.deny": "Deny",
    "claim.pending": "Pending",

    # Status values
    "status.draft": "Draft",
    "status.submitted": "Submitted",
    "status.processing": "Processing",
    "status.approved": "Approved",
    "status.denied": "Denied",
    "status.paid": "Paid",
    "status.closed": "Closed",

    # Member
    "member.id": "Member ID",
    "member.name": "Member Name",
    "member.dob": "Date of Birth",
    "member.policy": "Policy Number",

    # Provider
    "provider.id": "Provider ID",
    "provider.name": "Provider Name",
    "provider.specialty": "Specialty",
    "provider.npi": "NPI",

    # Financial
    "financial.charged": "Charged Amount",
    "financial.allowed": "Allowed Amount",
    "financial.paid": "Paid Amount",
    "financial.patient_resp": "Patient Responsibility",
    "financial.deductible": "Deductible",
    "financial.copay": "Copay",
    "financial.coinsurance": "Coinsurance",

    # Errors
    "error.required": "This field is required",
    "error.invalid_date": "Invalid date format",
    "error.invalid_amount": "Invalid amount",
    "error.claim_not_found": "Claim not found",
    "error.unauthorized": "Unauthorized access",

    # Messages
    "msg.claim_submitted": "Claim submitted successfully",
    "msg.claim_approved": "Claim approved",
    "msg.claim_denied": "Claim denied",
    "msg.saved": "Changes saved successfully",
}

# Arabic translations
ARABIC_STRINGS = {
    # Common
    "app.name": "نظام معالجة المطالبات",
    "app.welcome": "مرحباً",
    "app.logout": "تسجيل خروج",
    "app.save": "حفظ",
    "app.cancel": "إلغاء",
    "app.submit": "إرسال",
    "app.delete": "حذف",
    "app.edit": "تعديل",
    "app.view": "عرض",
    "app.search": "بحث",
    "app.filter": "تصفية",
    "app.loading": "جاري التحميل...",
    "app.error": "خطأ",
    "app.success": "نجاح",

    # Claims
    "claim.title": "مطالبة",
    "claim.claims": "المطالبات",
    "claim.new": "مطالبة جديدة",
    "claim.id": "رقم المطالبة",
    "claim.status": "الحالة",
    "claim.date": "تاريخ الخدمة",
    "claim.amount": "المبلغ",
    "claim.provider": "مقدم الخدمة",
    "claim.member": "العضو",
    "claim.diagnosis": "التشخيص",
    "claim.procedure": "الإجراء",
    "claim.submit": "تقديم المطالبة",
    "claim.approve": "موافقة",
    "claim.deny": "رفض",
    "claim.pending": "قيد الانتظار",

    # Status values
    "status.draft": "مسودة",
    "status.submitted": "مقدمة",
    "status.processing": "قيد المعالجة",
    "status.approved": "موافق عليها",
    "status.denied": "مرفوضة",
    "status.paid": "مدفوعة",
    "status.closed": "مغلقة",

    # Member
    "member.id": "رقم العضو",
    "member.name": "اسم العضو",
    "member.dob": "تاريخ الميلاد",
    "member.policy": "رقم البوليصة",

    # Provider
    "provider.id": "رقم مقدم الخدمة",
    "provider.name": "اسم مقدم الخدمة",
    "provider.specialty": "التخصص",
    "provider.npi": "رقم التعريف الوطني",

    # Financial
    "financial.charged": "المبلغ المطالب به",
    "financial.allowed": "المبلغ المسموح",
    "financial.paid": "المبلغ المدفوع",
    "financial.patient_resp": "مسؤولية المريض",
    "financial.deductible": "المبلغ المقتطع",
    "financial.copay": "المساهمة",
    "financial.coinsurance": "التأمين المشترك",

    # Errors
    "error.required": "هذا الحقل مطلوب",
    "error.invalid_date": "تنسيق التاريخ غير صالح",
    "error.invalid_amount": "المبلغ غير صالح",
    "error.claim_not_found": "المطالبة غير موجودة",
    "error.unauthorized": "غير مصرح بالوصول",

    # Messages
    "msg.claim_submitted": "تم تقديم المطالبة بنجاح",
    "msg.claim_approved": "تمت الموافقة على المطالبة",
    "msg.claim_denied": "تم رفض المطالبة",
    "msg.saved": "تم حفظ التغييرات بنجاح",
}


class LocalizationService:
    """
    Provides UI localization for claims processing.

    Features:
    - Multi-language string management
    - Date/time formatting
    - Number formatting
    - RTL text support
    """

    def __init__(self, default_language: SupportedLanguage = SupportedLanguage.ENGLISH):
        """
        Initialize LocalizationService.

        Args:
            default_language: Default language for the service
        """
        self._default_language = default_language
        self._current_language = default_language
        self._strings: dict[SupportedLanguage, dict[str, str]] = {
            SupportedLanguage.ENGLISH: DEFAULT_STRINGS.copy(),
            SupportedLanguage.ARABIC: ARABIC_STRINGS.copy(),
        }
        self._custom_strings: dict[SupportedLanguage, dict[str, str]] = {}

    def set_language(self, language: SupportedLanguage) -> None:
        """Set the current language."""
        self._current_language = language

    def get_language(self) -> SupportedLanguage:
        """Get the current language."""
        return self._current_language

    def get_locale_config(
        self,
        language: Optional[SupportedLanguage] = None,
    ) -> LocaleConfig:
        """
        Get locale configuration.

        Args:
            language: Language to get config for (current if None)

        Returns:
            LocaleConfig for the language
        """
        lang = language or self._current_language
        return LOCALE_CONFIGS.get(
            lang,
            LOCALE_CONFIGS[SupportedLanguage.ENGLISH],
        )

    def get_string(
        self,
        key: str,
        language: Optional[SupportedLanguage] = None,
        default: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Get localized string.

        Args:
            key: String key (e.g., "claim.status")
            language: Language to get string in (current if None)
            default: Default value if key not found
            **kwargs: Interpolation values

        Returns:
            Localized string
        """
        lang = language or self._current_language

        # Check custom strings first
        if lang in self._custom_strings and key in self._custom_strings[lang]:
            result = self._custom_strings[lang][key]
        elif lang in self._strings and key in self._strings[lang]:
            result = self._strings[lang][key]
        elif key in DEFAULT_STRINGS:
            result = DEFAULT_STRINGS[key]
        else:
            result = default or key

        # Interpolate values
        if kwargs:
            try:
                result = result.format(**kwargs)
            except KeyError:
                pass

        return result

    def t(
        self,
        key: str,
        language: Optional[SupportedLanguage] = None,
        default: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Shorthand for get_string."""
        return self.get_string(key, language, default, **kwargs)

    def add_string(
        self,
        key: str,
        value: str,
        language: SupportedLanguage,
    ) -> None:
        """
        Add or update a localized string.

        Args:
            key: String key
            value: Localized value
            language: Language for the string
        """
        if language not in self._custom_strings:
            self._custom_strings[language] = {}
        self._custom_strings[language][key] = value

    def load_strings(
        self,
        strings: dict[str, str],
        language: SupportedLanguage,
    ) -> None:
        """
        Load multiple strings for a language.

        Args:
            strings: Dictionary of key-value pairs
            language: Language for the strings
        """
        if language not in self._strings:
            self._strings[language] = {}
        self._strings[language].update(strings)

    def format_date(
        self,
        value: date,
        language: Optional[SupportedLanguage] = None,
    ) -> str:
        """
        Format date according to locale.

        Args:
            value: Date to format
            language: Language for formatting

        Returns:
            Formatted date string
        """
        config = self.get_locale_config(language)
        return value.strftime(config.date_format)

    def format_datetime(
        self,
        value: datetime,
        language: Optional[SupportedLanguage] = None,
    ) -> str:
        """
        Format datetime according to locale.

        Args:
            value: Datetime to format
            language: Language for formatting

        Returns:
            Formatted datetime string
        """
        config = self.get_locale_config(language)
        return value.strftime(config.datetime_format)

    def format_number(
        self,
        value: float | int | Decimal,
        decimals: int = 2,
        language: Optional[SupportedLanguage] = None,
    ) -> str:
        """
        Format number according to locale.

        Args:
            value: Number to format
            decimals: Number of decimal places
            language: Language for formatting

        Returns:
            Formatted number string
        """
        config = self.get_locale_config(language)

        # Format with decimals
        formatted = f"{float(value):,.{decimals}f}"

        # Replace separators
        if config.number_thousands_separator != ",":
            # Temporarily replace decimal point
            formatted = formatted.replace(".", "DECIMAL")
            formatted = formatted.replace(",", config.number_thousands_separator)
            formatted = formatted.replace("DECIMAL", config.number_decimal_separator)
        elif config.number_decimal_separator != ".":
            formatted = formatted.replace(".", config.number_decimal_separator)

        return formatted

    def get_text_direction(
        self,
        language: Optional[SupportedLanguage] = None,
    ) -> TextDirection:
        """
        Get text direction for language.

        Args:
            language: Language to check

        Returns:
            TextDirection (LTR or RTL)
        """
        config = self.get_locale_config(language)
        return config.text_direction

    def is_rtl(self, language: Optional[SupportedLanguage] = None) -> bool:
        """Check if language uses RTL text direction."""
        return self.get_text_direction(language) == TextDirection.RTL

    def get_available_languages(self) -> list[dict]:
        """
        Get list of available languages.

        Returns:
            List of language info dictionaries
        """
        languages = []
        for lang, config in LOCALE_CONFIGS.items():
            languages.append({
                "code": lang.value,
                "name": config.language_name,
                "native_name": config.language_native_name,
                "direction": config.text_direction.value,
            })
        return languages

    def localize_claim_status(
        self,
        status: str,
        language: Optional[SupportedLanguage] = None,
    ) -> str:
        """
        Localize claim status value.

        Args:
            status: Status value (e.g., "approved")
            language: Language for localization

        Returns:
            Localized status string
        """
        key = f"status.{status.lower()}"
        return self.get_string(key, language, default=status)

    def get_all_strings(
        self,
        language: Optional[SupportedLanguage] = None,
    ) -> dict[str, str]:
        """
        Get all strings for a language.

        Args:
            language: Language to get strings for

        Returns:
            Dictionary of all strings
        """
        lang = language or self._current_language
        result = DEFAULT_STRINGS.copy()

        if lang in self._strings:
            result.update(self._strings[lang])

        if lang in self._custom_strings:
            result.update(self._custom_strings[lang])

        return result

    def export_strings(
        self,
        language: SupportedLanguage,
        file_path: Optional[str] = None,
    ) -> dict[str, str]:
        """
        Export strings for a language.

        Args:
            language: Language to export
            file_path: Optional file path to save to

        Returns:
            Dictionary of strings
        """
        strings = self.get_all_strings(language)

        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(strings, f, ensure_ascii=False, indent=2)

        return strings


# =============================================================================
# Factory Functions
# =============================================================================


_localization_service: Optional[LocalizationService] = None


def get_localization_service(
    default_language: SupportedLanguage = SupportedLanguage.ENGLISH,
) -> LocalizationService:
    """Get singleton LocalizationService instance."""
    global _localization_service
    if _localization_service is None:
        _localization_service = LocalizationService(default_language)
    return _localization_service


def create_localization_service(
    default_language: SupportedLanguage = SupportedLanguage.ENGLISH,
) -> LocalizationService:
    """Create a new LocalizationService instance."""
    return LocalizationService(default_language)
