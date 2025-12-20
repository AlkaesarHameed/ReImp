"""
Medical Code Extractor (Rule 2).

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Extracts medical codes from documents using LLM:
- ICD-10-CM/PCS diagnosis codes
- CPT/HCPCS procedure codes
- Revenue codes
- NDC medication codes
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from src.schemas.llm_settings import LLMTaskType
from src.services.validation.llm_validation_service import (
    LLMValidationService,
    get_llm_validation_service,
)

logger = logging.getLogger(__name__)


class CodeType(str, Enum):
    """Types of medical codes."""

    ICD10_CM = "icd10_cm"       # ICD-10 Clinical Modification (diagnosis)
    ICD10_PCS = "icd10_pcs"     # ICD-10 Procedure Coding System
    CPT = "cpt"                 # Current Procedural Terminology
    HCPCS = "hcpcs"             # Healthcare Common Procedure Coding System
    REVENUE = "revenue"         # Revenue codes (UB-04)
    NDC = "ndc"                 # National Drug Code
    DRG = "drg"                 # Diagnosis Related Group
    MODIFIER = "modifier"       # CPT/HCPCS modifiers


@dataclass
class ExtractedCode:
    """A single extracted medical code."""

    code: str
    code_type: CodeType
    description: Optional[str] = None
    qualifier: Optional[str] = None  # For ICD: principal, secondary, etc.
    modifier: Optional[str] = None   # For CPT: 25, 59, etc.
    units: Optional[int] = None      # For CPT: service units
    charge: Optional[float] = None   # Associated charge amount
    page_number: Optional[int] = None
    line_reference: Optional[str] = None
    confidence: float = 0.0
    extraction_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "code": self.code,
            "code_type": self.code_type.value,
            "description": self.description,
            "qualifier": self.qualifier,
            "modifier": self.modifier,
            "units": self.units,
            "charge": self.charge,
            "page_number": self.page_number,
            "line_reference": self.line_reference,
            "confidence": self.confidence,
        }


@dataclass
class ServiceLine:
    """Extracted service line with codes and charges."""

    line_number: int
    date_of_service: Optional[str] = None
    place_of_service: Optional[str] = None
    diagnosis_pointers: list[str] = field(default_factory=list)  # A, B, C, D
    cpt_codes: list[ExtractedCode] = field(default_factory=list)
    units: int = 1
    charges: Optional[float] = None
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "line_number": self.line_number,
            "date_of_service": self.date_of_service,
            "place_of_service": self.place_of_service,
            "diagnosis_pointers": self.diagnosis_pointers,
            "cpt_codes": [c.to_dict() for c in self.cpt_codes],
            "units": self.units,
            "charges": self.charges,
            "confidence": self.confidence,
        }


@dataclass
class CodeExtractionResult:
    """Complete code extraction result."""

    success: bool
    diagnosis_codes: list[ExtractedCode] = field(default_factory=list)
    procedure_codes: list[ExtractedCode] = field(default_factory=list)
    revenue_codes: list[ExtractedCode] = field(default_factory=list)
    medication_codes: list[ExtractedCode] = field(default_factory=list)
    drg_code: Optional[ExtractedCode] = None
    service_lines: list[ServiceLine] = field(default_factory=list)
    principal_diagnosis: Optional[str] = None
    admitting_diagnosis: Optional[str] = None
    total_charges: Optional[float] = None
    overall_confidence: float = 0.0
    execution_time_ms: int = 0
    llm_provider_used: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def all_icd_codes(self) -> list[str]:
        """Get all ICD-10 codes."""
        return [c.code for c in self.diagnosis_codes]

    @property
    def all_cpt_codes(self) -> list[str]:
        """Get all CPT/HCPCS codes."""
        return [c.code for c in self.procedure_codes]

    def to_evidence_dict(self) -> dict[str, Any]:
        """Convert to evidence format."""
        return {
            "success": self.success,
            "overall_confidence": self.overall_confidence,
            "diagnosis_count": len(self.diagnosis_codes),
            "procedure_count": len(self.procedure_codes),
            "principal_diagnosis": self.principal_diagnosis,
            "diagnoses": [c.to_dict() for c in self.diagnosis_codes],
            "procedures": [c.to_dict() for c in self.procedure_codes],
            "service_lines": [s.to_dict() for s in self.service_lines],
            "total_charges": self.total_charges,
            "warnings": self.warnings,
            "errors": self.errors,
        }


# System prompt for code extraction
CODE_EXTRACTION_SYSTEM_PROMPT = """You are an expert medical coder with deep knowledge of:
- ICD-10-CM/PCS coding guidelines
- CPT/HCPCS coding rules
- Revenue code assignment
- NDC medication coding
- Modifier usage and sequencing

Your role is to accurately extract all medical codes from documents.
Be precise with:
- Code format (include dots for ICD-10, correct length for CPT)
- Code sequencing (principal vs secondary diagnoses)
- Modifiers and their placement
- Service dates and units

Extract ALL codes visible in the document. If uncertain about a code, include it with lower confidence."""


CODE_EXTRACTION_PROMPT = """Extract all medical codes from this document:

Document content:
{document_content}

Extract the following code types:

1. DIAGNOSIS CODES (ICD-10-CM/PCS):
   - Principal diagnosis (first listed)
   - Secondary diagnoses
   - Admitting diagnosis (if present)
   - External cause codes (V, W, X, Y codes)

2. PROCEDURE CODES (CPT/HCPCS):
   - All procedure codes with modifiers
   - Units for each code
   - Associated charges

3. REVENUE CODES (if UB-04 format):
   - Revenue code and description
   - Associated charges

4. MEDICATION CODES (NDC):
   - Drug identification codes

5. SERVICE LINES:
   - Date of service
   - Place of service
   - Diagnosis pointers (A, B, C, D)
   - Procedure codes with modifiers and units

Return the data as JSON with this structure:
{{
    "document_type": "CMS-1500|UB-04|EOB|other",
    "principal_diagnosis": "ICD-10 code or null",
    "admitting_diagnosis": "ICD-10 code or null (for inpatient)",
    "diagnosis_codes": [
        {{
            "code": "ICD-10 code (e.g., E11.9)",
            "code_type": "icd10_cm|icd10_pcs",
            "description": "Description if visible",
            "qualifier": "principal|secondary|admitting|external_cause",
            "page_number": 1,
            "confidence": 0.0 to 1.0
        }}
    ],
    "procedure_codes": [
        {{
            "code": "CPT/HCPCS code (e.g., 99213)",
            "code_type": "cpt|hcpcs",
            "description": "Description if visible",
            "modifier": "Modifier if present (e.g., 25)",
            "units": 1,
            "charge": 150.00,
            "page_number": 1,
            "confidence": 0.0 to 1.0
        }}
    ],
    "revenue_codes": [
        {{
            "code": "0450",
            "code_type": "revenue",
            "description": "Description",
            "charge": 500.00,
            "confidence": 0.0 to 1.0
        }}
    ],
    "medication_codes": [
        {{
            "code": "NDC code",
            "code_type": "ndc",
            "description": "Drug name",
            "units": 1,
            "confidence": 0.0 to 1.0
        }}
    ],
    "drg": {{
        "code": "DRG code",
        "description": "DRG description",
        "confidence": 0.0 to 1.0
    }},
    "service_lines": [
        {{
            "line_number": 1,
            "date_of_service": "YYYY-MM-DD",
            "place_of_service": "11",
            "diagnosis_pointers": ["A", "B"],
            "cpt_code": "99213",
            "modifier": "25",
            "units": 1,
            "charges": 150.00,
            "confidence": 0.0 to 1.0
        }}
    ],
    "total_charges": 1500.00,
    "overall_confidence": 0.0 to 1.0,
    "warnings": ["List of extraction concerns"]
}}"""


CODE_EXTRACTION_VISION_PROMPT = """Analyze this medical claim document image and extract all medical codes:

1. DIAGNOSIS CODES (ICD-10-CM/PCS):
   - Principal diagnosis (first listed)
   - Secondary diagnoses
   - Admitting diagnosis (if present)
   - External cause codes

2. PROCEDURE CODES (CPT/HCPCS):
   - All procedure codes with modifiers
   - Units for each code
   - Associated charges

3. REVENUE CODES (if UB-04 format):
   - Revenue code and description
   - Associated charges

4. SERVICE LINES:
   - Date of service
   - Place of service
   - Diagnosis pointers (A, B, C, D)
   - Procedure codes with modifiers and units

Return the data as JSON with this structure:
{{
    "document_type": "CMS-1500|UB-04|EOB|other",
    "principal_diagnosis": "ICD-10 code or null",
    "admitting_diagnosis": "ICD-10 code or null",
    "diagnosis_codes": [
        {{
            "code": "ICD-10 code (e.g., E11.9)",
            "code_type": "icd10_cm|icd10_pcs",
            "description": "Description if visible",
            "qualifier": "principal|secondary|admitting|external_cause",
            "confidence": 0.0 to 1.0
        }}
    ],
    "procedure_codes": [
        {{
            "code": "CPT/HCPCS code (e.g., 99213)",
            "code_type": "cpt|hcpcs",
            "description": "Description if visible",
            "modifier": "Modifier if present",
            "units": 1,
            "charge": 150.00,
            "confidence": 0.0 to 1.0
        }}
    ],
    "revenue_codes": [
        {{
            "code": "0450",
            "code_type": "revenue",
            "description": "Description",
            "charge": 500.00,
            "confidence": 0.0 to 1.0
        }}
    ],
    "service_lines": [
        {{
            "line_number": 1,
            "date_of_service": "YYYY-MM-DD",
            "place_of_service": "11",
            "diagnosis_pointers": ["A", "B"],
            "cpt_code": "99213",
            "modifier": "25",
            "units": 1,
            "charges": 150.00,
            "confidence": 0.0 to 1.0
        }}
    ],
    "total_charges": 1500.00,
    "overall_confidence": 0.0 to 1.0,
    "warnings": ["List of extraction concerns"]
}}"""


class CodeExtractor:
    """
    Extracts medical codes from documents.

    Uses LLM to extract:
    - ICD-10-CM/PCS diagnosis codes
    - CPT/HCPCS procedure codes
    - Revenue codes
    - NDC medication codes

    Source: Design Document Section 2.2 - Validation Rules (Rule 2)
    """

    # Code format patterns for validation
    ICD10_PATTERN = re.compile(r'^[A-TV-Z][0-9][0-9AB]\.?[0-9A-Z]{0,4}$', re.IGNORECASE)
    CPT_PATTERN = re.compile(r'^[0-9]{5}$')
    HCPCS_PATTERN = re.compile(r'^[A-V][0-9]{4}$', re.IGNORECASE)
    REVENUE_PATTERN = re.compile(r'^[0-9]{4}$')
    NDC_PATTERN = re.compile(r'^[0-9]{10,11}$|^[0-9]{4,5}-[0-9]{4}-[0-9]{1,2}$')
    MODIFIER_PATTERN = re.compile(r'^[0-9A-Z]{2}$', re.IGNORECASE)

    def __init__(
        self,
        llm_service: Optional[LLMValidationService] = None,
    ):
        """
        Initialize the code extractor.

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
    ) -> CodeExtractionResult:
        """
        Extract medical codes from document text.

        Args:
            document_content: OCR'd or text content of the document
            tenant_id: Tenant ID for LLM configuration

        Returns:
            CodeExtractionResult with extracted codes
        """
        import time
        start_time = time.perf_counter()

        if not document_content or len(document_content.strip()) < 50:
            return CodeExtractionResult(
                success=False,
                errors=["Document content is too short or empty"],
                execution_time_ms=0,
            )

        # Build prompt
        prompt = CODE_EXTRACTION_PROMPT.format(document_content=document_content)

        # Generate cache key
        cache_key = self._generate_cache_key(document_content)

        # Call LLM
        llm_result = await self.llm_service.complete(
            prompt=prompt,
            system_prompt=CODE_EXTRACTION_SYSTEM_PROMPT,
            task_type=LLMTaskType.EXTRACTION,
            tenant_id=tenant_id,
            json_mode=True,
            cache_key=cache_key,
        )

        execution_time = int((time.perf_counter() - start_time) * 1000)

        if not llm_result.success or not llm_result.parsed_data:
            logger.error(f"Code extraction failed: {llm_result.error}")
            return CodeExtractionResult(
                success=False,
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
            f"Code extraction: success={result.success}, "
            f"diagnoses={len(result.diagnosis_codes)}, "
            f"procedures={len(result.procedure_codes)}, "
            f"confidence={result.overall_confidence:.2f}, "
            f"time={execution_time}ms"
        )

        return result

    async def extract_from_image(
        self,
        image_data: bytes,
        media_type: str = "image/png",
        tenant_id: Optional[UUID] = None,
    ) -> CodeExtractionResult:
        """
        Extract medical codes from a document image.

        Args:
            image_data: Raw image bytes
            media_type: MIME type of the image
            tenant_id: Tenant ID for LLM configuration

        Returns:
            CodeExtractionResult with extracted codes
        """
        import time
        from src.gateways.llm_gateway import LLMRequest

        start_time = time.perf_counter()

        if not image_data:
            return CodeExtractionResult(
                success=False,
                errors=["No image data provided"],
                execution_time_ms=0,
            )

        # Create vision request
        request = LLMRequest.with_image(
            prompt=CODE_EXTRACTION_VISION_PROMPT,
            image_data=image_data,
            media_type=media_type,
            system_prompt=CODE_EXTRACTION_SYSTEM_PROMPT,
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
                return CodeExtractionResult(
                    success=False,
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
                f"Code vision extraction: success={extraction_result.success}, "
                f"diagnoses={len(extraction_result.diagnosis_codes)}, "
                f"procedures={len(extraction_result.procedure_codes)}, "
                f"time={execution_time}ms"
            )

            return extraction_result

        except Exception as e:
            execution_time = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"Vision extraction error: {e}")
            return CodeExtractionResult(
                success=False,
                errors=[f"Vision extraction error: {str(e)}"],
                execution_time_ms=execution_time,
            )

    def _generate_cache_key(self, content: str) -> str:
        """Generate cache key for extraction request."""
        content_hash = hashlib.md5(content[:5000].encode()).hexdigest()
        return f"extract:codes:{content_hash}"

    def _parse_extraction_response(
        self,
        data: dict,
        execution_time: int,
        provider_used: str,
    ) -> CodeExtractionResult:
        """Parse LLM response into structured result."""
        try:
            warnings = data.get("warnings", [])

            # Parse diagnosis codes
            diagnosis_codes = []
            for dx in data.get("diagnosis_codes", []):
                code = dx.get("code", "").strip().upper()
                if code:
                    # Validate and normalize code
                    normalized = self._normalize_icd10(code)
                    if normalized:
                        diagnosis_codes.append(ExtractedCode(
                            code=normalized,
                            code_type=CodeType(dx.get("code_type", "icd10_cm")),
                            description=dx.get("description"),
                            qualifier=dx.get("qualifier"),
                            page_number=dx.get("page_number"),
                            confidence=float(dx.get("confidence", 0.7)),
                        ))
                    else:
                        warnings.append(f"Invalid ICD-10 format: {code}")

            # Parse procedure codes
            procedure_codes = []
            for px in data.get("procedure_codes", []):
                code = px.get("code", "").strip().upper()
                if code:
                    # Determine code type
                    code_type = self._determine_procedure_code_type(code)
                    if code_type:
                        procedure_codes.append(ExtractedCode(
                            code=code,
                            code_type=code_type,
                            description=px.get("description"),
                            modifier=px.get("modifier"),
                            units=px.get("units", 1),
                            charge=px.get("charge"),
                            page_number=px.get("page_number"),
                            confidence=float(px.get("confidence", 0.7)),
                        ))
                    else:
                        warnings.append(f"Invalid procedure code format: {code}")

            # Parse revenue codes
            revenue_codes = []
            for rev in data.get("revenue_codes", []):
                code = rev.get("code", "").strip()
                if code and self.REVENUE_PATTERN.match(code):
                    revenue_codes.append(ExtractedCode(
                        code=code,
                        code_type=CodeType.REVENUE,
                        description=rev.get("description"),
                        charge=rev.get("charge"),
                        confidence=float(rev.get("confidence", 0.7)),
                    ))

            # Parse medication codes
            medication_codes = []
            for med in data.get("medication_codes", []):
                code = med.get("code", "").strip()
                if code:
                    medication_codes.append(ExtractedCode(
                        code=code,
                        code_type=CodeType.NDC,
                        description=med.get("description"),
                        units=med.get("units"),
                        confidence=float(med.get("confidence", 0.7)),
                    ))

            # Parse DRG
            drg_code = None
            drg_data = data.get("drg")
            if drg_data and drg_data.get("code"):
                drg_code = ExtractedCode(
                    code=drg_data.get("code"),
                    code_type=CodeType.DRG,
                    description=drg_data.get("description"),
                    confidence=float(drg_data.get("confidence", 0.7)),
                )

            # Parse service lines
            service_lines = []
            for sl in data.get("service_lines", []):
                cpt_codes = []
                cpt_code = sl.get("cpt_code", "").strip().upper()
                if cpt_code:
                    code_type = self._determine_procedure_code_type(cpt_code)
                    if code_type:
                        cpt_codes.append(ExtractedCode(
                            code=cpt_code,
                            code_type=code_type,
                            modifier=sl.get("modifier"),
                            units=sl.get("units", 1),
                            charge=sl.get("charges"),
                            confidence=float(sl.get("confidence", 0.7)),
                        ))

                service_lines.append(ServiceLine(
                    line_number=sl.get("line_number", 1),
                    date_of_service=sl.get("date_of_service"),
                    place_of_service=sl.get("place_of_service"),
                    diagnosis_pointers=sl.get("diagnosis_pointers", []),
                    cpt_codes=cpt_codes,
                    units=sl.get("units", 1),
                    charges=sl.get("charges"),
                    confidence=float(sl.get("confidence", 0.7)),
                ))

            overall_confidence = float(data.get("overall_confidence", 0.7))

            return CodeExtractionResult(
                success=True,
                diagnosis_codes=diagnosis_codes,
                procedure_codes=procedure_codes,
                revenue_codes=revenue_codes,
                medication_codes=medication_codes,
                drg_code=drg_code,
                service_lines=service_lines,
                principal_diagnosis=data.get("principal_diagnosis"),
                admitting_diagnosis=data.get("admitting_diagnosis"),
                total_charges=data.get("total_charges"),
                overall_confidence=overall_confidence,
                execution_time_ms=execution_time,
                llm_provider_used=provider_used,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Error parsing extraction response: {e}")
            return CodeExtractionResult(
                success=False,
                errors=[f"Parse error: {str(e)}"],
                execution_time_ms=execution_time,
                llm_provider_used=provider_used,
            )

    def _normalize_icd10(self, code: str) -> Optional[str]:
        """
        Normalize ICD-10 code format.

        Args:
            code: Raw ICD-10 code

        Returns:
            Normalized code with proper formatting, or None if invalid
        """
        # Remove spaces and extra characters
        code = re.sub(r'[\s\-]', '', code.upper())

        # Add dot if missing (e.g., E119 -> E11.9)
        if len(code) > 3 and '.' not in code:
            code = code[:3] + '.' + code[3:]

        # Validate format
        if self.ICD10_PATTERN.match(code):
            return code

        return None

    def _determine_procedure_code_type(self, code: str) -> Optional[CodeType]:
        """
        Determine the type of procedure code.

        Args:
            code: Procedure code

        Returns:
            CodeType or None if unrecognized
        """
        code = code.strip().upper()

        if self.CPT_PATTERN.match(code):
            return CodeType.CPT
        elif self.HCPCS_PATTERN.match(code):
            return CodeType.HCPCS

        return None

    def validate_code_format(self, code: str, code_type: CodeType) -> bool:
        """
        Validate code format.

        Args:
            code: Medical code
            code_type: Type of code

        Returns:
            True if valid format
        """
        code = code.strip().upper()

        patterns = {
            CodeType.ICD10_CM: self.ICD10_PATTERN,
            CodeType.ICD10_PCS: self.ICD10_PATTERN,
            CodeType.CPT: self.CPT_PATTERN,
            CodeType.HCPCS: self.HCPCS_PATTERN,
            CodeType.REVENUE: self.REVENUE_PATTERN,
            CodeType.NDC: self.NDC_PATTERN,
            CodeType.MODIFIER: self.MODIFIER_PATTERN,
        }

        pattern = patterns.get(code_type)
        if pattern:
            return bool(pattern.match(code))

        return True  # Unknown type, assume valid


# Singleton instance
_code_extractor: Optional[CodeExtractor] = None


def get_code_extractor() -> CodeExtractor:
    """Get or create the singleton code extractor."""
    global _code_extractor
    if _code_extractor is None:
        _code_extractor = CodeExtractor()
    return _code_extractor
