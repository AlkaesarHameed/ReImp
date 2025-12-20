/**
 * Reports Dashboard Component.
 * Source: Phase 5 Implementation Document
 *
 * Central hub for all reports with quick access to report types,
 * saved templates, and export options.
 */
import {
  Component,
  ChangeDetectionStrategy,
  signal,
} from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { DropdownModule } from 'primeng/dropdown';
import { CalendarModule } from 'primeng/calendar';
import { ChartModule } from 'primeng/chart';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';

interface ReportCard {
  id: string;
  title: string;
  description: string;
  icon: string;
  route: string;
  lastGenerated?: Date;
  category: 'claims' | 'financial' | 'operations';
}

interface QuickStat {
  label: string;
  value: string | number;
  icon: string;
  trend?: string;
  trendDirection?: 'up' | 'down' | 'neutral';
}

interface RecentReport {
  id: string;
  name: string;
  type: string;
  generatedAt: Date;
  generatedBy: string;
  fileType: 'pdf' | 'excel';
}

@Component({
  selector: 'app-reports-dashboard',
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
    CurrencyPipe,
    DatePipe,
    DecimalPipe,
  ],
  template: `
    <div class="reports-container">
      <!-- Header -->
      <div class="reports-header">
        <div class="header-content">
          <h1>
            <i class="pi pi-chart-line"></i>
            Reports & Analytics
          </h1>
          <p>Generate comprehensive reports and analyze claims data</p>
        </div>
        <div class="header-actions">
          <button pButton label="Schedule Report" icon="pi pi-calendar" class="p-button-outlined"></button>
          <button pButton label="Export All" icon="pi pi-download"></button>
        </div>
      </div>

      <!-- Quick Stats -->
      <div class="quick-stats">
        @for (stat of quickStats(); track stat.label) {
          <div class="stat-card">
            <div class="stat-icon">
              <i [class]="'pi ' + stat.icon"></i>
            </div>
            <div class="stat-content">
              <span class="stat-value">{{ stat.value }}</span>
              <span class="stat-label">{{ stat.label }}</span>
              @if (stat.trend) {
                <span class="stat-trend" [class]="'trend-' + stat.trendDirection">
                  <i [class]="'pi ' + (stat.trendDirection === 'up' ? 'pi-arrow-up' : stat.trendDirection === 'down' ? 'pi-arrow-down' : 'pi-minus')"></i>
                  {{ stat.trend }}
                </span>
              }
            </div>
          </div>
        }
      </div>

      <!-- Date Range Filter -->
      <div class="date-filter-bar">
        <div class="filter-group">
          <label>Report Period</label>
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
        <button pButton label="Apply" icon="pi pi-check" class="apply-btn"></button>
      </div>

      <!-- Report Categories -->
      <div class="report-categories">
        <h2>Available Reports</h2>

        <div class="category-section">
          <h3><i class="pi pi-file-edit"></i> Claims Reports</h3>
          <div class="report-cards">
            @for (report of claimsReports(); track report.id) {
              <div class="report-card" [routerLink]="report.route">
                <div class="report-icon">
                  <i [class]="'pi ' + report.icon"></i>
                </div>
                <div class="report-info">
                  <h4>{{ report.title }}</h4>
                  <p>{{ report.description }}</p>
                  @if (report.lastGenerated) {
                    <span class="last-generated">
                      Last generated: {{ report.lastGenerated | date:'short' }}
                    </span>
                  }
                </div>
                <div class="report-arrow">
                  <i class="pi pi-chevron-right"></i>
                </div>
              </div>
            }
          </div>
        </div>

        <div class="category-section">
          <h3><i class="pi pi-dollar"></i> Financial Reports</h3>
          <div class="report-cards">
            @for (report of financialReports(); track report.id) {
              <div class="report-card" [routerLink]="report.route">
                <div class="report-icon financial">
                  <i [class]="'pi ' + report.icon"></i>
                </div>
                <div class="report-info">
                  <h4>{{ report.title }}</h4>
                  <p>{{ report.description }}</p>
                  @if (report.lastGenerated) {
                    <span class="last-generated">
                      Last generated: {{ report.lastGenerated | date:'short' }}
                    </span>
                  }
                </div>
                <div class="report-arrow">
                  <i class="pi pi-chevron-right"></i>
                </div>
              </div>
            }
          </div>
        </div>
      </div>

      <!-- Charts Row -->
      <div class="charts-row">
        <p-card header="Claims Volume (Last 30 Days)" styleClass="chart-card">
          <p-chart type="bar" [data]="volumeChartData()" [options]="barChartOptions" height="250"></p-chart>
        </p-card>

        <p-card header="Financial Overview" styleClass="chart-card">
          <p-chart type="line" [data]="financialChartData()" [options]="lineChartOptions" height="250"></p-chart>
        </p-card>
      </div>

      <!-- Recent Reports -->
      <p-card header="Recently Generated Reports" styleClass="recent-card">
        <p-table
          [value]="recentReports()"
          [rows]="5"
          styleClass="p-datatable-sm"
        >
          <ng-template pTemplate="header">
            <tr>
              <th>Report Name</th>
              <th>Type</th>
              <th>Generated</th>
              <th>Generated By</th>
              <th>Format</th>
              <th>Actions</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-report>
            <tr>
              <td>
                <div class="report-name">
                  <i class="pi pi-file"></i>
                  {{ report.name }}
                </div>
              </td>
              <td>{{ report.type }}</td>
              <td>{{ report.generatedAt | date:'short' }}</td>
              <td>{{ report.generatedBy }}</td>
              <td>
                <p-tag
                  [value]="report.fileType.toUpperCase()"
                  [severity]="report.fileType === 'pdf' ? 'danger' : 'success'"
                ></p-tag>
              </td>
              <td>
                <button pButton icon="pi pi-download" class="p-button-text p-button-sm" pTooltip="Download"></button>
                <button pButton icon="pi pi-eye" class="p-button-text p-button-sm" pTooltip="Preview"></button>
                <button pButton icon="pi pi-refresh" class="p-button-text p-button-sm" pTooltip="Regenerate"></button>
              </td>
            </tr>
          </ng-template>
          <ng-template pTemplate="emptymessage">
            <tr>
              <td colspan="6" class="text-center p-4">
                No recent reports found. Generate your first report above.
              </td>
            </tr>
          </ng-template>
        </p-table>
      </p-card>
    </div>
  `,
  styles: [`
    .reports-container {
      padding: 1.5rem;
      background: #F8F9FA;
      min-height: 100vh;
    }

    .reports-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);
      color: white;
      padding: 1.5rem 2rem;
      border-radius: 10px;
      margin-bottom: 1.5rem;
    }

    .reports-header h1 {
      margin: 0;
      font-size: 1.75rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .reports-header p {
      margin: 0.5rem 0 0;
      opacity: 0.9;
    }

    .header-actions {
      display: flex;
      gap: 0.75rem;
    }

    .quick-stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    .stat-card {
      background: white;
      border-radius: 10px;
      padding: 1.25rem;
      display: flex;
      align-items: center;
      gap: 1rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }

    .stat-icon {
      width: 48px;
      height: 48px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #EEF2FF;
      color: #6366F1;
    }

    .stat-icon i { font-size: 1.25rem; }

    .stat-content {
      display: flex;
      flex-direction: column;
    }

    .stat-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: #1F2937;
    }

    .stat-label {
      font-size: 0.85rem;
      color: #6B7280;
    }

    .stat-trend {
      font-size: 0.75rem;
      display: flex;
      align-items: center;
      gap: 0.25rem;
      margin-top: 0.25rem;
    }

    .trend-up { color: #10B981; }
    .trend-down { color: #EF4444; }
    .trend-neutral { color: #6B7280; }

    .date-filter-bar {
      background: white;
      border-radius: 10px;
      padding: 1rem 1.5rem;
      display: flex;
      align-items: flex-end;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
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

    .apply-btn {
      margin-left: auto;
    }

    .report-categories {
      margin-bottom: 1.5rem;
    }

    .report-categories h2 {
      font-size: 1.25rem;
      color: #1F2937;
      margin-bottom: 1rem;
    }

    .category-section {
      margin-bottom: 1.5rem;
    }

    .category-section h3 {
      font-size: 1rem;
      color: #4B5563;
      margin-bottom: 0.75rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .report-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 1rem;
    }

    .report-card {
      background: white;
      border-radius: 10px;
      padding: 1.25rem;
      display: flex;
      align-items: center;
      gap: 1rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      cursor: pointer;
      transition: all 0.2s ease;
      border: 2px solid transparent;
    }

    .report-card:hover {
      border-color: #6366F1;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
    }

    .report-icon {
      width: 50px;
      height: 50px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #DBEAFE;
      color: #2563EB;
      flex-shrink: 0;
    }

    .report-icon.financial {
      background: #D1FAE5;
      color: #059669;
    }

    .report-icon i { font-size: 1.25rem; }

    .report-info {
      flex: 1;
    }

    .report-info h4 {
      margin: 0;
      font-size: 1rem;
      color: #1F2937;
    }

    .report-info p {
      margin: 0.25rem 0 0;
      font-size: 0.85rem;
      color: #6B7280;
    }

    .last-generated {
      font-size: 0.75rem;
      color: #9CA3AF;
      display: block;
      margin-top: 0.5rem;
    }

    .report-arrow {
      color: #9CA3AF;
    }

    .report-card:hover .report-arrow {
      color: #6366F1;
    }

    .charts-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    :host ::ng-deep .chart-card {
      height: 100%;
    }

    :host ::ng-deep .recent-card .p-card-body {
      padding: 0;
    }

    :host ::ng-deep .recent-card .p-card-content {
      padding: 0;
    }

    .report-name {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .report-name i {
      color: #6B7280;
    }

    @media (max-width: 1200px) {
      .charts-row {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 768px) {
      .reports-header {
        flex-direction: column;
        gap: 1rem;
        text-align: center;
      }

      .header-actions {
        width: 100%;
        justify-content: center;
      }

      .date-filter-bar {
        flex-wrap: wrap;
      }

      .filter-group {
        min-width: 150px;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReportsDashboardComponent {
  // Filter state
  selectedPeriod = 'last30';
  startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
  endDate = new Date();

  periodOptions = [
    { label: 'Last 7 Days', value: 'last7' },
    { label: 'Last 30 Days', value: 'last30' },
    { label: 'Last Quarter', value: 'lastQuarter' },
    { label: 'Year to Date', value: 'ytd' },
    { label: 'Custom Range', value: 'custom' },
  ];

  readonly quickStats = signal<QuickStat[]>([
    {
      label: 'Total Claims This Month',
      value: '2,847',
      icon: 'pi-file',
      trend: '+12.5%',
      trendDirection: 'up',
    },
    {
      label: 'Approval Rate',
      value: '87.3%',
      icon: 'pi-check-circle',
      trend: '+2.1%',
      trendDirection: 'up',
    },
    {
      label: 'Total Amount Processed',
      value: '$1.2M',
      icon: 'pi-dollar',
      trend: '+8.7%',
      trendDirection: 'up',
    },
    {
      label: 'Avg Processing Time',
      value: '2.3 days',
      icon: 'pi-clock',
      trend: '-0.5 days',
      trendDirection: 'up',
    },
  ]);

  readonly claimsReports = signal<ReportCard[]>([
    {
      id: 'claims-status',
      title: 'Claims Status Report',
      description: 'Detailed breakdown of claims by status, processing time, and outcome',
      icon: 'pi-chart-bar',
      route: '/reports/claims',
      lastGenerated: new Date(Date.now() - 2 * 60 * 60 * 1000),
      category: 'claims',
    },
    {
      id: 'denial-analysis',
      title: 'Denial Analysis Report',
      description: 'Analysis of denial reasons, patterns, and appeal outcomes',
      icon: 'pi-times-circle',
      route: '/reports/claims',
      lastGenerated: new Date(Date.now() - 24 * 60 * 60 * 1000),
      category: 'claims',
    },
    {
      id: 'processing-metrics',
      title: 'Processing Metrics Report',
      description: 'Performance metrics including turnaround time and volume trends',
      icon: 'pi-chart-line',
      route: '/reports/claims',
      category: 'claims',
    },
  ]);

  readonly financialReports = signal<ReportCard[]>([
    {
      id: 'financial-summary',
      title: 'Financial Summary Report',
      description: 'Overview of billed amounts, payments, and outstanding balances',
      icon: 'pi-wallet',
      route: '/reports/financial',
      lastGenerated: new Date(Date.now() - 4 * 60 * 60 * 1000),
      category: 'financial',
    },
    {
      id: 'reimbursement-analysis',
      title: 'Reimbursement Analysis',
      description: 'Analysis of reimbursement rates by provider, procedure, and payer',
      icon: 'pi-percentage',
      route: '/reports/financial',
      category: 'financial',
    },
    {
      id: 'aging-report',
      title: 'Accounts Receivable Aging',
      description: 'Outstanding claims categorized by age buckets (30/60/90+ days)',
      icon: 'pi-calendar',
      route: '/reports/financial',
      lastGenerated: new Date(Date.now() - 48 * 60 * 60 * 1000),
      category: 'financial',
    },
  ]);

  readonly recentReports = signal<RecentReport[]>([
    {
      id: '1',
      name: 'Claims Status Report - December 2024',
      type: 'Claims Status',
      generatedAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
      generatedBy: 'John Smith',
      fileType: 'pdf',
    },
    {
      id: '2',
      name: 'Financial Summary Q4 2024',
      type: 'Financial Summary',
      generatedAt: new Date(Date.now() - 4 * 60 * 60 * 1000),
      generatedBy: 'Jane Doe',
      fileType: 'excel',
    },
    {
      id: '3',
      name: 'Denial Analysis - November 2024',
      type: 'Denial Analysis',
      generatedAt: new Date(Date.now() - 24 * 60 * 60 * 1000),
      generatedBy: 'John Smith',
      fileType: 'pdf',
    },
    {
      id: '4',
      name: 'AR Aging Report - Week 50',
      type: 'Aging Report',
      generatedAt: new Date(Date.now() - 48 * 60 * 60 * 1000),
      generatedBy: 'Admin User',
      fileType: 'excel',
    },
  ]);

  // Chart data
  readonly volumeChartData = signal({
    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
    datasets: [
      {
        label: 'Approved',
        data: [580, 620, 590, 670],
        backgroundColor: '#10B981',
      },
      {
        label: 'Denied',
        data: [65, 72, 58, 68],
        backgroundColor: '#EF4444',
      },
      {
        label: 'Pending',
        data: [120, 95, 130, 85],
        backgroundColor: '#F59E0B',
      },
    ],
  });

  readonly financialChartData = signal({
    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
    datasets: [
      {
        label: 'Billed Amount',
        data: [320000, 345000, 298000, 378000],
        borderColor: '#6366F1',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Paid Amount',
        data: [275000, 302000, 265000, 342000],
        borderColor: '#10B981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
  });

  readonly barChartOptions = {
    plugins: {
      legend: {
        position: 'bottom',
      },
    },
    scales: {
      x: {
        stacked: false,
      },
      y: {
        beginAtZero: true,
      },
    },
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
        ticks: {
          callback: (value: number) => '$' + (value / 1000).toFixed(0) + 'K',
        },
      },
    },
  };
}
