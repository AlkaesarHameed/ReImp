"""
Search Gateway for Typesense Medical Code Search.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Provides high-performance search for medical codes (ICD-10, CPT, NCCI, MUE)
with sub-50ms latency target.
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import typesense
from typesense.exceptions import ObjectNotFound, TypesenseClientError

from src.core.config import get_claims_settings
from src.schemas.medical_codes import (
    CPTCode,
    CrosswalkResult,
    ICD10Code,
    MUELimit,
    NCCIEdit,
    ModifierIndicator,
    NCCIEditType,
    MUEAdjudicator,
    GenderRestriction,
)

logger = logging.getLogger(__name__)


class SearchCollection(str, Enum):
    """Typesense collection names."""

    ICD10_CODES = "icd10_codes"
    CPT_CODES = "cpt_codes"
    NCCI_EDITS = "ncci_edits"
    MUE_LIMITS = "mue_limits"
    ICD_CPT_CROSSWALK = "icd_cpt_crosswalk"


@dataclass
class SearchConfig:
    """Search gateway configuration."""

    host: str = "localhost"
    port: int = 8108
    protocol: str = "http"
    api_key: str = "claims-typesense-dev-key"
    connection_timeout: int = 5
    search_timeout_ms: int = 50


# Typesense collection schemas
COLLECTION_SCHEMAS = {
    SearchCollection.ICD10_CODES: {
        "name": "icd10_codes",
        "fields": [
            {"name": "code", "type": "string", "facet": True},
            {"name": "description", "type": "string"},
            {"name": "short_description", "type": "string", "optional": True},
            {"name": "category", "type": "string", "facet": True},
            {"name": "chapter", "type": "string", "optional": True},
            {"name": "is_billable", "type": "bool", "facet": True},
            {"name": "is_header", "type": "bool", "facet": True},
            {"name": "min_age", "type": "int32", "optional": True},
            {"name": "max_age", "type": "int32", "optional": True},
            {"name": "gender_restriction", "type": "string", "facet": True},
            {"name": "effective_date", "type": "string", "optional": True},
            {"name": "termination_date", "type": "string", "optional": True},
        ],
        "default_sorting_field": "code",
        "token_separators": [".", "-"],
    },
    SearchCollection.CPT_CODES: {
        "name": "cpt_codes",
        "fields": [
            {"name": "code", "type": "string", "facet": True},
            {"name": "description", "type": "string"},
            {"name": "short_description", "type": "string", "optional": True},
            {"name": "category", "type": "string", "facet": True},
            {"name": "subcategory", "type": "string", "optional": True},
            {"name": "work_rvu", "type": "float", "optional": True},
            {"name": "facility_pe_rvu", "type": "float", "optional": True},
            {"name": "non_facility_pe_rvu", "type": "float", "optional": True},
            {"name": "mp_rvu", "type": "float", "optional": True},
            {"name": "status", "type": "string", "facet": True},
            {"name": "min_age", "type": "int32", "optional": True},
            {"name": "max_age", "type": "int32", "optional": True},
            {"name": "gender_restriction", "type": "string", "facet": True},
            {"name": "global_period", "type": "int32", "optional": True},
            {"name": "modifier_allowed", "type": "bool"},
        ],
        "default_sorting_field": "code",
    },
    SearchCollection.NCCI_EDITS: {
        "name": "ncci_edits",
        "fields": [
            {"name": "column1_code", "type": "string", "facet": True},
            {"name": "column2_code", "type": "string", "facet": True},
            {"name": "modifier_indicator", "type": "string", "facet": True},
            {"name": "effective_date", "type": "string"},
            {"name": "deletion_date", "type": "string", "optional": True},
            {"name": "edit_type", "type": "string", "facet": True},
            {"name": "rationale", "type": "string", "optional": True},
        ],
    },
    SearchCollection.MUE_LIMITS: {
        "name": "mue_limits",
        "fields": [
            {"name": "cpt_code", "type": "string", "facet": True},
            {"name": "practitioner_limit", "type": "int32"},
            {"name": "facility_limit", "type": "int32"},
            {"name": "dme_limit", "type": "int32", "optional": True},
            {"name": "adjudicator", "type": "string", "facet": True},
            {"name": "effective_date", "type": "string"},
            {"name": "rationale", "type": "string", "optional": True},
        ],
    },
    SearchCollection.ICD_CPT_CROSSWALK: {
        "name": "icd_cpt_crosswalk",
        "fields": [
            {"name": "icd_code", "type": "string", "facet": True},
            {"name": "cpt_code", "type": "string", "facet": True},
            {"name": "is_valid", "type": "bool", "facet": True},
            {"name": "confidence", "type": "float"},
            {"name": "evidence", "type": "string", "optional": True},
            {"name": "source", "type": "string", "facet": True},
        ],
    },
}


class SearchGateway:
    """
    High-performance search gateway for medical codes.

    Provides:
    - ICD-10 code search with typo tolerance
    - CPT/HCPCS code search
    - NCCI edit lookups
    - MUE limit lookups
    - ICD-CPT crosswalk validation

    Target: <50ms search latency
    """

    def __init__(self, config: Optional[SearchConfig] = None):
        """
        Initialize the search gateway.

        Args:
            config: Optional search configuration. If not provided,
                    loads from application settings.
        """
        if config is None:
            settings = get_claims_settings()
            config = SearchConfig(
                host=settings.TYPESENSE_HOST,
                port=settings.TYPESENSE_PORT,
                protocol=settings.TYPESENSE_PROTOCOL,
                api_key=settings.TYPESENSE_API_KEY,
                connection_timeout=settings.TYPESENSE_CONNECTION_TIMEOUT,
                search_timeout_ms=settings.TYPESENSE_SEARCH_TIMEOUT_MS,
            )

        self.config = config
        self._client: Optional[typesense.Client] = None
        self._initialized = False

    @property
    def client(self) -> typesense.Client:
        """Get or create Typesense client."""
        if self._client is None:
            self._client = typesense.Client({
                "nodes": [{
                    "host": self.config.host,
                    "port": str(self.config.port),
                    "protocol": self.config.protocol,
                }],
                "api_key": self.config.api_key,
                "connection_timeout_seconds": self.config.connection_timeout,
            })
        return self._client

    async def initialize(self) -> None:
        """Initialize the gateway and verify connection."""
        if self._initialized:
            return

        try:
            # Verify connection with health check
            health = self.client.operations.is_healthy()
            if not health:
                raise ConnectionError("Typesense health check failed")

            logger.info(
                f"Search gateway connected to Typesense at "
                f"{self.config.protocol}://{self.config.host}:{self.config.port}"
            )
            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize search gateway: {e}")
            raise

    async def create_collections(self, drop_existing: bool = False) -> dict[str, bool]:
        """
        Create all medical code collections in Typesense.

        Args:
            drop_existing: If True, drop existing collections before creating.

        Returns:
            Dict mapping collection names to success status.
        """
        results = {}

        for collection_enum, schema in COLLECTION_SCHEMAS.items():
            collection_name = schema["name"]
            try:
                if drop_existing:
                    try:
                        self.client.collections[collection_name].delete()
                        logger.info(f"Dropped existing collection: {collection_name}")
                    except ObjectNotFound:
                        pass

                self.client.collections.create(schema)
                results[collection_name] = True
                logger.info(f"Created collection: {collection_name}")

            except TypesenseClientError as e:
                if "already exists" in str(e).lower():
                    results[collection_name] = True
                    logger.info(f"Collection already exists: {collection_name}")
                else:
                    results[collection_name] = False
                    logger.error(f"Failed to create collection {collection_name}: {e}")

        return results

    async def get_collection_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all collections."""
        stats = {}
        for collection_enum in SearchCollection:
            try:
                info = self.client.collections[collection_enum.value].retrieve()
                stats[collection_enum.value] = {
                    "num_documents": info.get("num_documents", 0),
                    "num_fields": len(info.get("fields", [])),
                }
            except ObjectNotFound:
                stats[collection_enum.value] = {"num_documents": 0, "exists": False}
        return stats

    # =========================================================================
    # ICD-10 Code Operations
    # =========================================================================

    async def search_icd10(
        self,
        query: str,
        limit: int = 10,
        billable_only: bool = False,
    ) -> tuple[list[ICD10Code], int]:
        """
        Search ICD-10 codes with typo tolerance.

        Args:
            query: Search query (code or description text)
            limit: Maximum results to return
            billable_only: If True, only return billable codes

        Returns:
            Tuple of (list of matching codes, search time in ms)
        """
        start_time = time.perf_counter()

        search_params = {
            "q": query,
            "query_by": "code,description,short_description",
            "per_page": limit,
            "num_typos": 2,
            "typo_tokens_threshold": 1,
        }

        if billable_only:
            search_params["filter_by"] = "is_billable:true"

        try:
            results = self.client.collections[
                SearchCollection.ICD10_CODES.value
            ].documents.search(search_params)

            search_time_ms = int((time.perf_counter() - start_time) * 1000)

            codes = []
            for hit in results.get("hits", []):
                doc = hit["document"]
                codes.append(ICD10Code(
                    code=doc["code"],
                    description=doc["description"],
                    short_description=doc.get("short_description"),
                    category=doc["category"],
                    chapter=doc.get("chapter"),
                    is_billable=doc.get("is_billable", True),
                    is_header=doc.get("is_header", False),
                    min_age=doc.get("min_age"),
                    max_age=doc.get("max_age"),
                    gender_restriction=GenderRestriction(
                        doc.get("gender_restriction", "N")
                    ),
                ))

            logger.debug(
                f"ICD-10 search '{query}': {len(codes)} results in {search_time_ms}ms"
            )
            return codes, search_time_ms

        except Exception as e:
            logger.error(f"ICD-10 search failed: {e}")
            raise

    async def get_icd10_by_code(self, code: str) -> Optional[ICD10Code]:
        """
        Get a specific ICD-10 code by exact match.

        Args:
            code: The ICD-10 code (e.g., 'E11.9')

        Returns:
            ICD10Code if found, None otherwise
        """
        search_params = {
            "q": code,
            "query_by": "code",
            "filter_by": f'code:="{code}"',
            "per_page": 1,
        }

        try:
            results = self.client.collections[
                SearchCollection.ICD10_CODES.value
            ].documents.search(search_params)

            if results.get("found", 0) > 0:
                doc = results["hits"][0]["document"]
                return ICD10Code(
                    code=doc["code"],
                    description=doc["description"],
                    short_description=doc.get("short_description"),
                    category=doc["category"],
                    chapter=doc.get("chapter"),
                    is_billable=doc.get("is_billable", True),
                    is_header=doc.get("is_header", False),
                    min_age=doc.get("min_age"),
                    max_age=doc.get("max_age"),
                    gender_restriction=GenderRestriction(
                        doc.get("gender_restriction", "N")
                    ),
                )
            return None

        except Exception as e:
            logger.error(f"ICD-10 lookup failed for {code}: {e}")
            raise

    # =========================================================================
    # CPT Code Operations
    # =========================================================================

    async def search_cpt(
        self,
        query: str,
        limit: int = 10,
        active_only: bool = True,
    ) -> tuple[list[CPTCode], int]:
        """
        Search CPT/HCPCS codes with typo tolerance.

        Args:
            query: Search query (code or description text)
            limit: Maximum results to return
            active_only: If True, only return active codes

        Returns:
            Tuple of (list of matching codes, search time in ms)
        """
        start_time = time.perf_counter()

        search_params = {
            "q": query,
            "query_by": "code,description,short_description",
            "per_page": limit,
            "num_typos": 2,
        }

        if active_only:
            search_params["filter_by"] = 'status:="A"'

        try:
            results = self.client.collections[
                SearchCollection.CPT_CODES.value
            ].documents.search(search_params)

            search_time_ms = int((time.perf_counter() - start_time) * 1000)

            codes = []
            for hit in results.get("hits", []):
                doc = hit["document"]
                codes.append(CPTCode(
                    code=doc["code"],
                    description=doc["description"],
                    short_description=doc.get("short_description"),
                    category=doc["category"],
                    subcategory=doc.get("subcategory"),
                    work_rvu=doc.get("work_rvu"),
                    facility_pe_rvu=doc.get("facility_pe_rvu"),
                    non_facility_pe_rvu=doc.get("non_facility_pe_rvu"),
                    mp_rvu=doc.get("mp_rvu"),
                    status=doc.get("status", "A"),
                    min_age=doc.get("min_age"),
                    max_age=doc.get("max_age"),
                    gender_restriction=GenderRestriction(
                        doc.get("gender_restriction", "N")
                    ),
                    global_period=doc.get("global_period"),
                    modifier_allowed=doc.get("modifier_allowed", True),
                ))

            logger.debug(
                f"CPT search '{query}': {len(codes)} results in {search_time_ms}ms"
            )
            return codes, search_time_ms

        except Exception as e:
            logger.error(f"CPT search failed: {e}")
            raise

    async def get_cpt_by_code(self, code: str) -> Optional[CPTCode]:
        """
        Get a specific CPT code by exact match.

        Args:
            code: The CPT/HCPCS code (e.g., '99213')

        Returns:
            CPTCode if found, None otherwise
        """
        search_params = {
            "q": code,
            "query_by": "code",
            "filter_by": f'code:="{code}"',
            "per_page": 1,
        }

        try:
            results = self.client.collections[
                SearchCollection.CPT_CODES.value
            ].documents.search(search_params)

            if results.get("found", 0) > 0:
                doc = results["hits"][0]["document"]
                return CPTCode(
                    code=doc["code"],
                    description=doc["description"],
                    short_description=doc.get("short_description"),
                    category=doc["category"],
                    subcategory=doc.get("subcategory"),
                    work_rvu=doc.get("work_rvu"),
                    status=doc.get("status", "A"),
                    min_age=doc.get("min_age"),
                    max_age=doc.get("max_age"),
                    gender_restriction=GenderRestriction(
                        doc.get("gender_restriction", "N")
                    ),
                )
            return None

        except Exception as e:
            logger.error(f"CPT lookup failed for {code}: {e}")
            raise

    # =========================================================================
    # NCCI Edit Operations
    # =========================================================================

    async def check_ncci_edit(
        self,
        cpt1: str,
        cpt2: str,
    ) -> Optional[NCCIEdit]:
        """
        Check for NCCI PTP edit between two CPT codes.

        Args:
            cpt1: First CPT code (potential column 1)
            cpt2: Second CPT code (potential column 2)

        Returns:
            NCCIEdit if an edit exists, None otherwise
        """
        # Check both directions
        for col1, col2 in [(cpt1, cpt2), (cpt2, cpt1)]:
            search_params = {
                "q": "*",
                "filter_by": f'column1_code:="{col1}" && column2_code:="{col2}"',
                "per_page": 1,
            }

            try:
                results = self.client.collections[
                    SearchCollection.NCCI_EDITS.value
                ].documents.search(search_params)

                if results.get("found", 0) > 0:
                    doc = results["hits"][0]["document"]
                    return NCCIEdit(
                        column1_code=doc["column1_code"],
                        column2_code=doc["column2_code"],
                        modifier_indicator=ModifierIndicator(doc["modifier_indicator"]),
                        effective_date=doc["effective_date"],
                        deletion_date=doc.get("deletion_date"),
                        edit_type=NCCIEditType(doc.get("edit_type", "PTP")),
                        rationale=doc.get("rationale"),
                    )

            except Exception as e:
                logger.error(f"NCCI edit check failed for {col1}/{col2}: {e}")
                raise

        return None

    # =========================================================================
    # MUE Limit Operations
    # =========================================================================

    async def get_mue_limit(self, cpt_code: str) -> Optional[MUELimit]:
        """
        Get MUE (Medically Unlikely Edit) limit for a CPT code.

        Args:
            cpt_code: The CPT/HCPCS code

        Returns:
            MUELimit if found, None otherwise
        """
        search_params = {
            "q": "*",
            "filter_by": f'cpt_code:="{cpt_code}"',
            "per_page": 1,
        }

        try:
            results = self.client.collections[
                SearchCollection.MUE_LIMITS.value
            ].documents.search(search_params)

            if results.get("found", 0) > 0:
                doc = results["hits"][0]["document"]
                return MUELimit(
                    cpt_code=doc["cpt_code"],
                    practitioner_limit=doc["practitioner_limit"],
                    facility_limit=doc["facility_limit"],
                    dme_limit=doc.get("dme_limit"),
                    adjudicator=MUEAdjudicator(doc["adjudicator"]),
                    effective_date=doc["effective_date"],
                    rationale=doc.get("rationale"),
                )
            return None

        except Exception as e:
            logger.error(f"MUE lookup failed for {cpt_code}: {e}")
            raise

    # =========================================================================
    # ICD-CPT Crosswalk Operations
    # =========================================================================

    async def validate_icd_cpt_pair(
        self,
        icd_code: str,
        cpt_code: str,
    ) -> CrosswalkResult:
        """
        Validate an ICD-CPT code pairing.

        Args:
            icd_code: ICD-10 diagnosis code
            cpt_code: CPT procedure code

        Returns:
            CrosswalkResult indicating validity
        """
        search_params = {
            "q": "*",
            "filter_by": f'icd_code:="{icd_code}" && cpt_code:="{cpt_code}"',
            "per_page": 1,
        }

        try:
            results = self.client.collections[
                SearchCollection.ICD_CPT_CROSSWALK.value
            ].documents.search(search_params)

            if results.get("found", 0) > 0:
                doc = results["hits"][0]["document"]
                return CrosswalkResult(
                    icd_code=icd_code,
                    cpt_code=cpt_code,
                    is_valid=doc.get("is_valid", True),
                    confidence=doc.get("confidence", 1.0),
                    evidence=doc.get("evidence"),
                    source=doc.get("source", "CMS"),
                )

            # If no specific crosswalk found, return uncertain result
            return CrosswalkResult(
                icd_code=icd_code,
                cpt_code=cpt_code,
                is_valid=True,  # Default to valid if no explicit edit
                confidence=0.5,  # Low confidence when not in database
                evidence="No specific crosswalk found in database",
                source="DEFAULT",
            )

        except Exception as e:
            logger.error(f"Crosswalk validation failed for {icd_code}/{cpt_code}: {e}")
            raise

    async def validate_all_pairs(
        self,
        icd_codes: list[str],
        cpt_codes: list[str],
    ) -> list[CrosswalkResult]:
        """
        Validate all combinations of ICD and CPT codes.

        Args:
            icd_codes: List of ICD-10 codes
            cpt_codes: List of CPT codes

        Returns:
            List of CrosswalkResults for all pairs
        """
        results = []
        for icd in icd_codes:
            for cpt in cpt_codes:
                result = await self.validate_icd_cpt_pair(icd, cpt)
                results.append(result)
        return results

    # =========================================================================
    # Bulk Import Operations
    # =========================================================================

    async def import_documents(
        self,
        collection: SearchCollection,
        documents: list[dict],
        batch_size: int = 100,
    ) -> dict[str, int]:
        """
        Bulk import documents into a collection.

        Args:
            collection: Target collection
            documents: List of documents to import
            batch_size: Number of documents per batch

        Returns:
            Dict with success/failure counts
        """
        success_count = 0
        failure_count = 0

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            try:
                # Use import with action=upsert to handle duplicates
                result = self.client.collections[collection.value].documents.import_(
                    batch,
                    {"action": "upsert"}
                )

                # Count successes and failures
                for item in result:
                    if item.get("success", False):
                        success_count += 1
                    else:
                        failure_count += 1
                        logger.warning(f"Import failed: {item.get('error', 'Unknown error')}")

            except Exception as e:
                failure_count += len(batch)
                logger.error(f"Batch import failed: {e}")

        logger.info(
            f"Imported to {collection.value}: "
            f"{success_count} success, {failure_count} failures"
        )
        return {"success": success_count, "failure": failure_count}

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on Typesense connection.

        Returns:
            Dict with health status and metrics
        """
        try:
            is_healthy = self.client.operations.is_healthy()
            stats = await self.get_collection_stats()

            return {
                "healthy": is_healthy,
                "host": f"{self.config.protocol}://{self.config.host}:{self.config.port}",
                "collections": stats,
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }

    async def close(self) -> None:
        """Close the gateway and clean up resources."""
        self._client = None
        self._initialized = False
        logger.info("Search gateway closed")


# Singleton instance
_search_gateway: Optional[SearchGateway] = None


def get_search_gateway() -> SearchGateway:
    """Get or create the singleton search gateway instance."""
    global _search_gateway
    if _search_gateway is None:
        _search_gateway = SearchGateway()
    return _search_gateway


async def initialize_search_gateway() -> SearchGateway:
    """Initialize and return the search gateway."""
    gateway = get_search_gateway()
    await gateway.initialize()
    return gateway
