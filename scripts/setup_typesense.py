#!/usr/bin/env python3
"""
Typesense Setup Script for Claims Validation Engine.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

This script:
1. Creates all required Typesense collections
2. Optionally imports sample data for development/testing

Usage:
    python scripts/setup_typesense.py [--sample-data] [--drop-existing]

Options:
    --sample-data    Import sample medical codes for testing
    --drop-existing  Drop existing collections before creating
    --host          Typesense host (default: localhost)
    --port          Typesense port (default: 8108)
    --api-key       Typesense API key
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gateways.search_gateway import (
    SearchConfig,
    SearchGateway,
    SearchCollection,
)
from src.services.data_import import (
    ICD10Importer,
    CPTImporter,
    NCCIImporter,
    MUEImporter,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def setup_collections(
    gateway: SearchGateway,
    drop_existing: bool = False,
) -> dict[str, bool]:
    """
    Create all required Typesense collections.

    Args:
        gateway: SearchGateway instance
        drop_existing: If True, drop existing collections first

    Returns:
        Dict mapping collection names to success status
    """
    logger.info("Creating Typesense collections...")
    results = await gateway.create_collections(drop_existing=drop_existing)

    for name, success in results.items():
        status = "✓" if success else "✗"
        logger.info(f"  {status} {name}")

    return results


async def import_sample_data(gateway: SearchGateway) -> dict[str, dict[str, int]]:
    """
    Import sample medical code data for development/testing.

    Args:
        gateway: SearchGateway instance

    Returns:
        Dict mapping collection names to import statistics
    """
    logger.info("Importing sample data...")
    results = {}

    # Import ICD-10 sample data
    logger.info("  Importing ICD-10 codes...")
    icd10_importer = ICD10Importer(gateway)
    icd10_samples = await icd10_importer.generate_sample_data(count=50)
    icd10_result = await gateway.import_documents(
        SearchCollection.ICD10_CODES,
        icd10_samples,
    )
    results["icd10_codes"] = icd10_result
    logger.info(f"    Imported {icd10_result['success']} ICD-10 codes")

    # Import CPT sample data
    logger.info("  Importing CPT codes...")
    cpt_importer = CPTImporter(gateway)
    cpt_samples = await cpt_importer.generate_sample_data(count=50)
    cpt_result = await gateway.import_documents(
        SearchCollection.CPT_CODES,
        cpt_samples,
    )
    results["cpt_codes"] = cpt_result
    logger.info(f"    Imported {cpt_result['success']} CPT codes")

    # Import NCCI sample data
    logger.info("  Importing NCCI edits...")
    ncci_importer = NCCIImporter(gateway)
    ncci_samples = await ncci_importer.generate_sample_data(count=50)
    ncci_result = await gateway.import_documents(
        SearchCollection.NCCI_EDITS,
        ncci_samples,
    )
    results["ncci_edits"] = ncci_result
    logger.info(f"    Imported {ncci_result['success']} NCCI edits")

    # Import MUE sample data
    logger.info("  Importing MUE limits...")
    mue_importer = MUEImporter(gateway)
    mue_samples = await mue_importer.generate_sample_data(count=50)
    mue_result = await gateway.import_documents(
        SearchCollection.MUE_LIMITS,
        mue_samples,
    )
    results["mue_limits"] = mue_result
    logger.info(f"    Imported {mue_result['success']} MUE limits")

    return results


async def verify_setup(gateway: SearchGateway) -> bool:
    """
    Verify the Typesense setup by running test queries.

    Args:
        gateway: SearchGateway instance

    Returns:
        True if all verifications pass
    """
    logger.info("Verifying setup...")
    all_passed = True

    # Test ICD-10 search
    try:
        codes, search_time = await gateway.search_icd10("diabetes", limit=5)
        if codes:
            logger.info(f"  ✓ ICD-10 search: {len(codes)} results in {search_time}ms")
        else:
            logger.warning("  ✗ ICD-10 search: No results (may need data import)")
            all_passed = False
    except Exception as e:
        logger.error(f"  ✗ ICD-10 search failed: {e}")
        all_passed = False

    # Test CPT search
    try:
        codes, search_time = await gateway.search_cpt("office visit", limit=5)
        if codes:
            logger.info(f"  ✓ CPT search: {len(codes)} results in {search_time}ms")
        else:
            logger.warning("  ✗ CPT search: No results (may need data import)")
            all_passed = False
    except Exception as e:
        logger.error(f"  ✗ CPT search failed: {e}")
        all_passed = False

    # Test collection stats
    try:
        stats = await gateway.get_collection_stats()
        logger.info("  Collection statistics:")
        for name, info in stats.items():
            doc_count = info.get("num_documents", 0)
            logger.info(f"    {name}: {doc_count} documents")
    except Exception as e:
        logger.error(f"  ✗ Failed to get stats: {e}")
        all_passed = False

    return all_passed


async def main(
    host: str = "localhost",
    port: int = 8108,
    api_key: str = "claims-typesense-dev-key",
    drop_existing: bool = False,
    sample_data: bool = False,
) -> int:
    """
    Main setup function.

    Args:
        host: Typesense host
        port: Typesense port
        api_key: Typesense API key
        drop_existing: Drop existing collections
        sample_data: Import sample data

    Returns:
        Exit code (0 for success)
    """
    logger.info("=" * 60)
    logger.info("Typesense Setup for Claims Validation Engine")
    logger.info("=" * 60)

    # Create gateway
    config = SearchConfig(
        host=host,
        port=port,
        api_key=api_key,
    )
    gateway = SearchGateway(config)

    try:
        # Initialize and check connection
        logger.info(f"Connecting to Typesense at {host}:{port}...")
        await gateway.initialize()

        health = await gateway.health_check()
        if not health.get("healthy"):
            logger.error("Typesense health check failed!")
            logger.error("Make sure Typesense is running:")
            logger.error("  docker compose -f docker/docker-compose.local.yml up -d typesense")
            return 1

        logger.info("✓ Connected to Typesense")

        # Create collections
        results = await setup_collections(gateway, drop_existing=drop_existing)
        if not all(results.values()):
            logger.error("Some collections failed to create")
            return 1

        # Import sample data if requested
        if sample_data:
            await import_sample_data(gateway)

        # Verify setup
        if not await verify_setup(gateway):
            logger.warning("Some verifications failed (may be expected without data)")

        logger.info("=" * 60)
        logger.info("Setup complete!")
        logger.info("=" * 60)

        if not sample_data:
            logger.info("")
            logger.info("To import sample data, run:")
            logger.info("  python scripts/setup_typesense.py --sample-data")
            logger.info("")
            logger.info("To import production CMS data, use the data importers:")
            logger.info("  python scripts/import_medical_codes.py --icd10 <file>")

        return 0

    except ConnectionError as e:
        logger.error(f"Connection failed: {e}")
        logger.error("")
        logger.error("Make sure Typesense is running:")
        logger.error("  docker compose -f docker/docker-compose.local.yml up -d typesense")
        return 1

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return 1

    finally:
        await gateway.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Setup Typesense for Claims Validation Engine"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Typesense host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8108,
        help="Typesense port (default: 8108)",
    )
    parser.add_argument(
        "--api-key",
        default="claims-typesense-dev-key",
        help="Typesense API key",
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop existing collections before creating",
    )
    parser.add_argument(
        "--sample-data",
        action="store_true",
        help="Import sample medical codes for testing",
    )

    args = parser.parse_args()

    exit_code = asyncio.run(
        main(
            host=args.host,
            port=args.port,
            api_key=args.api_key,
            drop_existing=args.drop_existing,
            sample_data=args.sample_data,
        )
    )
    sys.exit(exit_code)
