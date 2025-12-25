/**
 * Claims API Service.
 * Source: Design Document Section 4.1
 * Source: FastAPI Backend - src/api/routes/claims.py
 * Verified: 2025-12-18
 *
 * HTTP client for claims CRUD operations.
 * Integrates with FastAPI backend REST API.
 * Includes mock mode for development without backend.
 */
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of, delay } from 'rxjs';

import {
  Claim,
  ClaimCreate,
  ClaimUpdate,
  ClaimStatus,
  ClaimType,
  ClaimPriority,
  ClaimStats,
  ClaimValidationResult,
  ClaimAction,
} from '@claims-processing/models';
import { environment } from '../../../apps/claims-portal/src/environments/environment';

// Enable mock mode when backend is not available (development)
// Set to false to use real backend API even in development mode
const ENABLE_MOCK_API = false; // Disabled - always use real backend API

// In-memory store for mock claims (persists during session)
const mockClaimsStore: Map<string, Claim> = new Map();

// Initialize with sample mock claims
function initMockClaims(): void {
  if (mockClaimsStore.size > 0) return;

  const sampleClaims: Claim[] = [
    {
      id: 'CLM-00001',
      tracking_number: 'CLM-00001',
      policy_id: 'POL-001',
      member_id: 'MEM-001',
      provider_id: 'PRV-001',
      claim_type: ClaimType.PROFESSIONAL,
      status: ClaimStatus.APPROVED,
      priority: ClaimPriority.NORMAL,
      service_date_from: '2024-06-15',
      service_date_to: '2024-06-15',
      diagnosis_codes: ['J06.9'],
      primary_diagnosis: 'J06.9',
      total_charged: 250.00,
      total_allowed: 200.00,
      total_paid: 180.00,
      patient_responsibility: 20.00,
      line_items: [],
      created_at: '2024-06-15T10:00:00Z',
      updated_at: '2024-06-16T14:00:00Z',
    },
    {
      id: 'CLM-00002',
      tracking_number: 'CLM-00002',
      policy_id: 'POL-002',
      member_id: 'MEM-002',
      provider_id: 'PRV-002',
      claim_type: ClaimType.INSTITUTIONAL,
      status: ClaimStatus.SUBMITTED,
      priority: ClaimPriority.HIGH,
      service_date_from: '2024-06-20',
      service_date_to: '2024-06-22',
      diagnosis_codes: ['K21.0', 'R10.9'],
      primary_diagnosis: 'K21.0',
      total_charged: 1500.00,
      total_allowed: 1200.00,
      line_items: [],
      created_at: '2024-06-22T08:00:00Z',
      updated_at: '2024-06-22T08:00:00Z',
    },
    {
      id: 'CLM-00003',
      tracking_number: 'CLM-00003',
      policy_id: 'POL-001',
      member_id: 'MEM-003',
      provider_id: 'PRV-001',
      claim_type: ClaimType.PROFESSIONAL,
      status: ClaimStatus.DENIED,
      priority: ClaimPriority.LOW,
      service_date_from: '2024-06-10',
      service_date_to: '2024-06-10',
      diagnosis_codes: ['M54.5'],
      primary_diagnosis: 'M54.5',
      total_charged: 175.00,
      total_allowed: 0,
      total_paid: 0,
      line_items: [],
      created_at: '2024-06-10T09:00:00Z',
      updated_at: '2024-06-12T11:00:00Z',
    },
  ];

  sampleClaims.forEach(claim => mockClaimsStore.set(claim.id, claim));
}

/**
 * Paginated response from the API.
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

/**
 * Query parameters for claims list.
 */
export interface ClaimsQueryParams {
  status?: ClaimStatus;
  claimType?: ClaimType;
  priority?: ClaimPriority;
  search?: string;
  memberId?: string;
  providerId?: string;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  size?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

/**
 * Query parameters for claim statistics.
 */
export interface ClaimStatsParams {
  dateFrom?: string;
  dateTo?: string;
  groupBy?: 'day' | 'week' | 'month';
}

/**
 * Claims API Service.
 *
 * Provides HTTP methods for all claims-related operations.
 * All requests include credentials for HttpOnly cookie authentication.
 */
@Injectable({
  providedIn: 'root',
})
export class ClaimsApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/claims`;

  // ============================================================================
  // CRUD Operations
  // ============================================================================

  /**
   * Get paginated list of claims.
   * Source: GET /api/v1/claims
   */
  getClaims(params?: ClaimsQueryParams): Observable<PaginatedResponse<Claim>> {
    if (ENABLE_MOCK_API) {
      return this.getMockClaims(params);
    }

    let httpParams = new HttpParams();

    if (params) {
      if (params.status) {
        httpParams = httpParams.set('status', params.status);
      }
      if (params.claimType) {
        httpParams = httpParams.set('claim_type', params.claimType);
      }
      if (params.priority) {
        httpParams = httpParams.set('priority', params.priority);
      }
      if (params.search) {
        httpParams = httpParams.set('search', params.search);
      }
      if (params.memberId) {
        httpParams = httpParams.set('member_id', params.memberId);
      }
      if (params.providerId) {
        httpParams = httpParams.set('provider_id', params.providerId);
      }
      if (params.dateFrom) {
        httpParams = httpParams.set('date_from', params.dateFrom);
      }
      if (params.dateTo) {
        httpParams = httpParams.set('date_to', params.dateTo);
      }
      if (params.page !== undefined && !isNaN(params.page) && params.page > 0) {
        httpParams = httpParams.set('page', params.page.toString());
      }
      if (params.size !== undefined && !isNaN(params.size) && params.size > 0) {
        httpParams = httpParams.set('size', params.size.toString());
      }
      if (params.sortBy) {
        httpParams = httpParams.set('sort_by', params.sortBy);
      }
      if (params.sortOrder) {
        httpParams = httpParams.set('sort_order', params.sortOrder);
      }
    }

    return this.http.get<PaginatedResponse<Claim>>(this.baseUrl, {
      params: httpParams,
      withCredentials: true,
    });
  }

  /**
   * Mock getClaims for development.
   */
  private getMockClaims(params?: ClaimsQueryParams): Observable<PaginatedResponse<Claim>> {
    initMockClaims();

    let claims = Array.from(mockClaimsStore.values());

    // Apply filters
    if (params?.status) {
      claims = claims.filter(c => c.status === params.status);
    }
    if (params?.claimType) {
      claims = claims.filter(c => c.claim_type === params.claimType);
    }
    if (params?.search) {
      const search = params.search.toLowerCase();
      claims = claims.filter(c =>
        c.id.toLowerCase().includes(search) ||
        c.tracking_number.toLowerCase().includes(search) ||
        c.member_id.toLowerCase().includes(search)
      );
    }

    // Sort by created_at descending (newest first)
    claims.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    const page = params?.page || 1;
    const size = params?.size || 20;
    const start = (page - 1) * size;
    const paginatedClaims = claims.slice(start, start + size);

    console.log('Mock API: Returning', paginatedClaims.length, 'of', claims.length, 'claims');

    return of({
      items: paginatedClaims,
      total: claims.length,
      page,
      size,
    }).pipe(delay(300));
  }

  /**
   * Get a single claim by ID.
   * Source: GET /api/v1/claims/{id}
   */
  getClaim(claimId: string): Observable<Claim> {
    if (ENABLE_MOCK_API) {
      return this.getMockClaim(claimId);
    }
    return this.http.get<Claim>(`${this.baseUrl}/${claimId}`, {
      withCredentials: true,
    });
  }

  /**
   * Mock getClaim for development.
   */
  private getMockClaim(claimId: string): Observable<Claim> {
    initMockClaims();
    const claim = mockClaimsStore.get(claimId);
    if (claim) {
      return of(claim).pipe(delay(200));
    }
    return of(null as unknown as Claim).pipe(delay(200));
  }

  /**
   * Create a new claim.
   * Source: POST /api/v1/claims
   */
  createClaim(claim: ClaimCreate): Observable<Claim> {
    if (ENABLE_MOCK_API) {
      return this.createMockClaim(claim);
    }
    return this.http.post<Claim>(this.baseUrl, claim, {
      withCredentials: true,
    });
  }

  /**
   * Mock claim creation for development.
   */
  private createMockClaim(claimData: ClaimCreate): Observable<Claim> {
    const claimId = `CLM-${Date.now().toString().slice(-8)}`;
    const now = new Date().toISOString();

    const mockClaim: Claim = {
      id: claimId,
      tracking_number: claimId,
      // Use provided IDs or generate defaults for document-first workflow
      policy_id: claimData.policy_id || `POL-${Date.now().toString().slice(-6)}`,
      member_id: claimData.member_id || claimData.patient?.member_id || `MBR-${Date.now().toString().slice(-6)}`,
      provider_id: claimData.provider_id || `PRV-${Date.now().toString().slice(-6)}`,
      claim_type: claimData.claim_type,
      status: ClaimStatus.SUBMITTED,
      priority: ClaimPriority.NORMAL,
      service_date_from: claimData.service_date_from,
      service_date_to: claimData.service_date_to,
      diagnosis_codes: claimData.diagnosis_codes,
      primary_diagnosis: claimData.primary_diagnosis,
      total_charged: claimData.total_charged,
      total_allowed: claimData.total_charged * 0.8,
      total_paid: 0,
      patient_responsibility: claimData.total_charged * 0.2,
      place_of_service: claimData.place_of_service,
      prior_auth_number: claimData.prior_auth_number,
      line_items: (claimData.line_items || []).map((item, index) => ({
        id: `LI-${claimId}-${index + 1}`,
        line_number: index + 1,
        procedure_code: item.procedure_code,
        procedure_code_system: item.procedure_code_system || 'CPT-4',
        modifier_codes: item.modifier_codes,
        service_date: item.service_date,
        quantity: item.quantity,
        unit_price: item.unit_price,
        charged_amount: item.charged_amount,
        allowed_amount: item.charged_amount * 0.8,
        paid_amount: 0,
        denied: false,
      })),
      created_at: now,
      updated_at: now,
      submitted_at: now,
    };

    // Store in mock store so it appears in list
    mockClaimsStore.set(claimId, mockClaim);
    console.log('Mock API: Created claim', claimId);
    return of(mockClaim).pipe(delay(800));
  }

  /**
   * Update an existing claim.
   * Source: PATCH /api/v1/claims/{id}
   */
  updateClaim(claimId: string, updates: Partial<ClaimUpdate>): Observable<Claim> {
    return this.http.patch<Claim>(`${this.baseUrl}/${claimId}`, updates, {
      withCredentials: true,
    });
  }

  /**
   * Delete a claim.
   * Source: DELETE /api/v1/claims/{id}
   */
  deleteClaim(claimId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${claimId}`, {
      withCredentials: true,
    });
  }

  // ============================================================================
  // Workflow Operations
  // ============================================================================

  /**
   * Submit a draft claim for processing.
   * Source: POST /api/v1/claims/{id}/submit
   */
  submitClaim(claimId: string): Observable<Claim> {
    return this.http.post<Claim>(`${this.baseUrl}/${claimId}/submit`, {}, {
      withCredentials: true,
    });
  }

  /**
   * Approve a claim.
   * Source: POST /api/v1/claims/{id}/approve
   */
  approveClaim(claimId: string, action?: Partial<ClaimAction>): Observable<Claim> {
    return this.http.post<Claim>(`${this.baseUrl}/${claimId}/approve`, action || {}, {
      withCredentials: true,
    });
  }

  /**
   * Deny a claim.
   * Source: POST /api/v1/claims/{id}/deny
   */
  denyClaim(claimId: string, action: Partial<ClaimAction>): Observable<Claim> {
    return this.http.post<Claim>(`${this.baseUrl}/${claimId}/deny`, action, {
      withCredentials: true,
    });
  }

  /**
   * Validate a claim without submitting.
   * Source: POST /api/v1/claims/{id}/validate
   */
  validateClaim(claimId: string): Observable<ClaimValidationResult> {
    return this.http.post<ClaimValidationResult>(
      `${this.baseUrl}/${claimId}/validate`,
      {},
      { withCredentials: true }
    );
  }

  /**
   * Pend a claim for additional information.
   * Source: POST /api/v1/claims/{id}/pend
   */
  pendClaim(claimId: string, action: Partial<ClaimAction>): Observable<Claim> {
    return this.http.post<Claim>(`${this.baseUrl}/${claimId}/pend`, action, {
      withCredentials: true,
    });
  }

  /**
   * Void a claim.
   * Source: POST /api/v1/claims/{id}/void
   */
  voidClaim(claimId: string, action: Partial<ClaimAction>): Observable<Claim> {
    return this.http.post<Claim>(`${this.baseUrl}/${claimId}/void`, action, {
      withCredentials: true,
    });
  }

  // ============================================================================
  // Statistics & Reporting
  // ============================================================================

  /**
   * Get claim statistics summary.
   * Source: GET /api/v1/claims/stats/summary
   */
  getClaimStats(params?: ClaimStatsParams): Observable<ClaimStats> {
    let httpParams = new HttpParams();

    if (params) {
      if (params.dateFrom) {
        httpParams = httpParams.set('date_from', params.dateFrom);
      }
      if (params.dateTo) {
        httpParams = httpParams.set('date_to', params.dateTo);
      }
      if (params.groupBy) {
        httpParams = httpParams.set('group_by', params.groupBy);
      }
    }

    return this.http.get<ClaimStats>(`${this.baseUrl}/stats/summary`, {
      params: httpParams,
      withCredentials: true,
    });
  }

  // ============================================================================
  // Bulk Operations
  // ============================================================================

  /**
   * Bulk approve multiple claims.
   */
  bulkApprove(claimIds: string[], notes?: string): Observable<Claim[]> {
    return this.http.post<Claim[]>(
      `${this.baseUrl}/bulk/approve`,
      { claim_ids: claimIds, notes },
      { withCredentials: true }
    );
  }

  /**
   * Bulk deny multiple claims.
   */
  bulkDeny(claimIds: string[], reason: string, notes?: string): Observable<Claim[]> {
    return this.http.post<Claim[]>(
      `${this.baseUrl}/bulk/deny`,
      { claim_ids: claimIds, reason, notes },
      { withCredentials: true }
    );
  }

  /**
   * Export claims to CSV.
   */
  exportClaims(params?: ClaimsQueryParams): Observable<Blob> {
    let httpParams = new HttpParams();

    if (params?.status) {
      httpParams = httpParams.set('status', params.status);
    }
    if (params?.dateFrom) {
      httpParams = httpParams.set('date_from', params.dateFrom);
    }
    if (params?.dateTo) {
      httpParams = httpParams.set('date_to', params.dateTo);
    }

    return this.http.get(`${this.baseUrl}/export`, {
      params: httpParams,
      responseType: 'blob',
      withCredentials: true,
    });
  }
}
