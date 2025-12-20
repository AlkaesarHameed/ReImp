/**
 * Examples Component.
 * Step-by-step walkthroughs for common tasks.
 */
import { Component, ChangeDetectionStrategy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { StepsModule } from 'primeng/steps';
import { AccordionModule } from 'primeng/accordion';
import { TagModule } from 'primeng/tag';

interface Example {
  id: string;
  title: string;
  description: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  duration: string;
  icon: string;
  steps: ExampleStep[];
}

interface ExampleStep {
  label: string;
  description: string;
  tips?: string[];
  screenshot?: string;
}

@Component({
  selector: 'app-examples',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    CardModule,
    ButtonModule,
    StepsModule,
    AccordionModule,
    TagModule,
  ],
  template: `
    <div class="examples-page">
      <!-- Header -->
      <section class="intro-section">
        <h2><i class="pi pi-file-edit"></i> Step-by-Step Examples</h2>
        <p class="lead">
          Learn by doing with these detailed walkthroughs. Each example guides you
          through common tasks with clear instructions and helpful tips.
        </p>
      </section>

      <!-- Example Cards Grid -->
      <section class="examples-grid-section">
        <div class="examples-grid">
          @for (example of examples; track example.id) {
            <div class="example-card" (click)="selectExample(example)"
                 [class.selected]="selectedExample()?.id === example.id">
              <div class="example-header">
                <div class="example-icon" [class]="'icon-' + example.difficulty">
                  <i [class]="'pi ' + example.icon"></i>
                </div>
                <p-tag [value]="example.difficulty | titlecase"
                       [severity]="getDifficultySeverity(example.difficulty)"></p-tag>
              </div>
              <h4>{{ example.title }}</h4>
              <p>{{ example.description }}</p>
              <div class="example-meta">
                <span><i class="pi pi-clock"></i> {{ example.duration }}</span>
                <span><i class="pi pi-list"></i> {{ example.steps.length }} steps</span>
              </div>
            </div>
          }
        </div>
      </section>

      <!-- Selected Example Detail -->
      @if (selectedExample()) {
        <section class="example-detail-section">
          <div class="example-detail">
            <div class="detail-header">
              <div class="header-left">
                <h3>{{ selectedExample()!.title }}</h3>
                <div class="header-meta">
                  <p-tag [value]="selectedExample()!.difficulty | titlecase"
                         [severity]="getDifficultySeverity(selectedExample()!.difficulty)"></p-tag>
                  <span><i class="pi pi-clock"></i> {{ selectedExample()!.duration }}</span>
                </div>
              </div>
              <button pButton label="Close" icon="pi pi-times"
                      class="p-button-text" (click)="clearSelection()"></button>
            </div>

            <!-- Steps -->
            <div class="steps-container">
              @for (step of selectedExample()!.steps; track step.label; let i = $index) {
                <div class="step-item" [class.active]="activeStep() === i">
                  <div class="step-marker" (click)="setActiveStep(i)">
                    <span class="step-number">{{ i + 1 }}</span>
                  </div>
                  <div class="step-content">
                    <h4 (click)="setActiveStep(i)">{{ step.label }}</h4>
                    @if (activeStep() === i) {
                      <div class="step-details">
                        <p>{{ step.description }}</p>
                        @if (step.tips && step.tips.length > 0) {
                          <div class="tips-box">
                            <h5><i class="pi pi-lightbulb"></i> Pro Tips</h5>
                            <ul>
                              @for (tip of step.tips; track tip) {
                                <li>{{ tip }}</li>
                              }
                            </ul>
                          </div>
                        }
                      </div>
                    }
                  </div>
                </div>
              }
            </div>

            <!-- Navigation -->
            <div class="step-navigation">
              <button pButton label="Previous" icon="pi pi-arrow-left"
                      class="p-button-outlined"
                      [disabled]="activeStep() === 0"
                      (click)="previousStep()"></button>
              <span class="step-indicator">
                Step {{ activeStep() + 1 }} of {{ selectedExample()!.steps.length }}
              </span>
              <button pButton [label]="activeStep() === selectedExample()!.steps.length - 1 ? 'Finish' : 'Next'"
                      [icon]="activeStep() === selectedExample()!.steps.length - 1 ? 'pi pi-check' : 'pi pi-arrow-right'"
                      iconPos="right"
                      (click)="nextStep()"></button>
            </div>
          </div>
        </section>
      }

      <!-- Quick Reference Section -->
      <section class="quick-ref-section">
        <h3>Quick Reference</h3>
        <p-accordion>
          <p-accordionTab header="Common Keyboard Shortcuts">
            <div class="shortcuts-grid">
              <div class="shortcut">
                <kbd>Ctrl</kbd> + <kbd>N</kbd>
                <span>New Claim</span>
              </div>
              <div class="shortcut">
                <kbd>Ctrl</kbd> + <kbd>S</kbd>
                <span>Save Draft</span>
              </div>
              <div class="shortcut">
                <kbd>Ctrl</kbd> + <kbd>F</kbd>
                <span>Search Claims</span>
              </div>
              <div class="shortcut">
                <kbd>Ctrl</kbd> + <kbd>E</kbd>
                <span>Check Eligibility</span>
              </div>
              <div class="shortcut">
                <kbd>Esc</kbd>
                <span>Close Dialog</span>
              </div>
              <div class="shortcut">
                <kbd>Tab</kbd>
                <span>Next Field</span>
              </div>
            </div>
          </p-accordionTab>

          <p-accordionTab header="Sample Data for Testing">
            <div class="sample-data">
              <h5>Test Member IDs</h5>
              <table class="data-table">
                <tr>
                  <th>Member ID</th>
                  <th>Name</th>
                  <th>Coverage Type</th>
                </tr>
                <tr>
                  <td><code>MEM-001</code></td>
                  <td>John Smith</td>
                  <td>PPO - Family</td>
                </tr>
                <tr>
                  <td><code>MEM-002</code></td>
                  <td>Jane Doe</td>
                  <td>HMO - Individual</td>
                </tr>
                <tr>
                  <td><code>MEM-003</code></td>
                  <td>Robert Johnson</td>
                  <td>EPO - Family</td>
                </tr>
              </table>

              <h5>Test Provider NPIs</h5>
              <table class="data-table">
                <tr>
                  <th>NPI</th>
                  <th>Provider Name</th>
                  <th>Specialty</th>
                </tr>
                <tr>
                  <td><code>1234567890</code></td>
                  <td>City Medical Center</td>
                  <td>General Hospital</td>
                </tr>
                <tr>
                  <td><code>2345678901</code></td>
                  <td>Dr. Sarah Williams</td>
                  <td>Internal Medicine</td>
                </tr>
                <tr>
                  <td><code>3456789012</code></td>
                  <td>Valley Urgent Care</td>
                  <td>Urgent Care</td>
                </tr>
              </table>

              <h5>Common Diagnosis Codes (ICD-10)</h5>
              <table class="data-table">
                <tr>
                  <th>Code</th>
                  <th>Description</th>
                </tr>
                <tr>
                  <td><code>J06.9</code></td>
                  <td>Acute upper respiratory infection</td>
                </tr>
                <tr>
                  <td><code>M54.5</code></td>
                  <td>Low back pain</td>
                </tr>
                <tr>
                  <td><code>I10</code></td>
                  <td>Essential hypertension</td>
                </tr>
                <tr>
                  <td><code>E11.9</code></td>
                  <td>Type 2 diabetes mellitus</td>
                </tr>
              </table>

              <h5>Common Procedure Codes (CPT)</h5>
              <table class="data-table">
                <tr>
                  <th>Code</th>
                  <th>Description</th>
                </tr>
                <tr>
                  <td><code>99213</code></td>
                  <td>Office visit - established patient, moderate complexity</td>
                </tr>
                <tr>
                  <td><code>99214</code></td>
                  <td>Office visit - established patient, high complexity</td>
                </tr>
                <tr>
                  <td><code>36415</code></td>
                  <td>Venipuncture (blood draw)</td>
                </tr>
                <tr>
                  <td><code>80053</code></td>
                  <td>Comprehensive metabolic panel</td>
                </tr>
              </table>
            </div>
          </p-accordionTab>

          <p-accordionTab header="Troubleshooting Common Issues">
            <div class="troubleshooting">
              <div class="issue">
                <h5><i class="pi pi-exclamation-circle"></i> Claim Submission Fails</h5>
                <p><strong>Problem:</strong> Error message when trying to submit a claim</p>
                <p><strong>Solution:</strong></p>
                <ul>
                  <li>Verify all required fields are completed</li>
                  <li>Check that member eligibility is active</li>
                  <li>Ensure provider NPI is valid and in network</li>
                  <li>Confirm diagnosis codes match service codes</li>
                </ul>
              </div>

              <div class="issue">
                <h5><i class="pi pi-exclamation-circle"></i> Member Not Found</h5>
                <p><strong>Problem:</strong> Unable to find member during eligibility check</p>
                <p><strong>Solution:</strong></p>
                <ul>
                  <li>Verify member ID format (MEM-XXX)</li>
                  <li>Check date of birth matches records</li>
                  <li>Try searching by name and DOB combination</li>
                  <li>Contact enrollment if member recently added</li>
                </ul>
              </div>

              <div class="issue">
                <h5><i class="pi pi-exclamation-circle"></i> Session Timeout</h5>
                <p><strong>Problem:</strong> Logged out unexpectedly</p>
                <p><strong>Solution:</strong></p>
                <ul>
                  <li>Sessions expire after 15 minutes of inactivity (HIPAA requirement)</li>
                  <li>Save drafts frequently during claim entry</li>
                  <li>Keep browser active while working</li>
                  <li>Re-login and restore from saved draft</li>
                </ul>
              </div>
            </div>
          </p-accordionTab>
        </p-accordion>
      </section>

      <!-- Action Cards -->
      <section class="action-section">
        <h3>Ready to Try?</h3>
        <div class="action-cards">
          <a routerLink="/claims/new" class="action-card primary">
            <i class="pi pi-file-plus"></i>
            <span>Submit a New Claim</span>
            <small>Start with a real claim submission</small>
          </a>
          <a routerLink="/eligibility" class="action-card secondary">
            <i class="pi pi-verified"></i>
            <span>Check Eligibility</span>
            <small>Verify member coverage</small>
          </a>
          <a routerLink="/claims" class="action-card tertiary">
            <i class="pi pi-list"></i>
            <span>Browse Claims</span>
            <small>View existing claims</small>
          </a>
        </div>
      </section>
    </div>
  `,
  styles: [`
    .examples-page {
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

    /* Examples Grid */
    .examples-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1.25rem;
    }

    .example-card {
      background: white;
      border: 2px solid #e9ecef;
      border-radius: 10px;
      padding: 1.5rem;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .example-card:hover {
      border-color: #17a2b8;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .example-card.selected {
      border-color: #17a2b8;
      background: #e8f7f9;
    }

    .example-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1rem;
    }

    .example-icon {
      width: 45px;
      height: 45px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
    }

    .example-icon.icon-beginner { background: #28a745; }
    .example-icon.icon-intermediate { background: #ffc107; }
    .example-icon.icon-advanced { background: #dc3545; }

    .example-icon i {
      font-size: 1.25rem;
    }

    .example-card h4 {
      margin: 0 0 0.5rem;
      color: #343a40;
    }

    .example-card p {
      margin: 0 0 1rem;
      color: #6c757d;
      font-size: 0.9rem;
    }

    .example-meta {
      display: flex;
      gap: 1rem;
      font-size: 0.85rem;
      color: #adb5bd;
    }

    .example-meta span {
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }

    /* Example Detail */
    .example-detail {
      background: #f8f9fa;
      border-radius: 10px;
      padding: 1.5rem;
      border: 1px solid #e9ecef;
    }

    .detail-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1.5rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid #e9ecef;
    }

    .detail-header h3 {
      margin: 0 0 0.5rem;
      padding: 0;
      border: none;
    }

    .header-meta {
      display: flex;
      align-items: center;
      gap: 1rem;
      color: #6c757d;
      font-size: 0.9rem;
    }

    /* Steps */
    .steps-container {
      margin-bottom: 1.5rem;
    }

    .step-item {
      display: flex;
      gap: 1rem;
      margin-bottom: 0.5rem;
    }

    .step-marker {
      flex-shrink: 0;
      cursor: pointer;
    }

    .step-number {
      width: 32px;
      height: 32px;
      background: #e9ecef;
      color: #6c757d;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      transition: all 0.2s ease;
    }

    .step-item.active .step-number {
      background: #17a2b8;
      color: white;
    }

    .step-content {
      flex: 1;
      padding-bottom: 1rem;
      border-bottom: 1px solid #e9ecef;
    }

    .step-item:last-child .step-content {
      border-bottom: none;
    }

    .step-content h4 {
      margin: 0;
      color: #6c757d;
      cursor: pointer;
      font-size: 1rem;
      padding: 0.25rem 0;
    }

    .step-item.active .step-content h4 {
      color: #17a2b8;
    }

    .step-details {
      margin-top: 0.75rem;
      padding: 1rem;
      background: white;
      border-radius: 8px;
      border-left: 3px solid #17a2b8;
    }

    .step-details p {
      margin: 0 0 1rem;
      color: #495057;
      line-height: 1.6;
    }

    .tips-box {
      background: #fff3cd;
      border-radius: 6px;
      padding: 1rem;
    }

    .tips-box h5 {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin: 0 0 0.5rem;
      color: #856404;
    }

    .tips-box ul {
      margin: 0;
      padding-left: 1.25rem;
    }

    .tips-box li {
      color: #856404;
      margin-bottom: 0.25rem;
    }

    /* Step Navigation */
    .step-navigation {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 1rem;
      border-top: 1px solid #e9ecef;
    }

    .step-indicator {
      color: #6c757d;
      font-size: 0.9rem;
    }

    /* Shortcuts Grid */
    .shortcuts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
    }

    .shortcut {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem;
      background: #f8f9fa;
      border-radius: 6px;
    }

    kbd {
      background: #343a40;
      color: white;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      font-family: monospace;
      font-size: 0.85rem;
    }

    .shortcut span {
      margin-left: auto;
      color: #6c757d;
      font-size: 0.9rem;
    }

    /* Sample Data */
    .sample-data h5 {
      color: #343a40;
      margin: 1.5rem 0 0.75rem;
    }

    .sample-data h5:first-child {
      margin-top: 0;
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }

    .data-table th,
    .data-table td {
      padding: 0.75rem;
      text-align: left;
      border-bottom: 1px solid #e9ecef;
    }

    .data-table th {
      background: #f8f9fa;
      font-weight: 600;
      color: #343a40;
    }

    .data-table code {
      background: #e9ecef;
      padding: 0.15rem 0.4rem;
      border-radius: 3px;
      font-family: monospace;
      color: #d63384;
    }

    /* Troubleshooting */
    .troubleshooting .issue {
      padding: 1rem;
      background: #f8f9fa;
      border-radius: 8px;
      margin-bottom: 1rem;
      border-left: 3px solid #ffc107;
    }

    .troubleshooting .issue:last-child {
      margin-bottom: 0;
    }

    .troubleshooting h5 {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin: 0 0 0.75rem;
      color: #856404;
    }

    .troubleshooting p {
      margin: 0 0 0.5rem;
      color: #495057;
    }

    .troubleshooting ul {
      margin: 0;
      padding-left: 1.5rem;
    }

    .troubleshooting li {
      margin-bottom: 0.25rem;
      color: #6c757d;
    }

    /* Action Cards */
    .action-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1.25rem;
    }

    .action-card {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      padding: 1.5rem;
      border-radius: 10px;
      text-decoration: none;
      transition: all 0.2s ease;
    }

    .action-card.primary {
      background: linear-gradient(135deg, #17a2b8, #138496);
      color: white;
    }

    .action-card.secondary {
      background: linear-gradient(135deg, #28a745, #1e7e34);
      color: white;
    }

    .action-card.tertiary {
      background: linear-gradient(135deg, #6f42c1, #5a32a3);
      color: white;
    }

    .action-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
    }

    .action-card i {
      font-size: 2rem;
      margin-bottom: 0.75rem;
    }

    .action-card span {
      font-weight: 600;
      font-size: 1.1rem;
      margin-bottom: 0.25rem;
    }

    .action-card small {
      opacity: 0.9;
    }

    @media (max-width: 768px) {
      .detail-header {
        flex-direction: column;
        gap: 1rem;
      }

      .step-navigation {
        flex-direction: column;
        gap: 1rem;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExamplesComponent {
  readonly selectedExample = signal<Example | null>(null);
  readonly activeStep = signal<number>(0);

  readonly examples: Example[] = [
    {
      id: 'submit-claim',
      title: 'Submit a Professional Claim',
      description: 'Learn how to submit a standard professional claim using the multi-step wizard.',
      difficulty: 'beginner',
      duration: '10 min',
      icon: 'pi-file-plus',
      steps: [
        {
          label: 'Navigate to New Claim',
          description: 'From the dashboard, click "Submit Claim" or navigate to Claims > New Claim from the menu. This opens the claim submission wizard.',
          tips: [
            'You can also use the keyboard shortcut Ctrl+N',
            'Make sure you\'re logged in with appropriate permissions'
          ]
        },
        {
          label: 'Enter Member Information',
          description: 'Search for the member by entering their Member ID (e.g., MEM-001) or search by name and date of birth. The system will verify eligibility automatically.',
          tips: [
            'Always verify the member\'s eligibility before proceeding',
            'Check for any authorization requirements',
            'Confirm the correct policy period'
          ]
        },
        {
          label: 'Select Provider',
          description: 'Enter the rendering provider\'s NPI number (10 digits). The system will validate the NPI and show provider details. Also enter the billing provider if different.',
          tips: [
            'Use the provider search if you don\'t have the NPI',
            'Verify the provider is in-network for better reimbursement',
            'The billing address must match the provider\'s registered address'
          ]
        },
        {
          label: 'Add Service Lines',
          description: 'Enter the diagnosis codes (ICD-10) and add service line items with CPT/HCPCS codes, dates of service, and billed amounts. Link each service to appropriate diagnosis codes.',
          tips: [
            'Primary diagnosis should be listed first',
            'Each service line can link to up to 4 diagnosis codes',
            'Use modifiers when applicable (e.g., 25 for significant E/M)',
            'Double-check units for injection codes'
          ]
        },
        {
          label: 'Review and Submit',
          description: 'Review all entered information on the summary screen. The system will show any validation warnings. Once verified, click Submit to process the claim.',
          tips: [
            'Save as draft if you need to gather more information',
            'Review the estimated allowed amount',
            'Note the claim ID for tracking purposes'
          ]
        }
      ]
    },
    {
      id: 'check-eligibility',
      title: 'Verify Member Eligibility',
      description: 'Check a member\'s coverage status, benefits, and authorization requirements.',
      difficulty: 'beginner',
      duration: '5 min',
      icon: 'pi-verified',
      steps: [
        {
          label: 'Access Eligibility Check',
          description: 'Navigate to Eligibility from the main menu or dashboard. You can also access it during claim submission.',
          tips: [
            'Use Ctrl+E for quick access',
            'Eligibility can be checked without starting a claim'
          ]
        },
        {
          label: 'Search for Member',
          description: 'Enter the member\'s ID number or search by name and date of birth. For dependents, you may need the subscriber\'s information.',
          tips: [
            'Member IDs are case-sensitive',
            'Include leading zeros if applicable'
          ]
        },
        {
          label: 'Select Date of Service',
          description: 'Enter the date of service you want to verify eligibility for. This is important as coverage can change over time.',
          tips: [
            'You can check eligibility for past dates',
            'Future dates up to 90 days can be verified',
            'Consider checking multiple dates for ongoing treatment'
          ]
        },
        {
          label: 'Review Coverage Details',
          description: 'The system displays the member\'s plan information, benefit details, deductible status, and any limitations or exclusions.',
          tips: [
            'Note the accumulator balances (deductible met)',
            'Check out-of-pocket maximum status',
            'Review any pre-existing condition periods'
          ]
        },
        {
          label: 'Check Authorization Requirements',
          description: 'View any services that require prior authorization. The system shows which procedures need approval before services are rendered.',
          tips: [
            'Request authorization well in advance',
            'Note the authorization validity period',
            'Document the authorization number'
          ]
        }
      ]
    },
    {
      id: 'review-claim',
      title: 'Review and Adjudicate Claims',
      description: 'Process claims from the review queue, including approval, denial, and adjustment workflows.',
      difficulty: 'intermediate',
      duration: '15 min',
      icon: 'pi-eye',
      steps: [
        {
          label: 'Access Review Queue',
          description: 'Navigate to Claims > Pending Review to see claims awaiting manual adjudication. Use filters to sort by pend reason, age, or dollar amount.',
          tips: [
            'Sort by oldest first to meet processing timelines',
            'High-dollar claims may have different workflows',
            'Check your assigned queue first'
          ]
        },
        {
          label: 'Open Claim for Review',
          description: 'Click on a claim to open the review screen. Review all claim details including member info, provider, diagnosis codes, and billed amounts.',
          tips: [
            'Use the keyboard arrows to navigate between claims',
            'Open medical policy reference in a new tab',
            'Check the audit trail for previous actions'
          ]
        },
        {
          label: 'Evaluate Pend Reason',
          description: 'Review why the claim was pended. Common reasons include missing authorization, medical necessity review, or coordination of benefits.',
          tips: [
            'Refer to the pend code reference guide',
            'Check if documentation has been received',
            'Review similar claims for consistency'
          ]
        },
        {
          label: 'Make Adjudication Decision',
          description: 'Based on your review, select the appropriate action: Approve (process for payment), Deny (with reason code), Adjust (modify payment), or Request Info.',
          tips: [
            'Always include denial reason codes',
            'Document your rationale for auditing',
            'Use adjustment codes for partial payments'
          ]
        },
        {
          label: 'Complete and Document',
          description: 'Add any necessary notes explaining your decision. Submit the adjudication and the claim will move to the next status.',
          tips: [
            'Clear documentation protects against appeals',
            'Reference specific policy provisions',
            'Note any provider education opportunities'
          ]
        }
      ]
    },
    {
      id: 'generate-report',
      title: 'Generate Claims Reports',
      description: 'Create and export reports for claims activity, financial summaries, and performance metrics.',
      difficulty: 'intermediate',
      duration: '10 min',
      icon: 'pi-chart-bar',
      steps: [
        {
          label: 'Navigate to Reports',
          description: 'Access the Reports section from the main navigation. You\'ll see a dashboard with key metrics and report options.',
          tips: [
            'Reports require the reports:view permission',
            'Scheduled reports run automatically'
          ]
        },
        {
          label: 'Select Report Type',
          description: 'Choose from available report types: Claims Summary, Financial Report, Processing Metrics, Provider Analysis, or create a Custom Report.',
          tips: [
            'Start with pre-built reports before customizing',
            'Check report definitions for included data'
          ]
        },
        {
          label: 'Configure Parameters',
          description: 'Set the date range, filters (status, provider, amount range), and grouping options. Preview the report before generating.',
          tips: [
            'Large date ranges may take longer to process',
            'Use appropriate filters to limit data size',
            'Save parameter sets for repeated reports'
          ]
        },
        {
          label: 'Generate and Review',
          description: 'Click Generate to create the report. Review the results on screen, checking totals and data accuracy.',
          tips: [
            'Verify totals against known benchmarks',
            'Drill down into details for verification',
            'Note any unexpected variances'
          ]
        },
        {
          label: 'Export and Share',
          description: 'Export the report in your preferred format (PDF, Excel, CSV). Schedule recurring reports or share with team members.',
          tips: [
            'Excel format is best for further analysis',
            'PDF is ideal for presentations',
            'Set up automated email delivery for recurring reports'
          ]
        }
      ]
    }
  ];

  selectExample(example: Example): void {
    this.selectedExample.set(example);
    this.activeStep.set(0);
  }

  clearSelection(): void {
    this.selectedExample.set(null);
    this.activeStep.set(0);
  }

  setActiveStep(index: number): void {
    this.activeStep.set(index);
  }

  nextStep(): void {
    const example = this.selectedExample();
    if (example && this.activeStep() < example.steps.length - 1) {
      this.activeStep.update(s => s + 1);
    }
  }

  previousStep(): void {
    if (this.activeStep() > 0) {
      this.activeStep.update(s => s - 1);
    }
  }

  getDifficultySeverity(difficulty: string): 'success' | 'warning' | 'danger' {
    switch (difficulty) {
      case 'beginner': return 'success';
      case 'intermediate': return 'warning';
      case 'advanced': return 'danger';
      default: return 'success';
    }
  }
}
