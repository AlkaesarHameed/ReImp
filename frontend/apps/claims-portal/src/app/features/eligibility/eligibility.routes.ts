/**
 * Eligibility Module Routes.
 * Source: Design Document Section 3.4
 */
import { Routes } from '@angular/router';

export const ELIGIBILITY_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./components/eligibility-search.component').then(
        (m) => m.EligibilitySearchComponent
      ),
  },
];
