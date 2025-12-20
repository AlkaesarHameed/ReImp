"""
OCR Gateway with PaddleOCR and Azure Document Intelligence.

Provides unified OCR capabilities for medical document processing:
- Primary: PaddleOCR (open-source, multilingual)
- Fallback: Azure Document Intelligence (commercial, high accuracy)

Features:
- Multi-language support (English, Arabic)
- Table extraction
- Form field detection
- Medical document layouts
- Confidence scoring
"""

import asyncio
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor

from src.core.config import get_claims_settings
from src.core.enums import OCRProvider
from src.gateways.base import (
    BaseGateway,
    GatewayConfig,
    GatewayError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

# Import PaddleOCR with graceful fallback
try:
    from paddleocr import PaddleOCR

    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logger.warning("PaddleOCR not installed. OCR Gateway will use fallback providers.")

# Import Azure Document Intelligence with graceful fallback
try:
    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential

    AZURE_DI_AVAILABLE = True
except ImportError:
    AZURE_DI_AVAILABLE = False
    logger.warning(
        "Azure Document Intelligence SDK not installed. "
        "Azure fallback will not be available."
    )

# Import Tesseract with graceful fallback
try:
    import pytesseract
    from PIL import Image

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("Tesseract not installed. Tesseract fallback will not be available.")


@dataclass
class OCRBoundingBox:
    """Bounding box for detected text."""

    x: float
    y: float
    width: float
    height: float
    rotation: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
        }


@dataclass
class OCRTextBlock:
    """Text block detected by OCR."""

    text: str
    confidence: float
    bbox: OCRBoundingBox
    language: Optional[str] = None
    block_type: str = "text"  # text, table_cell, form_field

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bbox": self.bbox.to_dict(),
            "language": self.language,
            "block_type": self.block_type,
        }


@dataclass
class OCRTableCell:
    """Table cell with row/column information."""

    text: str
    row: int
    column: int
    row_span: int = 1
    col_span: int = 1
    confidence: float = 1.0


@dataclass
class OCRTableData:
    """Extracted table data."""

    cells: list[OCRTableCell]
    row_count: int
    column_count: int
    bbox: Optional[OCRBoundingBox] = None

    def to_dataframe_dict(self) -> dict[str, list]:
        """Convert to a dictionary suitable for pandas DataFrame."""
        # Build grid
        grid: list[list[str]] = [
            ["" for _ in range(self.column_count)] for _ in range(self.row_count)
        ]
        for cell in self.cells:
            if 0 <= cell.row < self.row_count and 0 <= cell.column < self.column_count:
                grid[cell.row][cell.column] = cell.text

        # Convert to column-based dict
        if self.row_count == 0:
            return {}

        headers = grid[0] if grid else []
        result = {h or f"col_{i}": [] for i, h in enumerate(headers)}

        for row in grid[1:]:
            for i, (header, value) in enumerate(zip(headers, row)):
                key = header or f"col_{i}"
                result[key].append(value)

        return result


@dataclass
class OCRRequest:
    """Request for OCR processing."""

    image_data: bytes
    languages: list[str] = field(default_factory=lambda: ["en"])
    detect_tables: bool = True
    detect_forms: bool = False
    dpi: int = 300
    preprocess: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_file(cls, file_path: Union[str, Path], **kwargs) -> "OCRRequest":
        """Create request from file path."""
        path = Path(file_path)
        with open(path, "rb") as f:
            image_data = f.read()
        return cls(image_data=image_data, **kwargs)


@dataclass
class OCRResponse:
    """Response from OCR processing."""

    text: str
    text_blocks: list[OCRTextBlock]
    tables: list[OCRTableData]
    confidence: float
    language_detected: Optional[str] = None
    page_count: int = 1
    provider: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Get full text from all blocks."""
        return "\n".join(block.text for block in self.text_blocks)

    def get_text_by_region(
        self, x: float, y: float, width: float, height: float
    ) -> list[OCRTextBlock]:
        """Get text blocks within a specific region."""
        results = []
        for block in self.text_blocks:
            bbox = block.bbox
            # Check if block overlaps with region
            if (
                bbox.x < x + width
                and bbox.x + bbox.width > x
                and bbox.y < y + height
                and bbox.y + bbox.height > y
            ):
                results.append(block)
        return results


class OCRGateway(BaseGateway[OCRRequest, OCRResponse, OCRProvider]):
    """
    OCR Gateway for document processing.

    Supports multiple OCR engines:
    - PaddleOCR (primary, open-source, multilingual)
    - Azure Document Intelligence (fallback, commercial)
    - Tesseract (backup fallback)
    """

    def __init__(self, config: Optional[GatewayConfig] = None):
        settings = get_claims_settings()

        if config is None:
            config = GatewayConfig(
                primary_provider=settings.OCR_PRIMARY_PROVIDER.value,
                fallback_provider=(
                    settings.OCR_FALLBACK_PROVIDER.value
                    if settings.OCR_FALLBACK_ON_ERROR
                    else None
                ),
                fallback_on_error=settings.OCR_FALLBACK_ON_ERROR,
                timeout_seconds=settings.OCR_TIMEOUT_SECONDS,
                confidence_threshold=settings.OCR_CONFIDENCE_THRESHOLD,
            )

        super().__init__(config)
        self._settings = settings
        self._paddle_ocr: Optional[Any] = None
        self._azure_client: Optional[Any] = None
        self._executor = ThreadPoolExecutor(max_workers=4)

    @property
    def gateway_name(self) -> str:
        return "OCR"

    async def _initialize_provider(self, provider: OCRProvider) -> None:
        """Initialize OCR provider."""
        if provider == OCRProvider.PADDLEOCR:
            if not PADDLEOCR_AVAILABLE:
                raise ProviderUnavailableError(
                    "PaddleOCR is not installed", provider=provider.value
                )
            # Initialize PaddleOCR in thread pool (CPU-bound)
            loop = asyncio.get_event_loop()
            self._paddle_ocr = await loop.run_in_executor(
                self._executor, self._create_paddle_ocr
            )
            logger.info("PaddleOCR initialized")

        elif provider == OCRProvider.AZURE_DI:
            if not AZURE_DI_AVAILABLE:
                raise ProviderUnavailableError(
                    "Azure Document Intelligence SDK not installed",
                    provider=provider.value,
                )
            if not self._settings.AZURE_DI_ENDPOINT or not self._settings.AZURE_DI_KEY:
                raise ProviderUnavailableError(
                    "Azure Document Intelligence credentials not configured",
                    provider=provider.value,
                )
            self._azure_client = DocumentAnalysisClient(
                endpoint=self._settings.AZURE_DI_ENDPOINT,
                credential=AzureKeyCredential(self._settings.AZURE_DI_KEY),
            )
            logger.info("Azure Document Intelligence initialized")

        elif provider == OCRProvider.TESSERACT:
            if not TESSERACT_AVAILABLE:
                raise ProviderUnavailableError(
                    "Tesseract/pytesseract is not installed", provider=provider.value
                )
            logger.info("Tesseract initialized")

    def _create_paddle_ocr(self) -> Any:
        """Create PaddleOCR instance (runs in thread pool)."""
        languages = self._settings.paddleocr_languages_list
        # Map language codes to PaddleOCR format
        lang_map = {"en": "en", "ar": "ar", "zh": "ch", "es": "es", "fr": "french"}
        paddle_langs = [lang_map.get(lang, lang) for lang in languages]

        return PaddleOCR(
            use_angle_cls=True,
            lang=paddle_langs[0] if paddle_langs else "en",
            show_log=False,
            use_gpu=self._settings.PADDLEOCR_USE_GPU,
        )

    async def _execute_request(
        self, request: OCRRequest, provider: OCRProvider
    ) -> OCRResponse:
        """Execute OCR request using specified provider."""
        if provider == OCRProvider.PADDLEOCR:
            return await self._execute_paddleocr(request)
        elif provider == OCRProvider.AZURE_DI:
            return await self._execute_azure_di(request)
        elif provider == OCRProvider.TESSERACT:
            return await self._execute_tesseract(request)
        else:
            raise GatewayError(f"Unsupported OCR provider: {provider}")

    async def _execute_paddleocr(self, request: OCRRequest) -> OCRResponse:
        """Execute OCR using PaddleOCR."""
        if not self._paddle_ocr:
            raise ProviderUnavailableError(
                "PaddleOCR not initialized", provider="paddleocr"
            )

        loop = asyncio.get_event_loop()

        def run_ocr():
            # Convert bytes to numpy array
            import numpy as np
            from PIL import Image

            image = Image.open(io.BytesIO(request.image_data))
            img_array = np.array(image)

            # Run OCR
            results = self._paddle_ocr.ocr(img_array, cls=True)
            return results

        results = await loop.run_in_executor(self._executor, run_ocr)

        # Parse PaddleOCR results
        text_blocks: list[OCRTextBlock] = []
        all_text_parts: list[str] = []
        total_confidence = 0.0
        block_count = 0

        if results and results[0]:
            for line in results[0]:
                if len(line) >= 2:
                    bbox_points = line[0]
                    text_info = line[1]

                    text = text_info[0] if isinstance(text_info, tuple) else str(text_info)
                    confidence = text_info[1] if isinstance(text_info, tuple) and len(text_info) > 1 else 0.9

                    # Convert polygon to bounding box
                    x_coords = [p[0] for p in bbox_points]
                    y_coords = [p[1] for p in bbox_points]
                    bbox = OCRBoundingBox(
                        x=min(x_coords),
                        y=min(y_coords),
                        width=max(x_coords) - min(x_coords),
                        height=max(y_coords) - min(y_coords),
                    )

                    text_blocks.append(
                        OCRTextBlock(
                            text=text,
                            confidence=confidence,
                            bbox=bbox,
                        )
                    )
                    all_text_parts.append(text)
                    total_confidence += confidence
                    block_count += 1

        avg_confidence = total_confidence / block_count if block_count > 0 else 0.0

        return OCRResponse(
            text="\n".join(all_text_parts),
            text_blocks=text_blocks,
            tables=[],  # PaddleOCR table extraction requires separate processing
            confidence=avg_confidence,
            provider="paddleocr",
        )

    async def _execute_azure_di(self, request: OCRRequest) -> OCRResponse:
        """Execute OCR using Azure Document Intelligence."""
        if not self._azure_client:
            raise ProviderUnavailableError(
                "Azure DI not initialized", provider="azure_di"
            )

        # Use prebuilt-read model for general OCR
        model_id = "prebuilt-read"
        if request.detect_forms:
            model_id = "prebuilt-document"

        loop = asyncio.get_event_loop()

        def run_azure_ocr():
            poller = self._azure_client.begin_analyze_document(
                model_id,
                document=io.BytesIO(request.image_data),
            )
            return poller.result()

        result = await loop.run_in_executor(self._executor, run_azure_ocr)

        # Parse Azure DI results
        text_blocks: list[OCRTextBlock] = []
        tables: list[OCRTableData] = []
        all_text_parts: list[str] = []
        total_confidence = 0.0
        block_count = 0

        # Process paragraphs/lines
        for page in result.pages:
            for line in page.lines:
                # Get bounding polygon
                polygon = line.polygon
                if polygon and len(polygon) >= 4:
                    x_coords = [p.x for p in polygon]
                    y_coords = [p.y for p in polygon]
                    bbox = OCRBoundingBox(
                        x=min(x_coords),
                        y=min(y_coords),
                        width=max(x_coords) - min(x_coords),
                        height=max(y_coords) - min(y_coords),
                    )
                else:
                    bbox = OCRBoundingBox(x=0, y=0, width=0, height=0)

                # Get confidence from words
                word_confidences = [
                    w.confidence for w in line.words if w.confidence is not None
                ]
                confidence = (
                    sum(word_confidences) / len(word_confidences)
                    if word_confidences
                    else 0.9
                )

                text_blocks.append(
                    OCRTextBlock(
                        text=line.content,
                        confidence=confidence,
                        bbox=bbox,
                    )
                )
                all_text_parts.append(line.content)
                total_confidence += confidence
                block_count += 1

        # Process tables
        if hasattr(result, "tables"):
            for table in result.tables:
                cells = []
                for cell in table.cells:
                    cells.append(
                        OCRTableCell(
                            text=cell.content,
                            row=cell.row_index,
                            column=cell.column_index,
                            row_span=cell.row_span or 1,
                            col_span=cell.column_span or 1,
                            confidence=cell.confidence or 0.9,
                        )
                    )
                tables.append(
                    OCRTableData(
                        cells=cells,
                        row_count=table.row_count,
                        column_count=table.column_count,
                    )
                )

        avg_confidence = total_confidence / block_count if block_count > 0 else 0.0

        return OCRResponse(
            text="\n".join(all_text_parts),
            text_blocks=text_blocks,
            tables=tables,
            confidence=avg_confidence,
            page_count=len(result.pages),
            provider="azure_di",
            language_detected=result.languages[0] if result.languages else None,
        )

    async def _execute_tesseract(self, request: OCRRequest) -> OCRResponse:
        """Execute OCR using Tesseract."""
        if not TESSERACT_AVAILABLE:
            raise ProviderUnavailableError(
                "Tesseract not available", provider="tesseract"
            )

        loop = asyncio.get_event_loop()

        def run_tesseract():
            image = Image.open(io.BytesIO(request.image_data))

            # Get detailed data with bounding boxes
            lang_str = "+".join(request.languages)
            data = pytesseract.image_to_data(
                image, lang=lang_str, output_type=pytesseract.Output.DICT
            )
            return data, image.size

        data, image_size = await loop.run_in_executor(self._executor, run_tesseract)

        # Parse Tesseract results
        text_blocks: list[OCRTextBlock] = []
        all_text_parts: list[str] = []
        total_confidence = 0.0
        block_count = 0

        n_boxes = len(data["text"])
        for i in range(n_boxes):
            text = data["text"][i].strip()
            if not text:
                continue

            conf = float(data["conf"][i])
            if conf < 0:
                conf = 0.0
            else:
                conf = conf / 100.0  # Convert to 0-1 scale

            bbox = OCRBoundingBox(
                x=float(data["left"][i]),
                y=float(data["top"][i]),
                width=float(data["width"][i]),
                height=float(data["height"][i]),
            )

            text_blocks.append(
                OCRTextBlock(
                    text=text,
                    confidence=conf,
                    bbox=bbox,
                )
            )
            all_text_parts.append(text)
            total_confidence += conf
            block_count += 1

        avg_confidence = total_confidence / block_count if block_count > 0 else 0.0

        return OCRResponse(
            text=" ".join(all_text_parts),
            text_blocks=text_blocks,
            tables=[],
            confidence=avg_confidence,
            provider="tesseract",
        )

    async def _health_check(self, provider: OCRProvider) -> bool:
        """Check if OCR provider is healthy."""
        # Create a simple test image (1x1 white pixel)
        test_image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7V\x7f\x00\x00\x00\x00IEND\xaeB`\x82"

        try:
            request = OCRRequest(image_data=test_image, languages=["en"])
            await self._execute_request(request, provider)
            return True
        except Exception as e:
            logger.warning(f"OCR health check failed for {provider.value}: {e}")
            return False

    def _parse_provider(self, provider_str: str) -> OCRProvider:
        """Parse provider string to OCRProvider enum."""
        return OCRProvider(provider_str)

    async def close(self) -> None:
        """Clean up OCR gateway resources."""
        self._executor.shutdown(wait=False)
        if self._azure_client:
            self._azure_client.close()
        await super().close()


# Singleton instance
_ocr_gateway: Optional[OCRGateway] = None


def get_ocr_gateway() -> OCRGateway:
    """Get or create the singleton OCR gateway instance."""
    global _ocr_gateway
    if _ocr_gateway is None:
        _ocr_gateway = OCRGateway()
    return _ocr_gateway


async def reset_ocr_gateway() -> None:
    """Reset the OCR gateway (for testing)."""
    global _ocr_gateway
    if _ocr_gateway:
        await _ocr_gateway.close()
    _ocr_gateway = None
