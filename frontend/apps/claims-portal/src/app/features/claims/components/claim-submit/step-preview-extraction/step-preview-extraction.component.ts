/**
 * Step Preview Extraction Component.
 * Source: Design Document - 08-document-extraction-preview-step-design.md
 * Verified: 2025-12-22
 *
 * Third step of claim submission wizard - Preview extracted data before review.
 * Displays all extracted data on a single page with clear visual organization.
 * This step is READ-ONLY - no validation is executed here.
 */
import {
  Component,
  ChangeDetectionStrategy,
  input,
  output,
  computed,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { DividerModule } from 'primeng/divider';
import { MessageModule } from 'primeng/message';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { ChipModule } from 'primeng/chip';
import { PanelModule } from 'primeng/panel';

import {
  DocumentUploadState,
  MergedExtractedData,
} from '@claims-processing/models';
import { ConfidenceBadgeComponent } from '../../../../../shared/components/confidence-badge.component';

/**
 * Data structure for a preview field
 */
interface PreviewField {
  label: string;
  value: string | number | null | undefined;
  confidence?: number;
  source?: string;
  icon?: string;
}

/**
 * Data structure for diagnosis/procedure items
 */
interface CodeItem {
  code: string;
  description?: string;
  confidence?: number;
  isPrimary?: boolean;
  modifiers?: string[];
  quantity?: number;
  chargedAmount?: string;
  serviceDate?: string;
}

@Component({
  selector: 'app-step-preview-extraction',
  standalone: true,
  imports: [
    CommonModule,
    ButtonModule,
    CardModule,
    ChipModule,
    DividerModule,
    MessageModule,
    PanelModule,
    TagModule,
    TooltipModule,
    ConfidenceBadgeComponent,
  ],
  template: `
    <div class="extraction-preview">
      <!-- Header Section -->
      <div class="preview-header">
        <div class="header-left">
          <h2><i class="pi pi-file-check"></i> Extraction Preview</h2>
          <p class="subtitle">Review the data extracted from your documents</p>
        </div>
        <div class="header-right">
          <div class="confidence-display" [class]="getConfidenceClass(overallConfidence())">
            <span class="confidence-value">{{ formatPercent(overallConfidence()) }}</span>
            <span class="confidence-label">Overall Confidence</span>
          </div>
        </div>
      </div>

      <!-- Alerts Section -->
      @if (lowConfidenceCount() > 0) {
        <p-message
          severity="warn"
          styleClass="alert-message"
        >
          <ng-template pTemplate="content">
            <i class="pi pi-exclamation-triangle"></i>
            <span>{{ lowConfidenceCount() }} field(s) have low confidence and may need manual review</span>
          </ng-template>
        </p-message>
      }

      @if (!hasAnyData()) {
        <p-message
          severity="info"
          styleClass="alert-message"
        >
          <ng-template pTemplate="content">
            <i class="pi pi-info-circle"></i>
            <span>No data was extracted from the uploaded documents. You can add information manually in the next step.</span>
          </ng-template>
        </p-message>
      }

      <!-- Main Content - Single Page Layout -->
      <div class="extraction-content">
        <!-- Row 1: Patient & Provider -->
        <div class="content-row two-columns">
          <!-- Patient Information -->
          <div class="info-section patient-section">
            <div class="section-header">
              <div class="section-title">
                <i class="pi pi-user"></i>
                <h3>Patient Information</h3>
              </div>
              <app-confidence-badge
                [score]="patientConfidence()"
                label="Patient data confidence"
              />
            </div>
            <div class="section-body">
              @if (hasPatientData()) {
                <div class="info-grid">
                  @for (field of patientFields(); track field.label) {
                    <div class="info-item">
                      <span class="info-label">{{ field.label }}</span>
                      <span class="info-value" [class.empty]="!field.value">
                        {{ field.value || 'Not extracted' }}
                      </span>
                    </div>
                  }
                </div>
              } @else {
                <div class="no-data">
                  <i class="pi pi-inbox"></i>
                  <span>No patient information extracted</span>
                </div>
              }
            </div>
          </div>

          <!-- Provider Information -->
          <div class="info-section provider-section">
            <div class="section-header">
              <div class="section-title">
                <i class="pi pi-building"></i>
                <h3>Provider Information</h3>
              </div>
              <app-confidence-badge
                [score]="providerConfidence()"
                label="Provider data confidence"
              />
            </div>
            <div class="section-body">
              @if (hasProviderData()) {
                <div class="info-grid">
                  @for (field of providerFields(); track field.label) {
                    <div class="info-item">
                      <span class="info-label">{{ field.label }}</span>
                      <span class="info-value" [class.empty]="!field.value">
                        {{ field.value || 'Not extracted' }}
                      </span>
                    </div>
                  }
                </div>
              } @else {
                <div class="no-data">
                  <i class="pi pi-inbox"></i>
                  <span>No provider information extracted</span>
                </div>
              }
            </div>
          </div>
        </div>

        <!-- Row 2: Clinical Data (Diagnoses & Procedures) -->
        <div class="content-row">
          <div class="info-section clinical-section">
            <div class="section-header">
              <div class="section-title">
                <i class="pi pi-heart"></i>
                <h3>Clinical Information</h3>
              </div>
            </div>
            <div class="section-body clinical-body">
              <!-- Diagnoses Column -->
              <div class="clinical-column">
                <h4>
                  <i class="pi pi-tag"></i>
                  Diagnoses
                  <span class="count-badge">{{ diagnosisCodes().length }}</span>
                </h4>
                @if (diagnosisCodes().length > 0) {
                  <div class="code-list">
                    @for (dx of diagnosisCodes(); track dx.code; let i = $index) {
                      <div class="code-card" [class.primary]="dx.isPrimary">
                        <div class="code-header">
                          <span class="code-value">{{ dx.code }}</span>
                          @if (dx.isPrimary) {
                            <p-tag value="Primary" severity="info" styleClass="primary-tag"></p-tag>
                          }
                          @if (dx.confidence !== undefined) {
                            <app-confidence-badge [score]="dx.confidence" size="small" />
                          }
                        </div>
                        @if (dx.description) {
                          <div class="code-description">{{ dx.description }}</div>
                        }
                      </div>
                    }
                  </div>
                } @else {
                  <div class="no-data small">
                    <i class="pi pi-inbox"></i>
                    <span>No diagnoses extracted</span>
                  </div>
                }
              </div>

              <p-divider layout="vertical" styleClass="clinical-divider"></p-divider>

              <!-- Procedures Column -->
              <div class="clinical-column">
                <h4>
                  <i class="pi pi-list"></i>
                  Procedures
                  <span class="count-badge">{{ procedureCodes().length }}</span>
                </h4>
                @if (procedureCodes().length > 0) {
                  <div class="code-list">
                    @for (proc of procedureCodes(); track proc.code; let i = $index) {
                      <div class="code-card">
                        <div class="code-header">
                          <span class="code-value">{{ proc.code }}</span>
                          @if (proc.modifiers && proc.modifiers.length > 0) {
                            @for (mod of proc.modifiers; track mod) {
                              <p-tag [value]="mod" severity="secondary" styleClass="modifier-tag"></p-tag>
                            }
                          }
                          @if (proc.confidence !== undefined) {
                            <app-confidence-badge [score]="proc.confidence" size="small" />
                          }
                        </div>
                        @if (proc.description) {
                          <div class="code-description">{{ proc.description }}</div>
                        }
                        @if (proc.chargedAmount || proc.quantity || proc.serviceDate) {
                          <div class="code-details">
                            @if (proc.quantity) {
                              <span class="detail-item">
                                <i class="pi pi-hashtag"></i> Qty: {{ proc.quantity }}
                              </span>
                            }
                            @if (proc.chargedAmount) {
                              <span class="detail-item">
                                <i class="pi pi-dollar"></i> {{ proc.chargedAmount }}
                              </span>
                            }
                            @if (proc.serviceDate) {
                              <span class="detail-item">
                                <i class="pi pi-calendar"></i> {{ proc.serviceDate }}
                              </span>
                            }
                          </div>
                        }
                      </div>
                    }
                  </div>
                } @else {
                  <div class="no-data small">
                    <i class="pi pi-inbox"></i>
                    <span>No procedures extracted</span>
                  </div>
                }
              </div>
            </div>
          </div>
        </div>

        <!-- Row 3: Financial & Dates/Identifiers -->
        <div class="content-row two-columns">
          <!-- Financial Summary -->
          <div class="info-section financial-section">
            <div class="section-header">
              <div class="section-title">
                <i class="pi pi-dollar"></i>
                <h3>Financial Summary</h3>
              </div>
              <app-confidence-badge
                [score]="financialConfidence()"
                label="Financial data confidence"
              />
            </div>
            <div class="section-body">
              @if (hasFinancialData()) {
                <div class="financial-display">
                  <div class="total-amount">
                    <span class="amount-label">Total Charged</span>
                    <span class="amount-value">
                      {{ getCurrencySymbol() }}{{ financialTotal() }}
                    </span>
                    <span class="currency-code">{{ getCurrency() }}</span>
                  </div>
                </div>
              } @else {
                <div class="no-data">
                  <i class="pi pi-inbox"></i>
                  <span>No financial information extracted</span>
                </div>
              }
            </div>
          </div>

          <!-- Dates & Identifiers -->
          <div class="info-section dates-section">
            <div class="section-header">
              <div class="section-title">
                <i class="pi pi-calendar"></i>
                <h3>Dates & Identifiers</h3>
              </div>
            </div>
            <div class="section-body">
              <div class="info-grid">
                @for (field of datesAndIdentifiersFields(); track field.label) {
                  <div class="info-item">
                    <span class="info-label">{{ field.label }}</span>
                    <span class="info-value" [class.empty]="!field.value">
                      {{ field.value || 'Not extracted' }}
                    </span>
                  </div>
                }
              </div>
            </div>
          </div>
        </div>

        <!-- Row 4: Processed Documents -->
        <div class="content-row">
          <div class="info-section documents-section">
            <div class="section-header">
              <div class="section-title">
                <i class="pi pi-file"></i>
                <h3>Processed Documents</h3>
              </div>
              <span class="doc-count">{{ processedDocuments().length }} document(s)</span>
            </div>
            <div class="section-body">
              <div class="doc-list">
                @for (doc of processedDocuments(); track doc.id) {
                  <div class="doc-item">
                    <i class="pi pi-file-pdf"></i>
                    <span class="doc-name">{{ doc.filename }}</span>
                    <span class="doc-confidence" [class]="getConfidenceClass(doc.ocrConfidence || 0)">
                      OCR: {{ formatPercent(doc.ocrConfidence || 0) }}
                    </span>
                    <p-tag
                      value="Processed"
                      severity="success"
                      icon="pi pi-check"
                    ></p-tag>
                  </div>
                }
                @if (processedDocuments().length === 0) {
                  <div class="no-data small">
                    <i class="pi pi-inbox"></i>
                    <span>No documents processed</span>
                  </div>
                }
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Navigation Actions -->
      <div class="preview-actions">
        <p-button
          label="Back to Processing"
          icon="pi pi-arrow-left"
          styleClass="p-button-outlined p-button-secondary"
          (onClick)="onBack()"
        ></p-button>
        <p-button
          label="Continue to Review & Edit"
          icon="pi pi-arrow-right"
          iconPos="right"
          styleClass="p-button-primary"
          (onClick)="onContinue()"
        ></p-button>
      </div>
    </div>
  `,
  styles: [`
    .extraction-preview {
      padding: 0;
    }

    /* Header */
    .preview-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.5rem 2rem;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border-radius: 12px 12px 0 0;
      margin: -1rem -1rem 1.5rem -1rem;
    }

    .header-left h2 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .header-left .subtitle {
      margin: 0.5rem 0 0 0;
      opacity: 0.9;
      font-size: 0.95rem;
    }

    .confidence-display {
      text-align: center;
      padding: 1rem 1.5rem;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.15);
      backdrop-filter: blur(10px);
    }

    .confidence-display .confidence-value {
      display: block;
      font-size: 2rem;
      font-weight: 700;
      line-height: 1;
    }

    .confidence-display .confidence-label {
      display: block;
      font-size: 0.8rem;
      margin-top: 0.25rem;
      opacity: 0.9;
    }

    .confidence-display.high {
      background: rgba(76, 175, 80, 0.3);
    }

    .confidence-display.medium {
      background: rgba(255, 193, 7, 0.3);
    }

    .confidence-display.low {
      background: rgba(244, 67, 54, 0.3);
    }

    /* Alerts */
    :host ::ng-deep .alert-message {
      margin-bottom: 1.5rem;
    }

    :host ::ng-deep .alert-message .p-message-wrapper {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    /* Content Layout */
    .extraction-content {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .content-row {
      display: flex;
      gap: 1.5rem;
    }

    .content-row.two-columns > .info-section {
      flex: 1;
    }

    /* Info Sections */
    .info-section {
      background: white;
      border: 1px solid #e0e0e0;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem 1.25rem;
      background: #f8f9fa;
      border-bottom: 1px solid #e0e0e0;
    }

    .section-title {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .section-title i {
      font-size: 1.25rem;
      color: #667eea;
    }

    .section-title h3 {
      margin: 0;
      font-size: 1.1rem;
      font-weight: 600;
      color: #333;
    }

    .section-body {
      padding: 1.25rem;
    }

    /* Info Grid */
    .info-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;
    }

    .info-item {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .info-label {
      font-size: 0.8rem;
      font-weight: 500;
      color: #666;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .info-value {
      font-size: 1rem;
      color: #333;
      font-weight: 500;
    }

    .info-value.empty {
      color: #999;
      font-style: italic;
      font-weight: 400;
    }

    /* Clinical Section */
    .clinical-section {
      flex: 1;
    }

    .clinical-body {
      display: flex;
      gap: 1.5rem;
    }

    .clinical-column {
      flex: 1;
    }

    .clinical-column h4 {
      margin: 0 0 1rem 0;
      font-size: 1rem;
      font-weight: 600;
      color: #555;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .count-badge {
      background: #667eea;
      color: white;
      padding: 0.15rem 0.5rem;
      border-radius: 10px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    :host ::ng-deep .clinical-divider {
      margin: 0 !important;
    }

    .code-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .code-card {
      padding: 0.875rem;
      background: #f8f9fa;
      border-radius: 8px;
      border-left: 3px solid #e0e0e0;
      transition: all 0.2s ease;
    }

    .code-card:hover {
      background: #f0f0f0;
    }

    .code-card.primary {
      border-left-color: #2196F3;
      background: #e3f2fd;
    }

    .code-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex-wrap: wrap;
    }

    .code-value {
      font-family: 'Monaco', 'Menlo', monospace;
      font-weight: 700;
      font-size: 1rem;
      color: #333;
    }

    :host ::ng-deep .primary-tag {
      font-size: 0.65rem;
      padding: 0.15rem 0.4rem;
    }

    :host ::ng-deep .modifier-tag {
      font-size: 0.65rem;
      padding: 0.15rem 0.4rem;
    }

    .code-description {
      margin-top: 0.5rem;
      font-size: 0.9rem;
      color: #555;
    }

    .code-details {
      display: flex;
      gap: 1rem;
      margin-top: 0.5rem;
      padding-top: 0.5rem;
      border-top: 1px dashed #ddd;
    }

    .detail-item {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      font-size: 0.8rem;
      color: #666;
    }

    .detail-item i {
      font-size: 0.75rem;
    }

    /* Financial Section */
    .financial-display {
      display: flex;
      justify-content: center;
      padding: 1rem;
    }

    .total-amount {
      text-align: center;
    }

    .amount-label {
      display: block;
      font-size: 0.85rem;
      color: #666;
      margin-bottom: 0.5rem;
    }

    .amount-value {
      display: block;
      font-size: 2.5rem;
      font-weight: 700;
      color: #2e7d32;
      line-height: 1;
    }

    .currency-code {
      display: block;
      font-size: 0.9rem;
      color: #888;
      margin-top: 0.25rem;
    }

    /* Documents Section */
    .doc-count {
      font-size: 0.85rem;
      color: #666;
    }

    .doc-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .doc-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem 1rem;
      background: #f8f9fa;
      border-radius: 8px;
    }

    .doc-item i.pi-file-pdf {
      font-size: 1.5rem;
      color: #e53935;
    }

    .doc-name {
      flex: 1;
      font-weight: 500;
      color: #333;
    }

    .doc-confidence {
      font-size: 0.85rem;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
    }

    .doc-confidence.high {
      background: #e8f5e9;
      color: #2e7d32;
    }

    .doc-confidence.medium {
      background: #fff8e1;
      color: #f57f17;
    }

    .doc-confidence.low {
      background: #ffebee;
      color: #c62828;
    }

    /* No Data State */
    .no-data {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 2rem;
      color: #999;
      gap: 0.5rem;
    }

    .no-data i {
      font-size: 2rem;
      opacity: 0.5;
    }

    .no-data.small {
      padding: 1rem;
    }

    .no-data.small i {
      font-size: 1.25rem;
    }

    /* Actions */
    .preview-actions {
      display: flex;
      justify-content: space-between;
      margin-top: 2rem;
      padding-top: 1.5rem;
      border-top: 1px solid #e0e0e0;
    }

    /* Responsive */
    @media (max-width: 992px) {
      .content-row.two-columns {
        flex-direction: column;
      }

      .clinical-body {
        flex-direction: column;
      }

      :host ::ng-deep .clinical-divider {
        display: none;
      }

      .info-grid {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 768px) {
      .preview-header {
        flex-direction: column;
        text-align: center;
        gap: 1rem;
      }

      .preview-actions {
        flex-direction: column;
        gap: 1rem;
      }

      .preview-actions p-button {
        width: 100%;
      }

      :host ::ng-deep .preview-actions .p-button {
        width: 100%;
        justify-content: center;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StepPreviewExtractionComponent {
  /**
   * Merged extracted data from processing step
   */
  readonly mergedExtractedData = input<MergedExtractedData | null>(null);

  /**
   * Policy documents (processed)
   */
  readonly policyDocuments = input<DocumentUploadState[]>([]);

  /**
   * Claim documents (processed)
   */
  readonly claimDocuments = input<DocumentUploadState[]>([]);

  /**
   * Emitted when user wants to proceed to review
   */
  readonly stepComplete = output<void>();

  /**
   * Emitted when user wants to go back to processing
   */
  readonly stepBack = output<void>();

  // =========================================================================
  // Computed Properties
  // =========================================================================

  readonly overallConfidence = computed(() => {
    return this.mergedExtractedData()?.overall_confidence ?? 0;
  });

  readonly lowConfidenceCount = computed(() => {
    let count = 0;
    const data = this.mergedExtractedData();
    if (!data) return 0;

    // Check diagnoses
    data.diagnoses?.forEach(dx => {
      if (dx.confidence !== undefined && dx.confidence < 0.7) count++;
    });

    // Check procedures
    data.procedures?.forEach(proc => {
      if (proc.confidence !== undefined && proc.confidence < 0.7) count++;
    });

    return count;
  });

  readonly patientConfidence = computed(() => {
    return this.mergedExtractedData()?.overall_confidence ?? 0;
  });

  readonly providerConfidence = computed(() => {
    return this.mergedExtractedData()?.overall_confidence ?? 0;
  });

  readonly financialConfidence = computed(() => {
    return this.mergedExtractedData()?.overall_confidence ?? 0;
  });

  readonly patientFields = computed((): PreviewField[] => {
    const patient = this.mergedExtractedData()?.patient;
    if (!patient) return [];

    return [
      { label: 'Full Name', value: patient.name },
      { label: 'Member ID', value: patient.member_id },
      { label: 'Date of Birth', value: patient.date_of_birth },
      { label: 'Gender', value: patient.gender },
      { label: 'Address', value: patient.address },
    ].filter(f => f.value);
  });

  readonly providerFields = computed((): PreviewField[] => {
    const provider = this.mergedExtractedData()?.provider;
    if (!provider) return [];

    return [
      { label: 'Provider Name', value: provider.name },
      { label: 'NPI / License', value: provider.npi },
      { label: 'Tax ID', value: provider.tax_id },
      { label: 'Specialty', value: provider.specialty },
    ].filter(f => f.value);
  });

  readonly datesAndIdentifiersFields = computed((): PreviewField[] => {
    const data = this.mergedExtractedData();
    if (!data) return [];

    const fields: PreviewField[] = [];

    if (data.dates?.service_date_from) {
      fields.push({ label: 'Service Date From', value: data.dates.service_date_from });
    }
    if (data.dates?.service_date_to) {
      fields.push({ label: 'Service Date To', value: data.dates.service_date_to });
    }
    if (data.identifiers?.claim_number) {
      fields.push({ label: 'Claim Number', value: data.identifiers.claim_number });
    }
    if (data.identifiers?.policy_number) {
      fields.push({ label: 'Policy Number', value: data.identifiers.policy_number });
    }
    if (data.identifiers?.prior_auth_number) {
      fields.push({ label: 'Prior Auth #', value: data.identifiers.prior_auth_number });
    }

    return fields;
  });

  readonly diagnosisCodes = computed((): CodeItem[] => {
    const diagnoses = this.mergedExtractedData()?.diagnoses;
    if (!diagnoses) return [];

    return diagnoses.map((dx, index) => ({
      code: dx.code,
      description: dx.description,
      confidence: dx.confidence,
      isPrimary: dx.is_primary || index === 0,
    }));
  });

  readonly procedureCodes = computed((): CodeItem[] => {
    const data = this.mergedExtractedData();
    const procedures = data?.procedures || [];
    const lineItems = (data as any)?.line_items || [];

    // Map standard procedures
    const procedureItems = procedures.map(proc => ({
      code: proc.code,
      description: proc.description,
      confidence: proc.confidence,
      modifiers: proc.modifiers,
      quantity: proc.quantity,
      chargedAmount: proc.charged_amount,
      serviceDate: proc.service_date,
    }));

    // Map invoice line items (from hospital bills, invoices)
    const invoiceItems = lineItems.map((item: any) => ({
      code: item.sac_code || item.sl_no?.toString() || '',
      description: item.description,
      confidence: item.confidence,
      modifiers: [],
      quantity: item.quantity,
      chargedAmount: item.total_value || item.gross_value,
      serviceDate: item.date,
      category: item.category,
    }));

    // Return invoice items if present, otherwise procedures
    return invoiceItems.length > 0 ? invoiceItems : procedureItems;
  });

  readonly processedDocuments = computed(() => {
    const all = [...this.policyDocuments(), ...this.claimDocuments()];
    return all.filter(doc => doc.status === 'completed');
  });

  // =========================================================================
  // Helper Methods
  // =========================================================================

  hasPatientData(): boolean {
    const patient = this.mergedExtractedData()?.patient;
    return !!(patient?.name || patient?.member_id || patient?.date_of_birth);
  }

  hasProviderData(): boolean {
    const provider = this.mergedExtractedData()?.provider;
    return !!(provider?.name || provider?.npi);
  }

  hasFinancialData(): boolean {
    return !!this.mergedExtractedData()?.financial?.total_charged;
  }

  hasAnyData(): boolean {
    return this.hasPatientData() ||
           this.hasProviderData() ||
           this.hasFinancialData() ||
           this.diagnosisCodes().length > 0 ||
           this.procedureCodes().length > 0;
  }

  financialTotal(): string {
    return this.mergedExtractedData()?.financial?.total_charged || '0.00';
  }

  getCurrency(): string {
    return this.mergedExtractedData()?.financial?.currency || 'USD';
  }

  getCurrencySymbol(): string {
    const currency = this.getCurrency();
    switch (currency) {
      case 'USD': return '$';
      case 'EUR': return '€';
      case 'GBP': return '£';
      case 'AED': return 'AED ';
      default: return '';
    }
  }

  formatPercent(value: number): string {
    return `${Math.round(value * 100)}%`;
  }

  getConfidenceClass(confidence: number): string {
    if (confidence >= 0.85) return 'high';
    if (confidence >= 0.70) return 'medium';
    return 'low';
  }

  // =========================================================================
  // Event Handlers
  // =========================================================================

  onBack(): void {
    this.stepBack.emit();
  }

  onContinue(): void {
    this.stepComplete.emit();
  }
}
