/**
 * Policy Models.
 * Source: Design Document Section 4.1
 */

export interface Policy {
  id: string;
  policy_id: string;
  policy_name: string;
  policy_number: string;
  plan_type: PlanType;
  group_id?: string;
  group_name?: string;
  effective_date: string;
  termination_date?: string;
  status: PolicyStatus;
  deductible: number;
  out_of_pocket_max: number;
  coinsurance_in_network: number;
  coinsurance_out_network: number;
  copay_primary_care?: number;
  copay_specialist?: number;
  copay_emergency?: number;
  copay_urgent_care?: number;
  network_ids: string[];
  benefits: PolicyBenefit[];
  exclusions: string[];
  created_at: string;
  updated_at: string;
}

export interface PolicyCreate {
  policy_name: string;
  policy_number: string;
  plan_type: PlanType;
  group_id?: string;
  group_name?: string;
  effective_date: string;
  termination_date?: string;
  deductible: number;
  out_of_pocket_max: number;
  coinsurance_in_network: number;
  coinsurance_out_network: number;
  copay_primary_care?: number;
  copay_specialist?: number;
  copay_emergency?: number;
  copay_urgent_care?: number;
  network_ids?: string[];
}

export interface PolicyBenefit {
  id: string;
  service_category: string;
  service_code?: string;
  covered: boolean;
  requires_prior_auth: boolean;
  cost_share_type: CostShareType;
  cost_share_amount: number;
  annual_limit?: number;
  lifetime_limit?: number;
  waiting_period_days?: number;
  notes?: string;
}

export interface PolicyBenefitCreate {
  service_category: string;
  service_code?: string;
  covered: boolean;
  requires_prior_auth?: boolean;
  cost_share_type: CostShareType;
  cost_share_amount: number;
  annual_limit?: number;
  lifetime_limit?: number;
  waiting_period_days?: number;
  notes?: string;
}

export enum PlanType {
  HMO = 'hmo',
  PPO = 'ppo',
  EPO = 'epo',
  POS = 'pos',
  HDHP = 'hdhp',
  INDEMNITY = 'indemnity',
}

export enum PolicyStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  PENDING = 'pending',
  TERMINATED = 'terminated',
  SUSPENDED = 'suspended',
}

export enum CostShareType {
  COPAY = 'copay',
  COINSURANCE = 'coinsurance',
  DEDUCTIBLE = 'deductible',
  NOT_COVERED = 'not_covered',
}

// Helper functions
export function getPlanTypeLabel(type: PlanType): string {
  const labels: Record<PlanType, string> = {
    [PlanType.HMO]: 'HMO (Health Maintenance Organization)',
    [PlanType.PPO]: 'PPO (Preferred Provider Organization)',
    [PlanType.EPO]: 'EPO (Exclusive Provider Organization)',
    [PlanType.POS]: 'POS (Point of Service)',
    [PlanType.HDHP]: 'HDHP (High Deductible Health Plan)',
    [PlanType.INDEMNITY]: 'Indemnity',
  };
  return labels[type] || type;
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

export function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

export function isPolicyActive(policy: Policy): boolean {
  if (policy.status !== PolicyStatus.ACTIVE) {
    return false;
  }
  const today = new Date();
  const effectiveDate = new Date(policy.effective_date);
  if (effectiveDate > today) {
    return false;
  }
  if (policy.termination_date) {
    const terminationDate = new Date(policy.termination_date);
    if (terminationDate < today) {
      return false;
    }
  }
  return true;
}
