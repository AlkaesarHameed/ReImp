# Phase 4: Eligibility & Admin Implementation

**Document Version:** 1.0
**Implementation Date:** 2025-12-18
**Author:** Claude Code (Following implement.md methodology)
**Status:** Design - Awaiting Approval

---

## 1. Requirements Analysis

### 1.1 Business Objectives

Based on [angular_frontend_design.md](../design/angular_frontend_design.md) Section 9, Phase 4:

| Objective | Deliverable |
|-----------|-------------|
| Eligibility verification | Real-time member eligibility search and display |
| Benefits visualization | Clear display of coverage, deductibles, copays |
| Provider management | CRUD operations for provider registry |
| Member management | CRUD operations for member registry |
| Policy management | Policy configuration and coverage rules |
| User management | RBAC-based user administration |

### 1.2 Acceptance Criteria

1. **Eligibility Search**
   - [ ] Search by member ID, name, DOB, or SSN (last 4)
   - [ ] Real-time eligibility status display
   - [ ] Coverage effective dates clearly shown
   - [ ] Network status indicator (in-network/out-of-network)
   - [ ] Prior authorization requirements displayed
   - [ ] Eligibility history available

2. **Benefits Display**
   - [ ] Deductible progress (individual/family)
   - [ ] Out-of-pocket maximum progress
   - [ ] Copay amounts by service type
   - [ ] Coinsurance percentages
   - [ ] Coverage exclusions highlighted
   - [ ] Printable benefits summary

3. **Provider Management**
   - [ ] Provider search with filters (NPI, name, specialty, location)
   - [ ] Provider detail view with credentials
   - [ ] Add/Edit provider with NPI validation
   - [ ] Network affiliation management
   - [ ] Provider status (active/inactive/suspended)
   - [ ] Bulk import from CSV/Excel

4. **Member Management**
   - [ ] Member search with filters
   - [ ] Member detail with demographics
   - [ ] Add/Edit member with PHI protection
   - [ ] Dependent management
   - [ ] Coverage history timeline
   - [ ] Member status management

5. **Policy Management**
   - [ ] Policy search and listing
   - [ ] Policy detail with coverage rules
   - [ ] Benefit configuration editor
   - [ ] Fee schedule management
   - [ ] Policy version history
   - [ ] Effective date management

6. **User Management (RBAC)**
   - [ ] User listing with role indicators
   - [ ] User creation with role assignment
   - [ ] Role management (predefined roles)
   - [ ] Permission matrix display
   - [ ] User activity audit log
   - [ ] Password reset capability
   - [ ] Account lock/unlock

7. **Performance**
   - [ ] Eligibility check < 2 seconds
   - [ ] Search results < 500ms
   - [ ] Pagination for large datasets
   - [ ] Virtual scrolling for lists > 100 items

### 1.3 Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| Member Store (New) | Internal | To create |
| Provider Store (New) | Internal | To create |
| Policy Store (New) | Internal | To create |
| User Store (New) | Internal | To create |
| Auth Store (Phase 1) | Internal | Completed |
| PrimeNG Table/Grid | External | Available (v17.18+) |
| PrimeNG Form Components | External | Available (v17.18+) |
| Backend /members endpoints | External | Must validate |
| Backend /providers endpoints | External | Must validate |
| Backend /policies endpoints | External | Must validate |
| Backend /users endpoints | External | Must validate |

---

## 2. Design Proposal

### 2.1 Feature Module Architecture

```
features/
├── eligibility/
│   ├── components/
│   │   ├── eligibility-search/
│   │   │   ├── eligibility-search.component.ts
│   │   │   └── eligibility-search.component.spec.ts
│   │   ├── eligibility-result/
│   │   │   ├── eligibility-result.component.ts
│   │   │   └── eligibility-result.component.spec.ts
│   │   └── benefits-summary/
│   │       ├── benefits-summary.component.ts
│   │       └── benefits-summary.component.spec.ts
│   ├── eligibility.routes.ts
│   └── index.ts
│
├── admin/
│   ├── providers/
│   │   ├── components/
│   │   │   ├── provider-list/
│   │   │   ├── provider-detail/
│   │   │   └── provider-form/
│   │   ├── providers.routes.ts
│   │   └── index.ts
│   │
│   ├── members/
│   │   ├── components/
│   │   │   ├── member-list/
│   │   │   ├── member-detail/
│   │   │   └── member-form/
│   │   ├── members.routes.ts
│   │   └── index.ts
│   │
│   ├── policies/
│   │   ├── components/
│   │   │   ├── policy-list/
│   │   │   ├── policy-detail/
│   │   │   └── policy-form/
│   │   ├── policies.routes.ts
│   │   └── index.ts
│   │
│   └── users/
│       ├── components/
│       │   ├── user-list/
│       │   ├── user-detail/
│       │   └── user-form/
│       ├── users.routes.ts
│       └── index.ts
│
libs/
├── api-client/src/
│   ├── eligibility.api.ts
│   ├── eligibility.api.spec.ts
│   ├── providers.api.ts
│   ├── providers.api.spec.ts
│   ├── members.api.ts
│   ├── members.api.spec.ts
│   ├── policies.api.ts
│   ├── policies.api.spec.ts
│   ├── users.api.ts
│   └── users.api.spec.ts
│
├── shared/data-access/src/
│   ├── members.store.ts
│   ├── providers.store.ts
│   ├── policies.store.ts
│   └── users.store.ts
│
└── shared/models/src/
    ├── eligibility.model.ts
    └── user.model.ts
```

### 2.2 Data Flow Diagram

```
                    ELIGIBILITY VERIFICATION FLOW

┌─────────────────────────────────────────────────────────────────────┐
│                         ELIGIBILITY MODULE                           │
│                                                                      │
│  ┌─────────────────┐                         ┌─────────────────┐    │
│  │ Eligibility     │                         │  Benefits       │    │
│  │ Search          │──────────────────────>  │  Summary        │    │
│  │                 │     eligibilityResult   │                 │    │
│  └────────┬────────┘                         └─────────────────┘    │
│           │                                                          │
│           │ searchQuery                                              │
│           ▼                                                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                  Eligibility API Service                     │    │
│  │  checkEligibility(memberId, dateOfService)                   │    │
│  └────────────────────────────┬────────────────────────────────┘    │
│                               │                                      │
└───────────────────────────────┼──────────────────────────────────────┘
                                │
                                ▼
                  ┌─────────────────────────┐
                  │  GET /api/v1/eligibility │
                  │  POST (batch check)      │
                  └───────────┬─────────────┘
                              │
                              ▼
                  ┌─────────────────────────┐
                  │   Backend Response       │
                  │   - coverage status      │
                  │   - benefits details     │
                  │   - accumulator totals   │
                  └─────────────────────────┘
```

### 2.3 Admin CRUD Pattern

```
                    ADMIN ENTITY MANAGEMENT (Generic Pattern)

┌─────────────────────────────────────────────────────────────────────┐
│                         ENTITY MODULE                                │
│                                                                      │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐                │
│  │ Entity     │───>│ Entity     │───>│ Entity     │                │
│  │ List       │    │ Detail     │    │ Form       │                │
│  │            │    │            │    │ (Create/   │                │
│  │ - Search   │    │ - View     │    │  Edit)     │                │
│  │ - Filter   │    │ - Actions  │    │            │                │
│  │ - Paginate │    │            │    │ - Validate │                │
│  └─────┬──────┘    └─────┬──────┘    └─────┬──────┘                │
│        │                 │                 │                        │
│        ▼                 ▼                 ▼                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    NgRx Signal Store                         │   │
│  │  entities() │ selectedEntity() │ loading() │ error()        │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                     │
└───────────────────────────────┼─────────────────────────────────────┘
                                │
                                ▼
                  ┌─────────────────────────┐
                  │   Entity API Service    │
                  │   - getAll()            │
                  │   - getById()           │
                  │   - create()            │
                  │   - update()            │
                  │   - delete()            │
                  └─────────────────────────┘
```

### 2.4 State Management

```typescript
// Members Store
interface MembersState {
  members: Member[];
  selectedMember: Member | null;
  loading: boolean;
  error: string | null;
  filters: MemberFilters;
  pagination: PaginationState;
}

// Providers Store
interface ProvidersState {
  providers: Provider[];
  selectedProvider: Provider | null;
  loading: boolean;
  error: string | null;
  filters: ProviderFilters;
  pagination: PaginationState;
}

// Policies Store
interface PoliciesState {
  policies: Policy[];
  selectedPolicy: Policy | null;
  loading: boolean;
  error: string | null;
  filters: PolicyFilters;
  pagination: PaginationState;
}

// Users Store
interface UsersState {
  users: User[];
  selectedUser: User | null;
  roles: Role[];
  loading: boolean;
  error: string | null;
  pagination: PaginationState;
}
```

### 2.5 API Contracts

**Eligibility Endpoints**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/v1/eligibility/{memberId} | Check member eligibility |
| POST | /api/v1/eligibility/batch | Batch eligibility check |
| GET | /api/v1/eligibility/{memberId}/benefits | Get benefits details |
| GET | /api/v1/eligibility/{memberId}/history | Eligibility history |

**Members Endpoints**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/v1/members | List members (paginated) |
| GET | /api/v1/members/{id} | Get member detail |
| POST | /api/v1/members | Create member |
| PATCH | /api/v1/members/{id} | Update member |
| DELETE | /api/v1/members/{id} | Delete member |
| GET | /api/v1/members/{id}/dependents | Get dependents |

**Providers Endpoints**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/v1/providers | List providers (paginated) |
| GET | /api/v1/providers/{id} | Get provider detail |
| POST | /api/v1/providers | Create provider |
| PATCH | /api/v1/providers/{id} | Update provider |
| DELETE | /api/v1/providers/{id} | Delete provider |
| POST | /api/v1/providers/validate-npi | Validate NPI |

**Policies Endpoints**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/v1/policies | List policies (paginated) |
| GET | /api/v1/policies/{id} | Get policy detail |
| POST | /api/v1/policies | Create policy |
| PATCH | /api/v1/policies/{id} | Update policy |
| DELETE | /api/v1/policies/{id} | Delete policy |
| GET | /api/v1/policies/{id}/benefits | Get benefit rules |

**Users Endpoints**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/v1/users | List users (paginated) |
| GET | /api/v1/users/{id} | Get user detail |
| POST | /api/v1/users | Create user |
| PATCH | /api/v1/users/{id} | Update user |
| DELETE | /api/v1/users/{id} | Delete user |
| POST | /api/v1/users/{id}/reset-password | Reset password |
| POST | /api/v1/users/{id}/lock | Lock account |
| POST | /api/v1/users/{id}/unlock | Unlock account |
| GET | /api/v1/roles | List roles |
| GET | /api/v1/permissions | List permissions |

### 2.6 Security Considerations

| Concern | Implementation |
|---------|----------------|
| PHI Protection | Mask SSN (show last 4), mask DOB in lists |
| Role-based Access | Permission guards on routes and actions |
| Audit Logging | Log all PHI access with user/timestamp |
| Password Management | Backend handles password hashing, no frontend storage |
| Session Timeout | 15-minute inactivity logout |

---

## 3. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Backend API endpoints not ready | Medium | High | Mock services, validate endpoints early |
| Complex eligibility rules | High | Medium | Use backend for all business logic |
| PHI exposure in UI | Low | Critical | Implement masking, audit all access |
| Large dataset performance | Medium | Medium | Pagination, virtual scrolling |
| Role permission mismatch | Medium | High | Validate RBAC with backend team |
| User management security | Low | Critical | Backend-only password handling |

---

## 4. Implementation Plan

### 4.1 Task Breakdown

| # | Task | Priority | Tests First |
|---|------|----------|-------------|
| 1 | Create User model and API service | P0 | Yes |
| 2 | Create Members API service + tests | P0 | Yes |
| 3 | Create Providers API service + tests | P0 | Yes |
| 4 | Create Policies API service + tests | P0 | Yes |
| 5 | Create Eligibility API service + tests | P0 | Yes |
| 6 | Create Members Store | P0 | Yes |
| 7 | Create Providers Store | P0 | Yes |
| 8 | Create Policies Store | P0 | Yes |
| 9 | Create Users Store | P0 | Yes |
| 10 | Create Eligibility Search component | P0 | Yes |
| 11 | Create Eligibility Result component | P0 | Yes |
| 12 | Create Benefits Summary component | P0 | Yes |
| 13 | Create Provider List component | P0 | Yes |
| 14 | Create Provider Detail component | P0 | Yes |
| 15 | Create Provider Form component | P0 | Yes |
| 16 | Create Member List component | P0 | Yes |
| 17 | Create Member Detail component | P0 | Yes |
| 18 | Create Member Form component | P0 | Yes |
| 19 | Create Policy List component | P1 | Yes |
| 20 | Create Policy Detail component | P1 | Yes |
| 21 | Create Policy Form component | P1 | Yes |
| 22 | Create User List component | P1 | Yes |
| 23 | Create User Detail component | P1 | Yes |
| 24 | Create User Form component | P1 | Yes |
| 25 | Configure routes for all modules | P0 | Yes |
| 26 | Integration testing | P0 | N/A |

### 4.2 File Inventory

**New Files to Create:**

```
# API Services
libs/api-client/src/eligibility.api.ts
libs/api-client/src/eligibility.api.spec.ts
libs/api-client/src/users.api.ts
libs/api-client/src/users.api.spec.ts

# Models
libs/shared/models/src/eligibility.model.ts
libs/shared/models/src/user.model.ts

# Stores
libs/shared/data-access/src/members.store.ts
libs/shared/data-access/src/providers.store.ts
libs/shared/data-access/src/policies.store.ts
libs/shared/data-access/src/users.store.ts

# Eligibility Feature
apps/claims-portal/src/app/features/eligibility/eligibility.routes.ts
apps/claims-portal/src/app/features/eligibility/components/eligibility-search/eligibility-search.component.ts
apps/claims-portal/src/app/features/eligibility/components/eligibility-search/eligibility-search.component.spec.ts
apps/claims-portal/src/app/features/eligibility/components/eligibility-result/eligibility-result.component.ts
apps/claims-portal/src/app/features/eligibility/components/eligibility-result/eligibility-result.component.spec.ts
apps/claims-portal/src/app/features/eligibility/components/benefits-summary/benefits-summary.component.ts
apps/claims-portal/src/app/features/eligibility/components/benefits-summary/benefits-summary.component.spec.ts

# Admin - Providers
apps/claims-portal/src/app/features/admin/providers/providers.routes.ts
apps/claims-portal/src/app/features/admin/providers/components/provider-list/provider-list.component.ts
apps/claims-portal/src/app/features/admin/providers/components/provider-list/provider-list.component.spec.ts
apps/claims-portal/src/app/features/admin/providers/components/provider-detail/provider-detail.component.ts
apps/claims-portal/src/app/features/admin/providers/components/provider-detail/provider-detail.component.spec.ts
apps/claims-portal/src/app/features/admin/providers/components/provider-form/provider-form.component.ts
apps/claims-portal/src/app/features/admin/providers/components/provider-form/provider-form.component.spec.ts

# Admin - Members
apps/claims-portal/src/app/features/admin/members/members.routes.ts
apps/claims-portal/src/app/features/admin/members/components/member-list/member-list.component.ts
apps/claims-portal/src/app/features/admin/members/components/member-list/member-list.component.spec.ts
apps/claims-portal/src/app/features/admin/members/components/member-detail/member-detail.component.ts
apps/claims-portal/src/app/features/admin/members/components/member-detail/member-detail.component.spec.ts
apps/claims-portal/src/app/features/admin/members/components/member-form/member-form.component.ts
apps/claims-portal/src/app/features/admin/members/components/member-form/member-form.component.spec.ts

# Admin - Policies
apps/claims-portal/src/app/features/admin/policies/policies.routes.ts
apps/claims-portal/src/app/features/admin/policies/components/policy-list/policy-list.component.ts
apps/claims-portal/src/app/features/admin/policies/components/policy-list/policy-list.component.spec.ts
apps/claims-portal/src/app/features/admin/policies/components/policy-detail/policy-detail.component.ts
apps/claims-portal/src/app/features/admin/policies/components/policy-detail/policy-detail.component.spec.ts
apps/claims-portal/src/app/features/admin/policies/components/policy-form/policy-form.component.ts
apps/claims-portal/src/app/features/admin/policies/components/policy-form/policy-form.component.spec.ts

# Admin - Users
apps/claims-portal/src/app/features/admin/users/users.routes.ts
apps/claims-portal/src/app/features/admin/users/components/user-list/user-list.component.ts
apps/claims-portal/src/app/features/admin/users/components/user-list/user-list.component.spec.ts
apps/claims-portal/src/app/features/admin/users/components/user-detail/user-detail.component.ts
apps/claims-portal/src/app/features/admin/users/components/user-detail/user-detail.component.spec.ts
apps/claims-portal/src/app/features/admin/users/components/user-form/user-form.component.ts
apps/claims-portal/src/app/features/admin/users/components/user-form/user-form.component.spec.ts

# Admin routes
apps/claims-portal/src/app/features/admin/admin.routes.ts
```

**Files to Modify:**

```
libs/api-client/src/index.ts                    # Export new APIs
libs/shared/models/src/index.ts                 # Export new models
libs/shared/data-access/src/index.ts            # Export new stores
apps/claims-portal/src/app/app.routes.ts        # Add feature routes
```

---

## 5. Environment Verification

**Development Environment:** Nx Monorepo with Angular 19+
**Build Command:** `npm run build`
**Test Command:** `npm run test`
**Lint Command:** `npm run lint`

**Dependencies Status:**
- PrimeNG 17.18+ (Table, Form, Dialog) - Available in package.json
- Angular Reactive Forms - Available
- NgRx Signal Store - Available
- RxJS 7.8+ - Available

---

## 6. Approval Checkpoint

**Requesting approval to proceed with Phase 4 implementation.**

Questions for stakeholder:
1. Are the backend endpoints for members, providers, policies, and users available?
2. What are the specific RBAC roles and permissions for user management?
3. Should member SSN be stored/displayed, or just the last 4 digits?
4. Are there specific password policies (length, complexity) to enforce in the UI?
5. Is bulk import functionality required for providers in this phase?

---

**Status:** AWAITING APPROVAL

Once approved, implementation will proceed with:
1. Writing test files first (TDD)
2. Implementing API services and stores
3. Creating eligibility components
4. Creating admin CRUD components
5. Running quality checks
6. Providing deliverables summary
