/**
 * Extraction Panel Component.
 *
 * Displays all extracted text and selected region details.
 * Provides full text view and region selection details.
 *
 * Source: Design Document 10 - Visual Extraction Display
 * Verified: 2025-12-24
 */
import {
  Component,
  Input,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { CardModule } from 'primeng/card';
import { DividerModule } from 'primeng/divider';
import { TagModule } from 'primeng/tag';
import { ScrollPanelModule } from 'primeng/scrollpanel';
import { TextRegion } from '../document-viewer/document-viewer.component';

/**
 * Page extraction data with regions.
 */
export interface PageExtraction {
  page_number: number;
  width: number;
  height: number;
  image_url: string;
  regions: TextRegion[];
}

@Component({
  selector: 'app-extraction-panel',
  standalone: true,
  imports: [CommonModule, CardModule, DividerModule, TagModule, ScrollPanelModule],
  template: `
    <div class="extraction-panel">
      <!-- Selected Region Details -->
      @if (selectedRegion) {
        <p-card styleClass="region-details-card">
          <ng-template pTemplate="header">
            <div class="card-header">
              <span class="header-title">Selected Region</span>
              <p-tag
                [value]="getConfidenceLabel(selectedRegion.confidence)"
                [severity]="getConfidenceSeverity(selectedRegion.confidence)"
              />
            </div>
          </ng-template>

          <div class="region-content">
            <div class="region-text">{{ selectedRegion.text }}</div>

            <p-divider />

            <div class="region-meta">
              <div class="meta-item">
                <span class="meta-label">Confidence:</span>
                <span class="meta-value">{{ (selectedRegion.confidence * 100).toFixed(1) }}%</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Position:</span>
                <span class="meta-value">
                  ({{ (selectedRegion.bounding_box.x * 100).toFixed(1) }}%,
                  {{ (selectedRegion.bounding_box.y * 100).toFixed(1) }}%)
                </span>
              </div>
              @if (selectedRegion.category) {
                <div class="meta-item">
                  <span class="meta-label">Category:</span>
                  <span class="meta-value">{{ selectedRegion.category }}</span>
                </div>
              }
              @if (selectedRegion.field_name) {
                <div class="meta-item">
                  <span class="meta-label">Field:</span>
                  <span class="meta-value">{{ selectedRegion.field_name }}</span>
                </div>
              }
            </div>
          </div>
        </p-card>
      }

      <!-- Full Text Display -->
      <p-card styleClass="full-text-card">
        <ng-template pTemplate="header">
          <div class="card-header">
            <span class="header-title">All Extracted Text</span>
            <span class="region-count">{{ getTotalRegions() }} regions</span>
          </div>
        </ng-template>

        <p-scrollPanel [style]="{ width: '100%', height: '300px' }">
          <div class="pages-container">
            @for (page of pages; track page.page_number) {
              <div class="page-section">
                <div class="page-header">
                  <i class="pi pi-file"></i>
                  Page {{ page.page_number }}
                  <span class="region-badge">{{ page.regions.length }} regions</span>
                </div>
                <div class="page-text">
                  @for (region of page.regions; track region.id) {
                    <span
                      class="text-region"
                      [class.selected]="isSelected(region)"
                      [class.high-confidence]="region.confidence >= 0.8"
                      [class.medium-confidence]="region.confidence >= 0.5 && region.confidence < 0.8"
                      [class.low-confidence]="region.confidence < 0.5"
                      [title]="'Confidence: ' + (region.confidence * 100).toFixed(1) + '%'"
                    >{{ region.text }}</span>
                  }
                </div>
              </div>
            }

            @if (pages.length === 0) {
              <div class="empty-state">
                <i class="pi pi-info-circle"></i>
                <span>No text extracted</span>
              </div>
            }
          </div>
        </p-scrollPanel>
      </p-card>
    </div>
  `,
  styles: [`
    .extraction-panel {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      height: 100%;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem 1rem;
      background: #f8f9fa;
      border-bottom: 1px solid #dee2e6;
    }

    .header-title {
      font-weight: 600;
      color: #343a40;
    }

    .region-count {
      font-size: 0.8rem;
      color: #6c757d;
    }

    :host ::ng-deep .region-details-card .p-card-body {
      padding: 0;
    }

    :host ::ng-deep .region-details-card .p-card-content {
      padding: 1rem;
    }

    :host ::ng-deep .full-text-card .p-card-body {
      padding: 0;
    }

    :host ::ng-deep .full-text-card .p-card-content {
      padding: 0;
    }

    .region-content {
      padding: 0.5rem;
    }

    .region-text {
      font-size: 1rem;
      line-height: 1.5;
      color: #212529;
      padding: 0.5rem;
      background: #f8f9fa;
      border-radius: 4px;
      word-break: break-word;
    }

    .region-meta {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.5rem;
    }

    .meta-item {
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
    }

    .meta-label {
      font-size: 0.75rem;
      color: #6c757d;
      text-transform: uppercase;
    }

    .meta-value {
      font-size: 0.875rem;
      color: #212529;
    }

    .pages-container {
      padding: 0.5rem;
    }

    .page-section {
      margin-bottom: 1rem;
    }

    .page-section:last-child {
      margin-bottom: 0;
    }

    .page-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.8rem;
      font-weight: 600;
      color: #495057;
      padding: 0.5rem;
      background: #e9ecef;
      border-radius: 4px;
      margin-bottom: 0.5rem;
    }

    .region-badge {
      margin-left: auto;
      font-weight: normal;
      color: #6c757d;
    }

    .page-text {
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem;
      padding: 0.5rem;
    }

    .text-region {
      display: inline-block;
      padding: 0.15rem 0.35rem;
      border-radius: 3px;
      font-size: 0.85rem;
      cursor: default;
      border: 1px solid transparent;
      transition: all 0.15s ease;
    }

    .text-region.high-confidence {
      background: rgba(40, 167, 69, 0.1);
    }

    .text-region.medium-confidence {
      background: rgba(255, 193, 7, 0.15);
    }

    .text-region.low-confidence {
      background: rgba(220, 53, 69, 0.1);
    }

    .text-region.selected {
      border-color: #007bff;
      background: rgba(0, 123, 255, 0.15);
      font-weight: 600;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
      padding: 2rem;
      color: #6c757d;
    }

    .empty-state i {
      font-size: 1.5rem;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExtractionPanelComponent {
  @Input() pages: PageExtraction[] = [];
  @Input() selectedRegion: TextRegion | null = null;

  getTotalRegions(): number {
    return this.pages.reduce((sum, page) => sum + page.regions.length, 0);
  }

  isSelected(region: TextRegion): boolean {
    return this.selectedRegion?.id === region.id;
  }

  getConfidenceLabel(confidence: number): string {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.5) return 'Medium';
    return 'Low';
  }

  getConfidenceSeverity(confidence: number): 'success' | 'warning' | 'danger' {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.5) return 'warning';
    return 'danger';
  }
}
