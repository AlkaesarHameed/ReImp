/**
 * Idle Warning Dialog Component.
 * Source: Phase 6 Implementation Document
 *
 * Displays warning before automatic logout due to inactivity.
 * HIPAA-compliant session timeout notification.
 */
import { Component, ChangeDetectionStrategy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { ProgressBarModule } from 'primeng/progressbar';

import { IdleTimeoutService } from '../../core/services/idle-timeout.service';

@Component({
  selector: 'app-idle-warning-dialog',
  standalone: true,
  imports: [CommonModule, DialogModule, ButtonModule, ProgressBarModule],
  template: `
    <p-dialog
      header="Session Timeout Warning"
      [visible]="idleService.showWarning()"
      [modal]="true"
      [closable]="false"
      [style]="{ width: '400px' }"
      [draggable]="false"
      [resizable]="false"
      styleClass="idle-warning-dialog"
    >
      <div class="warning-content">
        <div class="warning-icon">
          <i class="pi pi-exclamation-triangle"></i>
        </div>
        <p class="warning-message">
          Your session is about to expire due to inactivity.
        </p>
        <p class="warning-countdown">
          You will be logged out in <strong>{{ idleService.remainingTime() }}</strong> seconds.
        </p>
        <p-progressBar
          [value]="getProgressValue()"
          [showValue]="false"
          styleClass="countdown-bar"
        ></p-progressBar>
      </div>
      <ng-template pTemplate="footer">
        <button
          pButton
          label="Stay Logged In"
          icon="pi pi-refresh"
          (click)="extendSession()"
          class="p-button-lg"
          autofocus
        ></button>
        <button
          pButton
          label="Log Out Now"
          icon="pi pi-sign-out"
          (click)="logout()"
          class="p-button-outlined p-button-secondary"
        ></button>
      </ng-template>
    </p-dialog>
  `,
  styles: [`
    .warning-content {
      text-align: center;
      padding: 1rem;
    }

    .warning-icon {
      font-size: 3rem;
      color: #F59E0B;
      margin-bottom: 1rem;
    }

    .warning-message {
      font-size: 1.1rem;
      color: #374151;
      margin-bottom: 0.5rem;
    }

    .warning-countdown {
      font-size: 1rem;
      color: #6B7280;
      margin-bottom: 1rem;
    }

    .warning-countdown strong {
      color: #DC3545;
      font-size: 1.25rem;
    }

    :host ::ng-deep .countdown-bar .p-progressbar {
      height: 6px;
      background: #E5E7EB;
    }

    :host ::ng-deep .countdown-bar .p-progressbar-value {
      background: linear-gradient(90deg, #F59E0B 0%, #DC3545 100%);
    }

    :host ::ng-deep .idle-warning-dialog .p-dialog-footer {
      display: flex;
      justify-content: center;
      gap: 1rem;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class IdleWarningDialogComponent {
  readonly idleService = inject(IdleTimeoutService);

  private readonly WARNING_TOTAL = 60; // seconds

  getProgressValue(): number {
    return ((this.WARNING_TOTAL - this.idleService.remainingTime()) / this.WARNING_TOTAL) * 100;
  }

  extendSession(): void {
    this.idleService.extendSession();
  }

  logout(): void {
    // Force immediate logout
    window.location.href = '/auth/login?reason=manual';
  }
}
