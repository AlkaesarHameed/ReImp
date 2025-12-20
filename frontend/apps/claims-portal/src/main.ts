/**
 * Application Bootstrap.
 * Source: Design Document Section 3.0
 *
 * Initializes the Angular application with zoneless change detection
 * for optimal performance (targeting 4000 claims/minute).
 */
import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';

bootstrapApplication(AppComponent, appConfig)
  .catch((err) => console.error('Application bootstrap failed:', err));
