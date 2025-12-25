/**
 * Error Interceptor.
 * Source: Design Document Section 6.3
 *
 * Handles HTTP errors globally.
 * Never exposes PHI in error messages (HIPAA compliance).
 */
import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { MessageService } from 'primeng/api';
import { LoggerService } from '../services/logger.service';

export interface ApiError {
  detail: string | { message: string; errors?: ValidationError[] };
  status_code: number;
}

export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

/**
 * Error interceptor function.
 */
export const errorInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
) => {
  const router = inject(Router);
  const messageService = inject(MessageService);
  const logger = inject(LoggerService);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      let userMessage = 'An unexpected error occurred. Please try again.';

      switch (error.status) {
        case 0:
          // Network error
          userMessage = 'Unable to connect to server. Please check your connection.';
          logger.error('Network error', 'ErrorInterceptor', { url: req.url });
          break;

        case 400:
          // Bad request - validation error
          userMessage = extractErrorMessage(error);
          break;

        case 401:
          // Unauthorized - redirect to login
          userMessage = 'Your session has expired. Please log in again.';
          router.navigate(['/auth/login']);
          break;

        case 403:
          // Forbidden
          userMessage = 'You do not have permission to perform this action.';
          logger.warn('Access denied', 'ErrorInterceptor', { url: req.url });
          break;

        case 404:
          // Not found
          userMessage = 'The requested resource was not found.';
          break;

        case 422:
          // Validation error
          userMessage = extractValidationErrors(error);
          break;

        case 429:
          // Rate limited
          userMessage = 'Too many requests. Please wait a moment and try again.';
          break;

        case 500:
        case 502:
        case 503:
        case 504:
          // Server error - don't expose details
          userMessage = 'A server error occurred. Please try again later.';
          logger.error('Server error', 'ErrorInterceptor', {
            url: req.url,
            status: error.status,
          });
          break;

        default:
          logger.error('Unexpected error', 'ErrorInterceptor', {
            url: req.url,
            status: error.status,
            message: error.message,
          });
      }

      // Show toast notification
      messageService.add({
        severity: 'error',
        summary: 'Error',
        detail: userMessage,
        life: 5000,
      });

      return throwError(() => ({
        status: error.status,
        message: userMessage,
        original: error,
      }));
    })
  );
};

/**
 * Extract error message from response.
 */
function extractErrorMessage(error: HttpErrorResponse): string {
  const body = error.error as ApiError | undefined;

  if (!body?.detail) {
    return 'Invalid request. Please check your input.';
  }

  if (typeof body.detail === 'string') {
    return sanitizeErrorMessage(body.detail);
  }

  return sanitizeErrorMessage(body.detail.message);
}

/**
 * Extract validation errors from response.
 */
function extractValidationErrors(error: HttpErrorResponse): string {
  const body = error.error as ApiError | undefined;

  if (!body?.detail) {
    return 'Validation failed. Please check your input.';
  }

  if (typeof body.detail === 'string') {
    return sanitizeErrorMessage(body.detail);
  }

  if (body.detail.errors && body.detail.errors.length > 0) {
    const firstError = body.detail.errors[0];
    return `${firstError.field}: ${sanitizeErrorMessage(firstError.message)}`;
  }

  return sanitizeErrorMessage(body.detail.message);
}

/**
 * Sanitize error message to remove potential PHI.
 * HIPAA compliance: Never expose member IDs, SSN, or other PHI in errors.
 */
function sanitizeErrorMessage(message: string | undefined | null): string {
  // Handle undefined/null messages
  if (!message || typeof message !== 'string') {
    return 'An error occurred. Please try again.';
  }

  // Remove potential PHI patterns
  return message
    .replace(/\b\d{3}-\d{2}-\d{4}\b/g, '[REDACTED]') // SSN
    .replace(/\b\d{9}\b/g, '[REDACTED]') // SSN without dashes
    .replace(/MEM-[A-Z0-9]+/gi, '[MEMBER]') // Member IDs
    .replace(/CLM-[A-Z0-9]+/gi, '[CLAIM]') // Claim IDs
    .replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, '[EMAIL]'); // Emails
}
