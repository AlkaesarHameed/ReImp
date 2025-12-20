/**
 * Login Component.
 * Source: Design Document Section 6.2
 *
 * HIPAA-compliant login with secure session handling.
 * Uses HttpOnly cookies for JWT storage.
 */
import {
  Component,
  ChangeDetectionStrategy,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    CardModule,
    InputTextModule,
    PasswordModule,
    ButtonModule,
    MessageModule,
  ],
  template: `
    <div class="login-container">
      <div class="login-card">
        <!-- Header -->
        <div class="login-header">
          <div class="logo">
            <i class="pi pi-heart-fill"></i>
          </div>
          <h1>Claims Processing System</h1>
          <p>Enterprise Healthcare Claims Management</p>
        </div>

        <!-- HIPAA Notice -->
        <div class="hipaa-notice">
          <i class="pi pi-lock"></i>
          <span>This system contains Protected Health Information (PHI). Unauthorized access is prohibited.</span>
        </div>

        <!-- Login Form -->
        <form [formGroup]="loginForm" (ngSubmit)="onSubmit()">
          @if (errorMessage()) {
            <p-message severity="error" [text]="errorMessage()!" styleClass="mb-3 w-full" />
          }

          <div class="field">
            <label for="username">Username</label>
            <input
              pInputText
              id="username"
              formControlName="username"
              class="w-full"
              placeholder="Enter your username"
              [class.ng-invalid]="isFieldInvalid('username')"
              autocomplete="username"
            />
            @if (isFieldInvalid('username')) {
              <small class="p-error">Username is required</small>
            }
          </div>

          <div class="field">
            <label for="password">Password</label>
            <p-password
              id="password"
              formControlName="password"
              [feedback]="false"
              [toggleMask]="true"
              styleClass="w-full"
              inputStyleClass="w-full"
              placeholder="Enter your password"
              autocomplete="current-password"
            />
            @if (isFieldInvalid('password')) {
              <small class="p-error">Password is required</small>
            }
          </div>

          <button
            pButton
            type="submit"
            label="Sign In"
            icon="pi pi-sign-in"
            class="w-full mt-3"
            [loading]="loading()"
            [disabled]="loading() || loginForm.invalid"
          ></button>
        </form>

        <!-- Footer -->
        <div class="login-footer">
          <p>Forgot your password? Contact your system administrator.</p>
          <p class="version">v1.0.0</p>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .login-container {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #0066CC 0%, #004C99 100%);
      padding: 1rem;
    }

    .login-card {
      background: white;
      border-radius: 12px;
      padding: 2rem;
      width: 100%;
      max-width: 420px;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
    }

    .login-header {
      text-align: center;
      margin-bottom: 1.5rem;
    }

    .logo {
      width: 60px;
      height: 60px;
      background: linear-gradient(135deg, #0066CC 0%, #004C99 100%);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 1rem;
    }

    .logo i {
      color: white;
      font-size: 1.75rem;
    }

    .login-header h1 {
      margin: 0;
      font-size: 1.5rem;
      color: #343A40;
      font-weight: 600;
    }

    .login-header p {
      margin: 0.5rem 0 0;
      color: #6C757D;
      font-size: 0.9rem;
    }

    .hipaa-notice {
      background: #FFF3CD;
      border: 1px solid #FFEEBA;
      border-radius: 6px;
      padding: 0.75rem 1rem;
      margin-bottom: 1.5rem;
      display: flex;
      align-items: flex-start;
      gap: 0.5rem;
      font-size: 0.85rem;
      color: #856404;
    }

    .hipaa-notice i {
      margin-top: 2px;
    }

    .field {
      margin-bottom: 1rem;
    }

    .field label {
      display: block;
      margin-bottom: 0.5rem;
      font-weight: 500;
      color: #343A40;
    }

    .p-error {
      color: #DC3545;
      font-size: 0.85rem;
      margin-top: 0.25rem;
    }

    .login-footer {
      text-align: center;
      margin-top: 1.5rem;
      padding-top: 1rem;
      border-top: 1px solid #DEE2E6;
    }

    .login-footer p {
      margin: 0;
      color: #6C757D;
      font-size: 0.85rem;
    }

    .login-footer .version {
      margin-top: 0.5rem;
      font-size: 0.75rem;
    }

    :host ::ng-deep .p-password {
      width: 100%;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LoginComponent {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly loading = this.authService.loading;
  readonly errorMessage = signal<string | null>(null);

  readonly loginForm = this.fb.nonNullable.group({
    username: ['', [Validators.required]],
    password: ['', [Validators.required]],
  });

  isFieldInvalid(field: 'username' | 'password'): boolean {
    const control = this.loginForm.get(field);
    return control ? control.invalid && (control.dirty || control.touched) : false;
  }

  onSubmit(): void {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.errorMessage.set(null);

    const { username, password } = this.loginForm.getRawValue();

    this.authService.login({ username, password }).subscribe({
      next: () => {
        // Redirect to return URL or dashboard
        const returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/dashboard';
        this.router.navigateByUrl(returnUrl);
      },
      error: (error) => {
        this.errorMessage.set(
          error.message || 'Login failed. Please check your credentials.'
        );
      },
    });
  }
}
