/**
 * Financial Report Component.
 * Source: Phase 5 Implementation Document
 *
 * Financial summary and analysis report with billed vs paid amounts,
 * reimbursement rates, outstanding claims value, and chart visualizations.
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
import { DividerModule } from 'primeng/divider';
import { ProgressBarModule } from 'primeng/progressbar';

interface FinancialSummary {
  label: string;
  value: number;
  previousValue: number;
  change: number;
  icon: string;
  colorClass: string;
}

interface PayerBreakdown {
  payer: string;
  billedAmount: number;
  paidAmount: number;
  adjustments: number;
  writeOffs: number;
  outstandingBalance: number;
  reimbursementRate: number;
}

interface AgingBucket {
  bucket: string;
  claimCount: number;
  totalAmount: number;
  percentage: number;
  color: string;
}

interface MonthlyTrend {
  month: string;
  billed: number;
  paid: number;
  adjustments: number;
  netRevenue: number;
}

interface TopProvider {
  providerId: string;
  providerName: string;
  specialty: string;
  claimCount: number;
  totalBilled: number;
  totalPaid: number;
  avgReimbursement: number;
}

@Component({
  selector: 'app-financial-report',
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
    DividerModule,
    ProgressBarModule,
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
            <i class="pi pi-dollar"></i>
            Financial Summary Report
          </h1>
          <p>Comprehensive financial analysis and revenue metrics</p>
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
            <label>Reporting Period</label>
            <p-dropdown
              [options]="periodOptions"
              [(ngModel)]="selectedPeriod"
              optionLabel="label"
              optionValue="value"
              placeholder="Select Period"
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
            <label>Payer</label>
            <p-dropdown
              [options]="payerOptions"
              [(ngModel)]="selectedPayer"
              optionLabel="label"
              optionValue="value"
              placeholder="All Payers"
            ></p-dropdown>
          </div>
          <button pButton label="Generate Report" icon="pi pi-refresh" (click)="generateReport()"></button>
        </div>
      </p-card>

      <!-- Financial Summary Cards -->
      <div class="summary-grid">
        @for (summary of financialSummary(); track summary.label) {
          <div class="summary-card" [class]="summary.colorClass">
            <div class="summary-icon">
              <i [class]="'pi ' + summary.icon"></i>
            </div>
            <div class="summary-content">
              <span class="summary-label">{{ summary.label }}</span>
              <span class="summary-value">{{ summary.value | currency:'USD':'symbol':'1.0-0' }}</span>
              <div class="summary-change" [class.positive]="summary.change > 0" [class.negative]="summary.change < 0">
                @if (summary.change > 0) {
                  <i class="pi pi-arrow-up"></i>
                } @else if (summary.change < 0) {
                  <i class="pi pi-arrow-down"></i>
                }
                {{ summary.change > 0 ? '+' : '' }}{{ summary.change | percent:'1.1-1' }}
                <span class="vs-previous">vs previous period</span>
              </div>
            </div>
          </div>
        }
      </div>

      <!-- Key Metrics Row -->
      <div class="metrics-row">
        <div class="metric-card">
          <span class="metric-label">Net Collection Rate</span>
          <span class="metric-value">{{ netCollectionRate() | percent:'1.1-1' }}</span>
          <p-progressBar [value]="netCollectionRate() * 100" [showValue]="false"></p-progressBar>
        </div>
        <div class="metric-card">
          <span class="metric-label">Days in A/R</span>
          <span class="metric-value">{{ daysInAR() }}</span>
          <span class="metric-target">Target: &lt; 35 days</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Clean Claim Rate</span>
          <span class="metric-value">{{ cleanClaimRate() | percent:'1.1-1' }}</span>
          <p-progressBar [value]="cleanClaimRate() * 100" [showValue]="false" styleClass="success-bar"></p-progressBar>
        </div>
        <div class="metric-card">
          <span class="metric-label">Denial Rate</span>
          <span class="metric-value">{{ denialRate() | percent:'1.1-1' }}</span>
          <span class="metric-target">Target: &lt; 5%</span>
        </div>
      </div>

      <!-- Charts Row -->
      <div class="charts-section">
        <p-card header="Revenue Trend" styleClass="chart-card">
          <p-chart type="bar" [data]="revenueTrendData()" [options]="barChartOptions" height="300"></p-chart>
        </p-card>

        <p-card header="Payment Distribution" styleClass="chart-card">
          <p-chart type="doughnut" [data]="paymentDistributionData()" [options]="doughnutOptions" height="300"></p-chart>
        </p-card>
      </div>

      <!-- Payer Breakdown Table -->
      <p-card header="Payer Analysis" styleClass="table-card">
        <p-table
          [value]="payerBreakdown()"
          styleClass="p-datatable-sm p-datatable-striped"
          [sortField]="'billedAmount'"
          [sortOrder]="-1"
        >
          <ng-template pTemplate="header">
            <tr>
              <th pSortableColumn="payer">Payer <p-sortIcon field="payer"></p-sortIcon></th>
              <th pSortableColumn="billedAmount" style="text-align: right">Billed <p-sortIcon field="billedAmount"></p-sortIcon></th>
              <th pSortableColumn="paidAmount" style="text-align: right">Paid <p-sortIcon field="paidAmount"></p-sortIcon></th>
              <th style="text-align: right">Adjustments</th>
              <th style="text-align: right">Write-offs</th>
              <th pSortableColumn="outstandingBalance" style="text-align: right">Outstanding <p-sortIcon field="outstandingBalance"></p-sortIcon></th>
              <th pSortableColumn="reimbursementRate" style="text-align: right">Reimb. Rate <p-sortIcon field="reimbursementRate"></p-sortIcon></th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-payer>
            <tr>
              <td>
                <div class="payer-name">
                  <i class="pi pi-building"></i>
                  {{ payer.payer }}
                </div>
              </td>
              <td style="text-align: right">{{ payer.billedAmount | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right">{{ payer.paidAmount | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right; color: #6B7280">{{ payer.adjustments | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right; color: #EF4444">{{ payer.writeOffs | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right">
                <span [class.outstanding-high]="payer.outstandingBalance > 50000">
                  {{ payer.outstandingBalance | currency:'USD':'symbol':'1.0-0' }}
                </span>
              </td>
              <td style="text-align: right">
                <p-tag
                  [value]="(payer.reimbursementRate | percent:'1.0-0') || '0%'"
                  [severity]="getReimbursementSeverity(payer.reimbursementRate)"
                ></p-tag>
              </td>
            </tr>
          </ng-template>
          <ng-template pTemplate="footer">
            <tr class="font-bold">
              <td>Total</td>
              <td style="text-align: right">{{ getTotalBilled() | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right">{{ getTotalPaid() | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right">{{ getTotalAdjustments() | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right">{{ getTotalWriteOffs() | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right">{{ getTotalOutstanding() | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right">{{ getAvgReimbursementRate() | percent:'1.0-0' }}</td>
            </tr>
          </ng-template>
        </p-table>
      </p-card>

      <!-- A/R Aging -->
      <p-card header="Accounts Receivable Aging" styleClass="aging-card">
        <div class="aging-grid">
          @for (bucket of agingBuckets(); track bucket.bucket) {
            <div class="aging-bucket" [style.border-left-color]="bucket.color">
              <div class="aging-header">
                <span class="aging-label">{{ bucket.bucket }}</span>
                <span class="aging-percentage">{{ bucket.percentage | percent:'1.0-0' }}</span>
              </div>
              <div class="aging-amount">{{ bucket.totalAmount | currency:'USD':'symbol':'1.0-0' }}</div>
              <div class="aging-claims">{{ bucket.claimCount | number }} claims</div>
              <p-progressBar
                [value]="bucket.percentage * 100"
                [showValue]="false"
                [style]="{ height: '6px' }"
              ></p-progressBar>
            </div>
          }
        </div>
        <p-divider></p-divider>
        <div class="aging-chart-container">
          <p-chart type="bar" [data]="agingChartData()" [options]="agingChartOptions" height="200"></p-chart>
        </div>
      </p-card>

      <!-- Top Providers -->
      <p-card header="Top Providers by Revenue" styleClass="table-card">
        <p-table
          [value]="topProviders()"
          styleClass="p-datatable-sm p-datatable-striped"
          [rows]="5"
        >
          <ng-template pTemplate="header">
            <tr>
              <th>Provider</th>
              <th>Specialty</th>
              <th style="text-align: right">Claims</th>
              <th style="text-align: right">Total Billed</th>
              <th style="text-align: right">Total Paid</th>
              <th style="text-align: right">Avg Reimbursement</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-provider>
            <tr>
              <td>
                <div class="provider-info">
                  <span class="provider-name">{{ provider.providerName }}</span>
                  <span class="provider-id">{{ provider.providerId }}</span>
                </div>
              </td>
              <td>{{ provider.specialty }}</td>
              <td style="text-align: right">{{ provider.claimCount | number }}</td>
              <td style="text-align: right">{{ provider.totalBilled | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right">{{ provider.totalPaid | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right">{{ provider.avgReimbursement | percent:'1.1-1' }}</td>
            </tr>
          </ng-template>
        </p-table>
      </p-card>

      <!-- Monthly Trend Table -->
      <p-card header="Monthly Financial Trend" styleClass="table-card">
        <p-table
          [value]="monthlyTrend()"
          styleClass="p-datatable-sm p-datatable-striped"
        >
          <ng-template pTemplate="header">
            <tr>
              <th>Month</th>
              <th style="text-align: right">Billed</th>
              <th style="text-align: right">Paid</th>
              <th style="text-align: right">Adjustments</th>
              <th style="text-align: right">Net Revenue</th>
              <th>Collection Trend</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-month>
            <tr>
              <td>{{ month.month }}</td>
              <td style="text-align: right">{{ month.billed | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right">{{ month.paid | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right; color: #6B7280">{{ month.adjustments | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="text-align: right; font-weight: 600">{{ month.netRevenue | currency:'USD':'symbol':'1.0-0' }}</td>
              <td style="width: 150px">
                <p-progressBar
                  [value]="(month.paid / month.billed) * 100"
                  [showValue]="false"
                  [style]="{ height: '8px' }"
                ></p-progressBar>
              </td>
            </tr>
          </ng-template>
        </p-table>
      </p-card>

      <!-- Report Footer -->
      <div class="report-footer">
        <div class="footer-info">
          <span>Report generated on {{ generatedDate | date:'medium' }}</span>
          <span>Fiscal Period: {{ startDate | date:'shortDate' }} - {{ endDate | date:'shortDate' }}</span>
        </div>
        <div class="footer-disclaimer">
          This financial report is for internal use only. All figures are subject to final reconciliation
          and may be adjusted during the audit process.
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
      color: #10B981;
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
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 1rem;
      margin: 1.5rem 0;
    }

    .summary-card {
      background: white;
      border-radius: 12px;
      padding: 1.5rem;
      display: flex;
      align-items: flex-start;
      gap: 1rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      border-top: 4px solid #10B981;
    }

    .summary-card.billed { border-top-color: #3B82F6; }
    .summary-card.paid { border-top-color: #10B981; }
    .summary-card.adjustments { border-top-color: #F59E0B; }
    .summary-card.outstanding { border-top-color: #EF4444; }

    .summary-icon {
      width: 48px;
      height: 48px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #D1FAE5;
      color: #10B981;
      flex-shrink: 0;
    }

    .summary-card.billed .summary-icon { background: #DBEAFE; color: #3B82F6; }
    .summary-card.paid .summary-icon { background: #D1FAE5; color: #10B981; }
    .summary-card.adjustments .summary-icon { background: #FEF3C7; color: #F59E0B; }
    .summary-card.outstanding .summary-icon { background: #FEE2E2; color: #EF4444; }

    .summary-icon i { font-size: 1.25rem; }

    .summary-content {
      flex: 1;
    }

    .summary-label {
      font-size: 0.85rem;
      color: #6B7280;
      display: block;
    }

    .summary-value {
      font-size: 1.75rem;
      font-weight: 700;
      color: #1F2937;
      display: block;
      margin: 0.25rem 0;
    }

    .summary-change {
      font-size: 0.85rem;
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }

    .summary-change.positive { color: #10B981; }
    .summary-change.negative { color: #EF4444; }

    .vs-previous {
      color: #9CA3AF;
      margin-left: 0.25rem;
    }

    .metrics-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    .metric-card {
      background: white;
      border-radius: 10px;
      padding: 1.25rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }

    .metric-label {
      font-size: 0.85rem;
      color: #6B7280;
      display: block;
    }

    .metric-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: #1F2937;
      display: block;
      margin: 0.5rem 0;
    }

    .metric-target {
      font-size: 0.8rem;
      color: #9CA3AF;
    }

    :host ::ng-deep .success-bar .p-progressbar-value {
      background: #10B981;
    }

    .charts-section {
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    :host ::ng-deep .chart-card,
    :host ::ng-deep .table-card,
    :host ::ng-deep .aging-card {
      margin-bottom: 1.5rem;
    }

    .payer-name {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .payer-name i { color: #6B7280; }

    .outstanding-high {
      color: #EF4444;
      font-weight: 600;
    }

    .aging-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
    }

    .aging-bucket {
      padding: 1rem;
      background: #F9FAFB;
      border-radius: 8px;
      border-left: 4px solid #10B981;
    }

    .aging-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.5rem;
    }

    .aging-label {
      font-size: 0.9rem;
      font-weight: 500;
      color: #374151;
    }

    .aging-percentage {
      font-size: 0.85rem;
      color: #6B7280;
    }

    .aging-amount {
      font-size: 1.25rem;
      font-weight: 700;
      color: #1F2937;
    }

    .aging-claims {
      font-size: 0.8rem;
      color: #9CA3AF;
      margin-bottom: 0.5rem;
    }

    .aging-chart-container {
      margin-top: 1rem;
    }

    .provider-info {
      display: flex;
      flex-direction: column;
    }

    .provider-name {
      font-weight: 500;
      color: #1F2937;
    }

    .provider-id {
      font-size: 0.8rem;
      color: #9CA3AF;
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
      color: #6B7280;
      padding: 0.75rem;
      background: #F3F4F6;
      border-radius: 6px;
      border: 1px solid #E5E7EB;
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
export class FinancialReportComponent {
  // Filter state
  selectedPeriod = 'last30';
  startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
  endDate = new Date();
  selectedPayer = '';
  generatedDate = new Date();

  periodOptions = [
    { label: 'Last 30 Days', value: 'last30' },
    { label: 'Last Quarter', value: 'lastQuarter' },
    { label: 'Year to Date', value: 'ytd' },
    { label: 'Custom Range', value: 'custom' },
  ];

  payerOptions = [
    { label: 'All Payers', value: '' },
    { label: 'Blue Cross Blue Shield', value: 'bcbs' },
    { label: 'Aetna', value: 'aetna' },
    { label: 'UnitedHealthcare', value: 'uhc' },
    { label: 'Cigna', value: 'cigna' },
    { label: 'Medicare', value: 'medicare' },
    { label: 'Medicaid', value: 'medicaid' },
  ];

  // Key metrics
  readonly netCollectionRate = signal(0.892);
  readonly daysInAR = signal(32);
  readonly cleanClaimRate = signal(0.943);
  readonly denialRate = signal(0.068);

  readonly financialSummary = signal<FinancialSummary[]>([
    { label: 'Total Billed', value: 1456780, previousValue: 1324560, change: 0.099, icon: 'pi-file', colorClass: 'billed' },
    { label: 'Total Paid', value: 1245890, previousValue: 1156780, change: 0.077, icon: 'pi-check-circle', colorClass: 'paid' },
    { label: 'Adjustments', value: 125670, previousValue: 118900, change: 0.057, icon: 'pi-percentage', colorClass: 'adjustments' },
    { label: 'Outstanding', value: 85220, previousValue: 78450, change: 0.086, icon: 'pi-clock', colorClass: 'outstanding' },
  ]);

  readonly payerBreakdown = signal<PayerBreakdown[]>([
    { payer: 'Blue Cross Blue Shield', billedAmount: 425000, paidAmount: 382500, adjustments: 25000, writeOffs: 5000, outstandingBalance: 12500, reimbursementRate: 0.90 },
    { payer: 'UnitedHealthcare', billedAmount: 356000, paidAmount: 302600, adjustments: 32000, writeOffs: 8000, outstandingBalance: 13400, reimbursementRate: 0.85 },
    { payer: 'Aetna', billedAmount: 289000, paidAmount: 254320, adjustments: 20000, writeOffs: 4000, outstandingBalance: 10680, reimbursementRate: 0.88 },
    { payer: 'Cigna', billedAmount: 198000, paidAmount: 166320, adjustments: 18000, writeOffs: 6000, outstandingBalance: 7680, reimbursementRate: 0.84 },
    { payer: 'Medicare', billedAmount: 156780, paidAmount: 125424, adjustments: 25000, writeOffs: 2000, outstandingBalance: 4356, reimbursementRate: 0.80 },
    { payer: 'Medicaid', billedAmount: 32000, paidAmount: 22400, adjustments: 5670, writeOffs: 1500, outstandingBalance: 2430, reimbursementRate: 0.70 },
  ]);

  readonly agingBuckets = signal<AgingBucket[]>([
    { bucket: 'Current (0-30)', claimCount: 234, totalAmount: 45670, percentage: 0.536, color: '#10B981' },
    { bucket: '31-60 Days', claimCount: 89, totalAmount: 18450, percentage: 0.217, color: '#F59E0B' },
    { bucket: '61-90 Days', claimCount: 45, totalAmount: 12340, percentage: 0.145, color: '#F97316' },
    { bucket: '90+ Days', claimCount: 23, totalAmount: 8760, percentage: 0.102, color: '#EF4444' },
  ]);

  readonly topProviders = signal<TopProvider[]>([
    { providerId: 'PRV-001', providerName: 'Dr. Smith Medical Group', specialty: 'Internal Medicine', claimCount: 456, totalBilled: 234500, totalPaid: 205160, avgReimbursement: 0.875 },
    { providerId: 'PRV-002', providerName: 'City Orthopedics', specialty: 'Orthopedics', claimCount: 298, totalBilled: 198700, totalPaid: 178830, avgReimbursement: 0.90 },
    { providerId: 'PRV-003', providerName: 'Family Care Associates', specialty: 'Family Medicine', claimCount: 512, totalBilled: 156890, totalPaid: 134930, avgReimbursement: 0.86 },
    { providerId: 'PRV-004', providerName: 'Cardiology Partners', specialty: 'Cardiology', claimCount: 187, totalBilled: 145670, totalPaid: 130856, avgReimbursement: 0.898 },
    { providerId: 'PRV-005', providerName: 'Regional Imaging Center', specialty: 'Radiology', claimCount: 423, totalBilled: 134560, totalPaid: 114576, avgReimbursement: 0.851 },
  ]);

  readonly monthlyTrend = signal<MonthlyTrend[]>([
    { month: 'September 2024', billed: 320000, paid: 275000, adjustments: 28000, netRevenue: 247000 },
    { month: 'October 2024', billed: 345000, paid: 298000, adjustments: 30000, netRevenue: 268000 },
    { month: 'November 2024', billed: 368000, paid: 315000, adjustments: 32000, netRevenue: 283000 },
    { month: 'December 2024', billed: 423780, paid: 357890, adjustments: 35670, netRevenue: 322220 },
  ]);

  // Chart data
  readonly revenueTrendData = computed(() => ({
    labels: this.monthlyTrend().map(m => m.month.split(' ')[0]),
    datasets: [
      {
        label: 'Billed',
        data: this.monthlyTrend().map(m => m.billed),
        backgroundColor: '#3B82F6',
      },
      {
        label: 'Paid',
        data: this.monthlyTrend().map(m => m.paid),
        backgroundColor: '#10B981',
      },
      {
        label: 'Adjustments',
        data: this.monthlyTrend().map(m => m.adjustments),
        backgroundColor: '#F59E0B',
      },
    ],
  }));

  readonly paymentDistributionData = computed(() => ({
    labels: this.payerBreakdown().map(p => p.payer),
    datasets: [{
      data: this.payerBreakdown().map(p => p.paidAmount),
      backgroundColor: ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'],
    }],
  }));

  readonly agingChartData = computed(() => ({
    labels: this.agingBuckets().map(b => b.bucket),
    datasets: [{
      label: 'Outstanding Amount',
      data: this.agingBuckets().map(b => b.totalAmount),
      backgroundColor: this.agingBuckets().map(b => b.color),
    }],
  }));

  readonly barChartOptions = {
    plugins: {
      legend: {
        position: 'bottom',
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: (value: number) => '$' + (value / 1000).toFixed(0) + 'K',
        },
      },
    },
  };

  readonly doughnutOptions = {
    plugins: {
      legend: {
        position: 'right',
      },
    },
    cutout: '55%',
  };

  readonly agingChartOptions = {
    indexAxis: 'y',
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      x: {
        beginAtZero: true,
        ticks: {
          callback: (value: number) => '$' + (value / 1000).toFixed(0) + 'K',
        },
      },
    },
  };

  getReimbursementSeverity(rate: number): 'success' | 'warning' | 'danger' {
    if (rate >= 0.85) return 'success';
    if (rate >= 0.75) return 'warning';
    return 'danger';
  }

  getTotalBilled(): number {
    return this.payerBreakdown().reduce((sum, p) => sum + p.billedAmount, 0);
  }

  getTotalPaid(): number {
    return this.payerBreakdown().reduce((sum, p) => sum + p.paidAmount, 0);
  }

  getTotalAdjustments(): number {
    return this.payerBreakdown().reduce((sum, p) => sum + p.adjustments, 0);
  }

  getTotalWriteOffs(): number {
    return this.payerBreakdown().reduce((sum, p) => sum + p.writeOffs, 0);
  }

  getTotalOutstanding(): number {
    return this.payerBreakdown().reduce((sum, p) => sum + p.outstandingBalance, 0);
  }

  getAvgReimbursementRate(): number {
    const payers = this.payerBreakdown();
    return payers.reduce((sum, p) => sum + p.reimbursementRate, 0) / payers.length;
  }

  generateReport(): void {
    this.generatedDate = new Date();
    console.log('Generating financial report with filters:', {
      period: this.selectedPeriod,
      startDate: this.startDate,
      endDate: this.endDate,
      payer: this.selectedPayer,
    });
  }
}
