/**
 * Step Policy Documents Component.
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Verified: 2025-12-19
 *
 * Second step of claim submission wizard - Upload policy documents (PDFs).
 * Supports multiple file upload with drag-and-drop.
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
import { FileUploadModule } from 'primeng/fileupload';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { MessageModule } from 'primeng/message';
import { ProgressBarModule } from 'primeng/progressbar';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { Subject } from 'rxjs';

import {
  DocumentUploadState,
  validatePdfFile,
  createDocumentUploadState,
  formatFileSize,
  getDocumentStatusSeverity,
} from '@claims-processing/models';
import { DocumentUploadService } from '../../../../../core/services/document-upload.service';

export interface PolicyDocsStepData {
  documents: DocumentUploadState[];
  skipped: boolean;
}

@Component({
  selector: 'app-step-policy-docs',
  standalone: true,
  imports: [
    CommonModule,
    FileUploadModule,
    ButtonModule,
    CardModule,
    MessageModule,
    ProgressBarModule,
    TagModule,
    TooltipModule,
  ],
  template: `
    <div class="step-policy-docs">
      <h3>Step 2: Policy Documents</h3>
      <p class="step-description">
        Upload insurance policy documents (PDF format). These will be processed to extract coverage information.
        <span class="optional-note">(Optional - you may skip if not available)</span>
      </p>

      <!-- File Upload -->
      <div class="upload-section">
        <p-fileUpload
          #fileUpload
          name="policyDocs[]"
          [multiple]="true"
          accept=".pdf,application/pdf"
          [maxFileSize]="52428800"
          [customUpload]="true"
          (uploadHandler)="onFilesSelected($event)"
          (onSelect)="onFilesSelected($event)"
          [showUploadButton]="false"
          [showCancelButton]="false"
          styleClass="policy-upload"
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
                PDF files only, max 50MB each, up to 10 files
              </span>
            </div>
          </ng-template>

          <ng-template pTemplate="content" let-files let-uploadedFiles="uploadedFiles" let-removeFileCallback="removeFileCallback">
            @if (documents().length === 0) {
              <div class="upload-empty">
                <i class="pi pi-cloud-upload"></i>
                <p>Drag and drop policy PDF files here</p>
                <p class="subtext">or click "Choose Files" above</p>
              </div>
            }
          </ng-template>

          <ng-template pTemplate="empty">
            <div class="upload-empty">
              <i class="pi pi-cloud-upload"></i>
              <p>Drag and drop policy PDF files here</p>
              <p class="subtext">or click "Choose Files" above</p>
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
                  <span class="file-size">{{ formatFileSize(doc.fileSize) }}</span>
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

        <div class="nav-right">
          <button
            pButton
            type="button"
            label="Skip This Step"
            class="p-button-text"
            (click)="onSkip()"
          ></button>

          <button
            pButton
            type="button"
            label="Next"
            icon="pi pi-arrow-right"
            iconPos="right"
            [disabled]="!canProceed()"
            [loading]="uploading()"
            (click)="onNext()"
          ></button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .step-policy-docs {
      padding: 1rem;
    }

    .step-description {
      color: #6c757d;
      margin-bottom: 1.5rem;
    }

    .optional-note {
      display: block;
      font-style: italic;
      font-size: 0.9rem;
      margin-top: 0.25rem;
    }

    .upload-section {
      margin-bottom: 1.5rem;
    }

    :host ::ng-deep .policy-upload {
      border: 2px dashed #ced4da;
      border-radius: 8px;
      background: #fafafa;
    }

    :host ::ng-deep .policy-upload .p-fileupload-content {
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
    }

    .file-icon {
      font-size: 1.5rem;
      color: #dc3545;
    }

    .file-info {
      flex: 1;
      min-width: 0;
    }

    .file-name {
      display: block;
      font-weight: 500;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .file-size {
      display: block;
      font-size: 0.85rem;
      color: #6c757d;
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
      flex-shrink: 0;
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

    .nav-right {
      display: flex;
      gap: 0.5rem;
    }

    @media (max-width: 768px) {
      .upload-header {
        flex-direction: column;
        gap: 0.5rem;
        text-align: center;
      }

      .file-item {
        flex-wrap: wrap;
      }

      .file-progress {
        width: 100%;
        order: 10;
      }

      .step-navigation {
        flex-direction: column;
        gap: 1rem;
      }

      .nav-right {
        width: 100%;
        flex-direction: column;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StepPolicyDocsComponent implements OnDestroy {
  private readonly uploadService = inject(DocumentUploadService);
  private readonly destroy$ = new Subject<void>();

  @Input() initialData?: PolicyDocsStepData;

  @Output() stepComplete = new EventEmitter<PolicyDocsStepData>();
  @Output() stepBack = new EventEmitter<void>();
  @Output() dirty = new EventEmitter<boolean>();

  // State
  readonly documents = signal<DocumentUploadState[]>([]);
  readonly validationErrors = signal<string[]>([]);
  readonly uploadError = signal<string | null>(null);
  readonly uploading = signal<boolean>(false);

  // Computed
  readonly canProceed = computed(() => {
    const docs = this.documents();
    // Can proceed if no documents (will skip) or all uploaded successfully
    return docs.length === 0 || docs.every(d => d.status === 'pending' || d.documentId);
  });

  readonly hasUploadedDocs = computed(() =>
    this.documents().some(d => d.documentId)
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
          validDocs.push(createDocumentUploadState(file, 'policy'));
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
   * Upload all pending documents.
   */
  private async uploadDocuments(): Promise<void> {
    const pendingDocs = this.documents().filter(d => d.status === 'pending');
    if (pendingDocs.length === 0) {
      return;
    }

    this.uploading.set(true);
    this.uploadError.set(null);

    try {
      const files = pendingDocs.map(d => d.file);

      // Update status to uploading
      this.documents.update(docs =>
        docs.map(d =>
          pendingDocs.find(p => p.id === d.id)
            ? { ...d, status: 'uploading' as const, progressPercent: 0 }
            : d
        )
      );

      // Use batch upload
      const response = await this.uploadService
        .uploadBatch(files, 'policy')
        .toPromise();

      if (response) {
        // Update documents with response
        this.documents.update(docs =>
          docs.map(d => {
            const pendingDoc = pendingDocs.find(p => p.id === d.id);
            if (pendingDoc) {
              const idx = pendingDocs.indexOf(pendingDoc);
              const result = response.documents[idx];
              if (result && result.status === 'accepted') {
                return {
                  ...d,
                  documentId: result.document_id,
                  status: 'processing' as const,
                  progressPercent: 25,
                };
              } else {
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
          this.uploadError.set(`${response.failed} file(s) failed to upload`);
        }
      }
    } catch (error) {
      this.uploadError.set('Failed to upload documents. Please try again.');
      // Reset status
      this.documents.update(docs =>
        docs.map(d =>
          pendingDocs.find(p => p.id === d.id)
            ? { ...d, status: 'failed' as const }
            : d
        )
      );
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
   * Skip this step.
   */
  onSkip(): void {
    this.stepComplete.emit({
      documents: [],
      skipped: true,
    });
  }

  /**
   * Proceed to next step.
   */
  async onNext(): Promise<void> {
    if (!this.canProceed()) {
      return;
    }

    // Upload any pending documents first
    const pendingDocs = this.documents().filter(d => d.status === 'pending');
    if (pendingDocs.length > 0) {
      await this.uploadDocuments();

      // Check if all uploads succeeded
      const failedDocs = this.documents().filter(d => d.status === 'failed');
      if (failedDocs.length > 0) {
        this.uploadError.set('Some files failed to upload. Please remove them and try again.');
        return;
      }
    }

    this.stepComplete.emit({
      documents: this.documents(),
      skipped: false,
    });
  }

  // Utility methods for template
  formatFileSize = formatFileSize;
  getStatusSeverity = getDocumentStatusSeverity;
}
