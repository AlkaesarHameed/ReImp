/**
 * Authentication Service.
 * Source: Design Document Section 6.2
 *
 * Handles user authentication with JWT tokens stored in HttpOnly cookies.
 * Implements HIPAA-compliant session management with 15-minute timeout.
 */
import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap, catchError, of } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  permissions: string[];
  firstName?: string;
  lastName?: string;
}

export type UserRole = 'claims_processor' | 'supervisor' | 'administrator' | 'auditor' | 'member';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  expiresAt: string;
}

// Mock users for development
const MOCK_USERS: Record<string, User> = {
  admin: {
    id: 'usr-001',
    username: 'admin',
    email: 'admin@claims.local',
    role: 'administrator',
    permissions: ['claims:read', 'claims:write', 'claims:create', 'claims:update', 'claims:approve', 'admin:users', 'admin:settings', 'admin:access', 'reports:view'],
    firstName: 'System',
    lastName: 'Administrator',
  },
  processor: {
    id: 'usr-002',
    username: 'processor',
    email: 'processor@claims.local',
    role: 'claims_processor',
    permissions: ['claims:read', 'claims:write', 'claims:create', 'claims:update'],
    firstName: 'Claims',
    lastName: 'Processor',
  },
  supervisor: {
    id: 'usr-003',
    username: 'supervisor',
    email: 'supervisor@claims.local',
    role: 'supervisor',
    permissions: ['claims:read', 'claims:write', 'claims:create', 'claims:update', 'claims:approve', 'reports:view'],
    firstName: 'Team',
    lastName: 'Supervisor',
  },
};

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  // Enable mock auth in development
  private readonly useMockAuth = !environment.production;

  // Reactive state using signals
  private readonly userSignal = signal<User | null>(null);
  private readonly loadingSignal = signal<boolean>(false);
  private sessionTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private lastActivityTime = Date.now();

  // Public computed signals
  readonly user = this.userSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();
  readonly isLoggedIn = computed(() => this.userSignal() !== null);
  readonly userRole = computed(() => this.userSignal()?.role ?? null);
  readonly userPermissions = computed(() => this.userSignal()?.permissions ?? []);

  /**
   * Initialize authentication state from stored session.
   */
  initializeAuth(): void {
    this.loadingSignal.set(true);

    // Check for stored mock user in development
    if (this.useMockAuth) {
      const storedUser = sessionStorage.getItem('mock_user');
      if (storedUser) {
        this.userSignal.set(JSON.parse(storedUser));
        this.startSessionMonitoring();
      }
      this.loadingSignal.set(false);
      return;
    }

    this.http.get<User>(`${environment.apiUrl}/auth/me`, {
      withCredentials: true,
    }).pipe(
      tap((user) => {
        this.userSignal.set(user);
        this.startSessionMonitoring();
      }),
      catchError(() => {
        this.userSignal.set(null);
        return of(null);
      }),
    ).subscribe(() => {
      this.loadingSignal.set(false);
    });
  }

  /**
   * Authenticate user with credentials.
   */
  login(credentials: LoginRequest): Observable<LoginResponse> {
    this.loadingSignal.set(true);

    // Mock authentication in development
    if (this.useMockAuth) {
      return this.mockLogin(credentials);
    }

    return this.http.post<LoginResponse>(
      `${environment.apiUrl}/auth/login`,
      credentials,
      { withCredentials: true }
    ).pipe(
      tap((response) => {
        this.userSignal.set(response.user);
        this.startSessionMonitoring();
        this.loadingSignal.set(false);
      }),
      catchError((error) => {
        this.loadingSignal.set(false);
        throw error;
      }),
    );
  }

  /**
   * Mock login for development.
   */
  private mockLogin(credentials: LoginRequest): Observable<LoginResponse> {
    const user = MOCK_USERS[credentials.username.toLowerCase()];

    if (!user || credentials.password !== 'demo123') {
      this.loadingSignal.set(false);
      return new Observable((subscriber) => {
        setTimeout(() => {
          subscriber.error(new Error('Invalid username or password. Use: admin/demo123, processor/demo123, or supervisor/demo123'));
        }, 500);
      });
    }

    return new Observable<LoginResponse>((subscriber) => {
      setTimeout(() => {
        sessionStorage.setItem('mock_user', JSON.stringify(user));
        this.userSignal.set(user);
        this.startSessionMonitoring();
        this.loadingSignal.set(false);

        subscriber.next({
          user,
          expiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
        });
        subscriber.complete();
      }, 500);
    });
  }

  /**
   * Logout user and clear session.
   */
  logout(): Observable<void> {
    // Mock logout in development
    if (this.useMockAuth) {
      sessionStorage.removeItem('mock_user');
      this.clearSession();
      this.router.navigate(['/auth/login']);
      return of(undefined);
    }

    return this.http.post<void>(
      `${environment.apiUrl}/auth/logout`,
      {},
      { withCredentials: true }
    ).pipe(
      tap(() => {
        this.clearSession();
        this.router.navigate(['/auth/login']);
      }),
      catchError(() => {
        this.clearSession();
        this.router.navigate(['/auth/login']);
        return of(undefined);
      }),
    );
  }

  /**
   * Check if user is authenticated.
   */
  isAuthenticated(): boolean {
    return this.userSignal() !== null;
  }

  /**
   * Check if user has specific permission.
   */
  hasPermission(permission: string): boolean {
    const permissions = this.userSignal()?.permissions ?? [];
    return permissions.includes(permission);
  }

  /**
   * Check if user has any of the specified roles.
   */
  hasRole(...roles: UserRole[]): boolean {
    const userRole = this.userSignal()?.role;
    return userRole !== null && roles.includes(userRole as UserRole);
  }

  /**
   * Record user activity to reset session timeout.
   */
  recordActivity(): void {
    this.lastActivityTime = Date.now();
  }

  /**
   * Start session monitoring for HIPAA-compliant timeout.
   */
  private startSessionMonitoring(): void {
    this.stopSessionMonitoring();

    // Check for inactivity every minute
    this.sessionTimeoutId = setInterval(() => {
      const inactiveTime = Date.now() - this.lastActivityTime;

      if (inactiveTime >= environment.sessionTimeout) {
        console.warn('Session timeout due to inactivity');
        this.logout().subscribe();
      }
    }, 60 * 1000);

    // Track user activity
    this.setupActivityTracking();
  }

  /**
   * Stop session monitoring.
   */
  private stopSessionMonitoring(): void {
    if (this.sessionTimeoutId) {
      clearInterval(this.sessionTimeoutId);
      this.sessionTimeoutId = null;
    }
  }

  /**
   * Setup activity tracking for session timeout.
   */
  private setupActivityTracking(): void {
    const events = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    events.forEach((event) => {
      document.addEventListener(event, () => this.recordActivity(), { passive: true });
    });
  }

  /**
   * Clear session state.
   */
  private clearSession(): void {
    this.userSignal.set(null);
    this.stopSessionMonitoring();
  }
}
