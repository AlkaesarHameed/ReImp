/**
 * Claims Store - NgRx Signal Store.
 * Source: Design Document Section 3.2, 4.0
 * Source: @ngrx/signals documentation - https://ngrx.io/guide/signals
 * Verified: 2025-12-18
 *
 * Reactive state management for claims with computed selectors.
 * Optimized for 4000 claims/minute throughput.
 */
import { Injectable, computed, signal } from '@angular/core';
import {
  Claim,
  ClaimStatus,
  ClaimType,
  ClaimPriority,
} from '@claims-processing/models';

/**
 * Claim filters interface.
 */
export interface ClaimFilters {
  status?: ClaimStatus;
  claimType?: ClaimType;
  priority?: ClaimPriority;
  searchTerm?: string;
  dateFrom?: string;
  dateTo?: string;
  memberId?: string;
  providerId?: string;
}

/**
 * Real-time metrics from WebSocket.
 */
export interface ClaimMetrics {
  claims_per_minute: number;
  pending_count: number;
  processing_count: number;
  approved_today: number;
  denied_today: number;
}

/**
 * WebSocket claim update payload.
 */
export interface ClaimUpdateEvent {
  claim_id: string;
  status: ClaimStatus;
  tracking_number: string;
  updated_fields: string[];
}

/**
 * Claims Store using Angular Signals.
 *
 * Performance optimizations:
 * - Uses signals for fine-grained reactivity
 * - Memoized computed selectors
 * - Efficient array operations with immutable updates
 */
@Injectable({
  providedIn: 'root',
})
export class ClaimsStore {
  // ============================================================================
  // Private State Signals
  // ============================================================================

  private readonly _claims = signal<Claim[]>([]);
  private readonly _loading = signal<boolean>(false);
  private readonly _error = signal<string | null>(null);
  private readonly _selectedClaimId = signal<string | null>(null);
  private readonly _filters = signal<ClaimFilters>({});
  private readonly _pageSize = signal<number>(20);
  private readonly _currentPage = signal<number>(1);
  private readonly _metrics = signal<ClaimMetrics | null>(null);
  private readonly _totalRecords = signal<number>(0); // Server-side total for pagination

  // ============================================================================
  // Public Readonly Signals (State)
  // ============================================================================

  readonly claims = this._claims.asReadonly();
  readonly loading = this._loading.asReadonly();
  readonly error = this._error.asReadonly();
  readonly filters = this._filters.asReadonly();
  readonly pageSize = this._pageSize.asReadonly();
  readonly currentPage = this._currentPage.asReadonly();
  readonly metrics = this._metrics.asReadonly();
  readonly totalRecords = this._totalRecords.asReadonly(); // Server-side total for pagination

  // ============================================================================
  // Computed Selectors
  // ============================================================================

  /**
   * Currently selected claim.
   */
  readonly selectedClaim = computed(() => {
    const id = this._selectedClaimId();
    if (!id) return null;
    return this._claims().find((c) => c.id === id) ?? null;
  });

  /**
   * Total number of claims.
   */
  readonly totalCount = computed(() => this._claims().length);

  /**
   * Pending claims (submitted, validating, adjudicating, needs_review).
   */
  readonly pendingClaims = computed(() =>
    this._claims().filter((c) =>
      [
        ClaimStatus.SUBMITTED,
        ClaimStatus.VALIDATING,
        ClaimStatus.ADJUDICATING,
        ClaimStatus.NEEDS_REVIEW,
        ClaimStatus.DOC_PROCESSING,
      ].includes(c.status)
    )
  );

  /**
   * Approved claims.
   */
  readonly approvedClaims = computed(() =>
    this._claims().filter((c) =>
      [ClaimStatus.APPROVED, ClaimStatus.PAID, ClaimStatus.PAYMENT_PROCESSING].includes(c.status)
    )
  );

  /**
   * Denied claims.
   */
  readonly deniedClaims = computed(() =>
    this._claims().filter((c) => c.status === ClaimStatus.DENIED)
  );

  /**
   * Claims count by status - memoized for performance.
   */
  readonly claimsByStatus = computed(() => {
    const counts: Partial<Record<ClaimStatus, number>> = {};
    for (const claim of this._claims()) {
      counts[claim.status] = (counts[claim.status] || 0) + 1;
    }
    return counts;
  });

  /**
   * Total charged amount across all claims.
   */
  readonly totalCharged = computed(() =>
    this._claims().reduce((sum, c) => sum + (c.total_charged || 0), 0)
  );

  /**
   * Total paid amount across all claims.
   */
  readonly totalPaid = computed(() =>
    this._claims().reduce((sum, c) => sum + (c.total_paid || 0), 0)
  );

  /**
   * Filtered claims based on current filters.
   */
  readonly filteredClaims = computed(() => {
    const filters = this._filters();
    let result = this._claims();

    if (filters.status) {
      result = result.filter((c) => c.status === filters.status);
    }

    if (filters.claimType) {
      result = result.filter((c) => c.claim_type === filters.claimType);
    }

    if (filters.priority) {
      result = result.filter((c) => c.priority === filters.priority);
    }

    if (filters.searchTerm) {
      const term = filters.searchTerm.toLowerCase();
      result = result.filter(
        (c) =>
          c.tracking_number.toLowerCase().includes(term) ||
          c.member_id.toLowerCase().includes(term) ||
          c.provider_id.toLowerCase().includes(term)
      );
    }

    if (filters.memberId) {
      result = result.filter((c) => c.member_id === filters.memberId);
    }

    if (filters.providerId) {
      result = result.filter((c) => c.provider_id === filters.providerId);
    }

    if (filters.dateFrom) {
      result = result.filter((c) => c.service_date_from >= filters.dateFrom!);
    }

    if (filters.dateTo) {
      result = result.filter((c) => c.service_date_to <= filters.dateTo!);
    }

    return result;
  });

  /**
   * Total pages based on filtered claims and page size.
   */
  readonly totalPages = computed(() =>
    Math.ceil(this.filteredClaims().length / this._pageSize())
  );

  /**
   * Paginated claims for current page.
   */
  readonly paginatedClaims = computed(() => {
    const start = (this._currentPage() - 1) * this._pageSize();
    const end = start + this._pageSize();
    return this.filteredClaims().slice(start, end);
  });

  // ============================================================================
  // State Mutations
  // ============================================================================

  /**
   * Set claims and clear any existing error.
   */
  setClaims(claims: Claim[]): void {
    this._claims.set(claims);
    this._error.set(null);
  }

  /**
   * Set loading state.
   */
  setLoading(loading: boolean): void {
    this._loading.set(loading);
  }

  /**
   * Set error message.
   */
  setError(error: string | null): void {
    this._error.set(error);
    this._loading.set(false);
  }

  /**
   * Select a claim by ID.
   */
  selectClaim(claimId: string): void {
    this._selectedClaimId.set(claimId);
  }

  /**
   * Clear the current selection.
   */
  clearSelection(): void {
    this._selectedClaimId.set(null);
  }

  /**
   * Add a new claim to the store.
   */
  addClaim(claim: Claim): void {
    this._claims.update((claims) => [...claims, claim]);
  }

  /**
   * Update an existing claim.
   */
  updateClaim(claimId: string, updates: Partial<Claim>): void {
    this._claims.update((claims) =>
      claims.map((c) => (c.id === claimId ? { ...c, ...updates } : c))
    );
  }

  /**
   * Remove a claim from the store.
   */
  removeClaim(claimId: string): void {
    this._claims.update((claims) => claims.filter((c) => c.id !== claimId));
    // Clear selection if removed claim was selected
    if (this._selectedClaimId() === claimId) {
      this._selectedClaimId.set(null);
    }
  }

  /**
   * Set filters for claims.
   */
  setFilters(filters: ClaimFilters): void {
    this._filters.set(filters);
    // Reset to first page when filters change
    this._currentPage.set(1);
  }

  /**
   * Clear all filters.
   */
  clearFilters(): void {
    this._filters.set({});
    this._currentPage.set(1);
  }

  /**
   * Set page size for pagination.
   */
  setPageSize(size: number): void {
    this._pageSize.set(size);
    this._currentPage.set(1);
  }

  /**
   * Set current page.
   */
  setCurrentPage(page: number): void {
    this._currentPage.set(page);
  }

  /**
   * Set total records count from server-side pagination.
   */
  setTotalRecords(total: number): void {
    this._totalRecords.set(total);
  }

  // ============================================================================
  // WebSocket Event Handlers
  // ============================================================================

  /**
   * Handle real-time claim update from WebSocket.
   * Source: Design Document Section 4.2
   */
  handleClaimUpdate(event: ClaimUpdateEvent): void {
    this._claims.update((claims) =>
      claims.map((c) =>
        c.id === event.claim_id
          ? { ...c, status: event.status, updated_at: new Date().toISOString() }
          : c
      )
    );
  }

  /**
   * Update metrics from WebSocket.
   */
  updateMetrics(metrics: ClaimMetrics): void {
    this._metrics.set(metrics);
  }

  // ============================================================================
  // Batch Operations (for high-volume updates)
  // ============================================================================

  /**
   * Batch update multiple claims at once.
   * Optimized for handling 4000 claims/minute throughput.
   */
  batchUpdateClaims(updates: Array<{ id: string; changes: Partial<Claim> }>): void {
    const updateMap = new Map(updates.map((u) => [u.id, u.changes]));

    this._claims.update((claims) =>
      claims.map((c) => {
        const changes = updateMap.get(c.id);
        return changes ? { ...c, ...changes } : c;
      })
    );
  }

  /**
   * Batch add multiple claims.
   */
  batchAddClaims(newClaims: Claim[]): void {
    this._claims.update((claims) => [...claims, ...newClaims]);
  }
}
