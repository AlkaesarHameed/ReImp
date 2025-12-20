/**
 * Help Module Routes.
 * Comprehensive help system with guides, examples, and workflows.
 */
import { Routes } from '@angular/router';

export const HELP_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./components/help-center.component').then(
        (m) => m.HelpCenterComponent
      ),
    children: [
      {
        path: '',
        redirectTo: 'getting-started',
        pathMatch: 'full',
      },
      {
        path: 'getting-started',
        loadComponent: () =>
          import('./components/getting-started.component').then(
            (m) => m.GettingStartedComponent
          ),
      },
      {
        path: 'workflow',
        loadComponent: () =>
          import('./components/workflow-guide.component').then(
            (m) => m.WorkflowGuideComponent
          ),
      },
      {
        path: 'examples',
        loadComponent: () =>
          import('./components/examples.component').then(
            (m) => m.ExamplesComponent
          ),
      },
      {
        path: 'faq',
        loadComponent: () =>
          import('./components/faq.component').then(
            (m) => m.FaqComponent
          ),
      },
    ],
  },
];
