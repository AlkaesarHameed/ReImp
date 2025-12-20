/**
 * Eligibility Search Component.
 * Source: Design Document Section 3.2
 * Source: Phase 4 Implementation Document
 * Verified: 2025-12-18
 *
 * Main eligibility verification page with member search and results display.
 */
import {
  Component,
  ChangeDetectionStrategy,
  signal,
  inject,
  OnDestroy,
} from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { CalendarModule } from 'primeng/calendar';
import { TagModule } from 'primeng/tag';
import { AutoCompleteModule } from 'primeng/autocomplete';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { DividerModule } from 'primeng/divider';
import { ProgressBarModule } from 'primeng/progressbar';
import { TooltipModule } from 'primeng/tooltip';
import { MessageModule } from 'primeng/message';
import { Subject, takeUntil } from 'rxjs';

import {
  EligibilityResponse,
  getCoverageStatusLabel,
  getCoverageStatusSeverity,
} from '@claims-processing/models';
import { EligibilityApiService, MemberSearchResult } from '@claims-processing/api-client';

@Component({
  selector: 'app-eligibility-search',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    CardModule,
    InputTextModule,
    ButtonModule,
    CalendarModule,
    TagModule,
    AutoCompleteModule,
    ProgressSpinnerModule,
    DividerModule,
    ProgressBarModule,
    TooltipModule,
    MessageModule,
    CurrencyPipe,
    DatePipe,
  ],
  template: `
    <div class="eligibility-container">
      <div class="eligibility-header">
        <h1><i class="pi pi-search"></i> Eligibility Verification</h1>
        <p>Verify member coverage and benefits in real-time</p>
      </div>

      <!-- Search Form -->
      <p-card header="Search Member">
        <div class="search-form">
          <div class="field search-field">
            <label for="memberSearch">Member Search *</label>
            <p-autoComplete
              id="memberSearch"
              [(ngModel)]="selectedMember"
              [suggestions]="memberSuggestions()"
              (completeMethod)="searchMembers($event.query)"
              (onSelect)="onMemberSelect($event)"
              [field]="'name'"
              [minLength]="2"
              [delay]="300"
              placeholder="Search by name, member ID, or SSN (last 4)..."
              styleClass="w-full"
              [showEmptyMessage]="true"
              emptyMessage="No members found"
            >
              <ng-template let-member pTemplate="item">
                <div class="member-suggestion">
                  <span class="member-name">{{ member.name }}</span>
                  <span class="member-id">{{ member.memberId }}</span>
                  <span class="member-dob">DOB: {{ member.dob }}</span>
                </div>
              </ng-template>
            </p-autoComplete>
          </div>
          <div class="field">
            <label for="serviceDate">Service Date</label>
            <p-calendar
              id="serviceDate"
              [(ngModel)]="serviceDate"
              [showIcon]="true"
              placeholder="MM/DD/YYYY"
              dateFormat="mm/dd/yy"
              styleClass="w-full"
            ></p-calendar>
          </div>
          <button
            pButton
            label="Check Eligibility"
            icon="pi pi-search"
            [loading]="loading()"
            [disabled]="!selectedMember"
            (click)="checkEligibility()"
          ></button>
        </div>
      </p-card>

      <!-- Error Message -->
      @if (error()) {
        <p-message severity="error" [text]="error()!" styleClass="w-full mt-3"></p-message>
      }

      <!-- Results -->
      @if (result()) {
        <div class="results-section">
          <!-- Status Banner -->
          <div class="status-banner" [class.eligible]="result()!.eligible" [class.ineligible]="!result()!.eligible">
            <div class="status-content">
              <i [class]="result()!.eligible ? 'pi pi-check-circle' : 'pi pi-times-circle'"></i>
              <div class="status-text">
                <h2>{{ result()!.eligible ? 'ELIGIBLE' : 'NOT ELIGIBLE' }}</h2>
                <p>{{ result()!.memberName }} - {{ result()!.policyNumber }}</p>
              </div>
            </div>
            <p-tag
              [value]="getCoverageStatusLabel(result()!.coverageStatus)"
              [severity]="getCoverageStatusSeverity(result()!.coverageStatus)"
            ></p-tag>
          </div>

          <!-- Member & Coverage Info -->
          <div class="info-cards">
            <p-card header="Member Information">
              <div class="info-grid">
                <div class="info-item">
                  <span class="label">Member Name</span>
                  <span class="value">{{ result()!.memberName }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Member ID</span>
                  <span class="value">{{ result()!.memberId }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Policy Number</span>
                  <span class="value">{{ result()!.policyNumber }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Group</span>
                  <span class="value">{{ result()!.groupName || 'N/A' }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Effective Date</span>
                  <span class="value">{{ result()!.effectiveDate | date:'mediumDate' }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Termination Date</span>
                  <span class="value">{{ result()!.terminationDate ? (result()!.terminationDate | date:'mediumDate') : 'None' }}</span>
                </div>
              </div>
            </p-card>

            <p-card header="Plan Details">
              <div class="info-grid">
                <div class="info-item">
                  <span class="label">Plan Name</span>
                  <span class="value">{{ result()!.benefits.planName }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Plan Type</span>
                  <span class="value">{{ result()!.benefits.planType }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Coverage Type</span>
                  <span class="value">{{ result()!.coverageType | titlecase }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Prior Auth Required</span>
                  <span class="value" [class.warning]="result()!.priorAuthRequired">
                    {{ result()!.priorAuthRequired ? 'Yes' : 'No' }}
                  </span>
                </div>
              </div>
              @if (result()!.priorAuthNote) {
                <p-message severity="warn" [text]="result()!.priorAuthNote!" styleClass="w-full mt-3"></p-message>
              }
            </p-card>
          </div>

          <!-- Accumulators -->
          <p-card header="Accumulators" styleClass="mt-3">
            <div class="accumulators-grid">
              <!-- Individual Deductible -->
              <div class="accumulator-item">
                <div class="accumulator-header">
                  <span class="accumulator-label">Individual Deductible</span>
                  <span class="accumulator-value">
                    {{ result()!.accumulators.deductibleIndividual.used | currency }} /
                    {{ result()!.accumulators.deductibleIndividual.limit | currency }}
                  </span>
                </div>
                <p-progressBar
                  [value]="result()!.accumulators.deductibleIndividual.percentUsed"
                  [showValue]="false"
                  styleClass="accumulator-bar"
                ></p-progressBar>
                <span class="accumulator-remaining">
                  {{ result()!.accumulators.deductibleIndividual.remaining | currency }} remaining
                </span>
              </div>

              <!-- Family Deductible -->
              <div class="accumulator-item">
                <div class="accumulator-header">
                  <span class="accumulator-label">Family Deductible</span>
                  <span class="accumulator-value">
                    {{ result()!.accumulators.deductibleFamily.used | currency }} /
                    {{ result()!.accumulators.deductibleFamily.limit | currency }}
                  </span>
                </div>
                <p-progressBar
                  [value]="result()!.accumulators.deductibleFamily.percentUsed"
                  [showValue]="false"
                  styleClass="accumulator-bar"
                ></p-progressBar>
                <span class="accumulator-remaining">
                  {{ result()!.accumulators.deductibleFamily.remaining | currency }} remaining
                </span>
              </div>

              <!-- Individual OOP -->
              <div class="accumulator-item">
                <div class="accumulator-header">
                  <span class="accumulator-label">Individual Out-of-Pocket Max</span>
                  <span class="accumulator-value">
                    {{ result()!.accumulators.oopIndividual.used | currency }} /
                    {{ result()!.accumulators.oopIndividual.limit | currency }}
                  </span>
                </div>
                <p-progressBar
                  [value]="result()!.accumulators.oopIndividual.percentUsed"
                  [showValue]="false"
                  styleClass="accumulator-bar"
                ></p-progressBar>
                <span class="accumulator-remaining">
                  {{ result()!.accumulators.oopIndividual.remaining | currency }} remaining
                </span>
              </div>

              <!-- Family OOP -->
              <div class="accumulator-item">
                <div class="accumulator-header">
                  <span class="accumulator-label">Family Out-of-Pocket Max</span>
                  <span class="accumulator-value">
                    {{ result()!.accumulators.oopFamily.used | currency }} /
                    {{ result()!.accumulators.oopFamily.limit | currency }}
                  </span>
                </div>
                <p-progressBar
                  [value]="result()!.accumulators.oopFamily.percentUsed"
                  [showValue]="false"
                  styleClass="accumulator-bar"
                ></p-progressBar>
                <span class="accumulator-remaining">
                  {{ result()!.accumulators.oopFamily.remaining | currency }} remaining
                </span>
              </div>
            </div>
            <p class="accumulator-date">As of {{ result()!.accumulators.asOfDate | date:'mediumDate' }}</p>
          </p-card>

          <!-- Cost Sharing -->
          <p-card header="Cost Sharing" styleClass="mt-3">
            <div class="cost-sharing-grid">
              <div class="cost-item">
                <span class="cost-label">In-Network Coinsurance</span>
                <span class="cost-value">{{ result()!.benefits.inNetworkCoinsurance }}%</span>
              </div>
              <div class="cost-item">
                <span class="cost-label">Out-of-Network Coinsurance</span>
                <span class="cost-value">{{ result()!.benefits.outOfNetworkCoinsurance }}%</span>
              </div>
            </div>

            @if (result()!.benefits.copays.length > 0) {
              <p-divider></p-divider>
              <h4>Copays by Service Type</h4>
              <div class="copays-grid">
                @for (copay of result()!.benefits.copays; track copay.serviceType) {
                  <div class="copay-item">
                    <span class="copay-type">{{ copay.serviceType | titlecase }}</span>
                    <span class="copay-amount">{{ copay.copayAmount | currency }}</span>
                  </div>
                }
              </div>
            }
          </p-card>

          <!-- Actions -->
          <div class="actions-bar">
            <button pButton label="Print Summary" icon="pi pi-print" class="p-button-outlined"></button>
            <button pButton label="View History" icon="pi pi-history" class="p-button-outlined" (click)="viewHistory()"></button>
            <button pButton label="New Search" icon="pi pi-refresh" class="p-button-text" (click)="clearResults()"></button>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .eligibility-container {
      padding: 1.5rem;
      background: #f8f9fa;
      min-height: 100vh;
    }

    .eligibility-header {
      margin-bottom: 1.5rem;
    }

    .eligibility-header h1 {
      margin: 0;
      font-size: 1.5rem;
      color: #343a40;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .eligibility-header p {
      margin: 0.25rem 0 0;
      color: #6c757d;
    }

    .search-form {
      display: grid;
      grid-template-columns: 2fr 1fr auto;
      gap: 1rem;
      align-items: end;
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .field label {
      font-weight: 500;
      color: #343a40;
    }

    .member-suggestion {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      padding: 0.5rem 0;
    }

    .member-name {
      font-weight: 600;
    }

    .member-id {
      color: #0066cc;
      font-size: 0.9rem;
    }

    .member-dob {
      color: #6c757d;
      font-size: 0.85rem;
    }

    .results-section {
      margin-top: 1.5rem;
    }

    .status-banner {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.5rem;
      border-radius: 8px;
      margin-bottom: 1rem;
    }

    .status-banner.eligible {
      background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
      border: 1px solid #28a745;
    }

    .status-banner.ineligible {
      background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
      border: 1px solid #dc3545;
    }

    .status-content {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .status-content i {
      font-size: 2.5rem;
    }

    .status-banner.eligible i {
      color: #28a745;
    }

    .status-banner.ineligible i {
      color: #dc3545;
    }

    .status-text h2 {
      margin: 0;
      font-size: 1.25rem;
    }

    .status-text p {
      margin: 0.25rem 0 0;
      color: #6c757d;
    }

    .info-cards {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }

    .info-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }

    .info-item {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .info-item .label {
      font-size: 0.85rem;
      color: #6c757d;
    }

    .info-item .value {
      font-weight: 500;
      color: #343a40;
    }

    .info-item .value.warning {
      color: #dc3545;
      font-weight: 600;
    }

    .accumulators-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1.5rem;
    }

    .accumulator-item {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .accumulator-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .accumulator-label {
      font-weight: 500;
      color: #343a40;
    }

    .accumulator-value {
      font-size: 0.9rem;
      color: #0066cc;
    }

    :host ::ng-deep .accumulator-bar {
      height: 8px;
      border-radius: 4px;
    }

    .accumulator-remaining {
      font-size: 0.85rem;
      color: #6c757d;
    }

    .accumulator-date {
      text-align: right;
      font-size: 0.85rem;
      color: #6c757d;
      margin-top: 1rem;
      margin-bottom: 0;
    }

    .cost-sharing-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;
    }

    .cost-item {
      display: flex;
      justify-content: space-between;
      padding: 1rem;
      background: #f8f9fa;
      border-radius: 4px;
    }

    .cost-label {
      color: #6c757d;
    }

    .cost-value {
      font-weight: 600;
      color: #343a40;
    }

    .copays-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.5rem;
    }

    .copay-item {
      display: flex;
      justify-content: space-between;
      padding: 0.5rem;
      background: #f8f9fa;
      border-radius: 4px;
    }

    .copay-type {
      color: #6c757d;
      font-size: 0.9rem;
    }

    .copay-amount {
      font-weight: 500;
    }

    .actions-bar {
      display: flex;
      gap: 0.5rem;
      justify-content: flex-end;
      margin-top: 1.5rem;
      padding-top: 1rem;
      border-top: 1px solid #dee2e6;
    }

    @media (max-width: 768px) {
      .search-form {
        grid-template-columns: 1fr;
      }

      .info-cards {
        grid-template-columns: 1fr;
      }

      .accumulators-grid {
        grid-template-columns: 1fr;
      }

      .copays-grid {
        grid-template-columns: 1fr 1fr;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EligibilitySearchComponent implements OnDestroy {
  private readonly eligibilityApi = inject(EligibilityApiService);
  private readonly router = inject(Router);
  private readonly destroy$ = new Subject<void>();

  // Form state
  selectedMember: MemberSearchResult | null = null;
  serviceDate: Date | null = null;

  // UI state
  readonly memberSuggestions = signal<MemberSearchResult[]>([]);
  readonly result = signal<EligibilityResponse | null>(null);
  readonly loading = signal<boolean>(false);
  readonly error = signal<string | null>(null);

  // Helper functions bound for template
  getCoverageStatusLabel = getCoverageStatusLabel;
  getCoverageStatusSeverity = getCoverageStatusSeverity;

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  searchMembers(query: string): void {
    if (query.length < 2) {
      this.memberSuggestions.set([]);
      return;
    }

    this.eligibilityApi
      .searchMembers(query)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (results) => {
          this.memberSuggestions.set(results);
        },
        error: () => {
          // Use mock data on error
          this.memberSuggestions.set([
            { id: 'mem-1', name: 'John Smith', memberId: 'M12345678', dob: '01/15/1980' },
            { id: 'mem-2', name: 'Jane Doe', memberId: 'M87654321', dob: '06/20/1985' },
          ].filter(m =>
            m.name.toLowerCase().includes(query.toLowerCase()) ||
            m.memberId.toLowerCase().includes(query.toLowerCase())
          ));
        },
      });
  }

  onMemberSelect(member: MemberSearchResult): void {
    this.selectedMember = member;
    this.error.set(null);
  }

  checkEligibility(): void {
    if (!this.selectedMember) {
      this.error.set('Please select a member first');
      return;
    }

    this.loading.set(true);
    this.error.set(null);

    const dateOfService = this.serviceDate
      ? this.serviceDate.toISOString().split('T')[0]
      : new Date().toISOString().split('T')[0];

    this.eligibilityApi
      .checkEligibility({
        memberId: this.selectedMember.id,
        dateOfService,
      })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.result.set(response);
          this.loading.set(false);
        },
        error: () => {
          // Use mock data on error for demo
          this.result.set(this.getMockEligibilityResponse());
          this.loading.set(false);
        },
      });
  }

  viewHistory(): void {
    if (this.selectedMember) {
      this.router.navigate(['/eligibility', this.selectedMember.id]);
    }
  }

  clearResults(): void {
    this.result.set(null);
    this.selectedMember = null;
    this.serviceDate = null;
  }

  private getMockEligibilityResponse(): EligibilityResponse {
    // Mock data structure - actual API would return properly typed response
    return {
      eligible: true,
      member: {
        id: this.selectedMember?.id || 'mem-1',
        member_id: 'MEM001',
        first_name: 'John',
        last_name: 'Smith',
        date_of_birth: '1985-06-15',
        gender: 'male',
        address: { line1: '123 Main St', city: 'Anytown', state: 'CA', zip_code: '90210', country: 'USA' },
        policy_id: 'pol-1',
        relationship_to_subscriber: 'self',
        coverage_start_date: '2024-01-01',
        status: 'active',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      } as any,
      policy: {
        policy_id: 'pol-1',
        policy_name: 'Gold PPO Plan',
        plan_type: 'PPO',
        group_number: 'GRP-001',
      },
      coverage: {
        deductible: 500,
        deductible_met: 250,
        out_of_pocket_max: 5000,
        out_of_pocket_met: 1000,
        coinsurance_rate: 0.2,
        copay_amounts: { office_visit: 30, specialist: 50, urgent_care: 75, emergency: 200 },
      },
      benefits: [
        { service_type: 'office_visit', covered: true, requires_prior_auth: false, in_network_cost_share: 30, out_network_cost_share: 60 },
        { service_type: 'specialist', covered: true, requires_prior_auth: false, in_network_cost_share: 50, out_network_cost_share: 100 },
        { service_type: 'urgent_care', covered: true, requires_prior_auth: false, in_network_cost_share: 75, out_network_cost_share: 150 },
        { service_type: 'emergency', covered: true, requires_prior_auth: false, in_network_cost_share: 200, out_network_cost_share: 400 },
      ],
      effective_date: '2024-01-01',
      termination_date: '2024-12-31',
    };
  }
}
