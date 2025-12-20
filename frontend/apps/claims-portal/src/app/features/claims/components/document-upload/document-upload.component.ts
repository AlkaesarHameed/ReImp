/**
 * Document Upload Component.
 * Source: Phase 3 Implementation Document
 * Source: Design Document Section 3.4
 * Verified: 2025-12-18
 *
 * Reusable component for uploading and managing claim documents.
 * Supports drag-and-drop, file validation, and document type selection.
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
import { HttpClient, HttpEventType } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { FileUploadModule } from 'primeng/fileupload';
import { ButtonModule } from 'primeng/button';
import { DropdownModule } from 'primeng/dropdown';
import { TableModule } from 'primeng/table';
import { ProgressBarModule } from 'primeng/progressbar';
import { TooltipModule } from 'primeng/tooltip';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ConfirmationService, MessageService } from 'primeng/api';
import { Subject, takeUntil, catchError, of, tap } from 'rxjs';

import { ClaimDocument } from '@claims-processing/models';
import { environment } from '../../../../../environments/environment';

interface DocumentType {
  label: string;
  value: string;
}

interface ValidationResult {
  valid: boolean;
  error?: string;
}

@Component({
  selector: 'app-document-upload',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    FileUploadModule,
    ButtonModule,
    DropdownModule,
    TableModule,
    ProgressBarModule,
    TooltipModule,
    ConfirmDialogModule,
  ],
  providers: [ConfirmationService],
  template: `
    <div class="document-upload">
      <p-confirmDialog></p-confirmDialog>

      <!-- Upload Section (hidden in read-only mode) -->
      @if (!readOnly) {
        <div class="upload-section">
          <!-- Document Type Selection -->
          <div class="document-type-selection">
            <label for="docType">Document Type *</label>
            <p-dropdown
              id="docType"
              [options]="documentTypes"
              [(ngModel)]="selectedDocumentType"
              (onChange)="onDocumentTypeChange($event.value)"
              placeholder="Select document type"
              styleClass="w-full"
            ></p-dropdown>
          </div>

          <!-- Drag & Drop Upload Area -->
          <div
            class="upload-area"
            [class.dragging]="isDragging()"
            (dragover)="onDragOver($event)"
            (dragleave)="onDragLeave($event)"
            (drop)="onDrop($event)"
            role="region"
            aria-label="File upload area"
          >
            <div class="upload-content">
              <i class="pi pi-cloud-upload upload-icon"></i>
              <p class="upload-text">Drag and drop files here</p>
              <p class="upload-or">or</p>
              <button
                pButton
                type="button"
                label="Browse Files"
                icon="pi pi-folder-open"
                class="p-button-outlined"
                (click)="fileInput.click()"
              ></button>
              <input
                #fileInput
                type="file"
                [accept]="acceptedTypes"
                (change)="onFileSelected($event)"
                multiple
                hidden
                aria-label="Select files to upload"
              />
            </div>
            <p class="upload-hint">
              Accepted formats: PDF, JPG, PNG, TIFF. Max size: {{ maxFileSize / 1024 / 1024 }}MB
            </p>
          </div>

          <!-- Upload Progress -->
          @if (uploading()) {
            <div class="upload-progress" role="status" aria-live="polite">
              <p-progressBar
                [value]="uploadProgress()"
                [showValue]="true"
              ></p-progressBar>
              <span class="sr-only">{{ uploadStatusMessage() }}</span>
            </div>
          }

          <!-- Pending Files Queue -->
          @if (pendingFiles().length > 0) {
            <div class="pending-files">
              <h4>Pending Upload ({{ pendingFiles().length }})</h4>
              <ul class="pending-list">
                @for (file of pendingFiles(); track file.name) {
                  <li class="pending-item">
                    <i class="pi pi-file"></i>
                    <span class="file-name">{{ file.name }}</span>
                    <span class="file-size">{{ formatFileSize(file.size) }}</span>
                    <button
                      pButton
                      type="button"
                      icon="pi pi-times"
                      class="p-button-text p-button-danger p-button-sm"
                      (click)="removePendingFile(file)"
                      pTooltip="Remove"
                    ></button>
                  </li>
                }
              </ul>
              <button
                pButton
                type="button"
                label="Upload All"
                icon="pi pi-upload"
                [loading]="uploading()"
                [disabled]="!selectedDocumentType"
                (click)="uploadAllPending()"
                class="mt-2"
              ></button>
            </div>
          }
        </div>
      }

      <!-- Uploaded Documents Table -->
      @if (documents().length > 0) {
        <div class="documents-section">
          <h4>Uploaded Documents ({{ documents().length }})</h4>
          <p-table
            [value]="documents()"
            [tableStyle]="{ 'min-width': '50rem' }"
            styleClass="p-datatable-sm"
          >
            <ng-template pTemplate="header">
              <tr>
                <th>Type</th>
                <th>File Name</th>
                <th>Size</th>
                <th>Uploaded</th>
                @if (canDelete()) {
                  <th style="width: 5rem">Actions</th>
                }
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-doc>
              <tr>
                <td>
                  <span class="document-type-badge">{{ doc.document_type }}</span>
                </td>
                <td>
                  <div class="file-info">
                    <i [class]="getFileIcon(doc.mime_type)"></i>
                    <span>{{ doc.file_name }}</span>
                  </div>
                </td>
                <td>{{ formatFileSize(doc.file_size) }}</td>
                <td>{{ doc.uploaded_at | date:'short' }}</td>
                @if (canDelete()) {
                  <td>
                    <button
                      pButton
                      type="button"
                      icon="pi pi-trash"
                      class="p-button-text p-button-danger p-button-sm"
                      (click)="confirmDelete(doc)"
                      pTooltip="Delete"
                    ></button>
                  </td>
                }
              </tr>
            </ng-template>
            <ng-template pTemplate="emptymessage">
              <tr>
                <td [attr.colspan]="canDelete() ? 5 : 4" class="text-center">
                  No documents uploaded yet.
                </td>
              </tr>
            </ng-template>
          </p-table>
        </div>
      } @else if (readOnly) {
        <div class="no-documents">
          <i class="pi pi-inbox"></i>
          <p>No documents attached to this claim.</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .document-upload {
      padding: 1rem;
    }

    .upload-section {
      margin-bottom: 1.5rem;
    }

    .document-type-selection {
      margin-bottom: 1rem;
    }

    .document-type-selection label {
      display: block;
      margin-bottom: 0.5rem;
      font-weight: 500;
    }

    .upload-area {
      border: 2px dashed #dee2e6;
      border-radius: 8px;
      padding: 2rem;
      text-align: center;
      background: #f8f9fa;
      transition: all 0.2s ease;
      cursor: pointer;
    }

    .upload-area:hover,
    .upload-area.dragging {
      border-color: #0066cc;
      background: #e7f1ff;
    }

    .upload-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
    }

    .upload-icon {
      font-size: 3rem;
      color: #6c757d;
    }

    .upload-text {
      font-size: 1.1rem;
      color: #343a40;
      margin: 0;
    }

    .upload-or {
      color: #6c757d;
      margin: 0;
    }

    .upload-hint {
      color: #6c757d;
      font-size: 0.85rem;
      margin-top: 1rem;
      margin-bottom: 0;
    }

    .upload-progress {
      margin-top: 1rem;
    }

    .pending-files {
      margin-top: 1rem;
      padding: 1rem;
      background: #fff;
      border: 1px solid #dee2e6;
      border-radius: 4px;
    }

    .pending-files h4 {
      margin: 0 0 0.5rem;
    }

    .pending-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }

    .pending-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem;
      border-bottom: 1px solid #f0f0f0;
    }

    .pending-item:last-child {
      border-bottom: none;
    }

    .pending-item .file-name {
      flex: 1;
    }

    .pending-item .file-size {
      color: #6c757d;
      font-size: 0.85rem;
    }

    .documents-section {
      margin-top: 1.5rem;
    }

    .documents-section h4 {
      margin-bottom: 1rem;
    }

    .document-type-badge {
      background: #e7f1ff;
      color: #0066cc;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.85rem;
    }

    .file-info {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .file-info i {
      color: #6c757d;
    }

    .no-documents {
      text-align: center;
      padding: 3rem;
      color: #6c757d;
    }

    .no-documents i {
      font-size: 3rem;
      margin-bottom: 1rem;
    }

    .no-documents p {
      margin: 0;
    }

    .sr-only {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      border: 0;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DocumentUploadComponent implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly messageService = inject(MessageService);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly destroy$ = new Subject<void>();
  private readonly apiUrl = environment.apiUrl;

  // Inputs
  @Input() claimId?: string;
  @Input() initialDocuments?: ClaimDocument[];
  @Input() readOnly = false;

  // Outputs
  @Output() documentUploaded = new EventEmitter<ClaimDocument>();
  @Output() documentDeleted = new EventEmitter<string>();
  @Output() documentsChanged = new EventEmitter<ClaimDocument[]>();

  // Configuration
  readonly acceptedTypes = 'application/pdf,image/jpeg,image/png,image/tiff';
  readonly maxFileSize = 10 * 1024 * 1024; // 10MB

  readonly documentTypes: DocumentType[] = [
    { label: 'Explanation of Benefits (EOB)', value: 'EOB' },
    { label: 'Medical Record', value: 'Medical Record' },
    { label: 'Itemized Bill', value: 'Itemized Bill' },
    { label: 'Prior Authorization', value: 'Prior Authorization' },
    { label: 'Referral', value: 'Referral' },
    { label: 'Lab Results', value: 'Lab Results' },
    { label: 'Prescription', value: 'Prescription' },
    { label: 'Other', value: 'Other' },
  ];

  selectedDocumentType = '';

  // State
  readonly documents = signal<ClaimDocument[]>([]);
  readonly pendingFiles = signal<File[]>([]);
  readonly uploading = signal<boolean>(false);
  readonly uploadProgress = signal<number>(0);
  readonly isDragging = signal<boolean>(false);

  // Computed
  readonly canDelete = computed(() => !this.readOnly);
  readonly uploadStatusMessage = computed(() => {
    if (this.uploading()) {
      return `Uploading... ${this.uploadProgress()}%`;
    }
    return '';
  });

  ngOnInit(): void {
    if (this.initialDocuments) {
      this.documents.set([...this.initialDocuments]);
      this.documentsChanged.emit(this.documents());
    } else if (this.claimId) {
      this.loadDocuments();
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadDocuments(): void {
    if (!this.claimId) return;

    this.http
      .get<ClaimDocument[]>(`${this.apiUrl}/claims/${this.claimId}/documents`)
      .pipe(
        takeUntil(this.destroy$),
        catchError(error => {
          console.error('Failed to load documents:', error);
          return of([]);
        })
      )
      .subscribe(docs => {
        this.documents.set(docs);
        this.documentsChanged.emit(docs);
      });
  }

  validateFile(file: File): ValidationResult {
    // Check file size
    if (file.size > this.maxFileSize) {
      return {
        valid: false,
        error: `File size exceeds maximum of ${this.maxFileSize / 1024 / 1024}MB`,
      };
    }

    // Check file type
    const acceptedTypesArray = this.acceptedTypes.split(',');
    if (!acceptedTypesArray.includes(file.type)) {
      return {
        valid: false,
        error: `File type "${file.type}" is not allowed`,
      };
    }

    return { valid: true };
  }

  onDocumentTypeChange(type: string): void {
    this.selectedDocumentType = type;
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(false);

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.processFiles(Array.from(files));
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.processFiles(Array.from(input.files));
      input.value = ''; // Reset input for re-selection
    }
  }

  private processFiles(files: File[]): void {
    const validFiles: File[] = [];

    for (const file of files) {
      const validation = this.validateFile(file);
      if (validation.valid) {
        validFiles.push(file);
      } else {
        this.messageService.add({
          severity: 'error',
          summary: 'Invalid File',
          detail: `${file.name}: ${validation.error}`,
        });
      }
    }

    if (validFiles.length > 0) {
      this.pendingFiles.update(pending => [...pending, ...validFiles]);
    }
  }

  removePendingFile(file: File): void {
    this.pendingFiles.update(pending => pending.filter(f => f !== file));
  }

  uploadAllPending(): void {
    const files = this.pendingFiles();
    if (files.length === 0) return;

    // Upload files sequentially
    this.uploadNextFile(files, 0);
  }

  private uploadNextFile(files: File[], index: number): void {
    if (index >= files.length) {
      this.pendingFiles.set([]);
      return;
    }

    this.uploadFile(files[index]).then(() => {
      this.uploadNextFile(files, index + 1);
    });
  }

  uploadFile(file: File): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.selectedDocumentType) {
        this.messageService.add({
          severity: 'warn',
          summary: 'Document Type Required',
          detail: 'Please select a document type before uploading.',
        });
        resolve();
        return;
      }

      if (!this.claimId) {
        this.messageService.add({
          severity: 'error',
          summary: 'Upload Error',
          detail: 'No claim ID provided for document upload.',
        });
        resolve();
        return;
      }

      const formData = new FormData();
      formData.append('file', file);
      formData.append('document_type', this.selectedDocumentType);

      this.uploading.set(true);
      this.uploadProgress.set(0);

      this.http
        .post<ClaimDocument>(
          `${this.apiUrl}/claims/${this.claimId}/documents`,
          formData,
          {
            reportProgress: true,
            observe: 'events',
          }
        )
        .pipe(
          takeUntil(this.destroy$),
          tap(event => {
            if (event.type === HttpEventType.UploadProgress && event.total) {
              this.uploadProgress.set(Math.round((event.loaded / event.total) * 100));
            }
          }),
          catchError(error => {
            this.messageService.add({
              severity: 'error',
              summary: 'Upload Failed',
              detail: `Failed to upload ${file.name}`,
            });
            this.uploading.set(false);
            reject(error);
            return of(null);
          })
        )
        .subscribe(event => {
          if (event?.type === HttpEventType.Response && event.body) {
            const doc = event.body as ClaimDocument;
            this.documents.update(docs => [...docs, doc]);
            this.documentUploaded.emit(doc);
            this.documentsChanged.emit(this.documents());
            this.messageService.add({
              severity: 'success',
              summary: 'Upload Complete',
              detail: `${file.name} uploaded successfully.`,
            });
          }
          if (event?.type === HttpEventType.Response) {
            this.uploading.set(false);
            this.uploadProgress.set(0);
            resolve();
          }
        });
    });
  }

  confirmDelete(doc: ClaimDocument): void {
    this.confirmationService.confirm({
      message: `Are you sure you want to delete "${doc.file_name}"?`,
      header: 'Confirm Delete',
      icon: 'pi pi-exclamation-triangle',
      accept: () => this.deleteDocument(doc),
    });
  }

  deleteDocument(doc: ClaimDocument): void {
    if (!this.claimId) return;

    this.http
      .delete(`${this.apiUrl}/claims/${this.claimId}/documents/${doc.id}`)
      .pipe(
        takeUntil(this.destroy$),
        catchError(error => {
          this.messageService.add({
            severity: 'error',
            summary: 'Delete Failed',
            detail: `Failed to delete ${doc.file_name}`,
          });
          return of(null);
        })
      )
      .subscribe(() => {
        this.documents.update(docs => docs.filter(d => d.id !== doc.id));
        this.documentDeleted.emit(doc.id);
        this.documentsChanged.emit(this.documents());
        this.messageService.add({
          severity: 'success',
          summary: 'Deleted',
          detail: `${doc.file_name} has been deleted.`,
        });
      });
  }

  formatFileSize(bytes: number): string {
    if (bytes < 1024) {
      return `${bytes} B`;
    } else if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(2)} KB`;
    } else {
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }
  }

  getFileIcon(mimeType: string): string {
    if (mimeType === 'application/pdf') {
      return 'pi pi-file-pdf';
    } else if (mimeType.startsWith('image/')) {
      return 'pi pi-image';
    }
    return 'pi pi-file';
  }
}
