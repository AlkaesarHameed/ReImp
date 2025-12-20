/**
 * Modern Claims List Component.
 * Source: Design Document - DESIGN_DUAL_INTERFACE_SYSTEM.md Section 4.3
 * Source: Metronic Demo7 - apps/chat
 * Verified: 2024-12-19
 *
 * Claims list with Metronic-styled table, filters, and pagination.
 * Uses the same data layer as Classic interface.
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
import { Subject, takeUntil } from 'rxjs';

import {
  ClaimStatus,
  ClaimType,
  getStatusLabel,
} from '@claims-processing/models';
import { ClaimsStore } from '@claims-processing/data-access';
import { ClaimsApiService } from '@claims-processing/api-client';
import { WebSocketService } from '../../core/services/websocket.service';

@Component({
  selector: 'app-modern-claims-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, DatePipe, CurrencyPipe],
  template: `
    <div class="card card-flush">
      <!--begin::Card header-->
      <div class="card-header border-0 pt-6">
        <div class="card-title">
          <!--begin::Search-->
          <div class="d-flex align-items-center position-relative my-1">
            <i class="ki-duotone ki-magnifier fs-3 position-absolute ms-5">
              <span class="path1"></span>
              <span class="path2"></span>
            </i>
            <input
              type="text"
              class="form-control form-control-solid w-250px ps-13"
              placeholder="Search claims..."
              [(ngModel)]="searchTerm"
              (input)="onSearch()"
            />
          </div>
          <!--end::Search-->
        </div>
        <div class="card-toolbar">
          <!--begin::Filters-->
          <div class="d-flex gap-3 align-items-center">
            <div class="w-150px">
              <select
                class="form-select form-select-solid"
                [(ngModel)]="selectedStatus"
                (change)="onFilterChange()"
              >
                <option [ngValue]="null">All Status</option>
                @for (option of statusOptions; track option.value) {
                  <option [ngValue]="option.value">{{ option.label }}</option>
                }
              </select>
            </div>
            <div class="w-150px">
              <select
                class="form-select form-select-solid"
                [(ngModel)]="selectedType"
                (change)="onFilterChange()"
              >
                <option [ngValue]="null">All Types</option>
                @for (option of typeOptions; track option.value) {
                  <option [ngValue]="option.value">{{ option.label }}</option>
                }
              </select>
            </div>
            <button
              type="button"
              class="btn btn-light-primary"
              (click)="refresh()"
            >
              <i class="ki-duotone ki-arrows-circle fs-2">
                <span class="path1"></span>
                <span class="path2"></span>
              </i>
              Refresh
            </button>
            <a routerLink="new" class="btn btn-primary">
              <i class="ki-duotone ki-plus fs-2"></i>
              New Claim
            </a>
          </div>
          <!--end::Filters-->
        </div>
      </div>
      <!--end::Card header-->

      <!--begin::Card body-->
      <div class="card-body pt-0">
        @if (error()) {
          <div class="alert alert-danger d-flex align-items-center p-5 mb-5">
            <i class="ki-duotone ki-shield-cross fs-2hx text-danger me-4">
              <span class="path1"></span>
              <span class="path2"></span>
            </i>
            <div class="d-flex flex-column">
              <h4 class="mb-1 text-danger">Error</h4>
              <span>{{ error() }}</span>
            </div>
            <button
              type="button"
              class="btn btn-danger btn-sm ms-auto"
              (click)="refresh()"
            >
              Retry
            </button>
          </div>
        }

        <!--begin::Table-->
        <div class="table-responsive">
          <table class="table align-middle table-row-dashed fs-6 gy-5">
            <thead>
              <tr class="text-start text-muted fw-bold fs-7 text-uppercase gs-0">
                <th class="w-25px pe-2">
                  <div class="form-check form-check-sm form-check-custom form-check-solid">
                    <input
                      class="form-check-input"
                      type="checkbox"
                      [checked]="allSelected()"
                      (change)="toggleSelectAll()"
                    />
                  </div>
                </th>
                <th class="min-w-125px">Tracking #</th>
                <th class="min-w-125px">Status</th>
                <th class="min-w-125px">Type</th>
                <th class="min-w-125px">Member</th>
                <th class="min-w-125px">Provider</th>
                <th class="min-w-125px">Service Date</th>
                <th class="text-end min-w-100px">Charged</th>
                <th class="text-end min-w-100px">Paid</th>
                <th class="text-end min-w-100px">Actions</th>
              </tr>
            </thead>
            <tbody class="text-gray-600 fw-semibold">
              @if (loading()) {
                @for (i of [1, 2, 3, 4, 5]; track i) {
                  <tr>
                    <td colspan="10">
                      <div class="placeholder-glow">
                        <span class="placeholder col-12"></span>
                      </div>
                    </td>
                  </tr>
                }
              } @else {
                @for (claim of claims(); track claim.id) {
                  <tr [class.table-active]="isSelected(claim.id)">
                    <td>
                      <div class="form-check form-check-sm form-check-custom form-check-solid">
                        <input
                          class="form-check-input"
                          type="checkbox"
                          [checked]="isSelected(claim.id)"
                          (change)="toggleClaimSelection(claim.id)"
                        />
                      </div>
                    </td>
                    <td>
                      <a
                        [routerLink]="[claim.id]"
                        class="text-gray-900 fw-bold text-hover-primary fs-6"
                      >
                        {{ claim.tracking_number }}
                      </a>
                    </td>
                    <td>
                      <span [class]="getStatusBadgeClass(claim.status)">
                        {{ getStatusLabel(claim.status) }}
                      </span>
                    </td>
                    <td>
                      <span class="badge badge-light-dark">
                        {{ claim.claim_type | titlecase }}
                      </span>
                    </td>
                    <td>{{ claim.member_id }}</td>
                    <td>{{ claim.provider_id }}</td>
                    <td>{{ claim.service_date_from | date:'shortDate' }}</td>
                    <td class="text-end">{{ claim.total_charged | currency }}</td>
                    <td class="text-end">{{ claim.total_paid | currency }}</td>
                    <td class="text-end">
                      <div class="d-flex justify-content-end gap-1">
                        <a
                          [routerLink]="[claim.id]"
                          class="btn btn-icon btn-bg-light btn-active-color-primary btn-sm"
                          title="View"
                        >
                          <i class="ki-duotone ki-eye fs-5">
                            <span class="path1"></span>
                            <span class="path2"></span>
                            <span class="path3"></span>
                          </i>
                        </a>
                        @if (claim.status === 'needs_review') {
                          <a
                            [routerLink]="[claim.id, 'review']"
                            class="btn btn-icon btn-bg-light btn-active-color-success btn-sm"
                            title="Review"
                          >
                            <i class="ki-duotone ki-check-square fs-5">
                              <span class="path1"></span>
                              <span class="path2"></span>
                            </i>
                          </a>
                        }
                      </div>
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="10" class="text-center py-10">
                      <div class="d-flex flex-column align-items-center">
                        <i class="ki-duotone ki-document fs-3x text-gray-300 mb-3">
                          <span class="path1"></span>
                          <span class="path2"></span>
                        </i>
                        <span class="text-muted fs-6">No claims found</span>
                      </div>
                    </td>
                  </tr>
                }
              }
            </tbody>
          </table>
        </div>
        <!--end::Table-->

        <!--begin::Pagination-->
        @if (totalRecords() > pageSize) {
          <div class="d-flex flex-stack flex-wrap pt-10">
            <div class="fs-6 fw-semibold text-gray-700">
              Showing {{ (currentPage() - 1) * pageSize + 1 }} to
              {{ Math.min(currentPage() * pageSize, totalRecords()) }} of
              {{ totalRecords() }} entries
            </div>
            <ul class="pagination">
              <li class="page-item" [class.disabled]="currentPage() === 1">
                <button
                  class="page-link"
                  (click)="goToPage(currentPage() - 1)"
                  [disabled]="currentPage() === 1"
                >
                  <i class="ki-duotone ki-left fs-5"></i>
                </button>
              </li>
              @for (page of getVisiblePages(); track page) {
                <li class="page-item" [class.active]="page === currentPage()">
                  <button class="page-link" (click)="goToPage(page)">
                    {{ page }}
                  </button>
                </li>
              }
              <li class="page-item" [class.disabled]="currentPage() === totalPages()">
                <button
                  class="page-link"
                  (click)="goToPage(currentPage() + 1)"
                  [disabled]="currentPage() === totalPages()"
                >
                  <i class="ki-duotone ki-right fs-5"></i>
                </button>
              </li>
            </ul>
          </div>
        }
        <!--end::Pagination-->
      </div>
      <!--end::Card body-->
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }

    .table-active {
      background-color: rgba(0, 158, 247, 0.05) !important;
    }

    .pagination .page-item.active .page-link {
      background-color: #009ef7;
      border-color: #009ef7;
    }

    .pagination .page-link {
      cursor: pointer;
    }

    .pagination .page-item.disabled .page-link {
      cursor: not-allowed;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModernClaimsListComponent implements OnInit, OnDestroy {
  protected readonly Math = Math;

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
  readonly currentPage = signal(1);

  // Bulk selection
  private readonly _selectedClaimIds = signal<string[]>([]);
  readonly selectedClaimIds = this._selectedClaimIds.asReadonly();
  readonly allSelected = computed(
    () =>
      this.claims().length > 0 &&
      this._selectedClaimIds().length === this.claims().length
  );

  // Pagination
  readonly pageSize = 20;
  readonly totalPages = computed(() =>
    Math.ceil(this.totalRecords() / this.pageSize)
  );

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
  getStatusLabel = getStatusLabel;

  ngOnInit(): void {
    // Check for status filter in query params
    const status = this.route.snapshot.queryParams['status'];
    if (status) {
      this.selectedStatus = status as ClaimStatus;
      this.claimsStore.setFilters({ status: status as ClaimStatus });
    }

    // Subscribe to WebSocket claim updates
    this.wsService.connect();
    this.wsService
      .getClaimUpdates()
      .pipe(takeUntil(this.destroy$))
      .subscribe((updates) => {
        updates.forEach((event) => {
          this.claimsStore.handleClaimUpdate({
            ...event,
            status: event.status as ClaimStatus,
          });
        });
      });

    // Load initial data
    this.loadClaims();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadClaims(): void {
    this.claimsStore.setLoading(true);

    const params = {
      page: this.currentPage(),
      size: this.pageSize,
      status: this.selectedStatus || undefined,
      claimType: this.selectedType || undefined,
      search: this.searchTerm || undefined,
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
    this.currentPage.set(1);
    this.claimsStore.setFilters({ searchTerm: this.searchTerm });
    this.loadClaims();
  }

  onFilterChange(): void {
    this.currentPage.set(1);
    this.claimsStore.setFilters({
      status: this.selectedStatus || undefined,
      claimType: this.selectedType || undefined,
    });
    this.loadClaims();
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages()) return;
    this.currentPage.set(page);
    this.loadClaims();
  }

  getVisiblePages(): number[] {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: number[] = [];

    let start = Math.max(1, current - 2);
    let end = Math.min(total, current + 2);

    if (end - start < 4) {
      if (start === 1) {
        end = Math.min(total, 5);
      } else {
        start = Math.max(1, total - 4);
      }
    }

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    return pages;
  }

  refresh(): void {
    this.loadClaims();
  }

  // Selection methods
  toggleClaimSelection(claimId: string): void {
    this._selectedClaimIds.update((ids) => {
      if (ids.includes(claimId)) {
        return ids.filter((id) => id !== claimId);
      }
      return [...ids, claimId];
    });
  }

  toggleSelectAll(): void {
    if (this.allSelected()) {
      this._selectedClaimIds.set([]);
    } else {
      this._selectedClaimIds.set(this.claims().map((c) => c.id));
    }
  }

  isSelected(claimId: string): boolean {
    return this._selectedClaimIds().includes(claimId);
  }

  getStatusBadgeClass(status: ClaimStatus): string {
    const classes: Record<string, string> = {
      [ClaimStatus.DRAFT]: 'badge badge-light-secondary',
      [ClaimStatus.SUBMITTED]: 'badge badge-light-info',
      [ClaimStatus.APPROVED]: 'badge badge-light-success',
      [ClaimStatus.DENIED]: 'badge badge-light-danger',
      [ClaimStatus.PAID]: 'badge badge-light-primary',
      [ClaimStatus.NEEDS_REVIEW]: 'badge badge-light-warning',
    };
    return classes[status] || 'badge badge-light';
  }
}
