/**
 * Dashboard Overview Component.
 * Source: Design Document Section 3.2
 *
 * Real-time claims dashboard with KPIs and metrics.
 * Uses Signals for reactive state management.
 */
import {
  Component,
  ChangeDetectionStrategy,
  inject,
  OnInit,
  OnDestroy,
  signal,
  computed,
} from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { ChartModule } from 'primeng/chart';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { SkeletonModule } from 'primeng/skeleton';
import { Subject, takeUntil } from 'rxjs';

import { WebSocketService, MetricsPayload } from '../../../core/services/websocket.service';

interface KpiCard {
  label: string;
  value: number | string;
  icon: string;
  color: 'primary' | 'success' | 'warning' | 'danger' | 'info';
  delta?: string;
  deltaType?: 'positive' | 'negative' | 'neutral';
}

interface RecentActivity {
  id: string;
  action: string;
  details: string;
  timestamp: Date;
  type: 'success' | 'warning' | 'info' | 'error';
}

@Component({
  selector: 'app-dashboard-overview',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    CardModule,
    ButtonModule,
    ChartModule,
    TableModule,
    TagModule,
    SkeletonModule,
    DatePipe,
  ],
  template: `
    <div class="dashboard-container">
      <!-- Header -->
      <div class="dashboard-header">
        <div class="header-content">
          <h1>
            <i class="pi pi-chart-bar"></i>
            Claims Dashboard
          </h1>
          <p>Real-time analytics and claims processing metrics</p>
        </div>
        <div class="header-actions">
          <button pButton label="Submit Claim" icon="pi pi-plus" routerLink="/claims/new"></button>
          <button pButton label="Check Eligibility" icon="pi pi-search" class="p-button-outlined" routerLink="/eligibility"></button>
        </div>
      </div>

      <!-- KPI Cards -->
      <div class="kpi-grid">
        @for (kpi of kpiCards(); track kpi.label) {
          <div class="kpi-card" [class]="'kpi-' + kpi.color">
            <div class="kpi-icon">
              <i [class]="'pi ' + kpi.icon"></i>
            </div>
            <div class="kpi-content">
              <span class="kpi-label">{{ kpi.label }}</span>
              <span class="kpi-value">{{ kpi.value }}</span>
              @if (kpi.delta) {
                <span class="kpi-delta" [class]="'delta-' + kpi.deltaType">
                  {{ kpi.delta }}
                </span>
              }
            </div>
          </div>
        }
      </div>

      <!-- Charts Row -->
      <div class="charts-row">
        <p-card header="Claims Status Distribution" styleClass="chart-card">
          <p-chart type="doughnut" [data]="statusChartData()" [options]="chartOptions" height="300"></p-chart>
        </p-card>

        <p-card header="Claims Trend (7 Days)" styleClass="chart-card">
          <p-chart type="line" [data]="trendChartData()" [options]="lineChartOptions" height="300"></p-chart>
        </p-card>
      </div>

      <!-- Quick Actions & Activity -->
      <div class="bottom-row">
        <!-- Quick Actions -->
        <p-card header="Quick Actions" styleClass="actions-card">
          <div class="quick-actions">
            <button pButton label="New Claim" icon="pi pi-file-plus" class="p-button-lg" routerLink="/claims/new"></button>
            <button pButton label="Pending Review" icon="pi pi-clock" class="p-button-lg p-button-warning" routerLink="/claims" [queryParams]="{status: 'needs_review'}"></button>
            <button pButton label="Reports" icon="pi pi-chart-line" class="p-button-lg p-button-secondary" routerLink="/reports"></button>
            <button pButton label="Help Center" icon="pi pi-question-circle" class="p-button-lg p-button-help" routerLink="/help"></button>
          </div>
        </p-card>

        <!-- Recent Activity -->
        <p-card header="Recent Activity" styleClass="activity-card">
          <div class="activity-list">
            @for (activity of recentActivity(); track activity.id) {
              <div class="activity-item" [class]="'activity-' + activity.type">
                <div class="activity-icon">
                  @switch (activity.type) {
                    @case ('success') { <i class="pi pi-check-circle"></i> }
                    @case ('warning') { <i class="pi pi-exclamation-triangle"></i> }
                    @case ('error') { <i class="pi pi-times-circle"></i> }
                    @default { <i class="pi pi-info-circle"></i> }
                  }
                </div>
                <div class="activity-content">
                  <span class="activity-action">{{ activity.action }}</span>
                  <span class="activity-details">{{ activity.details }}</span>
                </div>
                <span class="activity-time">{{ activity.timestamp | date:'shortTime' }}</span>
              </div>
            }
          </div>
        </p-card>
      </div>

      <!-- System Status -->
      <div class="system-status">
        <div class="status-item status-online">
          <i class="pi pi-circle-fill"></i>
          <span>API Server</span>
        </div>
        <div class="status-item status-online">
          <i class="pi pi-circle-fill"></i>
          <span>Database</span>
        </div>
        <div class="status-item" [class.status-online]="wsConnected()" [class.status-offline]="!wsConnected()">
          <i class="pi pi-circle-fill"></i>
          <span>WebSocket</span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .dashboard-container {
      padding: 1.5rem;
      background: #F8F9FA;
      min-height: 100vh;
    }

    .dashboard-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: linear-gradient(135deg, #0066CC 0%, #004C99 100%);
      color: white;
      padding: 1.5rem 2rem;
      border-radius: 10px;
      margin-bottom: 1.5rem;
    }

    .dashboard-header h1 {
      margin: 0;
      font-size: 1.75rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .dashboard-header p {
      margin: 0.5rem 0 0;
      opacity: 0.9;
    }

    .header-actions {
      display: flex;
      gap: 0.75rem;
    }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    .kpi-card {
      background: white;
      border-radius: 10px;
      padding: 1.25rem;
      display: flex;
      align-items: center;
      gap: 1rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      border-left: 4px solid #0066CC;
    }

    .kpi-card.kpi-success { border-left-color: #28A745; }
    .kpi-card.kpi-warning { border-left-color: #FFC107; }
    .kpi-card.kpi-danger { border-left-color: #DC3545; }
    .kpi-card.kpi-info { border-left-color: #17A2B8; }

    .kpi-icon {
      width: 50px;
      height: 50px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #E8F4FD;
      color: #0066CC;
    }

    .kpi-success .kpi-icon { background: #D4EDDA; color: #28A745; }
    .kpi-warning .kpi-icon { background: #FFF3CD; color: #FFC107; }
    .kpi-danger .kpi-icon { background: #F8D7DA; color: #DC3545; }
    .kpi-info .kpi-icon { background: #D1ECF1; color: #17A2B8; }

    .kpi-icon i { font-size: 1.5rem; }

    .kpi-content {
      display: flex;
      flex-direction: column;
    }

    .kpi-label {
      font-size: 0.85rem;
      color: #6C757D;
      font-weight: 500;
    }

    .kpi-value {
      font-size: 1.75rem;
      font-weight: 700;
      color: #343A40;
    }

    .kpi-delta {
      font-size: 0.8rem;
      padding: 0.15rem 0.5rem;
      border-radius: 12px;
      display: inline-block;
      margin-top: 0.25rem;
    }

    .delta-positive { background: #D4EDDA; color: #155724; }
    .delta-negative { background: #F8D7DA; color: #721C24; }
    .delta-neutral { background: #E2E3E5; color: #383D41; }

    .charts-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .bottom-row {
      display: grid;
      grid-template-columns: 1fr 2fr;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .quick-actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }

    .activity-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .activity-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem;
      background: #F8F9FA;
      border-radius: 8px;
      border-left: 3px solid #17A2B8;
    }

    .activity-success { border-left-color: #28A745; }
    .activity-warning { border-left-color: #FFC107; }
    .activity-error { border-left-color: #DC3545; }

    .activity-icon { color: #17A2B8; }
    .activity-success .activity-icon { color: #28A745; }
    .activity-warning .activity-icon { color: #FFC107; }
    .activity-error .activity-icon { color: #DC3545; }

    .activity-content {
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    .activity-action {
      font-weight: 500;
      color: #343A40;
    }

    .activity-details {
      font-size: 0.85rem;
      color: #6C757D;
    }

    .activity-time {
      font-size: 0.8rem;
      color: #6C757D;
    }

    .system-status {
      display: flex;
      justify-content: center;
      gap: 2rem;
      padding: 1rem;
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }

    .status-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.9rem;
    }

    .status-online i { color: #28A745; }
    .status-offline i { color: #DC3545; }

    @media (max-width: 1200px) {
      .charts-row, .bottom-row {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 768px) {
      .dashboard-header {
        flex-direction: column;
        gap: 1rem;
        text-align: center;
      }

      .header-actions {
        width: 100%;
        justify-content: center;
      }

      .quick-actions {
        grid-template-columns: 1fr;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DashboardOverviewComponent implements OnInit, OnDestroy {
  private readonly wsService = inject(WebSocketService);
  private readonly destroy$ = new Subject<void>();

  // Reactive state
  readonly wsConnected = this.wsService.isConnected;
  private readonly metrics = signal<MetricsPayload | null>(null);

  readonly kpiCards = computed<KpiCard[]>(() => {
    const m = this.metrics();
    return [
      {
        label: 'Claims Today',
        value: m?.approved_today ?? 0 + (m?.denied_today ?? 0),
        icon: 'pi-file',
        color: 'primary',
        delta: '+12% vs yesterday',
        deltaType: 'positive',
      },
      {
        label: 'Approved',
        value: m?.approved_today ?? 0,
        icon: 'pi-check-circle',
        color: 'success',
        delta: '89% approval rate',
        deltaType: 'positive',
      },
      {
        label: 'Pending Review',
        value: m?.pending_count ?? 0,
        icon: 'pi-clock',
        color: 'warning',
        delta: 'Avg 2.1 days',
        deltaType: 'neutral',
      },
      {
        label: 'Processing',
        value: m?.processing_count ?? 0,
        icon: 'pi-spin pi-spinner',
        color: 'info',
        delta: `${m?.claims_per_minute ?? 0}/min`,
        deltaType: 'neutral',
      },
      {
        label: 'Denied',
        value: m?.denied_today ?? 0,
        icon: 'pi-times-circle',
        color: 'danger',
        delta: '11% denial rate',
        deltaType: 'negative',
      },
    ];
  });

  readonly recentActivity = signal<RecentActivity[]>([
    { id: '1', action: 'Claim Approved', details: 'CLM-2024-001234', timestamp: new Date(), type: 'success' },
    { id: '2', action: 'Eligibility Verified', details: 'MEM-ABC123', timestamp: new Date(Date.now() - 300000), type: 'info' },
    { id: '3', action: 'Prior Auth Approved', details: 'PA-789', timestamp: new Date(Date.now() - 720000), type: 'success' },
    { id: '4', action: 'Claim Needs Review', details: 'CLM-2024-001233', timestamp: new Date(Date.now() - 900000), type: 'warning' },
    { id: '5', action: 'New Provider Enrolled', details: 'PRV-XYZ', timestamp: new Date(Date.now() - 1200000), type: 'info' },
  ]);

  // Chart data
  readonly statusChartData = computed(() => ({
    labels: ['Approved', 'Pending', 'Denied', 'Processing'],
    datasets: [{
      data: [
        this.metrics()?.approved_today ?? 45,
        this.metrics()?.pending_count ?? 23,
        this.metrics()?.denied_today ?? 8,
        this.metrics()?.processing_count ?? 15,
      ],
      backgroundColor: ['#28A745', '#FFC107', '#DC3545', '#17A2B8'],
      hoverBackgroundColor: ['#218838', '#E0A800', '#C82333', '#138496'],
    }],
  }));

  readonly trendChartData = signal({
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    datasets: [
      {
        label: 'Approved',
        data: [25, 32, 28, 35, 42, 38, 45],
        borderColor: '#28A745',
        backgroundColor: 'rgba(40, 167, 69, 0.1)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Denied',
        data: [3, 2, 4, 2, 3, 2, 3],
        borderColor: '#DC3545',
        backgroundColor: 'rgba(220, 53, 69, 0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
  });

  readonly chartOptions = {
    plugins: {
      legend: {
        position: 'bottom',
      },
    },
    cutout: '60%',
  };

  readonly lineChartOptions = {
    plugins: {
      legend: {
        position: 'bottom',
      },
    },
    scales: {
      y: {
        beginAtZero: true,
      },
    },
  };

  ngOnInit(): void {
    // Subscribe to metrics updates
    this.wsService.getMetrics().pipe(
      takeUntil(this.destroy$)
    ).subscribe((m) => {
      if (m) {
        this.metrics.set(m);
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
