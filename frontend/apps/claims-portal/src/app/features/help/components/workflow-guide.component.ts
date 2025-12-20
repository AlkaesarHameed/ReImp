/**
 * Workflow Guide Component.
 * Comprehensive claims processing workflow documentation.
 */
import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { TabViewModule } from 'primeng/tabview';
import { TimelineModule } from 'primeng/timeline';
import { TagModule } from 'primeng/tag';

interface ClaimStatus {
  code: string;
  label: string;
  description: string;
  color: 'info' | 'warning' | 'success' | 'danger' | 'secondary';
}

@Component({
  selector: 'app-workflow-guide',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    CardModule,
    TabViewModule,
    TimelineModule,
    TagModule,
  ],
  template: `
    <div class="workflow-guide">
      <!-- Introduction -->
      <section class="intro-section">
        <h2><i class="pi pi-sitemap"></i> Claims Processing Workflow</h2>
        <p class="lead">
          Understanding the claims processing workflow is essential for efficient operations.
          This guide explains each stage of the process, from submission to final adjudication.
        </p>
      </section>

      <!-- Workflow Diagram -->
      <section class="diagram-section">
        <h3>Workflow Overview</h3>
        <div class="workflow-diagram">
          <div class="workflow-row">
            @for (stage of mainWorkflowStages; track stage.status) {
              <div class="workflow-node" [class]="'node-' + stage.status">
                <div class="node-icon">
                  <i [class]="'pi ' + stage.icon"></i>
                </div>
                <div class="node-label">{{ stage.label }}</div>
                @if (!$last) {
                  <div class="node-arrow">
                    <i class="pi pi-arrow-right"></i>
                  </div>
                }
              </div>
            }
          </div>
          <div class="workflow-legend">
            <span class="legend-item">
              <span class="legend-color pending"></span> Pending Action
            </span>
            <span class="legend-item">
              <span class="legend-color processing"></span> In Progress
            </span>
            <span class="legend-item">
              <span class="legend-color completed"></span> Completed
            </span>
          </div>
        </div>
      </section>

      <!-- Detailed Stages -->
      <section class="stages-section">
        <h3>Detailed Stage Descriptions</h3>
        <p-tabView>
          <!-- Submission Stage -->
          <p-tabPanel header="1. Submission">
            <div class="stage-detail">
              <div class="stage-header">
                <div class="stage-icon submission">
                  <i class="pi pi-file-plus"></i>
                </div>
                <div>
                  <h4>Claim Submission</h4>
                  <p-tag value="Initial Stage" severity="info"></p-tag>
                </div>
              </div>

              <div class="stage-content">
                <h5>Overview</h5>
                <p>
                  The submission stage is where new claims enter the system. Claims can be
                  submitted through the web portal, EDI batch processing, or API integration.
                </p>

                <h5>Required Information</h5>
                <div class="info-grid">
                  <div class="info-card">
                    <h6><i class="pi pi-user"></i> Member Information</h6>
                    <ul>
                      <li>Member ID</li>
                      <li>Date of Birth</li>
                      <li>Group Number</li>
                      <li>Relationship to Subscriber</li>
                    </ul>
                  </div>
                  <div class="info-card">
                    <h6><i class="pi pi-briefcase"></i> Provider Information</h6>
                    <ul>
                      <li>Rendering Provider NPI</li>
                      <li>Billing Provider NPI</li>
                      <li>Tax ID / EIN</li>
                      <li>Service Location</li>
                    </ul>
                  </div>
                  <div class="info-card">
                    <h6><i class="pi pi-list"></i> Service Details</h6>
                    <ul>
                      <li>Date of Service</li>
                      <li>Diagnosis Codes (ICD-10)</li>
                      <li>Procedure Codes (CPT/HCPCS)</li>
                      <li>Billed Amount</li>
                    </ul>
                  </div>
                </div>

                <h5>Validation Checks</h5>
                <ul class="validation-list">
                  <li><i class="pi pi-check-circle"></i> Member eligibility verification</li>
                  <li><i class="pi pi-check-circle"></i> Provider network status</li>
                  <li><i class="pi pi-check-circle"></i> Duplicate claim detection</li>
                  <li><i class="pi pi-check-circle"></i> Required field validation</li>
                  <li><i class="pi pi-check-circle"></i> Code validity (ICD-10, CPT)</li>
                </ul>
              </div>
            </div>
          </p-tabPanel>

          <!-- Processing Stage -->
          <p-tabPanel header="2. Processing">
            <div class="stage-detail">
              <div class="stage-header">
                <div class="stage-icon processing">
                  <i class="pi pi-cog"></i>
                </div>
                <div>
                  <h4>Claims Processing</h4>
                  <p-tag value="Auto-Adjudication" severity="warning"></p-tag>
                </div>
              </div>

              <div class="stage-content">
                <h5>Overview</h5>
                <p>
                  During processing, claims go through automated adjudication rules.
                  The system applies business rules, fee schedules, and policy terms
                  to determine payment amounts.
                </p>

                <h5>Auto-Adjudication Rules</h5>
                <div class="rules-grid">
                  <div class="rule-card">
                    <span class="rule-number">1</span>
                    <div class="rule-content">
                      <h6>Eligibility Check</h6>
                      <p>Verify member was eligible on date of service</p>
                    </div>
                  </div>
                  <div class="rule-card">
                    <span class="rule-number">2</span>
                    <div class="rule-content">
                      <h6>Benefits Application</h6>
                      <p>Apply deductibles, copays, and coinsurance</p>
                    </div>
                  </div>
                  <div class="rule-card">
                    <span class="rule-number">3</span>
                    <div class="rule-content">
                      <h6>Fee Schedule Lookup</h6>
                      <p>Determine allowed amounts based on contracts</p>
                    </div>
                  </div>
                  <div class="rule-card">
                    <span class="rule-number">4</span>
                    <div class="rule-content">
                      <h6>Medical Policy</h6>
                      <p>Check for medical necessity and coverage</p>
                    </div>
                  </div>
                  <div class="rule-card">
                    <span class="rule-number">5</span>
                    <div class="rule-content">
                      <h6>Coordination of Benefits</h6>
                      <p>Handle primary/secondary payer logic</p>
                    </div>
                  </div>
                  <div class="rule-card">
                    <span class="rule-number">6</span>
                    <div class="rule-content">
                      <h6>Payment Calculation</h6>
                      <p>Calculate final payment and member responsibility</p>
                    </div>
                  </div>
                </div>

                <h5>Processing Outcomes</h5>
                <div class="outcomes-grid">
                  <div class="outcome auto-approved">
                    <i class="pi pi-check-circle"></i>
                    <span>Auto-Approved</span>
                    <small>Passes all rules, payment calculated</small>
                  </div>
                  <div class="outcome pended">
                    <i class="pi pi-clock"></i>
                    <span>Pended for Review</span>
                    <small>Requires manual intervention</small>
                  </div>
                  <div class="outcome auto-denied">
                    <i class="pi pi-times-circle"></i>
                    <span>Auto-Denied</span>
                    <small>Fails critical rules</small>
                  </div>
                </div>
              </div>
            </div>
          </p-tabPanel>

          <!-- Review Stage -->
          <p-tabPanel header="3. Review">
            <div class="stage-detail">
              <div class="stage-header">
                <div class="stage-icon review">
                  <i class="pi pi-eye"></i>
                </div>
                <div>
                  <h4>Manual Review</h4>
                  <p-tag value="Human Decision" severity="secondary"></p-tag>
                </div>
              </div>

              <div class="stage-content">
                <h5>Overview</h5>
                <p>
                  Claims that cannot be auto-adjudicated are routed to manual review.
                  Trained claims examiners evaluate these claims and make decisions
                  based on policy guidelines and medical necessity.
                </p>

                <h5>Common Pend Reasons</h5>
                <div class="pend-reasons">
                  <div class="pend-reason">
                    <span class="pend-code">P01</span>
                    <span class="pend-desc">Missing or invalid authorization</span>
                  </div>
                  <div class="pend-reason">
                    <span class="pend-code">P02</span>
                    <span class="pend-desc">Medical records required</span>
                  </div>
                  <div class="pend-reason">
                    <span class="pend-code">P03</span>
                    <span class="pend-desc">Coordination of benefits needed</span>
                  </div>
                  <div class="pend-reason">
                    <span class="pend-code">P04</span>
                    <span class="pend-desc">High dollar threshold exceeded</span>
                  </div>
                  <div class="pend-reason">
                    <span class="pend-code">P05</span>
                    <span class="pend-desc">Clinical review required</span>
                  </div>
                  <div class="pend-reason">
                    <span class="pend-code">P06</span>
                    <span class="pend-desc">Provider credentialing issue</span>
                  </div>
                </div>

                <h5>Reviewer Actions</h5>
                <ul class="action-list">
                  <li>
                    <i class="pi pi-check action-approve"></i>
                    <strong>Approve:</strong> Claim meets all requirements, process for payment
                  </li>
                  <li>
                    <i class="pi pi-times action-deny"></i>
                    <strong>Deny:</strong> Claim does not meet coverage criteria
                  </li>
                  <li>
                    <i class="pi pi-pencil action-adjust"></i>
                    <strong>Adjust:</strong> Modify payment amount with explanation
                  </li>
                  <li>
                    <i class="pi pi-envelope action-request"></i>
                    <strong>Request Info:</strong> Request additional documentation
                  </li>
                  <li>
                    <i class="pi pi-arrow-up action-escalate"></i>
                    <strong>Escalate:</strong> Send to supervisor for complex cases
                  </li>
                </ul>
              </div>
            </div>
          </p-tabPanel>

          <!-- Adjudication Stage -->
          <p-tabPanel header="4. Adjudication">
            <div class="stage-detail">
              <div class="stage-header">
                <div class="stage-icon adjudication">
                  <i class="pi pi-check-square"></i>
                </div>
                <div>
                  <h4>Final Adjudication</h4>
                  <p-tag value="Decision Made" severity="success"></p-tag>
                </div>
              </div>

              <div class="stage-content">
                <h5>Overview</h5>
                <p>
                  The final adjudication stage represents the conclusion of claims processing.
                  At this point, a definitive decision has been made and the claim is ready
                  for payment or denial notification.
                </p>

                <h5>Final Statuses</h5>
                <div class="status-grid">
                  <div class="status-card approved">
                    <div class="status-icon">
                      <i class="pi pi-check-circle"></i>
                    </div>
                    <div class="status-info">
                      <h6>Approved</h6>
                      <p>Claim approved for payment. Payment will be issued to provider or member based on assignment.</p>
                    </div>
                  </div>
                  <div class="status-card denied">
                    <div class="status-icon">
                      <i class="pi pi-times-circle"></i>
                    </div>
                    <div class="status-info">
                      <h6>Denied</h6>
                      <p>Claim denied with reason codes. Member and provider notified of appeal rights.</p>
                    </div>
                  </div>
                  <div class="status-card partial">
                    <div class="status-icon">
                      <i class="pi pi-minus-circle"></i>
                    </div>
                    <div class="status-info">
                      <h6>Partial Payment</h6>
                      <p>Some services approved, others denied. Detailed EOB provided.</p>
                    </div>
                  </div>
                </div>

                <h5>Post-Adjudication</h5>
                <ul class="post-adj-list">
                  <li><strong>EOB Generation:</strong> Explanation of Benefits sent to member</li>
                  <li><strong>ERA/835:</strong> Electronic remittance advice sent to provider</li>
                  <li><strong>Payment Issue:</strong> Check or EFT processed</li>
                  <li><strong>Appeal Window:</strong> 180-day appeal period begins</li>
                </ul>
              </div>
            </div>
          </p-tabPanel>
        </p-tabView>
      </section>

      <!-- Claim Statuses Reference -->
      <section class="statuses-section">
        <h3>Claim Status Reference</h3>
        <div class="status-table">
          <div class="table-header">
            <span>Status</span>
            <span>Description</span>
          </div>
          @for (status of claimStatuses; track status.code) {
            <div class="table-row">
              <span class="status-badge">
                <p-tag [value]="status.label" [severity]="status.color"></p-tag>
              </span>
              <span class="status-desc">{{ status.description }}</span>
            </div>
          }
        </div>
      </section>

      <!-- Timing Guidelines -->
      <section class="timing-section">
        <h3>Processing Timelines</h3>
        <div class="timeline-cards">
          <div class="timeline-card">
            <div class="timeline-value">24h</div>
            <div class="timeline-label">Initial Validation</div>
            <p>Claims are validated and acknowledged within 24 hours of receipt</p>
          </div>
          <div class="timeline-card">
            <div class="timeline-value">3-5 Days</div>
            <div class="timeline-label">Auto-Adjudication</div>
            <p>Clean claims processed automatically within 3-5 business days</p>
          </div>
          <div class="timeline-card">
            <div class="timeline-value">15 Days</div>
            <div class="timeline-label">Manual Review</div>
            <p>Pended claims reviewed within 15 business days</p>
          </div>
          <div class="timeline-card">
            <div class="timeline-value">30 Days</div>
            <div class="timeline-label">Payment Issue</div>
            <p>Payment issued within 30 days of clean claim receipt</p>
          </div>
        </div>
      </section>
    </div>
  `,
  styles: [`
    .workflow-guide {
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

    /* Workflow Diagram */
    .workflow-diagram {
      background: #f8f9fa;
      border-radius: 10px;
      padding: 2rem;
      border: 1px solid #e9ecef;
    }

    .workflow-row {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 0.5rem;
      flex-wrap: wrap;
    }

    .workflow-node {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .node-icon {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #17a2b8;
      color: white;
    }

    .node-icon i {
      font-size: 1.5rem;
    }

    .node-label {
      font-weight: 500;
      color: #343a40;
      min-width: 80px;
    }

    .node-arrow {
      color: #adb5bd;
      margin: 0 0.5rem;
    }

    .workflow-legend {
      display: flex;
      justify-content: center;
      gap: 2rem;
      margin-top: 1.5rem;
      padding-top: 1rem;
      border-top: 1px solid #e9ecef;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.85rem;
      color: #6c757d;
    }

    .legend-color {
      width: 12px;
      height: 12px;
      border-radius: 50%;
    }

    .legend-color.pending { background: #ffc107; }
    .legend-color.processing { background: #17a2b8; }
    .legend-color.completed { background: #28a745; }

    /* Stage Details */
    .stage-detail {
      padding: 1rem 0;
    }

    .stage-header {
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    .stage-icon {
      width: 50px;
      height: 50px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
    }

    .stage-icon.submission { background: #0066cc; }
    .stage-icon.processing { background: #ffc107; color: #343a40; }
    .stage-icon.review { background: #6c757d; }
    .stage-icon.adjudication { background: #28a745; }

    .stage-icon i {
      font-size: 1.5rem;
    }

    .stage-header h4 {
      margin: 0 0 0.25rem;
      color: #343a40;
    }

    .stage-content h5 {
      color: #495057;
      margin: 1.5rem 0 1rem;
      font-size: 1rem;
    }

    .stage-content p {
      color: #6c757d;
      line-height: 1.6;
    }

    /* Info Grid */
    .info-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
    }

    .info-card {
      background: #f8f9fa;
      padding: 1rem;
      border-radius: 8px;
      border-left: 3px solid #17a2b8;
    }

    .info-card h6 {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin: 0 0 0.75rem;
      color: #343a40;
    }

    .info-card ul {
      margin: 0;
      padding-left: 1.25rem;
    }

    .info-card li {
      margin-bottom: 0.25rem;
      color: #6c757d;
      font-size: 0.9rem;
    }

    /* Validation List */
    .validation-list {
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 0.5rem;
    }

    .validation-list li {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem;
      background: #d4edda;
      border-radius: 4px;
      color: #155724;
      font-size: 0.9rem;
    }

    /* Rules Grid */
    .rules-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1rem;
    }

    .rule-card {
      display: flex;
      gap: 1rem;
      padding: 1rem;
      background: #f8f9fa;
      border-radius: 8px;
    }

    .rule-number {
      width: 30px;
      height: 30px;
      background: #17a2b8;
      color: white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      flex-shrink: 0;
    }

    .rule-content h6 {
      margin: 0 0 0.25rem;
      color: #343a40;
    }

    .rule-content p {
      margin: 0;
      font-size: 0.9rem;
    }

    /* Outcomes Grid */
    .outcomes-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
    }

    .outcome {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      padding: 1.25rem;
      border-radius: 8px;
    }

    .outcome i {
      font-size: 2rem;
      margin-bottom: 0.5rem;
    }

    .outcome span {
      font-weight: 600;
      margin-bottom: 0.25rem;
    }

    .outcome small {
      color: #6c757d;
      font-size: 0.85rem;
    }

    .outcome.auto-approved {
      background: #d4edda;
      color: #155724;
    }

    .outcome.pended {
      background: #fff3cd;
      color: #856404;
    }

    .outcome.auto-denied {
      background: #f8d7da;
      color: #721c24;
    }

    /* Pend Reasons */
    .pend-reasons {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 0.75rem;
    }

    .pend-reason {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem;
      background: #fff3cd;
      border-radius: 6px;
    }

    .pend-code {
      background: #856404;
      color: white;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-family: monospace;
      font-weight: 600;
    }

    .pend-desc {
      color: #856404;
      font-size: 0.9rem;
    }

    /* Action List */
    .action-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }

    .action-list li {
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
      padding: 0.75rem 0;
      border-bottom: 1px solid #e9ecef;
    }

    .action-list li:last-child {
      border-bottom: none;
    }

    .action-list i {
      font-size: 1.25rem;
      margin-top: 0.1rem;
    }

    .action-approve { color: #28a745; }
    .action-deny { color: #dc3545; }
    .action-adjust { color: #ffc107; }
    .action-request { color: #17a2b8; }
    .action-escalate { color: #6f42c1; }

    /* Status Grid */
    .status-grid {
      display: grid;
      gap: 1rem;
    }

    .status-card {
      display: flex;
      gap: 1rem;
      padding: 1rem;
      border-radius: 8px;
      border-left: 4px solid;
    }

    .status-card.approved {
      background: #d4edda;
      border-color: #28a745;
    }

    .status-card.denied {
      background: #f8d7da;
      border-color: #dc3545;
    }

    .status-card.partial {
      background: #fff3cd;
      border-color: #ffc107;
    }

    .status-icon i {
      font-size: 1.5rem;
    }

    .status-card.approved .status-icon { color: #28a745; }
    .status-card.denied .status-icon { color: #dc3545; }
    .status-card.partial .status-icon { color: #ffc107; }

    .status-info h6 {
      margin: 0 0 0.25rem;
      color: #343a40;
    }

    .status-info p {
      margin: 0;
      font-size: 0.9rem;
    }

    /* Post Adjudication */
    .post-adj-list {
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 0.75rem;
    }

    .post-adj-list li {
      padding: 0.75rem;
      background: #e8f4f8;
      border-radius: 6px;
      font-size: 0.9rem;
    }

    /* Status Table */
    .status-table {
      background: #f8f9fa;
      border-radius: 8px;
      overflow: hidden;
    }

    .table-header {
      display: grid;
      grid-template-columns: 150px 1fr;
      gap: 1rem;
      padding: 1rem;
      background: #e9ecef;
      font-weight: 600;
      color: #343a40;
    }

    .table-row {
      display: grid;
      grid-template-columns: 150px 1fr;
      gap: 1rem;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid #e9ecef;
      align-items: center;
    }

    .table-row:last-child {
      border-bottom: none;
    }

    .status-desc {
      color: #6c757d;
      font-size: 0.9rem;
    }

    /* Timeline Cards */
    .timeline-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.25rem;
    }

    .timeline-card {
      background: #f8f9fa;
      padding: 1.5rem;
      border-radius: 10px;
      text-align: center;
      border: 1px solid #e9ecef;
    }

    .timeline-value {
      font-size: 2rem;
      font-weight: 700;
      color: #17a2b8;
      margin-bottom: 0.25rem;
    }

    .timeline-label {
      font-weight: 600;
      color: #343a40;
      margin-bottom: 0.5rem;
    }

    .timeline-card p {
      margin: 0;
      font-size: 0.9rem;
      color: #6c757d;
    }

    @media (max-width: 768px) {
      .outcomes-grid {
        grid-template-columns: 1fr;
      }

      .table-header,
      .table-row {
        grid-template-columns: 1fr;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkflowGuideComponent {
  readonly mainWorkflowStages = [
    { status: 'submitted', label: 'Submitted', icon: 'pi-file-plus' },
    { status: 'processing', label: 'Processing', icon: 'pi-cog' },
    { status: 'review', label: 'Review', icon: 'pi-eye' },
    { status: 'adjudicated', label: 'Adjudicated', icon: 'pi-check-square' },
  ];

  readonly claimStatuses: ClaimStatus[] = [
    { code: 'SUBMITTED', label: 'Submitted', description: 'Claim received and awaiting initial processing', color: 'info' },
    { code: 'VALIDATING', label: 'Validating', description: 'Claim is being validated for required information', color: 'info' },
    { code: 'PROCESSING', label: 'Processing', description: 'Claim is being processed through adjudication rules', color: 'warning' },
    { code: 'PENDED', label: 'Pended', description: 'Claim requires manual review or additional information', color: 'warning' },
    { code: 'IN_REVIEW', label: 'In Review', description: 'Claim is being reviewed by a claims examiner', color: 'secondary' },
    { code: 'APPROVED', label: 'Approved', description: 'Claim approved and scheduled for payment', color: 'success' },
    { code: 'DENIED', label: 'Denied', description: 'Claim denied - see denial reason codes', color: 'danger' },
    { code: 'PAID', label: 'Paid', description: 'Payment has been issued', color: 'success' },
    { code: 'APPEALED', label: 'Appealed', description: 'Provider or member has filed an appeal', color: 'warning' },
  ];
}
