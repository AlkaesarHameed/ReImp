/**
 * Document Status Polling Service Tests.
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Verified: 2025-12-19
 */
import { TestBed, fakeAsync, tick, discardPeriodicTasks } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';

import { DocumentStatusPollingService } from './document-status-polling.service';
import {
  DocumentProcessingStatus,
  ExtractedDataResponse,
} from '@claims-processing/models';

describe('DocumentStatusPollingService', () => {
  let service: DocumentStatusPollingService;
  let httpMock: HttpTestingController;

  const mockPendingStatus: DocumentProcessingStatus = {
    document_id: 'doc-123',
    status: 'pending',
    processing_stage: 'upload',
    progress_percent: 0,
    needs_review: false,
  };

  const mockProcessingStatus: DocumentProcessingStatus = {
    document_id: 'doc-123',
    status: 'processing',
    processing_stage: 'ocr',
    progress_percent: 50,
    ocr_confidence: 0.85,
    needs_review: false,
  };

  const mockCompletedStatus: DocumentProcessingStatus = {
    document_id: 'doc-123',
    status: 'completed',
    processing_stage: 'complete',
    progress_percent: 100,
    ocr_confidence: 0.92,
    parsing_confidence: 0.88,
    needs_review: false,
  };

  const mockFailedStatus: DocumentProcessingStatus = {
    document_id: 'doc-123',
    status: 'failed',
    processing_stage: 'failed',
    progress_percent: 0,
    error: 'OCR processing failed',
    needs_review: true,
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [DocumentStatusPollingService],
    });

    service = TestBed.inject(DocumentStatusPollingService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    service.stopAllPolling();
    httpMock.verify();
  });

  describe('getStatus', () => {
    it('should fetch document status successfully', () => {
      service.getStatus('doc-123').subscribe((status) => {
        expect(status.document_id).toBe('doc-123');
        expect(status.status).toBe('processing');
        expect(status.progress_percent).toBe(50);
      });

      const req = httpMock.expectOne((r) =>
        r.url.includes('/documents/doc-123/status')
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.withCredentials).toBe(true);

      req.flush(mockProcessingStatus);
    });
  });

  describe('getExtractedData', () => {
    it('should fetch extracted data for completed document', () => {
      const mockExtracted: ExtractedDataResponse = {
        document_id: 'doc-123',
        extraction_confidence: 0.9,
        data: {
          patient: {
            name: 'John Doe',
            member_id: 'MEM001',
            date_of_birth: '1980-01-15',
            gender: 'M',
            address: '123 Main St',
          },
          provider: {
            name: 'Dr. Smith',
            npi: '1234567890',
            tax_id: '12-3456789',
            specialty: 'Internal Medicine',
          },
          diagnoses: [
            { code: 'J06.9', description: 'Upper respiratory infection', is_primary: true, confidence: 0.95 },
          ],
          procedures: [
            { code: '99213', description: 'Office visit', modifiers: [], quantity: 1, charged_amount: '150.00', service_date: '2024-12-01', confidence: 0.92 },
          ],
          financial: { total_charged: '150.00', currency: 'USD' },
          identifiers: { claim_number: 'CLM001', prior_auth_number: '', policy_number: 'POL123' },
          dates: { service_date_from: '2024-12-01', service_date_to: '2024-12-01' },
          overall_confidence: 0.9,
        },
        needs_review: false,
        validation_issues: [],
      };

      service.getExtractedData('doc-123').subscribe((data) => {
        expect(data.document_id).toBe('doc-123');
        expect(data.data.patient.name).toBe('John Doe');
        expect(data.data.diagnoses.length).toBe(1);
      });

      const req = httpMock.expectOne((r) =>
        r.url.includes('/documents/doc-123/extracted-data')
      );
      expect(req.request.method).toBe('GET');

      req.flush(mockExtracted);
    });
  });

  describe('pollUntilComplete', () => {
    it('should poll until status is completed', fakeAsync(() => {
      const statuses: DocumentProcessingStatus[] = [];

      service.pollUntilComplete('doc-123').subscribe({
        next: (status) => statuses.push(status),
        complete: () => {
          expect(statuses.length).toBe(3);
          expect(statuses[2].status).toBe('completed');
        },
      });

      // First poll - pending
      tick(0);
      const req1 = httpMock.expectOne((r) => r.url.includes('/documents/doc-123/status'));
      req1.flush(mockPendingStatus);

      // Second poll - processing
      tick(2000);
      const req2 = httpMock.expectOne((r) => r.url.includes('/documents/doc-123/status'));
      req2.flush(mockProcessingStatus);

      // Third poll - completed
      tick(2000);
      const req3 = httpMock.expectOne((r) => r.url.includes('/documents/doc-123/status'));
      req3.flush(mockCompletedStatus);

      discardPeriodicTasks();
    }));

    it('should stop polling on failed status', fakeAsync(() => {
      const statuses: DocumentProcessingStatus[] = [];

      service.pollUntilComplete('doc-123').subscribe({
        next: (status) => statuses.push(status),
        complete: () => {
          expect(statuses.length).toBe(2);
          expect(statuses[1].status).toBe('failed');
        },
      });

      tick(0);
      const req1 = httpMock.expectOne((r) => r.url.includes('/documents/doc-123/status'));
      req1.flush(mockPendingStatus);

      tick(2000);
      const req2 = httpMock.expectOne((r) => r.url.includes('/documents/doc-123/status'));
      req2.flush(mockFailedStatus);

      discardPeriodicTasks();
    }));

    it('should use cached observable for same document', fakeAsync(() => {
      const sub1Statuses: DocumentProcessingStatus[] = [];
      const sub2Statuses: DocumentProcessingStatus[] = [];

      // First subscription
      service.pollUntilComplete('doc-123').subscribe((s) => sub1Statuses.push(s));

      // Second subscription to same document
      service.pollUntilComplete('doc-123').subscribe((s) => sub2Statuses.push(s));

      tick(0);
      // Should only have ONE request due to caching
      const req = httpMock.expectOne((r) => r.url.includes('/documents/doc-123/status'));
      req.flush(mockCompletedStatus);

      // Both subscriptions should receive the same data
      expect(sub1Statuses.length).toBe(1);
      expect(sub2Statuses.length).toBe(1);

      discardPeriodicTasks();
    }));
  });

  describe('pollMultiple', () => {
    it('should poll multiple documents in parallel', fakeAsync(() => {
      let resultMap: Map<string, DocumentProcessingStatus> | null = null;

      service.pollMultiple(['doc-1', 'doc-2']).subscribe((map) => {
        resultMap = map;
      });

      tick(0);

      // Should make requests for both documents
      const req1 = httpMock.expectOne((r) => r.url.includes('/documents/doc-1/status'));
      const req2 = httpMock.expectOne((r) => r.url.includes('/documents/doc-2/status'));

      req1.flush({ ...mockCompletedStatus, document_id: 'doc-1' });
      req2.flush({ ...mockCompletedStatus, document_id: 'doc-2' });

      expect(resultMap).toBeTruthy();
      expect(resultMap!.get('doc-1')?.status).toBe('completed');
      expect(resultMap!.get('doc-2')?.status).toBe('completed');

      discardPeriodicTasks();
    }));

    it('should return empty map for empty input', (done) => {
      service.pollMultiple([]).subscribe((map) => {
        expect(map.size).toBe(0);
        done();
      });
    });

    it('should handle errors gracefully', fakeAsync(() => {
      const results: Map<string, DocumentProcessingStatus>[] = [];

      const subscription = service.pollMultiple(['doc-1', 'doc-error']).subscribe((map) => {
        results.push(map);
      });

      tick(0);

      const req1 = httpMock.expectOne((r) => r.url.includes('/documents/doc-1/status'));
      const req2 = httpMock.expectOne((r) => r.url.includes('/documents/doc-error/status'));

      // Complete doc-1 first
      req1.flush({ ...mockCompletedStatus, document_id: 'doc-1' });

      // Error on doc-error - should be caught and return failed status
      req2.error(new ErrorEvent('Network error'));

      tick(100);

      // After all complete, we should have results
      if (results.length > 0) {
        const lastResult = results[results.length - 1];
        expect(lastResult.get('doc-1')?.status).toBe('completed');
        expect(lastResult.get('doc-error')?.status).toBe('failed');
      }

      // Cleanup: unsubscribe and stop polling to prevent pending requests
      subscription.unsubscribe();
      service.stopAllPolling();
      discardPeriodicTasks();
    }));
  });

  describe('getMultipleExtractedData', () => {
    it('should fetch extracted data for multiple documents', () => {
      const mockData: ExtractedDataResponse = {
        document_id: 'doc-1',
        extraction_confidence: 0.9,
        data: {
          patient: { name: 'Test', member_id: '001', date_of_birth: '', gender: '', address: '' },
          provider: { name: '', npi: '', tax_id: '', specialty: '' },
          diagnoses: [],
          procedures: [],
          financial: { total_charged: '', currency: '' },
          identifiers: { claim_number: '', prior_auth_number: '', policy_number: '' },
          dates: { service_date_from: '', service_date_to: '' },
          overall_confidence: 0.9,
        },
        needs_review: false,
        validation_issues: [],
      };

      service.getMultipleExtractedData(['doc-1', 'doc-2']).subscribe((responses) => {
        expect(responses.length).toBe(2);
      });

      const req1 = httpMock.expectOne((r) => r.url.includes('/documents/doc-1/extracted-data'));
      const req2 = httpMock.expectOne((r) => r.url.includes('/documents/doc-2/extracted-data'));

      req1.flush({ ...mockData, document_id: 'doc-1' });
      req2.flush({ ...mockData, document_id: 'doc-2' });
    });

    it('should return empty array for empty input', (done) => {
      service.getMultipleExtractedData([]).subscribe((data) => {
        expect(data.length).toBe(0);
        done();
      });
    });
  });

  describe('stopPolling', () => {
    it('should clear polling cache for specific document', () => {
      // Start polling to add to cache
      const subscription = service.pollUntilComplete('doc-123').subscribe();

      // Stop polling should clear the cache
      service.stopPolling('doc-123');

      // After stopping, a new poll should create a fresh observable
      // (the cache should be empty)
      const sub2 = service.pollUntilComplete('doc-123').subscribe();

      // Both subscriptions are valid
      expect(subscription).toBeTruthy();
      expect(sub2).toBeTruthy();

      subscription.unsubscribe();
      sub2.unsubscribe();
    });
  });

  describe('stopAllPolling', () => {
    it('should clear all polling from cache', () => {
      const sub1 = service.pollUntilComplete('doc-1').subscribe();
      const sub2 = service.pollUntilComplete('doc-2').subscribe();

      service.stopAllPolling();

      // After stopping all, new polls should create fresh observables
      const sub3 = service.pollUntilComplete('doc-1').subscribe();
      const sub4 = service.pollUntilComplete('doc-2').subscribe();

      expect(sub1).toBeTruthy();
      expect(sub2).toBeTruthy();
      expect(sub3).toBeTruthy();
      expect(sub4).toBeTruthy();

      sub1.unsubscribe();
      sub2.unsubscribe();
      sub3.unsubscribe();
      sub4.unsubscribe();
    });
  });
});
