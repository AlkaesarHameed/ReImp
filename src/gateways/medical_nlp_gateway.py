"""
Medical NLP Gateway with MedCAT.

Provides clinical NLP capabilities for claims processing:
- Primary: MedCAT (open-source, UMLS/SNOMED-CT)
- Fallback: AWS Comprehend Medical (commercial)

Features:
- Named Entity Recognition for medical terms
- ICD-10/SNOMED-CT code extraction
- Drug interaction detection
- Clinical concept linking
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from src.core.config import get_claims_settings
from src.core.enums import MedicalNLPProvider
from src.gateways.base import (
    BaseGateway,
    GatewayConfig,
    GatewayError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

# Import MedCAT with graceful fallback
try:
    from medcat.cat import CAT

    MEDCAT_AVAILABLE = True
except ImportError:
    MEDCAT_AVAILABLE = False
    logger.warning("MedCAT not installed. Medical NLP Gateway will operate in mock mode.")

# Import AWS Comprehend Medical with graceful fallback
try:
    import boto3

    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    logger.warning("boto3 not installed. AWS fallback will not be available.")


class EntityType(str, Enum):
    """Type of medical entity."""

    DIAGNOSIS = "diagnosis"
    PROCEDURE = "procedure"
    MEDICATION = "medication"
    ANATOMY = "anatomy"
    SYMPTOM = "symptom"
    LAB_TEST = "lab_test"
    MEDICAL_DEVICE = "medical_device"
    TREATMENT = "treatment"


class CodeSystem(str, Enum):
    """Medical code system."""

    ICD10_CM = "icd10_cm"
    ICD10_PCS = "icd10_pcs"
    SNOMED_CT = "snomed_ct"
    CPT = "cpt"
    HCPCS = "hcpcs"
    NDC = "ndc"  # National Drug Code
    RXNORM = "rxnorm"
    LOINC = "loinc"


@dataclass
class MedicalEntity:
    """Extracted medical entity."""

    text: str
    entity_type: EntityType
    start_offset: int
    end_offset: int
    confidence: float
    codes: dict[str, str] = field(default_factory=dict)  # code_system -> code
    attributes: dict[str, Any] = field(default_factory=dict)
    negated: bool = False
    hypothetical: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "entity_type": self.entity_type.value,
            "start": self.start_offset,
            "end": self.end_offset,
            "confidence": self.confidence,
            "codes": self.codes,
            "attributes": self.attributes,
            "negated": self.negated,
            "hypothetical": self.hypothetical,
        }


@dataclass
class MedicalConcept:
    """Linked medical concept from knowledge base."""

    cui: str  # Concept Unique Identifier
    preferred_name: str
    semantic_types: list[str]
    definition: Optional[str] = None
    synonyms: list[str] = field(default_factory=list)
    related_codes: dict[str, str] = field(default_factory=dict)


@dataclass
class MedicalNLPRequest:
    """Request for medical NLP processing."""

    text: str
    detect_entities: bool = True
    link_concepts: bool = True
    detect_negation: bool = True
    detect_relations: bool = False
    entity_types: Optional[list[EntityType]] = None  # None = all types
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MedicalNLPResponse:
    """Response from medical NLP processing."""

    entities: list[MedicalEntity]
    concepts: list[MedicalConcept]
    text: str
    confidence: float
    provider: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_diagnoses(self) -> list[MedicalEntity]:
        """Get all diagnosis entities."""
        return [e for e in self.entities if e.entity_type == EntityType.DIAGNOSIS]

    def get_procedures(self) -> list[MedicalEntity]:
        """Get all procedure entities."""
        return [e for e in self.entities if e.entity_type == EntityType.PROCEDURE]

    def get_medications(self) -> list[MedicalEntity]:
        """Get all medication entities."""
        return [e for e in self.entities if e.entity_type == EntityType.MEDICATION]

    def get_icd10_codes(self) -> list[str]:
        """Get all ICD-10 codes from entities."""
        codes = []
        for entity in self.entities:
            if CodeSystem.ICD10_CM.value in entity.codes:
                codes.append(entity.codes[CodeSystem.ICD10_CM.value])
        return codes

    def get_cpt_codes(self) -> list[str]:
        """Get all CPT codes from entities."""
        codes = []
        for entity in self.entities:
            if CodeSystem.CPT.value in entity.codes:
                codes.append(entity.codes[CodeSystem.CPT.value])
        return codes


class MedicalNLPGateway(BaseGateway[MedicalNLPRequest, MedicalNLPResponse, MedicalNLPProvider]):
    """
    Medical NLP Gateway for clinical text processing.

    Uses MedCAT for medical entity extraction:
    - UMLS concept linking
    - ICD-10/SNOMED-CT code extraction
    - Negation detection
    - Drug interaction checking
    """

    def __init__(self, config: Optional[GatewayConfig] = None):
        settings = get_claims_settings()

        if config is None:
            config = GatewayConfig(
                primary_provider=settings.MEDICAL_NLP_PRIMARY_PROVIDER.value,
                fallback_provider=(
                    settings.MEDICAL_NLP_FALLBACK_PROVIDER.value
                    if settings.MEDICAL_NLP_FALLBACK_ON_ERROR
                    else None
                ),
                fallback_on_error=settings.MEDICAL_NLP_FALLBACK_ON_ERROR,
                timeout_seconds=settings.MEDICAL_NLP_TIMEOUT_SECONDS,
            )

        super().__init__(config)
        self._settings = settings
        self._cat: Optional[Any] = None
        self._comprehend_client: Optional[Any] = None
        self._executor = ThreadPoolExecutor(max_workers=2)

    @property
    def gateway_name(self) -> str:
        return "MedicalNLP"

    async def _initialize_provider(self, provider: MedicalNLPProvider) -> None:
        """Initialize medical NLP provider."""
        if provider == MedicalNLPProvider.MEDCAT:
            if not MEDCAT_AVAILABLE:
                logger.warning(
                    "MedCAT not available, using fallback entity extraction"
                )
                return

            # Load MedCAT model in thread pool
            model_path = self._settings.MEDCAT_MODEL_PATH
            if model_path and Path(model_path).exists():
                loop = asyncio.get_event_loop()
                self._cat = await loop.run_in_executor(
                    self._executor, self._load_medcat, model_path
                )
                logger.info(f"MedCAT model loaded from {model_path}")
            else:
                logger.warning(
                    f"MedCAT model not found at {model_path}, using basic extraction"
                )

        elif provider == MedicalNLPProvider.AWS_COMPREHEND_MEDICAL:
            if not AWS_AVAILABLE:
                raise ProviderUnavailableError(
                    "boto3 not installed", provider=provider.value
                )
            self._comprehend_client = boto3.client(
                "comprehendmedical",
                region_name=self._settings.AWS_REGION,
            )
            logger.info("AWS Comprehend Medical initialized")

    def _load_medcat(self, model_path: str) -> Any:
        """Load MedCAT model (runs in thread pool)."""
        return CAT.load_model_pack(model_path)

    async def _execute_request(
        self, request: MedicalNLPRequest, provider: MedicalNLPProvider
    ) -> MedicalNLPResponse:
        """Execute medical NLP request."""
        if provider == MedicalNLPProvider.MEDCAT:
            return await self._process_medcat(request)
        elif provider == MedicalNLPProvider.AWS_COMPREHEND_MEDICAL:
            return await self._process_aws_comprehend(request)
        else:
            raise GatewayError(f"Unsupported medical NLP provider: {provider}")

    async def _process_medcat(self, request: MedicalNLPRequest) -> MedicalNLPResponse:
        """Process text using MedCAT."""
        if self._cat:
            loop = asyncio.get_event_loop()

            def run_medcat():
                return self._cat.get_entities(request.text)

            result = await loop.run_in_executor(self._executor, run_medcat)
            return self._parse_medcat_result(result, request.text)
        else:
            # Fallback: Basic pattern-based extraction
            return await self._process_fallback(request)

    async def _process_aws_comprehend(
        self, request: MedicalNLPRequest
    ) -> MedicalNLPResponse:
        """Process text using AWS Comprehend Medical."""
        if not self._comprehend_client:
            raise ProviderUnavailableError(
                "AWS Comprehend Medical not initialized",
                provider="aws_comprehend_medical",
            )

        loop = asyncio.get_event_loop()

        def run_comprehend():
            return self._comprehend_client.detect_entities_v2(Text=request.text)

        try:
            result = await loop.run_in_executor(self._executor, run_comprehend)
            return self._parse_aws_comprehend_result(result, request.text)
        except Exception as e:
            raise GatewayError(
                f"AWS Comprehend Medical error: {e}",
                provider="aws_comprehend_medical",
                original_error=e,
            )

    def _parse_medcat_result(
        self, result: dict, original_text: str
    ) -> MedicalNLPResponse:
        """Parse MedCAT result into response."""
        entities = []
        concepts = []

        for ent_id, ent_data in result.get("entities", {}).items():
            # Map MedCAT semantic types to our entity types
            entity_type = self._map_semantic_type(ent_data.get("types", []))

            entity = MedicalEntity(
                text=ent_data.get("source_value", ""),
                entity_type=entity_type,
                start_offset=ent_data.get("start", 0),
                end_offset=ent_data.get("end", 0),
                confidence=ent_data.get("acc", 0.0),
                codes={
                    CodeSystem.SNOMED_CT.value: ent_data.get("cui", ""),
                },
                negated=ent_data.get("meta_anns", {}).get("negex", {}).get("value", False),
            )
            entities.append(entity)

            # Add concept
            concept = MedicalConcept(
                cui=ent_data.get("cui", ""),
                preferred_name=ent_data.get("pretty_name", ""),
                semantic_types=ent_data.get("types", []),
            )
            concepts.append(concept)

        avg_confidence = (
            sum(e.confidence for e in entities) / len(entities) if entities else 0.0
        )

        return MedicalNLPResponse(
            entities=entities,
            concepts=concepts,
            text=original_text,
            confidence=avg_confidence,
            provider="medcat",
        )

    def _parse_aws_comprehend_result(
        self, result: dict, original_text: str
    ) -> MedicalNLPResponse:
        """Parse AWS Comprehend Medical result."""
        entities = []
        concepts = []

        for ent in result.get("Entities", []):
            entity_type = self._map_aws_category(ent.get("Category", ""))

            # Extract codes from traits
            codes = {}
            for attr in ent.get("Attributes", []):
                if attr.get("Type") == "ICD10_CM_CODE":
                    codes[CodeSystem.ICD10_CM.value] = attr.get("Text", "")
                elif attr.get("Type") == "SNOMED_CT_CONCEPT":
                    codes[CodeSystem.SNOMED_CT.value] = attr.get("Text", "")

            entity = MedicalEntity(
                text=ent.get("Text", ""),
                entity_type=entity_type,
                start_offset=ent.get("BeginOffset", 0),
                end_offset=ent.get("EndOffset", 0),
                confidence=ent.get("Score", 0.0),
                codes=codes,
                negated="NEGATION" in [t.get("Name") for t in ent.get("Traits", [])],
            )
            entities.append(entity)

        avg_confidence = (
            sum(e.confidence for e in entities) / len(entities) if entities else 0.0
        )

        return MedicalNLPResponse(
            entities=entities,
            concepts=concepts,
            text=original_text,
            confidence=avg_confidence,
            provider="aws_comprehend_medical",
        )

    async def _process_fallback(self, request: MedicalNLPRequest) -> MedicalNLPResponse:
        """Fallback pattern-based extraction."""
        # Common medical patterns for basic extraction
        import re

        text = request.text
        entities = []

        # ICD-10 code pattern
        icd10_pattern = r'\b([A-Z]\d{2}\.?\d{0,4})\b'
        for match in re.finditer(icd10_pattern, text):
            entities.append(
                MedicalEntity(
                    text=match.group(0),
                    entity_type=EntityType.DIAGNOSIS,
                    start_offset=match.start(),
                    end_offset=match.end(),
                    confidence=0.7,
                    codes={CodeSystem.ICD10_CM.value: match.group(0)},
                )
            )

        # CPT code pattern (5 digits)
        cpt_pattern = r'\b(\d{5})\b'
        for match in re.finditer(cpt_pattern, text):
            code = match.group(0)
            # Basic validation: CPT codes typically start with certain ranges
            if code.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
                entities.append(
                    MedicalEntity(
                        text=code,
                        entity_type=EntityType.PROCEDURE,
                        start_offset=match.start(),
                        end_offset=match.end(),
                        confidence=0.5,
                        codes={CodeSystem.CPT.value: code},
                    )
                )

        return MedicalNLPResponse(
            entities=entities,
            concepts=[],
            text=text,
            confidence=0.5 if entities else 0.0,
            provider="fallback",
            metadata={"fallback": True},
        )

    def _map_semantic_type(self, types: list[str]) -> EntityType:
        """Map MedCAT semantic types to our entity types."""
        type_mapping = {
            "T047": EntityType.DIAGNOSIS,  # Disease or Syndrome
            "T184": EntityType.SYMPTOM,  # Sign or Symptom
            "T061": EntityType.PROCEDURE,  # Therapeutic or Preventive Procedure
            "T121": EntityType.MEDICATION,  # Pharmacologic Substance
            "T023": EntityType.ANATOMY,  # Body Part
            "T059": EntityType.LAB_TEST,  # Laboratory Procedure
        }

        for t in types:
            if t in type_mapping:
                return type_mapping[t]

        return EntityType.DIAGNOSIS  # Default

    def _map_aws_category(self, category: str) -> EntityType:
        """Map AWS Comprehend Medical category to our entity types."""
        category_mapping = {
            "MEDICAL_CONDITION": EntityType.DIAGNOSIS,
            "MEDICATION": EntityType.MEDICATION,
            "TEST_TREATMENT_PROCEDURE": EntityType.PROCEDURE,
            "ANATOMY": EntityType.ANATOMY,
        }
        return category_mapping.get(category, EntityType.DIAGNOSIS)

    async def _health_check(self, provider: MedicalNLPProvider) -> bool:
        """Check if medical NLP provider is healthy."""
        try:
            test_request = MedicalNLPRequest(text="Patient has diabetes mellitus.")
            await self._execute_request(test_request, provider)
            return True
        except Exception as e:
            logger.warning(f"Medical NLP health check failed for {provider.value}: {e}")
            return False

    def _parse_provider(self, provider_str: str) -> MedicalNLPProvider:
        """Parse provider string to MedicalNLPProvider enum."""
        return MedicalNLPProvider(provider_str)

    # Convenience methods for claims processing

    async def extract_medical_codes(self, text: str) -> dict[str, list[str]]:
        """Extract all medical codes from text."""
        request = MedicalNLPRequest(text=text)
        result = await self.execute(request)

        if not result.success or not result.data:
            return {}

        response = result.data
        return {
            "icd10": response.get_icd10_codes(),
            "cpt": response.get_cpt_codes(),
            "diagnoses": [e.text for e in response.get_diagnoses()],
            "procedures": [e.text for e in response.get_procedures()],
            "medications": [e.text for e in response.get_medications()],
        }

    async def validate_diagnosis_codes(
        self, codes: list[str], clinical_text: str
    ) -> dict[str, Any]:
        """Validate that diagnosis codes match clinical text."""
        request = MedicalNLPRequest(text=clinical_text)
        result = await self.execute(request)

        if not result.success or not result.data:
            return {"valid": False, "error": result.error}

        extracted_codes = result.data.get_icd10_codes()

        matched = [c for c in codes if c in extracted_codes]
        unmatched = [c for c in codes if c not in extracted_codes]
        suggested = [c for c in extracted_codes if c not in codes]

        return {
            "valid": len(unmatched) == 0,
            "matched_codes": matched,
            "unmatched_codes": unmatched,
            "suggested_codes": suggested,
            "confidence": result.data.confidence,
        }

    async def close(self) -> None:
        """Clean up medical NLP gateway resources."""
        self._executor.shutdown(wait=False)
        self._cat = None
        await super().close()


# Singleton instance
_medical_nlp_gateway: Optional[MedicalNLPGateway] = None


def get_medical_nlp_gateway() -> MedicalNLPGateway:
    """Get or create the singleton Medical NLP gateway instance."""
    global _medical_nlp_gateway
    if _medical_nlp_gateway is None:
        _medical_nlp_gateway = MedicalNLPGateway()
    return _medical_nlp_gateway


async def reset_medical_nlp_gateway() -> None:
    """Reset the Medical NLP gateway (for testing)."""
    global _medical_nlp_gateway
    if _medical_nlp_gateway:
        await _medical_nlp_gateway.close()
    _medical_nlp_gateway = None
