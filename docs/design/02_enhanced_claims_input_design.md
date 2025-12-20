# Enhanced Claims Input System - Design Document

## Design Review Documentation

**Design Date**: December 19, 2025
**Feature**: Enhanced Claims Input with PDF Document Processing and Auto-Extraction
**Author**: Claude Code (AI Assistant)
**Status**: Ready for Review
**Related Research**: [04_enhanced_claims_input_research.md](../research/04_enhanced_claims_input_research.md)

---

## 1. Executive Summary

### Overview

This design document specifies the implementation of an enhanced claims input interface that accepts:
1. Patient demographics via structured form
2. Policy documents as PDF attachments (one or more)
3. Claim documents as PDF attachments (one or more)
4. Auto-processing with real-time progress tracking
5. Extracted data visualization with manual correction capabilities

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **UI Framework** | Extend existing PrimeNG wizard | Consistency, already installed |
| **File Upload** | PrimeNG FileUpload | Rich UI, drag-drop, Angular 19 native |
| **Processing** | Existing batch-upload API | Backend complete, 90% infrastructure ready |
| **Progress Tracking** | HTTP polling (2s interval) | Simple, reliable, WebSocket as future enhancement |
| **State Management** | Angular Signals | Modern, performant, already in use |

### Scope

**In Scope**:
- New wizard steps for document upload (Policy, Claim docs)
- Processing progress visualization component
- Extracted data display with confidence indicators
- Field-level correction interface
- Data merging from multiple documents

**Out of Scope**:
- WebSocket real-time updates (future enhancement)
- Chunked upload for very large files (future)
- Bulk multi-claim upload (future)
- PDF preview/thumbnail generation (future)

---

## 2. Requirements Specification

### Business Objectives

| ID | Objective | Acceptance Criteria |
|----|-----------|---------------------|
| BO-1 | Reduce manual data entry | 80% of claim fields auto-populated from documents |
| BO-2 | Improve data accuracy | Extraction confidence scores displayed; low-confidence fields flagged |
| BO-3 | Streamline workflow | Single wizard flow from documents to submission |
| BO-4 | Support multiple documents | Upload 1-10 PDFs per document type |
| BO-5 | Enable corrections | Users can edit any extracted field before submission |

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Upload multiple PDF files for policy documents | Must Have |
| FR-2 | Upload multiple PDF files for claim documents | Must Have |
| FR-3 | Display real-time processing progress per document | Must Have |
| FR-4 | Show extracted data with confidence scores | Must Have |
| FR-5 | Allow editing of any extracted field | Must Have |
| FR-6 | Merge data from multiple documents intelligently | Must Have |
| FR-7 | Validate extracted data completeness | Must Have |
| FR-8 | Support drag-and-drop file upload | Should Have |
| FR-9 | Show processing stage labels (OCR, Parsing, etc.) | Should Have |
| FR-10 | Retry failed document processing | Should Have |
| FR-11 | Cancel upload in progress | Could Have |
| FR-12 | Resume interrupted uploads | Could Have |

### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Upload response time | < 2 seconds for file acceptance |
| NFR-2 | Processing time (1-page PDF) | < 15 seconds |
| NFR-3 | Processing time (5-page PDF) | < 40 seconds |
| NFR-4 | Max file size | 50 MB per file |
| NFR-5 | Max files per upload | 10 files |
| NFR-6 | Browser support | Chrome, Firefox, Edge, Safari (latest 2 versions) |
| NFR-7 | Accessibility | WCAG 2.1 AA compliant |
| NFR-8 | HIPAA compliance | PHI encryption, audit logging |

### Constraints

| ID | Constraint | Impact |
|----|------------|--------|
| C-1 | Backend API already defined | Must use existing endpoints |
| C-2 | PrimeNG component library | Use existing components where possible |
| C-3 | Angular 19 + Signals | Follow existing patterns |
| C-4 | 50MB file size limit | Backend enforced |
| C-5 | 10 files max per batch | Backend enforced |

### Stakeholders

| Stakeholder | Interest | Needs |
|-------------|----------|-------|
| Claims Processors | Primary users | Fast, accurate data entry |
| Claims Managers | Oversight | Quality metrics, error reduction |
| IT Operations | Maintenance | Monitoring, troubleshooting |
| Compliance | Regulatory | Audit trail, data security |

---

## 3. Architecture Design

### System Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Angular 19)                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        Enhanced Claims Wizard                            ││
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ││
│  │  │  Step 1   │ │  Step 2   │ │  Step 3   │ │  Step 4   │ │  Step 5   │ ││
│  │  │  Patient  │→│  Policy   │→│  Claim    │→│ Processing│→│  Review   │ ││
│  │  │Demographics│ │   Docs   │ │   Docs    │ │ & Results │ │ & Submit  │ ││
│  │  │ (existing)│ │  (NEW)    │ │  (NEW)    │ │  (NEW)    │ │(enhanced) │ ││
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘ ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                      │                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        Services Layer                                    ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         ││
│  │  │DocumentUpload   │  │DocumentStatus   │  │ExtractedData    │         ││
│  │  │Service          │  │PollingService  │  │MergeService     │         ││
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ HTTPS/TLS 1.3
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (FastAPI)                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        API Layer (Existing)                              ││
│  │  POST /api/v1/documents/batch-upload                                     ││
│  │  GET  /api/v1/documents/{id}/status                                      ││
│  │  GET  /api/v1/documents/{id}/extracted-data                              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                      │                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                     Processing Pipeline (Existing)                       ││
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐              ││
│  │  │ Upload  │ →  │  OCR    │ →  │  LLM    │ →  │Validate │              ││
│  │  │ MinIO   │    │Pipeline │    │ Parser  │    │  Data   │              ││
│  │  └─────────┘    └─────────┘    └─────────┘    └─────────┘              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Interactions

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            User Interaction Flow                              │
└──────────────────────────────────────────────────────────────────────────────┘

User                Frontend Components                Backend APIs
 │                        │                                 │
 │  1. Select PDF files   │                                 │
 │ ───────────────────────>                                 │
 │                        │                                 │
 │                        │  2. POST /batch-upload          │
 │                        │ ─────────────────────────────────>
 │                        │                                 │
 │                        │  3. Return document IDs         │
 │                        │ <─────────────────────────────────
 │                        │                                 │
 │                        │  4. Poll GET /status (2s)       │
 │                        │ ─────────────────────────────────>
 │                        │                                 │
 │  5. Display progress   │  6. Return progress %           │
 │ <───────────────────────                                 │
 │                        │ <─────────────────────────────────
 │                        │                                 │
 │                        │  [Repeat until complete]        │
 │                        │                                 │
 │                        │  7. GET /extracted-data         │
 │                        │ ─────────────────────────────────>
 │                        │                                 │
 │  8. Display results    │  9. Return extracted data       │
 │ <───────────────────────                                 │
 │                        │ <─────────────────────────────────
 │                        │                                 │
 │  10. Edit fields       │                                 │
 │ ───────────────────────>                                 │
 │                        │                                 │
 │  11. Submit claim      │  12. POST /claims               │
 │ ───────────────────────>─────────────────────────────────>
 │                        │                                 │
```

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Data Flow                                       │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌───────────────────┐
                    │   PDF Documents   │
                    │  (Policy + Claim) │
                    └─────────┬─────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  UPLOAD PHASE                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ FormData: files[], document_type, claim_id?                             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  PROCESSING PHASE (Backend - Async)                                          │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐         │
│  │   MinIO    │ → │  OCR Text  │ → │ LLM Parse  │ → │ Validation │         │
│  │  Storage   │   │ Extraction │   │ Structured │   │   Checks   │         │
│  └────────────┘   └────────────┘   └────────────┘   └────────────┘         │
└──────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  EXTRACTED DATA                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ {                                                                        ││
│  │   patient: { name, member_id, dob, gender, address },                   ││
│  │   provider: { name, npi, tax_id, specialty },                           ││
│  │   diagnoses: [{ code, description, confidence }],                       ││
│  │   procedures: [{ code, description, amount, confidence }],              ││
│  │   financial: { total_charged, currency },                               ││
│  │   identifiers: { claim_number, policy_number, prior_auth },             ││
│  │   overall_confidence: 0.87                                              ││
│  │ }                                                                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  MERGE PHASE (Frontend)                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Multiple documents → Merged result with conflict resolution             ││
│  │ Manual edits → Override extracted values                                ││
│  │ Demographics → Pre-fill from Step 1                                     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  FINAL CLAIM SUBMISSION                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ POST /api/v1/claims                                                     ││
│  │ { member, provider, services, documents[], extracted_data }             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────┘
```

### Component Structure

```
frontend/apps/claims-portal/src/app/
├── features/claims/components/claim-submit/
│   ├── claim-submit.component.ts          # Main wizard (MODIFY)
│   ├── step-member/                        # Step 1 - Existing
│   ├── step-policy-docs/                   # Step 2 - NEW
│   │   ├── step-policy-docs.component.ts
│   │   └── step-policy-docs.component.html
│   ├── step-claim-docs/                    # Step 3 - NEW
│   │   ├── step-claim-docs.component.ts
│   │   └── step-claim-docs.component.html
│   ├── step-processing/                    # Step 4 - NEW
│   │   ├── step-processing.component.ts
│   │   ├── step-processing.component.html
│   │   ├── document-progress-card/
│   │   ├── extracted-data-panel/
│   │   └── editable-field/
│   ├── step-provider/                      # Step 5 - Existing (renumber)
│   ├── step-services/                      # Step 6 - Existing (renumber)
│   └── step-review/                        # Step 7 - Existing (MODIFY)
│
├── core/services/
│   ├── document-upload.service.ts          # NEW
│   ├── document-status-polling.service.ts  # NEW
│   └── extracted-data-merge.service.ts     # NEW
│
└── shared/models/
    └── document-processing.models.ts       # NEW
```

---

## 4. API Contracts

### Existing Backend APIs (No Changes Required)

#### POST /api/v1/documents/batch-upload

**Request**:
```typescript
// Content-Type: multipart/form-data
interface BatchUploadRequest {
  files: File[];              // PDF files (max 10)
  document_type: DocumentType; // 'policy' | 'claim_form' | 'invoice' | 'medical_record'
  claim_id?: string;          // Optional association
}
```

**Response** (202 Accepted):
```typescript
interface BatchUploadResponse {
  total: number;
  successful: number;
  failed: number;
  documents: DocumentUploadResult[];
}

interface DocumentUploadResult {
  document_id: string;
  status: 'accepted' | 'failed';
  message: string;
  is_duplicate: boolean;
  processing_started: boolean;
}
```

#### GET /api/v1/documents/{document_id}/status

**Response** (200 OK):
```typescript
interface DocumentProcessingStatus {
  document_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  processing_stage: 'upload' | 'ocr' | 'parsing' | 'validation' | 'complete' | 'failed';
  progress_percent: number;    // 0-100
  ocr_confidence?: number;     // 0.0-1.0
  parsing_confidence?: number; // 0.0-1.0
  needs_review: boolean;
  error?: string;
}
```

#### GET /api/v1/documents/{document_id}/extracted-data

**Response** (200 OK):
```typescript
interface ExtractedDataResponse {
  document_id: string;
  extraction_confidence: number;
  data: ExtractedClaimData;
  needs_review: boolean;
  validation_issues: string[];
}

interface ExtractedClaimData {
  patient: {
    name: string;
    member_id: string;
    date_of_birth: string;
    gender: string;
    address: string;
  };
  provider: {
    name: string;
    npi: string;
    tax_id: string;
    specialty: string;
  };
  diagnoses: DiagnosisCode[];
  procedures: ProcedureCode[];
  financial: {
    total_charged: string;
    currency: string;
  };
  identifiers: {
    claim_number: string;
    prior_auth_number: string;
    policy_number: string;
  };
  dates: {
    service_date_from: string;
    service_date_to: string;
  };
  overall_confidence: number;
}

interface DiagnosisCode {
  code: string;
  description: string;
  is_primary: boolean;
  confidence: number;
}

interface ProcedureCode {
  code: string;
  description: string;
  modifiers: string[];
  quantity: number;
  charged_amount: string;
  service_date: string;
  confidence: number;
}
```

### New Frontend Service Interfaces

#### DocumentUploadService

```typescript
@Injectable({ providedIn: 'root' })
export class DocumentUploadService {
  private readonly http = inject(HttpClient);
  private readonly API_URL = '/api/v1/documents';

  /**
   * Upload batch of PDF files for processing
   */
  uploadBatch(
    files: File[],
    documentType: DocumentType,
    claimId?: string
  ): Observable<BatchUploadResponse> {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('document_type', documentType);
    if (claimId) formData.append('claim_id', claimId);

    return this.http.post<BatchUploadResponse>(
      `${this.API_URL}/batch-upload`,
      formData
    );
  }

  /**
   * Get single document upload (for single file scenarios)
   */
  uploadSingle(
    file: File,
    documentType: DocumentType,
    claimId?: string
  ): Observable<DocumentUploadResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    if (claimId) formData.append('claim_id', claimId);

    return this.http.post<DocumentUploadResult>(
      `${this.API_URL}/upload`,
      formData
    );
  }
}
```

#### DocumentStatusPollingService

```typescript
@Injectable({ providedIn: 'root' })
export class DocumentStatusPollingService {
  private readonly http = inject(HttpClient);
  private readonly API_URL = '/api/v1/documents';
  private readonly POLL_INTERVAL = 2000; // 2 seconds

  /**
   * Poll document status until complete or failed
   * Emits progress updates, completes when done
   */
  pollUntilComplete(documentId: string): Observable<DocumentProcessingStatus> {
    return timer(0, this.POLL_INTERVAL).pipe(
      switchMap(() =>
        this.http.get<DocumentProcessingStatus>(
          `${this.API_URL}/${documentId}/status`
        )
      ),
      takeWhile(
        status =>
          status.status !== 'completed' && status.status !== 'failed',
        true // Include the final emission
      ),
      retryWhen(errors =>
        errors.pipe(
          delay(this.POLL_INTERVAL),
          take(3) // Retry up to 3 times on error
        )
      )
    );
  }

  /**
   * Poll multiple documents in parallel
   */
  pollMultiple(documentIds: string[]): Observable<Map<string, DocumentProcessingStatus>> {
    return combineLatest(
      documentIds.map(id =>
        this.pollUntilComplete(id).pipe(
          map(status => ({ id, status }))
        )
      )
    ).pipe(
      map(results => new Map(results.map(r => [r.id, r.status])))
    );
  }
}
```

#### ExtractedDataMergeService

```typescript
@Injectable({ providedIn: 'root' })
export class ExtractedDataMergeService {
  private readonly http = inject(HttpClient);
  private readonly API_URL = '/api/v1/documents';

  /**
   * Fetch extracted data for a document
   */
  getExtractedData(documentId: string): Observable<ExtractedDataResponse> {
    return this.http.get<ExtractedDataResponse>(
      `${this.API_URL}/${documentId}/extracted-data`
    );
  }

  /**
   * Merge extracted data from multiple documents
   * Uses highest-confidence values when conflicts exist
   */
  mergeExtractedData(
    dataList: ExtractedDataResponse[]
  ): MergedExtractedData {
    // Take highest confidence value for each field
    // Combine all diagnoses and procedures
    // Flag conflicts for user review

    const merged: MergedExtractedData = {
      patient: this.mergePatientData(dataList),
      provider: this.mergeProviderData(dataList),
      diagnoses: this.mergeDiagnoses(dataList),
      procedures: this.mergeProcedures(dataList),
      financial: this.mergeFinancial(dataList),
      identifiers: this.mergeIdentifiers(dataList),
      conflicts: [],
      overallConfidence: this.calculateOverallConfidence(dataList),
    };

    return merged;
  }

  private mergePatientData(dataList: ExtractedDataResponse[]): PatientData {
    // Select field values with highest confidence
    // Track conflicts where values differ significantly
  }

  // ... other merge methods
}

interface MergedExtractedData extends ExtractedClaimData {
  conflicts: DataConflict[];
  fieldSources: Map<string, string>; // field path -> document_id
}

interface DataConflict {
  field: string;
  values: { documentId: string; value: any; confidence: number }[];
  resolvedValue: any;
  resolvedFrom: string;
  requiresReview: boolean;
}
```

---

## 5. Technology Stack

### Frontend Technologies (No New Dependencies)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| Angular | 19.x | Framework | Existing |
| PrimeNG | 19.x | UI Components | Existing |
| RxJS | 7.x | Reactive programming | Existing |
| Angular Signals | Built-in | State management | Existing |

### Components to Use

| Component | Package | Purpose |
|-----------|---------|---------|
| `p-fileUpload` | primeng/fileupload | File upload with drag-drop |
| `p-steps` | primeng/steps | Wizard navigation |
| `p-progressBar` | primeng/progressbar | Processing progress |
| `p-accordion` | primeng/accordion | Collapsible data sections |
| `p-table` | primeng/table | Diagnosis/procedure lists |
| `p-badge` | primeng/badge | Confidence indicators |
| `p-tag` | primeng/tag | Status labels |
| `p-inputText` | primeng/inputtext | Editable fields |
| `p-toast` | primeng/toast | Notifications |

### Backend Technologies (Existing - No Changes)

| Technology | Purpose | Status |
|------------|---------|--------|
| FastAPI | API framework | Existing |
| MinIO | Document storage | Existing |
| PaddleOCR | Primary OCR | Existing |
| Ollama/OpenAI | LLM parsing | Existing |

---

## 6. Security Design

### Threat Model (STRIDE Analysis)

| Threat | Category | Mitigation |
|--------|----------|------------|
| Malicious file upload | Tampering | File type validation, size limits, antivirus scan (recommended) |
| Unauthorized access | Spoofing | JWT authentication, auth guards |
| Data interception | Information Disclosure | TLS 1.3 encryption |
| Session hijacking | Elevation of Privilege | Token expiration, refresh tokens |
| XSS via filename | Tampering | Filename sanitization |
| Path traversal | Tampering | UUID-based storage paths |

### OWASP Top 10 Mapping

| OWASP Risk | Applicable | Control |
|------------|-----------|---------|
| A01:2021 Broken Access Control | Yes | RBAC, tenant isolation |
| A02:2021 Cryptographic Failures | Yes | AES-256, TLS 1.3 |
| A03:2021 Injection | Low | No user input in queries |
| A04:2021 Insecure Design | N/A | Security by design |
| A05:2021 Security Misconfiguration | Yes | Secure defaults |
| A06:2021 Vulnerable Components | Yes | Dependency scanning |
| A07:2021 Auth Failures | Yes | JWT, MFA ready |
| A08:2021 Data Integrity Failures | Yes | File hash verification |
| A09:2021 Security Logging | Yes | Audit trail |
| A10:2021 SSRF | Low | No external URL processing |

### Data Protection Controls

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Security Layers                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 1: Transport                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ TLS 1.3 encryption for all API calls                                    ││
│  │ HTTPS enforced via redirect                                             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 2: Authentication                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ JWT tokens with short expiration (15 min access, 7 day refresh)         ││
│  │ AuthGuard on all routes                                                 ││
│  │ Token refresh on API calls                                              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 3: Authorization                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Permission: documents:upload required                                   ││
│  │ Permission: documents:read required                                     ││
│  │ Tenant isolation via middleware                                         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 4: Storage                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ MinIO with AES-256 encryption at rest                                   ││
│  │ Tenant-isolated buckets                                                 ││
│  │ UUID-based file paths (no user input)                                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 5: Audit                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Upload events logged with user, timestamp, document ID                  ││
│  │ Access events logged                                                    ││
│  │ Immutable audit trail                                                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### File Upload Security

```typescript
// Client-side validation (defense in depth)
const ALLOWED_MIME_TYPES = ['application/pdf'];
const ALLOWED_EXTENSIONS = ['.pdf'];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

function validateFile(file: File): ValidationResult {
  // Check extension
  const extension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return { valid: false, error: 'Only PDF files are allowed' };
  }

  // Check MIME type
  if (!ALLOWED_MIME_TYPES.includes(file.type)) {
    return { valid: false, error: 'Invalid file type' };
  }

  // Check size
  if (file.size > MAX_FILE_SIZE) {
    return { valid: false, error: 'File exceeds 50MB limit' };
  }

  // Sanitize filename for display
  const sanitizedName = file.name.replace(/[<>:"/\\|?*]/g, '_');

  return { valid: true, sanitizedName };
}
```

---

## 7. Performance Plan

### Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Upload acceptance | < 2 seconds | Time to receive 202 response |
| Progress update | < 500ms | Polling response time |
| UI responsiveness | < 100ms | Interaction response |
| Memory usage | < 100MB | Browser heap size |
| Bundle size impact | < 50KB | Gzipped delta |

### Optimization Strategies

#### 1. Lazy Loading
```typescript
// Wizard steps lazy loaded via dynamic imports
const routes: Routes = [
  {
    path: 'claims/new',
    loadComponent: () =>
      import('./claim-submit/claim-submit.component')
        .then(m => m.ClaimSubmitComponent),
  },
];
```

#### 2. Efficient Polling
```typescript
// Use shareReplay to avoid duplicate polls
pollStatus(id: string) {
  return this.http.get<Status>(`/api/v1/documents/${id}/status`).pipe(
    shareReplay({ bufferSize: 1, refCount: true })
  );
}

// Stop polling immediately on completion
takeWhile(status => !['completed', 'failed'].includes(status.status), true)
```

#### 3. Progress Aggregation
```typescript
// Computed signal for overall progress - no subscriptions
readonly overallProgress = computed(() => {
  const docs = this.documents();
  if (docs.length === 0) return 0;
  return docs.reduce((sum, d) => sum + d.progressPercent, 0) / docs.length;
});
```

#### 4. File Streaming
```typescript
// Use native FormData - no base64 encoding
const formData = new FormData();
formData.append('file', file); // File object, not bytes

// Stream uploads via browser's native fetch
this.http.post(url, formData, {
  reportProgress: true,
  observe: 'events'
});
```

### Caching Strategy

| Data | Cache Location | TTL | Invalidation |
|------|---------------|-----|--------------|
| Document status | Memory (signal) | Real-time | On poll update |
| Extracted data | Memory (signal) | Session | On edit |
| Member lookup | Service cache | 5 min | Manual refresh |
| Provider lookup | Service cache | 5 min | Manual refresh |

---

## 8. Risk Register

| ID | Risk | Probability | Impact | Mitigation | Owner |
|----|------|-------------|--------|------------|-------|
| R1 | Large PDF causes timeout | Medium | Medium | Show estimated time, allow retry | Dev Team |
| R2 | Low OCR confidence | High | Medium | Flag for review, manual entry fallback | Dev Team |
| R3 | Multiple documents conflict | Medium | Low | Show comparison, let user choose | Dev Team |
| R4 | Network interruption | Medium | Medium | Auto-retry, progress persistence | Dev Team |
| R5 | Backend API changes | Low | High | API versioning, contract tests | Dev Team |
| R6 | Browser compatibility | Low | Medium | Progressive enhancement, polyfills | Dev Team |
| R7 | Memory leak on large batches | Low | Medium | Cleanup on destroy, streaming | Dev Team |
| R8 | User abandons mid-upload | Medium | Low | Draft saving, resume capability | Future |

### Risk Mitigation Details

#### R1: Large PDF Timeout
```typescript
// Show estimated processing time based on page count
readonly estimatedTime = computed(() => {
  const pageCount = this.estimatedPages();
  const secondsPerPage = 8; // Based on benchmarks
  return Math.ceil(pageCount * secondsPerPage);
});

// Display to user
<div class="estimate">
  Estimated processing time: {{ estimatedTime() }} seconds
</div>
```

#### R2: Low OCR Confidence
```typescript
// Visual indicator for low confidence
getConfidenceSeverity(confidence: number): string {
  if (confidence >= 0.85) return 'success';
  if (confidence >= 0.70) return 'warning';
  return 'danger';
}

// Automatic flagging
readonly needsReview = computed(() =>
  this.documents().some(d =>
    d.ocrConfidence < 0.70 || d.parsingConfidence < 0.70
  )
);
```

#### R3: Document Conflicts
```typescript
// Conflict resolution UI
interface ConflictResolution {
  field: string;
  options: { source: string; value: any; confidence: number }[];
  selected?: string;
}

// Let user pick which value to use
<div class="conflict-resolver" *ngFor="let conflict of conflicts">
  <span class="field-name">{{ conflict.field }}</span>
  <div class="options">
    <button *ngFor="let opt of conflict.options"
            [class.selected]="conflict.selected === opt.source"
            (click)="resolveConflict(conflict, opt.source)">
      {{ opt.value }} ({{ opt.confidence * 100 | number:'1.0-0' }}%)
      <small>from {{ opt.source }}</small>
    </button>
  </div>
</div>
```

---

## 9. Implementation Roadmap

### Phase 1: Core Upload Components (3-4 days)

| Task | Effort | Dependencies |
|------|--------|--------------|
| Create `StepPolicyDocsComponent` | 1 day | None |
| Create `StepClaimDocsComponent` | 1 day | StepPolicyDocsComponent |
| Create `DocumentUploadService` | 0.5 day | None |
| Create `DocumentStatusPollingService` | 0.5 day | DocumentUploadService |
| Update wizard navigation | 0.5 day | All above |
| Unit tests | 0.5 day | All above |

**Deliverable**: Users can upload policy and claim PDFs, processing starts automatically.

### Phase 2: Processing & Results Display (3-4 days)

| Task | Effort | Dependencies |
|------|--------|--------------|
| Create `StepProcessingComponent` | 1.5 days | Phase 1 |
| Create progress card subcomponent | 0.5 day | StepProcessingComponent |
| Create extracted data panel | 1 day | StepProcessingComponent |
| Create editable field component | 0.5 day | Extracted data panel |
| Create `ExtractedDataMergeService` | 0.5 day | Phase 1 |
| Unit tests | 0.5 day | All above |

**Deliverable**: Users see real-time progress and can view/edit extracted data.

### Phase 3: Integration & Polish (2-3 days)

| Task | Effort | Dependencies |
|------|--------|--------------|
| Update `StepReviewComponent` | 1 day | Phases 1-2 |
| Data merging from demographics + documents | 0.5 day | Phase 2 |
| Error handling & edge cases | 0.5 day | All |
| Accessibility improvements | 0.5 day | All |
| E2E tests | 0.5 day | All |
| Documentation | 0.5 day | All |

**Deliverable**: Complete flow from upload to submission, production ready.

### Milestone Schedule

```
Week 1                           Week 2
┌─────┬─────┬─────┬─────┬─────┐ ┌─────┬─────┬─────┬─────┬─────┐
│ Mon │ Tue │ Wed │ Thu │ Fri │ │ Mon │ Tue │ Wed │ Thu │ Fri │
├─────┴─────┴─────┴─────┴─────┤ ├─────┴─────┴─────┴─────┴─────┤
│     Phase 1: Core Upload     │ │ Phase 2: Processing Display │
│ ████████████████████████████ │ │ ████████████████████████████│
└──────────────────────────────┘ └──────────────────────────────┘
                                          │
                                          ▼
                                 Week 2 (cont) / Week 3
                                 ┌─────┬─────┬─────┐
                                 │ Mon │ Tue │ Wed │
                                 ├─────┴─────┴─────┤
                                 │Phase 3: Polish  │
                                 │ ████████████████│
                                 └─────────────────┘
                                          │
                                          ▼
                                    ✓ Production Ready
```

### Testing Strategy

| Test Type | Coverage | Tools |
|-----------|----------|-------|
| Unit Tests | Services, Components | Jest, Angular Testing Library |
| Integration Tests | API calls, state management | Jest, HttpClientTestingModule |
| E2E Tests | Complete wizard flow | Playwright |
| Visual Regression | UI consistency | Chromatic (optional) |

```typescript
// Example unit test for DocumentUploadService
describe('DocumentUploadService', () => {
  it('should upload batch of files', () => {
    const files = [new File([''], 'test.pdf', { type: 'application/pdf' })];
    service.uploadBatch(files, 'claim_form').subscribe(response => {
      expect(response.successful).toBe(1);
      expect(response.documents[0].processing_started).toBe(true);
    });

    const req = httpMock.expectOne('/api/v1/documents/batch-upload');
    expect(req.request.method).toBe('POST');
    expect(req.request.body instanceof FormData).toBe(true);
  });
});
```

---

## 10. Open Questions

| ID | Question | Status | Decision Needed By |
|----|----------|--------|-------------------|
| OQ-1 | Should we combine Policy and Claim docs into single step? | Open | Design Review |
| OQ-2 | Should users be able to skip document upload? | Open | Product Owner |
| OQ-3 | What happens if OCR completely fails on a document? | Open | Design Review |
| OQ-4 | Should we show PDF preview before upload? | Deferred | Phase 2 |
| OQ-5 | Do we need document reordering capability? | Open | Product Owner |
| OQ-6 | Should extracted data be auto-saved to draft? | Open | Product Owner |

### Recommendations for Open Questions

**OQ-1**: Recommend separate steps for clarity. Policy docs and claim docs serve different purposes and may have different processing requirements.

**OQ-2**: Recommend allowing skip with confirmation. Some claims may not have attachments, but user should explicitly acknowledge.

**OQ-3**: Recommend showing error with retry option. User can:
1. Retry processing
2. Upload different scan
3. Proceed with manual entry

**OQ-6**: Recommend auto-save every 30 seconds during processing to prevent data loss.

---

## Validation Checklist

- [x] Business requirements clearly mapped to technical solution
- [x] All integration points identified and specified
- [x] Security requirements addressed (HIPAA, OWASP)
- [x] Performance requirements defined
- [x] Risks identified with mitigation strategies
- [x] Implementation broken into manageable phases
- [x] Technology choices justified with evidence
- [ ] Open questions resolved (pending user review)

---

**Document Version**: 1.0
**Created**: December 19, 2025
**Last Updated**: December 19, 2025
**Status**: Ready for User Review
**Next Step**: Review open questions, approve design, proceed to implementation
