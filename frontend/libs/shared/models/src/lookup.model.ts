/**
 * Lookup Models.
 * Source: Design Document Section 4.1
 * Source: Phase 3 Implementation Document
 * Verified: 2025-12-18
 *
 * TypeScript interfaces for code lookup services (ICD-10, CPT, HCPCS).
 */

/**
 * ICD-10 Diagnosis Code.
 */
export interface ICD10Code {
  code: string;
  description: string;
  category: string;
  isHeader: boolean;
  isBillable: boolean;
}

/**
 * CPT Procedure Code.
 */
export interface CPTCode {
  code: string;
  description: string;
  category: string;
  shortDescription: string;
  relativeValue?: number;
}

/**
 * HCPCS Code.
 */
export interface HCPCSCode {
  code: string;
  description: string;
  category: string;
  shortDescription: string;
  pricingIndicator?: string;
}

/**
 * Place of Service Code.
 */
export interface PlaceOfServiceCode {
  code: string;
  name: string;
  description: string;
}

/**
 * Denial Reason Code.
 */
export interface DenialReasonCode {
  code: string;
  description: string;
  category: 'medical' | 'administrative' | 'eligibility' | 'other';
}

/**
 * Modifier Code.
 */
export interface ModifierCode {
  code: string;
  description: string;
  applicableTo: ('CPT' | 'HCPCS')[];
}

/**
 * Generic lookup response wrapper.
 */
export interface LookupResponse<T> {
  items: T[];
  total: number;
  query: string;
}

/**
 * Lookup query parameters.
 */
export interface LookupQueryParams {
  q: string;
  limit?: number;
  offset?: number;
}

/**
 * Code validation result.
 */
export interface CodeValidationResult {
  code: string;
  valid: boolean;
  message?: string;
  suggestions?: string[];
}

/**
 * Claim form state for wizard.
 */
export interface ClaimFormState {
  currentStep: number;
  isDirty: boolean;
  isValid: boolean;
  draftId?: string;

  // Step 1: Member
  member: MemberStepData;

  // Step 2: Provider
  provider: ProviderStepData;

  // Step 3: Services
  services: ServicesStepData;

  // Validation
  validationErrors: FormValidationError[];
  validationWarnings: FormValidationWarning[];
}

export interface MemberStepData {
  memberId: string;
  policyId: string;
  eligibilityVerified: boolean;
  eligibilityResponse?: EligibilityCheckResponse;
}

export interface ProviderStepData {
  providerId: string;
  providerNPI: string;
  placeOfService: string;
  priorAuthNumber?: string;
  referringProviderId?: string;
}

export interface ServicesStepData {
  serviceDateFrom: Date | string;
  serviceDateTo: Date | string;
  diagnosisCodes: string[];
  primaryDiagnosis: string;
  lineItems: ClaimLineItemForm[];
}

export interface ClaimLineItemForm {
  id?: string;
  procedureCode: string;
  procedureCodeSystem: 'CPT' | 'HCPCS';
  modifiers: string[];
  serviceDate: Date | string | null;
  quantity: number;
  unitPrice: number;
  chargedAmount: number;
  diagnosisPointers: number[];
}

export interface EligibilityCheckResponse {
  eligible: boolean;
  effectiveDate: string;
  terminationDate?: string;
  coverageType: string;
  copay?: number;
  deductible?: number;
  deductibleMet?: number;
  outOfPocketMax?: number;
  outOfPocketMet?: number;
}

export interface FormValidationError {
  step: number;
  field: string;
  code: string;
  message: string;
}

export interface FormValidationWarning {
  step: number;
  field: string;
  code: string;
  message: string;
}

/**
 * Review workflow types.
 */
export interface ReviewAction {
  action: 'approve' | 'deny' | 'pend' | 'void';
  reason?: string;
  notes?: string;
  denialCode?: string;
}

export interface ReviewQueueFilters {
  priority?: string;
  claimType?: string;
  dateFrom?: string;
  dateTo?: string;
  assignedTo?: string;
}

/**
 * Document upload types.
 */
export interface ClaimDocumentUpload {
  file: File;
  documentType: ClaimDocumentType;
  description?: string;
}

/**
 * Legacy document type for claim attachments.
 * Note: For document processing, use DocumentType from document-processing.model instead.
 */
export type ClaimDocumentType =
  | 'medical_record'
  | 'itemized_bill'
  | 'eob'
  | 'prior_auth'
  | 'referral'
  | 'other';

export interface UploadProgress {
  fileName: string;
  progress: number;
  status: 'pending' | 'uploading' | 'complete' | 'error';
  error?: string;
}

/**
 * Initial form state factory.
 */
export function createInitialClaimFormState(): ClaimFormState {
  return {
    currentStep: 0,
    isDirty: false,
    isValid: false,
    member: {
      memberId: '',
      policyId: '',
      eligibilityVerified: false,
    },
    provider: {
      providerId: '',
      providerNPI: '',
      placeOfService: '',
    },
    services: {
      serviceDateFrom: '',
      serviceDateTo: '',
      diagnosisCodes: [],
      primaryDiagnosis: '',
      lineItems: [],
    },
    validationErrors: [],
    validationWarnings: [],
  };
}

/**
 * Create empty line item.
 */
export function createEmptyLineItem(): ClaimLineItemForm {
  return {
    procedureCode: '',
    procedureCodeSystem: 'CPT',
    modifiers: [],
    serviceDate: null,
    quantity: 1,
    unitPrice: 0,
    chargedAmount: 0,
    diagnosisPointers: [1],
  };
}
