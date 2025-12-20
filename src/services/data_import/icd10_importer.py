"""
ICD-10-CM/PCS Code Importer.

Source: Design Document 04_validation_engine_comprehensive_design.md
CMS Data Source: https://www.cms.gov/medicare/coding-billing/icd-10-codes
Verified: 2025-12-19

Imports ICD-10-CM (diagnosis) and ICD-10-PCS (procedure) codes from CMS
data files into Typesense for high-speed search.
"""

import logging
import re
from pathlib import Path
from typing import Optional

from src.gateways.search_gateway import SearchCollection, SearchGateway
from src.services.data_import.base_importer import BaseImporter

logger = logging.getLogger(__name__)


# ICD-10-CM chapter mapping
ICD10_CHAPTERS = {
    "A": "Certain infectious and parasitic diseases (A00-B99)",
    "B": "Certain infectious and parasitic diseases (A00-B99)",
    "C": "Neoplasms (C00-D49)",
    "D0": "Neoplasms (C00-D49)",
    "D1": "Neoplasms (C00-D49)",
    "D2": "Neoplasms (C00-D49)",
    "D3": "Neoplasms (C00-D49)",
    "D4": "Neoplasms (C00-D49)",
    "D5": "Diseases of the blood (D50-D89)",
    "D6": "Diseases of the blood (D50-D89)",
    "D7": "Diseases of the blood (D50-D89)",
    "D8": "Diseases of the blood (D50-D89)",
    "E": "Endocrine, nutritional and metabolic diseases (E00-E89)",
    "F": "Mental, behavioral and neurodevelopmental disorders (F01-F99)",
    "G": "Diseases of the nervous system (G00-G99)",
    "H0": "Diseases of the eye (H00-H59)",
    "H1": "Diseases of the eye (H00-H59)",
    "H2": "Diseases of the eye (H00-H59)",
    "H3": "Diseases of the eye (H00-H59)",
    "H4": "Diseases of the eye (H00-H59)",
    "H5": "Diseases of the eye (H00-H59)",
    "H6": "Diseases of the ear (H60-H95)",
    "H7": "Diseases of the ear (H60-H95)",
    "H8": "Diseases of the ear (H60-H95)",
    "H9": "Diseases of the ear (H60-H95)",
    "I": "Diseases of the circulatory system (I00-I99)",
    "J": "Diseases of the respiratory system (J00-J99)",
    "K": "Diseases of the digestive system (K00-K95)",
    "L": "Diseases of the skin (L00-L99)",
    "M": "Diseases of the musculoskeletal system (M00-M99)",
    "N": "Diseases of the genitourinary system (N00-N99)",
    "O": "Pregnancy, childbirth and the puerperium (O00-O9A)",
    "P": "Certain conditions originating in the perinatal period (P00-P96)",
    "Q": "Congenital malformations (Q00-Q99)",
    "R": "Symptoms, signs and abnormal clinical and laboratory findings (R00-R99)",
    "S": "Injury, poisoning and external causes (S00-T88)",
    "T": "Injury, poisoning and external causes (S00-T88)",
    "V": "External causes of morbidity (V00-Y99)",
    "W": "External causes of morbidity (V00-Y99)",
    "X": "External causes of morbidity (V00-Y99)",
    "Y": "External causes of morbidity (V00-Y99)",
    "Z": "Factors influencing health status (Z00-Z99)",
}

# Gender-specific ICD-10 codes (simplified list - production would need full list)
MALE_ONLY_CODES = frozenset([
    "C61", "C62", "N40", "N41", "N42", "N43", "N44", "N45", "N46",
    "N47", "N48", "N49", "N50", "N51",
])

FEMALE_ONLY_CODES = frozenset([
    "C51", "C52", "C53", "C54", "C55", "C56", "C57", "C58",
    "N70", "N71", "N72", "N73", "N74", "N75", "N76", "N77",
    "N80", "N81", "N82", "N83", "N84", "N85", "N86", "N87",
    "N88", "N89", "N90", "N91", "N92", "N93", "N94", "N95",
    "O00", "O01", "O02", "O03", "O04", "O05", "O06", "O07",
    "O08", "O09", "O10", "O11", "O12", "O13", "O14", "O15",
])

# Pediatric codes (age < 18)
PEDIATRIC_CODES = frozenset([
    "P00", "P01", "P02", "P03", "P04", "P05", "P07", "P08",
    "P09", "P10", "P11", "P12", "P13", "P14", "P15", "P19",
    "P20", "P21", "P22", "P23", "P24", "P25", "P26", "P27",
    "P28", "P29", "P35", "P36", "P37", "P38", "P39", "P50",
    "Z00.12",  # Encounter for routine child health examination
])


class ICD10Importer(BaseImporter):
    """
    Importer for ICD-10-CM/PCS codes from CMS data files.

    Supports both the standard CMS format and simplified CSV format.
    """

    @property
    def collection(self) -> SearchCollection:
        return SearchCollection.ICD10_CODES

    @property
    def source_description(self) -> str:
        return "CMS ICD-10-CM/PCS Code Files (https://www.cms.gov/medicare/coding-billing/icd-10-codes)"

    def get_column_mapping(self) -> dict[str, str]:
        """Map CMS column names to internal names."""
        return {
            "CODE": "code",
            "LONG DESCRIPTION": "description",
            "SHORT DESCRIPTION": "short_description",
            "DIAGNOSIS CODE": "code",
            "PROCEDURE CODE": "code",
            "DIAGNOSIS DESCRIPTION": "description",
            "PROCEDURE DESCRIPTION": "description",
        }

    def validate_row(self, row: dict) -> bool:
        """Validate ICD-10 code row."""
        code = row.get("code", "").strip()
        if not code:
            return False

        # ICD-10 codes are alphanumeric, 3-7 characters
        if not re.match(r"^[A-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$", code, re.IGNORECASE):
            # Also allow codes without decimal for header codes
            if not re.match(r"^[A-Z][0-9][0-9A-Z]{0,4}$", code, re.IGNORECASE):
                return False

        return True

    def parse_row(self, row: dict) -> Optional[dict]:
        """Parse ICD-10 row into Typesense document."""
        code = row.get("code", "").strip().upper()
        description = row.get("description", "").strip()
        short_desc = row.get("short_description", "").strip()

        if not code or not description:
            return None

        # Normalize code format (add decimal if needed)
        if len(code) > 3 and "." not in code:
            code = f"{code[:3]}.{code[3:]}"

        # Determine chapter from first characters
        chapter = self._get_chapter(code)

        # Determine category range
        category = self._get_category(code)

        # Check if billable (codes with 4+ characters after decimal are typically billable)
        is_billable = "." in code and len(code.split(".")[1]) >= 1
        is_header = len(code) <= 3 or (len(code) == 4 and "." not in code)

        # Check gender restrictions
        gender = self._get_gender_restriction(code)

        # Check age restrictions
        min_age, max_age = self._get_age_restrictions(code)

        return {
            "id": code.replace(".", "_"),  # Typesense ID
            "code": code,
            "description": description,
            "short_description": short_desc or description[:50],
            "category": category,
            "chapter": chapter,
            "is_billable": is_billable,
            "is_header": is_header,
            "min_age": min_age,
            "max_age": max_age,
            "gender_restriction": gender,
        }

    def _get_chapter(self, code: str) -> str:
        """Get chapter name from ICD-10 code."""
        # Try two-character lookup first, then one-character
        prefix2 = code[:2].upper() if len(code) >= 2 else ""
        prefix1 = code[0].upper() if code else ""

        return ICD10_CHAPTERS.get(prefix2) or ICD10_CHAPTERS.get(prefix1, "Unknown")

    def _get_category(self, code: str) -> str:
        """Get category range from ICD-10 code."""
        prefix = code[0].upper() if code else ""

        category_ranges = {
            "A": "A00-B99", "B": "A00-B99",
            "C": "C00-D49", "D": "D50-D89",
            "E": "E00-E89", "F": "F01-F99",
            "G": "G00-G99", "H": "H00-H95",
            "I": "I00-I99", "J": "J00-J99",
            "K": "K00-K95", "L": "L00-L99",
            "M": "M00-M99", "N": "N00-N99",
            "O": "O00-O9A", "P": "P00-P96",
            "Q": "Q00-Q99", "R": "R00-R99",
            "S": "S00-T88", "T": "S00-T88",
            "V": "V00-Y99", "W": "V00-Y99",
            "X": "V00-Y99", "Y": "V00-Y99",
            "Z": "Z00-Z99",
        }

        return category_ranges.get(prefix, "Unknown")

    def _get_gender_restriction(self, code: str) -> str:
        """Determine gender restriction for code."""
        # Check first 3 characters (category)
        prefix3 = code[:3].upper().replace(".", "") if code else ""

        if prefix3 in MALE_ONLY_CODES:
            return "M"
        if prefix3 in FEMALE_ONLY_CODES:
            return "F"
        # Pregnancy codes (O chapter) are female only
        if code.startswith("O"):
            return "F"

        return "N"  # No restriction

    def _get_age_restrictions(self, code: str) -> tuple[Optional[int], Optional[int]]:
        """Determine age restrictions for code."""
        # Check for perinatal codes
        prefix3 = code[:3].upper().replace(".", "") if code else ""

        if prefix3 in PEDIATRIC_CODES or code in PEDIATRIC_CODES:
            return (0, 0)  # Newborn only

        # P codes are generally for newborns/infants
        if code.startswith("P"):
            return (0, 1)

        # Some Z codes have pediatric restrictions
        if code.startswith("Z00.12"):
            return (0, 17)

        return (None, None)

    async def import_from_cms_file(
        self,
        codes_file: Path,
        descriptions_file: Optional[Path] = None,
    ) -> dict[str, int]:
        """
        Import ICD-10 codes from CMS format files.

        CMS provides codes in either:
        1. Single file with codes and descriptions
        2. Separate order file and descriptions file

        Args:
            codes_file: Path to main codes file (or order file)
            descriptions_file: Optional path to descriptions file

        Returns:
            Import statistics
        """
        # Detect file format based on content
        with open(codes_file, "r", encoding="utf-8") as f:
            first_line = f.readline()

        # Check if it's a pipe-delimited CMS file or CSV
        if "|" in first_line:
            return await self._import_pipe_delimited(codes_file)
        elif "\t" in first_line:
            return await self._import_tab_delimited(codes_file)
        else:
            return await self.import_from_file(codes_file)

    async def _import_pipe_delimited(self, file_path: Path) -> dict[str, int]:
        """Import from CMS pipe-delimited format."""
        return await self.import_from_file(file_path, delimiter="|")

    async def _import_tab_delimited(self, file_path: Path) -> dict[str, int]:
        """Import from tab-delimited format."""
        return await self.import_from_file(file_path, delimiter="\t")

    async def generate_sample_data(self, count: int = 100) -> list[dict]:
        """
        Generate sample ICD-10 codes for testing.

        Args:
            count: Number of sample codes to generate

        Returns:
            List of sample ICD-10 code documents
        """
        sample_codes = [
            ("E11.9", "Type 2 diabetes mellitus without complications"),
            ("J06.9", "Acute upper respiratory infection, unspecified"),
            ("I10", "Essential (primary) hypertension"),
            ("M54.5", "Low back pain"),
            ("K21.0", "Gastro-esophageal reflux disease with esophagitis"),
            ("J18.9", "Pneumonia, unspecified organism"),
            ("N39.0", "Urinary tract infection, site not specified"),
            ("F41.1", "Generalized anxiety disorder"),
            ("G43.909", "Migraine, unspecified, not intractable, without status migrainosus"),
            ("R10.9", "Unspecified abdominal pain"),
            ("J02.9", "Acute pharyngitis, unspecified"),
            ("J00", "Acute nasopharyngitis [common cold]"),
            ("M79.3", "Panniculitis, unspecified"),
            ("R05", "Cough"),
            ("J45.909", "Unspecified asthma, uncomplicated"),
            ("E78.5", "Hyperlipidemia, unspecified"),
            ("Z23", "Encounter for immunization"),
            ("Z00.00", "Encounter for general adult medical examination without abnormal findings"),
            ("K08.9", "Disorder of teeth and supporting structures, unspecified"),
            ("H10.9", "Unspecified conjunctivitis"),
        ]

        documents = []
        for i, (code, description) in enumerate(sample_codes[:count]):
            doc = self.parse_row({
                "code": code,
                "description": description,
                "short_description": description[:50],
            })
            if doc:
                documents.append(doc)

        return documents
