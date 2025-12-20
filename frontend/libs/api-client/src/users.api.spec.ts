/**
 * Users API Service Tests.
 * Source: Phase 4 Implementation Document
 * TDD: Tests written first
 */
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';

import { UsersApiService } from './users.api';
import {
  User,
  UserCreate,
  UserUpdate,
  UserRole,
  UserStatus,
  Role,
  Permission,
} from '@claims-processing/models';
import { environment } from '@claims-processing/environment';

describe('UsersApiService', () => {
  let service: UsersApiService;
  let httpMock: HttpTestingController;
  // Use environment configuration for consistent API URL
  const baseUrl = environment.apiUrl;

  const mockUser: User = {
    id: 'user-1',
    email: 'john.doe@example.com',
    first_name: 'John',
    last_name: 'Doe',
    role: UserRole.CLAIMS_PROCESSOR,
    permissions: [],
    status: UserStatus.ACTIVE,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    failed_login_attempts: 0,
  };

  const mockUsers: User[] = [
    mockUser,
    {
      ...mockUser,
      id: 'user-2',
      email: 'jane.smith@example.com',
      first_name: 'Jane',
      last_name: 'Smith',
      role: UserRole.SUPERVISOR,
    },
  ];

  const mockRoles: Role[] = [
    {
      id: 'role-1',
      name: UserRole.ADMIN,
      description: 'Administrator with full access',
      permissions: [],
    },
    {
      id: 'role-2',
      name: UserRole.CLAIMS_PROCESSOR,
      description: 'Claims processing staff',
      permissions: [],
    },
  ];

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        UsersApiService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });

    service = TestBed.inject(UsersApiService);
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

  describe('getUsers', () => {
    it('should fetch paginated users list', () => {
      const mockResponse = {
        items: mockUsers,
        total: 2,
        page: 1,
        size: 20,
      };

      service.getUsers().subscribe(response => {
        expect(response.items.length).toBe(2);
        expect(response.total).toBe(2);
      });

      const req = httpMock.expectOne(`${baseUrl}/users`);
      expect(req.request.method).toBe('GET');
      expect(req.request.withCredentials).toBeTrue();
      req.flush(mockResponse);
    });

    it('should apply query parameters', () => {
      service.getUsers({
        search: 'john',
        role: UserRole.CLAIMS_PROCESSOR,
        status: UserStatus.ACTIVE,
        page: 2,
        size: 10,
      }).subscribe();

      const req = httpMock.expectOne(req =>
        req.url === `${baseUrl}/users` &&
        req.params.get('search') === 'john' &&
        req.params.get('role') === 'claims_processor' &&
        req.params.get('status') === 'active' &&
        req.params.get('page') === '2' &&
        req.params.get('size') === '10'
      );
      expect(req.request.method).toBe('GET');
      req.flush({ items: [], total: 0, page: 2, size: 10 });
    });
  });

  describe('getUser', () => {
    it('should fetch single user by ID', () => {
      service.getUser('user-1').subscribe(user => {
        expect(user.id).toBe('user-1');
        expect(user.email).toBe('john.doe@example.com');
      });

      const req = httpMock.expectOne(`${baseUrl}/users/user-1`);
      expect(req.request.method).toBe('GET');
      req.flush(mockUser);
    });
  });

  describe('createUser', () => {
    it('should create new user', () => {
      const newUser: UserCreate = {
        email: 'new.user@example.com',
        password: 'SecurePassword123!',
        first_name: 'New',
        last_name: 'User',
        role: UserRole.CLAIMS_PROCESSOR,
      };

      service.createUser(newUser).subscribe(user => {
        expect(user.email).toBe('new.user@example.com');
      });

      const req = httpMock.expectOne(`${baseUrl}/users`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(newUser);
      req.flush({ ...mockUser, email: 'new.user@example.com' });
    });
  });

  describe('updateUser', () => {
    it('should update existing user', () => {
      const updates: UserUpdate = {
        first_name: 'Johnny',
        role: UserRole.SUPERVISOR,
      };

      service.updateUser('user-1', updates).subscribe(user => {
        expect(user.first_name).toBe('Johnny');
      });

      const req = httpMock.expectOne(`${baseUrl}/users/user-1`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(updates);
      req.flush({ ...mockUser, first_name: 'Johnny', role: UserRole.SUPERVISOR });
    });
  });

  describe('deleteUser', () => {
    it('should delete user', () => {
      service.deleteUser('user-1').subscribe();

      const req = httpMock.expectOne(`${baseUrl}/users/user-1`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });

  describe('resetPassword', () => {
    it('should reset user password', () => {
      service.resetPassword('user-1').subscribe();

      const req = httpMock.expectOne(`${baseUrl}/users/user-1/reset-password`);
      expect(req.request.method).toBe('POST');
      req.flush({ success: true });
    });
  });

  describe('lockUser', () => {
    it('should lock user account', () => {
      service.lockUser('user-1').subscribe(user => {
        expect(user.status).toBe(UserStatus.LOCKED);
      });

      const req = httpMock.expectOne(`${baseUrl}/users/user-1/lock`);
      expect(req.request.method).toBe('POST');
      req.flush({ ...mockUser, status: UserStatus.LOCKED });
    });
  });

  describe('unlockUser', () => {
    it('should unlock user account', () => {
      service.unlockUser('user-1').subscribe(user => {
        expect(user.status).toBe(UserStatus.ACTIVE);
      });

      const req = httpMock.expectOne(`${baseUrl}/users/user-1/unlock`);
      expect(req.request.method).toBe('POST');
      req.flush({ ...mockUser, status: UserStatus.ACTIVE });
    });
  });

  describe('getRoles', () => {
    it('should fetch available roles', () => {
      service.getRoles().subscribe(roles => {
        expect(roles.length).toBe(2);
        expect(roles[0].name).toBe(UserRole.ADMIN);
      });

      const req = httpMock.expectOne(`${baseUrl}/roles`);
      expect(req.request.method).toBe('GET');
      req.flush(mockRoles);
    });
  });

  describe('getPermissions', () => {
    it('should fetch available permissions', () => {
      const mockPermissions: Permission[] = [
        { id: 'p1', name: 'claims:read', description: 'Read claims', resource: 'claims', action: 'read' },
        { id: 'p2', name: 'claims:create', description: 'Create claims', resource: 'claims', action: 'create' },
      ];

      service.getPermissions().subscribe(permissions => {
        expect(permissions.length).toBe(2);
      });

      const req = httpMock.expectOne(`${baseUrl}/permissions`);
      expect(req.request.method).toBe('GET');
      req.flush(mockPermissions);
    });
  });

  describe('getUserActivityLog', () => {
    it('should fetch user activity log', () => {
      const mockLogs = [
        { id: 'log-1', userId: 'user-1', action: 'login', resource: 'auth', timestamp: '2024-01-15T10:00:00Z' },
        { id: 'log-2', userId: 'user-1', action: 'view', resource: 'claims', resourceId: 'claim-1', timestamp: '2024-01-15T10:05:00Z' },
      ];

      service.getUserActivityLog('user-1').subscribe(logs => {
        expect(logs.length).toBe(2);
      });

      const req = httpMock.expectOne(req =>
        req.url === `${baseUrl}/users/user-1/activity`
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockLogs);
    });
  });
});
