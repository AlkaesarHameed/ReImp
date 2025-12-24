/**
 * Document Upload Service.
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Source: Design Document 10 - Visual Extraction Display
 * Verified: 2025-12-24
 *
 * Handles document upload to backend API with batch support.
 * Integrates with the document processing pipeline for OCR and extraction.
 * Provides quick extraction for visual extraction display step.
 */
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType, HttpProgressEvent } from '@angular/common/http';
import { Observable, map, filter } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  BatchUploadResponse,
  DocumentUploadResult,
  DocumentType,
} from '@claims-processing/models';

/**
 * Quick extraction response from backend.
 * Source: Design Document 10 - Visual Extraction Display
 */
export interface QuickExtractionResponse {
  document_id: string;
  filename: string;
  total_pages: number;
  overall_confidence: number;
  processing_time_ms: number;
  pages: PageExtraction[];
  tables: TableExtraction[];
}

export interface PageExtraction {
  page_number: number;
  width: number;
  height: number;
  image_url: string;
  regions: TextRegion[];
}

export interface TextRegion {
  id: string;
  text: string;
  confidence: number;
  bounding_box: BoundingBox;
  category?: string;
  field_name?: string;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface TableExtraction {
  page_number: number;
  bounding_box: BoundingBox;
  headers: string[];
  rows: string[][];
  confidence: number;
}

export interface PageThumbnailsResponse {
  document_id: string;
  total_pages: number;
  thumbnails: PageThumbnail[];
}

export interface PageThumbnail {
  page_number: number;
  url: string;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

@Injectable({
  providedIn: 'root',
})
export class DocumentUploadService {
  private readonly http = inject(HttpClient);
  private readonly API_URL = `${environment.apiUrl}/documents`;

  /**
   * Upload a batch of PDF files for processing.
   * Source: POST /api/v1/documents/batch-upload
   *
   * @param files Array of files to upload (max 10)
   * @param documentType Type of documents being uploaded
   * @param claimId Optional claim ID to associate with documents
   * @returns Observable of batch upload response
   */
  uploadBatch(
    files: File[],
    documentType: DocumentType,
    claimId?: string
  ): Observable<BatchUploadResponse> {
    const formData = new FormData();

    files.forEach((file) => {
      formData.append('files', file);
    });
    formData.append('document_type', documentType);

    if (claimId) {
      formData.append('claim_id', claimId);
    }

    return this.http.post<BatchUploadResponse>(
      `${this.API_URL}/batch-upload`,
      formData,
      { withCredentials: true }
    );
  }

  /**
   * Upload a single document for processing.
   * Source: POST /api/v1/documents/upload
   *
   * @param file File to upload
   * @param documentType Type of document
   * @param claimId Optional claim ID
   * @returns Observable of upload result
   */
  uploadSingle(
    file: File,
    documentType: DocumentType,
    claimId?: string
  ): Observable<DocumentUploadResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);

    if (claimId) {
      formData.append('claim_id', claimId);
    }

    return this.http.post<DocumentUploadResult>(
      `${this.API_URL}/upload`,
      formData,
      { withCredentials: true }
    );
  }

  /**
   * Upload a single document with progress tracking.
   *
   * @param file File to upload
   * @param documentType Type of document
   * @param claimId Optional claim ID
   * @returns Observable of upload progress and result
   */
  uploadWithProgress(
    file: File,
    documentType: DocumentType,
    claimId?: string
  ): Observable<UploadProgress | DocumentUploadResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);

    if (claimId) {
      formData.append('claim_id', claimId);
    }

    return this.http
      .post<DocumentUploadResult>(`${this.API_URL}/upload`, formData, {
        withCredentials: true,
        reportProgress: true,
        observe: 'events',
      })
      .pipe(
        filter(
          (event): event is HttpProgressEvent | HttpEvent<DocumentUploadResult> =>
            event.type === HttpEventType.UploadProgress ||
            event.type === HttpEventType.Response
        ),
        map((event) => {
          if (event.type === HttpEventType.UploadProgress) {
            const progressEvent = event as HttpProgressEvent;
            const total = progressEvent.total ?? 0;
            const loaded = progressEvent.loaded;
            return {
              loaded,
              total,
              percentage: total > 0 ? Math.round((loaded / total) * 100) : 0,
            } as UploadProgress;
          } else {
            // Response event
            return (event as { body: DocumentUploadResult }).body;
          }
        })
      );
  }

  /**
   * Check if result is upload progress (type guard).
   */
  isUploadProgress(
    result: UploadProgress | DocumentUploadResult
  ): result is UploadProgress {
    return 'percentage' in result;
  }

  /**
   * Perform quick OCR extraction with bounding boxes.
   *
   * This extracts text with position information but does NOT
   * perform LLM parsing. Used for the Visual Extraction Display step.
   *
   * Source: Design Document 10 - Visual Extraction Display
   * API: POST /api/v1/documents/quick-extract
   *
   * @param file File to extract
   * @param returnImages Whether to cache page images for display
   * @returns Observable of quick extraction response
   */
  quickExtract(
    file: File,
    returnImages: boolean = true
  ): Observable<QuickExtractionResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('return_images', String(returnImages));

    return this.http.post<QuickExtractionResponse>(
      `${this.API_URL}/quick-extract`,
      formData,
      { withCredentials: true }
    );
  }

  /**
   * Get a single page of a document as an image URL.
   *
   * Source: Design Document 10 - Visual Extraction Display
   * API: GET /api/v1/documents/{document_id}/page/{page_number}/image
   *
   * @param documentId Document identifier
   * @param pageNumber Page number (1-indexed)
   * @param width Optional width for resizing
   * @returns Full URL to the page image
   */
  getPageImageUrl(
    documentId: string,
    pageNumber: number,
    width: number = 800
  ): string {
    return `${this.API_URL}/${documentId}/page/${pageNumber}/image?width=${width}`;
  }

  /**
   * Get thumbnail URLs for all pages of a document.
   *
   * Source: Design Document 10 - Visual Extraction Display
   * API: GET /api/v1/documents/{document_id}/pages/thumbnails
   *
   * @param documentId Document identifier
   * @param width Thumbnail width
   * @returns Observable of page thumbnails response
   */
  getPageThumbnails(
    documentId: string,
    width: number = 200
  ): Observable<PageThumbnailsResponse> {
    return this.http.get<PageThumbnailsResponse>(
      `${this.API_URL}/${documentId}/pages/thumbnails?width=${width}`,
      { withCredentials: true }
    );
  }
}
