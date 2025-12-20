/**
 * Claims API Service Tests.
 * Source: Design Document Section 4.1
 * Verified: 2025-12-18
 *
 * TDD: Tests written before implementation per implement.md methodology.
 */
import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';

import { ClaimsApiService } from './claims.api';
import {
  Claim,
  ClaimCreate,
  ClaimStatus,
  ClaimType,
  ClaimPriority,
  ClaimStats,
} from '@claims-processing/models';
import { environment } from '@claims-processing/environment';

describe('ClaimsApiService', () => {
  let service: ClaimsApiService;
  let httpMock: HttpTestingController;

  // Use environment configuration for consistent API URL
  const API_URL = environment.apiUrl;

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
    total_charged: 150.0,
    line_items: [],
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  };

  const mockClaimCreate: ClaimCreate = {
    policy_id: 'POL-001',
    member_id: 'MEM-001',
    provider_id: 'PRV-001',
    claim_type: ClaimType.PROFESSIONAL,
    service_date_from: '2024-01-15',
    service_date_to: '2024-01-15',
    diagnosis_codes: ['J06.9'],
    primary_diagnosis: 'J06.9',
    total_charged: 150.0,
    line_items: [],
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ClaimsApiService],
    });
    service = TestBed.inject(ClaimsApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('getClaims', () => {
    it('should fetch claims list', () => {
      const mockResponse = {
        items: [mockClaim],
        total: 1,
        page: 1,
        size: 20,
      };

      service.getClaims().subscribe((response) => {
        expect(response.items.length).toBe(1);
        expect(response.total).toBe(1);
      });

      const req = httpMock.expectOne(`${API_URL}/claims`);
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should include query parameters', () => {
      service
        .getClaims({
          status: ClaimStatus.SUBMITTED,
          page: 2,
          size: 50,
        })
        .subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API_URL}/claims` &&
          r.params.get('status') === 'submitted' &&
          r.params.get('page') === '2' &&
          r.params.get('size') === '50'
      );
      expect(req.request.method).toBe('GET');
      req.flush({ items: [], total: 0, page: 2, size: 50 });
    });

    it('should handle search parameter', () => {
      service.getClaims({ search: 'CLM-2024' }).subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API_URL}/claims` &&
          r.params.get('search') === 'CLM-2024'
      );
      req.flush({ items: [], total: 0, page: 1, size: 20 });
    });
  });

  describe('getClaim', () => {
    it('should fetch a single claim by ID', () => {
      service.getClaim('claim-001').subscribe((claim) => {
        expect(claim.id).toBe('claim-001');
        expect(claim.tracking_number).toBe('CLM-2024-000001');
      });

      const req = httpMock.expectOne(`${API_URL}/claims/claim-001`);
      expect(req.request.method).toBe('GET');
      req.flush(mockClaim);
    });

    it('should handle 404 error', () => {
      service.getClaim('nonexistent').subscribe({
        error: (error) => {
          expect(error.status).toBe(404);
        },
      });

      const req = httpMock.expectOne(`${API_URL}/claims/nonexistent`);
      req.flush({ detail: 'Claim not found' }, { status: 404, statusText: 'Not Found' });
    });
  });

  describe('createClaim', () => {
    it('should create a new claim', () => {
      service.createClaim(mockClaimCreate).subscribe((claim) => {
        expect(claim.id).toBe('claim-001');
        expect(claim.status).toBe(ClaimStatus.SUBMITTED);
      });

      const req = httpMock.expectOne(`${API_URL}/claims`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(mockClaimCreate);
      req.flush(mockClaim);
    });

    it('should handle validation errors', () => {
      const invalidClaim = { ...mockClaimCreate, policy_id: '' };

      service.createClaim(invalidClaim).subscribe({
        error: (error) => {
          expect(error.status).toBe(422);
        },
      });

      const req = httpMock.expectOne(`${API_URL}/claims`);
      req.flush(
        { detail: { message: 'Validation failed', errors: [{ field: 'policy_id', message: 'Required' }] } },
        { status: 422, statusText: 'Unprocessable Entity' }
      );
    });
  });

  describe('updateClaim', () => {
    it('should update an existing claim', () => {
      const updates = { priority: ClaimPriority.HIGH };

      service.updateClaim('claim-001', updates).subscribe((claim) => {
        expect(claim.priority).toBe(ClaimPriority.HIGH);
      });

      const req = httpMock.expectOne(`${API_URL}/claims/claim-001`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(updates);
      req.flush({ ...mockClaim, priority: ClaimPriority.HIGH });
    });
  });

  describe('deleteClaim', () => {
    it('should delete a claim', () => {
      service.deleteClaim('claim-001').subscribe((result) => {
        expect(result).toBeUndefined();
      });

      const req = httpMock.expectOne(`${API_URL}/claims/claim-001`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null, { status: 204, statusText: 'No Content' });
    });
  });

  describe('submitClaim', () => {
    it('should submit a draft claim', () => {
      service.submitClaim('claim-001').subscribe((claim) => {
        expect(claim.status).toBe(ClaimStatus.SUBMITTED);
      });

      const req = httpMock.expectOne(`${API_URL}/claims/claim-001/submit`);
      expect(req.request.method).toBe('POST');
      req.flush({ ...mockClaim, status: ClaimStatus.SUBMITTED });
    });
  });

  describe('approveClaim', () => {
    it('should approve a claim', () => {
      service
        .approveClaim('claim-001', { notes: 'Approved after review' })
        .subscribe((claim) => {
          expect(claim.status).toBe(ClaimStatus.APPROVED);
        });

      const req = httpMock.expectOne(`${API_URL}/claims/claim-001/approve`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ notes: 'Approved after review' });
      req.flush({ ...mockClaim, status: ClaimStatus.APPROVED });
    });
  });

  describe('denyClaim', () => {
    it('should deny a claim with reason', () => {
      service
        .denyClaim('claim-001', { reason: 'Not covered', notes: 'Service not in policy' })
        .subscribe((claim) => {
          expect(claim.status).toBe(ClaimStatus.DENIED);
        });

      const req = httpMock.expectOne(`${API_URL}/claims/claim-001/deny`);
      expect(req.request.method).toBe('POST');
      req.flush({ ...mockClaim, status: ClaimStatus.DENIED });
    });
  });

  describe('validateClaim', () => {
    it('should validate a claim', () => {
      service.validateClaim('claim-001').subscribe((result) => {
        expect(result.valid).toBe(true);
        expect(result.errors).toEqual([]);
      });

      const req = httpMock.expectOne(`${API_URL}/claims/claim-001/validate`);
      expect(req.request.method).toBe('POST');
      req.flush({ valid: true, errors: [], warnings: [] });
    });

    it('should return validation errors', () => {
      service.validateClaim('claim-001').subscribe((result) => {
        expect(result.valid).toBe(false);
        expect(result.errors.length).toBe(1);
      });

      const req = httpMock.expectOne(`${API_URL}/claims/claim-001/validate`);
      req.flush({
        valid: false,
        errors: [{ field: 'diagnosis_codes', code: 'INVALID', message: 'Invalid ICD-10 code' }],
        warnings: [],
      });
    });
  });

  describe('getClaimStats', () => {
    it('should fetch claim statistics', () => {
      const mockStats: ClaimStats = {
        total_claims: 1000,
        pending_count: 50,
        approved_count: 800,
        denied_count: 100,
        processing_count: 50,
        total_billed: 500000,
        total_paid: 400000,
        approval_rate: 0.8,
        average_processing_time: 2.5,
      };

      service.getClaimStats().subscribe((stats) => {
        expect(stats.total_claims).toBe(1000);
        expect(stats.approval_rate).toBe(0.8);
      });

      const req = httpMock.expectOne(`${API_URL}/claims/stats/summary`);
      expect(req.request.method).toBe('GET');
      req.flush(mockStats);
    });

    it('should include date range parameters', () => {
      service
        .getClaimStats({ dateFrom: '2024-01-01', dateTo: '2024-01-31' })
        .subscribe();

      const req = httpMock.expectOne(
        (r) =>
          r.url === `${API_URL}/claims/stats/summary` &&
          r.params.get('date_from') === '2024-01-01' &&
          r.params.get('date_to') === '2024-01-31'
      );
      req.flush({});
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors', () => {
      service.getClaims().subscribe({
        error: (error) => {
          expect(error.status).toBe(0);
        },
      });

      const req = httpMock.expectOne(`${API_URL}/claims`);
      req.error(new ProgressEvent('Network error'));
    });

    it('should handle server errors', () => {
      service.getClaims().subscribe({
        error: (error) => {
          expect(error.status).toBe(500);
        },
      });

      const req = httpMock.expectOne(`${API_URL}/claims`);
      req.flush({ detail: 'Internal server error' }, { status: 500, statusText: 'Server Error' });
    });
  });
});
