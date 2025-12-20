/**
 * FAQ Component.
 * Frequently Asked Questions with searchable answers.
 */
import { Component, ChangeDetectionStrategy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AccordionModule } from 'primeng/accordion';
import { InputTextModule } from 'primeng/inputtext';
import { TagModule } from 'primeng/tag';

interface FaqItem {
  id: string;
  question: string;
  answer: string;
  category: string;
  tags: string[];
}

interface FaqCategory {
  name: string;
  icon: string;
  items: FaqItem[];
}

@Component({
  selector: 'app-faq',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    AccordionModule,
    InputTextModule,
    TagModule,
  ],
  template: `
    <div class="faq-page">
      <!-- Header -->
      <section class="intro-section">
        <h2><i class="pi pi-comments"></i> Frequently Asked Questions</h2>
        <p class="lead">
          Find answers to common questions about the claims processing system.
          Can't find what you're looking for? Contact support for assistance.
        </p>
      </section>

      <!-- Search -->
      <section class="search-section">
        <div class="search-box">
          <i class="pi pi-search"></i>
          <input type="text"
                 pInputText
                 [(ngModel)]="searchQuery"
                 placeholder="Search questions..."
                 (input)="onSearch()" />
          @if (searchQuery()) {
            <button class="clear-btn" (click)="clearSearch()">
              <i class="pi pi-times"></i>
            </button>
          }
        </div>
        @if (searchQuery()) {
          <p class="search-results">
            Found {{ filteredCategories().length }} categories with matching questions
          </p>
        }
      </section>

      <!-- Category Quick Links -->
      <section class="category-links">
        @for (category of allCategories; track category.name) {
          <button class="category-link"
                  [class.active]="activeCategory() === category.name"
                  (click)="scrollToCategory(category.name)">
            <i [class]="'pi ' + category.icon"></i>
            <span>{{ category.name }}</span>
            <span class="count">{{ getCategoryCount(category.name) }}</span>
          </button>
        }
      </section>

      <!-- FAQ Categories -->
      <section class="faq-categories">
        @for (category of filteredCategories(); track category.name) {
          <div class="faq-category" [id]="'category-' + category.name.toLowerCase().replace(' ', '-')">
            <h3>
              <i [class]="'pi ' + category.icon"></i>
              {{ category.name }}
            </h3>
            <p-accordion [multiple]="true">
              @for (item of category.items; track item.id) {
                <p-accordionTab>
                  <ng-template pTemplate="header">
                    <div class="faq-header">
                      <span class="question">{{ item.question }}</span>
                      <div class="tags">
                        @for (tag of item.tags; track tag) {
                          <p-tag [value]="tag" severity="secondary" [rounded]="true"></p-tag>
                        }
                      </div>
                    </div>
                  </ng-template>
                  <div class="faq-answer" [innerHTML]="item.answer"></div>
                </p-accordionTab>
              }
            </p-accordion>
          </div>
        }

        @if (filteredCategories().length === 0) {
          <div class="no-results">
            <i class="pi pi-search"></i>
            <h4>No matching questions found</h4>
            <p>Try adjusting your search terms or browse all categories</p>
            <button class="p-button p-button-outlined" (click)="clearSearch()">
              Clear Search
            </button>
          </div>
        }
      </section>

      <!-- Contact Support -->
      <section class="support-section">
        <div class="support-card">
          <div class="support-content">
            <h3>Still have questions?</h3>
            <p>Our support team is here to help. Contact us for personalized assistance.</p>
          </div>
          <div class="support-actions">
            <a href="mailto:support&#64;claims.local" class="support-btn email">
              <i class="pi pi-envelope"></i>
              <span>Email Support</span>
            </a>
            <a href="tel:+18001234567" class="support-btn phone">
              <i class="pi pi-phone"></i>
              <span>1-800-123-4567</span>
            </a>
          </div>
        </div>
      </section>

      <!-- Related Resources -->
      <section class="resources-section">
        <h3>Related Resources</h3>
        <div class="resources-grid">
          <a routerLink="../getting-started" class="resource-card">
            <i class="pi pi-play"></i>
            <span>Getting Started Guide</span>
          </a>
          <a routerLink="../workflow" class="resource-card">
            <i class="pi pi-sitemap"></i>
            <span>Workflow Documentation</span>
          </a>
          <a routerLink="../examples" class="resource-card">
            <i class="pi pi-file-edit"></i>
            <span>Step-by-Step Examples</span>
          </a>
        </div>
      </section>
    </div>
  `,
  styles: [`
    .faq-page {
      max-width: 1000px;
      margin: 0 auto;
    }

    section {
      margin-bottom: 2rem;
    }

    h2 {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      color: #17a2b8;
      margin-bottom: 1rem;
    }

    h3 {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      color: #343a40;
      margin-bottom: 1rem;
    }

    .lead {
      font-size: 1.1rem;
      color: #6c757d;
      line-height: 1.7;
    }

    /* Search */
    .search-section {
      margin-bottom: 1.5rem;
    }

    .search-box {
      position: relative;
      max-width: 500px;
    }

    .search-box i.pi-search {
      position: absolute;
      left: 1rem;
      top: 50%;
      transform: translateY(-50%);
      color: #adb5bd;
    }

    .search-box input {
      width: 100%;
      padding: 0.875rem 2.5rem;
      border: 2px solid #e9ecef;
      border-radius: 25px;
      font-size: 1rem;
      transition: border-color 0.2s ease;
    }

    .search-box input:focus {
      border-color: #17a2b8;
      outline: none;
    }

    .clear-btn {
      position: absolute;
      right: 1rem;
      top: 50%;
      transform: translateY(-50%);
      background: none;
      border: none;
      color: #adb5bd;
      cursor: pointer;
      padding: 0.25rem;
    }

    .clear-btn:hover {
      color: #343a40;
    }

    .search-results {
      margin-top: 0.75rem;
      color: #6c757d;
      font-size: 0.9rem;
    }

    /* Category Links */
    .category-links {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-bottom: 2rem;
    }

    .category-link {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      background: #f8f9fa;
      border: 1px solid #e9ecef;
      border-radius: 20px;
      cursor: pointer;
      transition: all 0.2s ease;
      font-size: 0.9rem;
      color: #495057;
    }

    .category-link:hover {
      background: #e9ecef;
      border-color: #dee2e6;
    }

    .category-link.active {
      background: #17a2b8;
      border-color: #17a2b8;
      color: white;
    }

    .category-link .count {
      background: rgba(0, 0, 0, 0.1);
      padding: 0.1rem 0.4rem;
      border-radius: 10px;
      font-size: 0.8rem;
    }

    .category-link.active .count {
      background: rgba(255, 255, 255, 0.2);
    }

    /* FAQ Categories */
    .faq-category {
      margin-bottom: 2rem;
      scroll-margin-top: 1rem;
    }

    .faq-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      width: 100%;
      gap: 1rem;
    }

    .question {
      font-weight: 500;
      color: #343a40;
      flex: 1;
      text-align: left;
    }

    .tags {
      display: flex;
      gap: 0.25rem;
      flex-shrink: 0;
    }

    :host ::ng-deep .tags .p-tag {
      font-size: 0.7rem;
      padding: 0.1rem 0.4rem;
    }

    .faq-answer {
      color: #495057;
      line-height: 1.7;
      padding: 0.5rem 0;
    }

    .faq-answer :deep(ul),
    .faq-answer :deep(ol) {
      margin: 0.75rem 0;
      padding-left: 1.5rem;
    }

    .faq-answer :deep(li) {
      margin-bottom: 0.5rem;
    }

    .faq-answer :deep(strong) {
      color: #343a40;
    }

    .faq-answer :deep(code) {
      background: #e9ecef;
      padding: 0.1rem 0.4rem;
      border-radius: 3px;
      font-family: monospace;
      font-size: 0.9rem;
      color: #d63384;
    }

    /* No Results */
    .no-results {
      text-align: center;
      padding: 3rem;
      background: #f8f9fa;
      border-radius: 10px;
    }

    .no-results i {
      font-size: 3rem;
      color: #adb5bd;
      margin-bottom: 1rem;
    }

    .no-results h4 {
      margin: 0 0 0.5rem;
      color: #495057;
    }

    .no-results p {
      margin: 0 0 1rem;
      color: #6c757d;
    }

    /* Support Section */
    .support-card {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: linear-gradient(135deg, #17a2b8, #138496);
      color: white;
      padding: 1.5rem 2rem;
      border-radius: 10px;
    }

    .support-content h3 {
      margin: 0 0 0.25rem;
      color: white;
    }

    .support-content p {
      margin: 0;
      opacity: 0.9;
    }

    .support-actions {
      display: flex;
      gap: 1rem;
    }

    .support-btn {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1.25rem;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 500;
      transition: all 0.2s ease;
    }

    .support-btn.email {
      background: white;
      color: #17a2b8;
    }

    .support-btn.phone {
      background: rgba(255, 255, 255, 0.2);
      color: white;
    }

    .support-btn:hover {
      transform: translateY(-2px);
    }

    /* Resources */
    .resources-section h3 {
      padding-bottom: 0.5rem;
      border-bottom: 2px solid #e9ecef;
    }

    .resources-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
    }

    .resource-card {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem;
      background: #f8f9fa;
      border-radius: 8px;
      text-decoration: none;
      color: #495057;
      transition: all 0.2s ease;
    }

    .resource-card:hover {
      background: #17a2b8;
      color: white;
    }

    .resource-card i {
      font-size: 1.25rem;
    }

    @media (max-width: 768px) {
      .support-card {
        flex-direction: column;
        gap: 1.5rem;
        text-align: center;
      }

      .support-actions {
        flex-direction: column;
        width: 100%;
      }

      .support-btn {
        justify-content: center;
      }

      .faq-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.5rem;
      }

      .tags {
        align-self: flex-start;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FaqComponent {
  readonly searchQuery = signal<string>('');
  readonly activeCategory = signal<string>('');

  readonly allCategories: FaqCategory[] = [
    {
      name: 'General',
      icon: 'pi-info-circle',
      items: [
        {
          id: 'g1',
          question: 'What is the Claims Processing System?',
          answer: `The Claims Processing System is a comprehensive healthcare claims management platform designed to streamline the submission, processing, and adjudication of medical claims. It supports <strong>HIPAA-compliant</strong> workflows and real-time eligibility verification.`,
          category: 'General',
          tags: ['overview', 'basics'],
        },
        {
          id: 'g2',
          question: 'What browsers are supported?',
          answer: `The system supports all modern browsers including:
            <ul>
              <li>Google Chrome (recommended)</li>
              <li>Mozilla Firefox</li>
              <li>Microsoft Edge</li>
              <li>Safari (macOS)</li>
            </ul>
            For the best experience, we recommend using the latest version of Chrome.`,
          category: 'General',
          tags: ['requirements', 'browser'],
        },
        {
          id: 'g3',
          question: 'How do I change my password?',
          answer: `To change your password:
            <ol>
              <li>Click on your profile icon in the top right corner</li>
              <li>Select "Account Settings"</li>
              <li>Click "Change Password"</li>
              <li>Enter your current password and new password</li>
              <li>Click "Update Password"</li>
            </ol>
            Passwords must be at least 12 characters with uppercase, lowercase, numbers, and special characters.`,
          category: 'General',
          tags: ['account', 'security'],
        },
        {
          id: 'g4',
          question: 'Why does my session keep timing out?',
          answer: `For <strong>HIPAA compliance</strong>, sessions automatically expire after 15 minutes of inactivity. This protects sensitive healthcare information. To prevent losing work:
            <ul>
              <li>Save drafts frequently when entering claims</li>
              <li>Stay active in the application</li>
              <li>Log back in to restore your session</li>
            </ul>`,
          category: 'General',
          tags: ['security', 'session'],
        },
      ],
    },
    {
      name: 'Claims',
      icon: 'pi-file',
      items: [
        {
          id: 'c1',
          question: 'How do I submit a new claim?',
          answer: `To submit a new claim:
            <ol>
              <li>Click "Submit Claim" from the dashboard or navigate to Claims > New</li>
              <li>Enter member information and verify eligibility</li>
              <li>Select the rendering and billing provider</li>
              <li>Add diagnosis codes (ICD-10) and service lines</li>
              <li>Review all information and click Submit</li>
            </ol>
            For detailed steps, see the <strong>Examples</strong> section.`,
          category: 'Claims',
          tags: ['submission', 'how-to'],
        },
        {
          id: 'c2',
          question: 'What claim types are supported?',
          answer: `The system supports multiple claim types:
            <ul>
              <li><strong>Professional (CMS-1500)</strong>: Physician and outpatient services</li>
              <li><strong>Institutional (UB-04)</strong>: Hospital and facility claims</li>
              <li><strong>Dental</strong>: Dental procedure claims</li>
              <li><strong>Pharmacy</strong>: Prescription drug claims</li>
            </ul>`,
          category: 'Claims',
          tags: ['types', 'CMS-1500', 'UB-04'],
        },
        {
          id: 'c3',
          question: 'How can I check the status of my claim?',
          answer: `To check claim status:
            <ol>
              <li>Navigate to Claims from the main menu</li>
              <li>Use filters to search by claim ID, member, or date range</li>
              <li>Click on a claim to view detailed status</li>
            </ol>
            The claim detail page shows current status, processing history, and any required actions.`,
          category: 'Claims',
          tags: ['status', 'tracking'],
        },
        {
          id: 'c4',
          question: 'Why was my claim denied?',
          answer: `Claims can be denied for various reasons:
            <ul>
              <li><strong>Eligibility</strong>: Member not covered on date of service</li>
              <li><strong>Authorization</strong>: Missing or invalid prior authorization</li>
              <li><strong>Duplicate</strong>: Claim already processed</li>
              <li><strong>Coding</strong>: Invalid or mismatched codes</li>
              <li><strong>Timely Filing</strong>: Submitted after deadline</li>
            </ul>
            Check the denial reason code on the claim for specific details. Most denials can be appealed within 180 days.`,
          category: 'Claims',
          tags: ['denial', 'troubleshooting'],
        },
        {
          id: 'c5',
          question: 'Can I save a claim as a draft?',
          answer: `Yes! You can save a claim as a draft at any point during submission:
            <ul>
              <li>Click "Save Draft" at the bottom of any wizard step</li>
              <li>Drafts are saved to your account and can be resumed later</li>
              <li>Access saved drafts from Claims > My Drafts</li>
              <li>Drafts are automatically saved every 60 seconds</li>
            </ul>
            Drafts are retained for 30 days.`,
          category: 'Claims',
          tags: ['draft', 'save'],
        },
      ],
    },
    {
      name: 'Eligibility',
      icon: 'pi-verified',
      items: [
        {
          id: 'e1',
          question: 'How do I verify member eligibility?',
          answer: `To verify eligibility:
            <ol>
              <li>Navigate to Eligibility from the main menu</li>
              <li>Enter the member ID or search by name/DOB</li>
              <li>Select the date of service</li>
              <li>View coverage details, benefits, and limitations</li>
            </ol>
            You can also check eligibility during claim submission.`,
          category: 'Eligibility',
          tags: ['verification', 'how-to'],
        },
        {
          id: 'e2',
          question: 'What information does eligibility verification show?',
          answer: `Eligibility verification displays:
            <ul>
              <li><strong>Coverage Status</strong>: Active, terminated, or pending</li>
              <li><strong>Plan Information</strong>: Plan name, type, and network</li>
              <li><strong>Benefits</strong>: Deductibles, copays, coinsurance</li>
              <li><strong>Accumulators</strong>: Deductible met, out-of-pocket status</li>
              <li><strong>Limitations</strong>: Exclusions and waiting periods</li>
              <li><strong>Prior Auth</strong>: Services requiring authorization</li>
            </ul>`,
          category: 'Eligibility',
          tags: ['coverage', 'benefits'],
        },
        {
          id: 'e3',
          question: 'What does "eligibility not found" mean?',
          answer: `This error typically means:
            <ul>
              <li>Incorrect member ID entered</li>
              <li>Member not enrolled on the selected date</li>
              <li>Member data not yet loaded in the system</li>
              <li>Dependent entered without subscriber info</li>
            </ul>
            Try searching by name and DOB instead, or verify the member ID with enrollment.`,
          category: 'Eligibility',
          tags: ['error', 'troubleshooting'],
        },
      ],
    },
    {
      name: 'Payments',
      icon: 'pi-dollar',
      items: [
        {
          id: 'p1',
          question: 'When will payment be issued?',
          answer: `Payment timelines depend on claim type:
            <ul>
              <li><strong>Clean Claims</strong>: Payment within 30 days of receipt</li>
              <li><strong>Pended Claims</strong>: After manual review completion</li>
              <li><strong>Electronic (EFT)</strong>: 2-3 business days after approval</li>
              <li><strong>Paper Check</strong>: 7-10 business days after approval</li>
            </ul>`,
          category: 'Payments',
          tags: ['timeline', 'EFT'],
        },
        {
          id: 'p2',
          question: 'How do I sign up for electronic payments?',
          answer: `To enroll in EFT payments:
            <ol>
              <li>Contact Provider Services at 1-800-123-4567</li>
              <li>Complete the EFT enrollment form</li>
              <li>Provide banking information and tax ID</li>
              <li>Allow 2-3 weeks for processing</li>
            </ol>
            EFT payments are faster and more secure than paper checks.`,
          category: 'Payments',
          tags: ['EFT', 'enrollment'],
        },
        {
          id: 'p3',
          question: 'What is an ERA/835?',
          answer: `An <strong>ERA (Electronic Remittance Advice)</strong> or <strong>835 transaction</strong> is the electronic version of an Explanation of Benefits. It contains:
            <ul>
              <li>Payment details for each claim line</li>
              <li>Adjustment reason codes</li>
              <li>Patient responsibility amounts</li>
              <li>Remark codes with additional information</li>
            </ul>
            ERAs can be downloaded from the Reports section or received via clearinghouse.`,
          category: 'Payments',
          tags: ['ERA', '835', 'remittance'],
        },
      ],
    },
    {
      name: 'Technical',
      icon: 'pi-cog',
      items: [
        {
          id: 't1',
          question: 'What file formats are supported for attachments?',
          answer: `Supported attachment formats include:
            <ul>
              <li><strong>Documents</strong>: PDF, DOC, DOCX</li>
              <li><strong>Images</strong>: JPG, PNG, TIFF</li>
              <li><strong>Spreadsheets</strong>: XLS, XLSX, CSV</li>
            </ul>
            Maximum file size is 10MB per attachment, 50MB total per claim.`,
          category: 'Technical',
          tags: ['attachments', 'files'],
        },
        {
          id: 't2',
          question: 'Can I integrate with my practice management system?',
          answer: `Yes! We offer several integration options:
            <ul>
              <li><strong>EDI/837</strong>: Standard HIPAA transactions</li>
              <li><strong>REST API</strong>: Real-time claim submission and status</li>
              <li><strong>SFTP</strong>: Batch file submission</li>
              <li><strong>Clearinghouse</strong>: Connect through your existing clearinghouse</li>
            </ul>
            Contact Technical Support for integration documentation.`,
          category: 'Technical',
          tags: ['integration', 'API', 'EDI'],
        },
        {
          id: 't3',
          question: 'Is the system HIPAA compliant?',
          answer: `Yes, the system is fully <strong>HIPAA compliant</strong>:
            <ul>
              <li>256-bit AES encryption for data at rest</li>
              <li>TLS 1.3 encryption for data in transit</li>
              <li>Automatic session timeout after 15 minutes</li>
              <li>Complete audit logging of all user actions</li>
              <li>Role-based access controls</li>
              <li>Annual third-party security assessments</li>
            </ul>`,
          category: 'Technical',
          tags: ['HIPAA', 'security', 'compliance'],
        },
      ],
    },
  ];

  readonly filteredCategories = computed(() => {
    const query = this.searchQuery().toLowerCase();
    if (!query) {
      return this.allCategories;
    }

    return this.allCategories
      .map(category => ({
        ...category,
        items: category.items.filter(item =>
          item.question.toLowerCase().includes(query) ||
          item.answer.toLowerCase().includes(query) ||
          item.tags.some(tag => tag.toLowerCase().includes(query))
        ),
      }))
      .filter(category => category.items.length > 0);
  });

  onSearch(): void {
    // Search is handled by computed signal
  }

  clearSearch(): void {
    this.searchQuery.set('');
  }

  getCategoryCount(categoryName: string): number {
    const category = this.allCategories.find(c => c.name === categoryName);
    return category?.items.length ?? 0;
  }

  scrollToCategory(categoryName: string): void {
    this.activeCategory.set(categoryName);
    const elementId = 'category-' + categoryName.toLowerCase().replace(' ', '-');
    const element = document.getElementById(elementId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  }
}
