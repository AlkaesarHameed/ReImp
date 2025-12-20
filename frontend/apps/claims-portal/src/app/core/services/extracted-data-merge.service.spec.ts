/**
 * Extracted Data Merge Service Tests.
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Verified: 2025-12-19
 */
import { TestBed } from '@angular/core/testing';
import { ExtractedDataMergeService } from './extracted-data-merge.service';
import { ExtractedDataResponse } from '@claims-processing/models';

describe('ExtractedDataMergeService', () => {
  let service: ExtractedDataMergeService;

  const createMockExtractedData = (
    docId: string,
    patientName: string,
    confidence: number
  ): ExtractedDataResponse => ({
    document_id: docId,
    extraction_confidence: confidence,
    data: {
      patient: {
        name: patientName,
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
        {
          code: 'J06.9',
          description: 'Upper respiratory infection',
          is_primary: true,
          confidence: 0.95,
        },
      ],
      procedures: [
        {
          code: '99213',
          description: 'Office visit',
          modifiers: [],
          quantity: 1,
          charged_amount: '150.00',
          service_date: '2024-12-01',
          confidence: 0.92,
        },
      ],
      financial: {
        total_charged: '150.00',
        currency: 'USD',
      },
      identifiers: {
        claim_number: 'CLM001',
        prior_auth_number: 'PA123',
        policy_number: 'POL001',
      },
      dates: {
        service_date_from: '2024-12-01',
        service_date_to: '2024-12-01',
      },
      overall_confidence: confidence,
    },
    needs_review: confidence < 0.85,
    validation_issues: [],
  });

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ExtractedDataMergeService],
    });

    service = TestBed.inject(ExtractedDataMergeService);
  });

  describe('mergeExtractedData', () => {
    it('should return empty data for empty input', () => {
      const result = service.mergeExtractedData([]);

      expect(result.patient.name).toBe('');
      expect(result.conflicts.length).toBe(0);
      expect(result.overall_confidence).toBe(0);
    });

    it('should return single document data without conflicts', () => {
      const singleDoc = createMockExtractedData('doc-1', 'John Doe', 0.9);

      const result = service.mergeExtractedData([singleDoc]);

      expect(result.patient.name).toBe('John Doe');
      expect(result.conflicts.length).toBe(0);
      expect(result.fieldSources['Patient Name']).toBe('doc-1');
    });

    it('should detect conflicts when values differ', () => {
      const doc1 = createMockExtractedData('doc-1', 'John Doe', 0.9);
      const doc2 = createMockExtractedData('doc-2', 'Jane Doe', 0.85);

      const result = service.mergeExtractedData([doc1, doc2]);

      const nameConflict = result.conflicts.find((c) => c.field === 'Patient Name');
      expect(nameConflict).toBeTruthy();
      expect(nameConflict!.values.length).toBe(2);
      expect(nameConflict!.resolvedValue).toBe('John Doe'); // Higher confidence
      expect(nameConflict!.resolvedFrom).toBe('doc-1');
    });

    it('should use highest confidence value by default', () => {
      const doc1 = createMockExtractedData('doc-1', 'Low Conf Name', 0.7);
      const doc2 = createMockExtractedData('doc-2', 'High Conf Name', 0.95);

      const result = service.mergeExtractedData([doc1, doc2], 'highest_confidence');

      const nameConflict = result.conflicts.find((c) => c.field === 'Patient Name');
      expect(nameConflict!.resolvedValue).toBe('High Conf Name');
      expect(nameConflict!.resolvedFrom).toBe('doc-2');
    });

    it('should flag low confidence values for review', () => {
      const doc1 = createMockExtractedData('doc-1', 'Name 1', 0.6);
      const doc2 = createMockExtractedData('doc-2', 'Name 2', 0.7);

      const result = service.mergeExtractedData([doc1, doc2]);

      const nameConflict = result.conflicts.find((c) => c.field === 'Patient Name');
      expect(nameConflict!.requiresReview).toBe(true); // Confidence < 0.85
    });

    it('should not flag high confidence values for review', () => {
      const doc1 = createMockExtractedData('doc-1', 'Name 1', 0.95);
      const doc2 = createMockExtractedData('doc-2', 'Name 2', 0.88);

      const result = service.mergeExtractedData([doc1, doc2]);

      const nameConflict = result.conflicts.find((c) => c.field === 'Patient Name');
      expect(nameConflict!.requiresReview).toBe(false);
    });

    it('should leave conflicts unresolved for manual strategy', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.9);
      const doc2 = createMockExtractedData('doc-2', 'Jane', 0.9);

      const result = service.mergeExtractedData([doc1, doc2], 'manual');

      const nameConflict = result.conflicts.find((c) => c.field === 'Patient Name');
      expect(nameConflict!.resolvedValue).toBeNull();
      expect(nameConflict!.requiresReview).toBe(true);
    });

    it('should calculate average overall confidence', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.8);
      const doc2 = createMockExtractedData('doc-2', 'John', 0.9);

      const result = service.mergeExtractedData([doc1, doc2]);

      expect(result.overall_confidence).toBe(0.85);
    });
  });

  describe('mergeDiagnoses', () => {
    it('should deduplicate diagnosis codes by keeping highest confidence', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.9);
      doc1.data.diagnoses = [
        { code: 'J06.9', description: 'URI', is_primary: true, confidence: 0.8 },
      ];

      const doc2 = createMockExtractedData('doc-2', 'John', 0.9);
      doc2.data.diagnoses = [
        { code: 'J06.9', description: 'Upper Respiratory Infection', is_primary: true, confidence: 0.95 },
      ];

      const result = service.mergeExtractedData([doc1, doc2]);

      expect(result.diagnoses.length).toBe(1);
      expect(result.diagnoses[0].description).toBe('Upper Respiratory Infection');
      expect(result.diagnoses[0].confidence).toBe(0.95);
    });

    it('should combine unique diagnosis codes', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.9);
      doc1.data.diagnoses = [
        { code: 'J06.9', description: 'URI', is_primary: true, confidence: 0.9 },
      ];

      const doc2 = createMockExtractedData('doc-2', 'John', 0.9);
      doc2.data.diagnoses = [
        { code: 'E11.9', description: 'Diabetes', is_primary: false, confidence: 0.85 },
      ];

      const result = service.mergeExtractedData([doc1, doc2]);

      expect(result.diagnoses.length).toBe(2);
    });

    it('should sort diagnoses with primary first', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.9);
      doc1.data.diagnoses = [
        { code: 'J06.9', description: 'URI', is_primary: false, confidence: 0.95 },
        { code: 'E11.9', description: 'Diabetes', is_primary: true, confidence: 0.85 },
      ];

      const result = service.mergeExtractedData([doc1]);

      expect(result.diagnoses[0].is_primary).toBe(true);
      expect(result.diagnoses[0].code).toBe('E11.9');
    });
  });

  describe('mergeProcedures', () => {
    it('should deduplicate procedures by code and date', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.9);
      doc1.data.procedures = [
        { code: '99213', description: 'Office Visit', modifiers: [], quantity: 1, charged_amount: '100.00', service_date: '2024-12-01', confidence: 0.8 },
      ];

      const doc2 = createMockExtractedData('doc-2', 'John', 0.9);
      doc2.data.procedures = [
        { code: '99213', description: 'Office Visit Level 3', modifiers: [], quantity: 1, charged_amount: '150.00', service_date: '2024-12-01', confidence: 0.95 },
      ];

      const result = service.mergeExtractedData([doc1, doc2]);

      expect(result.procedures.length).toBe(1);
      expect(result.procedures[0].charged_amount).toBe('150.00'); // Higher confidence
    });

    it('should keep procedures with different dates', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.9);
      doc1.data.procedures = [
        { code: '99213', description: 'Visit 1', modifiers: [], quantity: 1, charged_amount: '100.00', service_date: '2024-12-01', confidence: 0.9 },
      ];

      const doc2 = createMockExtractedData('doc-2', 'John', 0.9);
      doc2.data.procedures = [
        { code: '99213', description: 'Visit 2', modifiers: [], quantity: 1, charged_amount: '100.00', service_date: '2024-12-15', confidence: 0.9 },
      ];

      const result = service.mergeExtractedData([doc1, doc2]);

      expect(result.procedures.length).toBe(2);
    });
  });

  describe('applyConflictResolution', () => {
    it('should apply manual conflict resolution', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.9);
      const doc2 = createMockExtractedData('doc-2', 'Jane', 0.85);

      const merged = service.mergeExtractedData([doc1, doc2]);
      const resolved = service.applyConflictResolution(
        merged,
        'Patient Name',
        'Jane',
        'doc-2'
      );

      const nameConflict = resolved.conflicts.find((c) => c.field === 'Patient Name');
      expect(nameConflict!.resolvedValue).toBe('Jane');
      expect(nameConflict!.resolvedFrom).toBe('doc-2');
      expect(nameConflict!.requiresReview).toBe(false);
    });

    it('should update field sources map', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.9);
      const doc2 = createMockExtractedData('doc-2', 'Jane', 0.85);

      const merged = service.mergeExtractedData([doc1, doc2]);
      const resolved = service.applyConflictResolution(
        merged,
        'Patient Name',
        'Jane',
        'doc-2'
      );

      expect(resolved.fieldSources['Patient Name']).toBe('doc-2');
    });
  });

  describe('areAllConflictsResolved', () => {
    it('should return true when no conflicts', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.9);
      const merged = service.mergeExtractedData([doc1]);

      expect(service.areAllConflictsResolved(merged)).toBe(true);
    });

    it('should return true when all conflicts resolved', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.95);
      const doc2 = createMockExtractedData('doc-2', 'Jane', 0.9);

      const merged = service.mergeExtractedData([doc1, doc2]);

      // By default, highest confidence is selected, not requiring review
      expect(service.areAllConflictsResolved(merged)).toBe(true);
    });

    it('should return false when conflicts require review', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.7);
      const doc2 = createMockExtractedData('doc-2', 'Jane', 0.6);

      const merged = service.mergeExtractedData([doc1, doc2]);

      expect(service.areAllConflictsResolved(merged)).toBe(false);
    });
  });

  describe('getUnresolvedConflicts', () => {
    it('should return only unresolved conflicts', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.7);
      const doc2 = createMockExtractedData('doc-2', 'Jane', 0.6);

      const merged = service.mergeExtractedData([doc1, doc2]);
      const unresolved = service.getUnresolvedConflicts(merged);

      expect(unresolved.length).toBeGreaterThan(0);
      expect(unresolved.every((c) => c.requiresReview)).toBe(true);
    });
  });

  describe('calculateQualityScore', () => {
    it('should return high score for high confidence no conflicts', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.95);
      const merged = service.mergeExtractedData([doc1]);

      const score = service.calculateQualityScore(merged);

      expect(score).toBeGreaterThan(0.9);
    });

    it('should penalize for conflicts', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.9);
      const doc2 = createMockExtractedData('doc-2', 'Jane', 0.9);

      const merged = service.mergeExtractedData([doc1, doc2]);
      const score = service.calculateQualityScore(merged);

      expect(score).toBeLessThan(0.9);
    });

    it('should penalize more for unresolved conflicts', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.7);
      const doc2 = createMockExtractedData('doc-2', 'Jane', 0.6);

      const merged = service.mergeExtractedData([doc1, doc2]);
      const score = service.calculateQualityScore(merged);

      expect(score).toBeLessThan(0.7);
    });
  });

  describe('validateCompleteness', () => {
    it('should return no issues for complete data', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.9);
      const merged = service.mergeExtractedData([doc1]);

      const issues = service.validateCompleteness(merged);

      expect(issues.length).toBe(0);
    });

    it('should flag missing patient name', () => {
      const doc1 = createMockExtractedData('doc-1', '', 0.9);
      const merged = service.mergeExtractedData([doc1]);

      const issues = service.validateCompleteness(merged);

      expect(issues).toContain('Patient name is required');
    });

    it('should flag missing provider NPI', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.9);
      doc1.data.provider.npi = '';
      const merged = service.mergeExtractedData([doc1]);

      const issues = service.validateCompleteness(merged);

      expect(issues).toContain('Provider NPI is required');
    });

    it('should flag missing diagnosis codes', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.9);
      doc1.data.diagnoses = [];
      const merged = service.mergeExtractedData([doc1]);

      const issues = service.validateCompleteness(merged);

      expect(issues).toContain('At least one diagnosis code is required');
    });

    it('should flag missing procedure codes', () => {
      const doc1 = createMockExtractedData('doc-1', 'John', 0.9);
      doc1.data.procedures = [];
      const merged = service.mergeExtractedData([doc1]);

      const issues = service.validateCompleteness(merged);

      expect(issues).toContain('At least one procedure code is required');
    });
  });
});
