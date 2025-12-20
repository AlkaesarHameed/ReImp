# Reimbursement Claims Management System
# Implementation Plan

**Document Version**: 1.0
**Created**: December 18, 2025
**Based On**: [01_configurable_claims_processing_design.md](../design/01_configurable_claims_processing_design.md)
**Status**: Ready for Approval

---

## 1. Executive Summary

This implementation plan details the step-by-step approach to build the Reimbursement Claims Management and Auto-Processing System. The plan follows a **4-pillar methodology**: Design-First, Evidence-Based, Test-Driven, and Quality-First development.

### 1.1 Existing Foundation

The project already has a FastAPI starter template with:
- FastAPI application structure (`src/api/`)
- SQLAlchemy models (`src/models/`)
- Pydantic schemas (`src/schemas/`)
- Redis caching (`src/services/cache.py`)
- LLM service (`src/services/llm.py`)
- Celery task queue (`src/utils/celery_app.py`)
- Streamlit app (`streamlit_app/`)
- Test infrastructure (`tests/`)

### 1.2 Implementation Approach

| Principle | Application |
|-----------|-------------|
| **Incremental Delivery** | 4 phases with working software at each milestone |
| **Test-First** | Tests written before implementation for each feature |
| **Provider Abstraction** | All AI/ML components behind swappable interfaces |
| **Demo-Ready** | Each phase produces demonstrable functionality |

---

## 2. Phase 1: Foundation & Provider Abstraction

**Duration**: Sprints 1-4
**Goal**: Establish core infrastructure and provider abstraction layer

### 2.1 Sprint 1: Project Configuration & Database Schema

#### 2.1.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 1.1.1 | Create extended configuration settings for claims processing | High | None |
| 1.1.2 | Define provider configuration enums and settings | High | 1.1.1 |
| 1.1.3 | Create PostgreSQL migration infrastructure with Alembic | High | None |
| 1.1.4 | Implement tenant isolation database schema | High | 1.1.3 |
| 1.1.5 | Create core domain models (Claim, Policy, Provider, Member) | High | 1.1.4 |
| 1.1.6 | Implement audit logging with TimescaleDB extension | Medium | 1.1.3 |
| 1.1.7 | Create database connection manager with tenant routing | High | 1.1.4 |
| 1.1.8 | Write unit tests for all configuration and models | High | 1.1.1-1.1.7 |

#### 2.1.2 Deliverables

```
src/
├── api/
│   └── config.py                 # Extended with claims settings
├── db/
│   ├── migrations/               # NEW: Alembic migrations
│   │   ├── env.py
│   │   └── versions/
│   │       ├── 001_tenant_schema.py
│   │       ├── 002_claims_tables.py
│   │       └── 003_audit_tables.py
│   ├── tenant_manager.py         # NEW: Multi-tenant routing
│   └── connection.py             # Extended
├── models/
│   ├── tenant.py                 # NEW: Tenant model
│   ├── claim.py                  # NEW: Claim model
│   ├── policy.py                 # NEW: Policy model
│   ├── provider.py               # NEW: Provider model
│   ├── member.py                 # NEW: Member model
│   └── audit.py                  # NEW: Audit log model
└── schemas/
    ├── tenant.py                 # NEW
    ├── claim.py                  # NEW
    ├── policy.py                 # NEW
    ├── provider.py               # NEW
    └── member.py                 # NEW
```

#### 2.1.3 Exit Criteria

- [ ] All migrations run successfully
- [ ] Tenant isolation verified with tests
- [ ] 90%+ test coverage for models
- [ ] Configuration validation working

---

### 2.2 Sprint 2: Provider Abstraction Layer - Part 1 (LLM & OCR)

#### 2.2.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 1.2.1 | Research LiteLLM latest version and API | High | None |
| 1.2.2 | Create base gateway abstract class | High | None |
| 1.2.3 | Implement LLM Gateway with LiteLLM | High | 1.2.1, 1.2.2 |
| 1.2.4 | Add Ollama/Qwen2.5-VL provider | High | 1.2.3 |
| 1.2.5 | Add GPT-4 Vision fallback provider | High | 1.2.3 |
| 1.2.6 | Implement confidence-based fallback logic | High | 1.2.4, 1.2.5 |
| 1.2.7 | Research PaddleOCR latest version | High | None |
| 1.2.8 | Create OCR Gateway with provider abstraction | High | 1.2.2 |
| 1.2.9 | Implement PaddleOCR provider | High | 1.2.7, 1.2.8 |
| 1.2.10 | Implement Azure Document Intelligence fallback | High | 1.2.8 |
| 1.2.11 | Create provider health monitoring | Medium | 1.2.3, 1.2.8 |
| 1.2.12 | Write integration tests with mocked providers | High | All above |

#### 2.2.2 Deliverables

```
src/
├── gateways/                     # NEW: Provider abstraction layer
│   ├── __init__.py
│   ├── base.py                   # Abstract gateway base class
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── gateway.py            # LLM Gateway using LiteLLM
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── ollama.py         # Ollama/Qwen2.5-VL
│   │   │   └── openai.py         # GPT-4 Vision
│   │   └── fallback.py           # Fallback controller
│   ├── ocr/
│   │   ├── __init__.py
│   │   ├── gateway.py            # OCR Gateway
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── paddleocr.py      # PaddleOCR provider
│   │   │   └── azure_di.py       # Azure Document Intelligence
│   │   └── fallback.py           # Confidence-based fallback
│   └── health.py                 # Provider health monitoring
```

#### 2.2.3 Key Implementation Details

```python
# src/gateways/base.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional
from pydantic import BaseModel
from enum import Enum

class ProviderStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

T = TypeVar("T")
R = TypeVar("R")

class GatewayResult(BaseModel, Generic[T]):
    """Standard gateway response wrapper."""
    success: bool
    data: Optional[T] = None
    provider: str
    fallback_used: bool = False
    confidence: float = 1.0
    latency_ms: int = 0
    error: Optional[str] = None

class BaseGateway(ABC, Generic[T, R]):
    """Abstract base for all provider gateways."""

    @abstractmethod
    async def execute(self, request: T) -> GatewayResult[R]:
        """Execute the primary operation with automatic fallback."""
        pass

    @abstractmethod
    async def health_check(self) -> ProviderStatus:
        """Check provider health status."""
        pass
```

#### 2.2.4 Exit Criteria

- [ ] LLM Gateway functional with Ollama
- [ ] OCR Gateway functional with PaddleOCR
- [ ] Fallback to commercial providers working
- [ ] Health monitoring operational
- [ ] 85%+ test coverage

---

### 2.3 Sprint 3: Provider Abstraction Layer - Part 2 (Translation, Rules, Medical NLP)

#### 2.3.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 1.3.1 | Research LibreTranslate API and deployment | High | None |
| 1.3.2 | Create Translation Gateway | High | 1.3.1 |
| 1.3.3 | Implement LibreTranslate provider | High | 1.3.2 |
| 1.3.4 | Implement Azure Translator fallback | Medium | 1.3.2 |
| 1.3.5 | Research GoRules ZEN engine and Python bindings | High | None |
| 1.3.6 | Create Rules Engine Gateway | High | 1.3.5 |
| 1.3.7 | Implement ZEN provider with JSON rules | High | 1.3.6 |
| 1.3.8 | Research MedCAT and UMLS requirements | High | None |
| 1.3.9 | Create Medical NLP Gateway | High | 1.3.8 |
| 1.3.10 | Implement MedCAT provider | High | 1.3.9 |
| 1.3.11 | Add medspaCy fallback (UMLS-free) | Medium | 1.3.9 |
| 1.3.12 | Create Currency Gateway with caching | Medium | None |
| 1.3.13 | Write comprehensive gateway tests | High | All above |

#### 2.3.2 Deliverables

```
src/gateways/
├── translation/
│   ├── __init__.py
│   ├── gateway.py
│   └── providers/
│       ├── libretranslate.py
│       └── azure_translator.py
├── rules/
│   ├── __init__.py
│   ├── gateway.py
│   └── providers/
│       └── zen.py                # GoRules ZEN
├── medical/
│   ├── __init__.py
│   ├── gateway.py
│   └── providers/
│       ├── medcat.py
│       └── medspacy.py
└── currency/
    ├── __init__.py
    ├── gateway.py
    └── providers/
        ├── fawazahmed.py         # Free API
        └── fixer.py              # Commercial fallback
```

#### 2.3.3 Exit Criteria

- [ ] All 6 gateways implemented and tested
- [ ] Provider switching via configuration
- [ ] Automatic fallback functional
- [ ] Gateway metrics exposed
- [ ] 85%+ test coverage

---

### 2.4 Sprint 4: Authentication & Multi-Tenancy

#### 2.4.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 1.4.1 | Extend JWT authentication with tenant claims | High | None |
| 1.4.2 | Implement RBAC permission system | High | 1.4.1 |
| 1.4.3 | Create tenant onboarding service | High | 1.4.2 |
| 1.4.4 | Implement tenant context middleware | High | 1.4.3 |
| 1.4.5 | Add tenant-specific configuration loading | High | 1.4.4 |
| 1.4.6 | Create tenant admin API endpoints | Medium | 1.4.3 |
| 1.4.7 | Implement tenant-level rate limiting | Medium | 1.4.4 |
| 1.4.8 | Write security and isolation tests | High | All above |

#### 2.4.2 Deliverables

```
src/
├── api/
│   ├── middleware/               # NEW
│   │   ├── __init__.py
│   │   ├── tenant.py            # Tenant context middleware
│   │   └── rate_limit.py        # Per-tenant rate limiting
│   └── routes/
│       └── tenants.py           # NEW: Tenant admin API
├── services/
│   ├── auth.py                  # Extended with RBAC
│   └── tenant.py                # NEW: Tenant service
├── models/
│   ├── permission.py            # NEW: RBAC models
│   └── role.py                  # NEW
└── schemas/
    ├── permission.py            # NEW
    └── role.py                  # NEW
```

#### 2.4.3 JWT Claims Structure

```python
# Extended JWT claims
{
    "sub": "user_uuid",
    "tenant_id": "tenant_001",
    "roles": ["claims_processor", "viewer"],
    "permissions": ["claims:read", "claims:submit", "documents:upload"],
    "provider_preferences": {
        "llm": "ollama",
        "ocr": "paddleocr"
    },
    "exp": 1734567890,
    "iat": 1734564290
}
```

#### 2.4.4 Exit Criteria

- [ ] Multi-tenant isolation verified
- [ ] RBAC permissions enforced
- [ ] Tenant configuration working
- [ ] Security tests passing
- [ ] 90%+ coverage on auth code

---

## 3. Phase 2: Core Claims Processing

**Duration**: Sprints 5-8
**Goal**: Implement end-to-end claim submission and processing

### 3.1 Sprint 5: Document Processing Service

#### 3.1.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 2.1.1 | Create document upload endpoint | High | Phase 1 |
| 2.1.2 | Implement document storage service (MinIO) | High | 2.1.1 |
| 2.1.3 | Create OCR processing pipeline | High | 2.1.2 |
| 2.1.4 | Implement LLM document parsing | High | 2.1.3 |
| 2.1.5 | Create structured data extraction | High | 2.1.4 |
| 2.1.6 | Implement multi-page document handling | High | 2.1.3 |
| 2.1.7 | Add document validation service | Medium | 2.1.5 |
| 2.1.8 | Create async document processing with Celery | High | 2.1.3 |
| 2.1.9 | Write document processing tests | High | All above |

#### 3.1.2 Deliverables

```
src/
├── api/routes/
│   └── documents.py              # NEW: Document upload/status API
├── services/
│   ├── document/
│   │   ├── __init__.py
│   │   ├── service.py           # Document processing orchestrator
│   │   ├── ocr_processor.py     # OCR pipeline
│   │   ├── llm_parser.py        # LLM document parsing
│   │   └── validator.py         # Document validation
│   └── storage.py               # Extended for documents
├── tasks/
│   └── document_processing.py   # NEW: Celery tasks
└── schemas/
    └── document.py              # Extended
```

#### 3.1.3 Document Processing Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Upload    │────>│     OCR     │────>│  LLM Parse  │────>│  Validate   │
│  Document   │     │  Extraction │     │  Structure  │     │   Output    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
   Store in           PaddleOCR/          Qwen2.5-VL/         Schema
   MinIO               Azure              GPT-4 Vision        Validation
```

#### 3.1.4 Exit Criteria

- [ ] PDF/image upload working
- [ ] OCR extraction functional
- [ ] LLM parsing returning structured data
- [ ] Multi-page support working
- [ ] Async processing operational
- [ ] 80%+ test coverage

---

### 3.2 Sprint 6: Claims Submission API

#### 3.2.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 2.2.1 | Create claim submission endpoint | High | Sprint 5 |
| 2.2.2 | Implement claim validation service | High | 2.2.1 |
| 2.2.3 | Create claim status tracking | High | 2.2.1 |
| 2.2.4 | Implement claim state machine | High | 2.2.3 |
| 2.2.5 | Create claim retrieval and search API | High | 2.2.1 |
| 2.2.6 | Implement claim line item processing | High | 2.2.1 |
| 2.2.7 | Add claim event publishing (audit) | Medium | 2.2.4 |
| 2.2.8 | Create claim webhooks for status updates | Medium | 2.2.4 |
| 2.2.9 | Write claims API tests | High | All above |

#### 3.2.2 Deliverables

```
src/
├── api/routes/
│   └── claims.py                # NEW: Full claims API
├── services/
│   └── claims/
│       ├── __init__.py
│       ├── service.py           # Claims orchestrator
│       ├── submission.py        # Submission handling
│       ├── validation.py        # Claim validation
│       ├── state_machine.py     # State transitions
│       └── events.py            # Event publishing
├── models/
│   └── claim.py                 # Extended with line items
└── schemas/
    └── claim.py                 # Extended
```

#### 3.2.3 Claim State Machine

```python
# src/services/claims/state_machine.py
from enum import Enum
from typing import Dict, Set

class ClaimStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    DOC_PROCESSING = "doc_processing"
    VALIDATING = "validating"
    ADJUDICATING = "adjudicating"
    APPROVED = "approved"
    DENIED = "denied"
    NEEDS_REVIEW = "needs_review"
    PAYMENT_PROCESSING = "payment_processing"
    PAID = "paid"
    CLOSED = "closed"

# Valid state transitions
TRANSITIONS: Dict[ClaimStatus, Set[ClaimStatus]] = {
    ClaimStatus.DRAFT: {ClaimStatus.SUBMITTED},
    ClaimStatus.SUBMITTED: {ClaimStatus.DOC_PROCESSING},
    ClaimStatus.DOC_PROCESSING: {ClaimStatus.VALIDATING, ClaimStatus.NEEDS_REVIEW},
    ClaimStatus.VALIDATING: {ClaimStatus.ADJUDICATING, ClaimStatus.DENIED},
    ClaimStatus.ADJUDICATING: {ClaimStatus.APPROVED, ClaimStatus.DENIED, ClaimStatus.NEEDS_REVIEW},
    ClaimStatus.APPROVED: {ClaimStatus.PAYMENT_PROCESSING},
    ClaimStatus.PAYMENT_PROCESSING: {ClaimStatus.PAID, ClaimStatus.NEEDS_REVIEW},
    ClaimStatus.PAID: {ClaimStatus.CLOSED},
    ClaimStatus.NEEDS_REVIEW: {ClaimStatus.APPROVED, ClaimStatus.DENIED},
    ClaimStatus.DENIED: {ClaimStatus.CLOSED},
}
```

#### 3.2.4 Exit Criteria

- [ ] Full claim CRUD API working
- [ ] State machine enforcing valid transitions
- [ ] Audit events being published
- [ ] Claim search functional
- [ ] 85%+ test coverage

---

### 3.3 Sprint 7: Benefit Calculation Engine

#### 3.3.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 2.3.1 | Create benefit lookup service | High | Sprint 6 |
| 2.3.2 | Implement fee schedule management | High | 2.3.1 |
| 2.3.3 | Integrate GoRules ZEN engine | High | 2.3.2 |
| 2.3.4 | Create benefit calculation rules | High | 2.3.3 |
| 2.3.5 | Implement deduction calculation | High | 2.3.4 |
| 2.3.6 | Create patient share calculation | High | 2.3.5 |
| 2.3.7 | Add copay/coinsurance handling | High | 2.3.6 |
| 2.3.8 | Implement deductible tracking | High | 2.3.6 |
| 2.3.9 | Create benefit calculation tests | High | All above |

#### 3.3.2 Deliverables

```
src/
├── services/
│   └── benefits/
│       ├── __init__.py
│       ├── service.py           # Benefit calculation orchestrator
│       ├── lookup.py            # Benefit/Fee schedule lookup
│       ├── rules_engine.py      # GoRules ZEN integration
│       ├── calculator.py        # Calculation logic
│       └── patient_share.py     # Patient responsibility calc
├── rules/                       # NEW: Rule definitions
│   ├── benefit_rules.json       # Benefit calculation rules
│   ├── deduction_rules.json     # Deduction rules
│   └── validation_rules.json    # Validation rules
└── schemas/
    └── benefit.py               # NEW
```

#### 3.3.3 Benefit Calculation Example

```python
# src/services/benefits/calculator.py
from decimal import Decimal
from pydantic import BaseModel

class BenefitResult(BaseModel):
    """Result of benefit calculation for a line item."""
    line_number: int
    procedure_code: str
    charged_amount: Decimal
    allowed_amount: Decimal
    deductible_applied: Decimal
    copay_amount: Decimal
    coinsurance_amount: Decimal
    benefit_paid: Decimal
    patient_responsibility: Decimal
    adjustment_codes: list[str]
    remarks: list[str]

async def calculate_benefit(
    claim_line: ClaimLineItem,
    policy: Policy,
    fee_schedule: FeeSchedule,
    ytd_deductible_met: Decimal
) -> BenefitResult:
    """Calculate benefit for a single claim line item."""

    # 1. Get allowed amount from fee schedule
    allowed = fee_schedule.get_allowed_amount(claim_line.procedure_code)

    # 2. Apply deductible
    remaining_deductible = policy.deductible - ytd_deductible_met
    deductible_applied = min(allowed, remaining_deductible)

    # 3. Calculate coinsurance on remaining amount
    after_deductible = allowed - deductible_applied
    coinsurance_rate = policy.get_coinsurance_rate(claim_line.procedure_code)
    patient_coinsurance = after_deductible * coinsurance_rate

    # 4. Apply copay if applicable
    copay = policy.get_copay(claim_line.procedure_code)

    # 5. Calculate final amounts
    patient_responsibility = deductible_applied + patient_coinsurance + copay
    benefit_paid = allowed - patient_responsibility

    return BenefitResult(...)
```

#### 3.3.4 Exit Criteria

- [ ] Fee schedule lookup working
- [ ] Rules engine processing correctly
- [ ] Benefit calculations accurate
- [ ] Patient share calculations correct
- [ ] 90%+ test coverage on calculations

---

### 3.4 Sprint 8: Claim Adjudication Pipeline

#### 3.4.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 2.4.1 | Create adjudication orchestrator | High | Sprint 7 |
| 2.4.2 | Implement policy validation | High | 2.4.1 |
| 2.4.3 | Create eligibility verification | High | 2.4.2 |
| 2.4.4 | Implement provider network validation | High | 2.4.2 |
| 2.4.5 | Create auto-adjudication pipeline | High | 2.4.3, 2.4.4 |
| 2.4.6 | Implement EOB generation | Medium | 2.4.5 |
| 2.4.7 | Add adjudication result caching | Medium | 2.4.5 |
| 2.4.8 | Create full pipeline integration tests | High | All above |

#### 3.4.2 Deliverables

```
src/
├── services/
│   └── adjudication/
│       ├── __init__.py
│       ├── service.py           # Adjudication orchestrator
│       ├── pipeline.py          # Processing pipeline
│       ├── policy_validator.py  # Policy validation
│       ├── eligibility.py       # Eligibility check
│       ├── network_validator.py # Provider network validation
│       └── eob_generator.py     # EOB generation
└── tasks/
    └── adjudication.py          # NEW: Async adjudication tasks
```

#### 3.4.3 Adjudication Pipeline Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        ADJUDICATION PIPELINE                              │
└──────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   Policy    │────>│ Eligibility │────>│  Provider   │
    │ Validation  │     │   Check     │     │  Network    │
    └─────────────┘     └─────────────┘     └─────────────┘
           │                   │                   │
           ▼                   ▼                   ▼
    Policy active?      Member eligible?    Provider in-network?
           │                   │                   │
           └───────────────────┴───────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Benefit Engine    │
                    │  (GoRules + Calc)   │
                    └─────────────────────┘
                               │
                               ▼
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   APPROVE   │     │    DENY     │     │   REVIEW    │
    │ (auto-adjud)│     │ (violation) │     │ (flagged)   │
    └─────────────┘     └─────────────┘     └─────────────┘
```

#### 3.4.4 Exit Criteria

- [ ] End-to-end claim processing working
- [ ] Auto-adjudication for clean claims
- [ ] Proper denial handling
- [ ] EOB generation functional
- [ ] 85%+ test coverage

---

## 4. Phase 3: Advanced Features

**Duration**: Sprints 9-12
**Goal**: Add medical validation, FWA detection, and internationalization

### 4.1 Sprint 9: Medical Validation

#### 4.1.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 3.1.1 | Integrate MedCAT for entity extraction | High | Phase 2 |
| 3.1.2 | Create medical code validation service | High | 3.1.1 |
| 3.1.3 | Implement ICD-10 to CPT mapping | High | 3.1.2 |
| 3.1.4 | Add medical necessity validation | High | 3.1.3 |
| 3.1.5 | Create diagnosis-procedure compatibility check | High | 3.1.3 |
| 3.1.6 | Add Australian coding support (ICD-10-AM, ACHI) | Medium | 3.1.3 |
| 3.1.7 | Create clinically implausible detection | Medium | 3.1.5 |
| 3.1.8 | Write medical validation tests | High | All above |

#### 4.1.2 Deliverables

```
src/
├── services/
│   └── medical/
│       ├── __init__.py
│       ├── service.py           # Medical validation orchestrator
│       ├── entity_extractor.py  # MedCAT integration
│       ├── code_validator.py    # ICD-10, CPT validation
│       ├── code_mapper.py       # Diagnosis to procedure mapping
│       ├── necessity.py         # Medical necessity check
│       └── compatibility.py     # Procedure compatibility
└── data/
    ├── icd10_cm.json           # US diagnosis codes
    ├── icd10_am.json           # Australian diagnosis codes
    ├── cpt_codes.json          # CPT procedure codes
    └── achi_codes.json         # Australian procedure codes
```

#### 4.1.3 Exit Criteria

- [ ] Medical entity extraction working
- [ ] Code validation accurate
- [ ] Diagnosis-procedure mapping functional
- [ ] US and AU coding supported
- [ ] 85%+ test coverage

---

### 4.2 Sprint 10: Fraud Detection (FWA)

#### 4.2.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 3.2.1 | Create FWA detection service | High | Phase 2 |
| 3.2.2 | Implement duplicate claim detection | High | 3.2.1 |
| 3.2.3 | Create billing pattern analyzer | High | 3.2.1 |
| 3.2.4 | Implement upcoding detection | High | 3.2.3 |
| 3.2.5 | Add provider behavior scoring | Medium | 3.2.3 |
| 3.2.6 | Create XGBoost FWA model integration | High | 3.2.3 |
| 3.2.7 | Implement FWA risk scoring | High | 3.2.6 |
| 3.2.8 | Add FWA alert generation | Medium | 3.2.7 |
| 3.2.9 | Write FWA detection tests | High | All above |

#### 4.2.2 Deliverables

```
src/
├── services/
│   └── fwa/
│       ├── __init__.py
│       ├── service.py           # FWA orchestrator
│       ├── duplicate_detector.py
│       ├── pattern_analyzer.py
│       ├── upcoding_detector.py
│       ├── provider_scoring.py
│       ├── ml_model.py          # XGBoost integration
│       └── risk_scorer.py       # Risk scoring
└── ml/
    ├── models/
    │   └── fwa_xgboost_v1.joblib
    └── training/
        └── fwa_training.py
```

#### 4.2.3 FWA Risk Scoring

```python
# src/services/fwa/risk_scorer.py
from pydantic import BaseModel
from enum import Enum

class FWARiskLevel(str, Enum):
    LOW = "low"           # 0.0 - 0.3
    MEDIUM = "medium"     # 0.3 - 0.6
    HIGH = "high"         # 0.6 - 0.8
    CRITICAL = "critical" # 0.8 - 1.0

class FWAResult(BaseModel):
    """FWA analysis result."""
    claim_id: str
    risk_score: float  # 0.0 - 1.0
    risk_level: FWARiskLevel
    flags: list[str]
    duplicate_found: bool
    upcoding_detected: bool
    pattern_anomalies: list[str]
    recommendation: str  # "approve", "review", "deny"
    model_version: str
    confidence: float
```

#### 4.2.4 Exit Criteria

- [ ] Duplicate detection working
- [ ] Upcoding detection functional
- [ ] ML model integrated
- [ ] Risk scoring operational
- [ ] 80%+ test coverage

---

### 4.3 Sprint 11: Internationalization (i18n)

#### 4.3.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 3.3.1 | Set up LibreTranslate service | High | Phase 2 |
| 3.3.2 | Implement Arabic document translation | High | 3.3.1 |
| 3.3.3 | Create bidirectional text handling | High | 3.3.2 |
| 3.3.4 | Implement currency conversion service | High | None |
| 3.3.5 | Add multi-currency claim support | High | 3.3.4 |
| 3.3.6 | Create currency audit trail | Medium | 3.3.5 |
| 3.3.7 | Implement UI localization support | Medium | 3.3.3 |
| 3.3.8 | Write i18n tests | High | All above |

#### 4.3.2 Deliverables

```
src/
├── services/
│   └── i18n/
│       ├── __init__.py
│       ├── service.py           # i18n orchestrator
│       ├── translation.py       # Translation service
│       ├── currency.py          # Currency conversion
│       └── localization.py      # UI localization
├── gateways/
│   ├── translation/             # Already exists
│   └── currency/                # Already exists
└── locales/
    ├── en.json
    └── ar.json
```

#### 4.3.3 Exit Criteria

- [ ] Arabic translation working
- [ ] Currency conversion accurate
- [ ] Multi-currency claims supported
- [ ] 85%+ test coverage

---

### 4.4 Sprint 12: Demo Mode & Admin Portal

#### 4.4.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 3.4.1 | Create demo mode configuration | High | Phase 2 |
| 3.4.2 | Implement service adapters (demo/live) | High | 3.4.1 |
| 3.4.3 | Create admin API for policy management | High | 3.4.2 |
| 3.4.4 | Create admin API for provider management | High | 3.4.2 |
| 3.4.5 | Create admin API for member management | High | 3.4.2 |
| 3.4.6 | Create admin API for fee schedules | High | 3.4.2 |
| 3.4.7 | Implement payment simulation | High | 3.4.2 |
| 3.4.8 | Build Streamlit admin portal - Policies | High | 3.4.3 |
| 3.4.9 | Build Streamlit admin portal - Providers | High | 3.4.4 |
| 3.4.10 | Build Streamlit admin portal - Members | High | 3.4.5 |
| 3.4.11 | Build Streamlit admin portal - Fee Schedules | High | 3.4.6 |
| 3.4.12 | Create demo data generation script | Medium | 3.4.2 |
| 3.4.13 | Write admin portal tests | High | All above |

#### 4.4.2 Deliverables

```
src/
├── api/routes/
│   └── admin/
│       ├── __init__.py
│       ├── policies.py          # Policy admin API
│       ├── providers.py         # Provider admin API
│       ├── members.py           # Member admin API
│       ├── fee_schedules.py     # Fee schedule admin API
│       └── payments.py          # Payment simulation API
├── services/
│   └── adapters/
│       ├── __init__.py
│       ├── base.py              # Abstract adapter
│       ├── policy_adapter.py    # Demo/Live policy adapter
│       ├── provider_adapter.py
│       ├── member_adapter.py
│       └── payment_adapter.py
├── models/
│   └── demo/
│       ├── __init__.py
│       ├── policy.py            # Demo policy model
│       ├── provider.py
│       ├── member.py
│       └── fee_schedule.py
streamlit_app/
├── app.py                       # Main app
├── pages/
│   ├── 01_policies.py          # Policy management
│   ├── 02_providers.py         # Provider management
│   ├── 03_members.py           # Member management
│   ├── 04_fee_schedules.py     # Fee schedule management
│   ├── 05_claims.py            # Claims dashboard
│   └── 06_analytics.py         # Analytics
scripts/
└── generate_demo_data.py        # Demo data generator
```

#### 4.4.3 Exit Criteria

- [ ] Demo mode fully functional
- [ ] Admin portal operational
- [ ] All external system simulation working
- [ ] Demo data generation script working
- [ ] 80%+ test coverage

---

## 5. Phase 4: Production Readiness

**Duration**: Sprints 13-16
**Goal**: Performance optimization, security hardening, and deployment

### 5.1 Sprint 13: Performance Optimization

#### 5.1.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 4.1.1 | Implement Redis caching strategy | High | Phase 3 |
| 4.1.2 | Add database query optimization | High | 4.1.1 |
| 4.1.3 | Implement connection pooling | High | 4.1.2 |
| 4.1.4 | Add async processing optimization | High | 4.1.2 |
| 4.1.5 | Create performance monitoring | High | 4.1.3 |
| 4.1.6 | Implement load testing suite | High | 4.1.4 |
| 4.1.7 | Optimize OCR/LLM pipeline | Medium | 4.1.4 |
| 4.1.8 | Add request/response compression | Medium | 4.1.4 |

#### 5.1.2 Exit Criteria

- [ ] < 30s claim processing time
- [ ] 1000+ concurrent users supported
- [ ] < 500ms API response time
- [ ] Load tests passing

---

### 5.2 Sprint 14: Security Hardening

#### 5.2.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 4.2.1 | Implement PHI encryption at rest | Critical | Phase 3 |
| 4.2.2 | Add field-level encryption for sensitive data | Critical | 4.2.1 |
| 4.2.3 | Implement secure secret management (Vault) | High | 4.2.1 |
| 4.2.4 | Add security headers middleware | High | 4.2.3 |
| 4.2.5 | Implement request signing | Medium | 4.2.3 |
| 4.2.6 | Run security scanning (Bandit, Safety) | High | All above |
| 4.2.7 | Conduct penetration testing | High | 4.2.6 |
| 4.2.8 | Create security incident response plan | Medium | 4.2.7 |

#### 5.2.2 Exit Criteria

- [ ] All PHI encrypted
- [ ] Security scans passing
- [ ] Penetration test completed
- [ ] No critical/high vulnerabilities

---

### 5.3 Sprint 15: Monitoring & Observability

#### 5.3.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 4.3.1 | Configure Prometheus metrics | High | Phase 3 |
| 4.3.2 | Create Grafana dashboards | High | 4.3.1 |
| 4.3.3 | Set up Loki for log aggregation | High | 4.3.2 |
| 4.3.4 | Implement distributed tracing | Medium | 4.3.3 |
| 4.3.5 | Create alerting rules | High | 4.3.2 |
| 4.3.6 | Build operations runbook | High | 4.3.5 |
| 4.3.7 | Create health check endpoints | High | 4.3.1 |
| 4.3.8 | Implement SLA monitoring | Medium | 4.3.5 |

#### 5.3.2 Exit Criteria

- [ ] All metrics exposed
- [ ] Dashboards operational
- [ ] Alerting configured
- [ ] Runbook completed

---

### 5.4 Sprint 16: Deployment & Documentation

#### 5.4.1 Tasks

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| 4.4.1 | Create Kubernetes manifests | High | Sprint 15 |
| 4.4.2 | Create Helm charts | High | 4.4.1 |
| 4.4.3 | Set up CI/CD pipeline | High | 4.4.2 |
| 4.4.4 | Create deployment documentation | High | 4.4.3 |
| 4.4.5 | Write API documentation | High | 4.4.3 |
| 4.4.6 | Create user guide | Medium | 4.4.4 |
| 4.4.7 | Conduct UAT | High | 4.4.4 |
| 4.4.8 | Production deployment | High | 4.4.7 |

#### 5.4.2 Deliverables

```
kubernetes/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── secrets.yaml
├── overlays/
│   ├── development/
│   ├── staging/
│   └── production/
helm/
├── reimp/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
.github/
└── workflows/
    ├── ci.yml
    ├── cd-staging.yml
    └── cd-production.yml
docs/
├── deployment/
│   ├── kubernetes.md
│   ├── docker.md
│   └── configuration.md
├── api/
│   └── openapi.yaml
└── user-guide/
    └── getting-started.md
```

#### 5.4.3 Exit Criteria

- [ ] Kubernetes deployment working
- [ ] CI/CD pipeline functional
- [ ] Documentation complete
- [ ] UAT passed
- [ ] Production deployed

---

## 6. Testing Strategy

### 6.1 Test Categories

| Category | Coverage Target | Description |
|----------|-----------------|-------------|
| **Unit Tests** | 90%+ | Individual functions/classes |
| **Integration Tests** | 80%+ | Component interactions |
| **API Tests** | 100% endpoints | All API endpoints |
| **Gateway Tests** | 85%+ | Provider abstraction |
| **Security Tests** | OWASP Top 10 | Security vulnerabilities |
| **Performance Tests** | NFRs | Load and stress testing |
| **E2E Tests** | Critical paths | Full claim lifecycle |

### 6.2 Test Infrastructure

```
tests/
├── conftest.py                  # Shared fixtures
├── unit/
│   ├── test_models.py
│   ├── test_schemas.py
│   ├── test_services/
│   └── test_gateways/
├── integration/
│   ├── test_database.py
│   ├── test_claim_pipeline.py
│   └── test_adjudication.py
├── api/
│   ├── test_claims_routes.py
│   ├── test_documents_routes.py
│   └── test_admin_routes.py
├── security/
│   ├── test_authentication.py
│   ├── test_authorization.py
│   └── test_injection.py
├── performance/
│   ├── locustfile.py            # Load testing
│   └── test_benchmarks.py
└── e2e/
    └── test_claim_lifecycle.py
```

### 6.3 Key Test Scenarios

1. **Claim Submission Flow**
   - Valid claim submission
   - Invalid document format
   - Missing required fields
   - Duplicate claim detection

2. **Document Processing**
   - PDF OCR extraction
   - Image processing
   - Multi-page handling
   - Arabic document translation

3. **Adjudication**
   - Auto-approval path
   - Denial scenarios
   - Manual review triggers
   - Benefit calculation accuracy

4. **Multi-Tenancy**
   - Tenant isolation
   - Cross-tenant access prevention
   - Tenant configuration

5. **Provider Fallback**
   - Primary provider failure
   - Confidence-based fallback
   - All providers unavailable

---

## 7. Risk Mitigation Plan

| Risk | Mitigation | Contingency |
|------|------------|-------------|
| PaddleOCR accuracy on Arabic | Test early in Sprint 5 | Use Azure as primary for Arabic |
| Qwen2.5-VL parsing accuracy | A/B test vs GPT-4 in Sprint 5 | Lower confidence threshold |
| UMLS license delay | Apply in Sprint 1 | Use medspaCy without UMLS |
| GPU infrastructure | Validate in Sprint 1 | Cloud GPU (AWS/GCP) |
| GoRules performance at scale | Load test in Sprint 7 | Consider Drools if needed |

---

## 8. Approval Checklist

**Before proceeding to implementation, confirm:**

- [ ] Design document approved
- [ ] GPU infrastructure available or cloud alternative confirmed
- [ ] UMLS license application submitted
- [ ] Development environment set up
- [ ] Team roles assigned
- [ ] Sprint schedule confirmed

---

## 9. Next Steps

1. **Immediate (This Sprint)**:
   - Set up development environment
   - Configure Docker Compose for local development
   - Create first database migration

2. **Sprint 1 Kickoff**:
   - Begin Task 1.1.1: Extended configuration
   - Apply for UMLS license
   - Validate GPU access

---

**Document Status**: Ready for Approval
**Author**: Claude Code (AI Assistant)
**Review Date**: TBD
