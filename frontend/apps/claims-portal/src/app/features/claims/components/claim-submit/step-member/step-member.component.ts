/**
 * Step Member Component.
 * Source: Phase 3 Implementation Document
 * Source: Design Document Section 3.4
 * Verified: 2025-12-18
 *
 * First step of claim submission wizard - Member selection and eligibility verification.
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
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { AutoCompleteModule } from 'primeng/autocomplete';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { MessageModule } from 'primeng/message';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { DividerModule } from 'primeng/divider';
import { Subject, distinctUntilChanged, takeUntil } from 'rxjs';

import {
  MemberStepData,
  EligibilityCheckResponse,
  Member,
} from '@claims-processing/models';

@Component({
  selector: 'app-step-member',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    AutoCompleteModule,
    InputTextModule,
    ButtonModule,
    CardModule,
    MessageModule,
    ProgressSpinnerModule,
    DividerModule,
  ],
  template: `
    <div class="step-member">
      <h3>Step 1: Select Member</h3>
      <p class="step-description">Search for the member and verify their eligibility.</p>

      <form [formGroup]="form" class="member-form">
        <!-- Member Search -->
        <div class="field">
          <label for="memberSearch">Member Search *</label>
          <p-autoComplete
            id="memberSearch"
            formControlName="memberSearch"
            [suggestions]="memberSuggestions()"
            (completeMethod)="onMemberSearch($event.query)"
            (onSelect)="selectMember($event)"
            [field]="'display'"
            [minLength]="2"
            [delay]="300"
            placeholder="Search by name or member ID..."
            styleClass="w-full"
            [showEmptyMessage]="true"
            emptyMessage="No members found"
          >
            <ng-template let-member pTemplate="item">
              <div class="member-suggestion">
                <span class="member-name">{{ member.first_name }} {{ member.last_name }}</span>
                <span class="member-id">{{ member.member_number }}</span>
                <span class="member-dob">DOB: {{ member.date_of_birth | date:'shortDate' }}</span>
              </div>
            </ng-template>
          </p-autoComplete>
          @if (form.get('memberSearch')?.hasError('required') && form.get('memberSearch')?.touched) {
            <small class="p-error" role="alert">Member is required</small>
          }
        </div>

        <!-- Hidden fields for actual values -->
        <input type="hidden" formControlName="memberId" />
        <input type="hidden" formControlName="policyId" />

        <!-- Selected Member Display -->
        @if (selectedMember()) {
          <p-card styleClass="selected-member-card">
            <div class="selected-member">
              <div class="member-info">
                <h4>{{ selectedMember()?.first_name }} {{ selectedMember()?.last_name }}</h4>
                <div class="member-details">
                  <span><strong>Member ID:</strong> {{ selectedMember()?.member_number }}</span>
                  <span><strong>DOB:</strong> {{ selectedMember()?.date_of_birth | date:'mediumDate' }}</span>
                  <span><strong>Policy:</strong> {{ form.get('policyId')?.value }}</span>
                </div>
              </div>

              <div class="eligibility-actions">
                @if (!eligibilityVerified()) {
                  <button
                    pButton
                    type="button"
                    label="Verify Eligibility"
                    icon="pi pi-check-circle"
                    [loading]="verifying()"
                    (click)="verifyEligibility()"
                    class="p-button-outlined"
                  ></button>
                } @else {
                  <span class="eligibility-badge" [class.eligible]="eligibilityResponse()?.eligible" [class.ineligible]="!eligibilityResponse()?.eligible">
                    <i [class]="eligibilityResponse()?.eligible ? 'pi pi-check-circle' : 'pi pi-times-circle'"></i>
                    {{ eligibilityResponse()?.eligible ? 'Eligible' : 'Not Eligible' }}
                  </span>
                }
              </div>
            </div>
          </p-card>
        }

        <!-- Eligibility Details -->
        @if (eligibilityVerified() && eligibilityResponse()) {
          <p-card styleClass="eligibility-card">
            <ng-template pTemplate="header">
              <div class="eligibility-header">
                <h4>Coverage Details</h4>
                <span class="coverage-type">{{ eligibilityResponse()?.coverageType }}</span>
              </div>
            </ng-template>

            <div class="eligibility-details">
              <div class="detail-row">
                <span class="label">Effective Date:</span>
                <span class="value">{{ eligibilityResponse()?.effectiveDate | date:'mediumDate' }}</span>
              </div>
              @if (eligibilityResponse()?.terminationDate) {
                <div class="detail-row">
                  <span class="label">Termination Date:</span>
                  <span class="value">{{ eligibilityResponse()?.terminationDate | date:'mediumDate' }}</span>
                </div>
              }

              <p-divider></p-divider>

              <div class="benefits-grid">
                @if (eligibilityResponse()?.copay !== undefined) {
                  <div class="benefit-item">
                    <span class="benefit-label">Copay</span>
                    <span class="benefit-value">{{ eligibilityResponse()?.copay | currency }}</span>
                  </div>
                }
                @if (eligibilityResponse()?.deductible !== undefined) {
                  <div class="benefit-item">
                    <span class="benefit-label">Deductible</span>
                    <span class="benefit-value">
                      {{ eligibilityResponse()?.deductibleMet | currency }} / {{ eligibilityResponse()?.deductible | currency }}
                    </span>
                  </div>
                }
                @if (eligibilityResponse()?.outOfPocketMax !== undefined) {
                  <div class="benefit-item">
                    <span class="benefit-label">Out of Pocket Max</span>
                    <span class="benefit-value">
                      {{ eligibilityResponse()?.outOfPocketMet | currency }} / {{ eligibilityResponse()?.outOfPocketMax | currency }}
                    </span>
                  </div>
                }
              </div>
            </div>
          </p-card>
        }

        <!-- Error Message -->
        @if (error()) {
          <p-message severity="error" [text]="error()!" styleClass="w-full mt-3"></p-message>
        }

        <!-- Not Eligible Warning -->
        @if (eligibilityVerified() && !eligibilityResponse()?.eligible) {
          <p-message
            severity="warn"
            text="This member is not currently eligible. You may still submit the claim for review."
            styleClass="w-full mt-3"
          ></p-message>
        }
      </form>

      <!-- Navigation -->
      <div class="step-navigation">
        <button
          pButton
          type="button"
          label="Next"
          icon="pi pi-arrow-right"
          iconPos="right"
          [disabled]="!canProceed()"
          (click)="onNext()"
        ></button>
      </div>
    </div>
  `,
  styles: [`
    .step-member {
      padding: 1rem;
    }

    .step-description {
      color: #6c757d;
      margin-bottom: 1.5rem;
    }

    .member-form {
      max-width: 800px;
    }

    .field {
      margin-bottom: 1.5rem;
    }

    .field label {
      display: block;
      margin-bottom: 0.5rem;
      font-weight: 500;
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

    .selected-member-card {
      margin-top: 1rem;
      background: #f8f9fa;
    }

    .selected-member {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 1rem;
    }

    .member-info h4 {
      margin: 0 0 0.5rem;
    }

    .member-details {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      color: #6c757d;
      font-size: 0.9rem;
    }

    .eligibility-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      border-radius: 4px;
      font-weight: 500;
    }

    .eligibility-badge.eligible {
      background: #d4edda;
      color: #155724;
    }

    .eligibility-badge.ineligible {
      background: #f8d7da;
      color: #721c24;
    }

    .eligibility-card {
      margin-top: 1rem;
    }

    .eligibility-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      background: #f8f9fa;
    }

    .eligibility-header h4 {
      margin: 0;
    }

    .coverage-type {
      background: #0066cc;
      color: white;
      padding: 0.25rem 0.75rem;
      border-radius: 4px;
      font-size: 0.85rem;
    }

    .eligibility-details {
      padding: 1rem;
    }

    .detail-row {
      display: flex;
      justify-content: space-between;
      padding: 0.5rem 0;
    }

    .detail-row .label {
      color: #6c757d;
    }

    .benefits-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-top: 1rem;
    }

    .benefit-item {
      background: #f8f9fa;
      padding: 1rem;
      border-radius: 4px;
      text-align: center;
    }

    .benefit-label {
      display: block;
      color: #6c757d;
      font-size: 0.85rem;
      margin-bottom: 0.25rem;
    }

    .benefit-value {
      font-size: 1.1rem;
      font-weight: 600;
    }

    .step-navigation {
      display: flex;
      justify-content: flex-end;
      margin-top: 2rem;
      padding-top: 1rem;
      border-top: 1px solid #dee2e6;
    }

    @media (max-width: 768px) {
      .selected-member {
        flex-direction: column;
      }

      .benefits-grid {
        grid-template-columns: 1fr;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StepMemberComponent implements OnInit, OnDestroy {
  private readonly fb = inject(FormBuilder);
  private readonly destroy$ = new Subject<void>();

  @Input() initialData?: MemberStepData;

  @Output() stepComplete = new EventEmitter<MemberStepData>();
  @Output() dirty = new EventEmitter<boolean>();

  // Form
  form: FormGroup = this.fb.group({
    memberSearch: [''],
    memberId: ['', Validators.required],
    policyId: ['', Validators.required],
  });

  // State
  readonly memberSuggestions = signal<any[]>([]);
  readonly selectedMember = signal<Member | null>(null);
  readonly eligibilityVerified = signal<boolean>(false);
  readonly eligibilityResponse = signal<EligibilityCheckResponse | null>(null);
  readonly verifying = signal<boolean>(false);
  readonly error = signal<string | null>(null);

  // Computed
  readonly canProceed = computed(() =>
    this.form.valid && this.eligibilityVerified()
  );

  ngOnInit(): void {
    // Load initial data if provided
    if (this.initialData) {
      this.form.patchValue({
        memberId: this.initialData.memberId,
        policyId: this.initialData.policyId,
      });
      this.eligibilityVerified.set(this.initialData.eligibilityVerified);
      if (this.initialData.eligibilityResponse) {
        this.eligibilityResponse.set(this.initialData.eligibilityResponse);
      }
    }

    // Track dirty state
    this.form.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.dirty.emit(this.form.dirty);
      });

    // Reset eligibility when member changes
    this.form.get('memberId')?.valueChanges
      .pipe(
        takeUntil(this.destroy$),
        distinctUntilChanged()
      )
      .subscribe(() => {
        if (this.eligibilityVerified()) {
          this.eligibilityVerified.set(false);
          this.eligibilityResponse.set(null);
        }
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  onMemberSearch(query: string): void {
    if (query.length < 2) {
      this.memberSuggestions.set([]);
      return;
    }

    // Mock data for now - would call MembersApiService
    const mockResults = [
      {
        id: 'MEM-001',
        first_name: 'John',
        last_name: 'Doe',
        date_of_birth: '1980-01-15',
        member_number: 'M12345678',
        policy_id: 'POL-001',
        display: 'John Doe (M12345678)',
      },
      {
        id: 'MEM-002',
        first_name: 'Jane',
        last_name: 'Smith',
        date_of_birth: '1975-06-20',
        member_number: 'M87654321',
        policy_id: 'POL-002',
        display: 'Jane Smith (M87654321)',
      },
    ].filter(m =>
      m.first_name.toLowerCase().includes(query.toLowerCase()) ||
      m.last_name.toLowerCase().includes(query.toLowerCase()) ||
      m.member_number.toLowerCase().includes(query.toLowerCase())
    );

    this.memberSuggestions.set(mockResults);
  }

  selectMember(member: any): void {
    this.selectedMember.set(member);
    this.form.patchValue({
      memberId: member.id,
      policyId: member.policy_id,
    });
    this.error.set(null);
  }

  verifyEligibility(): void {
    if (!this.form.get('memberId')?.value || !this.form.get('policyId')?.value) {
      return;
    }

    this.verifying.set(true);
    this.error.set(null);

    // Mock eligibility check - would call EligibilityApiService
    setTimeout(() => {
      const mockResponse: EligibilityCheckResponse = {
        eligible: true,
        effectiveDate: '2024-01-01',
        terminationDate: '2024-12-31',
        coverageType: 'PPO',
        copay: 30,
        deductible: 500,
        deductibleMet: 250,
        outOfPocketMax: 5000,
        outOfPocketMet: 1000,
      };

      this.eligibilityResponse.set(mockResponse);
      this.eligibilityVerified.set(true);
      this.verifying.set(false);
    }, 1000);
  }

  onNext(): void {
    if (!this.canProceed()) {
      this.form.markAllAsTouched();
      return;
    }

    const stepData: MemberStepData = {
      memberId: this.form.get('memberId')?.value,
      policyId: this.form.get('policyId')?.value,
      eligibilityVerified: this.eligibilityVerified(),
      eligibilityResponse: this.eligibilityResponse() ?? undefined,
    };

    this.stepComplete.emit(stepData);
  }
}
