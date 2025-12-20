/**
 * Users API Service.
 * Source: Design Document Section 4.1
 * Source: Phase 4 Implementation Document
 * Verified: 2025-12-18
 *
 * HTTP client for user management operations.
 */
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  User,
  UserCreate,
  UserUpdate,
  UserQueryParams,
  UserActivityLog,
  Role,
  Permission,
} from '@claims-processing/models';
import { environment } from '../../../apps/claims-portal/src/environments/environment';
import { PaginatedResponse } from './claims.api';

/**
 * Users API Service.
 *
 * Provides HTTP methods for user management and RBAC operations.
 */
@Injectable({
  providedIn: 'root',
})
export class UsersApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/users`;
  private readonly rolesUrl = `${environment.apiUrl}/roles`;
  private readonly permissionsUrl = `${environment.apiUrl}/permissions`;

  // ============================================================================
  // User CRUD Operations
  // ============================================================================

  /**
   * Get paginated list of users.
   * Source: GET /api/v1/users
   */
  getUsers(params?: UserQueryParams): Observable<PaginatedResponse<User>> {
    let httpParams = new HttpParams();

    if (params) {
      if (params.search) {
        httpParams = httpParams.set('search', params.search);
      }
      if (params.role) {
        httpParams = httpParams.set('role', params.role);
      }
      if (params.status) {
        httpParams = httpParams.set('status', params.status);
      }
      if (params.page !== undefined) {
        httpParams = httpParams.set('page', params.page.toString());
      }
      if (params.size !== undefined) {
        httpParams = httpParams.set('size', params.size.toString());
      }
      if (params.sortBy) {
        httpParams = httpParams.set('sort_by', params.sortBy);
      }
      if (params.sortOrder) {
        httpParams = httpParams.set('sort_order', params.sortOrder);
      }
    }

    return this.http.get<PaginatedResponse<User>>(this.baseUrl, {
      params: httpParams,
      withCredentials: true,
    });
  }

  /**
   * Get a single user by ID.
   * Source: GET /api/v1/users/{id}
   */
  getUser(userId: string): Observable<User> {
    return this.http.get<User>(`${this.baseUrl}/${userId}`, {
      withCredentials: true,
    });
  }

  /**
   * Create a new user.
   * Source: POST /api/v1/users
   */
  createUser(user: UserCreate): Observable<User> {
    return this.http.post<User>(this.baseUrl, user, {
      withCredentials: true,
    });
  }

  /**
   * Update an existing user.
   * Source: PATCH /api/v1/users/{id}
   */
  updateUser(userId: string, updates: UserUpdate): Observable<User> {
    return this.http.patch<User>(`${this.baseUrl}/${userId}`, updates, {
      withCredentials: true,
    });
  }

  /**
   * Delete a user.
   * Source: DELETE /api/v1/users/{id}
   */
  deleteUser(userId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${userId}`, {
      withCredentials: true,
    });
  }

  // ============================================================================
  // Account Management
  // ============================================================================

  /**
   * Reset user password.
   * Source: POST /api/v1/users/{id}/reset-password
   */
  resetPassword(userId: string): Observable<{ success: boolean }> {
    return this.http.post<{ success: boolean }>(
      `${this.baseUrl}/${userId}/reset-password`,
      {},
      { withCredentials: true }
    );
  }

  /**
   * Lock user account.
   * Source: POST /api/v1/users/{id}/lock
   */
  lockUser(userId: string): Observable<User> {
    return this.http.post<User>(
      `${this.baseUrl}/${userId}/lock`,
      {},
      { withCredentials: true }
    );
  }

  /**
   * Unlock user account.
   * Source: POST /api/v1/users/{id}/unlock
   */
  unlockUser(userId: string): Observable<User> {
    return this.http.post<User>(
      `${this.baseUrl}/${userId}/unlock`,
      {},
      { withCredentials: true }
    );
  }

  // ============================================================================
  // Roles and Permissions
  // ============================================================================

  /**
   * Get available roles.
   * Source: GET /api/v1/roles
   */
  getRoles(): Observable<Role[]> {
    return this.http.get<Role[]>(this.rolesUrl, {
      withCredentials: true,
    });
  }

  /**
   * Get available permissions.
   * Source: GET /api/v1/permissions
   */
  getPermissions(): Observable<Permission[]> {
    return this.http.get<Permission[]>(this.permissionsUrl, {
      withCredentials: true,
    });
  }

  // ============================================================================
  // Activity Logging
  // ============================================================================

  /**
   * Get user activity log.
   * Source: GET /api/v1/users/{id}/activity
   */
  getUserActivityLog(
    userId: string,
    params?: { page?: number; size?: number; dateFrom?: string; dateTo?: string }
  ): Observable<UserActivityLog[]> {
    let httpParams = new HttpParams();

    if (params) {
      if (params.page !== undefined) {
        httpParams = httpParams.set('page', params.page.toString());
      }
      if (params.size !== undefined) {
        httpParams = httpParams.set('size', params.size.toString());
      }
      if (params.dateFrom) {
        httpParams = httpParams.set('date_from', params.dateFrom);
      }
      if (params.dateTo) {
        httpParams = httpParams.set('date_to', params.dateTo);
      }
    }

    return this.http.get<UserActivityLog[]>(
      `${this.baseUrl}/${userId}/activity`,
      {
        params: httpParams,
        withCredentials: true,
      }
    );
  }
}
