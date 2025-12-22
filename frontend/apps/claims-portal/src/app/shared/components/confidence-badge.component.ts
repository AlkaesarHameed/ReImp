/**
 * Confidence Badge Component
 *
 * A reusable component that displays extraction confidence scores
 * with color-coded visual indicators.
 *
 * Source: Design Doc 08 Section 12.3 - ConfidenceBadgeComponent
 * Verified: 2025-12-21
 */

import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Confidence thresholds for color coding
 * - High: >= 80% (green)
 * - Medium: 50-79% (yellow/amber)
 * - Low: < 50% (red)
 */
const CONFIDENCE_THRESHOLDS = {
  HIGH: 0.8,
  MEDIUM: 0.5,
} as const;

@Component({
  selector: 'app-confidence-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span
      class="confidence-badge"
      [class.confidence-high]="confidenceLevel === 'high'"
      [class.confidence-medium]="confidenceLevel === 'medium'"
      [class.confidence-low]="confidenceLevel === 'low'"
      [class.confidence-unknown]="confidenceLevel === 'unknown'"
      [attr.title]="tooltipText"
      [attr.aria-label]="ariaLabel"
    >
      {{ displayScore }}
    </span>
  `,
  styles: [`
    .confidence-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      min-width: 42px;
      text-align: center;
    }

    .confidence-high {
      background-color: #d4edda;
      color: #155724;
      border: 1px solid #c3e6cb;
    }

    .confidence-medium {
      background-color: #fff3cd;
      color: #856404;
      border: 1px solid #ffeeba;
    }

    .confidence-low {
      background-color: #f8d7da;
      color: #721c24;
      border: 1px solid #f5c6cb;
    }

    .confidence-unknown {
      background-color: #e2e3e5;
      color: #6c757d;
      border: 1px solid #d6d8db;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ConfidenceBadgeComponent {
  /**
   * The confidence score (0-1 or 0-100)
   * Values > 1 are treated as percentages
   */
  @Input() score: number | undefined | null = null;

  /**
   * Whether to show "N/A" for missing scores
   * Default: true
   */
  @Input() showNaForMissing = true;

  /**
   * Optional label for accessibility
   */
  @Input() label = 'Confidence score';

  /**
   * Get the normalized score (0-1 range)
   */
  get normalizedScore(): number | null {
    if (this.score === null || this.score === undefined) {
      return null;
    }

    // Handle percentage values (> 1)
    if (this.score > 1) {
      return this.score / 100;
    }

    return this.score;
  }

  /**
   * Get the confidence level classification
   */
  get confidenceLevel(): 'high' | 'medium' | 'low' | 'unknown' {
    const score = this.normalizedScore;

    if (score === null) {
      return 'unknown';
    }

    if (score >= CONFIDENCE_THRESHOLDS.HIGH) {
      return 'high';
    }

    if (score >= CONFIDENCE_THRESHOLDS.MEDIUM) {
      return 'medium';
    }

    return 'low';
  }

  /**
   * Get the display score string
   */
  get displayScore(): string {
    const score = this.normalizedScore;

    if (score === null) {
      return this.showNaForMissing ? 'N/A' : '';
    }

    return `${Math.round(score * 100)}%`;
  }

  /**
   * Get tooltip text with more details
   */
  get tooltipText(): string {
    const level = this.confidenceLevel;

    if (level === 'unknown') {
      return 'Confidence score not available';
    }

    const levelLabel =
      level === 'high' ? 'High confidence' :
      level === 'medium' ? 'Medium confidence' :
      'Low confidence - may need review';

    return `${this.displayScore} - ${levelLabel}`;
  }

  /**
   * Get ARIA label for accessibility
   */
  get ariaLabel(): string {
    return `${this.label}: ${this.tooltipText}`;
  }
}
