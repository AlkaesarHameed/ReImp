"""
Visual Extraction Display Schemas.

Pydantic models for the Visual Extraction Display step API contracts.
These schemas support the quick extraction endpoint that returns
OCR results with bounding boxes for source-faithful document rendering.

Source: Design Document 10 - Visual Extraction Display
Verified: 2025-12-24
"""

from typing import Optional
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """
    Normalized bounding box for text region positioning.

    All values are normalized to 0-1 range relative to page dimensions.
    This allows accurate overlay rendering at any zoom level.
    """

    x: float = Field(..., ge=0.0, le=1.0, description="Left position (0-1)")
    y: float = Field(..., ge=0.0, le=1.0, description="Top position (0-1)")
    width: float = Field(..., ge=0.0, le=1.0, description="Width (0-1)")
    height: float = Field(..., ge=0.0, le=1.0, description="Height (0-1)")


class TextRegion(BaseModel):
    """
    Extracted text region with position and confidence.

    Each region represents a contiguous block of text extracted by OCR,
    with normalized coordinates for positioning on the document overlay.
    """

    id: str = Field(..., description="Unique region identifier")
    text: str = Field(..., description="Extracted text content")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="OCR confidence score (0.0-1.0)"
    )
    bounding_box: BoundingBox = Field(..., description="Position on page")
    category: Optional[str] = Field(
        None,
        description="Field category from LLM parsing (patient, provider, diagnosis, etc.)"
    )
    field_name: Optional[str] = Field(
        None,
        description="Specific field name (patient_name, total_amount, etc.)"
    )


class TableExtraction(BaseModel):
    """Extracted table with structure and position."""

    page_number: int = Field(..., ge=1, description="Page containing the table")
    bounding_box: BoundingBox = Field(..., description="Table position on page")
    headers: list[str] = Field(default_factory=list, description="Table column headers")
    rows: list[list[str]] = Field(default_factory=list, description="Table data rows")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Table extraction confidence"
    )


class PageExtraction(BaseModel):
    """
    Extraction results for a single page.

    Contains all text regions and the page image URL for overlay rendering.
    """

    page_number: int = Field(..., ge=1, description="Page number (1-indexed)")
    width: int = Field(..., gt=0, description="Original page width in pixels")
    height: int = Field(..., gt=0, description="Original page height in pixels")
    image_url: str = Field(..., description="URL to page image for display")
    regions: list[TextRegion] = Field(
        default_factory=list,
        description="Text regions with bounding boxes"
    )


class QuickExtractionResponse(BaseModel):
    """
    Response from quick extraction endpoint.

    Returns OCR results with bounding boxes for source-faithful rendering.
    Does NOT include LLM parsing - that happens in the Processing step.

    Source: Design Document 10 - Visual Extraction Display
    """

    document_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original filename")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    overall_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average OCR confidence across all regions"
    )
    processing_time_ms: int = Field(..., ge=0, description="Processing time in milliseconds")
    pages: list[PageExtraction] = Field(
        default_factory=list,
        description="Per-page extraction results"
    )
    tables: list[TableExtraction] = Field(
        default_factory=list,
        description="Extracted tables with structure"
    )

    model_config = {"json_schema_extra": {
        "example": {
            "document_id": "550e8400-e29b-41d4-a716-446655440000",
            "filename": "medical_claim.pdf",
            "total_pages": 3,
            "overall_confidence": 0.87,
            "processing_time_ms": 2340,
            "pages": [
                {
                    "page_number": 1,
                    "width": 2480,
                    "height": 3508,
                    "image_url": "/api/v1/documents/550e8400.../page/1/image",
                    "regions": [
                        {
                            "id": "r1",
                            "text": "PATIENT INFORMATION",
                            "confidence": 0.95,
                            "bounding_box": {
                                "x": 0.05,
                                "y": 0.08,
                                "width": 0.25,
                                "height": 0.03
                            },
                            "category": None,
                            "field_name": None
                        }
                    ]
                }
            ],
            "tables": []
        }
    }}


class PageThumbnail(BaseModel):
    """Single page thumbnail reference."""

    page_number: int = Field(..., ge=1, description="Page number")
    url: str = Field(..., description="Thumbnail image URL")


class PageThumbnailsResponse(BaseModel):
    """Response for page thumbnails endpoint."""

    document_id: str = Field(..., description="Document identifier")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    thumbnails: list[PageThumbnail] = Field(
        default_factory=list,
        description="Thumbnail URLs for each page"
    )
