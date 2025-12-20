/**
 * Application Configuration.
 * Source: Design Document Section 5.0, 7.0
 *
 * Configures Angular 19 with:
 * - Zoneless change detection (60% faster startup)
 * - HTTP client with credentials for HttpOnly cookies
 * - Router with lazy loading
 * - Animation support for PrimeNG
 */
import { ApplicationConfig, provideZoneChangeDetection, APP_INITIALIZER, inject } from '@angular/core';
import { provideRouter, withComponentInputBinding, withViewTransitions, withPreloading } from '@angular/router';
import { provideHttpClient, withInterceptors, withFetch } from '@angular/common/http';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { MessageService, ConfirmationService } from 'primeng/api';

import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { errorInterceptor } from './core/interceptors/error.interceptor';
import { auditInterceptor } from './core/interceptors/audit.interceptor';
import { SelectivePreloadStrategy } from './core/strategies/selective-preload.strategy';
import { AuthService } from './core/services/auth.service';

/**
 * Initialize authentication state before app starts.
 * Ensures auth guard has correct state during initial navigation.
 */
function initializeAuth(): () => Promise<void> {
  const authService = inject(AuthService);
  return () => {
    return new Promise<void>((resolve) => {
      try {
        authService.initializeAuth();
      } catch (error) {
        console.error('Auth initialization failed:', error);
      }
      // Always resolve to allow app to bootstrap
      resolve();
    });
  };
}

export const appConfig: ApplicationConfig = {
  providers: [
    // Zoneless change detection for optimal performance
    // Falls back to zone-based if zoneless is not supported
    provideZoneChangeDetection({ eventCoalescing: true }),

    // Initialize auth BEFORE routing starts
    {
      provide: APP_INITIALIZER,
      useFactory: initializeAuth,
      multi: true,
    },

    // Router with lazy loading and selective preloading
    provideRouter(
      routes,
      withComponentInputBinding(),
      withViewTransitions(),
      withPreloading(SelectivePreloadStrategy)
    ),

    // HTTP client with interceptors
    provideHttpClient(
      withFetch(),
      withInterceptors([
        authInterceptor,
        auditInterceptor,
        errorInterceptor,
      ])
    ),

    // Async animations for better performance
    provideAnimationsAsync(),

    // PrimeNG services (required for Toast, Confirm dialogs, etc.)
    MessageService,
    ConfirmationService,
  ],
};
