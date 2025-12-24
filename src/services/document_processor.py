"""
Document Processing Orchestrator.

Coordinates the full document processing pipeline:
1. Upload and storage (MinIO)
2. OCR text extraction
3. LLM-based data parsing
4. Database persistence

Source: Design Document Section 4.3 - Document Processing
Verified: 2025-12-18
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import BinaryIO, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import DocumentStatus, DocumentType

logger = logging.getLogger(__name__)


# =============================================================================
# WebSocket Integration
# =============================================================================


async def _notify_websocket_progress(
    document_id: str,
    stage: str,
    progress_percent: int,
    message: str = "",
    ocr_confidence: Optional[float] = None,
    parsing_confidence: Optional[float] = None,
) -> None:
    """
    Send progress update via WebSocket if manager is available.

    This is a best-effort notification - failures are logged but don't
    interrupt document processing.
    """
    try:
        from src.api.websocket import get_websocket_manager

        manager = get_websocket_manager()
        await manager.send_progress(
            document_id=document_id,
            stage=stage,
            progress_percent=progress_percent,
            message=message,
            ocr_confidence=ocr_confidence,
            parsing_confidence=parsing_confidence,
        )
    except Exception as e:
        # WebSocket notification is non-critical
        logger.debug(f"WebSocket notification failed (non-critical): {e}")


class ProcessingStage(str, Enum):
    """Document processing stages."""

    UPLOAD = "upload"
    OCR = "ocr"
    PARSING = "parsing"
    VALIDATION = "validation"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ProcessingProgress:
    """Progress tracking for document processing."""

    document_id: str
    stage: ProcessingStage
    progress_percent: int = 0
    message: str = ""
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class DocumentProcessingResult:
    """Complete document processing result."""

    success: bool
    document_id: str
    claim_id: Optional[str] = None

    # Storage info
    storage_path: str = ""
    storage_bucket: str = ""
    storage_document_id: str = ""  # Document ID from storage service
    file_hash: str = ""
    file_size: int = 0
    content_type: str = ""

    # OCR results
    ocr_text: str = ""
    ocr_confidence: float = 0.0
    ocr_quality: str = ""
    detected_languages: list[str] = field(default_factory=list)
    tables_extracted: int = 0

    # Parsing results
    extracted_data: Optional[dict] = None
    parsing_confidence: float = 0.0
    fields_extracted: int = 0
    fields_needs_review: int = 0

    # Processing metrics
    processing_stage: ProcessingStage = ProcessingStage.UPLOAD
    total_processing_time_ms: int = 0
    ocr_time_ms: int = 0
    parsing_time_ms: int = 0
    providers_used: dict = field(default_factory=dict)

    # Errors
    error: Optional[str] = None
    error_stage: Optional[ProcessingStage] = None

    # Flags
    is_duplicate: bool = False
    needs_review: bool = False


@dataclass
class ProcessorConfig:
    """Document processor configuration."""

    # Processing options
    skip_ocr_for_pdf_text: bool = True
    extract_tables: bool = True
    extract_medical_codes: bool = True
    validate_extracted_data: bool = True

    # Thresholds
    min_ocr_confidence: float = 0.70
    min_parsing_confidence: float = 0.70
    auto_flag_low_confidence: bool = True

    # Timeouts
    upload_timeout_seconds: int = 60
    ocr_timeout_seconds: int = 120
    parsing_timeout_seconds: int = 300  # Increased to 5 minutes for vision model processing

    # Concurrency
    max_concurrent_pages: int = 5


# =============================================================================
# Document Processor
# =============================================================================


class DocumentProcessor:
    """
    Orchestrates complete document processing pipeline.

    Coordinates:
    - Document storage (MinIO)
    - OCR processing
    - LLM-based parsing
    - Data validation
    - Database persistence
    """

    def __init__(
        self,
        config: Optional[ProcessorConfig] = None,
        storage_service=None,
        ocr_pipeline=None,
        llm_parser=None,
    ):
        """
        Initialize document processor.

        Args:
            config: Processor configuration
            storage_service: Document storage service
            ocr_pipeline: OCR processing pipeline
            llm_parser: LLM parsing service
        """
        self.config = config or ProcessorConfig()
        self._storage = storage_service
        self._ocr = ocr_pipeline
        self._parser = llm_parser
        self._initialized = False
        self._progress_callbacks: dict[str, callable] = {}

    async def initialize(self) -> None:
        """Initialize all component services."""
        if self._initialized:
            return

        # Initialize storage service
        if self._storage is None:
            from src.services.document_storage import DocumentStorageService

            # Create fresh instance to ensure latest config is used
            self._storage = DocumentStorageService()
            await self._storage.initialize()
            logger.info("Document storage initialized")

        # Initialize OCR pipeline
        if self._ocr is None:
            from src.services.ocr_pipeline import OCRPipelineService

            self._ocr = OCRPipelineService()
            await self._ocr.initialize()
            logger.info("OCR pipeline initialized")

        # Initialize LLM parser
        if self._parser is None:
            from src.services.llm_parser import LLMParserService

            self._parser = LLMParserService()
            await self._parser.initialize()
            logger.info("LLM parser initialized")

        self._initialized = True

    def register_progress_callback(
        self,
        document_id: str,
        callback: callable,
    ) -> None:
        """Register callback for processing progress updates."""
        self._progress_callbacks[document_id] = callback

    def unregister_progress_callback(self, document_id: str) -> None:
        """Unregister progress callback."""
        self._progress_callbacks.pop(document_id, None)

    async def _update_progress(
        self,
        document_id: str,
        stage: ProcessingStage,
        progress: int,
        message: str,
        ocr_confidence: Optional[float] = None,
        parsing_confidence: Optional[float] = None,
    ) -> None:
        """Update processing progress via callback and WebSocket."""
        # Update via callback (for background task status tracking)
        callback = self._progress_callbacks.get(document_id)
        if callback:
            try:
                progress_info = ProcessingProgress(
                    document_id=document_id,
                    stage=stage,
                    progress_percent=progress,
                    message=message,
                    updated_at=datetime.now(timezone.utc),
                )
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress_info)
                else:
                    callback(progress_info)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

        # Also notify via WebSocket for real-time UI updates
        await _notify_websocket_progress(
            document_id=document_id,
            stage=stage.value,
            progress_percent=progress,
            message=message,
            ocr_confidence=ocr_confidence,
            parsing_confidence=parsing_confidence,
        )

    async def process_document(
        self,
        tenant_id: str,
        claim_id: Optional[str],
        document_type: DocumentType,
        filename: str,
        file_data: BinaryIO | bytes,
        content_type: str,
        existing_hashes: Optional[set[str]] = None,
        document_id: Optional[str] = None,
    ) -> DocumentProcessingResult:
        """
        Process a document through the complete pipeline.

        Args:
            tenant_id: Tenant ID for isolation
            claim_id: Associated claim ID (optional)
            document_type: Type of document
            filename: Original filename
            file_data: File content
            content_type: MIME type
            existing_hashes: Set of existing file hashes for dedup
            document_id: Optional externally-provided document ID

        Returns:
            DocumentProcessingResult with all processing data
        """
        await self.initialize()

        document_id = document_id or str(uuid4())
        start_time = datetime.now(timezone.utc)
        result = DocumentProcessingResult(
            success=False,
            document_id=document_id,
            claim_id=claim_id,
        )

        try:
            # Stage 1: Upload to storage
            await self._update_progress(
                document_id, ProcessingStage.UPLOAD, 10, "Uploading document..."
            )

            upload_result = await asyncio.wait_for(
                self._storage.upload_document(
                    tenant_id=tenant_id,
                    document_type=document_type,
                    filename=filename,
                    data=file_data,
                    content_type=content_type,
                    existing_hashes=existing_hashes,
                ),
                timeout=self.config.upload_timeout_seconds,
            )

            if not upload_result.success:
                result.error = upload_result.error
                result.error_stage = ProcessingStage.UPLOAD
                return result

            if upload_result.is_duplicate:
                result.is_duplicate = True
                result.file_hash = upload_result.file_hash
                result.success = True
                result.processing_stage = ProcessingStage.COMPLETE
                return result

            # Keep the original document_id, but store the storage-generated one for reference
            result.storage_document_id = upload_result.document_id
            result.storage_path = upload_result.storage_path
            result.storage_bucket = upload_result.storage_bucket
            result.file_hash = upload_result.file_hash
            result.file_size = upload_result.file_size
            result.content_type = upload_result.content_type

            await self._update_progress(
                document_id, ProcessingStage.UPLOAD, 25, "Upload complete"
            )

            # Stage 2: OCR Processing
            await self._update_progress(
                document_id, ProcessingStage.OCR, 30, "Extracting text..."
            )

            # Get the file data for OCR
            if hasattr(file_data, "read"):
                file_data.seek(0)
                raw_bytes = file_data.read()
            else:
                raw_bytes = file_data

            # Convert PDF to images if necessary
            # Source: Design Doc 08 Section 14 - PDF-to-Image Conversion Fix
            # Verified: 2025-12-21
            if content_type == "application/pdf":
                await self._update_progress(
                    document_id, ProcessingStage.OCR, 35, "Converting PDF to images..."
                )
                image_bytes = await self._convert_pdf_to_images(raw_bytes)
                logger.info(f"Converted PDF to {len(image_bytes)} page images for OCR")
            else:
                image_bytes = raw_bytes

            ocr_result = await asyncio.wait_for(
                self._ocr.process_document(
                    document_id=result.document_id,
                    image_data=image_bytes,
                    document_type=document_type,
                    filename=filename,
                ),
                timeout=self.config.ocr_timeout_seconds,
            )

            if not ocr_result.success:
                result.error = ocr_result.error or "OCR processing failed"
                result.error_stage = ProcessingStage.OCR
                result.processing_stage = ProcessingStage.FAILED
                return result

            result.ocr_text = ocr_result.full_text
            result.ocr_confidence = ocr_result.overall_confidence
            result.ocr_quality = ocr_result.quality.value
            result.detected_languages = ocr_result.detected_languages
            result.tables_extracted = len(ocr_result.tables)
            result.ocr_time_ms = ocr_result.processing_time_ms
            result.providers_used["ocr"] = ocr_result.primary_provider

            await self._update_progress(
                document_id, ProcessingStage.OCR, 60, "Text extraction complete"
            )

            # Check OCR confidence
            if ocr_result.overall_confidence < self.config.min_ocr_confidence:
                if self.config.auto_flag_low_confidence:
                    result.needs_review = True
                logger.warning(
                    f"Low OCR confidence ({ocr_result.overall_confidence:.2f}) for {document_id}"
                )

            # Stage 3: LLM Parsing
            await self._update_progress(
                document_id, ProcessingStage.PARSING, 65, "Parsing document data..."
            )

            # Convert tables to dict format
            tables_data = [
                table.to_dict() for table in ocr_result.tables
            ]

            # Pass image data to LLM for vision-based parsing
            # For PDFs, image_bytes is a list of page images - use first page
            # For images, image_bytes is the raw bytes
            if content_type == "application/pdf" and isinstance(image_bytes, list):
                # Use first page image for vision parsing
                parser_image_data = image_bytes[0] if image_bytes else None
            elif content_type.startswith("image/"):
                parser_image_data = image_bytes
            else:
                parser_image_data = None

            parsing_result = await asyncio.wait_for(
                self._parser.parse_claim_document(
                    ocr_text=ocr_result.full_text,
                    document_type=document_type,
                    tables=tables_data,
                    image_data=parser_image_data,
                ),
                timeout=self.config.parsing_timeout_seconds,
            )

            if not parsing_result.success:
                # Parsing failure is not fatal - we still have OCR text
                logger.warning(f"Parsing failed for {document_id}: {parsing_result.error}")
                result.needs_review = True
            else:
                result.parsing_confidence = parsing_result.overall_confidence
                result.fields_extracted = parsing_result.fields_extracted
                result.fields_needs_review = parsing_result.fields_needs_review
                result.parsing_time_ms = parsing_result.processing_time_ms
                result.providers_used["llm"] = parsing_result.provider_used

                # Build extracted data dict
                result.extracted_data = self._build_extracted_data(parsing_result)

                # Check parsing confidence
                if parsing_result.overall_confidence < self.config.min_parsing_confidence:
                    if self.config.auto_flag_low_confidence:
                        result.needs_review = True

            await self._update_progress(
                document_id, ProcessingStage.PARSING, 90, "Parsing complete"
            )

            # Stage 4: Validation
            if self.config.validate_extracted_data and result.extracted_data:
                await self._update_progress(
                    document_id, ProcessingStage.VALIDATION, 95, "Validating data..."
                )

                validation_issues = await self._validate_extracted_data(
                    result.extracted_data,
                    document_type,
                )
                if validation_issues:
                    result.needs_review = True
                    if "validation_issues" not in result.extracted_data:
                        result.extracted_data["validation_issues"] = []
                    result.extracted_data["validation_issues"].extend(validation_issues)

            # Complete
            result.success = True
            result.processing_stage = ProcessingStage.COMPLETE
            result.total_processing_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            await self._update_progress(
                document_id, ProcessingStage.COMPLETE, 100, "Processing complete"
            )

            return result

        except asyncio.TimeoutError as e:
            result.error = f"Processing timeout: {str(e)}"
            result.processing_stage = ProcessingStage.FAILED
            logger.error(f"Document processing timeout: {document_id}")
            return result

        except Exception as e:
            result.error = str(e)
            result.processing_stage = ProcessingStage.FAILED
            logger.error(f"Document processing error: {e}", exc_info=True)
            return result

        finally:
            self.unregister_progress_callback(document_id)

    def _build_extracted_data(self, parsing_result) -> dict:
        """Build extracted data dictionary from parsing result."""
        data = {}

        if parsing_result.patient:
            data["patient"] = {
                "name": parsing_result.patient.name,
                "member_id": parsing_result.patient.member_id,
                "date_of_birth": (
                    parsing_result.patient.date_of_birth.isoformat()
                    if parsing_result.patient.date_of_birth
                    else None
                ),
                "gender": parsing_result.patient.gender,
                "address": parsing_result.patient.address,
            }

        if parsing_result.provider:
            data["provider"] = {
                "name": parsing_result.provider.name,
                "npi": parsing_result.provider.npi,
                "tax_id": parsing_result.provider.tax_id,
                "specialty": parsing_result.provider.specialty,
            }

        data["diagnoses"] = [
            {
                "code": dx.code,
                "description": dx.description,
                "is_primary": dx.is_primary,
                "confidence": dx.confidence,
            }
            for dx in parsing_result.diagnoses
        ]

        # Separate procedures into real CPT procedures vs invoice line items
        real_procedures = []
        converted_line_items = []

        for proc in parsing_result.procedures:
            code = proc.code
            # Check if this is a real CPT code (5 digits) or HCPCS (5 chars, starts with letter)
            is_cpt_code = code and len(str(code)) == 5 and str(code).isdigit()
            is_hcpcs_code = code and len(str(code)) == 5 and str(code)[0].isalpha()

            if is_cpt_code or is_hcpcs_code:
                real_procedures.append({
                    "code": proc.code,
                    "description": proc.description,
                    "modifiers": proc.modifiers,
                    "quantity": proc.quantity,
                    "charged_amount": str(proc.charged_amount) if proc.charged_amount else None,
                    "service_date": proc.service_date.isoformat() if proc.service_date else None,
                    "confidence": proc.confidence,
                })
            else:
                # Convert to line item format
                converted_line_items.append({
                    "sl_no": len(converted_line_items) + 1,
                    "date": proc.service_date.isoformat() if proc.service_date else None,
                    "description": proc.description,
                    "sac_code": str(code) if code else "",
                    "quantity": proc.quantity,
                    "rate": None,
                    "gross_value": str(proc.charged_amount) if proc.charged_amount else None,
                    "discount": None,
                    "total_value": str(proc.charged_amount) if proc.charged_amount else None,
                    "category": "",
                    "confidence": proc.confidence,
                })

        data["procedures"] = real_procedures
        logger.info(f"Separated {len(real_procedures)} real procedures and {len(converted_line_items)} line items from procedures array")

        # Extract line items (for invoices with itemized charges)
        # Start with converted line items from procedures
        data["line_items"] = converted_line_items.copy()

        # Then add explicitly returned line items from the parser
        if hasattr(parsing_result, 'line_items') and parsing_result.line_items:
            explicit_line_items = [
                {
                    "sl_no": item.sl_no + len(data["line_items"]),  # Adjust serial number
                    "date": item.date.isoformat() if item.date else None,
                    "description": item.description,
                    "sac_code": item.sac_code,
                    "quantity": item.quantity,
                    "rate": str(item.rate) if item.rate else None,
                    "gross_value": str(item.gross_value) if item.gross_value else None,
                    "discount": str(item.discount) if item.discount else None,
                    "total_value": str(item.total_value) if item.total_value else None,
                    "category": item.category,
                    "confidence": item.confidence,
                }
                for item in parsing_result.line_items
            ]
            data["line_items"].extend(explicit_line_items)
            logger.info(f"Added {len(parsing_result.line_items)} explicit line items from document")

        logger.info(f"Total line items: {len(data['line_items'])}")

        if parsing_result.total_charged:
            data["financial"] = {
                "total_charged": str(parsing_result.total_charged),
                "currency": parsing_result.currency,
            }

        data["dates"] = {
            "service_date_from": (
                parsing_result.service_date_from.isoformat()
                if parsing_result.service_date_from
                else None
            ),
            "service_date_to": (
                parsing_result.service_date_to.isoformat()
                if parsing_result.service_date_to
                else None
            ),
        }

        data["identifiers"] = {
            "claim_number": parsing_result.claim_number,
            "prior_auth_number": parsing_result.prior_auth_number,
            "policy_number": parsing_result.policy_number,
        }

        data["claim_type"] = (
            parsing_result.claim_type.value if parsing_result.claim_type else None
        )
        data["overall_confidence"] = parsing_result.overall_confidence

        return data

    async def _validate_extracted_data(
        self,
        data: dict,
        document_type: DocumentType,
    ) -> list[str]:
        """Validate extracted data for completeness and consistency."""
        issues = []

        # Check required fields based on document type
        if document_type in (DocumentType.CLAIM_FORM, DocumentType.INVOICE):
            # Check patient info
            patient = data.get("patient", {})
            if not patient.get("name"):
                issues.append("Missing patient name")
            if not patient.get("member_id"):
                issues.append("Missing patient member ID")

            # Check provider info
            provider = data.get("provider", {})
            if not provider.get("name"):
                issues.append("Missing provider name")
            if not provider.get("npi"):
                issues.append("Missing provider NPI")

            # Check diagnoses
            diagnoses = data.get("diagnoses", [])
            if not diagnoses:
                issues.append("No diagnosis codes found")

            # Check procedures
            procedures = data.get("procedures", [])
            if not procedures:
                issues.append("No procedure codes found")

            # Check financial
            financial = data.get("financial", {})
            if not financial.get("total_charged"):
                issues.append("Missing total charged amount")

            # Check service dates
            dates = data.get("dates", {})
            if not dates.get("service_date_from"):
                issues.append("Missing service date")

        return issues

    async def _convert_pdf_to_images(
        self,
        pdf_bytes: bytes,
        dpi: int = 300,
    ) -> list[bytes]:
        """
        Convert PDF pages to PNG images for OCR processing.

        Supports partial success - continues processing remaining pages if
        individual pages fail to convert. This ensures we get as much data
        as possible from documents with corrupted or complex pages.

        Args:
            pdf_bytes: Raw PDF file bytes
            dpi: Resolution for rendering (default 300 for good OCR quality)

        Returns:
            List of PNG image bytes for successfully converted pages

        Raises:
            ImportError: If PyMuPDF is not installed
            ValueError: If no pages could be converted at all

        Source: Design Doc 08 Section 14 - PDF-to-Image Conversion Fix
        Evidence: PyMuPDF (fitz) is the standard library for PDF rendering
        https://pymupdf.readthedocs.io/en/latest/
        Verified: 2025-12-21
        """
        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            logger.error("PyMuPDF (fitz) not installed. Run: pip install pymupdf")
            raise ImportError(
                "PyMuPDF is required for PDF processing. Install with: pip install pymupdf"
            ) from e

        images: list[bytes] = []
        failed_pages: list[tuple[int, str]] = []
        doc = None

        try:
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = len(doc)

            if total_pages == 0:
                raise ValueError("PDF contains no pages")

            # Calculate zoom factor for desired DPI (PDF default is 72 DPI)
            zoom = dpi / 72

            for page_num in range(total_pages):
                try:
                    page = doc.load_page(page_num)

                    # Create transformation matrix for desired resolution
                    mat = fitz.Matrix(zoom, zoom)

                    # Render page to pixmap (image)
                    pix = page.get_pixmap(matrix=mat)

                    # Convert to PNG bytes
                    png_bytes = pix.tobytes("png")
                    images.append(png_bytes)

                    logger.debug(
                        f"Converted PDF page {page_num + 1}/{total_pages} to PNG "
                        f"({pix.width}x{pix.height} @ {dpi} DPI)"
                    )

                except Exception as page_error:
                    # Log the error but continue with other pages
                    error_msg = str(page_error)
                    failed_pages.append((page_num + 1, error_msg))
                    logger.warning(
                        f"Failed to convert PDF page {page_num + 1}/{total_pages}: {error_msg}"
                    )

            # Check if we got any images at all
            if not images:
                error_details = "; ".join(
                    f"page {p}: {e}" for p, e in failed_pages
                )
                raise ValueError(
                    f"PDF conversion failed - no pages could be converted. "
                    f"Errors: {error_details}"
                )

            # Log summary
            if failed_pages:
                failed_nums = [str(p) for p, _ in failed_pages]
                logger.warning(
                    f"PDF conversion completed with {len(failed_pages)} failed pages "
                    f"({', '.join(failed_nums)}) out of {total_pages} total. "
                    f"Successfully converted {len(images)} pages."
                )
            else:
                logger.info(
                    f"Successfully converted all {len(images)} PDF pages to images"
                )

            return images

        except ValueError:
            # Re-raise ValueError (our custom errors) as-is
            raise

        except Exception as e:
            logger.error(f"Failed to open or process PDF: {e}")
            raise ValueError(f"PDF conversion failed: {e}") from e

        finally:
            if doc:
                try:
                    doc.close()
                except Exception:
                    pass  # Ignore close errors

    async def reprocess_document(
        self,
        tenant_id: str,
        document_id: str,
        storage_bucket: str,
        storage_path: str,
        document_type: DocumentType,
    ) -> DocumentProcessingResult:
        """
        Reprocess an existing document.

        Useful when OCR or parsing fails and needs retry.
        """
        await self.initialize()

        # Download document
        download_result = await self._storage.download_document(
            bucket=storage_bucket,
            storage_path=storage_path,
        )

        if not download_result.success:
            return DocumentProcessingResult(
                success=False,
                document_id=document_id,
                error=download_result.error,
                error_stage=ProcessingStage.UPLOAD,
            )

        # Process without re-uploading
        return await self._process_existing_document(
            document_id=document_id,
            document_type=document_type,
            file_data=download_result.data,
            content_type=download_result.content_type,
        )

    async def _process_existing_document(
        self,
        document_id: str,
        document_type: DocumentType,
        file_data: bytes,
        content_type: str,
    ) -> DocumentProcessingResult:
        """Process an existing document (OCR + parsing only)."""
        result = DocumentProcessingResult(
            success=False,
            document_id=document_id,
        )

        start_time = datetime.now(timezone.utc)

        try:
            # OCR
            ocr_result = await self._ocr.process_document(
                document_id=document_id,
                image_data=file_data,
                document_type=document_type,
            )

            if not ocr_result.success:
                result.error = ocr_result.error
                result.error_stage = ProcessingStage.OCR
                return result

            result.ocr_text = ocr_result.full_text
            result.ocr_confidence = ocr_result.overall_confidence
            result.ocr_time_ms = ocr_result.processing_time_ms

            # Parsing
            parsing_result = await self._parser.parse_claim_document(
                ocr_text=ocr_result.full_text,
                document_type=document_type,
            )

            if parsing_result.success:
                result.parsing_confidence = parsing_result.overall_confidence
                result.extracted_data = self._build_extracted_data(parsing_result)
                result.parsing_time_ms = parsing_result.processing_time_ms

            result.success = True
            result.processing_stage = ProcessingStage.COMPLETE
            result.total_processing_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            return result

        except Exception as e:
            result.error = str(e)
            result.processing_stage = ProcessingStage.FAILED
            return result


# =============================================================================
# Database Persistence
# =============================================================================


async def persist_document_result(
    session: AsyncSession,
    claim_id: str,
    result: DocumentProcessingResult,
    tenant_id: Optional[str] = None,
) -> str:
    """
    Persist document processing result to database.

    Creates:
    - ClaimDocument record with extracted_data JSONB (backward compatibility)
    - Person record with structured demographics
    - AssociatedData records for diagnoses, procedures, etc.

    Args:
        session: Database session
        claim_id: Associated claim ID
        result: Processing result
        tenant_id: Tenant ID for Person records

    Returns:
        Document ID

    Source: Design Document 07-document-extraction-system-design.md Section 3.4
    Verified: 2025-12-20
    """
    from uuid import UUID as UUIDType

    from src.models.claim import ClaimDocument

    # Create ClaimDocument (with JSONB for backward compatibility)
    document = ClaimDocument(
        id=result.document_id,
        claim_id=claim_id,
        document_type=result.extracted_data.get("claim_type", "other") if result.extracted_data else "other",
        filename=result.storage_path.split("/")[-1] if result.storage_path else "document",
        content_type=result.content_type,
        file_size=result.file_size,
        storage_path=result.storage_path,
        storage_bucket=result.storage_bucket,
        file_hash=result.file_hash,
        processed=result.success,
        ocr_text=result.ocr_text,
        ocr_confidence=Decimal(str(round(result.ocr_confidence, 3))) if result.ocr_confidence else None,
        extracted_data=result.extracted_data,
    )

    session.add(document)
    await session.flush()

    # Create Person and AssociatedData records if we have tenant_id and extracted data
    if tenant_id and result.extracted_data and result.success:
        try:
            from src.models.person import (
                create_associated_data_from_extracted,
                create_person_from_extracted_data,
            )

            # Parse UUIDs
            doc_uuid = UUIDType(result.document_id) if isinstance(result.document_id, str) else result.document_id
            tenant_uuid = UUIDType(tenant_id) if isinstance(tenant_id, str) else tenant_id

            # Create Person record
            person = create_person_from_extracted_data(
                document_id=doc_uuid,
                tenant_id=tenant_uuid,
                extracted_data=result.extracted_data,
                confidence_scores=None,  # Could be populated from result
            )
            session.add(person)
            await session.flush()  # Get person.id

            # Create AssociatedData records
            associated_records = create_associated_data_from_extracted(
                person_id=person.id,
                document_id=doc_uuid,
                tenant_id=tenant_uuid,
                extracted_data=result.extracted_data,
            )
            for record in associated_records:
                session.add(record)

            logger.info(
                f"Created Person and {len(associated_records)} AssociatedData records "
                f"for document {result.document_id}"
            )

        except Exception as e:
            # Person creation is non-critical - JSONB data is still saved
            logger.warning(f"Failed to create Person records (non-critical): {e}")

    return result.document_id


# =============================================================================
# Factory Functions
# =============================================================================


_document_processor: Optional[DocumentProcessor] = None


def get_document_processor(
    config: Optional[ProcessorConfig] = None,
) -> DocumentProcessor:
    """Get document processor instance."""
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor(config=config)
    return _document_processor


def reset_document_processor() -> None:
    """Reset document processor singleton. Useful after config changes."""
    global _document_processor
    _document_processor = None


async def create_document_processor(
    config: Optional[ProcessorConfig] = None,
) -> DocumentProcessor:
    """Create and initialize document processor."""
    processor = DocumentProcessor(config=config)
    await processor.initialize()
    return processor
