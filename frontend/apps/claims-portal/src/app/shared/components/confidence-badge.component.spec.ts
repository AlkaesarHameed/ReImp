/**
 * Unit tests for ConfidenceBadgeComponent
 *
 * Source: Design Doc 08 - TDD Implementation
 * Verified: 2025-12-21
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ConfidenceBadgeComponent } from './confidence-badge.component';

describe('ConfidenceBadgeComponent', () => {
  let component: ConfidenceBadgeComponent;
  let fixture: ComponentFixture<ConfidenceBadgeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConfidenceBadgeComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ConfidenceBadgeComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('Confidence Level Classification', () => {
    it('should classify scores >= 80% as high confidence', () => {
      component.score = 0.8;
      expect(component.confidenceLevel).toBe('high');

      component.score = 0.95;
      expect(component.confidenceLevel).toBe('high');

      component.score = 1.0;
      expect(component.confidenceLevel).toBe('high');
    });

    it('should classify scores 50-79% as medium confidence', () => {
      component.score = 0.5;
      expect(component.confidenceLevel).toBe('medium');

      component.score = 0.65;
      expect(component.confidenceLevel).toBe('medium');

      component.score = 0.79;
      expect(component.confidenceLevel).toBe('medium');
    });

    it('should classify scores < 50% as low confidence', () => {
      component.score = 0.49;
      expect(component.confidenceLevel).toBe('low');

      component.score = 0.25;
      expect(component.confidenceLevel).toBe('low');

      component.score = 0;
      expect(component.confidenceLevel).toBe('low');
    });

    it('should classify null/undefined scores as unknown', () => {
      component.score = null;
      expect(component.confidenceLevel).toBe('unknown');

      component.score = undefined;
      expect(component.confidenceLevel).toBe('unknown');
    });
  });

  describe('Score Normalization', () => {
    it('should handle decimal scores (0-1 range)', () => {
      component.score = 0.85;
      expect(component.normalizedScore).toBe(0.85);
      expect(component.displayScore).toBe('85%');
    });

    it('should handle percentage scores (0-100 range)', () => {
      component.score = 85;
      expect(component.normalizedScore).toBe(0.85);
      expect(component.displayScore).toBe('85%');
    });

    it('should handle edge case of exactly 1', () => {
      component.score = 1;
      expect(component.normalizedScore).toBe(1);
      expect(component.displayScore).toBe('100%');
    });

    it('should handle null score', () => {
      component.score = null;
      expect(component.normalizedScore).toBeNull();
    });
  });

  describe('Display Score Formatting', () => {
    it('should format score as percentage', () => {
      component.score = 0.875;
      expect(component.displayScore).toBe('88%'); // Rounded
    });

    it('should show N/A for missing scores by default', () => {
      component.score = null;
      component.showNaForMissing = true;
      expect(component.displayScore).toBe('N/A');
    });

    it('should show empty string when showNaForMissing is false', () => {
      component.score = null;
      component.showNaForMissing = false;
      expect(component.displayScore).toBe('');
    });
  });

  describe('Accessibility', () => {
    it('should have aria-label with full description', () => {
      component.score = 0.85;
      component.label = 'Patient name';
      expect(component.ariaLabel).toContain('Patient name');
      expect(component.ariaLabel).toContain('85%');
    });

    it('should have tooltip with confidence level', () => {
      component.score = 0.45;
      expect(component.tooltipText).toContain('Low confidence');
      expect(component.tooltipText).toContain('may need review');
    });
  });

  describe('Visual Rendering', () => {
    it('should apply high confidence class for scores >= 80%', () => {
      component.score = 0.9;
      fixture.detectChanges();

      const badge = fixture.nativeElement.querySelector('.confidence-badge');
      expect(badge.classList.contains('confidence-high')).toBe(true);
    });

    it('should apply medium confidence class for scores 50-79%', () => {
      component.score = 0.6;
      fixture.detectChanges();

      const badge = fixture.nativeElement.querySelector('.confidence-badge');
      expect(badge.classList.contains('confidence-medium')).toBe(true);
    });

    it('should apply low confidence class for scores < 50%', () => {
      component.score = 0.3;
      fixture.detectChanges();

      const badge = fixture.nativeElement.querySelector('.confidence-badge');
      expect(badge.classList.contains('confidence-low')).toBe(true);
    });

    it('should apply unknown confidence class for null scores', () => {
      component.score = null;
      fixture.detectChanges();

      const badge = fixture.nativeElement.querySelector('.confidence-badge');
      expect(badge.classList.contains('confidence-unknown')).toBe(true);
    });
  });
});
