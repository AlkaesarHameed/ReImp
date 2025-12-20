/**
 * Modern Dashboard Component.
 * Source: Design Document - DESIGN_DUAL_INTERFACE_SYSTEM.md Section 4.2
 * Source: Metronic Demo7 - modules/widgets-examples/statistics
 * Verified: 2024-12-19
 *
 * Dashboard with Metronic-styled statistics widgets and charts.
 * Enhanced with welcome banner, animated stats, and improved UX.
 */
import { Component, inject, signal, computed, OnInit, DestroyRef } from '@angular/core';
import { CommonModule, CurrencyPipe, DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ClaimsApiService } from '@claims-processing/api-client';
import { ClaimStatus } from '@claims-processing/models';
import { AuthService } from '../../core/services/auth.service';

interface StatCard {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon: string;
  iconBg: string;
  iconColor: string;
  link?: string;
}

interface RecentClaim {
  id: string;
  trackingNumber: string;
  memberName: string;
  amount: number;
  status: ClaimStatus;
  date: string;
}

interface PendingAction {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  icon: string;
  link: string;
}

@Component({
  selector: 'app-modern-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, CurrencyPipe, DatePipe],
  template: `
    <!--begin::Welcome Banner-->
    <div class="card card-flush mb-5 mb-xl-8 welcome-banner">
      <div class="card-body py-9">
        <div class="d-flex flex-wrap flex-sm-nowrap">
          <div class="me-7 mb-4">
            <div class="symbol symbol-100px symbol-lg-160px symbol-fixed position-relative">
              <div class="symbol-label bg-light-primary">
                <i class="ki-duotone ki-user fs-3x text-primary">
                  <span class="path1"></span>
                  <span class="path2"></span>
                </i>
              </div>
              <div class="position-absolute translate-middle bottom-0 start-100 mb-6 bg-success rounded-circle border border-4 border-body h-20px w-20px"></div>
            </div>
          </div>
          <div class="flex-grow-1">
            <div class="d-flex justify-content-between align-items-start flex-wrap mb-2">
              <div class="d-flex flex-column">
                <div class="d-flex align-items-center mb-2">
                  <span class="text-gray-900 fs-2 fw-bold me-1">{{ greeting() }}, {{ userName() }}!</span>
                  <i class="ki-duotone ki-verify fs-1 text-primary">
                    <span class="path1"></span>
                    <span class="path2"></span>
                  </i>
                </div>
                <div class="d-flex flex-wrap fw-semibold fs-6 mb-4 pe-2">
                  <span class="d-flex align-items-center text-muted me-5 mb-2">
                    <i class="ki-duotone ki-calendar fs-4 me-1">
                      <span class="path1"></span>
                      <span class="path2"></span>
                    </i>
                    {{ currentDate | date:'fullDate' }}
                  </span>
                  <span class="d-flex align-items-center text-muted me-5 mb-2">
                    <i class="ki-duotone ki-time fs-4 me-1">
                      <span class="path1"></span>
                      <span class="path2"></span>
                    </i>
                    {{ currentTime() }}
                  </span>
                </div>
              </div>
              <div class="d-flex my-4">
                <a routerLink="/modern/claims/new" class="btn btn-sm btn-primary me-3">
                  <i class="ki-duotone ki-plus fs-3"></i>
                  New Claim
                </a>
              </div>
            </div>
            <div class="d-flex flex-wrap flex-stack">
              <div class="d-flex flex-column flex-grow-1 pe-8">
                <div class="d-flex flex-wrap">
                  @for (summary of quickSummary(); track summary.label) {
                    <div class="border border-gray-300 border-dashed rounded min-w-125px py-3 px-4 me-6 mb-3">
                      <div class="d-flex align-items-center">
                        <i [class]="summary.icon + ' fs-3 text-' + summary.color + ' me-2'"></i>
                        <div class="fs-2 fw-bold" [class]="'text-' + summary.color">{{ summary.value }}</div>
                      </div>
                      <div class="fw-semibold fs-6 text-gray-500">{{ summary.label }}</div>
                    </div>
                  }
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!--end::Welcome Banner-->

    <!--begin::Pending Actions Alert-->
    @if (pendingActions().length > 0) {
      <div class="card card-flush mb-5 mb-xl-8 bg-light-warning">
        <div class="card-body py-4">
          <div class="d-flex align-items-center">
            <i class="ki-duotone ki-notification-bing fs-2x text-warning me-4">
              <span class="path1"></span>
              <span class="path2"></span>
              <span class="path3"></span>
            </i>
            <div class="flex-grow-1">
              <span class="fw-bold text-gray-800">You have {{ pendingActions().length }} pending action(s) requiring attention</span>
            </div>
            <a routerLink="/modern/claims" [queryParams]="{status: 'needs_review'}" class="btn btn-sm btn-warning">
              Review Now
            </a>
          </div>
        </div>
      </div>
    }
    <!--end::Pending Actions Alert-->

    <div class="row g-5 g-xl-8">
      <!--begin::Stats Cards-->
      @for (stat of statsCards(); track stat.title; let i = $index) {
        <div class="col-xl-3">
          <div class="card card-flush stat-card h-xl-100"
               [class.animate-in]="!loading()"
               [style.animation-delay]="(i * 100) + 'ms'"
               [style.background]="getStatGradient(stat.iconBg)">
            <div class="card-header pt-5 pb-4 border-0">
              <div class="d-flex flex-center rounded-circle h-80px w-80px stat-icon-wrapper"
                   [style.background-color]="'rgba(255,255,255,0.2)'">
                <i [class]="stat.icon + ' fs-2qx text-white'"></i>
              </div>
            </div>
            <div class="card-body d-flex align-items-end pt-0">
              <div class="d-flex align-items-center flex-column w-100">
                <div class="d-flex justify-content-between fw-bold fs-6 w-100 mt-auto mb-2">
                  <span class="text-white opacity-75">{{ stat.title }}</span>
                  @if (stat.change !== undefined) {
                    <span class="badge" [class]="stat.change >= 0 ? 'badge-light-success' : 'badge-light-danger'">
                      <i [class]="stat.change >= 0 ? 'ki-duotone ki-arrow-up' : 'ki-duotone ki-arrow-down'"></i>
                      {{ stat.change >= 0 ? '+' : '' }}{{ stat.change }}%
                    </span>
                  }
                </div>
                <div class="fs-2hx fw-bold text-white stat-value">
                  @if (loading()) {
                    <span class="placeholder-glow"><span class="placeholder col-6"></span></span>
                  } @else {
                    {{ stat.value }}
                  }
                </div>
                @if (stat.link) {
                  <a [routerLink]="stat.link" class="text-white text-opacity-75 fs-7 mt-2 text-hover-white">
                    View Details <i class="ki-duotone ki-arrow-right fs-7"></i>
                  </a>
                }
              </div>
            </div>
          </div>
        </div>
      }
      <!--end::Stats Cards-->
    </div>

    <div class="row g-5 g-xl-8 mt-1">
      <!--begin::Recent Claims-->
      <div class="col-xl-8">
        <div class="card card-flush h-xl-100">
          <div class="card-header border-0 pt-5">
            <h3 class="card-title align-items-start flex-column">
              <span class="card-label fw-bold text-gray-900">Recent Claims</span>
              <span class="text-muted mt-1 fw-semibold fs-7">Latest {{ recentClaims().length }} claim submissions</span>
            </h3>
            <div class="card-toolbar">
              <ul class="nav nav-pills nav-pills-sm nav-light">
                <li class="nav-item">
                  <a class="nav-link btn btn-active-light btn-color-muted py-2 px-4 active"
                     data-bs-toggle="tab" href="#">All</a>
                </li>
                <li class="nav-item">
                  <a class="nav-link btn btn-active-light btn-color-muted py-2 px-4"
                     routerLink="/modern/claims" [queryParams]="{status: 'needs_review'}">Pending</a>
                </li>
              </ul>
            </div>
          </div>
          <div class="card-body py-3">
            @if (loading()) {
              <div class="table-responsive">
                <table class="table table-row-dashed table-row-gray-300 align-middle gs-0 gy-4">
                  <tbody>
                    @for (i of [1,2,3,4,5]; track i) {
                      <tr>
                        <td colspan="5">
                          <div class="placeholder-glow">
                            <span class="placeholder col-12"></span>
                          </div>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            } @else {
              <div class="table-responsive">
                <table class="table table-row-dashed table-row-gray-300 align-middle gs-0 gy-4">
                  <thead>
                    <tr class="fw-bold text-muted">
                      <th class="min-w-150px">Claim ID</th>
                      <th class="min-w-140px">Member</th>
                      <th class="min-w-120px">Amount</th>
                      <th class="min-w-100px">Status</th>
                      <th class="min-w-100px text-end">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (claim of recentClaims(); track claim.id) {
                      <tr class="claim-row">
                        <td>
                          <div class="d-flex align-items-center">
                            <div class="symbol symbol-45px me-3">
                              <span [class]="'symbol-label ' + getStatusBgClass(claim.status)">
                                <i class="ki-duotone ki-document fs-3 text-gray-500">
                                  <span class="path1"></span>
                                  <span class="path2"></span>
                                </i>
                              </span>
                            </div>
                            <div>
                              <a [routerLink]="['/modern/claims', claim.id]"
                                 class="text-gray-900 fw-bold text-hover-primary fs-6">
                                {{ claim.trackingNumber }}
                              </a>
                              <span class="text-muted fw-semibold d-block fs-7">{{ claim.date | date:'short' }}</span>
                            </div>
                          </div>
                        </td>
                        <td>
                          <span class="text-gray-800 fw-semibold d-block fs-6">{{ claim.memberName }}</span>
                        </td>
                        <td>
                          <span class="text-gray-900 fw-bold">{{ claim.amount | currency }}</span>
                        </td>
                        <td>
                          <span [class]="getStatusBadgeClass(claim.status)">
                            {{ getStatusLabel(claim.status) }}
                          </span>
                        </td>
                        <td class="text-end">
                          <div class="d-flex justify-content-end gap-2">
                            <a [routerLink]="['/modern/claims', claim.id]"
                               class="btn btn-icon btn-bg-light btn-active-color-primary btn-sm"
                               title="View">
                              <i class="ki-duotone ki-eye fs-5">
                                <span class="path1"></span>
                                <span class="path2"></span>
                                <span class="path3"></span>
                              </i>
                            </a>
                            @if (claim.status === 'needs_review') {
                              <a [routerLink]="['/modern/claims', claim.id, 'review']"
                                 class="btn btn-icon btn-bg-light btn-active-color-success btn-sm"
                                 title="Review">
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
                        <td colspan="5" class="text-center py-10">
                          <div class="d-flex flex-column align-items-center">
                            <i class="ki-duotone ki-document fs-3x text-gray-300 mb-3">
                              <span class="path1"></span>
                              <span class="path2"></span>
                            </i>
                            <span class="text-muted fs-6">No claims found</span>
                            <a routerLink="/modern/claims/new" class="btn btn-sm btn-primary mt-3">
                              Create Your First Claim
                            </a>
                          </div>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
              @if (recentClaims().length > 0) {
                <div class="d-flex justify-content-end mt-3">
                  <a routerLink="/modern/claims" class="btn btn-sm btn-light-primary">
                    View All Claims
                    <i class="ki-duotone ki-arrow-right fs-5 ms-1"></i>
                  </a>
                </div>
              }
            }
          </div>
        </div>
      </div>
      <!--end::Recent Claims-->

      <!--begin::Status Distribution-->
      <div class="col-xl-4">
        <div class="card card-flush h-xl-100">
          <div class="card-header border-0 pt-5">
            <h3 class="card-title align-items-start flex-column">
              <span class="card-label fw-bold text-gray-900">Claims by Status</span>
              <span class="text-muted mt-1 fw-semibold fs-7">Distribution overview</span>
            </h3>
          </div>
          <div class="card-body d-flex flex-column pt-0">
            <!--begin::Progress bars-->
            @for (status of statusDistribution(); track status.name) {
              <div class="mb-5">
                <div class="d-flex justify-content-between mb-2">
                  <div class="d-flex align-items-center">
                    <span class="bullet bullet-vertical h-15px me-2" [class]="'bg-' + status.color"></span>
                    <span class="fs-6 fw-semibold text-gray-700">{{ status.name }}</span>
                  </div>
                  <span class="fs-6 fw-bold" [class]="'text-' + status.color">{{ status.count }}</span>
                </div>
                <div class="progress h-8px">
                  <div class="progress-bar"
                       [class]="'bg-' + status.color"
                       role="progressbar"
                       [style.width.%]="getStatusPercentage(status.count)"
                       [attr.aria-valuenow]="status.count"
                       aria-valuemin="0"
                       [attr.aria-valuemax]="totalClaims()">
                  </div>
                </div>
              </div>
            }
            <!--end::Progress bars-->

            <div class="separator separator-dashed my-4"></div>

            <!--begin::Status Legend-->
            <div class="d-flex flex-wrap gap-4">
              @for (status of statusDistribution(); track status.name) {
                <a [routerLink]="'/modern/claims'"
                   [queryParams]="{status: status.statusValue}"
                   class="d-flex align-items-center text-hover-primary cursor-pointer">
                  <span [class]="'symbol-label me-2 rounded-circle w-10px h-10px bg-' + status.color"></span>
                  <span class="fs-7 text-gray-600">{{ status.name }}</span>
                </a>
              }
            </div>
            <!--end::Status Legend-->
          </div>
        </div>
      </div>
      <!--end::Status Distribution-->
    </div>

    <div class="row g-5 g-xl-8 mt-1">
      <!--begin::Quick Actions-->
      <div class="col-xl-4">
        <div class="card card-flush h-xl-100">
          <div class="card-header border-0 pt-5">
            <h3 class="card-title align-items-start flex-column">
              <span class="card-label fw-bold text-gray-900">Quick Actions</span>
              <span class="text-muted mt-1 fw-semibold fs-7">Common tasks</span>
            </h3>
          </div>
          <div class="card-body py-3">
            <div class="d-grid gap-3">
              <a routerLink="/modern/claims/new" class="btn btn-primary btn-lg d-flex align-items-center justify-content-start">
                <span class="symbol symbol-40px me-3">
                  <span class="symbol-label bg-white bg-opacity-25">
                    <i class="ki-duotone ki-plus fs-2 text-white"></i>
                  </span>
                </span>
                <span class="d-flex flex-column align-items-start">
                  <span class="fs-5 fw-bold">New Claim</span>
                  <span class="fs-7 opacity-75">Submit a new claim</span>
                </span>
              </a>
              <a routerLink="/modern/eligibility" class="btn btn-light-info btn-lg d-flex align-items-center justify-content-start">
                <span class="symbol symbol-40px me-3">
                  <span class="symbol-label bg-info bg-opacity-25">
                    <i class="ki-duotone ki-verify fs-2 text-info"></i>
                  </span>
                </span>
                <span class="d-flex flex-column align-items-start">
                  <span class="fs-5 fw-bold text-info">Check Eligibility</span>
                  <span class="fs-7 text-gray-500">Verify member coverage</span>
                </span>
              </a>
              <a routerLink="/modern/reports" class="btn btn-light-success btn-lg d-flex align-items-center justify-content-start">
                <span class="symbol symbol-40px me-3">
                  <span class="symbol-label bg-success bg-opacity-25">
                    <i class="ki-duotone ki-chart-simple fs-2 text-success"></i>
                  </span>
                </span>
                <span class="d-flex flex-column align-items-start">
                  <span class="fs-5 fw-bold text-success">View Reports</span>
                  <span class="fs-7 text-gray-500">Analytics & insights</span>
                </span>
              </a>
              <a routerLink="/modern/members" class="btn btn-light-warning btn-lg d-flex align-items-center justify-content-start">
                <span class="symbol symbol-40px me-3">
                  <span class="symbol-label bg-warning bg-opacity-25">
                    <i class="ki-duotone ki-people fs-2 text-warning"></i>
                  </span>
                </span>
                <span class="d-flex flex-column align-items-start">
                  <span class="fs-5 fw-bold text-warning">Manage Members</span>
                  <span class="fs-7 text-gray-500">View member directory</span>
                </span>
              </a>
            </div>
          </div>
        </div>
      </div>
      <!--end::Quick Actions-->

      <!--begin::Activity-->
      <div class="col-xl-8">
        <div class="card card-flush h-xl-100">
          <div class="card-header border-0 pt-5">
            <h3 class="card-title align-items-start flex-column">
              <span class="card-label fw-bold text-gray-900">Recent Activity</span>
              <span class="text-muted mt-1 fw-semibold fs-7">Latest system events</span>
            </h3>
            <div class="card-toolbar">
              <button type="button" class="btn btn-sm btn-light-primary" (click)="refreshActivity()">
                <i class="ki-duotone ki-arrows-circle fs-3">
                  <span class="path1"></span>
                  <span class="path2"></span>
                </i>
                Refresh
              </button>
            </div>
          </div>
          <div class="card-body pt-6">
            <div class="timeline timeline-border-dashed">
              @for (activity of recentActivity(); track activity.id; let isLast = $last) {
                <div class="timeline-item" [class.pb-5]="!isLast">
                  <div class="timeline-line"></div>
                  <div class="timeline-icon">
                    <div [class]="'symbol symbol-circle symbol-40px ' + activity.iconBg">
                      <div class="symbol-label">
                        <i [class]="activity.icon + ' fs-4 ' + activity.iconColor"></i>
                      </div>
                    </div>
                  </div>
                  <div class="timeline-content ms-4">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                      <span class="fs-6 fw-semibold text-gray-800">{{ activity.title }}</span>
                      <span class="badge badge-light-dark fs-8">{{ activity.time }}</span>
                    </div>
                    @if (activity.description) {
                      <span class="fs-7 text-gray-500">{{ activity.description }}</span>
                    }
                  </div>
                </div>
              }
            </div>
          </div>
        </div>
      </div>
      <!--end::Activity-->
    </div>
  `,
  styles: [`
    .welcome-banner {
      background: linear-gradient(135deg, #009ef7 0%, #0061c7 100%);
      color: white;
    }

    .welcome-banner .text-gray-900,
    .welcome-banner .text-gray-800 {
      color: white !important;
    }

    .welcome-banner .text-muted {
      color: rgba(255, 255, 255, 0.75) !important;
    }

    .welcome-banner .border-gray-300 {
      border-color: rgba(255, 255, 255, 0.3) !important;
    }

    .welcome-banner .text-gray-500 {
      color: rgba(255, 255, 255, 0.75) !important;
    }

    .stat-card {
      transition: transform 0.3s ease, box-shadow 0.3s ease;
      opacity: 0;
      transform: translateY(20px);
    }

    .stat-card.animate-in {
      animation: fadeInUp 0.5s ease forwards;
    }

    @keyframes fadeInUp {
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .stat-card:hover {
      transform: translateY(-5px);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
    }

    .stat-icon-wrapper {
      transition: transform 0.3s ease;
    }

    .stat-card:hover .stat-icon-wrapper {
      transform: scale(1.1);
    }

    .stat-value {
      transition: all 0.3s ease;
    }

    .claim-row {
      transition: background-color 0.2s ease;
    }

    .claim-row:hover {
      background-color: rgba(0, 158, 247, 0.05);
    }

    .timeline {
      position: relative;
    }

    .timeline-item {
      position: relative;
      display: flex;
      align-items: flex-start;
    }

    .timeline-line {
      position: absolute;
      left: 20px;
      top: 40px;
      bottom: 0;
      border-left: 1px dashed #e4e6ef;
    }

    .timeline-item:last-child .timeline-line {
      display: none;
    }

    .timeline-icon {
      z-index: 1;
    }

    .timeline-content {
      flex: 1;
    }

    .progress {
      background-color: #f5f8fa;
    }

    .btn-lg {
      padding: 1rem 1.5rem;
    }

    /* Dark mode adjustments */
    :host-context(.dark-mode) .welcome-banner {
      background: linear-gradient(135deg, #1e1e2d 0%, #151521 100%);
    }

    :host-context(.dark-mode) .card {
      background-color: var(--kt-card-bg, #1e1e2d);
    }

    :host-context(.dark-mode) .timeline-line {
      border-color: #2b2b40;
    }

    :host-context(.dark-mode) .progress {
      background-color: #2b2b40;
    }
  `],
})
export class ModernDashboardComponent implements OnInit {
  private readonly claimsApi = inject(ClaimsApiService);
  private readonly authService = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);

  readonly loading = signal(true);
  readonly currentDate = new Date();
  readonly currentTime = signal(this.formatTime(new Date()));

  readonly userName = computed(() => {
    const user = this.authService.user();
    return user?.firstName || user?.username || 'User';
  });

  readonly greeting = computed(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  });

  readonly quickSummary = signal([
    { label: 'Claims Today', value: '0', icon: 'ki-duotone ki-document', color: 'primary' },
    { label: 'Pending Review', value: '0', icon: 'ki-duotone ki-time', color: 'warning' },
    { label: 'Processing Rate', value: '95%', icon: 'ki-duotone ki-chart-simple', color: 'success' },
  ]);

  readonly statsCards = signal<StatCard[]>([
    {
      title: 'Total Claims',
      value: '0',
      change: 12,
      icon: 'ki-duotone ki-document',
      iconBg: '#009ef7',
      iconColor: '#fff',
      link: '/modern/claims',
    },
    {
      title: 'Pending Review',
      value: '0',
      change: -5,
      icon: 'ki-duotone ki-time',
      iconBg: '#ffc700',
      iconColor: '#fff',
      link: '/modern/claims?status=needs_review',
    },
    {
      title: 'Approved',
      value: '0',
      change: 8,
      icon: 'ki-duotone ki-check-circle',
      iconBg: '#50cd89',
      iconColor: '#fff',
      link: '/modern/claims?status=approved',
    },
    {
      title: 'Total Paid',
      value: '$0',
      change: 15,
      icon: 'ki-duotone ki-dollar',
      iconBg: '#7239ea',
      iconColor: '#fff',
      link: '/modern/claims?status=paid',
    },
  ]);

  readonly recentClaims = signal<RecentClaim[]>([]);
  readonly totalClaims = signal(0);

  readonly pendingActions = signal<PendingAction[]>([]);

  readonly statusDistribution = signal([
    { name: 'Submitted', count: 0, color: 'info', statusValue: 'submitted' },
    { name: 'Approved', count: 0, color: 'success', statusValue: 'approved' },
    { name: 'Denied', count: 0, color: 'danger', statusValue: 'denied' },
    { name: 'Paid', count: 0, color: 'primary', statusValue: 'paid' },
    { name: 'Needs Review', count: 0, color: 'warning', statusValue: 'needs_review' },
  ]);

  readonly recentActivity = signal([
    { id: '1', title: 'Claim CLM-00001 approved', description: 'Approved by system', time: '2 hours ago', icon: 'ki-duotone ki-check', iconBg: 'bg-light-success', iconColor: 'text-success' },
    { id: '2', title: 'New claim submitted', description: 'By John Doe', time: '5 hours ago', icon: 'ki-duotone ki-plus', iconBg: 'bg-light-primary', iconColor: 'text-primary' },
    { id: '3', title: 'Payment processed', description: 'CLM-00003 - $1,250.00', time: '1 day ago', icon: 'ki-duotone ki-dollar', iconBg: 'bg-light-info', iconColor: 'text-info' },
    { id: '4', title: 'Claim requires review', description: 'CLM-00005 flagged for manual review', time: '2 days ago', icon: 'ki-duotone ki-notification', iconBg: 'bg-light-warning', iconColor: 'text-warning' },
  ]);

  ngOnInit(): void {
    this.loadDashboardData();
    this.startTimeUpdate();
  }

  private startTimeUpdate(): void {
    setInterval(() => {
      this.currentTime.set(this.formatTime(new Date()));
    }, 60000); // Update every minute
  }

  private formatTime(date: Date): string {
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  }

  private loadDashboardData(): void {
    this.loading.set(true);

    this.claimsApi.getClaims({ size: 10 })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          // Update recent claims
          const claims = response.items.map(claim => ({
            id: claim.id,
            trackingNumber: claim.tracking_number,
            memberName: `Member ${claim.member_id}`,
            amount: claim.total_charged,
            status: claim.status,
            date: claim.created_at,
          }));
          this.recentClaims.set(claims);
          this.totalClaims.set(response.total);

          // Update stats
          const total = response.total;
          const approved = response.items.filter(c => c.status === ClaimStatus.APPROVED).length;
          const pending = response.items.filter(c => c.status === ClaimStatus.SUBMITTED || c.status === ClaimStatus.NEEDS_REVIEW).length;
          const needsReview = response.items.filter(c => c.status === ClaimStatus.NEEDS_REVIEW).length;
          const totalPaid = response.items
            .filter(c => c.status === ClaimStatus.PAID || c.status === ClaimStatus.APPROVED)
            .reduce((sum, c) => sum + (c.total_paid || 0), 0);

          this.statsCards.update(cards => [
            { ...cards[0], value: total.toString() },
            { ...cards[1], value: pending.toString() },
            { ...cards[2], value: approved.toString() },
            { ...cards[3], value: `$${totalPaid.toLocaleString()}` },
          ]);

          // Update quick summary
          this.quickSummary.update(summary => [
            { ...summary[0], value: total.toString() },
            { ...summary[1], value: needsReview.toString() },
            { ...summary[2], value: '95%' },
          ]);

          // Update pending actions
          if (needsReview > 0) {
            this.pendingActions.set([{
              id: 'review',
              title: `${needsReview} claims need review`,
              description: 'These claims require manual review',
              priority: 'high',
              icon: 'ki-duotone ki-notification',
              link: '/modern/claims?status=needs_review',
            }]);
          } else {
            this.pendingActions.set([]);
          }

          // Update status distribution
          const submitted = response.items.filter(c => c.status === ClaimStatus.SUBMITTED).length;
          const denied = response.items.filter(c => c.status === ClaimStatus.DENIED).length;
          const paid = response.items.filter(c => c.status === ClaimStatus.PAID).length;

          this.statusDistribution.update(dist => [
            { ...dist[0], count: submitted },
            { ...dist[1], count: approved },
            { ...dist[2], count: denied },
            { ...dist[3], count: paid },
            { ...dist[4], count: needsReview },
          ]);

          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
        },
      });
  }

  getStatGradient(baseColor: string): string {
    const gradients: Record<string, string> = {
      '#009ef7': 'linear-gradient(135deg, #009ef7 0%, #0061c7 100%)',
      '#ffc700': 'linear-gradient(135deg, #ffc700 0%, #f7931e 100%)',
      '#50cd89': 'linear-gradient(135deg, #50cd89 0%, #3cb371 100%)',
      '#7239ea': 'linear-gradient(135deg, #7239ea 0%, #5a2db0 100%)',
    };
    return gradients[baseColor] || baseColor;
  }

  getStatusPercentage(count: number): number {
    const total = this.totalClaims();
    if (total === 0) return 0;
    return Math.round((count / total) * 100);
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

  getStatusBgClass(status: ClaimStatus): string {
    const classes: Record<string, string> = {
      [ClaimStatus.DRAFT]: 'bg-light-secondary',
      [ClaimStatus.SUBMITTED]: 'bg-light-info',
      [ClaimStatus.APPROVED]: 'bg-light-success',
      [ClaimStatus.DENIED]: 'bg-light-danger',
      [ClaimStatus.PAID]: 'bg-light-primary',
      [ClaimStatus.NEEDS_REVIEW]: 'bg-light-warning',
    };
    return classes[status] || 'bg-light';
  }

  getStatusLabel(status: ClaimStatus): string {
    const labels: Record<string, string> = {
      [ClaimStatus.DRAFT]: 'Draft',
      [ClaimStatus.SUBMITTED]: 'Submitted',
      [ClaimStatus.APPROVED]: 'Approved',
      [ClaimStatus.DENIED]: 'Denied',
      [ClaimStatus.PAID]: 'Paid',
      [ClaimStatus.NEEDS_REVIEW]: 'Needs Review',
    };
    return labels[status] || status;
  }

  refreshActivity(): void {
    this.loadDashboardData();
  }
}
