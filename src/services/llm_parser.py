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
import decimal
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
class ExtractedLineItem:
    """Extracted invoice line item (medications, supplies, services)."""

    sl_no: int = 0
    date: Optional[date] = None
    description: str = ""
    sac_code: str = ""
    quantity: float = 1.0
    rate: Optional[Decimal] = None
    gross_value: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    total_value: Optional[Decimal] = None
    category: str = ""  # e.g., "Inventory Item", "Service", "Surgeon Fees"
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
    line_items: list[ExtractedLineItem] = field(default_factory=list)

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
    timeout_seconds: int = 300  # Increased to 5 minutes for vision models
    max_retries: int = 2
    extract_medical_codes: bool = True


# =============================================================================
# Extraction Prompts
# =============================================================================

CLAIM_EXTRACTION_PROMPT = """You are a medical claims and invoice data extraction expert. Extract ALL structured data from the following {document_type} document.

{ocr_text_section}

=== CRITICAL INSTRUCTIONS - READ CAREFULLY ===

**IMPORTANT: UNDERSTAND THE DIFFERENCE BETWEEN PROCEDURES AND LINE_ITEMS**

1. **line_items** = ALL itemized charges from invoices/bills (medications, supplies, room charges, tests, fees, etc.)
   - This is the MAIN array for hospital bills and invoices
   - Extract EVERY SINGLE ROW from the billing table
   - Includes: medicines, injections, needles, syringes, bed charges, surgery fees, lab tests, etc.

2. **procedures** = Medical/surgical procedures with CPT codes (e.g., 99213 Office Visit, 43239 Endoscopy)
   - Only for formal medical procedure codes
   - Usually NOT present in simple invoices/bills
   - Leave EMPTY if the document is an itemized bill without CPT codes

=== LINE ITEMS EXTRACTION (MOST IMPORTANT) ===

For invoices/hospital bills, extract EVERY ROW from the itemized table into line_items:
- Medications/drugs (e.g., "PARACETAMOL 500MG", "OFLOX 4MG INJ")
- Medical supplies (e.g., "NEEDLE 18X1.5G", "SYRINGE 5ML", "IV CANNULA")
- Lab tests (e.g., "BLOOD TEST", "URINE ANALYSIS")
- Room charges (e.g., "BED CHARGE", "ICU CHARGE")
- Doctor fees (e.g., "SURGEON FEES", "CONSULTATION")
- Services (e.g., "NURSING CARE", "OT CHARGES")
- Any other itemized charge

For each LINE ITEM extract:
- sl_no: Row/serial number from table (1, 2, 3...)
- date: Service date
- description: Item name/description
- sac_code: SAC/HSN code or item code (e.g., "9018", "3004")
- quantity: Qty (default 1)
- rate: Unit rate/price
- gross_value: Amount before discount
- discount: Discount amount (0 if none)
- total_value: Final amount
- category: Category like "Pharmacy", "Inventory Item", "Surgeon Fees", "Bed Charge", etc.

=== DIAGNOSIS EXTRACTION (CRITICAL) ===

Extract ALL diagnoses from the document. This is VERY IMPORTANT for medical claims.

**Where to Find Diagnoses:**
- Look for: "Diagnosis", "Dx", "Primary Diagnosis", "Principal Diagnosis", "Admitting Diagnosis"
- Also check: "Chief Complaint", "Reason for Visit", "Condition", "Clinical Findings"
- Look for ICD-10 codes (format: letter + 2-3 digits + optional decimal, e.g., "J06.9", "M54.5", "K21.0")
- Check table headers like "ICD Code", "Diagnosis Code", "DX", "Medical Condition"

**Diagnosis Classification Rules:**
1. **Principal/Primary Diagnosis** (is_primary: true):
   - The condition established AFTER study to be chiefly responsible for admission/visit
   - Usually appears first or is explicitly labeled "Primary" or "Principal"
   - Only ONE diagnosis should have is_primary: true

2. **Secondary Diagnoses** (is_primary: false):
   - All other conditions that coexist or develop during the treatment
   - Contributing conditions, comorbidities, complications
   - Can have MULTIPLE secondary diagnoses

3. **If No Explicit Classification:**
   - The FIRST diagnosis mentioned is usually the primary
   - If multiple unlabeled diagnoses exist, infer from context (most severe = primary)
   - Conditions like "Diabetes", "Hypertension" listed alongside acute conditions are usually secondary

**Diagnosis Inference:**
If diagnoses are not explicitly stated, try to INFER them from:
- Treatment being provided (e.g., antibiotics suggest infection)
- Procedures performed (e.g., endoscopy suggests GI issue)
- Medications prescribed (e.g., insulin = diabetes, antihypertensives = hypertension)
- Doctor's notes or clinical summary
- When inferring, set confidence lower (0.6-0.7)

=== JSON OUTPUT FORMAT ===

{{
    "patient_info": {{
        "name": "full patient name",
        "member_id": "insurance/member ID",
        "date_of_birth": "YYYY-MM-DD",
        "gender": "M/F",
        "address": "full address",
        "age": "age in years",
        "uhid_no": "hospital UHID"
    }},
    "provider_info": {{
        "name": "hospital/clinic name",
        "npi": "NPI if available",
        "tax_id": "GSTIN/Tax ID",
        "address": "address",
        "phone": "phone",
        "specialty": "specialty",
        "department": "department",
        "doctor_name": "treating doctor name"
    }},
    "diagnoses": [
        {{"code": "K21.0", "description": "Gastroesophageal reflux disease with esophagitis", "is_primary": true, "confidence": 0.9}},
        {{"code": "E11.9", "description": "Type 2 diabetes mellitus without complications", "is_primary": false, "confidence": 0.85}},
        {{"code": "", "description": "Inferred from medications: Hypertension", "is_primary": false, "confidence": 0.6}}
    ],
    "procedures": [],
    "line_items": [
        {{"sl_no": 1, "date": "2025-12-08", "description": "NEEDLE 18X1.5G", "sac_code": "9018", "quantity": 3, "rate": "3.40", "gross_value": "10.20", "discount": "0.00", "total_value": "10.20", "category": "Inventory Item"}},
        {{"sl_no": 2, "date": "2025-12-08", "description": "OFLOX 4MG INJ", "sac_code": "3004", "quantity": 1, "rate": "12.72", "gross_value": "12.72", "discount": "0.00", "total_value": "12.72", "category": "Pharmacy"}}
    ],
    "financial": {{
        "total_charged": "grand total",
        "subtotal": "subtotal before discount",
        "discount_total": "total discount",
        "tax": "GST/tax amount",
        "currency": "INR",
        "bill_amount": "final bill amount",
        "patient_share": "patient payable",
        "amount_paid": "amount already paid"
    }},
    "dates": {{
        "service_date_from": "start date",
        "service_date_to": "end date",
        "admission_date": "admission date",
        "discharge_date": "discharge date",
        "bill_date": "bill date"
    }},
    "identifiers": {{
        "claim_number": "claim/reference number",
        "prior_auth_number": "prior auth",
        "policy_number": "policy number",
        "group_number": "group number",
        "bill_no": "bill/invoice number",
        "uhid_no": "UHID"
    }},
    "place_of_service": {{
        "code": "POS code",
        "facility_name": "facility name",
        "ward": "ward name"
    }},
    "claim_type": "invoice",
    "overall_confidence": 0.85
}}

**CRITICAL REMINDER**:
- Put ALL itemized charges (medicines, supplies, fees, etc.) in "line_items" array
- Leave "procedures" array EMPTY unless there are actual CPT procedure codes
- If there are 60 line items in the invoice, return ALL 60 in the line_items array
- Do NOT summarize or skip any items"""

INVOICE_EXTRACTION_PROMPT = """Extract invoice data from the following OCR text:

OCR TEXT:
{ocr_text}

Return JSON with:
1. invoice_number
2. invoice_date
3. vendor_info: name, address, tax_id
4. line_items: array of {{description, quantity, unit_price, total}}
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

                # Use default gateway config from settings (or pass custom GatewayConfig)
                self._llm_gateway = LLMGateway()
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
            # Build OCR text section - include guidance if no OCR text
            if ocr_text and len(ocr_text.strip()) > 0:
                ocr_text_section = f"OCR TEXT:\n{ocr_text[:15000]}"  # Increased limit
            else:
                ocr_text_section = """NOTE: No OCR text available. Please extract all data directly from the image.
Carefully examine the entire document including:
- Header information (hospital name, bill number, patient details)
- ALL table rows with line items
- ALL inventory items, medications, services, and charges
- Summary totals and subtotals
- Footer information"""

            # Build prompt
            prompt = CLAIM_EXTRACTION_PROMPT.format(
                document_type=document_type.value,
                ocr_text_section=ocr_text_section,
            )

            # Call LLM
            print(f"[PARSER DEBUG] Calling LLM with image_data={image_data is not None}, ocr_text_len={len(ocr_text)}", flush=True)
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

            # Create request using appropriate factory method
            system_prompt = "You are a medical document extraction expert. Return only valid JSON."
            if image_data:
                request = LLMRequest.with_image(
                    prompt=prompt,
                    image_data=image_data,
                    system_prompt=system_prompt,
                )
            else:
                request = LLMRequest.simple(
                    prompt=prompt,
                    system_prompt=system_prompt,
                )
            # Override settings for extraction
            # Increased max_tokens for documents with many line items (60+ items need ~10K tokens)
            request.max_tokens = 16000
            request.temperature = 0.1  # Low temperature for consistent extraction

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
        print(f"[JSON EXTRACT] Response length: {len(text)} chars")
        print(f"[JSON EXTRACT] First 500 chars: {text[:500]}")

        # Try direct parse
        try:
            result = json.loads(text)
            print(f"[JSON EXTRACT] Direct parse succeeded, keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"[JSON EXTRACT] Direct parse failed: {e}")

        # Try to find JSON in markdown code block (greedy match for nested braces)
        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                logger.info(f"[JSON EXTRACT] Markdown block parse succeeded, keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
                return result
            except json.JSONDecodeError as e:
                logger.debug(f"[JSON EXTRACT] Markdown block parse failed: {e}")

        # Try to find the largest JSON object in the text
        # This handles nested objects properly
        brace_count = 0
        start_idx = -1
        for i, char in enumerate(text):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx >= 0:
                    json_str = text[start_idx:i+1]
                    try:
                        result = json.loads(json_str)
                        logger.info(f"[JSON EXTRACT] Brace matching succeeded, keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
                        if isinstance(result, dict):
                            logger.info(f"[JSON EXTRACT] line_items count: {len(result.get('line_items', []))}")
                            logger.info(f"[JSON EXTRACT] procedures count: {len(result.get('procedures', []))}")
                        return result
                    except json.JSONDecodeError as e:
                        logger.debug(f"[JSON EXTRACT] Brace matching parse failed: {e}")
                        # Continue looking for another JSON object
                        start_idx = -1
                        continue

        logger.warning(f"[JSON EXTRACT] Failed to extract JSON from response")
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
        diagnoses_data = extracted.get("diagnoses", [])
        if isinstance(diagnoses_data, list):
            for dx in diagnoses_data:
                if isinstance(dx, dict):
                    result.diagnoses.append(ExtractedDiagnosis(
                        code=dx.get("code", ""),
                        description=dx.get("description", ""),
                        code_system=DiagnosisCodeSystem.ICD10_CM,
                        is_primary=dx.get("is_primary", False),
                        confidence=float(dx.get("confidence", 0.8)),
                    ))
                    result.fields_extracted += 1

        # Extract line items FIRST (for invoices with itemized charges)
        # This is the primary array for invoice/bill data
        line_items_data = extracted.get("line_items", [])
        print(f"[EXTRACT] LLM returned {len(line_items_data) if isinstance(line_items_data, list) else 'non-list'} line_items")
        if isinstance(line_items_data, list):
            for idx, item in enumerate(line_items_data):
                if not isinstance(item, dict):
                    continue
                try:
                    line_item = ExtractedLineItem(
                        sl_no=int(item.get("sl_no", idx + 1) or idx + 1),
                        date=self._parse_date(item.get("date")),
                        description=str(item.get("description", "")),
                        sac_code=str(item.get("sac_code", "")),
                        quantity=float(item.get("quantity", 1) or 1),
                        rate=self._parse_decimal(item.get("rate")),
                        gross_value=self._parse_decimal(item.get("gross_value")),
                        discount=self._parse_decimal(item.get("discount")),
                        total_value=self._parse_decimal(item.get("total_value") or item.get("charged_amount")),
                        category=str(item.get("category", "")),
                        confidence=float(item.get("confidence", 0.8)),
                    )
                    result.line_items.append(line_item)
                    result.fields_extracted += 1
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse line item {idx}: {e}")
                    continue

        # Extract procedures - but convert non-CPT items to line_items
        procedures_data = extracted.get("procedures", [])
        print(f"[EXTRACT] LLM returned {len(procedures_data) if isinstance(procedures_data, list) else 'non-list'} procedures")
        if not isinstance(procedures_data, list):
            procedures_data = []

        for idx, proc in enumerate(procedures_data):
            if not isinstance(proc, dict):
                continue
            charged = proc.get("charged_amount")
            code = proc.get("code", "")

            # Check if this is a real CPT procedure code (5 digits) or just an invoice item
            # CPT codes are 5 digits, HCPCS are 5 chars starting with letter
            is_cpt_code = code and len(str(code)) == 5 and str(code).isdigit()
            is_hcpcs_code = code and len(str(code)) == 5 and str(code)[0].isalpha()

            if is_cpt_code or is_hcpcs_code:
                # This is a real medical procedure code - add to procedures
                result.procedures.append(ExtractedProcedure(
                    code=str(code),
                    description=proc.get("description", ""),
                    code_system=ProcedureCodeSystem.CPT,
                    modifiers=proc.get("modifiers", []),
                    quantity=int(proc.get("quantity", 1) or 1),
                    charged_amount=self._parse_decimal(charged),
                    service_date=self._parse_date(proc.get("service_date")),
                    confidence=float(proc.get("confidence", 0.8)),
                ))
                result.fields_extracted += 1
            else:
                # This is an invoice line item incorrectly placed in procedures
                # Convert it to a line_item
                print(f"[EXTRACT] Converting procedure '{proc.get('description')}' to line_item (no valid CPT code)")
                try:
                    line_item = ExtractedLineItem(
                        sl_no=len(result.line_items) + 1,
                        date=self._parse_date(proc.get("service_date")),
                        description=str(proc.get("description", "")),
                        sac_code=str(code) if code else "",
                        quantity=float(proc.get("quantity", 1) or 1),
                        rate=None,
                        gross_value=self._parse_decimal(charged),
                        discount=None,
                        total_value=self._parse_decimal(charged),
                        category="",  # Unknown category from procedure
                        confidence=float(proc.get("confidence", 0.8)),
                    )
                    result.line_items.append(line_item)
                    result.fields_extracted += 1
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to convert procedure to line item: {e}")

        # Extract financial
        financial = extracted.get("financial", {})
        if financial.get("total_charged"):
            result.total_charged = self._parse_decimal(financial["total_charged"])
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
        claim_type_str = (extracted.get("claim_type") or "").lower()
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
            "%d-%m-%Y",  # Common in Indian invoices (08-12-2025)
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y%m%d",
            "%m-%d-%Y",
            "%d.%m.%Y",
            "%d %b %Y",  # 08 Dec 2025
            "%d %B %Y",  # 08 December 2025
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """Parse various numeric formats to Decimal."""
        if value is None:
            return None
        try:
            # Handle string with commas (e.g., "1,125.00" or "1,17,550.00")
            if isinstance(value, str):
                # Remove commas, currency symbols, spaces, and any non-numeric chars except . and -
                cleaned = value.replace(",", "").replace("₹", "").replace("$", "").replace(" ", "").strip()
                if not cleaned:
                    return None
                # Remove any characters that aren't digits, decimal point, or minus
                import re
                cleaned = re.sub(r'[^\d.\-]', '', cleaned)
                if not cleaned or cleaned == '-' or cleaned == '.':
                    return None
                return Decimal(cleaned)
            # Handle float/int
            return Decimal(str(value))
        except Exception:
            # Catch all decimal parsing errors
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
