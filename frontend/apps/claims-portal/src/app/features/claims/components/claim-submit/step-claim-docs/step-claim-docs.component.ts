/**
 * Step Claim Documents Component.
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Verified: 2025-12-19
 *
 * Third step of claim submission wizard - Upload claim documents (PDFs).
 * Supports multiple file upload with document type selection.
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
  OnDestroy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FileUploadModule } from 'primeng/fileupload';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { MessageModule } from 'primeng/message';
import { ProgressBarModule } from 'primeng/progressbar';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { DropdownModule } from 'primeng/dropdown';
import { Subject } from 'rxjs';

import {
  DocumentUploadState,
  DocumentType,
  validatePdfFile,
  createDocumentUploadState,
  formatFileSize,
  getDocumentStatusSeverity,
  getDocumentTypeLabel,
} from '@claims-processing/models';
import { DocumentUploadService } from '../../../../../core/services/document-upload.service';

export interface ClaimDocsStepData {
  documents: DocumentUploadState[];
}

interface DocumentTypeOption {
  label: string;
  value: DocumentType;
}

@Component({
  selector: 'app-step-claim-docs',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    FileUploadModule,
    ButtonModule,
    CardModule,
    MessageModule,
    ProgressBarModule,
    TagModule,
    TooltipModule,
    DropdownModule,
  ],
  template: `
    <div class="step-claim-docs">
      <h3>Step 3: Claim Documents</h3>
      <p class="step-description">
        Upload claim-related documents (PDF format). These will be automatically processed to extract claim data.
        <span class="required-note">At least one claim document is required.</span>
      </p>

      <!-- Document Type Selection -->
      <div class="type-selector">
        <label for="docType">Document Type:</label>
        <p-dropdown
          id="docType"
          [options]="documentTypeOptions"
          [(ngModel)]="selectedDocType"
          optionLabel="label"
          optionValue="value"
          placeholder="Select document type"
          styleClass="type-dropdown"
        ></p-dropdown>
      </div>

      <!-- File Upload -->
      <div class="upload-section">
        <p-fileUpload
          #fileUpload
          name="claimDocs[]"
          [multiple]="true"
          accept=".pdf,application/pdf"
          [maxFileSize]="52428800"
          [customUpload]="true"
          (uploadHandler)="onFilesSelected($event)"
          (onSelect)="onFilesSelected($event)"
          [showUploadButton]="false"
          [showCancelButton]="false"
          styleClass="claim-upload"
        >
          <ng-template pTemplate="header" let-files let-chooseCallback="chooseCallback">
            <div class="upload-header">
              <button
                pButton
                type="button"
                icon="pi pi-plus"
                label="Choose Files"
                (click)="chooseCallback()"
                class="p-button-outlined"
              ></button>
              <span class="upload-info">
                PDF files only, max 50MB each, up to 10 files total
              </span>
            </div>
          </ng-template>

          <ng-template pTemplate="content">
            @if (documents().length === 0) {
              <div class="upload-empty">
                <i class="pi pi-cloud-upload"></i>
                <p>Drag and drop claim PDF files here</p>
                <p class="subtext">Claim forms, invoices, medical records</p>
              </div>
            }
          </ng-template>

          <ng-template pTemplate="empty">
            <div class="upload-empty">
              <i class="pi pi-cloud-upload"></i>
              <p>Drag and drop claim PDF files here</p>
              <p class="subtext">Claim forms, invoices, medical records</p>
            </div>
          </ng-template>
        </p-fileUpload>
      </div>

      <!-- Uploaded Files List -->
      @if (documents().length > 0) {
        <div class="files-list">
          <h4>Uploaded Documents ({{ documents().length }})</h4>

          @for (doc of documents(); track doc.id) {
            <p-card styleClass="file-card">
              <div class="file-item">
                <div class="file-icon">
                  <i class="pi pi-file-pdf"></i>
                </div>

                <div class="file-info">
                  <span class="file-name">{{ doc.filename }}</span>
                  <div class="file-meta">
                    <span class="file-size">{{ formatFileSize(doc.fileSize) }}</span>
                    <span class="file-type">{{ getDocumentTypeLabel(doc.documentType) }}</span>
                  </div>
                </div>

                <div class="file-status">
                  <p-tag
                    [value]="doc.status"
                    [severity]="getStatusSeverity(doc.status)"
                  ></p-tag>
                </div>

                @if (doc.status === 'uploading') {
                  <div class="file-progress">
                    <p-progressBar
                      [value]="doc.progressPercent"
                      [showValue]="true"
                      styleClass="progress-bar-sm"
                    ></p-progressBar>
                  </div>
                }

                <div class="file-actions">
                  <!-- Change Type Dropdown -->
                  <p-dropdown
                    [options]="documentTypeOptions"
                    [(ngModel)]="doc.documentType"
                    optionLabel="label"
                    optionValue="value"
                    styleClass="type-mini-dropdown"
                    [disabled]="doc.status !== 'pending'"
                  ></p-dropdown>

                  <button
                    pButton
                    type="button"
                    icon="pi pi-times"
                    class="p-button-text p-button-danger p-button-sm"
                    pTooltip="Remove"
                    tooltipPosition="top"
                    [disabled]="doc.status === 'uploading'"
                    (click)="removeDocument(doc.id)"
                  ></button>
                </div>
              </div>

              @if (doc.error) {
                <div class="file-error">
                  <i class="pi pi-exclamation-triangle"></i>
                  {{ doc.error }}
                </div>
              }
            </p-card>
          }
        </div>
      }

      <!-- Validation Errors -->
      @if (validationErrors().length > 0) {
        <div class="validation-errors">
          @for (error of validationErrors(); track error) {
            <p-message severity="error" [text]="error" styleClass="w-full"></p-message>
          }
        </div>
      }

      <!-- Upload Error -->
      @if (uploadError()) {
        <p-message
          severity="error"
          [text]="uploadError()!"
          styleClass="w-full mt-3"
        ></p-message>
      }

      <!-- No Documents Warning -->
      @if (documents().length === 0) {
        <p-message
          severity="warn"
          text="Please upload at least one claim document to proceed."
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
          label="Upload & Process"
          icon="pi pi-arrow-right"
          iconPos="right"
          [disabled]="!canProceed()"
          [loading]="uploading()"
          (click)="onNext()"
        ></button>
      </div>
    </div>
  `,
  styles: [`
    .step-claim-docs {
      padding: 1rem;
    }

    .step-description {
      color: #6c757d;
      margin-bottom: 1.5rem;
    }

    .required-note {
      display: block;
      font-weight: 500;
      color: #495057;
      margin-top: 0.25rem;
    }

    .type-selector {
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1rem;
    }

    .type-selector label {
      font-weight: 500;
      color: #495057;
    }

    :host ::ng-deep .type-dropdown {
      min-width: 200px;
    }

    .upload-section {
      margin-bottom: 1.5rem;
    }

    :host ::ng-deep .claim-upload {
      border: 2px dashed #ced4da;
      border-radius: 8px;
      background: #fafafa;
    }

    :host ::ng-deep .claim-upload .p-fileupload-content {
      padding: 2rem;
    }

    .upload-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      background: #f8f9fa;
      border-bottom: 1px solid #e9ecef;
    }

    .upload-info {
      color: #6c757d;
      font-size: 0.9rem;
    }

    .upload-empty {
      text-align: center;
      padding: 3rem;
      color: #6c757d;
    }

    .upload-empty i {
      font-size: 3rem;
      color: #ced4da;
      margin-bottom: 1rem;
    }

    .upload-empty p {
      margin: 0.5rem 0;
    }

    .upload-empty .subtext {
      font-size: 0.9rem;
      color: #adb5bd;
    }

    .files-list {
      margin-top: 1.5rem;
    }

    .files-list h4 {
      margin-bottom: 1rem;
      color: #495057;
    }

    .file-card {
      margin-bottom: 0.75rem;
    }

    :host ::ng-deep .file-card .p-card-body {
      padding: 0.75rem 1rem;
    }

    .file-item {
      display: flex;
      align-items: center;
      gap: 1rem;
      flex-wrap: wrap;
    }

    .file-icon {
      font-size: 1.5rem;
      color: #dc3545;
      flex-shrink: 0;
    }

    .file-info {
      flex: 1;
      min-width: 150px;
    }

    .file-name {
      display: block;
      font-weight: 500;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .file-meta {
      display: flex;
      gap: 1rem;
      font-size: 0.85rem;
      color: #6c757d;
    }

    .file-type {
      color: #0066cc;
    }

    .file-status {
      flex-shrink: 0;
    }

    .file-progress {
      width: 120px;
      flex-shrink: 0;
    }

    :host ::ng-deep .progress-bar-sm .p-progressbar {
      height: 0.5rem;
    }

    .file-actions {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex-shrink: 0;
    }

    :host ::ng-deep .type-mini-dropdown {
      max-width: 140px;
    }

    :host ::ng-deep .type-mini-dropdown .p-dropdown-label {
      font-size: 0.85rem;
      padding: 0.25rem 0.5rem;
    }

    .file-error {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-top: 0.5rem;
      padding: 0.5rem;
      background: #f8d7da;
      color: #721c24;
      border-radius: 4px;
      font-size: 0.85rem;
    }

    .validation-errors {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      margin-top: 1rem;
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
      .type-selector {
        flex-direction: column;
        align-items: flex-start;
      }

      .upload-header {
        flex-direction: column;
        gap: 0.5rem;
        text-align: center;
      }

      .file-item {
        flex-direction: column;
        align-items: flex-start;
      }

      .file-actions {
        width: 100%;
        justify-content: flex-end;
      }

      .file-progress {
        width: 100%;
      }

      .step-navigation {
        flex-direction: column;
        gap: 1rem;
      }

      .step-navigation button {
        width: 100%;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StepClaimDocsComponent implements OnDestroy {
  private readonly uploadService = inject(DocumentUploadService);
  private readonly destroy$ = new Subject<void>();

  @Input() initialData?: ClaimDocsStepData;

  @Output() stepComplete = new EventEmitter<ClaimDocsStepData>();
  @Output() stepBack = new EventEmitter<void>();
  @Output() dirty = new EventEmitter<boolean>();

  // Document type options
  readonly documentTypeOptions: DocumentTypeOption[] = [
    { label: 'Claim Form', value: 'claim_form' },
    { label: 'Invoice/Bill', value: 'invoice' },
    { label: 'Medical Records', value: 'medical_record' },
    { label: 'Other', value: 'other' },
  ];

  selectedDocType: DocumentType = 'claim_form';

  // State
  readonly documents = signal<DocumentUploadState[]>([]);
  readonly validationErrors = signal<string[]>([]);
  readonly uploadError = signal<string | null>(null);
  readonly uploading = signal<boolean>(false);

  // Computed
  readonly canProceed = computed(() => {
    const docs = this.documents();
    // Need at least one document
    return docs.length > 0;
  });

  readonly allUploaded = computed(() =>
    this.documents().every(d => d.documentId || d.status === 'failed')
  );

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Handle files selected from upload component.
   */
  onFilesSelected(event: { files: File[] }): void {
    const files = event.files;
    const errors: string[] = [];
    const validDocs: DocumentUploadState[] = [];

    // Validate each file
    for (const file of files) {
      const validation = validatePdfFile(file);
      if (validation.valid) {
        // Check if already added
        const existing = this.documents().find(d => d.filename === file.name);
        if (!existing) {
          const docState = createDocumentUploadState(file, this.selectedDocType);
          validDocs.push(docState);
        }
      } else {
        errors.push(`${file.name}: ${validation.error}`);
      }
    }

    // Check total count
    const totalCount = this.documents().length + validDocs.length;
    if (totalCount > 10) {
      errors.push('Maximum 10 files allowed. Please remove some files.');
      validDocs.splice(10 - this.documents().length);
    }

    // Update state
    if (validDocs.length > 0) {
      this.documents.update(docs => [...docs, ...validDocs]);
      this.dirty.emit(true);
    }

    this.validationErrors.set(errors);
  }

  /**
   * Remove a document from the list.
   */
  removeDocument(id: string): void {
    this.documents.update(docs => docs.filter(d => d.id !== id));
    this.dirty.emit(this.documents().length > 0);
  }

  /**
   * Upload all pending documents by type.
   */
  private async uploadDocuments(): Promise<boolean> {
    const pendingDocs = this.documents().filter(d => d.status === 'pending');
    if (pendingDocs.length === 0) {
      return true;
    }

    this.uploading.set(true);
    this.uploadError.set(null);

    try {
      // Group by document type
      const docsByType = new Map<DocumentType, DocumentUploadState[]>();
      for (const doc of pendingDocs) {
        const existing = docsByType.get(doc.documentType) || [];
        existing.push(doc);
        docsByType.set(doc.documentType, existing);
      }

      // Update status to uploading
      this.documents.update(docs =>
        docs.map(d =>
          pendingDocs.find(p => p.id === d.id)
            ? { ...d, status: 'uploading' as const, progressPercent: 0 }
            : d
        )
      );

      // Upload each type separately
      let hasFailures = false;
      for (const [docType, docs] of docsByType) {
        const files = docs.map(d => d.file);
        const response = await this.uploadService
          .uploadBatch(files, docType)
          .toPromise();

        if (response) {
          this.documents.update(allDocs =>
            allDocs.map(d => {
              const docIdx = docs.findIndex(pd => pd.id === d.id);
              if (docIdx >= 0) {
                const result = response.documents[docIdx];
                if (result && result.status === 'accepted') {
                  return {
                    ...d,
                    documentId: result.document_id,
                    status: 'processing' as const,
                    progressPercent: 25,
                  };
                } else {
                  hasFailures = true;
                  return {
                    ...d,
                    status: 'failed' as const,
                    error: result?.message || 'Upload failed',
                  };
                }
              }
              return d;
            })
          );

          if (response.failed > 0) {
            hasFailures = true;
          }
        }
      }

      if (hasFailures) {
        this.uploadError.set('Some files failed to upload. You can remove and retry them.');
      }

      return !hasFailures;
    } catch (error) {
      this.uploadError.set('Failed to upload documents. Please try again.');
      // Reset status
      this.documents.update(docs =>
        docs.map(d =>
          pendingDocs.find(p => p.id === d.id)
            ? { ...d, status: 'failed' as const, error: 'Upload failed' }
            : d
        )
      );
      return false;
    } finally {
      this.uploading.set(false);
    }
  }

  /**
   * Navigate to previous step.
   */
  onBack(): void {
    this.stepBack.emit();
  }

  /**
   * Proceed to next step (processing).
   */
  async onNext(): Promise<void> {
    if (!this.canProceed()) {
      return;
    }

    // Upload any pending documents first
    const pendingDocs = this.documents().filter(d => d.status === 'pending');
    if (pendingDocs.length > 0) {
      await this.uploadDocuments();

      // Allow proceeding even with some failures
      // The processing step will handle failed documents
    }

    // Get successfully uploaded documents
    const uploadedDocs = this.documents().filter(
      d => d.documentId || d.status === 'processing'
    );

    if (uploadedDocs.length === 0) {
      this.uploadError.set('No documents were successfully uploaded. Please try again.');
      return;
    }

    this.stepComplete.emit({
      documents: this.documents(),
    });
  }

  // Utility methods for template
  formatFileSize = formatFileSize;
  getStatusSeverity = getDocumentStatusSeverity;
  getDocumentTypeLabel = getDocumentTypeLabel;
}
