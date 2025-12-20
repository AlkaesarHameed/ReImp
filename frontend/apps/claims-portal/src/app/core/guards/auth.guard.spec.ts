/**
 * Auth Guard Unit Tests.
 * Comprehensive test coverage for route protection.
 * Tests the UrlTree-based redirect for zoneless change detection.
 */
import { TestBed } from '@angular/core/testing';
import { Router, ActivatedRouteSnapshot, RouterStateSnapshot, UrlTree } from '@angular/router';
import { authGuard } from './auth.guard';
import { AuthService } from '../services/auth.service';

describe('authGuard', () => {
  let authServiceSpy: jest.Mocked<AuthService>;
  let routerSpy: jest.Mocked<Router>;
  let mockRoute: ActivatedRouteSnapshot;
  let mockState: RouterStateSnapshot;
  let mockUrlTree: UrlTree;

  beforeEach(() => {
    // Create mock UrlTree
    mockUrlTree = { toString: () => '/auth/login?returnUrl=/dashboard' } as unknown as UrlTree;

    // Create spies
    authServiceSpy = {
      isAuthenticated: jest.fn(),
    } as unknown as jest.Mocked<AuthService>;

    routerSpy = {
      createUrlTree: jest.fn().mockReturnValue(mockUrlTree),
    } as unknown as jest.Mocked<Router>;

    // Create mock route and state
    mockRoute = {} as ActivatedRouteSnapshot;
    mockState = {
      url: '/dashboard',
    } as RouterStateSnapshot;

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: authServiceSpy },
        { provide: Router, useValue: routerSpy },
      ],
    });
  });

  describe('when user is authenticated', () => {
    beforeEach(() => {
      authServiceSpy.isAuthenticated.mockReturnValue(true);
    });

    it('should return true', () => {
      const result = TestBed.runInInjectionContext(() => {
        return authGuard(mockRoute, mockState);
      });
      expect(result).toBe(true);
    });

    it('should not create redirect UrlTree', () => {
      TestBed.runInInjectionContext(() => {
        authGuard(mockRoute, mockState);
      });
      expect(routerSpy.createUrlTree).not.toHaveBeenCalled();
    });
  });

  describe('when user is not authenticated', () => {
    beforeEach(() => {
      authServiceSpy.isAuthenticated.mockReturnValue(false);
    });

    it('should return a UrlTree', () => {
      const result = TestBed.runInInjectionContext(() => {
        return authGuard(mockRoute, mockState);
      });
      expect(result).toBe(mockUrlTree);
    });

    it('should create UrlTree for login page redirect', () => {
      TestBed.runInInjectionContext(() => {
        authGuard(mockRoute, mockState);
      });
      expect(routerSpy.createUrlTree).toHaveBeenCalledWith(
        ['/auth/login'],
        { queryParams: { returnUrl: '/dashboard' } }
      );
    });

    it('should include return URL in redirect UrlTree', () => {
      mockState = { url: '/claims/new' } as RouterStateSnapshot;

      TestBed.runInInjectionContext(() => {
        authGuard(mockRoute, mockState);
      });

      expect(routerSpy.createUrlTree).toHaveBeenCalledWith(
        ['/auth/login'],
        { queryParams: { returnUrl: '/claims/new' } }
      );
    });

    it('should handle complex return URLs', () => {
      mockState = { url: '/reports?type=financial&year=2024' } as RouterStateSnapshot;

      TestBed.runInInjectionContext(() => {
        authGuard(mockRoute, mockState);
      });

      expect(routerSpy.createUrlTree).toHaveBeenCalledWith(
        ['/auth/login'],
        { queryParams: { returnUrl: '/reports?type=financial&year=2024' } }
      );
    });
  });

  describe('Protected Routes', () => {
    const protectedUrls = [
      '/dashboard',
      '/claims',
      '/claims/new',
      '/claims/CLM-001',
      '/eligibility',
      '/admin',
      '/admin/users',
      '/reports',
    ];

    protectedUrls.forEach((url) => {
      it(`should return UrlTree for ${url} when unauthenticated`, () => {
        authServiceSpy.isAuthenticated.mockReturnValue(false);
        mockState = { url } as RouterStateSnapshot;

        const result = TestBed.runInInjectionContext(() => {
          return authGuard(mockRoute, mockState);
        });

        expect(result).toBe(mockUrlTree);
        expect(routerSpy.createUrlTree).toHaveBeenCalledWith(
          ['/auth/login'],
          { queryParams: { returnUrl: url } }
        );
      });

      it(`should allow access to ${url} when authenticated`, () => {
        authServiceSpy.isAuthenticated.mockReturnValue(true);
        mockState = { url } as RouterStateSnapshot;

        const result = TestBed.runInInjectionContext(() => {
          return authGuard(mockRoute, mockState);
        });

        expect(result).toBe(true);
        expect(routerSpy.createUrlTree).not.toHaveBeenCalled();
      });
    });
  });

  describe('Edge Cases', () => {
    beforeEach(() => {
      authServiceSpy.isAuthenticated.mockReturnValue(false);
    });

    it('should handle empty URL', () => {
      mockState = { url: '' } as RouterStateSnapshot;

      TestBed.runInInjectionContext(() => {
        authGuard(mockRoute, mockState);
      });

      expect(routerSpy.createUrlTree).toHaveBeenCalledWith(
        ['/auth/login'],
        { queryParams: { returnUrl: '' } }
      );
    });

    it('should handle root URL', () => {
      mockState = { url: '/' } as RouterStateSnapshot;

      TestBed.runInInjectionContext(() => {
        authGuard(mockRoute, mockState);
      });

      expect(routerSpy.createUrlTree).toHaveBeenCalledWith(
        ['/auth/login'],
        { queryParams: { returnUrl: '/' } }
      );
    });

    it('should handle URLs with fragments', () => {
      mockState = { url: '/claims#section1' } as RouterStateSnapshot;

      TestBed.runInInjectionContext(() => {
        authGuard(mockRoute, mockState);
      });

      expect(routerSpy.createUrlTree).toHaveBeenCalledWith(
        ['/auth/login'],
        { queryParams: { returnUrl: '/claims#section1' } }
      );
    });
  });

  describe('Data Extraction', () => {
    it('should correctly read authentication state', () => {
      authServiceSpy.isAuthenticated.mockReturnValue(true);

      const result = TestBed.runInInjectionContext(() => {
        return authGuard(mockRoute, mockState);
      });

      expect(authServiceSpy.isAuthenticated).toHaveBeenCalled();
      expect(result).toBe(true);
    });

    it('should extract return URL from router state', () => {
      authServiceSpy.isAuthenticated.mockReturnValue(false);
      const testUrl = '/test/url/path';
      mockState = { url: testUrl } as RouterStateSnapshot;

      TestBed.runInInjectionContext(() => {
        authGuard(mockRoute, mockState);
      });

      expect(routerSpy.createUrlTree).toHaveBeenCalledWith(
        expect.any(Array),
        expect.objectContaining({
          queryParams: { returnUrl: testUrl },
        })
      );
    });
  });

  describe('Return Type Validation', () => {
    it('should return boolean true when authenticated', () => {
      authServiceSpy.isAuthenticated.mockReturnValue(true);

      const result = TestBed.runInInjectionContext(() => {
        return authGuard(mockRoute, mockState);
      });

      expect(typeof result).toBe('boolean');
      expect(result).toBe(true);
    });

    it('should return UrlTree when not authenticated', () => {
      authServiceSpy.isAuthenticated.mockReturnValue(false);

      const result = TestBed.runInInjectionContext(() => {
        return authGuard(mockRoute, mockState);
      });

      expect(result).toBe(mockUrlTree);
      // UrlTree is an object, not a boolean
      expect(typeof result).toBe('object');
    });
  });
});
