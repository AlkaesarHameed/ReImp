/**
 * Skip Link Component.
 * Source: Phase 6 Implementation Document
 *
 * WCAG 2.1 AA compliant skip navigation link.
 * Allows keyboard users to skip directly to main content.
 */
import { Component, ChangeDetectionStrategy } from '@angular/core';

@Component({
  selector: 'app-skip-link',
  standalone: true,
  template: `
    <a href="#main-content" class="skip-link">
      Skip to main content
    </a>
  `,
  styles: [`
    .skip-link {
      position: absolute;
      top: -100px;
      left: 0;
      background: #0066CC;
      color: white;
      padding: 0.75rem 1.5rem;
      z-index: 10000;
      font-weight: 600;
      text-decoration: none;
      border-radius: 0 0 4px 0;
      transition: top 0.2s ease;
    }

    .skip-link:focus {
      top: 0;
      outline: 3px solid #FFC107;
      outline-offset: 2px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SkipLinkComponent {}
