"""
Medical Report Validator (Rule 9 - Documentation).

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Validates medical reports and documentation for:
- Completeness of required sections
- Date consistency
- Provider signature presence
- Clinical findings supporting diagnoses
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from src.schemas.llm_settings import LLMTaskType
from src.services.validation.llm_validation_service import (
    LLMValidationService,
    get_llm_validation_service,
)

logger = logging.getLogger(__name__)


class DocumentSection(str, Enum):
    """Required document sections."""

    PATIENT_IDENTIFICATION = "patient_identification"
    PROVIDER_IDENTIFICATION = "provider_identification"
    DATE_OF_SERVICE = "date_of_service"
    CHIEF_COMPLAINT = "chief_complaint"
    HISTORY = "history"
    PHYSICAL_EXAM = "physical_exam"
    ASSESSMENT = "assessment"
    PLAN = "plan"
    DIAGNOSIS = "diagnosis"
    PROCEDURES = "procedures"
    SIGNATURE = "signature"
    ORDERS = "orders"
    RESULTS = "results"


class SectionStatus(str, Enum):
    """Status of a document section."""

    PRESENT = "present"
    MISSING = "missing"
    INCOMPLETE = "incomplete"
    UNCLEAR = "unclear"


class ComplianceLevel(str, Enum):
    """Documentation compliance level."""

    COMPLIANT = "compliant"            # Meets all requirements
    MINOR_ISSUES = "minor_issues"      # Small issues, acceptable
    MAJOR_ISSUES = "major_issues"      # Significant issues
    NON_COMPLIANT = "non_compliant"    # Does not meet requirements


@dataclass
class SectionAnalysis:
    """Analysis of a document section."""

    section: DocumentSection
    status: SectionStatus
    content_summary: Optional[str] = None
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "section": self.section.value,
            "status": self.status.value,
            "content_summary": self.content_summary,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "confidence": self.confidence,
        }


@dataclass
class DateConsistency:
    """Date consistency check result."""

    is_consistent: bool
    report_date: Optional[str] = None
    service_date: Optional[str] = None
    signature_date: Optional[str] = None
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_consistent": self.is_consistent,
            "report_date": self.report_date,
            "service_date": self.service_date,
            "signature_date": self.signature_date,
            "issues": self.issues,
        }


@dataclass
class SignatureValidation:
    """Signature validation result."""

    has_signature: bool
    signature_type: Optional[str] = None  # handwritten, electronic, stamp
    signer_name: Optional[str] = None
    signer_credentials: Optional[str] = None
    signature_date: Optional[str] = None
    is_legible: bool = True
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "has_signature": self.has_signature,
            "signature_type": self.signature_type,
            "signer_name": self.signer_name,
            "signer_credentials": self.signer_credentials,
            "signature_date": self.signature_date,
            "is_legible": self.is_legible,
            "issues": self.issues,
        }


@dataclass
class DiagnosisSupportAnalysis:
    """Analysis of documentation supporting diagnosis."""

    diagnosis_code: str
    diagnosis_description: Optional[str] = None
    is_supported: bool = False
    supporting_evidence: list[str] = field(default_factory=list)
    missing_documentation: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "diagnosis_code": self.diagnosis_code,
            "diagnosis_description": self.diagnosis_description,
            "is_supported": self.is_supported,
            "supporting_evidence": self.supporting_evidence,
            "missing_documentation": self.missing_documentation,
            "confidence": self.confidence,
        }


@dataclass
class MedicalReportValidationResult:
    """Complete medical report validation result."""

    is_valid: bool
    compliance_level: ComplianceLevel
    section_analyses: list[SectionAnalysis]
    date_consistency: DateConsistency
    signature_validation: SignatureValidation
    diagnosis_support: list[DiagnosisSupportAnalysis]
    critical_issues: list[str]
    warnings: list[str]
    recommendations: list[str]
    overall_confidence: float
    execution_time_ms: int
    llm_provider_used: str = ""

    @property
    def missing_sections(self) -> list[DocumentSection]:
        """Get list of missing sections."""
        return [
            s.section for s in self.section_analyses
            if s.status == SectionStatus.MISSING
        ]

    @property
    def requires_review(self) -> bool:
        """Check if manual review is required."""
        return (
            self.compliance_level in (ComplianceLevel.MAJOR_ISSUES, ComplianceLevel.NON_COMPLIANT)
            or len(self.critical_issues) > 0
            or self.overall_confidence < 0.7
        )

    def to_evidence_dict(self) -> dict[str, Any]:
        """Convert to evidence format for rejection."""
        return {
            "is_valid": self.is_valid,
            "compliance_level": self.compliance_level.value,
            "confidence": self.overall_confidence,
            "sections": [s.to_dict() for s in self.section_analyses],
            "date_consistency": self.date_consistency.to_dict(),
            "signature": self.signature_validation.to_dict(),
            "diagnosis_support": [d.to_dict() for d in self.diagnosis_support],
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
        }


# System prompt for medical report validation
MEDICAL_REPORT_SYSTEM_PROMPT = """You are an expert medical documentation reviewer with deep knowledge of:
- Clinical documentation requirements (CMS guidelines)
- Medical record standards (HIPAA, Joint Commission)
- Evaluation and Management (E/M) documentation guidelines
- ICD-10 and CPT documentation requirements
- Medical necessity documentation

Your role is to review medical documentation for:
1. Completeness of required sections
2. Consistency of dates and information
3. Provider signature requirements
4. Clinical support for diagnoses
5. Medical necessity documentation

Be thorough but fair in your assessment.
Flag critical issues that could affect claim payment.
Provide specific recommendations for improvement."""


MEDICAL_REPORT_VALIDATION_PROMPT = """Review this medical report/documentation for completeness and compliance:

Document Content:
{document_content}

Claim Information:
- Service Date(s): {service_dates}
- Diagnosis Codes: {diagnosis_codes}
- Procedure Codes: {procedure_codes}
- Provider Type: {provider_type}

Evaluate the following:

1. REQUIRED SECTIONS:
   - Patient identification
   - Provider identification
   - Date of service
   - Chief complaint / reason for visit
   - History (relevant medical history)
   - Physical examination findings
   - Assessment/diagnosis
   - Treatment plan
   - Signature with credentials

2. DATE CONSISTENCY:
   - Report date vs service date
   - Signature date
   - Any date discrepancies

3. SIGNATURE VALIDATION:
   - Signature present
   - Type (handwritten, electronic, stamp)
   - Signer credentials visible
   - Legibility

4. DIAGNOSIS SUPPORT:
   For each diagnosis code, identify:
   - Clinical findings that support it
   - Missing documentation
   - Medical necessity evidence

Return your assessment as JSON with this structure:
{{
    "document_type": "office_visit|operative_report|discharge_summary|consultation|other",
    "sections": [
        {{
            "section": "patient_identification|provider_identification|date_of_service|chief_complaint|history|physical_exam|assessment|plan|diagnosis|procedures|signature|orders|results",
            "status": "present|missing|incomplete|unclear",
            "content_summary": "Brief summary of section content",
            "issues": ["List of issues found"],
            "recommendations": ["Recommendations for improvement"],
            "confidence": 0.0 to 1.0
        }}
    ],
    "date_consistency": {{
        "is_consistent": true|false,
        "report_date": "YYYY-MM-DD or null",
        "service_date": "YYYY-MM-DD or null",
        "signature_date": "YYYY-MM-DD or null",
        "issues": ["Date-related issues"]
    }},
    "signature": {{
        "has_signature": true|false,
        "signature_type": "handwritten|electronic|stamp|none",
        "signer_name": "Provider name or null",
        "signer_credentials": "MD, DO, NP, etc. or null",
        "signature_date": "YYYY-MM-DD or null",
        "is_legible": true|false,
        "issues": ["Signature-related issues"]
    }},
    "diagnosis_support": [
        {{
            "diagnosis_code": "ICD-10 code",
            "diagnosis_description": "Description",
            "is_supported": true|false,
            "supporting_evidence": ["Clinical findings that support"],
            "missing_documentation": ["Documentation needed"],
            "confidence": 0.0 to 1.0
        }}
    ],
    "compliance_level": "compliant|minor_issues|major_issues|non_compliant",
    "critical_issues": ["Issues that could cause claim denial"],
    "warnings": ["Issues to be aware of"],
    "recommendations": ["Overall recommendations"],
    "overall_confidence": 0.0 to 1.0
}}"""


class MedicalReportValidator:
    """
    Validates medical reports and documentation.

    Checks for:
    - Completeness of required sections
    - Date consistency
    - Provider signature presence
    - Clinical findings supporting diagnoses

    Source: Design Document Section 2.2 - Validation Rules (Rule 9)
    """

    def __init__(
        self,
        llm_service: Optional[LLMValidationService] = None,
    ):
        """
        Initialize the medical report validator.

        Args:
            llm_service: LLM validation service
        """
        self._llm_service = llm_service

    @property
    def llm_service(self) -> LLMValidationService:
        """Get LLM service instance."""
        if self._llm_service is None:
            self._llm_service = get_llm_validation_service()
        return self._llm_service

    async def validate(
        self,
        document_content: str,
        service_dates: Optional[list[str]] = None,
        diagnosis_codes: Optional[list[str]] = None,
        procedure_codes: Optional[list[str]] = None,
        provider_type: str = "physician",
        tenant_id: Optional[UUID] = None,
    ) -> MedicalReportValidationResult:
        """
        Validate a medical report for documentation requirements.

        Args:
            document_content: OCR'd or text content of the document
            service_dates: List of service dates (YYYY-MM-DD)
            diagnosis_codes: ICD-10 diagnosis codes
            procedure_codes: CPT/HCPCS procedure codes
            provider_type: Type of provider (physician, NP, PA, etc.)
            tenant_id: Tenant ID for LLM configuration

        Returns:
            MedicalReportValidationResult with validation details
        """
        import time
        start_time = time.perf_counter()

        if not document_content or len(document_content.strip()) < 100:
            return MedicalReportValidationResult(
                is_valid=False,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                section_analyses=[],
                date_consistency=DateConsistency(is_consistent=False, issues=["No document content"]),
                signature_validation=SignatureValidation(has_signature=False),
                diagnosis_support=[],
                critical_issues=["Document content is empty or too short"],
                warnings=[],
                recommendations=["Provide complete medical documentation"],
                overall_confidence=0.0,
                execution_time_ms=0,
            )

        # Format inputs for prompt
        service_dates_str = ", ".join(service_dates) if service_dates else "Not specified"
        diagnosis_codes_str = ", ".join(diagnosis_codes) if diagnosis_codes else "Not specified"
        procedure_codes_str = ", ".join(procedure_codes) if procedure_codes else "Not specified"

        # Build prompt
        prompt = MEDICAL_REPORT_VALIDATION_PROMPT.format(
            document_content=document_content[:10000],  # Limit content length
            service_dates=service_dates_str,
            diagnosis_codes=diagnosis_codes_str,
            procedure_codes=procedure_codes_str,
            provider_type=provider_type,
        )

        # Generate cache key
        cache_key = self._generate_cache_key(
            document_content,
            diagnosis_codes or [],
            procedure_codes or [],
        )

        # Call LLM
        llm_result = await self.llm_service.complete(
            prompt=prompt,
            system_prompt=MEDICAL_REPORT_SYSTEM_PROMPT,
            task_type=LLMTaskType.VALIDATION,
            tenant_id=tenant_id,
            json_mode=True,
            cache_key=cache_key,
        )

        execution_time = int((time.perf_counter() - start_time) * 1000)

        if not llm_result.success or not llm_result.parsed_data:
            logger.error(f"Medical report validation failed: {llm_result.error}")
            return MedicalReportValidationResult(
                is_valid=True,  # Don't reject on LLM failure
                compliance_level=ComplianceLevel.MINOR_ISSUES,
                section_analyses=[],
                date_consistency=DateConsistency(is_consistent=True),
                signature_validation=SignatureValidation(has_signature=True),
                diagnosis_support=[],
                critical_issues=[],
                warnings=[f"Documentation review could not be completed: {llm_result.error}"],
                recommendations=["Manual documentation review required"],
                overall_confidence=0.0,
                execution_time_ms=execution_time,
            )

        # Parse LLM response
        result = self._parse_validation_response(
            llm_result.parsed_data,
            execution_time,
            llm_result.provider_used,
        )

        logger.info(
            f"Medical report validation: valid={result.is_valid}, "
            f"compliance={result.compliance_level.value}, "
            f"confidence={result.overall_confidence:.2f}, "
            f"time={execution_time}ms"
        )

        return result

    def _generate_cache_key(
        self,
        content: str,
        diagnosis_codes: list[str],
        procedure_codes: list[str],
    ) -> str:
        """Generate cache key for validation request."""
        key_data = {
            "content_hash": hashlib.md5(content[:5000].encode()).hexdigest(),
            "dx": sorted(diagnosis_codes),
            "px": sorted(procedure_codes),
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return f"report_val:{hashlib.md5(key_str.encode()).hexdigest()}"

    def _parse_validation_response(
        self,
        data: dict,
        execution_time: int,
        provider_used: str,
    ) -> MedicalReportValidationResult:
        """Parse LLM response into structured result."""
        try:
            # Parse section analyses
            section_analyses = []
            for s in data.get("sections", []):
                try:
                    section = DocumentSection(s.get("section", ""))
                    section_analyses.append(SectionAnalysis(
                        section=section,
                        status=SectionStatus(s.get("status", "unclear")),
                        content_summary=s.get("content_summary"),
                        issues=s.get("issues", []),
                        recommendations=s.get("recommendations", []),
                        confidence=float(s.get("confidence", 0.5)),
                    ))
                except ValueError:
                    continue  # Skip unknown sections

            # Parse date consistency
            dc = data.get("date_consistency", {})
            date_consistency = DateConsistency(
                is_consistent=dc.get("is_consistent", True),
                report_date=dc.get("report_date"),
                service_date=dc.get("service_date"),
                signature_date=dc.get("signature_date"),
                issues=dc.get("issues", []),
            )

            # Parse signature validation
            sig = data.get("signature", {})
            signature_validation = SignatureValidation(
                has_signature=sig.get("has_signature", False),
                signature_type=sig.get("signature_type"),
                signer_name=sig.get("signer_name"),
                signer_credentials=sig.get("signer_credentials"),
                signature_date=sig.get("signature_date"),
                is_legible=sig.get("is_legible", True),
                issues=sig.get("issues", []),
            )

            # Parse diagnosis support
            diagnosis_support = []
            for ds in data.get("diagnosis_support", []):
                diagnosis_support.append(DiagnosisSupportAnalysis(
                    diagnosis_code=ds.get("diagnosis_code", ""),
                    diagnosis_description=ds.get("diagnosis_description"),
                    is_supported=ds.get("is_supported", False),
                    supporting_evidence=ds.get("supporting_evidence", []),
                    missing_documentation=ds.get("missing_documentation", []),
                    confidence=float(ds.get("confidence", 0.5)),
                ))

            compliance_level = ComplianceLevel(
                data.get("compliance_level", "minor_issues")
            )
            critical_issues = data.get("critical_issues", [])
            warnings = data.get("warnings", [])
            recommendations = data.get("recommendations", [])
            overall_confidence = float(data.get("overall_confidence", 0.5))

            # Determine validity
            is_valid = compliance_level not in (
                ComplianceLevel.NON_COMPLIANT,
            ) and len(critical_issues) == 0

            return MedicalReportValidationResult(
                is_valid=is_valid,
                compliance_level=compliance_level,
                section_analyses=section_analyses,
                date_consistency=date_consistency,
                signature_validation=signature_validation,
                diagnosis_support=diagnosis_support,
                critical_issues=critical_issues,
                warnings=warnings,
                recommendations=recommendations,
                overall_confidence=overall_confidence,
                execution_time_ms=execution_time,
                llm_provider_used=provider_used,
            )

        except Exception as e:
            logger.error(f"Error parsing validation response: {e}")
            return MedicalReportValidationResult(
                is_valid=True,
                compliance_level=ComplianceLevel.MINOR_ISSUES,
                section_analyses=[],
                date_consistency=DateConsistency(is_consistent=True),
                signature_validation=SignatureValidation(has_signature=True),
                diagnosis_support=[],
                critical_issues=[],
                warnings=[f"Error parsing documentation review: {str(e)}"],
                recommendations=["Manual documentation review required"],
                overall_confidence=0.0,
                execution_time_ms=execution_time,
                llm_provider_used=provider_used,
            )

    async def validate_signature_only(
        self,
        document_content: str,
        tenant_id: Optional[UUID] = None,
    ) -> SignatureValidation:
        """
        Validate just the signature portion of a document.

        Args:
            document_content: Document content
            tenant_id: Tenant ID

        Returns:
            SignatureValidation result
        """
        prompt = """Analyze this document and validate the provider signature:

Document:
{content}

Check for:
1. Is there a provider signature present?
2. What type of signature (handwritten, electronic, stamp)?
3. Is the signer's name visible?
4. Are credentials visible (MD, DO, NP, PA, etc.)?
5. Is there a signature date?
6. Is the signature legible?

Return JSON:
{{
    "has_signature": true|false,
    "signature_type": "handwritten|electronic|stamp|none",
    "signer_name": "name or null",
    "signer_credentials": "credentials or null",
    "signature_date": "YYYY-MM-DD or null",
    "is_legible": true|false,
    "issues": ["any issues found"]
}}""".format(content=document_content[:5000])

        llm_result = await self.llm_service.complete(
            prompt=prompt,
            system_prompt="You are a document reviewer checking for provider signatures.",
            task_type=LLMTaskType.VALIDATION,
            tenant_id=tenant_id,
            json_mode=True,
        )

        if not llm_result.success or not llm_result.parsed_data:
            return SignatureValidation(
                has_signature=False,
                issues=[f"Signature validation failed: {llm_result.error}"],
            )

        data = llm_result.parsed_data
        return SignatureValidation(
            has_signature=data.get("has_signature", False),
            signature_type=data.get("signature_type"),
            signer_name=data.get("signer_name"),
            signer_credentials=data.get("signer_credentials"),
            signature_date=data.get("signature_date"),
            is_legible=data.get("is_legible", True),
            issues=data.get("issues", []),
        )


# Singleton instance
_medical_report_validator: Optional[MedicalReportValidator] = None


def get_medical_report_validator() -> MedicalReportValidator:
    """Get or create the singleton medical report validator."""
    global _medical_report_validator
    if _medical_report_validator is None:
        _medical_report_validator = MedicalReportValidator()
    return _medical_report_validator
