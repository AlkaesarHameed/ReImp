# Automated Validation Engine - Design Document

## Design Review Documentation

**Design Date**: December 19, 2025
**Feature**: Automation-First Claims Processing with Comprehensive Validation
**Author**: Claude Code (AI Assistant)
**Status**: Ready for Review
**Related Design**: [02_enhanced_claims_input_design.md](02_enhanced_claims_input_design.md)

---

## 1. Executive Summary

### Overview

This design document specifies an **automation-first** claims processing system that minimizes end-user effort by:

1. **Auto-extracting** all claim data from uploaded documents (member, provider, services)
2. **Auto-populating** form fields with extracted data (no manual entry required)
3. **Comprehensive validation** through 13 automated validation rules
4. **Intelligent workflow** that only requires user intervention for exceptions

### Design Philosophy

> "The system should capture information with **minimal effort** from the end user and process the data automatically."

The user's role shifts from **data entry** to **exception handling**:
- Upload documents → System extracts everything
- Review highlighted issues → Approve or correct
- Submit → System validates and processes

### Validation Rules (13 Requirements)

| # | Validation Rule | Category |
|---|-----------------|----------|
| 1 | Extract insured data (member, policy) | Extraction |
| 2 | Extract codes, services, medications, consumables | Extraction |
| 3 | Detect computer-edited/fraudulent documents | Fraud |
| 4 | Medical necessity: Services vs Diagnosis crosswalk | Medical |
| 5 | Medical necessity: Via coding and medical notes | Medical |
| 6 | ICD × ICD crosswalk validation | Medical |
| 7 | Gender/age appropriateness for diagnoses | Medical |
| 8 | Gender/age appropriateness for procedures/drugs | Medical |
| 9 | Medical reports necessity validation | Medical |
| 10 | Claim rejection reason validation | Business |
| 11 | Policy coverage and Table of Benefits validation | Coverage |
| 12 | Network/country coverage for provider | Network |

---

## 2. Architecture Overview

### Current vs. Proposed Flow

```
CURRENT FLOW (Manual-Heavy):
┌─────────────┐   ┌──────────────┐   ┌────────────────┐   ┌────────────────┐
│ Step 1      │ → │ Step 2       │ → │ Step 3         │ → │ Step 4         │
│ Member      │   │ Policy Docs  │   │ Claim Docs     │   │ Processing     │
│ (MANUAL)    │   │ (Upload)     │   │ (Upload)       │   │ (View Extract) │
└─────────────┘   └──────────────┘   └────────────────┘   └────────────────┘
       ↓                                                         ↓
┌─────────────┐   ┌──────────────┐   ┌────────────────┐
│ Step 5      │ ← │ Step 6       │ ← │ Step 7         │
│ Provider    │   │ Services     │   │ Review         │
│ (MANUAL)    │   │ (MANUAL)     │   │ (Submit)       │
└─────────────┘   └──────────────┘   └────────────────┘

PROPOSED FLOW (Automation-First):
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ Step 1          │ → │ Step 2          │ → │ Step 3          │
│ Upload Docs     │   │ Processing &    │   │ Review &        │
│ (Policy+Claim)  │   │ Validation      │   │ Submit          │
│                 │   │ (AUTO)          │   │ (Exceptions)    │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

### System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                      │
│  ┌──────────────┐  ┌────────────────┐  ┌────────────────────────────┐  │
│  │ Doc Upload   │→ │ Processing     │→ │ Validation Review          │  │
│  │ Component    │  │ Dashboard      │  │ Component                  │  │
│  │ • Policy     │  │ • Progress     │  │ • Auto-populated fields    │  │
│  │ • Claim      │  │ • Status       │  │ • Validation results       │  │
│  │ • Medical    │  │ • Confidence   │  │ • Exception handling       │  │
│  └──────────────┘  └────────────────┘  └────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    VALIDATION ENGINE (Backend)                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   Orchestrator Service                           │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │   │
│  │  │ Extraction   │ │ Validation   │ │ Risk Assessment          │ │   │
│  │  │ Pipeline     │ │ Pipeline     │ │ Pipeline                 │ │   │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │ Extraction  │ │ Medical     │ │ FWA         │ │ Coverage        │   │
│  │ Services    │ │ Validators  │ │ Detection   │ │ Validators      │   │
│  ├─────────────┤ ├─────────────┤ ├─────────────┤ ├─────────────────┤   │
│  │ • OCR       │ │ • ICD-CPT   │ │ • Duplicate │ │ • Policy        │   │
│  │ • NLP       │ │ • Age/Gender│ │ • Upcoding  │ │ • Eligibility   │   │
│  │ • Code Map  │ │ • Necessity │ │ • Pattern   │ │ • Network       │   │
│  │ • Entity    │ │ • ICD×ICD   │ │ • Forgery   │ │ • TOB           │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Validation Rules Implementation

### Rule 1: Extract Insured Data

**Purpose**: Auto-extract member/patient information from documents.

**Implementation**:
```python
# src/services/extraction/insured_extractor.py

class InsuredDataExtractor:
    """Extracts insured/member data from documents."""

    def extract(self, document: ProcessedDocument) -> InsuredData:
        """
        Extracts:
        - Patient name (first, middle, last)
        - Date of birth
        - Gender
        - Member ID / Policy ID
        - Address
        - Contact information
        - Relationship to subscriber
        """
        pass
```

**Data Flow**:
```
Document → OCR → NLP Entity Recognition → Member Lookup → Auto-populate
```

**Confidence Handling**:
- High confidence (≥90%): Auto-populate, no review needed
- Medium confidence (70-89%): Auto-populate, flag for review
- Low confidence (<70%): Show suggestions, require user selection

### Rule 2: Extract Codes, Services, Medications

**Purpose**: Auto-extract all billing information.

**Implementation**:
```python
# src/services/extraction/billing_extractor.py

class BillingDataExtractor:
    """Extracts billing codes and services from documents."""

    def extract(self, document: ProcessedDocument) -> BillingData:
        """
        Extracts:
        - ICD-10 diagnosis codes
        - CPT/HCPCS procedure codes
        - Modifiers
        - Service dates
        - Quantities
        - Charges
        - Medications (NDC codes)
        - Consumables/supplies
        """
        pass
```

**Code Mapping**:
```
Raw Text → NLP → Code Recognition → Validation → Standardization
           ↓
    "chest xray" → CPT 71046
    "hypertension" → ICD-10 I10
    "amoxicillin 500mg" → NDC 00093-3109
```

### Rule 3: Fraud Detection (Computer-Edited Documents)

**Purpose**: Detect potentially fraudulent or altered documents.

**Implementation**:
```python
# src/services/fwa/forgery_detector.py

class DocumentForgeryDetector:
    """Detects signs of document tampering or forgery."""

    def analyze(self, document: ProcessedDocument) -> ForgeryAnalysis:
        """
        Detects:
        - PDF metadata anomalies (creation date ≠ modification date)
        - Font inconsistencies within document
        - Image manipulation artifacts
        - Copy-paste patterns
        - Digital signature tampering
        - Embedded document fragments
        - Unusual character encoding
        """
        pass
```

**Detection Signals**:
| Signal | Weight | Description |
|--------|--------|-------------|
| Metadata mismatch | 0.3 | Creation vs modification date |
| Font variance | 0.2 | Multiple fonts in typed text |
| Image analysis | 0.2 | JPEG artifact analysis |
| Pattern detection | 0.2 | Repeated elements |
| Signature check | 0.1 | Digital signature validation |

### Rule 4: Medical Necessity - Service vs Diagnosis Crosswalk

**Purpose**: Validate that procedures are medically appropriate for diagnoses.

**Implementation**:
```python
# src/services/medical/crosswalk_validator.py

class ProcedureDiagnosisCrosswalk:
    """Validates procedure codes against diagnosis codes."""

    def validate(self, diagnoses: list[str], procedures: list[str]) -> CrosswalkResult:
        """
        Validates:
        - Each procedure has supporting diagnosis
        - Primary diagnosis supports primary procedure
        - No contradictory codes (e.g., bilateral code with unilateral diagnosis)
        - Modifier appropriateness
        """
        pass
```

**Crosswalk Database**:
```yaml
# Example mappings
CPT_99213:  # Office visit, established patient
  supported_diagnoses:
    - all  # General visit, most diagnoses valid

CPT_71046:  # Chest X-ray, 2 views
  supported_diagnoses:
    - J00-J99  # Respiratory diseases
    - R05      # Cough
    - R06      # Breathing abnormalities
    - Z87.01   # History of pneumonia
```

### Rule 5: Medical Necessity via Coding and Notes

**Purpose**: Validate medical necessity using clinical documentation.

**Implementation**:
```python
# src/services/medical/clinical_necessity.py

class ClinicalNecessityValidator:
    """Validates medical necessity from clinical notes."""

    def validate(self, claim: ClaimData, clinical_notes: str) -> NecessityResult:
        """
        Analyzes:
        - Chief complaint supports diagnosis
        - Examination findings support procedures
        - Test results justify treatment
        - Treatment plan alignment
        - Progress notes consistency
        """
        pass
```

**NLP Analysis**:
```
Clinical Notes → Entity Extraction → Symptom-Diagnosis Mapping → Validation
                        ↓
              "SOB, wheezing, productive cough"
                        ↓
              Supports: J06.9 (URI), J44.1 (COPD exacerbation)
              Procedures: 71046 (CXR), 94010 (Spirometry) ✓
```

### Rule 6: ICD × ICD Crosswalk Validation

**Purpose**: Detect invalid or implausible diagnosis combinations.

**Implementation**:
```python
# src/services/medical/icd_crosswalk.py

class ICDCrosswalkValidator:
    """Validates ICD code combinations for clinical plausibility."""

    def validate(self, diagnoses: list[str]) -> ICDValidationResult:
        """
        Checks:
        - Mutually exclusive codes (can't have both)
        - Code specificity (use most specific available)
        - Manifestation codes require etiology codes
        - Sequelae codes temporal logic
        - Excludes1 and Excludes2 edits
        """
        pass
```

**Invalid Combinations**:
| Code 1 | Code 2 | Reason |
|--------|--------|--------|
| O80 | O82 | Delivery cannot be both normal and cesarean |
| E10.x | E11.x | Type 1 and Type 2 diabetes are mutually exclusive |
| Z38.x | Any adult | Newborn codes invalid for adults |

### Rule 7: Gender/Age Appropriateness for Diagnoses

**Purpose**: Validate diagnoses are appropriate for patient demographics.

**Implementation**:
```python
# src/services/medical/demographic_validator.py

class DiagnosisDemographicValidator:
    """Validates diagnosis codes against patient demographics."""

    def validate(self, patient: PatientData, diagnoses: list[str]) -> DemographicResult:
        """
        Validates:
        - Gender-specific diagnoses (prostate, ovarian, etc.)
        - Age-appropriate diagnoses (senile dementia not in children)
        - Pregnancy codes only for females
        - Newborn codes only for age < 28 days
        - Pediatric codes for appropriate ages
        """
        pass
```

**Validation Rules**:
```yaml
gender_rules:
  male_only:
    - N40-N42  # Prostate disorders
    - C61      # Prostate cancer
    - N46      # Male infertility
  female_only:
    - N80-N98  # Female genital disorders
    - O00-O9A  # Pregnancy/childbirth
    - C56-C57  # Ovarian/uterine cancer

age_rules:
  pediatric_only:  # Age < 18
    - P00-P96  # Perinatal conditions
    - Q00-Q99  # Congenital malformations (except some)
  adult_only:      # Age >= 18
    - F03       # Senile dementia
    - N40       # Prostate hyperplasia
  geriatric_specific:  # Age >= 65
    - G30       # Alzheimer's (more common, not exclusive)
```

### Rule 8: Gender/Age Appropriateness for Procedures/Drugs

**Purpose**: Validate procedures and medications are appropriate for patient.

**Implementation**:
```python
# src/services/medical/procedure_demographic_validator.py

class ProcedureDemographicValidator:
    """Validates procedures and drugs against patient demographics."""

    def validate(self, patient: PatientData, procedures: list[str],
                 medications: list[str]) -> DemographicResult:
        """
        Validates:
        - Gender-specific procedures (prostatectomy, hysterectomy)
        - Age-appropriate procedures (pediatric vs adult dosing)
        - Drug contraindications by age/gender
        - Pediatric drug formulations
        - Geriatric medication alerts
        """
        pass
```

**Examples**:
| Code | Type | Restriction | Reason |
|------|------|-------------|--------|
| 58150 | CPT | Female only | Hysterectomy |
| 55840 | CPT | Male only | Prostatectomy |
| J1745 | HCPCS | Age ≥ 18 | Infliximab - adult only |
| 90460 | CPT | Age < 19 | Immunization - pediatric |

### Rule 9: Medical Reports Necessity Validation

**Purpose**: Validate that medical reports support billed services.

**Implementation**:
```python
# src/services/medical/report_validator.py

class MedicalReportValidator:
    """Validates medical reports support claimed services."""

    def validate(self, claim: ClaimData, reports: list[MedicalReport]) -> ReportValidation:
        """
        Validates:
        - Lab results support ordered tests
        - Imaging reports support imaging codes
        - Pathology reports support biopsy codes
        - Operative notes support surgical codes
        - Therapy notes support therapy codes
        """
        pass
```

**Report Matching**:
```
CPT 71046 (Chest X-ray) → Requires: Radiology report
   Report found: ✓
   Report date matches service date: ✓
   Findings documented: ✓

CPT 99213 (Office visit) → Requires: Progress note
   Report found: ✓
   Chief complaint documented: ✓
   Examination documented: ✓
   Medical decision making documented: ✓
```

### Rule 10: Claim Rejection Reason Validation

**Purpose**: Validate rejection reasons and provide actionable feedback.

**Implementation**:
```python
# src/services/validation/rejection_validator.py

class RejectionReasonValidator:
    """Validates and explains claim rejection reasons."""

    def validate(self, claim: ClaimData) -> RejectionAnalysis:
        """
        Identifies:
        - Primary rejection reason
        - Secondary rejection reasons
        - Corrective actions possible
        - Resubmission eligibility
        - Appeal options
        """
        pass
```

**Rejection Categories**:
| Category | Code Range | Description |
|----------|------------|-------------|
| Eligibility | A0-A9 | Member not eligible |
| Coverage | B0-B9 | Service not covered |
| Authorization | C0-C9 | Prior auth required/invalid |
| Coding | D0-D9 | Invalid or missing codes |
| Timely Filing | E0-E9 | Past filing deadline |
| Duplicate | F0-F9 | Duplicate claim detected |

### Rule 11: Policy Coverage and TOB Validation

**Purpose**: Validate claim against policy's Table of Benefits.

**Implementation**:
```python
# src/services/coverage/tob_validator.py

class TableOfBenefitsValidator:
    """Validates claim against policy Table of Benefits."""

    def validate(self, claim: ClaimData, policy: PolicyDocument) -> CoverageResult:
        """
        Validates:
        - Service category coverage
        - Annual/lifetime maximums
        - Deductible status
        - Copay/coinsurance levels
        - Waiting period compliance
        - Pre-existing condition exclusions
        - Service frequency limits
        """
        pass
```

**TOB Structure**:
```yaml
policy_tob:
  inpatient:
    covered: true
    deductible: 500
    coinsurance: 0.20
    annual_max: 1000000
    pre_auth_required: true

  outpatient:
    covered: true
    copay: 50
    annual_max: 50000

  pharmacy:
    generic:
      copay: 10
    brand:
      copay: 35
    specialty:
      coinsurance: 0.25
```

### Rule 12: Network/Country Coverage Validation

**Purpose**: Validate provider is in-network and geographically covered.

**Implementation**:
```python
# src/services/network/network_validator.py

class NetworkCoverageValidator:
    """Validates provider network and geographic coverage."""

    def validate(self, claim: ClaimData, provider: ProviderData) -> NetworkResult:
        """
        Validates:
        - Provider in network (in-network/out-of-network/non-participating)
        - Provider active and credentialed
        - Geographic coverage (country, region, state)
        - Emergency exception handling
        - Single case agreement status
        """
        pass
```

**Network Tiers**:
| Tier | In-Network | Coinsurance | Notes |
|------|------------|-------------|-------|
| Preferred | Yes | 10% | Contracted rates |
| Standard | Yes | 20% | Contracted rates |
| Out-of-Network | No | 40% | UCR limits apply |
| Non-Participating | No | 50%+ | Balance billing possible |

---

## 4. Frontend Changes

### Simplified Workflow

**Old: 7 Steps with Manual Entry**
```
Member → Policy Docs → Claim Docs → Processing → Provider → Services → Review
```

**New: 3 Steps with Auto-Population**
```
Documents → Validation Review → Submit
```

### Step 1: Document Upload (Unified)

```typescript
// step-documents.component.ts

@Component({
  selector: 'app-step-documents',
  template: `
    <div class="upload-section">
      <h3>Upload All Documents</h3>
      <p>Upload policy documents, claim forms, invoices, and medical records.
         The system will automatically extract all required information.</p>

      <p-fileUpload
        [multiple]="true"
        accept=".pdf,.jpg,.jpeg,.png"
        [maxFileSize]="52428800"
        [auto]="true"
        (onUpload)="onUpload($event)">
      </p-fileUpload>

      <div class="document-categories">
        <p-chip
          *ngFor="let doc of uploadedDocs()"
          [label]="doc.filename"
          [icon]="getDocTypeIcon(doc.detectedType)"
          [removable]="true"
          (onRemove)="removeDoc(doc)">
        </p-chip>
      </div>
    </div>
  `
})
export class StepDocumentsComponent {
  // System auto-detects document type from content
  uploadedDocs = signal<UploadedDocument[]>([]);

  // Document types detected by AI:
  // - policy, claim_form, invoice, medical_record, lab_report,
  //   imaging_report, prescription, referral, prior_auth, other
}
```

### Step 2: Validation Review (Auto-Populated)

```typescript
// step-validation-review.component.ts

@Component({
  selector: 'app-step-validation-review',
  template: `
    <div class="validation-dashboard">
      <!-- Auto-populated Member Info -->
      <p-panel header="Member Information" [toggleable]="true">
        <div class="auto-populated-section" [class.needs-review]="memberNeedsReview()">
          <div class="field">
            <label>Member ID</label>
            <span class="value">{{ extractedData().member_id }}</span>
            <i class="pi" [class]="getConfidenceIcon(extractedData().member_id_confidence)"></i>
          </div>
          <!-- Other member fields... -->
        </div>
      </p-panel>

      <!-- Auto-populated Provider Info -->
      <p-panel header="Provider Information" [toggleable]="true">
        <div class="auto-populated-section">
          <div class="field">
            <label>Provider Name</label>
            <span class="value">{{ extractedData().provider_name }}</span>
            <span class="source">(Auto-fetched from NPI: {{ extractedData().provider_npi }})</span>
          </div>
        </div>
      </p-panel>

      <!-- Validation Results -->
      <p-panel header="Validation Results" [toggleable]="false">
        <p-table [value]="validationResults()" [paginator]="false">
          <ng-template pTemplate="header">
            <tr>
              <th>Rule</th>
              <th>Status</th>
              <th>Details</th>
              <th>Action</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-result>
            <tr [class]="result.severity">
              <td>{{ result.ruleName }}</td>
              <td>
                <p-tag [severity]="result.severity" [value]="result.status"></p-tag>
              </td>
              <td>{{ result.message }}</td>
              <td>
                <button pButton
                  *ngIf="result.actionRequired"
                  [label]="result.actionLabel"
                  (click)="handleAction(result)">
                </button>
              </td>
            </tr>
          </ng-template>
        </p-table>
      </p-panel>
    </div>
  `
})
export class StepValidationReviewComponent {
  extractedData = signal<ExtractedClaimData | null>(null);
  validationResults = signal<ValidationResult[]>([]);

  // All fields auto-populated from extraction
  // User only reviews exceptions and validation failures
}
```

### Step 3: Submit (Minimal)

```typescript
// step-submit.component.ts

@Component({
  selector: 'app-step-submit',
  template: `
    <div class="submit-section">
      <div class="summary-card">
        <h3>Claim Summary</h3>
        <div class="summary-row">
          <span>Member:</span>
          <span>{{ summary().memberName }}</span>
        </div>
        <div class="summary-row">
          <span>Provider:</span>
          <span>{{ summary().providerName }}</span>
        </div>
        <div class="summary-row">
          <span>Total Charged:</span>
          <span>{{ summary().totalCharged | currency }}</span>
        </div>
        <div class="summary-row">
          <span>Validation Status:</span>
          <p-tag [severity]="summary().validationSeverity"
                 [value]="summary().validationStatus">
          </p-tag>
        </div>
      </div>

      <div class="action-buttons">
        <button pButton
          label="Submit Claim"
          icon="pi pi-check"
          [disabled]="hasBlockingErrors()"
          (click)="submitClaim()">
        </button>
      </div>
    </div>
  `
})
export class StepSubmitComponent {
  // Minimal interaction - just confirm and submit
}
```

---

## 5. API Changes

### New Validation Endpoint

```python
# src/api/routes/validation.py

@router.post("/claims/validate-comprehensive")
async def validate_comprehensive(
    documents: list[UploadFile],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ComprehensiveValidationResponse:
    """
    Comprehensive validation endpoint that:
    1. Processes uploaded documents
    2. Extracts all claim data
    3. Runs all 13 validation rules
    4. Returns auto-populated claim with validation results
    """

    # Step 1: Process documents
    processed_docs = await document_processor.process_batch(documents)

    # Step 2: Extract data
    extracted_data = await extraction_service.extract_all(processed_docs)

    # Step 3: Auto-populate missing data
    enriched_data = await enrichment_service.enrich(extracted_data)

    # Step 4: Run all validations
    validation_results = await validation_engine.validate_all(enriched_data)

    return ComprehensiveValidationResponse(
        extracted_data=enriched_data,
        validation_results=validation_results,
        can_submit=not validation_results.has_blocking_errors,
        warnings=validation_results.warnings,
        errors=validation_results.errors
    )
```

### Validation Engine Orchestrator

```python
# src/services/validation/engine.py

class ValidationEngine:
    """Orchestrates all 13 validation rules."""

    def __init__(self):
        self.validators = [
            InsuredDataExtractor(),           # Rule 1
            BillingDataExtractor(),           # Rule 2
            DocumentForgeryDetector(),        # Rule 3
            ProcedureDiagnosisCrosswalk(),    # Rule 4
            ClinicalNecessityValidator(),     # Rule 5
            ICDCrosswalkValidator(),          # Rule 6
            DiagnosisDemographicValidator(),  # Rule 7
            ProcedureDemographicValidator(),  # Rule 8
            MedicalReportValidator(),         # Rule 9
            RejectionReasonValidator(),       # Rule 10
            TableOfBenefitsValidator(),       # Rule 11
            NetworkCoverageValidator(),       # Rule 12
        ]

    async def validate_all(self, data: ExtractedClaimData) -> ValidationResults:
        """Run all validators and aggregate results."""
        results = []

        for validator in self.validators:
            try:
                result = await validator.validate(data)
                results.append(result)
            except Exception as e:
                results.append(ValidationResult(
                    rule=validator.name,
                    status="error",
                    message=f"Validation failed: {str(e)}"
                ))

        return ValidationResults(
            results=results,
            has_blocking_errors=any(r.is_blocking for r in results),
            overall_status=self._calculate_overall_status(results)
        )
```

---

## 6. Data Models

### Comprehensive Validation Response

```python
# src/schemas/validation.py

class ComprehensiveValidationResponse(BaseModel):
    """Response from comprehensive validation endpoint."""

    # Auto-extracted and enriched claim data
    extracted_data: ExtractedClaimData

    # Validation results for all 13 rules
    validation_results: list[ValidationRuleResult]

    # Summary
    can_submit: bool
    overall_risk_score: float  # 0.0 - 1.0

    # Issues by severity
    errors: list[ValidationIssue]    # Blocking
    warnings: list[ValidationIssue]  # Non-blocking
    info: list[ValidationIssue]      # Informational

    # Fraud indicators
    fwa_flags: list[str]
    fwa_risk_level: FWARiskLevel

    # Coverage summary
    coverage_summary: CoverageSummary

    # Suggested corrections
    suggested_corrections: list[SuggestedCorrection]


class ExtractedClaimData(BaseModel):
    """Auto-extracted claim data from documents."""

    # Member (auto-populated)
    member_id: str
    member_name: str
    member_dob: date
    member_gender: str
    policy_id: str

    # Provider (auto-fetched from NPI)
    provider_npi: str
    provider_name: str  # Auto-fetched
    provider_specialty: str  # Auto-fetched
    provider_network_status: str  # Auto-determined

    # Services (auto-extracted)
    service_date_from: date
    service_date_to: date
    diagnoses: list[ExtractedDiagnosis]
    procedures: list[ExtractedProcedure]
    medications: list[ExtractedMedication]

    # Financial (auto-calculated)
    total_charged: Decimal

    # Confidence scores
    extraction_confidence: float
    field_confidences: dict[str, float]
```

---

## 7. Implementation Phases

### Phase 1: Backend Validation Engine (Week 1-2)
1. Create ValidationEngine orchestrator
2. Integrate existing validators into engine
3. Implement missing validators (Rules 3, 5, 9, 11)
4. Create comprehensive validation endpoint

### Phase 2: Auto-Population Services (Week 2-3)
1. Enhance extraction services for all document types
2. Implement provider auto-fetch from NPI
3. Implement member lookup from extracted data
4. Create data enrichment pipeline

### Phase 3: Frontend Simplification (Week 3-4)
1. Create unified document upload component
2. Create validation review dashboard
3. Implement auto-population UI
4. Create exception handling workflows

### Phase 4: Integration & Testing (Week 4-5)
1. End-to-end testing
2. Validation rule accuracy testing
3. Performance optimization
4. User acceptance testing

---

## 8. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Fields manually entered | 15+ | 0-3 |
| Claim submission time | 10+ min | < 2 min |
| Data entry errors | 5-10% | < 1% |
| Validation accuracy | Manual | 95%+ automated |
| User satisfaction | N/A | > 4.5/5 |

---

## 9. Appendix: Validation Rule Matrix

| Rule | Validator Class | Input | Output | Blocking |
|------|-----------------|-------|--------|----------|
| 1 | InsuredDataExtractor | Documents | MemberData | No |
| 2 | BillingDataExtractor | Documents | BillingData | No |
| 3 | DocumentForgeryDetector | Documents | FraudFlags | Yes |
| 4 | ProcedureDiagnosisCrosswalk | Codes | CrosswalkResult | Yes |
| 5 | ClinicalNecessityValidator | Notes | NecessityResult | Yes |
| 6 | ICDCrosswalkValidator | Diagnoses | ICDResult | Yes |
| 7 | DiagnosisDemographicValidator | Patient+Dx | DemoResult | Yes |
| 8 | ProcedureDemographicValidator | Patient+Px | DemoResult | Yes |
| 9 | MedicalReportValidator | Reports | ReportResult | No |
| 10 | RejectionReasonValidator | Claim | RejectionResult | Info |
| 11 | TableOfBenefitsValidator | Policy+Claim | CoverageResult | Yes |
| 12 | NetworkCoverageValidator | Provider | NetworkResult | No |
