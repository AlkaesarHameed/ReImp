/**
 * Users List Component.
 * Source: Design Document Section 3.4
 * Source: Phase 4 Implementation Document
 * Verified: 2025-12-18
 *
 * Full CRUD management for system users with RBAC.
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
import { PasswordModule } from 'primeng/password';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { AvatarModule } from 'primeng/avatar';
import { MenuModule } from 'primeng/menu';

import {
  User,
  UserCreate,
  UserRole,
  UserStatus,
  getRoleLabel,
  getStatusSeverity,
} from '@claims-processing/models';
import { UsersStore } from '@claims-processing/data-access';

@Component({
  selector: 'app-users-list',
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
    PasswordModule,
    ProgressSpinnerModule,
    AvatarModule,
    MenuModule,
  ],
  providers: [ConfirmationService, MessageService],
  template: `
    <div class="admin-container">
      <p-toast></p-toast>
      <p-confirmDialog></p-confirmDialog>

      <p-card>
        <ng-template pTemplate="header">
          <div class="card-header">
            <h2>Users Management</h2>
            <p-button
              icon="pi pi-plus"
              label="Add User"
              (onClick)="openCreateDialog()"
            ></p-button>
          </div>
        </ng-template>

        <!-- Stats Summary -->
        <div class="stats-row">
          <div class="stat-card">
            <span class="stat-value">{{ store.users().length }}</span>
            <span class="stat-label">Total Users</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ store.activeUsers().length }}</span>
            <span class="stat-label">Active</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ store.lockedUsers().length }}</span>
            <span class="stat-label">Locked</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ store.adminCount() }}</span>
            <span class="stat-label">Admins</span>
          </div>
        </div>

        <!-- Filters -->
        <div class="filters-row">
          <span class="p-input-icon-left">
            <i class="pi pi-search"></i>
            <input
              type="text"
              pInputText
              placeholder="Search by name or email..."
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
            [options]="roleOptions"
            [(ngModel)]="selectedRole"
            placeholder="All Roles"
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
            [value]="store.filteredUsers()"
            [paginator]="true"
            [rows]="10"
            [rowsPerPageOptions]="[10, 25, 50]"
            [showCurrentPageReport]="true"
            currentPageReportTemplate="Showing {first} to {last} of {totalRecords} users"
            [sortField]="'last_name'"
            [sortOrder]="1"
            styleClass="p-datatable-sm p-datatable-striped"
          >
            <ng-template pTemplate="header">
              <tr>
                <th>User</th>
                <th pSortableColumn="email">Email <p-sortIcon field="email"></p-sortIcon></th>
                <th pSortableColumn="role">Role <p-sortIcon field="role"></p-sortIcon></th>
                <th pSortableColumn="status">Status <p-sortIcon field="status"></p-sortIcon></th>
                <th pSortableColumn="last_login">Last Login <p-sortIcon field="last_login"></p-sortIcon></th>
                <th>Actions</th>
              </tr>
            </ng-template>
            <ng-template pTemplate="body" let-user>
              <tr>
                <td>
                  <div class="user-info">
                    <p-avatar
                      [label]="getInitials(user)"
                      shape="circle"
                      [style]="{ 'background-color': getAvatarColor(user.role), color: '#fff' }"
                    ></p-avatar>
                    <div class="user-details">
                      <span class="user-name">{{ user.first_name }} {{ user.last_name }}</span>
                    </div>
                  </div>
                </td>
                <td>{{ user.email }}</td>
                <td>
                  <p-tag
                    [value]="getRoleDisplayLabel(user.role)"
                    [severity]="getRoleSeverity(user.role)"
                  ></p-tag>
                </td>
                <td>
                  <p-tag
                    [value]="user.status"
                    [severity]="getUserStatusSeverity(user.status)"
                  ></p-tag>
                </td>
                <td>{{ user.last_login ? (user.last_login | date:'MM/dd/yyyy HH:mm') : 'Never' }}</td>
                <td>
                  <div class="action-buttons">
                    <p-button
                      icon="pi pi-eye"
                      [rounded]="true"
                      [text]="true"
                      pTooltip="View"
                      (onClick)="viewUser(user)"
                    ></p-button>
                    <p-button
                      icon="pi pi-pencil"
                      [rounded]="true"
                      [text]="true"
                      pTooltip="Edit"
                      (onClick)="editUser(user)"
                    ></p-button>
                    @if (user.status === 'locked') {
                      <p-button
                        icon="pi pi-unlock"
                        [rounded]="true"
                        [text]="true"
                        severity="success"
                        pTooltip="Unlock"
                        (onClick)="unlockUser(user)"
                      ></p-button>
                    } @else if (user.status === 'active') {
                      <p-button
                        icon="pi pi-lock"
                        [rounded]="true"
                        [text]="true"
                        severity="warning"
                        pTooltip="Lock"
                        (onClick)="lockUser(user)"
                      ></p-button>
                    }
                    <p-button
                      icon="pi pi-key"
                      [rounded]="true"
                      [text]="true"
                      pTooltip="Reset Password"
                      (onClick)="confirmResetPassword(user)"
                    ></p-button>
                    <p-button
                      icon="pi pi-trash"
                      [rounded]="true"
                      [text]="true"
                      severity="danger"
                      pTooltip="Delete"
                      (onClick)="confirmDelete(user)"
                    ></p-button>
                  </div>
                </td>
              </tr>
            </ng-template>
            <ng-template pTemplate="emptymessage">
              <tr>
                <td colspan="6" class="text-center">
                  No users found. Click "Add User" to create one.
                </td>
              </tr>
            </ng-template>
          </p-table>
        }
      </p-card>

      <!-- Create/Edit Dialog -->
      <p-dialog
        [(visible)]="dialogVisible"
        [header]="editMode ? 'Edit User' : 'Add User'"
        [modal]="true"
        [style]="{ width: '500px' }"
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

          <div class="form-field full-width">
            <label for="email">Email *</label>
            <input
              id="email"
              type="email"
              pInputText
              [(ngModel)]="formData.email"
              placeholder="user@example.com"
              [disabled]="editMode"
            />
          </div>

          @if (!editMode) {
            <div class="form-field full-width">
              <label for="password">Password *</label>
              <p-password
                id="password"
                [(ngModel)]="formData.password"
                [toggleMask]="true"
                [feedback]="true"
                placeholder="Enter password"
                [style]="{ width: '100%' }"
                [inputStyle]="{ width: '100%' }"
              ></p-password>
            </div>
          }

          <div class="form-field full-width">
            <label for="role">Role *</label>
            <p-dropdown
              id="role"
              [options]="roleOptions"
              [(ngModel)]="formData.role"
              placeholder="Select role"
              [style]="{ width: '100%' }"
            ></p-dropdown>
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
            (onClick)="saveUser()"
            [disabled]="!isFormValid()"
          ></p-button>
        </ng-template>
      </p-dialog>

      <!-- View Dialog -->
      <p-dialog
        [(visible)]="viewDialogVisible"
        header="User Details"
        [modal]="true"
        [style]="{ width: '500px' }"
        [draggable]="false"
        [resizable]="false"
      >
        @if (selectedUser()) {
          <div class="user-profile">
            <div class="profile-header">
              <p-avatar
                [label]="getInitials(selectedUser()!)"
                size="xlarge"
                shape="circle"
                [style]="{ 'background-color': getAvatarColor(selectedUser()!.role), color: '#fff', 'font-size': '1.5rem' }"
              ></p-avatar>
              <div class="profile-name">
                <h3>{{ selectedUser()!.first_name }} {{ selectedUser()!.last_name }}</h3>
                <span>{{ selectedUser()!.email }}</span>
              </div>
            </div>

            <div class="detail-grid">
              <div class="detail-row">
                <span class="detail-label">Role:</span>
                <p-tag
                  [value]="getRoleDisplayLabel(selectedUser()!.role)"
                  [severity]="getRoleSeverity(selectedUser()!.role)"
                ></p-tag>
              </div>
              <div class="detail-row">
                <span class="detail-label">Status:</span>
                <p-tag
                  [value]="selectedUser()!.status"
                  [severity]="getUserStatusSeverity(selectedUser()!.status)"
                ></p-tag>
              </div>
              <div class="detail-row">
                <span class="detail-label">Created:</span>
                <span class="detail-value">{{ selectedUser()!.created_at | date:'MM/dd/yyyy' }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Last Login:</span>
                <span class="detail-value">{{ selectedUser()!.last_login ? (selectedUser()!.last_login | date:'MM/dd/yyyy HH:mm') : 'Never' }}</span>
              </div>
              @if (selectedUser()!.locked_at) {
                <div class="detail-row full-width">
                  <span class="detail-label">Locked At:</span>
                  <span class="detail-value locked">{{ selectedUser()!.locked_at | date:'MM/dd/yyyy HH:mm' }}</span>
                </div>
              }
              <div class="detail-row">
                <span class="detail-label">Failed Logins:</span>
                <span class="detail-value" [class.warning]="selectedUser()!.failed_login_attempts > 2">
                  {{ selectedUser()!.failed_login_attempts }}
                </span>
              </div>
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

      .stats-row {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
      }

      .stat-card {
        background: var(--surface-card);
        border: 1px solid var(--surface-border);
        border-radius: 8px;
        padding: 1rem 1.5rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        min-width: 100px;
      }

      .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--primary-color);
      }

      .stat-label {
        font-size: 0.875rem;
        color: var(--text-color-secondary);
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

      .user-info {
        display: flex;
        align-items: center;
        gap: 0.75rem;
      }

      .user-details {
        display: flex;
        flex-direction: column;
      }

      .user-name {
        font-weight: 500;
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

      .user-profile {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
      }

      .profile-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--surface-border);
      }

      .profile-name h3 {
        margin: 0;
        font-size: 1.25rem;
      }

      .profile-name span {
        color: var(--text-color-secondary);
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

      .detail-value.locked {
        color: var(--red-500);
      }

      .detail-value.warning {
        color: var(--orange-500);
        font-weight: 600;
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UsersListComponent implements OnInit {
  protected readonly store = inject(UsersStore);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly messageService = inject(MessageService);

  // Filters
  searchTerm = '';
  selectedStatus: UserStatus | null = null;
  selectedRole: UserRole | null = null;

  // Dialog state
  dialogVisible = false;
  viewDialogVisible = false;
  editMode = false;
  selectedUser = signal<User | null>(null);

  // Form data
  formData: UserCreate = this.getEmptyFormData();

  // Dropdown options
  statusOptions = [
    { label: 'Active', value: UserStatus.ACTIVE },
    { label: 'Inactive', value: UserStatus.INACTIVE },
    { label: 'Locked', value: UserStatus.LOCKED },
    { label: 'Pending', value: UserStatus.PENDING },
  ];

  roleOptions = [
    { label: 'Administrator', value: UserRole.ADMIN },
    { label: 'Supervisor', value: UserRole.SUPERVISOR },
    { label: 'Claims Processor', value: UserRole.CLAIMS_PROCESSOR },
    { label: 'Auditor', value: UserRole.AUDITOR },
    { label: 'Read Only', value: UserRole.READ_ONLY },
  ];

  ngOnInit(): void {
    this.loadMockData();
  }

  private loadMockData(): void {
    const mockUsers: User[] = [
      {
        id: 'user-1',
        email: 'admin@example.com',
        first_name: 'System',
        last_name: 'Administrator',
        role: UserRole.ADMIN,
        permissions: [],
        status: UserStatus.ACTIVE,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2024-12-15T00:00:00Z',
        last_login: '2024-12-17T14:30:00Z',
        failed_login_attempts: 0,
      },
      {
        id: 'user-2',
        email: 'supervisor@example.com',
        first_name: 'Jane',
        last_name: 'Supervisor',
        role: UserRole.SUPERVISOR,
        permissions: [],
        status: UserStatus.ACTIVE,
        created_at: '2023-06-15T00:00:00Z',
        updated_at: '2024-12-10T00:00:00Z',
        last_login: '2024-12-16T09:15:00Z',
        failed_login_attempts: 0,
      },
      {
        id: 'user-3',
        email: 'processor1@example.com',
        first_name: 'John',
        last_name: 'Processor',
        role: UserRole.CLAIMS_PROCESSOR,
        permissions: [],
        status: UserStatus.ACTIVE,
        created_at: '2023-09-01T00:00:00Z',
        updated_at: '2024-12-05T00:00:00Z',
        last_login: '2024-12-17T08:00:00Z',
        failed_login_attempts: 1,
      },
      {
        id: 'user-4',
        email: 'auditor@example.com',
        first_name: 'Mary',
        last_name: 'Auditor',
        role: UserRole.AUDITOR,
        permissions: [],
        status: UserStatus.ACTIVE,
        created_at: '2024-01-15T00:00:00Z',
        updated_at: '2024-11-20T00:00:00Z',
        last_login: '2024-12-15T11:30:00Z',
        failed_login_attempts: 0,
      },
      {
        id: 'user-5',
        email: 'locked.user@example.com',
        first_name: 'Locked',
        last_name: 'User',
        role: UserRole.CLAIMS_PROCESSOR,
        permissions: [],
        status: UserStatus.LOCKED,
        created_at: '2024-03-01T00:00:00Z',
        updated_at: '2024-12-17T00:00:00Z',
        locked_at: '2024-12-17T10:45:00Z',
        failed_login_attempts: 5,
      },
      {
        id: 'user-6',
        email: 'newuser@example.com',
        first_name: 'New',
        last_name: 'User',
        role: UserRole.READ_ONLY,
        permissions: [],
        status: UserStatus.PENDING,
        created_at: '2024-12-16T00:00:00Z',
        updated_at: '2024-12-16T00:00:00Z',
        failed_login_attempts: 0,
      },
    ];

    this.store.setUsers(mockUsers);
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
      role: this.selectedRole || undefined,
    });
  }

  openCreateDialog(): void {
    this.editMode = false;
    this.formData = this.getEmptyFormData();
    this.dialogVisible = true;
  }

  viewUser(user: User): void {
    this.selectedUser.set(user);
    this.viewDialogVisible = true;
  }

  editUser(user: User): void {
    this.editMode = true;
    this.selectedUser.set(user);
    this.formData = {
      email: user.email,
      password: '',
      first_name: user.first_name,
      last_name: user.last_name,
      role: user.role,
    };
    this.dialogVisible = true;
  }

  lockUser(user: User): void {
    this.confirmationService.confirm({
      message: `Are you sure you want to lock user "${user.first_name} ${user.last_name}"?`,
      header: 'Confirm Lock',
      icon: 'pi pi-lock',
      accept: () => {
        this.store.lockUser(user.id);
        this.messageService.add({
          severity: 'warn',
          summary: 'User Locked',
          detail: `${user.first_name} ${user.last_name} has been locked.`,
        });
      },
    });
  }

  unlockUser(user: User): void {
    this.store.unlockUser(user.id);
    this.messageService.add({
      severity: 'success',
      summary: 'User Unlocked',
      detail: `${user.first_name} ${user.last_name} has been unlocked.`,
    });
  }

  confirmResetPassword(user: User): void {
    this.confirmationService.confirm({
      message: `Send password reset email to ${user.email}?`,
      header: 'Reset Password',
      icon: 'pi pi-key',
      accept: () => {
        this.messageService.add({
          severity: 'success',
          summary: 'Password Reset',
          detail: `Password reset email sent to ${user.email}.`,
        });
      },
    });
  }

  confirmDelete(user: User): void {
    this.confirmationService.confirm({
      message: `Are you sure you want to delete user "${user.first_name} ${user.last_name}"?`,
      header: 'Confirm Delete',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        this.store.removeUser(user.id);
        this.messageService.add({
          severity: 'success',
          summary: 'Deleted',
          detail: 'User has been deleted.',
        });
      },
    });
  }

  closeDialog(): void {
    this.dialogVisible = false;
    this.formData = this.getEmptyFormData();
  }

  saveUser(): void {
    if (!this.isFormValid()) return;

    if (this.editMode && this.selectedUser()) {
      this.store.updateUser(this.selectedUser()!.id, {
        first_name: this.formData.first_name,
        last_name: this.formData.last_name,
        role: this.formData.role,
      });
      this.messageService.add({
        severity: 'success',
        summary: 'Updated',
        detail: 'User has been updated.',
      });
    } else {
      const newUser: User = {
        id: `user-${Date.now()}`,
        email: this.formData.email,
        first_name: this.formData.first_name,
        last_name: this.formData.last_name,
        role: this.formData.role,
        permissions: [],
        status: UserStatus.PENDING,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        failed_login_attempts: 0,
      };
      this.store.addUser(newUser);
      this.messageService.add({
        severity: 'success',
        summary: 'Created',
        detail: 'User has been created. They will receive an email to set their password.',
      });
    }

    this.closeDialog();
  }

  isFormValid(): boolean {
    if (this.editMode) {
      return !!(
        this.formData.first_name &&
        this.formData.last_name &&
        this.formData.role
      );
    }
    return !!(
      this.formData.email &&
      this.formData.password &&
      this.formData.first_name &&
      this.formData.last_name &&
      this.formData.role
    );
  }

  getInitials(user: User): string {
    return `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`.toUpperCase();
  }

  getAvatarColor(role: UserRole): string {
    const colors: Record<UserRole, string> = {
      [UserRole.ADMIN]: '#DC2626',
      [UserRole.SUPERVISOR]: '#7C3AED',
      [UserRole.CLAIMS_PROCESSOR]: '#2563EB',
      [UserRole.AUDITOR]: '#059669',
      [UserRole.READ_ONLY]: '#6B7280',
    };
    return colors[role] || '#6B7280';
  }

  getRoleDisplayLabel(role: UserRole): string {
    return getRoleLabel(role);
  }

  getRoleSeverity(role: UserRole): 'success' | 'info' | 'warning' | 'danger' {
    const severities: Record<UserRole, 'success' | 'info' | 'warning' | 'danger'> = {
      [UserRole.ADMIN]: 'danger',
      [UserRole.SUPERVISOR]: 'warning',
      [UserRole.CLAIMS_PROCESSOR]: 'info',
      [UserRole.AUDITOR]: 'success',
      [UserRole.READ_ONLY]: 'info',
    };
    return severities[role] || 'info';
  }

  getUserStatusSeverity(status: UserStatus): 'success' | 'info' | 'warning' | 'danger' {
    return getStatusSeverity(status);
  }

  private getEmptyFormData(): UserCreate {
    return {
      email: '',
      password: '',
      first_name: '',
      last_name: '',
      role: UserRole.READ_ONLY,
    };
  }
}
