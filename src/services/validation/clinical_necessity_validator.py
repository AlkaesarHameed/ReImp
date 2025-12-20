"""
Clinical Necessity Validator (Rule 5).

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Uses LLM to assess whether procedures are medically necessary
based on diagnoses, patient information, and clinical guidelines.
"""

import hashlib
import json
import logging
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


class NecessityLevel(str, Enum):
    """Medical necessity determination levels."""

    NECESSARY = "necessary"         # Clearly medically necessary
    LIKELY_NECESSARY = "likely_necessary"  # Probably necessary with some caveats
    UNCERTAIN = "uncertain"         # Needs clinical review
    LIKELY_UNNECESSARY = "likely_unnecessary"  # Probably not necessary
    UNNECESSARY = "unnecessary"     # Clearly not medically necessary


class NecessitySeverity(str, Enum):
    """Severity of necessity concern."""

    NONE = "none"           # No concerns
    LOW = "low"             # Minor concerns
    MEDIUM = "medium"       # Moderate concerns
    HIGH = "high"           # Significant concerns
    CRITICAL = "critical"   # Definite medical necessity issue


@dataclass
class ProcedureNecessityResult:
    """Necessity assessment for a single procedure."""

    cpt_code: str
    necessity_level: NecessityLevel
    confidence: float
    supporting_diagnoses: list[str]
    reasoning: str
    guidelines_referenced: list[str] = field(default_factory=list)
    alternatives_suggested: list[str] = field(default_factory=list)
    documentation_needed: list[str] = field(default_factory=list)


@dataclass
class ClinicalNecessityResult:
    """Complete clinical necessity validation result."""

    is_valid: bool
    overall_necessity: NecessityLevel
    overall_confidence: float
    procedure_assessments: list[ProcedureNecessityResult]
    critical_issues: list[str]
    warnings: list[str]
    recommendations: list[str]
    execution_time_ms: int
    llm_provider_used: str = ""

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical necessity issues."""
        return len(self.critical_issues) > 0

    @property
    def requires_review(self) -> bool:
        """Check if human review is required."""
        return (
            self.overall_necessity == NecessityLevel.UNCERTAIN
            or self.overall_confidence < 0.7
        )

    def to_evidence_dict(self) -> dict[str, Any]:
        """Convert to evidence format for rejection."""
        return {
            "is_valid": self.is_valid,
            "overall_necessity": self.overall_necessity.value,
            "confidence": self.overall_confidence,
            "procedure_count": len(self.procedure_assessments),
            "critical_issues": self.critical_issues,
            "procedures": [
                {
                    "cpt_code": p.cpt_code,
                    "necessity": p.necessity_level.value,
                    "confidence": p.confidence,
                    "reasoning": p.reasoning,
                    "supporting_diagnoses": p.supporting_diagnoses,
                }
                for p in self.procedure_assessments
            ],
            "recommendations": self.recommendations,
        }


# System prompt for clinical necessity assessment
CLINICAL_NECESSITY_SYSTEM_PROMPT = """You are an expert medical reviewer with deep knowledge of:
- Clinical practice guidelines (AMA, specialty societies)
- Medicare/Medicaid coverage determinations (LCD/NCD)
- Evidence-based medicine principles
- Medical necessity criteria

Your role is to assess whether procedures are medically necessary based on:
1. The diagnosed conditions (ICD-10 codes)
2. Patient demographics (age, gender)
3. Clinical guidelines and coverage policies
4. Standard of care for the conditions

Be objective and evidence-based in your assessments.
Cite specific guidelines or policies when available.
Flag any documentation that would strengthen medical necessity."""


CLINICAL_NECESSITY_PROMPT = """Assess the medical necessity of these procedures for the given patient:

PATIENT INFORMATION:
- Age: {age} years
- Gender: {gender}
- Setting: {place_of_service}

DIAGNOSES (ICD-10):
{diagnoses}

PROCEDURES REQUESTED (CPT):
{procedures}

ADDITIONAL CONTEXT:
{additional_context}

For each procedure, evaluate:
1. Is there clinical justification from the diagnoses?
2. Is this consistent with clinical guidelines?
3. Are there red flags suggesting over-utilization?
4. What documentation would strengthen medical necessity?

Return your assessment as JSON with this structure:
{{
    "overall_assessment": {{
        "necessity_level": "necessary|likely_necessary|uncertain|likely_unnecessary|unnecessary",
        "confidence": 0.0 to 1.0,
        "summary": "Brief overall summary"
    }},
    "procedures": [
        {{
            "cpt_code": "XXXXX",
            "necessity_level": "necessary|likely_necessary|uncertain|likely_unnecessary|unnecessary",
            "confidence": 0.0 to 1.0,
            "supporting_diagnoses": ["ICD codes that support this procedure"],
            "reasoning": "Detailed reasoning for the assessment",
            "guidelines_referenced": ["Relevant guidelines/policies"],
            "alternatives": ["Alternative approaches if applicable"],
            "documentation_needed": ["Documentation that would help"]
        }}
    ],
    "critical_issues": ["List of critical concerns"],
    "warnings": ["List of warnings/concerns"],
    "recommendations": ["Recommendations for the claim"]
}}"""


class ClinicalNecessityValidator:
    """
    Validates clinical/medical necessity of procedures.

    Uses LLM to assess whether procedures are medically
    justified based on diagnoses and clinical guidelines.

    Source: Design Document Section 2.2 - Validation Rules (Rule 5)
    """

    def __init__(
        self,
        llm_service: Optional[LLMValidationService] = None,
    ):
        """
        Initialize the clinical necessity validator.

        Args:
            llm_service: LLM validation service for assessments
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
        icd_codes: list[str],
        cpt_codes: list[str],
        patient_age: Optional[int] = None,
        patient_gender: Optional[str] = None,
        place_of_service: str = "Office",
        additional_context: str = "",
        tenant_id: Optional[UUID] = None,
    ) -> ClinicalNecessityResult:
        """
        Validate clinical necessity of procedures.

        Args:
            icd_codes: List of ICD-10 diagnosis codes
            cpt_codes: List of CPT procedure codes
            patient_age: Patient age in years
            patient_gender: Patient gender ("M" or "F")
            place_of_service: Place of service description
            additional_context: Additional clinical context
            tenant_id: Tenant ID for LLM configuration

        Returns:
            ClinicalNecessityResult with assessment details
        """
        import time
        start_time = time.perf_counter()

        # Handle empty inputs
        if not icd_codes:
            return ClinicalNecessityResult(
                is_valid=False,
                overall_necessity=NecessityLevel.UNCERTAIN,
                overall_confidence=0.0,
                procedure_assessments=[],
                critical_issues=["No diagnosis codes provided"],
                warnings=[],
                recommendations=["Provide diagnosis codes for medical necessity review"],
                execution_time_ms=0,
            )

        if not cpt_codes:
            return ClinicalNecessityResult(
                is_valid=True,
                overall_necessity=NecessityLevel.NECESSARY,
                overall_confidence=1.0,
                procedure_assessments=[],
                critical_issues=[],
                warnings=["No procedure codes to validate"],
                recommendations=[],
                execution_time_ms=0,
            )

        # Format diagnoses and procedures for prompt
        diagnoses_text = "\n".join(f"- {code}" for code in icd_codes)
        procedures_text = "\n".join(f"- {code}" for code in cpt_codes)

        # Build prompt
        prompt = CLINICAL_NECESSITY_PROMPT.format(
            age=patient_age or "Unknown",
            gender=patient_gender or "Unknown",
            place_of_service=place_of_service,
            diagnoses=diagnoses_text,
            procedures=procedures_text,
            additional_context=additional_context or "None provided",
        )

        # Generate cache key
        cache_key = self._generate_cache_key(
            icd_codes, cpt_codes, patient_age, patient_gender
        )

        # Call LLM
        llm_result = await self.llm_service.complete(
            prompt=prompt,
            system_prompt=CLINICAL_NECESSITY_SYSTEM_PROMPT,
            task_type=LLMTaskType.NECESSITY,
            tenant_id=tenant_id,
            json_mode=True,
            cache_key=cache_key,
        )

        execution_time = int((time.perf_counter() - start_time) * 1000)

        if not llm_result.success or not llm_result.parsed_data:
            logger.error(f"Clinical necessity LLM call failed: {llm_result.error}")
            return ClinicalNecessityResult(
                is_valid=True,  # Don't reject on LLM failure
                overall_necessity=NecessityLevel.UNCERTAIN,
                overall_confidence=0.0,
                procedure_assessments=[],
                critical_issues=[],
                warnings=[f"Medical necessity review could not be completed: {llm_result.error}"],
                recommendations=["Manual review required"],
                execution_time_ms=execution_time,
            )

        # Parse LLM response
        result = self._parse_llm_response(
            llm_result.parsed_data,
            cpt_codes,
            execution_time,
            llm_result.provider_used,
        )

        logger.info(
            f"Clinical necessity validation: valid={result.is_valid}, "
            f"necessity={result.overall_necessity.value}, "
            f"confidence={result.overall_confidence:.2f}, "
            f"time={execution_time}ms"
        )

        return result

    def _generate_cache_key(
        self,
        icd_codes: list[str],
        cpt_codes: list[str],
        patient_age: Optional[int],
        patient_gender: Optional[str],
    ) -> str:
        """Generate a cache key for the validation request."""
        key_data = {
            "icd": sorted(icd_codes),
            "cpt": sorted(cpt_codes),
            "age_group": self._age_group(patient_age) if patient_age else "unknown",
            "gender": patient_gender or "unknown",
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return f"necessity:{hashlib.md5(key_str.encode()).hexdigest()}"

    def _age_group(self, age: int) -> str:
        """Convert age to age group for caching."""
        if age < 18:
            return "pediatric"
        elif age < 65:
            return "adult"
        else:
            return "elderly"

    def _parse_llm_response(
        self,
        data: dict,
        cpt_codes: list[str],
        execution_time: int,
        provider_used: str,
    ) -> ClinicalNecessityResult:
        """Parse LLM response into structured result."""
        try:
            overall = data.get("overall_assessment", {})
            overall_necessity = NecessityLevel(
                overall.get("necessity_level", "uncertain")
            )
            overall_confidence = float(overall.get("confidence", 0.5))

            # Parse procedure assessments
            procedure_assessments = []
            for proc in data.get("procedures", []):
                assessment = ProcedureNecessityResult(
                    cpt_code=proc.get("cpt_code", ""),
                    necessity_level=NecessityLevel(
                        proc.get("necessity_level", "uncertain")
                    ),
                    confidence=float(proc.get("confidence", 0.5)),
                    supporting_diagnoses=proc.get("supporting_diagnoses", []),
                    reasoning=proc.get("reasoning", ""),
                    guidelines_referenced=proc.get("guidelines_referenced", []),
                    alternatives_suggested=proc.get("alternatives", []),
                    documentation_needed=proc.get("documentation_needed", []),
                )
                procedure_assessments.append(assessment)

            # If not all procedures were assessed, add placeholders
            assessed_codes = {p.cpt_code for p in procedure_assessments}
            for cpt in cpt_codes:
                if cpt not in assessed_codes:
                    procedure_assessments.append(
                        ProcedureNecessityResult(
                            cpt_code=cpt,
                            necessity_level=NecessityLevel.UNCERTAIN,
                            confidence=0.3,
                            supporting_diagnoses=[],
                            reasoning="Not assessed by LLM",
                        )
                    )

            critical_issues = data.get("critical_issues", [])
            warnings = data.get("warnings", [])
            recommendations = data.get("recommendations", [])

            # Determine validity based on necessity assessments
            is_valid = overall_necessity not in (
                NecessityLevel.UNNECESSARY,
                NecessityLevel.LIKELY_UNNECESSARY,
            )

            return ClinicalNecessityResult(
                is_valid=is_valid,
                overall_necessity=overall_necessity,
                overall_confidence=overall_confidence,
                procedure_assessments=procedure_assessments,
                critical_issues=critical_issues,
                warnings=warnings,
                recommendations=recommendations,
                execution_time_ms=execution_time,
                llm_provider_used=provider_used,
            )

        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return ClinicalNecessityResult(
                is_valid=True,
                overall_necessity=NecessityLevel.UNCERTAIN,
                overall_confidence=0.0,
                procedure_assessments=[],
                critical_issues=[],
                warnings=[f"Error parsing assessment: {str(e)}"],
                recommendations=["Manual review required"],
                execution_time_ms=execution_time,
                llm_provider_used=provider_used,
            )

    async def validate_single_procedure(
        self,
        icd_codes: list[str],
        cpt_code: str,
        patient_age: Optional[int] = None,
        patient_gender: Optional[str] = None,
    ) -> ProcedureNecessityResult:
        """
        Validate necessity of a single procedure.

        Convenience method for single-procedure validation.
        """
        result = await self.validate(
            icd_codes=icd_codes,
            cpt_codes=[cpt_code],
            patient_age=patient_age,
            patient_gender=patient_gender,
        )

        if result.procedure_assessments:
            return result.procedure_assessments[0]

        return ProcedureNecessityResult(
            cpt_code=cpt_code,
            necessity_level=NecessityLevel.UNCERTAIN,
            confidence=0.0,
            supporting_diagnoses=[],
            reasoning="Validation failed",
        )


# Singleton instance
_clinical_necessity_validator: Optional[ClinicalNecessityValidator] = None


def get_clinical_necessity_validator() -> ClinicalNecessityValidator:
    """Get or create the singleton clinical necessity validator."""
    global _clinical_necessity_validator
    if _clinical_necessity_validator is None:
        _clinical_necessity_validator = ClinicalNecessityValidator()
    return _clinical_necessity_validator
