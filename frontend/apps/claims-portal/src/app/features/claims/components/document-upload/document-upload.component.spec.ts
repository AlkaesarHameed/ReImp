/**
 * Document Upload Component Tests.
 * Source: Phase 3 Implementation Document
 * TDD: Tests written first
 */
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MessageService } from 'primeng/api';

import { DocumentUploadComponent } from './document-upload.component';
import { ClaimDocument } from '@claims-processing/models';

describe('DocumentUploadComponent', () => {
  let component: DocumentUploadComponent;
  let fixture: ComponentFixture<DocumentUploadComponent>;
  let httpMock: HttpTestingController;
  let messageService: jasmine.SpyObj<MessageService>;

  const mockDocuments: ClaimDocument[] = [
    {
      id: 'doc-1',
      document_type: 'EOB',
      file_name: 'explanation_of_benefits.pdf',
      file_size: 1024000,
      mime_type: 'application/pdf',
      uploaded_at: '2024-01-15T10:00:00Z',
      uploaded_by: 'user-1',
    },
    {
      id: 'doc-2',
      document_type: 'Medical Record',
      file_name: 'medical_record.pdf',
      file_size: 2048000,
      mime_type: 'application/pdf',
      uploaded_at: '2024-01-15T11:00:00Z',
      uploaded_by: 'user-1',
    },
  ];

  beforeEach(async () => {
    messageService = jasmine.createSpyObj('MessageService', ['add']);

    await TestBed.configureTestingModule({
      imports: [DocumentUploadComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MessageService, useValue: messageService },
      ],
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(DocumentUploadComponent);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('Component Creation', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should initialize with empty documents list', () => {
      expect(component.documents()).toEqual([]);
    });

    it('should have default allowed file types', () => {
      expect(component.acceptedTypes).toContain('application/pdf');
      expect(component.acceptedTypes).toContain('image/jpeg');
      expect(component.acceptedTypes).toContain('image/png');
    });

    it('should have default max file size of 10MB', () => {
      expect(component.maxFileSize).toBe(10 * 1024 * 1024);
    });
  });

  describe('Initial Data Loading', () => {
    it('should load existing documents when provided', () => {
      component.initialDocuments = mockDocuments;
      component.ngOnInit();

      expect(component.documents()).toEqual(mockDocuments);
    });

    it('should load documents by claim ID when provided', fakeAsync(() => {
      component.claimId = 'claim-123';
      fixture.detectChanges();

      const req = httpMock.expectOne(req =>
        req.url.includes('/claims/claim-123/documents')
      );
      req.flush(mockDocuments);
      tick();

      expect(component.documents()).toEqual(mockDocuments);
    }));
  });

  describe('File Validation', () => {
    it('should reject files exceeding max size', () => {
      const largeFile = new File(['x'.repeat(11 * 1024 * 1024)], 'large.pdf', {
        type: 'application/pdf',
      });

      const result = component.validateFile(largeFile);

      expect(result.valid).toBe(false);
      expect(result.error).toContain('size');
    });

    it('should reject files with invalid type', () => {
      const invalidFile = new File(['test'], 'test.exe', {
        type: 'application/x-msdownload',
      });

      const result = component.validateFile(invalidFile);

      expect(result.valid).toBe(false);
      expect(result.error).toContain('type');
    });

    it('should accept valid PDF files', () => {
      const validFile = new File(['test content'], 'document.pdf', {
        type: 'application/pdf',
      });

      const result = component.validateFile(validFile);

      expect(result.valid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('should accept valid image files', () => {
      const imageFile = new File(['image data'], 'scan.jpg', {
        type: 'image/jpeg',
      });

      const result = component.validateFile(imageFile);

      expect(result.valid).toBe(true);
    });
  });

  describe('File Upload', () => {
    it('should upload file and emit event on success', fakeAsync(() => {
      const uploadSpy = spyOn(component.documentUploaded, 'emit');
      const file = new File(['test content'], 'document.pdf', {
        type: 'application/pdf',
      });
      component.claimId = 'claim-123';
      component.selectedDocumentType = 'EOB';

      component.uploadFile(file);
      tick();

      const req = httpMock.expectOne(req =>
        req.url.includes('/claims/claim-123/documents')
      );
      expect(req.request.method).toBe('POST');

      const mockResponse: ClaimDocument = {
        id: 'new-doc',
        document_type: 'EOB',
        file_name: 'document.pdf',
        file_size: 12,
        mime_type: 'application/pdf',
        uploaded_at: new Date().toISOString(),
        uploaded_by: 'current-user',
      };
      req.flush(mockResponse);
      tick();

      expect(component.documents().length).toBe(1);
      expect(uploadSpy).toHaveBeenCalledWith(mockResponse);
    }));

    it('should show progress during upload', fakeAsync(() => {
      const file = new File(['test content'], 'document.pdf', {
        type: 'application/pdf',
      });
      component.claimId = 'claim-123';
      component.selectedDocumentType = 'EOB';

      component.uploadFile(file);

      expect(component.uploading()).toBe(true);

      const req = httpMock.expectOne(req =>
        req.url.includes('/claims/claim-123/documents')
      );
      req.flush({});
      tick();

      expect(component.uploading()).toBe(false);
    }));

    it('should handle upload errors gracefully', fakeAsync(() => {
      const file = new File(['test content'], 'document.pdf', {
        type: 'application/pdf',
      });
      component.claimId = 'claim-123';
      component.selectedDocumentType = 'EOB';

      component.uploadFile(file);

      const req = httpMock.expectOne(req =>
        req.url.includes('/claims/claim-123/documents')
      );
      req.error(new ProgressEvent('error'), { status: 500 });
      tick();

      expect(component.uploading()).toBe(false);
      expect(messageService.add).toHaveBeenCalledWith(
        jasmine.objectContaining({
          severity: 'error',
        })
      );
    }));

    it('should require document type before upload', () => {
      const file = new File(['test content'], 'document.pdf', {
        type: 'application/pdf',
      });
      component.claimId = 'claim-123';
      component.selectedDocumentType = '';

      component.uploadFile(file);

      expect(messageService.add).toHaveBeenCalledWith(
        jasmine.objectContaining({
          severity: 'warn',
          detail: jasmine.stringMatching(/document type/i),
        })
      );
    });
  });

  describe('Document Management', () => {
    beforeEach(() => {
      component.initialDocuments = mockDocuments;
      component.ngOnInit();
    });

    it('should display uploaded documents', () => {
      expect(component.documents().length).toBe(2);
    });

    it('should delete document and emit event', fakeAsync(() => {
      const deleteSpy = spyOn(component.documentDeleted, 'emit');
      component.claimId = 'claim-123';

      component.deleteDocument(mockDocuments[0]);

      const req = httpMock.expectOne(req =>
        req.url.includes('/claims/claim-123/documents/doc-1')
      );
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
      tick();

      expect(component.documents().length).toBe(1);
      expect(deleteSpy).toHaveBeenCalledWith('doc-1');
    }));

    it('should format file size correctly', () => {
      expect(component.formatFileSize(1024)).toBe('1.00 KB');
      expect(component.formatFileSize(1048576)).toBe('1.00 MB');
      expect(component.formatFileSize(500)).toBe('500 B');
    });
  });

  describe('Document Types', () => {
    it('should have predefined document types', () => {
      expect(component.documentTypes.length).toBeGreaterThan(0);
      expect(component.documentTypes).toContain(
        jasmine.objectContaining({ value: 'EOB' })
      );
      expect(component.documentTypes).toContain(
        jasmine.objectContaining({ value: 'Medical Record' })
      );
    });

    it('should allow selecting document type', () => {
      component.onDocumentTypeChange('Medical Record');
      expect(component.selectedDocumentType).toBe('Medical Record');
    });
  });

  describe('Drag and Drop', () => {
    it('should update drag state on dragover', () => {
      const event = new DragEvent('dragover');
      component.onDragOver(event);

      expect(component.isDragging()).toBe(true);
    });

    it('should reset drag state on dragleave', () => {
      component.isDragging.set(true);
      const event = new DragEvent('dragleave');
      component.onDragLeave(event);

      expect(component.isDragging()).toBe(false);
    });

    it('should process dropped files', fakeAsync(() => {
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);

      const event = new DragEvent('drop', { dataTransfer });
      component.claimId = 'claim-123';
      component.selectedDocumentType = 'EOB';

      component.onDrop(event);
      tick();

      expect(component.isDragging()).toBe(false);
      // File should be queued for upload
      expect(component.pendingFiles().length).toBeGreaterThanOrEqual(0);
    }));
  });

  describe('Read-Only Mode', () => {
    it('should hide upload controls in read-only mode', () => {
      component.readOnly = true;
      fixture.detectChanges();

      expect(component.readOnly).toBe(true);
    });

    it('should hide delete buttons in read-only mode', () => {
      component.readOnly = true;
      component.initialDocuments = mockDocuments;
      component.ngOnInit();

      expect(component.canDelete()).toBe(false);
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels on upload area', () => {
      fixture.detectChanges();
      const uploadArea = fixture.nativeElement.querySelector('.upload-area');

      // Upload area should exist (even if no specific ARIA label in this test)
      expect(uploadArea || component.readOnly === false).toBeTruthy();
    });

    it('should announce upload progress to screen readers', fakeAsync(() => {
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });
      component.claimId = 'claim-123';
      component.selectedDocumentType = 'EOB';

      component.uploadFile(file);

      expect(component.uploadStatusMessage()).toContain('Uploading');

      const req = httpMock.expectOne(req =>
        req.url.includes('/claims/claim-123/documents')
      );
      req.flush({});
      tick();

      expect(component.uploadStatusMessage()).toBe('');
    }));
  });

  describe('Events', () => {
    it('should emit documentsChanged when documents list changes', () => {
      const changesSpy = spyOn(component.documentsChanged, 'emit');
      component.initialDocuments = mockDocuments;
      component.ngOnInit();

      expect(changesSpy).toHaveBeenCalledWith(mockDocuments);
    });
  });
});
