"""
Document Processing API Endpoints.

Provides:
- Document upload and processing
- Document retrieval and download
- Processing status tracking
- Batch document operations

Source: Design Document Section 4.3 - Document Processing
Verified: 2025-12-18
"""

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware.tenant import (
    get_current_tenant_id,
    get_token_claims,
    require_permission,
)
from src.api.middleware.rate_limit import moderate_rate_limit
from src.core.enums import DocumentStatus, DocumentType
from src.db.connection import get_session

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
)


# =============================================================================
# Schemas
# =============================================================================


class DocumentUploadResponse(BaseModel):
    """Response for document upload."""

    document_id: str
    status: str
    message: str
    is_duplicate: bool = False
    processing_started: bool = False


class DocumentProcessingStatus(BaseModel):
    """Document processing status."""

    document_id: str
    status: DocumentStatus
    processing_stage: str
    progress_percent: int = 0
    ocr_confidence: Optional[float] = None
    parsing_confidence: Optional[float] = None
    needs_review: bool = False
    error: Optional[str] = None


class DocumentResponse(BaseModel):
    """Full document response."""

    id: str
    claim_id: Optional[str] = None
    document_type: str
    filename: str
    content_type: str
    file_size: int
    status: str
    processed: bool
    ocr_confidence: Optional[float] = None
    extracted_data: Optional[dict] = None
    created_at: str
    updated_at: str


class DocumentListResponse(BaseModel):
    """Paginated document list response."""

    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class ExtractedDataResponse(BaseModel):
    """Response for extracted document data."""

    document_id: str
    extraction_confidence: float
    data: dict
    needs_review: bool
    validation_issues: list[str] = []


class BatchUploadResponse(BaseModel):
    """Response for batch document upload."""

    total: int
    successful: int
    failed: int
    documents: list[DocumentUploadResponse]


# =============================================================================
# In-Memory Processing State (for demo/dev)
# =============================================================================

# Track processing status for async operations
_processing_status: dict[str, DocumentProcessingStatus] = {}


def update_processing_status(
    document_id: str,
    status: DocumentProcessingStatus,
) -> None:
    """Update processing status in memory."""
    _processing_status[document_id] = status


def get_processing_status(document_id: str) -> Optional[DocumentProcessingStatus]:
    """Get processing status from memory."""
    return _processing_status.get(document_id)


# =============================================================================
# Upload Endpoints
# =============================================================================


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission("documents:upload"))],
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file to upload"),
    document_type: DocumentType = Form(
        DocumentType.OTHER,
        description="Type of document",
    ),
    claim_id: Optional[str] = Form(
        None,
        description="Associated claim ID",
    ),
    process_async: bool = Form(
        True,
        description="Process document asynchronously",
    ),
    session: AsyncSession = Depends(get_session),
) -> DocumentUploadResponse:
    """
    Upload a document for processing.

    The document will be:
    1. Stored in MinIO
    2. Processed through OCR
    3. Parsed by LLM to extract structured data

    Use the /status endpoint to track processing progress.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content type is required",
        )

    # Check file size (50MB limit)
    max_size = 50 * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum of {max_size} bytes",
        )

    try:
        from src.services.document_processor import get_document_processor

        processor = get_document_processor()

        if process_async:
            # Start async processing
            from uuid import uuid4

            document_id = str(uuid4())

            # Initialize status
            update_processing_status(
                document_id,
                DocumentProcessingStatus(
                    document_id=document_id,
                    status=DocumentStatus.PENDING,
                    processing_stage="upload",
                    progress_percent=0,
                ),
            )

            # Add background task
            background_tasks.add_task(
                _process_document_background,
                tenant_id,
                claim_id,
                document_type,
                file.filename,
                contents,
                file.content_type,
                document_id,
            )

            return DocumentUploadResponse(
                document_id=document_id,
                status="accepted",
                message="Document upload accepted, processing started",
                processing_started=True,
            )
        else:
            # Synchronous processing
            result = await processor.process_document(
                tenant_id=tenant_id,
                claim_id=claim_id,
                document_type=document_type,
                filename=file.filename,
                file_data=contents,
                content_type=file.content_type,
            )

            if not result.success:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=result.error or "Document processing failed",
                )

            return DocumentUploadResponse(
                document_id=result.document_id,
                status="completed",
                message="Document processed successfully",
                is_duplicate=result.is_duplicate,
                processing_started=False,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document",
        )


async def _process_document_background(
    tenant_id: str,
    claim_id: Optional[str],
    document_type: DocumentType,
    filename: str,
    file_data: bytes,
    content_type: str,
    document_id: str,
) -> None:
    """Background task for document processing."""
    try:
        from src.services.document_processor import get_document_processor

        processor = get_document_processor()
        await processor.initialize()

        # Register progress callback
        def progress_callback(progress):
            update_processing_status(
                document_id,
                DocumentProcessingStatus(
                    document_id=document_id,
                    status=DocumentStatus.PROCESSING,
                    processing_stage=progress.stage.value,
                    progress_percent=progress.progress_percent,
                ),
            )

        processor.register_progress_callback(document_id, progress_callback)

        result = await processor.process_document(
            tenant_id=tenant_id,
            claim_id=claim_id,
            document_type=document_type,
            filename=filename,
            file_data=file_data,
            content_type=content_type,
        )

        # Update final status
        if result.success:
            update_processing_status(
                document_id,
                DocumentProcessingStatus(
                    document_id=document_id,
                    status=DocumentStatus.COMPLETED,
                    processing_stage="complete",
                    progress_percent=100,
                    ocr_confidence=result.ocr_confidence,
                    parsing_confidence=result.parsing_confidence,
                    needs_review=result.needs_review,
                ),
            )
        else:
            update_processing_status(
                document_id,
                DocumentProcessingStatus(
                    document_id=document_id,
                    status=DocumentStatus.FAILED,
                    processing_stage="failed",
                    progress_percent=0,
                    error=result.error,
                ),
            )

    except Exception as e:
        logger.error(f"Background processing error: {e}", exc_info=True)
        update_processing_status(
            document_id,
            DocumentProcessingStatus(
                document_id=document_id,
                status=DocumentStatus.FAILED,
                processing_stage="failed",
                error=str(e),
            ),
        )


@router.post(
    "/batch-upload",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[
        Depends(require_permission("documents:upload")),
        Depends(moderate_rate_limit),
    ],
)
async def batch_upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(..., description="Documents to upload"),
    document_type: DocumentType = Form(
        DocumentType.OTHER,
        description="Type of documents",
    ),
    claim_id: Optional[str] = Form(
        None,
        description="Associated claim ID",
    ),
) -> BatchUploadResponse:
    """
    Upload multiple documents for processing.

    All documents will be processed asynchronously.
    Maximum 10 files per request.
    """
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )

    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files per batch",
        )

    results = []
    successful = 0
    failed = 0

    for file in files:
        try:
            if not file.filename or not file.content_type:
                results.append(DocumentUploadResponse(
                    document_id="",
                    status="failed",
                    message="Missing filename or content type",
                ))
                failed += 1
                continue

            contents = await file.read()
            from uuid import uuid4

            document_id = str(uuid4())

            # Initialize status
            update_processing_status(
                document_id,
                DocumentProcessingStatus(
                    document_id=document_id,
                    status=DocumentStatus.PENDING,
                    processing_stage="upload",
                ),
            )

            # Add to background tasks
            background_tasks.add_task(
                _process_document_background,
                tenant_id,
                claim_id,
                document_type,
                file.filename,
                contents,
                file.content_type,
                document_id,
            )

            results.append(DocumentUploadResponse(
                document_id=document_id,
                status="accepted",
                message="Processing started",
                processing_started=True,
            ))
            successful += 1

        except Exception as e:
            results.append(DocumentUploadResponse(
                document_id="",
                status="failed",
                message=str(e),
            ))
            failed += 1

    return BatchUploadResponse(
        total=len(files),
        successful=successful,
        failed=failed,
        documents=results,
    )


# =============================================================================
# Status & Retrieval Endpoints
# =============================================================================


@router.get(
    "/{document_id}/status",
    response_model=DocumentProcessingStatus,
    dependencies=[Depends(require_permission("documents:read"))],
)
async def get_document_status(
    document_id: str,
) -> DocumentProcessingStatus:
    """
    Get document processing status.

    Returns current processing stage and progress.
    """
    status_info = get_processing_status(document_id)

    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or processing not started",
        )

    return status_info


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    dependencies=[Depends(require_permission("documents:read"))],
)
async def get_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    """
    Get document details.

    Returns full document metadata and extracted data.
    """
    # In production, fetch from database
    # For demo, return mock data based on status
    status_info = get_processing_status(document_id)

    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    from datetime import datetime

    return DocumentResponse(
        id=document_id,
        claim_id=None,
        document_type="claim_form",
        filename="document.pdf",
        content_type="application/pdf",
        file_size=0,
        status=status_info.status.value,
        processed=status_info.status == DocumentStatus.COMPLETED,
        ocr_confidence=status_info.ocr_confidence,
        extracted_data=None,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )


@router.get(
    "/{document_id}/extracted-data",
    response_model=ExtractedDataResponse,
    dependencies=[Depends(require_permission("documents:read"))],
)
async def get_extracted_data(
    document_id: str,
    session: AsyncSession = Depends(get_session),
) -> ExtractedDataResponse:
    """
    Get extracted data from a processed document.

    Returns structured data extracted by OCR and LLM parsing.
    """
    status_info = get_processing_status(document_id)

    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if status_info.status != DocumentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document processing not complete. Status: {status_info.status.value}",
        )

    # Return mock extracted data for demo
    return ExtractedDataResponse(
        document_id=document_id,
        extraction_confidence=status_info.parsing_confidence or 0.85,
        data={
            "patient": {"name": "Demo Patient", "member_id": "MEM123"},
            "provider": {"name": "Demo Provider", "npi": "1234567890"},
            "diagnoses": [{"code": "J06.9", "description": "Upper respiratory infection"}],
            "procedures": [{"code": "99213", "description": "Office visit"}],
        },
        needs_review=status_info.needs_review,
        validation_issues=[],
    )


@router.get(
    "/{document_id}/download",
    dependencies=[Depends(require_permission("documents:read"))],
)
async def download_document(
    document_id: str,
) -> StreamingResponse:
    """
    Download the original document file.

    Returns the document as a streaming download.
    """
    try:
        from src.services.document_storage import get_document_storage_service

        storage = get_document_storage_service()
        await storage.initialize()

        # In production, get bucket/path from database
        # For demo, return 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download document",
        )


# =============================================================================
# List & Search Endpoints
# =============================================================================


@router.get(
    "/",
    response_model=DocumentListResponse,
    dependencies=[Depends(require_permission("documents:read"))],
)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    claim_id: Optional[str] = Query(None, description="Filter by claim ID"),
    document_type: Optional[DocumentType] = Query(None, description="Filter by type"),
    status_filter: Optional[DocumentStatus] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> DocumentListResponse:
    """
    List documents with pagination and filters.
    """
    tenant_id = get_current_tenant_id()

    # In production, query database
    # For demo, return empty list
    return DocumentListResponse(
        items=[],
        total=0,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Reprocessing Endpoint
# =============================================================================


@router.post(
    "/{document_id}/reprocess",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission("documents:upload"))],
)
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> DocumentUploadResponse:
    """
    Reprocess an existing document.

    Useful when initial processing failed or needs to be retried
    with updated models/settings.
    """
    # In production, fetch document from database and reprocess
    # For demo, return error
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Document not found for reprocessing",
    )


# =============================================================================
# Delete Endpoint
# =============================================================================


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("documents:delete"))],
)
async def delete_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete a document.

    Removes both the database record and stored file.
    """
    tenant_id = get_current_tenant_id()

    # In production, delete from database and storage
    # For demo, clear from memory
    if document_id in _processing_status:
        del _processing_status[document_id]
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
