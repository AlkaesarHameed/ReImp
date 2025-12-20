/**
 * Claim Review Component.
 * Source: Phase 3 Implementation Document
 * Source: Design Document Section 3.4
 * Verified: 2025-12-18
 *
 * Supervisor review workflow for claims needing manual review.
 */
import {
  Component,
  ChangeDetectionStrategy,
  inject,
  signal,
  computed,
  OnInit,
  OnDestroy,
} from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { DropdownModule } from 'primeng/dropdown';
import { InputTextareaModule } from 'primeng/inputtextarea';
import { DialogModule } from 'primeng/dialog';
import { ToastModule } from 'primeng/toast';
import { SplitterModule } from 'primeng/splitter';
import { MessageService } from 'primeng/api';
import { Subject, takeUntil } from 'rxjs';

import {
  Claim,
  ClaimStatus,
  DenialReasonCode,
  getStatusColor,
  getStatusLabel,
} from '@claims-processing/models';
import { ClaimsApiService } from '@claims-processing/api-client';

@Component({
  selector: 'app-claim-review',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    CardModule,
    ButtonModule,
    TableModule,
    TagModule,
    DropdownModule,
    InputTextareaModule,
    DialogModule,
    ToastModule,
    SplitterModule,
    CurrencyPipe,
    DatePipe,
  ],
  providers: [MessageService],
  template: `
    <div class="claim-review-container">
      <p-toast></p-toast>

      <div class="review-header">
        <h1><i class="pi pi-check-square"></i> Claims Review Queue</h1>
        <div class="header-stats">
          <span class="stat">
            <strong>{{ reviewQueue().length }}</strong> claims pending review
          </span>
        </div>
      </div>

      <p-splitter [style]="{height: 'calc(100vh - 150px)'}" layout="horizontal" [panelSizes]="[40, 60]">
        <!-- Queue Panel -->
        <ng-template pTemplate>
          <div class="queue-panel">
            <p-card styleClass="queue-card">
              <ng-template pTemplate="header">
                <div class="panel-header">
                  <h4>Review Queue</h4>
                  <div class="queue-filters">
                    <p-dropdown
                      [options]="priorityOptions"
                      [(ngModel)]="selectedPriority"
                      placeholder="All Priorities"
                      [showClear]="true"
                      (onChange)="filterQueue()"
                    ></p-dropdown>
                  </div>
                </div>
              </ng-template>

              <p-table
                [value]="filteredQueue()"
                [selection]="selectedClaim()"
                selectionMode="single"
                (onRowSelect)="onClaimSelect($event.data)"
                [scrollable]="true"
                scrollHeight="flex"
                styleClass="p-datatable-sm"
              >
                <ng-template pTemplate="header">
                  <tr>
                    <th>Tracking #</th>
                    <th>Member</th>
                    <th class="text-right">Amount</th>
                    <th>Priority</th>
                  </tr>
                </ng-template>
                <ng-template pTemplate="body" let-claim>
                  <tr [pSelectableRow]="claim" [class.selected]="selectedClaim()?.id === claim.id">
                    <td>
                      <span class="tracking-number">{{ claim.tracking_number }}</span>
                    </td>
                    <td>{{ claim.member_id }}</td>
                    <td class="text-right">{{ claim.total_charged | currency }}</td>
                    <td>
                      <p-tag
                        [value]="claim.priority"
                        [severity]="getPrioritySeverity(claim.priority)"
                      ></p-tag>
                    </td>
                  </tr>
                </ng-template>
                <ng-template pTemplate="emptymessage">
                  <tr>
                    <td colspan="4" class="text-center p-4">
                      <i class="pi pi-check-circle text-4xl text-green-300 mb-2"></i>
                      <p>All claims have been reviewed!</p>
                    </td>
                  </tr>
                </ng-template>
              </p-table>
            </p-card>
          </div>
        </ng-template>

        <!-- Detail Panel -->
        <ng-template pTemplate>
          <div class="detail-panel">
            @if (selectedClaim()) {
              <p-card styleClass="detail-card">
                <ng-template pTemplate="header">
                  <div class="detail-header">
                    <div>
                      <h4>{{ selectedClaim()!.tracking_number }}</h4>
                      <p-tag
                        [value]="getStatusLabel(selectedClaim()!.status)"
                        [style]="{ 'background-color': getStatusColor(selectedClaim()!.status) }"
                      ></p-tag>
                    </div>
                    <div class="detail-amount">
                      <span class="amount-label">Total Charged</span>
                      <span class="amount-value">{{ selectedClaim()!.total_charged | currency }}</span>
                    </div>
                  </div>
                </ng-template>

                <!-- Claim Details -->
                <div class="claim-details">
                  <div class="detail-section">
                    <h5>Member Information</h5>
                    <div class="detail-grid">
                      <div class="detail-item">
                        <span class="label">Member ID</span>
                        <span class="value">{{ selectedClaim()!.member_id }}</span>
                      </div>
                      <div class="detail-item">
                        <span class="label">Policy ID</span>
                        <span class="value">{{ selectedClaim()!.policy_id }}</span>
                      </div>
                    </div>
                  </div>

                  <div class="detail-section">
                    <h5>Service Information</h5>
                    <div class="detail-grid">
                      <div class="detail-item">
                        <span class="label">Provider ID</span>
                        <span class="value">{{ selectedClaim()!.provider_id }}</span>
                      </div>
                      <div class="detail-item">
                        <span class="label">Service Date</span>
                        <span class="value">{{ selectedClaim()!.service_date_from | date:'mediumDate' }}</span>
                      </div>
                      <div class="detail-item">
                        <span class="label">Primary Diagnosis</span>
                        <span class="value">{{ selectedClaim()!.primary_diagnosis }}</span>
                      </div>
                    </div>
                  </div>

                  <!-- Line Items -->
                  <div class="detail-section">
                    <h5>Service Lines</h5>
                    <p-table [value]="selectedClaim()!.line_items" styleClass="p-datatable-sm">
                      <ng-template pTemplate="header">
                        <tr>
                          <th>#</th>
                          <th>Procedure</th>
                          <th>Qty</th>
                          <th class="text-right">Charged</th>
                        </tr>
                      </ng-template>
                      <ng-template pTemplate="body" let-line let-i="rowIndex">
                        <tr>
                          <td>{{ i + 1 }}</td>
                          <td>{{ line.procedure_code }}</td>
                          <td>{{ line.quantity }}</td>
                          <td class="text-right">{{ line.charged_amount | currency }}</td>
                        </tr>
                      </ng-template>
                    </p-table>
                  </div>

                  <!-- FWA Score (if applicable) -->
                  @if (selectedClaim()!.fwa_score !== undefined) {
                    <div class="detail-section fwa-section">
                      <h5>Fraud Risk Assessment</h5>
                      <div class="fwa-display" [class]="selectedClaim()!.fwa_risk_level">
                        <span class="fwa-score">{{ selectedClaim()!.fwa_score | number:'1.0-0' }}%</span>
                        <span class="fwa-label">{{ selectedClaim()!.fwa_risk_level | uppercase }} RISK</span>
                      </div>
                    </div>
                  }
                </div>

                <!-- Review Actions -->
                <ng-template pTemplate="footer">
                  <div class="review-actions">
                    <button
                      pButton
                      label="Approve"
                      icon="pi pi-check"
                      class="p-button-success"
                      (click)="showApproveDialog()"
                    ></button>
                    <button
                      pButton
                      label="Deny"
                      icon="pi pi-times"
                      class="p-button-danger"
                      (click)="showDenyDialog()"
                    ></button>
                    <button
                      pButton
                      label="Pend"
                      icon="pi pi-clock"
                      class="p-button-warning"
                      (click)="showPendDialog()"
                    ></button>
                  </div>
                </ng-template>
              </p-card>
            } @else {
              <div class="no-selection">
                <i class="pi pi-arrow-left text-6xl text-gray-300"></i>
                <p>Select a claim from the queue to review</p>
              </div>
            }
          </div>
        </ng-template>
      </p-splitter>

      <!-- Approve Dialog -->
      <p-dialog
        header="Approve Claim"
        [(visible)]="showApprove"
        [style]="{width: '450px'}"
        [modal]="true"
      >
        <div class="dialog-content">
          <label for="approveNotes">Notes (Optional)</label>
          <textarea
            pInputTextarea
            id="approveNotes"
            [(ngModel)]="reviewNotes"
            rows="3"
            class="w-full"
            placeholder="Add any notes for this approval..."
          ></textarea>
        </div>
        <ng-template pTemplate="footer">
          <button pButton label="Cancel" class="p-button-text" (click)="showApprove = false"></button>
          <button pButton label="Approve" icon="pi pi-check" class="p-button-success" [loading]="processing()" (click)="approveClaim()"></button>
        </ng-template>
      </p-dialog>

      <!-- Deny Dialog -->
      <p-dialog
        header="Deny Claim"
        [(visible)]="showDeny"
        [style]="{width: '450px'}"
        [modal]="true"
      >
        <div class="dialog-content">
          <div class="field">
            <label for="denialReason">Denial Reason *</label>
            <p-dropdown
              id="denialReason"
              [options]="denialReasons()"
              [(ngModel)]="selectedDenialReason"
              optionLabel="description"
              optionValue="code"
              placeholder="Select a reason"
              styleClass="w-full"
            ></p-dropdown>
          </div>
          <div class="field">
            <label for="denyNotes">Notes *</label>
            <textarea
              pInputTextarea
              id="denyNotes"
              [(ngModel)]="reviewNotes"
              rows="3"
              class="w-full"
              placeholder="Explain the denial..."
            ></textarea>
          </div>
        </div>
        <ng-template pTemplate="footer">
          <button pButton label="Cancel" class="p-button-text" (click)="showDeny = false"></button>
          <button pButton label="Deny" icon="pi pi-times" class="p-button-danger" [loading]="processing()" [disabled]="!selectedDenialReason || !reviewNotes" (click)="denyClaim()"></button>
        </ng-template>
      </p-dialog>

      <!-- Pend Dialog -->
      <p-dialog
        header="Pend Claim"
        [(visible)]="showPend"
        [style]="{width: '450px'}"
        [modal]="true"
      >
        <div class="dialog-content">
          <label for="pendNotes">Reason for Pending *</label>
          <textarea
            pInputTextarea
            id="pendNotes"
            [(ngModel)]="reviewNotes"
            rows="3"
            class="w-full"
            placeholder="What additional information is needed..."
          ></textarea>
        </div>
        <ng-template pTemplate="footer">
          <button pButton label="Cancel" class="p-button-text" (click)="showPend = false"></button>
          <button pButton label="Pend" icon="pi pi-clock" class="p-button-warning" [loading]="processing()" [disabled]="!reviewNotes" (click)="pendClaim()"></button>
        </ng-template>
      </p-dialog>
    </div>
  `,
  styles: [`
    .claim-review-container {
      padding: 1.5rem;
      background: #f8f9fa;
      min-height: 100vh;
    }

    .review-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }

    .review-header h1 {
      margin: 0;
      font-size: 1.5rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .header-stats .stat {
      background: white;
      padding: 0.5rem 1rem;
      border-radius: 4px;
      font-size: 0.9rem;
    }

    .queue-panel, .detail-panel {
      height: 100%;
      padding: 0.5rem;
    }

    .queue-card, .detail-card {
      height: 100%;
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      background: #f8f9fa;
    }

    .panel-header h4 {
      margin: 0;
    }

    .tracking-number {
      color: #0066cc;
      font-weight: 500;
    }

    .text-right {
      text-align: right;
    }

    .text-center {
      text-align: center;
    }

    .detail-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      padding: 1rem;
      background: #f8f9fa;
    }

    .detail-header h4 {
      margin: 0 0 0.5rem;
    }

    .detail-amount {
      text-align: right;
    }

    .amount-label {
      display: block;
      font-size: 0.85rem;
      color: #6c757d;
    }

    .amount-value {
      font-size: 1.5rem;
      font-weight: 600;
      color: #0066cc;
    }

    .claim-details {
      padding: 1rem;
    }

    .detail-section {
      margin-bottom: 1.5rem;
    }

    .detail-section h5 {
      margin: 0 0 0.75rem;
      color: #343a40;
      border-bottom: 1px solid #dee2e6;
      padding-bottom: 0.5rem;
    }

    .detail-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 1rem;
    }

    .detail-item {
      display: flex;
      flex-direction: column;
    }

    .detail-item .label {
      font-size: 0.85rem;
      color: #6c757d;
    }

    .detail-item .value {
      font-weight: 500;
    }

    .fwa-section {
      background: #f8f9fa;
      padding: 1rem;
      border-radius: 4px;
    }

    .fwa-display {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 1rem;
      border-radius: 4px;
    }

    .fwa-display.low { background: #d4edda; }
    .fwa-display.medium { background: #fff3cd; }
    .fwa-display.high { background: #f8d7da; }
    .fwa-display.critical { background: #dc3545; color: white; }

    .fwa-score {
      font-size: 2rem;
      font-weight: 600;
    }

    .fwa-label {
      font-weight: 500;
    }

    .review-actions {
      display: flex;
      gap: 0.5rem;
      justify-content: flex-end;
      padding: 1rem;
      border-top: 1px solid #dee2e6;
    }

    .no-selection {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #6c757d;
    }

    .dialog-content {
      padding: 1rem 0;
    }

    .dialog-content .field {
      margin-bottom: 1rem;
    }

    .dialog-content label {
      display: block;
      margin-bottom: 0.5rem;
      font-weight: 500;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClaimReviewComponent implements OnInit, OnDestroy {
  private readonly claimsApi = inject(ClaimsApiService);
  private readonly messageService = inject(MessageService);
  private readonly destroy$ = new Subject<void>();

  // State
  readonly reviewQueue = signal<Claim[]>([]);
  readonly selectedClaim = signal<Claim | null>(null);
  readonly denialReasons = signal<DenialReasonCode[]>([]);
  readonly processing = signal<boolean>(false);

  // Filters
  selectedPriority: string | null = null;
  readonly priorityOptions = [
    { label: 'Low', value: 'low' },
    { label: 'Normal', value: 'normal' },
    { label: 'High', value: 'high' },
    { label: 'Urgent', value: 'urgent' },
  ];

  // Computed
  readonly filteredQueue = computed(() => {
    const queue = this.reviewQueue();
    if (!this.selectedPriority) return queue;
    return queue.filter(c => c.priority === this.selectedPriority);
  });

  // Dialog state
  showApprove = false;
  showDeny = false;
  showPend = false;
  reviewNotes = '';
  selectedDenialReason: string | null = null;

  // Helpers bound for template
  getStatusColor = getStatusColor;
  getStatusLabel = getStatusLabel;

  ngOnInit(): void {
    this.loadReviewQueue();
    this.loadDenialReasons();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadReviewQueue(): void {
    this.claimsApi
      .getClaims({ status: ClaimStatus.NEEDS_REVIEW })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.reviewQueue.set(response.items);
        },
        error: () => {
          this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to load review queue',
          });
        },
      });
  }

  private loadDenialReasons(): void {
    // Mock data - would call lookupApi.getDenialReasonCodes()
    this.denialReasons.set([
      { code: 'NC', description: 'Not Covered', category: 'eligibility' },
      { code: 'MD', description: 'Medical Necessity Not Met', category: 'medical' },
      { code: 'DP', description: 'Duplicate Claim', category: 'administrative' },
      { code: 'PA', description: 'Prior Authorization Required', category: 'administrative' },
      { code: 'EX', description: 'Benefit Exhausted', category: 'eligibility' },
      { code: 'OT', description: 'Other', category: 'other' },
    ]);
  }

  filterQueue(): void {
    // Filtering is handled by computed signal
  }

  onClaimSelect(claim: Claim): void {
    this.selectedClaim.set(claim);
  }

  getPrioritySeverity(priority: string): 'success' | 'info' | 'warning' | 'danger' {
    switch (priority) {
      case 'low': return 'success';
      case 'normal': return 'info';
      case 'high': return 'warning';
      case 'urgent': return 'danger';
      default: return 'info';
    }
  }

  showApproveDialog(): void {
    this.reviewNotes = '';
    this.showApprove = true;
  }

  showDenyDialog(): void {
    this.reviewNotes = '';
    this.selectedDenialReason = null;
    this.showDeny = true;
  }

  showPendDialog(): void {
    this.reviewNotes = '';
    this.showPend = true;
  }

  approveClaim(): void {
    const claim = this.selectedClaim();
    if (!claim) return;

    this.processing.set(true);

    this.claimsApi
      .approveClaim(claim.id, { notes: this.reviewNotes })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.processing.set(false);
          this.showApprove = false;
          this.messageService.add({
            severity: 'success',
            summary: 'Approved',
            detail: `Claim ${claim.tracking_number} has been approved.`,
          });
          this.removeFromQueue(claim.id);
        },
        error: () => {
          this.processing.set(false);
          this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to approve claim',
          });
        },
      });
  }

  denyClaim(): void {
    const claim = this.selectedClaim();
    if (!claim || !this.selectedDenialReason || !this.reviewNotes) return;

    this.processing.set(true);

    this.claimsApi
      .denyClaim(claim.id, { reason: this.selectedDenialReason, notes: this.reviewNotes })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.processing.set(false);
          this.showDeny = false;
          this.messageService.add({
            severity: 'info',
            summary: 'Denied',
            detail: `Claim ${claim.tracking_number} has been denied.`,
          });
          this.removeFromQueue(claim.id);
        },
        error: () => {
          this.processing.set(false);
          this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to deny claim',
          });
        },
      });
  }

  pendClaim(): void {
    const claim = this.selectedClaim();
    if (!claim || !this.reviewNotes) return;

    this.processing.set(true);

    this.claimsApi
      .pendClaim(claim.id, { notes: this.reviewNotes })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.processing.set(false);
          this.showPend = false;
          this.messageService.add({
            severity: 'warn',
            summary: 'Pended',
            detail: `Claim ${claim.tracking_number} has been pended for additional information.`,
          });
          this.removeFromQueue(claim.id);
        },
        error: () => {
          this.processing.set(false);
          this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to pend claim',
          });
        },
      });
  }

  private removeFromQueue(claimId: string): void {
    this.reviewQueue.update(queue => queue.filter(c => c.id !== claimId));
    this.selectedClaim.set(null);
  }
}
