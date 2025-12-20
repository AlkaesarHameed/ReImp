/**
 * Claims List Component.
 * Source: Design Document Section 3.2, 7.0
 * Verified: 2025-12-18
 *
 * Virtualized claims table for high-volume display (4000+ claims).
 * Uses OnPush change detection and NgRx Signal Store for optimal performance.
 */
import {
  Component,
  ChangeDetectionStrategy,
  inject,
  signal,
  computed,
  OnInit,
  OnDestroy,
} from '@angular/core';
import { CommonModule, DatePipe, CurrencyPipe } from '@angular/common';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { DropdownModule } from 'primeng/dropdown';
import { TagModule } from 'primeng/tag';
import { CardModule } from 'primeng/card';
import { TooltipModule } from 'primeng/tooltip';
import { CheckboxModule } from 'primeng/checkbox';
import { MessageModule } from 'primeng/message';
import { Subject, takeUntil } from 'rxjs';

import {
  Claim,
  ClaimStatus,
  ClaimType,
  getStatusColor,
  getStatusLabel,
} from '@claims-processing/models';
import { ClaimsStore } from '@claims-processing/data-access';
import { ClaimsApiService } from '@claims-processing/api-client';
import { WebSocketService } from '../../../core/services/websocket.service';

@Component({
  selector: 'app-claims-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    TableModule,
    ButtonModule,
    InputTextModule,
    DropdownModule,
    TagModule,
    CardModule,
    TooltipModule,
    DatePipe,
    CurrencyPipe,
    CheckboxModule,
    MessageModule,
  ],
  template: `
    <div class="claims-container">
      <!-- Error Message -->
      @if (error()) {
        <p-message severity="error" [text]="error()!" styleClass="mb-3 w-full"></p-message>
        @if (showRetry()) {
          <button pButton label="Retry" icon="pi pi-refresh" class="p-button-outlined mb-3" (click)="refresh()"></button>
        }
      }

      <!-- Header -->
      <div class="claims-header">
        <div class="header-content">
          <h1><i class="pi pi-file"></i> Claims</h1>
          <p>{{ totalRecords() }} total claims</p>
        </div>
        <div class="header-actions">
          @if (selectedClaimIds().length > 0) {
            <span class="selection-info">{{ selectedClaimIds().length }} selected</span>
            <button pButton label="Clear" icon="pi pi-times" class="p-button-text" (click)="clearSelection()"></button>
          }
          <button pButton label="New Claim" icon="pi pi-plus" routerLink="new"></button>
        </div>
      </div>

      <!-- Filters -->
      <p-card styleClass="filters-card">
        <div class="filters-row">
          <span class="p-input-icon-left flex-1">
            <i class="pi pi-search"></i>
            <input
              pInputText
              type="text"
              [(ngModel)]="searchTerm"
              placeholder="Search claims..."
              class="w-full"
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
            [options]="typeOptions"
            [(ngModel)]="selectedType"
            placeholder="All Types"
            [showClear]="true"
            (onChange)="onFilterChange()"
          ></p-dropdown>

          <button
            pButton
            icon="pi pi-refresh"
            class="p-button-outlined"
            pTooltip="Refresh"
            (click)="refresh()"
          ></button>
        </div>
      </p-card>

      <!-- Claims Table -->
      <p-card>
        <p-table
          [value]="claims()"
          [lazy]="true"
          [paginator]="true"
          [rows]="20"
          [totalRecords]="totalRecords()"
          [loading]="loading()"
          [rowsPerPageOptions]="[10, 20, 50, 100]"
          [scrollable]="true"
          scrollHeight="600px"
          [virtualScroll]="true"
          [virtualScrollItemSize]="48"
          styleClass="p-datatable-sm p-datatable-striped"
          (onLazyLoad)="loadClaims($event)"
        >
          <ng-template pTemplate="header">
            <tr>
              <th class="checkbox-col">
                <p-checkbox
                  [binary]="true"
                  [ngModel]="selectedClaimIds().length === claims().length && claims().length > 0"
                  (onChange)="selectedClaimIds().length === claims().length ? clearSelection() : selectAllClaims()"
                ></p-checkbox>
              </th>
              <th pSortableColumn="tracking_number">
                Tracking # <p-sortIcon field="tracking_number"></p-sortIcon>
              </th>
              <th pSortableColumn="status">
                Status <p-sortIcon field="status"></p-sortIcon>
              </th>
              <th pSortableColumn="claim_type">
                Type <p-sortIcon field="claim_type"></p-sortIcon>
              </th>
              <th>Member</th>
              <th>Provider</th>
              <th pSortableColumn="service_date_from">
                Service Date <p-sortIcon field="service_date_from"></p-sortIcon>
              </th>
              <th pSortableColumn="total_charged" class="text-right">
                Charged <p-sortIcon field="total_charged"></p-sortIcon>
              </th>
              <th pSortableColumn="total_paid" class="text-right">
                Paid <p-sortIcon field="total_paid"></p-sortIcon>
              </th>
              <th>Actions</th>
            </tr>
          </ng-template>

          <ng-template pTemplate="body" let-claim>
            <tr [class.selected-row]="isSelected(claim.id)">
              <td class="checkbox-col">
                <p-checkbox
                  [binary]="true"
                  [ngModel]="isSelected(claim.id)"
                  (onChange)="toggleClaimSelection(claim.id)"
                ></p-checkbox>
              </td>
              <td>
                <a [routerLink]="[claim.id]" class="tracking-link">
                  {{ claim.tracking_number }}
                </a>
              </td>
              <td>
                <p-tag
                  [value]="getStatusLabel(claim.status)"
                  [style]="{ 'background-color': getStatusColor(claim.status) }"
                ></p-tag>
              </td>
              <td>{{ claim.claim_type | titlecase }}</td>
              <td>{{ claim.member_id }}</td>
              <td>{{ claim.provider_id }}</td>
              <td>{{ claim.service_date_from | date:'shortDate' }}</td>
              <td class="text-right">{{ claim.total_charged | currency }}</td>
              <td class="text-right">{{ claim.total_paid | currency }}</td>
              <td>
                <div class="action-buttons">
                  <button
                    pButton
                    icon="pi pi-eye"
                    class="p-button-text p-button-sm"
                    pTooltip="View"
                    [routerLink]="[claim.id]"
                  ></button>
                  @if (claim.status === 'needs_review') {
                    <button
                      pButton
                      icon="pi pi-check-square"
                      class="p-button-text p-button-sm p-button-success"
                      pTooltip="Review"
                      [routerLink]="[claim.id, 'review']"
                    ></button>
                  }
                </div>
              </td>
            </tr>
          </ng-template>

          <ng-template pTemplate="emptymessage">
            <tr>
              <td colspan="10" class="text-center p-4">
                <i class="pi pi-inbox text-4xl text-gray-300 mb-2"></i>
                <p class="text-gray-500">No claims found</p>
              </td>
            </tr>
          </ng-template>
        </p-table>
      </p-card>
    </div>
  `,
  styles: [`
    .claims-container {
      padding: 1.5rem;
      background: #F8F9FA;
      min-height: 100vh;
    }

    .claims-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .selection-info {
      color: #0066CC;
      font-weight: 500;
    }

    .claims-header h1 {
      margin: 0;
      font-size: 1.5rem;
      color: #343A40;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .claims-header p {
      margin: 0.25rem 0 0;
      color: #6C757D;
      font-size: 0.9rem;
    }

    :host ::ng-deep .filters-card .p-card-body {
      padding: 1rem;
    }

    .filters-row {
      display: flex;
      gap: 1rem;
      align-items: center;
    }

    .tracking-link {
      color: #0066CC;
      text-decoration: none;
      font-weight: 500;
    }

    .tracking-link:hover {
      text-decoration: underline;
    }

    .action-buttons {
      display: flex;
      gap: 0.25rem;
    }

    .text-right {
      text-align: right;
    }

    .checkbox-col {
      width: 50px;
      text-align: center;
    }

    .selected-row {
      background-color: rgba(0, 102, 204, 0.1) !important;
    }

    @media (max-width: 768px) {
      .filters-row {
        flex-direction: column;
      }

      .filters-row > * {
        width: 100%;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClaimsListComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly claimsStore = inject(ClaimsStore);
  private readonly claimsApi = inject(ClaimsApiService);
  private readonly wsService = inject(WebSocketService);
  private readonly destroy$ = new Subject<void>();

  // State from store
  readonly claims = computed(() => this.claimsStore.paginatedClaims());
  readonly totalRecords = computed(() => this.claimsStore.totalCount());
  readonly loading = computed(() => this.claimsStore.loading());
  readonly error = computed(() => this.claimsStore.error());
  readonly showRetry = computed(() => !!this.claimsStore.error());

  // Bulk selection
  private readonly _selectedClaimIds = signal<string[]>([]);
  readonly selectedClaimIds = this._selectedClaimIds.asReadonly();

  // Pagination
  readonly pageSize = 20;
  readonly virtualScroll = true;

  // Filters
  searchTerm = '';
  selectedStatus: ClaimStatus | null = null;
  selectedType: ClaimType | null = null;

  readonly statusOptions = Object.values(ClaimStatus).map((status) => ({
    label: getStatusLabel(status),
    value: status,
  }));

  readonly typeOptions = Object.values(ClaimType).map((type) => ({
    label: type.charAt(0).toUpperCase() + type.slice(1),
    value: type,
  }));

  // Helper methods bound for template
  getStatusColor = getStatusColor;
  getStatusLabel = getStatusLabel;

  ngOnInit(): void {
    // Check for status filter in query params
    const status = this.route.snapshot.queryParams['status'];
    if (status) {
      this.selectedStatus = status as ClaimStatus;
      this.claimsStore.setFilters({ status: status as ClaimStatus });
    }

    // Subscribe to WebSocket claim updates with built-in throttling
    this.wsService.connect();
    this.wsService
      .getClaimUpdates()
      .pipe(takeUntil(this.destroy$))
      .subscribe((updates) => {
        // Process batched updates
        updates.forEach((event) => {
          this.claimsStore.handleClaimUpdate({
            ...event,
            status: event.status as ClaimStatus,
          });
        });
      });

    // Load initial data
    this.loadClaims({ first: 0, rows: this.pageSize });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadClaims(event: any): void {
    this.claimsStore.setLoading(true);

    const page = Math.floor(event.first / event.rows) + 1;
    const params = {
      page,
      size: event.rows,
      status: this.selectedStatus || undefined,
      claimType: this.selectedType || undefined,
      search: this.searchTerm || undefined,
      sortBy: event.sortField,
      sortOrder: event.sortOrder === 1 ? 'asc' as const : 'desc' as const,
    };

    this.claimsApi
      .getClaims(params)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.claimsStore.setClaims(response.items);
          this.claimsStore.setCurrentPage(response.page);
          this.claimsStore.setPageSize(response.size);
          this.claimsStore.setLoading(false);
          this.claimsStore.setError(null);
        },
        error: (err) => {
          this.claimsStore.setError(err.message || 'Failed to load claims');
          this.claimsStore.setLoading(false);
        },
      });
  }

  onSearch(): void {
    this.claimsStore.setFilters({ searchTerm: this.searchTerm });
    this.loadClaims({ first: 0, rows: this.pageSize });
  }

  onFilterChange(): void {
    this.claimsStore.setFilters({
      status: this.selectedStatus || undefined,
      claimType: this.selectedType || undefined,
    });
    this.loadClaims({ first: 0, rows: this.pageSize });
  }

  onPageChange(event: { page: number; rows: number }): void {
    this.claimsStore.setCurrentPage(event.page);
    this.claimsStore.setPageSize(event.rows);
    this.loadClaims({ first: (event.page - 1) * event.rows, rows: event.rows });
  }

  clearFilters(): void {
    this.searchTerm = '';
    this.selectedStatus = null;
    this.selectedType = null;
    this.claimsStore.clearFilters();
    this.loadClaims({ first: 0, rows: this.pageSize });
  }

  refresh(): void {
    this.loadClaims({ first: 0, rows: this.pageSize });
  }

  // Selection methods
  onClaimSelect(claim: Claim): void {
    this.claimsStore.selectClaim(claim.id);
  }

  toggleClaimSelection(claimId: string): void {
    this._selectedClaimIds.update((ids) => {
      if (ids.includes(claimId)) {
        return ids.filter((id) => id !== claimId);
      }
      return [...ids, claimId];
    });
  }

  selectAllClaims(): void {
    const allIds = this.claims().map((c) => c.id);
    this._selectedClaimIds.set(allIds);
  }

  clearSelection(): void {
    this._selectedClaimIds.set([]);
  }

  isSelected(claimId: string): boolean {
    return this._selectedClaimIds().includes(claimId);
  }
}
