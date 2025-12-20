/**
 * Members Store - NgRx Signal Store.
 * Source: Design Document Section 3.2, 4.0
 * Source: Phase 4 Implementation Document
 * Verified: 2025-12-18
 *
 * Reactive state management for members with computed selectors.
 */
import { Injectable, computed, signal } from '@angular/core';
import {
  Member,
  MemberStatus,
  RelationshipType,
  getMemberFullName,
} from '@claims-processing/models';

/**
 * Member filters interface.
 */
export interface MemberFilters {
  status?: MemberStatus;
  searchTerm?: string;
  policyId?: string;
  relationship?: RelationshipType;
}

/**
 * Members Store using Angular Signals.
 */
@Injectable({
  providedIn: 'root',
})
export class MembersStore {
  // ============================================================================
  // Private State Signals
  // ============================================================================

  private readonly _members = signal<Member[]>([]);
  private readonly _loading = signal<boolean>(false);
  private readonly _error = signal<string | null>(null);
  private readonly _selectedMemberId = signal<string | null>(null);
  private readonly _filters = signal<MemberFilters>({});
  private readonly _pageSize = signal<number>(20);
  private readonly _currentPage = signal<number>(1);
  private readonly _totalCount = signal<number>(0);

  // ============================================================================
  // Public Readonly Signals (State)
  // ============================================================================

  readonly members = this._members.asReadonly();
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
   * Currently selected member.
   */
  readonly selectedMember = computed(() => {
    const id = this._selectedMemberId();
    if (!id) return null;
    return this._members().find((m) => m.id === id) ?? null;
  });

  /**
   * Active members.
   */
  readonly activeMembers = computed(() =>
    this._members().filter((m) => m.status === MemberStatus.ACTIVE)
  );

  /**
   * Inactive members.
   */
  readonly inactiveMembers = computed(() =>
    this._members().filter((m) =>
      [MemberStatus.INACTIVE, MemberStatus.TERMINATED].includes(m.status)
    )
  );

  /**
   * Members count by status.
   */
  readonly membersByStatus = computed(() => {
    const counts: Partial<Record<MemberStatus, number>> = {};
    for (const member of this._members()) {
      counts[member.status] = (counts[member.status] || 0) + 1;
    }
    return counts;
  });

  /**
   * Filtered members based on current filters.
   */
  readonly filteredMembers = computed(() => {
    const filters = this._filters();
    let result = this._members();

    if (filters.status) {
      result = result.filter((m) => m.status === filters.status);
    }

    if (filters.policyId) {
      result = result.filter((m) => m.policy_id === filters.policyId);
    }

    if (filters.relationship) {
      result = result.filter((m) => m.relationship_to_subscriber === filters.relationship);
    }

    if (filters.searchTerm) {
      const term = filters.searchTerm.toLowerCase();
      result = result.filter(
        (m) =>
          m.member_id.toLowerCase().includes(term) ||
          m.first_name.toLowerCase().includes(term) ||
          m.last_name.toLowerCase().includes(term) ||
          m.email?.toLowerCase().includes(term) ||
          getMemberFullName(m).toLowerCase().includes(term)
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

  /**
   * Members grouped by policy.
   */
  readonly membersByPolicy = computed(() => {
    const grouped = new Map<string, Member[]>();
    for (const member of this._members()) {
      const existing = grouped.get(member.policy_id) || [];
      grouped.set(member.policy_id, [...existing, member]);
    }
    return grouped;
  });

  // ============================================================================
  // State Mutations
  // ============================================================================

  /**
   * Set members and clear any existing error.
   */
  setMembers(members: Member[]): void {
    this._members.set(members);
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
   * Select a member by ID.
   */
  selectMember(memberId: string): void {
    this._selectedMemberId.set(memberId);
  }

  /**
   * Clear the current selection.
   */
  clearSelection(): void {
    this._selectedMemberId.set(null);
  }

  /**
   * Add a new member to the store.
   */
  addMember(member: Member): void {
    this._members.update((members) => [...members, member]);
    this._totalCount.update((count) => count + 1);
  }

  /**
   * Update an existing member.
   */
  updateMember(memberId: string, updates: Partial<Member>): void {
    this._members.update((members) =>
      members.map((m) => (m.id === memberId ? { ...m, ...updates } : m))
    );
  }

  /**
   * Remove a member from the store.
   */
  removeMember(memberId: string): void {
    this._members.update((members) => members.filter((m) => m.id !== memberId));
    this._totalCount.update((count) => Math.max(0, count - 1));
    if (this._selectedMemberId() === memberId) {
      this._selectedMemberId.set(null);
    }
  }

  /**
   * Set filters for members.
   */
  setFilters(filters: MemberFilters): void {
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
    this._members.set([]);
    this._loading.set(false);
    this._error.set(null);
    this._selectedMemberId.set(null);
    this._filters.set({});
    this._pageSize.set(20);
    this._currentPage.set(1);
    this._totalCount.set(0);
  }
}
