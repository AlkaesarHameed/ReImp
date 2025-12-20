/**
 * Audit Interceptor.
 * Source: Design Document Section 6.3
 *
 * Logs all PHI access for HIPAA compliance.
 * Automatically detects PHI-related endpoints.
 */
import { HttpInterceptorFn, HttpRequest, HttpHandlerFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { tap } from 'rxjs';
import { AuditService } from '../services/audit.service';

/**
 * Extract resource ID from URL.
 */
function extractResourceId(url: string): string | undefined {
  // Match patterns like /claims/123 or /members/abc-def
  const match = url.match(/\/[a-z]+\/([a-zA-Z0-9-]+)(?:\/|$|\?)/);
  return match ? match[1] : undefined;
}

/**
 * Audit interceptor function.
 */
export const auditInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
) => {
  const auditService = inject(AuditService);

  // Only audit PHI access
  if (!auditService.isPHIAccess(req.url)) {
    return next(req);
  }

  const resourceId = extractResourceId(req.url);

  return next(req).pipe(
    tap({
      next: () => {
        // Log successful PHI access
        auditService.logHttpAccess(req.method, req.url, resourceId);
      },
      error: () => {
        // Also log failed attempts (potential security concern)
        auditService.logHttpAccess(req.method, req.url, resourceId);
      },
    })
  );
};
