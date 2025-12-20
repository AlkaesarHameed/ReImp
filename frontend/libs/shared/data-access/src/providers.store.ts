/**
 * Providers Store - NgRx Signal Store.
 * Source: Design Document Section 3.2, 4.0
 * Source: Phase 4 Implementation Document
 * Verified: 2025-12-18
 *
 * Reactive state management for providers with computed selectors.
 */
import { Injectable, computed, signal } from '@angular/core';
import { Provider, ProviderStatus, ProviderType, NetworkStatus } from '@claims-processing/models';

/**
 * Provider filters interface.
 */
export interface ProviderFilters {
  status?: ProviderStatus;
  providerType?: ProviderType;
  specialty?: string;
  searchTerm?: string;
  city?: string;
  state?: string;
  inNetwork?: boolean;
}

/**
 * Providers Store using Angular Signals.
 */
@Injectable({
  providedIn: 'root',
})
export class ProvidersStore {
  // ============================================================================
  // Private State Signals
  // ============================================================================

  private readonly _providers = signal<Provider[]>([]);
  private readonly _loading = signal<boolean>(false);
  private readonly _error = signal<string | null>(null);
  private readonly _selectedProviderId = signal<string | null>(null);
  private readonly _filters = signal<ProviderFilters>({});
  private readonly _pageSize = signal<number>(20);
  private readonly _currentPage = signal<number>(1);
  private readonly _totalCount = signal<number>(0);

  // ============================================================================
  // Public Readonly Signals (State)
  // ============================================================================

  readonly providers = this._providers.asReadonly();
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
   * Currently selected provider.
   */
  readonly selectedProvider = computed(() => {
    const id = this._selectedProviderId();
    if (!id) return null;
    return this._providers().find((p) => p.id === id) ?? null;
  });

  /**
   * Active providers.
   */
  readonly activeProviders = computed(() =>
    this._providers().filter((p) => p.status === ProviderStatus.ACTIVE)
  );

  /**
   * In-network providers.
   */
  readonly inNetworkProviders = computed(() =>
    this._providers().filter((p) =>
      p.network_status === NetworkStatus.IN_NETWORK ||
      p.network_status === NetworkStatus.PREFERRED
    )
  );

  /**
   * Providers count by status.
   */
  readonly providersByStatus = computed(() => {
    const counts: Partial<Record<ProviderStatus, number>> = {};
    for (const provider of this._providers()) {
      counts[provider.status] = (counts[provider.status] || 0) + 1;
    }
    return counts;
  });

  /**
   * Providers count by type.
   */
  readonly providersByType = computed(() => {
    const counts: Partial<Record<ProviderType, number>> = {};
    for (const provider of this._providers()) {
      counts[provider.provider_type] = (counts[provider.provider_type] || 0) + 1;
    }
    return counts;
  });

  /**
   * Unique specialties for filtering.
   */
  readonly uniqueSpecialties = computed(() => {
    const specialties = new Set<string>();
    for (const provider of this._providers()) {
      if (provider.specialty) {
        specialties.add(provider.specialty);
      }
    }
    return Array.from(specialties).sort();
  });

  /**
   * Filtered providers based on current filters.
   */
  readonly filteredProviders = computed(() => {
    const filters = this._filters();
    let result = this._providers();

    if (filters.status) {
      result = result.filter((p) => p.status === filters.status);
    }

    if (filters.providerType) {
      result = result.filter((p) => p.provider_type === filters.providerType);
    }

    if (filters.specialty) {
      result = result.filter((p) => p.specialty === filters.specialty);
    }

    if (filters.inNetwork !== undefined) {
      const isInNetwork = (p: Provider) =>
        p.network_status === NetworkStatus.IN_NETWORK ||
        p.network_status === NetworkStatus.PREFERRED;
      result = result.filter((p) =>
        filters.inNetwork ? isInNetwork(p) : !isInNetwork(p)
      );
    }

    if (filters.state) {
      result = result.filter((p) => p.address.state === filters.state);
    }

    if (filters.city) {
      result = result.filter((p) =>
        p.address.city.toLowerCase().includes(filters.city!.toLowerCase())
      );
    }

    if (filters.searchTerm) {
      const term = filters.searchTerm.toLowerCase();
      result = result.filter(
        (p) =>
          p.npi.toLowerCase().includes(term) ||
          p.name.toLowerCase().includes(term) ||
          p.specialty?.toLowerCase().includes(term) ||
          p.tax_id?.toLowerCase().includes(term)
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
   * Set providers and clear any existing error.
   */
  setProviders(providers: Provider[]): void {
    this._providers.set(providers);
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
   * Select a provider by ID.
   */
  selectProvider(providerId: string): void {
    this._selectedProviderId.set(providerId);
  }

  /**
   * Clear the current selection.
   */
  clearSelection(): void {
    this._selectedProviderId.set(null);
  }

  /**
   * Add a new provider to the store.
   */
  addProvider(provider: Provider): void {
    this._providers.update((providers) => [...providers, provider]);
    this._totalCount.update((count) => count + 1);
  }

  /**
   * Update an existing provider.
   */
  updateProvider(providerId: string, updates: Partial<Provider>): void {
    this._providers.update((providers) =>
      providers.map((p) => (p.id === providerId ? { ...p, ...updates } : p))
    );
  }

  /**
   * Remove a provider from the store.
   */
  removeProvider(providerId: string): void {
    this._providers.update((providers) => providers.filter((p) => p.id !== providerId));
    this._totalCount.update((count) => Math.max(0, count - 1));
    if (this._selectedProviderId() === providerId) {
      this._selectedProviderId.set(null);
    }
  }

  /**
   * Set filters for providers.
   */
  setFilters(filters: ProviderFilters): void {
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
    this._providers.set([]);
    this._loading.set(false);
    this._error.set(null);
    this._selectedProviderId.set(null);
    this._filters.set({});
    this._pageSize.set(20);
    this._currentPage.set(1);
    this._totalCount.set(0);
  }
}
