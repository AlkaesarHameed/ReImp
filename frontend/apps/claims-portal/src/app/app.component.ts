/**
 * Root Application Component.
 * Source: Design Document Section 3.2
 * Updated: Phase 6 Implementation
 *
 * Main container for the claims processing application.
 * Uses OnPush change detection for optimal performance.
 * Includes accessibility features and idle timeout handling.
 */
import { Component, ChangeDetectionStrategy, inject, OnInit, OnDestroy, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';

import { AuthService } from './core/services/auth.service';
import { WebSocketService } from './core/services/websocket.service';
import { IdleTimeoutService } from './core/services/idle-timeout.service';
import { SkipLinkComponent } from './shared/components/skip-link.component';
import { IdleWarningDialogComponent } from './shared/components/idle-warning-dialog.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    ToastModule,
    ConfirmDialogModule,
    SkipLinkComponent,
    IdleWarningDialogComponent,
  ],
  // MessageService and ConfirmationService are provided at root level in app.config.ts
  template: `
    <!-- Accessibility: Skip link for keyboard navigation -->
    <app-skip-link />

    <!-- Global notifications -->
    <p-toast position="top-right" [life]="5000" />
    <p-confirmDialog />

    <!-- Idle timeout warning -->
    <app-idle-warning-dialog />

    <!-- Main content area with ARIA landmark -->
    <main id="main-content" role="main" tabindex="-1">
      <router-outlet />
    </main>
  `,
  styles: [`
    :host {
      display: block;
      min-height: 100vh;
    }

    main:focus {
      outline: none;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent implements OnInit, OnDestroy {
  private readonly authService = inject(AuthService);
  private readonly wsService = inject(WebSocketService);
  private readonly idleService = inject(IdleTimeoutService);

  constructor() {
    // Reactively connect/disconnect WebSocket based on auth state
    // This ensures WebSocket connects after login and disconnects after logout
    effect(() => {
      const isLoggedIn = this.authService.isLoggedIn();
      if (isLoggedIn) {
        this.wsService.connect();
        this.idleService.startMonitoring();
      } else {
        this.wsService.disconnect();
        this.idleService.stopMonitoring();
      }
    });
  }

  ngOnInit(): void {
    // Note: Auth initialization is handled by APP_INITIALIZER in app.config.ts
    // This ensures auth state is ready BEFORE routing starts
    // WebSocket and idle monitoring are now handled reactively via effect()
  }

  ngOnDestroy(): void {
    this.wsService.disconnect();
    this.idleService.stopMonitoring();
  }
}
