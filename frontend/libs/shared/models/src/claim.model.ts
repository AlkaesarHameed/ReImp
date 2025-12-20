/**
 * Claim Models.
 * Source: Design Document Section 4.1
 *
 * TypeScript interfaces matching the FastAPI backend schemas.
 */

export interface Claim {
  id: string;
  tracking_number: string;
  claim_type: ClaimType;
  status: ClaimStatus;
  priority: ClaimPriority;
  policy_id: string;
  member_id: string;
  provider_id: string;
  service_date_from: string;
  service_date_to: string;
  diagnosis_codes: string[];
  primary_diagnosis: string;
  total_charged: number;
  total_allowed?: number;
  total_paid?: number;
  patient_responsibility?: number;
  fwa_score?: number;
  fwa_risk_level?: FWARiskLevel;
  line_items: ClaimLineItem[];
  documents?: ClaimDocument[];
  notes?: ClaimNote[];
  created_at: string;
  updated_at: string;
  submitted_at?: string;
  processed_at?: string;
  place_of_service?: string;
  prior_auth_number?: string;
  referring_provider_id?: string;
}

/**
 * Patient information for claim submission.
 * Fields are optional to support document-first workflow.
 */
export interface PatientInfo {
  member_id?: string;
  first_name?: string;
  last_name?: string;
  date_of_birth?: string;
  relationship?: string;
}

/**
 * Provider information for claim submission.
 * NPI is optional to support document-first workflow.
 */
export interface ProviderInfoCreate {
  npi?: string;
  name?: string;
  tax_id?: string;
}

/**
 * Claim creation payload.
 * Patient and provider are optional to support document-first workflow
 * where claims are submitted from extracted document data.
 */
export interface ClaimCreate {
  // Optional references for document-first workflow
  policy_id?: string;
  member_id?: string;
  provider_id?: string;
  patient?: PatientInfo;
  provider?: ProviderInfoCreate;
  billing_provider?: ProviderInfoCreate;
  referring_provider?: ProviderInfoCreate;
  // Required fields
  claim_type: ClaimType;
  service_date_from: string;
  service_date_to: string;
  diagnosis_codes: string[];
  primary_diagnosis: string;
  total_charged: number;
  line_items: ClaimLineItemCreate[];
  // Optional fields
  source?: ClaimSource;
  priority?: ClaimPriority;
  place_of_service?: string;
  prior_auth_number?: string;
  referring_provider_id?: string;
}

export interface ClaimUpdate {
  status?: ClaimStatus;
  priority?: ClaimPriority;
  diagnosis_codes?: string[];
  primary_diagnosis?: string;
  total_charged?: number;
  notes?: string;
}

export interface ClaimLineItem {
  id: string;
  line_number: number;
  procedure_code: string;
  procedure_code_system: string;
  modifier_codes?: string[];
  service_date: string;
  quantity: number;
  unit_price: number;
  charged_amount: number;
  allowed_amount?: number;
  paid_amount?: number;
  denied: boolean;
  denial_reason?: string;
  adjustment_reason?: string;
}

export interface ClaimLineItemCreate {
  procedure_code: string;
  procedure_code_system?: string;
  modifier_codes?: string[];
  service_date: string;
  quantity: number;
  unit_price: number;
  charged_amount: number;
}

export interface ClaimDocument {
  id: string;
  document_type: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  uploaded_at: string;
  uploaded_by: string;
}

export interface ClaimNote {
  id: string;
  note_type: 'internal' | 'external';
  content: string;
  created_at: string;
  created_by: string;
}

export interface ClaimAction {
  action: 'approve' | 'deny' | 'pend' | 'void';
  reason?: string;
  notes?: string;
}

export interface ClaimValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface ValidationError {
  field: string;
  code: string;
  message: string;
}

export interface ValidationWarning {
  field: string;
  code: string;
  message: string;
}

export interface ClaimStats {
  total_claims: number;
  pending_count: number;
  approved_count: number;
  denied_count: number;
  processing_count: number;
  total_billed: number;
  total_paid: number;
  approval_rate: number;
  average_processing_time: number;
}

export enum ClaimStatus {
  DRAFT = 'draft',
  SUBMITTED = 'submitted',
  DOC_PROCESSING = 'doc_processing',
  VALIDATING = 'validating',
  ADJUDICATING = 'adjudicating',
  APPROVED = 'approved',
  DENIED = 'denied',
  PAYMENT_PROCESSING = 'payment_processing',
  PAID = 'paid',
  CLOSED = 'closed',
  NEEDS_REVIEW = 'needs_review',
  VOID = 'void',
}

export enum ClaimType {
  PROFESSIONAL = 'professional',
  INSTITUTIONAL = 'institutional',
  DENTAL = 'dental',
  PHARMACY = 'pharmacy',
}

export enum ClaimPriority {
  LOW = 'low',
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent',
}

export enum ClaimSource {
  PORTAL = 'portal',
  EDI = 'edi',
  API = 'api',
  PAPER = 'paper',
}

export enum FWARiskLevel {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

// Helper functions
export function getStatusColor(status: ClaimStatus): string {
  const colors: Record<ClaimStatus, string> = {
    [ClaimStatus.DRAFT]: '#6C757D',
    [ClaimStatus.SUBMITTED]: '#17A2B8',
    [ClaimStatus.DOC_PROCESSING]: '#17A2B8',
    [ClaimStatus.VALIDATING]: '#17A2B8',
    [ClaimStatus.ADJUDICATING]: '#FFC107',
    [ClaimStatus.APPROVED]: '#28A745',
    [ClaimStatus.DENIED]: '#DC3545',
    [ClaimStatus.PAYMENT_PROCESSING]: '#17A2B8',
    [ClaimStatus.PAID]: '#28A745',
    [ClaimStatus.CLOSED]: '#6C757D',
    [ClaimStatus.NEEDS_REVIEW]: '#FFC107',
    [ClaimStatus.VOID]: '#DC3545',
  };
  return colors[status] || '#6C757D';
}

export function getStatusLabel(status: ClaimStatus): string {
  const labels: Record<ClaimStatus, string> = {
    [ClaimStatus.DRAFT]: 'Draft',
    [ClaimStatus.SUBMITTED]: 'Submitted',
    [ClaimStatus.DOC_PROCESSING]: 'Processing Documents',
    [ClaimStatus.VALIDATING]: 'Validating',
    [ClaimStatus.ADJUDICATING]: 'Adjudicating',
    [ClaimStatus.APPROVED]: 'Approved',
    [ClaimStatus.DENIED]: 'Denied',
    [ClaimStatus.PAYMENT_PROCESSING]: 'Processing Payment',
    [ClaimStatus.PAID]: 'Paid',
    [ClaimStatus.CLOSED]: 'Closed',
    [ClaimStatus.NEEDS_REVIEW]: 'Needs Review',
    [ClaimStatus.VOID]: 'Void',
  };
  return labels[status] || status;
}
