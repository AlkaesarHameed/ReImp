/**
 * Admin Module Routes.
 * Source: Design Document Section 3.4
 */
import { Routes } from '@angular/router';
import { adminGuard } from '../../core/guards/role.guard';

export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    redirectTo: 'policies',
    pathMatch: 'full',
  },
  {
    path: 'policies',
    loadComponent: () =>
      import('./policies/policies-list.component').then(
        (m) => m.PoliciesListComponent
      ),
  },
  {
    path: 'providers',
    loadComponent: () =>
      import('./providers/providers-list.component').then(
        (m) => m.ProvidersListComponent
      ),
  },
  {
    path: 'members',
    loadComponent: () =>
      import('./members/members-list.component').then(
        (m) => m.MembersListComponent
      ),
  },
  {
    path: 'users',
    loadComponent: () =>
      import('./users/users-list.component').then(
        (m) => m.UsersListComponent
      ),
    canActivate: [adminGuard],
  },
  {
    path: 'llm-settings',
    loadComponent: () =>
      import('./llm-settings/llm-settings.component').then(
        (m) => m.LlmSettingsComponent
      ),
    canActivate: [adminGuard],
  },
];
