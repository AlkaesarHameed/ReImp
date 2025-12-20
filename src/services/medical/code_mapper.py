"""
Diagnosis-Procedure Code Mapping Service.
Source: Design Document Section 4.1 - Medical Validation
Verified: 2025-12-18

Maps diagnosis codes to valid procedure codes and vice versa.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from src.services.medical.code_validator import CodeSystem, MedicalCodeValidator, get_code_validator


class MappingStrength(str, Enum):
    """Strength of diagnosis-procedure mapping."""

    STRONG = "strong"  # Well-established clinical relationship
    MODERATE = "moderate"  # Common but not exclusive
    WEAK = "weak"  # Possible but unusual
    NONE = "none"  # No established relationship


class CodeMapping(BaseModel):
    """A mapping between diagnosis and procedure codes."""

    diagnosis_code: str
    procedure_code: str
    strength: MappingStrength
    bidirectional: bool = True
    notes: Optional[str] = None
    source: str = "clinical_guideline"


class MappingResult(BaseModel):
    """Result of code mapping lookup."""

    source_code: str
    source_type: str  # diagnosis or procedure
    mappings: list[CodeMapping] = Field(default_factory=list)
    is_valid_combination: bool = True
    confidence_score: float = 1.0
    warnings: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class DiagnosisProcedureMapper:
    """
    Maps diagnosis codes to valid procedure codes.

    Uses clinical guidelines and code relationships to determine
    valid diagnosis-procedure combinations for claims validation.
    """

    # Clinical mappings - diagnosis to procedures that strongly support it
    CLINICAL_MAPPINGS: dict[str, dict] = {
        # Diabetes mappings
        "E11.9": {
            "procedures": ["82947", "83036", "80053", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "E11.65": {
            "procedures": ["82947", "83036", "80053", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "E11.21": {
            "procedures": ["82565", "81001", "80053", "99213"],
            "strength": MappingStrength.STRONG,
        },
        # Hypertension mappings
        "I10": {
            "procedures": ["93000", "80061", "80053", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "I25.10": {
            "procedures": ["93000", "93015", "80061", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "I50.9": {
            "procedures": ["93000", "93306", "71046", "80053", "99214"],
            "strength": MappingStrength.STRONG,
        },
        # Respiratory mappings
        "J06.9": {
            "procedures": ["99213", "87880", "71046"],
            "strength": MappingStrength.STRONG,
        },
        "J18.9": {
            "procedures": ["71046", "87070", "85025", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "J45.909": {
            "procedures": ["94010", "94060", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "J44.9": {
            "procedures": ["94010", "94060", "71046", "99214"],
            "strength": MappingStrength.STRONG,
        },
        # Musculoskeletal mappings
        "M54.5": {
            "procedures": ["72148", "97110", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "M17.11": {
            "procedures": ["27447", "73560", "20610", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "M17.12": {
            "procedures": ["27447", "73560", "20610", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "M16.11": {
            "procedures": ["27130", "73501", "20610", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "M16.12": {
            "procedures": ["27130", "73501", "20610", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        # GI mappings
        "K21.0": {
            "procedures": ["43239", "91034", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "K58.9": {
            "procedures": ["45378", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "K80.20": {
            "procedures": ["47562", "74176", "99213"],
            "strength": MappingStrength.STRONG,
        },
        # Renal mappings
        "N18.3": {
            "procedures": ["82565", "80053", "36415", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "N39.0": {
            "procedures": ["81001", "87086", "99213"],
            "strength": MappingStrength.STRONG,
        },
        # Neurological mappings
        "G43.909": {
            "procedures": ["70553", "70552", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "G89.29": {
            "procedures": ["64483", "97110", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        # Mental health mappings
        "F32.9": {
            "procedures": ["90834", "90837", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        "F41.1": {
            "procedures": ["90834", "90837", "99213", "99214"],
            "strength": MappingStrength.STRONG,
        },
        # Screening/preventive mappings
        "Z12.31": {
            "procedures": ["77067"],
            "strength": MappingStrength.STRONG,
        },
        "Z00.00": {
            "procedures": ["99385", "99386", "99387", "80053", "85025"],
            "strength": MappingStrength.STRONG,
        },
        "Z23": {
            "procedures": ["90471", "90714", "90732", "90658"],
            "strength": MappingStrength.STRONG,
        },
        # Oncology mappings
        "C50.911": {
            "procedures": ["19301", "19120", "77067", "99214", "99215"],
            "strength": MappingStrength.STRONG,
        },
        "C61": {
            "procedures": ["84153", "55700", "76872", "99214", "99215"],
            "strength": MappingStrength.STRONG,
        },
    }

    # Universal procedures valid with most diagnoses
    UNIVERSAL_PROCEDURES = {
        "99213", "99214", "99215",  # Office visits
        "99203", "99204", "99205",  # New patient visits
        "36415",  # Venipuncture
    }

    def __init__(self, code_validator: Optional[MedicalCodeValidator] = None):
        """
        Initialize DiagnosisProcedureMapper.

        Args:
            code_validator: MedicalCodeValidator instance
        """
        self.code_validator = code_validator or get_code_validator()

    def get_valid_procedures(
        self,
        diagnosis_code: str,
        country: str = "US",
    ) -> MappingResult:
        """
        Get valid procedures for a diagnosis code.

        Args:
            diagnosis_code: The ICD-10 diagnosis code
            country: Country code (US or AU)

        Returns:
            MappingResult with valid procedures
        """
        diagnosis_code = diagnosis_code.strip().upper()

        result = MappingResult(
            source_code=diagnosis_code,
            source_type="diagnosis",
        )

        # Check if diagnosis code is valid
        code_system = CodeSystem.ICD10_AM if country.upper() == "AU" else CodeSystem.ICD10_CM
        validation = self.code_validator.validate_code(diagnosis_code, code_system)

        if not validation.is_valid:
            result.is_valid_combination = False
            result.confidence_score = 0.0
            result.warnings.append(f"Invalid diagnosis code: {diagnosis_code}")
            return result

        # Get clinical mappings
        clinical_mapping = self.CLINICAL_MAPPINGS.get(diagnosis_code)

        if clinical_mapping:
            for proc_code in clinical_mapping["procedures"]:
                mapping = CodeMapping(
                    diagnosis_code=diagnosis_code,
                    procedure_code=proc_code,
                    strength=clinical_mapping["strength"],
                )
                result.mappings.append(mapping)

        # Also include common procedures from code database
        common_procs = self.code_validator.get_common_procedures(diagnosis_code, country)
        existing_procs = {m.procedure_code for m in result.mappings}

        for proc_code in common_procs:
            if proc_code not in existing_procs:
                mapping = CodeMapping(
                    diagnosis_code=diagnosis_code,
                    procedure_code=proc_code,
                    strength=MappingStrength.MODERATE,
                    source="code_database",
                )
                result.mappings.append(mapping)

        # Add universal procedures
        for proc_code in self.UNIVERSAL_PROCEDURES:
            if proc_code not in existing_procs:
                mapping = CodeMapping(
                    diagnosis_code=diagnosis_code,
                    procedure_code=proc_code,
                    strength=MappingStrength.WEAK,
                    notes="Universal E/M code",
                    source="universal",
                )
                result.mappings.append(mapping)

        return result

    def validate_combination(
        self,
        diagnosis_code: str,
        procedure_code: str,
        country: str = "US",
    ) -> MappingResult:
        """
        Validate a diagnosis-procedure combination.

        Args:
            diagnosis_code: The ICD-10 diagnosis code
            procedure_code: The CPT/ACHI procedure code
            country: Country code (US or AU)

        Returns:
            MappingResult with validation details
        """
        diagnosis_code = diagnosis_code.strip().upper()
        procedure_code = procedure_code.strip().upper()

        result = MappingResult(
            source_code=f"{diagnosis_code}:{procedure_code}",
            source_type="combination",
        )

        # Validate both codes
        dx_system = CodeSystem.ICD10_AM if country.upper() == "AU" else CodeSystem.ICD10_CM
        px_system = CodeSystem.ACHI if country.upper() == "AU" else CodeSystem.CPT

        dx_validation = self.code_validator.validate_code(diagnosis_code, dx_system)
        px_validation = self.code_validator.validate_code(procedure_code, px_system)

        if not dx_validation.format_valid:
            result.is_valid_combination = False
            result.confidence_score = 0.0
            result.warnings.append(f"Invalid diagnosis code format: {diagnosis_code}")
            return result

        if not px_validation.format_valid:
            result.is_valid_combination = False
            result.confidence_score = 0.0
            result.warnings.append(f"Invalid procedure code format: {procedure_code}")
            return result

        # Check clinical mappings
        clinical_mapping = self.CLINICAL_MAPPINGS.get(diagnosis_code)

        if clinical_mapping and procedure_code in clinical_mapping["procedures"]:
            mapping = CodeMapping(
                diagnosis_code=diagnosis_code,
                procedure_code=procedure_code,
                strength=clinical_mapping["strength"],
            )
            result.mappings.append(mapping)
            result.is_valid_combination = True
            result.confidence_score = 1.0 if clinical_mapping["strength"] == MappingStrength.STRONG else 0.8
            return result

        # Check universal procedures
        if procedure_code in self.UNIVERSAL_PROCEDURES:
            mapping = CodeMapping(
                diagnosis_code=diagnosis_code,
                procedure_code=procedure_code,
                strength=MappingStrength.WEAK,
                notes="Universal E/M code",
            )
            result.mappings.append(mapping)
            result.is_valid_combination = True
            result.confidence_score = 0.6
            return result

        # Check common procedures from database
        common_procs = self.code_validator.get_common_procedures(diagnosis_code, country)
        if procedure_code in common_procs:
            mapping = CodeMapping(
                diagnosis_code=diagnosis_code,
                procedure_code=procedure_code,
                strength=MappingStrength.MODERATE,
                source="code_database",
            )
            result.mappings.append(mapping)
            result.is_valid_combination = True
            result.confidence_score = 0.8
            return result

        # No mapping found - may still be valid, just not in our database
        result.is_valid_combination = True  # Don't deny just because not in mapping
        result.confidence_score = 0.4
        result.warnings.append(
            f"No established mapping between {diagnosis_code} and {procedure_code}. "
            "Manual review recommended."
        )

        # Suggest valid procedures
        valid_procs = self.get_valid_procedures(diagnosis_code, country)
        if valid_procs.mappings:
            strong_procs = [
                m.procedure_code
                for m in valid_procs.mappings
                if m.strength == MappingStrength.STRONG
            ][:3]
            if strong_procs:
                result.suggestions.append(
                    f"Consider procedures commonly used with {diagnosis_code}: {', '.join(strong_procs)}"
                )

        return result

    def get_valid_diagnoses(
        self,
        procedure_code: str,
        country: str = "US",
    ) -> MappingResult:
        """
        Get valid diagnoses for a procedure code.

        Args:
            procedure_code: The CPT/ACHI procedure code
            country: Country code (US or AU)

        Returns:
            MappingResult with valid diagnoses
        """
        procedure_code = procedure_code.strip().upper()

        result = MappingResult(
            source_code=procedure_code,
            source_type="procedure",
        )

        # Validate procedure code
        px_system = CodeSystem.ACHI if country.upper() == "AU" else CodeSystem.CPT
        px_validation = self.code_validator.validate_code(procedure_code, px_system)

        if not px_validation.format_valid:
            result.is_valid_combination = False
            result.confidence_score = 0.0
            result.warnings.append(f"Invalid procedure code format: {procedure_code}")
            return result

        # Reverse lookup - find diagnoses that map to this procedure
        for dx_code, mapping_data in self.CLINICAL_MAPPINGS.items():
            if procedure_code in mapping_data["procedures"]:
                mapping = CodeMapping(
                    diagnosis_code=dx_code,
                    procedure_code=procedure_code,
                    strength=mapping_data["strength"],
                )
                result.mappings.append(mapping)

        return result

    def validate_claim_codes(
        self,
        diagnosis_codes: list[str],
        procedure_codes: list[str],
        country: str = "US",
    ) -> dict:
        """
        Validate all diagnosis-procedure combinations for a claim.

        Args:
            diagnosis_codes: List of diagnosis codes
            procedure_codes: List of procedure codes
            country: Country code (US or AU)

        Returns:
            Dictionary with validation results for all combinations
        """
        results = {
            "is_valid": True,
            "overall_confidence": 1.0,
            "combinations": [],
            "warnings": [],
            "suggestions": [],
        }

        # Primary diagnosis should support primary procedure
        if diagnosis_codes and procedure_codes:
            primary_result = self.validate_combination(
                diagnosis_codes[0],
                procedure_codes[0],
                country,
            )

            if not primary_result.is_valid_combination:
                results["is_valid"] = False
                results["warnings"].append(
                    f"Primary diagnosis {diagnosis_codes[0]} does not support "
                    f"primary procedure {procedure_codes[0]}"
                )

            # Check all combinations
            confidence_scores = []
            for dx in diagnosis_codes:
                for px in procedure_codes:
                    combo_result = self.validate_combination(dx, px, country)
                    results["combinations"].append({
                        "diagnosis": dx,
                        "procedure": px,
                        "is_valid": combo_result.is_valid_combination,
                        "confidence": combo_result.confidence_score,
                        "strength": combo_result.mappings[0].strength.value if combo_result.mappings else "none",
                    })
                    confidence_scores.append(combo_result.confidence_score)
                    results["warnings"].extend(combo_result.warnings)
                    results["suggestions"].extend(combo_result.suggestions)

            # Overall confidence is minimum of all combinations
            if confidence_scores:
                results["overall_confidence"] = min(confidence_scores)

        return results


# =============================================================================
# Factory Functions
# =============================================================================


_code_mapper: Optional[DiagnosisProcedureMapper] = None


def get_code_mapper(
    code_validator: Optional[MedicalCodeValidator] = None,
) -> DiagnosisProcedureMapper:
    """Get singleton DiagnosisProcedureMapper instance."""
    global _code_mapper
    if _code_mapper is None:
        _code_mapper = DiagnosisProcedureMapper(code_validator)
    return _code_mapper


def create_code_mapper(
    code_validator: Optional[MedicalCodeValidator] = None,
) -> DiagnosisProcedureMapper:
    """Create a new DiagnosisProcedureMapper instance."""
    return DiagnosisProcedureMapper(code_validator)
