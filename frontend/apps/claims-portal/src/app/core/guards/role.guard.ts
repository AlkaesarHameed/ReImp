/**
 * Role Guard.
 * Source: Design Document Section 6.0
 *
 * Protects routes based on user roles.
 * Used for admin-only or supervisor-only routes.
 */
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService, UserRole } from '../services/auth.service';
import { MessageService } from 'primeng/api';

/**
 * Create a role guard for specific roles.
 */
export function roleGuard(...allowedRoles: UserRole[]): CanActivateFn {
  return (_route, _state) => {
    const authService = inject(AuthService);
    const router = inject(Router);
    const messageService = inject(MessageService);

    if (!authService.isAuthenticated()) {
      router.navigate(['/auth/login']);
      return false;
    }

    if (authService.hasRole(...allowedRoles)) {
      return true;
    }

    // User doesn't have required role
    messageService.add({
      severity: 'error',
      summary: 'Access Denied',
      detail: 'You do not have permission to access this page.',
      life: 5000,
    });

    // Redirect to dashboard
    router.navigate(['/dashboard']);
    return false;
  };
}

// Pre-configured guards for common use cases
export const adminGuard: CanActivateFn = roleGuard('administrator');
export const supervisorGuard: CanActivateFn = roleGuard('administrator', 'supervisor');
export const processorGuard: CanActivateFn = roleGuard('administrator', 'supervisor', 'claims_processor');
