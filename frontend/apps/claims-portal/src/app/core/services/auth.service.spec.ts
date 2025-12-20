/**
 * Auth Service Unit Tests.
 * Comprehensive test coverage for authentication functionality.
 */
import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { AuthService, User, LoginRequest, LoginResponse } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  let routerSpy: jest.Mocked<Router>;

  // Test user data
  const mockUser: User = {
    id: 'usr-001',
    username: 'testuser',
    email: 'test@claims.local',
    role: 'claims_processor',
    permissions: ['claims:read', 'claims:write'],
    firstName: 'Test',
    lastName: 'User',
  };

  beforeEach(() => {
    // Create router spy
    routerSpy = {
      navigate: jest.fn().mockReturnValue(Promise.resolve(true)),
      navigateByUrl: jest.fn().mockReturnValue(Promise.resolve(true)),
    } as unknown as jest.Mocked<Router>;

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        AuthService,
        { provide: Router, useValue: routerSpy },
      ],
    });

    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);

    // Clear sessionStorage before each test
    sessionStorage.clear();
  });

  afterEach(() => {
    httpMock.verify();
    sessionStorage.clear();
  });

  describe('Initial State', () => {
    it('should be created', () => {
      expect(service).toBeTruthy();
    });

    it('should have null user initially', () => {
      expect(service.user()).toBeNull();
    });

    it('should not be logged in initially', () => {
      expect(service.isLoggedIn()).toBe(false);
    });

    it('should not be loading initially', () => {
      expect(service.loading()).toBe(false);
    });

    it('should have null role initially', () => {
      expect(service.userRole()).toBeNull();
    });

    it('should have empty permissions initially', () => {
      expect(service.userPermissions()).toEqual([]);
    });
  });

  describe('Mock Authentication (Development Mode)', () => {
    describe('login()', () => {
      it('should authenticate with valid admin credentials', fakeAsync(() => {
        const credentials: LoginRequest = { username: 'admin', password: 'demo123' };
        let result: LoginResponse | undefined;

        service.login(credentials).subscribe({
          next: (response) => { result = response; },
        });

        tick(600); // Wait for mock delay

        expect(result).toBeDefined();
        expect(result!.user.username).toBe('admin');
        expect(result!.user.role).toBe('administrator');
        expect(service.isLoggedIn()).toBe(true);
        expect(service.user()).not.toBeNull();
      }));

      it('should authenticate with valid processor credentials', fakeAsync(() => {
        const credentials: LoginRequest = { username: 'processor', password: 'demo123' };
        let result: LoginResponse | undefined;

        service.login(credentials).subscribe({
          next: (response) => { result = response; },
        });

        tick(600);

        expect(result).toBeDefined();
        expect(result!.user.username).toBe('processor');
        expect(result!.user.role).toBe('claims_processor');
      }));

      it('should authenticate with valid supervisor credentials', fakeAsync(() => {
        const credentials: LoginRequest = { username: 'supervisor', password: 'demo123' };
        let result: LoginResponse | undefined;

        service.login(credentials).subscribe({
          next: (response) => { result = response; },
        });

        tick(600);

        expect(result).toBeDefined();
        expect(result!.user.username).toBe('supervisor');
        expect(result!.user.role).toBe('supervisor');
      }));

      it('should be case-insensitive for username', fakeAsync(() => {
        const credentials: LoginRequest = { username: 'ADMIN', password: 'demo123' };
        let result: LoginResponse | undefined;

        service.login(credentials).subscribe({
          next: (response) => { result = response; },
        });

        tick(600);

        expect(result).toBeDefined();
        expect(result!.user.username).toBe('admin');
      }));

      it('should fail with invalid username', fakeAsync(() => {
        const credentials: LoginRequest = { username: 'invalid', password: 'demo123' };
        let error: Error | undefined;

        service.login(credentials).subscribe({
          error: (err) => { error = err; },
        });

        tick(600);

        expect(error).toBeDefined();
        expect(error!.message).toContain('Invalid username or password');
        expect(service.isLoggedIn()).toBe(false);
      }));

      it('should fail with invalid password', fakeAsync(() => {
        const credentials: LoginRequest = { username: 'admin', password: 'wrongpassword' };
        let error: Error | undefined;

        service.login(credentials).subscribe({
          error: (err) => { error = err; },
        });

        tick(600);

        expect(error).toBeDefined();
        expect(error!.message).toContain('Invalid username or password');
        expect(service.isLoggedIn()).toBe(false);
      }));

      it('should store user in sessionStorage on successful login', fakeAsync(() => {
        const credentials: LoginRequest = { username: 'admin', password: 'demo123' };

        service.login(credentials).subscribe();
        tick(600);

        const storedUser = sessionStorage.getItem('mock_user');
        expect(storedUser).not.toBeNull();
        expect(JSON.parse(storedUser!).username).toBe('admin');
      }));

      it('should set loading state during login', fakeAsync(() => {
        const credentials: LoginRequest = { username: 'admin', password: 'demo123' };

        service.login(credentials).subscribe();

        // Loading should be true immediately
        expect(service.loading()).toBe(true);

        tick(600);

        // Loading should be false after completion
        expect(service.loading()).toBe(false);
      }));
    });

    describe('logout()', () => {
      it('should clear user state on logout', fakeAsync(() => {
        // First login
        service.login({ username: 'admin', password: 'demo123' }).subscribe();
        tick(600);
        expect(service.isLoggedIn()).toBe(true);

        // Then logout
        service.logout().subscribe();
        tick();

        expect(service.isLoggedIn()).toBe(false);
        expect(service.user()).toBeNull();
      }));

      it('should clear sessionStorage on logout', fakeAsync(() => {
        // First login
        service.login({ username: 'admin', password: 'demo123' }).subscribe();
        tick(600);
        expect(sessionStorage.getItem('mock_user')).not.toBeNull();

        // Then logout
        service.logout().subscribe();
        tick();

        expect(sessionStorage.getItem('mock_user')).toBeNull();
      }));

      it('should navigate to login page on logout', fakeAsync(() => {
        // First login
        service.login({ username: 'admin', password: 'demo123' }).subscribe();
        tick(600);

        // Then logout
        service.logout().subscribe();
        tick();

        expect(routerSpy.navigate).toHaveBeenCalledWith(['/auth/login']);
      }));
    });

    describe('initializeAuth()', () => {
      it('should restore user from sessionStorage', fakeAsync(() => {
        // Store a mock user
        sessionStorage.setItem('mock_user', JSON.stringify(mockUser));

        service.initializeAuth();
        tick();

        expect(service.isLoggedIn()).toBe(true);
        expect(service.user()?.username).toBe('testuser');
      }));

      it('should handle empty sessionStorage', fakeAsync(() => {
        service.initializeAuth();
        tick();

        expect(service.isLoggedIn()).toBe(false);
        expect(service.user()).toBeNull();
      }));

      it('should set loading to false after initialization', fakeAsync(() => {
        service.initializeAuth();
        tick();

        expect(service.loading()).toBe(false);
      }));
    });
  });

  describe('isAuthenticated()', () => {
    it('should return false when not logged in', () => {
      expect(service.isAuthenticated()).toBe(false);
    });

    it('should return true when logged in', fakeAsync(() => {
      service.login({ username: 'admin', password: 'demo123' }).subscribe();
      tick(600);

      expect(service.isAuthenticated()).toBe(true);
    }));
  });

  describe('hasPermission()', () => {
    it('should return false when not logged in', () => {
      expect(service.hasPermission('claims:read')).toBe(false);
    });

    it('should return true for granted permission', fakeAsync(() => {
      service.login({ username: 'admin', password: 'demo123' }).subscribe();
      tick(600);

      expect(service.hasPermission('claims:read')).toBe(true);
      expect(service.hasPermission('admin:users')).toBe(true);
    }));

    it('should return false for non-granted permission', fakeAsync(() => {
      service.login({ username: 'processor', password: 'demo123' }).subscribe();
      tick(600);

      expect(service.hasPermission('admin:users')).toBe(false);
    }));
  });

  describe('hasRole()', () => {
    it('should return false when not logged in', () => {
      expect(service.hasRole('administrator')).toBe(false);
    });

    it('should return true for matching role', fakeAsync(() => {
      service.login({ username: 'admin', password: 'demo123' }).subscribe();
      tick(600);

      expect(service.hasRole('administrator')).toBe(true);
    }));

    it('should return false for non-matching role', fakeAsync(() => {
      service.login({ username: 'admin', password: 'demo123' }).subscribe();
      tick(600);

      expect(service.hasRole('claims_processor')).toBe(false);
    }));

    it('should return true if user has any of the specified roles', fakeAsync(() => {
      service.login({ username: 'admin', password: 'demo123' }).subscribe();
      tick(600);

      expect(service.hasRole('claims_processor', 'administrator')).toBe(true);
    }));
  });

  describe('recordActivity()', () => {
    it('should update last activity time', () => {
      // Activity time should be updated (we can't directly access it, but it shouldn't throw)
      service.recordActivity();
      expect(() => service.recordActivity()).not.toThrow();
    });
  });

  describe('User Permissions by Role', () => {
    it('admin should have full permissions', fakeAsync(() => {
      service.login({ username: 'admin', password: 'demo123' }).subscribe();
      tick(600);

      const permissions = service.userPermissions();
      expect(permissions).toContain('claims:read');
      expect(permissions).toContain('claims:write');
      expect(permissions).toContain('claims:approve');
      expect(permissions).toContain('admin:users');
      expect(permissions).toContain('admin:settings');
      expect(permissions).toContain('reports:view');
    }));

    it('processor should have limited permissions', fakeAsync(() => {
      service.login({ username: 'processor', password: 'demo123' }).subscribe();
      tick(600);

      const permissions = service.userPermissions();
      expect(permissions).toContain('claims:read');
      expect(permissions).toContain('claims:write');
      expect(permissions).not.toContain('claims:approve');
      expect(permissions).not.toContain('admin:users');
    }));

    it('supervisor should have supervisor permissions', fakeAsync(() => {
      service.login({ username: 'supervisor', password: 'demo123' }).subscribe();
      tick(600);

      const permissions = service.userPermissions();
      expect(permissions).toContain('claims:read');
      expect(permissions).toContain('claims:write');
      expect(permissions).toContain('claims:approve');
      expect(permissions).toContain('reports:view');
      expect(permissions).not.toContain('admin:users');
    }));
  });

  describe('Data Extraction', () => {
    it('should return extractable user data after login', fakeAsync(() => {
      service.login({ username: 'admin', password: 'demo123' }).subscribe();
      tick(600);

      const user = service.user();
      expect(user).not.toBeNull();

      // Verify all user fields are extractable
      expect(user!.id).toBeDefined();
      expect(user!.username).toBe('admin');
      expect(user!.email).toBe('admin@claims.local');
      expect(user!.role).toBe('administrator');
      expect(user!.permissions).toBeInstanceOf(Array);
      expect(user!.firstName).toBe('System');
      expect(user!.lastName).toBe('Administrator');
    }));

    it('should return extractable login response', fakeAsync(() => {
      let response: LoginResponse | undefined;

      service.login({ username: 'admin', password: 'demo123' }).subscribe({
        next: (res) => { response = res; },
      });
      tick(600);

      expect(response).toBeDefined();
      expect(response!.user).toBeDefined();
      expect(response!.expiresAt).toBeDefined();

      // Verify expiresAt is a valid ISO date string
      const expiresAt = new Date(response!.expiresAt);
      expect(expiresAt.getTime()).toBeGreaterThan(Date.now());
    }));
  });
});
