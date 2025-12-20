/**
 * Permission Guard.
 * Source: Design Document Section 6.0
 *
 * Protects routes based on specific permissions.
 * More granular than role-based access control.
 */
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { MessageService } from 'primeng/api';

/**
 * Create a permission guard for specific permissions.
 */
export function permissionGuard(...requiredPermissions: string[]): CanActivateFn {
  return (_route, _state) => {
    const authService = inject(AuthService);
    const router = inject(Router);
    const messageService = inject(MessageService);

    if (!authService.isAuthenticated()) {
      router.navigate(['/auth/login']);
      return false;
    }

    // Check if user has all required permissions
    const hasAllPermissions = requiredPermissions.every((permission) =>
      authService.hasPermission(permission)
    );

    if (hasAllPermissions) {
      return true;
    }

    // User doesn't have required permissions
    messageService.add({
      severity: 'error',
      summary: 'Access Denied',
      detail: 'You do not have the required permissions for this action.',
      life: 5000,
    });

    // Redirect to dashboard
    router.navigate(['/dashboard']);
    return false;
  };
}

// Pre-configured guards for common permissions
export const claimsReadGuard: CanActivateFn = permissionGuard('claims:read');
export const claimsWriteGuard: CanActivateFn = permissionGuard('claims:create', 'claims:update');
export const claimsApproveGuard: CanActivateFn = permissionGuard('claims:approve');
export const adminAccessGuard: CanActivateFn = permissionGuard('admin:access');
