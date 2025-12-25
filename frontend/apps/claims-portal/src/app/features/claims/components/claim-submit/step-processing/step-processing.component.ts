/**
 * Step Processing Component.
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Verified: 2025-12-19
 *
 * Fourth step of claim submission wizard - Document processing and data extraction.
 * Polls document status, displays progress, shows extracted data with editing.
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
  OnInit,
  OnDestroy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AccordionModule } from 'primeng/accordion';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { MessageModule } from 'primeng/message';
import { ProgressBarModule } from 'primeng/progressbar';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { DividerModule } from 'primeng/divider';
import { Subject, takeUntil } from 'rxjs';

import {
  DocumentUploadState,
  DocumentProcessingStatus,
  ExtractedDataResponse,
  ExtractedClaimData,
  MergedExtractedData,
  DataConflict,
  getProcessingStageLabel,
  getConfidenceSeverity,
  getDocumentTypeLabel,
  formatFileSize,
} from '@claims-processing/models';
import { DocumentStatusPollingService } from '../../../../../core/services/document-status-polling.service';

export interface ProcessingStepData {
  policyDocuments: DocumentUploadState[];
  claimDocuments: DocumentUploadState[];
  mergedData: MergedExtractedData | null;
  allProcessed: boolean;
}

interface EditableField {
  key: string;
  label: string;
  value: string | number;
  originalValue: string | number;
  confidence: number;
  source: string;
  edited: boolean;
}

@Component({
  selector: 'app-step-processing',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    AccordionModule,
    ButtonModule,
    CardModule,
    InputTextModule,
    InputNumberModule,
    MessageModule,
    ProgressBarModule,
    TagModule,
    TooltipModule,
    DividerModule,
  ],
  template: `
    <div class="step-processing">
      <h3>Step 4: Document Processing</h3>
      <p class="step-description">
        Your documents are being processed. Extracted data will appear below for review and editing.
      </p>

      <!-- Overall Progress -->
      <div class="overall-progress">
        <div class="progress-header">
          <span>Overall Progress</span>
          <span class="progress-text">{{ processedCount() }} of {{ totalDocuments() }} documents</span>
        </div>
        <p-progressBar
          [value]="overallProgress()"
          [showValue]="true"
          styleClass="overall-progress-bar"
        ></p-progressBar>
      </div>

      <!-- Document Processing Status -->
      <div class="documents-section">
        <h4>Document Status</h4>

        @for (doc of allDocuments(); track doc.id) {
          <p-card styleClass="document-card">
            <div class="document-row">
              <div class="doc-icon">
                <i class="pi pi-file-pdf"></i>
              </div>

              <div class="doc-info">
                <span class="doc-name">{{ doc.filename }}</span>
                <span class="doc-meta">
                  {{ getDocumentTypeLabel(doc.documentType) }} · {{ formatFileSize(doc.fileSize) }}
                </span>
              </div>

              <div class="doc-status">
                @if (doc.status === 'processing' || doc.status === 'uploading') {
                  <div class="processing-info">
                    <span class="stage-label">{{ getStageLabel(doc) }}</span>
                    <p-progressBar
                      [value]="getDocProgress(doc)"
                      [showValue]="false"
                      styleClass="doc-progress-bar"
                    ></p-progressBar>
                  </div>
                } @else if (doc.status === 'completed') {
                  <p-tag value="Completed" severity="success" icon="pi pi-check"></p-tag>
                  @if (doc.ocrConfidence) {
                    <span class="confidence-badge" [pTooltip]="'OCR Confidence'">
                      {{ (doc.ocrConfidence * 100).toFixed(0) }}%
                    </span>
                  }
                } @else if (doc.status === 'failed') {
                  <p-tag value="Failed" severity="danger" icon="pi pi-times"></p-tag>
                  @if (doc.error) {
                    <span class="error-text">{{ doc.error }}</span>
                  }
                } @else {
                  <p-tag value="Pending" severity="secondary"></p-tag>
                }
              </div>
            </div>
          </p-card>
        }
      </div>

      <!-- Extracted Data Section -->
      @if (hasExtractedData()) {
        <div class="extracted-data-section">
          <h4>
            Extracted Data
            @if (needsReview()) {
              <p-tag value="Needs Review" severity="warn" styleClass="ml-2"></p-tag>
            }
          </h4>

          @if (validationIssues().length > 0) {
            <div class="validation-issues">
              @for (issue of validationIssues(); track issue) {
                <p-message severity="warn" [text]="issue" styleClass="w-full"></p-message>
              }
            </div>
          }

          <!-- Data Conflicts -->
          @if (conflicts().length > 0) {
            <p-card header="Data Conflicts" styleClass="conflicts-card">
              <p class="conflicts-info">
                Multiple documents contained different values for these fields. Please review and confirm.
              </p>
              @for (conflict of conflicts(); track conflict.field) {
                <div class="conflict-item">
                  <span class="conflict-field">{{ conflict.field }}</span>
                  <div class="conflict-values">
                    @for (val of conflict.values; track val.documentId) {
                      <span
                        class="conflict-value"
                        [class.selected]="conflict.resolvedValue === val.value"
                        (click)="resolveConflict(conflict, val.value, val.documentId)"
                      >
                        {{ val.value }} ({{ (val.confidence * 100).toFixed(0) }}%)
                      </span>
                    }
                  </div>
                </div>
              }
            </p-card>
          }

          <!-- Editable Fields Accordion -->
          <p-accordion [multiple]="true">
            <!-- Patient Information -->
            <p-accordionTab header="Patient Information">
              <div class="field-grid">
                @for (field of patientFields(); track field.key) {
                  <div class="editable-field">
                    <label [for]="field.key">{{ field.label }}</label>
                    <div class="field-input-wrapper">
                      <input
                        pInputText
                        [id]="field.key"
                        [(ngModel)]="field.value"
                        (ngModelChange)="onFieldEdit(field)"
                        [class.edited]="field.edited"
                      />
                      <p-tag
                        [value]="(field.confidence * 100).toFixed(0) + '%'"
                        [severity]="getConfidenceSeverity(field.confidence)"
                        styleClass="confidence-tag"
                        [pTooltip]="'Extraction confidence'"
                      ></p-tag>
                    </div>
                    @if (field.edited) {
                      <button
                        pButton
                        type="button"
                        icon="pi pi-undo"
                        class="p-button-text p-button-sm"
                        pTooltip="Restore original"
                        (click)="restoreField(field)"
                      ></button>
                    }
                  </div>
                }
              </div>
            </p-accordionTab>

            <!-- Provider Information -->
            <p-accordionTab header="Provider Information">
              <div class="field-grid">
                @for (field of providerFields(); track field.key) {
                  <div class="editable-field">
                    <label [for]="field.key">{{ field.label }}</label>
                    <div class="field-input-wrapper">
                      <input
                        pInputText
                        [id]="field.key"
                        [(ngModel)]="field.value"
                        (ngModelChange)="onFieldEdit(field)"
                        [class.edited]="field.edited"
                      />
                      <p-tag
                        [value]="(field.confidence * 100).toFixed(0) + '%'"
                        [severity]="getConfidenceSeverity(field.confidence)"
                        styleClass="confidence-tag"
                      ></p-tag>
                    </div>
                    @if (field.edited) {
                      <button
                        pButton
                        type="button"
                        icon="pi pi-undo"
                        class="p-button-text p-button-sm"
                        (click)="restoreField(field)"
                      ></button>
                    }
                  </div>
                }
              </div>
            </p-accordionTab>

            <!-- Diagnosis Codes -->
            <p-accordionTab header="Diagnosis Codes">
              @if (mergedData()?.diagnoses?.length) {
                <div class="codes-list">
                  @for (diag of mergedData()!.diagnoses; track diag.code; let i = $index) {
                    <div class="code-item">
                      <span class="code-value">{{ diag.code }}</span>
                      <span class="code-description">{{ diag.description }}</span>
                      @if (diag.is_primary) {
                        <p-tag value="Primary" severity="info" styleClass="ml-2"></p-tag>
                      }
                      <p-tag
                        [value]="(diag.confidence * 100).toFixed(0) + '%'"
                        [severity]="getConfidenceSeverity(diag.confidence)"
                        styleClass="ml-auto"
                      ></p-tag>
                    </div>
                  }
                </div>
              } @else {
                <p class="no-data">No diagnosis codes extracted</p>
              }
            </p-accordionTab>

            <!-- Procedure Codes (CPT/HCPCS) -->
            <p-accordionTab header="Procedure Codes">
              @if (mergedData()?.procedures?.length) {
                <div class="codes-list">
                  @for (proc of mergedData()!.procedures; track proc.code; let i = $index) {
                    <div class="code-item procedure">
                      <div class="proc-main">
                        <span class="code-value">{{ proc.code }}</span>
                        <span class="code-description">{{ proc.description }}</span>
                      </div>
                      <div class="proc-details">
                        <span>Qty: {{ proc.quantity }}</span>
                        <span>Date: {{ proc.service_date }}</span>
                        <span>Charged: {{ proc.charged_amount }}</span>
                      </div>
                      <p-tag
                        [value]="(proc.confidence * 100).toFixed(0) + '%'"
                        [severity]="getConfidenceSeverity(proc.confidence)"
                      ></p-tag>
                    </div>
                  }
                </div>
              } @else {
                <p class="no-data">No CPT/HCPCS procedure codes extracted</p>
              }
            </p-accordionTab>

            <!-- Services & Line Items (from invoices/hospital bills) -->
            <p-accordionTab header="Services & Line Items">
              @if (lineItems().length > 0) {
                <div class="line-items-table">
                  <table class="items-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Description</th>
                        <th>Category</th>
                        <th>Code</th>
                        <th>Qty</th>
                        <th>Rate</th>
                        <th>Total</th>
                        <th>Conf.</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (item of lineItems(); track item.sl_no; let i = $index) {
                        <tr>
                          <td>{{ item.sl_no || i + 1 }}</td>
                          <td class="description-cell">{{ item.description }}</td>
                          <td>
                            <p-tag
                              [value]="item.category || 'Services'"
                              [severity]="getCategorySeverity(item.category)"
                              styleClass="category-tag"
                            ></p-tag>
                          </td>
                          <td class="code-cell">{{ item.sac_code || '-' }}</td>
                          <td>{{ item.quantity }}</td>
                          <td>{{ item.rate || '-' }}</td>
                          <td class="total-cell">{{ item.total_value }}</td>
                          <td>
                            <p-tag
                              [value]="((item.confidence || 0.8) * 100).toFixed(0) + '%'"
                              [severity]="getConfidenceSeverity(item.confidence || 0.8)"
                              styleClass="conf-tag"
                            ></p-tag>
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                  <div class="items-summary">
                    <span class="items-count">{{ lineItems().length }} item(s)</span>
                    <span class="items-total">Total: {{ calculateLineItemsTotal() }}</span>
                  </div>
                </div>
              } @else {
                <p class="no-data">No services or line items extracted from invoice</p>
              }
            </p-accordionTab>

            <!-- Financial Information -->
            <p-accordionTab header="Financial Information">
              <div class="field-grid">
                @for (field of financialFields(); track field.key) {
                  <div class="editable-field">
                    <label [for]="field.key">{{ field.label }}</label>
                    <div class="field-input-wrapper">
                      <input
                        pInputText
                        [id]="field.key"
                        [(ngModel)]="field.value"
                        (ngModelChange)="onFieldEdit(field)"
                        [class.edited]="field.edited"
                      />
                      <p-tag
                        [value]="(field.confidence * 100).toFixed(0) + '%'"
                        [severity]="getConfidenceSeverity(field.confidence)"
                        styleClass="confidence-tag"
                      ></p-tag>
                    </div>
                    @if (field.edited) {
                      <button
                        pButton
                        type="button"
                        icon="pi pi-undo"
                        class="p-button-text p-button-sm"
                        (click)="restoreField(field)"
                      ></button>
                    }
                  </div>
                }
              </div>
            </p-accordionTab>
          </p-accordion>
        </div>
      }

      <!-- Processing Error -->
      @if (processingError()) {
        <p-message
          severity="error"
          [text]="processingError()!"
          styleClass="w-full mt-3"
        ></p-message>
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

        <button
          pButton
          type="button"
          label="Continue to Review"
          icon="pi pi-arrow-right"
          iconPos="right"
          [disabled]="!canProceed()"
          [loading]="isProcessing()"
          (click)="onNext()"
        ></button>
      </div>
    </div>
  `,
  styles: [`
    .step-processing {
      padding: 1rem;
    }

    .step-description {
      color: #6c757d;
      margin-bottom: 1.5rem;
    }

    .overall-progress {
      background: #f8f9fa;
      padding: 1rem;
      border-radius: 8px;
      margin-bottom: 1.5rem;
    }

    .progress-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 0.5rem;
      font-weight: 500;
    }

    .progress-text {
      color: #6c757d;
      font-size: 0.9rem;
    }

    :host ::ng-deep .overall-progress-bar .p-progressbar {
      height: 1rem;
    }

    .documents-section {
      margin-bottom: 2rem;
    }

    .documents-section h4 {
      margin-bottom: 1rem;
      color: #495057;
    }

    .document-card {
      margin-bottom: 0.75rem;
    }

    :host ::ng-deep .document-card .p-card-body {
      padding: 0.75rem 1rem;
    }

    .document-row {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .doc-icon {
      font-size: 1.5rem;
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
      font-size: 0.85rem;
      color: #6c757d;
    }

    .doc-status {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex-shrink: 0;
    }

    .processing-info {
      width: 200px;
    }

    .stage-label {
      display: block;
      font-size: 0.8rem;
      color: #6c757d;
      margin-bottom: 0.25rem;
    }

    :host ::ng-deep .doc-progress-bar .p-progressbar {
      height: 0.5rem;
    }

    .confidence-badge {
      background: #e9ecef;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.8rem;
    }

    .error-text {
      color: #dc3545;
      font-size: 0.85rem;
    }

    .extracted-data-section {
      margin-top: 2rem;
    }

    .extracted-data-section h4 {
      display: flex;
      align-items: center;
      margin-bottom: 1rem;
    }

    .validation-issues {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }

    .conflicts-card {
      margin-bottom: 1rem;
      border-left: 4px solid #ffc107;
    }

    .conflicts-info {
      color: #6c757d;
      margin-bottom: 1rem;
    }

    .conflict-item {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 0.5rem 0;
      border-bottom: 1px solid #e9ecef;
    }

    .conflict-item:last-child {
      border-bottom: none;
    }

    .conflict-field {
      font-weight: 500;
      min-width: 150px;
    }

    .conflict-values {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }

    .conflict-value {
      padding: 0.25rem 0.75rem;
      background: #f8f9fa;
      border: 1px solid #dee2e6;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.2s;
    }

    .conflict-value:hover {
      background: #e9ecef;
    }

    .conflict-value.selected {
      background: #0d6efd;
      color: white;
      border-color: #0d6efd;
    }

    .field-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 1rem;
    }

    .editable-field {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .editable-field label {
      font-weight: 500;
      font-size: 0.9rem;
      color: #495057;
    }

    .field-input-wrapper {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .field-input-wrapper input {
      flex: 1;
    }

    .field-input-wrapper input.edited {
      border-color: #ffc107;
      background: #fffbea;
    }

    :host ::ng-deep .confidence-tag {
      font-size: 0.75rem;
      padding: 0.25rem 0.5rem;
    }

    .codes-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .code-item {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 0.75rem;
      background: #f8f9fa;
      border-radius: 4px;
    }

    .code-item.procedure {
      flex-direction: column;
      align-items: flex-start;
    }

    .proc-main {
      display: flex;
      gap: 1rem;
      width: 100%;
    }

    .proc-details {
      display: flex;
      gap: 1rem;
      font-size: 0.85rem;
      color: #6c757d;
    }

    .code-value {
      font-family: monospace;
      font-weight: 600;
      background: #e9ecef;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
    }

    .code-description {
      flex: 1;
    }

    .no-data {
      color: #6c757d;
      font-style: italic;
    }

    /* Line Items Table Styles */
    .line-items-table {
      overflow-x: auto;
    }

    .items-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }

    .items-table th {
      background: #f8f9fa;
      padding: 0.75rem 0.5rem;
      text-align: left;
      font-weight: 600;
      border-bottom: 2px solid #dee2e6;
      white-space: nowrap;
    }

    .items-table td {
      padding: 0.5rem;
      border-bottom: 1px solid #e9ecef;
      vertical-align: middle;
    }

    .items-table tbody tr:hover {
      background: #f8f9fa;
    }

    .description-cell {
      max-width: 250px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .code-cell {
      font-family: monospace;
      font-weight: 500;
    }

    .total-cell {
      font-weight: 600;
      color: #28a745;
    }

    :host ::ng-deep .category-tag {
      font-size: 0.7rem;
      padding: 0.2rem 0.4rem;
    }

    :host ::ng-deep .conf-tag {
      font-size: 0.7rem;
      padding: 0.2rem 0.4rem;
    }

    .items-summary {
      display: flex;
      justify-content: space-between;
      padding: 1rem;
      background: #f8f9fa;
      border-top: 2px solid #dee2e6;
      margin-top: 0.5rem;
      border-radius: 0 0 4px 4px;
    }

    .items-count {
      color: #6c757d;
    }

    .items-total {
      font-weight: 700;
      color: #28a745;
      font-size: 1.1rem;
    }

    .step-navigation {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 2rem;
      padding-top: 1rem;
      border-top: 1px solid #dee2e6;
    }

    @media (max-width: 768px) {
      .document-row {
        flex-wrap: wrap;
      }

      .doc-status {
        width: 100%;
        justify-content: flex-end;
      }

      .processing-info {
        width: 100%;
      }

      .field-grid {
        grid-template-columns: 1fr;
      }

      .conflict-item {
        flex-direction: column;
        align-items: flex-start;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StepProcessingComponent implements OnInit, OnDestroy {
  private readonly pollingService = inject(DocumentStatusPollingService);
  private readonly destroy$ = new Subject<void>();

  @Input() policyDocuments: DocumentUploadState[] = [];
  @Input() claimDocuments: DocumentUploadState[] = [];

  @Output() stepComplete = new EventEmitter<ProcessingStepData>();
  @Output() stepBack = new EventEmitter<void>();

  // State
  readonly documentStatuses = signal<Map<string, DocumentProcessingStatus>>(new Map());
  readonly extractedDataMap = signal<Map<string, ExtractedDataResponse>>(new Map());
  readonly mergedData = signal<MergedExtractedData | null>(null);
  readonly processingError = signal<string | null>(null);
  readonly isProcessing = signal<boolean>(false);

  // Editable fields
  readonly patientFields = signal<EditableField[]>([]);
  readonly providerFields = signal<EditableField[]>([]);
  readonly financialFields = signal<EditableField[]>([]);

  // Computed
  readonly allDocuments = computed(() => [
    ...this.policyDocuments,
    ...this.claimDocuments,
  ].map(doc => this.getUpdatedDocument(doc)));

  readonly totalDocuments = computed(() =>
    this.policyDocuments.length + this.claimDocuments.length
  );

  readonly processedCount = computed(() => {
    const statuses = this.documentStatuses();
    let count = 0;
    statuses.forEach(status => {
      if (status.status === 'completed' || status.status === 'failed') {
        count++;
      }
    });
    return count;
  });

  readonly overallProgress = computed(() => {
    const total = this.totalDocuments();
    if (total === 0) return 100;

    let totalProgress = 0;
    const statuses = this.documentStatuses();

    this.allDocuments().forEach(doc => {
      if (doc.documentId) {
        const status = statuses.get(doc.documentId);
        if (status) {
          totalProgress += status.progress_percent;
        }
      }
    });

    return Math.round(totalProgress / total);
  });

  readonly hasExtractedData = computed(() =>
    this.mergedData() !== null
  );

  readonly needsReview = computed(() =>
    this.mergedData()?.conflicts.some(c => c.requiresReview) ?? false
  );

  readonly validationIssues = computed(() => {
    const issues: string[] = [];
    this.extractedDataMap().forEach(data => {
      issues.push(...data.validation_issues);
    });
    return [...new Set(issues)];
  });

  readonly conflicts = computed(() =>
    this.mergedData()?.conflicts ?? []
  );

  /**
   * Get line items from merged data.
   * Line items include medications, supplies, services from invoices/hospital bills.
   * Items without a category are assigned 'Services' as default.
   */
  readonly lineItems = computed(() => {
    const data = this.mergedData();
    if (!data) return [];

    // Access line_items from the merged data (may be on the data object)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const items = (data as any).line_items || [];

    // Ensure each item has a category, default to 'Services' if not classified
    return items.map((item: any) => ({
      ...item,
      category: item.category || 'Services',
    }));
  });

  readonly canProceed = computed(() => {
    const processed = this.processedCount();
    const total = this.totalDocuments();

    // All documents must be processed
    if (processed < total) return false;

    // Must have extracted data or all failed
    const allFailed = this.allDocuments().every(d => d.status === 'failed');
    if (!allFailed && !this.hasExtractedData()) return false;

    // No unresolved conflicts requiring review
    const unresolvedConflicts = this.conflicts().filter(c => c.requiresReview && !c.resolvedValue);
    if (unresolvedConflicts.length > 0) return false;

    return true;
  });

  ngOnInit(): void {
    this.startPolling();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.pollingService.stopAllPolling();
  }

  private startPolling(): void {
    const documentIds = this.allDocuments()
      .filter(d => d.documentId)
      .map(d => d.documentId!);

    if (documentIds.length === 0) {
      return;
    }

    this.isProcessing.set(true);

    this.pollingService.pollMultiple(documentIds)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (statuses) => {
          this.documentStatuses.set(statuses);
          this.checkProcessingComplete(statuses);
        },
        error: () => {
          this.processingError.set('Failed to poll document status. Please try again.');
          this.isProcessing.set(false);
        },
      });
  }

  private checkProcessingComplete(statuses: Map<string, DocumentProcessingStatus>): void {
    const allComplete = Array.from(statuses.values()).every(
      s => s.status === 'completed' || s.status === 'failed'
    );

    if (allComplete) {
      this.isProcessing.set(false);
      this.fetchExtractedData();
    }
  }

  private fetchExtractedData(): void {
    const completedIds = Array.from(this.documentStatuses().entries())
      .filter(([_, status]) => status.status === 'completed')
      .map(([id]) => id);

    if (completedIds.length === 0) {
      return;
    }

    this.pollingService.getMultipleExtractedData(completedIds)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (responses) => {
          const dataMap = new Map<string, ExtractedDataResponse>();
          responses.forEach(r => dataMap.set(r.document_id, r));
          this.extractedDataMap.set(dataMap);
          this.mergeExtractedData(responses);
        },
        error: () => {
          this.processingError.set('Failed to fetch extracted data.');
        },
      });
  }

  private mergeExtractedData(responses: ExtractedDataResponse[]): void {
    if (responses.length === 0) {
      return;
    }

    // Use first response as base, detect conflicts
    const base = responses[0].data;
    const conflicts: DataConflict[] = [];
    const fieldSources: Record<string, string> = {};

    // Helper to find conflicts
    const checkConflict = (field: string, getValue: (data: ExtractedClaimData) => unknown) => {
      const values = responses.map(r => ({
        documentId: r.document_id,
        value: getValue(r.data),
        confidence: r.extraction_confidence,
      })).filter(v => v.value);

      const uniqueValues = new Set(values.map(v => JSON.stringify(v.value)));
      if (uniqueValues.size > 1) {
        // Find highest confidence value
        const sorted = values.sort((a, b) => b.confidence - a.confidence);
        conflicts.push({
          field,
          values,
          resolvedValue: sorted[0].value,
          resolvedFrom: sorted[0].documentId,
          requiresReview: sorted[0].confidence < 0.85,
        });
      } else if (values.length > 0) {
        fieldSources[field] = values[0].documentId;
      }
    };

    // Check patient fields
    checkConflict('Patient Name', d => d.patient.name);
    checkConflict('Member ID', d => d.patient.member_id);
    checkConflict('Date of Birth', d => d.patient.date_of_birth);

    // Check provider fields
    checkConflict('Provider Name', d => d.provider.name);
    checkConflict('Provider NPI', d => d.provider.npi);

    // Create merged data
    const merged: MergedExtractedData = {
      ...base,
      conflicts,
      fieldSources,
    };

    this.mergedData.set(merged);
    this.initializeEditableFields(merged);
  }

  private initializeEditableFields(data: MergedExtractedData): void {
    const defaultConfidence = data.overall_confidence;

    this.patientFields.set([
      { key: 'patient_name', label: 'Patient Name', value: data.patient.name, originalValue: data.patient.name, confidence: defaultConfidence, source: '', edited: false },
      { key: 'member_id', label: 'Member ID', value: data.patient.member_id, originalValue: data.patient.member_id, confidence: defaultConfidence, source: '', edited: false },
      { key: 'date_of_birth', label: 'Date of Birth', value: data.patient.date_of_birth, originalValue: data.patient.date_of_birth, confidence: defaultConfidence, source: '', edited: false },
      { key: 'gender', label: 'Gender', value: data.patient.gender, originalValue: data.patient.gender, confidence: defaultConfidence, source: '', edited: false },
      { key: 'address', label: 'Address', value: data.patient.address, originalValue: data.patient.address, confidence: defaultConfidence, source: '', edited: false },
    ]);

    this.providerFields.set([
      { key: 'provider_name', label: 'Provider Name', value: data.provider.name, originalValue: data.provider.name, confidence: defaultConfidence, source: '', edited: false },
      { key: 'provider_npi', label: 'NPI', value: data.provider.npi, originalValue: data.provider.npi, confidence: defaultConfidence, source: '', edited: false },
      { key: 'tax_id', label: 'Tax ID', value: data.provider.tax_id, originalValue: data.provider.tax_id, confidence: defaultConfidence, source: '', edited: false },
      { key: 'specialty', label: 'Specialty', value: data.provider.specialty, originalValue: data.provider.specialty, confidence: defaultConfidence, source: '', edited: false },
    ]);

    this.financialFields.set([
      { key: 'total_charged', label: 'Total Charged', value: data.financial.total_charged, originalValue: data.financial.total_charged, confidence: defaultConfidence, source: '', edited: false },
      { key: 'currency', label: 'Currency', value: data.financial.currency, originalValue: data.financial.currency, confidence: defaultConfidence, source: '', edited: false },
    ]);
  }

  private getUpdatedDocument(doc: DocumentUploadState): DocumentUploadState {
    if (!doc.documentId) {
      return doc;
    }

    const status = this.documentStatuses().get(doc.documentId);
    if (!status) {
      return doc;
    }

    return {
      ...doc,
      status: status.status,
      progressPercent: status.progress_percent,
      processingStage: status.processing_stage,
      ocrConfidence: status.ocr_confidence,
      parsingConfidence: status.parsing_confidence,
      error: status.error,
      needsReview: status.needs_review,
    };
  }

  getDocProgress(doc: DocumentUploadState): number {
    if (!doc.documentId) {
      return 0;
    }
    const status = this.documentStatuses().get(doc.documentId);
    return status?.progress_percent ?? doc.progressPercent;
  }

  getStageLabel(doc: DocumentUploadState): string {
    if (!doc.documentId) {
      return 'Waiting...';
    }
    const status = this.documentStatuses().get(doc.documentId);
    if (status?.processing_stage) {
      return getProcessingStageLabel(status.processing_stage);
    }
    return 'Processing...';
  }

  resolveConflict(conflict: DataConflict, value: unknown, sourceId: string): void {
    const merged = this.mergedData();
    if (!merged) return;

    const updatedConflicts = merged.conflicts.map(c =>
      c.field === conflict.field
        ? { ...c, resolvedValue: value, resolvedFrom: sourceId, requiresReview: false }
        : c
    );

    this.mergedData.set({
      ...merged,
      conflicts: updatedConflicts,
    });
  }

  onFieldEdit(field: EditableField): void {
    field.edited = field.value !== field.originalValue;
  }

  restoreField(field: EditableField): void {
    field.value = field.originalValue;
    field.edited = false;
  }

  onBack(): void {
    this.pollingService.stopAllPolling();
    this.stepBack.emit();
  }

  onNext(): void {
    if (!this.canProceed()) {
      return;
    }

    // Apply field edits to merged data
    const merged = this.applyFieldEdits();

    this.stepComplete.emit({
      policyDocuments: this.policyDocuments.map(d => this.getUpdatedDocument(d)),
      claimDocuments: this.claimDocuments.map(d => this.getUpdatedDocument(d)),
      mergedData: merged,
      allProcessed: true,
    });
  }

  private applyFieldEdits(): MergedExtractedData | null {
    const merged = this.mergedData();
    if (!merged) return null;

    // Apply patient field edits
    const patientEdits = this.patientFields();
    const patient = { ...merged.patient };
    patientEdits.forEach(f => {
      if (f.edited) {
        switch (f.key) {
          case 'patient_name': patient.name = f.value as string; break;
          case 'member_id': patient.member_id = f.value as string; break;
          case 'date_of_birth': patient.date_of_birth = f.value as string; break;
          case 'gender': patient.gender = f.value as string; break;
          case 'address': patient.address = f.value as string; break;
        }
      }
    });

    // Apply provider field edits
    const providerEdits = this.providerFields();
    const provider = { ...merged.provider };
    providerEdits.forEach(f => {
      if (f.edited) {
        switch (f.key) {
          case 'provider_name': provider.name = f.value as string; break;
          case 'provider_npi': provider.npi = f.value as string; break;
          case 'tax_id': provider.tax_id = f.value as string; break;
          case 'specialty': provider.specialty = f.value as string; break;
        }
      }
    });

    // Apply financial field edits
    const financialEdits = this.financialFields();
    const financial = { ...merged.financial };
    financialEdits.forEach(f => {
      if (f.edited) {
        switch (f.key) {
          case 'total_charged': financial.total_charged = f.value as string; break;
          case 'currency': financial.currency = f.value as string; break;
        }
      }
    });

    return {
      ...merged,
      patient,
      provider,
      financial,
    };
  }

  // Utility methods for template
  getDocumentTypeLabel = getDocumentTypeLabel;
  formatFileSize = formatFileSize;
  getConfidenceSeverity = getConfidenceSeverity;

  /**
   * Get severity color for category tags.
   * Categorizes items by type for visual distinction.
   */
  getCategorySeverity(category: string | undefined): 'success' | 'info' | 'warn' | 'secondary' {
    if (!category) return 'secondary';

    const normalizedCategory = category.toLowerCase();

    // Pharmacy/Medications - green
    if (normalizedCategory.includes('pharma') ||
        normalizedCategory.includes('medic') ||
        normalizedCategory.includes('drug') ||
        normalizedCategory.includes('injection')) {
      return 'success';
    }

    // Inventory/Supplies - blue
    if (normalizedCategory.includes('inventory') ||
        normalizedCategory.includes('supply') ||
        normalizedCategory.includes('consumable')) {
      return 'info';
    }

    // Fees/Charges - warning
    if (normalizedCategory.includes('fee') ||
        normalizedCategory.includes('charge') ||
        normalizedCategory.includes('surgeon') ||
        normalizedCategory.includes('doctor')) {
      return 'warn';
    }

    // Default for Services and others
    return 'secondary';
  }

  /**
   * Calculate total of all line items.
   */
  calculateLineItemsTotal(): string {
    const items = this.lineItems();
    if (items.length === 0) return '0.00';

    const total = items.reduce((sum: number, item: any) => {
      const value = parseFloat(item.total_value || item.gross_value || '0') || 0;
      return sum + value;
    }, 0);

    return total.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
}
