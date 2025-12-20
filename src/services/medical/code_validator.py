"""
Medical Code Validation Service.
Source: Design Document Section 4.1 - Medical Validation
Verified: 2025-12-18

Validates ICD-10, CPT, and Australian medical codes against reference data.
"""

import json
import re
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class CodeSystem(str, Enum):
    """Supported medical code systems."""

    ICD10_CM = "icd10_cm"  # US Clinical Modification
    ICD10_AM = "icd10_am"  # Australian Modification
    CPT = "cpt"  # Current Procedural Terminology (US)
    ACHI = "achi"  # Australian Classification of Health Interventions
    HCPCS = "hcpcs"  # Healthcare Common Procedure Coding System


class CodeValidationResult(BaseModel):
    """Result of medical code validation."""

    code: str
    code_system: CodeSystem
    is_valid: bool
    exists_in_database: bool
    format_valid: bool
    description: Optional[str] = None
    category: Optional[str] = None
    chapter: Optional[str] = None
    error_message: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class MedicalCodeValidator:
    """
    Validates medical codes against reference databases.

    Supports:
    - ICD-10-CM (US diagnosis codes)
    - ICD-10-AM (Australian diagnosis codes)
    - CPT (US procedure codes)
    - ACHI (Australian procedure codes)
    - HCPCS (Healthcare Common Procedure Coding System)
    """

    # Code format patterns
    CODE_PATTERNS = {
        CodeSystem.ICD10_CM: r"^[A-Z]\d{2}(\.\d{1,4})?$",
        CodeSystem.ICD10_AM: r"^[A-Z]\d{2}(\.\d{1,4})?$",
        CodeSystem.CPT: r"^\d{5}$",
        CodeSystem.ACHI: r"^\d{5}-\d{2}$|^\d{3}$",
        CodeSystem.HCPCS: r"^[A-Z]\d{4}$",
    }

    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize MedicalCodeValidator.

        Args:
            data_path: Path to medical code data files. Defaults to src/data.
        """
        if data_path is None:
            # Default to src/data relative to this file
            data_path = Path(__file__).parent.parent.parent / "data"

        self.data_path = data_path
        self._code_databases: dict[CodeSystem, dict] = {}
        self._load_databases()

    def _load_databases(self) -> None:
        """Load code databases from JSON files."""
        database_files = {
            CodeSystem.ICD10_CM: "icd10_cm.json",
            CodeSystem.ICD10_AM: "icd10_am.json",
            CodeSystem.CPT: "cpt_codes.json",
            CodeSystem.ACHI: "achi_codes.json",
        }

        for code_system, filename in database_files.items():
            file_path = self.data_path / filename
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self._code_databases[code_system] = data.get("codes", {})
                except (json.JSONDecodeError, IOError):
                    self._code_databases[code_system] = {}
            else:
                self._code_databases[code_system] = {}

    def validate_code(
        self,
        code: str,
        code_system: CodeSystem,
    ) -> CodeValidationResult:
        """
        Validate a single medical code.

        Args:
            code: The medical code to validate
            code_system: The code system (ICD-10-CM, CPT, etc.)

        Returns:
            CodeValidationResult with validation details
        """
        code = code.strip().upper()

        # Check format validity
        pattern = self.CODE_PATTERNS.get(code_system)
        format_valid = bool(pattern and re.match(pattern, code))

        # Check if code exists in database
        database = self._code_databases.get(code_system, {})
        code_data = database.get(code)
        exists_in_database = code_data is not None

        # Build result
        result = CodeValidationResult(
            code=code,
            code_system=code_system,
            is_valid=format_valid and exists_in_database,
            exists_in_database=exists_in_database,
            format_valid=format_valid,
        )

        if code_data:
            result.description = code_data.get("description")
            result.category = code_data.get("category")
            result.chapter = code_data.get("chapter")
            result.metadata = {
                k: v
                for k, v in code_data.items()
                if k not in ["description", "category", "chapter"]
            }
        else:
            if not format_valid:
                result.error_message = f"Invalid {code_system.value} code format"
            elif not exists_in_database:
                result.error_message = f"Code {code} not found in {code_system.value} database"
                # If format is valid but not in DB, it might still be a valid code
                # just not in our subset
                result.warnings.append(
                    "Code format is valid but not in reference database. "
                    "May be valid but not in subset."
                )

        return result

    def validate_codes(
        self,
        codes: list[str],
        code_system: CodeSystem,
    ) -> list[CodeValidationResult]:
        """
        Validate multiple medical codes.

        Args:
            codes: List of medical codes to validate
            code_system: The code system (ICD-10-CM, CPT, etc.)

        Returns:
            List of CodeValidationResult for each code
        """
        return [self.validate_code(code, code_system) for code in codes]

    def validate_diagnosis_codes(
        self,
        codes: list[str],
        country: str = "US",
    ) -> list[CodeValidationResult]:
        """
        Validate diagnosis codes (ICD-10-CM or ICD-10-AM).

        Args:
            codes: List of diagnosis codes
            country: Country code (US or AU)

        Returns:
            List of CodeValidationResult
        """
        code_system = CodeSystem.ICD10_AM if country.upper() == "AU" else CodeSystem.ICD10_CM
        return self.validate_codes(codes, code_system)

    def validate_procedure_codes(
        self,
        codes: list[str],
        country: str = "US",
    ) -> list[CodeValidationResult]:
        """
        Validate procedure codes (CPT or ACHI).

        Args:
            codes: List of procedure codes
            country: Country code (US or AU)

        Returns:
            List of CodeValidationResult
        """
        code_system = CodeSystem.ACHI if country.upper() == "AU" else CodeSystem.CPT
        return self.validate_codes(codes, code_system)

    def get_code_info(
        self,
        code: str,
        code_system: CodeSystem,
    ) -> Optional[dict]:
        """
        Get full information about a code.

        Args:
            code: The medical code
            code_system: The code system

        Returns:
            Code information dictionary or None
        """
        code = code.strip().upper()
        database = self._code_databases.get(code_system, {})
        return database.get(code)

    def search_codes(
        self,
        query: str,
        code_system: CodeSystem,
        limit: int = 10,
    ) -> list[dict]:
        """
        Search codes by description.

        Args:
            query: Search query
            code_system: The code system to search
            limit: Maximum results to return

        Returns:
            List of matching codes with details
        """
        query = query.lower()
        database = self._code_databases.get(code_system, {})
        results = []

        for code, data in database.items():
            description = data.get("description", "").lower()
            if query in description or query in code.lower():
                results.append({"code": code, **data})
                if len(results) >= limit:
                    break

        return results

    def is_valid_format(self, code: str, code_system: CodeSystem) -> bool:
        """
        Check if a code has valid format for the given system.

        Args:
            code: The medical code
            code_system: The code system

        Returns:
            True if format is valid
        """
        pattern = self.CODE_PATTERNS.get(code_system)
        if not pattern:
            return False
        return bool(re.match(pattern, code.strip().upper()))

    def get_common_procedures(
        self,
        diagnosis_code: str,
        country: str = "US",
    ) -> list[str]:
        """
        Get common procedures associated with a diagnosis code.

        Args:
            diagnosis_code: The ICD-10 diagnosis code
            country: Country code (US or AU)

        Returns:
            List of commonly associated procedure codes
        """
        code_system = CodeSystem.ICD10_AM if country.upper() == "AU" else CodeSystem.ICD10_CM
        code_data = self.get_code_info(diagnosis_code, code_system)

        if code_data:
            return code_data.get("common_procedures", [])
        return []

    def requires_prior_auth(
        self,
        procedure_code: str,
        country: str = "US",
    ) -> bool:
        """
        Check if a procedure requires prior authorization.

        Args:
            procedure_code: The procedure code
            country: Country code (US or AU)

        Returns:
            True if prior authorization is typically required
        """
        code_system = CodeSystem.ACHI if country.upper() == "AU" else CodeSystem.CPT
        code_data = self.get_code_info(procedure_code, code_system)

        if code_data:
            return code_data.get("requires_prior_auth", False)
        return False

    def get_gender_specific(
        self,
        code: str,
        code_system: CodeSystem,
    ) -> Optional[str]:
        """
        Get gender specificity for a code.

        Args:
            code: The medical code
            code_system: The code system

        Returns:
            Gender code (M, F) or None if not gender-specific
        """
        code_data = self.get_code_info(code, code_system)
        if code_data:
            return code_data.get("gender_specific")
        return None

    def get_age_restrictions(
        self,
        code: str,
        code_system: CodeSystem,
    ) -> Optional[tuple[int, int]]:
        """
        Get age restrictions for a code.

        Args:
            code: The medical code
            code_system: The code system

        Returns:
            Tuple of (min_age, max_age) or None
        """
        code_data = self.get_code_info(code, code_system)
        if code_data:
            age_range = code_data.get("age_range")
            if age_range:
                return tuple(age_range)
            age_min = code_data.get("age_minimum")
            if age_min is not None:
                return (age_min, 999)
        return None


# =============================================================================
# Factory Functions
# =============================================================================


_code_validator: Optional[MedicalCodeValidator] = None


def get_code_validator(data_path: Optional[Path] = None) -> MedicalCodeValidator:
    """Get singleton MedicalCodeValidator instance."""
    global _code_validator
    if _code_validator is None:
        _code_validator = MedicalCodeValidator(data_path)
    return _code_validator


def create_code_validator(data_path: Optional[Path] = None) -> MedicalCodeValidator:
    """Create a new MedicalCodeValidator instance."""
    return MedicalCodeValidator(data_path)
