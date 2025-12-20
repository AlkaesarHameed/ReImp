/**
 * Claims Store Tests.
 * Source: Design Document Section 4.0, 7.0
 * Verified: 2025-12-18
 *
 * TDD: Tests written before implementation per implement.md methodology.
 */
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

import { ClaimsStore } from './claims.store';
import { Claim, ClaimStatus, ClaimType, ClaimPriority } from '@claims-processing/models';

describe('ClaimsStore', () => {
  let store: InstanceType<typeof ClaimsStore>;

  const mockClaim: Claim = {
    id: 'claim-001',
    tracking_number: 'CLM-2024-000001',
    claim_type: ClaimType.PROFESSIONAL,
    status: ClaimStatus.SUBMITTED,
    priority: ClaimPriority.NORMAL,
    policy_id: 'POL-001',
    member_id: 'MEM-001',
    provider_id: 'PRV-001',
    service_date_from: '2024-01-15',
    service_date_to: '2024-01-15',
    diagnosis_codes: ['J06.9'],
    primary_diagnosis: 'J06.9',
    total_charged: 150.00,
    total_allowed: 120.00,
    total_paid: 96.00,
    line_items: [],
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  };

  const mockClaims: Claim[] = [
    mockClaim,
    {
      ...mockClaim,
      id: 'claim-002',
      tracking_number: 'CLM-2024-000002',
      status: ClaimStatus.APPROVED,
    },
    {
      ...mockClaim,
      id: 'claim-003',
      tracking_number: 'CLM-2024-000003',
      status: ClaimStatus.DENIED,
    },
  ];

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ClaimsStore,
        provideHttpClient(),
      ],
    });
    store = TestBed.inject(ClaimsStore);
  });

  describe('Initial State', () => {
    it('should have empty claims array initially', () => {
      expect(store.claims()).toEqual([]);
    });

    it('should have loading as false initially', () => {
      expect(store.loading()).toBe(false);
    });

    it('should have no error initially', () => {
      expect(store.error()).toBeNull();
    });

    it('should have no selected claim initially', () => {
      expect(store.selectedClaim()).toBeNull();
    });

    it('should have empty filters initially', () => {
      expect(store.filters()).toEqual({});
    });
  });

  describe('Computed Selectors', () => {
    beforeEach(() => {
      store.setClaims(mockClaims);
    });

    it('should compute total count', () => {
      expect(store.totalCount()).toBe(3);
    });

    it('should compute pending claims count', () => {
      const pending = store.pendingClaims();
      expect(pending.length).toBe(1);
      expect(pending[0].status).toBe(ClaimStatus.SUBMITTED);
    });

    it('should compute approved claims count', () => {
      const approved = store.approvedClaims();
      expect(approved.length).toBe(1);
      expect(approved[0].status).toBe(ClaimStatus.APPROVED);
    });

    it('should compute denied claims count', () => {
      const denied = store.deniedClaims();
      expect(denied.length).toBe(1);
      expect(denied[0].status).toBe(ClaimStatus.DENIED);
    });

    it('should compute claims by status', () => {
      const byStatus = store.claimsByStatus();
      expect(byStatus[ClaimStatus.SUBMITTED]).toBe(1);
      expect(byStatus[ClaimStatus.APPROVED]).toBe(1);
      expect(byStatus[ClaimStatus.DENIED]).toBe(1);
    });

    it('should compute total charged amount', () => {
      expect(store.totalCharged()).toBe(450.00); // 150 * 3
    });

    it('should compute total paid amount', () => {
      expect(store.totalPaid()).toBe(288.00); // 96 * 3
    });
  });

  describe('State Mutations', () => {
    it('should set claims', () => {
      store.setClaims(mockClaims);
      expect(store.claims().length).toBe(3);
    });

    it('should set loading state', () => {
      store.setLoading(true);
      expect(store.loading()).toBe(true);
    });

    it('should set error state', () => {
      store.setError('Test error');
      expect(store.error()).toBe('Test error');
    });

    it('should clear error when setting claims', () => {
      store.setError('Test error');
      store.setClaims(mockClaims);
      expect(store.error()).toBeNull();
    });

    it('should select a claim', () => {
      store.setClaims(mockClaims);
      store.selectClaim('claim-001');
      expect(store.selectedClaim()?.id).toBe('claim-001');
    });

    it('should clear selected claim', () => {
      store.setClaims(mockClaims);
      store.selectClaim('claim-001');
      store.clearSelection();
      expect(store.selectedClaim()).toBeNull();
    });

    it('should add a new claim', () => {
      store.setClaims(mockClaims);
      const newClaim: Claim = {
        ...mockClaim,
        id: 'claim-004',
        tracking_number: 'CLM-2024-000004',
      };
      store.addClaim(newClaim);
      expect(store.claims().length).toBe(4);
    });

    it('should update an existing claim', () => {
      store.setClaims(mockClaims);
      store.updateClaim('claim-001', { status: ClaimStatus.APPROVED });
      const updated = store.claims().find(c => c.id === 'claim-001');
      expect(updated?.status).toBe(ClaimStatus.APPROVED);
    });

    it('should remove a claim', () => {
      store.setClaims(mockClaims);
      store.removeClaim('claim-001');
      expect(store.claims().length).toBe(2);
      expect(store.claims().find(c => c.id === 'claim-001')).toBeUndefined();
    });
  });

  describe('Filtering', () => {
    beforeEach(() => {
      store.setClaims(mockClaims);
    });

    it('should filter by status', () => {
      store.setFilters({ status: ClaimStatus.APPROVED });
      expect(store.filteredClaims().length).toBe(1);
      expect(store.filteredClaims()[0].status).toBe(ClaimStatus.APPROVED);
    });

    it('should filter by claim type', () => {
      store.setFilters({ claimType: ClaimType.PROFESSIONAL });
      expect(store.filteredClaims().length).toBe(3);
    });

    it('should filter by search term (tracking number)', () => {
      store.setFilters({ searchTerm: '000002' });
      expect(store.filteredClaims().length).toBe(1);
      expect(store.filteredClaims()[0].tracking_number).toContain('000002');
    });

    it('should combine multiple filters', () => {
      store.setClaims([
        ...mockClaims,
        {
          ...mockClaim,
          id: 'claim-004',
          tracking_number: 'CLM-2024-000004',
          status: ClaimStatus.APPROVED,
          claim_type: ClaimType.INSTITUTIONAL,
        },
      ]);
      store.setFilters({
        status: ClaimStatus.APPROVED,
        claimType: ClaimType.PROFESSIONAL,
      });
      expect(store.filteredClaims().length).toBe(1);
    });

    it('should clear filters', () => {
      store.setFilters({ status: ClaimStatus.APPROVED });
      store.clearFilters();
      expect(store.filters()).toEqual({});
      expect(store.filteredClaims().length).toBe(3);
    });
  });

  describe('Pagination', () => {
    beforeEach(() => {
      // Create 50 mock claims
      const manyClaims = Array.from({ length: 50 }, (_, i) => ({
        ...mockClaim,
        id: `claim-${i + 1}`,
        tracking_number: `CLM-2024-${String(i + 1).padStart(6, '0')}`,
      }));
      store.setClaims(manyClaims);
    });

    it('should set page size', () => {
      store.setPageSize(20);
      expect(store.pageSize()).toBe(20);
    });

    it('should set current page', () => {
      store.setCurrentPage(2);
      expect(store.currentPage()).toBe(2);
    });

    it('should compute total pages', () => {
      store.setPageSize(10);
      expect(store.totalPages()).toBe(5);
    });

    it('should return paginated claims', () => {
      store.setPageSize(10);
      store.setCurrentPage(1);
      expect(store.paginatedClaims().length).toBe(10);
    });

    it('should handle last page with fewer items', () => {
      store.setPageSize(15);
      store.setCurrentPage(4); // Last page should have 5 items
      expect(store.paginatedClaims().length).toBe(5);
    });
  });

  describe('Real-time Updates (WebSocket)', () => {
    beforeEach(() => {
      store.setClaims(mockClaims);
    });

    it('should handle claim update event', () => {
      store.handleClaimUpdate({
        claim_id: 'claim-001',
        status: ClaimStatus.APPROVED,
        tracking_number: 'CLM-2024-000001',
        updated_fields: ['status'],
      });
      const updated = store.claims().find(c => c.id === 'claim-001');
      expect(updated?.status).toBe(ClaimStatus.APPROVED);
    });

    it('should update metrics from WebSocket', () => {
      store.updateMetrics({
        claims_per_minute: 67,
        pending_count: 23,
        processing_count: 15,
        approved_today: 145,
        denied_today: 12,
      });
      expect(store.metrics()?.claims_per_minute).toBe(67);
      expect(store.metrics()?.approved_today).toBe(145);
    });
  });

  describe('Performance (4000 claims/min requirement)', () => {
    it('should handle large dataset efficiently', () => {
      const largeClaims = Array.from({ length: 10000 }, (_, i) => ({
        ...mockClaim,
        id: `claim-${i + 1}`,
        tracking_number: `CLM-2024-${String(i + 1).padStart(6, '0')}`,
      }));

      const startTime = performance.now();
      store.setClaims(largeClaims);
      const setTime = performance.now() - startTime;

      // Setting 10K claims should be under 100ms
      expect(setTime).toBeLessThan(100);
      expect(store.claims().length).toBe(10000);
    });

    it('should compute selectors efficiently on large dataset', () => {
      const largeClaims = Array.from({ length: 10000 }, (_, i) => ({
        ...mockClaim,
        id: `claim-${i + 1}`,
        tracking_number: `CLM-2024-${String(i + 1).padStart(6, '0')}`,
        status: i % 3 === 0 ? ClaimStatus.APPROVED :
                i % 3 === 1 ? ClaimStatus.DENIED : ClaimStatus.SUBMITTED,
      }));
      store.setClaims(largeClaims);

      const startTime = performance.now();
      const byStatus = store.claimsByStatus();
      const computeTime = performance.now() - startTime;

      // Computing status counts should be under 50ms
      expect(computeTime).toBeLessThan(50);
      expect(Object.values(byStatus).reduce((a, b) => a + b, 0)).toBe(10000);
    });
  });
});
