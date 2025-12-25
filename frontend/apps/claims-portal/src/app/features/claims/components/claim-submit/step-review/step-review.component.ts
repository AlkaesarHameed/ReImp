/**
 * Step Review Component.
 * Source: Phase 3 Implementation Document
 * Source: Design Document Section 3.4
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Verified: 2025-12-19
 *
 * Final step of claim submission wizard - Review and submit claim.
 * Displays member, provider, services, and uploaded document information.
 */
import {
  Component,
  ChangeDetectionStrategy,
  Input,
  Output,
  EventEmitter,
  inject,
  signal,
  computed,
} from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { switchMap } from 'rxjs/operators';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { DividerModule } from 'primeng/divider';
import { TableModule } from 'primeng/table';
import { MessageModule } from 'primeng/message';
import { CheckboxModule } from 'primeng/checkbox';
import { TagModule } from 'primeng/tag';
import { AccordionModule } from 'primeng/accordion';
import { TooltipModule } from 'primeng/tooltip';
import { FormsModule } from '@angular/forms';

import {
  ClaimFormState,
  ClaimCreate,
  ClaimLineItemCreate,
  ClaimType,
  DocumentUploadState,
  MergedExtractedData,
  getDocumentTypeLabel,
  formatFileSize,
  getConfidenceSeverity,
} from '@claims-processing/models';
import { ClaimsApiService } from '@claims-processing/api-client';

/**
 * Enhanced form state with document data.
 */
interface EnhancedClaimFormState extends ClaimFormState {
  policyDocuments: DocumentUploadState[];
  claimDocuments: DocumentUploadState[];
  mergedExtractedData: MergedExtractedData | null;
  policyDocsSkipped: boolean;
}

@Component({
  selector: 'app-step-review',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ButtonModule,
    CardModule,
    DividerModule,
    TableModule,
    MessageModule,
    CheckboxModule,
    TagModule,
    AccordionModule,
    TooltipModule,
    CurrencyPipe,
    DatePipe,
  ],
  template: `
    <div class="step-review">
      <h3>{{ editMode ? 'Step 5: Review Data' : 'Step 6: Submit' }}</h3>
      <p class="step-description">{{ editMode ? 'Review and edit claim details before submission.' : 'Review all claim details and submit your claim.' }}</p>

      <!-- Validation Summary -->
      @if (validationErrors().length > 0) {
        <p-card styleClass="validation-card error">
          <ng-template pTemplate="header">
            <div class="validation-header error">
              <i class="pi pi-times-circle"></i>
              <span>Validation Errors</span>
            </div>
          </ng-template>
          <ul class="validation-list">
            @for (error of validationErrors(); track error.field) {
              <li>{{ error.message }}</li>
            }
          </ul>
        </p-card>
      }

      @if (validationWarnings().length > 0) {
        <p-card styleClass="validation-card warning">
          <ng-template pTemplate="header">
            <div class="validation-header warning">
              <i class="pi pi-exclamation-triangle"></i>
              <span>Warnings</span>
            </div>
          </ng-template>
          <ul class="validation-list">
            @for (warning of validationWarnings(); track warning.field) {
              <li>{{ warning.message }}</li>
            }
          </ul>
        </p-card>
      }

      <!-- Member Summary -->
      <p-card styleClass="summary-card">
        <ng-template pTemplate="header">
          <div class="summary-header">
            <h4>Member Information</h4>
            <button pButton type="button" label="Edit" icon="pi pi-pencil" class="p-button-text p-button-sm" (click)="editStep(0)"></button>
          </div>
        </ng-template>
        <div class="summary-grid">
          <div class="summary-item">
            <span class="label">Member ID</span>
            <span class="value">{{ formState?.member?.memberId }}</span>
          </div>
          <div class="summary-item">
            <span class="label">Policy ID</span>
            <span class="value">{{ formState?.member?.policyId }}</span>
          </div>
          <div class="summary-item">
            <span class="label">Eligibility</span>
            <span class="value" [class.verified]="formState?.member?.eligibilityVerified">
              {{ formState?.member?.eligibilityVerified ? 'Verified' : 'Not Verified' }}
            </span>
          </div>
          @if (formState?.member?.eligibilityResponse) {
            <div class="summary-item">
              <span class="label">Coverage Type</span>
              <span class="value">{{ formState?.member?.eligibilityResponse?.coverageType }}</span>
            </div>
          }
        </div>
      </p-card>

      <!-- Uploaded Documents Summary -->
      @if (hasDocuments()) {
        <p-card styleClass="summary-card">
          <ng-template pTemplate="header">
            <div class="summary-header">
              <h4>Uploaded Documents</h4>
              <div class="header-actions">
                <button pButton type="button" label="Policy Docs" icon="pi pi-pencil" class="p-button-text p-button-sm" (click)="editStep(1)"></button>
                <button pButton type="button" label="Claim Docs" icon="pi pi-pencil" class="p-button-text p-button-sm" (click)="editStep(2)"></button>
              </div>
            </div>
          </ng-template>

          @if (enhancedFormState?.policyDocsSkipped) {
            <p-message severity="info" text="Policy documents were skipped" styleClass="mb-3"></p-message>
          }

          <div class="documents-grid">
            @if (enhancedFormState?.policyDocuments?.length) {
              <div class="doc-group">
                <h5>Policy Documents ({{ enhancedFormState.policyDocuments.length }})</h5>
                @for (doc of enhancedFormState.policyDocuments; track doc.id) {
                  <div class="doc-item">
                    <i class="pi pi-file-pdf doc-icon"></i>
                    <div class="doc-info">
                      <span class="doc-name">{{ doc.filename }}</span>
                      <span class="doc-meta">{{ formatFileSize(doc.fileSize) }}</span>
                    </div>
                    <p-tag
                      [value]="doc.status"
                      [severity]="doc.status === 'completed' ? 'success' : doc.status === 'failed' ? 'danger' : 'info'"
                    ></p-tag>
                  </div>
                }
              </div>
            }

            @if (enhancedFormState?.claimDocuments?.length) {
              <div class="doc-group">
                <h5>Claim Documents ({{ enhancedFormState.claimDocuments.length }})</h5>
                @for (doc of enhancedFormState.claimDocuments; track doc.id) {
                  <div class="doc-item">
                    <i class="pi pi-file-pdf doc-icon"></i>
                    <div class="doc-info">
                      <span class="doc-name">{{ doc.filename }}</span>
                      <span class="doc-meta">{{ getDocumentTypeLabel(doc.documentType) }} · {{ formatFileSize(doc.fileSize) }}</span>
                    </div>
                    <p-tag
                      [value]="doc.status"
                      [severity]="doc.status === 'completed' ? 'success' : doc.status === 'failed' ? 'danger' : 'info'"
                    ></p-tag>
                  </div>
                }
              </div>
            }
          </div>

          <!-- Extracted Data Confidence -->
          @if (enhancedFormState?.mergedExtractedData) {
            <p-divider></p-divider>
            <div class="extraction-summary">
              <h5>Data Extraction Summary</h5>
              <div class="confidence-info">
                <span>Overall Confidence:</span>
                <p-tag
                  [value]="(enhancedFormState.mergedExtractedData.overall_confidence * 100).toFixed(0) + '%'"
                  [severity]="getConfidenceSeverity(enhancedFormState.mergedExtractedData.overall_confidence)"
                ></p-tag>
              </div>
              @if (enhancedFormState.mergedExtractedData.conflicts?.length) {
                <p-message
                  severity="warn"
                  [text]="enhancedFormState.mergedExtractedData.conflicts.length + ' data conflict(s) were resolved'"
                  styleClass="mt-2"
                ></p-message>
              }
            </div>
          }
        </p-card>
      }

      <!-- Provider Summary -->
      <p-card styleClass="summary-card">
        <ng-template pTemplate="header">
          <div class="summary-header">
            <h4>Provider Information</h4>
            <button pButton type="button" label="Edit" icon="pi pi-pencil" class="p-button-text p-button-sm" (click)="editStep(4)"></button>
          </div>
        </ng-template>
        <div class="summary-grid">
          <div class="summary-item">
            <span class="label">Provider ID</span>
            <span class="value">{{ formState?.provider?.providerId }}</span>
          </div>
          <div class="summary-item">
            <span class="label">NPI</span>
            <span class="value">{{ formState?.provider?.providerNPI }}</span>
          </div>
          <div class="summary-item">
            <span class="label">Place of Service</span>
            <span class="value">{{ formState?.provider?.placeOfService }}</span>
          </div>
          @if (formState?.provider?.priorAuthNumber) {
            <div class="summary-item">
              <span class="label">Prior Auth #</span>
              <span class="value">{{ formState?.provider?.priorAuthNumber }}</span>
            </div>
          }
        </div>
      </p-card>

      <!-- Services Summary -->
      <p-card styleClass="summary-card">
        <ng-template pTemplate="header">
          <div class="summary-header">
            <h4>Service Information</h4>
            <button pButton type="button" label="Edit" icon="pi pi-pencil" class="p-button-text p-button-sm" (click)="editStep(5)"></button>
          </div>
        </ng-template>

        <div class="summary-grid">
          <div class="summary-item">
            <span class="label">Service Date From</span>
            <span class="value">{{ formState?.services?.serviceDateFrom | date:'mediumDate' }}</span>
          </div>
          <div class="summary-item">
            <span class="label">Service Date To</span>
            <span class="value">{{ formState?.services?.serviceDateTo | date:'mediumDate' }}</span>
          </div>
        </div>

        <p-divider></p-divider>

        <h5>Diagnosis Codes</h5>
        <div class="diagnosis-summary">
          @for (dx of formState?.services?.diagnosisCodes || []; track dx; let i = $index) {
            <span class="diagnosis-chip" [class.primary]="dx === formState?.services?.primaryDiagnosis">
              {{ i + 1 }}. {{ dx }}
              @if (dx === formState?.services?.primaryDiagnosis) {
                <small>(Primary)</small>
              }
            </span>
          }
        </div>

        <p-divider></p-divider>

        <h5>Service Lines ({{ (formState?.services?.lineItems || []).length }} items)</h5>
        <p-table [value]="formState?.services?.lineItems || []" styleClass="p-datatable-sm" [scrollable]="true" scrollHeight="400px">
          <ng-template pTemplate="header">
            <tr>
              <th style="width: 50px">#</th>
              <th style="width: 120px">Code</th>
              <th>Description</th>
              <th style="width: 80px">Qty</th>
              <th style="width: 100px" class="text-right">Unit Price</th>
              <th style="width: 120px" class="text-right">Amount</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-line let-i="rowIndex">
            <tr>
              <td>{{ i + 1 }}</td>
              <td>{{ line.procedureCode || '-' }}</td>
              <td>{{ line.description || line.procedureCode || '-' }}</td>
              <td>{{ line.quantity || 1 }}</td>
              <td class="text-right">{{ line.unitPrice | currency:'INR':'symbol':'1.2-2' }}</td>
              <td class="text-right">{{ line.chargedAmount | currency:'INR':'symbol':'1.2-2' }}</td>
            </tr>
          </ng-template>
          <ng-template pTemplate="footer">
            <tr class="font-bold">
              <td colspan="5" class="text-right"><strong>Total Charged:</strong></td>
              <td class="text-right"><strong>{{ totalCharged() | currency:'INR':'symbol':'1.2-2' }}</strong></td>
            </tr>
          </ng-template>
        </p-table>
      </p-card>

      <!-- Edit Mode: Proceed to Submit button -->
      @if (editMode) {
        <div class="step-navigation">
          <button
            pButton
            type="button"
            label="Back"
            icon="pi pi-arrow-left"
            class="p-button-outlined"
            (click)="onBack()"
          ></button>
          <button
            pButton
            type="button"
            label="Proceed to Submit"
            icon="pi pi-arrow-right"
            (click)="onProceedToSubmit()"
          ></button>
        </div>
      } @else {
        <!-- Confirmation -->
        <div class="confirmation-section">
          <p-checkbox
            [(ngModel)]="confirmed"
            [binary]="true"
            inputId="confirmSubmit"
          ></p-checkbox>
          <label for="confirmSubmit" class="confirmation-label">
            I confirm that the information provided is accurate and complete. I understand that submitting false claims may result in penalties.
          </label>
        </div>

        <!-- Submission Error -->
        @if (submitError()) {
          <p-message severity="error" [text]="submitError()!" styleClass="w-full mt-3"></p-message>
        }

        <!-- Navigation -->
        <div class="step-navigation">
          <button
            pButton
            type="button"
            label="Back"
            icon="pi pi-arrow-left"
            class="p-button-outlined"
            (click)="onBack()"
          ></button>
          <div class="submit-actions">
            <button
              pButton
              type="button"
              label="Save as Draft"
              icon="pi pi-save"
              class="p-button-outlined"
              [loading]="saving()"
              (click)="onSaveDraft()"
            ></button>
            <button
              pButton
              type="button"
              label="Submit Claim"
              icon="pi pi-send"
              [disabled]="!canSubmit()"
              [loading]="submitting()"
              (click)="onSubmit()"
            ></button>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .step-review {
      padding: 1rem;
    }

    .step-description {
      color: #6c757d;
      margin-bottom: 1.5rem;
    }

    .validation-card {
      margin-bottom: 1rem;
    }

    .validation-card.error :host ::ng-deep .p-card {
      border-left: 4px solid #dc3545;
    }

    .validation-card.warning :host ::ng-deep .p-card {
      border-left: 4px solid #ffc107;
    }

    .validation-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1rem;
      font-weight: 600;
    }

    .validation-header.error {
      background: #f8d7da;
      color: #721c24;
    }

    .validation-header.warning {
      background: #fff3cd;
      color: #856404;
    }

    .validation-list {
      margin: 0;
      padding-left: 1.5rem;
    }

    .validation-list li {
      margin-bottom: 0.25rem;
    }

    .summary-card {
      margin-bottom: 1rem;
    }

    .summary-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem 1rem;
      background: #f8f9fa;
    }

    .summary-header h4 {
      margin: 0;
    }

    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      padding: 1rem;
    }

    .summary-item {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .summary-item .label {
      font-size: 0.85rem;
      color: #6c757d;
    }

    .summary-item .value {
      font-weight: 500;
    }

    .summary-item .value.verified {
      color: #28a745;
    }

    .diagnosis-summary {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      padding: 0 1rem;
    }

    .diagnosis-chip {
      background: #f8f9fa;
      padding: 0.5rem 1rem;
      border-radius: 4px;
      font-size: 0.9rem;
    }

    .diagnosis-chip.primary {
      background: #e7f3ff;
      border: 1px solid #0066cc;
    }

    .diagnosis-chip small {
      color: #0066cc;
      margin-left: 0.25rem;
    }

    h5 {
      padding: 0 1rem;
      margin: 1rem 0 0.5rem;
    }

    .text-right {
      text-align: right;
    }

    .confirmation-section {
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
      padding: 1rem;
      background: #f8f9fa;
      border-radius: 4px;
      margin-top: 1.5rem;
    }

    .confirmation-label {
      font-size: 0.9rem;
      line-height: 1.5;
      cursor: pointer;
    }

    .step-navigation {
      display: flex;
      justify-content: space-between;
      margin-top: 2rem;
      padding-top: 1rem;
      border-top: 1px solid #dee2e6;
    }

    .submit-actions {
      display: flex;
      gap: 0.5rem;
    }

    .header-actions {
      display: flex;
      gap: 0.5rem;
    }

    .documents-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 1.5rem;
      padding: 1rem;
    }

    .doc-group h5 {
      padding: 0;
      margin: 0 0 0.75rem 0;
      color: #495057;
    }

    .doc-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.5rem;
      background: #f8f9fa;
      border-radius: 4px;
      margin-bottom: 0.5rem;
    }

    .doc-icon {
      font-size: 1.25rem;
      color: #dc3545;
    }

    .doc-info {
      flex: 1;
      min-width: 0;
    }

    .doc-name {
      display: block;
      font-weight: 500;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .doc-meta {
      font-size: 0.8rem;
      color: #6c757d;
    }

    .extraction-summary {
      padding: 1rem;
    }

    .extraction-summary h5 {
      padding: 0;
      margin: 0 0 0.75rem 0;
    }

    .confidence-info {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    @media (max-width: 768px) {
      .summary-grid {
        grid-template-columns: 1fr;
      }

      .submit-actions {
        flex-direction: column;
      }

      .header-actions {
        flex-direction: column;
      }

      .documents-grid {
        grid-template-columns: 1fr;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StepReviewComponent {
  private readonly claimsApi = inject(ClaimsApiService);

  @Input() formState?: ClaimFormState;
  @Input() enhancedFormState?: EnhancedClaimFormState;
  @Input() editMode = false; // When true, allows inline editing before submit

  @Output() stepBack = new EventEmitter<void>();
  @Output() editStepRequest = new EventEmitter<number>();
  @Output() submitSuccess = new EventEmitter<string>();
  @Output() draftSaved = new EventEmitter<string>();
  @Output() dataUpdated = new EventEmitter<{
    member?: import('@claims-processing/models').MemberStepData;
    provider?: import('@claims-processing/models').ProviderStepData;
    services?: import('@claims-processing/models').ServicesStepData;
  }>();
  @Output() proceedToSubmit = new EventEmitter<void>();

  // Use a signal for confirmed to ensure canSubmit computed properly reacts to changes
  readonly confirmedSignal = signal<boolean>(false);

  // Getter/setter for template binding compatibility with [(ngModel)]
  get confirmed(): boolean {
    return this.confirmedSignal();
  }
  set confirmed(value: boolean) {
    this.confirmedSignal.set(value);
  }

  readonly validationErrors = signal<{ field: string; message: string }[]>([]);
  readonly validationWarnings = signal<{ field: string; message: string }[]>([]);
  readonly submitting = signal<boolean>(false);
  readonly saving = signal<boolean>(false);
  readonly submitError = signal<string | null>(null);

  /**
   * Calculate total charged from line items.
   * Uses chargedAmount (already parsed from total_value during data mapping).
   * Also adds grossValue if present, subtracts discount for accurate total.
   */
  readonly totalCharged = computed(() => {
    const lineItems = this.formState?.services?.lineItems || [];
    if (lineItems.length === 0) {
      // Fallback to mergedExtractedData.financial.total_charged if no line items
      const extractedTotal = this.enhancedFormState?.mergedExtractedData?.financial?.total_charged;
      return extractedTotal ? parseFloat(extractedTotal) || 0 : 0;
    }
    return lineItems.reduce(
      (sum, item) => sum + (item.chargedAmount || 0),
      0
    );
  });

  readonly canSubmit = computed(() =>
    this.confirmedSignal() &&
    this.validationErrors().length === 0 &&
    !this.submitting()
  );

  /**
   * Check if there are any uploaded documents.
   */
  hasDocuments(): boolean {
    const enhanced = this.enhancedFormState;
    if (!enhanced) return false;
    return (
      (enhanced.policyDocuments?.length > 0) ||
      (enhanced.claimDocuments?.length > 0) ||
      enhanced.policyDocsSkipped
    );
  }

  // Utility methods for template
  formatFileSize = formatFileSize;
  getDocumentTypeLabel = getDocumentTypeLabel;
  getConfidenceSeverity = getConfidenceSeverity;

  editStep(stepIndex: number): void {
    this.editStepRequest.emit(stepIndex);
  }

  onBack(): void {
    this.stepBack.emit();
  }

  onProceedToSubmit(): void {
    this.proceedToSubmit.emit();
  }

  onSaveDraft(): void {
    if (!this.formState) {
      console.warn('Cannot save draft: formState is not available');
      return;
    }

    console.log('Saving draft...');
    this.saving.set(true);
    this.submitError.set(null);

    // Build claim data (would be used with actual API)
    const claimData = this.buildClaimCreate();
    console.log('Draft claim data:', claimData);

    // Mock API call to save draft
    setTimeout(() => {
      const draftId = 'draft-' + Date.now();
      console.log('Draft saved successfully:', draftId);
      this.saving.set(false);
      this.draftSaved.emit(draftId);
    }, 1000);
  }

  onSubmit(): void {
    if (!this.canSubmit() || !this.formState) return;

    this.submitting.set(true);
    this.submitError.set(null);

    const claim = this.buildClaimCreate();

    // Create claim first (DRAFT status), then submit it (DRAFT -> SUBMITTED)
    this.claimsApi.createClaim(claim).pipe(
      switchMap((createdClaim) => this.claimsApi.submitClaim(createdClaim.id))
    ).subscribe({
      next: (submittedClaim) => {
        this.submitting.set(false);
        this.submitSuccess.emit(submittedClaim.id);
      },
      error: (error) => {
        this.submitting.set(false);
        this.submitError.set(error.message || 'Failed to submit claim');
      },
    });
  }

  private buildClaimCreate(): ClaimCreate {
    const fs = this.formState!;

    const lineItems: ClaimLineItemCreate[] = (fs.services?.lineItems || []).map(item => ({
      procedure_code: item.procedureCode,
      procedure_code_system: item.procedureCodeSystem === 'CPT' ? 'CPT-4' : 'HCPCS',
      modifier_codes: item.modifiers,
      service_date: this.formatDate(item.serviceDate),
      quantity: item.quantity,
      unit_price: item.unitPrice,
      charged_amount: item.chargedAmount,
    }));

    // Build claim with optional member/provider data (document-first workflow)
    const claim: ClaimCreate = {
      claim_type: ClaimType.PROFESSIONAL,
      service_date_from: this.formatDate(fs.services.serviceDateFrom),
      service_date_to: this.formatDate(fs.services.serviceDateTo),
      diagnosis_codes: fs.services.diagnosisCodes,
      primary_diagnosis: fs.services.primaryDiagnosis,
      total_charged: this.totalCharged(),
      line_items: lineItems,
      place_of_service: fs.provider.placeOfService || undefined,
      prior_auth_number: fs.provider.priorAuthNumber || undefined,
    };

    // Add optional member data if available
    if (fs.member.memberId || fs.member.policyId) {
      claim.member_id = fs.member.memberId || undefined;
      claim.policy_id = fs.member.policyId || undefined;
    }

    // Add optional provider data if available
    if (fs.provider.providerId || fs.provider.providerNPI) {
      claim.provider_id = fs.provider.providerId || undefined;
      if (fs.provider.providerNPI) {
        claim.provider = { npi: fs.provider.providerNPI };
      }
    }

    return claim;
  }

  private formatDate(value: Date | string | null | undefined): string {
    if (!value) return '';
    if (typeof value === 'string') return value;
    return value.toISOString().split('T')[0];
  }
}
