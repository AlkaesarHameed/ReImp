/**
 * Policies List Component.
 * Source: Design Document Section 3.4
 * Source: Phase 4 Implementation Document
 * Verified: 2025-12-18
 *
 * Full CRUD management for insurance policies.
 */
import {
  Component,
  ChangeDetectionStrategy,
  inject,
  signal,
  OnInit,
} from '@angular/core';
import { CommonModule, CurrencyPipe, PercentPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CardModule } from 'primeng/card';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { DropdownModule } from 'primeng/dropdown';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { DialogModule } from 'primeng/dialog';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { DividerModule } from 'primeng/divider';

import {
  Policy,
  PolicyCreate,
  PolicyStatus,
  PlanType,
  getPlanTypeLabel,
} from '@claims-processing/models';
import { PoliciesStore } from '@claims-processing/data-access';

@Component({
  selector: 'app-policies-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    CardModule,
    TableModule,
    ButtonModule,
    InputTextModule,
    InputNumberModule,
    DropdownModule,
    TagModule,
    TooltipModule,
    DialogModule,
    ConfirmDialogModule,
    ToastModule,
    ProgressSpinnerModule,
    DividerModule,
    CurrencyPipe,
    PercentPipe,
  ],
  providers: [ConfirmationService, MessageService],
  template: `
    <div class="admin-container">
      <p-toast></p-toast>
      <p-confirmDialog></p-confirmDialog>

      <p-card>
        <ng-template pTemplate="header">
          <div class="card-header">
            <h2>Policies Management</h2>
            <p-button
              icon="pi pi-plus"
              label="Add Policy"
              (onClick)="openCreateDialog()"
            ></p-button>
          </div>
        </ng-template>

        <!-- Filters -->
        <div class="filters-row">
          <span class="p-input-icon-left">
            <i class="pi pi-search"></i>
            <input
              type="text"
              pInputText
              placeholder="Search by name or number..."
              [(ngModel)]="searchTerm"
              (input)="onSearch()"
            />
          </span>

          <p-dropdown
            [options]="statusOptions"
            [(ngModel)]="selectedStatus"
            placeholder="All Statuses"
            [showClear]="true"
            (onChange)="onFilterChange()"
          ></p-dropdown>

          <p-dropdown
            [options]="planTypeOptions"
            [(ngModel)]="selectedPlanType"
            placeholder="All Plan Types"
            [showClear]="true"
            (onChange)="onFilterChange()"
          ></p-dropdown>
        </div>

        <!-- Data Table -->
        @if (store.loading()) {
          <div class="loading-container">
            <p-progressSpinner></p-progressSpinner>
          </div>
        } @else {
          <p-table
            [value]="store.filteredPolicies()"
            [paginator]="true"
            [rows]="10"
            [rowsPerPageOptions]="[10, 25, 50]"
            [showCurrentPageReport]="true"
            currentPageReportTemplate="Showing {first} to {last} of {totalRecords} policies"
            [sortField]="'policy_name'"
            [sortOrder]="1"
            styleClass="p-datatable-sm p-datatable-striped"
          >
            <ng-template pTemplate="header">
              <tr>
                <th pSortableColumn="policy_number">Policy # <p-sortIcon field="policy_number"></p-sortIcon></th>
                <th pSortableColumn="policy_name">Name <p-sortIcon field="policy_name"></p-sortIcon></th>
                <th pSortableColumn="plan_type">Plan Type <p-sortIcon field="plan_type"></p-sortIcon></th>
                <th pSortableColumn="deductible">Deductible <p-sortIcon field="deductible"></p-sortIcon></th>
                <th pSortableColumn="out_of_pocket_max">OOP Max <p-sortIcon field="out_of_pocket_max"></p-sortIcon></th>
                <th pSortableColumn="effective_date">Effective <p-sortIcon field="effective_date"></p-sortIcon></th>
                <th pSortableColumn="status">Status <p-sortIcon field="status"></p-sortIcon></th>
                <th>Actions</th>
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-policy>
              <tr>
                <td>{{ policy.policy_number }}</td>
                <td>{{ policy.policy_name }}</td>
                <td>{{ getPlanLabel(policy.plan_type) }}</td>
                <td>{{ policy.deductible | currency }}</td>
                <td>{{ policy.out_of_pocket_max | currency }}</td>
                <td>{{ policy.effective_date | date:'MM/dd/yyyy' }}</td>
                <td>
                  <p-tag
                    [value]="policy.status"
                    [severity]="getStatusSeverity(policy.status)"
                  ></p-tag>
                </td>
                <td>
                  <div class="action-buttons">
                    <p-button
                      icon="pi pi-eye"
                      [rounded]="true"
                      [text]="true"
                      pTooltip="View"
                      (onClick)="viewPolicy(policy)"
                    ></p-button>
                    <p-button
                      icon="pi pi-pencil"
                      [rounded]="true"
                      [text]="true"
                      pTooltip="Edit"
                      (onClick)="editPolicy(policy)"
                    ></p-button>
                    <p-button
                      icon="pi pi-trash"
                      [rounded]="true"
                      [text]="true"
                      severity="danger"
                      pTooltip="Delete"
                      (onClick)="confirmDelete(policy)"
                    ></p-button>
                  </div>
                </td>
              </tr>
            </ng-template>
            <ng-template pTemplate="emptymessage">
              <tr>
                <td colspan="8" class="text-center">
                  No policies found. Click "Add Policy" to create one.
                </td>
              </tr>
            </ng-template>
          </p-table>
        }
      </p-card>

      <!-- Create/Edit Dialog -->
      <p-dialog
        [(visible)]="dialogVisible"
        [header]="editMode ? 'Edit Policy' : 'Add Policy'"
        [modal]="true"
        [style]="{ width: '700px' }"
        [draggable]="false"
        [resizable]="false"
      >
        <div class="form-grid">
          <div class="form-field">
            <label for="policyName">Policy Name *</label>
            <input
              id="policyName"
              type="text"
              pInputText
              [(ngModel)]="formData.policy_name"
              placeholder="e.g., Gold Plan"
            />
          </div>

          <div class="form-field">
            <label for="policyNumber">Policy Number *</label>
            <input
              id="policyNumber"
              type="text"
              pInputText
              [(ngModel)]="formData.policy_number"
              placeholder="e.g., POL-001"
            />
          </div>

          <div class="form-field">
            <label for="planType">Plan Type *</label>
            <p-dropdown
              id="planType"
              [options]="planTypeOptions"
              [(ngModel)]="formData.plan_type"
              placeholder="Select plan type"
              [style]="{ width: '100%' }"
            ></p-dropdown>
          </div>

          <div class="form-field">
            <label for="groupId">Group ID</label>
            <input
              id="groupId"
              type="text"
              pInputText
              [(ngModel)]="formData.group_id"
              placeholder="Group ID"
            />
          </div>

          <div class="form-field full-width">
            <label for="groupName">Group Name</label>
            <input
              id="groupName"
              type="text"
              pInputText
              [(ngModel)]="formData.group_name"
              placeholder="e.g., Acme Corporation"
            />
          </div>

          <p-divider class="full-width"></p-divider>
          <h4 class="full-width section-title">Cost Sharing</h4>

          <div class="form-field">
            <label for="deductible">Annual Deductible *</label>
            <p-inputNumber
              id="deductible"
              [(ngModel)]="formData.deductible"
              mode="currency"
              currency="USD"
              locale="en-US"
              [style]="{ width: '100%' }"
            ></p-inputNumber>
          </div>

          <div class="form-field">
            <label for="oopMax">Out-of-Pocket Max *</label>
            <p-inputNumber
              id="oopMax"
              [(ngModel)]="formData.out_of_pocket_max"
              mode="currency"
              currency="USD"
              locale="en-US"
              [style]="{ width: '100%' }"
            ></p-inputNumber>
          </div>

          <div class="form-field">
            <label for="coinsuranceIn">In-Network Coinsurance *</label>
            <p-inputNumber
              id="coinsuranceIn"
              [(ngModel)]="formData.coinsurance_in_network"
              [min]="0"
              [max]="1"
              [minFractionDigits]="0"
              [maxFractionDigits]="2"
              suffix="%"
              [style]="{ width: '100%' }"
            ></p-inputNumber>
          </div>

          <div class="form-field">
            <label for="coinsuranceOut">Out-of-Network Coinsurance *</label>
            <p-inputNumber
              id="coinsuranceOut"
              [(ngModel)]="formData.coinsurance_out_network"
              [min]="0"
              [max]="1"
              [minFractionDigits]="0"
              [maxFractionDigits]="2"
              suffix="%"
              [style]="{ width: '100%' }"
            ></p-inputNumber>
          </div>

          <p-divider class="full-width"></p-divider>
          <h4 class="full-width section-title">Copays</h4>

          <div class="form-field">
            <label for="copayPrimary">Primary Care Copay</label>
            <p-inputNumber
              id="copayPrimary"
              [(ngModel)]="formData.copay_primary_care"
              mode="currency"
              currency="USD"
              locale="en-US"
              [style]="{ width: '100%' }"
            ></p-inputNumber>
          </div>

          <div class="form-field">
            <label for="copaySpecialist">Specialist Copay</label>
            <p-inputNumber
              id="copaySpecialist"
              [(ngModel)]="formData.copay_specialist"
              mode="currency"
              currency="USD"
              locale="en-US"
              [style]="{ width: '100%' }"
            ></p-inputNumber>
          </div>

          <div class="form-field">
            <label for="copayEmergency">Emergency Copay</label>
            <p-inputNumber
              id="copayEmergency"
              [(ngModel)]="formData.copay_emergency"
              mode="currency"
              currency="USD"
              locale="en-US"
              [style]="{ width: '100%' }"
            ></p-inputNumber>
          </div>

          <div class="form-field">
            <label for="copayUrgent">Urgent Care Copay</label>
            <p-inputNumber
              id="copayUrgent"
              [(ngModel)]="formData.copay_urgent_care"
              mode="currency"
              currency="USD"
              locale="en-US"
              [style]="{ width: '100%' }"
            ></p-inputNumber>
          </div>

          <p-divider class="full-width"></p-divider>
          <h4 class="full-width section-title">Effective Dates</h4>

          <div class="form-field">
            <label for="effectiveDate">Effective Date *</label>
            <input
              id="effectiveDate"
              type="date"
              pInputText
              [(ngModel)]="formData.effective_date"
            />
          </div>

          <div class="form-field">
            <label for="terminationDate">Termination Date</label>
            <input
              id="terminationDate"
              type="date"
              pInputText
              [(ngModel)]="formData.termination_date"
            />
          </div>
        </div>

        <ng-template pTemplate="footer">
          <p-button
            label="Cancel"
            [text]="true"
            (onClick)="closeDialog()"
          ></p-button>
          <p-button
            [label]="editMode ? 'Update' : 'Create'"
            (onClick)="savePolicy()"
            [disabled]="!isFormValid()"
          ></p-button>
        </ng-template>
      </p-dialog>

      <!-- View Dialog -->
      <p-dialog
        [(visible)]="viewDialogVisible"
        header="Policy Details"
        [modal]="true"
        [style]="{ width: '650px' }"
        [draggable]="false"
        [resizable]="false"
      >
        @if (selectedPolicy()) {
          <div class="detail-grid">
            <div class="detail-row">
              <span class="detail-label">Policy Number:</span>
              <span class="detail-value">{{ selectedPolicy()!.policy_number }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Policy Name:</span>
              <span class="detail-value">{{ selectedPolicy()!.policy_name }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Plan Type:</span>
              <span class="detail-value">{{ getPlanLabel(selectedPolicy()!.plan_type) }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Status:</span>
              <p-tag
                [value]="selectedPolicy()!.status"
                [severity]="getStatusSeverity(selectedPolicy()!.status)"
              ></p-tag>
            </div>
            @if (selectedPolicy()!.group_name) {
              <div class="detail-row full-width">
                <span class="detail-label">Group:</span>
                <span class="detail-value">{{ selectedPolicy()!.group_name }} ({{ selectedPolicy()!.group_id }})</span>
              </div>
            }

            <p-divider class="full-width"></p-divider>
            <h4 class="full-width section-title">Cost Sharing</h4>

            <div class="detail-row">
              <span class="detail-label">Annual Deductible:</span>
              <span class="detail-value">{{ selectedPolicy()!.deductible | currency }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Out-of-Pocket Max:</span>
              <span class="detail-value">{{ selectedPolicy()!.out_of_pocket_max | currency }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">In-Network Coinsurance:</span>
              <span class="detail-value">{{ selectedPolicy()!.coinsurance_in_network * 100 }}%</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Out-of-Network Coinsurance:</span>
              <span class="detail-value">{{ selectedPolicy()!.coinsurance_out_network * 100 }}%</span>
            </div>

            <p-divider class="full-width"></p-divider>
            <h4 class="full-width section-title">Copays</h4>

            <div class="detail-row">
              <span class="detail-label">Primary Care:</span>
              <span class="detail-value">{{ selectedPolicy()!.copay_primary_care ? (selectedPolicy()!.copay_primary_care | currency) : 'N/A' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Specialist:</span>
              <span class="detail-value">{{ selectedPolicy()!.copay_specialist ? (selectedPolicy()!.copay_specialist | currency) : 'N/A' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Emergency:</span>
              <span class="detail-value">{{ selectedPolicy()!.copay_emergency ? (selectedPolicy()!.copay_emergency | currency) : 'N/A' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Urgent Care:</span>
              <span class="detail-value">{{ selectedPolicy()!.copay_urgent_care ? (selectedPolicy()!.copay_urgent_care | currency) : 'N/A' }}</span>
            </div>

            <p-divider class="full-width"></p-divider>
            <h4 class="full-width section-title">Dates</h4>

            <div class="detail-row">
              <span class="detail-label">Effective Date:</span>
              <span class="detail-value">{{ selectedPolicy()!.effective_date | date:'MM/dd/yyyy' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Termination Date:</span>
              <span class="detail-value">{{ selectedPolicy()!.termination_date ? (selectedPolicy()!.termination_date | date:'MM/dd/yyyy') : 'Active' }}</span>
            </div>
          </div>
        }
      </p-dialog>
    </div>
  `,
  styles: [
    `
      .admin-container {
        padding: 1.5rem;
      }

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem;
      }

      .card-header h2 {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 600;
      }

      .filters-row {
        display: flex;
        gap: 1rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
      }

      .filters-row input {
        min-width: 250px;
      }

      .loading-container {
        display: flex;
        justify-content: center;
        padding: 3rem;
      }

      .action-buttons {
        display: flex;
        gap: 0.25rem;
      }

      .text-center {
        text-align: center;
        padding: 2rem;
        color: var(--text-color-secondary);
      }

      .form-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
      }

      .form-field {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
      }

      .form-field.full-width {
        grid-column: span 2;
      }

      .form-field label {
        font-weight: 500;
        font-size: 0.875rem;
      }

      .form-field input {
        width: 100%;
      }

      .section-title {
        margin: 0.5rem 0;
        color: var(--primary-color);
        font-size: 1rem;
      }

      .detail-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
      }

      .detail-row {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
      }

      .detail-row.full-width {
        grid-column: span 2;
      }

      .detail-label {
        font-weight: 600;
        font-size: 0.875rem;
        color: var(--text-color-secondary);
      }

      .detail-value {
        font-size: 1rem;
      }

      :host ::ng-deep .full-width {
        grid-column: span 2;
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PoliciesListComponent implements OnInit {
  protected readonly store = inject(PoliciesStore);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly messageService = inject(MessageService);

  // Filters
  searchTerm = '';
  selectedStatus: PolicyStatus | null = null;
  selectedPlanType: PlanType | null = null;

  // Dialog state
  dialogVisible = false;
  viewDialogVisible = false;
  editMode = false;
  selectedPolicy = signal<Policy | null>(null);

  // Form data
  formData: PolicyCreate = this.getEmptyFormData();

  // Dropdown options
  statusOptions = [
    { label: 'Active', value: PolicyStatus.ACTIVE },
    { label: 'Inactive', value: PolicyStatus.INACTIVE },
    { label: 'Pending', value: PolicyStatus.PENDING },
    { label: 'Suspended', value: PolicyStatus.SUSPENDED },
    { label: 'Terminated', value: PolicyStatus.TERMINATED },
  ];

  planTypeOptions = [
    { label: 'HMO', value: PlanType.HMO },
    { label: 'PPO', value: PlanType.PPO },
    { label: 'EPO', value: PlanType.EPO },
    { label: 'POS', value: PlanType.POS },
    { label: 'HDHP', value: PlanType.HDHP },
    { label: 'Indemnity', value: PlanType.INDEMNITY },
  ];

  ngOnInit(): void {
    this.loadMockData();
  }

  private loadMockData(): void {
    const mockPolicies: Policy[] = [
      {
        id: 'pol-1',
        policy_id: 'POL001',
        policy_name: 'Gold Plan',
        policy_number: 'POL-001',
        plan_type: PlanType.PPO,
        group_id: 'GRP001',
        group_name: 'Acme Corporation',
        effective_date: '2024-01-01',
        status: PolicyStatus.ACTIVE,
        deductible: 1500,
        out_of_pocket_max: 6000,
        coinsurance_in_network: 0.2,
        coinsurance_out_network: 0.4,
        copay_primary_care: 25,
        copay_specialist: 50,
        copay_emergency: 250,
        copay_urgent_care: 75,
        network_ids: ['net-1'],
        benefits: [],
        exclusions: [],
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-15T00:00:00Z',
      },
      {
        id: 'pol-2',
        policy_id: 'POL002',
        policy_name: 'Silver Plan',
        policy_number: 'POL-002',
        plan_type: PlanType.HMO,
        group_id: 'GRP001',
        group_name: 'Acme Corporation',
        effective_date: '2024-01-01',
        status: PolicyStatus.ACTIVE,
        deductible: 2500,
        out_of_pocket_max: 8000,
        coinsurance_in_network: 0.3,
        coinsurance_out_network: 0.5,
        copay_primary_care: 30,
        copay_specialist: 60,
        copay_emergency: 300,
        copay_urgent_care: 100,
        network_ids: ['net-1'],
        benefits: [],
        exclusions: [],
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-15T00:00:00Z',
      },
      {
        id: 'pol-3',
        policy_id: 'POL003',
        policy_name: 'Bronze HDHP',
        policy_number: 'POL-003',
        plan_type: PlanType.HDHP,
        group_id: 'GRP002',
        group_name: 'Tech Startup Inc.',
        effective_date: '2024-01-01',
        status: PolicyStatus.ACTIVE,
        deductible: 5000,
        out_of_pocket_max: 12000,
        coinsurance_in_network: 0.2,
        coinsurance_out_network: 0.5,
        network_ids: ['net-1', 'net-2'],
        benefits: [],
        exclusions: [],
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-10T00:00:00Z',
      },
      {
        id: 'pol-4',
        policy_id: 'POL004',
        policy_name: 'Platinum Plan',
        policy_number: 'POL-004',
        plan_type: PlanType.PPO,
        effective_date: '2023-01-01',
        termination_date: '2023-12-31',
        status: PolicyStatus.TERMINATED,
        deductible: 500,
        out_of_pocket_max: 3000,
        coinsurance_in_network: 0.1,
        coinsurance_out_network: 0.3,
        copay_primary_care: 15,
        copay_specialist: 35,
        copay_emergency: 150,
        copay_urgent_care: 50,
        network_ids: ['net-1'],
        benefits: [],
        exclusions: [],
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-12-31T00:00:00Z',
      },
    ];

    this.store.setPolicies(mockPolicies);
  }

  onSearch(): void {
    this.store.setFilters({
      ...this.store.filters(),
      searchTerm: this.searchTerm,
    });
  }

  onFilterChange(): void {
    this.store.setFilters({
      searchTerm: this.searchTerm,
      status: this.selectedStatus || undefined,
      policyType: this.selectedPlanType || undefined,
    });
  }

  openCreateDialog(): void {
    this.editMode = false;
    this.formData = this.getEmptyFormData();
    this.dialogVisible = true;
  }

  viewPolicy(policy: Policy): void {
    this.selectedPolicy.set(policy);
    this.viewDialogVisible = true;
  }

  editPolicy(policy: Policy): void {
    this.editMode = true;
    this.selectedPolicy.set(policy);
    this.formData = {
      policy_name: policy.policy_name,
      policy_number: policy.policy_number,
      plan_type: policy.plan_type,
      group_id: policy.group_id,
      group_name: policy.group_name,
      effective_date: policy.effective_date,
      termination_date: policy.termination_date,
      deductible: policy.deductible,
      out_of_pocket_max: policy.out_of_pocket_max,
      coinsurance_in_network: policy.coinsurance_in_network,
      coinsurance_out_network: policy.coinsurance_out_network,
      copay_primary_care: policy.copay_primary_care,
      copay_specialist: policy.copay_specialist,
      copay_emergency: policy.copay_emergency,
      copay_urgent_care: policy.copay_urgent_care,
      network_ids: [...policy.network_ids],
    };
    this.dialogVisible = true;
  }

  confirmDelete(policy: Policy): void {
    this.confirmationService.confirm({
      message: `Are you sure you want to delete policy "${policy.policy_name}"?`,
      header: 'Confirm Delete',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        this.store.removePolicy(policy.id);
        this.messageService.add({
          severity: 'success',
          summary: 'Deleted',
          detail: 'Policy has been deleted.',
        });
      },
    });
  }

  closeDialog(): void {
    this.dialogVisible = false;
    this.formData = this.getEmptyFormData();
  }

  savePolicy(): void {
    if (!this.isFormValid()) return;

    if (this.editMode && this.selectedPolicy()) {
      this.store.updatePolicy(this.selectedPolicy()!.id, this.formData);
      this.messageService.add({
        severity: 'success',
        summary: 'Updated',
        detail: 'Policy has been updated.',
      });
    } else {
      const newPolicy: Policy = {
        id: `pol-${Date.now()}`,
        policy_id: `POL${Date.now().toString().slice(-6)}`,
        ...this.formData,
        status: PolicyStatus.ACTIVE,
        network_ids: this.formData.network_ids || [],
        benefits: [],
        exclusions: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      this.store.addPolicy(newPolicy);
      this.messageService.add({
        severity: 'success',
        summary: 'Created',
        detail: 'Policy has been created.',
      });
    }

    this.closeDialog();
  }

  isFormValid(): boolean {
    return !!(
      this.formData.policy_name &&
      this.formData.policy_number &&
      this.formData.plan_type &&
      this.formData.effective_date &&
      this.formData.deductible !== null &&
      this.formData.out_of_pocket_max !== null &&
      this.formData.coinsurance_in_network !== null &&
      this.formData.coinsurance_out_network !== null
    );
  }

  getPlanLabel(planType: PlanType): string {
    return getPlanTypeLabel(planType);
  }

  getStatusSeverity(status: PolicyStatus): 'success' | 'info' | 'warning' | 'danger' {
    const severities: Record<PolicyStatus, 'success' | 'info' | 'warning' | 'danger'> = {
      [PolicyStatus.ACTIVE]: 'success',
      [PolicyStatus.INACTIVE]: 'info',
      [PolicyStatus.PENDING]: 'warning',
      [PolicyStatus.SUSPENDED]: 'warning',
      [PolicyStatus.TERMINATED]: 'danger',
    };
    return severities[status] || 'info';
  }

  private getEmptyFormData(): PolicyCreate {
    return {
      policy_name: '',
      policy_number: '',
      plan_type: PlanType.PPO,
      group_id: '',
      group_name: '',
      effective_date: new Date().toISOString().split('T')[0],
      termination_date: undefined,
      deductible: 0,
      out_of_pocket_max: 0,
      coinsurance_in_network: 0.2,
      coinsurance_out_network: 0.4,
      copay_primary_care: undefined,
      copay_specialist: undefined,
      copay_emergency: undefined,
      copay_urgent_care: undefined,
      network_ids: [],
    };
  }
}
