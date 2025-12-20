/**
 * Eligibility API Service Tests.
 * Source: Phase 4 Implementation Document
 * TDD: Tests written first
 */
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';

import { EligibilityApiService } from './eligibility.api';
import {
  EligibilityCheck,
  EligibilityResponse,
  EligibilityHistory,
  CoverageStatus,
  CoverageType,
} from '@claims-processing/models';

describe('EligibilityApiService', () => {
  let service: EligibilityApiService;
  let httpMock: HttpTestingController;
  const baseUrl = 'http://localhost:8000/api/v1';

  const mockEligibilityResponse: EligibilityResponse = {
    memberId: 'mem-1',
    memberName: 'John Doe',
    policyId: 'pol-1',
    policyNumber: 'P123456',
    groupId: 'grp-1',
    groupName: 'ACME Corp',
    eligible: true,
    effectiveDate: '2024-01-01',
    terminationDate: '2024-12-31',
    coverageStatus: CoverageStatus.ACTIVE,
    coverageType: CoverageType.MEDICAL,
    priorAuthRequired: false,
    verifiedAt: '2024-01-15T10:00:00Z',
    verificationSource: 'real-time',
    benefits: {
      planName: 'Gold PPO',
      planType: 'PPO',
      individualDeductible: 500,
      individualDeductibleMet: 250,
      familyDeductible: 1500,
      familyDeductibleMet: 500,
      individualOopMax: 5000,
      individualOopMet: 1000,
      familyOopMax: 10000,
      familyOopMet: 2000,
      inNetworkCoinsurance: 20,
      outOfNetworkCoinsurance: 40,
      copays: [],
      coverageDetails: [],
    },
    accumulators: {
      deductibleIndividual: { limit: 500, used: 250, remaining: 250, percentUsed: 50 },
      deductibleFamily: { limit: 1500, used: 500, remaining: 1000, percentUsed: 33 },
      oopIndividual: { limit: 5000, used: 1000, remaining: 4000, percentUsed: 20 },
      oopFamily: { limit: 10000, used: 2000, remaining: 8000, percentUsed: 20 },
      asOfDate: '2024-01-15',
    },
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        EligibilityApiService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });

    service = TestBed.inject(EligibilityApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('Service Creation', () => {
    it('should be created', () => {
      expect(service).toBeTruthy();
    });
  });

  describe('checkEligibility', () => {
    it('should check member eligibility', () => {
      const check: EligibilityCheck = {
        memberId: 'mem-1',
        dateOfService: '2024-01-15',
      };

      service.checkEligibility(check).subscribe(response => {
        expect(response.eligible).toBe(true);
        expect(response.memberId).toBe('mem-1');
        expect(response.coverageStatus).toBe(CoverageStatus.ACTIVE);
      });

      const req = httpMock.expectOne(`${baseUrl}/eligibility/mem-1`);
      expect(req.request.method).toBe('GET');
      expect(req.request.params.get('date_of_service')).toBe('2024-01-15');
      req.flush(mockEligibilityResponse);
    });

    it('should include provider ID when provided', () => {
      const check: EligibilityCheck = {
        memberId: 'mem-1',
        dateOfService: '2024-01-15',
        providerId: 'prov-1',
      };

      service.checkEligibility(check).subscribe();

      const req = httpMock.expectOne(req =>
        req.url === `${baseUrl}/eligibility/mem-1` &&
        req.params.get('provider_id') === 'prov-1'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockEligibilityResponse);
    });
  });

  describe('batchCheckEligibility', () => {
    it('should check eligibility for multiple members', () => {
      const checks: EligibilityCheck[] = [
        { memberId: 'mem-1', dateOfService: '2024-01-15' },
        { memberId: 'mem-2', dateOfService: '2024-01-15' },
      ];

      service.batchCheckEligibility(checks).subscribe(response => {
        expect(response.successCount).toBe(2);
        expect(response.results.length).toBe(2);
      });

      const req = httpMock.expectOne(`${baseUrl}/eligibility/batch`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body.checks.length).toBe(2);
      req.flush({
        results: [
          { memberId: 'mem-1', success: true, response: mockEligibilityResponse },
          { memberId: 'mem-2', success: true, response: mockEligibilityResponse },
        ],
        successCount: 2,
        failureCount: 0,
      });
    });
  });

  describe('getBenefits', () => {
    it('should get member benefits details', () => {
      service.getBenefits('mem-1').subscribe(response => {
        expect(response.benefits.planName).toBe('Gold PPO');
        expect(response.benefits.individualDeductible).toBe(500);
      });

      const req = httpMock.expectOne(`${baseUrl}/eligibility/mem-1/benefits`);
      expect(req.request.method).toBe('GET');
      req.flush(mockEligibilityResponse);
    });

    it('should include date of service parameter', () => {
      service.getBenefits('mem-1', '2024-02-01').subscribe();

      const req = httpMock.expectOne(req =>
        req.url === `${baseUrl}/eligibility/mem-1/benefits` &&
        req.params.get('date_of_service') === '2024-02-01'
      );
      req.flush(mockEligibilityResponse);
    });
  });

  describe('getEligibilityHistory', () => {
    it('should get eligibility verification history', () => {
      const mockHistory: EligibilityHistory = {
        memberId: 'mem-1',
        records: [
          {
            id: 'hist-1',
            checkDate: '2024-01-15T10:00:00Z',
            dateOfService: '2024-01-15',
            eligible: true,
            coverageStatus: CoverageStatus.ACTIVE,
            checkedBy: 'user-1',
          },
          {
            id: 'hist-2',
            checkDate: '2024-01-10T09:00:00Z',
            dateOfService: '2024-01-10',
            eligible: true,
            coverageStatus: CoverageStatus.ACTIVE,
            checkedBy: 'user-2',
          },
        ],
      };

      service.getEligibilityHistory('mem-1').subscribe(history => {
        expect(history.records.length).toBe(2);
        expect(history.memberId).toBe('mem-1');
      });

      const req = httpMock.expectOne(`${baseUrl}/eligibility/mem-1/history`);
      expect(req.request.method).toBe('GET');
      req.flush(mockHistory);
    });

    it('should support pagination parameters', () => {
      service.getEligibilityHistory('mem-1', { page: 2, size: 10 }).subscribe();

      const req = httpMock.expectOne(req =>
        req.url === `${baseUrl}/eligibility/mem-1/history` &&
        req.params.get('page') === '2' &&
        req.params.get('size') === '10'
      );
      req.flush({ memberId: 'mem-1', records: [] });
    });
  });

  describe('searchMembers', () => {
    it('should search members for eligibility check', () => {
      const mockResults = [
        { id: 'mem-1', name: 'John Doe', memberId: 'M12345678', dob: '1980-01-15' },
        { id: 'mem-2', name: 'Jane Doe', memberId: 'M87654321', dob: '1985-06-20' },
      ];

      service.searchMembers('doe').subscribe(results => {
        expect(results.length).toBe(2);
      });

      const req = httpMock.expectOne(req =>
        req.url === `${baseUrl}/members/search` &&
        req.params.get('q') === 'doe'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResults);
    });
  });
});
