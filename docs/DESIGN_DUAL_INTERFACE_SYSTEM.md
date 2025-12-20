# Design Document: Dual Interface System (Metronic + PrimeNG)

**Feature:** Metronic-themed Dashboard, Reports, and Details Interface
**Version:** 1.0.0
**Date:** December 19, 2024
**Status:** Draft - Awaiting Approval

---

## 1. Executive Summary

### 1.1 Overview

This design document outlines the architecture for implementing a **dual-interface system** that allows users to switch between:

1. **Classic Interface** - Existing PrimeNG-based UI (current implementation)
2. **Modern Interface** - Metronic Bootstrap-based UI (new implementation)

Both interfaces will share the same data layer (API services, models) but provide different visual experiences without impacting each other.

### 1.2 Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Interface Switching | Route-based with shared shell | Clean separation, easy navigation |
| Layout System | Metronic Demo7 layout | Pre-built, responsive, modern |
| Charts Library | ApexCharts (Metronic) + Chart.js (existing) | Best-in-class for each interface |
| State Management | Shared NgRx Signals | Single source of truth |
| Component Isolation | Feature modules per interface | No style bleeding |

### 1.3 Scope

**In Scope:**
- Metronic-styled Dashboard with widgets and statistics
- Metronic-styled Reports with ApexCharts
- Metronic-styled Claims List and Detail views
- Interface switcher in header/settings
- Shared authentication and data layer

**Out of Scope:**
- Backend API changes
- Mobile app development
- User preference persistence (Phase 2)

---

## 2. Requirements Specification

### 2.1 Business Objectives

| ID | Objective | Success Criteria |
|----|-----------|------------------|
| BO-1 | Provide modern admin interface | Users can access Metronic-styled pages |
| BO-2 | Maintain existing functionality | PrimeNG interface remains fully functional |
| BO-3 | Easy interface switching | < 2 clicks to switch interfaces |
| BO-4 | Consistent data experience | Same data shown in both interfaces |

### 2.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Dashboard with statistics widgets | High |
| FR-2 | Claims list with Metronic DataTable styling | High |
| FR-3 | Claim detail page with Metronic cards | High |
| FR-4 | Reports with ApexCharts visualizations | High |
| FR-5 | Interface switcher component | Medium |
| FR-6 | Sidebar navigation (Metronic aside) | High |
| FR-7 | Header with user menu (Metronic topbar) | High |
| FR-8 | Breadcrumb navigation | Medium |

### 2.3 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Page load time | < 2 seconds |
| NFR-2 | Bundle size increase | < 30% |
| NFR-3 | Browser support | Chrome, Firefox, Edge, Safari |
| NFR-4 | Accessibility | WCAG 2.1 AA |

### 2.4 Constraints

1. **Technical:** Angular 19 with standalone components
2. **UI Libraries:** Must coexist - Bootstrap/ng-bootstrap + PrimeNG
3. **Styling:** Metronic CSS must not affect PrimeNG components
4. **Timeline:** Phase 1 (MVP) - 2 weeks

### 2.5 Assumptions

1. Metronic template license covers this usage
2. Users prefer modern dashboard aesthetics
3. ApexCharts is compatible with Angular 19
4. No IE11 support required

---

## 3. Architecture Design

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        App Shell                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Router Outlet                            ││
│  │  ┌──────────────────────┐  ┌──────────────────────────────┐││
│  │  │   Classic Routes     │  │    Modern Routes              │││
│  │  │   /classic/*         │  │    /modern/*                  │││
│  │  │                      │  │                               │││
│  │  │  ┌────────────────┐  │  │  ┌────────────────────────┐  │││
│  │  │  │ PrimeNG Layout │  │  │  │ Metronic Layout        │  │││
│  │  │  │  - p-menubar   │  │  │  │  - app-aside           │  │││
│  │  │  │  - p-sidebar   │  │  │  │  - app-header          │  │││
│  │  │  │  - p-toast     │  │  │  │  - app-toolbar         │  │││
│  │  │  └────────────────┘  │  │  └────────────────────────┘  │││
│  │  │         │            │  │           │                   │││
│  │  │         v            │  │           v                   │││
│  │  │  ┌────────────────┐  │  │  ┌────────────────────────┐  │││
│  │  │  │ Feature Module │  │  │  │ Metronic Feature       │  │││
│  │  │  │  - Dashboard   │  │  │  │  - Dashboard           │  │││
│  │  │  │  - Claims      │  │  │  │  - Claims              │  │││
│  │  │  │  - Reports     │  │  │  │  - Reports             │  │││
│  │  │  └────────────────┘  │  │  └────────────────────────┘  │││
│  │  └──────────────────────┘  └──────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                              v                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Shared Layer                             ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ ││
│  │  │ API Client  │  │   Models    │  │  State Management   │ ││
│  │  │  Services   │  │  Interfaces │  │   NgRx Signals      │ ││
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Directory Structure

```
apps/claims-portal/src/app/
├── _metronic/                    # Metronic core (existing)
│   ├── layout/
│   ├── partials/
│   ├── kt/
│   └── shared/
│
├── core/                         # Shared core services
│   ├── guards/
│   ├── interceptors/
│   └── services/
│       └── interface-switcher.service.ts  # NEW
│
├── features/                     # Classic PrimeNG features (existing)
│   ├── dashboard/
│   ├── claims/
│   ├── reports/
│   └── ...
│
├── modern/                       # NEW: Metronic-based features
│   ├── modern-layout/
│   │   ├── modern-layout.component.ts
│   │   ├── modern-layout.component.html
│   │   └── modern-layout.routes.ts
│   │
│   ├── dashboard/
│   │   ├── modern-dashboard.component.ts
│   │   ├── widgets/
│   │   │   ├── stats-widget.component.ts
│   │   │   ├── charts-widget.component.ts
│   │   │   └── activity-widget.component.ts
│   │   └── modern-dashboard.routes.ts
│   │
│   ├── claims/
│   │   ├── claims-list/
│   │   │   └── modern-claims-list.component.ts
│   │   ├── claim-detail/
│   │   │   └── modern-claim-detail.component.ts
│   │   └── modern-claims.routes.ts
│   │
│   └── reports/
│       ├── modern-reports-dashboard.component.ts
│       ├── charts/
│       │   ├── claims-chart.component.ts
│       │   ├── revenue-chart.component.ts
│       │   └── status-chart.component.ts
│       └── modern-reports.routes.ts
│
├── shared/
│   └── components/
│       └── interface-switcher/   # NEW
│           └── interface-switcher.component.ts
│
└── app.routes.ts                 # Updated with modern routes
```

### 3.3 Routing Strategy

```typescript
// app.routes.ts
export const routes: Routes = [
  // Default redirect based on user preference
  { path: '', redirectTo: '/modern/dashboard', pathMatch: 'full' },

  // Authentication (shared)
  { path: 'auth', loadChildren: () => import('./features/auth/auth.routes') },

  // Classic Interface (PrimeNG)
  {
    path: 'classic',
    loadChildren: () => import('./features/shell/classic-shell.routes'),
    canActivate: [authGuard],
  },

  // Modern Interface (Metronic)
  {
    path: 'modern',
    loadChildren: () => import('./modern/modern-layout/modern-layout.routes'),
    canActivate: [authGuard],
  },

  // Error pages
  { path: 'error', loadChildren: () => import('./features/errors/errors.routes') },
  { path: '**', redirectTo: '/error/404' },
];
```

### 3.4 Component Interactions

```
┌────────────────┐     ┌─────────────────────┐
│  Interface     │────>│  InterfaceSwitcher  │
│  Switcher UI   │     │  Service            │
└────────────────┘     └─────────────────────┘
                               │
                               │ currentInterface$
                               v
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        v                      v                      v
┌───────────────┐    ┌─────────────────┐    ┌───────────────┐
│ Modern Layout │    │  Header Menu    │    │ Classic Layout│
│ Component     │    │  (shows current)│    │ Component     │
└───────────────┘    └─────────────────┘    └───────────────┘
        │                                          │
        │                                          │
        v                                          v
┌───────────────┐                         ┌───────────────┐
│ Modern        │                         │ Classic       │
│ Dashboard     │◄──── Shared ────────────│ Dashboard     │
│ (ApexCharts)  │      API Layer          │ (Chart.js)    │
└───────────────┘      & Models           └───────────────┘
```

---

## 4. API Contracts

### 4.1 Interface Switcher Service

```typescript
// core/services/interface-switcher.service.ts

export type InterfaceType = 'classic' | 'modern';

export interface InterfaceConfig {
  type: InterfaceType;
  basePath: string;
  label: string;
  icon: string;
}

@Injectable({ providedIn: 'root' })
export class InterfaceSwitcherService {
  private readonly router = inject(Router);

  readonly interfaces: InterfaceConfig[] = [
    { type: 'classic', basePath: '/classic', label: 'Classic', icon: 'pi pi-th-large' },
    { type: 'modern', basePath: '/modern', label: 'Modern', icon: 'ki-duotone ki-element-11' },
  ];

  readonly currentInterface = signal<InterfaceType>('modern');

  switchTo(type: InterfaceType): void {
    this.currentInterface.set(type);
    const config = this.interfaces.find(i => i.type === type);
    if (config) {
      this.router.navigate([config.basePath, 'dashboard']);
    }
  }

  getCurrentBasePath(): string {
    const type = this.currentInterface();
    return this.interfaces.find(i => i.type === type)?.basePath || '/modern';
  }
}
```

### 4.2 Modern Dashboard Widgets

```typescript
// modern/dashboard/widgets/stats-widget.component.ts

export interface StatWidgetConfig {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon: string;
  iconColor: 'primary' | 'success' | 'warning' | 'danger' | 'info';
  trend?: 'up' | 'down' | 'neutral';
}

@Component({
  selector: 'app-stats-widget',
  standalone: true,
  template: `
    <div class="card card-flush h-100">
      <div class="card-header pt-5">
        <div class="card-title d-flex flex-column">
          <span class="fs-2hx fw-bold text-gray-900 me-2">{{ config().value }}</span>
          <span class="text-gray-500 pt-1 fw-semibold fs-6">{{ config().title }}</span>
        </div>
      </div>
      <div class="card-body d-flex align-items-end pt-0">
        <div class="d-flex align-items-center flex-column w-100">
          @if (config().change !== undefined) {
            <div class="d-flex justify-content-between w-100 mt-auto mb-2">
              <span class="fw-bold fs-6 text-gray-500">Change</span>
              <span [class]="getTrendClass()">
                <i [class]="getTrendIcon()"></i>
                {{ config().change }}%
              </span>
            </div>
          }
        </div>
      </div>
    </div>
  `,
})
export class StatsWidgetComponent {
  config = input.required<StatWidgetConfig>();

  getTrendClass(): string {
    const trend = this.config().trend || (this.config().change! >= 0 ? 'up' : 'down');
    return trend === 'up' ? 'text-success' : 'text-danger';
  }

  getTrendIcon(): string {
    const trend = this.config().trend || (this.config().change! >= 0 ? 'up' : 'down');
    return trend === 'up' ? 'ki-duotone ki-arrow-up' : 'ki-duotone ki-arrow-down';
  }
}
```

### 4.3 Modern Claims List

```typescript
// modern/claims/claims-list/modern-claims-list.component.ts

@Component({
  selector: 'app-modern-claims-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  template: `
    <div class="card">
      <!--begin::Header-->
      <div class="card-header border-0 pt-6">
        <div class="card-title">
          <div class="d-flex align-items-center position-relative my-1">
            <i class="ki-duotone ki-magnifier fs-3 position-absolute ms-5">
              <span class="path1"></span>
              <span class="path2"></span>
            </i>
            <input type="text"
                   class="form-control form-control-solid w-250px ps-13"
                   placeholder="Search claims..."
                   [(ngModel)]="searchTerm"
                   (input)="onSearch()">
          </div>
        </div>
        <div class="card-toolbar">
          <button class="btn btn-primary" routerLink="../new">
            <i class="ki-duotone ki-plus fs-2"></i>
            New Claim
          </button>
        </div>
      </div>
      <!--end::Header-->

      <!--begin::Body-->
      <div class="card-body py-4">
        <table class="table align-middle table-row-dashed fs-6 gy-5">
          <thead>
            <tr class="text-start text-muted fw-bold fs-7 text-uppercase gs-0">
              <th>Claim ID</th>
              <th>Member</th>
              <th>Provider</th>
              <th>Service Date</th>
              <th>Amount</th>
              <th>Status</th>
              <th class="text-end">Actions</th>
            </tr>
          </thead>
          <tbody class="text-gray-600 fw-semibold">
            @for (claim of claims(); track claim.id) {
              <tr>
                <td>
                  <a [routerLink]="['..', claim.id]" class="text-gray-800 text-hover-primary">
                    {{ claim.tracking_number }}
                  </a>
                </td>
                <td>{{ claim.member_id }}</td>
                <td>{{ claim.provider_id }}</td>
                <td>{{ claim.service_date_from | date:'mediumDate' }}</td>
                <td>{{ claim.total_charged | currency }}</td>
                <td>
                  <span [class]="getStatusBadgeClass(claim.status)">
                    {{ claim.status }}
                  </span>
                </td>
                <td class="text-end">
                  <a [routerLink]="['..', claim.id]" class="btn btn-sm btn-light btn-active-light-primary">
                    View
                  </a>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      <!--end::Body-->
    </div>
  `,
})
export class ModernClaimsListComponent implements OnInit {
  private readonly claimsApi = inject(ClaimsApiService);

  claims = signal<Claim[]>([]);
  loading = signal(true);
  searchTerm = '';

  ngOnInit() {
    this.loadClaims();
  }

  loadClaims() {
    this.loading.set(true);
    this.claimsApi.getClaims({ search: this.searchTerm })
      .pipe(takeUntilDestroyed(inject(DestroyRef)))
      .subscribe({
        next: (response) => {
          this.claims.set(response.items);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
  }

  onSearch() {
    this.loadClaims();
  }

  getStatusBadgeClass(status: ClaimStatus): string {
    const classes: Record<ClaimStatus, string> = {
      [ClaimStatus.DRAFT]: 'badge badge-light-warning',
      [ClaimStatus.SUBMITTED]: 'badge badge-light-info',
      [ClaimStatus.APPROVED]: 'badge badge-light-success',
      [ClaimStatus.DENIED]: 'badge badge-light-danger',
      [ClaimStatus.PAID]: 'badge badge-light-success',
      // ... other statuses
    };
    return classes[status] || 'badge badge-light';
  }
}
```

---

## 5. Technology Stack

### 5.1 Core Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| Angular | 19.2.0 | Frontend framework |
| TypeScript | 5.8.0 | Type safety |
| RxJS | 7.8.1 | Reactive programming |
| NgRx Signals | 19.0.0 | State management |

### 5.2 UI Libraries (Dual)

| Library | Interface | Purpose |
|---------|-----------|---------|
| Metronic | Modern | Admin template, layout |
| Bootstrap | Modern | CSS framework |
| ng-bootstrap | Modern | Angular Bootstrap components |
| PrimeNG | Classic | UI component library |
| PrimeFlex | Classic | CSS utilities |

### 5.3 Charts

| Library | Interface | Purpose |
|---------|-----------|---------|
| ApexCharts | Modern | Interactive charts |
| ng-apexcharts | Modern | Angular wrapper |
| Chart.js | Classic | Existing charts |

### 5.4 Dependencies to Add

```json
{
  "dependencies": {
    "apexcharts": "^3.37.1",
    "ng-apexcharts": "^1.7.4"
  }
}
```

**Justification:** ApexCharts is Metronic's native charting library with excellent documentation and Angular integration.

---

## 6. Security Design

### 6.1 Authentication

Both interfaces share the same authentication layer:
- HttpOnly cookie-based sessions
- Auth guards on all protected routes
- Token refresh handling

### 6.2 Authorization

Role-based access control applies to both interfaces:
- Same permissions model
- Feature flags shared between interfaces

### 6.3 Data Security

- No sensitive data in localStorage for interface preference
- CSRF protection on all mutations
- Same API security as classic interface

---

## 7. Performance Plan

### 7.1 Bundle Size Strategy

| Approach | Impact |
|----------|--------|
| Lazy loading | Modern routes loaded on demand |
| Tree shaking | Unused Metronic components excluded |
| Code splitting | Separate chunks for each interface |

### 7.2 Load Time Optimization

- Preload modern routes when hovering interface switcher
- Cache Metronic CSS in service worker
- Optimize chart data fetching

### 7.3 Estimated Bundle Impact

| Component | Size (gzipped) |
|-----------|----------------|
| Metronic CSS | ~180KB |
| Metronic Layout | ~50KB |
| ApexCharts | ~120KB |
| Modern Features | ~80KB |
| **Total Addition** | ~430KB |

---

## 8. Risk Register

| ID | Risk | Probability | Impact | Mitigation |
|----|------|-------------|--------|------------|
| R1 | CSS conflicts between Bootstrap and PrimeNG | Medium | High | Scope Bootstrap styles to .modern-layout container |
| R2 | ApexCharts Angular 19 compatibility | Low | High | Test in isolated environment first |
| R3 | User confusion with dual interfaces | Medium | Medium | Clear labeling, consistent navigation |
| R4 | Increased maintenance burden | Medium | Medium | Shared data layer reduces duplication |
| R5 | Performance degradation | Low | Medium | Lazy loading, monitoring |

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Week 1)

| Task | Effort | Deliverable |
|------|--------|-------------|
| Set up modern routes structure | 2 hours | Route configuration |
| Create Modern Layout component | 4 hours | Layout shell with aside/header |
| Implement Interface Switcher | 2 hours | Switcher service + component |
| CSS scoping for Bootstrap | 3 hours | Isolated Metronic styles |

### Phase 2: Dashboard (Week 1)

| Task | Effort | Deliverable |
|------|--------|-------------|
| Stats widgets | 3 hours | 4 statistics cards |
| Charts widget (ApexCharts) | 4 hours | Claims trend chart |
| Activity feed widget | 2 hours | Recent activity list |
| Dashboard layout | 2 hours | Grid arrangement |

### Phase 3: Claims Module (Week 2)

| Task | Effort | Deliverable |
|------|--------|-------------|
| Claims list (Metronic table) | 4 hours | Searchable, sortable table |
| Claim detail page | 6 hours | Full claim view with tabs |
| Claim form (if needed) | 4 hours | Metronic form styling |

### Phase 4: Reports (Week 2)

| Task | Effort | Deliverable |
|------|--------|-------------|
| Reports dashboard | 4 hours | Chart grid layout |
| Claims by status chart | 2 hours | Pie/donut chart |
| Revenue trend chart | 2 hours | Area chart |
| Export functionality | 2 hours | PDF/CSV export |

### Phase 5: Polish (Week 2)

| Task | Effort | Deliverable |
|------|--------|-------------|
| Breadcrumb navigation | 2 hours | Dynamic breadcrumbs |
| Loading states | 2 hours | Skeleton loaders |
| Error handling | 2 hours | Error pages |
| Testing | 4 hours | E2E tests |

---

## 10. Open Questions

| ID | Question | Owner | Status |
|----|----------|-------|--------|
| Q1 | Should interface preference be persisted per user? | Product | Open |
| Q2 | Default interface for new users? | Product | Modern |
| Q3 | Should all features be in both interfaces? | Product | Open |
| Q4 | Migration path for existing users? | Product | Open |

---

## Validation Checklist

- [x] Business requirements clearly mapped to technical solution
- [x] All integration points identified and specified
- [x] Security requirements addressed
- [x] Performance requirements defined
- [x] Risks identified with mitigation strategies
- [x] Implementation broken into manageable phases
- [ ] No major assumptions left unvalidated
- [x] Technology choices justified with evidence

---

## Appendix A: Metronic Component Mapping

| Claims Portal Feature | Metronic Component | Location |
|-----------------------|-------------------|----------|
| Sidebar Navigation | `app-aside` | `_metronic/layout/components/aside` |
| Top Header | `app-header` | `_metronic/layout/components/header` |
| User Menu | `app-topbar` | `_metronic/layout/components/topbar` |
| Page Title | `app-page-title` | `_metronic/layout/components/header/page-title` |
| Statistics Cards | Widget Examples | `modules/widgets-examples/statistics` |
| Data Tables | CRUD Module | `modules/crud` |
| Charts | Widget Examples | `modules/widgets-examples/charts` |
| Forms | Wizards | `modules/wizards` |

---

## Appendix B: File Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Modern Component | `modern-*.component.ts` | `modern-dashboard.component.ts` |
| Modern Route | `modern-*.routes.ts` | `modern-claims.routes.ts` |
| Widget | `*-widget.component.ts` | `stats-widget.component.ts` |
| Chart | `*-chart.component.ts` | `claims-chart.component.ts` |

---

**End of Design Document**

*Awaiting approval before implementation begins.*
