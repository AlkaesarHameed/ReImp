/**
 * Help Center Component.
 * Main container for the 360 Help System.
 * Provides navigation to all help sections.
 */
import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';

interface HelpSection {
  label: string;
  icon: string;
  route: string;
  description: string;
}

@Component({
  selector: 'app-help-center',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
    CardModule,
    ButtonModule,
  ],
  template: `
    <div class="help-center">
      <!-- Header -->
      <div class="help-header">
        <div class="header-content">
          <h1>
            <i class="pi pi-question-circle"></i>
            Help Center
          </h1>
          <p>Your complete guide to the Claims Processing System</p>
        </div>
        <button pButton label="Back to Dashboard" icon="pi pi-arrow-left"
                class="p-button-outlined" routerLink="/dashboard"></button>
      </div>

      <!-- Navigation Tabs -->
      <div class="help-nav">
        @for (section of sections; track section.route) {
          <a [routerLink]="section.route"
             routerLinkActive="active"
             class="nav-item">
            <i [class]="'pi ' + section.icon"></i>
            <span>{{ section.label }}</span>
          </a>
        }
      </div>

      <!-- Content Area -->
      <div class="help-content">
        <router-outlet />
      </div>

      <!-- Quick Links Footer -->
      <div class="quick-links">
        <h3>Quick Actions</h3>
        <div class="links-grid">
          <a routerLink="/claims/new" class="quick-link">
            <i class="pi pi-plus-circle"></i>
            <span>Submit New Claim</span>
          </a>
          <a routerLink="/eligibility" class="quick-link">
            <i class="pi pi-search"></i>
            <span>Check Eligibility</span>
          </a>
          <a routerLink="/claims" class="quick-link">
            <i class="pi pi-list"></i>
            <span>View All Claims</span>
          </a>
          <a routerLink="/reports" class="quick-link">
            <i class="pi pi-chart-bar"></i>
            <span>Reports</span>
          </a>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .help-center {
      padding: 1.5rem;
      background: #f8f9fa;
      min-height: 100vh;
    }

    .help-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: linear-gradient(135deg, #17a2b8 0%, #138496 100%);
      color: white;
      padding: 1.5rem 2rem;
      border-radius: 10px;
      margin-bottom: 1.5rem;
    }

    .help-header h1 {
      margin: 0;
      font-size: 1.75rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .help-header p {
      margin: 0.5rem 0 0;
      opacity: 0.9;
    }

    .help-nav {
      display: flex;
      gap: 0.5rem;
      background: white;
      padding: 0.5rem;
      border-radius: 10px;
      margin-bottom: 1.5rem;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1.25rem;
      border-radius: 8px;
      color: #495057;
      text-decoration: none;
      font-weight: 500;
      transition: all 0.2s ease;
    }

    .nav-item:hover {
      background: #e9ecef;
      color: #17a2b8;
    }

    .nav-item.active {
      background: #17a2b8;
      color: white;
    }

    .nav-item i {
      font-size: 1.1rem;
    }

    .help-content {
      background: white;
      border-radius: 10px;
      padding: 2rem;
      min-height: 500px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
      margin-bottom: 1.5rem;
    }

    .quick-links {
      background: white;
      border-radius: 10px;
      padding: 1.5rem;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }

    .quick-links h3 {
      margin: 0 0 1rem;
      color: #343a40;
      font-size: 1.1rem;
    }

    .links-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
    }

    .quick-link {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem;
      background: #f8f9fa;
      border-radius: 8px;
      color: #495057;
      text-decoration: none;
      transition: all 0.2s ease;
      border: 1px solid #e9ecef;
    }

    .quick-link:hover {
      background: #17a2b8;
      color: white;
      border-color: #17a2b8;
      transform: translateY(-2px);
    }

    .quick-link i {
      font-size: 1.25rem;
    }

    @media (max-width: 768px) {
      .help-header {
        flex-direction: column;
        gap: 1rem;
        text-align: center;
      }

      .help-nav {
        flex-wrap: wrap;
      }

      .nav-item {
        flex: 1;
        justify-content: center;
        min-width: 120px;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HelpCenterComponent {
  readonly sections: HelpSection[] = [
    {
      label: 'Getting Started',
      icon: 'pi-play',
      route: 'getting-started',
      description: 'Learn the basics of the claims system',
    },
    {
      label: 'Workflow',
      icon: 'pi-sitemap',
      route: 'workflow',
      description: 'Understand the claims processing workflow',
    },
    {
      label: 'Examples',
      icon: 'pi-file-edit',
      route: 'examples',
      description: 'Step-by-step examples',
    },
    {
      label: 'FAQ',
      icon: 'pi-comments',
      route: 'faq',
      description: 'Frequently asked questions',
    },
  ];
}
