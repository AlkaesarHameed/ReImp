"""
Translation Service.
Source: Design Document Section 4.3 - Internationalization
Verified: 2025-12-18

Provides document and text translation with Arabic/English support.
"""

from enum import Enum
from typing import Optional
import re

from pydantic import BaseModel, Field


class SupportedLanguage(str, Enum):
    """Supported languages for translation."""

    ENGLISH = "en"
    ARABIC = "ar"
    FRENCH = "fr"
    GERMAN = "de"
    SPANISH = "es"


class TextDirection(str, Enum):
    """Text direction for display."""

    LTR = "ltr"  # Left-to-right
    RTL = "rtl"  # Right-to-left


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


class DocumentTranslation(BaseModel):
    """Result of document translation."""

    original_content: str
    translated_content: str
    source_language: SupportedLanguage
    target_language: SupportedLanguage
    word_count: int = 0
    medical_terms_found: list[str] = Field(default_factory=list)
    confidence_score: float = 1.0
    processing_notes: list[str] = Field(default_factory=list)


# Medical terminology glossary for accurate translations
MEDICAL_GLOSSARY_EN_AR = {
    # General medical terms
    "diagnosis": "تشخيص",
    "treatment": "علاج",
    "prescription": "وصفة طبية",
    "surgery": "جراحة",
    "patient": "مريض",
    "doctor": "طبيب",
    "hospital": "مستشفى",
    "clinic": "عيادة",
    "emergency": "طوارئ",
    "pharmacy": "صيدلية",
    "laboratory": "مختبر",
    "radiology": "أشعة",

    # Insurance terms
    "insurance": "تأمين",
    "claim": "مطالبة",
    "copay": "مساهمة التأمين",
    "deductible": "المبلغ المقتطع",
    "premium": "قسط التأمين",
    "pre-authorization": "موافقة مسبقة",
    "referral": "إحالة",
    "coverage": "تغطية",
    "benefit": "منفعة",
    "policy": "بوليصة",
    "member": "عضو",
    "provider": "مقدم خدمة",
    "network": "شبكة",

    # Medical codes
    "ICD-10": "التصنيف الدولي للأمراض",
    "CPT": "رمز الإجراءات الطبية",
    "procedure code": "رمز الإجراء",
    "diagnosis code": "رمز التشخيص",

    # Clinical terms
    "inpatient": "مريض داخلي",
    "outpatient": "مريض خارجي",
    "admission": "إدخال",
    "discharge": "خروج",
    "consultation": "استشارة",
    "examination": "فحص",
    "medication": "دواء",
    "dosage": "جرعة",

    # Specialties
    "cardiology": "أمراض القلب",
    "dermatology": "أمراض جلدية",
    "neurology": "أمراض عصبية",
    "orthopedics": "عظام",
    "pediatrics": "طب أطفال",
    "psychiatry": "طب نفسي",
    "gynecology": "أمراض نسائية",
    "ophthalmology": "طب عيون",
    "dentistry": "طب أسنان",
}

# Reverse glossary
MEDICAL_GLOSSARY_AR_EN = {v: k for k, v in MEDICAL_GLOSSARY_EN_AR.items()}


class TranslationService:
    """
    Provides translation services for claims processing.

    Features:
    - English/Arabic bidirectional translation
    - Medical terminology handling
    - RTL text support
    - Document translation
    """

    def __init__(self):
        """Initialize TranslationService."""
        self._en_ar_glossary = MEDICAL_GLOSSARY_EN_AR.copy()
        self._ar_en_glossary = MEDICAL_GLOSSARY_AR_EN.copy()

    def get_text_direction(self, language: SupportedLanguage) -> TextDirection:
        """Get text direction for a language."""
        if language == SupportedLanguage.ARABIC:
            return TextDirection.RTL
        return TextDirection.LTR

    def detect_language(self, text: str) -> tuple[SupportedLanguage, float]:
        """
        Detect the language of text.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (detected_language, confidence)
        """
        # Simple heuristic: check for Arabic characters
        arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')
        arabic_chars = len(arabic_pattern.findall(text))
        total_chars = len(re.findall(r'\w', text))

        if total_chars == 0:
            return SupportedLanguage.ENGLISH, 0.5

        arabic_ratio = arabic_chars / total_chars

        if arabic_ratio > 0.3:
            return SupportedLanguage.ARABIC, min(1.0, arabic_ratio + 0.3)
        else:
            return SupportedLanguage.ENGLISH, min(1.0, 1 - arabic_ratio)

    async def translate_text(
        self,
        text: str,
        source_language: Optional[SupportedLanguage] = None,
        target_language: SupportedLanguage = SupportedLanguage.ENGLISH,
        use_glossary: bool = True,
    ) -> TranslatedText:
        """
        Translate text between languages.

        Args:
            text: Text to translate
            source_language: Source language (auto-detect if None)
            target_language: Target language
            use_glossary: Whether to use medical glossary

        Returns:
            TranslatedText with translation result
        """
        # Auto-detect source language if not provided
        if source_language is None:
            source_language, _ = self.detect_language(text)

        # Check if translation is needed
        if source_language == target_language:
            return TranslatedText(
                original_text=text,
                translated_text=text,
                source_language=source_language,
                target_language=target_language,
                confidence=1.0,
                text_direction=self.get_text_direction(target_language),
            )

        # Apply glossary translation
        translated = text
        glossary_applied = False
        is_medical = False

        if use_glossary:
            if source_language == SupportedLanguage.ENGLISH and target_language == SupportedLanguage.ARABIC:
                translated, was_applied, found_medical = self._apply_glossary(
                    text, self._en_ar_glossary
                )
                glossary_applied = was_applied
                is_medical = found_medical
            elif source_language == SupportedLanguage.ARABIC and target_language == SupportedLanguage.ENGLISH:
                translated, was_applied, found_medical = self._apply_glossary(
                    text, self._ar_en_glossary
                )
                glossary_applied = was_applied
                is_medical = found_medical

        # In production, this would call the translation gateway
        # For now, use glossary-based translation for known terms

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

    def _apply_glossary(
        self,
        text: str,
        glossary: dict[str, str],
    ) -> tuple[str, bool, bool]:
        """
        Apply glossary translations to text.

        Returns:
            Tuple of (translated_text, was_glossary_applied, found_medical_terms)
        """
        result = text
        was_applied = False
        found_medical = False

        # Sort by length (longest first) to avoid partial matches
        sorted_terms = sorted(glossary.keys(), key=len, reverse=True)

        for term in sorted_terms:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            if pattern.search(result):
                result = pattern.sub(glossary[term], result)
                was_applied = True
                found_medical = True

        return result, was_applied, found_medical

    async def translate_document(
        self,
        content: str,
        source_language: Optional[SupportedLanguage] = None,
        target_language: SupportedLanguage = SupportedLanguage.ENGLISH,
    ) -> DocumentTranslation:
        """
        Translate a document.

        Args:
            content: Document content
            source_language: Source language (auto-detect if None)
            target_language: Target language

        Returns:
            DocumentTranslation with full translation result
        """
        # Auto-detect source language
        if source_language is None:
            source_language, confidence = self.detect_language(content)
        else:
            confidence = 1.0

        # Translate the content
        translation = await self.translate_text(
            content,
            source_language,
            target_language,
        )

        # Find medical terms
        medical_terms = []
        glossary = (
            self._en_ar_glossary
            if source_language == SupportedLanguage.ENGLISH
            else self._ar_en_glossary
        )

        for term in glossary.keys():
            if term.lower() in content.lower():
                medical_terms.append(term)

        # Word count
        word_count = len(content.split())

        return DocumentTranslation(
            original_content=content,
            translated_content=translation.translated_text,
            source_language=source_language,
            target_language=target_language,
            word_count=word_count,
            medical_terms_found=medical_terms,
            confidence_score=translation.confidence,
        )

    async def translate_claim_fields(
        self,
        claim_data: dict,
        target_language: SupportedLanguage = SupportedLanguage.ARABIC,
    ) -> dict:
        """
        Translate claim fields to target language.

        Args:
            claim_data: Claim data dictionary
            target_language: Target language for translation

        Returns:
            Translated claim data
        """
        # Fields that should be translated
        translatable_fields = [
            "provider_name",
            "member_name",
            "diagnosis_description",
            "procedure_description",
            "notes",
            "remarks",
            "denial_reason",
        ]

        translated = claim_data.copy()

        for field in translatable_fields:
            if field in translated and translated[field]:
                result = await self.translate_text(
                    translated[field],
                    SupportedLanguage.ENGLISH,
                    target_language,
                )
                translated[f"{field}_translated"] = result.translated_text

        return translated

    def add_glossary_term(
        self,
        english_term: str,
        arabic_term: str,
    ) -> None:
        """Add a custom term to the glossary."""
        self._en_ar_glossary[english_term.lower()] = arabic_term
        self._ar_en_glossary[arabic_term] = english_term.lower()

    def get_glossary_terms(self) -> dict[str, str]:
        """Get current English to Arabic glossary."""
        return self._en_ar_glossary.copy()

    def wrap_rtl_text(self, text: str) -> str:
        """
        Wrap text with RTL markers for proper bidirectional display.

        Args:
            text: Arabic text to wrap

        Returns:
            Text wrapped with Unicode RTL markers
        """
        # Unicode Right-to-Left Embedding
        RLE = "\u202B"
        # Unicode Pop Directional Formatting
        PDF = "\u202C"

        return f"{RLE}{text}{PDF}"

    def format_bidirectional_text(
        self,
        arabic_text: str,
        english_text: str,
        separator: str = " - ",
    ) -> str:
        """
        Format mixed Arabic/English text for proper display.

        Args:
            arabic_text: Arabic portion
            english_text: English portion
            separator: Separator between texts

        Returns:
            Properly formatted bidirectional text
        """
        wrapped_arabic = self.wrap_rtl_text(arabic_text)
        return f"{wrapped_arabic}{separator}{english_text}"


# =============================================================================
# Factory Functions
# =============================================================================


_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get singleton TranslationService instance."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service


def create_translation_service() -> TranslationService:
    """Create a new TranslationService instance."""
    return TranslationService()
