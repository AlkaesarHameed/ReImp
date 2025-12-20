/**
 * Eligibility API Service.
 * Source: Design Document Section 4.1
 * Source: Phase 4 Implementation Document
 * Verified: 2025-12-18
 *
 * HTTP client for eligibility verification operations.
 */
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  EligibilityCheck,
  EligibilityResponse,
  EligibilityHistory,
  BatchEligibilityCheck,
  BatchEligibilityResponse,
} from '@claims-processing/models';
import { environment } from '../../../apps/claims-portal/src/environments/environment';

/**
 * Member search result for eligibility lookup.
 */
export interface MemberSearchResult {
  id: string;
  name: string;
  memberId: string;
  dob: string;
  policyNumber?: string;
}

/**
 * Eligibility API Service.
 *
 * Provides HTTP methods for eligibility verification.
 */
@Injectable({
  providedIn: 'root',
})
export class EligibilityApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/eligibility`;
  private readonly membersUrl = `${environment.apiUrl}/members`;

  // ============================================================================
  // Eligibility Verification
  // ============================================================================

  /**
   * Check member eligibility for a date of service.
   * Source: GET /api/v1/eligibility/{memberId}
   */
  checkEligibility(check: EligibilityCheck): Observable<EligibilityResponse> {
    let params = new HttpParams()
      .set('date_of_service', check.dateOfService);

    if (check.providerId) {
      params = params.set('provider_id', check.providerId);
    }
    if (check.serviceType) {
      params = params.set('service_type', check.serviceType);
    }

    return this.http.get<EligibilityResponse>(
      `${this.baseUrl}/${check.memberId}`,
      {
        params,
        withCredentials: true,
      }
    );
  }

  /**
   * Batch eligibility check for multiple members.
   * Source: POST /api/v1/eligibility/batch
   */
  batchCheckEligibility(
    checks: EligibilityCheck[]
  ): Observable<BatchEligibilityResponse> {
    const request: BatchEligibilityCheck = { checks };

    return this.http.post<BatchEligibilityResponse>(
      `${this.baseUrl}/batch`,
      request,
      { withCredentials: true }
    );
  }

  // ============================================================================
  // Benefits Information
  // ============================================================================

  /**
   * Get detailed benefits for a member.
   * Source: GET /api/v1/eligibility/{memberId}/benefits
   */
  getBenefits(
    memberId: string,
    dateOfService?: string
  ): Observable<EligibilityResponse> {
    let params = new HttpParams();

    if (dateOfService) {
      params = params.set('date_of_service', dateOfService);
    }

    return this.http.get<EligibilityResponse>(
      `${this.baseUrl}/${memberId}/benefits`,
      {
        params,
        withCredentials: true,
      }
    );
  }

  // ============================================================================
  // Eligibility History
  // ============================================================================

  /**
   * Get eligibility verification history for a member.
   * Source: GET /api/v1/eligibility/{memberId}/history
   */
  getEligibilityHistory(
    memberId: string,
    params?: { page?: number; size?: number; dateFrom?: string; dateTo?: string }
  ): Observable<EligibilityHistory> {
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

    return this.http.get<EligibilityHistory>(
      `${this.baseUrl}/${memberId}/history`,
      {
        params: httpParams,
        withCredentials: true,
      }
    );
  }

  // ============================================================================
  // Member Search (for eligibility lookup)
  // ============================================================================

  /**
   * Search members for eligibility check.
   * Source: GET /api/v1/members/search
   */
  searchMembers(
    query: string,
    limit: number = 20
  ): Observable<MemberSearchResult[]> {
    const params = new HttpParams()
      .set('q', query)
      .set('limit', limit.toString());

    return this.http.get<MemberSearchResult[]>(`${this.membersUrl}/search`, {
      params,
      withCredentials: true,
    });
  }
}
