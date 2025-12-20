/**
 * Eligibility Models.
 * Source: Design Document Section 4.1
 * Source: Phase 4 Implementation Document
 * Verified: 2025-12-18
 *
 * TypeScript interfaces for eligibility verification.
 */

export interface EligibilityCheck {
  memberId: string;
  dateOfService: string;
  providerId?: string;
  serviceType?: ServiceType;
}

export interface EligibilityResponse {
  memberId: string;
  memberName: string;
  policyId: string;
  policyNumber: string;
  groupId?: string;
  groupName?: string;

  // Coverage Status
  eligible: boolean;
  effectiveDate: string;
  terminationDate?: string;
  coverageStatus: CoverageStatus;
  coverageType: CoverageType;

  // Network Status
  networkStatus?: NetworkStatus;

  // Benefits Summary
  benefits: BenefitsSummary;

  // Accumulators
  accumulators: Accumulators;

  // Prior Auth Requirements
  priorAuthRequired: boolean;
  priorAuthNote?: string;

  // Verification Info
  verifiedAt: string;
  verificationSource: string;
}

export interface BenefitsSummary {
  planName: string;
  planType: string;

  // Deductible
  individualDeductible: number;
  individualDeductibleMet: number;
  familyDeductible: number;
  familyDeductibleMet: number;

  // Out of Pocket
  individualOopMax: number;
  individualOopMet: number;
  familyOopMax: number;
  familyOopMet: number;

  // Copays by service type
  copays: CopaySchedule[];

  // Coinsurance
  inNetworkCoinsurance: number;
  outOfNetworkCoinsurance: number;

  // Coverage Details
  coverageDetails: CoverageDetail[];
}

export interface CopaySchedule {
  serviceType: ServiceType;
  copayAmount: number;
  coinsurancePercent?: number;
  notes?: string;
}

export interface CoverageDetail {
  serviceType: ServiceType;
  covered: boolean;
  requiresPreAuth: boolean;
  limitType?: 'visits' | 'days' | 'amount';
  limitValue?: number;
  limitUsed?: number;
  notes?: string;
}

export interface Accumulators {
  deductibleIndividual: AccumulatorValue;
  deductibleFamily: AccumulatorValue;
  oopIndividual: AccumulatorValue;
  oopFamily: AccumulatorValue;
  asOfDate: string;
}

export interface AccumulatorValue {
  limit: number;
  used: number;
  remaining: number;
  percentUsed: number;
}

export interface EligibilityHistory {
  memberId: string;
  records: EligibilityHistoryRecord[];
}

export interface EligibilityHistoryRecord {
  id: string;
  checkDate: string;
  dateOfService: string;
  eligible: boolean;
  coverageStatus: CoverageStatus;
  checkedBy: string;
  notes?: string;
}

export interface BatchEligibilityCheck {
  checks: EligibilityCheck[];
}

export interface BatchEligibilityResponse {
  results: EligibilityResult[];
  successCount: number;
  failureCount: number;
}

export interface EligibilityResult {
  memberId: string;
  success: boolean;
  response?: EligibilityResponse;
  error?: string;
}

export enum CoverageStatus {
  ACTIVE = 'active',
  TERMINATED = 'terminated',
  COBRA = 'cobra',
  PENDING = 'pending',
  SUSPENDED = 'suspended',
}

export enum CoverageType {
  MEDICAL = 'medical',
  DENTAL = 'dental',
  VISION = 'vision',
  PHARMACY = 'pharmacy',
  BEHAVIORAL = 'behavioral',
}

export enum NetworkStatus {
  IN_NETWORK = 'in_network',
  OUT_OF_NETWORK = 'out_of_network',
  TIER_1 = 'tier_1',
  TIER_2 = 'tier_2',
}

export enum ServiceType {
  OFFICE_VISIT = 'office_visit',
  SPECIALIST = 'specialist',
  URGENT_CARE = 'urgent_care',
  EMERGENCY = 'emergency',
  INPATIENT = 'inpatient',
  OUTPATIENT = 'outpatient',
  LAB = 'lab',
  IMAGING = 'imaging',
  PREVENTIVE = 'preventive',
  MENTAL_HEALTH = 'mental_health',
  PHYSICAL_THERAPY = 'physical_therapy',
  PRESCRIPTION = 'prescription',
  DURABLE_MEDICAL = 'durable_medical',
}

/**
 * Helper to get coverage status label.
 */
export function getCoverageStatusLabel(status: CoverageStatus): string {
  const labels: Record<CoverageStatus, string> = {
    [CoverageStatus.ACTIVE]: 'Active',
    [CoverageStatus.TERMINATED]: 'Terminated',
    [CoverageStatus.COBRA]: 'COBRA',
    [CoverageStatus.PENDING]: 'Pending',
    [CoverageStatus.SUSPENDED]: 'Suspended',
  };
  return labels[status] || status;
}

/**
 * Helper to get coverage status severity.
 */
export function getCoverageStatusSeverity(status: CoverageStatus): 'success' | 'info' | 'warning' | 'danger' {
  const severities: Record<CoverageStatus, 'success' | 'info' | 'warning' | 'danger'> = {
    [CoverageStatus.ACTIVE]: 'success',
    [CoverageStatus.TERMINATED]: 'danger',
    [CoverageStatus.COBRA]: 'warning',
    [CoverageStatus.PENDING]: 'info',
    [CoverageStatus.SUSPENDED]: 'warning',
  };
  return severities[status] || 'info';
}

/**
 * Helper to format currency.
 */
export function formatAccumulator(accumulator: AccumulatorValue): string {
  return `$${accumulator.used.toLocaleString()} / $${accumulator.limit.toLocaleString()}`;
}

/**
 * Helper to get service type label.
 */
export function getServiceTypeLabel(type: ServiceType): string {
  const labels: Record<ServiceType, string> = {
    [ServiceType.OFFICE_VISIT]: 'Office Visit',
    [ServiceType.SPECIALIST]: 'Specialist',
    [ServiceType.URGENT_CARE]: 'Urgent Care',
    [ServiceType.EMERGENCY]: 'Emergency Room',
    [ServiceType.INPATIENT]: 'Inpatient',
    [ServiceType.OUTPATIENT]: 'Outpatient',
    [ServiceType.LAB]: 'Lab/Pathology',
    [ServiceType.IMAGING]: 'Imaging/Radiology',
    [ServiceType.PREVENTIVE]: 'Preventive Care',
    [ServiceType.MENTAL_HEALTH]: 'Mental Health',
    [ServiceType.PHYSICAL_THERAPY]: 'Physical Therapy',
    [ServiceType.PRESCRIPTION]: 'Prescription Drugs',
    [ServiceType.DURABLE_MEDICAL]: 'Durable Medical Equipment',
  };
  return labels[type] || type;
}
