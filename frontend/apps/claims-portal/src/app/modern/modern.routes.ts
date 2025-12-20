/**
 * Modern Interface Routes.
 * Source: Design Document - DESIGN_DUAL_INTERFACE_SYSTEM.md Section 3.4
 * Verified: 2024-12-19
 *
 * Routes for the Modern (Metronic) interface.
 * Uses ModernLayoutComponent as the parent layout shell.
 */
import { Routes } from '@angular/router';
import { permissionGuard } from '../core/guards/permission.guard';

export const MODERN_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./modern-layout/modern-layout.component').then(
        (m) => m.ModernLayoutComponent
      ),
    children: [
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full',
      },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./dashboard/modern-dashboard.component').then(
            (m) => m.ModernDashboardComponent
          ),
      },
      {
        path: 'claims',
        children: [
          {
            path: '',
            loadComponent: () =>
              import('./claims/modern-claims-list.component').then(
                (m) => m.ModernClaimsListComponent
              ),
          },
          {
            path: 'new',
            loadComponent: () =>
              import('../features/claims/components/claim-submit/claim-submit.component').then(
                (m) => m.ClaimSubmitComponent
              ),
            canActivate: [permissionGuard('claims:create')],
          },
          {
            path: ':id',
            loadComponent: () =>
              import('../features/claims/components/claim-detail.component').then(
                (m) => m.ClaimDetailComponent
              ),
          },
          {
            path: ':id/review',
            loadComponent: () =>
              import('../features/claims/components/claim-review/claim-review.component').then(
                (m) => m.ClaimReviewComponent
              ),
            canActivate: [permissionGuard('claims:approve')],
          },
        ],
      },
      {
        path: 'members',
        loadComponent: () =>
          import('../features/admin/members/members-list.component').then(
            (m) => m.MembersListComponent
          ),
      },
      {
        path: 'providers',
        loadComponent: () =>
          import('../features/admin/providers/providers-list.component').then(
            (m) => m.ProvidersListComponent
          ),
      },
      {
        path: 'eligibility',
        loadComponent: () =>
          import('../features/eligibility/components/eligibility-search.component').then(
            (m) => m.EligibilitySearchComponent
          ),
      },
      {
        path: 'reports',
        loadComponent: () =>
          import('../features/reports/components/reports-dashboard.component').then(
            (m) => m.ReportsDashboardComponent
          ),
      },
      {
        path: 'help',
        loadComponent: () =>
          import('../features/help/components/help-center.component').then(
            (m) => m.HelpCenterComponent
          ),
      },
    ],
  },
];
