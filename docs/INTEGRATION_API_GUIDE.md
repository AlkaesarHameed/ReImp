# Medical Claims Processing System - Integration API Guide

**Version:** 1.0.0
**Last Updated:** December 19, 2024
**Author:** Development Team

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [API Layer Structure](#2-api-layer-structure)
3. [Claims API Service](#3-claims-api-service)
4. [Lookup API Service](#4-lookup-api-service)
5. [Eligibility API Service](#5-eligibility-api-service)
6. [Users API Service](#6-users-api-service)
7. [Mock API Pattern](#7-mock-api-pattern)
8. [Data Models](#8-data-models)
9. [Authentication & Security](#9-authentication--security)
10. [Metronic Template Integration](#10-metronic-template-integration)
11. [Error Handling](#11-error-handling)
12. [Best Practices](#12-best-practices)

---

## 1. Architecture Overview

### 1.1 System Architecture

```
+------------------+     +------------------+     +------------------+
|                  |     |                  |     |                  |
|  Angular 19 UI   |<--->|  API Client Lib  |<--->|  FastAPI Backend |
|  (claims-portal) |     |  (@claims-       |     |  (Python 3.11+)  |
|                  |     |  processing/     |     |                  |
|                  |     |  api-client)     |     |                  |
+------------------+     +------------------+     +------------------+
        |                        |                        |
        v                        v                        v
+------------------+     +------------------+     +------------------+
|  Metronic Theme  |     |  Shared Models   |     |  PostgreSQL DB   |
|  (Bootstrap 5)   |     |  (@claims-       |     |  (Claims Data)   |
|                  |     |  processing/     |     |                  |
|                  |     |  models)         |     |                  |
+------------------+     +------------------+     +------------------+
```

### 1.2 NX Monorepo Structure

```
frontend/
├── apps/
│   └── claims-portal/           # Main Angular application
│       ├── src/
│       │   ├── app/
│       │   │   ├── _metronic/   # Metronic layout components
│       │   │   ├── core/        # Core services, guards, interceptors
│       │   │   ├── features/    # Feature modules
│       │   │   └── shared/      # Shared components
│       │   └── assets/          # Static assets, Metronic CSS
│       └── project.json
│
├── libs/
│   ├── api-client/              # HTTP API services
│   │   └── src/
│   │       ├── claims.api.ts    # Claims CRUD operations
│   │       ├── lookup.api.ts    # Medical code lookups
│   │       ├── eligibility.api.ts
│   │       ├── users.api.ts
│   │       └── index.ts
│   │
│   └── shared/
│       └── models/              # TypeScript interfaces
│           └── src/
│               ├── claim.model.ts
│               ├── member.model.ts
│               ├── provider.model.ts
│               ├── policy.model.ts
│               ├── lookup.model.ts
│               ├── user.model.ts
│               ├── eligibility.model.ts
│               └── index.ts
│
└── package.json
```

---

## 2. API Layer Structure

### 2.1 API Client Library

The API client library (`@claims-processing/api-client`) provides typed HTTP services for all backend operations.

**Import Path:**
```typescript
import { ClaimsApiService, LookupApiService, EligibilityApiService, UsersApiService } from '@claims-processing/api-client';
```

### 2.2 Service Registration

All API services are registered as `providedIn: 'root'` singletons:

```typescript
@Injectable({
  providedIn: 'root',
})
export class ClaimsApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/claims`;
  // ...
}
```

### 2.3 Environment Configuration

```typescript
// environments/environment.ts (development)
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1',
};

// environments/environment.prod.ts (production)
export const environment = {
  production: true,
  apiUrl: '/api/v1',
};
```

---

## 3. Claims API Service

### 3.1 Overview

The Claims API Service handles all claim-related CRUD operations and workflow actions.

**File:** `libs/api-client/src/claims.api.ts`

### 3.2 CRUD Operations

#### Get Claims (Paginated)
```typescript
getClaims(params?: ClaimsQueryParams): Observable<PaginatedResponse<Claim>>

// Usage
this.claimsApi.getClaims({
  status: ClaimStatus.SUBMITTED,
  page: 1,
  size: 20,
  sortBy: 'created_at',
  sortOrder: 'desc'
}).subscribe(response => {
  console.log(response.items);  // Claim[]
  console.log(response.total);  // Total count
});
```

#### Query Parameters
```typescript
interface ClaimsQueryParams {
  status?: ClaimStatus;           // Filter by status
  claimType?: ClaimType;          // PROFESSIONAL, INSTITUTIONAL, DENTAL, etc.
  priority?: ClaimPriority;       // LOW, NORMAL, HIGH, URGENT
  search?: string;                // Search by ID, tracking number, member
  memberId?: string;              // Filter by member
  providerId?: string;            // Filter by provider
  dateFrom?: string;              // Service date range start
  dateTo?: string;                // Service date range end
  page?: number;                  // Page number (1-based)
  size?: number;                  // Items per page
  sortBy?: string;                // Sort field
  sortOrder?: 'asc' | 'desc';     // Sort direction
}
```

#### Get Single Claim
```typescript
getClaim(claimId: string): Observable<Claim>

// Usage
this.claimsApi.getClaim('CLM-00001').subscribe(claim => {
  console.log(claim.status);
  console.log(claim.total_charged);
});
```

#### Create Claim
```typescript
createClaim(claim: ClaimCreate): Observable<Claim>

// Usage
const newClaim: ClaimCreate = {
  member_id: 'MEM-001',
  provider_id: 'PRV-001',
  policy_id: 'POL-001',
  claim_type: ClaimType.PROFESSIONAL,
  service_date_from: '2024-12-15',
  service_date_to: '2024-12-15',
  diagnosis_codes: ['J06.9'],
  primary_diagnosis: 'J06.9',
  place_of_service: '11',
  total_charged: 250.00,
  line_items: [{
    procedure_code: '99213',
    procedure_code_system: 'CPT-4',
    service_date: '2024-12-15',
    quantity: 1,
    unit_price: 250.00,
    charged_amount: 250.00,
  }],
};

this.claimsApi.createClaim(newClaim).subscribe(createdClaim => {
  console.log('Created:', createdClaim.id);
});
```

#### Update Claim
```typescript
updateClaim(claimId: string, updates: Partial<ClaimUpdate>): Observable<Claim>
```

#### Delete Claim
```typescript
deleteClaim(claimId: string): Observable<void>
```

### 3.3 Workflow Operations

```typescript
// Submit a draft claim for processing
submitClaim(claimId: string): Observable<Claim>

// Approve a claim
approveClaim(claimId: string, action?: Partial<ClaimAction>): Observable<Claim>

// Deny a claim
denyClaim(claimId: string, action: Partial<ClaimAction>): Observable<Claim>

// Validate without submitting
validateClaim(claimId: string): Observable<ClaimValidationResult>

// Pend for additional information
pendClaim(claimId: string, action: Partial<ClaimAction>): Observable<Claim>

// Void a claim
voidClaim(claimId: string, action: Partial<ClaimAction>): Observable<Claim>
```

### 3.4 Bulk Operations

```typescript
// Bulk approve
bulkApprove(claimIds: string[], notes?: string): Observable<Claim[]>

// Bulk deny
bulkDeny(claimIds: string[], reason: string, notes?: string): Observable<Claim[]>

// Export to CSV
exportClaims(params?: ClaimsQueryParams): Observable<Blob>
```

### 3.5 Statistics

```typescript
getClaimStats(params?: ClaimStatsParams): Observable<ClaimStats>

interface ClaimStatsParams {
  dateFrom?: string;
  dateTo?: string;
  groupBy?: 'day' | 'week' | 'month';
}
```

---

## 4. Lookup API Service

### 4.1 Overview

The Lookup API Service provides medical code lookups with caching for static data.

**File:** `libs/api-client/src/lookup.api.ts`

### 4.2 ICD-10 Diagnosis Codes

```typescript
// Search codes
searchICD10(query: string, limit?: number): Observable<LookupResponse<ICD10Code>>

// Validate a code
validateICD10(code: string): Observable<CodeValidationResult>

// Get code details
getICD10Code(code: string): Observable<ICD10Code>

// Usage
this.lookupApi.searchICD10('diabetes', 10).subscribe(response => {
  response.items.forEach(code => {
    console.log(`${code.code}: ${code.description}`);
  });
});
```

### 4.3 CPT Procedure Codes

```typescript
searchCPT(query: string, limit?: number): Observable<LookupResponse<CPTCode>>
validateCPT(code: string): Observable<CodeValidationResult>
getCPTCode(code: string): Observable<CPTCode>
```

### 4.4 HCPCS Codes

```typescript
searchHCPCS(query: string, limit?: number): Observable<LookupResponse<HCPCSCode>>
validateHCPCS(code: string): Observable<CodeValidationResult>
getHCPCSCode(code: string): Observable<HCPCSCode>
```

### 4.5 Static Lookups (Cached)

```typescript
// Place of Service codes (cached)
getPlaceOfServiceCodes(): Observable<PlaceOfServiceCode[]>

// Denial reason codes (cached)
getDenialReasonCodes(category?: string): Observable<DenialReasonCode[]>

// Modifier codes (cached)
getModifierCodes(system?: 'CPT' | 'HCPCS'): Observable<ModifierCode[]>

// Clear caches
clearCaches(): void
```

### 4.6 Utility Methods

```typescript
// Validate any code type
validateCode(code: string, codeType: 'ICD10' | 'CPT' | 'HCPCS'): Observable<CodeValidationResult>

// Search any code type
searchCodes(query: string, codeType: 'ICD10' | 'CPT' | 'HCPCS', limit?: number): Observable<LookupResponse<...>>
```

---

## 5. Eligibility API Service

### 5.1 Overview

The Eligibility API Service handles member eligibility verification and coverage checks.

### 5.2 Eligibility Operations

```typescript
// Check member eligibility
checkEligibility(request: EligibilityCheck): Observable<EligibilityResult>

// Get eligibility history
getEligibilityHistory(memberId: string): Observable<EligibilityHistory>

// Batch eligibility check
batchCheckEligibility(checks: BatchEligibilityCheck): Observable<BatchEligibilityResponse>

// Get coverage details
getCoverageDetails(memberId: string, serviceDate: string): Observable<CoverageDetail[]>

// Get accumulators (deductibles, out-of-pocket)
getAccumulators(memberId: string, policyId: string): Observable<Accumulators>
```

---

## 6. Users API Service

### 6.1 Overview

The Users API Service manages user accounts, roles, and permissions.

### 6.2 User Operations

```typescript
// Get users (paginated)
getUsers(params?: UserQueryParams): Observable<PaginatedResponse<User>>

// Get single user
getUser(userId: string): Observable<User>

// Create user
createUser(user: UserCreate): Observable<User>

// Update user
updateUser(userId: string, updates: UserUpdate): Observable<User>

// Delete user
deleteUser(userId: string): Observable<void>

// Get current user profile
getCurrentUser(): Observable<UserProfile>

// Update profile
updateProfile(updates: Partial<UserProfile>): Observable<UserProfile>

// Change password
changePassword(request: PasswordChangeRequest): Observable<void>
```

---

## 7. Mock API Pattern

### 7.1 Overview

The system includes a mock API layer for development without a backend server.

### 7.2 Enabling Mock Mode

```typescript
// In claims.api.ts
const ENABLE_MOCK_API = !environment.production;
```

When `ENABLE_MOCK_API` is `true`:
- All API calls use mock implementations
- Data is stored in-memory (persists during session)
- Simulated network delays are added

### 7.3 Mock Implementation Pattern

```typescript
// Example: Mock getClaims
getClaims(params?: ClaimsQueryParams): Observable<PaginatedResponse<Claim>> {
  if (ENABLE_MOCK_API) {
    return this.getMockClaims(params);
  }
  // Real HTTP implementation
  return this.http.get<PaginatedResponse<Claim>>(this.baseUrl, {
    params: httpParams,
    withCredentials: true,
  });
}

private getMockClaims(params?: ClaimsQueryParams): Observable<PaginatedResponse<Claim>> {
  initMockClaims();  // Initialize sample data if empty

  let claims = Array.from(mockClaimsStore.values());

  // Apply filters
  if (params?.status) {
    claims = claims.filter(c => c.status === params.status);
  }

  // Pagination
  const page = params?.page || 1;
  const size = params?.size || 20;
  const start = (page - 1) * size;
  const paginatedClaims = claims.slice(start, start + size);

  // Simulate network delay
  return of({
    items: paginatedClaims,
    total: claims.length,
    page,
    size,
  }).pipe(delay(300));
}
```

### 7.4 In-Memory Store

```typescript
// Persistent storage for mock data
const mockClaimsStore: Map<string, Claim> = new Map();

// Initialize with sample data
function initMockClaims(): void {
  if (mockClaimsStore.size > 0) return;

  const sampleClaims: Claim[] = [
    {
      id: 'CLM-00001',
      tracking_number: 'CLM-00001',
      status: ClaimStatus.APPROVED,
      // ... other fields
    },
    // More sample claims...
  ];

  sampleClaims.forEach(claim => mockClaimsStore.set(claim.id, claim));
}
```

### 7.5 Mock Claim Creation

```typescript
private createMockClaim(claimData: ClaimCreate): Observable<Claim> {
  const claimId = `CLM-${Date.now().toString().slice(-8)}`;
  const now = new Date().toISOString();

  const mockClaim: Claim = {
    id: claimId,
    tracking_number: claimId,
    status: ClaimStatus.SUBMITTED,
    // Map from ClaimCreate to Claim
    // Calculate allowed amounts (80% of charged)
    total_allowed: claimData.total_charged * 0.8,
    patient_responsibility: claimData.total_charged * 0.2,
    // ... other fields
  };

  // Store in mock store
  mockClaimsStore.set(claimId, mockClaim);

  return of(mockClaim).pipe(delay(800));
}
```

---

## 8. Data Models

### 8.1 Import Path

```typescript
import {
  Claim,
  ClaimCreate,
  ClaimStatus,
  ClaimType,
  Member,
  Provider,
  // ...
} from '@claims-processing/models';
```

### 8.2 Claim Model

```typescript
interface Claim {
  id: string;
  tracking_number: string;
  policy_id: string;
  member_id: string;
  provider_id: string;
  claim_type: ClaimType;
  status: ClaimStatus;
  priority: ClaimPriority;
  service_date_from: string;
  service_date_to: string;
  diagnosis_codes: string[];
  primary_diagnosis: string;
  place_of_service?: string;
  prior_auth_number?: string;
  total_charged: number;
  total_allowed?: number;
  total_paid?: number;
  patient_responsibility?: number;
  line_items: ClaimLineItem[];
  attachments?: ClaimAttachment[];
  notes?: ClaimNote[];
  created_at: string;
  updated_at: string;
  submitted_at?: string;
  processed_at?: string;
}

enum ClaimStatus {
  DRAFT = 'draft',
  SUBMITTED = 'submitted',
  DOC_PROCESSING = 'doc_processing',
  VALIDATING = 'validating',
  ADJUDICATING = 'adjudicating',
  APPROVED = 'approved',
  DENIED = 'denied',
  PAYMENT_PROCESSING = 'payment_processing',
  PAID = 'paid',
  CLOSED = 'closed',
  NEEDS_REVIEW = 'needs_review',
  VOID = 'void',
}

enum ClaimType {
  PROFESSIONAL = 'professional',
  INSTITUTIONAL = 'institutional',
  DENTAL = 'dental',
  PHARMACY = 'pharmacy',
  VISION = 'vision',
}
```

### 8.3 Claim Line Item

```typescript
interface ClaimLineItem {
  id?: string;
  line_number: number;
  procedure_code: string;
  procedure_code_system: string;
  modifier_codes?: string[];
  service_date: string;
  quantity: number;
  unit_price: number;
  charged_amount: number;
  allowed_amount?: number;
  paid_amount?: number;
  denied: boolean;
  denial_reason?: string;
}
```

### 8.4 Member Model

```typescript
interface Member {
  id: string;
  member_id: string;
  first_name: string;
  last_name: string;
  middle_name?: string;
  date_of_birth: string;
  gender: Gender;
  ssn?: string;
  email?: string;
  phone?: string;
  address: Address;
  status: MemberStatus;
  relationship: RelationshipType;
  policy_id: string;
  effective_date: string;
  termination_date?: string;
}
```

### 8.5 Provider Model

```typescript
interface Provider {
  id: string;
  npi: string;
  name: string;
  first_name?: string;
  last_name?: string;
  provider_type: ProviderType;
  specialty?: string;
  tax_id?: string;
  address: ProviderAddress;
  phone?: string;
  fax?: string;
  email?: string;
  network_status: NetworkStatus;
  status: ProviderStatus;
  effective_date: string;
  termination_date?: string;
}
```

### 8.6 Lookup Response

```typescript
interface LookupResponse<T> {
  items: T[];
  total: number;
  query: string;
}

interface CodeValidationResult {
  valid: boolean;
  code: string;
  message?: string;
  suggestions?: string[];
}
```

---

## 9. Authentication & Security

### 9.1 HTTP Only Cookies

All API requests include credentials for cookie-based authentication:

```typescript
return this.http.get<T>(url, {
  withCredentials: true,  // Include HttpOnly cookies
});
```

### 9.2 Auth Interceptor

```typescript
// core/interceptors/auth.interceptor.ts
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  // Clone request with credentials
  const authReq = req.clone({
    withCredentials: true,
  });

  return next(authReq).pipe(
    catchError(error => {
      if (error.status === 401) {
        // Redirect to login
        inject(Router).navigate(['/auth/login']);
      }
      return throwError(() => error);
    })
  );
};
```

### 9.3 CSRF Protection

The backend includes CSRF tokens in responses. The frontend should include them in mutation requests.

---

## 10. Metronic Template Integration

### 10.1 Overview

The application uses the Metronic Angular Template v8.3.2 Demo7 for UI components and styling.

### 10.2 Integrated Components

```
apps/claims-portal/src/
├── app/
│   └── _metronic/
│       ├── layout/           # Main layout components
│       │   ├── components/
│       │   │   ├── aside/    # Sidebar navigation
│       │   │   ├── header/   # Top header
│       │   │   ├── footer/   # Footer
│       │   │   ├── toolbar/  # Page toolbar
│       │   │   └── content/  # Content wrapper
│       │   └── core/         # Layout services
│       ├── partials/         # Reusable UI components
│       ├── kt/               # Keenthemes utilities
│       └── shared/           # Shared pipes, directives
│
└── assets/
    ├── metronic-styles.css   # Compiled Metronic CSS
    ├── keenicons-*.{woff,ttf,eot,svg}  # Icon fonts
    ├── sass/                 # SCSS source files
    ├── plugins/              # Keenicons, third-party plugins
    └── media/                # Images, SVG icons
```

### 10.3 Style Configuration

```json
// project.json
{
  "styles": [
    "apps/claims-portal/src/assets/metronic-styles.css",
    "apps/claims-portal/src/assets/plugins/keenicons/duotone/style.css",
    "apps/claims-portal/src/assets/plugins/keenicons/outline/style.css",
    "apps/claims-portal/src/assets/plugins/keenicons/solid/style.css",
    "node_modules/primeng/resources/themes/lara-light-blue/theme.css",
    "node_modules/primeng/resources/primeng.min.css",
    "node_modules/primeicons/primeicons.css",
    "node_modules/primeflex/primeflex.css",
    "apps/claims-portal/src/styles/styles.scss"
  ]
}
```

### 10.4 Dependencies Added

```json
{
  "dependencies": {
    "@ng-bootstrap/ng-bootstrap": "^17.0.0",
    "@angular/localize": "^19.2.0",
    "@ngx-translate/core": "^15.0.0",
    "@ngx-translate/http-loader": "^8.0.0",
    "bootstrap": "^5.3.2",
    "bootstrap-icons": "^1.10.3",
    "@fortawesome/fontawesome-free": "^6.3.0",
    "@popperjs/core": "^2.11.8",
    "ng-inline-svg-2": "^15.0.1"
  }
}
```

### 10.5 UI Component Libraries

The application uses **two UI libraries** that coexist:

1. **Metronic/Bootstrap** - Layout, navigation, styling
2. **PrimeNG** - Forms, tables, dialogs, data components

This hybrid approach allows using Metronic's polished admin template styling while leveraging PrimeNG's powerful form and data components.

---

## 11. Error Handling

### 11.1 HTTP Error Interceptor

```typescript
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      let message = 'An error occurred';

      if (error.error instanceof ErrorEvent) {
        // Client-side error
        message = error.error.message;
      } else {
        // Server-side error
        switch (error.status) {
          case 400:
            message = error.error?.detail || 'Bad request';
            break;
          case 401:
            message = 'Unauthorized - Please log in';
            break;
          case 403:
            message = 'Access denied';
            break;
          case 404:
            message = 'Resource not found';
            break;
          case 422:
            message = formatValidationErrors(error.error?.detail);
            break;
          case 500:
            message = 'Internal server error';
            break;
        }
      }

      // Show toast notification
      inject(MessageService).add({
        severity: 'error',
        summary: 'Error',
        detail: message,
      });

      return throwError(() => error);
    })
  );
};
```

### 11.2 API Response Pattern

```typescript
// Success response
interface ApiResponse<T> {
  data: T;
  message?: string;
}

// Error response
interface ApiError {
  detail: string | ValidationError[];
  code?: string;
}

interface ValidationError {
  loc: string[];
  msg: string;
  type: string;
}
```

---

## 12. Best Practices

### 12.1 Service Injection

Use Angular's `inject()` function for dependency injection:

```typescript
@Injectable({ providedIn: 'root' })
export class ClaimsService {
  private readonly claimsApi = inject(ClaimsApiService);
  private readonly messageService = inject(MessageService);
}
```

### 12.2 Observable Handling

Always unsubscribe from observables to prevent memory leaks:

```typescript
// Using takeUntilDestroyed
export class ClaimsListComponent {
  private readonly destroyRef = inject(DestroyRef);

  ngOnInit() {
    this.claimsApi.getClaims()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(response => {
        this.claims = response.items;
      });
  }
}

// Or using async pipe in template
@Component({
  template: `
    @for (claim of claims$ | async; track claim.id) {
      <div>{{ claim.tracking_number }}</div>
    }
  `
})
export class ClaimsListComponent {
  claims$ = this.claimsApi.getClaims().pipe(
    map(response => response.items)
  );
}
```

### 12.3 Type Safety

Always use typed interfaces for API responses:

```typescript
// Good
getClaims(): Observable<PaginatedResponse<Claim>>

// Avoid
getClaims(): Observable<any>
```

### 12.4 Error Handling

Handle errors gracefully in components:

```typescript
this.claimsApi.createClaim(data).subscribe({
  next: (claim) => {
    this.messageService.add({
      severity: 'success',
      summary: 'Success',
      detail: `Claim ${claim.id} created`
    });
    this.router.navigate(['/claims']);
  },
  error: (error) => {
    console.error('Failed to create claim:', error);
    // Error interceptor will show toast
  }
});
```

### 12.5 Loading States

Track loading states for better UX:

```typescript
@Component({
  template: `
    @if (loading()) {
      <p-progressSpinner />
    } @else {
      <p-table [value]="claims()" />
    }
  `
})
export class ClaimsListComponent {
  loading = signal(true);
  claims = signal<Claim[]>([]);

  ngOnInit() {
    this.claimsApi.getClaims().subscribe({
      next: (response) => {
        this.claims.set(response.items);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      }
    });
  }
}
```

---

## Appendix A: API Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/claims` | List claims (paginated) |
| GET | `/api/v1/claims/{id}` | Get claim by ID |
| POST | `/api/v1/claims` | Create new claim |
| PATCH | `/api/v1/claims/{id}` | Update claim |
| DELETE | `/api/v1/claims/{id}` | Delete claim |
| POST | `/api/v1/claims/{id}/submit` | Submit claim |
| POST | `/api/v1/claims/{id}/approve` | Approve claim |
| POST | `/api/v1/claims/{id}/deny` | Deny claim |
| POST | `/api/v1/claims/{id}/validate` | Validate claim |
| GET | `/api/v1/claims/stats/summary` | Get statistics |
| GET | `/api/v1/lookup/icd10` | Search ICD-10 codes |
| GET | `/api/v1/lookup/cpt` | Search CPT codes |
| GET | `/api/v1/lookup/hcpcs` | Search HCPCS codes |
| GET | `/api/v1/lookup/pos` | Get POS codes |
| GET | `/api/v1/lookup/modifiers` | Get modifier codes |
| POST | `/api/v1/eligibility/check` | Check eligibility |
| GET | `/api/v1/users` | List users |
| GET | `/api/v1/users/me` | Get current user |

---

## Appendix B: Development URLs

| Service | URL |
|---------|-----|
| Claims Portal (with Metronic) | http://localhost:4202 |
| Metronic Template (standalone) | http://localhost:4201 |
| FastAPI Backend (when running) | http://localhost:8000 |
| API Documentation (Swagger) | http://localhost:8000/docs |

---

**End of Integration API Guide**
