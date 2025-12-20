/**
 * Members List Component.
 * Source: Design Document Section 3.4
 * Source: Phase 4 Implementation Document
 * Verified: 2025-12-18
 *
 * Full CRUD management for enrolled members.
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
import { CalendarModule } from 'primeng/calendar';
import { ProgressSpinnerModule } from 'primeng/progressspinner';

import {
  Member,
  MemberCreate,
  MemberStatus,
  Gender,
  RelationshipType,
  getMemberFullName,
  maskSSN,
} from '@claims-processing/models';
import { MembersStore } from '@claims-processing/data-access';

@Component({
  selector: 'app-members-list',
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
    CalendarModule,
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
            <h2>Members Management</h2>
            <p-button
              icon="pi pi-plus"
              label="Add Member"
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
              placeholder="Search by name or ID..."
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
            [options]="relationshipOptions"
            [(ngModel)]="selectedRelationship"
            placeholder="All Relationships"
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
            [value]="store.filteredMembers()"
            [paginator]="true"
            [rows]="10"
            [rowsPerPageOptions]="[10, 25, 50]"
            [showCurrentPageReport]="true"
            currentPageReportTemplate="Showing {first} to {last} of {totalRecords} members"
            [sortField]="'last_name'"
            [sortOrder]="1"
            styleClass="p-datatable-sm p-datatable-striped"
          >
            <ng-template pTemplate="header">
              <tr>
                <th pSortableColumn="member_id">Member ID <p-sortIcon field="member_id"></p-sortIcon></th>
                <th pSortableColumn="last_name">Name <p-sortIcon field="last_name"></p-sortIcon></th>
                <th pSortableColumn="date_of_birth">DOB <p-sortIcon field="date_of_birth"></p-sortIcon></th>
                <th pSortableColumn="relationship_to_subscriber">Relationship <p-sortIcon field="relationship_to_subscriber"></p-sortIcon></th>
                <th pSortableColumn="coverage_start_date">Coverage Start <p-sortIcon field="coverage_start_date"></p-sortIcon></th>
                <th pSortableColumn="status">Status <p-sortIcon field="status"></p-sortIcon></th>
                <th>Actions</th>
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-member>
              <tr>
                <td>{{ member.member_id }}</td>
                <td>{{ getFullName(member) }}</td>
                <td>{{ member.date_of_birth | date:'MM/dd/yyyy' }}</td>
                <td>{{ getRelationshipLabel(member.relationship_to_subscriber) }}</td>
                <td>{{ member.coverage_start_date | date:'MM/dd/yyyy' }}</td>
                <td>
                  <p-tag
                    [value]="member.status"
                    [severity]="getStatusSeverity(member.status)"
                  ></p-tag>
                </td>
                <td>
                  <div class="action-buttons">
                    <p-button
                      icon="pi pi-eye"
                      [rounded]="true"
                      [text]="true"
                      pTooltip="View"
                      (onClick)="viewMember(member)"
                    ></p-button>
                    <p-button
                      icon="pi pi-pencil"
                      [rounded]="true"
                      [text]="true"
                      pTooltip="Edit"
                      (onClick)="editMember(member)"
                    ></p-button>
                    <p-button
                      icon="pi pi-trash"
                      [rounded]="true"
                      [text]="true"
                      severity="danger"
                      pTooltip="Delete"
                      (onClick)="confirmDelete(member)"
                    ></p-button>
                  </div>
                </td>
              </tr>
            </ng-template>
            <ng-template pTemplate="emptymessage">
              <tr>
                <td colspan="7" class="text-center">
                  No members found. Click "Add Member" to create one.
                </td>
              </tr>
            </ng-template>
          </p-table>
        }
      </p-card>

      <!-- Create/Edit Dialog -->
      <p-dialog
        [(visible)]="dialogVisible"
        [header]="editMode ? 'Edit Member' : 'Add Member'"
        [modal]="true"
        [style]="{ width: '650px' }"
        [draggable]="false"
        [resizable]="false"
      >
        <div class="form-grid">
          <div class="form-field">
            <label for="firstName">First Name *</label>
            <input
              id="firstName"
              type="text"
              pInputText
              [(ngModel)]="formData.first_name"
              placeholder="First name"
            />
          </div>

          <div class="form-field">
            <label for="lastName">Last Name *</label>
            <input
              id="lastName"
              type="text"
              pInputText
              [(ngModel)]="formData.last_name"
              placeholder="Last name"
            />
          </div>

          <div class="form-field">
            <label for="middleName">Middle Name</label>
            <input
              id="middleName"
              type="text"
              pInputText
              [(ngModel)]="formData.middle_name"
              placeholder="Middle name"
            />
          </div>

          <div class="form-field">
            <label for="dob">Date of Birth *</label>
            <input
              id="dob"
              type="date"
              pInputText
              [(ngModel)]="formData.date_of_birth"
            />
          </div>

          <div class="form-field">
            <label for="gender">Gender *</label>
            <p-dropdown
              id="gender"
              [options]="genderOptions"
              [(ngModel)]="formData.gender"
              placeholder="Select gender"
              [style]="{ width: '100%' }"
            ></p-dropdown>
          </div>

          <div class="form-field">
            <label for="ssn">SSN (Last 4 digits)</label>
            <p-inputMask
              id="ssn"
              [(ngModel)]="formData.ssn"
              mask="9999"
              placeholder="1234"
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
              placeholder="member@example.com"
            />
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
              placeholder="Apt, suite, unit, etc."
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
            <label for="relationship">Relationship *</label>
            <p-dropdown
              id="relationship"
              [options]="relationshipOptions"
              [(ngModel)]="formData.relationship_to_subscriber"
              placeholder="Select relationship"
              [style]="{ width: '100%' }"
            ></p-dropdown>
          </div>

          <div class="form-field">
            <label for="policyId">Policy ID *</label>
            <input
              id="policyId"
              type="text"
              pInputText
              [(ngModel)]="formData.policy_id"
              placeholder="POL-001"
            />
          </div>

          <div class="form-field">
            <label for="subscriberId">Subscriber ID</label>
            <input
              id="subscriberId"
              type="text"
              pInputText
              [(ngModel)]="formData.subscriber_id"
              placeholder="Subscriber ID (if dependent)"
            />
          </div>

          <div class="form-field">
            <label for="coverageStart">Coverage Start Date *</label>
            <input
              id="coverageStart"
              type="date"
              pInputText
              [(ngModel)]="formData.coverage_start_date"
            />
          </div>

          <div class="form-field">
            <label for="coverageEnd">Coverage End Date</label>
            <input
              id="coverageEnd"
              type="date"
              pInputText
              [(ngModel)]="formData.coverage_end_date"
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
            (onClick)="saveMember()"
            [disabled]="!isFormValid()"
          ></p-button>
        </ng-template>
      </p-dialog>

      <!-- View Dialog -->
      <p-dialog
        [(visible)]="viewDialogVisible"
        header="Member Details"
        [modal]="true"
        [style]="{ width: '600px' }"
        [draggable]="false"
        [resizable]="false"
      >
        @if (selectedMember()) {
          <div class="detail-grid">
            <div class="detail-row">
              <span class="detail-label">Member ID:</span>
              <span class="detail-value">{{ selectedMember()!.member_id }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Full Name:</span>
              <span class="detail-value">{{ getFullName(selectedMember()!) }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Date of Birth:</span>
              <span class="detail-value">{{ selectedMember()!.date_of_birth | date:'MM/dd/yyyy' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Gender:</span>
              <span class="detail-value">{{ getGenderLabel(selectedMember()!.gender) }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">SSN:</span>
              <span class="detail-value">{{ maskSsn(selectedMember()!.ssn_last_four) }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Relationship:</span>
              <span class="detail-value">{{ getRelationshipLabel(selectedMember()!.relationship_to_subscriber) }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Email:</span>
              <span class="detail-value">{{ selectedMember()!.email || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Phone:</span>
              <span class="detail-value">{{ selectedMember()!.phone || '-' }}</span>
            </div>
            <div class="detail-row full-width">
              <span class="detail-label">Address:</span>
              <span class="detail-value">
                {{ selectedMember()!.address.line1 }}
                @if (selectedMember()!.address.line2) {
                  <br>{{ selectedMember()!.address.line2 }}
                }
                <br>{{ selectedMember()!.address.city }}, {{ selectedMember()!.address.state }} {{ selectedMember()!.address.zip_code }}
              </span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Policy ID:</span>
              <span class="detail-value">{{ selectedMember()!.policy_id }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Coverage Start:</span>
              <span class="detail-value">{{ selectedMember()!.coverage_start_date | date:'MM/dd/yyyy' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Coverage End:</span>
              <span class="detail-value">{{ selectedMember()!.coverage_end_date ? (selectedMember()!.coverage_end_date | date:'MM/dd/yyyy') : 'Active' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Status:</span>
              <p-tag
                [value]="selectedMember()!.status"
                [severity]="getStatusSeverity(selectedMember()!.status)"
              ></p-tag>
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
export class MembersListComponent implements OnInit {
  protected readonly store = inject(MembersStore);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly messageService = inject(MessageService);

  // Filters
  searchTerm = '';
  selectedStatus: MemberStatus | null = null;
  selectedRelationship: RelationshipType | null = null;

  // Dialog state
  dialogVisible = false;
  viewDialogVisible = false;
  editMode = false;
  selectedMember = signal<Member | null>(null);

  // Form data
  formData: MemberCreate = this.getEmptyFormData();

  // Dropdown options
  statusOptions = [
    { label: 'Active', value: MemberStatus.ACTIVE },
    { label: 'Inactive', value: MemberStatus.INACTIVE },
    { label: 'Pending', value: MemberStatus.PENDING },
    { label: 'Terminated', value: MemberStatus.TERMINATED },
  ];

  genderOptions = [
    { label: 'Male', value: Gender.MALE },
    { label: 'Female', value: Gender.FEMALE },
    { label: 'Other', value: Gender.OTHER },
    { label: 'Unknown', value: Gender.UNKNOWN },
  ];

  relationshipOptions = [
    { label: 'Self (Subscriber)', value: RelationshipType.SELF },
    { label: 'Spouse', value: RelationshipType.SPOUSE },
    { label: 'Child', value: RelationshipType.CHILD },
    { label: 'Domestic Partner', value: RelationshipType.DOMESTIC_PARTNER },
    { label: 'Other', value: RelationshipType.OTHER },
  ];

  ngOnInit(): void {
    this.loadMockData();
  }

  private loadMockData(): void {
    const mockMembers: Member[] = [
      {
        id: 'mem-1',
        member_id: 'MEM001',
        first_name: 'John',
        last_name: 'Doe',
        middle_name: 'Robert',
        date_of_birth: '1985-05-15',
        gender: Gender.MALE,
        ssn_last_four: '1234',
        email: 'john.doe@example.com',
        phone: '(512) 555-1234',
        address: {
          line1: '123 Main Street',
          city: 'Austin',
          state: 'TX',
          zip_code: '78701',
          country: 'USA',
        },
        policy_id: 'POL-001',
        relationship_to_subscriber: RelationshipType.SELF,
        coverage_start_date: '2023-01-01',
        status: MemberStatus.ACTIVE,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2024-01-15T00:00:00Z',
      },
      {
        id: 'mem-2',
        member_id: 'MEM002',
        first_name: 'Jane',
        last_name: 'Doe',
        date_of_birth: '1987-08-22',
        gender: Gender.FEMALE,
        ssn_last_four: '5678',
        email: 'jane.doe@example.com',
        phone: '(512) 555-5678',
        address: {
          line1: '123 Main Street',
          city: 'Austin',
          state: 'TX',
          zip_code: '78701',
          country: 'USA',
        },
        policy_id: 'POL-001',
        subscriber_id: 'mem-1',
        relationship_to_subscriber: RelationshipType.SPOUSE,
        coverage_start_date: '2023-01-01',
        status: MemberStatus.ACTIVE,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2024-01-15T00:00:00Z',
      },
      {
        id: 'mem-3',
        member_id: 'MEM003',
        first_name: 'Emily',
        last_name: 'Doe',
        date_of_birth: '2015-03-10',
        gender: Gender.FEMALE,
        address: {
          line1: '123 Main Street',
          city: 'Austin',
          state: 'TX',
          zip_code: '78701',
          country: 'USA',
        },
        policy_id: 'POL-001',
        subscriber_id: 'mem-1',
        relationship_to_subscriber: RelationshipType.CHILD,
        coverage_start_date: '2023-01-01',
        status: MemberStatus.ACTIVE,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2024-01-15T00:00:00Z',
      },
      {
        id: 'mem-4',
        member_id: 'MEM004',
        first_name: 'Michael',
        last_name: 'Smith',
        date_of_birth: '1978-11-03',
        gender: Gender.MALE,
        ssn_last_four: '9012',
        email: 'michael.smith@example.com',
        phone: '(512) 555-9012',
        address: {
          line1: '456 Oak Avenue',
          city: 'Round Rock',
          state: 'TX',
          zip_code: '78664',
          country: 'USA',
        },
        policy_id: 'POL-002',
        relationship_to_subscriber: RelationshipType.SELF,
        coverage_start_date: '2022-06-01',
        coverage_end_date: '2024-05-31',
        status: MemberStatus.INACTIVE,
        created_at: '2022-06-01T00:00:00Z',
        updated_at: '2024-05-31T00:00:00Z',
      },
    ];

    this.store.setMembers(mockMembers);
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
    });
  }

  openCreateDialog(): void {
    this.editMode = false;
    this.formData = this.getEmptyFormData();
    this.dialogVisible = true;
  }

  viewMember(member: Member): void {
    this.selectedMember.set(member);
    this.viewDialogVisible = true;
  }

  editMember(member: Member): void {
    this.editMode = true;
    this.selectedMember.set(member);
    this.formData = {
      first_name: member.first_name,
      last_name: member.last_name,
      middle_name: member.middle_name,
      date_of_birth: member.date_of_birth,
      gender: member.gender,
      ssn: member.ssn_last_four,
      email: member.email,
      phone: member.phone,
      address: { ...member.address },
      policy_id: member.policy_id,
      subscriber_id: member.subscriber_id,
      relationship_to_subscriber: member.relationship_to_subscriber,
      coverage_start_date: member.coverage_start_date,
      coverage_end_date: member.coverage_end_date,
    };
    this.dialogVisible = true;
  }

  confirmDelete(member: Member): void {
    this.confirmationService.confirm({
      message: `Are you sure you want to delete member "${this.getFullName(member)}"?`,
      header: 'Confirm Delete',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        this.store.removeMember(member.id);
        this.messageService.add({
          severity: 'success',
          summary: 'Deleted',
          detail: 'Member has been deleted.',
        });
      },
    });
  }

  closeDialog(): void {
    this.dialogVisible = false;
    this.formData = this.getEmptyFormData();
  }

  saveMember(): void {
    if (!this.isFormValid()) return;

    if (this.editMode && this.selectedMember()) {
      this.store.updateMember(this.selectedMember()!.id, {
        first_name: this.formData.first_name,
        last_name: this.formData.last_name,
        middle_name: this.formData.middle_name,
        email: this.formData.email,
        phone: this.formData.phone,
        address: {
          ...this.formData.address,
          country: this.formData.address.country || 'USA',
        },
        coverage_end_date: this.formData.coverage_end_date,
      });
      this.messageService.add({
        severity: 'success',
        summary: 'Updated',
        detail: 'Member has been updated.',
      });
    } else {
      const newMember: Member = {
        id: `mem-${Date.now()}`,
        member_id: `MEM${Date.now().toString().slice(-6)}`,
        first_name: this.formData.first_name,
        last_name: this.formData.last_name,
        middle_name: this.formData.middle_name,
        date_of_birth: this.formData.date_of_birth,
        gender: this.formData.gender,
        ssn_last_four: this.formData.ssn,
        email: this.formData.email,
        phone: this.formData.phone,
        address: {
          ...this.formData.address,
          country: this.formData.address.country || 'USA',
        },
        policy_id: this.formData.policy_id,
        subscriber_id: this.formData.subscriber_id,
        relationship_to_subscriber: this.formData.relationship_to_subscriber,
        coverage_start_date: this.formData.coverage_start_date,
        coverage_end_date: this.formData.coverage_end_date,
        status: MemberStatus.ACTIVE,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      this.store.addMember(newMember);
      this.messageService.add({
        severity: 'success',
        summary: 'Created',
        detail: 'Member has been created.',
      });
    }

    this.closeDialog();
  }

  isFormValid(): boolean {
    return !!(
      this.formData.first_name &&
      this.formData.last_name &&
      this.formData.date_of_birth &&
      this.formData.gender &&
      this.formData.address.line1 &&
      this.formData.address.city &&
      this.formData.address.state &&
      this.formData.address.zip_code &&
      this.formData.policy_id &&
      this.formData.relationship_to_subscriber &&
      this.formData.coverage_start_date
    );
  }

  getFullName(member: Member): string {
    return getMemberFullName(member);
  }

  maskSsn(ssn?: string): string {
    return maskSSN(ssn || '');
  }

  getGenderLabel(gender: Gender): string {
    const labels: Record<Gender, string> = {
      [Gender.MALE]: 'Male',
      [Gender.FEMALE]: 'Female',
      [Gender.OTHER]: 'Other',
      [Gender.UNKNOWN]: 'Unknown',
    };
    return labels[gender] || gender;
  }

  getRelationshipLabel(relationship: RelationshipType): string {
    const labels: Record<RelationshipType, string> = {
      [RelationshipType.SELF]: 'Self',
      [RelationshipType.SPOUSE]: 'Spouse',
      [RelationshipType.CHILD]: 'Child',
      [RelationshipType.DOMESTIC_PARTNER]: 'Domestic Partner',
      [RelationshipType.OTHER]: 'Other',
    };
    return labels[relationship] || relationship;
  }

  getStatusSeverity(status: MemberStatus): 'success' | 'info' | 'warning' | 'danger' {
    const severities: Record<MemberStatus, 'success' | 'info' | 'warning' | 'danger'> = {
      [MemberStatus.ACTIVE]: 'success',
      [MemberStatus.INACTIVE]: 'info',
      [MemberStatus.PENDING]: 'warning',
      [MemberStatus.TERMINATED]: 'danger',
    };
    return severities[status] || 'info';
  }

  private getEmptyFormData(): MemberCreate {
    return {
      first_name: '',
      last_name: '',
      middle_name: '',
      date_of_birth: '',
      gender: Gender.UNKNOWN,
      ssn: '',
      email: '',
      phone: '',
      address: {
        line1: '',
        line2: '',
        city: '',
        state: '',
        zip_code: '',
      },
      policy_id: '',
      subscriber_id: '',
      relationship_to_subscriber: RelationshipType.SELF,
      coverage_start_date: new Date().toISOString().split('T')[0],
      coverage_end_date: undefined,
    };
  }
}
