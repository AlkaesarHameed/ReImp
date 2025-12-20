/**
 * Step Policy Documents Component Tests.
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Verified: 2025-12-19
 */
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { StepPolicyDocsComponent } from './step-policy-docs.component';
import { DocumentUploadService } from '../../../../../core/services/document-upload.service';
import { BatchUploadResponse } from '@claims-processing/models';

describe('StepPolicyDocsComponent', () => {
  let component: StepPolicyDocsComponent;
  let fixture: ComponentFixture<StepPolicyDocsComponent>;
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
        document_id: 'doc-123',
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
        StepPolicyDocsComponent,
        HttpClientTestingModule,
        NoopAnimationsModule,
      ],
      providers: [
        { provide: DocumentUploadService, useValue: uploadServiceMock },
      ],
    }).compileComponents();

    uploadService = TestBed.inject(DocumentUploadService) as unknown as { uploadBatch: jest.Mock };

    fixture = TestBed.createComponent(StepPolicyDocsComponent);
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

    it('should be able to proceed with no documents (optional step)', () => {
      expect(component.canProceed()).toBe(true);
    });
  });

  describe('file selection', () => {
    it('should add valid PDF files', () => {
      const file = createMockFile('policy.pdf');

      component.onFilesSelected({ files: [file] });

      expect(component.documents().length).toBe(1);
      expect(component.documents()[0].filename).toBe('policy.pdf');
    });

    it('should reject non-PDF files', () => {
      const file = new File(['content'], 'document.doc', { type: 'application/msword' });

      component.onFilesSelected({ files: [file] });

      expect(component.documents().length).toBe(0);
      expect(component.validationErrors().length).toBeGreaterThan(0);
    });

    it('should prevent duplicate filenames', () => {
      const file1 = createMockFile('policy.pdf');
      const file2 = createMockFile('policy.pdf');

      component.onFilesSelected({ files: [file1] });
      component.onFilesSelected({ files: [file2] });

      expect(component.documents().length).toBe(1);
    });

    it('should limit to 10 files', () => {
      const files = Array.from({ length: 12 }, (_, i) => createMockFile(`file${i}.pdf`));

      component.onFilesSelected({ files });

      expect(component.documents().length).toBeLessThanOrEqual(10);
      expect(component.validationErrors().some((e) => e.includes('Maximum'))).toBe(true);
    });

    it('should emit dirty event when files added', () => {
      const dirtySpy = jest.spyOn(component.dirty, 'emit');
      const file = createMockFile('policy.pdf');

      component.onFilesSelected({ files: [file] });

      expect(dirtySpy).toHaveBeenCalledWith(true);
    });
  });

  describe('file removal', () => {
    it('should remove document by id', () => {
      const file = createMockFile('policy.pdf');
      component.onFilesSelected({ files: [file] });

      const docId = component.documents()[0].id;
      component.removeDocument(docId);

      expect(component.documents().length).toBe(0);
    });

    it('should emit dirty event on removal', () => {
      const file = createMockFile('policy.pdf');
      component.onFilesSelected({ files: [file] });
      const dirtySpy = jest.spyOn(component.dirty, 'emit');

      const docId = component.documents()[0].id;
      component.removeDocument(docId);

      expect(dirtySpy).toHaveBeenCalled();
    });
  });

  describe('navigation', () => {
    it('should emit stepBack on back button', () => {
      const backSpy = jest.spyOn(component.stepBack, 'emit');

      component.onBack();

      expect(backSpy).toHaveBeenCalled();
    });

    it('should emit stepComplete with skipped=true when skipping', () => {
      const completeSpy = jest.spyOn(component.stepComplete, 'emit');

      component.onSkip();

      expect(completeSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          documents: [],
          skipped: true,
        })
      );
    });
  });

  describe('upload flow', () => {
    it('should upload documents on next', fakeAsync(() => {
      const file = createMockFile('policy.pdf');
      component.onFilesSelected({ files: [file] });
      const completeSpy = jest.spyOn(component.stepComplete, 'emit');

      component.onNext();
      tick();

      expect(uploadService.uploadBatch).toHaveBeenCalled();
      expect(completeSpy).toHaveBeenCalled();
    }));

    it('should set uploading state during upload', fakeAsync(() => {
      const file = createMockFile('policy.pdf');
      component.onFilesSelected({ files: [file] });

      component.onNext();
      expect(component.uploading()).toBe(true);

      tick();
      expect(component.uploading()).toBe(false);
    }));

    it('should handle upload errors', fakeAsync(() => {
      const file = createMockFile('policy.pdf');
      component.onFilesSelected({ files: [file] });
      uploadService.uploadBatch.mockReturnValue(throwError(() => new Error('Network error')));

      component.onNext();
      tick();

      expect(component.uploadError()).toBeTruthy();
    }));

    it('should update document status on successful upload', fakeAsync(() => {
      const file = createMockFile('policy.pdf');
      component.onFilesSelected({ files: [file] });

      component.onNext();
      tick();

      const doc = component.documents()[0];
      expect(doc.documentId).toBe('doc-123');
      expect(doc.status).toBe('processing');
    }));

    it('should handle partial upload failures', fakeAsync(() => {
      const file1 = createMockFile('file1.pdf');
      const file2 = createMockFile('file2.pdf');
      component.onFilesSelected({ files: [file1, file2] });

      const partialResponse: BatchUploadResponse = {
        total: 2,
        successful: 1,
        failed: 1,
        documents: [
          { document_id: 'doc-1', status: 'accepted', message: 'OK', is_duplicate: false, processing_started: true },
          { document_id: '', status: 'failed', message: 'Invalid', is_duplicate: false, processing_started: false },
        ],
      };
      uploadService.uploadBatch.mockReturnValue(of(partialResponse));

      component.onNext();
      tick();

      expect(component.uploadError()).toContain('failed');
    }));
  });

  describe('canProceed logic', () => {
    it('should allow proceed with no documents', () => {
      expect(component.canProceed()).toBe(true);
    });

    it('should allow proceed with pending documents', () => {
      const file = createMockFile('policy.pdf');
      component.onFilesSelected({ files: [file] });

      expect(component.canProceed()).toBe(true);
    });

    it('should not allow proceed while uploading', fakeAsync(() => {
      const file = createMockFile('policy.pdf');
      component.onFilesSelected({ files: [file] });

      // Start upload
      component.onNext();

      // While uploading
      expect(component.uploading()).toBe(true);

      tick();
    }));
  });

  describe('utility methods', () => {
    it('should format file size correctly', () => {
      expect(component.formatFileSize(1024)).toBe('1.00 KB');
      expect(component.formatFileSize(1048576)).toBe('1.00 MB');
    });

    it('should return correct status severity', () => {
      expect(component.getStatusSeverity('pending')).toBe('secondary');
      expect(component.getStatusSeverity('uploading')).toBe('info');
      expect(component.getStatusSeverity('processing')).toBe('info');
      expect(component.getStatusSeverity('completed')).toBe('success');
      expect(component.getStatusSeverity('failed')).toBe('danger');
    });
  });
});
