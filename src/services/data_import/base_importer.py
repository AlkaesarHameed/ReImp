"""
Base Importer Abstract Class for Medical Code Data.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19
"""

import csv
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generator, Optional

from src.gateways.search_gateway import SearchCollection, SearchGateway

logger = logging.getLogger(__name__)


class BaseImporter(ABC):
    """
    Abstract base class for medical code data importers.

    Subclasses must implement:
    - collection: Target Typesense collection
    - parse_row: Convert CSV row to document dict
    """

    def __init__(
        self,
        search_gateway: SearchGateway,
        batch_size: int = 500,
    ):
        """
        Initialize the importer.

        Args:
            search_gateway: SearchGateway instance for Typesense operations
            batch_size: Number of documents to import per batch
        """
        self.search_gateway = search_gateway
        self.batch_size = batch_size
        self._stats = {
            "total_rows": 0,
            "imported": 0,
            "skipped": 0,
            "errors": 0,
        }

    @property
    @abstractmethod
    def collection(self) -> SearchCollection:
        """Target Typesense collection for this importer."""
        pass

    @property
    @abstractmethod
    def source_description(self) -> str:
        """Description of the data source (for logging)."""
        pass

    @abstractmethod
    def parse_row(self, row: dict) -> Optional[dict]:
        """
        Parse a CSV row into a document dict for Typesense.

        Args:
            row: CSV row as dict

        Returns:
            Document dict for Typesense, or None to skip the row
        """
        pass

    def get_column_mapping(self) -> dict[str, str]:
        """
        Get column name mapping from source file to internal names.

        Override in subclass if source columns need renaming.

        Returns:
            Dict mapping source column names to internal names
        """
        return {}

    def validate_row(self, row: dict) -> bool:
        """
        Validate a row before parsing.

        Override in subclass for custom validation.

        Args:
            row: CSV row as dict

        Returns:
            True if row is valid, False to skip
        """
        return True

    async def import_from_file(
        self,
        file_path: Path,
        delimiter: str = ",",
        encoding: str = "utf-8",
        skip_header: bool = False,
    ) -> dict[str, int]:
        """
        Import data from a CSV file.

        Args:
            file_path: Path to the CSV file
            delimiter: CSV delimiter character
            encoding: File encoding
            skip_header: Whether to skip the first row

        Returns:
            Import statistics
        """
        logger.info(f"Starting import from {file_path}")
        logger.info(f"Source: {self.source_description}")

        self._stats = {
            "total_rows": 0,
            "imported": 0,
            "skipped": 0,
            "errors": 0,
        }

        documents = []
        column_mapping = self.get_column_mapping()

        try:
            with open(file_path, "r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f, delimiter=delimiter)

                for row in reader:
                    self._stats["total_rows"] += 1

                    # Apply column mapping
                    if column_mapping:
                        mapped_row = {}
                        for key, value in row.items():
                            mapped_key = column_mapping.get(key, key)
                            mapped_row[mapped_key] = value
                        row = mapped_row

                    # Validate row
                    if not self.validate_row(row):
                        self._stats["skipped"] += 1
                        continue

                    # Parse row
                    try:
                        doc = self.parse_row(row)
                        if doc is None:
                            self._stats["skipped"] += 1
                            continue
                        documents.append(doc)
                    except Exception as e:
                        self._stats["errors"] += 1
                        logger.warning(f"Error parsing row {self._stats['total_rows']}: {e}")
                        continue

                    # Import batch when full
                    if len(documents) >= self.batch_size:
                        await self._import_batch(documents)
                        documents = []

                # Import remaining documents
                if documents:
                    await self._import_batch(documents)

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise

        logger.info(
            f"Import complete: {self._stats['imported']} imported, "
            f"{self._stats['skipped']} skipped, {self._stats['errors']} errors"
        )
        return self._stats

    async def import_from_generator(
        self,
        rows: Generator[dict, None, None],
    ) -> dict[str, int]:
        """
        Import data from a generator of row dicts.

        Args:
            rows: Generator yielding row dicts

        Returns:
            Import statistics
        """
        self._stats = {
            "total_rows": 0,
            "imported": 0,
            "skipped": 0,
            "errors": 0,
        }

        documents = []

        for row in rows:
            self._stats["total_rows"] += 1

            if not self.validate_row(row):
                self._stats["skipped"] += 1
                continue

            try:
                doc = self.parse_row(row)
                if doc is None:
                    self._stats["skipped"] += 1
                    continue
                documents.append(doc)
            except Exception as e:
                self._stats["errors"] += 1
                logger.warning(f"Error parsing row {self._stats['total_rows']}: {e}")
                continue

            if len(documents) >= self.batch_size:
                await self._import_batch(documents)
                documents = []

        if documents:
            await self._import_batch(documents)

        return self._stats

    async def _import_batch(self, documents: list[dict]) -> None:
        """Import a batch of documents to Typesense."""
        try:
            result = await self.search_gateway.import_documents(
                self.collection,
                documents,
                batch_size=len(documents),
            )
            self._stats["imported"] += result["success"]
            self._stats["errors"] += result["failure"]
        except Exception as e:
            self._stats["errors"] += len(documents)
            logger.error(f"Batch import failed: {e}")

    @property
    def stats(self) -> dict[str, int]:
        """Get current import statistics."""
        return self._stats.copy()
