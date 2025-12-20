/**
 * Member Models.
 * Source: Design Document Section 4.1
 */

export interface Member {
  id: string;
  member_id: string;
  first_name: string;
  last_name: string;
  middle_name?: string;
  date_of_birth: string;
  gender: Gender;
  ssn_last_four?: string;
  email?: string;
  phone?: string;
  address: Address;
  policy_id: string;
  subscriber_id?: string;
  relationship_to_subscriber: RelationshipType;
  coverage_start_date: string;
  coverage_end_date?: string;
  status: MemberStatus;
  created_at: string;
  updated_at: string;
}

export interface MemberCreate {
  first_name: string;
  last_name: string;
  middle_name?: string;
  date_of_birth: string;
  gender: Gender;
  ssn?: string;
  email?: string;
  phone?: string;
  address: AddressCreate;
  policy_id: string;
  subscriber_id?: string;
  relationship_to_subscriber: RelationshipType;
  coverage_start_date: string;
  coverage_end_date?: string;
}

export interface Address {
  line1: string;
  line2?: string;
  city: string;
  state: string;
  zip_code: string;
  country: string;
}

export interface AddressCreate {
  line1: string;
  line2?: string;
  city: string;
  state: string;
  zip_code: string;
  country?: string;
}

export interface EligibilityRequest {
  member_id: string;
  service_date?: string;
  service_type?: string;
}

export interface EligibilityResponse {
  eligible: boolean;
  member: Member;
  policy: PolicySummary;
  coverage: CoverageDetails;
  benefits: BenefitSummary[];
  effective_date: string;
  termination_date?: string;
  limitations?: string[];
}

export interface PolicySummary {
  policy_id: string;
  policy_name: string;
  plan_type: string;
  group_number?: string;
}

export interface CoverageDetails {
  deductible: number;
  deductible_met: number;
  out_of_pocket_max: number;
  out_of_pocket_met: number;
  coinsurance_rate: number;
  copay_amounts: Record<string, number>;
}

export interface BenefitSummary {
  service_type: string;
  covered: boolean;
  requires_prior_auth: boolean;
  in_network_cost_share: number;
  out_network_cost_share: number;
  annual_limit?: number;
  lifetime_limit?: number;
}

export enum Gender {
  MALE = 'male',
  FEMALE = 'female',
  OTHER = 'other',
  UNKNOWN = 'unknown',
}

export enum RelationshipType {
  SELF = 'self',
  SPOUSE = 'spouse',
  CHILD = 'child',
  DOMESTIC_PARTNER = 'domestic_partner',
  OTHER = 'other',
}

export enum MemberStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  PENDING = 'pending',
  TERMINATED = 'terminated',
}

// Helper functions
export function getMemberFullName(member: Member): string {
  const parts = [member.first_name];
  if (member.middle_name) {
    parts.push(member.middle_name);
  }
  parts.push(member.last_name);
  return parts.join(' ');
}

export function formatMemberId(member: Member): string {
  return member.member_id;
}

export function maskSSN(ssn: string): string {
  if (!ssn || ssn.length < 4) return '***-**-****';
  return `***-**-${ssn.slice(-4)}`;
}
