/**
 * User Models.
 * Source: Design Document Section 4.1
 * Source: Phase 4 Implementation Document
 * Verified: 2025-12-18
 *
 * TypeScript interfaces for user management and RBAC.
 */

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  permissions: Permission[];
  status: UserStatus;
  created_at: string;
  updated_at: string;
  last_login?: string;
  locked_at?: string;
  failed_login_attempts: number;
}

export interface UserCreate {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role: UserRole;
}

export interface UserUpdate {
  first_name?: string;
  last_name?: string;
  role?: UserRole;
  status?: UserStatus;
}

export interface UserProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  permissions: Permission[];
}

export interface Role {
  id: string;
  name: UserRole;
  description: string;
  permissions: Permission[];
}

export interface Permission {
  id: string;
  name: string;
  description: string;
  resource: string;
  action: PermissionAction;
}

export enum UserRole {
  ADMIN = 'admin',
  SUPERVISOR = 'supervisor',
  CLAIMS_PROCESSOR = 'claims_processor',
  AUDITOR = 'auditor',
  READ_ONLY = 'read_only',
}

export enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  LOCKED = 'locked',
  PENDING = 'pending',
}

export type PermissionAction = 'create' | 'read' | 'update' | 'delete' | 'approve';

export interface UserQueryParams {
  search?: string;
  role?: UserRole;
  status?: UserStatus;
  page?: number;
  size?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface PasswordResetRequest {
  userId: string;
}

export interface PasswordChangeRequest {
  currentPassword: string;
  newPassword: string;
}

export interface UserActivityLog {
  id: string;
  userId: string;
  action: string;
  resource: string;
  resourceId?: string;
  timestamp: string;
  ipAddress?: string;
  userAgent?: string;
}

/**
 * Helper to get role display label.
 */
export function getRoleLabel(role: UserRole): string {
  const labels: Record<UserRole, string> = {
    [UserRole.ADMIN]: 'Administrator',
    [UserRole.SUPERVISOR]: 'Supervisor',
    [UserRole.CLAIMS_PROCESSOR]: 'Claims Processor',
    [UserRole.AUDITOR]: 'Auditor',
    [UserRole.READ_ONLY]: 'Read Only',
  };
  return labels[role] || role;
}

/**
 * Helper to get status color.
 */
export function getStatusColor(status: UserStatus): string {
  const colors: Record<UserStatus, string> = {
    [UserStatus.ACTIVE]: '#28A745',
    [UserStatus.INACTIVE]: '#6C757D',
    [UserStatus.LOCKED]: '#DC3545',
    [UserStatus.PENDING]: '#FFC107',
  };
  return colors[status] || '#6C757D';
}

/**
 * Helper to get status severity for PrimeNG tags.
 */
export function getStatusSeverity(status: UserStatus): 'success' | 'info' | 'warning' | 'danger' {
  const severities: Record<UserStatus, 'success' | 'info' | 'warning' | 'danger'> = {
    [UserStatus.ACTIVE]: 'success',
    [UserStatus.INACTIVE]: 'info',
    [UserStatus.LOCKED]: 'danger',
    [UserStatus.PENDING]: 'warning',
  };
  return severities[status] || 'info';
}
