# Angular Frontend Design Document

**Document Version:** 1.0
**Design Date:** 2025-12-18
**Author:** Claude Code (Following design.md methodology)
**Status:** Ready for Review

---

## 1. Executive Summary

This design document defines the architecture for an Angular 19+ frontend for the Medical Claims Processing System, targeting **4000 claims per minute** processing throughput with HIPAA compliance.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | Angular 19.2+ | Enterprise-grade, TypeScript-first, Google-backed |
| Change Detection | Zoneless + Signals | 60% faster startup, optimal for real-time updates |
| State Management | NgRx Signal Store | Structured + Signals performance |
| UI Library | PrimeNG 17.18+ | 90+ components, virtualization, healthcare themes |
| Build System | Nx Monorepo | Scalable, enforced boundaries, caching |
| Real-Time | WebSocket + RxJS | Throttled updates for high-volume data |

### Scope

- Claims processing dashboard with real-time updates
- Claims submission workflow
- Member eligibility verification
- Provider management
- Policy administration
- Reporting and analytics
- User authentication and RBAC

---

## 2. Requirements Specification

### 2.1 Business Objectives

| Objective | Metric | Target |
|-----------|--------|--------|
| Processing throughput | Claims/minute displayed | 4000 |
| User response time | UI interaction latency | < 100ms |
| Initial load time | First Contentful Paint | < 2s |
| Error rate | Failed UI operations | < 0.1% |
| Availability | Frontend uptime | 99.9% |
| HIPAA compliance | Security audit pass | 100% |

### 2.2 Acceptance Criteria

1. **Performance**
   - [ ] Dashboard loads within 2 seconds
   - [ ] Claims table renders 10,000+ rows without lag (virtualization)
   - [ ] Real-time updates at 100/second without UI freeze
   - [ ] Bundle size < 500KB gzipped

2. **Functionality**
   - [ ] Complete claims CRUD operations
   - [ ] Multi-step claims submission workflow
   - [ ] Real-time status updates via WebSocket
   - [ ] Eligibility verification with instant response
   - [ ] Role-based access control matching backend permissions

3. **Security**
   - [ ] HIPAA-compliant PHI handling
   - [ ] JWT authentication with HttpOnly cookies
   - [ ] Session timeout after 15 minutes inactivity
   - [ ] Complete audit trail for PHI access
   - [ ] CSP headers enforced

4. **Accessibility**
   - [ ] WCAG 2.1 AA compliance
   - [ ] Screen reader compatibility
   - [ ] Keyboard navigation

### 2.3 Stakeholders

| Stakeholder | Needs |
|-------------|-------|
| Claims Processors | Fast claims review, bulk operations, clear status |
| Supervisors | Dashboard overview, approval workflows, metrics |
| Administrators | User management, configuration, audit logs |
| Auditors | Read-only access, complete audit trail |
| Members (optional) | Claims status portal, EOB access |

### 2.4 Constraints

| Type | Constraint |
|------|------------|
| Technical | Must integrate with existing FastAPI backend |
| Technical | Must support modern browsers (Chrome, Firefox, Edge, Safari) |
| Regulatory | HIPAA Security Rule compliance required |
| Regulatory | PHI must be encrypted in transit (TLS 1.3) |
| Business | Must support multi-tenant architecture |
| Performance | Must handle 4000 claims/minute display rate |

### 2.5 Assumptions

| Assumption | Status | Validation Needed |
|------------|--------|-------------------|
| FastAPI backend is stable and available | Acceptable | No |
| WebSocket endpoint available at /ws | Must-validate | Yes - backend team |
| Backend RBAC permissions match frontend needs | Must-validate | Yes - review permissions |
| Users have modern browsers | Acceptable | No |
| Network latency < 100ms to API server | Acceptable | No |

---

## 3. Architecture Design

### 3.1 System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USERS                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Claims     │  │  Supervisor  │  │    Admin     │  │   Auditor    │     │
│  │  Processor   │  │              │  │              │  │              │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │                 │              │
└─────────┼─────────────────┼─────────────────┼─────────────────┼──────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ANGULAR FRONTEND (Browser)                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         Angular 19+ Application                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  │
│  │  │  Dashboard  │  │   Claims    │  │ Eligibility │  │    Admin    │   │  │
│  │  │   Feature   │  │   Feature   │  │   Feature   │  │   Feature   │   │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │  │
│  │         │                │                │                │          │  │
│  │         ▼                ▼                ▼                ▼          │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    NgRx Signal Store                             │  │  │
│  │  │  claims$ │ members$ │ providers$ │ policies$ │ auth$ │ ui$      │  │  │
│  │  └────────────────────────────┬────────────────────────────────────┘  │  │
│  │                               │                                       │  │
│  │  ┌────────────────────────────┴────────────────────────────────────┐  │  │
│  │  │                      Core Services Layer                         │  │  │
│  │  │  HTTP Service │ WebSocket Service │ Auth Service │ Audit Service │  │  │
│  │  └────────────────────────────┬────────────────────────────────────┘  │  │
│  └───────────────────────────────┼───────────────────────────────────────┘  │
│                                  │                                          │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
      ┌───────────────┐    ┌───────────────┐    ┌───────────────┐
      │  REST API     │    │  WebSocket    │    │  CDN/Static   │
      │  (FastAPI)    │    │  (FastAPI)    │    │   Assets      │
      │  :8000        │    │  :8000/ws     │    │               │
      └───────────────┘    └───────────────┘    └───────────────┘
              │                    │
              ▼                    ▼
      ┌─────────────────────────────────────────────────────────┐
      │                   BACKEND SERVICES                       │
      │  PostgreSQL │ Redis │ MinIO │ Celery Workers             │
      └─────────────────────────────────────────────────────────┘
```

### 3.2 Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ANGULAR APPLICATION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FEATURE MODULES (Lazy-loaded)                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                                                                          ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ ││
│  │  │  Dashboard   │  │    Claims    │  │  Eligibility │  │    Admin     │ ││
│  │  │   Module     │  │    Module    │  │    Module    │  │    Module    │ ││
│  │  │              │  │              │  │              │  │              │ ││
│  │  │ - Overview   │  │ - List       │  │ - Search     │  │ - Policies   │ ││
│  │  │ - Metrics    │  │ - Detail     │  │ - Verify     │  │ - Providers  │ ││
│  │  │ - Charts     │  │ - Submit     │  │ - Benefits   │  │ - Members    │ ││
│  │  │ - Activity   │  │ - Review     │  │ - History    │  │ - Users      │ ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ ││
│  │                                                                          ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   ││
│  │  │   Reports    │  │   Settings   │  │    Auth      │                   ││
│  │  │   Module     │  │    Module    │  │    Module    │                   ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  SHARED LIBRARY                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        ││
│  │  │    UI      │  │   Models   │  │   Utils    │  │   Pipes    │        ││
│  │  │ Components │  │ Interfaces │  │  Helpers   │  │  Filters   │        ││
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  CORE MODULE (Singleton Services)                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        ││
│  │  │   Auth     │  │   HTTP     │  │ WebSocket  │  │   Audit    │        ││
│  │  │  Service   │  │ Interceptor│  │  Service   │  │  Service   │        ││
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘        ││
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        ││
│  │  │   Error    │  │  Loading   │  │   Toast    │  │   Logger   │        ││
│  │  │  Handler   │  │  Service   │  │  Service   │  │  Service   │        ││
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  STATE MANAGEMENT (NgRx Signal Store)                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        ││
│  │  │  Claims    │  │  Members   │  │ Providers  │  │  Policies  │        ││
│  │  │   Store    │  │   Store    │  │   Store    │  │   Store    │        ││
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘        ││
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                        ││
│  │  │   Auth     │  │    UI      │  │   Lookup   │                        ││
│  │  │   Store    │  │   Store    │  │   Store    │                        ││
│  │  └────────────┘  └────────────┘  └────────────┘                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Data Flow Diagram

```
USER ACTION                     ANGULAR                           BACKEND
    │                              │                                  │
    │  1. Click "Submit Claim"     │                                  │
    ├─────────────────────────────>│                                  │
    │                              │                                  │
    │                              │  2. Dispatch submitClaim()       │
    │                              ├─────────┐                        │
    │                              │         │ NgRx Effect            │
    │                              │<────────┘                        │
    │                              │                                  │
    │                              │  3. POST /api/v1/claims          │
    │                              ├─────────────────────────────────>│
    │                              │                                  │
    │                              │  4. { claim_id, status }         │
    │                              │<─────────────────────────────────┤
    │                              │                                  │
    │                              │  5. Update Store                 │
    │                              ├─────────┐                        │
    │                              │         │ patchState()           │
    │                              │<────────┘                        │
    │                              │                                  │
    │  6. UI Updates (Signals)     │                                  │
    │<─────────────────────────────┤                                  │
    │                              │                                  │
    │                              │  7. WebSocket: claim_update      │
    │                              │<═════════════════════════════════╡
    │                              │                                  │
    │                              │  8. Throttle + Update Store      │
    │                              ├─────────┐                        │
    │                              │         │ throttleTime(500)      │
    │                              │<────────┘                        │
    │                              │                                  │
    │  9. Real-time UI Update      │                                  │
    │<─────────────────────────────┤                                  │
    │                              │                                  │
```

### 3.4 Project Structure

```
claims-processing/
├── apps/
│   └── claims-portal/
│       ├── src/
│       │   ├── app/
│       │   │   ├── core/
│       │   │   │   ├── guards/
│       │   │   │   │   ├── auth.guard.ts
│       │   │   │   │   ├── role.guard.ts
│       │   │   │   │   └── permission.guard.ts
│       │   │   │   ├── interceptors/
│       │   │   │   │   ├── auth.interceptor.ts
│       │   │   │   │   ├── error.interceptor.ts
│       │   │   │   │   └── audit.interceptor.ts
│       │   │   │   ├── services/
│       │   │   │   │   ├── auth.service.ts
│       │   │   │   │   ├── websocket.service.ts
│       │   │   │   │   ├── audit.service.ts
│       │   │   │   │   └── logger.service.ts
│       │   │   │   └── core.module.ts
│       │   │   │
│       │   │   ├── features/
│       │   │   │   ├── dashboard/
│       │   │   │   │   ├── components/
│       │   │   │   │   │   ├── dashboard-overview.component.ts
│       │   │   │   │   │   ├── metrics-panel.component.ts
│       │   │   │   │   │   ├── claims-chart.component.ts
│       │   │   │   │   │   └── activity-feed.component.ts
│       │   │   │   │   ├── dashboard.routes.ts
│       │   │   │   │   └── index.ts
│       │   │   │   │
│       │   │   │   ├── claims/
│       │   │   │   │   ├── components/
│       │   │   │   │   │   ├── claims-list.component.ts
│       │   │   │   │   │   ├── claim-detail.component.ts
│       │   │   │   │   │   ├── claim-submit/
│       │   │   │   │   │   │   ├── claim-submit.component.ts
│       │   │   │   │   │   │   ├── step-member.component.ts
│       │   │   │   │   │   │   ├── step-provider.component.ts
│       │   │   │   │   │   │   ├── step-services.component.ts
│       │   │   │   │   │   │   └── step-review.component.ts
│       │   │   │   │   │   ├── claim-review.component.ts
│       │   │   │   │   │   └── claims-table.component.ts
│       │   │   │   │   ├── claims.routes.ts
│       │   │   │   │   └── index.ts
│       │   │   │   │
│       │   │   │   ├── eligibility/
│       │   │   │   │   ├── components/
│       │   │   │   │   │   ├── eligibility-search.component.ts
│       │   │   │   │   │   ├── eligibility-result.component.ts
│       │   │   │   │   │   └── benefits-summary.component.ts
│       │   │   │   │   ├── eligibility.routes.ts
│       │   │   │   │   └── index.ts
│       │   │   │   │
│       │   │   │   ├── admin/
│       │   │   │   │   ├── policies/
│       │   │   │   │   ├── providers/
│       │   │   │   │   ├── members/
│       │   │   │   │   └── users/
│       │   │   │   │
│       │   │   │   └── auth/
│       │   │   │       ├── login.component.ts
│       │   │   │       └── auth.routes.ts
│       │   │   │
│       │   │   ├── shared/
│       │   │   │   ├── components/
│       │   │   │   │   ├── data-table/
│       │   │   │   │   ├── form-controls/
│       │   │   │   │   ├── status-badge/
│       │   │   │   │   ├── loading-spinner/
│       │   │   │   │   └── confirm-dialog/
│       │   │   │   ├── pipes/
│       │   │   │   │   ├── currency.pipe.ts
│       │   │   │   │   ├── date-format.pipe.ts
│       │   │   │   │   └── mask-phi.pipe.ts
│       │   │   │   └── directives/
│       │   │   │       ├── permission.directive.ts
│       │   │   │       └── autofocus.directive.ts
│       │   │   │
│       │   │   ├── app.component.ts
│       │   │   ├── app.config.ts
│       │   │   └── app.routes.ts
│       │   │
│       │   ├── environments/
│       │   │   ├── environment.ts
│       │   │   └── environment.prod.ts
│       │   │
│       │   ├── assets/
│       │   ├── styles/
│       │   │   ├── _variables.scss
│       │   │   ├── _healthcare-theme.scss
│       │   │   └── styles.scss
│       │   │
│       │   └── main.ts
│       │
│       ├── project.json
│       └── tsconfig.app.json
│
├── libs/
│   ├── shared/
│   │   ├── models/
│   │   │   └── src/
│   │   │       ├── claim.model.ts
│   │   │       ├── member.model.ts
│   │   │       ├── provider.model.ts
│   │   │       ├── policy.model.ts
│   │   │       └── index.ts
│   │   │
│   │   ├── data-access/
│   │   │   └── src/
│   │   │       ├── claims.store.ts
│   │   │       ├── members.store.ts
│   │   │       ├── providers.store.ts
│   │   │       ├── policies.store.ts
│   │   │       ├── auth.store.ts
│   │   │       └── index.ts
│   │   │
│   │   └── util/
│   │       └── src/
│   │           ├── validators.ts
│   │           ├── formatters.ts
│   │           └── index.ts
│   │
│   └── api-client/
│       └── src/
│           ├── claims.api.ts
│           ├── members.api.ts
│           ├── providers.api.ts
│           ├── policies.api.ts
│           └── index.ts
│
├── nx.json
├── package.json
├── tsconfig.base.json
└── angular.json
```

---

## 4. API Contracts

### 4.1 REST API Integration

Based on existing FastAPI backend endpoints:

#### Claims Endpoints

| Method | Endpoint | Request | Response | Permission |
|--------|----------|---------|----------|------------|
| POST | /api/v1/claims | ClaimCreate | ClaimResponse | claims:create |
| GET | /api/v1/claims | Query params | ClaimListResponse | claims:read |
| GET | /api/v1/claims/{id} | - | ClaimResponse | claims:read |
| PATCH | /api/v1/claims/{id} | ClaimUpdate | ClaimResponse | claims:update |
| DELETE | /api/v1/claims/{id} | - | 204 | claims:delete |
| POST | /api/v1/claims/{id}/submit | - | ClaimSubmitResponse | claims:submit |
| POST | /api/v1/claims/{id}/approve | ClaimAction | ClaimResponse | claims:approve |
| POST | /api/v1/claims/{id}/deny | ClaimAction | ClaimResponse | claims:deny |
| POST | /api/v1/claims/{id}/validate | - | ValidationResult | claims:read |
| GET | /api/v1/claims/stats/summary | Query params | ClaimStatsResponse | claims:read |

#### TypeScript Interfaces

```typescript
// libs/shared/models/src/claim.model.ts

export interface Claim {
  id: string;
  tracking_number: string;
  claim_type: ClaimType;
  status: ClaimStatus;
  priority: ClaimPriority;
  policy_id: string;
  member_id: string;
  provider_id: string;
  service_date_from: string;  // ISO date
  service_date_to: string;
  diagnosis_codes: string[];
  primary_diagnosis: string;
  total_charged: number;
  total_allowed?: number;
  total_paid?: number;
  patient_responsibility?: number;
  fwa_score?: number;
  fwa_risk_level?: FWARiskLevel;
  line_items: ClaimLineItem[];
  created_at: string;
  updated_at: string;
  submitted_at?: string;
}

export interface ClaimCreate {
  policy_id: string;
  member_id: string;
  provider_id: string;
  claim_type: ClaimType;
  service_date_from: string;
  service_date_to: string;
  diagnosis_codes: string[];
  primary_diagnosis: string;
  total_charged: number;
  line_items: ClaimLineItemCreate[];
  source?: ClaimSource;
  priority?: ClaimPriority;
  place_of_service?: string;
  prior_auth_number?: string;
}

export interface ClaimLineItem {
  id: string;
  line_number: number;
  procedure_code: string;
  procedure_code_system: string;
  service_date: string;
  quantity: number;
  charged_amount: number;
  allowed_amount?: number;
  paid_amount?: number;
  denied: boolean;
  denial_reason?: string;
}

export enum ClaimStatus {
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
  NEEDS_REVIEW = 'needs_review'
}

export enum ClaimType {
  PROFESSIONAL = 'professional',
  INSTITUTIONAL = 'institutional',
  DENTAL = 'dental',
  PHARMACY = 'pharmacy'
}
```

### 4.2 WebSocket Integration

```typescript
// WebSocket Message Types
interface WebSocketMessage {
  type: 'claim_update' | 'metrics' | 'notification' | 'heartbeat';
  payload: any;
  timestamp: string;
}

interface ClaimUpdateMessage {
  type: 'claim_update';
  payload: {
    claim_id: string;
    status: ClaimStatus;
    tracking_number: string;
    updated_fields: string[];
  };
  timestamp: string;
}

interface MetricsMessage {
  type: 'metrics';
  payload: {
    claims_per_minute: number;
    pending_count: number;
    processing_count: number;
    approved_today: number;
    denied_today: number;
  };
  timestamp: string;
}
```

### 4.3 Error Response Format

```typescript
interface ApiError {
  detail: string | {
    message: string;
    errors?: ValidationError[];
  };
  status_code: number;
}

interface ValidationError {
  field: string;
  message: string;
  code: string;
}
```

---

## 5. Technology Stack

### 5.1 Core Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| @angular/core | 19.2.0+ | Framework | MIT |
| @angular/cli | 19.2.0+ | Build tools | MIT |
| typescript | 5.8.0+ | Type system | Apache-2.0 |
| rxjs | 7.8.0+ | Reactive programming | Apache-2.0 |
| zone.js | - | Removed (zoneless) | MIT |

### 5.2 State Management

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| @ngrx/signals | 19.0.0+ | Signal Store | MIT |
| @ngrx/effects | 19.0.0+ | Side effects | MIT |
| @ngrx/operators | 19.0.0+ | Utility operators | MIT |

### 5.3 UI Components

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| primeng | 17.18.0+ | Component library | MIT |
| primeicons | 7.0.0+ | Icon set | MIT |
| primeflex | 3.3.0+ | CSS utilities | MIT |
| @angular/cdk | 19.0.0+ | CDK (virtual scroll) | MIT |

### 5.4 Build & Tooling

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| nx | 22.0.0+ | Monorepo management | MIT |
| esbuild | (CLI default) | Fast builds | MIT |
| jest | 29.0.0+ | Unit testing | MIT |
| playwright | 1.40.0+ | E2E testing | Apache-2.0 |

### 5.5 Security Justification

All dependencies:
- Use permissive licenses (MIT/Apache-2.0) compatible with commercial use
- Actively maintained (last commit < 6 months)
- No known critical CVEs as of 2025-12-18
- Used in production by major enterprises

---

## 6. Security Design

### 6.1 Threat Model (STRIDE)

| Threat | Category | Mitigation |
|--------|----------|------------|
| Credential theft | Spoofing | JWT in HttpOnly cookies, no localStorage |
| Session hijacking | Spoofing | SameSite cookies, CSRF tokens |
| XSS attacks | Tampering | Angular sanitization, CSP headers, Trusted Types |
| CSRF attacks | Tampering | CSRF token validation, SameSite cookies |
| Data exposure | Info Disclosure | TLS 1.3, PHI masking, audit logging |
| Privilege escalation | Elevation | Route guards, permission checks, backend validation |
| DoS via UI | Denial of Service | Rate limiting, request throttling |
| Token theft | Repudiation | Complete audit trail, session logging |

### 6.2 Authentication Flow

```
┌────────────┐     ┌────────────────┐     ┌────────────────┐
│   User     │     │   Angular      │     │   FastAPI      │
│   Browser  │     │   Frontend     │     │   Backend      │
└─────┬──────┘     └───────┬────────┘     └───────┬────────┘
      │                    │                      │
      │  1. Login form     │                      │
      ├───────────────────>│                      │
      │                    │                      │
      │                    │  2. POST /auth/login │
      │                    ├─────────────────────>│
      │                    │                      │
      │                    │  3. Set-Cookie:      │
      │                    │     access_token     │
      │                    │     (HttpOnly)       │
      │                    │<─────────────────────┤
      │                    │                      │
      │  4. Redirect to    │                      │
      │     dashboard      │                      │
      │<───────────────────┤                      │
      │                    │                      │
      │  5. API Request    │                      │
      │     (cookie auto)  │                      │
      ├───────────────────>│                      │
      │                    │  6. GET /api/claims  │
      │                    │     Cookie: token    │
      │                    ├─────────────────────>│
      │                    │                      │
```

### 6.3 HIPAA Security Controls

| Control | Implementation |
|---------|----------------|
| Access Control | Route guards, permission directive, RBAC |
| Audit Trail | Interceptor logs all PHI access with user/timestamp |
| Encryption | TLS 1.3 for all API calls |
| Session Management | 15-min timeout, secure logout |
| PHI Masking | Mask SSN, DOB on display (show last 4) |
| Error Handling | Never expose PHI in error messages |

### 6.4 Security Implementation

```typescript
// core/interceptors/security.interceptor.ts
@Injectable()
export class SecurityInterceptor implements HttpInterceptor {
  constructor(
    private auditService: AuditService,
    private csrfService: CsrfService
  ) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Add CSRF token
    const csrfToken = this.csrfService.getToken();

    const secureReq = req.clone({
      withCredentials: true,  // Send HttpOnly cookies
      headers: req.headers
        .set('X-CSRF-Token', csrfToken)
        .set('X-Request-ID', crypto.randomUUID())
    });

    // Audit PHI access
    if (this.isPHIEndpoint(req.url)) {
      this.auditService.logAccess({
        url: req.url,
        method: req.method,
        timestamp: new Date().toISOString()
      });
    }

    return next.handle(secureReq);
  }

  private isPHIEndpoint(url: string): boolean {
    return /\/(claims|members|eligibility)/.test(url);
  }
}
```

---

## 7. Performance Plan

### 7.1 Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| First Contentful Paint | < 1.5s | Lighthouse |
| Largest Contentful Paint | < 2.5s | Lighthouse |
| Time to Interactive | < 3s | Lighthouse |
| First Input Delay | < 100ms | Lighthouse |
| Cumulative Layout Shift | < 0.1 | Lighthouse |
| Claims table render (10K rows) | < 500ms | Custom metric |
| WebSocket update processing | < 16ms | Custom metric |
| Bundle size (initial) | < 200KB gzip | Build output |

### 7.2 Optimization Strategies

```typescript
// 1. Zoneless Change Detection
// app.config.ts
export const appConfig: ApplicationConfig = {
  providers: [
    provideZonelessChangeDetection(),
    // ...
  ]
};

// 2. OnPush for all components
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  // ...
})

// 3. Virtual Scrolling for large tables
@Component({
  template: `
    <cdk-virtual-scroll-viewport itemSize="48" class="claims-viewport">
      @for (claim of claims(); track claim.id) {
        <app-claim-row [claim]="claim" />
      }
    </cdk-virtual-scroll-viewport>
  `
})

// 4. WebSocket Throttling
claimUpdates$ = this.socket$.pipe(
  bufferTime(100),
  filter(batch => batch.length > 0),
  throttleTime(500),
  shareReplay(1)
);

// 5. Lazy Loading Routes
export const routes: Routes = [
  {
    path: 'claims',
    loadChildren: () => import('./features/claims/claims.routes')
  },
  {
    path: 'admin',
    loadChildren: () => import('./features/admin/admin.routes')
  }
];
```

### 7.3 Bundle Optimization

| Technique | Expected Savings |
|-----------|------------------|
| Zoneless (no zone.js) | 30-50KB |
| Tree-shaking (standalone) | 20-40% |
| Lazy loading | 40% initial |
| PrimeNG selective imports | 50% of library |
| Brotli compression | 70% |

---

## 8. Risk Register

| ID | Risk | Probability | Impact | Mitigation | Fallback |
|----|------|-------------|--------|------------|----------|
| R1 | Zoneless migration issues | Medium | Medium | Start with OnPush, migrate gradually | Keep zone.js initially |
| R2 | PrimeNG performance issues | Low | Medium | Profile components, use virtualization | Switch to Angular Material |
| R3 | WebSocket connection drops | Medium | High | Implement reconnection with backoff | Poll REST API |
| R4 | State management complexity | Medium | Medium | Team training, clear patterns | Use simpler service-based state |
| R5 | HIPAA compliance gaps | Low | Critical | Security audit pre-launch | External security review |
| R6 | Backend API changes | Medium | Medium | OpenAPI client generation | Version pinning |
| R7 | Browser compatibility | Low | Low | Target modern browsers only | Add polyfills |
| R8 | 4000 claims/min bottleneck | Medium | High | Throttling, virtualization, batching | Increase throttle interval |

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Sprint 1-2)

**Goal:** Core infrastructure and authentication

| Task | Priority | Effort |
|------|----------|--------|
| Nx workspace setup | P0 | Small |
| Angular 19 configuration (zoneless) | P0 | Small |
| Core module (services, interceptors) | P0 | Medium |
| Auth module (login, guards) | P0 | Medium |
| Shared UI components (basic) | P1 | Medium |
| CI/CD pipeline | P1 | Small |

**Deliverable:** Login working, protected routes

### Phase 2: Claims Core (Sprint 3-4)

**Goal:** Claims listing and detail views

| Task | Priority | Effort |
|------|----------|--------|
| Claims store (NgRx Signal Store) | P0 | Medium |
| Claims API service | P0 | Small |
| Claims list component (virtualized) | P0 | Large |
| Claim detail component | P0 | Medium |
| Status badges and indicators | P1 | Small |
| WebSocket integration | P1 | Medium |

**Deliverable:** View and filter claims, real-time updates

### Phase 3: Claims Workflow (Sprint 5-6)

**Goal:** Claims submission and review

| Task | Priority | Effort |
|------|----------|--------|
| Multi-step claim submission wizard | P0 | Large |
| Form validation (ICD-10, CPT) | P0 | Medium |
| Claim review workflow | P0 | Medium |
| Approval/denial actions | P0 | Small |
| Document upload | P1 | Medium |

**Deliverable:** End-to-end claims processing

### Phase 4: Eligibility & Admin (Sprint 7-8)

**Goal:** Eligibility verification and admin features

| Task | Priority | Effort |
|------|----------|--------|
| Eligibility search | P0 | Medium |
| Benefits display | P0 | Medium |
| Provider management | P1 | Medium |
| Member management | P1 | Medium |
| Policy management | P1 | Medium |
| User management (RBAC) | P1 | Medium |

**Deliverable:** Complete admin functionality

### Phase 5: Dashboard & Reports (Sprint 9-10)

**Goal:** Analytics and reporting

| Task | Priority | Effort |
|------|----------|--------|
| Dashboard overview | P0 | Large |
| Real-time metrics | P0 | Medium |
| Charts (claims status, financial) | P1 | Medium |
| Activity feed | P1 | Small |
| Export functionality | P2 | Medium |

**Deliverable:** Production-ready dashboard

### Phase 6: Polish & Launch (Sprint 11-12)

**Goal:** Production readiness

| Task | Priority | Effort |
|------|----------|--------|
| Performance optimization | P0 | Medium |
| Security audit | P0 | Large |
| Accessibility audit (WCAG) | P0 | Medium |
| E2E test suite | P1 | Large |
| Documentation | P1 | Medium |
| Production deployment | P0 | Small |

**Deliverable:** Production launch

---

## 10. Open Questions

| ID | Question | Owner | Status | Resolution |
|----|----------|-------|--------|------------|
| Q1 | Is WebSocket endpoint available at /ws? | Backend team | **Resolved** | Yes - endpoint available |
| Q2 | What are the exact RBAC permission names? | Backend team | **Resolved** | Yes - permissions defined in backend |
| Q3 | Should members have portal access? | Product | **Resolved** | Yes - required, add member portal feature |
| Q4 | What browser versions must be supported? | Product | **Resolved** | Latest Chrome, Latest Edge |
| Q5 | Is offline/PWA support required? | Product | Open | Sprint 6 |
| Q6 | What analytics/telemetry is needed? | Product | Open | Sprint 9 |

---

## Validation Checklist

- [x] Business requirements clearly mapped to technical solution
- [x] All integration points identified and specified
- [x] Security requirements addressed (HIPAA, STRIDE)
- [x] Performance requirements defined (4000 claims/min)
- [x] Risks identified with mitigation strategies
- [x] Implementation broken into manageable phases
- [x] No major assumptions left unvalidated (Q1-Q4 resolved)
- [x] Technology choices justified with evidence (research document)

---

**Document Status:** Approved - Implementation Started
**Resolved Questions:** Q1-Q4 (WebSocket confirmed, RBAC available, Member portal required, Chrome/Edge latest)
**Next Steps:**
1. ~~Resolve open questions (Q1, Q2)~~ Done
2. ~~Get stakeholder approval~~ Approved 2025-12-18
3. **Begin Phase 1 implementation** (In Progress)
