/**
 * Step Provider Component.
 * Source: Phase 3 Implementation Document
 * Source: Design Document Section 3.4
 * Verified: 2025-12-18
 *
 * Second step of claim submission wizard - Provider selection and NPI verification.
 */
import {
  Component,
  ChangeDetectionStrategy,
  Input,
  Output,
  EventEmitter,
  inject,
  signal,
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
import { DropdownModule } from 'primeng/dropdown';
import { MessageModule } from 'primeng/message';
import { Subject, takeUntil } from 'rxjs';

import { ProviderStepData } from '@claims-processing/models';

@Component({
  selector: 'app-step-provider',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    AutoCompleteModule,
    InputTextModule,
    ButtonModule,
    CardModule,
    DropdownModule,
    MessageModule,
  ],
  template: `
    <div class="step-provider">
      <h3>Step 2: Select Provider</h3>
      <p class="step-description">Search for the rendering provider and select place of service.</p>

      <form [formGroup]="form" class="provider-form">
        <!-- Provider Search -->
        <div class="field">
          <label for="providerSearch">Provider Search *</label>
          <p-autoComplete
            id="providerSearch"
            formControlName="providerSearch"
            [suggestions]="providerSuggestions()"
            (completeMethod)="onProviderSearch($event.query)"
            (onSelect)="selectProvider($event)"
            [field]="'display'"
            [minLength]="2"
            [delay]="300"
            placeholder="Search by name or NPI..."
            styleClass="w-full"
            [showEmptyMessage]="true"
            emptyMessage="No providers found"
          >
            <ng-template let-provider pTemplate="item">
              <div class="provider-suggestion">
                <span class="provider-name">{{ provider.name }}</span>
                <span class="provider-specialty">{{ provider.specialty }}</span>
                <span class="provider-npi">NPI: {{ provider.npi }}</span>
              </div>
            </ng-template>
          </p-autoComplete>
        </div>

        <!-- Hidden fields -->
        <input type="hidden" formControlName="providerId" />

        <!-- Selected Provider Display -->
        @if (selectedProvider()) {
          <p-card styleClass="selected-provider-card">
            <div class="selected-provider">
              <div class="provider-info">
                <h4>{{ selectedProvider()?.name }}</h4>
                <div class="provider-details">
                  <span><strong>NPI:</strong> {{ selectedProvider()?.npi }}</span>
                  <span><strong>Specialty:</strong> {{ selectedProvider()?.specialty }}</span>
                  <span><strong>Address:</strong> {{ selectedProvider()?.address }}, {{ selectedProvider()?.city }}, {{ selectedProvider()?.state }} {{ selectedProvider()?.zip }}</span>
                </div>
              </div>
              @if (npiVerified()) {
                <span class="verified-badge">
                  <i class="pi pi-verified"></i> NPI Verified
                </span>
              }
            </div>
          </p-card>
        }

        <!-- NPI Field (manual entry) -->
        <div class="field">
          <label for="providerNPI">Provider NPI *</label>
          <div class="npi-input-group">
            <input
              pInputText
              id="providerNPI"
              formControlName="providerNPI"
              placeholder="10-digit NPI"
              maxlength="10"
              class="w-full"
            />
            <button
              pButton
              type="button"
              icon="pi pi-check"
              [loading]="verifyingNPI()"
              (click)="verifyNPI()"
              [disabled]="!form.get('providerNPI')?.valid"
              pTooltip="Verify NPI"
            ></button>
          </div>
          @if (form.get('providerNPI')?.hasError('required') && form.get('providerNPI')?.touched) {
            <small class="p-error">NPI is required</small>
          }
          @if (form.get('providerNPI')?.hasError('pattern') && form.get('providerNPI')?.touched) {
            <small class="p-error">NPI must be 10 digits</small>
          }
        </div>

        <!-- Place of Service -->
        <div class="field">
          <label for="placeOfService">Place of Service *</label>
          <p-dropdown
            id="placeOfService"
            formControlName="placeOfService"
            [options]="posCodeOptions()"
            optionLabel="label"
            optionValue="value"
            placeholder="Select place of service"
            styleClass="w-full"
            [filter]="true"
            filterBy="label"
          ></p-dropdown>
          @if (form.get('placeOfService')?.hasError('required') && form.get('placeOfService')?.touched) {
            <small class="p-error">Place of service is required</small>
          }
        </div>

        <!-- Prior Authorization (Optional) -->
        <div class="field">
          <label for="priorAuthNumber">Prior Authorization Number (Optional)</label>
          <input
            pInputText
            id="priorAuthNumber"
            formControlName="priorAuthNumber"
            placeholder="Enter prior auth number if applicable"
            class="w-full"
          />
        </div>

        <!-- Referring Provider (Optional) -->
        <div class="field">
          <label for="referringProviderId">Referring Provider (Optional)</label>
          <p-autoComplete
            id="referringProviderId"
            formControlName="referringProviderId"
            [suggestions]="referringProviderSuggestions()"
            (completeMethod)="onReferringProviderSearch($event.query)"
            [field]="'display'"
            [minLength]="2"
            placeholder="Search referring provider..."
            styleClass="w-full"
          ></p-autoComplete>
        </div>

        <!-- Error Message -->
        @if (error()) {
          <p-message severity="error" [text]="error()!" styleClass="w-full mt-3"></p-message>
        }
      </form>

      <!-- Navigation -->
      <div class="step-navigation">
        <button
          pButton
          type="button"
          label="Back"
          icon="pi pi-arrow-left"
          class="p-button-outlined"
          (click)="onBack()"
        ></button>
        <button
          pButton
          type="button"
          label="Next"
          icon="pi pi-arrow-right"
          iconPos="right"
          [disabled]="!form.valid"
          (click)="onNext()"
        ></button>
      </div>
    </div>
  `,
  styles: [`
    .step-provider {
      padding: 1rem;
    }

    .step-description {
      color: #6c757d;
      margin-bottom: 1.5rem;
    }

    .provider-form {
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

    .provider-suggestion {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      padding: 0.5rem 0;
    }

    .provider-name {
      font-weight: 600;
    }

    .provider-specialty {
      color: #6c757d;
      font-size: 0.9rem;
    }

    .provider-npi {
      color: #0066cc;
      font-size: 0.85rem;
    }

    .selected-provider-card {
      margin-bottom: 1.5rem;
      background: #f8f9fa;
    }

    .selected-provider {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .provider-info h4 {
      margin: 0 0 0.5rem;
    }

    .provider-details {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      color: #6c757d;
      font-size: 0.9rem;
    }

    .verified-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: #d4edda;
      color: #155724;
      padding: 0.5rem 1rem;
      border-radius: 4px;
      font-size: 0.85rem;
    }

    .npi-input-group {
      display: flex;
      gap: 0.5rem;
    }

    .npi-input-group input {
      flex: 1;
    }

    .step-navigation {
      display: flex;
      justify-content: space-between;
      margin-top: 2rem;
      padding-top: 1rem;
      border-top: 1px solid #dee2e6;
    }

    @media (max-width: 768px) {
      .selected-provider {
        flex-direction: column;
        gap: 1rem;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StepProviderComponent implements OnInit, OnDestroy {
  private readonly fb = inject(FormBuilder);
  private readonly destroy$ = new Subject<void>();

  @Input() initialData?: ProviderStepData;

  @Output() stepComplete = new EventEmitter<ProviderStepData>();
  @Output() stepBack = new EventEmitter<void>();
  @Output() dirty = new EventEmitter<boolean>();

  // Form
  form: FormGroup = this.fb.group({
    providerSearch: [''],
    providerId: ['', Validators.required],
    providerNPI: ['', [Validators.required, Validators.pattern(/^\d{10}$/)]],
    placeOfService: ['', Validators.required],
    priorAuthNumber: [''],
    referringProviderId: [''],
  });

  // State
  readonly providerSuggestions = signal<any[]>([]);
  readonly referringProviderSuggestions = signal<any[]>([]);
  readonly selectedProvider = signal<any | null>(null);
  readonly posCodeOptions = signal<{ label: string; value: string }[]>([]);
  readonly npiVerified = signal<boolean>(false);
  readonly verifyingNPI = signal<boolean>(false);
  readonly error = signal<string | null>(null);

  ngOnInit(): void {
    // Load POS codes
    this.loadPOSCodes();

    // Load initial data if provided
    if (this.initialData) {
      this.form.patchValue({
        providerId: this.initialData.providerId,
        providerNPI: this.initialData.providerNPI,
        placeOfService: this.initialData.placeOfService,
        priorAuthNumber: this.initialData.priorAuthNumber || '',
        referringProviderId: this.initialData.referringProviderId || '',
      });
    }

    // Track dirty state
    this.form.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.dirty.emit(this.form.dirty);
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadPOSCodes(): void {
    // Mock POS codes - would call lookupApi.getPlaceOfServiceCodes()
    const mockPOS = [
      { code: '11', name: 'Office' },
      { code: '21', name: 'Inpatient Hospital' },
      { code: '22', name: 'Outpatient Hospital' },
      { code: '23', name: 'Emergency Room - Hospital' },
      { code: '31', name: 'Skilled Nursing Facility' },
      { code: '81', name: 'Independent Laboratory' },
    ];

    this.posCodeOptions.set(
      mockPOS.map(pos => ({ label: `${pos.code} - ${pos.name}`, value: pos.code }))
    );
  }

  onProviderSearch(query: string): void {
    if (query.length < 2) {
      this.providerSuggestions.set([]);
      return;
    }

    // Mock data - would call ProvidersApiService
    const mockResults = [
      {
        id: 'PRV-001',
        npi: '1234567890',
        name: 'Dr. Jane Smith',
        specialty: 'Internal Medicine',
        address: '123 Medical Way',
        city: 'Boston',
        state: 'MA',
        zip: '02101',
        display: 'Dr. Jane Smith (1234567890)',
      },
      {
        id: 'PRV-002',
        npi: '0987654321',
        name: 'Dr. John Davis',
        specialty: 'Family Medicine',
        address: '456 Health St',
        city: 'Cambridge',
        state: 'MA',
        zip: '02139',
        display: 'Dr. John Davis (0987654321)',
      },
    ].filter(p =>
      p.name.toLowerCase().includes(query.toLowerCase()) ||
      p.npi.includes(query)
    );

    this.providerSuggestions.set(mockResults);
  }

  onReferringProviderSearch(query: string): void {
    if (query.length < 2) {
      this.referringProviderSuggestions.set([]);
      return;
    }
    // Same as provider search for now
    this.onProviderSearch(query);
    this.referringProviderSuggestions.set(this.providerSuggestions());
  }

  selectProvider(provider: any): void {
    this.selectedProvider.set(provider);
    this.form.patchValue({
      providerId: provider.id,
      providerNPI: provider.npi,
    });
    this.npiVerified.set(false);
    this.error.set(null);
  }

  verifyNPI(): void {
    const npi = this.form.get('providerNPI')?.value;
    if (!npi || npi.length !== 10) {
      return;
    }

    this.verifyingNPI.set(true);

    // Mock NPI verification - would call NPPES API
    setTimeout(() => {
      this.npiVerified.set(true);
      this.verifyingNPI.set(false);
    }, 1000);
  }

  onBack(): void {
    this.stepBack.emit();
  }

  onNext(): void {
    if (!this.form.valid) {
      this.form.markAllAsTouched();
      return;
    }

    const stepData: ProviderStepData = {
      providerId: this.form.get('providerId')?.value,
      providerNPI: this.form.get('providerNPI')?.value,
      placeOfService: this.form.get('placeOfService')?.value,
      priorAuthNumber: this.form.get('priorAuthNumber')?.value || undefined,
      referringProviderId: this.form.get('referringProviderId')?.value || undefined,
    };

    this.stepComplete.emit(stepData);
  }
}
