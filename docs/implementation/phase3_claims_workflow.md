# Phase 3: Claims Workflow Implementation

**Document Version:** 1.0
**Implementation Date:** 2025-12-18
**Author:** Claude Code (Following implement.md methodology)
**Status:** Design - Awaiting Approval

---

## 1. Requirements Analysis

### 1.1 Business Objectives

Based on [angular_frontend_design.md](../design/angular_frontend_design.md) Section 9, Phase 3:

| Objective | Deliverable |
|-----------|-------------|
| End-to-end claims processing | Complete submission to payment workflow |
| Multi-step claim submission | 4-step wizard (Member → Provider → Services → Review) |
| Form validation | Real-time ICD-10/CPT code validation |
| Claim review workflow | Supervisor approval/denial interface |
| Document management | Upload supporting documents to claims |

### 1.2 Acceptance Criteria

1. **Claim Submission Wizard**
   - [ ] 4-step wizard with progress indicator
   - [ ] Step 1: Member selection with eligibility check
   - [ ] Step 2: Provider selection with NPI validation
   - [ ] Step 3: Service lines with ICD-10/CPT codes
   - [ ] Step 4: Review and submit with validation summary
   - [ ] Form state persists across steps
   - [ ] Draft save capability

2. **Form Validation**
   - [ ] ICD-10 code lookup with autocomplete (debounced 300ms)
   - [ ] CPT/HCPCS code validation
   - [ ] Date range validation (service dates)
   - [ ] Required field validation per step
   - [ ] Cross-field validation (e.g., diagnosis must match service)

3. **Claim Review Workflow**
   - [ ] Queue of claims in "needs_review" status
   - [ ] Side-by-side claim details and action panel
   - [ ] Approve action with optional notes
   - [ ] Deny action with required reason code
   - [ ] Pend action for additional information
   - [ ] Bulk approve/deny for eligible claims

4. **Document Upload**
   - [ ] Drag-and-drop file upload
   - [ ] Supported formats: PDF, PNG, JPG, TIFF
   - [ ] Max file size: 10MB per file
   - [ ] Progress indicator during upload
   - [ ] Document preview capability

5. **Performance**
   - [ ] Wizard step transitions < 100ms
   - [ ] Code lookup response < 500ms
   - [ ] Document upload with chunked transfer

### 1.3 Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| Claims Store (Phase 2) | Internal | Completed |
| Claims API Service (Phase 2) | Internal | Completed |
| WebSocket Service (Phase 2) | Internal | Completed |
| PrimeNG Stepper | External | Available (v17.18+) |
| PrimeNG FileUpload | External | Available (v17.18+) |
| Backend /claims endpoints | External | Available |
| Backend /lookup endpoints | External | Must validate |

---

## 2. Design Proposal

### 2.1 Component Architecture

```
claims/
├── components/
│   ├── claim-submit/
│   │   ├── claim-submit.component.ts        # Wizard container
│   │   ├── claim-submit.component.spec.ts   # Tests
│   │   ├── step-member/
│   │   │   ├── step-member.component.ts     # Member selection
│   │   │   └── step-member.component.spec.ts
│   │   ├── step-provider/
│   │   │   ├── step-provider.component.ts   # Provider selection
│   │   │   └── step-provider.component.spec.ts
│   │   ├── step-services/
│   │   │   ├── step-services.component.ts   # Service lines entry
│   │   │   └── step-services.component.spec.ts
│   │   └── step-review/
│   │       ├── step-review.component.ts     # Review & submit
│   │       └── step-review.component.spec.ts
│   │
│   ├── claim-review/
│   │   ├── claim-review.component.ts        # Review workflow
│   │   ├── claim-review.component.spec.ts
│   │   ├── review-queue.component.ts        # Queue list
│   │   └── review-action-panel.component.ts # Actions
│   │
│   └── document-upload/
│       ├── document-upload.component.ts     # Upload widget
│       └── document-upload.component.spec.ts
│
├── services/
│   ├── lookup.service.ts                    # ICD-10/CPT lookups
│   └── lookup.service.spec.ts
│
└── models/
    └── claim-form.model.ts                  # Form interfaces
```

### 2.2 Data Flow Diagram

```
                    CLAIM SUBMISSION WIZARD

┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │  Step 1  │───>│  Step 2  │───>│  Step 3  │───>│  Step 4  │      │
│  │  Member  │    │ Provider │    │ Services │    │  Review  │      │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘      │
│       │               │               │               │             │
│       ▼               ▼               ▼               ▼             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Claim Form State                          │   │
│  │  member: Member | provider: Provider | lines: LineItem[]     │   │
│  └──────────────────────────────┬──────────────────────────────┘   │
│                                 │                                   │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   POST /api/v1/claims   │
                    │   createClaim()         │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │   Claims Store          │
                    │   addClaim(newClaim)    │
                    └─────────────────────────┘
```

### 2.3 Wizard State Management

```typescript
// Claim Form State Interface
interface ClaimFormState {
  currentStep: number;
  isDirty: boolean;
  isValid: boolean;

  // Step 1: Member
  member: {
    memberId: string;
    policyId: string;
    eligibilityVerified: boolean;
    eligibilityResponse?: EligibilityResponse;
  };

  // Step 2: Provider
  provider: {
    providerId: string;
    providerNPI: string;
    placeOfService: string;
    priorAuthNumber?: string;
  };

  // Step 3: Services
  services: {
    serviceDateFrom: string;
    serviceDateTo: string;
    diagnosisCodes: string[];
    primaryDiagnosis: string;
    lineItems: ClaimLineItemForm[];
  };

  // Validation
  validationErrors: ValidationError[];
  validationWarnings: ValidationWarning[];
}

interface ClaimLineItemForm {
  procedureCode: string;
  procedureCodeSystem: 'CPT' | 'HCPCS';
  modifiers: string[];
  serviceDate: string;
  quantity: number;
  unitPrice: number;
  chargedAmount: number;
}
```

### 2.4 Review Workflow State

```typescript
interface ReviewWorkflowState {
  queue: Claim[];           // Claims needing review
  selectedClaim: Claim | null;
  reviewAction: ReviewAction | null;
  bulkSelection: string[];  // Claim IDs for bulk actions
}

interface ReviewAction {
  action: 'approve' | 'deny' | 'pend';
  reason?: string;          // Required for deny
  notes?: string;
  denialCode?: string;
}
```

### 2.5 API Contracts

**Lookup Endpoints (new)**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/v1/lookup/icd10?q={query} | ICD-10 code search |
| GET | /api/v1/lookup/cpt?q={query} | CPT code search |
| GET | /api/v1/lookup/hcpcs?q={query} | HCPCS code search |
| GET | /api/v1/lookup/pos | Place of service codes |
| GET | /api/v1/lookup/denial-reasons | Denial reason codes |

**Document Endpoints (existing)**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /api/v1/claims/{id}/documents | Upload document |
| GET | /api/v1/claims/{id}/documents | List documents |
| DELETE | /api/v1/claims/{id}/documents/{docId} | Delete document |

---

## 3. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Lookup API not available | Medium | High | Build with mock data, validate endpoint exists |
| Large file upload timeout | Medium | Medium | Implement chunked upload with retry |
| Form state loss on navigation | Low | High | LocalStorage draft save, route guard |
| ICD-10/CPT validation complexity | Medium | Medium | Use backend validation, frontend is advisory |
| Slow autocomplete performance | Medium | Medium | Debounce 300ms, limit results to 20 |

---

## 4. Implementation Plan

### 4.1 Task Breakdown

| # | Task | Priority | Tests First |
|---|------|----------|-------------|
| 1 | Create Lookup Service + Tests | P0 | Yes |
| 2 | Create Step Member Component + Tests | P0 | Yes |
| 3 | Create Step Provider Component + Tests | P0 | Yes |
| 4 | Create Step Services Component + Tests | P0 | Yes |
| 5 | Create Step Review Component + Tests | P0 | Yes |
| 6 | Create Claim Submit Wizard + Tests | P0 | Yes |
| 7 | Create Review Queue Component + Tests | P0 | Yes |
| 8 | Create Review Action Panel + Tests | P0 | Yes |
| 9 | Create Document Upload Component + Tests | P1 | Yes |
| 10 | Integration testing | P0 | N/A |

### 4.2 File Inventory

**New Files to Create:**
```
libs/api-client/src/lookup.api.ts
libs/api-client/src/lookup.api.spec.ts
libs/shared/models/src/lookup.model.ts

apps/claims-portal/src/app/features/claims/components/claim-submit/claim-submit.component.ts
apps/claims-portal/src/app/features/claims/components/claim-submit/claim-submit.component.spec.ts
apps/claims-portal/src/app/features/claims/components/claim-submit/step-member/step-member.component.ts
apps/claims-portal/src/app/features/claims/components/claim-submit/step-member/step-member.component.spec.ts
apps/claims-portal/src/app/features/claims/components/claim-submit/step-provider/step-provider.component.ts
apps/claims-portal/src/app/features/claims/components/claim-submit/step-provider/step-provider.component.spec.ts
apps/claims-portal/src/app/features/claims/components/claim-submit/step-services/step-services.component.ts
apps/claims-portal/src/app/features/claims/components/claim-submit/step-services/step-services.component.spec.ts
apps/claims-portal/src/app/features/claims/components/claim-submit/step-review/step-review.component.ts
apps/claims-portal/src/app/features/claims/components/claim-submit/step-review/step-review.component.spec.ts

apps/claims-portal/src/app/features/claims/components/claim-review/claim-review.component.ts
apps/claims-portal/src/app/features/claims/components/claim-review/claim-review.component.spec.ts
apps/claims-portal/src/app/features/claims/components/claim-review/review-queue.component.ts
apps/claims-portal/src/app/features/claims/components/claim-review/review-queue.component.spec.ts
apps/claims-portal/src/app/features/claims/components/claim-review/review-action-panel.component.ts
apps/claims-portal/src/app/features/claims/components/claim-review/review-action-panel.component.spec.ts

apps/claims-portal/src/app/features/claims/components/document-upload/document-upload.component.ts
apps/claims-portal/src/app/features/claims/components/document-upload/document-upload.component.spec.ts
```

**Files to Modify:**
```
libs/api-client/src/index.ts                    # Export lookup API
libs/shared/models/src/index.ts                 # Export lookup models
apps/claims-portal/src/app/features/claims/claims.routes.ts  # Add routes
```

---

## 5. Environment Verification

**Development Environment:** Nx Monorepo with Angular 19+
**Build Command:** `npm run build`
**Test Command:** `npm run test`
**Lint Command:** `npm run lint`

**Dependencies Status:**
- PrimeNG 17.18+ (Stepper, FileUpload) - Available in package.json
- Angular Forms (Reactive) - Available
- RxJS 7.8+ - Available

---

## 6. Approval Checkpoint

**Requesting approval to proceed with Phase 3 implementation.**

Questions for stakeholder:
1. Are the lookup API endpoints (/api/v1/lookup/*) available on the backend?
2. What is the maximum file size for document uploads?
3. Should draft claims auto-save to backend or localStorage only?

---

**Status:** AWAITING APPROVAL

Once approved, implementation will proceed with:
1. Writing test files first (TDD)
2. Implementing components to pass tests
3. Running quality checks
4. Providing deliverables summary
