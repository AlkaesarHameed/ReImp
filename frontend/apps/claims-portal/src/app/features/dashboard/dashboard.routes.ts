/**
 * Dashboard Module Routes.
 * Source: Design Document Section 3.4
 */
import { Routes } from '@angular/router';

export const DASHBOARD_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./components/dashboard-overview.component').then(
        (m) => m.DashboardOverviewComponent
      ),
  },
];
