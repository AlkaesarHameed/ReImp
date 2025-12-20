/**
 * Step Processing Component Tests.
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Verified: 2025-12-19
 */
import { ComponentFixture, TestBed, fakeAsync, tick, discardPeriodicTasks } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, Subject } from 'rxjs';

import { StepProcessingComponent, ProcessingStepData } from './step-processing.component';
import { DocumentStatusPollingService } from '../../../../../core/services/document-status-polling.service';
import {
  DocumentUploadState,
  DocumentProcessingStatus,
  ExtractedDataResponse,
} from '@claims-processing/models';

describe('StepProcessingComponent', () => {
  let component: StepProcessingComponent;
  let fixture: ComponentFixture<StepProcessingComponent>;
  let pollingService: { pollMultiple: jest.Mock; getMultipleExtractedData: jest.Mock; stopAllPolling: jest.Mock };
  let pollMultipleSubject: Subject<Map<string, DocumentProcessingStatus>>;

  const createMockUploadState = (id: string, docId: string, type: string = 'claim_form'): DocumentUploadState => ({
    id,
    file: new File([''], 'test.pdf'),
    filename: `${id}.pdf`,
    fileSize: 1024,
    documentType: type as any,
    status: 'processing',
    progressPercent: 25,
    documentId: docId,
    needsReview: false,
  });

  const mockCompletedStatus: DocumentProcessingStatus = {
    document_id: 'doc-1',
    status: 'completed',
    processing_stage: 'complete',
    progress_percent: 100,
    ocr_confidence: 0.92,
    parsing_confidence: 0.88,
    needs_review: false,
  };

  const mockProcessingStatus: DocumentProcessingStatus = {
    document_id: 'doc-1',
    status: 'processing',
    processing_stage: 'ocr',
    progress_percent: 50,
    needs_review: false,
  };

  const mockExtractedData: ExtractedDataResponse = {
    document_id: 'doc-1',
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
        { code: 'J06.9', description: 'URI', is_primary: true, confidence: 0.95 },
      ],
      procedures: [
        { code: '99213', description: 'Office visit', modifiers: [], quantity: 1, charged_amount: '150.00', service_date: '2024-12-01', confidence: 0.92 },
      ],
      financial: { total_charged: '150.00', currency: 'USD' },
      identifiers: { claim_number: 'CLM001', prior_auth_number: '', policy_number: 'POL001' },
      dates: { service_date_from: '2024-12-01', service_date_to: '2024-12-01' },
      overall_confidence: 0.9,
    },
    needs_review: false,
    validation_issues: [],
  };

  beforeEach(async () => {
    pollMultipleSubject = new Subject();

    const pollingServiceSpy = {
      pollMultiple: jest.fn(),
      getMultipleExtractedData: jest.fn(),
      stopAllPolling: jest.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [
        StepProcessingComponent,
        HttpClientTestingModule,
        NoopAnimationsModule,
      ],
      providers: [
        { provide: DocumentStatusPollingService, useValue: pollingServiceSpy },
      ],
    }).compileComponents();

    pollingService = TestBed.inject(DocumentStatusPollingService) as any;
    pollingService.pollMultiple.mockReturnValue(pollMultipleSubject.asObservable());
    pollingService.getMultipleExtractedData.mockReturnValue(of([mockExtractedData]));

    fixture = TestBed.createComponent(StepProcessingComponent);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    pollingService.stopAllPolling.mockClear();
    fixture.destroy();
  });

  describe('initialization', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should start with empty document statuses', () => {
      expect(component.documentStatuses().size).toBe(0);
    });

    it('should calculate total documents from inputs', () => {
      component.policyDocuments = [createMockUploadState('p1', 'doc-p1', 'policy')];
      component.claimDocuments = [createMockUploadState('c1', 'doc-c1')];

      expect(component.totalDocuments()).toBe(2);
    });
  });

  describe('polling', () => {
    it('should start polling on init when documents have IDs', fakeAsync(() => {
      component.claimDocuments = [createMockUploadState('c1', 'doc-1')];
      fixture.detectChanges();

      expect(pollingService.pollMultiple).toHaveBeenCalledWith(['doc-1']);

      discardPeriodicTasks();
    }));

    it('should not start polling without document IDs', fakeAsync(() => {
      component.claimDocuments = [{ ...createMockUploadState('c1', 'doc-1'), documentId: undefined }];
      fixture.detectChanges();

      expect(pollingService.pollMultiple).toHaveBeenCalledWith([]);

      discardPeriodicTasks();
    }));

    it('should update document statuses from polling', fakeAsync(() => {
      component.claimDocuments = [createMockUploadState('c1', 'doc-1')];
      fixture.detectChanges();

      const statusMap = new Map<string, DocumentProcessingStatus>();
      statusMap.set('doc-1', mockProcessingStatus);
      pollMultipleSubject.next(statusMap);
      tick();

      expect(component.documentStatuses().get('doc-1')?.progress_percent).toBe(50);

      discardPeriodicTasks();
    }));

    it('should stop polling on destroy', () => {
      component.claimDocuments = [createMockUploadState('c1', 'doc-1')];
      fixture.detectChanges();

      fixture.destroy();

      expect(pollingService.stopAllPolling).toHaveBeenCalled();
    });
  });

  describe('progress tracking', () => {
    it('should calculate overall progress', fakeAsync(() => {
      component.claimDocuments = [
        createMockUploadState('c1', 'doc-1'),
        createMockUploadState('c2', 'doc-2'),
      ];
      fixture.detectChanges();

      const statusMap = new Map<string, DocumentProcessingStatus>();
      statusMap.set('doc-1', { ...mockProcessingStatus, progress_percent: 50 });
      statusMap.set('doc-2', { ...mockProcessingStatus, progress_percent: 100, status: 'completed' });
      pollMultipleSubject.next(statusMap);
      tick();

      expect(component.overallProgress()).toBe(75);

      discardPeriodicTasks();
    }));

    it('should count processed documents', fakeAsync(() => {
      component.claimDocuments = [
        createMockUploadState('c1', 'doc-1'),
        createMockUploadState('c2', 'doc-2'),
      ];
      fixture.detectChanges();

      const statusMap = new Map<string, DocumentProcessingStatus>();
      statusMap.set('doc-1', mockCompletedStatus);
      statusMap.set('doc-2', mockProcessingStatus);
      pollMultipleSubject.next(statusMap);
      tick();

      expect(component.processedCount()).toBe(1);

      discardPeriodicTasks();
    }));
  });

  describe('extracted data', () => {
    it('should fetch extracted data when processing completes', fakeAsync(() => {
      component.claimDocuments = [createMockUploadState('c1', 'doc-1')];
      fixture.detectChanges();

      const statusMap = new Map<string, DocumentProcessingStatus>();
      statusMap.set('doc-1', mockCompletedStatus);
      pollMultipleSubject.next(statusMap);
      tick();

      expect(pollingService.getMultipleExtractedData).toHaveBeenCalledWith(['doc-1']);

      discardPeriodicTasks();
    }));

    it('should merge extracted data', fakeAsync(() => {
      component.claimDocuments = [createMockUploadState('c1', 'doc-1')];
      fixture.detectChanges();

      const statusMap = new Map<string, DocumentProcessingStatus>();
      statusMap.set('doc-1', mockCompletedStatus);
      pollMultipleSubject.next(statusMap);
      tick();

      expect(component.hasExtractedData()).toBe(true);
      expect(component.mergedData()?.patient.name).toBe('John Doe');

      discardPeriodicTasks();
    }));

    it('should initialize editable fields from merged data', fakeAsync(() => {
      component.claimDocuments = [createMockUploadState('c1', 'doc-1')];
      fixture.detectChanges();

      const statusMap = new Map<string, DocumentProcessingStatus>();
      statusMap.set('doc-1', mockCompletedStatus);
      pollMultipleSubject.next(statusMap);
      tick();

      expect(component.patientFields().length).toBeGreaterThan(0);
      expect(component.providerFields().length).toBeGreaterThan(0);
      expect(component.financialFields().length).toBeGreaterThan(0);

      discardPeriodicTasks();
    }));
  });

  describe('conflict resolution', () => {
    it('should detect conflicts from multiple documents', fakeAsync(() => {
      component.claimDocuments = [
        createMockUploadState('c1', 'doc-1'),
        createMockUploadState('c2', 'doc-2'),
      ];
      fixture.detectChanges();

      const extractedData1 = { ...mockExtractedData, document_id: 'doc-1' };
      const extractedData2 = {
        ...mockExtractedData,
        document_id: 'doc-2',
        data: {
          ...mockExtractedData.data,
          patient: { ...mockExtractedData.data.patient, name: 'Jane Doe' },
        },
      };
      pollingService.getMultipleExtractedData.and.returnValue(of([extractedData1, extractedData2]));

      const statusMap = new Map<string, DocumentProcessingStatus>();
      statusMap.set('doc-1', { ...mockCompletedStatus, document_id: 'doc-1' });
      statusMap.set('doc-2', { ...mockCompletedStatus, document_id: 'doc-2' });
      pollMultipleSubject.next(statusMap);
      tick();

      expect(component.conflicts().length).toBeGreaterThan(0);

      discardPeriodicTasks();
    }));

    it('should resolve conflict when value selected', fakeAsync(() => {
      component.claimDocuments = [createMockUploadState('c1', 'doc-1')];
      fixture.detectChanges();

      const statusMap = new Map<string, DocumentProcessingStatus>();
      statusMap.set('doc-1', mockCompletedStatus);
      pollMultipleSubject.next(statusMap);
      tick();

      // Manually add a conflict
      const merged = component.mergedData()!;
      const conflictMerged = {
        ...merged,
        conflicts: [
          {
            field: 'Patient Name',
            values: [
              { documentId: 'doc-1', value: 'John', confidence: 0.9 },
              { documentId: 'doc-2', value: 'Jane', confidence: 0.8 },
            ],
            resolvedValue: null,
            resolvedFrom: '',
            requiresReview: true,
          },
        ],
      };
      component['mergedData'].set(conflictMerged);

      component.resolveConflict(conflictMerged.conflicts[0], 'Jane', 'doc-2');

      const resolvedConflict = component.mergedData()!.conflicts[0];
      expect(resolvedConflict.resolvedValue).toBe('Jane');
      expect(resolvedConflict.resolvedFrom).toBe('doc-2');
      expect(resolvedConflict.requiresReview).toBe(false);

      discardPeriodicTasks();
    }));
  });

  describe('field editing', () => {
    it('should mark field as edited when value changes', fakeAsync(() => {
      component.claimDocuments = [createMockUploadState('c1', 'doc-1')];
      fixture.detectChanges();

      const statusMap = new Map<string, DocumentProcessingStatus>();
      statusMap.set('doc-1', mockCompletedStatus);
      pollMultipleSubject.next(statusMap);
      tick();

      const field = component.patientFields()[0];
      field.value = 'New Value';
      component.onFieldEdit(field);

      expect(field.edited).toBe(true);

      discardPeriodicTasks();
    }));

    it('should restore field to original value', fakeAsync(() => {
      component.claimDocuments = [createMockUploadState('c1', 'doc-1')];
      fixture.detectChanges();

      const statusMap = new Map<string, DocumentProcessingStatus>();
      statusMap.set('doc-1', mockCompletedStatus);
      pollMultipleSubject.next(statusMap);
      tick();

      const field = component.patientFields()[0];
      const originalValue = field.originalValue;
      field.value = 'New Value';
      component.onFieldEdit(field);

      component.restoreField(field);

      expect(field.value).toBe(originalValue);
      expect(field.edited).toBe(false);

      discardPeriodicTasks();
    }));
  });

  describe('navigation', () => {
    it('should emit stepBack and stop polling on back', fakeAsync(() => {
      component.claimDocuments = [createMockUploadState('c1', 'doc-1')];
      fixture.detectChanges();
      const backSpy = spyOn(component.stepBack, 'emit');

      component.onBack();

      expect(backSpy).toHaveBeenCalled();
      expect(pollingService.stopAllPolling).toHaveBeenCalled();

      discardPeriodicTasks();
    }));

    it('should not proceed while processing', fakeAsync(() => {
      component.claimDocuments = [createMockUploadState('c1', 'doc-1')];
      fixture.detectChanges();

      const statusMap = new Map<string, DocumentProcessingStatus>();
      statusMap.set('doc-1', mockProcessingStatus);
      pollMultipleSubject.next(statusMap);
      tick();

      expect(component.canProceed()).toBe(false);

      discardPeriodicTasks();
    }));

    it('should allow proceed when all documents processed', fakeAsync(() => {
      component.claimDocuments = [createMockUploadState('c1', 'doc-1')];
      fixture.detectChanges();

      const statusMap = new Map<string, DocumentProcessingStatus>();
      statusMap.set('doc-1', mockCompletedStatus);
      pollMultipleSubject.next(statusMap);
      tick();

      expect(component.canProceed()).toBe(true);

      discardPeriodicTasks();
    }));

    it('should emit stepComplete with merged data', fakeAsync(() => {
      component.claimDocuments = [createMockUploadState('c1', 'doc-1')];
      fixture.detectChanges();

      const statusMap = new Map<string, DocumentProcessingStatus>();
      statusMap.set('doc-1', mockCompletedStatus);
      pollMultipleSubject.next(statusMap);
      tick();

      let emittedData: ProcessingStepData | null = null;
      component.stepComplete.subscribe((data) => {
        emittedData = data;
      });

      component.onNext();

      expect(emittedData).toBeTruthy();
      expect(emittedData!.allProcessed).toBe(true);
      expect(emittedData!.mergedData).toBeTruthy();

      discardPeriodicTasks();
    }));

    it('should apply field edits to merged data on next', fakeAsync(() => {
      component.claimDocuments = [createMockUploadState('c1', 'doc-1')];
      fixture.detectChanges();

      const statusMap = new Map<string, DocumentProcessingStatus>();
      statusMap.set('doc-1', mockCompletedStatus);
      pollMultipleSubject.next(statusMap);
      tick();

      // Edit a patient field
      const nameField = component.patientFields().find((f) => f.key === 'patient_name');
      if (nameField) {
        nameField.value = 'Edited Name';
        component.onFieldEdit(nameField);
      }

      let emittedData: ProcessingStepData | null = null;
      component.stepComplete.subscribe((data) => {
        emittedData = data;
      });

      component.onNext();

      expect(emittedData!.mergedData!.patient.name).toBe('Edited Name');

      discardPeriodicTasks();
    }));
  });

  describe('utility methods', () => {
    it('should return processing stage labels', () => {
      expect(component.getDocumentTypeLabel('claim_form')).toBe('Claim Form');
      expect(component.getDocumentTypeLabel('policy')).toBe('Policy');
    });

    it('should return confidence severity', () => {
      expect(component.getConfidenceSeverity(0.95)).toBe('success');
      expect(component.getConfidenceSeverity(0.75)).toBe('warning');
      expect(component.getConfidenceSeverity(0.5)).toBe('danger');
    });
  });
});
