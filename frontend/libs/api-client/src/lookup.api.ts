/**
 * Lookup API Service.
 * Source: Phase 3 Implementation Document
 * Source: FastAPI Backend - src/api/routes/lookup.py
 * Verified: 2025-12-18
 *
 * HTTP client for code lookup operations (ICD-10, CPT, HCPCS).
 * Includes caching for static lookup tables.
 */
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, shareReplay } from 'rxjs';

import {
  ICD10Code,
  CPTCode,
  HCPCSCode,
  PlaceOfServiceCode,
  DenialReasonCode,
  ModifierCode,
  LookupResponse,
  CodeValidationResult,
} from '@claims-processing/models';
import { environment } from '../../../apps/claims-portal/src/environments/environment';

/**
 * Lookup API Service.
 *
 * Provides HTTP methods for medical code lookups.
 * Static lookup tables (POS, denial reasons, modifiers) are cached.
 */
@Injectable({
  providedIn: 'root',
})
export class LookupApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/lookup`;

  // Cached observables for static data
  private posCodesCache$: Observable<PlaceOfServiceCode[]> | null = null;
  private denialReasonsCache$: Observable<DenialReasonCode[]> | null = null;
  private modifiersCache$: Observable<ModifierCode[]> | null = null;

  // ============================================================================
  // ICD-10 Diagnosis Codes
  // ============================================================================

  /**
   * Search ICD-10 codes by code or description.
   * Source: GET /api/v1/lookup/icd10
   */
  searchICD10(query: string, limit: number = 20): Observable<LookupResponse<ICD10Code>> {
    let params = new HttpParams().set('q', query);

    if (limit) {
      params = params.set('limit', limit.toString());
    }

    return this.http.get<LookupResponse<ICD10Code>>(`${this.baseUrl}/icd10`, {
      params,
      withCredentials: true,
    });
  }

  /**
   * Validate a specific ICD-10 code.
   * Source: GET /api/v1/lookup/icd10/{code}/validate
   */
  validateICD10(code: string): Observable<CodeValidationResult> {
    return this.http.get<CodeValidationResult>(
      `${this.baseUrl}/icd10/${encodeURIComponent(code)}/validate`,
      { withCredentials: true }
    );
  }

  /**
   * Get ICD-10 code details.
   * Source: GET /api/v1/lookup/icd10/{code}
   */
  getICD10Code(code: string): Observable<ICD10Code> {
    return this.http.get<ICD10Code>(
      `${this.baseUrl}/icd10/${encodeURIComponent(code)}`,
      { withCredentials: true }
    );
  }

  // ============================================================================
  // CPT Procedure Codes
  // ============================================================================

  /**
   * Search CPT codes by code or description.
   * Source: GET /api/v1/lookup/cpt
   */
  searchCPT(query: string, limit: number = 20): Observable<LookupResponse<CPTCode>> {
    let params = new HttpParams().set('q', query);

    if (limit) {
      params = params.set('limit', limit.toString());
    }

    return this.http.get<LookupResponse<CPTCode>>(`${this.baseUrl}/cpt`, {
      params,
      withCredentials: true,
    });
  }

  /**
   * Validate a specific CPT code.
   * Source: GET /api/v1/lookup/cpt/{code}/validate
   */
  validateCPT(code: string): Observable<CodeValidationResult> {
    return this.http.get<CodeValidationResult>(
      `${this.baseUrl}/cpt/${encodeURIComponent(code)}/validate`,
      { withCredentials: true }
    );
  }

  /**
   * Get CPT code details.
   * Source: GET /api/v1/lookup/cpt/{code}
   */
  getCPTCode(code: string): Observable<CPTCode> {
    return this.http.get<CPTCode>(
      `${this.baseUrl}/cpt/${encodeURIComponent(code)}`,
      { withCredentials: true }
    );
  }

  // ============================================================================
  // HCPCS Codes
  // ============================================================================

  /**
   * Search HCPCS codes by code or description.
   * Source: GET /api/v1/lookup/hcpcs
   */
  searchHCPCS(query: string, limit: number = 20): Observable<LookupResponse<HCPCSCode>> {
    let params = new HttpParams().set('q', query);

    if (limit) {
      params = params.set('limit', limit.toString());
    }

    return this.http.get<LookupResponse<HCPCSCode>>(`${this.baseUrl}/hcpcs`, {
      params,
      withCredentials: true,
    });
  }

  /**
   * Validate a specific HCPCS code.
   * Source: GET /api/v1/lookup/hcpcs/{code}/validate
   */
  validateHCPCS(code: string): Observable<CodeValidationResult> {
    return this.http.get<CodeValidationResult>(
      `${this.baseUrl}/hcpcs/${encodeURIComponent(code)}/validate`,
      { withCredentials: true }
    );
  }

  /**
   * Get HCPCS code details.
   * Source: GET /api/v1/lookup/hcpcs/{code}
   */
  getHCPCSCode(code: string): Observable<HCPCSCode> {
    return this.http.get<HCPCSCode>(
      `${this.baseUrl}/hcpcs/${encodeURIComponent(code)}`,
      { withCredentials: true }
    );
  }

  // ============================================================================
  // Place of Service Codes (Cached)
  // ============================================================================

  /**
   * Get all Place of Service codes.
   * Source: GET /api/v1/lookup/pos
   *
   * Results are cached for the lifetime of the service.
   */
  getPlaceOfServiceCodes(): Observable<PlaceOfServiceCode[]> {
    if (!this.posCodesCache$) {
      this.posCodesCache$ = this.http
        .get<PlaceOfServiceCode[]>(`${this.baseUrl}/pos`, {
          withCredentials: true,
        })
        .pipe(shareReplay(1));
    }
    return this.posCodesCache$;
  }

  // ============================================================================
  // Denial Reason Codes (Cached)
  // ============================================================================

  /**
   * Get denial reason codes.
   * Source: GET /api/v1/lookup/denial-reasons
   *
   * @param category Optional category filter
   */
  getDenialReasonCodes(category?: string): Observable<DenialReasonCode[]> {
    if (category) {
      // Don't use cache when filtering by category
      const params = new HttpParams().set('category', category);
      return this.http.get<DenialReasonCode[]>(`${this.baseUrl}/denial-reasons`, {
        params,
        withCredentials: true,
      });
    }

    // Use cache for unfiltered requests
    if (!this.denialReasonsCache$) {
      this.denialReasonsCache$ = this.http
        .get<DenialReasonCode[]>(`${this.baseUrl}/denial-reasons`, {
          withCredentials: true,
        })
        .pipe(shareReplay(1));
    }
    return this.denialReasonsCache$;
  }

  // ============================================================================
  // Modifier Codes (Cached)
  // ============================================================================

  /**
   * Get modifier codes.
   * Source: GET /api/v1/lookup/modifiers
   *
   * @param system Optional filter by code system (CPT or HCPCS)
   */
  getModifierCodes(system?: 'CPT' | 'HCPCS'): Observable<ModifierCode[]> {
    if (system) {
      // Don't use cache when filtering by system
      const params = new HttpParams().set('system', system);
      return this.http.get<ModifierCode[]>(`${this.baseUrl}/modifiers`, {
        params,
        withCredentials: true,
      });
    }

    // Use cache for unfiltered requests
    if (!this.modifiersCache$) {
      this.modifiersCache$ = this.http
        .get<ModifierCode[]>(`${this.baseUrl}/modifiers`, {
          withCredentials: true,
        })
        .pipe(shareReplay(1));
    }
    return this.modifiersCache$;
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  /**
   * Clear all caches (useful for testing or after updates).
   */
  clearCaches(): void {
    this.posCodesCache$ = null;
    this.denialReasonsCache$ = null;
    this.modifiersCache$ = null;
  }

  /**
   * Validate any code type.
   */
  validateCode(
    code: string,
    codeType: 'ICD10' | 'CPT' | 'HCPCS'
  ): Observable<CodeValidationResult> {
    switch (codeType) {
      case 'ICD10':
        return this.validateICD10(code);
      case 'CPT':
        return this.validateCPT(code);
      case 'HCPCS':
        return this.validateHCPCS(code);
    }
  }

  /**
   * Search any code type.
   */
  searchCodes(
    query: string,
    codeType: 'ICD10' | 'CPT' | 'HCPCS',
    limit: number = 20
  ): Observable<LookupResponse<ICD10Code | CPTCode | HCPCSCode>> {
    switch (codeType) {
      case 'ICD10':
        return this.searchICD10(query, limit);
      case 'CPT':
        return this.searchCPT(query, limit);
      case 'HCPCS':
        return this.searchHCPCS(query, limit);
    }
  }
}
