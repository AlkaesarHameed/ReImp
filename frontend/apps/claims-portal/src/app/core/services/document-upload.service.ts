/**
 * Document Upload Service.
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Verified: 2025-12-19
 *
 * Handles document upload to backend API with batch support.
 * Integrates with the document processing pipeline for OCR and extraction.
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
}
