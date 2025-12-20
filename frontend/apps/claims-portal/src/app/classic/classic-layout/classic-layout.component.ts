/**
 * Classic Layout Component.
 * Source: Design Document - DESIGN_DUAL_INTERFACE_SYSTEM.md
 * Verified: 2024-12-19
 *
 * Main layout shell for the Classic (PrimeNG) interface.
 * Provides menubar navigation and interface switcher.
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, RouterOutlet, Router, NavigationEnd } from '@angular/router';
import { MenubarModule } from 'primeng/menubar';
import { ButtonModule } from 'primeng/button';
import { TooltipModule } from 'primeng/tooltip';
import { MenuItem } from 'primeng/api';
import { filter } from 'rxjs/operators';
import { InterfaceSwitcherService } from '../../core/services/interface-switcher.service';
import { ThemeService } from '../../core/services/theme.service';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-classic-layout',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    RouterOutlet,
    MenubarModule,
    ButtonModule,
    TooltipModule,
  ],
  template: `
    <div class="classic-layout">
      <!--begin::Header-->
      <header class="classic-header">
        <div class="header-content">
          <!--begin::Logo-->
          <div class="logo">
            <a routerLink="/classic/dashboard" class="logo-link">
              <i class="pi pi-heart-fill text-primary"></i>
              <span class="logo-text">Claims Portal</span>
            </a>
          </div>
          <!--end::Logo-->

          <!--begin::Navigation-->
          <nav class="main-nav">
            <p-menubar [model]="menuItems()" styleClass="border-none bg-transparent">
              <ng-template pTemplate="end">
                <div class="header-actions">
                  <!--begin::Theme Toggle-->
                  <button
                    pButton
                    type="button"
                    class="p-button-text p-button-rounded"
                    [icon]="themeService.isDarkMode() ? 'pi pi-sun' : 'pi pi-moon'"
                    [pTooltip]="themeService.isDarkMode() ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
                    tooltipPosition="bottom"
                    (click)="toggleTheme()"
                  ></button>
                  <!--end::Theme Toggle-->

                  <!--begin::Interface Switcher-->
                  <button
                    pButton
                    type="button"
                    class="p-button-text p-button-rounded"
                    icon="pi pi-th-large"
                    [pTooltip]="'Switch to Modern Interface'"
                    tooltipPosition="bottom"
                    (click)="switchInterface()"
                  ></button>
                  <!--end::Interface Switcher-->

                  <!--begin::User Menu-->
                  <button
                    pButton
                    type="button"
                    class="p-button-text p-button-rounded"
                    icon="pi pi-user"
                    [pTooltip]="'User Menu'"
                    tooltipPosition="bottom"
                  ></button>
                  <!--end::User Menu-->

                  <!--begin::Logout-->
                  <button
                    pButton
                    type="button"
                    class="p-button-text p-button-rounded p-button-danger"
                    icon="pi pi-sign-out"
                    [pTooltip]="'Logout'"
                    tooltipPosition="bottom"
                    (click)="logout()"
                  ></button>
                  <!--end::Logout-->
                </div>
              </ng-template>
            </p-menubar>
          </nav>
          <!--end::Navigation-->
        </div>
      </header>
      <!--end::Header-->

      <!--begin::Main Content-->
      <main class="classic-main">
        <div class="content-wrapper">
          <!--begin::Breadcrumb-->
          @if (currentSection()) {
            <div class="breadcrumb-bar">
              <nav class="breadcrumb">
                <a routerLink="/classic/dashboard" class="breadcrumb-link">Home</a>
                <span class="breadcrumb-separator">/</span>
                <span class="breadcrumb-current">{{ currentSection() }}</span>
              </nav>
            </div>
          }
          <!--end::Breadcrumb-->

          <!--begin::Page Content-->
          <div class="page-content">
            <router-outlet></router-outlet>
          </div>
          <!--end::Page Content-->
        </div>
      </main>
      <!--end::Main Content-->

      <!--begin::Footer-->
      <footer class="classic-footer">
        <div class="footer-content">
          <span class="copyright">2024 &copy; Medical Claims Processing System</span>
          <div class="footer-links">
            <a routerLink="/classic/help" class="footer-link">Help</a>
            <span class="link-separator">|</span>
            <a href="#" class="footer-link">Privacy Policy</a>
          </div>
        </div>
      </footer>
      <!--end::Footer-->
    </div>
  `,
  styles: [`
    .classic-layout {
      display: flex;
      flex-direction: column;
      min-height: 100vh;
      background-color: var(--surface-ground, #f8f9fa);
    }

    .classic-header {
      background: var(--surface-card, #ffffff);
      border-bottom: 1px solid var(--surface-border, #dee2e6);
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .header-content {
      display: flex;
      align-items: center;
      gap: 2rem;
      padding: 0 1.5rem;
      max-width: 1400px;
      margin: 0 auto;
    }

    .logo {
      flex-shrink: 0;
    }

    .logo-link {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      text-decoration: none;
      font-size: 1.25rem;
      font-weight: 600;
      color: var(--text-color, #343a40);
    }

    .logo-link i {
      font-size: 1.5rem;
    }

    .main-nav {
      flex: 1;
    }

    :host ::ng-deep .p-menubar {
      background: transparent !important;
      border: none !important;
      padding: 0.5rem 0 !important;
    }

    :host ::ng-deep .p-menubar .p-menuitem-link {
      padding: 0.75rem 1rem !important;
      border-radius: 6px !important;
    }

    :host ::ng-deep .p-menubar .p-menuitem-link:hover {
      background: var(--surface-hover, #f1f3f5) !important;
    }

    :host ::ng-deep .p-menubar .p-menuitem.p-menuitem-active > .p-menuitem-link {
      background: var(--primary-color, #3b82f6) !important;
      color: white !important;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }

    .classic-main {
      flex: 1;
      padding: 1.5rem;
    }

    .content-wrapper {
      max-width: 1400px;
      margin: 0 auto;
    }

    .breadcrumb-bar {
      margin-bottom: 1rem;
    }

    .breadcrumb {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
    }

    .breadcrumb-link {
      color: var(--primary-color, #3b82f6);
      text-decoration: none;
    }

    .breadcrumb-link:hover {
      text-decoration: underline;
    }

    .breadcrumb-separator {
      color: var(--text-color-secondary, #6c757d);
    }

    .breadcrumb-current {
      color: var(--text-color-secondary, #6c757d);
    }

    .page-content {
      background: var(--surface-card, #ffffff);
      border-radius: 8px;
      padding: 1.5rem;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }

    .classic-footer {
      background: var(--surface-card, #ffffff);
      border-top: 1px solid var(--surface-border, #dee2e6);
      padding: 1rem 1.5rem;
      margin-top: auto;
    }

    .footer-content {
      display: flex;
      justify-content: space-between;
      align-items: center;
      max-width: 1400px;
      margin: 0 auto;
      font-size: 0.875rem;
      color: var(--text-color-secondary, #6c757d);
    }

    .footer-links {
      display: flex;
      gap: 0.5rem;
    }

    .footer-link {
      color: var(--text-color-secondary, #6c757d);
      text-decoration: none;
    }

    .footer-link:hover {
      color: var(--primary-color, #3b82f6);
    }

    .link-separator {
      color: var(--surface-border, #dee2e6);
    }

    @media (max-width: 768px) {
      .header-content {
        flex-direction: column;
        padding: 0.75rem;
        gap: 0.75rem;
      }

      .footer-content {
        flex-direction: column;
        gap: 0.5rem;
        text-align: center;
      }
    }
  `],
})
export class ClassicLayoutComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly interfaceSwitcher = inject(InterfaceSwitcherService);
  readonly themeService = inject(ThemeService);
  private readonly authService = inject(AuthService);

  readonly currentSection = signal('');

  readonly menuItems = signal<MenuItem[]>([
    {
      label: 'Dashboard',
      icon: 'pi pi-home',
      routerLink: '/classic/dashboard',
    },
    {
      label: 'Claims',
      icon: 'pi pi-file',
      items: [
        { label: 'All Claims', icon: 'pi pi-list', routerLink: '/classic/claims' },
        { label: 'New Claim', icon: 'pi pi-plus', routerLink: '/classic/claims/new' },
      ],
    },
    {
      label: 'Members',
      icon: 'pi pi-users',
      routerLink: '/classic/admin/members',
    },
    {
      label: 'Providers',
      icon: 'pi pi-building',
      routerLink: '/classic/admin/providers',
    },
    {
      label: 'Eligibility',
      icon: 'pi pi-check-circle',
      routerLink: '/classic/eligibility',
    },
    {
      label: 'Reports',
      icon: 'pi pi-chart-bar',
      routerLink: '/classic/reports',
    },
    {
      label: 'Admin',
      icon: 'pi pi-cog',
      items: [
        { label: 'Users', icon: 'pi pi-users', routerLink: '/classic/admin/users' },
        { label: 'Policies', icon: 'pi pi-shield', routerLink: '/classic/admin/policies' },
        { label: 'LLM Settings', icon: 'pi pi-sliders-h', routerLink: '/classic/admin/llm-settings' },
      ],
    },
  ]);

  ngOnInit(): void {
    // Set interface type to classic
    this.interfaceSwitcher.currentInterface.set('classic');

    this.updateCurrentSection();

    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe(() => {
      this.updateCurrentSection();
    });
  }

  private updateCurrentSection(): void {
    const url = this.router.url;

    if (url.includes('/dashboard')) {
      this.currentSection.set('');
    } else if (url.includes('/claims')) {
      this.currentSection.set('Claims');
    } else if (url.includes('/eligibility')) {
      this.currentSection.set('Eligibility');
    } else if (url.includes('/admin/members')) {
      this.currentSection.set('Members');
    } else if (url.includes('/admin/providers')) {
      this.currentSection.set('Providers');
    } else if (url.includes('/admin/users')) {
      this.currentSection.set('Admin / Users');
    } else if (url.includes('/admin/policies')) {
      this.currentSection.set('Admin / Policies');
    } else if (url.includes('/admin/llm-settings')) {
      this.currentSection.set('Admin / LLM Settings');
    } else if (url.includes('/reports')) {
      this.currentSection.set('Reports');
    } else if (url.includes('/help')) {
      this.currentSection.set('Help');
    }
  }

  toggleTheme(): void {
    this.themeService.toggle();
  }

  switchInterface(): void {
    this.interfaceSwitcher.switchTo('modern');
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/auth/login']);
  }
}
