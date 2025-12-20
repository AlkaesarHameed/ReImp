/**
 * Users Store - NgRx Signal Store.
 * Source: Design Document Section 3.2, 4.0
 * Source: Phase 4 Implementation Document
 * Verified: 2025-12-18
 *
 * Reactive state management for users and RBAC.
 */
import { Injectable, computed, signal } from '@angular/core';
import {
  User,
  UserRole,
  UserStatus,
  Role,
  Permission,
  getRoleLabel,
} from '@claims-processing/models';

/**
 * User filters interface.
 */
export interface UserFilters {
  status?: UserStatus;
  role?: UserRole;
  searchTerm?: string;
}

/**
 * Users Store using Angular Signals.
 */
@Injectable({
  providedIn: 'root',
})
export class UsersStore {
  // ============================================================================
  // Private State Signals
  // ============================================================================

  private readonly _users = signal<User[]>([]);
  private readonly _roles = signal<Role[]>([]);
  private readonly _permissions = signal<Permission[]>([]);
  private readonly _loading = signal<boolean>(false);
  private readonly _error = signal<string | null>(null);
  private readonly _selectedUserId = signal<string | null>(null);
  private readonly _filters = signal<UserFilters>({});
  private readonly _pageSize = signal<number>(20);
  private readonly _currentPage = signal<number>(1);
  private readonly _totalCount = signal<number>(0);

  // ============================================================================
  // Public Readonly Signals (State)
  // ============================================================================

  readonly users = this._users.asReadonly();
  readonly roles = this._roles.asReadonly();
  readonly permissions = this._permissions.asReadonly();
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
   * Currently selected user.
   */
  readonly selectedUser = computed(() => {
    const id = this._selectedUserId();
    if (!id) return null;
    return this._users().find((u) => u.id === id) ?? null;
  });

  /**
   * Active users.
   */
  readonly activeUsers = computed(() =>
    this._users().filter((u) => u.status === UserStatus.ACTIVE)
  );

  /**
   * Locked users.
   */
  readonly lockedUsers = computed(() =>
    this._users().filter((u) => u.status === UserStatus.LOCKED)
  );

  /**
   * Users count by status.
   */
  readonly usersByStatus = computed(() => {
    const counts: Partial<Record<UserStatus, number>> = {};
    for (const user of this._users()) {
      counts[user.status] = (counts[user.status] || 0) + 1;
    }
    return counts;
  });

  /**
   * Users count by role.
   */
  readonly usersByRole = computed(() => {
    const counts: Partial<Record<UserRole, number>> = {};
    for (const user of this._users()) {
      counts[user.role] = (counts[user.role] || 0) + 1;
    }
    return counts;
  });

  /**
   * Roles with labels for dropdown.
   */
  readonly roleOptions = computed(() =>
    this._roles().map((r) => ({
      label: getRoleLabel(r.name),
      value: r.name,
      description: r.description,
    }))
  );

  /**
   * Filtered users based on current filters.
   */
  readonly filteredUsers = computed(() => {
    const filters = this._filters();
    let result = this._users();

    if (filters.status) {
      result = result.filter((u) => u.status === filters.status);
    }

    if (filters.role) {
      result = result.filter((u) => u.role === filters.role);
    }

    if (filters.searchTerm) {
      const term = filters.searchTerm.toLowerCase();
      result = result.filter(
        (u) =>
          u.email.toLowerCase().includes(term) ||
          u.first_name.toLowerCase().includes(term) ||
          u.last_name.toLowerCase().includes(term) ||
          `${u.first_name} ${u.last_name}`.toLowerCase().includes(term)
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
   * Administrators count.
   */
  readonly adminCount = computed(() =>
    this._users().filter((u) => u.role === UserRole.ADMIN).length
  );

  // ============================================================================
  // State Mutations
  // ============================================================================

  /**
   * Set users and clear any existing error.
   */
  setUsers(users: User[]): void {
    this._users.set(users);
    this._error.set(null);
  }

  /**
   * Set available roles.
   */
  setRoles(roles: Role[]): void {
    this._roles.set(roles);
  }

  /**
   * Set available permissions.
   */
  setPermissions(permissions: Permission[]): void {
    this._permissions.set(permissions);
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
   * Select a user by ID.
   */
  selectUser(userId: string): void {
    this._selectedUserId.set(userId);
  }

  /**
   * Clear the current selection.
   */
  clearSelection(): void {
    this._selectedUserId.set(null);
  }

  /**
   * Add a new user to the store.
   */
  addUser(user: User): void {
    this._users.update((users) => [...users, user]);
    this._totalCount.update((count) => count + 1);
  }

  /**
   * Update an existing user.
   */
  updateUser(userId: string, updates: Partial<User>): void {
    this._users.update((users) =>
      users.map((u) => (u.id === userId ? { ...u, ...updates } : u))
    );
  }

  /**
   * Remove a user from the store.
   */
  removeUser(userId: string): void {
    this._users.update((users) => users.filter((u) => u.id !== userId));
    this._totalCount.update((count) => Math.max(0, count - 1));
    if (this._selectedUserId() === userId) {
      this._selectedUserId.set(null);
    }
  }

  /**
   * Lock a user account.
   */
  lockUser(userId: string): void {
    this.updateUser(userId, {
      status: UserStatus.LOCKED,
      locked_at: new Date().toISOString(),
    });
  }

  /**
   * Unlock a user account.
   */
  unlockUser(userId: string): void {
    this.updateUser(userId, {
      status: UserStatus.ACTIVE,
      locked_at: undefined,
      failed_login_attempts: 0,
    });
  }

  /**
   * Set filters for users.
   */
  setFilters(filters: UserFilters): void {
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
    this._users.set([]);
    this._roles.set([]);
    this._permissions.set([]);
    this._loading.set(false);
    this._error.set(null);
    this._selectedUserId.set(null);
    this._filters.set({});
    this._pageSize.set(20);
    this._currentPage.set(1);
    this._totalCount.set(0);
  }
}
