/**
 * Document Upload Service Tests.
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Verified: 2025-12-19
 */
import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { HttpEventType, HttpResponse } from '@angular/common/http';

import { DocumentUploadService, UploadProgress } from './document-upload.service';
import {
  BatchUploadResponse,
  DocumentUploadResult,
  DocumentType,
} from '@claims-processing/models';

describe('DocumentUploadService', () => {
  let service: DocumentUploadService;
  let httpMock: HttpTestingController;

  const mockFile = new File(['test content'], 'test.pdf', {
    type: 'application/pdf',
  });

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [DocumentUploadService],
    });

    service = TestBed.inject(DocumentUploadService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('uploadBatch', () => {
    it('should upload batch of files successfully', () => {
      const files = [mockFile];
      const documentType: DocumentType = 'claim_form';
      const expectedResponse: BatchUploadResponse = {
        total: 1,
        successful: 1,
        failed: 0,
        documents: [
          {
            document_id: 'doc-123',
            status: 'accepted',
            message: 'Processing started',
            is_duplicate: false,
            processing_started: true,
          },
        ],
      };

      service.uploadBatch(files, documentType).subscribe((response) => {
        expect(response.successful).toBe(1);
        expect(response.documents[0].processing_started).toBe(true);
        expect(response.documents[0].document_id).toBe('doc-123');
      });

      const req = httpMock.expectOne((r) =>
        r.url.includes('/documents/batch-upload')
      );
      expect(req.request.method).toBe('POST');
      expect(req.request.body instanceof FormData).toBe(true);
      expect(req.request.withCredentials).toBe(true);

      req.flush(expectedResponse);
    });

    it('should include claim_id when provided', () => {
      const files = [mockFile];
      const documentType: DocumentType = 'policy';
      const claimId = 'claim-456';

      service.uploadBatch(files, documentType, claimId).subscribe();

      const req = httpMock.expectOne((r) =>
        r.url.includes('/documents/batch-upload')
      );

      const formData = req.request.body as FormData;
      expect(formData.get('claim_id')).toBe(claimId);
      expect(formData.get('document_type')).toBe(documentType);

      req.flush({ total: 1, successful: 1, failed: 0, documents: [] });
    });

    it('should handle batch upload with failures', () => {
      const files = [mockFile, mockFile];
      const expectedResponse: BatchUploadResponse = {
        total: 2,
        successful: 1,
        failed: 1,
        documents: [
          {
            document_id: 'doc-1',
            status: 'accepted',
            message: 'OK',
            is_duplicate: false,
            processing_started: true,
          },
          {
            document_id: '',
            status: 'failed',
            message: 'Invalid file',
            is_duplicate: false,
            processing_started: false,
          },
        ],
      };

      service.uploadBatch(files, 'claim_form').subscribe((response) => {
        expect(response.failed).toBe(1);
        expect(response.documents[1].status).toBe('failed');
      });

      const req = httpMock.expectOne((r) =>
        r.url.includes('/documents/batch-upload')
      );
      req.flush(expectedResponse);
    });
  });

  describe('uploadSingle', () => {
    it('should upload single file successfully', () => {
      const expectedResult: DocumentUploadResult = {
        document_id: 'doc-789',
        status: 'accepted',
        message: 'Processing started',
        is_duplicate: false,
        processing_started: true,
      };

      service.uploadSingle(mockFile, 'invoice').subscribe((result) => {
        expect(result.document_id).toBe('doc-789');
        expect(result.processing_started).toBe(true);
      });

      const req = httpMock.expectOne((r) => r.url.includes('/documents/upload'));
      expect(req.request.method).toBe('POST');
      expect(req.request.body instanceof FormData).toBe(true);

      req.flush(expectedResult);
    });

    it('should detect duplicate files', () => {
      const expectedResult: DocumentUploadResult = {
        document_id: 'doc-existing',
        status: 'accepted',
        message: 'Duplicate detected',
        is_duplicate: true,
        processing_started: false,
      };

      service.uploadSingle(mockFile, 'policy').subscribe((result) => {
        expect(result.is_duplicate).toBe(true);
        expect(result.processing_started).toBe(false);
      });

      const req = httpMock.expectOne((r) => r.url.includes('/documents/upload'));
      req.flush(expectedResult);
    });
  });

  describe('uploadWithProgress', () => {
    it('should report upload progress', (done) => {
      const progressEvents: (UploadProgress | DocumentUploadResult)[] = [];

      service.uploadWithProgress(mockFile, 'claim_form').subscribe({
        next: (event) => {
          progressEvents.push(event);
        },
        complete: () => {
          // Should have progress events and final response
          expect(progressEvents.length).toBeGreaterThan(0);

          const lastEvent = progressEvents[progressEvents.length - 1];
          expect('document_id' in lastEvent).toBe(true);
          done();
        },
      });

      const req = httpMock.expectOne((r) => r.url.includes('/documents/upload'));

      // Simulate progress events
      req.event({ type: HttpEventType.UploadProgress, loaded: 50, total: 100 });
      req.event({ type: HttpEventType.UploadProgress, loaded: 100, total: 100 });

      // Final response
      req.event(
        new HttpResponse<DocumentUploadResult>({
          body: {
            document_id: 'doc-progress',
            status: 'accepted',
            message: 'Done',
            is_duplicate: false,
            processing_started: true,
          },
        })
      );
    });

    it('should calculate progress percentage correctly', (done) => {
      let progressPercent = 0;

      service.uploadWithProgress(mockFile, 'claim_form').subscribe({
        next: (event) => {
          if (service.isUploadProgress(event)) {
            progressPercent = event.percentage;
          }
        },
        complete: () => {
          expect(progressPercent).toBe(100);
          done();
        },
      });

      const req = httpMock.expectOne((r) => r.url.includes('/documents/upload'));

      req.event({ type: HttpEventType.UploadProgress, loaded: 100, total: 100 });
      req.event(
        new HttpResponse<DocumentUploadResult>({
          body: {
            document_id: 'doc-1',
            status: 'accepted',
            message: 'Done',
            is_duplicate: false,
            processing_started: true,
          },
        })
      );
    });
  });

  describe('isUploadProgress', () => {
    it('should correctly identify upload progress', () => {
      const progress: UploadProgress = { loaded: 50, total: 100, percentage: 50 };
      const result: DocumentUploadResult = {
        document_id: 'doc-1',
        status: 'accepted',
        message: 'OK',
        is_duplicate: false,
        processing_started: true,
      };

      expect(service.isUploadProgress(progress)).toBe(true);
      expect(service.isUploadProgress(result)).toBe(false);
    });
  });
});
