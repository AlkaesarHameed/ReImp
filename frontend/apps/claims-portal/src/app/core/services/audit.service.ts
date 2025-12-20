/**
 * Audit Service.
 * Source: Design Document Section 6.3
 *
 * HIPAA-compliant audit logging for PHI access.
 * Logs all access to protected health information.
 */
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';

export interface AuditEntry {
  action: AuditAction;
  resource: string;
  resourceId?: string;
  method: string;
  url: string;
  userId?: string;
  username?: string;
  role?: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export type AuditAction =
  | 'view'
  | 'create'
  | 'update'
  | 'delete'
  | 'export'
  | 'print'
  | 'search'
  | 'login'
  | 'logout';

@Injectable({
  providedIn: 'root',
})
export class AuditService {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly buffer: AuditEntry[] = [];
  private readonly bufferSize = 10;
  private flushTimer: ReturnType<typeof setTimeout> | null = null;

  // PHI-related URL patterns that require audit logging
  private readonly phiPatterns = [
    /\/claims/,
    /\/members/,
    /\/eligibility/,
    /\/providers/,
    /\/policies/,
    /\/documents/,
  ];

  /**
   * Check if URL accesses PHI.
   */
  isPHIAccess(url: string): boolean {
    return this.phiPatterns.some((pattern) => pattern.test(url));
  }

  /**
   * Log an audit entry.
   */
  log(entry: Omit<AuditEntry, 'userId' | 'username' | 'role' | 'timestamp'>): void {
    if (!environment.enableAuditLogging) {
      return;
    }

    const user = this.authService.user();

    const fullEntry: AuditEntry = {
      ...entry,
      userId: user?.id,
      username: user?.username,
      role: user?.role,
      timestamp: new Date().toISOString(),
    };

    this.buffer.push(fullEntry);

    // Flush if buffer is full
    if (this.buffer.length >= this.bufferSize) {
      this.flush();
    } else {
      // Schedule flush after 5 seconds
      this.scheduleFlush();
    }
  }

  /**
   * Log PHI access from HTTP request.
   */
  logHttpAccess(method: string, url: string, resourceId?: string): void {
    if (!this.isPHIAccess(url)) {
      return;
    }

    const action = this.methodToAction(method);
    const resource = this.extractResource(url);

    this.log({
      action,
      resource,
      resourceId,
      method,
      url,
    });
  }

  /**
   * Flush buffered audit entries to server.
   */
  flush(): void {
    if (this.buffer.length === 0) {
      return;
    }

    const entries = [...this.buffer];
    this.buffer.length = 0;

    if (this.flushTimer) {
      clearTimeout(this.flushTimer);
      this.flushTimer = null;
    }

    // Send to server (fire and forget)
    this.http.post(
      `${environment.apiUrl}/audit/batch`,
      { entries },
      { withCredentials: true }
    ).subscribe({
      error: (error) => {
        console.error('Failed to flush audit logs:', error);
        // Re-add to buffer for retry
        this.buffer.push(...entries);
      },
    });
  }

  /**
   * Schedule buffer flush.
   */
  private scheduleFlush(): void {
    if (this.flushTimer) {
      return;
    }

    this.flushTimer = setTimeout(() => {
      this.flush();
    }, 5000);
  }

  /**
   * Map HTTP method to audit action.
   */
  private methodToAction(method: string): AuditAction {
    switch (method.toUpperCase()) {
      case 'GET':
        return 'view';
      case 'POST':
        return 'create';
      case 'PUT':
      case 'PATCH':
        return 'update';
      case 'DELETE':
        return 'delete';
      default:
        return 'view';
    }
  }

  /**
   * Extract resource type from URL.
   */
  private extractResource(url: string): string {
    const match = url.match(/\/api\/v1\/(\w+)/);
    return match ? match[1] : 'unknown';
  }
}
