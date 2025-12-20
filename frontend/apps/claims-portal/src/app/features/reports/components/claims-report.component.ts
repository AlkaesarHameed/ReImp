/**
 * Claims Report Component.
 * Source: Phase 5 Implementation Document
 *
 * Detailed claims status report with configurable parameters,
 * status breakdown, processing time analysis, and export options.
 */
import {
  Component,
  ChangeDetectionStrategy,
  signal,
  computed,
} from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe, DecimalPipe, PercentPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { DropdownModule } from 'primeng/dropdown';
import { CalendarModule } from 'primeng/calendar';
import { ChartModule } from 'primeng/chart';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { MultiSelectModule } from 'primeng/multiselect';
import { ProgressBarModule } from 'primeng/progressbar';
import { DividerModule } from 'primeng/divider';

interface ClaimStatusSummary {
  status: string;
  count: number;
  percentage: number;
  amount: number;
  avgProcessingDays: number;
  color: string;
}

interface DenialReason {
  reason: string;
  code: string;
  count: number;
  percentage: number;
  avgAmount: number;
}

interface ProcessingMetric {
  metric: string;
  current: number;
  previous: number;
  change: number;
  unit: string;
}

interface ClaimDetail {
  claimId: string;
  patientName: string;
  providerId: string;
  serviceDate: Date;
  submittedDate: Date;
  status: string;
  amount: number;
  processingDays: number;
}

@Component({
  selector: 'app-claims-report',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    CardModule,
    ButtonModule,
    DropdownModule,
    CalendarModule,
    ChartModule,
    TableModule,
    TagModule,
    MultiSelectModule,
    ProgressBarModule,
    DividerModule,
    CurrencyPipe,
    DatePipe,
    DecimalPipe,
    PercentPipe,
  ],
  template: `
    <div class="report-container">
      <!-- Header -->
      <div class="report-header">
        <div class="header-left">
          <a routerLink="/reports" class="back-link">
            <i class="pi pi-arrow-left"></i>
            Back to Reports
          </a>
          <h1>
            <i class="pi pi-chart-bar"></i>
            Claims Status Report
          </h1>
          <p>Comprehensive analysis of claims processing and outcomes</p>
        </div>
        <div class="header-actions">
          <button pButton label="Export PDF" icon="pi pi-file-pdf" class="p-button-danger"></button>
          <button pButton label="Export Excel" icon="pi pi-file-excel" class="p-button-success"></button>
          <button pButton label="Print" icon="pi pi-print" class="p-button-outlined"></button>
        </div>
      </div>

      <!-- Filters -->
      <p-card styleClass="filter-card">
        <div class="filter-row">
          <div class="filter-group">
            <label>Date Range</label>
            <p-dropdown
              [options]="dateRangeOptions"
              [(ngModel)]="selectedDateRange"
              optionLabel="label"
              optionValue="value"
              placeholder="Select Range"
            ></p-dropdown>
          </div>
          <div class="filter-group">
            <label>Start Date</label>
            <p-calendar
              [(ngModel)]="startDate"
              [showIcon]="true"
              dateFormat="mm/dd/yy"
            ></p-calendar>
          </div>
          <div class="filter-group">
            <label>End Date</label>
            <p-calendar
              [(ngModel)]="endDate"
              [showIcon]="true"
              dateFormat="mm/dd/yy"
            ></p-calendar>
          </div>
          <div class="filter-group">
            <label>Status</label>
            <p-multiSelect
              [options]="statusOptions"
              [(ngModel)]="selectedStatuses"
              optionLabel="label"
              optionValue="value"
              placeholder="All Statuses"
              display="chip"
            ></p-multiSelect>
          </div>
          <button pButton label="Generate Report" icon="pi pi-refresh" (click)="generateReport()"></button>
        </div>
      </p-card>

      <!-- Summary Cards -->
      <div class="summary-grid">
        <div class="summary-card total">
          <div class="summary-icon">
            <i class="pi pi-file"></i>
          </div>
          <div class="summary-content">
            <span class="summary-value">{{ totalClaims() | number }}</span>
            <span class="summary-label">Total Claims</span>
          </div>
        </div>
        <div class="summary-card approved">
          <div class="summary-icon">
            <i class="pi pi-check-circle"></i>
          </div>
          <div class="summary-content">
            <span class="summary-value">{{ approvalRate() | percent:'1.1-1' }}</span>
            <span class="summary-label">Approval Rate</span>
          </div>
        </div>
        <div class="summary-card amount">
          <div class="summary-icon">
            <i class="pi pi-dollar"></i>
          </div>
          <div class="summary-content">
            <span class="summary-value">{{ totalAmount() | currency:'USD':'symbol':'1.0-0' }}</span>
            <span class="summary-label">Total Amount</span>
          </div>
        </div>
        <div class="summary-card time">
          <div class="summary-icon">
            <i class="pi pi-clock"></i>
          </div>
          <div class="summary-content">
            <span class="summary-value">{{ avgProcessingDays() | number:'1.1-1' }}</span>
            <span class="summary-label">Avg Days to Process</span>
          </div>
        </div>
      </div>

      <!-- Status Breakdown -->
      <div class="charts-section">
        <p-card header="Claims by Status" styleClass="chart-card">
          <div class="chart-container">
            <p-chart type="doughnut" [data]="statusChartData()" [options]="doughnutOptions" height="280"></p-chart>
          </div>
          <p-divider></p-divider>
          <div class="status-legend">
            @for (status of statusSummary(); track status.status) {
              <div class="legend-item">
                <span class="legend-color" [style.background-color]="status.color"></span>
                <span class="legend-label">{{ status.status }}</span>
                <span class="legend-count">{{ status.count | number }}</span>
                <span class="legend-pct">({{ status.percentage | percent:'1.0-0' }})</span>
              </div>
            }
          </div>
        </p-card>

        <p-card header="Claims Trend" styleClass="chart-card">
          <p-chart type="line" [data]="trendChartData()" [options]="lineOptions" height="280"></p-chart>
        </p-card>
      </div>

      <!-- Status Details Table -->
      <p-card header="Status Breakdown Details" styleClass="table-card">
        <p-table
          [value]="statusSummary()"
          styleClass="p-datatable-sm p-datatable-striped"
        >
          <ng-template pTemplate="header">
            <tr>
              <th>Status</th>
              <th style="text-align: right">Count</th>
              <th style="text-align: right">Percentage</th>
              <th style="text-align: right">Total Amount</th>
              <th style="text-align: right">Avg Processing Days</th>
              <th>Distribution</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-item>
            <tr>
              <td>
                <span class="status-badge" [style.background-color]="item.color">
                  {{ item.status }}
                </span>
              </td>
              <td style="text-align: right">{{ item.count | number }}</td>
              <td style="text-align: right">{{ item.percentage | percent:'1.1-1' }}</td>
              <td style="text-align: right">{{ item.amount | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right">{{ item.avgProcessingDays | number:'1.1-1' }} days</td>
              <td style="width: 150px">
                <p-progressBar
                  [value]="item.percentage * 100"
                  [showValue]="false"
                  [style]="{ height: '8px' }"
                ></p-progressBar>
              </td>
            </tr>
          </ng-template>
          <ng-template pTemplate="footer">
            <tr class="font-bold">
              <td>Total</td>
              <td style="text-align: right">{{ totalClaims() | number }}</td>
              <td style="text-align: right">100%</td>
              <td style="text-align: right">{{ totalAmount() | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right">{{ avgProcessingDays() | number:'1.1-1' }} days</td>
              <td></td>
            </tr>
          </ng-template>
        </p-table>
      </p-card>

      <!-- Denial Analysis -->
      <p-card header="Denial Analysis" styleClass="table-card">
        <p-table
          [value]="denialReasons()"
          styleClass="p-datatable-sm p-datatable-striped"
          [rows]="5"
        >
          <ng-template pTemplate="header">
            <tr>
              <th>Denial Code</th>
              <th>Reason</th>
              <th style="text-align: right">Count</th>
              <th style="text-align: right">% of Denials</th>
              <th style="text-align: right">Avg Claim Amount</th>
              <th>Distribution</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-item>
            <tr>
              <td>
                <p-tag [value]="item.code" severity="danger"></p-tag>
              </td>
              <td>{{ item.reason }}</td>
              <td style="text-align: right">{{ item.count | number }}</td>
              <td style="text-align: right">{{ item.percentage | percent:'1.1-1' }}</td>
              <td style="text-align: right">{{ item.avgAmount | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="width: 150px">
                <p-progressBar
                  [value]="item.percentage * 100"
                  [showValue]="false"
                  [style]="{ height: '8px' }"
                  styleClass="denial-bar"
                ></p-progressBar>
              </td>
            </tr>
          </ng-template>
        </p-table>
      </p-card>

      <!-- Processing Metrics -->
      <p-card header="Processing Performance Metrics" styleClass="metrics-card">
        <div class="metrics-grid">
          @for (metric of processingMetrics(); track metric.metric) {
            <div class="metric-item">
              <div class="metric-label">{{ metric.metric }}</div>
              <div class="metric-values">
                <span class="metric-current">{{ metric.current }}{{ metric.unit }}</span>
                <span class="metric-change" [class.positive]="metric.change > 0" [class.negative]="metric.change < 0">
                  @if (metric.change > 0) {
                    <i class="pi pi-arrow-up"></i>
                  } @else if (metric.change < 0) {
                    <i class="pi pi-arrow-down"></i>
                  }
                  {{ metric.change > 0 ? '+' : '' }}{{ metric.change }}{{ metric.unit }}
                </span>
              </div>
              <div class="metric-previous">
                Previous: {{ metric.previous }}{{ metric.unit }}
              </div>
            </div>
          }
        </div>
      </p-card>

      <!-- Detailed Claims Table -->
      <p-card header="Claim Details" styleClass="table-card">
        <p-table
          [value]="claimDetails()"
          [paginator]="true"
          [rows]="10"
          [rowsPerPageOptions]="[10, 25, 50]"
          styleClass="p-datatable-sm p-datatable-gridlines"
          [sortField]="'submittedDate'"
          [sortOrder]="-1"
        >
          <ng-template pTemplate="header">
            <tr>
              <th pSortableColumn="claimId">Claim ID <p-sortIcon field="claimId"></p-sortIcon></th>
              <th pSortableColumn="patientName">Patient <p-sortIcon field="patientName"></p-sortIcon></th>
              <th>Provider ID</th>
              <th pSortableColumn="serviceDate">Service Date <p-sortIcon field="serviceDate"></p-sortIcon></th>
              <th pSortableColumn="submittedDate">Submitted <p-sortIcon field="submittedDate"></p-sortIcon></th>
              <th>Status</th>
              <th pSortableColumn="amount" style="text-align: right">Amount <p-sortIcon field="amount"></p-sortIcon></th>
              <th pSortableColumn="processingDays" style="text-align: right">Days <p-sortIcon field="processingDays"></p-sortIcon></th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-claim>
            <tr>
              <td>
                <a [routerLink]="['/claims', claim.claimId]" class="claim-link">
                  {{ claim.claimId }}
                </a>
              </td>
              <td>{{ claim.patientName }}</td>
              <td>{{ claim.providerId }}</td>
              <td>{{ claim.serviceDate | date:'shortDate' }}</td>
              <td>{{ claim.submittedDate | date:'shortDate' }}</td>
              <td>
                <p-tag
                  [value]="claim.status"
                  [severity]="getStatusSeverity(claim.status)"
                ></p-tag>
              </td>
              <td style="text-align: right">{{ claim.amount | currency:'USD':'symbol':'1.2-2' }}</td>
              <td style="text-align: right">{{ claim.processingDays }}</td>
            </tr>
          </ng-template>
        </p-table>
      </p-card>

      <!-- Report Footer -->
      <div class="report-footer">
        <div class="footer-info">
          <span>Report generated on {{ generatedDate | date:'medium' }}</span>
          <span>Data period: {{ startDate | date:'shortDate' }} - {{ endDate | date:'shortDate' }}</span>
        </div>
        <div class="footer-disclaimer">
          This report contains Protected Health Information (PHI) and is intended only for authorized personnel.
          Distribution or disclosure is prohibited without proper authorization.
        </div>
      </div>
    </div>
  `,
  styles: [`
    .report-container {
      padding: 1.5rem;
      background: #F8F9FA;
      min-height: 100vh;
    }

    .report-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1.5rem;
    }

    .back-link {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      color: #6366F1;
      text-decoration: none;
      font-size: 0.9rem;
      margin-bottom: 0.75rem;
    }

    .back-link:hover {
      text-decoration: underline;
    }

    .report-header h1 {
      margin: 0;
      font-size: 1.75rem;
      color: #1F2937;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .report-header p {
      margin: 0.5rem 0 0;
      color: #6B7280;
    }

    .header-actions {
      display: flex;
      gap: 0.5rem;
    }

    :host ::ng-deep .filter-card .p-card-body {
      padding: 1rem 1.5rem;
    }

    .filter-row {
      display: flex;
      align-items: flex-end;
      gap: 1.5rem;
      flex-wrap: wrap;
    }

    .filter-group {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .filter-group label {
      font-size: 0.85rem;
      font-weight: 500;
      color: #374151;
    }

    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
      margin: 1.5rem 0;
    }

    .summary-card {
      background: white;
      border-radius: 10px;
      padding: 1.5rem;
      display: flex;
      align-items: center;
      gap: 1rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      border-left: 4px solid #6366F1;
    }

    .summary-card.total { border-left-color: #6366F1; }
    .summary-card.approved { border-left-color: #10B981; }
    .summary-card.amount { border-left-color: #F59E0B; }
    .summary-card.time { border-left-color: #3B82F6; }

    .summary-icon {
      width: 56px;
      height: 56px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #EEF2FF;
      color: #6366F1;
    }

    .summary-card.total .summary-icon { background: #EEF2FF; color: #6366F1; }
    .summary-card.approved .summary-icon { background: #D1FAE5; color: #10B981; }
    .summary-card.amount .summary-icon { background: #FEF3C7; color: #F59E0B; }
    .summary-card.time .summary-icon { background: #DBEAFE; color: #3B82F6; }

    .summary-icon i { font-size: 1.5rem; }

    .summary-content {
      display: flex;
      flex-direction: column;
    }

    .summary-value {
      font-size: 1.75rem;
      font-weight: 700;
      color: #1F2937;
    }

    .summary-label {
      font-size: 0.9rem;
      color: #6B7280;
    }

    .charts-section {
      display: grid;
      grid-template-columns: 1fr 1.5fr;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    :host ::ng-deep .chart-card {
      height: 100%;
    }

    .chart-container {
      display: flex;
      justify-content: center;
    }

    .status-legend {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      padding-top: 0.5rem;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-size: 0.9rem;
    }

    .legend-color {
      width: 12px;
      height: 12px;
      border-radius: 3px;
    }

    .legend-label {
      flex: 1;
      color: #374151;
    }

    .legend-count {
      font-weight: 600;
      color: #1F2937;
    }

    .legend-pct {
      color: #6B7280;
      font-size: 0.85rem;
    }

    .status-badge {
      padding: 0.25rem 0.75rem;
      border-radius: 12px;
      color: white;
      font-size: 0.85rem;
      font-weight: 500;
    }

    :host ::ng-deep .table-card {
      margin-bottom: 1.5rem;
    }

    :host ::ng-deep .denial-bar .p-progressbar-value {
      background: #EF4444;
    }

    :host ::ng-deep .metrics-card .p-card-body {
      padding: 1rem 1.5rem;
    }

    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.5rem;
    }

    .metric-item {
      padding: 1rem;
      background: #F9FAFB;
      border-radius: 8px;
    }

    .metric-label {
      font-size: 0.85rem;
      color: #6B7280;
      margin-bottom: 0.5rem;
    }

    .metric-values {
      display: flex;
      align-items: baseline;
      gap: 0.75rem;
    }

    .metric-current {
      font-size: 1.5rem;
      font-weight: 700;
      color: #1F2937;
    }

    .metric-change {
      font-size: 0.9rem;
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }

    .metric-change.positive { color: #10B981; }
    .metric-change.negative { color: #EF4444; }

    .metric-previous {
      font-size: 0.8rem;
      color: #9CA3AF;
      margin-top: 0.25rem;
    }

    .claim-link {
      color: #6366F1;
      text-decoration: none;
      font-weight: 500;
    }

    .claim-link:hover {
      text-decoration: underline;
    }

    .report-footer {
      margin-top: 2rem;
      padding: 1.5rem;
      background: white;
      border-radius: 10px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }

    .footer-info {
      display: flex;
      justify-content: space-between;
      color: #6B7280;
      font-size: 0.9rem;
      margin-bottom: 1rem;
    }

    .footer-disclaimer {
      font-size: 0.8rem;
      color: #9CA3AF;
      padding: 0.75rem;
      background: #FEF3C7;
      border-radius: 6px;
      border: 1px solid #FCD34D;
    }

    @media (max-width: 1200px) {
      .charts-section {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 768px) {
      .report-header {
        flex-direction: column;
        gap: 1rem;
      }

      .header-actions {
        width: 100%;
        flex-wrap: wrap;
      }

      .filter-row {
        flex-direction: column;
        align-items: stretch;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClaimsReportComponent {
  // Filter state
  selectedDateRange = 'last30';
  startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
  endDate = new Date();
  selectedStatuses: string[] = [];
  generatedDate = new Date();

  dateRangeOptions = [
    { label: 'Last 7 Days', value: 'last7' },
    { label: 'Last 30 Days', value: 'last30' },
    { label: 'Last Quarter', value: 'lastQuarter' },
    { label: 'Year to Date', value: 'ytd' },
    { label: 'Custom Range', value: 'custom' },
  ];

  statusOptions = [
    { label: 'Approved', value: 'approved' },
    { label: 'Denied', value: 'denied' },
    { label: 'Pending', value: 'pending' },
    { label: 'Processing', value: 'processing' },
    { label: 'Needs Review', value: 'needs_review' },
  ];

  // Computed metrics
  readonly totalClaims = signal(2847);
  readonly approvalRate = signal(0.873);
  readonly totalAmount = signal(1245780);
  readonly avgProcessingDays = signal(2.3);

  readonly statusSummary = signal<ClaimStatusSummary[]>([
    { status: 'Approved', count: 2485, percentage: 0.873, amount: 1087340, avgProcessingDays: 1.8, color: '#10B981' },
    { status: 'Denied', count: 198, percentage: 0.070, amount: 89450, avgProcessingDays: 3.2, color: '#EF4444' },
    { status: 'Pending', count: 89, percentage: 0.031, amount: 42560, avgProcessingDays: 4.5, color: '#F59E0B' },
    { status: 'Processing', count: 52, percentage: 0.018, amount: 18920, avgProcessingDays: 0.5, color: '#3B82F6' },
    { status: 'Needs Review', count: 23, percentage: 0.008, amount: 7510, avgProcessingDays: 5.1, color: '#8B5CF6' },
  ]);

  readonly denialReasons = signal<DenialReason[]>([
    { reason: 'Service not covered under plan', code: 'CO-50', count: 45, percentage: 0.227, avgAmount: 456 },
    { reason: 'Pre-authorization required', code: 'CO-197', count: 38, percentage: 0.192, avgAmount: 892 },
    { reason: 'Duplicate claim submission', code: 'CO-18', count: 32, percentage: 0.162, avgAmount: 234 },
    { reason: 'Member not eligible on service date', code: 'CO-27', count: 28, percentage: 0.141, avgAmount: 567 },
    { reason: 'Exceeds benefit maximum', code: 'CO-119', count: 25, percentage: 0.126, avgAmount: 1250 },
    { reason: 'Invalid procedure code', code: 'CO-4', count: 18, percentage: 0.091, avgAmount: 345 },
    { reason: 'Other reasons', code: 'CO-XX', count: 12, percentage: 0.061, avgAmount: 412 },
  ]);

  readonly processingMetrics = signal<ProcessingMetric[]>([
    { metric: 'Average Processing Time', current: 2.3, previous: 2.8, change: -0.5, unit: ' days' },
    { metric: 'First Pass Approval Rate', current: 84, previous: 81, change: 3, unit: '%' },
    { metric: 'Claims Per Hour', current: 45, previous: 42, change: 3, unit: '' },
    { metric: 'Auto-Adjudication Rate', current: 67, previous: 62, change: 5, unit: '%' },
    { metric: 'Appeal Success Rate', current: 42, previous: 38, change: 4, unit: '%' },
    { metric: 'Error Rate', current: 2.1, previous: 2.8, change: -0.7, unit: '%' },
  ]);

  readonly claimDetails = signal<ClaimDetail[]>([
    { claimId: 'CLM-2024-001234', patientName: 'John Smith', providerId: 'PRV-001', serviceDate: new Date('2024-12-15'), submittedDate: new Date('2024-12-16'), status: 'Approved', amount: 450.00, processingDays: 1 },
    { claimId: 'CLM-2024-001233', patientName: 'Sarah Johnson', providerId: 'PRV-002', serviceDate: new Date('2024-12-14'), submittedDate: new Date('2024-12-15'), status: 'Approved', amount: 1250.00, processingDays: 2 },
    { claimId: 'CLM-2024-001232', patientName: 'Michael Brown', providerId: 'PRV-001', serviceDate: new Date('2024-12-13'), submittedDate: new Date('2024-12-14'), status: 'Denied', amount: 890.00, processingDays: 3 },
    { claimId: 'CLM-2024-001231', patientName: 'Emily Davis', providerId: 'PRV-003', serviceDate: new Date('2024-12-12'), submittedDate: new Date('2024-12-13'), status: 'Pending', amount: 320.00, processingDays: 4 },
    { claimId: 'CLM-2024-001230', patientName: 'Robert Wilson', providerId: 'PRV-002', serviceDate: new Date('2024-12-11'), submittedDate: new Date('2024-12-12'), status: 'Approved', amount: 567.50, processingDays: 2 },
    { claimId: 'CLM-2024-001229', patientName: 'Jennifer Taylor', providerId: 'PRV-004', serviceDate: new Date('2024-12-10'), submittedDate: new Date('2024-12-11'), status: 'Processing', amount: 2100.00, processingDays: 1 },
    { claimId: 'CLM-2024-001228', patientName: 'David Martinez', providerId: 'PRV-001', serviceDate: new Date('2024-12-09'), submittedDate: new Date('2024-12-10'), status: 'Needs Review', amount: 445.00, processingDays: 5 },
    { claimId: 'CLM-2024-001227', patientName: 'Lisa Anderson', providerId: 'PRV-005', serviceDate: new Date('2024-12-08'), submittedDate: new Date('2024-12-09'), status: 'Approved', amount: 780.00, processingDays: 1 },
  ]);

  // Chart data
  readonly statusChartData = computed(() => ({
    labels: this.statusSummary().map(s => s.status),
    datasets: [{
      data: this.statusSummary().map(s => s.count),
      backgroundColor: this.statusSummary().map(s => s.color),
      hoverBackgroundColor: this.statusSummary().map(s => s.color),
    }],
  }));

  readonly trendChartData = signal({
    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
    datasets: [
      {
        label: 'Approved',
        data: [580, 620, 615, 670],
        borderColor: '#10B981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Denied',
        data: [42, 48, 51, 57],
        borderColor: '#EF4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Pending',
        data: [25, 22, 28, 14],
        borderColor: '#F59E0B',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
  });

  readonly doughnutOptions = {
    plugins: {
      legend: {
        display: false,
      },
    },
    cutout: '65%',
  };

  readonly lineOptions = {
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

  getStatusSeverity(status: string): 'success' | 'danger' | 'warning' | 'info' | 'secondary' {
    const severities: Record<string, 'success' | 'danger' | 'warning' | 'info' | 'secondary'> = {
      'Approved': 'success',
      'Denied': 'danger',
      'Pending': 'warning',
      'Processing': 'info',
      'Needs Review': 'secondary',
    };
    return severities[status] || 'info';
  }

  generateReport(): void {
    this.generatedDate = new Date();
    // In production, this would call an API to generate the report
    console.log('Generating report with filters:', {
      dateRange: this.selectedDateRange,
      startDate: this.startDate,
      endDate: this.endDate,
      statuses: this.selectedStatuses,
    });
  }
}
