/**
 * Confidence Legend Component.
 *
 * Displays color legend for extraction confidence levels.
 *
 * Source: Design Document 10 - Visual Extraction Display
 * Verified: 2025-12-24
 */
import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-confidence-legend',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="confidence-legend">
      <span class="legend-title">Confidence:</span>
      <div class="legend-items">
        <div class="legend-item">
          <span class="color-box high"></span>
          <span class="label">High (>80%)</span>
        </div>
        <div class="legend-item">
          <span class="color-box medium"></span>
          <span class="label">Medium (50-80%)</span>
        </div>
        <div class="legend-item">
          <span class="color-box low"></span>
          <span class="label">Low (&lt;50%)</span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .confidence-legend {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 0.5rem 1rem;
      background: #f8f9fa;
      border-radius: 4px;
      font-size: 0.8rem;
    }

    .legend-title {
      font-weight: 600;
      color: #495057;
    }

    .legend-items {
      display: flex;
      gap: 1rem;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }

    .color-box {
      width: 16px;
      height: 16px;
      border-radius: 3px;
      border: 1px solid rgba(0, 0, 0, 0.2);
    }

    .color-box.high {
      background: rgba(40, 167, 69, 0.4);
    }

    .color-box.medium {
      background: rgba(255, 193, 7, 0.4);
    }

    .color-box.low {
      background: rgba(220, 53, 69, 0.4);
    }

    .label {
      color: #6c757d;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ConfidenceLegendComponent {}
