/**
 * Provider Models.
 * Source: Design Document Section 4.1
 */

export interface Provider {
  id: string;
  provider_id: string;
  npi: string;
  tax_id?: string;
  name: string;
  first_name?: string;
  last_name?: string;
  provider_type: ProviderType;
  specialty?: string;
  specialty_code?: string;
  address: ProviderAddress;
  phone?: string;
  fax?: string;
  email?: string;
  network_status: NetworkStatus;
  network_ids: string[];
  effective_date: string;
  termination_date?: string;
  status: ProviderStatus;
  license_number?: string;
  license_state?: string;
  license_expiry?: string;
  board_certified: boolean;
  accepting_new_patients: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProviderCreate {
  npi: string;
  tax_id?: string;
  name: string;
  first_name?: string;
  last_name?: string;
  provider_type: ProviderType;
  specialty?: string;
  specialty_code?: string;
  address: ProviderAddressCreate;
  phone?: string;
  fax?: string;
  email?: string;
  network_status?: NetworkStatus;
  network_ids?: string[];
  effective_date: string;
  termination_date?: string;
  license_number?: string;
  license_state?: string;
  license_expiry?: string;
  board_certified?: boolean;
  accepting_new_patients?: boolean;
}

export interface ProviderAddress {
  line1: string;
  line2?: string;
  city: string;
  state: string;
  zip_code: string;
  country: string;
}

export interface ProviderAddressCreate {
  line1: string;
  line2?: string;
  city: string;
  state: string;
  zip_code: string;
  country?: string;
}

export interface ProviderSearchParams {
  name?: string;
  npi?: string;
  specialty?: string;
  city?: string;
  state?: string;
  network_id?: string;
  accepting_new_patients?: boolean;
  limit?: number;
  offset?: number;
}

export enum ProviderType {
  INDIVIDUAL = 'individual',
  ORGANIZATION = 'organization',
  FACILITY = 'facility',
}

export enum ProviderStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  PENDING = 'pending',
  SUSPENDED = 'suspended',
  TERMINATED = 'terminated',
}

export enum NetworkStatus {
  IN_NETWORK = 'in_network',
  OUT_OF_NETWORK = 'out_of_network',
  PREFERRED = 'preferred',
  NON_PARTICIPATING = 'non_participating',
}

// Helper functions
export function getProviderDisplayName(provider: Provider): string {
  if (provider.provider_type === ProviderType.INDIVIDUAL) {
    return `${provider.first_name || ''} ${provider.last_name || provider.name}`.trim();
  }
  return provider.name;
}

export function formatNPI(npi: string): string {
  return npi;
}

export function isInNetwork(provider: Provider): boolean {
  return (
    provider.network_status === NetworkStatus.IN_NETWORK ||
    provider.network_status === NetworkStatus.PREFERRED
  );
}

export function getNetworkStatusLabel(status: NetworkStatus): string {
  const labels: Record<NetworkStatus, string> = {
    [NetworkStatus.IN_NETWORK]: 'In-Network',
    [NetworkStatus.OUT_OF_NETWORK]: 'Out-of-Network',
    [NetworkStatus.PREFERRED]: 'Preferred',
    [NetworkStatus.NON_PARTICIPATING]: 'Non-Participating',
  };
  return labels[status] || status;
}
