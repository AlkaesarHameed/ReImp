"""
NCCI (National Correct Coding Initiative) Edit Importer.

Source: Design Document 04_validation_engine_comprehensive_design.md
CMS NCCI: https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci
Verified: 2025-12-19

Imports NCCI Procedure-to-Procedure (PTP) edits that define code pairs
that should not be billed together.
"""

import logging
from datetime import date
from pathlib import Path
from typing import Optional

from src.gateways.search_gateway import SearchCollection, SearchGateway
from src.services.data_import.base_importer import BaseImporter

logger = logging.getLogger(__name__)


class NCCIImporter(BaseImporter):
    """
    Importer for NCCI PTP (Procedure-to-Procedure) edits.

    NCCI edits identify pairs of CPT/HCPCS codes that should not be
    billed together because:
    - One procedure is a component of the other
    - The procedures are mutually exclusive
    - The procedures represent standards of care
    """

    @property
    def collection(self) -> SearchCollection:
        return SearchCollection.NCCI_EDITS

    @property
    def source_description(self) -> str:
        return "CMS NCCI PTP Edits (https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci)"

    def get_column_mapping(self) -> dict[str, str]:
        """Map CMS NCCI file column names to internal names."""
        return {
            "COLUMN_1": "column1_code",
            "COLUMN_2": "column2_code",
            "Column 1": "column1_code",
            "Column 2": "column2_code",
            "Column1": "column1_code",
            "Column2": "column2_code",
            "HCPCS_CODE_1": "column1_code",
            "HCPCS_CODE_2": "column2_code",
            "MODIFIER": "modifier_indicator",
            "Modifier": "modifier_indicator",
            "MOD": "modifier_indicator",
            "EFFECTIVE_DATE": "effective_date",
            "Effective Date": "effective_date",
            "EFF_DATE": "effective_date",
            "DELETION_DATE": "deletion_date",
            "Deletion Date": "deletion_date",
            "DEL_DATE": "deletion_date",
            "PTP_EDIT_RATIONALE": "rationale",
            "Rationale": "rationale",
        }

    def validate_row(self, row: dict) -> bool:
        """Validate NCCI edit row."""
        col1 = row.get("column1_code", "").strip()
        col2 = row.get("column2_code", "").strip()

        if not col1 or not col2:
            return False

        # Both codes should be valid CPT/HCPCS format
        if len(col1) != 5 or len(col2) != 5:
            return False

        return True

    def parse_row(self, row: dict) -> Optional[dict]:
        """Parse NCCI edit row into Typesense document."""
        col1 = row.get("column1_code", "").strip().upper()
        col2 = row.get("column2_code", "").strip().upper()

        if not col1 or not col2:
            return None

        # Parse modifier indicator
        modifier = row.get("modifier_indicator", "0").strip()
        if modifier not in ("0", "1", "9"):
            modifier = "0"

        # Parse dates
        effective_date = self._parse_date(row.get("effective_date", ""))
        deletion_date = self._parse_date(row.get("deletion_date", ""))

        # Skip deleted edits if deletion date is in the past
        if deletion_date and deletion_date < date.today():
            return None

        return {
            "id": f"{col1}_{col2}",
            "column1_code": col1,
            "column2_code": col2,
            "modifier_indicator": modifier,
            "effective_date": effective_date.isoformat() if effective_date else "2024-01-01",
            "deletion_date": deletion_date.isoformat() if deletion_date else None,
            "edit_type": "PTP",
            "rationale": row.get("rationale", "").strip() or None,
        }

    def _parse_date(self, value: str) -> Optional[date]:
        """Parse date from various formats."""
        if not value:
            return None

        value = value.strip()

        # Try different date formats
        formats = [
            "%Y%m%d",      # 20240101
            "%m/%d/%Y",   # 01/01/2024
            "%Y-%m-%d",   # 2024-01-01
            "%m-%d-%Y",   # 01-01-2024
        ]

        for fmt in formats:
            try:
                return date.fromisoformat(value) if "-" in value and len(value) == 10 else None
            except ValueError:
                pass

            try:
                from datetime import datetime
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        return None

    async def import_practitioner_edits(
        self,
        file_path: Path,
    ) -> dict[str, int]:
        """
        Import NCCI edits for practitioner services.

        Args:
            file_path: Path to practitioner PTP edits file

        Returns:
            Import statistics
        """
        logger.info("Importing NCCI practitioner PTP edits")
        return await self.import_from_file(file_path)

    async def import_facility_edits(
        self,
        file_path: Path,
    ) -> dict[str, int]:
        """
        Import NCCI edits for facility services.

        Args:
            file_path: Path to facility PTP edits file

        Returns:
            Import statistics
        """
        logger.info("Importing NCCI facility PTP edits")
        return await self.import_from_file(file_path)

    async def generate_sample_data(self, count: int = 100) -> list[dict]:
        """
        Generate sample NCCI edits for testing.

        Args:
            count: Number of sample edits to generate

        Returns:
            List of sample NCCI edit documents
        """
        # Common NCCI edit pairs (comprehensive code, component code)
        sample_edits = [
            ("99214", "99211", "0", "Column 2 is a component of Column 1 E/M service"),
            ("99215", "99211", "0", "Column 2 is a component of Column 1 E/M service"),
            ("99215", "99212", "0", "Column 2 is a component of Column 1 E/M service"),
            ("99215", "99213", "0", "Column 2 is a component of Column 1 E/M service"),
            ("43239", "43235", "1", "EGD with biopsy includes diagnostic EGD"),
            ("43248", "43235", "1", "EGD with dilation includes diagnostic EGD"),
            ("45380", "45378", "1", "Colonoscopy with biopsy includes diagnostic colonoscopy"),
            ("45385", "45378", "1", "Colonoscopy with polypectomy includes diagnostic colonoscopy"),
            ("36415", "36416", "0", "Venipuncture and capillary blood not separately billable"),
            ("71046", "71045", "1", "2-view chest X-ray includes 1-view"),
            ("71047", "71045", "1", "3-view chest X-ray includes 1-view"),
            ("71047", "71046", "1", "3-view chest X-ray includes 2-view"),
            ("93000", "93005", "0", "Complete ECG includes tracing only"),
            ("93000", "93010", "0", "Complete ECG includes interpretation only"),
            ("80053", "80048", "0", "Comprehensive panel includes basic panel"),
            ("80053", "80051", "0", "Comprehensive panel includes electrolyte panel"),
            ("85025", "85027", "0", "Complete CBC includes automated hemogram"),
            ("10060", "10061", "0", "Simple I&D and complicated I&D mutually exclusive"),
            ("11042", "11040", "1", "Debridement levels are mutually exclusive"),
            ("17000", "17003", "0", "First lesion destruction includes additional lesions"),
        ]

        documents = []
        for col1, col2, modifier, rationale in sample_edits[:count]:
            doc = self.parse_row({
                "column1_code": col1,
                "column2_code": col2,
                "modifier_indicator": modifier,
                "effective_date": "2024-01-01",
                "rationale": rationale,
            })
            if doc:
                documents.append(doc)

        return documents
