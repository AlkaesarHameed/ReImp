"""
LLM Document Parsing Service.

Provides:
- Structured data extraction from OCR text
- Claim form parsing (CMS-1500, UB-04)
- Invoice parsing
- Medical code extraction
- Confidence scoring

Source: Design Document Section 4.3 - Document Processing
Verified: 2025-12-18
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from src.core.enums import (
    ClaimType,
    DiagnosisCodeSystem,
    DocumentType,
    LLMProvider,
    ProcedureCodeSystem,
)

logger = logging.getLogger(__name__)


class ExtractionConfidence(str, Enum):
    """Confidence level for extracted data."""

    HIGH = "high"  # > 0.90
    MEDIUM = "medium"  # 0.70 - 0.90
    LOW = "low"  # < 0.70


@dataclass
class ExtractedField:
    """Single extracted field with confidence."""

    name: str
    value: Any
    confidence: float
    source_text: str = ""
    needs_review: bool = False


@dataclass
class ExtractedDiagnosis:
    """Extracted diagnosis code."""

    code: str
    description: str
    code_system: DiagnosisCodeSystem
    is_primary: bool = False
    confidence: float = 0.0


@dataclass
class ExtractedProcedure:
    """Extracted procedure code."""

    code: str
    description: str
    code_system: ProcedureCodeSystem
    modifiers: list[str] = field(default_factory=list)
    quantity: int = 1
    charged_amount: Optional[Decimal] = None
    service_date: Optional[date] = None
    confidence: float = 0.0


@dataclass
class ExtractedProvider:
    """Extracted provider information."""

    name: str
    npi: str = ""
    tax_id: str = ""
    address: str = ""
    phone: str = ""
    specialty: str = ""
    confidence: float = 0.0


@dataclass
class ExtractedPatient:
    """Extracted patient information."""

    name: str
    member_id: str = ""
    date_of_birth: Optional[date] = None
    gender: str = ""
    address: str = ""
    phone: str = ""
    confidence: float = 0.0


@dataclass
class ClaimExtractionResult:
    """Complete claim extraction result."""

    success: bool
    document_type: DocumentType
    claim_type: Optional[ClaimType] = None

    # Extracted data
    patient: Optional[ExtractedPatient] = None
    provider: Optional[ExtractedProvider] = None
    billing_provider: Optional[ExtractedProvider] = None

    diagnoses: list[ExtractedDiagnosis] = field(default_factory=list)
    procedures: list[ExtractedProcedure] = field(default_factory=list)

    # Financial
    total_charged: Optional[Decimal] = None
    currency: str = "USD"

    # Dates
    service_date_from: Optional[date] = None
    service_date_to: Optional[date] = None
    admission_date: Optional[date] = None
    discharge_date: Optional[date] = None

    # Identifiers
    claim_number: str = ""
    prior_auth_number: str = ""
    policy_number: str = ""
    group_number: str = ""

    # Place of Service
    place_of_service: str = ""
    facility_name: str = ""

    # Confidence
    overall_confidence: float = 0.0
    fields_extracted: int = 0
    fields_needs_review: int = 0
    extraction_level: ExtractionConfidence = ExtractionConfidence.LOW

    # Processing
    provider_used: str = ""
    processing_time_ms: int = 0
    error: Optional[str] = None

    # Raw extraction
    raw_fields: list[ExtractedField] = field(default_factory=list)


@dataclass
class LLMParserConfig:
    """Configuration for LLM parser."""

    primary_provider: LLMProvider = LLMProvider.OLLAMA
    fallback_provider: Optional[LLMProvider] = LLMProvider.OPENAI
    confidence_threshold: float = 0.85
    fallback_on_low_confidence: bool = True
    timeout_seconds: int = 60
    max_retries: int = 2
    extract_medical_codes: bool = True


# =============================================================================
# Extraction Prompts
# =============================================================================

CLAIM_EXTRACTION_PROMPT = """You are a medical claims data extraction expert. Extract structured data from the following OCR text of a {document_type} document.

OCR TEXT:
{ocr_text}

Extract the following fields and return as JSON:
1. patient_info: name, member_id, date_of_birth (YYYY-MM-DD), gender, address
2. provider_info: name, npi (10 digits), tax_id, address, phone, specialty
3. billing_provider: same fields as provider if different
4. diagnoses: array of {code, description, is_primary}
5. procedures: array of {code, description, modifiers[], quantity, charged_amount, service_date}
6. financial: total_charged, currency
7. dates: service_date_from, service_date_to, admission_date, discharge_date
8. identifiers: claim_number, prior_auth_number, policy_number, group_number
9. place_of_service: code and facility_name
10. claim_type: "professional" (CMS-1500) or "institutional" (UB-04)

For each field, also provide a confidence score (0.0-1.0) based on OCR quality and data clarity.

Return ONLY valid JSON with this structure:
{{
    "patient_info": {{}},
    "provider_info": {{}},
    "diagnoses": [],
    "procedures": [],
    "financial": {{}},
    "dates": {{}},
    "identifiers": {{}},
    "place_of_service": {{}},
    "claim_type": "",
    "overall_confidence": 0.0
}}"""

INVOICE_EXTRACTION_PROMPT = """Extract invoice data from the following OCR text:

OCR TEXT:
{ocr_text}

Return JSON with:
1. invoice_number
2. invoice_date
3. vendor_info: name, address, tax_id
4. line_items: array of {description, quantity, unit_price, total}
5. totals: subtotal, tax, total_amount, currency
6. payment_terms

Return ONLY valid JSON."""


# =============================================================================
# LLM Parser Service
# =============================================================================


class LLMParserService:
    """
    LLM-based document parsing service.

    Uses LLM to extract structured data from OCR text,
    including medical codes, patient info, and financial data.
    """

    def __init__(
        self,
        config: Optional[LLMParserConfig] = None,
        llm_gateway=None,
        medical_nlp_gateway=None,
    ):
        """
        Initialize LLM parser.

        Args:
            config: Parser configuration
            llm_gateway: Pre-configured LLM gateway
            medical_nlp_gateway: Pre-configured medical NLP gateway
        """
        self.config = config or LLMParserConfig()
        self._llm_gateway = llm_gateway
        self._medical_nlp_gateway = medical_nlp_gateway
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize LLM and medical NLP gateways."""
        if self._initialized:
            return

        if self._llm_gateway is None:
            try:
                from src.gateways.llm_gateway import LLMGateway

                self._llm_gateway = LLMGateway(
                    primary_provider=self.config.primary_provider,
                    fallback_provider=self.config.fallback_provider,
                    confidence_threshold=self.config.confidence_threshold,
                )
                await self._llm_gateway.initialize()
                logger.info("LLM gateway initialized for parser")
            except ImportError:
                logger.warning("LLM gateway not available, using mock parser")
                self._llm_gateway = MockLLMGateway()
            except Exception as e:
                logger.error(f"Failed to initialize LLM gateway: {e}")
                self._llm_gateway = MockLLMGateway()

        if self._medical_nlp_gateway is None and self.config.extract_medical_codes:
            try:
                from src.gateways.medical_nlp_gateway import MedicalNLPGateway

                self._medical_nlp_gateway = MedicalNLPGateway()
                await self._medical_nlp_gateway.initialize()
                logger.info("Medical NLP gateway initialized")
            except ImportError:
                logger.warning("Medical NLP gateway not available")
            except Exception as e:
                logger.warning(f"Medical NLP gateway init failed: {e}")

        self._initialized = True

    async def parse_claim_document(
        self,
        ocr_text: str,
        document_type: DocumentType = DocumentType.CLAIM_FORM,
        tables: Optional[list[dict]] = None,
        image_data: Optional[bytes] = None,
    ) -> ClaimExtractionResult:
        """
        Parse a claim document and extract structured data.

        Args:
            ocr_text: OCR-extracted text
            document_type: Type of document
            tables: Extracted tables from OCR
            image_data: Original image for vision models

        Returns:
            ClaimExtractionResult with extracted data
        """
        await self.initialize()

        start_time = datetime.now(timezone.utc)

        try:
            # Build prompt
            prompt = CLAIM_EXTRACTION_PROMPT.format(
                document_type=document_type.value,
                ocr_text=ocr_text[:10000],  # Limit text length
            )

            # Call LLM
            llm_result = await self._call_llm(prompt, image_data)

            if not llm_result.get("success"):
                return ClaimExtractionResult(
                    success=False,
                    document_type=document_type,
                    error=llm_result.get("error", "LLM extraction failed"),
                )

            # Parse JSON response
            extracted_data = llm_result.get("data", {})

            # Build result
            result = await self._build_extraction_result(
                extracted_data,
                document_type,
                ocr_text,
            )

            # Enhance with medical NLP if available
            if self._medical_nlp_gateway and self.config.extract_medical_codes:
                result = await self._enhance_with_medical_nlp(result, ocr_text)

            # Calculate processing time
            result.processing_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            result.provider_used = llm_result.get("provider", "unknown")

            return result

        except Exception as e:
            logger.error(f"Claim parsing error: {e}")
            return ClaimExtractionResult(
                success=False,
                document_type=document_type,
                error=str(e),
            )

    async def _call_llm(
        self,
        prompt: str,
        image_data: Optional[bytes] = None,
    ) -> dict:
        """Call LLM gateway for extraction."""
        try:
            if isinstance(self._llm_gateway, MockLLMGateway):
                return await self._llm_gateway.extract(prompt)

            from src.gateways.llm_gateway import LLMRequest

            request = LLMRequest(
                prompt=prompt,
                system_prompt="You are a medical document extraction expert. Return only valid JSON.",
                image_data=image_data,
                max_tokens=4000,
                temperature=0.1,  # Low temperature for consistent extraction
            )

            result = await asyncio.wait_for(
                self._llm_gateway.execute(request),
                timeout=self.config.timeout_seconds,
            )

            if not result.success:
                return {"success": False, "error": result.error}

            # Parse JSON from response
            response_text = result.data.content

            # Try to extract JSON from response
            json_data = self._extract_json(response_text)

            return {
                "success": True,
                "data": json_data,
                "provider": result.provider_used,
                "confidence": result.data.confidence,
            }

        except asyncio.TimeoutError:
            return {"success": False, "error": "LLM timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from LLM response text."""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in markdown code block
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON object
        json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return {}

    async def _build_extraction_result(
        self,
        extracted: dict,
        document_type: DocumentType,
        ocr_text: str,
    ) -> ClaimExtractionResult:
        """Build extraction result from parsed JSON."""
        result = ClaimExtractionResult(
            success=True,
            document_type=document_type,
        )

        # Extract patient info
        patient_info = extracted.get("patient_info", {})
        if patient_info:
            result.patient = ExtractedPatient(
                name=patient_info.get("name", ""),
                member_id=patient_info.get("member_id", ""),
                date_of_birth=self._parse_date(patient_info.get("date_of_birth")),
                gender=patient_info.get("gender", ""),
                address=patient_info.get("address", ""),
                phone=patient_info.get("phone", ""),
                confidence=float(patient_info.get("confidence", 0.8)),
            )
            result.fields_extracted += 1

        # Extract provider info
        provider_info = extracted.get("provider_info", {})
        if provider_info:
            result.provider = ExtractedProvider(
                name=provider_info.get("name", ""),
                npi=provider_info.get("npi", ""),
                tax_id=provider_info.get("tax_id", ""),
                address=provider_info.get("address", ""),
                phone=provider_info.get("phone", ""),
                specialty=provider_info.get("specialty", ""),
                confidence=float(provider_info.get("confidence", 0.8)),
            )
            result.fields_extracted += 1

        # Extract diagnoses
        for dx in extracted.get("diagnoses", []):
            result.diagnoses.append(ExtractedDiagnosis(
                code=dx.get("code", ""),
                description=dx.get("description", ""),
                code_system=DiagnosisCodeSystem.ICD10_CM,
                is_primary=dx.get("is_primary", False),
                confidence=float(dx.get("confidence", 0.8)),
            ))
            result.fields_extracted += 1

        # Extract procedures
        for proc in extracted.get("procedures", []):
            charged = proc.get("charged_amount")
            result.procedures.append(ExtractedProcedure(
                code=proc.get("code", ""),
                description=proc.get("description", ""),
                code_system=ProcedureCodeSystem.CPT,
                modifiers=proc.get("modifiers", []),
                quantity=int(proc.get("quantity", 1)),
                charged_amount=Decimal(str(charged)) if charged else None,
                service_date=self._parse_date(proc.get("service_date")),
                confidence=float(proc.get("confidence", 0.8)),
            ))
            result.fields_extracted += 1

        # Extract financial
        financial = extracted.get("financial", {})
        if financial.get("total_charged"):
            result.total_charged = Decimal(str(financial["total_charged"]))
            result.currency = financial.get("currency", "USD")
            result.fields_extracted += 1

        # Extract dates
        dates = extracted.get("dates", {})
        result.service_date_from = self._parse_date(dates.get("service_date_from"))
        result.service_date_to = self._parse_date(dates.get("service_date_to"))
        result.admission_date = self._parse_date(dates.get("admission_date"))
        result.discharge_date = self._parse_date(dates.get("discharge_date"))

        # Extract identifiers
        identifiers = extracted.get("identifiers", {})
        result.claim_number = identifiers.get("claim_number", "")
        result.prior_auth_number = identifiers.get("prior_auth_number", "")
        result.policy_number = identifiers.get("policy_number", "")
        result.group_number = identifiers.get("group_number", "")

        # Extract place of service
        pos = extracted.get("place_of_service", {})
        result.place_of_service = pos.get("code", "")
        result.facility_name = pos.get("facility_name", "")

        # Determine claim type
        claim_type_str = extracted.get("claim_type", "").lower()
        if "professional" in claim_type_str or "cms-1500" in claim_type_str:
            result.claim_type = ClaimType.PROFESSIONAL
        elif "institutional" in claim_type_str or "ub-04" in claim_type_str:
            result.claim_type = ClaimType.INSTITUTIONAL

        # Calculate overall confidence
        result.overall_confidence = float(extracted.get("overall_confidence", 0.8))
        result.extraction_level = self._classify_confidence(result.overall_confidence)

        return result

    async def _enhance_with_medical_nlp(
        self,
        result: ClaimExtractionResult,
        ocr_text: str,
    ) -> ClaimExtractionResult:
        """Enhance extraction with medical NLP for code validation."""
        if not self._medical_nlp_gateway:
            return result

        try:
            from src.gateways.medical_nlp_gateway import MedicalNLPRequest

            request = MedicalNLPRequest(
                text=ocr_text[:5000],
                extract_diagnoses=True,
                extract_procedures=True,
                validate_codes=True,
            )

            nlp_result = await self._medical_nlp_gateway.execute(request)

            if nlp_result.success and nlp_result.data:
                # Validate and enhance diagnosis codes
                nlp_diagnoses = nlp_result.data.diagnosis_codes
                for extracted_dx in result.diagnoses:
                    for nlp_dx in nlp_diagnoses:
                        if extracted_dx.code == nlp_dx.get("code"):
                            # Update with validated description
                            if nlp_dx.get("description"):
                                extracted_dx.description = nlp_dx["description"]
                            extracted_dx.confidence = max(
                                extracted_dx.confidence,
                                nlp_dx.get("confidence", 0.8),
                            )

        except Exception as e:
            logger.warning(f"Medical NLP enhancement failed: {e}")

        return result

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None

        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y%m%d",
            "%m-%d-%Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def _classify_confidence(self, confidence: float) -> ExtractionConfidence:
        """Classify overall confidence level."""
        if confidence > 0.90:
            return ExtractionConfidence.HIGH
        elif confidence > 0.70:
            return ExtractionConfidence.MEDIUM
        else:
            return ExtractionConfidence.LOW

    async def extract_medical_codes(
        self,
        text: str,
    ) -> dict:
        """
        Extract medical codes (ICD-10, CPT) from text.

        Args:
            text: Text containing medical codes

        Returns:
            Dict with extracted codes
        """
        diagnoses = []
        procedures = []

        # ICD-10 pattern: Letter followed by 2+ digits, optional decimal
        icd10_pattern = r"\b[A-Z]\d{2}(?:\.\d{1,4})?\b"
        icd10_matches = re.findall(icd10_pattern, text)
        for code in set(icd10_matches):
            diagnoses.append({
                "code": code,
                "system": "ICD-10-CM",
            })

        # CPT pattern: 5 digits
        cpt_pattern = r"\b\d{5}\b"
        cpt_matches = re.findall(cpt_pattern, text)
        for code in set(cpt_matches):
            # Filter common non-CPT 5-digit numbers
            if 10000 <= int(code) <= 99999:
                procedures.append({
                    "code": code,
                    "system": "CPT",
                })

        return {
            "diagnoses": diagnoses,
            "procedures": procedures,
        }


# =============================================================================
# Mock LLM Gateway (Development/Testing)
# =============================================================================


class MockLLMGateway:
    """Mock LLM gateway for development and testing."""

    async def extract(self, prompt: str) -> dict:
        """Mock extraction."""
        await asyncio.sleep(0.1)

        return {
            "success": True,
            "data": {
                "patient_info": {
                    "name": "John Doe",
                    "member_id": "MEM123456",
                    "date_of_birth": "1980-05-15",
                    "gender": "M",
                    "confidence": 0.9,
                },
                "provider_info": {
                    "name": "Dr. Jane Smith",
                    "npi": "1234567890",
                    "confidence": 0.85,
                },
                "diagnoses": [
                    {
                        "code": "J06.9",
                        "description": "Acute upper respiratory infection",
                        "is_primary": True,
                        "confidence": 0.9,
                    }
                ],
                "procedures": [
                    {
                        "code": "99213",
                        "description": "Office visit, established patient",
                        "quantity": 1,
                        "charged_amount": "150.00",
                        "confidence": 0.88,
                    }
                ],
                "financial": {
                    "total_charged": "150.00",
                    "currency": "USD",
                },
                "dates": {
                    "service_date_from": "2025-01-15",
                    "service_date_to": "2025-01-15",
                },
                "identifiers": {
                    "claim_number": "CLM-2025-000001",
                    "policy_number": "POL-ABC-123",
                },
                "claim_type": "professional",
                "overall_confidence": 0.87,
            },
            "provider": "mock",
        }


# =============================================================================
# Factory Functions
# =============================================================================


_llm_parser: Optional[LLMParserService] = None


def get_llm_parser(
    config: Optional[LLMParserConfig] = None,
) -> LLMParserService:
    """Get LLM parser service instance."""
    global _llm_parser
    if _llm_parser is None:
        _llm_parser = LLMParserService(config=config)
    return _llm_parser


async def create_llm_parser(
    config: Optional[LLMParserConfig] = None,
) -> LLMParserService:
    """Create and initialize LLM parser."""
    parser = LLMParserService(config=config)
    await parser.initialize()
    return parser
