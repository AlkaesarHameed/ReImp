/**
 * Step Claim Documents Component Tests.
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Verified: 2025-12-19
 */
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { StepClaimDocsComponent } from './step-claim-docs.component';
import { DocumentUploadService } from '../../../../../core/services/document-upload.service';
import { BatchUploadResponse } from '@claims-processing/models';

describe('StepClaimDocsComponent', () => {
  let component: StepClaimDocsComponent;
  let fixture: ComponentFixture<StepClaimDocsComponent>;
  let uploadService: { uploadBatch: jest.Mock };

  const createMockFile = (name: string, size = 1024): File => {
    const content = new Array(size).fill('a').join('');
    return new File([content], name, { type: 'application/pdf' });
  };

  const mockUploadResponse: BatchUploadResponse = {
    total: 1,
    successful: 1,
    failed: 0,
    documents: [
      {
        document_id: 'doc-claim-123',
        status: 'accepted',
        message: 'Processing started',
        is_duplicate: false,
        processing_started: true,
      },
    ],
  };

  beforeEach(async () => {
    const uploadServiceMock = {
      uploadBatch: jest.fn().mockReturnValue(of(mockUploadResponse)),
    };

    await TestBed.configureTestingModule({
      imports: [
        StepClaimDocsComponent,
        HttpClientTestingModule,
        NoopAnimationsModule,
      ],
      providers: [
        { provide: DocumentUploadService, useValue: uploadServiceMock },
      ],
    }).compileComponents();

    uploadService = TestBed.inject(DocumentUploadService) as unknown as { uploadBatch: jest.Mock };

    fixture = TestBed.createComponent(StepClaimDocsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    fixture.destroy();
  });

  describe('initialization', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should start with empty documents list', () => {
      expect(component.documents().length).toBe(0);
    });

    it('should not be able to proceed without documents (required step)', () => {
      expect(component.canProceed()).toBe(false);
    });

    it('should have default document type of claim_form', () => {
      expect(component.selectedDocType).toBe('claim_form');
    });

    it('should have document type options', () => {
      expect(component.documentTypeOptions.length).toBeGreaterThan(0);
      expect(component.documentTypeOptions.some((o) => o.value === 'claim_form')).toBe(true);
      expect(component.documentTypeOptions.some((o) => o.value === 'invoice')).toBe(true);
      expect(component.documentTypeOptions.some((o) => o.value === 'medical_record')).toBe(true);
    });
  });

  describe('file selection', () => {
    it('should add valid PDF files with selected document type', () => {
      component.selectedDocType = 'invoice';
      const file = createMockFile('invoice.pdf');

      component.onFilesSelected({ files: [file] });

      expect(component.documents().length).toBe(1);
      expect(component.documents()[0].documentType).toBe('invoice');
    });

    it('should reject non-PDF files', () => {
      const file = new File(['content'], 'document.xlsx', { type: 'application/vnd.ms-excel' });

      component.onFilesSelected({ files: [file] });

      expect(component.documents().length).toBe(0);
      expect(component.validationErrors().length).toBeGreaterThan(0);
    });

    it('should allow proceed once file is added', () => {
      const file = createMockFile('claim.pdf');

      component.onFilesSelected({ files: [file] });

      expect(component.canProceed()).toBe(true);
    });

    it('should prevent duplicate filenames', () => {
      const file1 = createMockFile('claim.pdf');
      const file2 = createMockFile('claim.pdf');

      component.onFilesSelected({ files: [file1] });
      component.onFilesSelected({ files: [file2] });

      expect(component.documents().length).toBe(1);
    });

    it('should limit to 10 files total', () => {
      const files = Array.from({ length: 12 }, (_, i) => createMockFile(`claim${i}.pdf`));

      component.onFilesSelected({ files });

      expect(component.documents().length).toBeLessThanOrEqual(10);
    });
  });

  describe('file removal', () => {
    it('should remove document by id', () => {
      const file = createMockFile('claim.pdf');
      component.onFilesSelected({ files: [file] });

      const docId = component.documents()[0].id;
      component.removeDocument(docId);

      expect(component.documents().length).toBe(0);
      expect(component.canProceed()).toBe(false);
    });
  });

  describe('navigation', () => {
    it('should emit stepBack on back button', () => {
      const backSpy = jest.spyOn(component.stepBack, 'emit');

      component.onBack();

      expect(backSpy).toHaveBeenCalled();
    });

    it('should not proceed without documents', async () => {
      const completeSpy = jest.spyOn(component.stepComplete, 'emit');

      await component.onNext();

      expect(completeSpy).not.toHaveBeenCalled();
    });
  });

  describe('upload flow', () => {
    it('should upload documents on next', fakeAsync(() => {
      const file = createMockFile('claim.pdf');
      component.onFilesSelected({ files: [file] });
      const completeSpy = jest.spyOn(component.stepComplete, 'emit');

      component.onNext();
      tick();

      expect(uploadService.uploadBatch).toHaveBeenCalled();
      expect(completeSpy).toHaveBeenCalled();
    }));

    it('should group uploads by document type', fakeAsync(() => {
      component.selectedDocType = 'claim_form';
      component.onFilesSelected({ files: [createMockFile('form1.pdf')] });

      component.selectedDocType = 'invoice';
      component.onFilesSelected({ files: [createMockFile('invoice1.pdf')] });

      // Change the first document type
      component.documents()[0].documentType = 'claim_form';

      component.onNext();
      tick();

      // Should call uploadBatch for each document type
      expect(uploadService.uploadBatch).toHaveBeenCalledTimes(2);
    }));

    it('should handle upload errors', fakeAsync(() => {
      const file = createMockFile('claim.pdf');
      component.onFilesSelected({ files: [file] });
      uploadService.uploadBatch.mockReturnValue(throwError(() => new Error('Network error')));

      component.onNext();
      tick();

      expect(component.uploadError()).toBeTruthy();
    }));

    it('should block proceed when no uploads succeed', fakeAsync(() => {
      const file = createMockFile('claim.pdf');
      component.onFilesSelected({ files: [file] });

      const failedResponse: BatchUploadResponse = {
        total: 1,
        successful: 0,
        failed: 1,
        documents: [
          { document_id: '', status: 'failed', message: 'Error', is_duplicate: false, processing_started: false },
        ],
      };
      uploadService.uploadBatch.mockReturnValue(of(failedResponse));
      const completeSpy = jest.spyOn(component.stepComplete, 'emit');

      component.onNext();
      tick();

      expect(component.uploadError()).toBeTruthy();
      expect(completeSpy).not.toHaveBeenCalled();
    }));

    it('should allow proceed with partial failures', fakeAsync(() => {
      const file1 = createMockFile('claim1.pdf');
      const file2 = createMockFile('claim2.pdf');
      component.onFilesSelected({ files: [file1, file2] });

      const partialResponse: BatchUploadResponse = {
        total: 2,
        successful: 1,
        failed: 1,
        documents: [
          { document_id: 'doc-1', status: 'accepted', message: 'OK', is_duplicate: false, processing_started: true },
          { document_id: '', status: 'failed', message: 'Error', is_duplicate: false, processing_started: false },
        ],
      };
      uploadService.uploadBatch.mockReturnValue(of(partialResponse));
      const completeSpy = jest.spyOn(component.stepComplete, 'emit');

      component.onNext();
      tick();

      expect(completeSpy).toHaveBeenCalled();
    }));
  });

  describe('document type handling', () => {
    it('should use selected document type for new files', () => {
      component.selectedDocType = 'medical_record';
      const file = createMockFile('records.pdf');

      component.onFilesSelected({ files: [file] });

      expect(component.documents()[0].documentType).toBe('medical_record');
    });

    it('should allow changing document type before upload', () => {
      const file = createMockFile('document.pdf');
      component.onFilesSelected({ files: [file] });

      // Simulate changing type via dropdown
      component.documents()[0].documentType = 'invoice';

      expect(component.documents()[0].documentType).toBe('invoice');
    });
  });

  describe('utility methods', () => {
    it('should format file size correctly', () => {
      expect(component.formatFileSize(512)).toBe('512 B');
      expect(component.formatFileSize(2048)).toBe('2.00 KB');
    });

    it('should return document type labels', () => {
      expect(component.getDocumentTypeLabel('claim_form')).toBe('Claim Form');
      expect(component.getDocumentTypeLabel('invoice')).toBe('Invoice');
      expect(component.getDocumentTypeLabel('medical_record')).toBe('Medical Record');
    });

    it('should return correct status severity', () => {
      expect(component.getStatusSeverity('pending')).toBe('secondary');
      expect(component.getStatusSeverity('completed')).toBe('success');
      expect(component.getStatusSeverity('failed')).toBe('danger');
    });
  });

  describe('step complete data', () => {
    it('should emit all documents in step complete', fakeAsync(() => {
      const file = createMockFile('claim.pdf');
      component.onFilesSelected({ files: [file] });

      let emittedData: { documents: unknown[]; documentIds: string[] } | null = null;
      component.stepComplete.subscribe((data) => {
        emittedData = data;
      });

      component.onNext();
      tick();

      expect(emittedData).toBeTruthy();
      expect(emittedData!.documents.length).toBe(1);
    }));
  });
});
