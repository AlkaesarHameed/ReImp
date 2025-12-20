/**
 * Idle Timeout Service.
 * Source: Phase 6 Implementation Document
 *
 * HIPAA-compliant session timeout handling.
 * Automatically logs out users after period of inactivity.
 */
import { Injectable, inject, signal, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { fromEvent, merge, Subject } from 'rxjs';
import { takeUntil, debounceTime } from 'rxjs/operators';

import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class IdleTimeoutService implements OnDestroy {
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);
  private readonly destroy$ = new Subject<void>();

  // Default timeouts (can be overridden by environment)
  private readonly IDLE_TIMEOUT = environment.production
    ? (environment as any).security?.maxIdleTime || 10 * 60 * 1000  // 10 minutes
    : 30 * 60 * 1000; // 30 minutes in dev

  private readonly WARNING_TIME = 60 * 1000; // 1 minute warning before logout

  readonly isIdle = signal(false);
  readonly showWarning = signal(false);
  readonly remainingTime = signal(0);

  private idleTimer: ReturnType<typeof setTimeout> | null = null;
  private warningTimer: ReturnType<typeof setTimeout> | null = null;
  private countdownInterval: ReturnType<typeof setInterval> | null = null;

  /**
   * Start monitoring user activity.
   * Should be called after successful login.
   */
  startMonitoring(): void {
    // User activity events
    const activityEvents$ = merge(
      fromEvent(document, 'mousemove'),
      fromEvent(document, 'mousedown'),
      fromEvent(document, 'keypress'),
      fromEvent(document, 'touchstart'),
      fromEvent(document, 'scroll')
    );

    // Reset timer on any activity
    activityEvents$.pipe(
      debounceTime(500),
      takeUntil(this.destroy$)
    ).subscribe(() => {
      this.resetTimer();
    });

    // Start initial timer
    this.resetTimer();
  }

  /**
   * Stop monitoring (e.g., after logout).
   */
  stopMonitoring(): void {
    this.clearTimers();
    this.isIdle.set(false);
    this.showWarning.set(false);
  }

  /**
   * Reset the idle timer.
   */
  private resetTimer(): void {
    this.clearTimers();
    this.isIdle.set(false);
    this.showWarning.set(false);

    // Set warning timer
    this.warningTimer = setTimeout(() => {
      this.showIdleWarning();
    }, this.IDLE_TIMEOUT - this.WARNING_TIME);

    // Set logout timer
    this.idleTimer = setTimeout(() => {
      this.handleIdleTimeout();
    }, this.IDLE_TIMEOUT);
  }

  /**
   * Show warning before automatic logout.
   */
  private showIdleWarning(): void {
    this.showWarning.set(true);
    this.remainingTime.set(this.WARNING_TIME / 1000);

    // Start countdown
    this.countdownInterval = setInterval(() => {
      const current = this.remainingTime();
      if (current > 0) {
        this.remainingTime.set(current - 1);
      }
    }, 1000);
  }

  /**
   * Handle automatic logout due to inactivity.
   */
  private handleIdleTimeout(): void {
    this.isIdle.set(true);
    this.showWarning.set(false);
    this.clearTimers();

    // Log the timeout event
    console.warn('Session timed out due to inactivity');

    // Perform logout
    this.authService.logout().subscribe({
      complete: () => {
        this.router.navigate(['/auth/login'], {
          queryParams: { reason: 'timeout' }
        });
      }
    });
  }

  /**
   * Extend session when user responds to warning.
   */
  extendSession(): void {
    this.resetTimer();
  }

  /**
   * Clear all timers.
   */
  private clearTimers(): void {
    if (this.idleTimer) {
      clearTimeout(this.idleTimer);
      this.idleTimer = null;
    }
    if (this.warningTimer) {
      clearTimeout(this.warningTimer);
      this.warningTimer = null;
    }
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
      this.countdownInterval = null;
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.clearTimers();
  }
}
