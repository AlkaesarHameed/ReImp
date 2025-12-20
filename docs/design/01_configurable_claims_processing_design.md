# Reimbursement Claims Management System
# Configurable Hybrid Architecture - Design Document

**Document Version**: 1.0
**Design Date**: December 18, 2025
**Status**: Draft - Pending Approval
**Author**: Claude Code (AI Assistant)
**Based On**: [03_configurable_hybrid_architecture_research.md](../research/03_configurable_hybrid_architecture_research.md)

---

## 1. Executive Summary

### 1.1 Overview

This design document specifies a **Reimbursement Claims Management and Auto-Processing System** with a configurable hybrid architecture. The system enables healthcare insurance providers to process claims using swappable AI/ML providers, allowing organizations to balance cost, accuracy, and data privacy requirements.

### 1.2 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Architecture Pattern** | Provider Abstraction Layer (Strategy Pattern) | Enables runtime switching between commercial and open-source providers |
| **Primary LLM** | Qwen2.5-VL via Ollama | Cost-effective, on-premises deployment, no per-request costs |
| **OCR Engine** | PaddleOCR with Azure fallback | 98%+ accuracy for standard documents, commercial fallback for edge cases |
| **Rules Engine** | GoRules ZEN | Open-source, JSON-based rules, sub-millisecond execution |
| **Medical NLP** | MedCAT + medspaCy | UMLS-based entity extraction, no licensing costs |
| **Multi-tenancy** | Database-per-tenant | HIPAA compliance, complete data isolation |

### 1.3 Business Value

- **Cost Reduction**: 70-90% reduction in AI/ML operating costs using open-source defaults
- **Flexibility**: Switch providers without code changes via environment configuration
- **Resilience**: Automatic failover prevents service disruption
- **Compliance**: Sensitive data processing on-premises for HIPAA/privacy requirements
- **Scalability**: No per-request API limits with self-hosted providers

---

## 2. Requirements Specification

### 2.1 Business Objectives

| ID | Objective | Success Criteria |
|----|-----------|------------------|
| BO-1 | Automate claims processing | 80%+ claims processed without manual intervention |
| BO-2 | Reduce processing costs | 50% reduction in per-claim processing cost |
| BO-3 | Improve processing speed | Average claim processed in < 30 seconds |
| BO-4 | Ensure accuracy | 95%+ accuracy on benefit calculation and deduction |
| BO-5 | Maintain compliance | 100% HIPAA compliance, full audit trail |
| BO-6 | Support multiple markets | US (ICD-10-CM, CPT) and Australian (ICD-10-AM, ACHI) coding |

### 2.2 Functional Requirements

#### 2.2.1 Claims Information Capture
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | Extract claim header information (patient, provider, dates) | Must Have |
| FR-1.2 | Parse line items with procedure codes, diagnosis codes, charges | Must Have |
| FR-1.3 | Support multiple document formats (PDF, scanned images, CMS-1500, UB-04) | Must Have |
| FR-1.4 | Handle handwritten annotations on claim forms | Should Have |

#### 2.2.2 Policy and Benefit Processing
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | Validate claims against policy terms and conditions | Must Have |
| FR-2.2 | Apply benefit deduction rules per policy class | Must Have |
| FR-2.3 | Calculate patient share with threshold validation | Must Have |
| FR-2.4 | Support configurable benefit tables per tenant | Must Have |

#### 2.2.3 Medical Validation
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | Validate medical necessity for procedures | Must Have |
| FR-3.2 | Map diagnosis to procedure codes (ICD-10 to CPT/ACHI) | Must Have |
| FR-3.3 | Detect clinically implausible combinations | Should Have |
| FR-3.4 | Support both US and Australian coding standards | Must Have |

#### 2.2.4 Document Processing
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | OCR extraction with 95%+ accuracy | Must Have |
| FR-4.2 | Handwriting recognition (ICR) for annotations | Should Have |
| FR-4.3 | Document tampering detection | Should Have |
| FR-4.4 | Multi-page document handling | Must Have |

#### 2.2.5 Fraud Detection
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | Detect billing pattern anomalies | Must Have |
| FR-5.2 | Flag duplicate claims | Must Have |
| FR-5.3 | Identify upcoding attempts | Should Have |
| FR-5.4 | Provider behavior analysis | Could Have |

#### 2.2.6 Internationalization
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-6.1 | Arabic-English translation for documents | Must Have |
| FR-6.2 | Right-to-left (RTL) UI support | Must Have |
| FR-6.3 | Currency conversion with audit trail | Must Have |
| FR-6.4 | Multi-language claim forms | Should Have |

#### 2.2.7 Multi-Tenancy
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-7.1 | Complete data isolation between tenants | Must Have |
| FR-7.2 | Tenant-specific configuration (rules, thresholds) | Must Have |
| FR-7.3 | Per-tenant provider preferences | Should Have |
| FR-7.4 | Tenant-level usage metering | Must Have |

### 2.3 Non-Functional Requirements

| ID | Category | Requirement | Target |
|----|----------|-------------|--------|
| NFR-1 | Performance | Claim processing time | < 30 seconds average |
| NFR-2 | Performance | Document OCR time | < 5 seconds per page |
| NFR-3 | Availability | System uptime | 99.9% (8.76 hours downtime/year) |
| NFR-4 | Scalability | Concurrent claims | 1000+ simultaneous |
| NFR-5 | Security | Data encryption | AES-256 at rest, TLS 1.3 in transit |
| NFR-6 | Compliance | Audit logging | Complete audit trail, 7-year retention |
| NFR-7 | Latency | API response time | < 500ms for synchronous calls |
| NFR-8 | Throughput | Daily claim volume | 50,000+ claims/day |

### 2.4 Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Regulatory | HIPAA compliance required | Database-per-tenant, encryption, audit logging |
| Technical | Must integrate with existing ERP systems | REST API compatibility required |
| Budget | Infrastructure cost cap of $50K/month | Prioritize open-source providers |
| Timeline | MVP in 4 months | Phase-based delivery required |
| Technical | Arabic language support | RTL UI, bidirectional text handling |

### 2.5 Assumptions

| ID | Assumption | Risk if Invalid | Validation |
|----|------------|-----------------|------------|
| A-1 | GPU infrastructure available for ML models | High - open-source models require GPU | Confirm infrastructure specs |
| A-2 | UMLS license obtainable for MedCAT | Medium - impacts medical NLP | Verify licensing process |
| A-3 | 90%+ of claims are standard format | Medium - affects OCR accuracy | Analyze historical claims |
| A-4 | Commercial API fallback acceptable | Low - fallback is safety net | Business approval obtained |
| A-5 | Docker/Kubernetes deployment | Low - standard practice | Confirm DevOps capabilities |

---

## 3. Architecture Design

### 3.1 System Context Diagram

```
                                    ┌─────────────────────────────────────┐
                                    │         External Systems            │
                                    ├─────────────────────────────────────┤
                                    │  • ERP/Policy Management System     │
                                    │  • Provider Network Database        │
                                    │  • Member Eligibility Service       │
                                    │  • Payment Gateway                  │
                                    └────────────────┬────────────────────┘
                                                     │
                                                     ▼
    ┌─────────────────┐                  ┌──────────────────────┐
    │   Claims Portal │──────────────────│   ReImp Claims API   │
    │   (Web/Mobile)  │     HTTPS        │   (FastAPI Backend)  │
    └─────────────────┘                  └──────────────────────┘
                                                     │
                         ┌───────────────────────────┼───────────────────────────┐
                         │                           │                           │
                         ▼                           ▼                           ▼
              ┌────────────────────┐    ┌────────────────────┐    ┌────────────────────┐
              │  Document Service  │    │   Claims Engine    │    │  Analytics Service │
              │  (OCR, ICR, LLM)   │    │  (Rules, Adjud.)   │    │  (FWA, Reporting)  │
              └────────────────────┘    └────────────────────┘    └────────────────────┘
                         │                           │                           │
                         └───────────────────────────┼───────────────────────────┘
                                                     │
                                                     ▼
                                    ┌─────────────────────────────────────┐
                                    │     Provider Abstraction Layer      │
                                    │  (Configurable AI/ML Gateways)     │
                                    └────────────────┬────────────────────┘
                                                     │
              ┌──────────────┬──────────────┬────────┴────────┬──────────────┬──────────────┐
              ▼              ▼              ▼                 ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐       ┌──────────┐  ┌──────────┐  ┌──────────┐
        │   LLM    │  │   OCR    │  │  Trans   │       │  Rules   │  │ Currency │  │ Med NLP  │
        │ Gateway  │  │ Gateway  │  │ Gateway  │       │ Gateway  │  │ Gateway  │  │ Gateway  │
        └────┬─────┘  └────┬─────┘  └────┬─────┘       └────┬─────┘  └────┬─────┘  └────┬─────┘
             │              │              │                 │              │              │
      ┌──────┴──────┐┌─────┴──────┐┌─────┴──────┐   ┌──────┴──────┐┌─────┴──────┐┌─────┴──────┐
      ▼             ▼▼            ▼▼            ▼   ▼             ▼▼            ▼▼            ▼
   ┌─────┐      ┌─────┐┌─────┐ ┌─────┐┌─────┐ ┌─────┐┌─────┐  ┌─────┐┌─────┐ ┌─────┐┌─────┐ ┌─────┐
   │Ollama│     │GPT-4││Paddle│ │Azure││Libre│ │Azure││ ZEN │  │Drools││Fawaz│ │Fixer││MedCAT│ │AWS  │
   │Qwen │      │     ││OCR  │ │OCR  ││Trans│ │Trans││     │  │     ││     │ │     ││     │ │Comp.│
   └─────┘      └─────┘└─────┘ └─────┘└─────┘ └─────┘└─────┘  └─────┘└─────┘ └─────┘└─────┘ └─────┘
   Open-Src    Commercial Open-Src Commercial Open  Commercial Open   Comm.  Free   Comm.  Open   Comm.
```

### 3.2 Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                        API Gateway (Kong/Traefik)                                │
│                                    Rate Limiting, Auth, Load Balancing                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         FastAPI Application                                      │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐│
│  │                                    API Layer (Routers)                                       ││
│  ├─────────────┬─────────────┬─────────────┬─────────────┬─────────────┬─────────────┬─────────┤│
│  │  /claims    │  /documents │  /policies  │  /providers │  /analytics │  /admin     │ /health ││
│  └─────────────┴─────────────┴─────────────┴─────────────┴─────────────┴─────────────┴─────────┘│
│                                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐│
│  │                                    Service Layer                                             ││
│  ├───────────────────┬───────────────────┬───────────────────┬─────────────────────────────────┤│
│  │  ClaimsService    │  DocumentService  │  BenefitService   │  FraudDetectionService          ││
│  │  - submit_claim   │  - process_doc    │  - calculate      │  - analyze_patterns             ││
│  │  - adjudicate     │  - extract_data   │  - apply_rules    │  - detect_anomalies             ││
│  │  - get_status     │  - validate       │  - get_share      │  - score_claim                  ││
│  └───────────────────┴───────────────────┴───────────────────┴─────────────────────────────────┘│
│                                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐│
│  │                                Provider Abstraction Layer                                    ││
│  ├──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────────┤│
│  │  LLMGateway  │  OCRGateway  │  TransGateway│  RulesGateway│ CurrencyGW   │ MedicalNLPGateway││
│  │  (LiteLLM)   │  (Strategy)  │  (Strategy)  │  (ZEN/Drools)│ (Cached)     │ (MedCAT/spaCy)   ││
│  └──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────────┘│
│                                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐│
│  │                                    Data Layer                                                ││
│  ├───────────────────┬───────────────────┬───────────────────┬─────────────────────────────────┤│
│  │  ClaimRepository  │  PolicyRepository │  TenantRepository │  AuditRepository                ││
│  │  (SQLAlchemy)     │  (SQLAlchemy)     │  (SQLAlchemy)     │  (Time-series)                  ││
│  └───────────────────┴───────────────────┴───────────────────┴─────────────────────────────────┘│
│                                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                    │
          ┌─────────────────────────────────────────┼─────────────────────────────────────────┐
          ▼                                         ▼                                         ▼
┌─────────────────────┐               ┌─────────────────────┐               ┌─────────────────────┐
│    PostgreSQL       │               │       Redis         │               │   Message Queue     │
│  (Tenant Databases) │               │  (Cache + Sessions) │               │  (Redis Streams)    │
│                     │               │                     │               │                     │
│  ┌───────────────┐  │               │  • OCR cache        │               │  • Claim events     │
│  │ tenant_001_db │  │               │  • Rate lookup      │               │  • Async processing │
│  ├───────────────┤  │               │  • Session store    │               │  • Retry queue      │
│  │ tenant_002_db │  │               │  • Provider metrics │               │  • Dead letter      │
│  ├───────────────┤  │               │                     │               │                     │
│  │ tenant_003_db │  │               └─────────────────────┘               └─────────────────────┘
│  └───────────────┘  │
└─────────────────────┘
```

### 3.3 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     CLAIM PROCESSING FLOW                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
    │  Submit  │────>│   Document   │────>│    Claims    │────>│   Benefit    │────>│  Output  │
    │  Claim   │     │  Processing  │     │  Validation  │     │  Processing  │     │  Result  │
    └──────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────┘
         │                  │                    │                    │                   │
         ▼                  ▼                    ▼                    ▼                   ▼
    ┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
    │ • Upload │     │ • OCR/ICR    │     │ • Policy     │     │ • Benefit    │     │ • Claim  │
    │   docs   │     │ • LLM parse  │     │   lookup     │     │   lookup     │     │   status │
    │ • Meta   │     │ • Translate  │     │ • Eligibility│     │ • Deduction  │     │ • Amount │
    │   data   │     │ • Validate   │     │ • FWA check  │     │ • Pat. share │     │ • Audit  │
    └──────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────┘
                            │                    │                    │
                            ▼                    ▼                    ▼
                     ┌─────────────────────────────────────────────────────┐
                     │              Provider Abstraction Layer             │
                     │                                                     │
                     │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐│
                     │  │   OCR   │  │   LLM   │  │  Rules  │  │Med. NLP ││
                     │  │ Gateway │  │ Gateway │  │ Gateway │  │ Gateway ││
                     │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘│
                     │       │            │            │            │     │
                     │  ┌────▼────────────▼────────────▼────────────▼────┐│
                     │  │         Fallback Controller                    ││
                     │  │  • Confidence threshold check                  ││
                     │  │  • Error-based fallback                        ││
                     │  │  • Provider health monitoring                  ││
                     │  └────────────────────────────────────────────────┘│
                     └─────────────────────────────────────────────────────┘
```

### 3.4 Sequence Diagram - Claim Submission

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Client  │     │  API    │     │ Claims  │     │Document │     │ OCR     │     │  LLM    │
│         │     │ Gateway │     │ Service │     │ Service │     │ Gateway │     │ Gateway │
└────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘
     │               │               │               │               │               │
     │ POST /claims  │               │               │               │               │
     │──────────────>│               │               │               │               │
     │               │ authenticate  │               │               │               │
     │               │──────────────>│               │               │               │
     │               │               │               │               │               │
     │               │ submit_claim()│               │               │               │
     │               │──────────────>│               │               │               │
     │               │               │               │               │               │
     │               │               │ process_documents()           │               │
     │               │               │──────────────>│               │               │
     │               │               │               │               │               │
     │               │               │               │ extract_text()│               │
     │               │               │               │──────────────>│               │
     │               │               │               │               │               │
     │               │               │               │               │───┐ PaddleOCR │
     │               │               │               │               │   │ (primary) │
     │               │               │               │               │<──┘           │
     │               │               │               │               │               │
     │               │               │               │  [if confidence < threshold]  │
     │               │               │               │               │───┐ Azure OCR │
     │               │               │               │               │   │ (fallback)│
     │               │               │               │               │<──┘           │
     │               │               │               │               │               │
     │               │               │               │ OCRResult     │               │
     │               │               │               │<──────────────│               │
     │               │               │               │               │               │
     │               │               │               │ parse_claim() │               │
     │               │               │               │──────────────────────────────>│
     │               │               │               │               │               │
     │               │               │               │               │      ┌───┐ Qwen2.5-VL
     │               │               │               │               │      │   │ (primary)
     │               │               │               │               │      └───┘
     │               │               │               │               │               │
     │               │               │               │ ParsedClaim   │               │
     │               │               │               │<──────────────────────────────│
     │               │               │               │               │               │
     │               │               │ ClaimData     │               │               │
     │               │               │<──────────────│               │               │
     │               │               │               │               │               │
     │               │               │───────────────────────────────────────────────┐
     │               │               │  [Parallel: validate, apply rules, FWA check] │
     │               │               │<──────────────────────────────────────────────┘
     │               │               │               │               │               │
     │               │ ClaimResult   │               │               │               │
     │               │<──────────────│               │               │               │
     │               │               │               │               │               │
     │  202 Accepted │               │               │               │               │
     │<──────────────│               │               │               │               │
     │ (claim_id,    │               │               │               │               │
     │  status: proc)│               │               │               │               │
     │               │               │               │               │               │
```

### 3.5 Multi-Tenancy Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MULTI-TENANT ARCHITECTURE                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────────────────────┐
                              │         API Gateway             │
                              │  • Extract tenant from JWT      │
                              │  • Route to tenant context      │
                              └─────────────────────────────────┘
                                             │
                                             ▼
                              ┌─────────────────────────────────┐
                              │      Tenant Context Manager     │
                              │  • Resolve tenant database      │
                              │  • Load tenant configuration    │
                              │  • Apply tenant-specific rules  │
                              └─────────────────────────────────┘
                                             │
         ┌───────────────────────────────────┼───────────────────────────────────┐
         │                                   │                                   │
         ▼                                   ▼                                   ▼
┌─────────────────────┐         ┌─────────────────────┐         ┌─────────────────────┐
│     Tenant A        │         │     Tenant B        │         │     Tenant C        │
├─────────────────────┤         ├─────────────────────┤         ├─────────────────────┤
│ ┌─────────────────┐ │         │ ┌─────────────────┐ │         │ ┌─────────────────┐ │
│ │  PostgreSQL DB  │ │         │ │  PostgreSQL DB  │ │         │ │  PostgreSQL DB  │ │
│ │  tenant_a_db    │ │         │ │  tenant_b_db    │ │         │ │  tenant_c_db    │ │
│ └─────────────────┘ │         │ └─────────────────┘ │         │ └─────────────────┘ │
│ ┌─────────────────┐ │         │ ┌─────────────────┐ │         │ ┌─────────────────┐ │
│ │  Configuration  │ │         │ │  Configuration  │ │         │ │  Configuration  │ │
│ │ • US coding     │ │         │ │ • AU coding     │ │         │ │ • US coding     │
│ │ • USD currency  │ │         │ │ • AUD currency  │ │         │ │ • Multi-currency│
│ │ • English only  │ │         │ │ • English only  │ │         │ │ • Arabic+English│
│ └─────────────────┘ │         │ └─────────────────┘ │         │ └─────────────────┘ │
│ ┌─────────────────┐ │         │ ┌─────────────────┐ │         │ ┌─────────────────┐ │
│ │  Rules Engine   │ │         │ │  Rules Engine   │ │         │ │  Rules Engine   │ │
│ │  tenant_a.json  │ │         │ │  tenant_b.json  │ │         │ │  tenant_c.json  │ │
│ └─────────────────┘ │         │ └─────────────────┘ │         │ └─────────────────┘ │
│ ┌─────────────────┐ │         │ ┌─────────────────┐ │         │ ┌─────────────────┐ │
│ │ Provider Prefs  │ │         │ │ Provider Prefs  │ │         │ │ Provider Prefs  │ │
│ │ • LLM: GPT-4    │ │         │ │ • LLM: Qwen     │ │         │ │ • LLM: Qwen     │ │
│ │   (Premium)     │ │         │ │   (Cost-opt)    │ │         │ │   + GPT fallback│
│ └─────────────────┘ │         │ └─────────────────┘ │         │ └─────────────────┘ │
└─────────────────────┘         └─────────────────────┘         └─────────────────────┘
```

### 3.6 State Management - Claim Lifecycle

```
                                    ┌─────────────┐
                                    │   DRAFT     │
                                    │ (incomplete)│
                                    └──────┬──────┘
                                           │ submit
                                           ▼
                                    ┌─────────────┐
                                    │  SUBMITTED  │
                                    │  (pending)  │
                                    └──────┬──────┘
                                           │ process
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
             ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
             │  VALIDATING │       │  OCR_FAILED │       │DOC_PROCESSING│
             │  (eligibility)      │  (needs manual)     │  (OCR/LLM)  │
             └──────┬──────┘       └─────────────┘       └──────┬──────┘
                    │                                          │
                    │ valid                                    │ success
                    ▼                                          ▼
             ┌─────────────┐                           ┌─────────────┐
             │ADJUDICATING │<──────────────────────────│  VALIDATED  │
             │(rules engine)                           │(data extracted)
             └──────┬──────┘                           └─────────────┘
                    │
         ┌─────────┼─────────┐
         │         │         │
         ▼         ▼         ▼
  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
  │  APPROVED   │ │   DENIED    │ │NEEDS_REVIEW │
  │(auto-adjud.)│ │ (violation) │ │(FWA flagged)│
  └──────┬──────┘ └─────────────┘ └──────┬──────┘
         │                               │
         │ finalize                      │ manual_review
         ▼                               ▼
  ┌─────────────┐                 ┌─────────────┐
  │   PAYMENT   │                 │  ESCALATED  │
  │  PROCESSING │                 │(under review)
  └──────┬──────┘                 └──────┬──────┘
         │                               │
         │ paid                          │ decision
         ▼                               ▼
  ┌─────────────┐                 ┌─────────────┐
  │    PAID     │                 │FINAL_DECISION│
  │ (completed) │                 │(approved/denied)
  └─────────────┘                 └─────────────┘
```

---

## 4. API Contracts

### 4.1 Claims API

#### 4.1.1 Submit Claim

```
POST /api/v1/claims
Authorization: Bearer <JWT>
Content-Type: multipart/form-data
X-Tenant-ID: tenant_001

Request:
{
  "claim_type": "professional" | "institutional" | "dental" | "pharmacy",
  "patient": {
    "member_id": "string (required)",
    "first_name": "string",
    "last_name": "string",
    "date_of_birth": "YYYY-MM-DD",
    "relationship": "self" | "spouse" | "child" | "other"
  },
  "provider": {
    "npi": "string (10 digits, required)",
    "name": "string",
    "tax_id": "string"
  },
  "service_dates": {
    "from": "YYYY-MM-DD (required)",
    "to": "YYYY-MM-DD (required)"
  },
  "documents": [
    {
      "type": "claim_form" | "invoice" | "prescription" | "lab_result",
      "file": "<binary>",
      "filename": "string"
    }
  ],
  "line_items": [
    {
      "procedure_code": "string (CPT/HCPCS/ACHI)",
      "diagnosis_codes": ["string (ICD-10)"],
      "quantity": "integer",
      "charge_amount": "decimal",
      "currency": "USD" | "AED" | "AUD"
    }
  ],
  "metadata": {
    "source": "portal" | "api" | "edi",
    "priority": "normal" | "urgent"
  }
}

Response (202 Accepted):
{
  "claim_id": "uuid",
  "status": "submitted",
  "tracking_number": "CLM-2025-000001",
  "estimated_processing_time": "30 seconds",
  "links": {
    "self": "/api/v1/claims/{claim_id}",
    "status": "/api/v1/claims/{claim_id}/status",
    "documents": "/api/v1/claims/{claim_id}/documents"
  }
}

Error Responses:
400 Bad Request - Invalid input data
401 Unauthorized - Invalid/expired token
403 Forbidden - Tenant access denied
413 Payload Too Large - Document size exceeded
422 Unprocessable Entity - Validation failed
```

#### 4.1.2 Get Claim Status

```
GET /api/v1/claims/{claim_id}/status
Authorization: Bearer <JWT>

Response (200 OK):
{
  "claim_id": "uuid",
  "tracking_number": "CLM-2025-000001",
  "status": "adjudicating",
  "status_history": [
    {
      "status": "submitted",
      "timestamp": "2025-12-18T10:00:00Z",
      "actor": "system"
    },
    {
      "status": "doc_processing",
      "timestamp": "2025-12-18T10:00:05Z",
      "details": {
        "ocr_provider": "paddleocr",
        "confidence": 0.96
      }
    },
    {
      "status": "adjudicating",
      "timestamp": "2025-12-18T10:00:15Z",
      "details": {
        "rules_executed": ["benefit_lookup", "deduction_calc"]
      }
    }
  ],
  "processing_metrics": {
    "total_time_ms": 15230,
    "ocr_time_ms": 4520,
    "llm_time_ms": 8100,
    "rules_time_ms": 120
  }
}
```

#### 4.1.3 Get Claim Result

```
GET /api/v1/claims/{claim_id}
Authorization: Bearer <JWT>

Response (200 OK):
{
  "claim_id": "uuid",
  "tracking_number": "CLM-2025-000001",
  "status": "approved",
  "patient": { ... },
  "provider": { ... },
  "adjudication": {
    "decision": "approved",
    "decision_date": "2025-12-18T10:00:30Z",
    "adjudication_type": "auto",
    "line_items": [
      {
        "line_number": 1,
        "procedure_code": "99213",
        "charged_amount": 150.00,
        "allowed_amount": 125.00,
        "benefit_paid": 100.00,
        "patient_responsibility": 25.00,
        "adjustments": [
          {
            "code": "CO-45",
            "reason": "Charges exceed fee schedule",
            "amount": 25.00
          }
        ],
        "remarks": ["N/A"]
      }
    ],
    "totals": {
      "total_charged": 150.00,
      "total_allowed": 125.00,
      "total_paid": 100.00,
      "patient_responsibility": 25.00
    }
  },
  "medical_review": {
    "necessity_validated": true,
    "diagnosis_procedure_match": true,
    "coding_standard": "ICD-10-CM",
    "entities_extracted": [
      {
        "type": "DIAGNOSIS",
        "code": "J06.9",
        "description": "Acute upper respiratory infection",
        "confidence": 0.95
      }
    ]
  },
  "fraud_analysis": {
    "risk_score": 0.12,
    "flags": [],
    "model_version": "fwa_xgboost_v2.1"
  },
  "audit_trail": {
    "created_at": "2025-12-18T10:00:00Z",
    "updated_at": "2025-12-18T10:00:30Z",
    "providers_used": {
      "ocr": "paddleocr",
      "llm": "ollama/qwen2.5-vl:7b",
      "rules": "zen",
      "medical_nlp": "medcat"
    }
  }
}
```

### 4.2 Document Processing API

#### 4.2.1 Process Document

```
POST /api/v1/documents/process
Authorization: Bearer <JWT>
Content-Type: multipart/form-data

Request:
{
  "document": "<binary>",
  "document_type": "claim_form" | "invoice" | "prescription",
  "languages": ["en", "ar"],
  "options": {
    "extract_tables": true,
    "extract_handwriting": true,
    "force_provider": "paddleocr" | "azure" | null
  }
}

Response (200 OK):
{
  "document_id": "uuid",
  "processing_time_ms": 4520,
  "results": {
    "ocr": {
      "text": "Full extracted text...",
      "confidence": 0.96,
      "provider": "paddleocr",
      "fallback_used": false,
      "pages": [
        {
          "page_number": 1,
          "text": "...",
          "bounding_boxes": [...]
        }
      ]
    },
    "structured_data": {
      "patient_name": "John Doe",
      "member_id": "MBR123456",
      "service_date": "2025-12-15",
      "diagnosis_codes": ["J06.9"],
      "procedure_codes": ["99213"],
      "charges": [
        {
          "description": "Office visit",
          "code": "99213",
          "amount": 150.00
        }
      ]
    },
    "translation": {
      "original_language": "ar",
      "translated_text": "...",
      "provider": "libretranslate"
    },
    "handwriting": {
      "detected": true,
      "text": "Patient signature",
      "provider": "trocr"
    },
    "tampering_detection": {
      "suspicious_regions": [],
      "confidence": 0.98,
      "is_tampered": false
    }
  }
}
```

### 4.3 Gateway API (Internal)

#### 4.3.1 LLM Gateway

```python
# Internal service API - not exposed externally

class LLMGatewayAPI:
    async def complete(
        self,
        messages: List[ChatMessage],
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        structured_output: Optional[Type[BaseModel]] = None
    ) -> LLMResponse:
        """
        Send completion request with automatic fallback.

        Returns:
            LLMResponse:
                content: str
                provider: str
                model: str
                usage: TokenUsage
                fallback_used: bool
                latency_ms: int
        """
        pass

    async def complete_with_vision(
        self,
        prompt: str,
        images: List[bytes],
        provider: Optional[LLMProvider] = None
    ) -> LLMResponse:
        """Vision completion for document understanding."""
        pass

    async def extract_structured(
        self,
        text: str,
        schema: Type[BaseModel],
        provider: Optional[LLMProvider] = None
    ) -> StructuredOutput:
        """Extract structured data from text."""
        pass
```

#### 4.3.2 OCR Gateway

```python
class OCRGatewayAPI:
    async def extract_text(
        self,
        image: bytes,
        languages: List[str] = ["en"],
        provider: Optional[OCRProvider] = None
    ) -> OCRResult:
        """
        Extract text from image.

        Returns:
            OCRResult:
                text: str
                confidence: float
                bounding_boxes: List[BoundingBox]
                provider: str
                fallback_used: bool
        """
        pass

    async def extract_structured(
        self,
        image: bytes,
        document_type: str
    ) -> StructuredDocument:
        """Extract structured data (tables, key-value pairs)."""
        pass

    async def extract_handwriting(
        self,
        image: bytes,
        provider: Optional[ICRProvider] = None
    ) -> OCRResult:
        """Extract handwritten text."""
        pass
```

### 4.4 Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable error message",
    "details": [
      {
        "field": "patient.member_id",
        "code": "REQUIRED",
        "message": "Member ID is required"
      }
    ],
    "request_id": "uuid",
    "timestamp": "2025-12-18T10:00:00Z",
    "documentation_url": "https://docs.reimp.com/errors/VALIDATION_ERROR"
  }
}
```

### 4.5 Pagination Response Format

```json
{
  "data": [...],
  "pagination": {
    "total": 1250,
    "page": 1,
    "per_page": 50,
    "total_pages": 25,
    "has_next": true,
    "has_prev": false
  },
  "links": {
    "self": "/api/v1/claims?page=1&per_page=50",
    "next": "/api/v1/claims?page=2&per_page=50",
    "last": "/api/v1/claims?page=25&per_page=50"
  }
}
```

---

## 5. Technology Stack

### 5.1 Core Framework

| Component | Technology | Version | Justification |
|-----------|------------|---------|---------------|
| **Runtime** | Python | 3.11+ | Async support, type hints, ML ecosystem |
| **Web Framework** | FastAPI | 0.109+ | Async, OpenAPI, high performance |
| **ORM** | SQLAlchemy | 2.0+ | Async support, mature, well-documented |
| **Validation** | Pydantic | 2.5+ | FastAPI integration, settings management |
| **Task Queue** | Celery + Redis | 5.3+ | Reliable, distributed task processing |
| **HTTP Client** | httpx | 0.26+ | Async support, connection pooling |

### 5.2 AI/ML Providers (Configurable)

| Capability | Primary (Open-Source) | Fallback (Commercial) | Gateway |
|------------|----------------------|----------------------|---------|
| **Document LLM** | Qwen2.5-VL (Ollama) | GPT-4 Vision | LiteLLM |
| **Medical LLM** | BioMistral (Ollama) | GPT-4 Turbo | LiteLLM |
| **OCR** | PaddleOCR | Azure AI Doc Intelligence | Custom |
| **ICR (Handwriting)** | TrOCR | Azure AI | Custom |
| **Translation** | LibreTranslate | Azure Translator | Custom |
| **Medical NLP** | MedCAT + medspaCy | AWS Comprehend Medical | Custom |
| **Rules Engine** | GoRules ZEN | Custom Python | Custom |
| **Currency** | fawazahmed0 API | Fixer.io | Custom |

### 5.3 Data Stores

| Purpose | Technology | Justification |
|---------|------------|---------------|
| **Primary Database** | PostgreSQL 16 | ACID, multi-tenant schemas, JSONB |
| **Cache** | Redis 7 | Session, rate lookup, OCR cache |
| **Message Queue** | Redis Streams | Lightweight, already have Redis |
| **Search** | PostgreSQL FTS + pg_trgm | No additional infrastructure |
| **Time-Series (Audit)** | TimescaleDB | PostgreSQL extension, audit logs |

### 5.4 Infrastructure

| Component | Technology | Justification |
|-----------|------------|---------------|
| **Container Runtime** | Docker + Podman | Standard, rootless option |
| **Orchestration** | Kubernetes (EKS/GKE/AKS) | Scaling, self-healing |
| **API Gateway** | Kong / Traefik | Rate limiting, auth, routing |
| **Load Balancer** | NGINX / Cloud LB | SSL termination, health checks |
| **Monitoring** | Prometheus + Grafana | Industry standard, free |
| **Logging** | Loki + Promtail | Kubernetes-native, cost-effective |
| **Secrets** | HashiCorp Vault / AWS Secrets | Secure credential management |

### 5.5 Dependency Evaluation

#### 5.5.1 LiteLLM

| Criterion | Assessment |
|-----------|------------|
| **Latest Version** | v1.52+ (December 2025) |
| **Maintenance Status** | Active (daily commits) |
| **Security** | No known CVEs |
| **License** | MIT (permissive) |
| **Alternatives** | OpenRouter, LangChain - LiteLLM is lighter |
| **Integration Complexity** | Low - drop-in OpenAI replacement |
| **Learning Curve** | Minimal - same API as OpenAI |

#### 5.5.2 PaddleOCR

| Criterion | Assessment |
|-----------|------------|
| **Latest Version** | v2.8+ (2025) |
| **Maintenance Status** | Active (Baidu-maintained) |
| **Security** | No known CVEs |
| **License** | Apache 2.0 |
| **Alternatives** | Tesseract (lower accuracy), EasyOCR (slower) |
| **Integration Complexity** | Medium - requires GPU setup |
| **Learning Curve** | Low - simple Python API |

#### 5.5.3 GoRules ZEN

| Criterion | Assessment |
|-----------|------------|
| **Latest Version** | v0.26+ (2025) |
| **Maintenance Status** | Active |
| **Security** | No known CVEs |
| **License** | MIT |
| **Alternatives** | Drools (Java), PyKnow (Python but limited) |
| **Integration Complexity** | Low - Python bindings available |
| **Learning Curve** | Medium - JSON rule format |

#### 5.5.4 MedCAT

| Criterion | Assessment |
|-----------|------------|
| **Latest Version** | v1.12+ (2025) |
| **Maintenance Status** | Active (King's College London) |
| **Security** | No known CVEs |
| **License** | MIT |
| **Alternatives** | AWS Comprehend Medical (paid), scispaCy (less comprehensive) |
| **Integration Complexity** | Medium - requires UMLS setup |
| **Learning Curve** | Medium - UMLS knowledge helpful |

### 5.6 Development Environment

```yaml
# docker-compose.dev.yml
services:
  app:
    build: .
    volumes:
      - .:/app
    environment:
      - ENVIRONMENT=development
    depends_on:
      - postgres
      - redis
      - ollama

  postgres:
    image: timescale/timescaledb:latest-pg16

  redis:
    image: redis:7-alpine

  ollama:
    image: ollama/ollama:latest
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

  libretranslate:
    image: libretranslate/libretranslate:latest

  paddleocr:
    build: ./docker/paddleocr
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
```

---

## 6. Security Design

### 6.1 STRIDE Threat Model

| Threat | Category | Description | Mitigation |
|--------|----------|-------------|------------|
| **T1** | Spoofing | Attacker impersonates legitimate user | JWT authentication, MFA for admin |
| **T2** | Spoofing | API key theft | Key rotation, IP allowlisting |
| **T3** | Tampering | Claim data modification | Digital signatures, audit logging |
| **T4** | Tampering | Document tampering | Hash verification, tampering detection |
| **T5** | Repudiation | User denies actions | Comprehensive audit trail, timestamps |
| **T6** | Information Disclosure | PHI exposure | Encryption at rest/transit, access controls |
| **T7** | Information Disclosure | Cross-tenant data leak | Database-per-tenant, strict isolation |
| **T8** | Denial of Service | API flooding | Rate limiting, WAF, auto-scaling |
| **T9** | Denial of Service | Resource exhaustion | Request size limits, timeouts |
| **T10** | Elevation of Privilege | Admin access bypass | RBAC, principle of least privilege |

### 6.2 OWASP Top 10 Controls

| OWASP Risk | Control Measures |
|------------|------------------|
| **A01: Broken Access Control** | RBAC with tenant isolation, JWT validation, row-level security |
| **A02: Cryptographic Failures** | AES-256 encryption, TLS 1.3, secure key storage in Vault |
| **A03: Injection** | Parameterized queries (SQLAlchemy), input validation (Pydantic) |
| **A04: Insecure Design** | Threat modeling, security reviews, defense in depth |
| **A05: Security Misconfiguration** | Infrastructure as Code, security headers, minimal images |
| **A06: Vulnerable Components** | Dependency scanning (Snyk/Dependabot), SBOM tracking |
| **A07: Auth Failures** | Strong password policy, account lockout, MFA for sensitive ops |
| **A08: Data Integrity Failures** | CI/CD security, signed artifacts, SRI for frontend |
| **A09: Logging Failures** | Structured logging, log aggregation, alerting |
| **A10: SSRF** | URL validation, internal network isolation, egress filtering |

### 6.3 Authentication & Authorization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AUTHENTICATION FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────┐                ┌──────────┐                ┌──────────┐
    │  Client  │                │   Auth   │                │   IdP    │
    │  (SPA)   │                │ Service  │                │ (Keycloak)│
    └────┬─────┘                └────┬─────┘                └────┬─────┘
         │                           │                           │
         │  1. Login Request         │                           │
         │──────────────────────────>│                           │
         │                           │                           │
         │                           │  2. OIDC Auth Request     │
         │                           │──────────────────────────>│
         │                           │                           │
         │                           │  3. Auth Response (code)  │
         │                           │<──────────────────────────│
         │                           │                           │
         │                           │  4. Token Exchange        │
         │                           │──────────────────────────>│
         │                           │                           │
         │                           │  5. Access + Refresh Token│
         │                           │<──────────────────────────│
         │                           │                           │
         │  6. JWT Token             │                           │
         │<──────────────────────────│                           │
         │                           │                           │
         │  7. API Request + JWT     │                           │
         │──────────────────────────>│                           │
         │                           │                           │
         │                           │  8. Validate JWT          │
         │                           │──────────────────────────>│
         │                           │                           │

JWT Claims:
{
  "sub": "user_uuid",
  "tenant_id": "tenant_001",
  "roles": ["claims_processor", "viewer"],
  "permissions": ["claims:read", "claims:submit", "documents:upload"],
  "exp": 1734567890,
  "iat": 1734564290
}
```

### 6.4 Data Protection

#### 6.4.1 Encryption

| Data State | Method | Key Management |
|------------|--------|----------------|
| At Rest (Database) | AES-256-GCM | HashiCorp Vault |
| At Rest (Files) | AES-256-GCM | Vault + per-tenant keys |
| In Transit | TLS 1.3 | Managed certificates |
| In Memory | Secure memory handling | Clear after use |

#### 6.4.2 PHI Handling

```python
# PHI field detection and handling
PHI_FIELDS = [
    "patient.first_name",
    "patient.last_name",
    "patient.date_of_birth",
    "patient.ssn",
    "patient.member_id",
    "diagnosis_codes",
    "procedure_codes"
]

# Audit log PHI redaction
def redact_phi_for_logs(data: dict) -> dict:
    redacted = data.copy()
    for field in PHI_FIELDS:
        if field in redacted:
            redacted[field] = "[REDACTED]"
    return redacted
```

### 6.5 Audit Trail

```sql
-- Audit log table (TimescaleDB hypertable)
CREATE TABLE audit_logs (
    id BIGSERIAL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tenant_id UUID NOT NULL,
    user_id UUID,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    changes JSONB,
    ip_address INET,
    user_agent TEXT,
    request_id UUID,
    PRIMARY KEY (timestamp, id)
);

SELECT create_hypertable('audit_logs', 'timestamp');

-- Retention policy (7 years for HIPAA)
SELECT add_retention_policy('audit_logs', INTERVAL '7 years');
```

---

## 7. Performance Plan

### 7.1 Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Claim Submission** | < 100ms response | API response time |
| **Document OCR** | < 5s per page | Processing time |
| **LLM Parsing** | < 10s per document | Processing time |
| **Claim Adjudication** | < 500ms | Rules engine time |
| **End-to-End Processing** | < 30s | Total claim time |
| **API Throughput** | 1000 req/s | Load test |
| **Concurrent Users** | 5000+ | Connection pool |

### 7.2 Optimization Strategies

#### 7.2.1 Caching Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CACHING LAYERS                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Application   │     │   Redis Cache   │     │   Database      │
│     Cache       │────>│   (Distributed) │────>│   (PostgreSQL)  │
│  (In-Memory)    │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘

Cache TTLs:
- Policy data: 5 minutes (frequently accessed, rarely changes)
- Benefit tables: 10 minutes
- Exchange rates: 1 hour
- OCR results: 24 hours (document hash key)
- Provider health: 30 seconds

Cache Invalidation:
- Policy update -> Invalidate policy cache for tenant
- Configuration change -> Clear tenant config cache
- New exchange rates -> Clear currency cache
```

#### 7.2.2 Async Processing Pipeline

```python
# Async claim processing with parallel operations
async def process_claim_optimized(claim: ClaimSubmission) -> ClaimResult:
    # Stage 1: Parallel document processing
    document_tasks = [
        process_document(doc) for doc in claim.documents
    ]
    documents = await asyncio.gather(*document_tasks)

    # Stage 2: Parallel validation
    validation_tasks = [
        validate_eligibility(claim),
        validate_provider(claim),
        check_duplicate(claim)
    ]
    validations = await asyncio.gather(*validation_tasks)

    # Stage 3: Sequential adjudication (depends on above)
    adjudication = await adjudicate_claim(claim, documents, validations)

    # Stage 4: Parallel post-processing
    post_tasks = [
        run_fwa_analysis(claim, adjudication),
        generate_eob(claim, adjudication),
        update_audit_log(claim, adjudication)
    ]
    await asyncio.gather(*post_tasks)

    return adjudication
```

#### 7.2.3 Database Optimization

```sql
-- Indexes for common queries
CREATE INDEX CONCURRENTLY idx_claims_tenant_status
    ON claims(tenant_id, status)
    WHERE status IN ('submitted', 'processing');

CREATE INDEX CONCURRENTLY idx_claims_member_date
    ON claims(member_id, service_date_from);

CREATE INDEX CONCURRENTLY idx_claims_provider_date
    ON claims(provider_npi, created_at);

-- Partitioning by tenant for large tables
CREATE TABLE claims (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    ...
) PARTITION BY LIST (tenant_id);

-- Connection pooling
# SQLAlchemy async with pgbouncer
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)
```

### 7.3 Scalability Plan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HORIZONTAL SCALING                                   │
└─────────────────────────────────────────────────────────────────────────────┘

                         ┌─────────────────────┐
                         │   Load Balancer     │
                         │   (Kong/Traefik)    │
                         └──────────┬──────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   API Pod 1     │      │   API Pod 2     │      │   API Pod N     │
│   (Stateless)   │      │   (Stateless)   │      │   (Stateless)   │
└─────────────────┘      └─────────────────┘      └─────────────────┘
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Worker Pod 1   │      │  Worker Pod 2   │      │  Worker Pod N   │
│  (OCR/LLM)      │      │  (OCR/LLM)      │      │  (OCR/LLM)      │
│  GPU: 1x A100   │      │  GPU: 1x A100   │      │  GPU: 1x A100   │
└─────────────────┘      └─────────────────┘      └─────────────────┘

Kubernetes HPA Rules:
- API pods: Scale on CPU > 70%, min 3, max 20
- Worker pods: Scale on queue depth, min 2, max 10
- Ollama pods: Scale on GPU utilization > 80%
```

### 7.4 Performance Monitoring

```yaml
# Prometheus metrics
metrics:
  - name: claim_processing_duration_seconds
    type: histogram
    labels: [status, provider, tenant]
    buckets: [0.1, 0.5, 1, 5, 10, 30, 60]

  - name: ocr_processing_duration_seconds
    type: histogram
    labels: [provider, fallback_used]
    buckets: [0.5, 1, 2, 5, 10]

  - name: llm_request_duration_seconds
    type: histogram
    labels: [provider, model, operation]
    buckets: [1, 5, 10, 30, 60]

  - name: provider_fallback_total
    type: counter
    labels: [gateway, primary_provider, fallback_provider, reason]

  - name: active_claims_processing
    type: gauge
    labels: [tenant, status]
```

---

## 8. Risk Register

### 8.1 Technical Risks

| ID | Risk | Probability | Impact | Mitigation | Contingency |
|----|------|-------------|--------|------------|-------------|
| R1 | Open-source LLM accuracy below expectations | Medium | High | A/B testing during PoC, confidence thresholds | Increase commercial fallback usage |
| R2 | GPU infrastructure unavailable | Low | High | Early infrastructure planning | Cloud GPU (AWS/GCP) as backup |
| R3 | PaddleOCR Arabic accuracy issues | Medium | Medium | Extensive testing with Arabic documents | Azure fallback for Arabic |
| R4 | UMLS license delay for MedCAT | Medium | Medium | Early license application | Use medspaCy without UMLS |
| R5 | Provider rate limiting | Low | Medium | Multiple provider accounts | Circuit breaker, queue backpressure |
| R6 | Model version incompatibility | Low | Medium | Pin versions, test upgrades | Rollback procedure documented |
| R7 | Memory exhaustion on large documents | Medium | Medium | Streaming processing, chunking | Reject oversized documents |

### 8.2 Security Risks

| ID | Risk | Probability | Impact | Mitigation | Contingency |
|----|------|-------------|--------|------------|-------------|
| S1 | PHI data breach | Low | Critical | Encryption, access controls, audit | Incident response plan, legal |
| S2 | Cross-tenant data leakage | Low | Critical | Database-per-tenant, testing | Immediate isolation, investigation |
| S3 | API credential exposure | Low | High | Vault, rotation, monitoring | Immediate rotation, forensics |
| S4 | Supply chain attack (dependencies) | Low | High | SBOM, vulnerability scanning | Patching procedure, isolation |

### 8.3 Operational Risks

| ID | Risk | Probability | Impact | Mitigation | Contingency |
|----|------|-------------|--------|------------|-------------|
| O1 | Self-hosted service unavailability | Medium | Medium | Health checks, auto-restart | Commercial fallback |
| O2 | Database performance degradation | Low | High | Monitoring, query optimization | Read replicas, scaling |
| O3 | Regulatory changes (coding standards) | Medium | Medium | Modular coding tables | Rapid update process |
| O4 | Key personnel dependency | Medium | Medium | Documentation, cross-training | External consulting |

### 8.4 Risk Mitigation Timeline

| Phase | Focus | Key Mitigations |
|-------|-------|-----------------|
| Phase 1 | Infrastructure | GPU setup validation, Vault deployment |
| Phase 2 | Integration | Provider fallback testing, UMLS license |
| Phase 3 | Security | Penetration testing, access control verification |
| Phase 4 | Operations | Runbook creation, incident response drill |

---

## 9. Implementation Roadmap

### 9.1 Phase Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IMPLEMENTATION PHASES                                │
└─────────────────────────────────────────────────────────────────────────────┘

Phase 1: Foundation                Phase 2: Core Features
[Month 1-2]                        [Month 3-4]
┌───────────────────────┐          ┌───────────────────────┐
│ • Project setup       │          │ • Document processing │
│ • Provider abstraction│          │ • Claims submission   │
│ • Database schema     │          │ • Basic adjudication  │
│ • Auth integration    │          │ • Benefit calculation │
│ • CI/CD pipeline      │          │ • Patient share       │
└───────────────────────┘          └───────────────────────┘
           │                                  │
           ▼                                  ▼
Phase 3: Advanced Features         Phase 4: Production Ready
[Month 5-6]                        [Month 7-8]
┌───────────────────────┐          ┌───────────────────────┐
│ • Medical validation  │          │ • Performance tuning  │
│ • FWA detection       │          │ • Security hardening  │
│ • Multi-tenancy       │          │ • Monitoring/alerting │
│ • Arabic support      │          │ • Documentation       │
│ • Currency conversion │          │ • UAT & go-live       │
└───────────────────────┘          └───────────────────────┘
```

### 9.2 Phase 1: Foundation (Month 1-2)

| Milestone | Deliverables |
|-----------|--------------|
| **M1.1: Project Setup** | Repository, Docker dev environment, CI/CD skeleton |
| **M1.2: Provider Abstraction** | LLM Gateway (LiteLLM), OCR Gateway, base interfaces |
| **M1.3: Database Design** | PostgreSQL schemas, migrations, multi-tenant setup |
| **M1.4: Authentication** | Keycloak integration, JWT validation, RBAC |
| **M1.5: Infrastructure** | Kubernetes manifests, Helm charts, monitoring stack |

**Exit Criteria:**
- [ ] All gateways functional with at least one provider
- [ ] Database schema deployed and tested
- [ ] Authentication working end-to-end
- [ ] CI pipeline runs tests and builds images

### 9.3 Phase 2: Core Features (Month 3-4)

| Milestone | Deliverables |
|-----------|--------------|
| **M2.1: Document Processing** | OCR integration, LLM parsing, document validation |
| **M2.2: Claims API** | Submission, status, retrieval endpoints |
| **M2.3: Benefit Engine** | GoRules ZEN integration, benefit tables, deduction |
| **M2.4: Patient Share** | Threshold validation, calculation rules |
| **M2.5: Integration Testing** | End-to-end claim flow, provider fallback testing |

**Exit Criteria:**
- [ ] Complete claim submitted and processed
- [ ] Benefit calculation accurate to spec
- [ ] Fallback providers functioning
- [ ] 80%+ test coverage

### 9.4 Phase 3: Advanced Features (Month 5-6)

| Milestone | Deliverables |
|-----------|--------------|
| **M3.1: Medical Validation** | MedCAT integration, code validation, necessity check |
| **M3.2: FWA Detection** | XGBoost model, pattern analysis, flagging |
| **M3.3: Multi-Tenancy** | Tenant isolation, configuration, metering |
| **M3.4: Internationalization** | Arabic translation, RTL support, currency |
| **M3.5: Handwriting** | TrOCR integration, annotation extraction |

**Exit Criteria:**
- [ ] Medical validation operational
- [ ] FWA detection scoring claims
- [ ] Multiple tenants onboarded
- [ ] Arabic documents processed correctly

### 9.5 Phase 4: Production Ready (Month 7-8)

| Milestone | Deliverables |
|-----------|--------------|
| **M4.1: Performance** | Load testing, optimization, caching |
| **M4.2: Security** | Penetration testing, remediation, audit |
| **M4.3: Monitoring** | Dashboards, alerts, runbooks |
| **M4.4: Documentation** | API docs, operator guide, user manual |
| **M4.5: Go-Live** | UAT, staged rollout, production deployment |

**Exit Criteria:**
- [ ] Performance targets met under load
- [ ] No critical/high security findings
- [ ] Complete operational documentation
- [ ] Successful UAT signoff

### 9.6 MVP Scope

**Included in MVP (Phase 1-2):**
- Claims submission with document upload
- OCR extraction (PaddleOCR + Azure fallback)
- LLM document parsing (Qwen2.5-VL)
- Basic benefit calculation
- Patient share calculation
- Single tenant operation
- English language only
- US coding standards (ICD-10-CM, CPT)

**Deferred to Post-MVP:**
- Multi-tenant
- Arabic support
- Australian coding standards
- FWA detection
- Handwriting recognition
- Advanced medical validation

---

## 10. Open Questions

### 10.1 Requiring Business Decision

| ID | Question | Impact | Recommended Answer | Decision Owner |
|----|----------|--------|-------------------|----------------|
| Q1 | Should commercial providers be allowed by default or require explicit opt-in? | Cost vs accuracy | Opt-in for commercial (cost control) | Product Owner |
| Q2 | What is the acceptable FWA false positive rate? | User experience | < 5% false positive | Compliance |
| Q3 | Should handwriting annotations be mandatory extraction? | Scope | Should-have, not must-have | Product Owner |
| Q4 | Multi-tenant or dedicated deployment for enterprise clients? | Architecture | Multi-tenant with isolation options | Sales/Engineering |

### 10.2 Requiring Technical Investigation

| ID | Question | PoC Needed | Estimated Effort |
|----|----------|-----------|------------------|
| Q5 | PaddleOCR accuracy on Arabic handwritten forms? | Yes | 2 days |
| Q6 | Qwen2.5-VL performance on CMS-1500 forms vs GPT-4V? | Yes | 3 days |
| Q7 | GoRules ZEN latency at 1000+ rules per tenant? | Yes | 1 day |
| Q8 | MedCAT setup complexity without UMLS license? | Yes | 2 days |

### 10.3 Assumptions to Validate

| ID | Assumption | Validation Method | Timeline |
|----|------------|-------------------|----------|
| A1 | GPU infrastructure available (NVIDIA A100/V100) | Infrastructure review | Week 1 |
| A2 | UMLS license obtainable | Apply and track | Week 1-4 |
| A3 | 90%+ claims are standard format (CMS-1500, UB-04) | Analyze historical data | Week 2 |
| A4 | LibreTranslate Arabic quality acceptable | Manual testing | Week 3 |
| A5 | Existing ERP has REST API for policy data | Integration review | Week 2 |

---

## 11. Demo & Admin Interface

### 11.1 Overview

To enable solution demonstration without requiring integration with live external systems, the application includes a **Demo Mode** with an administrative interface for manually uploading and managing reference data. This allows:

- **Sales Demos**: Showcase full claim processing without production dependencies
- **Development/Testing**: Work with realistic data without external system access
- **Training**: Onboard users with controlled sample data
- **PoC Validation**: Test specific scenarios before full integration

### 11.2 Demo Mode Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      DEMO MODE ARCHITECTURE                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────────────────────┐
                              │      Mode Switch (ENV)          │
                              │  INTEGRATION_MODE=demo|live     │
                              └─────────────────────────────────┘
                                             │
              ┌──────────────────────────────┼──────────────────────────────┐
              │                              │                              │
              ▼                              │                              ▼
┌─────────────────────────────┐              │              ┌─────────────────────────────┐
│        DEMO MODE            │              │              │        LIVE MODE            │
├─────────────────────────────┤              │              ├─────────────────────────────┤
│                             │              │              │                             │
│  ┌───────────────────────┐  │              │              │  ┌───────────────────────┐  │
│  │   Admin Portal (UI)   │  │              │              │  │   External Systems    │  │
│  │   - Policy Upload     │  │              │              │  │   - ERP Integration   │  │
│  │   - Provider Mgmt     │  │              │              │  │   - Provider API      │  │
│  │   - Member Mgmt       │  │              │              │  │   - Eligibility Svc   │  │
│  │   - Payment Sim       │  │              │              │  │   - Payment Gateway   │  │
│  └───────────────────────┘  │              │              │  └───────────────────────┘  │
│             │               │              │              │             │               │
│             ▼               │              │              │             ▼               │
│  ┌───────────────────────┐  │              │              │  ┌───────────────────────┐  │
│  │   Local Database      │  │              │              │  │   API Adapters        │  │
│  │   (PostgreSQL)        │  │              │              │  │   (REST/SOAP/HL7)     │  │
│  │   - policies          │  │              │              │  │                       │  │
│  │   - providers         │  │              │              │  └───────────────────────┘  │
│  │   - members           │  │              │              │                             │
│  │   - benefit_tables    │  │              │              │                             │
│  │   - fee_schedules     │  │              │              │                             │
│  └───────────────────────┘  │              │              │                             │
│                             │              │              │                             │
└─────────────────────────────┘              │              └─────────────────────────────┘
                                             │
                                             ▼
                              ┌─────────────────────────────────┐
                              │     Unified Service Interface   │
                              │  (Same API regardless of mode)  │
                              └─────────────────────────────────┘
```

### 11.3 Admin Portal UI

#### 11.3.1 Technology Choice

| Component | Technology | Justification |
|-----------|------------|---------------|
| **Admin UI** | Streamlit | Rapid development, Python-native, built-in file upload |
| **Alternative** | FastAPI + React | More customizable but higher effort |
| **Charts/Reports** | Plotly | Interactive, Streamlit integration |

#### 11.3.2 Admin Portal Pages

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     ADMIN PORTAL STRUCTURE                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  📊 ReImp Admin Portal                                                    [Tenant: Demo Corp]   │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                  │
│  ┌──────────────────┐                                                                           │
│  │ 📁 Navigation    │   ┌─────────────────────────────────────────────────────────────────────┐│
│  ├──────────────────┤   │                                                                     ││
│  │ 🏠 Dashboard     │   │   POLICY MANAGEMENT                                                 ││
│  │ 📋 Policies      │◄──│   ────────────────────────────────────────────────────────────────  ││
│  │ 🏥 Providers     │   │                                                                     ││
│  │ 👥 Members       │   │   ┌─────────────────────────────────────────────────────────────┐  ││
│  │ 💰 Fee Schedules │   │   │  📤 Upload Policy File                                      │  ││
│  │ 📊 Benefits      │   │   │  ┌─────────────────────────────────────────────────────┐    │  ││
│  │ 💳 Payments      │   │   │  │  Drag & drop CSV/Excel/JSON file here              │    │  ││
│  │ 📈 Analytics     │   │   │  │  or click to browse                                 │    │  ││
│  │ ⚙️ Settings      │   │   │  └─────────────────────────────────────────────────────┘    │  ││
│  └──────────────────┘   │   │  Supported: .csv, .xlsx, .json                              │  ││
│                         │   └─────────────────────────────────────────────────────────────┘  ││
│                         │                                                                     ││
│                         │   ┌─────────────────────────────────────────────────────────────┐  ││
│                         │   │  📝 Or Enter Manually                                       │  ││
│                         │   │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐   │  ││
│                         │   │  │ Policy Number  │ │ Effective Date │ │ Expiry Date    │   │  ││
│                         │   │  │ POL-2025-001   │ │ 2025-01-01     │ │ 2025-12-31     │   │  ││
│                         │   │  └────────────────┘ └────────────────┘ └────────────────┘   │  ││
│                         │   │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐   │  ││
│                         │   │  │ Benefit Class  │ │ Max Annual     │ │ Deductible     │   │  ││
│                         │   │  │ Gold ▼         │ │ $50,000        │ │ $500           │   │  ││
│                         │   │  └────────────────┘ └────────────────┘ └────────────────┘   │  ││
│                         │   │                                                             │  ││
│                         │   │  [➕ Add Policy]  [📥 Import Bulk]  [📤 Export Template]    │  ││
│                         │   └─────────────────────────────────────────────────────────────┘  ││
│                         │                                                                     ││
│                         │   ┌─────────────────────────────────────────────────────────────┐  ││
│                         │   │  📋 Existing Policies (152 total)                           │  ││
│                         │   │  ┌───────────┬──────────┬────────────┬─────────┬─────────┐  │  ││
│                         │   │  │ Policy #  │ Member   │ Class      │ Status  │ Actions │  │  ││
│                         │   │  ├───────────┼──────────┼────────────┼─────────┼─────────┤  │  ││
│                         │   │  │ POL-001   │ John Doe │ Gold       │ Active  │ ✏️ 🗑️   │  │  ││
│                         │   │  │ POL-002   │ Jane Smi │ Silver     │ Active  │ ✏️ 🗑️   │  │  ││
│                         │   │  │ POL-003   │ Bob Wils │ Bronze     │ Expired │ ✏️ 🗑️   │  │  ││
│                         │   │  └───────────┴──────────┴────────────┴─────────┴─────────┘  │  ││
│                         │   └─────────────────────────────────────────────────────────────┘  ││
│                         └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 11.4 Data Models for External Systems

#### 11.4.1 Policy/ERP Data Model

```python
# models/demo/policy.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from decimal import Decimal
from enum import Enum

class BenefitClass(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    VIP = "vip"

class PolicyStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class CoverageType(str, Enum):
    INPATIENT = "inpatient"
    OUTPATIENT = "outpatient"
    DENTAL = "dental"
    OPTICAL = "optical"
    MATERNITY = "maternity"
    PHARMACY = "pharmacy"

class CoverageLimit(BaseModel):
    """Coverage limits per category."""
    coverage_type: CoverageType
    annual_limit: Decimal
    per_visit_limit: Optional[Decimal] = None
    copay_percentage: Decimal = Decimal("0.20")  # 20% copay
    copay_fixed: Optional[Decimal] = None
    waiting_period_days: int = 0
    pre_authorization_required: bool = False

class Policy(BaseModel):
    """Policy/ERP data for demo mode."""
    policy_id: str = Field(..., description="Unique policy identifier")
    policy_number: str = Field(..., description="Human-readable policy number")
    member_id: str = Field(..., description="Primary member ID")

    # Policy details
    benefit_class: BenefitClass
    status: PolicyStatus = PolicyStatus.ACTIVE
    effective_date: date
    expiry_date: date

    # Coverage configuration
    annual_limit: Decimal = Field(..., description="Total annual coverage limit")
    deductible: Decimal = Field(default=Decimal("0"), description="Annual deductible")
    out_of_pocket_max: Decimal = Field(..., description="Maximum out-of-pocket expense")

    # Coverage breakdown
    coverages: List[CoverageLimit] = []

    # Network restrictions
    network_type: str = "ppo"  # ppo, hmo, epo
    in_network_coverage: Decimal = Decimal("0.80")  # 80% coverage
    out_of_network_coverage: Decimal = Decimal("0.60")  # 60% coverage

    # Exclusions and conditions
    pre_existing_waiting_months: int = 12
    excluded_conditions: List[str] = []
    excluded_procedures: List[str] = []

    # Usage tracking (for demo)
    ytd_claims_paid: Decimal = Decimal("0")
    ytd_deductible_met: Decimal = Decimal("0")

    class Config:
        json_encoders = {Decimal: str}

class PolicyUploadSchema(BaseModel):
    """Schema for bulk policy upload (CSV/Excel)."""
    policy_number: str
    member_id: str
    benefit_class: str
    effective_date: str  # YYYY-MM-DD
    expiry_date: str
    annual_limit: float
    deductible: float = 0
    out_of_pocket_max: float
    network_type: str = "ppo"
```

#### 11.4.2 Provider Network Data Model

```python
# models/demo/provider.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from decimal import Decimal
from enum import Enum

class ProviderType(str, Enum):
    PHYSICIAN = "physician"
    HOSPITAL = "hospital"
    CLINIC = "clinic"
    LABORATORY = "laboratory"
    PHARMACY = "pharmacy"
    IMAGING_CENTER = "imaging_center"
    SPECIALIST = "specialist"

class ProviderStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

class NetworkTier(str, Enum):
    PREFERRED = "preferred"
    IN_NETWORK = "in_network"
    OUT_OF_NETWORK = "out_of_network"

class Specialty(str, Enum):
    GENERAL_PRACTICE = "general_practice"
    INTERNAL_MEDICINE = "internal_medicine"
    CARDIOLOGY = "cardiology"
    ORTHOPEDICS = "orthopedics"
    PEDIATRICS = "pediatrics"
    OBSTETRICS = "obstetrics"
    DERMATOLOGY = "dermatology"
    RADIOLOGY = "radiology"
    PATHOLOGY = "pathology"
    EMERGENCY = "emergency"

class Provider(BaseModel):
    """Healthcare provider data for demo mode."""
    provider_id: str = Field(..., description="Internal provider ID")
    npi: str = Field(..., description="National Provider Identifier (10 digits)")
    tax_id: str = Field(..., description="Tax Identification Number")

    # Provider info
    name: str
    provider_type: ProviderType
    specialty: Optional[Specialty] = None

    # Contact
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    zip_code: str
    country: str = "US"
    phone: str
    email: Optional[str] = None

    # Network status
    network_tier: NetworkTier = NetworkTier.IN_NETWORK
    status: ProviderStatus = ProviderStatus.ACTIVE
    effective_date: date
    termination_date: Optional[date] = None

    # Credentials
    license_number: str
    license_state: str
    license_expiry: date
    board_certified: bool = False

    # Contract details (for fee schedule)
    contracted_rate_multiplier: Decimal = Decimal("1.0")  # % of Medicare
    accepts_assignment: bool = True

    class Config:
        json_encoders = {Decimal: str}

class ProviderUploadSchema(BaseModel):
    """Schema for bulk provider upload."""
    npi: str
    tax_id: str
    name: str
    provider_type: str
    specialty: Optional[str] = None
    address: str
    city: str
    state: str
    zip_code: str
    phone: str
    network_tier: str = "in_network"
    license_number: str
    license_state: str
```

#### 11.4.3 Member Eligibility Data Model

```python
# models/demo/member.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from enum import Enum

class MemberStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"
    COBRA = "cobra"

class Relationship(str, Enum):
    SELF = "self"
    SPOUSE = "spouse"
    CHILD = "child"
    DOMESTIC_PARTNER = "domestic_partner"
    DEPENDENT = "dependent"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class Member(BaseModel):
    """Member eligibility data for demo mode."""
    member_id: str = Field(..., description="Unique member identifier")
    subscriber_id: str = Field(..., description="Subscriber/Primary member ID")

    # Personal info
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    date_of_birth: date
    gender: Gender
    ssn_last_four: Optional[str] = None  # Last 4 digits only for demo

    # Relationship to subscriber
    relationship: Relationship = Relationship.SELF

    # Contact
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    zip_code: str
    country: str = "US"
    phone: Optional[str] = None
    email: Optional[str] = None

    # Eligibility
    status: MemberStatus = MemberStatus.ACTIVE
    effective_date: date
    termination_date: Optional[date] = None

    # Associated policy
    policy_id: str
    group_number: Optional[str] = None

    # Primary care physician (if HMO)
    pcp_provider_id: Optional[str] = None

    # Special flags
    requires_pre_auth: bool = False
    has_secondary_insurance: bool = False

class EligibilityCheck(BaseModel):
    """Result of eligibility verification."""
    member_id: str
    is_eligible: bool
    eligibility_date: date
    policy_status: str
    benefit_class: str
    coverage_active: bool
    messages: List[str] = []

    # Coverage summary
    remaining_deductible: float
    remaining_out_of_pocket: float
    remaining_annual_limit: float

class MemberUploadSchema(BaseModel):
    """Schema for bulk member upload."""
    member_id: str
    subscriber_id: str
    first_name: str
    last_name: str
    date_of_birth: str  # YYYY-MM-DD
    gender: str
    relationship: str = "self"
    address: str
    city: str
    state: str
    zip_code: str
    policy_id: str
    effective_date: str
```

#### 11.4.4 Fee Schedule Data Model

```python
# models/demo/fee_schedule.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from decimal import Decimal
from enum import Enum

class CodingSystem(str, Enum):
    CPT = "cpt"
    HCPCS = "hcpcs"
    ICD10_PCS = "icd10_pcs"
    ACHI = "achi"  # Australian
    CDT = "cdt"  # Dental

class FeeScheduleEntry(BaseModel):
    """Fee schedule entry for procedure pricing."""
    code: str = Field(..., description="Procedure code (CPT/HCPCS/ACHI)")
    coding_system: CodingSystem = CodingSystem.CPT
    description: str

    # Pricing
    allowed_amount: Decimal = Field(..., description="Maximum allowed amount")
    medicare_rate: Optional[Decimal] = None
    medicaid_rate: Optional[Decimal] = None

    # Modifiers
    modifier_adjustments: dict = {}  # e.g., {"26": 0.4, "TC": 0.6}

    # Geographic adjustments
    geographic_adjustment: Decimal = Decimal("1.0")

    # Effective dates
    effective_date: date
    termination_date: Optional[date] = None

    # Additional info
    requires_pre_auth: bool = False
    bundled_codes: List[str] = []  # Codes that cannot be billed together

class FeeSchedule(BaseModel):
    """Complete fee schedule for a tenant."""
    schedule_id: str
    schedule_name: str
    effective_date: date
    coding_standard: str  # "US" or "AU"
    base_currency: str = "USD"
    entries: List[FeeScheduleEntry] = []

class FeeScheduleUploadSchema(BaseModel):
    """Schema for bulk fee schedule upload."""
    code: str
    description: str
    allowed_amount: float
    coding_system: str = "cpt"
    requires_pre_auth: bool = False
```

#### 11.4.5 Payment Simulation Data Model

```python
# models/demo/payment.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"

class PaymentMethod(str, Enum):
    ACH = "ach"
    CHECK = "check"
    WIRE = "wire"
    VIRTUAL_CARD = "virtual_card"

class Payment(BaseModel):
    """Payment record for demo mode."""
    payment_id: str = Field(..., description="Unique payment identifier")
    claim_id: str = Field(..., description="Associated claim ID")

    # Payment details
    payee_type: str  # "provider" or "member"
    payee_id: str
    payee_name: str

    # Amount
    amount: Decimal
    currency: str = "USD"

    # Status
    status: PaymentStatus = PaymentStatus.PENDING
    payment_method: PaymentMethod = PaymentMethod.ACH

    # Timing
    created_at: datetime
    processed_at: Optional[datetime] = None

    # Bank details (simulated)
    bank_reference: Optional[str] = None
    check_number: Optional[str] = None

    # Remittance
    remittance_advice_id: Optional[str] = None

class PaymentSimulationConfig(BaseModel):
    """Configuration for payment simulation."""
    auto_process: bool = True
    processing_delay_seconds: int = 5
    failure_rate: float = 0.02  # 2% simulated failure rate
    generate_remittance: bool = True
```

### 11.5 Admin API Endpoints

#### 11.5.1 Policy Management API

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ADMIN API - POLICY MANAGEMENT                       │
└─────────────────────────────────────────────────────────────────────────────┘

POST /api/v1/admin/policies
Authorization: Bearer <JWT> (admin role required)
Content-Type: multipart/form-data

Request (file upload):
{
  "file": <CSV/Excel/JSON file>,
  "mode": "append" | "replace",
  "validate_only": false
}

Response (200 OK):
{
  "status": "success",
  "records_processed": 150,
  "records_created": 145,
  "records_updated": 5,
  "errors": [
    {
      "row": 12,
      "field": "effective_date",
      "error": "Invalid date format"
    }
  ],
  "warnings": []
}

---

POST /api/v1/admin/policies/single
Authorization: Bearer <JWT>
Content-Type: application/json

Request:
{
  "policy_number": "POL-2025-001",
  "member_id": "MBR-001",
  "benefit_class": "gold",
  "effective_date": "2025-01-01",
  "expiry_date": "2025-12-31",
  "annual_limit": 50000,
  "deductible": 500,
  "out_of_pocket_max": 5000,
  "coverages": [
    {
      "coverage_type": "inpatient",
      "annual_limit": 30000,
      "copay_percentage": 0.20
    },
    {
      "coverage_type": "outpatient",
      "annual_limit": 15000,
      "copay_percentage": 0.30
    }
  ]
}

Response (201 Created):
{
  "policy_id": "uuid",
  "policy_number": "POL-2025-001",
  "status": "active",
  "message": "Policy created successfully"
}

---

GET /api/v1/admin/policies
Authorization: Bearer <JWT>
Query: ?page=1&per_page=50&status=active&benefit_class=gold

Response (200 OK):
{
  "data": [...],
  "pagination": {...}
}

---

GET /api/v1/admin/policies/{policy_id}
PUT /api/v1/admin/policies/{policy_id}
DELETE /api/v1/admin/policies/{policy_id}

---

GET /api/v1/admin/policies/template
Response: CSV/Excel template file download
```

#### 11.5.2 Provider Management API

```
POST /api/v1/admin/providers
POST /api/v1/admin/providers/single
GET /api/v1/admin/providers
GET /api/v1/admin/providers/{provider_id}
PUT /api/v1/admin/providers/{provider_id}
DELETE /api/v1/admin/providers/{provider_id}
GET /api/v1/admin/providers/template

# Provider network verification
POST /api/v1/admin/providers/verify-npi
Request: { "npi": "1234567890" }
Response: { "valid": true, "name": "...", "specialty": "..." }
```

#### 11.5.3 Member Management API

```
POST /api/v1/admin/members
POST /api/v1/admin/members/single
GET /api/v1/admin/members
GET /api/v1/admin/members/{member_id}
PUT /api/v1/admin/members/{member_id}
DELETE /api/v1/admin/members/{member_id}
GET /api/v1/admin/members/template

# Eligibility check
POST /api/v1/admin/members/check-eligibility
Request:
{
  "member_id": "MBR-001",
  "service_date": "2025-12-18",
  "procedure_codes": ["99213"]
}
Response:
{
  "is_eligible": true,
  "policy_status": "active",
  "benefit_class": "gold",
  "coverage": {
    "deductible_remaining": 250.00,
    "annual_limit_remaining": 45000.00
  }
}
```

#### 11.5.4 Fee Schedule Management API

```
POST /api/v1/admin/fee-schedules
POST /api/v1/admin/fee-schedules/{schedule_id}/entries
GET /api/v1/admin/fee-schedules
GET /api/v1/admin/fee-schedules/{schedule_id}
PUT /api/v1/admin/fee-schedules/{schedule_id}
DELETE /api/v1/admin/fee-schedules/{schedule_id}

# Lookup fee
GET /api/v1/admin/fee-schedules/lookup?code=99213&coding_system=cpt
Response:
{
  "code": "99213",
  "description": "Office visit, established patient, 20-29 min",
  "allowed_amount": 125.00,
  "requires_pre_auth": false
}
```

#### 11.5.5 Payment Simulation API

```
POST /api/v1/admin/payments/simulate
Request:
{
  "claim_id": "uuid",
  "simulate_failure": false
}
Response:
{
  "payment_id": "uuid",
  "status": "processing",
  "estimated_completion": "2025-12-18T10:05:00Z"
}

---

GET /api/v1/admin/payments
GET /api/v1/admin/payments/{payment_id}

---

POST /api/v1/admin/payments/{payment_id}/complete
POST /api/v1/admin/payments/{payment_id}/fail
POST /api/v1/admin/payments/{payment_id}/reverse
```

### 11.6 Streamlit Admin Portal Implementation

```python
# streamlit_app/pages/01_policies.py

import streamlit as st
import pandas as pd
import httpx
from datetime import date

st.set_page_config(page_title="Policy Management", page_icon="📋", layout="wide")

st.title("📋 Policy Management")

# Tabs for different operations
tab1, tab2, tab3 = st.tabs(["📤 Upload", "📝 Add Single", "📋 View All"])

with tab1:
    st.subheader("Bulk Policy Upload")

    uploaded_file = st.file_uploader(
        "Upload policy file (CSV, Excel, or JSON)",
        type=["csv", "xlsx", "json"],
        help="Download template below for correct format"
    )

    col1, col2 = st.columns(2)
    with col1:
        upload_mode = st.radio("Upload Mode", ["Append", "Replace All"])
    with col2:
        validate_only = st.checkbox("Validate Only (no save)")

    if uploaded_file:
        # Preview data
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.write(f"Preview ({len(df)} records):")
        st.dataframe(df.head(10))

        if st.button("🚀 Upload Policies"):
            with st.spinner("Processing..."):
                # API call to upload
                response = upload_policies(uploaded_file, upload_mode, validate_only)
                if response["status"] == "success":
                    st.success(f"✅ Uploaded {response['records_created']} policies")
                else:
                    st.error(f"❌ Upload failed: {response['errors']}")

    st.download_button(
        "📥 Download Template",
        data=get_policy_template(),
        file_name="policy_template.csv",
        mime="text/csv"
    )

with tab2:
    st.subheader("Add Single Policy")

    with st.form("add_policy_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            policy_number = st.text_input("Policy Number*", placeholder="POL-2025-001")
            member_id = st.text_input("Member ID*", placeholder="MBR-001")
            benefit_class = st.selectbox("Benefit Class*",
                ["bronze", "silver", "gold", "platinum", "vip"])

        with col2:
            effective_date = st.date_input("Effective Date*", value=date.today())
            expiry_date = st.date_input("Expiry Date*")
            network_type = st.selectbox("Network Type", ["ppo", "hmo", "epo"])

        with col3:
            annual_limit = st.number_input("Annual Limit ($)*", min_value=0, value=50000)
            deductible = st.number_input("Deductible ($)", min_value=0, value=500)
            oop_max = st.number_input("Out-of-Pocket Max ($)*", min_value=0, value=5000)

        st.subheader("Coverage Limits")

        coverages = []
        for coverage_type in ["Inpatient", "Outpatient", "Dental", "Pharmacy"]:
            col1, col2, col3 = st.columns(3)
            with col1:
                enabled = st.checkbox(coverage_type, value=coverage_type in ["Inpatient", "Outpatient"])
            with col2:
                limit = st.number_input(f"{coverage_type} Limit", min_value=0, value=10000,
                                       disabled=not enabled, key=f"{coverage_type}_limit")
            with col3:
                copay = st.slider(f"{coverage_type} Copay %", 0, 50, 20,
                                 disabled=not enabled, key=f"{coverage_type}_copay")

        submitted = st.form_submit_button("➕ Add Policy")
        if submitted:
            # Validate and submit
            result = create_policy({
                "policy_number": policy_number,
                "member_id": member_id,
                "benefit_class": benefit_class,
                # ... other fields
            })
            if result.get("policy_id"):
                st.success(f"✅ Policy {policy_number} created successfully!")
            else:
                st.error(f"❌ Failed to create policy: {result.get('error')}")

with tab3:
    st.subheader("All Policies")

    # Filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filter_status = st.multiselect("Status", ["active", "expired", "suspended"])
    with col2:
        filter_class = st.multiselect("Benefit Class", ["bronze", "silver", "gold", "platinum"])
    with col3:
        search = st.text_input("Search", placeholder="Policy # or Member ID")
    with col4:
        st.write("")  # Spacer
        if st.button("🔍 Search"):
            pass

    # Results table
    policies = fetch_policies(filter_status, filter_class, search)

    if policies:
        df = pd.DataFrame(policies)

        # Add action buttons
        selected = st.dataframe(
            df,
            column_config={
                "policy_id": None,  # Hide ID
                "policy_number": "Policy #",
                "member_id": "Member",
                "benefit_class": "Class",
                "status": st.column_config.SelectboxColumn("Status",
                    options=["active", "suspended", "expired"]),
                "annual_limit": st.column_config.NumberColumn("Annual Limit", format="$%d"),
            },
            use_container_width=True,
            hide_index=True
        )

        # Export
        st.download_button(
            "📥 Export to CSV",
            data=df.to_csv(index=False),
            file_name="policies_export.csv",
            mime="text/csv"
        )
    else:
        st.info("No policies found. Upload or add policies above.")
```

### 11.7 Sample Data Generation

```python
# scripts/generate_demo_data.py

"""
Generate realistic demo data for testing and demonstrations.
"""

import random
from faker import Faker
from datetime import date, timedelta
from decimal import Decimal

fake = Faker()

def generate_demo_policies(count: int = 100) -> list:
    """Generate sample policies."""
    policies = []
    benefit_classes = ["bronze", "silver", "gold", "platinum"]

    for i in range(count):
        effective = date.today() - timedelta(days=random.randint(0, 365))
        policies.append({
            "policy_number": f"POL-{date.today().year}-{str(i+1).zfill(5)}",
            "member_id": f"MBR-{str(i+1).zfill(6)}",
            "benefit_class": random.choice(benefit_classes),
            "effective_date": effective.isoformat(),
            "expiry_date": (effective + timedelta(days=365)).isoformat(),
            "annual_limit": random.choice([25000, 50000, 100000, 250000]),
            "deductible": random.choice([0, 250, 500, 1000]),
            "out_of_pocket_max": random.choice([2500, 5000, 7500, 10000]),
        })

    return policies

def generate_demo_providers(count: int = 50) -> list:
    """Generate sample healthcare providers."""
    providers = []
    specialties = ["general_practice", "cardiology", "orthopedics", "pediatrics"]

    for i in range(count):
        providers.append({
            "npi": f"{random.randint(1000000000, 9999999999)}",
            "tax_id": f"{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
            "name": f"Dr. {fake.last_name()}" if random.random() > 0.3 else fake.company() + " Medical Center",
            "provider_type": random.choice(["physician", "hospital", "clinic"]),
            "specialty": random.choice(specialties),
            "address": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip_code": fake.zipcode(),
            "phone": fake.phone_number(),
            "network_tier": random.choice(["preferred", "in_network"]),
        })

    return providers

def generate_demo_members(policies: list) -> list:
    """Generate members linked to policies."""
    members = []

    for policy in policies:
        # Primary member
        members.append({
            "member_id": policy["member_id"],
            "subscriber_id": policy["member_id"],
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "date_of_birth": fake.date_of_birth(minimum_age=25, maximum_age=65).isoformat(),
            "gender": random.choice(["male", "female"]),
            "relationship": "self",
            "address": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip_code": fake.zipcode(),
            "policy_id": policy["policy_number"],
            "effective_date": policy["effective_date"],
        })

        # Random dependents
        if random.random() > 0.5:
            # Spouse
            members.append({
                "member_id": f"{policy['member_id']}-S",
                "subscriber_id": policy["member_id"],
                "first_name": fake.first_name(),
                "last_name": members[-1]["last_name"],
                "date_of_birth": fake.date_of_birth(minimum_age=25, maximum_age=65).isoformat(),
                "gender": "female" if members[-1]["gender"] == "male" else "male",
                "relationship": "spouse",
                "address": members[-1]["address"],
                "city": members[-1]["city"],
                "state": members[-1]["state"],
                "zip_code": members[-1]["zip_code"],
                "policy_id": policy["policy_number"],
                "effective_date": policy["effective_date"],
            })

        if random.random() > 0.6:
            # Child
            for c in range(random.randint(1, 3)):
                members.append({
                    "member_id": f"{policy['member_id']}-C{c+1}",
                    "subscriber_id": policy["member_id"],
                    "first_name": fake.first_name(),
                    "last_name": members[-1]["last_name"],
                    "date_of_birth": fake.date_of_birth(minimum_age=1, maximum_age=24).isoformat(),
                    "gender": random.choice(["male", "female"]),
                    "relationship": "child",
                    "address": members[-1]["address"],
                    "city": members[-1]["city"],
                    "state": members[-1]["state"],
                    "zip_code": members[-1]["zip_code"],
                    "policy_id": policy["policy_number"],
                    "effective_date": policy["effective_date"],
                })

    return members

def generate_fee_schedule() -> list:
    """Generate common CPT codes with pricing."""
    fee_schedule = [
        {"code": "99213", "description": "Office visit, established patient, 20-29 min", "allowed_amount": 125.00},
        {"code": "99214", "description": "Office visit, established patient, 30-39 min", "allowed_amount": 175.00},
        {"code": "99215", "description": "Office visit, established patient, 40-54 min", "allowed_amount": 250.00},
        {"code": "99203", "description": "Office visit, new patient, 30-44 min", "allowed_amount": 165.00},
        {"code": "99204", "description": "Office visit, new patient, 45-59 min", "allowed_amount": 250.00},
        {"code": "99205", "description": "Office visit, new patient, 60-74 min", "allowed_amount": 325.00},
        {"code": "36415", "description": "Venipuncture", "allowed_amount": 15.00},
        {"code": "85025", "description": "Complete blood count (CBC)", "allowed_amount": 25.00},
        {"code": "80053", "description": "Comprehensive metabolic panel", "allowed_amount": 35.00},
        {"code": "71046", "description": "Chest X-ray, 2 views", "allowed_amount": 85.00},
        {"code": "93000", "description": "Electrocardiogram (ECG)", "allowed_amount": 50.00},
        {"code": "90471", "description": "Immunization administration", "allowed_amount": 25.00},
        {"code": "J3420", "description": "Vitamin B12 injection", "allowed_amount": 20.00},
        # Add more as needed
    ]
    return fee_schedule

if __name__ == "__main__":
    # Generate and save demo data
    policies = generate_demo_policies(100)
    providers = generate_demo_providers(50)
    members = generate_demo_members(policies)
    fees = generate_fee_schedule()

    # Save to JSON/CSV files
    import json
    with open("demo_data/policies.json", "w") as f:
        json.dump(policies, f, indent=2)
    # ... save other data
```

### 11.8 Demo Mode Configuration

```bash
# .env.demo

# === Demo Mode Configuration ===
INTEGRATION_MODE=demo

# Demo database (separate from production)
DEMO_DATABASE_URL=postgresql://demo:demo@localhost:5432/reimp_demo

# Disable external API calls in demo mode
DISABLE_EXTERNAL_APIS=true

# Auto-load sample data on startup
AUTO_LOAD_DEMO_DATA=true
DEMO_DATA_PATH=./demo_data

# Payment simulation
PAYMENT_SIMULATION_ENABLED=true
PAYMENT_SIMULATION_DELAY_MS=5000
PAYMENT_SIMULATION_FAILURE_RATE=0.02

# Admin portal
ADMIN_PORTAL_ENABLED=true
ADMIN_PORTAL_PORT=8501

# Demo user credentials
DEMO_ADMIN_USERNAME=admin@demo.reimp.com
DEMO_ADMIN_PASSWORD=demo123!
```

### 11.9 Service Adapter Pattern

```python
# services/adapters/policy_adapter.py

from abc import ABC, abstractmethod
from typing import Optional
from config.settings import settings

class PolicyServiceAdapter(ABC):
    """Abstract adapter for policy/ERP integration."""

    @abstractmethod
    async def get_policy(self, policy_id: str) -> Optional[Policy]:
        pass

    @abstractmethod
    async def validate_coverage(self, policy_id: str, procedure_code: str) -> CoverageResult:
        pass

class DemoPolicyAdapter(PolicyServiceAdapter):
    """Demo mode: reads from local database."""

    def __init__(self, db_session):
        self.db = db_session

    async def get_policy(self, policy_id: str) -> Optional[Policy]:
        return await self.db.query(DemoPolicy).filter_by(policy_id=policy_id).first()

    async def validate_coverage(self, policy_id: str, procedure_code: str) -> CoverageResult:
        policy = await self.get_policy(policy_id)
        if not policy:
            return CoverageResult(covered=False, reason="Policy not found")
        # ... validation logic
        return CoverageResult(covered=True, allowed_amount=125.00)

class LivePolicyAdapter(PolicyServiceAdapter):
    """Live mode: calls external ERP API."""

    def __init__(self, erp_client):
        self.erp = erp_client

    async def get_policy(self, policy_id: str) -> Optional[Policy]:
        response = await self.erp.get(f"/policies/{policy_id}")
        return Policy(**response.json()) if response.ok else None

# Factory function
def get_policy_adapter() -> PolicyServiceAdapter:
    if settings.INTEGRATION_MODE == "demo":
        return DemoPolicyAdapter(get_db_session())
    else:
        return LivePolicyAdapter(get_erp_client())
```

---

## Appendices

### Appendix A: Glossary

| Term | Definition |
|------|------------|
| **CPT** | Current Procedural Terminology - US procedure codes |
| **HCPCS** | Healthcare Common Procedure Coding System |
| **ICD-10-CM** | International Classification of Diseases, 10th revision, Clinical Modification (US) |
| **ICD-10-AM** | ICD-10 Australian Modification |
| **ACHI** | Australian Classification of Health Interventions |
| **FWA** | Fraud, Waste, and Abuse |
| **EOB** | Explanation of Benefits |
| **PHI** | Protected Health Information |
| **OCR** | Optical Character Recognition |
| **ICR** | Intelligent Character Recognition (handwriting) |
| **UMLS** | Unified Medical Language System |

### Appendix B: Related Documents

- [01_reimbursement_claims_solution_research.md](../research/01_reimbursement_claims_solution_research.md) - Commercial Stack Research
- [02_cost_effective_alternatives_research.md](../research/02_cost_effective_alternatives_research.md) - Open-Source Stack Research
- [03_configurable_hybrid_architecture_research.md](../research/03_configurable_hybrid_architecture_research.md) - Hybrid Architecture Research

### Appendix C: Validation Checklist

- [x] Business requirements clearly mapped to technical solution
- [x] All integration points identified and specified
- [x] Security requirements addressed (STRIDE, OWASP)
- [x] Performance requirements defined with targets
- [x] Risks identified with mitigation strategies
- [x] Implementation broken into manageable phases
- [ ] Assumptions validated (pending PoC)
- [x] Technology choices justified with evidence

---

**Document Status**: Draft - Pending Review
**Next Review Date**: TBD
**Approvers**: [Pending]
