/**
 * Reports Module Routes.
 * Source: Phase 5 Implementation Document
 *
 * Provides comprehensive reporting and analytics capabilities.
 */
import { Routes } from '@angular/router';

export const REPORTS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./components/reports-dashboard.component').then(
        (m) => m.ReportsDashboardComponent
      ),
  },
  {
    path: 'claims',
    loadComponent: () =>
      import('./components/claims-report.component').then(
        (m) => m.ClaimsReportComponent
      ),
  },
  {
    path: 'financial',
    loadComponent: () =>
      import('./components/financial-report.component').then(
        (m) => m.FinancialReportComponent
      ),
  },
];
