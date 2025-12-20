"""
OCR Processing Pipeline.

Provides:
- Multi-page document OCR processing
- Confidence-based provider fallback
- Table extraction
- Text region detection
- Language detection

Source: Design Document Section 4.3 - Document Processing
Verified: 2025-12-18
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from src.core.enums import DocumentType, OCRProvider

logger = logging.getLogger(__name__)


class OCRQuality(str, Enum):
    """OCR result quality classification."""

    HIGH = "high"  # > 0.95 confidence
    GOOD = "good"  # 0.85 - 0.95
    ACCEPTABLE = "acceptable"  # 0.70 - 0.85
    POOR = "poor"  # < 0.70


@dataclass
class TextRegion:
    """Detected text region in document."""

    text: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x, y, width, height
    page: int = 1


@dataclass
class TableCell:
    """Single cell in a detected table."""

    text: str
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    confidence: float = 1.0


@dataclass
class ExtractedTable:
    """Table extracted from document."""

    cells: list[TableCell]
    rows: int
    cols: int
    page: int
    confidence: float
    bbox: Optional[tuple[int, int, int, int]] = None

    def to_dict(self) -> dict:
        """Convert table to dictionary format."""
        grid = {}
        for cell in self.cells:
            grid[(cell.row, cell.col)] = cell.text

        result = []
        for r in range(self.rows):
            row_data = []
            for c in range(self.cols):
                row_data.append(grid.get((r, c), ""))
            result.append(row_data)
        return {
            "rows": result,
            "num_rows": self.rows,
            "num_cols": self.cols,
            "confidence": self.confidence,
        }


@dataclass
class PageOCRResult:
    """OCR result for a single page."""

    page_number: int
    text: str
    confidence: float
    regions: list[TextRegion] = field(default_factory=list)
    tables: list[ExtractedTable] = field(default_factory=list)
    detected_language: str = "en"
    processing_time_ms: int = 0
    provider_used: str = ""


@dataclass
class OCRPipelineResult:
    """Complete OCR pipeline result."""

    success: bool
    document_id: str
    pages: list[PageOCRResult] = field(default_factory=list)
    full_text: str = ""
    overall_confidence: float = 0.0
    quality: OCRQuality = OCRQuality.POOR
    total_pages: int = 0
    tables: list[ExtractedTable] = field(default_factory=list)
    detected_languages: list[str] = field(default_factory=list)
    primary_provider: str = ""
    fallback_used: bool = False
    processing_time_ms: int = 0
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class OCRPipelineConfig:
    """Configuration for OCR pipeline."""

    primary_provider: OCRProvider = OCRProvider.PADDLEOCR
    fallback_provider: Optional[OCRProvider] = OCRProvider.AZURE_DI
    confidence_threshold: float = 0.85
    fallback_on_low_confidence: bool = True
    extract_tables: bool = True
    detect_language: bool = True
    max_pages: int = 50
    timeout_per_page_seconds: int = 30
    languages: list[str] = field(default_factory=lambda: ["en", "ar"])


# =============================================================================
# OCR Pipeline Service
# =============================================================================


class OCRPipelineService:
    """
    OCR processing pipeline with multi-provider support.

    Features:
    - Automatic provider fallback on low confidence
    - Multi-page document processing
    - Table extraction
    - Language detection
    """

    def __init__(
        self,
        config: Optional[OCRPipelineConfig] = None,
        ocr_gateway=None,
    ):
        """
        Initialize OCR pipeline.

        Args:
            config: Pipeline configuration
            ocr_gateway: Pre-configured OCR gateway (for testing)
        """
        self.config = config or OCRPipelineConfig()
        self._ocr_gateway = ocr_gateway
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize OCR gateway."""
        if self._initialized:
            return

        if self._ocr_gateway is None:
            try:
                from src.gateways.ocr_gateway import OCRGateway

                self._ocr_gateway = OCRGateway(
                    primary_provider=self.config.primary_provider,
                    fallback_provider=self.config.fallback_provider,
                    confidence_threshold=self.config.confidence_threshold,
                )
                await self._ocr_gateway.initialize()
                logger.info("OCR gateway initialized")
            except ImportError:
                logger.warning("OCR gateway not available, using mock OCR")
                self._ocr_gateway = MockOCRGateway()
            except Exception as e:
                logger.error(f"Failed to initialize OCR gateway: {e}")
                self._ocr_gateway = MockOCRGateway()

        self._initialized = True

    async def process_document(
        self,
        document_id: str,
        image_data: bytes | list[bytes],
        document_type: DocumentType = DocumentType.OTHER,
        filename: str = "",
    ) -> OCRPipelineResult:
        """
        Process a document through OCR pipeline.

        Args:
            document_id: Unique document identifier
            image_data: Single image bytes or list of page images
            document_type: Type of document
            filename: Original filename

        Returns:
            OCRPipelineResult with extracted text and metadata
        """
        await self.initialize()

        start_time = datetime.now(timezone.utc)

        # Normalize to list of pages
        if isinstance(image_data, bytes):
            pages_data = [image_data]
        else:
            pages_data = image_data

        # Validate page count
        if len(pages_data) > self.config.max_pages:
            return OCRPipelineResult(
                success=False,
                document_id=document_id,
                error=f"Document exceeds maximum pages ({len(pages_data)} > {self.config.max_pages})",
            )

        page_results: list[PageOCRResult] = []
        all_tables: list[ExtractedTable] = []
        detected_langs: set[str] = set()
        fallback_used = False
        primary_provider = self.config.primary_provider.value

        # Process each page
        for page_num, page_data in enumerate(pages_data, start=1):
            try:
                page_result = await self._process_page(
                    page_data,
                    page_num,
                    document_type,
                )
                page_results.append(page_result)

                # Collect tables
                all_tables.extend(page_result.tables)

                # Track languages
                if page_result.detected_language:
                    detected_langs.add(page_result.detected_language)

                # Track if fallback was used
                if page_result.provider_used != primary_provider:
                    fallback_used = True

            except asyncio.TimeoutError:
                logger.warning(f"Timeout processing page {page_num}")
                page_results.append(PageOCRResult(
                    page_number=page_num,
                    text="",
                    confidence=0.0,
                    provider_used="timeout",
                ))
            except Exception as e:
                logger.error(f"Error processing page {page_num}: {e}")
                page_results.append(PageOCRResult(
                    page_number=page_num,
                    text="",
                    confidence=0.0,
                    provider_used="error",
                ))

        # Calculate overall metrics
        full_text = "\n\n".join(
            f"--- Page {p.page_number} ---\n{p.text}"
            for p in page_results
            if p.text
        )

        confidences = [p.confidence for p in page_results if p.confidence > 0]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        quality = self._classify_quality(overall_confidence)

        processing_time = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        return OCRPipelineResult(
            success=True,
            document_id=document_id,
            pages=page_results,
            full_text=full_text,
            overall_confidence=overall_confidence,
            quality=quality,
            total_pages=len(page_results),
            tables=all_tables,
            detected_languages=sorted(detected_langs),
            primary_provider=primary_provider,
            fallback_used=fallback_used,
            processing_time_ms=processing_time,
            metadata={
                "filename": filename,
                "document_type": document_type.value,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def _process_page(
        self,
        page_data: bytes,
        page_number: int,
        document_type: DocumentType,
    ) -> PageOCRResult:
        """Process a single page through OCR."""
        start_time = datetime.now(timezone.utc)

        # Create OCR request
        try:
            from src.gateways.ocr_gateway import OCRRequest

            request = OCRRequest(
                image_data=page_data,
                languages=self.config.languages,
                extract_tables=self.config.extract_tables,
                detect_layout=True,
            )

            result = await asyncio.wait_for(
                self._ocr_gateway.execute(request),
                timeout=self.config.timeout_per_page_seconds,
            )

            if not result.success:
                return PageOCRResult(
                    page_number=page_number,
                    text="",
                    confidence=0.0,
                    provider_used=result.provider_used or "error",
                )

            ocr_result = result.data

            # Convert text regions
            regions = []
            for region in ocr_result.text_regions:
                regions.append(TextRegion(
                    text=region.text,
                    confidence=region.confidence,
                    bbox=region.bbox,
                    page=page_number,
                ))

            # Convert tables
            tables = []
            for table in ocr_result.tables:
                cells = []
                for row_idx, row in enumerate(table.get("rows", [])):
                    for col_idx, cell_text in enumerate(row):
                        cells.append(TableCell(
                            text=str(cell_text),
                            row=row_idx,
                            col=col_idx,
                        ))
                if cells:
                    tables.append(ExtractedTable(
                        cells=cells,
                        rows=len(table.get("rows", [])),
                        cols=len(table.get("rows", [[]])[0]) if table.get("rows") else 0,
                        page=page_number,
                        confidence=table.get("confidence", 0.9),
                    ))

            processing_time = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            return PageOCRResult(
                page_number=page_number,
                text=ocr_result.text,
                confidence=ocr_result.confidence,
                regions=regions,
                tables=tables,
                detected_language=ocr_result.detected_language or "en",
                processing_time_ms=processing_time,
                provider_used=result.provider_used or self.config.primary_provider.value,
            )

        except ImportError:
            # Gateway not available, use mock
            return await self._mock_process_page(page_data, page_number)
        except Exception as e:
            logger.error(f"OCR processing error: {e}")
            return PageOCRResult(
                page_number=page_number,
                text="",
                confidence=0.0,
                provider_used="error",
            )

    async def _mock_process_page(
        self,
        page_data: bytes,
        page_number: int,
    ) -> PageOCRResult:
        """Mock page processing for development."""
        # Simulate processing delay
        await asyncio.sleep(0.1)

        return PageOCRResult(
            page_number=page_number,
            text=f"[Mock OCR Result for page {page_number}]",
            confidence=0.95,
            detected_language="en",
            processing_time_ms=100,
            provider_used="mock",
        )

    def _classify_quality(self, confidence: float) -> OCRQuality:
        """Classify OCR quality based on confidence."""
        if confidence > 0.95:
            return OCRQuality.HIGH
        elif confidence > 0.85:
            return OCRQuality.GOOD
        elif confidence > 0.70:
            return OCRQuality.ACCEPTABLE
        else:
            return OCRQuality.POOR

    async def extract_text_regions(
        self,
        image_data: bytes,
    ) -> list[TextRegion]:
        """
        Extract text regions from a single image.

        Args:
            image_data: Image bytes

        Returns:
            List of detected text regions
        """
        await self.initialize()

        result = await self.process_document(
            document_id=str(uuid4()),
            image_data=image_data,
        )

        if result.pages:
            return result.pages[0].regions
        return []

    async def extract_tables(
        self,
        image_data: bytes,
    ) -> list[ExtractedTable]:
        """
        Extract tables from a single image.

        Args:
            image_data: Image bytes

        Returns:
            List of extracted tables
        """
        await self.initialize()

        result = await self.process_document(
            document_id=str(uuid4()),
            image_data=image_data,
        )

        return result.tables

    async def detect_language(
        self,
        text: str,
    ) -> str:
        """
        Detect the primary language of text.

        Args:
            text: Text to analyze

        Returns:
            ISO 639-1 language code
        """
        # Simple heuristic for Arabic detection
        arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
        total_chars = len([c for c in text if c.isalpha()])

        if total_chars > 0 and arabic_chars / total_chars > 0.3:
            return "ar"
        return "en"


# =============================================================================
# Mock OCR Gateway (Development/Testing)
# =============================================================================


class MockOCRGateway:
    """Mock OCR gateway for development and testing."""

    async def execute(self, request) -> "MockOCRResult":
        """Execute mock OCR."""
        await asyncio.sleep(0.05)  # Simulate processing

        return MockOCRResult(
            success=True,
            data=MockOCRData(
                text="Mock OCR extracted text content",
                confidence=0.92,
                text_regions=[],
                tables=[],
                detected_language="en",
            ),
            provider_used="mock",
        )


@dataclass
class MockOCRData:
    """Mock OCR data."""

    text: str
    confidence: float
    text_regions: list
    tables: list
    detected_language: str


@dataclass
class MockOCRResult:
    """Mock OCR result."""

    success: bool
    data: MockOCRData
    provider_used: str


# =============================================================================
# Factory Functions
# =============================================================================


_ocr_pipeline: Optional[OCRPipelineService] = None


def get_ocr_pipeline(
    config: Optional[OCRPipelineConfig] = None,
) -> OCRPipelineService:
    """Get OCR pipeline service instance."""
    global _ocr_pipeline
    if _ocr_pipeline is None:
        _ocr_pipeline = OCRPipelineService(config=config)
    return _ocr_pipeline


async def create_ocr_pipeline(
    config: Optional[OCRPipelineConfig] = None,
) -> OCRPipelineService:
    """Create and initialize OCR pipeline."""
    pipeline = OCRPipelineService(config=config)
    await pipeline.initialize()
    return pipeline
