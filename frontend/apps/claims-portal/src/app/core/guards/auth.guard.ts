/**
 * Authentication Guard.
 * Source: Design Document Section 6.0
 *
 * Protects routes that require authentication.
 * Redirects to login if user is not authenticated.
 * Uses UrlTree for proper zoneless change detection support.
 */
import { inject } from '@angular/core';
import { CanActivateFn, Router, UrlTree } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = (_route, state): boolean | UrlTree => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated()) {
    return true;
  }

  // Store the attempted URL for redirecting after login
  const returnUrl = state.url;

  // Return UrlTree for proper routing with zoneless change detection
  return router.createUrlTree(['/auth/login'], {
    queryParams: { returnUrl },
  });
};
