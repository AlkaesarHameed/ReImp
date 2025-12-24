/**
 * Claim Submit Wizard Component.
 * Source: Phase 3 Implementation Document
 * Source: Design Document Section 3.4
 * Source: Design Document - 02_enhanced_claims_input_design.md
 * Source: Design Document 10 - Visual Extraction Display
 * Verified: 2025-12-24
 *
 * Multi-step wizard for claim submission with document upload and processing.
 * Orchestrates Upload, Visual Extraction, Processing, Preview, Review, and Submit steps.
 *
 * 6-Step Flow:
 * 0. Upload Documents
 * 1. Visual Extraction Display (NEW - source-faithful OCR visualization)
 * 2. Processing (OCR + LLM parsing)
 * 3. Preview Extraction (structured data cards)
 * 4. Review Data
 * 5. Submit
 */
import {
  Component,
  ChangeDetectionStrategy,
  signal,
  OnInit,
  OnDestroy,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { StepsModule } from 'primeng/steps';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ToastModule } from 'primeng/toast';
import { ConfirmationService, MessageService, MenuItem } from 'primeng/api';
import { Subject } from 'rxjs';

import {
  ClaimFormState,
  MemberStepData,
  ProviderStepData,
  ServicesStepData,
  DocumentUploadState,
  MergedExtractedData,
  createInitialClaimFormState,
} from '@claims-processing/models';
import { InterfaceSwitcherService } from '../../../../core/services/interface-switcher.service';

import { PolicyDocsStepData } from './step-policy-docs/step-policy-docs.component';
import { StepClaimDocsComponent, ClaimDocsStepData } from './step-claim-docs/step-claim-docs.component';
import { StepVisualExtractionComponent, QuickExtractionResponse } from './step-visual-extraction/step-visual-extraction.component';
import { StepProcessingComponent, ProcessingStepData } from './step-processing/step-processing.component';
import { StepPreviewExtractionComponent } from './step-preview-extraction/step-preview-extraction.component';
import { StepReviewComponent } from './step-review/step-review.component';

/**
 * Extended claim form state with document processing data.
 * Updated to include visual extraction result for the new step.
 */
interface EnhancedClaimFormState extends ClaimFormState {
  policyDocuments: DocumentUploadState[];
  claimDocuments: DocumentUploadState[];
  mergedExtractedData: MergedExtractedData | null;
  policyDocsSkipped: boolean;
  /** Visual extraction result from quick-extract endpoint */
  visualExtractionResult: QuickExtractionResponse | null;
}

@Component({
  selector: 'app-claim-submit',
  standalone: true,
  imports: [
    CommonModule,
    StepsModule,
    CardModule,
    ButtonModule,
    ConfirmDialogModule,
    ToastModule,
    StepClaimDocsComponent,
    StepVisualExtractionComponent,
    StepProcessingComponent,
    StepPreviewExtractionComponent,
    StepReviewComponent,
  ],
  providers: [ConfirmationService, MessageService],
  template: `
    <div class="claim-submit-wizard">
      <p-toast></p-toast>
      <p-confirmDialog></p-confirmDialog>

      <!-- Header -->
      <div class="wizard-header">
        <h2>New Claim Submission</h2>
        <button
          pButton
          type="button"
          label="Cancel"
          icon="pi pi-times"
          class="p-button-text"
          (click)="onCancel()"
        ></button>
      </div>

      <!-- Steps Indicator -->
      <p-steps
        [model]="steps"
        [activeIndex]="currentStep()"
        [readonly]="false"
        (activeIndexChange)="onStepClick($event)"
        styleClass="wizard-steps"
      ></p-steps>

      <!-- Step Content - New 6-step flow with Visual Extraction step -->
      <!-- Source: Design Doc 10 - Visual Extraction Display -->
      <div class="wizard-content">
        @switch (currentStep()) {
          @case (0) {
            <!-- Step 0: Upload Documents (combining all document uploads) -->
            <app-step-claim-docs
              [initialData]="getClaimDocsData()"
              (stepComplete)="onDocumentsComplete($event)"
              (stepBack)="goBack()"
              (dirty)="onDirtyChange($event)"
            />
          }
          @case (1) {
            <!-- Step 1: Visual Extraction Display - Source-faithful OCR visualization -->
            <app-step-visual-extraction
              [documents]="enhancedFormState().claimDocuments"
              (stepComplete)="onVisualExtractionComplete($event)"
              (stepBack)="goBack()"
            />
          }
          @case (2) {
            <!-- Step 2: Processing - Auto-extraction of data from documents -->
            <app-step-processing
              [policyDocuments]="enhancedFormState().policyDocuments"
              [claimDocuments]="enhancedFormState().claimDocuments"
              (stepComplete)="onProcessingComplete($event)"
              (stepBack)="goBack()"
            />
          }
          @case (3) {
            <!-- Step 3: Preview Extraction - Read-only view of extracted data -->
            <app-step-preview-extraction
              [mergedExtractedData]="enhancedFormState().mergedExtractedData"
              [policyDocuments]="enhancedFormState().policyDocuments"
              [claimDocuments]="enhancedFormState().claimDocuments"
              (stepComplete)="onPreviewComplete()"
              (stepBack)="goBack()"
            />
          }
          @case (4) {
            <!-- Step 4: Review Data - Edit auto-populated fields (member, provider, services all in one) -->
            <app-step-review
              [formState]="formState()"
              [enhancedFormState]="enhancedFormState()"
              [editMode]="true"
              (stepBack)="goBack()"
              (editStepRequest)="goToStep($event)"
              (dataUpdated)="onDataUpdated($event)"
              (proceedToSubmit)="onProceedToSubmit()"
            />
          }
          @case (5) {
            <!-- Step 5: Submit - Confirmation and final submission -->
            <app-step-review
              [formState]="formState()"
              [enhancedFormState]="enhancedFormState()"
              [editMode]="false"
              (stepBack)="goBack()"
              (submitSuccess)="onSubmitSuccess($event)"
              (draftSaved)="onDraftSaved($event)"
            />
          }
        }
      </div>

      <!-- Draft indicator -->
      @if (isDirty()) {
        <div class="draft-indicator">
          <i class="pi pi-exclamation-circle"></i>
          Unsaved changes
        </div>
      }
    </div>
  `,
  styles: [`
    .claim-submit-wizard {
      padding: 1.5rem;
      background: #f8f9fa;
      min-height: 100vh;
    }

    .wizard-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }

    .wizard-header h2 {
      margin: 0;
      color: #343a40;
    }

    :host ::ng-deep .wizard-steps {
      margin-bottom: 2rem;
    }

    :host ::ng-deep .wizard-steps .p-steps-item {
      flex: 1;
    }

    :host ::ng-deep .wizard-steps .p-steps-item .p-menuitem-link {
      flex-direction: column;
      gap: 0.5rem;
    }

    .wizard-content {
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      padding: 1.5rem;
      min-height: 500px;
    }

    .draft-indicator {
      position: fixed;
      bottom: 1rem;
      left: 1rem;
      background: #fff3cd;
      color: #856404;
      padding: 0.5rem 1rem;
      border-radius: 4px;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.85rem;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClaimSubmitComponent implements OnInit, OnDestroy {
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly messageService = inject(MessageService);
  private readonly interfaceSwitcher = inject(InterfaceSwitcherService);
  private readonly destroy$ = new Subject<void>();

  /**
   * 6-step wizard flow with Visual Extraction step:
   * 0. Upload Documents - Start with document upload (medical records, invoices)
   * 1. Visual Extraction - Source-faithful OCR visualization with bounding boxes
   * 2. Processing - LLM-based extraction of structured data
   * 3. Preview Extraction - Read-only view of extracted data with confidence scores
   * 4. Review Data - Show all auto-populated data, allow edits
   * 5. Submit - Final review and submission
   *
   * Source: Design Doc 10 - Visual Extraction Display
   * The Visual Extraction step displays OCR data in document layout format
   * before structured processing occurs.
   */
  readonly steps: MenuItem[] = [
    { label: 'Upload Documents', icon: 'pi pi-upload' },
    { label: 'Visual Extraction', icon: 'pi pi-image' },
    { label: 'Processing', icon: 'pi pi-cog' },
    { label: 'Preview Extraction', icon: 'pi pi-eye' },
    { label: 'Review Data', icon: 'pi pi-pencil' },
    { label: 'Submit', icon: 'pi pi-check-square' },
  ];

  readonly currentStep = signal<number>(0);
  readonly formState = signal<ClaimFormState>(createInitialClaimFormState());
  readonly enhancedFormState = signal<EnhancedClaimFormState>({
    ...createInitialClaimFormState(),
    policyDocuments: [],
    claimDocuments: [],
    mergedExtractedData: null,
    policyDocsSkipped: false,
    visualExtractionResult: null,
  });
  readonly isDirty = signal<boolean>(false);
  readonly completedSteps = signal<Set<number>>(new Set());

  ngOnInit(): void {
    // Check for draft ID in route params
    const draftId = this.route.snapshot.params['draftId'];
    if (draftId) {
      this.loadDraft(draftId);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadDraft(draftId: string): void {
    // Would load draft from backend
    console.log('Loading draft:', draftId);
  }

  onStepClick(stepIndex: number): void {
    // Only allow clicking on completed steps or current step
    if (stepIndex <= this.getMaxAllowedStep()) {
      this.currentStep.set(stepIndex);
    }
  }

  private getMaxAllowedStep(): number {
    // Can go to any step that's been completed, plus the next one
    const completed = Array.from(this.completedSteps());
    if (completed.length === 0) return 0;
    return Math.max(...completed) + 1;
  }

  /**
   * Step 0: Documents uploaded - proceed to Visual Extraction.
   * Source: Design Doc 10 - Visual Extraction Display
   */
  onDocumentsComplete(data: ClaimDocsStepData): void {
    this.enhancedFormState.update(state => ({
      ...state,
      claimDocuments: data.documents,
    }));
    this.completedSteps.update(set => new Set([...set, 0]));
    this.currentStep.set(1); // Go to Visual Extraction
  }

  /**
   * Step 1: Visual Extraction complete - proceed to Processing.
   * Source: Design Doc 10 - Visual Extraction Display
   * Stores the quick extraction result for potential future use.
   */
  onVisualExtractionComplete(result: QuickExtractionResponse): void {
    this.enhancedFormState.update(state => ({
      ...state,
      visualExtractionResult: result,
    }));
    this.completedSteps.update(set => new Set([...set, 1]));
    this.currentStep.set(2); // Go to Processing
  }

  /**
   * Step 2: Processing complete - auto-populate all fields and proceed to Preview.
   * This auto-populates member, provider, and services data from extraction.
   */
  onProcessingComplete(data: ProcessingStepData): void {
    const mergedData = data.mergedData;

    // Auto-populate member data from extraction (if available)
    const memberData: MemberStepData = {
      memberId: mergedData?.patient?.member_id || '',
      policyId: '',
      eligibilityVerified: false, // Will be verified later if needed
      eligibilityResponse: undefined,
    };

    // Auto-populate provider data from extraction (if available)
    const providerData: ProviderStepData = {
      providerId: '',
      providerNPI: mergedData?.provider?.npi || '',
      placeOfService: '11', // Default to Office
      priorAuthNumber: '',
      referringProviderId: '',
    };

    // Auto-populate services data from extraction (if available)
    const today = new Date().toISOString().split('T')[0];

    // Build line items from both procedures AND invoice line_items
    const procedureLineItems = (mergedData?.procedures || []).map(p => ({
      procedureCode: p.code || p.description?.substring(0, 20) || '',
      procedureCodeSystem: 'CPT' as const,
      modifiers: p.modifiers || [],
      serviceDate: p.service_date || today,
      quantity: p.quantity || 1,
      unitPrice: parseFloat(p.charged_amount || '0') || 0,
      chargedAmount: parseFloat(p.charged_amount || '0') || 0,
      diagnosisPointers: [1],
      description: p.description || '',
    }));

    // Invoice line items (for hospital bills, invoices with itemized charges)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const invoiceLineItems = ((mergedData as any)?.line_items || []).map((item: any) => ({
      procedureCode: item.sac_code || item.description?.substring(0, 20) || '',
      procedureCodeSystem: 'SAC' as const, // SAC code for services
      modifiers: [],
      serviceDate: item.date || today,
      quantity: item.quantity || 1,
      unitPrice: parseFloat(item.rate || item.total_value || '0') || 0,
      chargedAmount: parseFloat(item.total_value || '0') || 0,
      diagnosisPointers: [1],
      description: item.description || '',
      category: item.category || '',
      grossValue: parseFloat(item.gross_value || '0') || 0,
      discount: parseFloat(item.discount || '0') || 0,
    }));

    // Combine both types, prefer invoice line items if present
    const allLineItems = invoiceLineItems.length > 0 ? invoiceLineItems : procedureLineItems;

    const servicesData: ServicesStepData = {
      serviceDateFrom: mergedData?.dates?.service_date_from || today,
      serviceDateTo: mergedData?.dates?.service_date_to || today,
      primaryDiagnosis: mergedData?.diagnoses?.[0]?.code || '',
      diagnosisCodes: mergedData?.diagnoses?.map(d => d.code) || [],
      lineItems: allLineItems,
    };

    this.enhancedFormState.update(state => ({
      ...state,
      policyDocuments: data.policyDocuments,
      claimDocuments: data.claimDocuments,
      mergedExtractedData: mergedData,
    }));

    this.formState.update(state => ({
      ...state,
      member: memberData,
      provider: providerData,
      services: servicesData,
    }));

    this.completedSteps.update(set => new Set([...set, 2]));
    this.currentStep.set(3); // Go to Preview Extraction
  }

  /**
   * Step 3: Preview complete - proceed to review.
   * Source: Design Doc 08 - Preview step is read-only.
   */
  onPreviewComplete(): void {
    this.completedSteps.update(set => new Set([...set, 3]));
    this.currentStep.set(4); // Go to Review Data
  }

  /**
   * Step 4: Data updated in review step.
   * User can edit any auto-populated fields here.
   */
  onDataUpdated(data: {
    member?: MemberStepData;
    provider?: ProviderStepData;
    services?: ServicesStepData;
  }): void {
    if (data.member) {
      this.formState.update(state => ({ ...state, member: data.member! }));
      this.enhancedFormState.update(state => ({ ...state, member: data.member! }));
    }
    if (data.provider) {
      this.formState.update(state => ({ ...state, provider: data.provider! }));
      this.enhancedFormState.update(state => ({ ...state, provider: data.provider! }));
    }
    if (data.services) {
      this.formState.update(state => ({ ...state, services: data.services! }));
      this.enhancedFormState.update(state => ({ ...state, services: data.services! }));
    }
  }

  /**
   * Step 4 -> Step 5: User confirmed review data, proceed to final submission.
   */
  onProceedToSubmit(): void {
    this.completedSteps.update(set => new Set([...set, 4]));
    this.currentStep.set(5); // Go to Submit
  }

  // Legacy handlers kept for backward compatibility
  onMemberComplete(data: MemberStepData): void {
    this.formState.update(state => ({ ...state, member: data }));
    this.enhancedFormState.update(state => ({ ...state, member: data }));
  }

  onProviderComplete(data: ProviderStepData): void {
    this.formState.update(state => ({ ...state, provider: data }));
    this.enhancedFormState.update(state => ({ ...state, provider: data }));
  }

  onServicesComplete(data: ServicesStepData): void {
    this.formState.update(state => ({ ...state, services: data }));
    this.enhancedFormState.update(state => ({ ...state, services: data }));
  }

  /**
   * Get policy docs data for initial state.
   */
  getPolicyDocsData(): PolicyDocsStepData | undefined {
    const state = this.enhancedFormState();
    if (state.policyDocuments.length > 0 || state.policyDocsSkipped) {
      return {
        documents: state.policyDocuments,
        skipped: state.policyDocsSkipped,
      };
    }
    return undefined;
  }

  /**
   * Get claim docs data for initial state.
   */
  getClaimDocsData(): ClaimDocsStepData | undefined {
    const state = this.enhancedFormState();
    if (state.claimDocuments.length > 0) {
      return {
        documents: state.claimDocuments,
      };
    }
    return undefined;
  }

  goBack(): void {
    if (this.currentStep() > 0) {
      this.currentStep.update(step => step - 1);
    }
  }

  goToStep(stepIndex: number): void {
    this.currentStep.set(stepIndex);
  }

  onDirtyChange(dirty: boolean): void {
    this.isDirty.set(dirty);
  }

  onSubmitSuccess(claimId: string): void {
    this.messageService.add({
      severity: 'success',
      summary: 'Claim Submitted',
      detail: `Claim ${claimId} has been submitted successfully.`,
      life: 5000,
    });

    // Navigate to claims list using current interface path
    const basePath = this.interfaceSwitcher.getCurrentBasePath();
    setTimeout(() => {
      this.router.navigate([`${basePath}/claims`]);
    }, 1500);
  }

  onDraftSaved(draftId: string): void {
    console.log('Draft saved event received:', draftId);
    this.messageService.add({
      severity: 'success',
      summary: 'Draft Saved',
      detail: 'Your claim draft has been saved successfully.',
      life: 5000,
    });
    this.isDirty.set(false);
    this.formState.update(state => ({ ...state, draftId }));
  }

  onCancel(): void {
    const basePath = this.interfaceSwitcher.getCurrentBasePath();
    if (this.isDirty()) {
      this.confirmationService.confirm({
        message: 'You have unsaved changes. Are you sure you want to cancel?',
        header: 'Confirm Cancel',
        icon: 'pi pi-exclamation-triangle',
        accept: () => {
          this.router.navigate([`${basePath}/claims`]);
        },
      });
    } else {
      this.router.navigate([`${basePath}/claims`]);
    }
  }
}
