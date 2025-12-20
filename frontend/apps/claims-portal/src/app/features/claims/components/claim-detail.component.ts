/**
 * Claim Detail Component.
 * Source: Design Document Section 3.2
 */
import { Component, ChangeDetectionStrategy, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';

@Component({
  selector: 'app-claim-detail',
  standalone: true,
  imports: [CommonModule, CardModule, ButtonModule],
  template: `
    <div class="claim-detail-container">
      <p-card header="Claim Details">
        <p>Claim ID: {{ id() }}</p>
        <p>This component will display full claim details.</p>
      </p-card>
    </div>
  `,
  styles: [`
    .claim-detail-container {
      padding: 1.5rem;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClaimDetailComponent {
  readonly id = input.required<string>();
}
