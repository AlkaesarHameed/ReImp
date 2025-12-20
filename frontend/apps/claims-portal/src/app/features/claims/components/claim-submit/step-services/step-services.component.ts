/**
 * Step Services Component.
 * Source: Phase 3 Implementation Document
 * Source: Design Document Section 3.4
 * Verified: 2025-12-18
 *
 * Third step of claim submission wizard - Service lines and diagnosis codes.
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
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
  AbstractControl,
  ValidationErrors,
} from '@angular/forms';
import { AutoCompleteModule } from 'primeng/autocomplete';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { CalendarModule } from 'primeng/calendar';
import { DropdownModule } from 'primeng/dropdown';
import { ChipModule } from 'primeng/chip';
import { TableModule } from 'primeng/table';
import { MessageModule } from 'primeng/message';
import { TooltipModule } from 'primeng/tooltip';
import { MultiSelectModule } from 'primeng/multiselect';
import { Subject, takeUntil } from 'rxjs';

import {
  ServicesStepData,
  ClaimLineItemForm,
  createEmptyLineItem,
} from '@claims-processing/models';

@Component({
  selector: 'app-step-services',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    AutoCompleteModule,
    InputTextModule,
    InputNumberModule,
    ButtonModule,
    CardModule,
    CalendarModule,
    DropdownModule,
    ChipModule,
    TableModule,
    MessageModule,
    TooltipModule,
    MultiSelectModule,
    CurrencyPipe,
    DatePipe,
  ],
  template: `
    <div class="step-services">
      <h3>Step 3: Service Information</h3>
      <p class="step-description">Enter diagnosis codes and service line items.</p>

      <form [formGroup]="form" class="services-form">
        <!-- Service Date Range -->
        <div class="date-range-row">
          <div class="field">
            <label for="serviceDateFrom">Service Date From *</label>
            <p-calendar
              id="serviceDateFrom"
              formControlName="serviceDateFrom"
              dateFormat="mm/dd/yy"
              [showIcon]="true"
              [maxDate]="today"
              styleClass="w-full"
            ></p-calendar>
            @if (form.get('serviceDateFrom')?.hasError('required') && form.get('serviceDateFrom')?.touched) {
              <small class="p-error">Service date from is required</small>
            }
          </div>

          <div class="field">
            <label for="serviceDateTo">Service Date To *</label>
            <p-calendar
              id="serviceDateTo"
              formControlName="serviceDateTo"
              dateFormat="mm/dd/yy"
              [showIcon]="true"
              [maxDate]="today"
              styleClass="w-full"
            ></p-calendar>
            @if (form.get('serviceDateTo')?.hasError('required') && form.get('serviceDateTo')?.touched) {
              <small class="p-error">Service date to is required</small>
            }
          </div>
        </div>

        <!-- Diagnosis Codes Section -->
        <p-card styleClass="diagnosis-card">
          <ng-template pTemplate="header">
            <div class="section-header">
              <h4>Diagnosis Codes (ICD-10)</h4>
            </div>
          </ng-template>

          <div class="diagnosis-search">
            <p-autoComplete
              [suggestions]="diagnosisSuggestions()"
              (completeMethod)="onDiagnosisSearch($event.query)"
              (onSelect)="addDiagnosisCode($event)"
              [field]="'display'"
              [minLength]="2"
              [delay]="300"
              placeholder="Search ICD-10 codes..."
              styleClass="w-full"
              [showEmptyMessage]="true"
              emptyMessage="No codes found"
            >
              <ng-template let-code pTemplate="item">
                <div class="code-suggestion">
                  <span class="code">{{ code.code }}</span>
                  <span class="description">{{ code.description }}</span>
                </div>
              </ng-template>
            </p-autoComplete>
          </div>

          <div class="diagnosis-list">
            @for (dx of diagnosisCodes(); track dx.code; let i = $index) {
              <div class="diagnosis-item" [class.primary]="dx.code === form.get('primaryDiagnosis')?.value">
                <span class="dx-number">{{ i + 1 }}.</span>
                <span class="dx-code">{{ dx.code }}</span>
                <span class="dx-description">{{ dx.description }}</span>
                @if (dx.code === form.get('primaryDiagnosis')?.value) {
                  <span class="primary-badge">Primary</span>
                } @else {
                  <button
                    pButton
                    type="button"
                    icon="pi pi-star"
                    class="p-button-text p-button-sm"
                    pTooltip="Set as Primary"
                    (click)="setPrimaryDiagnosis(dx.code)"
                  ></button>
                }
                <button
                  pButton
                  type="button"
                  icon="pi pi-times"
                  class="p-button-text p-button-danger p-button-sm"
                  (click)="removeDiagnosisCode(i)"
                ></button>
              </div>
            }
            @if (diagnosisCodes().length === 0) {
              <p class="no-diagnosis">No diagnosis codes added. Search and add at least one.</p>
            }
          </div>
        </p-card>

        <!-- Line Items Section -->
        <p-card styleClass="line-items-card">
          <ng-template pTemplate="header">
            <div class="section-header">
              <h4>Service Lines</h4>
              <button
                pButton
                type="button"
                label="Add Line"
                icon="pi pi-plus"
                class="p-button-outlined p-button-sm"
                (click)="addLineItem()"
              ></button>
            </div>
          </ng-template>

          <p-table [value]="lineItems()" styleClass="p-datatable-sm">
            <ng-template pTemplate="header">
              <tr>
                <th style="width: 50px">#</th>
                <th>Procedure Code</th>
                <th>Modifiers</th>
                <th>Service Date</th>
                <th style="width: 80px">Qty</th>
                <th style="width: 120px">Unit Price</th>
                <th style="width: 120px">Charged</th>
                <th style="width: 80px">Dx Ptr</th>
                <th style="width: 60px"></th>
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-line let-i="rowIndex">
              <tr>
                <td>{{ i + 1 }}</td>
                <td>
                  <p-autoComplete
                    [ngModel]="line.procedureCode"
                    (ngModelChange)="updateLineItem(i, { procedureCode: $event })"
                    [ngModelOptions]="{standalone: true}"
                    [suggestions]="procedureSuggestions()[i] || []"
                    (completeMethod)="onProcedureSearch(i, $event.query)"
                    (onSelect)="selectProcedure(i, $event)"
                    [field]="'code'"
                    [minLength]="2"
                    placeholder="CPT/HCPCS"
                    styleClass="w-full"
                  ></p-autoComplete>
                </td>
                <td>
                  <p-multiSelect
                    [ngModel]="line.modifiers"
                    (ngModelChange)="updateLineItem(i, { modifiers: $event })"
                    [ngModelOptions]="{standalone: true}"
                    [options]="modifierOptions()"
                    optionLabel="label"
                    optionValue="value"
                    placeholder="Select"
                    [maxSelectedLabels]="2"
                    styleClass="w-full"
                  ></p-multiSelect>
                </td>
                <td>
                  <p-calendar
                    [ngModel]="line.serviceDate"
                    (ngModelChange)="updateLineItem(i, { serviceDate: $event })"
                    [ngModelOptions]="{standalone: true}"
                    dateFormat="mm/dd/yy"
                    [showIcon]="true"
                    styleClass="w-full"
                  ></p-calendar>
                </td>
                <td>
                  <p-inputNumber
                    [ngModel]="line.quantity"
                    (ngModelChange)="onQuantityChange(i, $event)"
                    [ngModelOptions]="{standalone: true}"
                    [min]="1"
                    [max]="999"
                    styleClass="w-full"
                  ></p-inputNumber>
                </td>
                <td>
                  <p-inputNumber
                    [ngModel]="line.unitPrice"
                    (ngModelChange)="onUnitPriceChange(i, $event)"
                    [ngModelOptions]="{standalone: true}"
                    mode="currency"
                    currency="USD"
                    locale="en-US"
                    styleClass="w-full"
                  ></p-inputNumber>
                </td>
                <td class="charged-amount">
                  {{ line.chargedAmount | currency }}
                </td>
                <td>
                  <p-dropdown
                    [ngModel]="line.diagnosisPointers"
                    (ngModelChange)="updateLineItem(i, { diagnosisPointers: $event })"
                    [ngModelOptions]="{standalone: true}"
                    [options]="diagnosisPointerOptions()"
                    [multiple]="true"
                    placeholder="Dx"
                    styleClass="w-full"
                  ></p-dropdown>
                </td>
                <td>
                  <button
                    pButton
                    type="button"
                    icon="pi pi-trash"
                    class="p-button-text p-button-danger p-button-sm"
                    [disabled]="lineItems().length === 1"
                    (click)="removeLineItem(i)"
                  ></button>
                </td>
              </tr>
            </ng-template>
            <ng-template pTemplate="footer">
              <tr>
                <td colspan="6" class="text-right"><strong>Total Charged:</strong></td>
                <td class="charged-amount"><strong>{{ totalCharged() | currency }}</strong></td>
                <td colspan="2"></td>
              </tr>
            </ng-template>
          </p-table>
        </p-card>

        <!-- Validation Messages -->
        @if (!canProceed() && form.touched) {
          <p-message
            severity="warn"
            text="Please complete all required fields: service dates, at least one diagnosis code, and at least one valid service line."
            styleClass="w-full mt-3"
          ></p-message>
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
          [disabled]="!canProceed()"
          (click)="onNext()"
        ></button>
      </div>
    </div>
  `,
  styles: [`
    .step-services {
      padding: 1rem;
    }

    .step-description {
      color: #6c757d;
      margin-bottom: 1.5rem;
    }

    .services-form {
      max-width: 1200px;
    }

    .date-range-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    .field {
      margin-bottom: 1rem;
    }

    .field label {
      display: block;
      margin-bottom: 0.5rem;
      font-weight: 500;
    }

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      background: #f8f9fa;
    }

    .section-header h4 {
      margin: 0;
    }

    .diagnosis-card, .line-items-card {
      margin-bottom: 1.5rem;
    }

    .diagnosis-search {
      margin-bottom: 1rem;
    }

    .code-suggestion {
      display: flex;
      gap: 1rem;
      padding: 0.5rem 0;
    }

    .code-suggestion .code {
      font-weight: 600;
      color: #0066cc;
      min-width: 80px;
    }

    .diagnosis-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .diagnosis-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.5rem 1rem;
      background: #f8f9fa;
      border-radius: 4px;
    }

    .diagnosis-item.primary {
      background: #e7f3ff;
      border: 1px solid #0066cc;
    }

    .dx-number {
      font-weight: 600;
      color: #6c757d;
      min-width: 24px;
    }

    .dx-code {
      font-weight: 600;
      color: #0066cc;
      min-width: 80px;
    }

    .dx-description {
      flex: 1;
    }

    .primary-badge {
      background: #0066cc;
      color: white;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
    }

    .no-diagnosis {
      color: #6c757d;
      font-style: italic;
      padding: 1rem;
      text-align: center;
    }

    .charged-amount {
      text-align: right;
      font-weight: 500;
    }

    .step-navigation {
      display: flex;
      justify-content: space-between;
      margin-top: 2rem;
      padding-top: 1rem;
      border-top: 1px solid #dee2e6;
    }

    @media (max-width: 768px) {
      .date-range-row {
        grid-template-columns: 1fr;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StepServicesComponent implements OnInit, OnDestroy {
  private readonly fb = inject(FormBuilder);
  private readonly destroy$ = new Subject<void>();

  @Input() initialData?: ServicesStepData;

  @Output() stepComplete = new EventEmitter<ServicesStepData>();
  @Output() stepBack = new EventEmitter<void>();
  @Output() dirty = new EventEmitter<boolean>();

  today = new Date();

  // Form
  form: FormGroup = this.fb.group({
    serviceDateFrom: ['', Validators.required],
    serviceDateTo: ['', Validators.required],
    primaryDiagnosis: ['', Validators.required],
  }, { validators: this.dateRangeValidator });

  // State
  readonly diagnosisCodes = signal<{ code: string; description: string }[]>([]);
  readonly lineItems = signal<ClaimLineItemForm[]>([createEmptyLineItem()]);
  readonly diagnosisSuggestions = signal<any[]>([]);
  readonly procedureSuggestions = signal<any[][]>([[]]);
  readonly modifierOptions = signal<{ label: string; value: string }[]>([]);

  // Computed
  readonly totalCharged = computed(() =>
    this.lineItems().reduce((sum, item) => sum + (item.chargedAmount || 0), 0)
  );

  readonly diagnosisPointerOptions = computed(() =>
    this.diagnosisCodes().map((_, i) => ({ label: `${i + 1}`, value: i + 1 }))
  );

  readonly canProceed = computed(() =>
    this.form.valid &&
    this.diagnosisCodes().length > 0 &&
    this.lineItems().some(item => this.isLineItemValid(this.lineItems().indexOf(item)))
  );

  ngOnInit(): void {
    this.loadModifiers();

    if (this.initialData) {
      this.form.patchValue({
        serviceDateFrom: this.initialData.serviceDateFrom,
        serviceDateTo: this.initialData.serviceDateTo,
        primaryDiagnosis: this.initialData.primaryDiagnosis,
      });
      this.diagnosisCodes.set(
        this.initialData.diagnosisCodes.map(code => ({ code, description: '' }))
      );
      if (this.initialData.lineItems.length > 0) {
        this.lineItems.set(this.initialData.lineItems);
      }
    }

    this.form.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => this.dirty.emit(this.form.dirty));
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private dateRangeValidator(control: AbstractControl): ValidationErrors | null {
    const from = control.get('serviceDateFrom')?.value;
    const to = control.get('serviceDateTo')?.value;

    if (from && to && new Date(from) > new Date(to)) {
      return { dateRange: true };
    }
    return null;
  }

  private loadModifiers(): void {
    const mockModifiers = [
      { code: '25', description: 'Significant, Separately Identifiable E/M' },
      { code: '59', description: 'Distinct Procedural Service' },
      { code: '76', description: 'Repeat Procedure by Same Physician' },
      { code: '77', description: 'Repeat Procedure by Another Physician' },
      { code: 'TC', description: 'Technical Component' },
      { code: '26', description: 'Professional Component' },
    ];

    this.modifierOptions.set(
      mockModifiers.map(m => ({ label: `${m.code} - ${m.description}`, value: m.code }))
    );
  }

  onDiagnosisSearch(query: string): void {
    if (query.length < 2) {
      this.diagnosisSuggestions.set([]);
      return;
    }

    // Mock - would call lookupApi.searchICD10()
    const mockResults = [
      { code: 'J06.9', description: 'Acute upper respiratory infection, unspecified', display: 'J06.9 - Acute upper respiratory infection' },
      { code: 'J20.9', description: 'Acute bronchitis, unspecified', display: 'J20.9 - Acute bronchitis' },
      { code: 'R05.9', description: 'Cough, unspecified', display: 'R05.9 - Cough' },
    ].filter(c => c.code.toLowerCase().includes(query.toLowerCase()) || c.description.toLowerCase().includes(query.toLowerCase()));

    this.diagnosisSuggestions.set(mockResults);
  }

  addDiagnosisCode(code: { code: string; description: string }): void {
    if (this.diagnosisCodes().some(c => c.code === code.code)) {
      return; // Already added
    }

    this.diagnosisCodes.update(codes => [...codes, code]);

    // Set as primary if first
    if (this.diagnosisCodes().length === 1) {
      this.form.get('primaryDiagnosis')?.setValue(code.code);
    }
  }

  removeDiagnosisCode(index: number): void {
    const removed = this.diagnosisCodes()[index];
    this.diagnosisCodes.update(codes => codes.filter((_, i) => i !== index));

    // Update primary if needed
    if (this.form.get('primaryDiagnosis')?.value === removed.code && this.diagnosisCodes().length > 0) {
      this.form.get('primaryDiagnosis')?.setValue(this.diagnosisCodes()[0].code);
    }
  }

  setPrimaryDiagnosis(code: string): void {
    this.form.get('primaryDiagnosis')?.setValue(code);
  }

  addLineItem(): void {
    this.lineItems.update(items => [...items, createEmptyLineItem()]);
    this.procedureSuggestions.update(s => [...s, []]);
  }

  removeLineItem(index: number): void {
    if (this.lineItems().length <= 1) return;

    this.lineItems.update(items => items.filter((_, i) => i !== index));
    this.procedureSuggestions.update(s => s.filter((_, i) => i !== index));
  }

  onProcedureSearch(index: number, query: string): void {
    if (query.length < 2) return;

    // Mock - would call lookupApi.searchCPT()
    const mockResults = [
      { code: '99213', description: 'Office visit, established, 20-29 min' },
      { code: '99214', description: 'Office visit, established, 30-39 min' },
      { code: '99215', description: 'Office visit, established, 40-54 min' },
    ].filter(c => c.code.includes(query) || c.description.toLowerCase().includes(query.toLowerCase()));

    this.procedureSuggestions.update(s => {
      const newS = [...s];
      newS[index] = mockResults;
      return newS;
    });
  }

  selectProcedure(index: number, procedure: { code: string; description: string }): void {
    this.updateLineItem(index, { procedureCode: procedure.code });
  }

  updateLineItem(index: number, updates: Partial<ClaimLineItemForm>): void {
    this.lineItems.update(items => {
      const newItems = [...items];
      newItems[index] = { ...newItems[index], ...updates };
      return newItems;
    });
  }

  onQuantityChange(index: number, quantity: number): void {
    const item = this.lineItems()[index];
    const chargedAmount = quantity * (item.unitPrice || 0);
    this.updateLineItem(index, { quantity, chargedAmount });
  }

  onUnitPriceChange(index: number, unitPrice: number): void {
    const item = this.lineItems()[index];
    const chargedAmount = (item.quantity || 1) * unitPrice;
    this.updateLineItem(index, { unitPrice, chargedAmount });
  }

  addModifier(index: number, modifier: string): void {
    const item = this.lineItems()[index];
    if (item.modifiers.length >= 4) return;
    if (item.modifiers.includes(modifier)) return;

    this.updateLineItem(index, { modifiers: [...item.modifiers, modifier] });
  }

  removeModifier(index: number, modifier: string): void {
    const item = this.lineItems()[index];
    this.updateLineItem(index, {
      modifiers: item.modifiers.filter(m => m !== modifier),
    });
  }

  isLineItemValid(index: number): boolean {
    const item = this.lineItems()[index];
    return !!(
      item.procedureCode &&
      item.serviceDate &&
      item.quantity > 0 &&
      item.chargedAmount > 0
    );
  }

  onBack(): void {
    this.stepBack.emit();
  }

  onNext(): void {
    if (!this.canProceed()) {
      this.form.markAllAsTouched();
      return;
    }

    const stepData: ServicesStepData = {
      serviceDateFrom: this.form.get('serviceDateFrom')?.value,
      serviceDateTo: this.form.get('serviceDateTo')?.value,
      diagnosisCodes: this.diagnosisCodes().map(d => d.code),
      primaryDiagnosis: this.form.get('primaryDiagnosis')?.value,
      lineItems: this.lineItems().filter((_, i) => this.isLineItemValid(i)),
    };

    this.stepComplete.emit(stepData);
  }
}
