/**
 * Document Status Polling Service.
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Verified: 2025-12-19
 *
 * Polls document processing status from backend API.
 * Supports polling single or multiple documents with automatic completion.
 */
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {
  Observable,
  timer,
  switchMap,
  takeWhile,
  retry,
  map,
  combineLatest,
  shareReplay,
  catchError,
  of,
} from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  DocumentProcessingStatus,
  ExtractedDataResponse,
} from '@claims-processing/models';

@Injectable({
  providedIn: 'root',
})
export class DocumentStatusPollingService {
  private readonly http = inject(HttpClient);
  private readonly API_URL = `${environment.apiUrl}/documents`;
  private readonly POLL_INTERVAL = 2000; // 2 seconds
  private readonly MAX_RETRIES = 3;

  // Cache for active polling observables
  private readonly pollingCache = new Map<string, Observable<DocumentProcessingStatus>>();

  /**
   * Poll document status until complete or failed.
   * Source: GET /api/v1/documents/{document_id}/status
   *
   * @param documentId Document ID to poll
   * @returns Observable that emits progress updates and completes when done
   */
  pollUntilComplete(documentId: string): Observable<DocumentProcessingStatus> {
    // Return cached observable if already polling
    const cached = this.pollingCache.get(documentId);
    if (cached) {
      return cached;
    }

    const polling$ = timer(0, this.POLL_INTERVAL).pipe(
      switchMap(() => this.getStatus(documentId)),
      takeWhile(
        (status) =>
          status.status !== 'completed' && status.status !== 'failed',
        true // Include the final emission
      ),
      retry({
        count: this.MAX_RETRIES,
        delay: this.POLL_INTERVAL,
      }),
      shareReplay({ bufferSize: 1, refCount: true })
    );

    this.pollingCache.set(documentId, polling$);

    // Clean up cache when complete
    polling$.subscribe({
      complete: () => this.pollingCache.delete(documentId),
      error: () => this.pollingCache.delete(documentId),
    });

    return polling$;
  }

  /**
   * Get current document status (single request).
   *
   * @param documentId Document ID
   * @returns Observable of current status
   */
  getStatus(documentId: string): Observable<DocumentProcessingStatus> {
    return this.http.get<DocumentProcessingStatus>(
      `${this.API_URL}/${documentId}/status`,
      { withCredentials: true }
    );
  }

  /**
   * Get extracted data for a completed document.
   * Source: GET /api/v1/documents/{document_id}/extracted-data
   *
   * @param documentId Document ID
   * @returns Observable of extracted data
   */
  getExtractedData(documentId: string): Observable<ExtractedDataResponse> {
    return this.http.get<ExtractedDataResponse>(
      `${this.API_URL}/${documentId}/extracted-data`,
      { withCredentials: true }
    );
  }

  /**
   * Poll multiple documents in parallel.
   * Returns a map of document ID to status.
   *
   * @param documentIds Array of document IDs to poll
   * @returns Observable of status map, updates as each document progresses
   */
  pollMultiple(
    documentIds: string[]
  ): Observable<Map<string, DocumentProcessingStatus>> {
    if (documentIds.length === 0) {
      return of(new Map());
    }

    const polls$ = documentIds.map((id) =>
      this.pollUntilComplete(id).pipe(
        map((status) => ({ id, status })),
        catchError(() => of({ id, status: this.createFailedStatus(id) }))
      )
    );

    return combineLatest(polls$).pipe(
      map((results) => new Map(results.map((r) => [r.id, r.status])))
    );
  }

  /**
   * Get extracted data for multiple documents.
   *
   * @param documentIds Array of document IDs
   * @returns Observable of extracted data array
   */
  getMultipleExtractedData(
    documentIds: string[]
  ): Observable<ExtractedDataResponse[]> {
    if (documentIds.length === 0) {
      return of([]);
    }

    return combineLatest(
      documentIds.map((id) =>
        this.getExtractedData(id).pipe(
          catchError(() =>
            of({
              document_id: id,
              extraction_confidence: 0,
              data: {
                patient: { name: '', member_id: '', date_of_birth: '', gender: '', address: '' },
                provider: { name: '', npi: '', tax_id: '', specialty: '' },
                diagnoses: [],
                procedures: [],
                financial: { total_charged: '', currency: '' },
                identifiers: { claim_number: '', prior_auth_number: '', policy_number: '' },
                dates: { service_date_from: '', service_date_to: '' },
                overall_confidence: 0,
              },
              needs_review: true,
              validation_issues: ['Failed to retrieve extracted data'],
            } as ExtractedDataResponse)
          )
        )
      )
    );
  }

  /**
   * Stop polling for a specific document.
   *
   * @param documentId Document ID to stop polling
   */
  stopPolling(documentId: string): void {
    this.pollingCache.delete(documentId);
  }

  /**
   * Stop all active polling.
   */
  stopAllPolling(): void {
    this.pollingCache.clear();
  }

  /**
   * Create a failed status object for error cases.
   */
  private createFailedStatus(documentId: string): DocumentProcessingStatus {
    return {
      document_id: documentId,
      status: 'failed',
      processing_stage: 'failed',
      progress_percent: 0,
      needs_review: true,
      error: 'Failed to retrieve document status',
    };
  }
}
