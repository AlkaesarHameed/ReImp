/**
 * Getting Started Component.
 * Introduction and onboarding guide for new users.
 */
import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { TimelineModule } from 'primeng/timeline';
import { AccordionModule } from 'primeng/accordion';

interface OnboardingStep {
  title: string;
  description: string;
  icon: string;
  action?: { label: string; route: string };
}

@Component({
  selector: 'app-getting-started',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    CardModule,
    ButtonModule,
    TimelineModule,
    AccordionModule,
  ],
  template: `
    <div class="getting-started">
      <!-- Welcome Section -->
      <section class="welcome-section">
        <h2><i class="pi pi-star"></i> Welcome to Claims Processing System</h2>
        <p class="lead">
          This comprehensive guide will help you understand and navigate the claims
          processing system efficiently. Whether you're a claims processor, supervisor,
          or administrator, you'll find everything you need to get started.
        </p>
      </section>

      <!-- Quick Overview Cards -->
      <section class="overview-section">
        <h3>System Overview</h3>
        <div class="overview-grid">
          <div class="overview-card">
            <div class="card-icon dashboard">
              <i class="pi pi-chart-bar"></i>
            </div>
            <h4>Dashboard</h4>
            <p>Real-time analytics, KPIs, and system status at a glance</p>
          </div>
          <div class="overview-card">
            <div class="card-icon claims">
              <i class="pi pi-file"></i>
            </div>
            <h4>Claims Management</h4>
            <p>Submit, track, review, and manage healthcare claims</p>
          </div>
          <div class="overview-card">
            <div class="card-icon eligibility">
              <i class="pi pi-verified"></i>
            </div>
            <h4>Eligibility Verification</h4>
            <p>Real-time member eligibility and benefits verification</p>
          </div>
          <div class="overview-card">
            <div class="card-icon reports">
              <i class="pi pi-chart-line"></i>
            </div>
            <h4>Reports & Analytics</h4>
            <p>Comprehensive reporting and data insights</p>
          </div>
        </div>
      </section>

      <!-- User Roles Section -->
      <section class="roles-section">
        <h3>User Roles & Permissions</h3>
        <div class="roles-grid">
          <p-card styleClass="role-card">
            <ng-template pTemplate="header">
              <div class="role-header processor">
                <i class="pi pi-user"></i>
                <span>Claims Processor</span>
              </div>
            </ng-template>
            <ul class="permissions-list">
              <li><i class="pi pi-check"></i> Submit new claims</li>
              <li><i class="pi pi-check"></i> View claim status</li>
              <li><i class="pi pi-check"></i> Update claim information</li>
              <li><i class="pi pi-check"></i> Check member eligibility</li>
            </ul>
            <p class="login-hint">Login: <code>processor / demo123</code></p>
          </p-card>

          <p-card styleClass="role-card">
            <ng-template pTemplate="header">
              <div class="role-header supervisor">
                <i class="pi pi-users"></i>
                <span>Supervisor</span>
              </div>
            </ng-template>
            <ul class="permissions-list">
              <li><i class="pi pi-check"></i> All Processor permissions</li>
              <li><i class="pi pi-check"></i> Approve/Deny claims</li>
              <li><i class="pi pi-check"></i> View reports</li>
              <li><i class="pi pi-check"></i> Escalation handling</li>
            </ul>
            <p class="login-hint">Login: <code>supervisor / demo123</code></p>
          </p-card>

          <p-card styleClass="role-card">
            <ng-template pTemplate="header">
              <div class="role-header admin">
                <i class="pi pi-shield"></i>
                <span>Administrator</span>
              </div>
            </ng-template>
            <ul class="permissions-list">
              <li><i class="pi pi-check"></i> All Supervisor permissions</li>
              <li><i class="pi pi-check"></i> User management</li>
              <li><i class="pi pi-check"></i> System configuration</li>
              <li><i class="pi pi-check"></i> Audit logs access</li>
            </ul>
            <p class="login-hint">Login: <code>admin / demo123</code></p>
          </p-card>
        </div>
      </section>

      <!-- Getting Started Steps -->
      <section class="steps-section">
        <h3>Your First Steps</h3>
        <div class="steps-timeline">
          @for (step of onboardingSteps; track step.title; let i = $index) {
            <div class="timeline-item">
              <div class="step-number">{{ i + 1 }}</div>
              <div class="step-content">
                <div class="step-header">
                  <i [class]="'pi ' + step.icon"></i>
                  <h4>{{ step.title }}</h4>
                </div>
                <p>{{ step.description }}</p>
                @if (step.action) {
                  <a [routerLink]="step.action.route" class="step-action">
                    {{ step.action.label }}
                    <i class="pi pi-arrow-right"></i>
                  </a>
                }
              </div>
            </div>
          }
        </div>
      </section>

      <!-- Key Features -->
      <section class="features-section">
        <h3>Key Features</h3>
        <p-accordion>
          <p-accordionTab header="Real-Time Dashboard">
            <div class="feature-content">
              <p>The dashboard provides a comprehensive view of your claims processing operations:</p>
              <ul>
                <li><strong>KPI Cards:</strong> Claims today, approval rates, pending reviews</li>
                <li><strong>Status Distribution:</strong> Visual breakdown of claim statuses</li>
                <li><strong>Trend Charts:</strong> 7-day claims processing trends</li>
                <li><strong>Live Updates:</strong> WebSocket-powered real-time metrics</li>
              </ul>
            </div>
          </p-accordionTab>

          <p-accordionTab header="Multi-Step Claim Submission">
            <div class="feature-content">
              <p>Our wizard-based claim submission ensures accuracy and completeness:</p>
              <ul>
                <li><strong>Step 1 - Member:</strong> Search and select member information</li>
                <li><strong>Step 2 - Provider:</strong> Choose rendering and billing providers</li>
                <li><strong>Step 3 - Services:</strong> Add diagnosis codes and service lines</li>
                <li><strong>Step 4 - Review:</strong> Verify all information before submission</li>
              </ul>
            </div>
          </p-accordionTab>

          <p-accordionTab header="Eligibility Verification">
            <div class="feature-content">
              <p>Instant verification of member eligibility and benefits:</p>
              <ul>
                <li><strong>Real-Time Check:</strong> Verify coverage before claim submission</li>
                <li><strong>Benefits Summary:</strong> View deductibles, copays, and coverage limits</li>
                <li><strong>Prior Authorization:</strong> Check if services require pre-approval</li>
                <li><strong>Coverage History:</strong> View historical eligibility data</li>
              </ul>
            </div>
          </p-accordionTab>

          <p-accordionTab header="Claims Review & Approval">
            <div class="feature-content">
              <p>Streamlined workflow for supervisors and reviewers:</p>
              <ul>
                <li><strong>Queue Management:</strong> Organized pending claims queue</li>
                <li><strong>Adjudication Tools:</strong> Approve, deny, or request more information</li>
                <li><strong>Audit Trail:</strong> Complete history of all claim actions</li>
                <li><strong>Bulk Actions:</strong> Process multiple claims efficiently</li>
              </ul>
            </div>
          </p-accordionTab>

          <p-accordionTab header="HIPAA Compliance">
            <div class="feature-content">
              <p>Built-in security features for healthcare compliance:</p>
              <ul>
                <li><strong>Session Timeout:</strong> Automatic logout after 15 minutes of inactivity</li>
                <li><strong>Audit Logging:</strong> Complete audit trail of all user actions</li>
                <li><strong>Role-Based Access:</strong> Granular permission controls</li>
                <li><strong>Secure Communication:</strong> Encrypted data transmission</li>
              </ul>
            </div>
          </p-accordionTab>
        </p-accordion>
      </section>

      <!-- Support Section -->
      <section class="support-section">
        <h3>Need Help?</h3>
        <div class="support-options">
          <div class="support-card">
            <i class="pi pi-book"></i>
            <h4>Documentation</h4>
            <p>Browse our comprehensive workflow guide and examples</p>
            <a routerLink="../workflow" class="support-link">View Workflow Guide</a>
          </div>
          <div class="support-card">
            <i class="pi pi-code"></i>
            <h4>Examples</h4>
            <p>Step-by-step walkthroughs for common tasks</p>
            <a routerLink="../examples" class="support-link">View Examples</a>
          </div>
          <div class="support-card">
            <i class="pi pi-comments"></i>
            <h4>FAQ</h4>
            <p>Answers to frequently asked questions</p>
            <a routerLink="../faq" class="support-link">View FAQ</a>
          </div>
        </div>
      </section>
    </div>
  `,
  styles: [`
    .getting-started {
      max-width: 1200px;
      margin: 0 auto;
    }

    section {
      margin-bottom: 2.5rem;
    }

    h2 {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      color: #17a2b8;
      margin-bottom: 1rem;
    }

    h3 {
      color: #343a40;
      margin-bottom: 1.25rem;
      padding-bottom: 0.5rem;
      border-bottom: 2px solid #e9ecef;
    }

    .lead {
      font-size: 1.1rem;
      color: #6c757d;
      line-height: 1.7;
    }

    /* Overview Cards */
    .overview-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1.25rem;
    }

    .overview-card {
      background: #f8f9fa;
      border-radius: 10px;
      padding: 1.5rem;
      text-align: center;
      border: 1px solid #e9ecef;
      transition: all 0.2s ease;
    }

    .overview-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .card-icon {
      width: 60px;
      height: 60px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 1rem;
    }

    .card-icon i {
      font-size: 1.75rem;
      color: white;
    }

    .card-icon.dashboard { background: linear-gradient(135deg, #0066cc, #004c99); }
    .card-icon.claims { background: linear-gradient(135deg, #28a745, #1e7e34); }
    .card-icon.eligibility { background: linear-gradient(135deg, #17a2b8, #138496); }
    .card-icon.reports { background: linear-gradient(135deg, #6f42c1, #5a32a3); }

    .overview-card h4 {
      margin: 0 0 0.5rem;
      color: #343a40;
    }

    .overview-card p {
      margin: 0;
      color: #6c757d;
      font-size: 0.9rem;
    }

    /* Roles Section */
    .roles-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1.25rem;
    }

    :host ::ng-deep .role-card {
      border: none;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }

    .role-header {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem 1.25rem;
      color: white;
      font-weight: 600;
      font-size: 1.1rem;
    }

    .role-header.processor { background: linear-gradient(135deg, #17a2b8, #138496); }
    .role-header.supervisor { background: linear-gradient(135deg, #ffc107, #d39e00); color: #343a40; }
    .role-header.admin { background: linear-gradient(135deg, #dc3545, #c82333); }

    .permissions-list {
      list-style: none;
      padding: 0;
      margin: 0 0 1rem;
    }

    .permissions-list li {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 0;
      border-bottom: 1px solid #f1f1f1;
    }

    .permissions-list li:last-child {
      border-bottom: none;
    }

    .permissions-list i {
      color: #28a745;
      font-size: 0.85rem;
    }

    .login-hint {
      background: #f8f9fa;
      padding: 0.5rem;
      border-radius: 4px;
      font-size: 0.85rem;
      color: #6c757d;
      margin: 0;
    }

    .login-hint code {
      background: #e9ecef;
      padding: 0.15rem 0.4rem;
      border-radius: 3px;
      font-family: monospace;
      color: #d63384;
    }

    /* Steps Timeline */
    .steps-timeline {
      position: relative;
      padding-left: 2rem;
    }

    .steps-timeline::before {
      content: '';
      position: absolute;
      left: 1rem;
      top: 0;
      bottom: 0;
      width: 2px;
      background: #e9ecef;
    }

    .timeline-item {
      display: flex;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
      position: relative;
    }

    .step-number {
      width: 2rem;
      height: 2rem;
      background: #17a2b8;
      color: white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      flex-shrink: 0;
      position: relative;
      z-index: 1;
    }

    .step-content {
      flex: 1;
      background: #f8f9fa;
      padding: 1.25rem;
      border-radius: 8px;
      border-left: 3px solid #17a2b8;
    }

    .step-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.5rem;
    }

    .step-header i {
      color: #17a2b8;
    }

    .step-header h4 {
      margin: 0;
      color: #343a40;
    }

    .step-content p {
      margin: 0 0 0.75rem;
      color: #6c757d;
    }

    .step-action {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      color: #17a2b8;
      text-decoration: none;
      font-weight: 500;
    }

    .step-action:hover {
      color: #138496;
    }

    /* Features Accordion */
    .feature-content {
      padding: 0.5rem 0;
    }

    .feature-content p {
      margin-bottom: 1rem;
      color: #6c757d;
    }

    .feature-content ul {
      margin: 0;
      padding-left: 1.5rem;
    }

    .feature-content li {
      margin-bottom: 0.5rem;
      color: #495057;
    }

    /* Support Section */
    .support-options {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 1.25rem;
    }

    .support-card {
      background: #f8f9fa;
      padding: 1.5rem;
      border-radius: 10px;
      text-align: center;
      border: 1px solid #e9ecef;
    }

    .support-card i {
      font-size: 2rem;
      color: #17a2b8;
      margin-bottom: 1rem;
    }

    .support-card h4 {
      margin: 0 0 0.5rem;
      color: #343a40;
    }

    .support-card p {
      margin: 0 0 1rem;
      color: #6c757d;
      font-size: 0.9rem;
    }

    .support-link {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      color: #17a2b8;
      text-decoration: none;
      font-weight: 500;
    }

    .support-link:hover {
      color: #138496;
    }

    @media (max-width: 768px) {
      .steps-timeline {
        padding-left: 0;
      }

      .steps-timeline::before {
        display: none;
      }

      .timeline-item {
        flex-direction: column;
        gap: 0.75rem;
      }

      .step-number {
        margin-left: 0;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GettingStartedComponent {
  readonly onboardingSteps: OnboardingStep[] = [
    {
      title: 'Log In to the System',
      description: 'Use your credentials to access the claims portal. For demo, use admin/demo123, processor/demo123, or supervisor/demo123.',
      icon: 'pi-sign-in',
    },
    {
      title: 'Explore the Dashboard',
      description: 'Familiarize yourself with the main dashboard showing real-time KPIs, recent activity, and system status.',
      icon: 'pi-chart-bar',
      action: { label: 'Go to Dashboard', route: '/dashboard' },
    },
    {
      title: 'Check Member Eligibility',
      description: 'Before submitting a claim, verify member eligibility and benefits coverage to ensure claim accuracy.',
      icon: 'pi-verified',
      action: { label: 'Check Eligibility', route: '/eligibility' },
    },
    {
      title: 'Submit Your First Claim',
      description: 'Use the multi-step wizard to submit a healthcare claim. Follow the guided process for member, provider, and service information.',
      icon: 'pi-file-plus',
      action: { label: 'Submit Claim', route: '/claims/new' },
    },
    {
      title: 'Track Claim Status',
      description: 'Monitor your submitted claims through the claims list. View detailed status, history, and any required actions.',
      icon: 'pi-search',
      action: { label: 'View Claims', route: '/claims' },
    },
  ];
}
