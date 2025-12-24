/**
 * Document Processing Models.
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Verified: 2025-12-19
 *
 * Models for document upload, processing status, and extracted data.
 * Supports the enhanced claims input workflow with PDF processing.
 */

// =============================================================================
// Document Type Enums
// =============================================================================

export type DocumentType =
  | 'policy'
  | 'claim_form'
  | 'invoice'
  | 'medical_record'
  | 'id_document'
  | 'other';

export type DocumentStatus = 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';

export type ProcessingStage =
  | 'upload'
  | 'ocr'
  | 'parsing'
  | 'validation'
  | 'complete'
  | 'failed';

// =============================================================================
// Upload Request/Response Models
// =============================================================================

export interface BatchUploadResponse {
  total: number;
  successful: number;
  failed: number;
  documents: DocumentUploadResult[];
}

export interface DocumentUploadResult {
  document_id: string;
  status: 'accepted' | 'failed';
  message: string;
  is_duplicate: boolean;
  processing_started: boolean;
}

// =============================================================================
// Processing Status Models
// =============================================================================

export interface DocumentProcessingStatus {
  document_id: string;
  status: DocumentStatus;
  processing_stage: ProcessingStage;
  progress_percent: number;
  ocr_confidence?: number;
  parsing_confidence?: number;
  needs_review: boolean;
  error?: string;
}

// =============================================================================
// Extracted Data Models
// =============================================================================

export interface ExtractedDataResponse {
  document_id: string;
  extraction_confidence: number;
  data: ExtractedClaimData;
  needs_review: boolean;
  validation_issues: string[];
}

export interface ExtractedClaimData {
  patient: ExtractedPatientData;
  provider: ExtractedProviderData;
  diagnoses: ExtractedDiagnosisCode[];
  procedures: ExtractedProcedureCode[];
  line_items?: ExtractedLineItem[];  // Invoice line items (medications, supplies, services)
  financial: ExtractedFinancialData;
  identifiers: ExtractedIdentifiers;
  dates: ExtractedDates;
  overall_confidence: number;
}

export interface ExtractedPatientData {
  name: string;
  member_id: string;
  date_of_birth: string;
  gender: string;
  address: string;
}

export interface ExtractedProviderData {
  name: string;
  npi: string;
  tax_id: string;
  specialty: string;
}

export interface ExtractedDiagnosisCode {
  code: string;
  description: string;
  is_primary: boolean;
  confidence: number;
}

export interface ExtractedProcedureCode {
  code: string;
  description: string;
  modifiers: string[];
  quantity: number;
  charged_amount: string;
  service_date: string;
  confidence: number;
}

/**
 * Line item from invoice/hospital bill extraction.
 * Represents itemized charges including medications, supplies, services.
 */
export interface ExtractedLineItem {
  sl_no: number;
  date: string;
  description: string;
  sac_code: string;
  quantity: number;
  rate: string;
  gross_value: string;
  discount: string;
  total_value: string;
  category: string;
  confidence: number;
}

export interface ExtractedFinancialData {
  total_charged: string;
  currency: string;
}

export interface ExtractedIdentifiers {
  claim_number: string;
  prior_auth_number: string;
  policy_number: string;
}

export interface ExtractedDates {
  service_date_from: string;
  service_date_to: string;
}

// =============================================================================
// Frontend State Models
// =============================================================================

export interface DocumentUploadState {
  id: string;
  file: File;
  filename: string;
  fileSize: number;
  documentType: DocumentType;
  documentId?: string;
  status: DocumentStatus;
  progressPercent: number;
  processingStage?: ProcessingStage;
  extractedData?: ExtractedClaimData;
  needsReview: boolean;
  ocrConfidence?: number;
  parsingConfidence?: number;
  error?: string;
  uploadedAt?: Date;
  processedAt?: Date;
}

export interface MergedExtractedData extends ExtractedClaimData {
  conflicts: DataConflict[];
  fieldSources: Record<string, string>;
}

export interface DataConflict {
  field: string;
  values: ConflictValue[];
  resolvedValue: unknown;
  resolvedFrom: string;
  requiresReview: boolean;
}

export interface ConflictValue {
  documentId: string;
  value: unknown;
  confidence: number;
}

// =============================================================================
// Form State Extension
// =============================================================================

export interface DocumentsFormState {
  policyDocuments: DocumentUploadState[];
  claimDocuments: DocumentUploadState[];
}

export interface ProcessingResultsState {
  mergedData: MergedExtractedData | null;
  allDocumentsProcessed: boolean;
  processingComplete: boolean;
  validationIssues: string[];
  overallConfidence: number;
  needsReview: boolean;
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get severity color for confidence score.
 */
export function getConfidenceSeverity(confidence: number): 'success' | 'warning' | 'danger' {
  if (confidence >= 0.85) return 'success';
  if (confidence >= 0.70) return 'warning';
  return 'danger';
}

/**
 * Get status severity for PrimeNG components.
 */
export function getDocumentStatusSeverity(
  status: DocumentStatus
): 'success' | 'info' | 'warn' | 'danger' | 'secondary' {
  switch (status) {
    case 'completed':
      return 'success';
    case 'processing':
    case 'uploading':
      return 'info';
    case 'pending':
      return 'secondary';
    case 'failed':
      return 'danger';
    default:
      return 'secondary';
  }
}

/**
 * Get human-readable label for processing stage.
 */
export function getProcessingStageLabel(stage: ProcessingStage): string {
  switch (stage) {
    case 'upload':
      return 'Uploading document...';
    case 'ocr':
      return 'Extracting text from document...';
    case 'parsing':
      return 'Analyzing and extracting data...';
    case 'validation':
      return 'Validating extracted information...';
    case 'complete':
      return 'Processing complete';
    case 'failed':
      return 'Processing failed';
    default:
      return 'Processing...';
  }
}

/**
 * Get human-readable label for document type.
 */
export function getDocumentTypeLabel(type: DocumentType): string {
  switch (type) {
    case 'policy':
      return 'Insurance Policy';
    case 'claim_form':
      return 'Claim Form';
    case 'invoice':
      return 'Invoice/Bill';
    case 'medical_record':
      return 'Medical Records';
    case 'id_document':
      return 'ID Document';
    case 'other':
      return 'Other Document';
    default:
      return 'Document';
  }
}

/**
 * Format file size for display.
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Validate file for upload.
 */
export interface FileValidationResult {
  valid: boolean;
  error?: string;
  sanitizedName?: string;
}

export function validatePdfFile(file: File, maxSizeBytes: number = 50 * 1024 * 1024): FileValidationResult {
  const allowedMimeTypes = ['application/pdf'];
  const allowedExtensions = ['.pdf'];

  // Check extension
  const extension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
  if (!allowedExtensions.includes(extension)) {
    return { valid: false, error: 'Only PDF files are allowed' };
  }

  // Check MIME type
  if (!allowedMimeTypes.includes(file.type)) {
    return { valid: false, error: 'Invalid file type. Please upload a PDF file.' };
  }

  // Check size
  if (file.size > maxSizeBytes) {
    return { valid: false, error: `File exceeds ${formatFileSize(maxSizeBytes)} limit` };
  }

  // Sanitize filename for display
  const sanitizedName = file.name.replace(/[<>:"/\\|?*]/g, '_');

  return { valid: true, sanitizedName };
}

/**
 * Create initial document upload state from file.
 */
export function createDocumentUploadState(
  file: File,
  documentType: DocumentType
): DocumentUploadState {
  return {
    id: crypto.randomUUID(),
    file,
    filename: file.name,
    fileSize: file.size,
    documentType,
    status: 'pending',
    progressPercent: 0,
    needsReview: false,
  };
}
