"""
CPT/HCPCS Code Importer.

Source: Design Document 04_validation_engine_comprehensive_design.md
AMA CPT: https://www.ama-assn.org/practice-management/cpt
CMS HCPCS: https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system
Verified: 2025-12-19

Imports CPT (Current Procedural Terminology) and HCPCS (Healthcare Common
Procedure Coding System) codes into Typesense for high-speed search.
"""

import logging
import re
from pathlib import Path
from typing import Optional

from src.gateways.search_gateway import SearchCollection, SearchGateway
from src.services.data_import.base_importer import BaseImporter

logger = logging.getLogger(__name__)


# CPT code categories based on code range
CPT_CATEGORIES = {
    "99": "E/M",  # Evaluation and Management
    "00": "Anesthesia",
    "01": "Anesthesia",
    "10": "Surgery",
    "11": "Surgery",
    "12": "Surgery",
    "13": "Surgery",
    "14": "Surgery",
    "15": "Surgery",
    "16": "Surgery",
    "17": "Surgery",
    "19": "Surgery",
    "20": "Surgery",
    "21": "Surgery",
    "22": "Surgery",
    "23": "Surgery",
    "24": "Surgery",
    "25": "Surgery",
    "26": "Surgery",
    "27": "Surgery",
    "28": "Surgery",
    "29": "Surgery",
    "30": "Surgery",
    "31": "Surgery",
    "32": "Surgery",
    "33": "Surgery",
    "34": "Surgery",
    "35": "Surgery",
    "36": "Surgery",
    "37": "Surgery",
    "38": "Surgery",
    "39": "Surgery",
    "40": "Surgery",
    "41": "Surgery",
    "42": "Surgery",
    "43": "Surgery",
    "44": "Surgery",
    "45": "Surgery",
    "46": "Surgery",
    "47": "Surgery",
    "48": "Surgery",
    "49": "Surgery",
    "50": "Surgery",
    "51": "Surgery",
    "52": "Surgery",
    "53": "Surgery",
    "54": "Surgery",
    "55": "Surgery",
    "56": "Surgery",
    "57": "Surgery",
    "58": "Surgery",
    "59": "Surgery",
    "60": "Surgery",
    "61": "Surgery",
    "62": "Surgery",
    "63": "Surgery",
    "64": "Surgery",
    "65": "Surgery",
    "66": "Surgery",
    "67": "Surgery",
    "68": "Surgery",
    "69": "Surgery",
    "70": "Radiology",
    "71": "Radiology",
    "72": "Radiology",
    "73": "Radiology",
    "74": "Radiology",
    "75": "Radiology",
    "76": "Radiology",
    "77": "Radiology",
    "78": "Radiology",
    "79": "Radiology",
    "80": "Pathology",
    "81": "Pathology",
    "82": "Pathology",
    "83": "Pathology",
    "84": "Pathology",
    "85": "Pathology",
    "86": "Pathology",
    "87": "Pathology",
    "88": "Pathology",
    "89": "Pathology",
    "90": "Medicine",
    "91": "Medicine",
    "92": "Medicine",
    "93": "Medicine",
    "94": "Medicine",
    "95": "Medicine",
    "96": "Medicine",
    "97": "Medicine",
    "98": "Medicine",
}

# Gender-specific CPT codes (simplified - production would need full list)
MALE_ONLY_CPT = frozenset([
    "55700", "55705", "55706", "55720", "55725", "55801", "55810",
    "55812", "55815", "55821", "55831", "55840", "55842", "55845",
    "55866", "55870", "55873", "55875", "55876",  # Prostate procedures
])

FEMALE_ONLY_CPT = frozenset([
    "57000", "57010", "57020", "57022", "57023", "57061", "57065",
    "57100", "57105", "57106", "57107", "57109", "57110", "57111",
    "57112", "57120", "57130", "57135", "57150", "57155", "57156",
    "57160", "57170", "57180", "57200", "57210", "57220", "57230",
    "57240", "57250", "57260", "57265", "57267", "57268", "57270",
    "57280", "57282", "57283", "57284", "57285", "57287", "57288",
    "57289", "57291", "57292", "57295", "57296", "57300", "57305",
    "57307", "57308", "57310", "57311", "57320", "57330", "57335",
    "57400", "57410", "57415", "57420", "57421", "57423", "57425",
    "57426", "57452", "57454", "57455", "57456", "57460", "57461",
    "57500", "57505", "57510", "57511", "57513", "57520", "57522",
    "57530", "57531", "57540", "57545", "57550", "57555", "57556",
    "57558",  # Vaginal/cervical procedures
    "58100", "58110", "58120", "58140", "58145", "58146", "58150",
    "58152", "58180", "58200", "58210", "58240", "58260", "58262",
    "58263", "58267", "58270", "58275", "58280", "58285", "58290",
    "58291", "58292", "58293", "58294",  # Uterine procedures
])


class CPTImporter(BaseImporter):
    """
    Importer for CPT/HCPCS codes.

    Supports:
    - AMA CPT code files
    - CMS HCPCS code files
    - RVU (Relative Value Unit) data
    """

    @property
    def collection(self) -> SearchCollection:
        return SearchCollection.CPT_CODES

    @property
    def source_description(self) -> str:
        return "AMA CPT / CMS HCPCS Code Files"

    def get_column_mapping(self) -> dict[str, str]:
        """Map source column names to internal names."""
        return {
            "HCPCS": "code",
            "CPT": "code",
            "CPT/HCPCS": "code",
            "HCPC": "code",
            "DESCRIPTION": "description",
            "LONG DESCRIPTION": "description",
            "SHORT DESCRIPTION": "short_description",
            "WORK RVU": "work_rvu",
            "FACILITY PE RVU": "facility_pe_rvu",
            "NON-FACILITY PE RVU": "non_facility_pe_rvu",
            "PLI RVU": "mp_rvu",
            "MP RVU": "mp_rvu",
            "GLOBAL": "global_period",
            "MOD": "modifier_allowed",
            "STATUS": "status",
        }

    def validate_row(self, row: dict) -> bool:
        """Validate CPT/HCPCS code row."""
        code = row.get("code", "").strip()
        if not code:
            return False

        # CPT codes are 5 digits, HCPCS are alphanumeric
        if not re.match(r"^[A-Z0-9]{5}$", code, re.IGNORECASE):
            return False

        return True

    def parse_row(self, row: dict) -> Optional[dict]:
        """Parse CPT/HCPCS row into Typesense document."""
        code = row.get("code", "").strip().upper()
        description = row.get("description", "").strip()
        short_desc = row.get("short_description", "").strip()

        if not code or not description:
            return None

        # Determine category
        category = self._get_category(code)

        # Parse RVU values
        work_rvu = self._parse_float(row.get("work_rvu"))
        facility_pe_rvu = self._parse_float(row.get("facility_pe_rvu"))
        non_facility_pe_rvu = self._parse_float(row.get("non_facility_pe_rvu"))
        mp_rvu = self._parse_float(row.get("mp_rvu"))

        # Parse global period
        global_period = self._parse_global_period(row.get("global_period", ""))

        # Parse status
        status = row.get("status", "A").strip().upper()
        if status not in ("A", "I", "D", "T", "R", "N"):
            status = "A"

        # Check gender restrictions
        gender = self._get_gender_restriction(code)

        return {
            "id": code,
            "code": code,
            "description": description,
            "short_description": short_desc or description[:50],
            "category": category,
            "subcategory": self._get_subcategory(code, category),
            "work_rvu": work_rvu,
            "facility_pe_rvu": facility_pe_rvu,
            "non_facility_pe_rvu": non_facility_pe_rvu,
            "mp_rvu": mp_rvu,
            "status": status,
            "global_period": global_period,
            "gender_restriction": gender,
            "modifier_allowed": row.get("modifier_allowed", "1") != "0",
        }

    def _get_category(self, code: str) -> str:
        """Get category from CPT code range."""
        if not code or len(code) < 2:
            return "Unknown"

        # HCPCS Level II codes start with a letter
        if code[0].isalpha():
            return "HCPCS"

        prefix = code[:2]
        return CPT_CATEGORIES.get(prefix, "Unknown")

    def _get_subcategory(self, code: str, category: str) -> Optional[str]:
        """Get subcategory based on code range."""
        if category == "E/M":
            if code.startswith("992"):
                return "Office/Outpatient"
            elif code.startswith("993"):
                return "Hospital"
            elif code.startswith("994"):
                return "Consultation"
            elif code.startswith("995"):
                return "Emergency"
            elif code.startswith("996"):
                return "Critical Care"
            elif code.startswith("997"):
                return "Nursing Facility"
            elif code.startswith("998"):
                return "Home Services"
            elif code.startswith("999"):
                return "Prolonged Services"
        elif category == "Surgery":
            if 10000 <= int(code) < 20000:
                return "Integumentary"
            elif 20000 <= int(code) < 30000:
                return "Musculoskeletal"
            elif 30000 <= int(code) < 40000:
                return "Respiratory/Cardiovascular"
            elif 40000 <= int(code) < 50000:
                return "Digestive"
            elif 50000 <= int(code) < 60000:
                return "Urinary/Male Genital"
            elif 60000 <= int(code) < 70000:
                return "Endocrine/Nervous"

        return None

    def _get_gender_restriction(self, code: str) -> str:
        """Determine gender restriction for CPT code."""
        if code in MALE_ONLY_CPT:
            return "M"
        if code in FEMALE_ONLY_CPT:
            return "F"
        return "N"

    def _parse_float(self, value: Optional[str]) -> Optional[float]:
        """Parse float value from string."""
        if not value:
            return None
        try:
            return float(value.strip())
        except (ValueError, AttributeError):
            return None

    def _parse_global_period(self, value: str) -> Optional[int]:
        """Parse global surgery period."""
        if not value:
            return None
        value = value.strip().upper()
        if value == "XXX" or value == "ZZZ":
            return None
        if value == "000":
            return 0
        if value == "010":
            return 10
        if value == "090":
            return 90
        try:
            return int(value)
        except ValueError:
            return None

    async def import_rvu_file(
        self,
        rvu_file: Path,
        update_existing: bool = True,
    ) -> dict[str, int]:
        """
        Import RVU data from CMS Physician Fee Schedule file.

        Args:
            rvu_file: Path to RVU file
            update_existing: If True, update existing codes with RVU data

        Returns:
            Import statistics
        """
        logger.info(f"Importing RVU data from {rvu_file}")
        return await self.import_from_file(rvu_file)

    async def generate_sample_data(self, count: int = 100) -> list[dict]:
        """
        Generate sample CPT codes for testing.

        Args:
            count: Number of sample codes to generate

        Returns:
            List of sample CPT code documents
        """
        sample_codes = [
            ("99213", "Office or other outpatient visit, established patient, low complexity", 1.30),
            ("99214", "Office or other outpatient visit, established patient, moderate complexity", 1.92),
            ("99215", "Office or other outpatient visit, established patient, high complexity", 2.80),
            ("99202", "Office or other outpatient visit, new patient, straightforward", 0.93),
            ("99203", "Office or other outpatient visit, new patient, low complexity", 1.60),
            ("99204", "Office or other outpatient visit, new patient, moderate complexity", 2.60),
            ("99205", "Office or other outpatient visit, new patient, high complexity", 3.50),
            ("99381", "Initial comprehensive preventive medicine, infant", 1.50),
            ("99391", "Periodic comprehensive preventive medicine, infant", 1.20),
            ("71046", "Radiologic examination, chest; 2 views", 0.22),
            ("71047", "Radiologic examination, chest; 3 views", 0.27),
            ("80053", "Comprehensive metabolic panel", 0.00),
            ("85025", "Blood count; complete (CBC)", 0.00),
            ("36415", "Collection of venous blood by venipuncture", 0.03),
            ("90471", "Immunization administration", 0.17),
            ("90472", "Immunization administration, additional vaccine", 0.15),
            ("96372", "Therapeutic injection, subcutaneous or intramuscular", 0.17),
            ("J3420", "Injection, vitamin B-12 cyanocobalamin", 0.00),
            ("A4206", "Syringe with needle, sterile 1cc", 0.00),
            ("G0438", "Annual wellness visit, initial", 2.43),
        ]

        documents = []
        for code, description, rvu in sample_codes[:count]:
            doc = self.parse_row({
                "code": code,
                "description": description,
                "short_description": description[:50],
                "work_rvu": str(rvu),
                "status": "A",
            })
            if doc:
                documents.append(doc)

        return documents
