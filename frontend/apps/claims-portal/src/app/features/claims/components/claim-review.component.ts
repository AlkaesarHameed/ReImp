/**
 * Claim Review Component.
 * Source: Design Document Section 3.2
 */
import { Component, ChangeDetectionStrategy, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';

@Component({
  selector: 'app-claim-review',
  standalone: true,
  imports: [CommonModule, CardModule, ButtonModule],
  template: `
    <div class="claim-review-container">
      <p-card header="Review Claim">
        <p>Claim ID: {{ id() }}</p>
        <p>This component will display the claim review workflow.</p>
        <div class="mt-4">
          <button pButton label="Approve" icon="pi pi-check" class="p-button-success mr-2"></button>
          <button pButton label="Deny" icon="pi pi-times" class="p-button-danger mr-2"></button>
          <button pButton label="Request Info" icon="pi pi-question" class="p-button-warning"></button>
        </div>
      </p-card>
    </div>
  `,
  styles: [`
    .claim-review-container {
      padding: 1.5rem;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClaimReviewComponent {
  readonly id = input.required<string>();
}
