/**
 * Providers List Component.
 * Source: Design Document Section 3.4
 * Source: Phase 4 Implementation Document
 * Verified: 2025-12-18
 *
 * Full CRUD management for healthcare providers.
 */
import {
  Component,
  ChangeDetectionStrategy,
  inject,
  signal,
  OnInit,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CardModule } from 'primeng/card';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { DropdownModule } from 'primeng/dropdown';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { DialogModule } from 'primeng/dialog';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { InputMaskModule } from 'primeng/inputmask';
import { CheckboxModule } from 'primeng/checkbox';
import { ProgressSpinnerModule } from 'primeng/progressspinner';

import {
  Provider,
  ProviderCreate,
  ProviderType,
  ProviderStatus,
  NetworkStatus,
  getProviderDisplayName,
  getNetworkStatusLabel,
} from '@claims-processing/models';
import { ProvidersStore } from '@claims-processing/data-access';

@Component({
  selector: 'app-providers-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    CardModule,
    TableModule,
    ButtonModule,
    InputTextModule,
    DropdownModule,
    TagModule,
    TooltipModule,
    DialogModule,
    ConfirmDialogModule,
    ToastModule,
    InputMaskModule,
    CheckboxModule,
    ProgressSpinnerModule,
  ],
  providers: [ConfirmationService, MessageService],
  template: `
    <div class="admin-container">
      <p-toast></p-toast>
      <p-confirmDialog></p-confirmDialog>

      <p-card>
        <ng-template pTemplate="header">
          <div class="card-header">
            <h2>Providers Management</h2>
            <p-button
              icon="pi pi-plus"
              label="Add Provider"
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
              placeholder="Search by name or NPI..."
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
            [options]="networkOptions"
            [(ngModel)]="selectedNetwork"
            placeholder="All Networks"
            [showClear]="true"
            (onChange)="onFilterChange()"
          ></p-dropdown>

          <p-dropdown
            [options]="typeOptions"
            [(ngModel)]="selectedType"
            placeholder="All Types"
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
            [value]="store.filteredProviders()"
            [paginator]="true"
            [rows]="10"
            [rowsPerPageOptions]="[10, 25, 50]"
            [showCurrentPageReport]="true"
            currentPageReportTemplate="Showing {first} to {last} of {totalRecords} providers"
            [sortField]="'name'"
            [sortOrder]="1"
            styleClass="p-datatable-sm p-datatable-striped"
          >
            <ng-template pTemplate="header">
              <tr>
                <th pSortableColumn="name">Name <p-sortIcon field="name"></p-sortIcon></th>
                <th pSortableColumn="npi">NPI <p-sortIcon field="npi"></p-sortIcon></th>
                <th pSortableColumn="provider_type">Type <p-sortIcon field="provider_type"></p-sortIcon></th>
                <th pSortableColumn="specialty">Specialty <p-sortIcon field="specialty"></p-sortIcon></th>
                <th pSortableColumn="network_status">Network <p-sortIcon field="network_status"></p-sortIcon></th>
                <th pSortableColumn="status">Status <p-sortIcon field="status"></p-sortIcon></th>
                <th>Actions</th>
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-provider>
              <tr>
                <td>{{ getDisplayName(provider) }}</td>
                <td>{{ provider.npi }}</td>
                <td>{{ getTypeLabel(provider.provider_type) }}</td>
                <td>{{ provider.specialty || '-' }}</td>
                <td>
                  <p-tag
                    [value]="getNetworkLabel(provider.network_status)"
                    [severity]="getNetworkSeverity(provider.network_status)"
                  ></p-tag>
                </td>
                <td>
                  <p-tag
                    [value]="provider.status"
                    [severity]="getStatusSeverity(provider.status)"
                  ></p-tag>
                </td>
                <td>
                  <div class="action-buttons">
                    <p-button
                      icon="pi pi-eye"
                      [rounded]="true"
                      [text]="true"
                      pTooltip="View"
                      (onClick)="viewProvider(provider)"
                    ></p-button>
                    <p-button
                      icon="pi pi-pencil"
                      [rounded]="true"
                      [text]="true"
                      pTooltip="Edit"
                      (onClick)="editProvider(provider)"
                    ></p-button>
                    <p-button
                      icon="pi pi-trash"
                      [rounded]="true"
                      [text]="true"
                      severity="danger"
                      pTooltip="Delete"
                      (onClick)="confirmDelete(provider)"
                    ></p-button>
                  </div>
                </td>
              </tr>
            </ng-template>
            <ng-template pTemplate="emptymessage">
              <tr>
                <td colspan="7" class="text-center">
                  No providers found. Click "Add Provider" to create one.
                </td>
              </tr>
            </ng-template>
          </p-table>
        }
      </p-card>

      <!-- Create/Edit Dialog -->
      <p-dialog
        [(visible)]="dialogVisible"
        [header]="editMode ? 'Edit Provider' : 'Add Provider'"
        [modal]="true"
        [style]="{ width: '600px' }"
        [draggable]="false"
        [resizable]="false"
      >
        <div class="form-grid">
          <div class="form-field">
            <label for="providerType">Provider Type *</label>
            <p-dropdown
              id="providerType"
              [options]="typeOptions"
              [(ngModel)]="formData.provider_type"
              placeholder="Select type"
              [style]="{ width: '100%' }"
            ></p-dropdown>
          </div>

          <div class="form-field">
            <label for="npi">NPI *</label>
            <p-inputMask
              id="npi"
              [(ngModel)]="formData.npi"
              mask="9999999999"
              placeholder="1234567890"
              [style]="{ width: '100%' }"
            ></p-inputMask>
          </div>

          <div class="form-field full-width">
            <label for="name">Organization/Provider Name *</label>
            <input
              id="name"
              type="text"
              pInputText
              [(ngModel)]="formData.name"
              placeholder="Enter name"
            />
          </div>

          @if (formData.provider_type === 'individual') {
            <div class="form-field">
              <label for="firstName">First Name</label>
              <input
                id="firstName"
                type="text"
                pInputText
                [(ngModel)]="formData.first_name"
                placeholder="First name"
              />
            </div>

            <div class="form-field">
              <label for="lastName">Last Name</label>
              <input
                id="lastName"
                type="text"
                pInputText
                [(ngModel)]="formData.last_name"
                placeholder="Last name"
              />
            </div>
          }

          <div class="form-field">
            <label for="specialty">Specialty</label>
            <input
              id="specialty"
              type="text"
              pInputText
              [(ngModel)]="formData.specialty"
              placeholder="e.g., Cardiology"
            />
          </div>

          <div class="form-field">
            <label for="networkStatus">Network Status *</label>
            <p-dropdown
              id="networkStatus"
              [options]="networkOptions"
              [(ngModel)]="formData.network_status"
              placeholder="Select network status"
              [style]="{ width: '100%' }"
            ></p-dropdown>
          </div>

          <div class="form-field">
            <label for="phone">Phone</label>
            <p-inputMask
              id="phone"
              [(ngModel)]="formData.phone"
              mask="(999) 999-9999"
              placeholder="(555) 123-4567"
              [style]="{ width: '100%' }"
            ></p-inputMask>
          </div>

          <div class="form-field">
            <label for="email">Email</label>
            <input
              id="email"
              type="email"
              pInputText
              [(ngModel)]="formData.email"
              placeholder="provider@example.com"
            />
          </div>

          <div class="form-field full-width">
            <label for="addressLine1">Address Line 1 *</label>
            <input
              id="addressLine1"
              type="text"
              pInputText
              [(ngModel)]="formData.address.line1"
              placeholder="Street address"
            />
          </div>

          <div class="form-field full-width">
            <label for="addressLine2">Address Line 2</label>
            <input
              id="addressLine2"
              type="text"
              pInputText
              [(ngModel)]="formData.address.line2"
              placeholder="Suite, unit, building, etc."
            />
          </div>

          <div class="form-field">
            <label for="city">City *</label>
            <input
              id="city"
              type="text"
              pInputText
              [(ngModel)]="formData.address.city"
              placeholder="City"
            />
          </div>

          <div class="form-field">
            <label for="state">State *</label>
            <input
              id="state"
              type="text"
              pInputText
              [(ngModel)]="formData.address.state"
              placeholder="State"
              maxlength="2"
            />
          </div>

          <div class="form-field">
            <label for="zipCode">ZIP Code *</label>
            <p-inputMask
              id="zipCode"
              [(ngModel)]="formData.address.zip_code"
              mask="99999"
              placeholder="12345"
              [style]="{ width: '100%' }"
            ></p-inputMask>
          </div>

          <div class="form-field">
            <label for="effectiveDate">Effective Date *</label>
            <input
              id="effectiveDate"
              type="date"
              pInputText
              [(ngModel)]="formData.effective_date"
            />
          </div>

          <div class="form-field checkbox-field">
            <p-checkbox
              [(ngModel)]="formData.accepting_new_patients"
              [binary]="true"
              inputId="acceptingPatients"
            ></p-checkbox>
            <label for="acceptingPatients">Accepting New Patients</label>
          </div>

          <div class="form-field checkbox-field">
            <p-checkbox
              [(ngModel)]="formData.board_certified"
              [binary]="true"
              inputId="boardCertified"
            ></p-checkbox>
            <label for="boardCertified">Board Certified</label>
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
            (onClick)="saveProvider()"
            [disabled]="!isFormValid()"
          ></p-button>
        </ng-template>
      </p-dialog>

      <!-- View Dialog -->
      <p-dialog
        [(visible)]="viewDialogVisible"
        header="Provider Details"
        [modal]="true"
        [style]="{ width: '600px' }"
        [draggable]="false"
        [resizable]="false"
      >
        @if (selectedProvider()) {
          <div class="detail-grid">
            <div class="detail-row">
              <span class="detail-label">Name:</span>
              <span class="detail-value">{{ getDisplayName(selectedProvider()!) }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">NPI:</span>
              <span class="detail-value">{{ selectedProvider()!.npi }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Type:</span>
              <span class="detail-value">{{ getTypeLabel(selectedProvider()!.provider_type) }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Specialty:</span>
              <span class="detail-value">{{ selectedProvider()!.specialty || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Network Status:</span>
              <p-tag
                [value]="getNetworkLabel(selectedProvider()!.network_status)"
                [severity]="getNetworkSeverity(selectedProvider()!.network_status)"
              ></p-tag>
            </div>
            <div class="detail-row">
              <span class="detail-label">Status:</span>
              <p-tag
                [value]="selectedProvider()!.status"
                [severity]="getStatusSeverity(selectedProvider()!.status)"
              ></p-tag>
            </div>
            <div class="detail-row">
              <span class="detail-label">Phone:</span>
              <span class="detail-value">{{ selectedProvider()!.phone || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Email:</span>
              <span class="detail-value">{{ selectedProvider()!.email || '-' }}</span>
            </div>
            <div class="detail-row full-width">
              <span class="detail-label">Address:</span>
              <span class="detail-value">
                {{ selectedProvider()!.address.line1 }}
                @if (selectedProvider()!.address.line2) {
                  <br>{{ selectedProvider()!.address.line2 }}
                }
                <br>{{ selectedProvider()!.address.city }}, {{ selectedProvider()!.address.state }} {{ selectedProvider()!.address.zip_code }}
              </span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Accepting Patients:</span>
              <span class="detail-value">{{ selectedProvider()!.accepting_new_patients ? 'Yes' : 'No' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Board Certified:</span>
              <span class="detail-value">{{ selectedProvider()!.board_certified ? 'Yes' : 'No' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Effective Date:</span>
              <span class="detail-value">{{ selectedProvider()!.effective_date | date }}</span>
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

      .checkbox-field {
        flex-direction: row;
        align-items: center;
        gap: 0.5rem;
      }

      .checkbox-field label {
        font-weight: normal;
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
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProvidersListComponent implements OnInit {
  protected readonly store = inject(ProvidersStore);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly messageService = inject(MessageService);

  // Filters
  searchTerm = '';
  selectedStatus: ProviderStatus | null = null;
  selectedNetwork: NetworkStatus | null = null;
  selectedType: ProviderType | null = null;

  // Dialog state
  dialogVisible = false;
  viewDialogVisible = false;
  editMode = false;
  selectedProvider = signal<Provider | null>(null);

  // Form data
  formData: ProviderCreate = this.getEmptyFormData();

  // Dropdown options
  statusOptions = [
    { label: 'Active', value: ProviderStatus.ACTIVE },
    { label: 'Inactive', value: ProviderStatus.INACTIVE },
    { label: 'Pending', value: ProviderStatus.PENDING },
    { label: 'Suspended', value: ProviderStatus.SUSPENDED },
    { label: 'Terminated', value: ProviderStatus.TERMINATED },
  ];

  networkOptions = [
    { label: 'In-Network', value: NetworkStatus.IN_NETWORK },
    { label: 'Out-of-Network', value: NetworkStatus.OUT_OF_NETWORK },
    { label: 'Preferred', value: NetworkStatus.PREFERRED },
    { label: 'Non-Participating', value: NetworkStatus.NON_PARTICIPATING },
  ];

  typeOptions = [
    { label: 'Individual', value: ProviderType.INDIVIDUAL },
    { label: 'Organization', value: ProviderType.ORGANIZATION },
    { label: 'Facility', value: ProviderType.FACILITY },
  ];

  ngOnInit(): void {
    this.loadMockData();
  }

  private loadMockData(): void {
    // Mock data for development
    const mockProviders: Provider[] = [
      {
        id: 'prov-1',
        provider_id: 'PROV001',
        npi: '1234567890',
        name: 'Dr. John Smith',
        first_name: 'John',
        last_name: 'Smith',
        provider_type: ProviderType.INDIVIDUAL,
        specialty: 'Cardiology',
        address: {
          line1: '123 Medical Center Dr',
          city: 'Austin',
          state: 'TX',
          zip_code: '78701',
          country: 'USA',
        },
        phone: '(512) 555-1234',
        email: 'dr.smith@example.com',
        network_status: NetworkStatus.IN_NETWORK,
        network_ids: ['net-1'],
        effective_date: '2023-01-01',
        status: ProviderStatus.ACTIVE,
        board_certified: true,
        accepting_new_patients: true,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2024-01-15T00:00:00Z',
      },
      {
        id: 'prov-2',
        provider_id: 'PROV002',
        npi: '0987654321',
        name: 'Austin General Hospital',
        provider_type: ProviderType.FACILITY,
        specialty: 'General Hospital',
        address: {
          line1: '456 Hospital Blvd',
          city: 'Austin',
          state: 'TX',
          zip_code: '78702',
          country: 'USA',
        },
        phone: '(512) 555-5678',
        network_status: NetworkStatus.PREFERRED,
        network_ids: ['net-1', 'net-2'],
        effective_date: '2022-06-01',
        status: ProviderStatus.ACTIVE,
        board_certified: false,
        accepting_new_patients: true,
        created_at: '2022-06-01T00:00:00Z',
        updated_at: '2024-01-10T00:00:00Z',
      },
      {
        id: 'prov-3',
        provider_id: 'PROV003',
        npi: '5555555555',
        name: 'Dr. Sarah Johnson',
        first_name: 'Sarah',
        last_name: 'Johnson',
        provider_type: ProviderType.INDIVIDUAL,
        specialty: 'Pediatrics',
        address: {
          line1: '789 Pediatric Way',
          city: 'Round Rock',
          state: 'TX',
          zip_code: '78664',
          country: 'USA',
        },
        phone: '(512) 555-9012',
        email: 'dr.johnson@example.com',
        network_status: NetworkStatus.OUT_OF_NETWORK,
        network_ids: [],
        effective_date: '2023-03-15',
        status: ProviderStatus.ACTIVE,
        board_certified: true,
        accepting_new_patients: false,
        created_at: '2023-03-15T00:00:00Z',
        updated_at: '2024-01-05T00:00:00Z',
      },
    ];

    this.store.setProviders(mockProviders);
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
      inNetwork: this.selectedNetwork === 'in_network' ? true : this.selectedNetwork === 'out_of_network' ? false : undefined,
      providerType: this.selectedType || undefined,
    });
  }

  openCreateDialog(): void {
    this.editMode = false;
    this.formData = this.getEmptyFormData();
    this.dialogVisible = true;
  }

  viewProvider(provider: Provider): void {
    this.selectedProvider.set(provider);
    this.viewDialogVisible = true;
  }

  editProvider(provider: Provider): void {
    this.editMode = true;
    this.selectedProvider.set(provider);
    this.formData = {
      npi: provider.npi,
      name: provider.name,
      first_name: provider.first_name,
      last_name: provider.last_name,
      provider_type: provider.provider_type,
      specialty: provider.specialty,
      address: { ...provider.address },
      phone: provider.phone,
      email: provider.email,
      network_status: provider.network_status,
      network_ids: [...provider.network_ids],
      effective_date: provider.effective_date,
      board_certified: provider.board_certified,
      accepting_new_patients: provider.accepting_new_patients,
    };
    this.dialogVisible = true;
  }

  confirmDelete(provider: Provider): void {
    this.confirmationService.confirm({
      message: `Are you sure you want to delete provider "${this.getDisplayName(provider)}"?`,
      header: 'Confirm Delete',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        this.store.removeProvider(provider.id);
        this.messageService.add({
          severity: 'success',
          summary: 'Deleted',
          detail: 'Provider has been deleted.',
        });
      },
    });
  }

  closeDialog(): void {
    this.dialogVisible = false;
    this.formData = this.getEmptyFormData();
  }

  saveProvider(): void {
    if (!this.isFormValid()) return;

    if (this.editMode && this.selectedProvider()) {
      const updates: Partial<Provider> = {
        ...this.formData,
        address: {
          ...this.formData.address,
          country: this.formData.address.country || 'USA',
        },
      };
      this.store.updateProvider(this.selectedProvider()!.id, updates);
      this.messageService.add({
        severity: 'success',
        summary: 'Updated',
        detail: 'Provider has been updated.',
      });
    } else {
      const newProvider: Provider = {
        id: `prov-${Date.now()}`,
        provider_id: `PROV${Date.now()}`,
        ...this.formData,
        address: {
          ...this.formData.address,
          country: this.formData.address.country || 'USA',
        },
        network_status: this.formData.network_status || NetworkStatus.OUT_OF_NETWORK,
        network_ids: this.formData.network_ids || [],
        status: ProviderStatus.ACTIVE,
        board_certified: this.formData.board_certified || false,
        accepting_new_patients: this.formData.accepting_new_patients || false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      this.store.addProvider(newProvider);
      this.messageService.add({
        severity: 'success',
        summary: 'Created',
        detail: 'Provider has been created.',
      });
    }

    this.closeDialog();
  }

  isFormValid(): boolean {
    return !!(
      this.formData.npi &&
      this.formData.name &&
      this.formData.provider_type &&
      this.formData.address.line1 &&
      this.formData.address.city &&
      this.formData.address.state &&
      this.formData.address.zip_code &&
      this.formData.effective_date
    );
  }

  getDisplayName(provider: Provider): string {
    return getProviderDisplayName(provider);
  }

  getNetworkLabel(status: NetworkStatus): string {
    return getNetworkStatusLabel(status);
  }

  getTypeLabel(type: ProviderType): string {
    const labels: Record<ProviderType, string> = {
      [ProviderType.INDIVIDUAL]: 'Individual',
      [ProviderType.ORGANIZATION]: 'Organization',
      [ProviderType.FACILITY]: 'Facility',
    };
    return labels[type] || type;
  }

  getStatusSeverity(status: ProviderStatus): 'success' | 'info' | 'warning' | 'danger' {
    const severities: Record<ProviderStatus, 'success' | 'info' | 'warning' | 'danger'> = {
      [ProviderStatus.ACTIVE]: 'success',
      [ProviderStatus.INACTIVE]: 'info',
      [ProviderStatus.PENDING]: 'warning',
      [ProviderStatus.SUSPENDED]: 'warning',
      [ProviderStatus.TERMINATED]: 'danger',
    };
    return severities[status] || 'info';
  }

  getNetworkSeverity(status: NetworkStatus): 'success' | 'info' | 'warning' | 'danger' {
    const severities: Record<NetworkStatus, 'success' | 'info' | 'warning' | 'danger'> = {
      [NetworkStatus.IN_NETWORK]: 'success',
      [NetworkStatus.PREFERRED]: 'success',
      [NetworkStatus.OUT_OF_NETWORK]: 'warning',
      [NetworkStatus.NON_PARTICIPATING]: 'danger',
    };
    return severities[status] || 'info';
  }

  private getEmptyFormData(): ProviderCreate {
    return {
      npi: '',
      name: '',
      first_name: '',
      last_name: '',
      provider_type: ProviderType.INDIVIDUAL,
      specialty: '',
      address: {
        line1: '',
        line2: '',
        city: '',
        state: '',
        zip_code: '',
      },
      phone: '',
      email: '',
      network_status: NetworkStatus.IN_NETWORK,
      network_ids: [],
      effective_date: new Date().toISOString().split('T')[0],
      board_certified: false,
      accepting_new_patients: true,
    };
  }
}
