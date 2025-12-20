/**
 * Login Component Unit Tests.
 * Comprehensive test coverage for login functionality.
 */
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { LoginComponent } from './login.component';
import { AuthService, LoginResponse, User } from '../../core/services/auth.service';

// Mock PrimeNG modules
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;
  let authServiceSpy: jest.Mocked<AuthService>;
  let routerSpy: jest.Mocked<Router>;
  let activatedRouteSpy: jest.Mocked<ActivatedRoute>;

  const mockUser: User = {
    id: 'usr-001',
    username: 'admin',
    email: 'admin@claims.local',
    role: 'administrator',
    permissions: ['claims:read', 'claims:write'],
    firstName: 'System',
    lastName: 'Administrator',
  };

  const mockLoginResponse: LoginResponse = {
    user: mockUser,
    expiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
  };

  beforeEach(async () => {
    // Create spies
    authServiceSpy = {
      login: jest.fn(),
      loading: jest.fn().mockReturnValue(false),
      isAuthenticated: jest.fn().mockReturnValue(false),
    } as unknown as jest.Mocked<AuthService>;

    routerSpy = {
      navigateByUrl: jest.fn().mockReturnValue(Promise.resolve(true)),
      navigate: jest.fn().mockReturnValue(Promise.resolve(true)),
    } as unknown as jest.Mocked<Router>;

    activatedRouteSpy = {
      snapshot: {
        queryParams: {},
      },
    } as unknown as jest.Mocked<ActivatedRoute>;

    await TestBed.configureTestingModule({
      imports: [
        LoginComponent,
        ReactiveFormsModule,
        NoopAnimationsModule,
        CardModule,
        InputTextModule,
        PasswordModule,
        ButtonModule,
        MessageModule,
      ],
      providers: [
        { provide: AuthService, useValue: authServiceSpy },
        { provide: Router, useValue: routerSpy },
        { provide: ActivatedRoute, useValue: activatedRouteSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('Component Initialization', () => {
    it('should create the component', () => {
      expect(component).toBeTruthy();
    });

    it('should have an empty form initially', () => {
      expect(component.loginForm.get('username')?.value).toBe('');
      expect(component.loginForm.get('password')?.value).toBe('');
    });

    it('should have invalid form initially', () => {
      expect(component.loginForm.valid).toBe(false);
    });

    it('should have no error message initially', () => {
      expect(component.errorMessage()).toBeNull();
    });
  });

  describe('Form Validation', () => {
    it('should be invalid when username is empty', () => {
      component.loginForm.patchValue({ username: '', password: 'demo123' });
      expect(component.loginForm.valid).toBe(false);
      expect(component.loginForm.get('username')?.hasError('required')).toBe(true);
    });

    it('should be invalid when password is empty', () => {
      component.loginForm.patchValue({ username: 'admin', password: '' });
      expect(component.loginForm.valid).toBe(false);
      expect(component.loginForm.get('password')?.hasError('required')).toBe(true);
    });

    it('should be valid when both fields are filled', () => {
      component.loginForm.patchValue({ username: 'admin', password: 'demo123' });
      expect(component.loginForm.valid).toBe(true);
    });
  });

  describe('isFieldInvalid()', () => {
    it('should return false for untouched field', () => {
      expect(component.isFieldInvalid('username')).toBe(false);
    });

    it('should return true for touched invalid field', () => {
      const usernameControl = component.loginForm.get('username');
      usernameControl?.markAsTouched();
      expect(component.isFieldInvalid('username')).toBe(true);
    });

    it('should return false for touched valid field', () => {
      component.loginForm.patchValue({ username: 'admin' });
      const usernameControl = component.loginForm.get('username');
      usernameControl?.markAsTouched();
      expect(component.isFieldInvalid('username')).toBe(false);
    });

    it('should return true for dirty invalid field', () => {
      const usernameControl = component.loginForm.get('username');
      usernameControl?.markAsDirty();
      expect(component.isFieldInvalid('username')).toBe(true);
    });
  });

  describe('onSubmit()', () => {
    it('should not call login if form is invalid', () => {
      component.onSubmit();
      expect(authServiceSpy.login).not.toHaveBeenCalled();
    });

    it('should mark all fields as touched if form is invalid', () => {
      component.onSubmit();
      expect(component.loginForm.get('username')?.touched).toBe(true);
      expect(component.loginForm.get('password')?.touched).toBe(true);
    });

    it('should call login service with form values', fakeAsync(() => {
      authServiceSpy.login.mockReturnValue(of(mockLoginResponse));

      component.loginForm.patchValue({ username: 'admin', password: 'demo123' });
      component.onSubmit();
      tick();

      expect(authServiceSpy.login).toHaveBeenCalledWith({
        username: 'admin',
        password: 'demo123',
      });
    }));

    it('should navigate to dashboard on successful login', fakeAsync(() => {
      authServiceSpy.login.mockReturnValue(of(mockLoginResponse));

      component.loginForm.patchValue({ username: 'admin', password: 'demo123' });
      component.onSubmit();
      tick();

      expect(routerSpy.navigateByUrl).toHaveBeenCalledWith('/dashboard');
    }));

    it('should navigate to returnUrl if provided', fakeAsync(() => {
      authServiceSpy.login.mockReturnValue(of(mockLoginResponse));
      activatedRouteSpy.snapshot.queryParams = { returnUrl: '/claims' };

      component.loginForm.patchValue({ username: 'admin', password: 'demo123' });
      component.onSubmit();
      tick();

      expect(routerSpy.navigateByUrl).toHaveBeenCalledWith('/claims');
    }));

    it('should clear error message before login attempt', fakeAsync(() => {
      // Set an existing error
      component.errorMessage.set('Previous error');

      authServiceSpy.login.mockReturnValue(of(mockLoginResponse));
      component.loginForm.patchValue({ username: 'admin', password: 'demo123' });
      component.onSubmit();

      // Error should be cleared immediately
      expect(component.errorMessage()).toBeNull();
    }));

    it('should set error message on login failure', fakeAsync(() => {
      const error = new Error('Invalid credentials');
      authServiceSpy.login.mockReturnValue(throwError(() => error));

      component.loginForm.patchValue({ username: 'admin', password: 'wrong' });
      component.onSubmit();
      tick();

      expect(component.errorMessage()).toBe('Invalid credentials');
    }));

    it('should set default error message if error has no message', fakeAsync(() => {
      authServiceSpy.login.mockReturnValue(throwError(() => ({})));

      component.loginForm.patchValue({ username: 'admin', password: 'wrong' });
      component.onSubmit();
      tick();

      expect(component.errorMessage()).toBe('Login failed. Please check your credentials.');
    }));
  });

  describe('Loading State', () => {
    it('should reflect loading state from auth service', () => {
      authServiceSpy.loading.mockReturnValue(true);
      expect(component.loading()).toBe(true);
    });
  });

  describe('UI Rendering', () => {
    it('should render login form', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.querySelector('form')).toBeTruthy();
    });

    it('should render username input', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.querySelector('#username')).toBeTruthy();
    });

    it('should render HIPAA notice', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      const hipaaNotice = compiled.querySelector('.hipaa-notice');
      expect(hipaaNotice).toBeTruthy();
      expect(hipaaNotice?.textContent).toContain('Protected Health Information');
    });

    it('should render Claims Processing System title', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.querySelector('h1')?.textContent).toContain('Claims Processing System');
    });
  });

  describe('Data Extraction', () => {
    it('should extract form data correctly', () => {
      component.loginForm.patchValue({
        username: 'testuser',
        password: 'testpass',
      });

      const formValue = component.loginForm.getRawValue();
      expect(formValue.username).toBe('testuser');
      expect(formValue.password).toBe('testpass');
    });

    it('should have extractable error message', fakeAsync(() => {
      const errorMsg = 'Test error message';
      const error = new Error(errorMsg);
      authServiceSpy.login.mockReturnValue(throwError(() => error));

      component.loginForm.patchValue({ username: 'admin', password: 'wrong' });
      component.onSubmit();
      tick();

      expect(component.errorMessage()).toBe(errorMsg);
    }));
  });

  describe('Accessibility', () => {
    it('should have autocomplete attribute on username input', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      const usernameInput = compiled.querySelector('#username');
      expect(usernameInput?.getAttribute('autocomplete')).toBe('username');
    });

    it('should have label for username input', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      const label = compiled.querySelector('label[for="username"]');
      expect(label).toBeTruthy();
      expect(label?.textContent).toContain('Username');
    });

    it('should have label for password input', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      const label = compiled.querySelector('label[for="password"]');
      expect(label).toBeTruthy();
      expect(label?.textContent).toContain('Password');
    });
  });
});
