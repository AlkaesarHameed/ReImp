/**
 * Claims Module Routes.
 * Source: Design Document Section 3.4
 */
import { Routes } from '@angular/router';
import { permissionGuard } from '../../core/guards/permission.guard';

export const CLAIMS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./components/claims-list.component').then(
        (m) => m.ClaimsListComponent
      ),
  },
  {
    path: 'new',
    loadComponent: () =>
      import('./components/claim-submit/claim-submit.component').then(
        (m) => m.ClaimSubmitComponent
      ),
    canActivate: [permissionGuard('claims:create')],
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./components/claim-detail.component').then(
        (m) => m.ClaimDetailComponent
      ),
  },
  {
    path: ':id/review',
    loadComponent: () =>
      import('./components/claim-review/claim-review.component').then(
        (m) => m.ClaimReviewComponent
      ),
    canActivate: [permissionGuard('claims:approve')],
  },
  {
    path: 'review',
    loadComponent: () =>
      import('./components/claim-review/claim-review.component').then(
        (m) => m.ClaimReviewComponent
      ),
    canActivate: [permissionGuard('claims:approve')],
  },
];
