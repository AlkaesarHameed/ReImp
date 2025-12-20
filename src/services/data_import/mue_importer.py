"""
MUE (Medically Unlikely Edits) Importer.

Source: Design Document 04_validation_engine_comprehensive_design.md
CMS MUE: https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci/medically-unlikely-edits
Verified: 2025-12-19

Imports MUE limits that define the maximum units of service that a provider
would report under most circumstances for a single beneficiary on a single
date of service.
"""

import logging
from pathlib import Path
from typing import Optional

from src.gateways.search_gateway import SearchCollection, SearchGateway
from src.services.data_import.base_importer import BaseImporter

logger = logging.getLogger(__name__)


class MUEImporter(BaseImporter):
    """
    Importer for MUE (Medically Unlikely Edits) limits.

    MUE values represent the maximum units of service that should be
    billed per line item, per date of service, or per claim depending
    on the adjudicator indicator.
    """

    @property
    def collection(self) -> SearchCollection:
        return SearchCollection.MUE_LIMITS

    @property
    def source_description(self) -> str:
        return "CMS MUE Files (https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci/medically-unlikely-edits)"

    def get_column_mapping(self) -> dict[str, str]:
        """Map CMS MUE file column names to internal names."""
        return {
            "HCPCS": "cpt_code",
            "CPT": "cpt_code",
            "CPT/HCPCS": "cpt_code",
            "HCPC": "cpt_code",
            "PRACTITIONER_MUE": "practitioner_limit",
            "Practitioner MUE": "practitioner_limit",
            "PRAC_MUE": "practitioner_limit",
            "PRACTITIONER_LIMIT": "practitioner_limit",
            "OUTPATIENT_HOSPITAL_MUE": "facility_limit",
            "Facility MUE": "facility_limit",
            "FAC_MUE": "facility_limit",
            "FACILITY_LIMIT": "facility_limit",
            "DME_MUE": "dme_limit",
            "DME MUE": "dme_limit",
            "DME_LIMIT": "dme_limit",
            "MAI": "adjudicator",
            "MUE_ADJUDICATION_INDICATOR": "adjudicator",
            "Adjudication Indicator": "adjudicator",
            "ADJUDICATOR": "adjudicator",
            "EFFECTIVE_DATE": "effective_date",
            "Effective Date": "effective_date",
            "EFF_DATE": "effective_date",
            "RATIONALE": "rationale",
            "MUE_RATIONALE": "rationale",
        }

    def validate_row(self, row: dict) -> bool:
        """Validate MUE row."""
        code = row.get("cpt_code", "").strip()
        if not code or len(code) != 5:
            return False

        # Must have at least one limit value
        prac_limit = row.get("practitioner_limit", "").strip()
        fac_limit = row.get("facility_limit", "").strip()

        if not prac_limit and not fac_limit:
            return False

        return True

    def parse_row(self, row: dict) -> Optional[dict]:
        """Parse MUE row into Typesense document."""
        code = row.get("cpt_code", "").strip().upper()

        if not code:
            return None

        # Parse limit values
        prac_limit = self._parse_limit(row.get("practitioner_limit"))
        fac_limit = self._parse_limit(row.get("facility_limit"))
        dme_limit = self._parse_limit(row.get("dme_limit"))

        # Skip if no valid limits
        if prac_limit is None and fac_limit is None:
            return None

        # Use default values if one is missing
        if prac_limit is None:
            prac_limit = fac_limit
        if fac_limit is None:
            fac_limit = prac_limit

        # Parse adjudicator indicator
        adjudicator = row.get("adjudicator", "2").strip()
        if adjudicator not in ("1", "2", "3"):
            adjudicator = "2"  # Default to date of service

        # Parse effective date
        effective_date = row.get("effective_date", "2024-01-01").strip()
        if not effective_date:
            effective_date = "2024-01-01"

        return {
            "id": code,
            "cpt_code": code,
            "practitioner_limit": prac_limit,
            "facility_limit": fac_limit,
            "dme_limit": dme_limit,
            "adjudicator": adjudicator,
            "effective_date": effective_date,
            "rationale": row.get("rationale", "").strip() or None,
        }

    def _parse_limit(self, value: Optional[str]) -> Optional[int]:
        """Parse limit value from string."""
        if not value:
            return None

        value = str(value).strip()

        # Handle special values
        if value.upper() in ("", "N/A", "NA", "-"):
            return None

        try:
            limit = int(value)
            return limit if limit > 0 else None
        except ValueError:
            return None

    async def import_practitioner_mues(
        self,
        file_path: Path,
    ) -> dict[str, int]:
        """
        Import MUE limits for practitioner services.

        Args:
            file_path: Path to practitioner MUE file

        Returns:
            Import statistics
        """
        logger.info("Importing practitioner MUE limits")
        return await self.import_from_file(file_path)

    async def import_facility_mues(
        self,
        file_path: Path,
    ) -> dict[str, int]:
        """
        Import MUE limits for facility/outpatient hospital services.

        Args:
            file_path: Path to facility MUE file

        Returns:
            Import statistics
        """
        logger.info("Importing facility MUE limits")
        return await self.import_from_file(file_path)

    async def import_dme_mues(
        self,
        file_path: Path,
    ) -> dict[str, int]:
        """
        Import MUE limits for DME (Durable Medical Equipment) services.

        Args:
            file_path: Path to DME MUE file

        Returns:
            Import statistics
        """
        logger.info("Importing DME MUE limits")
        return await self.import_from_file(file_path)

    async def generate_sample_data(self, count: int = 100) -> list[dict]:
        """
        Generate sample MUE limits for testing.

        Args:
            count: Number of sample limits to generate

        Returns:
            List of sample MUE limit documents
        """
        # Common MUE limits (code, practitioner limit, facility limit, adjudicator, rationale)
        sample_mues = [
            ("99213", 1, 1, "2", "One E/M service per date of service"),
            ("99214", 1, 1, "2", "One E/M service per date of service"),
            ("99215", 1, 1, "2", "One E/M service per date of service"),
            ("99202", 1, 1, "2", "One new patient visit per date of service"),
            ("99203", 1, 1, "2", "One new patient visit per date of service"),
            ("99204", 1, 1, "2", "One new patient visit per date of service"),
            ("99205", 1, 1, "2", "One new patient visit per date of service"),
            ("36415", 3, 3, "2", "Maximum venipunctures per date of service"),
            ("90471", 4, 4, "2", "Immunization administrations per date of service"),
            ("90472", 4, 4, "2", "Additional immunization administrations per date of service"),
            ("96372", 4, 4, "2", "Injections per date of service"),
            ("71046", 2, 2, "2", "Chest X-rays per date of service"),
            ("80053", 1, 1, "2", "One comprehensive metabolic panel per date of service"),
            ("85025", 2, 2, "2", "CBC per date of service"),
            ("93000", 3, 3, "2", "ECG per date of service"),
            ("J3420", 5, 5, "2", "B12 injections per date of service"),
            ("A4206", 10, 10, "1", "Syringes per claim line"),
            ("G0438", 1, 1, "3", "Annual wellness visit per policy period"),
            ("G0439", 1, 1, "3", "Subsequent wellness visit per policy period"),
            ("10060", 2, 2, "2", "Simple I&D procedures per date of service"),
        ]

        documents = []
        for code, prac_limit, fac_limit, adj, rationale in sample_mues[:count]:
            doc = self.parse_row({
                "cpt_code": code,
                "practitioner_limit": str(prac_limit),
                "facility_limit": str(fac_limit),
                "adjudicator": adj,
                "effective_date": "2024-01-01",
                "rationale": rationale,
            })
            if doc:
                documents.append(doc)

        return documents
