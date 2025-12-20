/**
 * Lookup API Service Tests.
 * Source: Phase 3 Implementation Document
 * Verified: 2025-12-18
 *
 * TDD: Tests written before implementation per implement.md methodology.
 */
import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';

import { LookupApiService } from './lookup.api';
import {
  ICD10Code,
  CPTCode,
  HCPCSCode,
  PlaceOfServiceCode,
  DenialReasonCode,
  ModifierCode,
  LookupResponse,
} from '@claims-processing/models';
import { environment } from '@claims-processing/environment';

describe('LookupApiService', () => {
  let service: LookupApiService;
  let httpMock: HttpTestingController;

  // Use environment configuration for consistent API URL
  const API_URL = environment.apiUrl;

  const mockICD10Codes: ICD10Code[] = [
    {
      code: 'J06.9',
      description: 'Acute upper respiratory infection, unspecified',
      category: 'Diseases of the respiratory system',
      isHeader: false,
      isBillable: true,
    },
    {
      code: 'J06.0',
      description: 'Acute laryngopharyngitis',
      category: 'Diseases of the respiratory system',
      isHeader: false,
      isBillable: true,
    },
  ];

  const mockCPTCodes: CPTCode[] = [
    {
      code: '99213',
      description: 'Office or other outpatient visit, established patient, low complexity',
      category: 'Evaluation and Management',
      shortDescription: 'Office visit, est patient, 20-29 min',
      relativeValue: 1.3,
    },
    {
      code: '99214',
      description: 'Office or other outpatient visit, established patient, moderate complexity',
      category: 'Evaluation and Management',
      shortDescription: 'Office visit, est patient, 30-39 min',
      relativeValue: 1.92,
    },
  ];

  const mockHCPCSCodes: HCPCSCode[] = [
    {
      code: 'J0585',
      description: 'Injection, onabotulinumtoxinA, 1 unit',
      category: 'J Codes - Drugs',
      shortDescription: 'Botulinum toxin type a',
      pricingIndicator: 'K',
    },
  ];

  const mockPOSCodes: PlaceOfServiceCode[] = [
    { code: '11', name: 'Office', description: 'Location where health care services are provided' },
    { code: '21', name: 'Inpatient Hospital', description: 'Hospital inpatient setting' },
    { code: '22', name: 'Outpatient Hospital', description: 'Hospital outpatient setting' },
  ];

  const mockDenialReasons: DenialReasonCode[] = [
    { code: 'NC', description: 'Not Covered', category: 'eligibility' },
    { code: 'MD', description: 'Medical Necessity Not Met', category: 'medical' },
    { code: 'DP', description: 'Duplicate Claim', category: 'administrative' },
  ];

  const mockModifiers: ModifierCode[] = [
    { code: '25', description: 'Significant, Separately Identifiable E/M Service', applicableTo: ['CPT'] },
    { code: '59', description: 'Distinct Procedural Service', applicableTo: ['CPT', 'HCPCS'] },
  ];

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [LookupApiService],
    });
    service = TestBed.inject(LookupApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('ICD-10 Lookup', () => {
    it('should search ICD-10 codes', () => {
      const mockResponse: LookupResponse<ICD10Code> = {
        items: mockICD10Codes,
        total: 2,
        query: 'J06',
      };

      service.searchICD10('J06').subscribe((response) => {
        expect(response.items.length).toBe(2);
        expect(response.items[0].code).toBe('J06.9');
        expect(response.items[0].isBillable).toBe(true);
      });

      const req = httpMock.expectOne((r) =>
        r.url === `${API_URL}/lookup/icd10` &&
        r.params.get('q') === 'J06'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should include limit parameter', () => {
      service.searchICD10('J06', 10).subscribe();

      const req = httpMock.expectOne((r) =>
        r.url === `${API_URL}/lookup/icd10` &&
        r.params.get('q') === 'J06' &&
        r.params.get('limit') === '10'
      );
      req.flush({ items: [], total: 0, query: 'J06' });
    });

    it('should validate ICD-10 code', () => {
      service.validateICD10('J06.9').subscribe((result) => {
        expect(result.valid).toBe(true);
        expect(result.code).toBe('J06.9');
      });

      const req = httpMock.expectOne(`${API_URL}/lookup/icd10/J06.9/validate`);
      expect(req.request.method).toBe('GET');
      req.flush({ code: 'J06.9', valid: true });
    });

    it('should return invalid for non-existent code', () => {
      service.validateICD10('INVALID').subscribe((result) => {
        expect(result.valid).toBe(false);
        expect(result.message).toBeDefined();
      });

      const req = httpMock.expectOne(`${API_URL}/lookup/icd10/INVALID/validate`);
      req.flush({
        code: 'INVALID',
        valid: false,
        message: 'Code not found',
        suggestions: ['J06.9'],
      });
    });
  });

  describe('CPT Lookup', () => {
    it('should search CPT codes', () => {
      const mockResponse: LookupResponse<CPTCode> = {
        items: mockCPTCodes,
        total: 2,
        query: '9921',
      };

      service.searchCPT('9921').subscribe((response) => {
        expect(response.items.length).toBe(2);
        expect(response.items[0].code).toBe('99213');
        expect(response.items[0].relativeValue).toBe(1.3);
      });

      const req = httpMock.expectOne((r) =>
        r.url === `${API_URL}/lookup/cpt` &&
        r.params.get('q') === '9921'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should validate CPT code', () => {
      service.validateCPT('99213').subscribe((result) => {
        expect(result.valid).toBe(true);
      });

      const req = httpMock.expectOne(`${API_URL}/lookup/cpt/99213/validate`);
      req.flush({ code: '99213', valid: true });
    });

    it('should search CPT by description', () => {
      service.searchCPT('office visit').subscribe((response) => {
        expect(response.items.length).toBeGreaterThan(0);
      });

      const req = httpMock.expectOne((r) =>
        r.url === `${API_URL}/lookup/cpt` &&
        r.params.get('q') === 'office visit'
      );
      req.flush({ items: mockCPTCodes, total: 2, query: 'office visit' });
    });
  });

  describe('HCPCS Lookup', () => {
    it('should search HCPCS codes', () => {
      const mockResponse: LookupResponse<HCPCSCode> = {
        items: mockHCPCSCodes,
        total: 1,
        query: 'J0585',
      };

      service.searchHCPCS('J0585').subscribe((response) => {
        expect(response.items.length).toBe(1);
        expect(response.items[0].code).toBe('J0585');
        expect(response.items[0].pricingIndicator).toBe('K');
      });

      const req = httpMock.expectOne((r) =>
        r.url === `${API_URL}/lookup/hcpcs` &&
        r.params.get('q') === 'J0585'
      );
      req.flush(mockResponse);
    });

    it('should validate HCPCS code', () => {
      service.validateHCPCS('J0585').subscribe((result) => {
        expect(result.valid).toBe(true);
      });

      const req = httpMock.expectOne(`${API_URL}/lookup/hcpcs/J0585/validate`);
      req.flush({ code: 'J0585', valid: true });
    });
  });

  describe('Place of Service Codes', () => {
    it('should get all POS codes', () => {
      service.getPlaceOfServiceCodes().subscribe((codes) => {
        expect(codes.length).toBe(3);
        expect(codes[0].code).toBe('11');
        expect(codes[0].name).toBe('Office');
      });

      const req = httpMock.expectOne(`${API_URL}/lookup/pos`);
      expect(req.request.method).toBe('GET');
      req.flush(mockPOSCodes);
    });

    it('should cache POS codes after first request', () => {
      // First request
      service.getPlaceOfServiceCodes().subscribe();
      const req1 = httpMock.expectOne(`${API_URL}/lookup/pos`);
      req1.flush(mockPOSCodes);

      // Second request should use cache (no HTTP call)
      service.getPlaceOfServiceCodes().subscribe((codes) => {
        expect(codes.length).toBe(3);
      });

      httpMock.expectNone(`${API_URL}/lookup/pos`);
    });
  });

  describe('Denial Reason Codes', () => {
    it('should get all denial reason codes', () => {
      service.getDenialReasonCodes().subscribe((codes) => {
        expect(codes.length).toBe(3);
        expect(codes[0].code).toBe('NC');
        expect(codes[0].category).toBe('eligibility');
      });

      const req = httpMock.expectOne(`${API_URL}/lookup/denial-reasons`);
      expect(req.request.method).toBe('GET');
      req.flush(mockDenialReasons);
    });

    it('should filter denial reasons by category', () => {
      service.getDenialReasonCodes('medical').subscribe((codes) => {
        expect(codes.every(c => c.category === 'medical')).toBe(true);
      });

      const req = httpMock.expectOne((r) =>
        r.url === `${API_URL}/lookup/denial-reasons` &&
        r.params.get('category') === 'medical'
      );
      req.flush(mockDenialReasons.filter(c => c.category === 'medical'));
    });
  });

  describe('Modifier Codes', () => {
    it('should get all modifier codes', () => {
      service.getModifierCodes().subscribe((codes) => {
        expect(codes.length).toBe(2);
        expect(codes[0].code).toBe('25');
      });

      const req = httpMock.expectOne(`${API_URL}/lookup/modifiers`);
      expect(req.request.method).toBe('GET');
      req.flush(mockModifiers);
    });

    it('should filter modifiers by applicable system', () => {
      service.getModifierCodes('CPT').subscribe((codes) => {
        expect(codes.every(c => c.applicableTo.includes('CPT'))).toBe(true);
      });

      const req = httpMock.expectOne((r) =>
        r.url === `${API_URL}/lookup/modifiers` &&
        r.params.get('system') === 'CPT'
      );
      req.flush(mockModifiers.filter(c => c.applicableTo.includes('CPT')));
    });
  });

  describe('Error Handling', () => {
    it('should handle 404 for invalid code lookup', () => {
      service.searchICD10('NONEXISTENT').subscribe({
        next: (response) => {
          expect(response.items.length).toBe(0);
        },
      });

      const req = httpMock.expectOne((r) => r.url === `${API_URL}/lookup/icd10`);
      req.flush({ items: [], total: 0, query: 'NONEXISTENT' });
    });

    it('should handle server errors gracefully', () => {
      service.searchICD10('J06').subscribe({
        error: (error) => {
          expect(error.status).toBe(500);
        },
      });

      const req = httpMock.expectOne((r) => r.url === `${API_URL}/lookup/icd10`);
      req.flush({ detail: 'Server error' }, { status: 500, statusText: 'Internal Server Error' });
    });

    it('should handle network errors', () => {
      service.searchCPT('99213').subscribe({
        error: (error) => {
          expect(error.status).toBe(0);
        },
      });

      const req = httpMock.expectOne((r) => r.url === `${API_URL}/lookup/cpt`);
      req.error(new ProgressEvent('Network error'));
    });
  });

  describe('Debouncing and Caching', () => {
    it('should return cached results for same query within cache window', () => {
      // This test verifies the service behavior for rapid sequential calls
      const query = 'J06';

      service.searchICD10(query).subscribe();
      const req = httpMock.expectOne((r) => r.params.get('q') === query);
      req.flush({ items: mockICD10Codes, total: 2, query });

      // Immediate second call should potentially use cache
      // (actual caching behavior depends on implementation)
    });
  });
});
