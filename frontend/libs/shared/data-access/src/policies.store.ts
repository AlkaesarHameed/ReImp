/**
 * Policies Store - NgRx Signal Store.
 * Source: Design Document Section 3.2, 4.0
 * Source: Phase 4 Implementation Document
 * Verified: 2025-12-18
 *
 * Reactive state management for policies with computed selectors.
 */
import { Injectable, computed, signal } from '@angular/core';
import { Policy, PolicyStatus, PlanType } from '@claims-processing/models';

/**
 * Policy filters interface.
 */
export interface PolicyFilters {
  status?: PolicyStatus;
  policyType?: PlanType;
  searchTerm?: string;
  effectiveFrom?: string;
  effectiveTo?: string;
  groupId?: string;
}

/**
 * Policies Store using Angular Signals.
 */
@Injectable({
  providedIn: 'root',
})
export class PoliciesStore {
  // ============================================================================
  // Private State Signals
  // ============================================================================

  private readonly _policies = signal<Policy[]>([]);
  private readonly _loading = signal<boolean>(false);
  private readonly _error = signal<string | null>(null);
  private readonly _selectedPolicyId = signal<string | null>(null);
  private readonly _filters = signal<PolicyFilters>({});
  private readonly _pageSize = signal<number>(20);
  private readonly _currentPage = signal<number>(1);
  private readonly _totalCount = signal<number>(0);

  // ============================================================================
  // Public Readonly Signals (State)
  // ============================================================================

  readonly policies = this._policies.asReadonly();
  readonly loading = this._loading.asReadonly();
  readonly error = this._error.asReadonly();
  readonly filters = this._filters.asReadonly();
  readonly pageSize = this._pageSize.asReadonly();
  readonly currentPage = this._currentPage.asReadonly();
  readonly totalCount = this._totalCount.asReadonly();

  // ============================================================================
  // Computed Selectors
  // ============================================================================

  /**
   * Currently selected policy.
   */
  readonly selectedPolicy = computed(() => {
    const id = this._selectedPolicyId();
    if (!id) return null;
    return this._policies().find((p) => p.id === id) ?? null;
  });

  /**
   * Active policies.
   */
  readonly activePolicies = computed(() =>
    this._policies().filter((p) => p.status === PolicyStatus.ACTIVE)
  );

  /**
   * Policies expiring soon (within 30 days).
   */
  readonly expiringPolicies = computed(() => {
    const thirtyDaysFromNow = new Date();
    thirtyDaysFromNow.setDate(thirtyDaysFromNow.getDate() + 30);
    const threshold = thirtyDaysFromNow.toISOString().split('T')[0];

    return this._policies().filter(
      (p) =>
        p.status === PolicyStatus.ACTIVE &&
        p.termination_date &&
        p.termination_date <= threshold
    );
  });

  /**
   * Policies count by status.
   */
  readonly policiesByStatus = computed(() => {
    const counts: Partial<Record<PolicyStatus, number>> = {};
    for (const policy of this._policies()) {
      counts[policy.status] = (counts[policy.status] || 0) + 1;
    }
    return counts;
  });

  /**
   * Policies count by type.
   */
  readonly policiesByType = computed(() => {
    const counts: Partial<Record<PlanType, number>> = {};
    for (const policy of this._policies()) {
      counts[policy.plan_type] = (counts[policy.plan_type] || 0) + 1;
    }
    return counts;
  });

  /**
   * Unique groups for filtering.
   */
  readonly uniqueGroups = computed(() => {
    const groups = new Map<string, string>();
    for (const policy of this._policies()) {
      if (policy.group_id && policy.group_name) {
        groups.set(policy.group_id, policy.group_name);
      }
    }
    return Array.from(groups.entries()).map(([id, name]) => ({ id, name }));
  });

  /**
   * Filtered policies based on current filters.
   */
  readonly filteredPolicies = computed(() => {
    const filters = this._filters();
    let result = this._policies();

    if (filters.status) {
      result = result.filter((p) => p.status === filters.status);
    }

    if (filters.policyType) {
      result = result.filter((p) => p.plan_type === filters.policyType);
    }

    if (filters.groupId) {
      result = result.filter((p) => p.group_id === filters.groupId);
    }

    if (filters.effectiveFrom) {
      result = result.filter((p) => p.effective_date >= filters.effectiveFrom!);
    }

    if (filters.effectiveTo) {
      result = result.filter(
        (p) => !p.termination_date || p.termination_date <= filters.effectiveTo!
      );
    }

    if (filters.searchTerm) {
      const term = filters.searchTerm.toLowerCase();
      result = result.filter(
        (p) =>
          p.policy_number.toLowerCase().includes(term) ||
          p.policy_name.toLowerCase().includes(term) ||
          p.group_name?.toLowerCase().includes(term)
      );
    }

    return result;
  });

  /**
   * Total pages based on total count and page size.
   */
  readonly totalPages = computed(() =>
    Math.ceil(this._totalCount() / this._pageSize())
  );

  // ============================================================================
  // State Mutations
  // ============================================================================

  /**
   * Set policies and clear any existing error.
   */
  setPolicies(policies: Policy[]): void {
    this._policies.set(policies);
    this._error.set(null);
  }

  /**
   * Set total count for pagination.
   */
  setTotalCount(count: number): void {
    this._totalCount.set(count);
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
   * Select a policy by ID.
   */
  selectPolicy(policyId: string): void {
    this._selectedPolicyId.set(policyId);
  }

  /**
   * Clear the current selection.
   */
  clearSelection(): void {
    this._selectedPolicyId.set(null);
  }

  /**
   * Add a new policy to the store.
   */
  addPolicy(policy: Policy): void {
    this._policies.update((policies) => [...policies, policy]);
    this._totalCount.update((count) => count + 1);
  }

  /**
   * Update an existing policy.
   */
  updatePolicy(policyId: string, updates: Partial<Policy>): void {
    this._policies.update((policies) =>
      policies.map((p) => (p.id === policyId ? { ...p, ...updates } : p))
    );
  }

  /**
   * Remove a policy from the store.
   */
  removePolicy(policyId: string): void {
    this._policies.update((policies) => policies.filter((p) => p.id !== policyId));
    this._totalCount.update((count) => Math.max(0, count - 1));
    if (this._selectedPolicyId() === policyId) {
      this._selectedPolicyId.set(null);
    }
  }

  /**
   * Set filters for policies.
   */
  setFilters(filters: PolicyFilters): void {
    this._filters.set(filters);
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
   * Reset store to initial state.
   */
  reset(): void {
    this._policies.set([]);
    this._loading.set(false);
    this._error.set(null);
    this._selectedPolicyId.set(null);
    this._filters.set({});
    this._pageSize.set(20);
    this._currentPage.set(1);
    this._totalCount.set(0);
  }
}
