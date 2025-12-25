/**
 * Step Visual Extraction Component.
 *
 * Main component for the Visual Extraction Display step.
 * Orchestrates document viewing with extraction overlays.
 *
 * This step displays extracted data in a format that mirrors the
 * original source document layout, allowing users to visually
 * verify OCR accuracy before proceeding to processing.
 *
 * Source: Design Document 10 - Visual Extraction Display
 * Verified: 2025-12-24
 */
import {
  Component,
  Input,
  Output,
  EventEmitter,
  OnInit,
  ChangeDetectionStrategy,
  signal,
  computed,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { SplitterModule } from 'primeng/splitter';
import { DropdownModule } from 'primeng/dropdown';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { MessageModule } from 'primeng/message';
import { TooltipModule } from 'primeng/tooltip';

import { DocumentViewerComponent, TextRegion } from './components/document-viewer/document-viewer.component';
import { PageNavigatorComponent } from './components/page-navigator/page-navigator.component';
import { ZoomControlsComponent } from './components/zoom-controls/zoom-controls.component';
import { ConfidenceLegendComponent } from './components/confidence-legend/confidence-legend.component';
import { ExtractionPanelComponent, PageExtraction } from './components/extraction-panel/extraction-panel.component';
import { DocumentUploadState } from '@claims-processing/models';
import { environment } from '../../../../../../environments/environment';

/**
 * Quick extraction response from backend.
 */
export interface QuickExtractionResponse {
  document_id: string;
  filename: string;
  total_pages: number;
  overall_confidence: number;
  processing_time_ms: number;
  pages: PageExtraction[];
  tables: any[];
}

/**
 * View mode options for the visual extraction display.
 */
type ViewMode = 'overlay' | 'side-by-side' | 'text-only';

@Component({
  selector: 'app-step-visual-extraction',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    CardModule,
    ButtonModule,
    SplitterModule,
    DropdownModule,
    ProgressSpinnerModule,
    MessageModule,
    TooltipModule,
    DocumentViewerComponent,
    PageNavigatorComponent,
    ZoomControlsComponent,
    ConfidenceLegendComponent,
    ExtractionPanelComponent,
  ],
  template: `
    <div class="visual-extraction-step">
      <!-- Header -->
      <div class="step-header">
        <div class="header-left">
          <h3>Visual Extraction Display</h3>
          @if (!isLoading() && !error()) {
            <span
              class="overall-confidence"
              [class.high]="overallConfidence() >= 0.8"
              [class.medium]="overallConfidence() >= 0.5 && overallConfidence() < 0.8"
              [class.low]="overallConfidence() < 0.5"
            >
              Overall Confidence: {{ (overallConfidence() * 100).toFixed(1) }}%
            </span>
          }
        </div>
        <div class="header-right">
          <p-dropdown
            [options]="viewModeOptions"
            [(ngModel)]="viewMode"
            optionLabel="label"
            optionValue="value"
            [style]="{ minWidth: '150px' }"
          />
        </div>
      </div>

      <!-- Loading State -->
      @if (isLoading()) {
        <div class="loading-container">
          <p-progressSpinner strokeWidth="4" />
          <p>Extracting document data...</p>
          <span class="loading-hint">This may take a few moments for multi-page documents</span>
        </div>
      }

      <!-- Error State -->
      @if (error()) {
        <div class="error-container">
          <p-message severity="error" [text]="error()!" />
          <p-button
            label="Retry"
            icon="pi pi-refresh"
            (onClick)="retryExtraction()"
            styleClass="p-button-outlined"
          />
        </div>
      }

      <!-- Content -->
      @if (!isLoading() && !error()) {
        <div class="content-container">
          @switch (viewMode) {
            @case ('overlay') {
              <p-splitter [style]="{ height: '500px' }" [panelSizes]="[60, 40]" styleClass="extraction-splitter">
                <!-- Document Viewer Panel -->
                <ng-template pTemplate>
                  <div class="viewer-panel">
                    <app-document-viewer
                      [pageImage]="currentPageImage()"
                      [regions]="currentPageRegions()"
                      [zoomLevel]="zoomLevel()"
                      [selectedRegion]="selectedRegion()"
                      (regionClick)="onRegionClick($event)"
                    />
                  </div>
                </ng-template>

                <!-- Extraction Panel -->
                <ng-template pTemplate>
                  <div class="extraction-side-panel">
                    <app-extraction-panel
                      [pages]="pages()"
                      [selectedRegion]="selectedRegion()"
                    />
                  </div>
                </ng-template>
              </p-splitter>
            }
            @case ('side-by-side') {
              <div class="side-by-side-view">
                <div class="original-panel">
                  <h4>Original Document</h4>
                  <app-document-viewer
                    [pageImage]="currentPageImage()"
                    [regions]="[]"
                    [zoomLevel]="zoomLevel()"
                    [selectedRegion]="null"
                  />
                </div>
                <div class="extracted-panel">
                  <h4>Extracted Data</h4>
                  <app-extraction-panel
                    [pages]="[currentPage()]"
                    [selectedRegion]="selectedRegion()"
                  />
                </div>
              </div>
            }
            @case ('text-only') {
              <div class="text-only-view">
                <app-extraction-panel
                  [pages]="pages()"
                  [selectedRegion]="selectedRegion()"
                />
              </div>
            }
          }

          <!-- Controls Bar -->
          <div class="controls-bar">
            <app-page-navigator
              [currentPage]="currentPageNumber()"
              [totalPages]="totalPages()"
              (pageChange)="onPageChange($event)"
            />

            <app-zoom-controls
              [zoomLevel]="zoomLevel()"
              (zoomChange)="onZoomChange($event)"
            />

            <app-confidence-legend />
          </div>
        </div>
      }

      <!-- Actions -->
      <div class="step-actions">
        <p-button
          label="Back to Upload"
          icon="pi pi-arrow-left"
          styleClass="p-button-outlined"
          (onClick)="onBack()"
        />
        <p-button
          label="Continue to Processing"
          icon="pi pi-arrow-right"
          iconPos="right"
          [disabled]="isLoading() || !!error()"
          (onClick)="onContinue()"
        />
      </div>
    </div>
  `,
  styles: [`
    .visual-extraction-step {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .step-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .header-left h3 {
      margin: 0;
      color: #343a40;
    }

    .overall-confidence {
      padding: 0.25rem 0.75rem;
      border-radius: 4px;
      font-size: 0.85rem;
      font-weight: 600;
    }

    .overall-confidence.high {
      background: #d4edda;
      color: #155724;
    }

    .overall-confidence.medium {
      background: #fff3cd;
      color: #856404;
    }

    .overall-confidence.low {
      background: #f8d7da;
      color: #721c24;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 1rem;
      padding: 4rem;
      background: #f8f9fa;
      border-radius: 8px;
    }

    .loading-container p {
      margin: 0;
      font-size: 1rem;
      color: #495057;
    }

    .loading-hint {
      font-size: 0.85rem;
      color: #6c757d;
    }

    .error-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1rem;
      padding: 2rem;
    }

    .content-container {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    :host ::ng-deep .extraction-splitter .p-splitter-panel {
      overflow: hidden;
    }

    .viewer-panel {
      height: 100%;
      overflow: auto;
      background: #e0e0e0;
    }

    .extraction-side-panel {
      height: 100%;
      overflow: auto;
      padding: 0.5rem;
      background: #f8f9fa;
    }

    .side-by-side-view {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      height: 500px;
    }

    .side-by-side-view h4 {
      margin: 0 0 0.5rem 0;
      padding: 0.5rem;
      background: #e9ecef;
      border-radius: 4px;
    }

    .original-panel,
    .extracted-panel {
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .text-only-view {
      height: 500px;
      overflow: auto;
    }

    .controls-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem 1rem;
      background: #f8f9fa;
      border-radius: 8px;
      flex-wrap: wrap;
      gap: 1rem;
    }

    .step-actions {
      display: flex;
      justify-content: space-between;
      padding-top: 1rem;
      border-top: 1px solid #dee2e6;
    }

    @media (max-width: 768px) {
      .side-by-side-view {
        grid-template-columns: 1fr;
        height: auto;
      }

      .controls-bar {
        flex-direction: column;
        align-items: stretch;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StepVisualExtractionComponent implements OnInit {
  /** Documents uploaded in the previous step. */
  @Input() documents: DocumentUploadState[] = [];

  /** Emits when extraction is complete and user wants to continue. */
  @Output() stepComplete = new EventEmitter<QuickExtractionResponse>();

  /** Emits when user wants to go back. */
  @Output() stepBack = new EventEmitter<void>();

  // State signals
  readonly isLoading = signal(true);
  readonly error = signal<string | null>(null);
  readonly extractionResult = signal<QuickExtractionResponse | null>(null);
  readonly currentPageNumber = signal(1);
  readonly zoomLevel = signal(100);
  readonly selectedRegion = signal<TextRegion | null>(null);

  // View mode
  viewMode: ViewMode = 'overlay';

  readonly viewModeOptions = [
    { label: 'Overlay View', value: 'overlay' },
    { label: 'Side by Side', value: 'side-by-side' },
    { label: 'Text Only', value: 'text-only' },
  ];

  // Computed values
  readonly pages = computed(() => this.extractionResult()?.pages || []);
  readonly totalPages = computed(() => this.extractionResult()?.total_pages || 0);
  readonly overallConfidence = computed(() => this.extractionResult()?.overall_confidence || 0);

  readonly currentPage = computed(() => {
    const pageNum = this.currentPageNumber();
    return this.pages().find(p => p.page_number === pageNum) || {
      page_number: pageNum,
      width: 0,
      height: 0,
      image_url: '',
      regions: [],
    };
  });

  readonly currentPageImage = computed(() => {
    const page = this.currentPage();
    if (!page.image_url) return '';
    // The image_url from backend already includes /api/v1 prefix
    // Just use it directly - the proxy will forward to backend
    return page.image_url;
  });

  readonly currentPageRegions = computed(() => this.currentPage().regions);

  async ngOnInit(): Promise<void> {
    if (this.documents.length > 0) {
      await this.performQuickExtraction();
    } else {
      this.isLoading.set(false);
      this.error.set('No documents to extract');
    }
  }

  private async performQuickExtraction(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);

    try {
      const document = this.documents[0];

      // Create form data for the file upload
      const formData = new FormData();

      // Get the file from the document state
      if (document.file) {
        formData.append('file', document.file, document.file.name);
      } else {
        throw new Error('No file available for extraction');
      }
      formData.append('return_images', 'true');

      // Call the quick-extract endpoint
      const response = await fetch(`${environment.apiUrl}/documents/quick-extract`, {
        method: 'POST',
        body: formData,
        headers: {
          // Note: Don't set Content-Type for FormData, browser sets it with boundary
          'Authorization': `Bearer ${this.getAuthToken()}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Extraction failed: ${response.status}`);
      }

      const result: QuickExtractionResponse = await response.json();
      this.extractionResult.set(result);
      this.isLoading.set(false);

    } catch (err) {
      console.error('Quick extraction error:', err);
      this.error.set(err instanceof Error ? err.message : 'Failed to extract document');
      this.isLoading.set(false);
    }
  }

  private getAuthToken(): string {
    // Get token from localStorage first
    const storedToken = localStorage.getItem('access_token');
    if (storedToken) {
      return storedToken;
    }

    // In development mode, use a pre-generated development token
    // This token is valid for the local development backend
    // Token payload: sub, tenant_id, role, permissions, exp (7 days from 2024-12-24)
    if (!environment.production) {
      // Development token - valid for local testing only (30 day expiry)
      // Generated with JWT_SECRET_KEY from .env: claims-jwt-secret-key-change-in-production-32chars
      const devToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdXNlci0wMDEiLCJ0ZW5hbnRfaWQiOiJ0ZXN0LXRlbmFudCIsInJvbGUiOiJhZG1pbiIsInBlcm1pc3Npb25zIjpbImRvY3VtZW50czp1cGxvYWQiLCJkb2N1bWVudHM6cmVhZCIsImRvY3VtZW50czp3cml0ZSIsImNsYWltczpyZWFkIiwiY2xhaW1zOndyaXRlIiwiYWRtaW46YWxsIl0sImV4cCI6MTc2OTE4OTk1MiwidHlwZSI6ImFjY2VzcyJ9.AgeaoR0wWy3yUsDsRKATAk6vUfuJEAs1dk8g0txumQU';
      return devToken;
    }

    return '';
  }

  retryExtraction(): void {
    this.performQuickExtraction();
  }

  onPageChange(page: number): void {
    this.currentPageNumber.set(page);
    this.selectedRegion.set(null);
  }

  onZoomChange(zoom: number): void {
    this.zoomLevel.set(zoom);
  }

  onRegionClick(region: TextRegion | null): void {
    this.selectedRegion.set(region);
  }

  onBack(): void {
    this.stepBack.emit();
  }

  onContinue(): void {
    const result = this.extractionResult();
    if (result) {
      this.stepComplete.emit(result);
    }
  }
}
