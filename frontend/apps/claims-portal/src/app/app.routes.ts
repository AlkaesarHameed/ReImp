/**
 * Application Routes.
 * Source: Design Document Section 3.4
 * Source: DESIGN_DUAL_INTERFACE_SYSTEM.md
 *
 * Implements lazy loading for optimal bundle size.
 * Supports dual interfaces: Classic (PrimeNG) and Modern (Metronic).
 * All routes are protected by auth guards except login.
 */
import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'auth/login',
    pathMatch: 'full',
  },
  {
    path: 'auth',
    loadChildren: () => import('./features/auth/auth.routes').then(m => m.AUTH_ROUTES),
  },

  // ========================================
  // Modern Interface (Metronic) Routes
  // ========================================
  {
    path: 'modern',
    loadChildren: () => import('./modern/modern.routes').then(m => m.MODERN_ROUTES),
    canActivate: [authGuard],
    data: { preload: true, preloadDelay: 500 },
  },

  // ========================================
  // Classic Interface (PrimeNG) Routes
  // Uses ClassicLayoutComponent as wrapper with navigation and interface switcher
  // ========================================
  {
    path: 'classic',
    loadComponent: () =>
      import('./classic/classic-layout/classic-layout.component').then(
        (m) => m.ClassicLayoutComponent
      ),
    canActivate: [authGuard],
    children: [
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full',
      },
      {
        path: 'dashboard',
        loadChildren: () => import('./features/dashboard/dashboard.routes').then(m => m.DASHBOARD_ROUTES),
      },
      {
        path: 'claims',
        loadChildren: () => import('./features/claims/claims.routes').then(m => m.CLAIMS_ROUTES),
        data: { preload: true, preloadDelay: 1500 },
      },
      {
        path: 'eligibility',
        loadChildren: () => import('./features/eligibility/eligibility.routes').then(m => m.ELIGIBILITY_ROUTES),
        data: { preload: true, preloadDelay: 2000 },
      },
      {
        path: 'admin',
        loadChildren: () => import('./features/admin/admin.routes').then(m => m.ADMIN_ROUTES),
      },
      {
        path: 'reports',
        loadChildren: () => import('./features/reports/reports.routes').then(m => m.REPORTS_ROUTES),
      },
      {
        path: 'help',
        loadChildren: () => import('./features/help/help.routes').then(m => m.HELP_ROUTES),
      },
    ],
  },

  // Legacy routes - redirect to classic interface for backward compatibility
  {
    path: 'dashboard',
    redirectTo: 'classic/dashboard',
    pathMatch: 'full',
  },
  {
    path: 'claims',
    redirectTo: 'classic/claims',
    pathMatch: 'prefix',
  },
  {
    path: 'eligibility',
    redirectTo: 'classic/eligibility',
    pathMatch: 'prefix',
  },
  {
    path: 'admin',
    redirectTo: 'classic/admin',
    pathMatch: 'prefix',
  },
  {
    path: 'reports',
    redirectTo: 'classic/reports',
    pathMatch: 'prefix',
  },
  {
    path: 'help',
    redirectTo: 'classic/help',
    pathMatch: 'prefix',
  },

  // Default fallback to modern interface
  {
    path: '**',
    redirectTo: 'modern/dashboard',
  },
];
