/**
 * Shared Models Library.
 * Source: Design Document Section 3.4
 *
 * Note: Some types may exist in multiple models. The order of exports
 * determines which version is used for conflicting names.
 */

// Claim models (primary source)
export * from './claim.model';

// Member models
export {
  Member,
  MemberCreate,
  Address,
  AddressCreate,
  EligibilityRequest,
  EligibilityResponse,
  PolicySummary,
  CoverageDetails,
  BenefitSummary,
  Gender,
  RelationshipType,
  MemberStatus,
  getMemberFullName,
  formatMemberId,
  maskSSN,
} from './member.model';

// Provider models
export {
  Provider,
  ProviderCreate,
  ProviderAddress,
  ProviderAddressCreate,
  ProviderSearchParams,
  ProviderType,
  ProviderStatus,
  NetworkStatus,
  getProviderDisplayName,
  formatNPI,
  isInNetwork,
  getNetworkStatusLabel,
} from './provider.model';

// Policy models
export * from './policy.model';

// Lookup models
export * from './lookup.model';

// User models (rename getStatusColor to avoid conflict with claim.model)
export {
  User,
  UserCreate,
  UserUpdate,
  UserProfile,
  Role,
  Permission,
  UserRole,
  UserStatus,
  UserQueryParams,
  PasswordResetRequest,
  PasswordChangeRequest,
  UserActivityLog,
  getRoleLabel,
  getStatusColor as getUserStatusColor,
  getStatusSeverity,
} from './user.model';
export type { PermissionAction } from './user.model';

// Eligibility models (additional types not conflicting with other exports)
export {
  EligibilityCheck,
  EligibilityResult,
  EligibilityHistory,
  EligibilityHistoryRecord,
  BatchEligibilityCheck,
  BatchEligibilityResponse,
  BenefitsSummary,
  CopaySchedule,
  CoverageDetail,
  Accumulators,
  AccumulatorValue,
  CoverageStatus,
  CoverageType,
  ServiceType,
  getCoverageStatusLabel,
  getCoverageStatusSeverity,
  formatAccumulator,
  getServiceTypeLabel,
} from './eligibility.model';
// Note: NetworkStatus and EligibilityResponse are exported from provider.model and member.model respectively

// Document processing models
export * from './document-processing.model';
