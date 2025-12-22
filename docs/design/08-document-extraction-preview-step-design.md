# Design Document: Document Extraction Preview Step

**Feature:** Document Extraction Preview Step in Claim Submission Wizard
**Version:** 1.0
**Date:** December 21, 2025
**Author:** Architecture Team
**Status:** DRAFT - Pending Approval

---

## 1. Executive Summary

### Overview

This design document specifies the addition of a **Preview** step to the claim submission wizard, positioned after document processing. This step allows users to review all extracted data from uploaded documents in both summary and detailed views before proceeding to edit or submit the claim.

The feature enhances user experience by providing transparency into what was extracted from documents, enabling users to:
1. Verify extraction accuracy before proceeding
2. Identify missing or incorrect information early
3. Understand confidence levels of extracted data
4. Review document-by-document extraction results

### Current vs Proposed Flow

```
CURRENT 4-STEP FLOW:
[Upload Documents] -> [Processing] -> [Review Data] -> [Submit]

PROPOSED 5-STEP FLOW:
[Upload Documents] -> [Processing] -> [Preview Extraction] -> [Review Data] -> [Submit]
                                              ^
                                              |
                                      NEW STEP
```

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Step Position | After Processing, Before Review | Natural flow - see what was extracted before editing |
| View Modes | Summary + Detailed tabs | Summary for quick overview, detailed for verification |
| Navigation | Can skip to Review or go back | Flexible user control |
| Data Display | Read-only with edit link | Preview only, editing happens in Review step |
| Confidence Display | Color-coded thresholds | Visual indication of extraction reliability |

### Success Criteria

- Users can view all extracted data before editing
- Summary view loads within 500ms of processing completion
- Detailed view shows extraction source and confidence per field
- Users can navigate back to re-upload or forward to review
- Zero additional API calls required (uses processing step data)

---

## 2. Requirements Specification

### 2.1 Business Objectives

| ID | Objective | Priority |
|----|-----------|----------|
| BO-1 | Display all extracted data in organized summary view | MUST |
| BO-2 | Provide detailed view with field-level extraction info | MUST |
| BO-3 | Show confidence scores for extracted fields | MUST |
| BO-4 | Allow users to proceed to review or go back | MUST |
| BO-5 | Highlight low-confidence extractions for attention | SHOULD |
| BO-6 | Show extraction source (OCR/LLM) per field | SHOULD |
| BO-7 | Display document thumbnails with extracted data mapping | COULD |

### 2.2 Functional Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-1 | Summary View | Display patient, provider, diagnoses, procedures, financial data in cards |
| FR-2 | Detailed View | Show all fields with confidence scores, source, and page reference |
| FR-3 | Confidence Indicators | Green (>80%), Yellow (50-80%), Red (<50%) color coding |
| FR-4 | Navigation Controls | "Back to Processing", "Edit in Review", "Skip to Review" buttons |
| FR-5 | Data Grouping | Group extracted data by category (Patient, Provider, Clinical, Financial) |
| FR-6 | Field Highlighting | Highlight fields requiring review (low confidence or missing) |
| FR-7 | Document Reference | Link extracted fields to source document page |
| FR-8 | Empty State | Show meaningful message when no data extracted |

### 2.3 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Load Time | < 500ms from processing completion |
| NFR-2 | Responsiveness | Mobile-friendly layout |
| NFR-3 | Accessibility | WCAG 2.1 AA compliance |
| NFR-4 | State Preservation | Data persists on back/forward navigation |
| NFR-5 | Memory Usage | < 50MB additional browser memory |

### 2.4 Constraints

| Type | Constraint |
|------|------------|
| Technical | Must integrate with existing Angular 19 + PrimeNG stack |
| Technical | Uses data already extracted in Processing step (no new API calls) |
| UX | Must not significantly increase wizard completion time |
| Design | Must follow existing healthcare theme and design system |

### 2.5 Assumptions

| ID | Assumption | Must Validate |
|----|------------|---------------|
| A-1 | Processing step returns complete MergedExtractedData | Yes - verified in code |
| A-2 | Confidence scores are available for all extracted fields | Yes - needs OCR pipeline fix |
| A-3 | Users want to see extraction preview before editing | Yes - user feedback |
| A-4 | Current processing step UI can transition to preview | Yes - architecture allows |

---

## 3. Architecture Design

### 3.1 Component Architecture

```
+------------------------------------------------------------------+
|                    ClaimSubmitComponent                           |
|                    (Wizard Orchestrator)                          |
+------------------------------------------------------------------+
     |          |           |            |            |
     v          v           v            v            v
+--------+ +--------+ +------------+ +--------+ +--------+
| Step   | | Step   | | Step       | | Step   | | Step   |
| Upload | | Process| | Preview    | | Review | | Submit |
| Docs   | | ing    | | Extraction | | Data   | |        |
+--------+ +--------+ +------------+ +--------+ +--------+
                            |
                            |
              +-------------+-------------+
              |                           |
              v                           v
      +---------------+          +----------------+
      | Preview       |          | Preview        |
      | Summary       |          | Detailed       |
      | Component     |          | Component      |
      +---------------+          +----------------+
              |                           |
              v                           v
      +---------------+          +----------------+
      | Extraction    |          | Field          |
      | Card          |          | Detail         |
      | Component     |          | Component      |
      +---------------+          +----------------+
```

### 3.2 Data Flow

```
Processing Step Completion:

+----------------+     +-------------------+     +------------------+
| ProcessingStep |---->| MergedExtracted   |---->| PreviewStep      |
| Component      |     | Data              |     | Component        |
+----------------+     +-------------------+     +------------------+
                              |
                              |
              +---------------+---------------+
              |               |               |
              v               v               v
      +-------------+  +-------------+  +-------------+
      | Patient     |  | Clinical    |  | Financial   |
      | Extraction  |  | Extraction  |  | Extraction  |
      | Card        |  | Card        |  | Card        |
      +-------------+  +-------------+  +-------------+


Preview to Review Transition:

+------------------+     +-------------------+     +------------------+
| PreviewStep      |---->| Preserved State   |---->| ReviewStep       |
| (Read-only)      |     | (No modification) |     | (Editable)       |
+------------------+     +-------------------+     +------------------+
```

### 3.3 Component Specifications

#### 3.3.1 StepPreviewExtractionComponent (New)

**Location:** `frontend/apps/claims-portal/src/app/features/claims/components/claim-submit/step-preview-extraction/`

**Files:**
- `step-preview-extraction.component.ts` - Main component
- `step-preview-extraction.component.html` - Template (inline or separate)
- `step-preview-extraction.component.scss` - Styles

**Inputs:**
```typescript
interface PreviewExtractionInputs {
  mergedExtractedData: MergedExtractedData | null;
  policyDocuments: DocumentUploadState[];
  claimDocuments: DocumentUploadState[];
  processingStats?: ProcessingStats;
}
```

**Outputs:**
```typescript
interface PreviewExtractionOutputs {
  stepComplete: EventEmitter<void>;  // Proceed to Review
  stepBack: EventEmitter<void>;      // Go back to Processing
  editRequest: EventEmitter<string>; // Request to edit specific section
}
```

#### 3.3.2 PreviewSummaryComponent (New)

**Purpose:** Display high-level summary of all extracted data in card format

**Template Structure:**
```html
<div class="preview-summary">
  <!-- Patient Information Card -->
  <p-card header="Patient Information" [style]="{...}">
    <div class="summary-row">
      <span class="label">Name:</span>
      <span class="value">{{ patient.name }}</span>
      <app-confidence-badge [score]="patient.name_confidence" />
    </div>
    <!-- More fields -->
  </p-card>

  <!-- Provider Information Card -->
  <p-card header="Provider Information">...</p-card>

  <!-- Clinical Data Card -->
  <p-card header="Diagnoses & Procedures">...</p-card>

  <!-- Financial Summary Card -->
  <p-card header="Financial Summary">...</p-card>
</div>
```

#### 3.3.3 PreviewDetailedComponent (New)

**Purpose:** Display detailed extraction with field-level metadata

**Features:**
- Expandable sections per category
- Field-level confidence scores
- Source document page reference
- Extraction method indicator (OCR/LLM/NER)
- Bounding box coordinates for source mapping

#### 3.3.4 ConfidenceBadgeComponent (New)

**Purpose:** Reusable confidence score indicator

```typescript
@Component({
  selector: 'app-confidence-badge',
  template: `
    <span class="confidence-badge" [ngClass]="confidenceClass">
      {{ score | percent:'1.0-0' }}
    </span>
  `
})
export class ConfidenceBadgeComponent {
  @Input() score: number = 0;

  get confidenceClass(): string {
    if (this.score >= 0.8) return 'confidence-high';
    if (this.score >= 0.5) return 'confidence-medium';
    return 'confidence-low';
  }
}
```

### 3.4 State Management

```
Wizard State with Preview Step:

enhancedFormState = {
  // Existing fields
  policyDocuments: DocumentUploadState[];
  claimDocuments: DocumentUploadState[];
  mergedExtractedData: MergedExtractedData | null;
  policyDocsSkipped: boolean;

  // New fields for preview
  previewViewed: boolean;           // Track if user viewed preview
  previewTimestamp: Date | null;    // When preview was viewed
  lowConfidenceFields: string[];    // Fields flagged for attention
}

Step Transitions:
[0: Upload] -> [1: Processing] -> [2: Preview] -> [3: Review] -> [4: Submit]
     |              |                  |              |              |
     v              v                  v              v              v
  (docs)      (extraction)       (read-only)    (editable)      (submit)
```

---

## 4. API Contracts

### 4.1 No New Backend APIs Required

The Preview step operates entirely on data already fetched during the Processing step. The `MergedExtractedData` interface already contains all necessary information.

### 4.2 Existing Data Structures Used

#### MergedExtractedData (from `@claims-processing/models`)

```typescript
interface MergedExtractedData {
  patient: {
    name: string;
    name_confidence?: number;
    date_of_birth: string;
    dob_confidence?: number;
    gender: string;
    gender_confidence?: number;
    member_id: string;
    member_id_confidence?: number;
    address?: string;
    phone?: string;
    // ... other patient fields
  };

  provider: {
    name: string;
    name_confidence?: number;
    npi: string;
    npi_confidence?: number;
    tax_id?: string;
    address?: string;
    specialty?: string;
    // ... other provider fields
  };

  diagnoses: Array<{
    code: string;
    code_confidence?: number;
    description: string;
    type: 'primary' | 'secondary' | 'admitting';
    source_page?: number;
  }>;

  procedures: Array<{
    code: string;
    code_confidence?: number;
    description: string;
    modifiers?: string[];
    quantity?: number;
    charge_amount?: number;
    source_page?: number;
  }>;

  financial: {
    total_charges?: number;
    total_charges_confidence?: number;
    total_payments?: number;
    amount_due?: number;
    insurance_paid?: number;
    patient_responsibility?: number;
    // ... other financial fields
  };

  dates: {
    service_date_from?: string;
    service_date_to?: string;
    admission_date?: string;
    discharge_date?: string;
    bill_date?: string;
  };

  extraction_metadata: {
    total_pages_processed: number;
    extraction_duration_ms: number;
    ocr_engine: string;
    llm_model?: string;
    overall_confidence: number;
  };
}
```

### 4.3 Future Enhancement: Field-Level Source API

For Phase 2, consider adding an endpoint to get field-level source information:

```http
GET /api/v1/documents/{document_id}/extraction/{field_path}

Response:
{
  "field_path": "patient.name",
  "extracted_value": "Mrs AMNA OBAID ALI ALZAABI",
  "confidence": 0.95,
  "source": {
    "document_id": "uuid",
    "page": 1,
    "bounding_box": {"x": 100, "y": 200, "width": 300, "height": 50},
    "extraction_method": "ocr+llm"
  },
  "alternatives": [
    {"value": "AMNA OBAID ALI", "confidence": 0.75}
  ]
}
```

---

## 5. Technology Stack

### 5.1 Frontend Technologies (Existing)

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | Angular | 19.x |
| UI Library | PrimeNG | 17.18.x |
| State | Angular Signals | Built-in |
| Styling | SCSS + PrimeNG Theme | - |
| Icons | PrimeIcons | Latest |

### 5.2 New Components/Modules

| Component | Purpose | Dependencies |
|-----------|---------|--------------|
| StepPreviewExtractionComponent | Main preview step | PrimeNG Card, TabView |
| PreviewSummaryComponent | Summary cards | PrimeNG Card, Tag |
| PreviewDetailedComponent | Detailed view | PrimeNG Accordion, Table |
| ConfidenceBadgeComponent | Score indicator | None (standalone) |
| ExtractionSourceIndicator | OCR/LLM badge | PrimeNG Tag |

### 5.3 No New Dependencies Required

All required functionality can be achieved with existing dependencies.

---

## 6. Security Design

### 6.1 Data Handling

| Aspect | Implementation |
|--------|----------------|
| PII Display | Same security as existing Review step |
| Data Transmission | No new API calls, data in memory only |
| Session Security | Relies on existing JWT authentication |
| Audit Trail | Log preview step access for compliance |

### 6.2 Access Control

- Preview step only accessible after successful document processing
- Same role requirements as claim submission workflow
- No additional permissions required

---

## 7. Performance Plan

### 7.1 Performance Targets

| Metric | Target |
|--------|--------|
| Preview load time | < 500ms |
| Memory footprint | < 50MB additional |
| DOM elements | < 500 for summary view |
| Rerender time | < 100ms |

### 7.2 Optimization Strategies

1. **Lazy Loading**: Preview components loaded only when step is reached
2. **Virtual Scrolling**: For detailed view with many fields
3. **Memoization**: Cache computed confidence classes
4. **OnPush Change Detection**: All preview components use OnPush

### 7.3 Performance Considerations

```typescript
// Use trackBy for ngFor loops
trackByFieldName(index: number, field: ExtractedField): string {
  return field.name;
}

// Memoize confidence calculations
private confidenceCache = new Map<number, string>();
getConfidenceClass(score: number): string {
  if (!this.confidenceCache.has(score)) {
    const cls = score >= 0.8 ? 'high' : score >= 0.5 ? 'medium' : 'low';
    this.confidenceCache.set(score, cls);
  }
  return this.confidenceCache.get(score)!;
}
```

---

## 8. Risk Register

| ID | Risk | Probability | Impact | Mitigation |
|----|------|-------------|--------|------------|
| R-1 | Users skip preview, miss errors | MEDIUM | MEDIUM | Add visual indicator for low-confidence fields |
| R-2 | Performance degradation with many fields | LOW | MEDIUM | Virtual scrolling, pagination |
| R-3 | Inconsistent confidence scores | MEDIUM | LOW | Standardize scoring in OCR pipeline |
| R-4 | Mobile layout issues | LOW | LOW | Responsive design testing |
| R-5 | State loss on browser refresh | MEDIUM | MEDIUM | Use session storage for state |

### Fallback Plans

| Risk | Fallback |
|------|----------|
| No extraction data | Show "No data extracted" with option to re-upload |
| Slow rendering | Progressive loading with skeleton UI |
| Missing confidence scores | Display "N/A" with tooltip explanation |

---

## 9. Implementation Roadmap

### Phase 1: Core Preview Step (MVP)

| Task | Description | Priority |
|------|-------------|----------|
| 1.1 | Create StepPreviewExtractionComponent scaffold | P0 |
| 1.2 | Implement summary view with patient/provider cards | P0 |
| 1.3 | Add confidence badge component | P0 |
| 1.4 | Integrate into wizard with step 2 position | P0 |
| 1.5 | Update wizard steps array (5 steps) | P0 |
| 1.6 | Add navigation controls (Back/Continue) | P0 |
| 1.7 | Style with healthcare theme | P0 |

**Deliverable:** Basic preview step with summary view

### Phase 2: Detailed View

| Task | Description | Priority |
|------|-------------|----------|
| 2.1 | Add TabView for Summary/Detailed toggle | P0 |
| 2.2 | Implement PreviewDetailedComponent | P0 |
| 2.3 | Add accordion sections per category | P1 |
| 2.4 | Display extraction source indicators | P1 |
| 2.5 | Add page reference links | P2 |

**Deliverable:** Full preview with summary and detailed views

### Phase 3: Enhanced Features

| Task | Description | Priority |
|------|-------------|----------|
| 3.1 | Add low-confidence field highlighting | P1 |
| 3.2 | Implement "Jump to Edit" functionality | P1 |
| 3.3 | Add document thumbnail sidebar | P2 |
| 3.4 | Implement field-to-document mapping UI | P2 |
| 3.5 | Add export extraction report feature | P3 |

**Deliverable:** Enhanced preview with advanced features

### Phase 4: Testing & Polish

| Task | Description | Priority |
|------|-------------|----------|
| 4.1 | Unit tests for preview components | P0 |
| 4.2 | E2E tests for wizard flow | P0 |
| 4.3 | Accessibility audit and fixes | P1 |
| 4.4 | Performance optimization | P1 |
| 4.5 | Mobile responsive testing | P1 |

**Deliverable:** Production-ready preview step

---

## 10. Open Questions

| ID | Question | Impact | Decision Needed By |
|----|----------|--------|-------------------|
| Q-1 | Should preview be skippable or mandatory? | MEDIUM | Phase 1 |
| Q-2 | Should we show document thumbnails in preview? | LOW | Phase 2 |
| Q-3 | How to handle documents with no extractable data? | MEDIUM | Phase 1 |
| Q-4 | Should we persist preview state across sessions? | LOW | Phase 3 |
| Q-5 | Should users be able to download extraction report? | LOW | Phase 3 |

---

## 11. UI Mockup

### 11.1 Summary View Layout

```
+------------------------------------------------------------------+
|  [< Back]                 Preview Extraction               [Skip >] |
+------------------------------------------------------------------+
|                                                                    |
|  Extraction Summary                Overall Confidence: 87%         |
|                                                                    |
|  +------------------------+  +------------------------+            |
|  | Patient Information    |  | Provider Information   |            |
|  |------------------------|  |------------------------|            |
|  | Name: Mrs AMNA...  95% |  | Name: Apollo Sp... 92% |            |
|  | DOB: 1985-03-15   88%  |  | NPI: 1234567890   85%  |            |
|  | Gender: Female    99%  |  | Specialty: Cardio 78%  |            |
|  | Member ID: ABC123 72%  |  | Address: 123 Main 90%  |            |
|  +------------------------+  +------------------------+            |
|                                                                    |
|  +------------------------+  +------------------------+            |
|  | Clinical Data          |  | Financial Summary      |            |
|  |------------------------|  |------------------------|            |
|  | Diagnoses: 3 found     |  | Total Charges: Rs. 2,0.|            |
|  | - I10 (Primary)   94%  |  | Discount: Rs. 21,452   |            |
|  | - E11.9          87%   |  | Amount Due: Rs. 1,80,0.|            |
|  | Procedures: 5 found    |  | Insurance: Pending     |            |
|  | - 99213          91%   |  |                        |            |
|  +------------------------+  +------------------------+            |
|                                                                    |
|  [!] 2 fields have low confidence and may need review              |
|                                                                    |
|  [Summary]  [Detailed View]                                        |
|                                                                    |
+------------------------------------------------------------------+
|                                                                    |
|  [ Back to Upload ]              [ Continue to Review > ]          |
|                                                                    |
+------------------------------------------------------------------+
```

### 11.2 Detailed View Layout

```
+------------------------------------------------------------------+
|  [Summary]  [Detailed View]                                        |
+------------------------------------------------------------------+
|                                                                    |
|  > Patient Information                                   [Expand]  |
|  +--------------------------------------------------------------+ |
|  | Field          | Value              | Conf. | Source | Page  | |
|  |----------------|--------------------+-------+--------+-------| |
|  | Full Name      | Mrs AMNA OBAID...  | 95%   | OCR+LLM| 1     | |
|  | Date of Birth  | 1985-03-15         | 88%   | LLM    | 1     | |
|  | Gender         | Female             | 99%   | OCR    | 1     | |
|  | Member ID      | ABC123             | 72%   | LLM    | 2     | |
|  +--------------------------------------------------------------+ |
|                                                                    |
|  > Provider Information                                  [Expand]  |
|  > Diagnoses (3)                                        [Expand]  |
|  > Procedures (5)                                       [Expand]  |
|  > Financial Data                                       [Expand]  |
|                                                                    |
+------------------------------------------------------------------+
```

---

## 12. Code Implementation Guide

### 12.1 Updated Wizard Steps

```typescript
// claim-submit.component.ts

readonly steps: MenuItem[] = [
  { label: 'Upload Documents', icon: 'pi pi-upload' },
  { label: 'Processing', icon: 'pi pi-cog' },
  { label: 'Preview Extraction', icon: 'pi pi-eye' },  // NEW
  { label: 'Review Data', icon: 'pi pi-pencil' },
  { label: 'Submit', icon: 'pi pi-check-square' },
];
```

### 12.2 Template Switch Statement Update

```typescript
@switch (currentStep()) {
  @case (0) {
    <app-step-claim-docs ... />
  }
  @case (1) {
    <app-step-processing ... />
  }
  @case (2) {
    <!-- NEW: Preview Extraction Step -->
    <app-step-preview-extraction
      [mergedExtractedData]="enhancedFormState().mergedExtractedData"
      [policyDocuments]="enhancedFormState().policyDocuments"
      [claimDocuments]="enhancedFormState().claimDocuments"
      (stepComplete)="onPreviewComplete()"
      (stepBack)="goBack()"
    />
  }
  @case (3) {
    <app-step-review [editMode]="true" ... />
  }
  @case (4) {
    <app-step-review [editMode]="false" ... />
  }
}
```

### 12.3 Preview Component Template

```typescript
// step-preview-extraction.component.ts

@Component({
  selector: 'app-step-preview-extraction',
  standalone: true,
  imports: [
    CommonModule,
    CardModule,
    TabViewModule,
    ButtonModule,
    TagModule,
    AccordionModule,
    TableModule,
    TooltipModule,
  ],
  template: `
    <div class="preview-step">
      <div class="preview-header">
        <h3>Extraction Preview</h3>
        <div class="overall-confidence">
          <span>Overall Confidence:</span>
          <app-confidence-badge
            [score]="extractedData?.extraction_metadata?.overall_confidence ?? 0"
          />
        </div>
      </div>

      <p-tabView [(activeIndex)]="activeTab">
        <p-tabPanel header="Summary">
          <app-preview-summary [data]="extractedData" />
        </p-tabPanel>
        <p-tabPanel header="Detailed View">
          <app-preview-detailed [data]="extractedData" />
        </p-tabPanel>
      </p-tabView>

      @if (lowConfidenceCount > 0) {
        <p-message
          severity="warn"
          [text]="lowConfidenceCount + ' fields have low confidence and may need review'"
        />
      }

      <div class="step-actions">
        <p-button
          label="Back to Processing"
          icon="pi pi-arrow-left"
          styleClass="p-button-outlined"
          (onClick)="stepBack.emit()"
        />
        <p-button
          label="Continue to Review"
          icon="pi pi-arrow-right"
          iconPos="right"
          (onClick)="stepComplete.emit()"
        />
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StepPreviewExtractionComponent {
  @Input() mergedExtractedData: MergedExtractedData | null = null;
  @Input() policyDocuments: DocumentUploadState[] = [];
  @Input() claimDocuments: DocumentUploadState[] = [];

  @Output() stepComplete = new EventEmitter<void>();
  @Output() stepBack = new EventEmitter<void>();

  activeTab = 0;

  get extractedData() {
    return this.mergedExtractedData;
  }

  get lowConfidenceCount(): number {
    // Count fields with confidence < 0.5
    return this.countLowConfidenceFields();
  }

  private countLowConfidenceFields(): number {
    if (!this.extractedData) return 0;
    let count = 0;
    // Check patient fields
    const patient = this.extractedData.patient;
    if (patient.name_confidence && patient.name_confidence < 0.5) count++;
    if (patient.dob_confidence && patient.dob_confidence < 0.5) count++;
    // ... more fields
    return count;
  }
}
```

---

## 13. Validation Rules Integration

### 13.1 Overview

The system has extensive validation rules organized across design documents 03, 04, and 05. The Preview step does NOT execute validation - it is read-only. This section provides a comprehensive cross-reference of all 19 designed rules with their implementation status.

### 13.2 Complete Validation Rules Matrix (19 Rules)

The following matrix shows all validation rules defined in design documents, cross-referenced with implementation:

| Rule # | Rule Name | Design Doc | Implementation File | Status |
|--------|-----------|------------|---------------------|--------|
| **Core Rules (Doc 03/04)** |
| Rule 1 | Policy Eligibility Check | 03, 04, 05 | `src/services/adjudication_validators.py` | ✅ Implemented |
| Rule 2 | Service Date Coverage | 03, 04, 05 | `src/services/claim_validation.py` | ✅ Implemented |
| Rule 3 | Provider Network Status | 03, 04, 05 | `src/services/adjudication_validators.py` | ✅ Implemented |
| Rule 4 | Prior Authorization Check | 03, 04, 05 | `src/services/adjudication_validators.py` | ✅ Implemented |
| Rule 5 | Claim Completeness | 03, 04, 05 | `src/services/claim_validation.py` | ✅ Implemented |
| Rule 6 | ICD-CPT Medical Crosswalk | 03, 04, 05 | `src/services/validation/icd_cpt_crosswalk.py` | ✅ Implemented |
| Rule 7 | NCCI Procedure-to-Procedure Edits | 03, 04, 05 | `src/services/validation/icd_cpt_crosswalk.py` | ✅ Implemented |
| Rule 8 | Medically Unlikely Edits (MUE) | 03, 04, 05 | `src/services/validation/icd_cpt_crosswalk.py` | ✅ Implemented |
| Rule 9 | Age/Gender Appropriateness | 03, 04, 05 | `src/services/validation/demographic_validator.py` | ✅ Implemented |
| Rule 10 | Diagnosis Conflict Detection | 03, 04, 05 | `src/services/validation/icd_conflict_validator.py` | ✅ Implemented |
| Rule 11 | Provider License/Scope Check | 03, 04, 05 | `src/services/adjudication_validators.py` | ✅ Implemented |
| Rule 12 | Timely Filing Check | 03, 04, 05 | `src/services/adjudication_validators.py` | ✅ Implemented |
| **Extended Rules (Doc 05)** |
| Rule 13 | Benefit Exhaustion Check | 05 | `src/services/adjudication_validators.py` | ✅ Implemented |
| Rule 14 | LCD Medical Necessity | 05 | `src/services/validation/clinical_necessity_validator.py` | ✅ Implemented |
| Rule 15 | NCD Medical Necessity | 05 | `src/services/validation/clinical_necessity_validator.py` | ✅ Implemented |
| Rule 16 | Duplicate Claim Detection | 05 | `src/services/fwa/duplicate_detector.py` | ✅ Implemented |
| Rule 17 | Upcoding Detection | 05 | `src/services/fwa/upcoding_detector.py` | ✅ Implemented |
| Rule 18 | Unbundling Detection | 05 | `src/services/fwa/upcoding_detector.py` | ✅ Implemented |
| Rule 19 | HCC Risk Validation | 05 | `src/services/validation/demographic_validator.py` | ✅ Implemented |

### 13.3 Validation Rules by Category

#### Category 1: Eligibility & Coverage (Rules 1-4, 13)
| Rule # | Rule Name | Description | Threshold/Logic |
|--------|-----------|-------------|-----------------|
| 1 | Policy Eligibility | Verify policy is active on service date | Policy status = "active" |
| 2 | Service Date Coverage | Ensure service dates within coverage period | Within policy effective dates |
| 3 | Provider Network Status | Check if provider is in-network | Network participation flag |
| 4 | Prior Authorization | Verify prior auth for high-cost/surgical CPTs | 15+ CPT codes require auth |
| 13 | Benefit Exhaustion | Check remaining benefit limits | Annual/lifetime limits |

#### Category 2: Claim Completeness (Rules 5, 12)
| Rule # | Rule Name | Description | Threshold/Logic |
|--------|-----------|-------------|-----------------|
| 5 | Claim Completeness | Validate required fields present | Member ID, provider NPI, dates, codes |
| 12 | Timely Filing | Check claim submitted within limits | 365 days (default), 90-180 days (some payers) |

#### Category 3: Medical Coding Validation (Rules 6-8)
| Rule # | Rule Name | Description | Threshold/Logic |
|--------|-----------|-------------|-----------------|
| 6 | ICD-CPT Crosswalk | Procedure code supports diagnosis | Clinical crosswalk database |
| 7 | NCCI PTP Edits | Column 1/2 bundling rules | CMS NCCI edits table |
| 8 | MUE Limits | Units per service per day | CMS MUE values, MAI indicators |

#### Category 4: Clinical Appropriateness (Rules 9-11, 14-15)
| Rule # | Rule Name | Description | Threshold/Logic |
|--------|-----------|-------------|-----------------|
| 9 | Age/Gender Appropriateness | Procedure valid for patient demographics | Age ranges, 50+ gender patterns |
| 10 | Diagnosis Conflict | Mutually exclusive diagnoses | ICD×ICD conflict matrix |
| 11 | Provider Scope | Provider qualified for procedure | License type vs. procedure mapping |
| 14 | LCD Medical Necessity | Local Coverage Determination rules | Medicare Administrative Contractor rules |
| 15 | NCD Medical Necessity | National Coverage Determination rules | CMS NCD database |

#### Category 5: FWA Detection (Rules 16-18)
| Rule # | Rule Name | Description | Threshold/Logic |
|--------|-----------|-------------|-----------------|
| 16 | Duplicate Detection | Identify exact/near duplicate claims | 95%+ exact match, 75-95% possible duplicate |
| 17 | Upcoding Detection | High-complexity codes without justification | E/M code distribution analysis |
| 18 | Unbundling Detection | Bundled services billed separately | Component billing detection |

#### Category 6: Risk Adjustment (Rule 19)
| Rule # | Rule Name | Description | Threshold/Logic |
|--------|-----------|-------------|-----------------|
| 19 | HCC Risk Validation | Validate HCC coding for risk adjustment | RAF score calculation, HCC model |

### 13.4 Implementation File Reference

| Implementation File | Rules Covered | Line Range |
|---------------------|---------------|------------|
| `src/services/claim_validation.py` | 2, 5 | Business validation |
| `src/services/adjudication_validators.py` | 1, 3, 4, 11, 12, 13 | Eligibility & adjudication |
| `src/services/validation/icd_cpt_crosswalk.py` | 6, 7, 8 | Medical coding |
| `src/services/validation/demographic_validator.py` | 9, 19 | Demographics & HCC |
| `src/services/validation/icd_conflict_validator.py` | 10 | Diagnosis conflicts |
| `src/services/validation/clinical_necessity_validator.py` | 14, 15 | LCD/NCD medical necessity |
| `src/services/fwa/duplicate_detector.py` | 16 | Duplicate detection |
| `src/services/fwa/upcoding_detector.py` | 17, 18 | Upcoding/Unbundling |
| `src/services/fwa/pattern_analyzer.py` | (Supporting) | Pattern analysis for FWA |

### 13.5 Validation Phases (from Design Doc 05)

The claim adjudication engine executes validation in 5 phases:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    ADJUDICATION ENGINE - 5 PHASES                         │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Phase 1: ELIGIBILITY           Phase 2: MEDICAL VALIDITY                 │
│  ┌─────────────────────────┐    ┌─────────────────────────────────────┐  │
│  │ Rule 1: Policy Active   │    │ Rule 6: ICD-CPT Crosswalk           │  │
│  │ Rule 2: Service Dates   │    │ Rule 7: NCCI PTP Edits              │  │
│  │ Rule 3: Network Status  │    │ Rule 8: MUE Limits                  │  │
│  │ Rule 13: Benefit Limits │    │ Rule 9: Age/Gender Appropriateness  │  │
│  └─────────────────────────┘    │ Rule 10: Diagnosis Conflicts        │  │
│                                 │ Rule 14-15: LCD/NCD Necessity        │  │
│                                 └─────────────────────────────────────┘  │
│                                                                           │
│  Phase 3: FWA DETECTION         Phase 4: PRIOR AUTH & COMPLIANCE         │
│  ┌─────────────────────────┐    ┌─────────────────────────────────────┐  │
│  │ Rule 16: Duplicates     │    │ Rule 4: Prior Authorization         │  │
│  │ Rule 17: Upcoding       │    │ Rule 11: Provider Scope             │  │
│  │ Rule 18: Unbundling     │    │ Rule 12: Timely Filing              │  │
│  │ (Pattern Analysis)      │    │ Rule 5: Completeness                │  │
│  └─────────────────────────┘    └─────────────────────────────────────┘  │
│                                                                           │
│  Phase 5: RISK ADJUSTMENT & FINAL DECISION                                │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │ Rule 19: HCC Risk Validation                                       │   │
│  │ Pricing Engine: Fee schedule lookup, allowed amounts               │   │
│  │ Auto-Decision: APPROVE | DENY | PEND (based on all rules)          │   │
│  └───────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────┘
```

### 13.6 Validation Execution Points in Wizard

```
┌───────────────────────────────────────────────────────────────────────────┐
│                         CLAIM SUBMISSION WORKFLOW                          │
├───────────┬────────────┬──────────────┬────────────┬─────────────────────┤
│  Step 0   │  Step 1    │   Step 2     │  Step 3    │      Step 4         │
│  Upload   │ Processing │   Preview    │  Review    │      Submit         │
│  Docs     │            │ (READ-ONLY)  │   Data     │                     │
├───────────┼────────────┼──────────────┼────────────┼─────────────────────┤
│           │ EXTRACTION │              │            │   FULL VALIDATION   │
│   None    │  + PDF     │    None      │   None     │   All 19 Rules      │
│           │ Forensics  │              │            │   (5 Phases)        │
└───────────┴────────────┴──────────────┴────────────┴─────────────────────┘
                │                                              │
                ▼                                              ▼
     ┌─────────────────────┐                     ┌─────────────────────────┐
     │ EXTRACTION RULES    │                     │ VALIDATION EXECUTION    │
     ├─────────────────────┤                     ├─────────────────────────┤
     │ 1. Insured Data     │                     │ Phase 1: Eligibility    │
     │ 2. Code Extraction  │                     │   Rules: 1, 2, 3, 13    │
     │ 3. PDF Forensics    │                     │ Phase 2: Medical Valid. │
     └─────────────────────┘                     │   Rules: 6-10, 14-15    │
                                                 │ Phase 3: FWA Detection  │
                                                 │   Rules: 16, 17, 18     │
                                                 │ Phase 4: Compliance     │
                                                 │   Rules: 4, 5, 11, 12   │
                                                 │ Phase 5: Risk & Decision│
                                                 │   Rule: 19 + Pricing    │
                                                 └─────────────────────────┘
```

### 13.7 Preview Step Scope (Clarification)

The **Preview step does NOT execute validation rules**. It is a **read-only display** of:
- Extracted data from Processing step
- Confidence scores per field
- Extraction source (OCR/LLM)
- Low-confidence field highlighting

**Validation rules execute:**
1. **Processing Step (Step 1)**: Only extraction-related rules + PDF Forensics
2. **Submit Step (Step 4)**: All 19 validation rules across 5 phases

### 13.8 Gap Analysis: Design vs Implementation

Based on cross-reference analysis between design documents 03, 04, 05 and actual implementation:

| Aspect | Design Specification | Implementation Status | Gap |
|--------|---------------------|----------------------|-----|
| Core Rules (1-12) | Doc 03, 04 | All implemented | ✅ None |
| Extended Rules (13-19) | Doc 05 | All implemented | ✅ None |
| FWA ML Model | Doc 05 | Pattern analyzer ready | ⚠️ Model training pending |
| LCD/NCD Database | Doc 05 | LLM fallback in place | ⚠️ CMS data feed pending |
| HCC Risk Calculator | Doc 05 | Basic validation | ⚠️ Full RAF scoring pending |

**Summary:** All 19 validation rules are implemented. Three areas have partial implementation with acceptable fallbacks.

### 13.9 Future Enhancement: Pre-Validation Preview

In a future phase, consider adding optional pre-validation in Preview step:
- Show potential validation warnings before review
- Flag fields likely to fail validation
- Suggest corrections before full submission

This would require:
- New API endpoint: `POST /api/v1/claims/pre-validate`
- Lightweight validation (Rules 5, 6, 9 only - completeness, crosswalk, demographics)
- User preference setting to enable/disable

---

## 14. Critical Fix: PDF-to-Image Conversion

### 14.1 Issue Identified

During testing, it was discovered that the document processor sends raw PDF bytes directly to the OCR service, which expects image data. This results in OCR failures for PDF documents.

**Current Flow (Broken):**
```
PDF File -> Raw Bytes -> OCR Service -> ERROR (cannot identify image)
```

**Required Flow:**
```
PDF File -> PyMuPDF (fitz) -> PNG Images -> OCR Service -> Success
```

### 14.2 Required Backend Changes

**File:** `src/services/document_processor.py`

```python
async def _process_pdf_to_images(self, pdf_bytes: bytes) -> list[bytes]:
    """Convert PDF pages to PNG images for OCR processing."""
    import fitz  # PyMuPDF

    images = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # Render at 300 DPI for good OCR quality
        mat = fitz.Matrix(300/72, 300/72)
        pix = page.get_pixmap(matrix=mat)
        images.append(pix.tobytes("png"))

    doc.close()
    return images
```

This fix is **required** for the Preview step to show accurate extraction results.

---

## Validation Checklist

- [x] Business requirements clearly mapped to technical solution
- [x] All integration points identified and specified
- [x] Security requirements addressed (same as existing flow)
- [x] Performance requirements defined
- [x] Risks identified with mitigation strategies
- [x] Implementation broken into manageable phases
- [x] Technology choices justified (using existing stack)
- [x] UI mockups provided
- [x] Code implementation guide included
- [ ] **PENDING:** User feedback on preview being mandatory vs optional
- [ ] **PENDING:** PDF-to-image conversion fix approval

---

## Appendix A: URL/Port Configuration Registry

To prevent future configuration issues, a centralized configuration approach:

| Service | Development Port | Configuration File |
|---------|------------------|-------------------|
| Angular Frontend | 4202 | `frontend/apps/claims-portal/project.json` |
| FastAPI Backend | 8002 | `docker/docker-compose.local.yml`, `.env` |
| PaddleOCR Service | 9091 | `docker/docker-compose.local.yml` |
| Ollama LLM | 11434 | `docker/docker-compose.local.yml` |
| PostgreSQL | 5432 | `docker/docker-compose.local.yml` |
| Redis | 6379 | `docker/docker-compose.local.yml` |
| MinIO | 9000 | `docker/docker-compose.local.yml` |

**Proxy Configuration:**
- File: `frontend/apps/claims-portal/proxy.conf.json`
- Backend target: `http://localhost:8002`
- WebSocket target: `ws://localhost:8002`

---

**Document Status:** DRAFT
**Next Action:** Review and approval required before implementation
**Approval Required From:** Tech Lead, Product Owner

---

## Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-21 | Architecture Team | Initial draft |
| 1.1 | 2025-12-21 | Architecture Team | Enhanced Section 13: Added comprehensive 19-rule validation matrix, cross-reference with design docs 03/04/05, gap analysis, validation phases diagram |
