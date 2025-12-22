/**
 * Unit tests for StepPreviewExtractionComponent
 *
 * Source: Design Doc 08 - Document Extraction Preview Step
 * Verified: 2025-12-21
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { StepPreviewExtractionComponent } from './step-preview-extraction.component';
import {
  MergedExtractedData,
  DocumentUploadState,
} from '@claims-processing/models';

// Mock ResizeObserver for PrimeNG TabView
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

(global as any).ResizeObserver = ResizeObserverMock;

describe('StepPreviewExtractionComponent', () => {
  let component: StepPreviewExtractionComponent;
  let fixture: ComponentFixture<StepPreviewExtractionComponent>;

  // Mock data for testing
  const mockMergedData: MergedExtractedData = {
    patient: {
      name: 'John Doe',
      member_id: 'MEM123456',
      date_of_birth: '1980-05-15',
      gender: 'Male',
      address: '123 Main St, City, ST 12345',
    },
    provider: {
      name: 'Dr. Jane Smith',
      npi: '1234567890',
      tax_id: '12-3456789',
      specialty: 'Internal Medicine',
    },
    diagnoses: [
      { code: 'J06.9', description: 'Acute upper respiratory infection', is_primary: true, confidence: 0.92 },
      { code: 'R05', description: 'Cough', is_primary: false, confidence: 0.85 },
    ],
    procedures: [
      { code: '99213', description: 'Office visit, established patient', modifiers: [], quantity: 1, charged_amount: '150.00', service_date: '2025-01-15', confidence: 0.88 },
    ],
    financial: {
      total_charged: '$150.00',
      currency: 'USD',
    },
    identifiers: {
      claim_number: 'CLM-2025-001',
      prior_auth_number: '',
      policy_number: 'POL-789',
    },
    dates: {
      service_date_from: '2025-01-15',
      service_date_to: '2025-01-15',
    },
    overall_confidence: 0.88,
    conflicts: [],
    fieldSources: {},
  };

  const mockDocuments: DocumentUploadState[] = [
    {
      id: 'doc-1',
      file: new File([''], 'medical-record.pdf'),
      filename: 'medical-record.pdf',
      fileSize: 1024000,
      documentType: 'medical_record',
      documentId: 'DOC-001',
      status: 'completed',
      progressPercent: 100,
      needsReview: false,
      ocrConfidence: 0.92,
    },
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StepPreviewExtractionComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(StepPreviewExtractionComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('Component Initialization', () => {
    it('should have default empty state', () => {
      expect(component.mergedExtractedData()).toBeNull();
      expect(component.policyDocuments()).toEqual([]);
      expect(component.claimDocuments()).toEqual([]);
    });

    it('should accept merged extracted data as input', () => {
      fixture.componentRef.setInput('mergedExtractedData', mockMergedData);
      fixture.detectChanges();

      expect(component.mergedExtractedData()).toEqual(mockMergedData);
    });

    it('should accept document arrays as inputs', () => {
      fixture.componentRef.setInput('policyDocuments', mockDocuments);
      fixture.componentRef.setInput('claimDocuments', mockDocuments);
      fixture.detectChanges();

      expect(component.policyDocuments().length).toBe(1);
      expect(component.claimDocuments().length).toBe(1);
    });
  });

  describe('Patient Data Display', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('mergedExtractedData', mockMergedData);
      fixture.detectChanges();
    });

    it('should compute patient fields correctly', () => {
      const fields = component.patientFields();
      expect(fields.length).toBe(4);
      expect(fields[0].label).toBe('Name');
      expect(fields[0].value).toBe('John Doe');
    });

    it('should compute detailed patient fields with source info', () => {
      const fields = component.patientFieldsDetailed();
      expect(fields.length).toBe(5);
      expect(fields[0].source).toBe('OCR+LLM');
    });

    it('should return true for hasPatientData when patient exists', () => {
      expect(component.hasPatientData()).toBe(true);
    });

    it('should return false for hasPatientData when patient is missing', () => {
      fixture.componentRef.setInput('mergedExtractedData', null);
      fixture.detectChanges();
      expect(component.hasPatientData()).toBe(false);
    });
  });

  describe('Provider Data Display', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('mergedExtractedData', mockMergedData);
      fixture.detectChanges();
    });

    it('should compute provider fields correctly', () => {
      const fields = component.providerFields();
      expect(fields.length).toBe(3);
      expect(fields[0].label).toBe('Name');
      expect(fields[0].value).toBe('Dr. Jane Smith');
    });

    it('should compute detailed provider fields with source info', () => {
      const fields = component.providerFieldsDetailed();
      expect(fields.length).toBe(4);
      expect(fields[1].label).toBe('NPI');
      expect(fields[1].source).toBe('OCR');
    });

    it('should return true for hasProviderData when provider exists', () => {
      expect(component.hasProviderData()).toBe(true);
    });
  });

  describe('Financial Data Display', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('mergedExtractedData', mockMergedData);
      fixture.detectChanges();
    });

    it('should compute financial fields correctly', () => {
      const fields = component.financialFields();
      expect(fields.length).toBe(2);
      expect(fields[0].label).toBe('Total Charged');
      expect(fields[0].value).toBe('$150.00');
    });

    it('should return true for hasFinancialData when total_charged exists', () => {
      expect(component.hasFinancialData()).toBe(true);
    });

    it('should return false for hasFinancialData when financial is missing', () => {
      fixture.componentRef.setInput('mergedExtractedData', {
        ...mockMergedData,
        financial: { total_charged: '', currency: 'USD' },
      });
      fixture.detectChanges();
      expect(component.hasFinancialData()).toBe(false);
    });
  });

  describe('Diagnosis Codes Display', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('mergedExtractedData', mockMergedData);
      fixture.detectChanges();
    });

    it('should compute diagnosis codes correctly', () => {
      const codes = component.diagnosisCodes();
      expect(codes.length).toBe(2);
      expect(codes[0].code).toBe('J06.9');
      expect(codes[0].isPrimary).toBe(true);
      expect(codes[0].confidence).toBe(0.92);
    });

    it('should mark first diagnosis as primary if is_primary not set', () => {
      fixture.componentRef.setInput('mergedExtractedData', {
        ...mockMergedData,
        diagnoses: [
          { code: 'A00', description: 'Test', is_primary: false, confidence: 0.8 },
        ],
      });
      fixture.detectChanges();
      const codes = component.diagnosisCodes();
      expect(codes[0].isPrimary).toBe(true);
    });

    it('should return empty array when no diagnoses', () => {
      // Create fresh component without data for this test
      const freshFixture = TestBed.createComponent(StepPreviewExtractionComponent);
      const freshComponent = freshFixture.componentInstance;
      expect(freshComponent.diagnosisCodes()).toEqual([]);
    });
  });

  describe('Procedure Codes Display', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('mergedExtractedData', mockMergedData);
      fixture.detectChanges();
    });

    it('should compute procedure codes correctly', () => {
      const codes = component.procedureCodes();
      expect(codes.length).toBe(1);
      expect(codes[0].code).toBe('99213');
      expect(codes[0].confidence).toBe(0.88);
    });

    it('should return empty array when no procedures', () => {
      // Create fresh component without data for this test
      const freshFixture = TestBed.createComponent(StepPreviewExtractionComponent);
      const freshComponent = freshFixture.componentInstance;
      expect(freshComponent.procedureCodes()).toEqual([]);
    });
  });

  describe('Confidence Scores', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('mergedExtractedData', mockMergedData);
      fixture.detectChanges();
    });

    it('should compute overall confidence from merged data', () => {
      expect(component.overallConfidence()).toBe(0.88);
    });

    it('should return 0 for confidence when data is null', () => {
      // Create fresh component without data for this test
      const freshFixture = TestBed.createComponent(StepPreviewExtractionComponent);
      const freshComponent = freshFixture.componentInstance;
      expect(freshComponent.overallConfidence()).toBe(0);
    });

    it('should use overall_confidence for patient confidence', () => {
      expect(component.patientConfidence()).toBe(0.88);
    });

    it('should use overall_confidence for provider confidence', () => {
      expect(component.providerConfidence()).toBe(0.88);
    });

    it('should use overall_confidence for financial confidence', () => {
      expect(component.financialConfidence()).toBe(0.88);
    });
  });

  describe('Processed Documents', () => {
    it('should combine and filter completed documents', () => {
      fixture.componentRef.setInput('policyDocuments', mockDocuments);
      fixture.componentRef.setInput('claimDocuments', [
        ...mockDocuments,
        {
          ...mockDocuments[0],
          id: 'doc-2',
          status: 'processing' as const,
        },
      ]);
      fixture.detectChanges();

      const processed = component.processedDocuments();
      expect(processed.length).toBe(2); // Only completed documents
    });

    it('should return empty array when no documents', () => {
      expect(component.processedDocuments()).toEqual([]);
    });
  });

  describe('Navigation Events', () => {
    it('should emit stepBack when onBack is called', () => {
      const stepBackSpy = jest.spyOn(component.stepBack, 'emit');
      component.onBack();
      expect(stepBackSpy).toHaveBeenCalled();
    });

    it('should emit stepComplete when onContinue is called', () => {
      const stepCompleteSpy = jest.spyOn(component.stepComplete, 'emit');
      component.onContinue();
      expect(stepCompleteSpy).toHaveBeenCalled();
    });
  });

  describe('View Toggle', () => {
    it('should default to summary view', () => {
      fixture.detectChanges();
      expect(component.activeTab).toBe(0);
    });

    it('should allow switching to detailed view', () => {
      fixture.detectChanges();
      component.activeTab = 1;
      expect(component.activeTab).toBe(1);
    });
  });

  describe('Empty State Handling', () => {
    it('should handle null merged data gracefully', () => {
      fixture.componentRef.setInput('mergedExtractedData', null);
      fixture.detectChanges();

      expect(component.patientFields()).toEqual([]);
      expect(component.providerFields()).toEqual([]);
      expect(component.financialFields()).toEqual([]);
      expect(component.diagnosisCodes()).toEqual([]);
      expect(component.procedureCodes()).toEqual([]);
    });
  });
});
