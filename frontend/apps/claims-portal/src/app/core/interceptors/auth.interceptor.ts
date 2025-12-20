/**
 * Authentication Interceptor.
 * Source: Design Document Section 6.2, 6.4
 *
 * Adds authentication credentials and CSRF token to requests.
 * Uses HttpOnly cookies for JWT (no localStorage for security).
 */
import { HttpInterceptorFn, HttpRequest, HttpHandlerFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';

/**
 * Get CSRF token from cookie.
 */
function getCsrfToken(): string | null {
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : null;
}

/**
 * Auth interceptor function.
 */
export const authInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
) => {
  const authService = inject(AuthService);

  // Skip auth for login endpoint
  if (req.url.includes('/auth/login')) {
    return next(req);
  }

  // Clone request with credentials and security headers
  const csrfToken = getCsrfToken();

  let headers = req.headers
    .set('X-Request-ID', crypto.randomUUID());

  if (csrfToken) {
    headers = headers.set('X-CSRF-Token', csrfToken);
  }

  const authReq = req.clone({
    withCredentials: true, // Send HttpOnly cookies
    headers,
  });

  // Record activity for session timeout
  authService.recordActivity();

  return next(authReq);
};
