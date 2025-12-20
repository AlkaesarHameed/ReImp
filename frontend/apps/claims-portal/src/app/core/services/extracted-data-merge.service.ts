/**
 * Extracted Data Merge Service.
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Verified: 2025-12-19
 *
 * Service for merging extracted data from multiple documents.
 * Detects conflicts, applies resolution strategies, and provides merge utilities.
 */
import { Injectable } from '@angular/core';
import {
  ExtractedDataResponse,
  ExtractedClaimData,
  MergedExtractedData,
  DataConflict,
  ConflictValue,
  ExtractedDiagnosisCode,
  ExtractedProcedureCode,
} from '@claims-processing/models';

/**
 * Strategy for resolving conflicts.
 */
export type ConflictResolutionStrategy = 'highest_confidence' | 'latest_document' | 'manual';

/**
 * Field path for accessing nested data.
 */
interface FieldPath {
  section: 'patient' | 'provider' | 'financial' | 'identifiers' | 'dates';
  field: string;
  label: string;
}

@Injectable({
  providedIn: 'root',
})
export class ExtractedDataMergeService {
  /**
   * Fields to check for conflicts.
   */
  private readonly conflictFields: FieldPath[] = [
    { section: 'patient', field: 'name', label: 'Patient Name' },
    { section: 'patient', field: 'member_id', label: 'Member ID' },
    { section: 'patient', field: 'date_of_birth', label: 'Date of Birth' },
    { section: 'patient', field: 'gender', label: 'Gender' },
    { section: 'patient', field: 'address', label: 'Address' },
    { section: 'provider', field: 'name', label: 'Provider Name' },
    { section: 'provider', field: 'npi', label: 'Provider NPI' },
    { section: 'provider', field: 'tax_id', label: 'Tax ID' },
    { section: 'provider', field: 'specialty', label: 'Specialty' },
    { section: 'identifiers', field: 'claim_number', label: 'Claim Number' },
    { section: 'identifiers', field: 'prior_auth_number', label: 'Prior Auth Number' },
    { section: 'identifiers', field: 'policy_number', label: 'Policy Number' },
    { section: 'dates', field: 'service_date_from', label: 'Service Date From' },
    { section: 'dates', field: 'service_date_to', label: 'Service Date To' },
    { section: 'financial', field: 'total_charged', label: 'Total Charged' },
  ];

  /**
   * Threshold for flagging low confidence values for review.
   */
  private readonly confidenceThreshold = 0.85;

  /**
   * Merge extracted data from multiple documents.
   *
   * @param responses Array of extracted data responses
   * @param strategy Conflict resolution strategy
   * @returns Merged data with conflicts
   */
  mergeExtractedData(
    responses: ExtractedDataResponse[],
    strategy: ConflictResolutionStrategy = 'highest_confidence'
  ): MergedExtractedData {
    if (responses.length === 0) {
      return this.createEmptyMergedData();
    }

    if (responses.length === 1) {
      return this.createMergedFromSingle(responses[0]);
    }

    // Detect conflicts
    const conflicts = this.detectConflicts(responses);

    // Merge base data using strategy
    const merged = this.mergeBaseData(responses, strategy);

    // Apply conflict resolutions
    const resolvedConflicts = this.resolveConflicts(conflicts, responses, strategy);

    // Build field sources map
    const fieldSources = this.buildFieldSources(responses, resolvedConflicts);

    return {
      ...merged,
      conflicts: resolvedConflicts,
      fieldSources,
    };
  }

  /**
   * Detect conflicts between multiple extracted data responses.
   */
  private detectConflicts(responses: ExtractedDataResponse[]): DataConflict[] {
    const conflicts: DataConflict[] = [];

    for (const fieldPath of this.conflictFields) {
      const values = this.collectFieldValues(responses, fieldPath);

      // Check if there are different non-empty values
      const uniqueNonEmptyValues = values
        .filter(v => v.value !== null && v.value !== undefined && v.value !== '')
        .map(v => JSON.stringify(v.value));

      const uniqueSet = new Set(uniqueNonEmptyValues);

      if (uniqueSet.size > 1) {
        // Found a conflict
        const nonEmptyValues = values.filter(
          v => v.value !== null && v.value !== undefined && v.value !== ''
        );

        conflicts.push({
          field: fieldPath.label,
          values: nonEmptyValues,
          resolvedValue: null,
          resolvedFrom: '',
          requiresReview: true,
        });
      }
    }

    return conflicts;
  }

  /**
   * Collect values for a specific field from all responses.
   */
  private collectFieldValues(
    responses: ExtractedDataResponse[],
    fieldPath: FieldPath
  ): ConflictValue[] {
    return responses.map(response => {
      const section = response.data[fieldPath.section] as unknown as Record<string, unknown>;
      const value = section?.[fieldPath.field];

      return {
        documentId: response.document_id,
        value: value ?? null,
        confidence: response.extraction_confidence,
      };
    });
  }

  /**
   * Resolve conflicts using the specified strategy.
   */
  private resolveConflicts(
    conflicts: DataConflict[],
    responses: ExtractedDataResponse[],
    strategy: ConflictResolutionStrategy
  ): DataConflict[] {
    return conflicts.map(conflict => {
      if (strategy === 'manual') {
        // Leave for manual resolution
        return conflict;
      }

      // Sort by strategy
      const sorted = [...conflict.values].sort((a, b) => {
        if (strategy === 'highest_confidence') {
          return b.confidence - a.confidence;
        }
        // latest_document - find response order
        const aIndex = responses.findIndex(r => r.document_id === a.documentId);
        const bIndex = responses.findIndex(r => r.document_id === b.documentId);
        return bIndex - aIndex;
      });

      const winner = sorted[0];
      const needsReview = winner.confidence < this.confidenceThreshold;

      return {
        ...conflict,
        resolvedValue: winner.value,
        resolvedFrom: winner.documentId,
        requiresReview: needsReview,
      };
    });
  }

  /**
   * Merge base data from multiple responses.
   */
  private mergeBaseData(
    responses: ExtractedDataResponse[],
    _strategy: ConflictResolutionStrategy
  ): ExtractedClaimData {
    // Use highest confidence response as base
    const sorted = [...responses].sort((a, b) => b.extraction_confidence - a.extraction_confidence);
    const base = sorted[0].data;

    // Merge arrays (diagnoses and procedures)
    const diagnoses = this.mergeDiagnoses(responses);
    const procedures = this.mergeProcedures(responses);

    // Calculate overall confidence
    const overall_confidence =
      responses.reduce((sum, r) => sum + r.extraction_confidence, 0) / responses.length;

    return {
      ...base,
      diagnoses,
      procedures,
      overall_confidence,
    };
  }

  /**
   * Merge diagnosis codes from multiple documents.
   * Deduplicates by code and keeps highest confidence.
   */
  private mergeDiagnoses(responses: ExtractedDataResponse[]): ExtractedDiagnosisCode[] {
    const diagMap = new Map<string, ExtractedDiagnosisCode>();

    for (const response of responses) {
      for (const diag of response.data.diagnoses) {
        const existing = diagMap.get(diag.code);
        if (!existing || diag.confidence > existing.confidence) {
          diagMap.set(diag.code, diag);
        }
      }
    }

    // Sort: primary first, then by confidence
    return Array.from(diagMap.values()).sort((a, b) => {
      if (a.is_primary !== b.is_primary) {
        return a.is_primary ? -1 : 1;
      }
      return b.confidence - a.confidence;
    });
  }

  /**
   * Merge procedure codes from multiple documents.
   * Deduplicates by code+date and keeps highest confidence.
   */
  private mergeProcedures(responses: ExtractedDataResponse[]): ExtractedProcedureCode[] {
    const procMap = new Map<string, ExtractedProcedureCode>();

    for (const response of responses) {
      for (const proc of response.data.procedures) {
        const key = `${proc.code}-${proc.service_date}`;
        const existing = procMap.get(key);
        if (!existing || proc.confidence > existing.confidence) {
          procMap.set(key, proc);
        }
      }
    }

    // Sort by service date, then by confidence
    return Array.from(procMap.values()).sort((a, b) => {
      const dateCompare = a.service_date.localeCompare(b.service_date);
      if (dateCompare !== 0) return dateCompare;
      return b.confidence - a.confidence;
    });
  }

  /**
   * Build field sources map showing which document each field came from.
   */
  private buildFieldSources(
    responses: ExtractedDataResponse[],
    conflicts: DataConflict[]
  ): Record<string, string> {
    const sources: Record<string, string> = {};

    // For conflicted fields, use resolved source
    for (const conflict of conflicts) {
      if (conflict.resolvedFrom) {
        sources[conflict.field] = conflict.resolvedFrom;
      }
    }

    // For non-conflicted fields, find first non-empty value
    for (const fieldPath of this.conflictFields) {
      if (!sources[fieldPath.label]) {
        for (const response of responses) {
          const section = response.data[fieldPath.section] as unknown as Record<string, unknown>;
          const value = section?.[fieldPath.field];
          if (value !== null && value !== undefined && value !== '') {
            sources[fieldPath.label] = response.document_id;
            break;
          }
        }
      }
    }

    return sources;
  }

  /**
   * Create merged data from a single response.
   */
  private createMergedFromSingle(response: ExtractedDataResponse): MergedExtractedData {
    const fieldSources: Record<string, string> = {};

    for (const fieldPath of this.conflictFields) {
      const section = response.data[fieldPath.section] as unknown as Record<string, unknown>;
      const value = section?.[fieldPath.field];
      if (value !== null && value !== undefined && value !== '') {
        fieldSources[fieldPath.label] = response.document_id;
      }
    }

    return {
      ...response.data,
      conflicts: [],
      fieldSources,
    };
  }

  /**
   * Create empty merged data structure.
   */
  private createEmptyMergedData(): MergedExtractedData {
    return {
      patient: {
        name: '',
        member_id: '',
        date_of_birth: '',
        gender: '',
        address: '',
      },
      provider: {
        name: '',
        npi: '',
        tax_id: '',
        specialty: '',
      },
      diagnoses: [],
      procedures: [],
      financial: {
        total_charged: '',
        currency: 'USD',
      },
      identifiers: {
        claim_number: '',
        prior_auth_number: '',
        policy_number: '',
      },
      dates: {
        service_date_from: '',
        service_date_to: '',
      },
      overall_confidence: 0,
      conflicts: [],
      fieldSources: {},
    };
  }

  /**
   * Apply manual conflict resolution.
   *
   * @param merged Current merged data
   * @param conflictField Field name of the conflict
   * @param value Resolved value
   * @param sourceId Source document ID
   * @returns Updated merged data
   */
  applyConflictResolution(
    merged: MergedExtractedData,
    conflictField: string,
    value: unknown,
    sourceId: string
  ): MergedExtractedData {
    const updatedConflicts = merged.conflicts.map(c => {
      if (c.field === conflictField) {
        return {
          ...c,
          resolvedValue: value,
          resolvedFrom: sourceId,
          requiresReview: false,
        };
      }
      return c;
    });

    const updatedSources = {
      ...merged.fieldSources,
      [conflictField]: sourceId,
    };

    // Apply value to the appropriate section
    const fieldPath = this.conflictFields.find(f => f.label === conflictField);
    let updatedMerged = { ...merged };

    if (fieldPath) {
      const section = { ...(merged[fieldPath.section] as unknown as Record<string, unknown>) };
      section[fieldPath.field] = value;
      updatedMerged = {
        ...updatedMerged,
        [fieldPath.section]: section,
      };
    }

    return {
      ...updatedMerged,
      conflicts: updatedConflicts,
      fieldSources: updatedSources,
    };
  }

  /**
   * Check if all conflicts are resolved.
   */
  areAllConflictsResolved(merged: MergedExtractedData): boolean {
    return merged.conflicts.every(c => c.resolvedValue !== null && !c.requiresReview);
  }

  /**
   * Get unresolved conflicts that require review.
   */
  getUnresolvedConflicts(merged: MergedExtractedData): DataConflict[] {
    return merged.conflicts.filter(c => c.requiresReview || c.resolvedValue === null);
  }

  /**
   * Calculate overall data quality score.
   */
  calculateQualityScore(merged: MergedExtractedData): number {
    const baseScore = merged.overall_confidence;
    const conflictPenalty = merged.conflicts.length * 0.02;
    const unresolvedPenalty = this.getUnresolvedConflicts(merged).length * 0.05;

    return Math.max(0, Math.min(1, baseScore - conflictPenalty - unresolvedPenalty));
  }

  /**
   * Validate merged data completeness.
   */
  validateCompleteness(merged: MergedExtractedData): string[] {
    const issues: string[] = [];

    // Required patient fields
    if (!merged.patient.name) {
      issues.push('Patient name is required');
    }
    if (!merged.patient.member_id) {
      issues.push('Member ID is required');
    }
    if (!merged.patient.date_of_birth) {
      issues.push('Date of birth is required');
    }

    // Required provider fields
    if (!merged.provider.name) {
      issues.push('Provider name is required');
    }
    if (!merged.provider.npi) {
      issues.push('Provider NPI is required');
    }

    // At least one diagnosis
    if (merged.diagnoses.length === 0) {
      issues.push('At least one diagnosis code is required');
    }

    // At least one procedure
    if (merged.procedures.length === 0) {
      issues.push('At least one procedure code is required');
    }

    // Financial
    if (!merged.financial.total_charged) {
      issues.push('Total charged amount is required');
    }

    return issues;
  }
}
