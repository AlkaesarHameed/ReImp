"""
Insured Data Extractor (Rule 1).

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Extracts patient, member, and provider information from medical documents
using LLM with vision capabilities.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from src.schemas.llm_settings import LLMTaskType
from src.services.validation.llm_validation_service import (
    LLMValidationService,
    get_llm_validation_service,
)

logger = logging.getLogger(__name__)


class ExtractionConfidence(str, Enum):
    """Confidence level for extracted data."""

    HIGH = "high"           # 0.9-1.0 - Very confident
    MEDIUM = "medium"       # 0.7-0.9 - Reasonably confident
    LOW = "low"             # 0.5-0.7 - Some uncertainty
    VERY_LOW = "very_low"   # <0.5 - Low confidence


@dataclass
class PatientInfo:
    """Extracted patient information."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    date_of_birth: Optional[str] = None  # ISO format YYYY-MM-DD
    gender: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    ssn_last4: Optional[str] = None
    confidence: float = 0.0
    extraction_notes: list[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        """Get full name."""
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "middle_name": self.middle_name,
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth,
            "gender": self.gender,
            "address": {
                "line1": self.address_line1,
                "line2": self.address_line2,
                "city": self.city,
                "state": self.state,
                "zip_code": self.zip_code,
            },
            "phone": self.phone,
            "confidence": self.confidence,
        }


@dataclass
class ProviderInfo:
    """Extracted healthcare provider information."""

    name: Optional[str] = None
    npi: Optional[str] = None
    tax_id: Optional[str] = None
    specialty: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    provider_type: Optional[str] = None  # billing, rendering, referring
    confidence: float = 0.0
    extraction_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "npi": self.npi,
            "tax_id": self.tax_id,
            "specialty": self.specialty,
            "provider_type": self.provider_type,
            "address": {
                "line1": self.address_line1,
                "line2": self.address_line2,
                "city": self.city,
                "state": self.state,
                "zip_code": self.zip_code,
            },
            "phone": self.phone,
            "confidence": self.confidence,
        }


@dataclass
class PolicyInfo:
    """Extracted insurance policy information."""

    member_id: Optional[str] = None
    group_number: Optional[str] = None
    policy_number: Optional[str] = None
    plan_name: Optional[str] = None
    subscriber_name: Optional[str] = None
    subscriber_relationship: Optional[str] = None  # self, spouse, child, other
    payer_name: Optional[str] = None
    payer_id: Optional[str] = None
    effective_date: Optional[str] = None
    termination_date: Optional[str] = None
    confidence: float = 0.0
    extraction_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "member_id": self.member_id,
            "group_number": self.group_number,
            "policy_number": self.policy_number,
            "plan_name": self.plan_name,
            "subscriber_name": self.subscriber_name,
            "subscriber_relationship": self.subscriber_relationship,
            "payer_name": self.payer_name,
            "payer_id": self.payer_id,
            "effective_date": self.effective_date,
            "termination_date": self.termination_date,
            "confidence": self.confidence,
        }


@dataclass
class InsuredDataResult:
    """Complete insured data extraction result."""

    success: bool
    patient: PatientInfo
    billing_provider: Optional[ProviderInfo] = None
    rendering_provider: Optional[ProviderInfo] = None
    referring_provider: Optional[ProviderInfo] = None
    policy: Optional[PolicyInfo] = None
    secondary_policy: Optional[PolicyInfo] = None
    document_type: Optional[str] = None  # CMS-1500, UB-04, EOB, etc.
    document_date: Optional[str] = None
    overall_confidence: float = 0.0
    execution_time_ms: int = 0
    llm_provider_used: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_evidence_dict(self) -> dict[str, Any]:
        """Convert to evidence format."""
        return {
            "success": self.success,
            "document_type": self.document_type,
            "document_date": self.document_date,
            "overall_confidence": self.overall_confidence,
            "patient": self.patient.to_dict() if self.patient else None,
            "billing_provider": self.billing_provider.to_dict() if self.billing_provider else None,
            "rendering_provider": self.rendering_provider.to_dict() if self.rendering_provider else None,
            "policy": self.policy.to_dict() if self.policy else None,
            "warnings": self.warnings,
            "errors": self.errors,
        }


# System prompt for data extraction
INSURED_DATA_SYSTEM_PROMPT = """You are an expert medical billing specialist with deep knowledge of:
- Healthcare claim forms (CMS-1500, UB-04)
- Medical document standards (HIPAA, EDI)
- Patient and provider identification
- Insurance policy structures

Your role is to accurately extract structured data from medical documents.
Be precise with:
- Names (exact spelling)
- Dates (convert to YYYY-MM-DD format)
- IDs (member IDs, NPIs, group numbers)
- Addresses (complete and accurate)

If a field is not visible or unclear, set it to null.
Include confidence scores for each extracted section."""


INSURED_DATA_PROMPT = """Extract the following information from this medical document:

1. PATIENT INFORMATION:
   - Full name (first, middle, last)
   - Date of birth
   - Gender
   - Address
   - Phone number

2. PROVIDER INFORMATION:
   - Billing provider (name, NPI, address, tax ID)
   - Rendering provider (name, NPI, specialty)
   - Referring provider (if present)

3. INSURANCE/POLICY INFORMATION:
   - Member ID / Subscriber ID
   - Group number
   - Policy number
   - Payer name and ID
   - Plan name
   - Subscriber relationship to patient

4. DOCUMENT INFORMATION:
   - Document type (CMS-1500, UB-04, EOB, medical record, etc.)
   - Document date

Return the data as JSON with this structure:
{{
    "document_type": "CMS-1500|UB-04|EOB|medical_record|other",
    "document_date": "YYYY-MM-DD or null",
    "patient": {{
        "first_name": "string or null",
        "last_name": "string or null",
        "middle_name": "string or null",
        "date_of_birth": "YYYY-MM-DD or null",
        "gender": "M|F|U or null",
        "address_line1": "string or null",
        "address_line2": "string or null",
        "city": "string or null",
        "state": "string (2-letter) or null",
        "zip_code": "string or null",
        "phone": "string or null",
        "confidence": 0.0 to 1.0
    }},
    "billing_provider": {{
        "name": "string or null",
        "npi": "10-digit string or null",
        "tax_id": "string or null",
        "specialty": "string or null",
        "address_line1": "string or null",
        "city": "string or null",
        "state": "string (2-letter) or null",
        "zip_code": "string or null",
        "phone": "string or null",
        "confidence": 0.0 to 1.0
    }},
    "rendering_provider": {{
        "name": "string or null",
        "npi": "10-digit string or null",
        "specialty": "string or null",
        "confidence": 0.0 to 1.0
    }},
    "referring_provider": {{
        "name": "string or null",
        "npi": "10-digit string or null",
        "confidence": 0.0 to 1.0
    }},
    "policy": {{
        "member_id": "string or null",
        "group_number": "string or null",
        "policy_number": "string or null",
        "plan_name": "string or null",
        "payer_name": "string or null",
        "payer_id": "string or null",
        "subscriber_name": "string or null",
        "subscriber_relationship": "self|spouse|child|other or null",
        "effective_date": "YYYY-MM-DD or null",
        "confidence": 0.0 to 1.0
    }},
    "warnings": ["List of any extraction concerns"],
    "overall_confidence": 0.0 to 1.0
}}

Document content to analyze:
{document_content}"""


INSURED_DATA_VISION_PROMPT = """Analyze this medical document image and extract:

1. PATIENT INFORMATION:
   - Full name (first, middle, last)
   - Date of birth
   - Gender
   - Address
   - Phone number

2. PROVIDER INFORMATION:
   - Billing provider (name, NPI, address, tax ID)
   - Rendering provider (name, NPI, specialty)
   - Referring provider (if present)

3. INSURANCE/POLICY INFORMATION:
   - Member ID / Subscriber ID
   - Group number
   - Policy number
   - Payer name and ID
   - Plan name
   - Subscriber relationship to patient

4. DOCUMENT INFORMATION:
   - Document type (CMS-1500, UB-04, EOB, medical record, etc.)
   - Document date

Return the data as JSON with the following structure. Use null for any field that is not visible or unclear:
{{
    "document_type": "CMS-1500|UB-04|EOB|medical_record|other",
    "document_date": "YYYY-MM-DD or null",
    "patient": {{
        "first_name": "string or null",
        "last_name": "string or null",
        "middle_name": "string or null",
        "date_of_birth": "YYYY-MM-DD or null",
        "gender": "M|F|U or null",
        "address_line1": "string or null",
        "address_line2": "string or null",
        "city": "string or null",
        "state": "string (2-letter) or null",
        "zip_code": "string or null",
        "phone": "string or null",
        "confidence": 0.0 to 1.0
    }},
    "billing_provider": {{
        "name": "string or null",
        "npi": "10-digit string or null",
        "tax_id": "string or null",
        "specialty": "string or null",
        "address_line1": "string or null",
        "city": "string or null",
        "state": "string (2-letter) or null",
        "zip_code": "string or null",
        "phone": "string or null",
        "confidence": 0.0 to 1.0
    }},
    "rendering_provider": {{
        "name": "string or null",
        "npi": "10-digit string or null",
        "specialty": "string or null",
        "confidence": 0.0 to 1.0
    }},
    "referring_provider": {{
        "name": "string or null",
        "npi": "10-digit string or null",
        "confidence": 0.0 to 1.0
    }},
    "policy": {{
        "member_id": "string or null",
        "group_number": "string or null",
        "policy_number": "string or null",
        "plan_name": "string or null",
        "payer_name": "string or null",
        "payer_id": "string or null",
        "subscriber_name": "string or null",
        "subscriber_relationship": "self|spouse|child|other or null",
        "effective_date": "YYYY-MM-DD or null",
        "confidence": 0.0 to 1.0
    }},
    "warnings": ["List of any extraction concerns"],
    "overall_confidence": 0.0 to 1.0
}}"""


class InsuredDataExtractor:
    """
    Extracts insured/patient data from medical documents.

    Uses LLM with vision capabilities to extract:
    - Patient demographic information
    - Provider information (billing, rendering, referring)
    - Insurance policy information

    Source: Design Document Section 2.2 - Validation Rules (Rule 1)
    """

    def __init__(
        self,
        llm_service: Optional[LLMValidationService] = None,
    ):
        """
        Initialize the insured data extractor.

        Args:
            llm_service: LLM validation service for extraction
        """
        self._llm_service = llm_service

    @property
    def llm_service(self) -> LLMValidationService:
        """Get LLM service instance."""
        if self._llm_service is None:
            self._llm_service = get_llm_validation_service()
        return self._llm_service

    async def extract_from_text(
        self,
        document_content: str,
        tenant_id: Optional[UUID] = None,
    ) -> InsuredDataResult:
        """
        Extract insured data from document text.

        Args:
            document_content: OCR'd or text content of the document
            tenant_id: Tenant ID for LLM configuration

        Returns:
            InsuredDataResult with extracted data
        """
        import time
        start_time = time.perf_counter()

        if not document_content or len(document_content.strip()) < 50:
            return InsuredDataResult(
                success=False,
                patient=PatientInfo(),
                errors=["Document content is too short or empty"],
                execution_time_ms=0,
            )

        # Build prompt
        prompt = INSURED_DATA_PROMPT.format(document_content=document_content)

        # Generate cache key
        cache_key = self._generate_cache_key(document_content)

        # Call LLM
        llm_result = await self.llm_service.complete(
            prompt=prompt,
            system_prompt=INSURED_DATA_SYSTEM_PROMPT,
            task_type=LLMTaskType.EXTRACTION,
            tenant_id=tenant_id,
            json_mode=True,
            cache_key=cache_key,
        )

        execution_time = int((time.perf_counter() - start_time) * 1000)

        if not llm_result.success or not llm_result.parsed_data:
            logger.error(f"Insured data extraction failed: {llm_result.error}")
            return InsuredDataResult(
                success=False,
                patient=PatientInfo(),
                errors=[f"Extraction failed: {llm_result.error}"],
                execution_time_ms=execution_time,
            )

        # Parse LLM response
        result = self._parse_extraction_response(
            llm_result.parsed_data,
            execution_time,
            llm_result.provider_used,
        )

        logger.info(
            f"Insured data extraction: success={result.success}, "
            f"confidence={result.overall_confidence:.2f}, "
            f"time={execution_time}ms"
        )

        return result

    async def extract_from_image(
        self,
        image_data: bytes,
        media_type: str = "image/png",
        tenant_id: Optional[UUID] = None,
    ) -> InsuredDataResult:
        """
        Extract insured data from a document image.

        Args:
            image_data: Raw image bytes
            media_type: MIME type of the image
            tenant_id: Tenant ID for LLM configuration

        Returns:
            InsuredDataResult with extracted data
        """
        import time
        from src.gateways.llm_gateway import LLMRequest

        start_time = time.perf_counter()

        if not image_data:
            return InsuredDataResult(
                success=False,
                patient=PatientInfo(),
                errors=["No image data provided"],
                execution_time_ms=0,
            )

        # Create vision request
        request = LLMRequest.with_image(
            prompt=INSURED_DATA_VISION_PROMPT,
            image_data=image_data,
            media_type=media_type,
            system_prompt=INSURED_DATA_SYSTEM_PROMPT,
        )
        request.json_mode = True
        request.temperature = 0.1

        try:
            from src.gateways.llm_gateway import get_llm_gateway

            gateway = get_llm_gateway()
            if not gateway._initialized:
                await gateway.initialize()

            result = await gateway.execute(request)

            execution_time = int((time.perf_counter() - start_time) * 1000)

            if not result.success or not result.data:
                return InsuredDataResult(
                    success=False,
                    patient=PatientInfo(),
                    errors=[f"Vision extraction failed: {result.error}"],
                    execution_time_ms=execution_time,
                )

            # Parse response
            parsed_data = result.data.parse_json()
            extraction_result = self._parse_extraction_response(
                parsed_data,
                execution_time,
                result.data.provider,
            )

            logger.info(
                f"Insured data vision extraction: success={extraction_result.success}, "
                f"confidence={extraction_result.overall_confidence:.2f}, "
                f"time={execution_time}ms"
            )

            return extraction_result

        except Exception as e:
            execution_time = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"Vision extraction error: {e}")
            return InsuredDataResult(
                success=False,
                patient=PatientInfo(),
                errors=[f"Vision extraction error: {str(e)}"],
                execution_time_ms=execution_time,
            )

    def _generate_cache_key(self, content: str) -> str:
        """Generate cache key for extraction request."""
        content_hash = hashlib.md5(content[:5000].encode()).hexdigest()
        return f"extract:insured:{content_hash}"

    def _parse_extraction_response(
        self,
        data: dict,
        execution_time: int,
        provider_used: str,
    ) -> InsuredDataResult:
        """Parse LLM response into structured result."""
        try:
            # Parse patient info
            patient_data = data.get("patient", {})
            patient = PatientInfo(
                first_name=patient_data.get("first_name"),
                last_name=patient_data.get("last_name"),
                middle_name=patient_data.get("middle_name"),
                date_of_birth=patient_data.get("date_of_birth"),
                gender=patient_data.get("gender"),
                address_line1=patient_data.get("address_line1"),
                address_line2=patient_data.get("address_line2"),
                city=patient_data.get("city"),
                state=patient_data.get("state"),
                zip_code=patient_data.get("zip_code"),
                phone=patient_data.get("phone"),
                confidence=float(patient_data.get("confidence", 0.5)),
            )

            # Parse billing provider
            billing_data = data.get("billing_provider", {})
            billing_provider = None
            if billing_data and any(billing_data.values()):
                billing_provider = ProviderInfo(
                    name=billing_data.get("name"),
                    npi=billing_data.get("npi"),
                    tax_id=billing_data.get("tax_id"),
                    specialty=billing_data.get("specialty"),
                    address_line1=billing_data.get("address_line1"),
                    city=billing_data.get("city"),
                    state=billing_data.get("state"),
                    zip_code=billing_data.get("zip_code"),
                    phone=billing_data.get("phone"),
                    provider_type="billing",
                    confidence=float(billing_data.get("confidence", 0.5)),
                )

            # Parse rendering provider
            rendering_data = data.get("rendering_provider", {})
            rendering_provider = None
            if rendering_data and any(rendering_data.values()):
                rendering_provider = ProviderInfo(
                    name=rendering_data.get("name"),
                    npi=rendering_data.get("npi"),
                    specialty=rendering_data.get("specialty"),
                    provider_type="rendering",
                    confidence=float(rendering_data.get("confidence", 0.5)),
                )

            # Parse referring provider
            referring_data = data.get("referring_provider", {})
            referring_provider = None
            if referring_data and any(referring_data.values()):
                referring_provider = ProviderInfo(
                    name=referring_data.get("name"),
                    npi=referring_data.get("npi"),
                    provider_type="referring",
                    confidence=float(referring_data.get("confidence", 0.5)),
                )

            # Parse policy info
            policy_data = data.get("policy", {})
            policy = None
            if policy_data and any(policy_data.values()):
                policy = PolicyInfo(
                    member_id=policy_data.get("member_id"),
                    group_number=policy_data.get("group_number"),
                    policy_number=policy_data.get("policy_number"),
                    plan_name=policy_data.get("plan_name"),
                    payer_name=policy_data.get("payer_name"),
                    payer_id=policy_data.get("payer_id"),
                    subscriber_name=policy_data.get("subscriber_name"),
                    subscriber_relationship=policy_data.get("subscriber_relationship"),
                    effective_date=policy_data.get("effective_date"),
                    confidence=float(policy_data.get("confidence", 0.5)),
                )

            overall_confidence = float(data.get("overall_confidence", 0.5))
            warnings = data.get("warnings", [])

            return InsuredDataResult(
                success=True,
                patient=patient,
                billing_provider=billing_provider,
                rendering_provider=rendering_provider,
                referring_provider=referring_provider,
                policy=policy,
                document_type=data.get("document_type"),
                document_date=data.get("document_date"),
                overall_confidence=overall_confidence,
                execution_time_ms=execution_time,
                llm_provider_used=provider_used,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Error parsing extraction response: {e}")
            return InsuredDataResult(
                success=False,
                patient=PatientInfo(),
                errors=[f"Parse error: {str(e)}"],
                execution_time_ms=execution_time,
                llm_provider_used=provider_used,
            )

    async def validate_npi(self, npi: str) -> bool:
        """
        Validate NPI format using Luhn check digit.

        Args:
            npi: 10-digit NPI number

        Returns:
            True if valid NPI format
        """
        if not npi or len(npi) != 10 or not npi.isdigit():
            return False

        # NPI validation using Luhn algorithm
        # Prefix with 80840 for health care provider identifier
        prefixed = "80840" + npi[:9]

        total = 0
        for i, digit in enumerate(prefixed):
            d = int(digit)
            if i % 2 == 0:
                d *= 2
                if d > 9:
                    d -= 9
            total += d

        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(npi[9])


# Singleton instance
_insured_data_extractor: Optional[InsuredDataExtractor] = None


def get_insured_data_extractor() -> InsuredDataExtractor:
    """Get or create the singleton insured data extractor."""
    global _insured_data_extractor
    if _insured_data_extractor is None:
        _insured_data_extractor = InsuredDataExtractor()
    return _insured_data_extractor
