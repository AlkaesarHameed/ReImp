/**
 * Claim Detail Component.
 * Source: Design Document Section 3.2
 *
 * Displays full claim details including status, amounts, line items, and documents.
 */
import {
  Component,
  ChangeDetectionStrategy,
  input,
  inject,
  signal,
  computed,
  OnInit,
} from '@angular/core';
import { CommonModule, DatePipe, CurrencyPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { DividerModule } from 'primeng/divider';
import { TableModule } from 'primeng/table';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { MessageModule } from 'primeng/message';
import { TooltipModule } from 'primeng/tooltip';
import { PanelModule } from 'primeng/panel';
import { TimelineModule } from 'primeng/timeline';

import {
  Claim,
  ClaimStatus,
  getStatusColor,
  getStatusLabel,
  FWARiskLevel,
} from '@claims-processing/models';
import { ClaimsApiService } from '@claims-processing/api-client';

@Component({
  selector: 'app-claim-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    CardModule,
    ButtonModule,
    TagModule,
    DividerModule,
    TableModule,
    ProgressSpinnerModule,
    MessageModule,
    TooltipModule,
    DatePipe,
    CurrencyPipe,
    PanelModule,
    TimelineModule,
  ],
  template: `
    <div class="claim-detail-container">
      <!-- Loading State -->
      @if (loading()) {
        <div class="loading-container">
          <p-progressSpinner strokeWidth="4"></p-progressSpinner>
          <p>Loading claim details...</p>
        </div>
      }

      <!-- Error State -->
      @if (error()) {
        <p-message severity="error" [text]="error()!" styleClass="mb-3 w-full"></p-message>
        <button pButton label="Retry" icon="pi pi-refresh" class="p-button-outlined" (click)="loadClaim()"></button>
      }

      <!-- Claim Details -->
      @if (claim(); as c) {
        <!-- Header -->
        <div class="claim-header">
          <div class="header-left">
            <button pButton icon="pi pi-arrow-left" class="p-button-text" routerLink="/claims" pTooltip="Back to Claims"></button>
            <div class="header-info">
              <h1>{{ c.tracking_number }}</h1>
              <div class="header-meta">
                <p-tag
                  [value]="getStatusLabel(c.status)"
                  [style]="{ 'background-color': getStatusColor(c.status) }"
                ></p-tag>
                <span class="claim-type">{{ c.claim_type | titlecase }}</span>
                @if (c.fwa_risk_level) {
                  <p-tag
                    [value]="'FWA: ' + c.fwa_risk_level"
                    [severity]="getFwaRiskSeverity(c.fwa_risk_level)"
                  ></p-tag>
                }
              </div>
            </div>
          </div>
          <div class="header-actions">
            @if (c.status === 'needs_review') {
              <button pButton label="Review" icon="pi pi-check-square" class="p-button-success" [routerLink]="['review']"></button>
            }
            @if (c.status === 'draft') {
              <button pButton label="Submit" icon="pi pi-send" class="p-button-primary" (click)="submitClaim()"></button>
            }
            <button pButton label="Print" icon="pi pi-print" class="p-button-outlined" (click)="printClaim()"></button>
          </div>
        </div>

        <!-- Summary Cards -->
        <div class="summary-cards">
          <p-card styleClass="summary-card">
            <div class="summary-item">
              <span class="summary-label">Total Charged</span>
              <span class="summary-value charged">{{ c.total_charged | currency }}</span>
            </div>
          </p-card>
          <p-card styleClass="summary-card">
            <div class="summary-item">
              <span class="summary-label">Total Allowed</span>
              <span class="summary-value">{{ c.total_allowed | currency }}</span>
            </div>
          </p-card>
          <p-card styleClass="summary-card">
            <div class="summary-item">
              <span class="summary-label">Total Paid</span>
              <span class="summary-value paid">{{ c.total_paid | currency }}</span>
            </div>
          </p-card>
          <p-card styleClass="summary-card">
            <div class="summary-item">
              <span class="summary-label">Patient Responsibility</span>
              <span class="summary-value">{{ c.patient_responsibility | currency }}</span>
            </div>
          </p-card>
        </div>

        <!-- Main Content Grid -->
        <div class="content-grid">
          <!-- Left Column -->
          <div class="content-left">
            <!-- Claim Information -->
            <p-panel header="Claim Information" [toggleable]="true">
              <div class="info-grid">
                <div class="info-item">
                  <label>Claim ID</label>
                  <span>{{ c.id }}</span>
                </div>
                <div class="info-item">
                  <label>Tracking Number</label>
                  <span>{{ c.tracking_number }}</span>
                </div>
                <div class="info-item">
                  <label>Claim Type</label>
                  <span>{{ c.claim_type | titlecase }}</span>
                </div>
                <div class="info-item">
                  <label>Service Dates</label>
                  <span>{{ c.service_date_from | date:'shortDate' }} - {{ c.service_date_to | date:'shortDate' }}</span>
                </div>
                <div class="info-item">
                  <label>Place of Service</label>
                  <span>{{ c.place_of_service || 'N/A' }}</span>
                </div>
                <div class="info-item">
                  <label>Prior Auth</label>
                  <span>{{ c.prior_auth_number || 'N/A' }}</span>
                </div>
              </div>
            </p-panel>

            <!-- Parties -->
            <p-panel header="Parties" [toggleable]="true" class="mt-3">
              <div class="info-grid">
                <div class="info-item">
                  <label>Member ID</label>
                  <span>{{ c.member_id }}</span>
                </div>
                <div class="info-item">
                  <label>Policy ID</label>
                  <span>{{ c.policy_id }}</span>
                </div>
                <div class="info-item">
                  <label>Provider ID</label>
                  <span>{{ c.provider_id }}</span>
                </div>
                @if (c.referring_provider_id) {
                  <div class="info-item">
                    <label>Referring Provider</label>
                    <span>{{ c.referring_provider_id }}</span>
                  </div>
                }
              </div>
            </p-panel>

            <!-- Diagnosis Codes -->
            <p-panel header="Diagnosis Codes" [toggleable]="true" class="mt-3">
              <div class="diagnosis-list">
                @for (code of c.diagnosis_codes; track code; let i = $index) {
                  <div class="diagnosis-item" [class.primary]="code === c.primary_diagnosis">
                    <span class="diagnosis-code">{{ code }}</span>
                    @if (code === c.primary_diagnosis) {
                      <p-tag value="Primary" severity="info" styleClass="ml-2"></p-tag>
                    }
                  </div>
                }
              </div>
            </p-panel>

            <!-- Line Items -->
            <p-panel header="Line Items" [toggleable]="true" class="mt-3">
              @if (c.line_items && c.line_items.length > 0) {
                <p-table [value]="c.line_items" styleClass="p-datatable-sm p-datatable-striped">
                  <ng-template pTemplate="header">
                    <tr>
                      <th>#</th>
                      <th>Procedure</th>
                      <th>Service Date</th>
                      <th>Qty</th>
                      <th class="text-right">Charged</th>
                      <th class="text-right">Allowed</th>
                      <th class="text-right">Paid</th>
                      <th>Status</th>
                    </tr>
                  </ng-template>
                  <ng-template pTemplate="body" let-item>
                    <tr [class.denied-row]="item.denied">
                      <td>{{ item.line_number }}</td>
                      <td>
                        <span class="procedure-code">{{ item.procedure_code }}</span>
                        @if (item.modifier_codes && item.modifier_codes.length > 0) {
                          <span class="modifiers">{{ item.modifier_codes.join(', ') }}</span>
                        }
                      </td>
                      <td>{{ item.service_date | date:'shortDate' }}</td>
                      <td>{{ item.quantity }}</td>
                      <td class="text-right">{{ item.charged_amount | currency }}</td>
                      <td class="text-right">{{ item.allowed_amount | currency }}</td>
                      <td class="text-right">{{ item.paid_amount | currency }}</td>
                      <td>
                        @if (item.denied) {
                          <p-tag value="Denied" severity="danger" pTooltip="{{ item.denial_reason }}"></p-tag>
                        } @else if (item.paid_amount && item.paid_amount > 0) {
                          <p-tag value="Paid" severity="success"></p-tag>
                        } @else {
                          <p-tag value="Pending" severity="info"></p-tag>
                        }
                      </td>
                    </tr>
                  </ng-template>
                  <ng-template pTemplate="footer">
                    <tr>
                      <td colspan="4" class="text-right font-bold">Totals:</td>
                      <td class="text-right font-bold">{{ c.total_charged | currency }}</td>
                      <td class="text-right font-bold">{{ c.total_allowed | currency }}</td>
                      <td class="text-right font-bold">{{ c.total_paid | currency }}</td>
                      <td></td>
                    </tr>
                  </ng-template>
                </p-table>
              } @else {
                <p class="text-gray-500">No line items</p>
              }
            </p-panel>
          </div>

          <!-- Right Column -->
          <div class="content-right">
            <!-- Timeline -->
            <p-panel header="Timeline" [toggleable]="true">
              <p-timeline [value]="claimTimeline()">
                <ng-template pTemplate="content" let-event>
                  <div class="timeline-event">
                    <span class="event-label">{{ event.label }}</span>
                    <span class="event-date">{{ event.date | date:'short' }}</span>
                  </div>
                </ng-template>
              </p-timeline>
            </p-panel>

            <!-- FWA Analysis -->
            @if (c.fwa_score !== undefined && c.fwa_score !== null) {
              <p-panel header="FWA Analysis" [toggleable]="true" class="mt-3">
                <div class="fwa-analysis">
                  <div class="fwa-score">
                    <span class="score-label">Risk Score</span>
                    <span class="score-value" [class]="'risk-' + c.fwa_risk_level">
                      {{ (c.fwa_score * 100).toFixed(1) }}%
                    </span>
                  </div>
                  <div class="fwa-level">
                    <span class="level-label">Risk Level</span>
                    <p-tag
                      [value]="c.fwa_risk_level || 'Unknown'"
                      [severity]="getFwaRiskSeverity(c.fwa_risk_level)"
                    ></p-tag>
                  </div>
                </div>
              </p-panel>
            }

            <!-- Documents -->
            <p-panel header="Documents" [toggleable]="true" class="mt-3">
              @if (c.documents && c.documents.length > 0) {
                <div class="documents-list">
                  @for (doc of c.documents; track doc.id) {
                    <div class="document-item">
                      <i class="pi pi-file"></i>
                      <div class="doc-info">
                        <span class="doc-name">{{ doc.file_name }}</span>
                        <span class="doc-meta">{{ doc.document_type }} • {{ formatFileSize(doc.file_size) }}</span>
                      </div>
                      <button pButton icon="pi pi-download" class="p-button-text p-button-sm"></button>
                    </div>
                  }
                </div>
              } @else {
                <p class="text-gray-500">No documents attached</p>
              }
            </p-panel>

            <!-- Notes -->
            <p-panel header="Notes" [toggleable]="true" class="mt-3">
              @if (c.notes && c.notes.length > 0) {
                <div class="notes-list">
                  @for (note of c.notes; track note.id) {
                    <div class="note-item" [class.internal]="note.note_type === 'internal'">
                      <div class="note-header">
                        <span class="note-by">{{ note.created_by }}</span>
                        <span class="note-date">{{ note.created_at | date:'short' }}</span>
                      </div>
                      <p class="note-content">{{ note.content }}</p>
                    </div>
                  }
                </div>
              } @else {
                <p class="text-gray-500">No notes</p>
              }
            </p-panel>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .claim-detail-container {
      padding: 1.5rem;
      background: #F8F9FA;
      min-height: 100vh;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 400px;
      gap: 1rem;
    }

    .claim-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
      background: white;
      padding: 1rem 1.5rem;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .header-info h1 {
      margin: 0;
      font-size: 1.5rem;
      color: #343A40;
    }

    .header-meta {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-top: 0.25rem;
    }

    .claim-type {
      color: #6C757D;
      font-size: 0.9rem;
    }

    .header-actions {
      display: flex;
      gap: 0.5rem;
    }

    .summary-cards {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    :host ::ng-deep .summary-card .p-card-body {
      padding: 1rem;
    }

    .summary-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
    }

    .summary-label {
      color: #6C757D;
      font-size: 0.85rem;
      margin-bottom: 0.25rem;
    }

    .summary-value {
      font-size: 1.5rem;
      font-weight: 600;
      color: #343A40;
    }

    .summary-value.charged {
      color: #6C757D;
    }

    .summary-value.paid {
      color: #28A745;
    }

    .content-grid {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 1.5rem;
    }

    .info-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;
    }

    .info-item {
      display: flex;
      flex-direction: column;
    }

    .info-item label {
      color: #6C757D;
      font-size: 0.8rem;
      text-transform: uppercase;
      margin-bottom: 0.25rem;
    }

    .info-item span {
      color: #343A40;
      font-weight: 500;
    }

    .diagnosis-list {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .diagnosis-item {
      display: flex;
      align-items: center;
      padding: 0.5rem 0.75rem;
      background: #F8F9FA;
      border-radius: 4px;
      border: 1px solid #DEE2E6;
    }

    .diagnosis-item.primary {
      background: #E3F2FD;
      border-color: #2196F3;
    }

    .diagnosis-code {
      font-family: monospace;
      font-weight: 600;
    }

    .procedure-code {
      font-family: monospace;
      font-weight: 500;
    }

    .modifiers {
      display: block;
      font-size: 0.8rem;
      color: #6C757D;
    }

    .text-right {
      text-align: right;
    }

    .font-bold {
      font-weight: 600;
    }

    .denied-row {
      background-color: #FFF5F5 !important;
    }

    .timeline-event {
      display: flex;
      flex-direction: column;
    }

    .event-label {
      font-weight: 500;
      color: #343A40;
    }

    .event-date {
      font-size: 0.8rem;
      color: #6C757D;
    }

    .fwa-analysis {
      display: flex;
      gap: 2rem;
    }

    .fwa-score, .fwa-level {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .score-label, .level-label {
      color: #6C757D;
      font-size: 0.8rem;
    }

    .score-value {
      font-size: 1.5rem;
      font-weight: 600;
    }

    .risk-low { color: #28A745; }
    .risk-medium { color: #FFC107; }
    .risk-high { color: #FD7E14; }
    .risk-critical { color: #DC3545; }

    .documents-list, .notes-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .document-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.5rem;
      background: #F8F9FA;
      border-radius: 4px;
    }

    .document-item i {
      font-size: 1.25rem;
      color: #6C757D;
    }

    .doc-info {
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    .doc-name {
      font-weight: 500;
      color: #343A40;
    }

    .doc-meta {
      font-size: 0.8rem;
      color: #6C757D;
    }

    .note-item {
      padding: 0.75rem;
      background: #F8F9FA;
      border-radius: 4px;
      border-left: 3px solid #17A2B8;
    }

    .note-item.internal {
      border-left-color: #FFC107;
    }

    .note-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 0.5rem;
    }

    .note-by {
      font-weight: 500;
      font-size: 0.9rem;
    }

    .note-date {
      font-size: 0.8rem;
      color: #6C757D;
    }

    .note-content {
      margin: 0;
      color: #343A40;
    }

    .text-gray-500 {
      color: #6C757D;
      font-style: italic;
    }

    .mt-3 {
      margin-top: 1rem;
    }

    @media (max-width: 1024px) {
      .summary-cards {
        grid-template-columns: repeat(2, 1fr);
      }

      .content-grid {
        grid-template-columns: 1fr;
      }

      .info-grid {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 768px) {
      .claim-header {
        flex-direction: column;
        gap: 1rem;
      }

      .header-actions {
        width: 100%;
        justify-content: flex-end;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClaimDetailComponent implements OnInit {
  private readonly claimsApi = inject(ClaimsApiService);

  readonly id = input.required<string>();

  readonly claim = signal<Claim | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  // Helper methods bound for template
  getStatusColor = getStatusColor;
  getStatusLabel = getStatusLabel;

  readonly claimTimeline = computed(() => {
    const c = this.claim();
    if (!c) return [];

    const events = [
      { label: 'Created', date: c.created_at },
    ];

    if (c.submitted_at) {
      events.push({ label: 'Submitted', date: c.submitted_at });
    }

    if (c.status === ClaimStatus.DOC_PROCESSING) {
      events.push({ label: 'Processing Documents', date: c.updated_at });
    }

    if (c.status === ClaimStatus.VALIDATING) {
      events.push({ label: 'Validating', date: c.updated_at });
    }

    if (c.status === ClaimStatus.ADJUDICATING) {
      events.push({ label: 'Adjudicating', date: c.updated_at });
    }

    if (c.processed_at) {
      events.push({ label: 'Processed', date: c.processed_at });
    }

    if (c.status === ClaimStatus.APPROVED) {
      events.push({ label: 'Approved', date: c.updated_at });
    }

    if (c.status === ClaimStatus.DENIED) {
      events.push({ label: 'Denied', date: c.updated_at });
    }

    return events;
  });

  ngOnInit(): void {
    this.loadClaim();
  }

  loadClaim(): void {
    this.loading.set(true);
    this.error.set(null);

    this.claimsApi.getClaim(this.id()).subscribe({
      next: (claim) => {
        this.claim.set(claim);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(err.message || 'Failed to load claim details');
        this.loading.set(false);
      },
    });
  }

  submitClaim(): void {
    const claimId = this.id();
    this.loading.set(true);

    this.claimsApi.submitClaim(claimId).subscribe({
      next: (claim) => {
        this.claim.set(claim);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(err.message || 'Failed to submit claim');
        this.loading.set(false);
      },
    });
  }

  printClaim(): void {
    window.print();
  }

  getFwaRiskSeverity(level: FWARiskLevel | undefined): 'success' | 'info' | 'warn' | 'danger' {
    if (!level) return 'info';
    const severityMap: Record<FWARiskLevel, 'success' | 'info' | 'warn' | 'danger'> = {
      [FWARiskLevel.LOW]: 'success',
      [FWARiskLevel.MEDIUM]: 'warn',
      [FWARiskLevel.HIGH]: 'warn',
      [FWARiskLevel.CRITICAL]: 'danger',
    };
    return severityMap[level] || 'info';
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
}
