/**
 * Modern Layout Component.
 * Source: Design Document - DESIGN_DUAL_INTERFACE_SYSTEM.md Section 3.2
 * Source: Metronic Demo7 Layout - _metronic/layout/layout.component.ts
 * Verified: 2024-12-19
 *
 * Main layout shell for the Modern (Metronic) interface.
 * Provides sidebar navigation, header, and content area.
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, RouterOutlet, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { InterfaceSwitcherService } from '../../core/services/interface-switcher.service';
import { ThemeService } from '../../core/services/theme.service';

interface MenuItem {
  label: string;
  icon: string;
  route: string;
  children?: MenuItem[];
}

@Component({
  selector: 'app-modern-layout',
  standalone: true,
  imports: [CommonModule, RouterModule, RouterOutlet],
  template: `
    <div class="d-flex flex-column flex-root app-root" id="kt_app_root">
      <!--begin::Page-->
      <div class="app-page flex-column flex-column-fluid" id="kt_app_page">
        <!--begin::Header-->
        <div id="kt_app_header" class="app-header" data-kt-sticky="true">
          <div class="app-container container-fluid d-flex align-items-stretch justify-content-between">
            <!--begin::Logo-->
            <div class="d-flex align-items-center flex-grow-1 flex-lg-grow-0 me-lg-15">
              <a routerLink="/modern/dashboard" class="d-lg-block">
                <span class="fs-2 fw-bold text-primary">Claims Portal</span>
              </a>
            </div>
            <!--end::Logo-->

            <!--begin::Header wrapper-->
            <div class="d-flex align-items-stretch justify-content-between flex-lg-grow-1">
              <!--begin::Menu wrapper-->
              <div class="app-header-menu app-header-mobile-drawer align-items-stretch">
                <div class="menu menu-rounded menu-column menu-lg-row my-5 my-lg-0 align-items-stretch fw-semibold px-2 px-lg-0">
                  @for (item of menuItems(); track item.route) {
                    <div class="menu-item me-0 me-lg-2">
                      <a class="menu-link py-3"
                         [routerLink]="item.route"
                         routerLinkActive="active"
                         [routerLinkActiveOptions]="{exact: item.route.endsWith('dashboard')}">
                        <span class="menu-icon">
                          <i [class]="item.icon"></i>
                        </span>
                        <span class="menu-title">{{ item.label }}</span>
                      </a>
                    </div>
                  }
                </div>
              </div>
              <!--end::Menu wrapper-->

              <!--begin::Navbar-->
              <div class="app-navbar flex-shrink-0">
                <!--begin::Theme Toggle-->
                <div class="app-navbar-item ms-1 ms-md-3">
                  <button class="btn btn-icon btn-custom btn-icon-muted btn-active-light btn-active-color-primary w-30px h-30px w-md-40px h-md-40px"
                          (click)="toggleTheme()"
                          [title]="themeService.isDarkMode() ? 'Switch to Light Mode' : 'Switch to Dark Mode'">
                    @if (themeService.isDarkMode()) {
                      <i class="ki-duotone ki-sun fs-2">
                        <span class="path1"></span>
                        <span class="path2"></span>
                      </i>
                    } @else {
                      <i class="ki-duotone ki-moon fs-2">
                        <span class="path1"></span>
                        <span class="path2"></span>
                      </i>
                    }
                  </button>
                </div>
                <!--end::Theme Toggle-->

                <!--begin::Interface Switcher-->
                <div class="app-navbar-item ms-1 ms-md-3">
                  <button class="btn btn-icon btn-custom btn-icon-muted btn-active-light btn-active-color-primary w-30px h-30px w-md-40px h-md-40px"
                          (click)="switchInterface()"
                          [title]="'Switch to ' + getAlternateLabel()">
                    <i class="ki-duotone ki-switch fs-2">
                      <span class="path1"></span>
                      <span class="path2"></span>
                    </i>
                  </button>
                </div>
                <!--end::Interface Switcher-->

                <!--begin::User menu-->
                <div class="app-navbar-item ms-1 ms-md-3">
                  <div class="cursor-pointer symbol symbol-30px symbol-md-40px">
                    <span class="symbol-label bg-light-primary text-primary fw-bold">
                      A
                    </span>
                  </div>
                </div>
                <!--end::User menu-->
              </div>
              <!--end::Navbar-->
            </div>
            <!--end::Header wrapper-->
          </div>
        </div>
        <!--end::Header-->

        <!--begin::Wrapper-->
        <div class="app-wrapper flex-column flex-row-fluid" id="kt_app_wrapper">
          <!--begin::Sidebar-->
          <div id="kt_app_sidebar" class="app-sidebar flex-column" [class.sidebar-minimized]="sidebarMinimized()">
            <!--begin::Sidebar menu-->
            <div class="app-sidebar-menu overflow-hidden flex-column-fluid">
              <div class="app-sidebar-wrapper">
                <div class="menu menu-column menu-rounded menu-sub-indention fw-semibold fs-6">
                  <!--begin::Menu items-->
                  @for (item of sidebarItems(); track item.route) {
                    <div class="menu-item">
                      <a class="menu-link"
                         [routerLink]="item.route"
                         routerLinkActive="active">
                        <span class="menu-icon">
                          <i [class]="item.icon + ' fs-2'"></i>
                        </span>
                        <span class="menu-title">{{ item.label }}</span>
                      </a>
                    </div>
                  }
                  <!--end::Menu items-->
                </div>
              </div>
            </div>
            <!--end::Sidebar menu-->

            <!--begin::Footer-->
            <div class="app-sidebar-footer flex-column-auto pt-2 pb-6 px-6">
              <button class="btn btn-flex flex-center btn-custom btn-primary overflow-hidden text-nowrap px-0 h-40px w-100"
                      (click)="toggleSidebar()">
                <span class="btn-label">
                  {{ sidebarMinimized() ? 'Expand' : 'Minimize' }}
                </span>
              </button>
            </div>
            <!--end::Footer-->
          </div>
          <!--end::Sidebar-->

          <!--begin::Main-->
          <div class="app-main flex-column flex-row-fluid" id="kt_app_main">
            <!--begin::Content wrapper-->
            <div class="d-flex flex-column flex-column-fluid">
              <!--begin::Toolbar-->
              <div id="kt_app_toolbar" class="app-toolbar py-3 py-lg-6">
                <div class="app-container container-fluid d-flex flex-stack">
                  <!--begin::Page title-->
                  <div class="page-title d-flex flex-column justify-content-center flex-wrap me-3">
                    <h1 class="page-heading d-flex text-gray-900 fw-bold fs-3 flex-column justify-content-center my-0">
                      {{ pageTitle() }}
                    </h1>
                    <!--begin::Breadcrumb-->
                    <ul class="breadcrumb breadcrumb-separatorless fw-semibold fs-7 my-0 pt-1">
                      <li class="breadcrumb-item text-muted">
                        <a routerLink="/modern/dashboard" class="text-muted text-hover-primary">Home</a>
                      </li>
                      @if (currentSection()) {
                        <li class="breadcrumb-item">
                          <span class="bullet bg-gray-500 w-5px h-2px"></span>
                        </li>
                        <li class="breadcrumb-item text-muted">{{ currentSection() }}</li>
                      }
                    </ul>
                    <!--end::Breadcrumb-->
                  </div>
                  <!--end::Page title-->
                </div>
              </div>
              <!--end::Toolbar-->

              <!--begin::Content-->
              <div id="kt_app_content" class="app-content flex-column-fluid">
                <div class="app-container container-fluid">
                  <router-outlet></router-outlet>
                </div>
              </div>
              <!--end::Content-->
            </div>
            <!--end::Content wrapper-->

            <!--begin::Footer-->
            <div id="kt_app_footer" class="app-footer">
              <div class="app-container container-fluid d-flex flex-column flex-md-row flex-center flex-md-stack py-3">
                <div class="text-gray-900 order-2 order-md-1">
                  <span class="text-muted fw-semibold me-1">2024&copy;</span>
                  <span class="text-gray-800">Medical Claims Processing System</span>
                </div>
                <ul class="menu menu-gray-600 menu-hover-primary fw-semibold order-1">
                  <li class="menu-item">
                    <a routerLink="/modern/help" class="menu-link px-2">Help</a>
                  </li>
                </ul>
              </div>
            </div>
            <!--end::Footer-->
          </div>
          <!--end::Main-->
        </div>
        <!--end::Wrapper-->
      </div>
      <!--end::Page-->
    </div>
  `,
  styles: [`
    :host {
      display: block;
      height: 100vh;
    }

    .app-root {
      height: 100%;
    }

    .app-header {
      background: #fff;
      box-shadow: 0 1px 10px rgba(0,0,0,0.05);
      height: 70px;
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 100;
    }

    .app-wrapper {
      padding-top: 70px;
    }

    .app-sidebar {
      background: #1e1e2d;
      width: 265px;
      position: fixed;
      top: 70px;
      bottom: 0;
      left: 0;
      z-index: 99;
      transition: width 0.3s ease;
    }

    .app-sidebar.sidebar-minimized {
      width: 75px;
    }

    .app-sidebar .menu-title {
      color: #9899ac;
    }

    .app-sidebar .menu-icon i {
      color: #6d6e82;
    }

    .app-sidebar .menu-link:hover .menu-title,
    .app-sidebar .menu-link.active .menu-title {
      color: #fff;
    }

    .app-sidebar .menu-link:hover .menu-icon i,
    .app-sidebar .menu-link.active .menu-icon i {
      color: #00b2ff;
    }

    .app-sidebar .menu-link {
      padding: 12px 20px;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .app-main {
      margin-left: 265px;
      transition: margin-left 0.3s ease;
    }

    .sidebar-minimized + .app-main {
      margin-left: 75px;
    }

    .app-toolbar {
      background: #fff;
    }

    .app-footer {
      background: #fff;
      border-top: 1px solid #eff2f5;
    }

    .menu-link.active {
      background: rgba(255,255,255,0.05);
    }

    /* Header menu styles */
    .app-header-menu .menu-link {
      padding: 8px 16px;
      border-radius: 6px;
    }

    .app-header-menu .menu-link:hover,
    .app-header-menu .menu-link.active {
      background: #f1f1f4;
    }

    .app-header-menu .menu-link.active .menu-title {
      color: #009ef7;
    }
  `],
})
export class ModernLayoutComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly interfaceSwitcher = inject(InterfaceSwitcherService);
  readonly themeService = inject(ThemeService);

  readonly sidebarMinimized = signal(false);
  readonly pageTitle = signal('Dashboard');
  readonly currentSection = signal('');

  readonly menuItems = signal<MenuItem[]>([
    { label: 'Dashboard', icon: 'ki-duotone ki-element-11', route: '/modern/dashboard' },
    { label: 'Claims', icon: 'ki-duotone ki-document', route: '/modern/claims' },
    { label: 'Reports', icon: 'ki-duotone ki-chart-simple', route: '/modern/reports' },
  ]);

  readonly sidebarItems = signal<MenuItem[]>([
    { label: 'Dashboard', icon: 'ki-duotone ki-element-11', route: '/modern/dashboard' },
    { label: 'Claims', icon: 'ki-duotone ki-document', route: '/modern/claims' },
    { label: 'Members', icon: 'ki-duotone ki-people', route: '/modern/members' },
    { label: 'Providers', icon: 'ki-duotone ki-profile-user', route: '/modern/providers' },
    { label: 'Eligibility', icon: 'ki-duotone ki-verify', route: '/modern/eligibility' },
    { label: 'Reports', icon: 'ki-duotone ki-chart-simple', route: '/modern/reports' },
    { label: 'Settings', icon: 'ki-duotone ki-setting-2', route: '/modern/settings' },
  ]);

  ngOnInit(): void {
    // Set interface type to modern
    this.interfaceSwitcher.currentInterface.set('modern');

    this.updatePageInfo();

    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe(() => {
      this.updatePageInfo();
    });
  }

  private updatePageInfo(): void {
    const url = this.router.url;

    if (url.includes('/dashboard')) {
      this.pageTitle.set('Dashboard');
      this.currentSection.set('');
    } else if (url.includes('/claims')) {
      this.pageTitle.set('Claims');
      this.currentSection.set('Claims Management');
    } else if (url.includes('/reports')) {
      this.pageTitle.set('Reports');
      this.currentSection.set('Analytics');
    } else if (url.includes('/members')) {
      this.pageTitle.set('Members');
      this.currentSection.set('Member Management');
    } else if (url.includes('/providers')) {
      this.pageTitle.set('Providers');
      this.currentSection.set('Provider Network');
    } else if (url.includes('/eligibility')) {
      this.pageTitle.set('Eligibility');
      this.currentSection.set('Eligibility Check');
    } else if (url.includes('/settings')) {
      this.pageTitle.set('Settings');
      this.currentSection.set('Configuration');
    }
  }

  toggleSidebar(): void {
    this.sidebarMinimized.update(v => !v);
  }

  toggleTheme(): void {
    this.themeService.toggle();
  }

  switchInterface(): void {
    this.interfaceSwitcher.switchTo('classic');
  }

  getAlternateLabel(): string {
    return this.interfaceSwitcher.getInterfaceConfig('classic')?.label || 'Classic';
  }
}
