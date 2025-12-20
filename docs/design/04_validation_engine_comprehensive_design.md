# High-Performance Claims Validation Engine - Comprehensive Design Document

**Design Date**: December 19, 2025
**Feature**: High-Performance Claims Validation Engine with 13 Rules, Configurable LLM Settings, Sub-50ms Search
**Author**: Claude Code (AI Assistant)
**Status**: ✅ APPROVED - Ready for Implementation
**Approved Date**: December 19, 2025
**Research Reference**: [05_comprehensive_validation_engine_research.md](../research/05_comprehensive_validation_engine_research.md)
**Previous Design**: [03_automated_validation_engine_design.md](03_automated_validation_engine_design.md)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Requirements Specification](#2-requirements-specification)
3. [Architecture Design](#3-architecture-design)
4. [API Contracts](#4-api-contracts)
5. [Technology Stack](#5-technology-stack)
6. [Security Design](#6-security-design)
7. [Performance Plan](#7-performance-plan)
8. [Risk Register](#8-risk-register)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [Open Questions](#10-open-questions)

---

## 1. Executive Summary

### 1.1 Overview

This document provides the comprehensive design for a **High-Performance Claims Validation Engine** that implements:

- **13 Validation Rules** for comprehensive medical claims processing
- **Sub-50ms Search Latency** using Typesense for medical code lookups
- **Configurable LLM Settings** with multi-tenant support and per-task configuration
- **Automation-First Workflow** minimizing user data entry

### 1.2 Key Decisions

| Decision Area | Choice | Rationale |
|--------------|--------|-----------|
| Search Engine | **Typesense** | Sub-50ms latency, typo-tolerance, GPL-3.0 license |
| Cache Layer | **Redis** (primary) | HIPAA-eligible, sub-ms response, proven in healthcare |
| Rules Engine | **GoRules ZEN** | Open-source, JSON-based, MIT license |
| PDF Forensics | **PyMuPDF** | Lower-level access, hash-based detection |
| LLM Gateway | **LiteLLM** | Provider abstraction, fallback support |

### 1.3 Design Philosophy

> "The system should capture information with **minimal effort** from the end user and process data automatically."

**Core Principles**:
1. **Automation-First**: Extract all data from documents; users only handle exceptions
2. **Speed-Critical**: Sub-50ms for searches, <2s for full validation
3. **Configurable**: Per-tenant LLM settings, customizable validation rules
4. **HIPAA-Compliant**: All data handling meets healthcare security standards

### 1.4 Scope

| In Scope | Out of Scope |
|----------|--------------|
| 13 validation rules implementation | Payment processing |
| High-speed search infrastructure | Claims adjudication logic |
| LLM settings configuration UI | External payer integrations |
| PDF forensics for fraud detection | Provider credentialing |
| Multi-tenant configuration | Member enrollment |

---

## 2. Requirements Specification

### 2.1 Business Objectives

| ID | Objective | Success Criteria |
|----|-----------|------------------|
| BO-1 | Reduce manual data entry | <3 manual fields vs current 15+ |
| BO-2 | Accelerate claim processing | <2 min submission vs current 10+ min |
| BO-3 | Improve validation accuracy | >95% automated validation coverage |
| BO-4 | Detect fraudulent documents | >85% detection rate for altered PDFs |
| BO-5 | Enable LLM customization | Per-tenant LLM provider/model configuration |

### 2.2 Functional Requirements

#### FR-1: Validation Rules

| Rule # | Name | Description | Priority |
|--------|------|-------------|----------|
| 1 | Insured Data Extraction | Extract member/policy info from documents | P0 |
| 2 | Code/Service Extraction | Extract ICD-10, CPT, medications | P0 |
| 3 | Fraud Detection | Detect computer-edited/forged documents | P0 |
| 4 | ICD-CPT Crosswalk | Validate procedures support diagnoses | P0 |
| 5 | Clinical Necessity | LLM-based medical necessity review | P1 |
| 6 | ICD×ICD Validation | Detect invalid diagnosis combinations | P0 |
| 7 | Diagnosis Demographics | Age/gender validation for diagnoses | P0 |
| 8 | Procedure Demographics | Age/gender validation for procedures | P0 |
| 9 | Medical Reports | Validate supporting documentation | P1 |
| 10 | Rejection Reasons | Explain and validate rejection codes | P1 |
| 11 | Policy/TOB Coverage | Validate against Table of Benefits | P0 |
| 12 | Network Coverage | Validate provider network status | P1 |

#### FR-2: Search Requirements

| Requirement | Specification |
|-------------|---------------|
| ICD-10 Search | <50ms for code lookup, typo-tolerant |
| CPT/HCPCS Search | <50ms for code lookup, typo-tolerant |
| NCCI Edit Lookup | <100ms for PTP and MUE checks |
| Provider Search | <50ms for NPI lookup |

#### FR-3: LLM Configuration

| Requirement | Specification |
|-------------|---------------|
| Provider Selection | OpenAI, Azure, Anthropic, Ollama, vLLM |
| Per-Task Config | Different models for extraction vs validation |
| Fallback Support | Automatic fallback on failure/low confidence |
| Rate Limiting | Configurable per-tenant limits |
| Cost Tracking | Token usage and cost metrics |

### 2.3 Non-Functional Requirements

| Category | Requirement | Target |
|----------|-------------|--------|
| Performance | Search latency | <50ms p95 |
| Performance | Validation latency | <2s for all 13 rules |
| Performance | Document processing | <15s per page |
| Scalability | Concurrent validations | 100+ simultaneous |
| Availability | Uptime | 99.9% |
| Security | HIPAA Compliance | Full compliance required |
| Security | Data encryption | AES-256 at rest, TLS 1.3 in transit |

### 2.4 Constraints

| Constraint | Description |
|------------|-------------|
| Technical | Must integrate with existing FastAPI backend |
| Technical | Must integrate with existing Angular 19 frontend |
| Technical | Must use PostgreSQL for persistent storage |
| Regulatory | HIPAA compliance required for PHI |
| Data | CMS data updates quarterly |
| License | Prefer MIT/Apache licenses for new dependencies |

### 2.5 Assumptions

| ID | Assumption | Status | Risk if Invalid |
|----|------------|--------|-----------------|
| A-1 | CMS data files available for download | Verified | High - No validation possible |
| A-2 | Typesense can handle 1M+ ICD codes | Verified | Low - Can shard |
| A-3 | Redis/Dragonfly HIPAA eligible | Verified | High - Must change cache |
| A-4 | PyMuPDF sufficient for forensics | Acceptable | Medium - May need ML models |
| A-5 | LLM latency acceptable for extraction | Must-validate | Medium - May need optimization |

---

## 3. Architecture Design

### 3.1 System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              CLAIMS VALIDATION ENGINE                              │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                            API GATEWAY (FastAPI)                            │  │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐   │  │
│  │  │ /api/v1/claims/  │ │ /api/v1/         │ │ /api/v1/settings/        │   │  │
│  │  │ validate         │ │ search/          │ │ llm                      │   │  │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                       │                                           │
│                                       ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                        VALIDATION ORCHESTRATOR                              │  │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐  │  │
│  │  │ Rule Router   │ │ Parallel      │ │ Result        │ │ Risk          │  │  │
│  │  │               │ │ Executor      │ │ Aggregator    │ │ Scorer        │  │  │
│  │  └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                       │                                           │
│         ┌─────────────────────────────┼─────────────────────────────┐            │
│         │                             │                             │            │
│         ▼                             ▼                             ▼            │
│  ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐    │
│  │ EXTRACTION      │         │ MEDICAL         │         │ COVERAGE        │    │
│  │ VALIDATORS      │         │ VALIDATORS      │         │ VALIDATORS      │    │
│  │ ┌─────────────┐ │         │ ┌─────────────┐ │         │ ┌─────────────┐ │    │
│  │ │ Rule 1      │ │         │ │ Rule 4      │ │         │ │ Rule 11     │ │    │
│  │ │ InsuredData │ │         │ │ ICD-CPT     │ │         │ │ Policy/TOB  │ │    │
│  │ ├─────────────┤ │         │ ├─────────────┤ │         │ ├─────────────┤ │    │
│  │ │ Rule 2      │ │         │ │ Rule 5      │ │         │ │ Rule 12     │ │    │
│  │ │ CodeExtract │ │         │ │ Necessity   │ │         │ │ Network     │ │    │
│  │ ├─────────────┤ │         │ ├─────────────┤ │         │ └─────────────┘ │    │
│  │ │ Rule 3      │ │         │ │ Rule 6-8    │ │         └─────────────────┘    │
│  │ │ Forensics   │ │         │ │ Demographic │ │                                 │
│  │ └─────────────┘ │         │ ├─────────────┤ │                                 │
│  └─────────────────┘         │ │ Rule 9      │ │                                 │
│                              │ │ Reports     │ │                                 │
│                              │ ├─────────────┤ │                                 │
│                              │ │ Rule 10     │ │                                 │
│                              │ │ Rejection   │ │                                 │
│                              │ └─────────────┘ │                                 │
│                              └─────────────────┘                                 │
│                                       │                                           │
│  ┌────────────────────────────────────┼────────────────────────────────────────┐ │
│  │                           SERVICE GATEWAYS                                   │ │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐   │ │
│  │  │ Search        │ │ Cache         │ │ LLM           │ │ Rules         │   │ │
│  │  │ Gateway       │ │ Gateway       │ │ Gateway       │ │ Gateway       │   │ │
│  │  │ (Typesense)   │ │ (Redis)       │ │ (LiteLLM)     │ │ (ZEN Engine)  │   │ │
│  │  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └───────┬───────┘   │ │
│  └──────────┼─────────────────┼─────────────────┼─────────────────┼───────────┘ │
│             │                 │                 │                 │             │
└─────────────┼─────────────────┼─────────────────┼─────────────────┼─────────────┘
              │                 │                 │                 │
              ▼                 ▼                 ▼                 ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   TYPESENSE     │  │     REDIS       │  │  LLM PROVIDERS  │  │   PostgreSQL    │
│   Collections:  │  │   Cache Keys:   │  │   - OpenAI      │  │   Tables:       │
│   - icd10_codes │  │   - validation  │  │   - Azure       │  │   - claims      │
│   - cpt_codes   │  │   - crosswalk   │  │   - Anthropic   │  │   - policies    │
│   - ncci_edits  │  │   - provider    │  │   - Ollama      │  │   - llm_config  │
│   - providers   │  │   - policy      │  │   - vLLM        │  │   - rules       │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
```

### 3.2 Component Interactions

```
Request Flow: Comprehensive Claim Validation
═══════════════════════════════════════════

User Upload Documents
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│ Angular Frontend│ ──── │ Document Upload │
└─────────────────┘      │ Component       │
         │               └─────────────────┘
         │ POST /api/v1/claims/validate-comprehensive
         ▼
┌─────────────────────────────────────────────────┐
│              FastAPI Backend                     │
│  ┌───────────────────────────────────────────┐  │
│  │           Validation Endpoint              │  │
│  └───────────────────────────────────────────┘  │
│         │                                        │
│         ▼                                        │
│  ┌───────────────────────────────────────────┐  │
│  │         Validation Orchestrator            │  │
│  │                                            │  │
│  │  Step 1: Document Processing               │  │
│  │    └─► OCR + Classification               │  │
│  │                                            │  │
│  │  Step 2: Data Extraction (Rules 1-2)      │  │
│  │    ├─► Insured Data → Member Lookup       │  │
│  │    └─► Codes/Services → Typesense         │  │
│  │                                            │  │
│  │  Step 3: Fraud Detection (Rule 3)         │  │
│  │    └─► PDF Forensics → Risk Score         │  │
│  │                                            │  │
│  │  Step 4: Parallel Medical Validation      │  │
│  │    ├─► Rule 4: ICD-CPT Crosswalk ─────────┼──┼─► Typesense
│  │    ├─► Rule 5: Clinical Necessity ────────┼──┼─► LLM Gateway
│  │    ├─► Rule 6: ICD×ICD ───────────────────┼──┼─► Rules Engine
│  │    ├─► Rule 7: Dx Demographics ───────────┼──┼─► Rules Engine
│  │    └─► Rule 8: Px Demographics ───────────┼──┼─► Rules Engine
│  │                                            │  │
│  │  Step 5: Documentation Check (Rule 9)     │  │
│  │    └─► Report Matching → LLM Gateway      │  │
│  │                                            │  │
│  │  Step 6: Coverage Validation (11-12)      │  │
│  │    ├─► Policy/TOB → Redis Cache           │  │
│  │    └─► Network → Provider DB              │  │
│  │                                            │  │
│  │  Step 7: Result Aggregation               │  │
│  │    └─► Risk Scoring + Response Build      │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│  ComprehensiveValidationResponse                │
│  {                                              │
│    extracted_data: { ... },                     │
│    validation_results: [ ... ],                 │
│    can_submit: true/false,                      │
│    risk_score: 0.0-1.0,                         │
│    errors: [ ... ],                             │
│    warnings: [ ... ]                            │
│  }                                              │
└─────────────────────────────────────────────────┘
```

### 3.3 Fraud Claim Workflow (Q1 Decision - Enhanced with Reasoning)

```
Fraud Detection Workflow: Accept → Record → Reject with Reasoning
═════════════════════════════════════════════════════════════════

User Uploads Documents
         │
         ▼
┌─────────────────────────────────┐
│   Document Processing           │
│   (OCR, Classification)         │
└─────────────────┬───────────────┘
                  │
                  ▼
┌─────────────────────────────────┐
│   Rule 3: Fraud Detection       │
│   (PDF Forensics Analysis)      │
│                                 │
│   Signals Detected:             │
│   - Metadata mismatch           │
│   - Suspicious producer         │
│   - Font inconsistencies        │
│   - Hash verification failed    │
└─────────────────┬───────────────┘
                  │
         ┌───────┴───────┐
         │               │
    NOT Fraud        FRAUD DETECTED
         │               │
         ▼               ▼
┌─────────────────┐   ┌─────────────────────────────────────┐
│ Continue with   │   │ Fraud Handling:                      │
│ normal          │   │                                      │
│ validation      │   │ 1. ACCEPT the claim submission       │
│ (Rules 4-12)    │   │    - User sees "Claim Received"      │
│                 │   │    - claim_id generated              │
│                 │   │                                      │
│                 │   │ 2. RECORD full audit trail           │
│                 │   │    - All documents stored            │
│                 │   │    - Forensic signals logged         │
│                 │   │    - Risk score recorded             │
│                 │   │    - User/session info captured      │
│                 │   │                                      │
│                 │   │ 3. SET STATUS = "Rejected - Fraud"   │
│                 │   │    - claim.status = 'rejected'       │
│                 │   │    - claim.rejection_reason = 'fraud'│
│                 │   │    - claim.fwa_risk_score = 0.85+    │
│                 │   │                                      │
│                 │   │ 4. GENERATE REJECTION REASONING      │
│                 │   │    - Human-readable explanation      │
│                 │   │    - Evidence references             │
│                 │   │    - Document locations              │
│                 │   │                                      │
│                 │   │ 5. ALERT fraud investigation team    │
│                 │   │    - WebSocket notification          │
│                 │   │    - Email to FWA team               │
└─────────────────┘   └─────────────────────────────────────┘
```

**Claim Status Flow for Fraud**:
```
submitted → processing → rejected (fraud)
                              │
                              └── Available for:
                                  - Audit review
                                  - Investigation
                                  - Appeal (if false positive)
```

### 3.3.1 Rejection Reasoning & Evidence Structure

When a claim is rejected (for fraud or any other validation failure), the system provides:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         REJECTION DISPLAY STRUCTURE                           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ CLAIM REJECTION SUMMARY                                                  │ │
│  │                                                                          │ │
│  │ Claim ID: CLM-2025-00123                                                │ │
│  │ Status: REJECTED                                                         │ │
│  │ Rejection Category: Document Integrity Failure (Fraud Detection)        │ │
│  │ Risk Score: 0.92 (Critical)                                             │ │
│  │ Date: December 19, 2025                                                  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ REJECTION REASONING (Human-Readable)                                     │ │
│  │                                                                          │ │
│  │ This claim has been rejected due to document integrity concerns:        │ │
│  │                                                                          │ │
│  │ 1. The submitted invoice (Invoice_123.pdf) shows signs of digital       │ │
│  │    modification after its original creation.                            │ │
│  │                                                                          │ │
│  │ 2. The document metadata indicates it was edited using PDF editing      │ │
│  │    software (Adobe Acrobat Pro) 3 days after the original creation.     │ │
│  │                                                                          │ │
│  │ 3. Font inconsistencies were detected in the billing amount section,    │ │
│  │    suggesting potential alteration of charged amounts.                  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ EVIDENCE REFERENCES                                                      │ │
│  │                                                                          │ │
│  │ ┌─────────────────────────────────────────────────────────────────────┐ │ │
│  │ │ Evidence #1: Metadata Mismatch                                      │ │ │
│  │ │ ─────────────────────────────────────────────────────────────────── │ │ │
│  │ │ Document: Invoice_123.pdf (Page 1)                                  │ │ │
│  │ │ Signal Type: metadata_mismatch                                      │ │ │
│  │ │ Severity: HIGH                                                       │ │ │
│  │ │ Confidence: 0.95                                                     │ │ │
│  │ │                                                                      │ │ │
│  │ │ Details:                                                             │ │ │
│  │ │   • Creation Date: 2025-12-10 09:15:00                              │ │ │
│  │ │   • Modification Date: 2025-12-13 14:30:22                          │ │ │
│  │ │   • Time Difference: 3 days, 5 hours                                │ │ │
│  │ │                                                                      │ │ │
│  │ │ Reference: PDF Metadata Analysis Report                             │ │ │
│  │ └─────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                          │ │
│  │ ┌─────────────────────────────────────────────────────────────────────┐ │ │
│  │ │ Evidence #2: Suspicious Producer Software                           │ │ │
│  │ │ ─────────────────────────────────────────────────────────────────── │ │ │
│  │ │ Document: Invoice_123.pdf                                           │ │ │
│  │ │ Signal Type: suspicious_producer                                    │ │ │
│  │ │ Severity: HIGH                                                       │ │ │
│  │ │ Confidence: 0.88                                                     │ │ │
│  │ │                                                                      │ │ │
│  │ │ Details:                                                             │ │ │
│  │ │   • Producer: Adobe Acrobat Pro DC (21.001.20155)                   │ │ │
│  │ │   • Original Creator: Hospital Billing System v3.2                  │ │ │
│  │ │   • Modification Tool Detected: Yes                                 │ │ │
│  │ │                                                                      │ │ │
│  │ │ Reference: Known PDF Editor Detection Database                      │ │ │
│  │ └─────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                          │ │
│  │ ┌─────────────────────────────────────────────────────────────────────┐ │ │
│  │ │ Evidence #3: Font Inconsistency                                     │ │ │
│  │ │ ─────────────────────────────────────────────────────────────────── │ │ │
│  │ │ Document: Invoice_123.pdf (Page 1, Section: Total Amount)           │ │ │
│  │ │ Signal Type: font_inconsistency                                     │ │ │
│  │ │ Severity: MEDIUM                                                     │ │ │
│  │ │ Confidence: 0.82                                                     │ │ │
│  │ │                                                                      │ │ │
│  │ │ Details:                                                             │ │ │
│  │ │   • Expected Font: Arial-Bold (consistent with document)            │ │ │
│  │ │   • Detected Font: Helvetica-Bold (in amount field only)            │ │ │
│  │ │   • Location: Line items total, coordinates (450, 680)              │ │ │
│  │ │                                                                      │ │ │
│  │ │ Reference: Document Font Analysis Report                            │ │ │
│  │ └─────────────────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ APPEAL INFORMATION                                                       │ │
│  │                                                                          │ │
│  │ If you believe this rejection is in error, you may:                     │ │
│  │                                                                          │ │
│  │ 1. Submit original unmodified documents                                 │ │
│  │ 2. Provide a letter of explanation from the provider                    │ │
│  │ 3. Request a manual review by contacting support@company.com            │ │
│  │                                                                          │ │
│  │ Appeal Deadline: 30 days from rejection date                            │ │
│  │ Reference Number: REJ-2025-12-00456                                     │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 3.3.2 Rejection Reasoning Data Model

```python
# src/schemas/rejection.py

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class RejectionCategory(str, Enum):
    FRAUD = "fraud"
    MEDICAL_NECESSITY = "medical_necessity"
    COVERAGE = "coverage"
    ELIGIBILITY = "eligibility"
    CODING = "coding"
    DOCUMENTATION = "documentation"
    DUPLICATE = "duplicate"
    TIMELY_FILING = "timely_filing"

class EvidenceSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class EvidenceReference(BaseModel):
    """Individual piece of evidence supporting rejection."""
    evidence_id: str
    signal_type: str                    # 'metadata_mismatch', 'font_inconsistency', etc.
    severity: EvidenceSeverity
    confidence: float                   # 0.0 - 1.0

    # Document reference
    document_name: str
    document_id: str
    page_number: Optional[int] = None
    location_description: Optional[str] = None  # "Section: Total Amount"
    coordinates: Optional[dict] = None  # {"x": 450, "y": 680}

    # Evidence details
    title: str                          # Human-readable title
    description: str                    # Detailed explanation
    details: dict                       # Specific data points

    # Reference source
    reference_source: str               # "PDF Metadata Analysis Report"
    reference_url: Optional[str] = None # Link to detailed report

class RejectionReasoning(BaseModel):
    """Complete rejection reasoning with evidence."""

    # Rejection summary
    claim_id: str
    rejection_id: str
    rejection_date: datetime
    category: RejectionCategory
    risk_score: float

    # Human-readable explanation
    summary: str                        # One-line summary
    reasoning: List[str]                # Numbered list of reasons

    # Evidence
    evidence_references: List[EvidenceReference]
    total_evidence_count: int

    # Rules that triggered rejection
    triggered_rules: List[dict]         # Which validation rules failed

    # Appeal information
    appeal_deadline: datetime
    appeal_reference: str
    appeal_instructions: List[str]

    # Audit trail
    reviewed_by: Optional[str] = None   # If manually reviewed
    review_notes: Optional[str] = None

class ClaimRejectionResponse(BaseModel):
    """API response for rejected claim."""
    claim_id: str
    status: str = "rejected"
    rejection_reasoning: RejectionReasoning

    # Original validation results (for context)
    validation_summary: dict

    # Next steps
    can_appeal: bool = True
    can_resubmit: bool = False          # Only if correctable
    resubmit_instructions: Optional[List[str]] = None
```

### 3.3.3 Frontend Rejection Display Component

```typescript
// frontend/apps/claims-portal/src/app/features/claims/components/rejection-details.component.ts

import { Component, Input, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PanelModule } from 'primeng/panel';
import { TagModule } from 'primeng/tag';
import { AccordionModule } from 'primeng/accordion';
import { ButtonModule } from 'primeng/button';
import { TimelineModule } from 'primeng/timeline';

interface EvidenceReference {
  evidence_id: string;
  signal_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  document_name: string;
  document_id: string;
  page_number?: number;
  location_description?: string;
  coordinates?: { x: number; y: number };
  title: string;
  description: string;
  details: Record<string, any>;
  reference_source: string;
  reference_url?: string;
}

interface RejectionReasoning {
  rejection_id: string;
  rejection_date: string;
  category: string;
  risk_score: number;
  summary: string;
  reasoning: string[];
  evidence_references: EvidenceReference[];
  total_evidence_count: number;
  triggered_rules: { rule_id: number; rule_name: string; status: string; message: string }[];
  appeal_deadline: string;
  appeal_reference: string;
  appeal_instructions: string[];
}

@Component({
  selector: 'app-rejection-details',
  standalone: true,
  imports: [
    CommonModule,
    PanelModule,
    TagModule,
    AccordionModule,
    ButtonModule,
    TimelineModule
  ],
  template: `
    <div class="rejection-details">
      <!-- Rejection Summary Header -->
      <p-panel styleClass="rejection-summary">
        <ng-template pTemplate="header">
          <div class="flex align-items-center gap-2">
            <i class="pi pi-exclamation-triangle text-red-500 text-xl"></i>
            <span class="font-bold text-lg">Claim Rejected</span>
            <p-tag [severity]="riskSeverity()" [value]="riskLabel()"></p-tag>
          </div>
        </ng-template>

        <div class="grid">
          <div class="col-12 md:col-6">
            <div class="field">
              <label class="font-semibold">Rejection ID</label>
              <div>{{ rejection()?.rejection_id }}</div>
            </div>
            <div class="field">
              <label class="font-semibold">Category</label>
              <div class="capitalize">{{ rejection()?.category | titlecase }}</div>
            </div>
          </div>
          <div class="col-12 md:col-6">
            <div class="field">
              <label class="font-semibold">Date</label>
              <div>{{ rejection()?.rejection_date | date:'medium' }}</div>
            </div>
            <div class="field">
              <label class="font-semibold">Risk Score</label>
              <div class="flex align-items-center gap-2">
                <div class="progress-bar" [style.width.%]="(rejection()?.risk_score || 0) * 100">
                  <div class="progress-fill" [class]="'risk-' + riskLevel()"></div>
                </div>
                <span>{{ (rejection()?.risk_score || 0) * 100 | number:'1.0-0' }}%</span>
              </div>
            </div>
          </div>
        </div>
      </p-panel>

      <!-- Reasoning Section -->
      <p-panel header="Rejection Reasoning" styleClass="mt-3">
        <div class="reasoning-content">
          <p class="text-lg mb-3">{{ rejection()?.summary }}</p>

          <ol class="reasoning-list">
            @for (reason of rejection()?.reasoning; track $index) {
              <li class="mb-2">{{ reason }}</li>
            }
          </ol>
        </div>
      </p-panel>

      <!-- Evidence Section -->
      <p-panel header="Evidence References" styleClass="mt-3" [toggleable]="true">
        <p-accordion [multiple]="true">
          @for (evidence of rejection()?.evidence_references; track evidence.evidence_id) {
            <p-accordionTab>
              <ng-template pTemplate="header">
                <div class="flex align-items-center gap-2 w-full">
                  <p-tag [severity]="getSeverityColor(evidence.severity)" [value]="evidence.severity | uppercase"></p-tag>
                  <span class="font-semibold">{{ evidence.title }}</span>
                  <span class="text-500 ml-auto">Confidence: {{ evidence.confidence * 100 | number:'1.0-0' }}%</span>
                </div>
              </ng-template>

              <div class="evidence-details">
                <div class="grid">
                  <div class="col-12 md:col-6">
                    <div class="field">
                      <label class="font-semibold text-500">Document</label>
                      <div class="flex align-items-center gap-2">
                        <i class="pi pi-file-pdf text-red-500"></i>
                        <span>{{ evidence.document_name }}</span>
                        @if (evidence.page_number) {
                          <span class="text-500">(Page {{ evidence.page_number }})</span>
                        }
                      </div>
                    </div>
                    <div class="field">
                      <label class="font-semibold text-500">Signal Type</label>
                      <div>{{ evidence.signal_type | titlecase }}</div>
                    </div>
                  </div>
                  <div class="col-12 md:col-6">
                    @if (evidence.location_description) {
                      <div class="field">
                        <label class="font-semibold text-500">Location</label>
                        <div>{{ evidence.location_description }}</div>
                      </div>
                    }
                    <div class="field">
                      <label class="font-semibold text-500">Reference</label>
                      <div>{{ evidence.reference_source }}</div>
                    </div>
                  </div>
                </div>

                <div class="field mt-3">
                  <label class="font-semibold text-500">Description</label>
                  <p>{{ evidence.description }}</p>
                </div>

                <div class="field">
                  <label class="font-semibold text-500">Details</label>
                  <div class="detail-grid">
                    @for (item of getDetailEntries(evidence.details); track item.key) {
                      <div class="detail-item">
                        <span class="detail-key">{{ item.key | titlecase }}:</span>
                        <span class="detail-value">{{ item.value }}</span>
                      </div>
                    }
                  </div>
                </div>

                @if (evidence.reference_url) {
                  <p-button
                    label="View Full Report"
                    icon="pi pi-external-link"
                    styleClass="p-button-text p-button-sm"
                    (onClick)="viewReport(evidence.reference_url)">
                  </p-button>
                }
              </div>
            </p-accordionTab>
          }
        </p-accordion>
      </p-panel>

      <!-- Appeal Section -->
      <p-panel header="Appeal Information" styleClass="mt-3" [toggleable]="true">
        <div class="appeal-info">
          <div class="flex align-items-center gap-2 mb-3">
            <i class="pi pi-calendar text-blue-500"></i>
            <span class="font-semibold">Appeal Deadline:</span>
            <span>{{ rejection()?.appeal_deadline | date:'longDate' }}</span>
          </div>

          <div class="mb-3">
            <span class="font-semibold">Reference Number:</span>
            <span class="ml-2 font-mono">{{ rejection()?.appeal_reference }}</span>
          </div>

          <div class="mt-3">
            <label class="font-semibold block mb-2">To appeal this decision, you may:</label>
            <ol class="appeal-instructions">
              @for (instruction of rejection()?.appeal_instructions; track $index) {
                <li>{{ instruction }}</li>
              }
            </ol>
          </div>

          <div class="flex gap-2 mt-4">
            <p-button label="Start Appeal" icon="pi pi-send" (onClick)="startAppeal()"></p-button>
            <p-button label="Download Rejection Letter" icon="pi pi-download" styleClass="p-button-outlined"></p-button>
          </div>
        </div>
      </p-panel>
    </div>
  `,
  styles: [`
    .rejection-details {
      max-width: 1200px;
      margin: 0 auto;
    }

    .reasoning-list {
      padding-left: 1.5rem;
      line-height: 1.8;
    }

    .progress-bar {
      height: 8px;
      background: var(--surface-200);
      border-radius: 4px;
      overflow: hidden;
      flex: 1;
      max-width: 150px;
    }

    .progress-fill {
      height: 100%;
      border-radius: 4px;
      width: 100%;
    }

    .risk-low { background: var(--green-500); }
    .risk-medium { background: var(--yellow-500); }
    .risk-high { background: var(--orange-500); }
    .risk-critical { background: var(--red-500); }

    .detail-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 0.5rem;
      background: var(--surface-50);
      padding: 1rem;
      border-radius: 6px;
    }

    .detail-item {
      display: flex;
      gap: 0.5rem;
    }

    .detail-key {
      color: var(--text-color-secondary);
    }

    .appeal-instructions {
      padding-left: 1.5rem;
      line-height: 2;
    }
  `]
})
export class RejectionDetailsComponent {
  @Input() rejection = signal<RejectionReasoning | null>(null);

  riskLevel = computed(() => {
    const score = this.rejection()?.risk_score || 0;
    if (score >= 0.8) return 'critical';
    if (score >= 0.6) return 'high';
    if (score >= 0.4) return 'medium';
    return 'low';
  });

  riskSeverity = computed(() => {
    const level = this.riskLevel();
    return level === 'critical' ? 'danger' : level === 'high' ? 'warning' : 'info';
  });

  riskLabel = computed(() => `Risk: ${((this.rejection()?.risk_score || 0) * 100).toFixed(0)}%`);

  getSeverityColor(severity: string): 'success' | 'info' | 'warning' | 'danger' {
    switch (severity) {
      case 'critical': return 'danger';
      case 'high': return 'warning';
      case 'medium': return 'info';
      default: return 'success';
    }
  }

  getDetailEntries(details: Record<string, any>): { key: string; value: string }[] {
    return Object.entries(details).map(([key, value]) => ({
      key: key.replace(/_/g, ' '),
      value: String(value)
    }));
  }

  viewReport(url: string): void {
    window.open(url, '_blank');
  }

  startAppeal(): void {
    // Navigate to appeal form
  }
}
```

### 3.4 Data Flow

```
Data Flow: Medical Code Validation
══════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│                         VALIDATION DATA FLOW                                 │
│                                                                              │
│   Input: ICD-10 Code "J06.9" + CPT Code "99213"                            │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ Layer 1: Redis Cache (<5ms)                                          │   │
│   │                                                                      │   │
│   │   Cache Key: "crosswalk:cpt-icd:99213"                              │   │
│   │   ┌─────────────────┐                                                │   │
│   │   │   HIT?          │── Yes ──► Return cached result                │   │
│   │   └────────┬────────┘                                                │   │
│   │            │ No                                                       │   │
│   └────────────┼─────────────────────────────────────────────────────────┘   │
│                ▼                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ Layer 2: Typesense Search (<50ms)                                    │   │
│   │                                                                      │   │
│   │   Collection: ncci_edits                                            │   │
│   │   Query: { filter: "cpt_code:99213 AND icd_code:J06.9" }           │   │
│   │   ┌─────────────────┐                                                │   │
│   │   │   FOUND?        │── Yes ──► Cache result + Return               │   │
│   │   └────────┬────────┘                                                │   │
│   │            │ No                                                       │   │
│   └────────────┼─────────────────────────────────────────────────────────┘   │
│                ▼                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ Layer 3: PostgreSQL (100-500ms)                                      │   │
│   │                                                                      │   │
│   │   Table: ncci_crosswalks                                            │   │
│   │   Full lookup with joins                                            │   │
│   │   ┌─────────────────┐                                                │   │
│   │   │   Result        │──► Cache in Redis + Return                    │   │
│   │   └─────────────────┘                                                │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   Output: { valid: true, message: "Supported combination" }                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 State Management

```typescript
// Frontend: Validation State Management (Angular Signals)

interface ValidationState {
  // Document upload state
  documents: Signal<UploadedDocument[]>;
  uploadProgress: Signal<number>;

  // Extraction state
  extractedData: Signal<ExtractedClaimData | null>;
  extractionStatus: Signal<'idle' | 'processing' | 'complete' | 'error'>;

  // Validation state
  validationResults: Signal<ValidationRuleResult[]>;
  validationStatus: Signal<'idle' | 'validating' | 'complete'>;

  // Overall claim state
  canSubmit: Signal<boolean>;
  riskScore: Signal<number>;

  // LLM settings state
  llmSettings: Signal<TenantLLMConfig>;
}

// State updates via WebSocket for real-time progress
interface ValidationProgressEvent {
  claim_id: string;
  rule_id: number;
  rule_name: string;
  status: 'running' | 'complete' | 'error';
  progress_percent: number;
  result?: ValidationRuleResult;
}
```

---

## 4. API Contracts

### 4.1 Comprehensive Validation Endpoint

```yaml
# POST /api/v1/claims/validate-comprehensive
# Validates uploaded documents and returns auto-populated claim data

Request:
  Content-Type: multipart/form-data
  Body:
    documents: File[]          # Required: Policy docs, claim forms, invoices, medical records
    tenant_id: string          # Required: Tenant identifier for LLM config lookup
    options:
      skip_forensics: boolean  # Optional: Skip fraud detection (default: false)
      skip_llm: boolean        # Optional: Skip LLM-based validations (default: false)
      validate_only: boolean   # Optional: Don't save, just validate (default: false)

Response:
  Status: 200 OK
  Content-Type: application/json
  Body:
    {
      "claim_id": "uuid",
      "status": "validated",

      "extracted_data": {
        "member": {
          "member_id": "string",
          "first_name": "string",
          "last_name": "string",
          "date_of_birth": "YYYY-MM-DD",
          "gender": "M|F|U",
          "policy_id": "string",
          "confidence": 0.95
        },
        "provider": {
          "npi": "string",
          "name": "string",              # Auto-fetched from NPPES
          "specialty": "string",         # Auto-fetched
          "network_status": "in_network|out_of_network|non_participating",
          "confidence": 0.98
        },
        "services": [
          {
            "service_date": "YYYY-MM-DD",
            "diagnosis_codes": ["J06.9"],
            "procedure_codes": ["99213"],
            "modifiers": ["25"],
            "quantity": 1,
            "charged_amount": 150.00,
            "confidence": 0.92
          }
        ],
        "medications": [
          {
            "ndc_code": "00093-3109",
            "drug_name": "Amoxicillin 500mg",
            "quantity": 30,
            "days_supply": 10,
            "confidence": 0.88
          }
        ],
        "total_charged": 350.00
      },

      "validation_results": [
        {
          "rule_id": 1,
          "rule_name": "Insured Data Extraction",
          "status": "pass|warn|fail|error",
          "severity": "info|warning|error|critical",
          "message": "Member data extracted successfully",
          "details": {},
          "is_blocking": false,
          "execution_time_ms": 45
        }
      ],

      "summary": {
        "can_submit": true,
        "risk_score": 0.15,
        "total_rules": 12,
        "passed": 10,
        "warnings": 2,
        "failures": 0,
        "errors": 0
      },

      "fwa_analysis": {
        "is_suspicious": false,
        "risk_level": "low|medium|high|critical",
        "signals": [],
        "document_hashes": ["abc123..."]
      },

      "suggested_corrections": [
        {
          "field": "services[0].diagnosis_codes[0]",
          "current_value": "J069",
          "suggested_value": "J06.9",
          "reason": "Invalid format - added decimal"
        }
      ]
    }

Error Responses:
  400 Bad Request:
    {
      "error": "validation_error",
      "message": "No documents provided",
      "details": {}
    }

  413 Payload Too Large:
    {
      "error": "file_too_large",
      "message": "Total upload size exceeds 50MB limit"
    }

  503 Service Unavailable:
    {
      "error": "service_unavailable",
      "message": "Validation service temporarily unavailable",
      "retry_after": 30
    }
```

### 4.2 Medical Code Search Endpoint

```yaml
# GET /api/v1/search/codes
# Fast medical code search with typo tolerance

Request:
  Query Parameters:
    q: string                  # Required: Search query (min 2 chars)
    type: icd10|cpt|hcpcs|ndc  # Required: Code type
    limit: integer             # Optional: Max results (default: 10, max: 50)
    filter_gender: M|F         # Optional: Filter gender-specific codes
    filter_age_min: integer    # Optional: Filter by minimum age
    filter_age_max: integer    # Optional: Filter by maximum age

Response:
  Status: 200 OK
  Headers:
    X-Search-Time-Ms: 23
  Body:
    {
      "results": [
        {
          "code": "J06.9",
          "description": "Acute upper respiratory infection, unspecified",
          "category": "Acute upper respiratory infections",
          "chapter": "Diseases of the respiratory system",
          "gender_specific": null,
          "age_range": null,
          "relevance_score": 0.98
        }
      ],
      "total_found": 15,
      "search_time_ms": 23
    }
```

### 4.3 NCCI Edit Check Endpoint

```yaml
# POST /api/v1/validation/ncci-check
# Check NCCI PTP edits and MUE limits

Request:
  Content-Type: application/json
  Body:
    {
      "procedure_codes": [
        {
          "code": "99213",
          "modifier": "25",
          "units": 1
        },
        {
          "code": "71046",
          "modifier": null,
          "units": 1
        }
      ],
      "place_of_service": "11",
      "service_date": "2025-12-19"
    }

Response:
  Status: 200 OK
  Body:
    {
      "is_valid": true,
      "ptp_edits": [
        {
          "column1_code": "99213",
          "column2_code": "71046",
          "edit_result": "pass",
          "modifier_indicator": "1",
          "message": "Modifier 25 allows separate reporting"
        }
      ],
      "mue_checks": [
        {
          "code": "99213",
          "units_billed": 1,
          "mue_limit": 1,
          "adjudication_indicator": "3",
          "result": "pass"
        },
        {
          "code": "71046",
          "units_billed": 1,
          "mue_limit": 2,
          "adjudication_indicator": "2",
          "result": "pass"
        }
      ],
      "check_time_ms": 45
    }
```

### 4.4 LLM Settings Endpoints

```yaml
# GET /api/v1/settings/llm
# Get tenant LLM configuration

Request:
  Headers:
    Authorization: Bearer <token>

Response:
  Status: 200 OK
  Body:
    {
      "tenant_id": "uuid",
      "configurations": {
        "document_extraction": {
          "provider": "azure",
          "model": "gpt-4o",
          "temperature": 0.1,
          "max_tokens": 4096,
          "is_active": true
        },
        "medical_validation": {
          "provider": "anthropic",
          "model": "claude-3-sonnet",
          "temperature": 0.0,
          "max_tokens": 2048,
          "is_active": true
        },
        "fraud_analysis": {
          "provider": "openai",
          "model": "gpt-4o-mini",
          "temperature": 0.0,
          "max_tokens": 1024,
          "is_active": true
        }
      },
      "fallback": {
        "provider": "ollama",
        "model": "llama3.1:70b",
        "trigger_on_error": true,
        "trigger_on_low_confidence": true,
        "confidence_threshold": 0.85
      },
      "validation_settings": {
        "clinical_necessity_review_threshold": 0.85,    # Configurable per Q4
        "require_human_review_below_threshold": true,
        "fraud_claim_action": "accept_then_reject",     # Per Q1
        "validation_cache_ttl_minutes": 5,              # Per Q3
        "persist_validation_results": true              # Per Q3
      },
      "rate_limits": {
        "requests_per_minute": 60,
        "tokens_per_day": 1000000
      },
      "usage_this_month": {
        "total_requests": 12450,
        "total_tokens": 485000,
        "estimated_cost": 45.67
      }
    }

---

# GET /api/v1/settings/system (Admin Only)
# Get system-wide default settings

Request:
  Headers:
    Authorization: Bearer <admin_token>

Response:
  Status: 200 OK
  Body:
    {
      "default_llm_provider": "openai",               # Configurable per Q2
      "available_providers": ["azure", "openai", "ollama"],
      "new_tenant_defaults": {
        "provider": "openai",
        "model": "gpt-4o",
        "clinical_necessity_review_threshold": 0.85
      }
    }

---

# PUT /api/v1/settings/system (Admin Only)
# Update system-wide default settings

Request:
  Headers:
    Authorization: Bearer <admin_token>
  Body:
    {
      "default_llm_provider": "azure",                # Admin can change default
      "new_tenant_defaults": {
        "provider": "azure",
        "model": "gpt-4o",
        "clinical_necessity_review_threshold": 0.80
      }
    }

---

# PUT /api/v1/settings/llm
# Update tenant LLM configuration

Request:
  Headers:
    Authorization: Bearer <token>
  Body:
    {
      "configurations": {
        "document_extraction": {
          "provider": "azure",
          "model": "gpt-4o",
          "temperature": 0.1,
          "max_tokens": 4096
        }
      },
      "fallback": {
        "provider": "ollama",
        "model": "llama3.1:70b",
        "confidence_threshold": 0.80
      }
    }

Response:
  Status: 200 OK
  Body:
    {
      "message": "Configuration updated successfully",
      "updated_at": "2025-12-19T10:30:00Z"
    }
```

### 4.5 Rejection Details Endpoint

```yaml
# GET /api/v1/claims/{claim_id}/rejection
# Get detailed rejection reasoning with evidence

Request:
  Headers:
    Authorization: Bearer <token>
  Path Parameters:
    claim_id: string           # UUID of the rejected claim

Response:
  Status: 200 OK
  Body:
    {
      "claim_id": "uuid",
      "status": "rejected",

      "rejection_reasoning": {
        "rejection_id": "REJ-2025-12-00456",
        "rejection_date": "2025-12-19T14:30:00Z",
        "category": "fraud",
        "risk_score": 0.92,

        "summary": "Claim rejected due to document integrity concerns",

        "reasoning": [
          "The submitted invoice (Invoice_123.pdf) shows signs of digital modification after its original creation.",
          "The document metadata indicates it was edited using PDF editing software (Adobe Acrobat Pro) 3 days after the original creation.",
          "Font inconsistencies were detected in the billing amount section, suggesting potential alteration of charged amounts."
        ],

        "evidence_references": [
          {
            "evidence_id": "EVD-001",
            "signal_type": "metadata_mismatch",
            "severity": "high",
            "confidence": 0.95,
            "document_name": "Invoice_123.pdf",
            "document_id": "doc-uuid-123",
            "page_number": 1,
            "location_description": null,
            "coordinates": null,
            "title": "Metadata Mismatch",
            "description": "Document creation and modification dates do not match",
            "details": {
              "creation_date": "2025-12-10T09:15:00Z",
              "modification_date": "2025-12-13T14:30:22Z",
              "time_difference_hours": 77
            },
            "reference_source": "PDF Metadata Analysis Report",
            "reference_url": "/api/v1/documents/doc-uuid-123/forensics"
          },
          {
            "evidence_id": "EVD-002",
            "signal_type": "suspicious_producer",
            "severity": "high",
            "confidence": 0.88,
            "document_name": "Invoice_123.pdf",
            "document_id": "doc-uuid-123",
            "page_number": null,
            "location_description": null,
            "coordinates": null,
            "title": "Suspicious Producer Software",
            "description": "Document was modified using known PDF editing software",
            "details": {
              "producer": "Adobe Acrobat Pro DC (21.001.20155)",
              "original_creator": "Hospital Billing System v3.2",
              "modification_detected": true
            },
            "reference_source": "Known PDF Editor Detection Database",
            "reference_url": null
          },
          {
            "evidence_id": "EVD-003",
            "signal_type": "font_inconsistency",
            "severity": "medium",
            "confidence": 0.82,
            "document_name": "Invoice_123.pdf",
            "document_id": "doc-uuid-123",
            "page_number": 1,
            "location_description": "Section: Total Amount",
            "coordinates": {"x": 450, "y": 680},
            "title": "Font Inconsistency",
            "description": "Different font detected in specific section",
            "details": {
              "expected_font": "Arial-Bold",
              "detected_font": "Helvetica-Bold",
              "affected_text": "Total: $12,500.00"
            },
            "reference_source": "Document Font Analysis Report",
            "reference_url": "/api/v1/documents/doc-uuid-123/font-analysis"
          }
        ],
        "total_evidence_count": 3,

        "triggered_rules": [
          {
            "rule_id": 3,
            "rule_name": "Fraud Detection",
            "status": "fail",
            "message": "Document tampering detected"
          }
        ],

        "appeal_deadline": "2026-01-18T23:59:59Z",
        "appeal_reference": "REJ-2025-12-00456",
        "appeal_instructions": [
          "Submit original unmodified documents",
          "Provide a letter of explanation from the provider",
          "Request a manual review by contacting support@company.com"
        ],

        "reviewed_by": null,
        "review_notes": null
      },

      "validation_summary": {
        "total_rules": 12,
        "passed": 0,
        "warnings": 0,
        "failures": 1,
        "errors": 0,
        "execution_time_ms": 1250
      },

      "can_appeal": true,
      "can_resubmit": false,
      "resubmit_instructions": null
    }

Error Responses:
  404 Not Found:
    {
      "error": "claim_not_found",
      "message": "Claim with ID {claim_id} not found"
    }

  400 Bad Request:
    {
      "error": "not_rejected",
      "message": "Claim is not in rejected status"
    }
```

### 4.6 Authentication/Authorization

```yaml
# All endpoints require JWT authentication

Headers:
  Authorization: Bearer <jwt_token>

JWT Claims:
  {
    "sub": "user_id",
    "tenant_id": "tenant_uuid",
    "roles": ["claims_processor", "admin"],
    "permissions": ["claims:read", "claims:write", "settings:read", "settings:write"],
    "exp": 1734600000
  }

Role-Based Access:
  claims_processor:
    - POST /api/v1/claims/validate-comprehensive
    - GET /api/v1/search/*
    - POST /api/v1/validation/*

  claims_admin:
    - All claims_processor permissions
    - GET /api/v1/settings/llm
    - PUT /api/v1/settings/llm

  system_admin:
    - All permissions
    - DELETE /api/v1/settings/llm
    - POST /api/v1/admin/*
```

---

## 5. Technology Stack

### 5.1 Core Technologies

| Component | Technology | Version | License | Justification |
|-----------|-----------|---------|---------|---------------|
| Backend API | FastAPI | 0.115.x | MIT | Existing stack, async support |
| Frontend | Angular | 19.x | MIT | Existing stack, signals |
| Database | PostgreSQL | 16.x | PostgreSQL | Existing stack, HIPAA-ready |
| Search Engine | Typesense | 27.1 | GPL-3.0 | Sub-50ms, typo-tolerance |
| Cache | Redis | 7.4.x | BSD-3 | HIPAA-eligible, proven |
| Rules Engine | GoRules ZEN | 0.25.x | MIT | JSON-based, embeddable |
| LLM Gateway | LiteLLM | 1.x | MIT | Provider abstraction |
| PDF Analysis | PyMuPDF | 1.26.x | AGPL-3.0 | Low-level PDF access |

### 5.2 New Dependencies Evaluation

#### Typesense

```
Package: Typesense
Latest Version: 27.1 (verified Dec 2025)
Last Updated: Active development
License: GPL-3.0
Maintenance: ACTIVE

Pros:
- Sub-50ms search latency (verified in benchmarks)
- Built-in typo tolerance
- In-memory index for speed
- Easy Docker deployment
- Python SDK actively maintained

Cons:
- GPL-3.0 license (copyleft)
- Vertical scaling only
- Smaller ecosystem than Elasticsearch

Security: ✓ No known CVEs
Alternatives: Meilisearch (MIT), Elasticsearch (SSPL)
Recommendation: USE - Best fit for sub-50ms requirement

Sources:
- Official Docs: https://typesense.org/docs/
- GitHub: https://github.com/typesense/typesense
- Python SDK: https://github.com/typesense/typesense-python
```

#### GoRules ZEN Engine

```
Package: GoRules ZEN Engine
Latest Version: 0.25.x (verified Dec 2025)
Last Updated: Active development
License: MIT
Maintenance: ACTIVE

Pros:
- JSON-based rule definitions
- Embeddable in Python/JavaScript
- Visual rule editor available
- Fast evaluation (<1ms per rule)
- Decision tables support

Cons:
- Newer project (less battle-tested)
- Smaller community
- Documentation gaps

Security: ✓ No known CVEs
Alternatives: Drools (Java), Easy Rules (Java), Rule Engine (Python)
Recommendation: USE - MIT license, embeddable, fast

Sources:
- Official: https://gorules.io/
- GitHub: https://github.com/gorules/zen
- Python: https://github.com/gorules/zen-python
```

#### Redis

```
Package: Redis
Latest Version: 7.4.x (verified Dec 2025)
Last Updated: Active development
License: BSD-3-Clause (Open Source)
Maintenance: ACTIVE

Pros:
- Sub-millisecond latency
- HIPAA eligible via AWS ElastiCache
- Proven in healthcare industry
- Rich data structures
- Excellent documentation

Cons:
- Memory-bound
- Single-threaded (pre-7.0)
- Enterprise features require license

Security: ✓ HIPAA eligible via managed services
Alternatives: Dragonfly (25x performance), Memcached
Recommendation: USE - Industry standard, HIPAA-ready

Sources:
- Official: https://redis.io/
- HIPAA: https://aws.amazon.com/compliance/hipaa-eligible-services-reference/
- Healthcare: https://redis.io/industries/healthcare/
```

### 5.3 Environment Configuration

```yaml
# Docker Compose for Development

version: '3.8'

services:
  # Typesense Search Engine
  typesense:
    image: typesense/typesense:27.1
    environment:
      TYPESENSE_API_KEY: ${TYPESENSE_API_KEY}
      TYPESENSE_DATA_DIR: /data
    volumes:
      - typesense_data:/data
    ports:
      - "8108:8108"
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

  # Redis Cache
  redis:
    image: redis:7.4-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    deploy:
      resources:
        limits:
          memory: 2G

  # PostgreSQL Database
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: claims_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # FastAPI Backend
  backend:
    build: ./src
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/claims_db
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
      TYPESENSE_URL: http://typesense:8108
      TYPESENSE_API_KEY: ${TYPESENSE_API_KEY}
    depends_on:
      - postgres
      - redis
      - typesense
    ports:
      - "8000:8000"

volumes:
  typesense_data:
  redis_data:
  postgres_data:
```

---

## 6. Security Design

### 6.1 Threat Model (STRIDE)

| Threat | Category | Risk | Mitigation |
|--------|----------|------|------------|
| Unauthorized access to PHI | Spoofing | High | JWT auth, role-based access |
| Claim data tampering | Tampering | High | Audit logs, digital signatures |
| Denial of sensitive actions | Repudiation | Medium | Comprehensive audit logging |
| PHI exposure in logs | Information Disclosure | High | PII masking, encrypted logs |
| Validation bypass | Denial of Service | Medium | Rate limiting, input validation |
| LLM prompt injection | Elevation of Privilege | Medium | Prompt sanitization, output validation |

### 6.2 OWASP Top 10 Mitigations

| OWASP Risk | Mitigation |
|------------|------------|
| A01: Broken Access Control | RBAC implementation, tenant isolation |
| A02: Cryptographic Failures | AES-256 at rest, TLS 1.3 in transit |
| A03: Injection | Parameterized queries, input sanitization |
| A04: Insecure Design | Threat modeling, security reviews |
| A05: Security Misconfiguration | Infrastructure as Code, security scanning |
| A06: Vulnerable Components | Dependency scanning, automated updates |
| A07: Auth Failures | MFA support, token rotation |
| A08: Software/Data Integrity | Signed artifacts, code reviews |
| A09: Logging Failures | Centralized logging, PII masking |
| A10: SSRF | URL validation, allowlisting |

### 6.3 PHI Handling

```python
# src/core/security/phi_handler.py

from typing import Any
import re

class PHIHandler:
    """Handles Protected Health Information securely."""

    # PHI patterns to detect and mask
    PHI_PATTERNS = {
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'member_id': r'\b[A-Z]{3}\d{9}\b',
        'dob': r'\b\d{2}/\d{2}/\d{4}\b',
        'phone': r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
    }

    @classmethod
    def mask_phi_for_logging(cls, data: dict) -> dict:
        """Mask PHI fields before logging."""
        masked = data.copy()
        phi_fields = ['ssn', 'date_of_birth', 'member_id', 'phone', 'address']

        for field in phi_fields:
            if field in masked:
                masked[field] = '***MASKED***'

        return masked

    @classmethod
    def encrypt_at_rest(cls, data: bytes, key: bytes) -> bytes:
        """Encrypt PHI data for storage."""
        from cryptography.fernet import Fernet
        f = Fernet(key)
        return f.encrypt(data)

    @classmethod
    def decrypt(cls, encrypted_data: bytes, key: bytes) -> bytes:
        """Decrypt PHI data."""
        from cryptography.fernet import Fernet
        f = Fernet(key)
        return f.decrypt(encrypted_data)
```

### 6.4 LLM Security

```python
# src/core/security/llm_security.py

class LLMSecurityGuard:
    """Security measures for LLM interactions."""

    # Patterns indicating prompt injection attempts
    INJECTION_PATTERNS = [
        r'ignore previous instructions',
        r'disregard (the )?above',
        r'you are now',
        r'new instructions:',
        r'system prompt:',
    ]

    @classmethod
    def sanitize_input(cls, user_input: str) -> str:
        """Sanitize user input before sending to LLM."""
        sanitized = user_input

        # Remove potential injection patterns
        for pattern in cls.INJECTION_PATTERNS:
            sanitized = re.sub(pattern, '[REMOVED]', sanitized, flags=re.IGNORECASE)

        # Limit input length
        max_length = 10000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized

    @classmethod
    def validate_output(cls, llm_output: str) -> tuple[bool, str]:
        """Validate LLM output for safety."""
        # Check for leaked system prompts
        if 'system prompt' in llm_output.lower():
            return False, "Output contained system prompt reference"

        # Check for code execution attempts
        if re.search(r'```(python|javascript|bash)', llm_output):
            return False, "Output contained code blocks"

        return True, "Output validated"
```

### 6.5 Validation Results Persistence (Q3 Decision)

```sql
-- Validation Results Storage (Per Q3: Cache 5 min, then persist to DB)

-- Validation run history
CREATE TABLE validation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id),
    tenant_id UUID NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    overall_status VARCHAR(20) NOT NULL,  -- 'pass', 'warn', 'fail', 'error'
    risk_score DECIMAL(3, 2),             -- 0.00 - 1.00
    total_rules_executed INTEGER,
    rules_passed INTEGER,
    rules_warned INTEGER,
    rules_failed INTEGER,
    execution_time_ms INTEGER,
    llm_tokens_used INTEGER,
    cached_at TIMESTAMP,                  -- When moved from Redis to DB
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Individual rule results
CREATE TABLE validation_rule_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    validation_run_id UUID NOT NULL REFERENCES validation_runs(id),
    rule_id INTEGER NOT NULL,             -- 1-12
    rule_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,          -- 'pass', 'warn', 'fail', 'error', 'skipped'
    severity VARCHAR(20),                 -- 'info', 'warning', 'error', 'critical'
    message TEXT,
    details JSONB,                        -- Rule-specific details
    is_blocking BOOLEAN DEFAULT false,
    confidence_score DECIMAL(3, 2),       -- For LLM-based rules
    required_human_review BOOLEAN DEFAULT false,  -- Per Q4 threshold
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fraud detection signals (for Rule 3)
CREATE TABLE fraud_detection_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    validation_run_id UUID NOT NULL REFERENCES validation_runs(id),
    claim_id UUID NOT NULL REFERENCES claims(id),
    document_id UUID NOT NULL,
    signal_type VARCHAR(50) NOT NULL,     -- 'metadata_mismatch', 'suspicious_producer', etc.
    severity VARCHAR(20) NOT NULL,        -- 'low', 'medium', 'high', 'critical'
    description TEXT,
    confidence DECIMAL(3, 2),
    location VARCHAR(100),                -- Page/section where detected
    raw_evidence JSONB,                   -- Metadata, hash values, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rejection reasoning storage (Enhanced for Q1)
CREATE TABLE claim_rejections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id),
    rejection_id VARCHAR(50) UNIQUE NOT NULL,  -- 'REJ-2025-12-00456'
    rejection_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    category VARCHAR(50) NOT NULL,              -- 'fraud', 'medical_necessity', etc.
    risk_score DECIMAL(3, 2),                   -- 0.00 - 1.00
    summary TEXT NOT NULL,                      -- One-line summary
    reasoning JSONB NOT NULL,                   -- Array of reasoning strings
    triggered_rules JSONB,                      -- Which rules caused rejection
    appeal_deadline TIMESTAMP,
    appeal_reference VARCHAR(50),
    reviewed_by UUID REFERENCES users(id),
    review_notes TEXT,
    appeal_status VARCHAR(20) DEFAULT 'none',   -- 'none', 'pending', 'approved', 'denied'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Evidence references for rejections
CREATE TABLE rejection_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rejection_id UUID NOT NULL REFERENCES claim_rejections(id),
    evidence_id VARCHAR(50) NOT NULL,           -- 'EVD-001'
    signal_type VARCHAR(50) NOT NULL,           -- 'metadata_mismatch', 'font_inconsistency'
    severity VARCHAR(20) NOT NULL,              -- 'low', 'medium', 'high', 'critical'
    confidence DECIMAL(3, 2) NOT NULL,
    document_name VARCHAR(255),
    document_id UUID,
    page_number INTEGER,
    location_description VARCHAR(255),
    coordinates JSONB,                          -- {"x": 450, "y": 680}
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    details JSONB NOT NULL,                     -- Signal-specific details
    reference_source VARCHAR(255),
    reference_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast queries
CREATE INDEX idx_validation_runs_claim ON validation_runs(claim_id);
CREATE INDEX idx_validation_runs_tenant ON validation_runs(tenant_id);
CREATE INDEX idx_validation_runs_status ON validation_runs(overall_status);
CREATE INDEX idx_rule_results_run ON validation_rule_results(validation_run_id);
CREATE INDEX idx_fraud_signals_claim ON fraud_detection_signals(claim_id);
CREATE INDEX idx_rejections_claim ON claim_rejections(claim_id);
CREATE INDEX idx_rejections_category ON claim_rejections(category);
CREATE INDEX idx_rejections_appeal ON claim_rejections(appeal_status);
CREATE INDEX idx_evidence_rejection ON rejection_evidence(rejection_id);
```

### 6.6 Audit Logging

```python
# src/core/audit/audit_logger.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class AuditEvent(BaseModel):
    """Audit log event structure."""
    timestamp: datetime
    event_type: str
    user_id: str
    tenant_id: str
    resource_type: str
    resource_id: str
    action: str
    ip_address: str
    user_agent: str
    request_id: str
    details: dict
    result: str  # success, failure, error

class AuditLogger:
    """HIPAA-compliant audit logging."""

    async def log_phi_access(
        self,
        user_id: str,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        request_context: dict
    ) -> None:
        """Log PHI access for HIPAA compliance."""
        event = AuditEvent(
            timestamp=datetime.utcnow(),
            event_type="phi_access",
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            ip_address=request_context.get('ip_address', 'unknown'),
            user_agent=request_context.get('user_agent', 'unknown'),
            request_id=request_context.get('request_id', 'unknown'),
            details={},
            result="success"
        )

        # Write to secure audit log
        await self._write_audit_log(event)
```

---

## 7. Performance Plan

### 7.1 Performance Requirements

| Operation | Target p50 | Target p95 | Target p99 |
|-----------|-----------|-----------|-----------|
| Code Search | 15ms | 50ms | 100ms |
| Cache Lookup | 1ms | 5ms | 10ms |
| NCCI Edit Check | 30ms | 100ms | 200ms |
| Single Rule Validation | 50ms | 200ms | 500ms |
| Full Validation (13 rules) | 500ms | 2000ms | 5000ms |
| Document OCR | 5s/page | 15s/page | 30s/page |
| LLM Extraction | 10s | 30s | 60s |

### 7.2 Optimization Strategy

```
Performance Optimization Layers
═══════════════════════════════

┌─────────────────────────────────────────────────────────────────────┐
│ Layer 1: Request Optimization                                        │
│                                                                      │
│   • Request coalescing for batch validations                        │
│   • Connection pooling (database, Redis, Typesense)                 │
│   • HTTP/2 for frontend connections                                  │
│   • Compression (gzip/brotli) for responses                         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 2: Cache Strategy                                              │
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │ Cache Key                          │ TTL      │ Invalidation │   │
│   ├─────────────────────────────────────────────────────────────┤   │
│   │ icd10:code:{code}                  │ 24h      │ Data refresh │   │
│   │ ncci:ptp:{code1}:{code2}           │ 24h      │ Quarterly    │   │
│   │ ncci:mue:{code}:{setting}          │ 24h      │ Quarterly    │   │
│   │ provider:network:{npi}:{policy}    │ 1h       │ Contract chg │   │
│   │ policy:tob:{policy_id}             │ 1h       │ Policy update│   │
│   │ validation:claim:{hash}            │ 5m       │ Never        │   │
│   └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 3: Parallel Execution                                          │
│                                                                      │
│   Validation Rules Execution Plan:                                   │
│                                                                      │
│   Sequential (must complete first):                                  │
│   ├── Rules 1-2: Extraction (required by other rules)               │
│   └── Rule 3: Fraud Detection (may block submission)                │
│                                                                      │
│   Parallel (after extraction):                                       │
│   ├── Rules 4-8: Medical Validations (independent)                  │
│   ├── Rule 9: Report Validation                                     │
│   ├── Rule 10: Rejection Validation                                 │
│   └── Rules 11-12: Coverage Validations (independent)               │
│                                                                      │
│   Expected parallelism benefit: ~60% reduction in total time        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 4: Index Optimization                                          │
│                                                                      │
│   Typesense Indexing Strategy:                                      │
│   • ICD-10 codes: ~70,000 records, indexed by code, description     │
│   • CPT codes: ~10,000 records, indexed by code, description        │
│   • NCCI edits: ~500,000 records, indexed by code pairs             │
│   • Providers: ~1M records, indexed by NPI, name, specialty         │
│                                                                      │
│   PostgreSQL Indexes:                                                │
│   • B-tree: claim_id, member_id, policy_id, service_date           │
│   • GIN: diagnosis_codes, procedure_codes (array columns)           │
│   • Hash: npi (exact match only)                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.3 Resource Estimates

| Service | CPU | Memory | Storage | Instances |
|---------|-----|--------|---------|-----------|
| FastAPI Backend | 4 cores | 8GB | - | 2-4 (auto-scale) |
| Typesense | 4 cores | 8GB | 20GB SSD | 1 (can shard) |
| Redis | 2 cores | 4GB | - | 1 (replica for HA) |
| PostgreSQL | 4 cores | 16GB | 100GB SSD | 1 (read replica) |

### 7.4 Load Testing Plan

```yaml
# k6 Load Test Configuration

scenarios:
  # Normal load
  steady_state:
    executor: constant-arrival-rate
    rate: 10  # 10 validations per second
    duration: 30m
    preAllocatedVUs: 50

  # Peak load
  peak_load:
    executor: ramping-arrival-rate
    startRate: 10
    stages:
      - duration: 5m, target: 50   # Ramp to 50 rps
      - duration: 10m, target: 50  # Hold at 50 rps
      - duration: 5m, target: 10   # Ramp down
    preAllocatedVUs: 200

thresholds:
  http_req_duration:
    - p(50)<500
    - p(95)<2000
    - p(99)<5000
  http_req_failed:
    - rate<0.01  # <1% error rate
```

---

## 8. Risk Register

### 8.1 Technical Risks

| ID | Risk | Probability | Impact | Mitigation | Owner |
|----|------|-------------|--------|------------|-------|
| R1 | Typesense performance degrades with large datasets | Low | High | Pre-test with 1M+ records; implement sharding if needed | Backend Lead |
| R2 | CMS data format changes break parsing | Medium | High | Abstract data parser; monitor CMS announcements | Data Team |
| R3 | LLM rate limits exceeded during peak | Medium | Medium | Implement tenant-level rate limiting; use fallback models | Backend Lead |
| R4 | PDF forensics false positives | High | Medium | Tune thresholds; allow manual override; confidence scoring | ML Team |
| R5 | Redis cache invalidation race conditions | Low | Medium | Use Redis transactions; implement cache versioning | Backend Lead |
| R6 | Angular 19 signals reactivity issues | Low | Low | Comprehensive testing; fallback to observables if needed | Frontend Lead |

### 8.2 External Dependencies

| Dependency | Risk | Fallback Plan |
|------------|------|---------------|
| NPPES API | Availability | Cache provider data locally; batch refresh |
| LLM Providers (OpenAI, Azure) | Outage/Rate Limits | Fallback to Ollama local deployment |
| CMS Data Downloads | Quarterly delays | Use previous quarter data; monitor CMS status |
| Typesense Cloud (if used) | Availability | Self-hosted Docker deployment |

### 8.3 Uncertain Assumptions

| Assumption | Uncertainty Level | Validation Approach |
|------------|-------------------|---------------------|
| PyMuPDF sufficient for fraud detection | Medium | PoC with 100 tampered PDFs; measure accuracy |
| LLM latency acceptable for real-time | Medium | Benchmark with production-like documents |
| Single Typesense instance handles load | Low | Load test with expected data volume |
| Redis memory sufficient for cache | Low | Calculate cache size based on TTLs |

### 8.4 Fallback Plans

| Scenario | Fallback |
|----------|----------|
| Typesense unavailable | Direct PostgreSQL queries (slower but functional) |
| Redis unavailable | Skip cache, direct database queries |
| LLM provider down | Use fallback provider chain (Azure → OpenAI → Ollama) |
| Full system overload | Queue requests with estimated wait times |

---

## 9. Implementation Roadmap

### 9.1 Phase Overview

```
Implementation Timeline
═══════════════════════

Phase 1: Data Infrastructure
├── Set up Typesense cluster
├── Import CMS medical code data
├── Configure Redis cache
└── Create database schema for LLM settings

Phase 2: Core Validation Services
├── Implement Search Gateway
├── Implement Cache Gateway
├── Implement Rules 4, 6, 7, 8 (deterministic)
└── Implement PDF Forensics (Rule 3)

Phase 3: LLM Integration
├── Implement LLM Gateway with LiteLLM
├── Implement Rules 1, 2 (extraction)
├── Implement Rules 5, 9 (LLM-based validation)
└── Configure fallback chain

Phase 4: Configuration UI
├── Create LLM settings API endpoints
├── Build Angular settings component
├── Implement per-tenant configuration
└── Add usage tracking dashboard

Phase 5: Integration & Testing
├── Integrate validation orchestrator
├── End-to-end testing
├── Performance optimization
├── Security audit
└── Documentation
```

### 9.2 Phase 1: Data Infrastructure

**Objective**: Set up search and cache infrastructure with medical code data

**Deliverables**:
1. Typesense cluster running with collections:
   - `icd10_codes` (~70,000 records)
   - `cpt_codes` (~10,000 records)
   - `ncci_edits` (~500,000 records)
   - `mue_limits` (~20,000 records)
2. Redis instance configured with cache key patterns
3. Database migrations for LLM settings tables
4. Data import scripts for CMS files

**Acceptance Criteria**:
- [ ] Typesense search returns results in <50ms
- [ ] All CMS data files imported successfully
- [ ] Redis cache operations complete in <5ms
- [ ] Database schema supports multi-tenant LLM config

### 9.3 Phase 2: Core Validation Services

**Objective**: Implement deterministic validation rules

**Deliverables**:
1. Search Gateway service (Typesense abstraction)
2. Cache Gateway service (Redis abstraction)
3. Rule 3: PDF Forensics service (PyMuPDF)
4. Rule 4: ICD-CPT Crosswalk validator
5. Rule 6: ICD×ICD validator
6. Rules 7-8: Demographic validators

**Acceptance Criteria**:
- [ ] All validators pass unit tests with >90% coverage
- [ ] Validators handle edge cases (missing data, invalid codes)
- [ ] Performance meets targets (see Section 7)
- [ ] Fraud detection identifies test tampered PDFs

### 9.4 Phase 3: LLM Integration

**Objective**: Implement LLM-powered extraction and validation

**Deliverables**:
1. LLM Gateway service (LiteLLM integration)
2. Rules 1-2: Data extraction services
3. Rule 5: Clinical necessity validator
4. Rule 9: Medical report validator
5. Fallback chain configuration

**Acceptance Criteria**:
- [ ] LLM gateway supports all configured providers
- [ ] Extraction achieves >90% accuracy on test documents
- [ ] Fallback activates correctly on provider failure
- [ ] Rate limiting prevents quota exhaustion

### 9.5 Phase 4: Configuration UI

**Objective**: Build LLM settings management interface

**Deliverables**:
1. Settings API endpoints (GET/PUT)
2. Angular LLM settings component
3. Provider selection with model dropdown
4. Usage tracking and cost display
5. Per-tenant configuration storage

**Acceptance Criteria**:
- [ ] Settings UI allows provider/model selection per task
- [ ] Changes persist and take effect immediately
- [ ] Usage metrics display accurately
- [ ] Multi-tenant isolation verified

### 9.6 Phase 5: Integration & Testing

**Objective**: Complete integration and prepare for production

**Deliverables**:
1. Validation Orchestrator (parallel execution)
2. End-to-end test suite
3. Performance optimization
4. Security audit report
5. User documentation

**Acceptance Criteria**:
- [ ] Full validation completes in <2s (target)
- [ ] Load testing passes (10 rps sustained)
- [ ] No critical security vulnerabilities
- [ ] Documentation complete and reviewed

---

## 10. Open Questions

### 10.1 User Decisions (APPROVED)

| # | Question | Decision | Implementation |
|---|----------|----------|----------------|
| Q1 | Should fraud detection block claim submission or just warn? | **Accept & Reject** | System accepts and records the claim, then sets status to "Rejected - Fraud". Claim is stored for audit/investigation. |
| Q2 | Which LLM provider should be default for new tenants? | **Configurable** | Admin can configure default provider (Azure OpenAI, OpenAI, or Ollama) in system settings. No hardcoded default. |
| Q3 | How long should validation results be cached? | **5 min + Persist** | Cache validation results for 5 minutes in Redis, then persist to database for historical reference and audit. |
| Q4 | Should Rule 5 (clinical necessity) require human review? | **Configurable Threshold** | Only low confidence requires review. Confidence threshold (default 85%) is configurable per-tenant in settings. |

### 10.2 Requiring Additional Research

| # | Question | Research Approach | Priority |
|---|----------|-------------------|----------|
| Q5 | What accuracy can PDF forensics achieve? | PoC with 100+ test documents | High |
| Q6 | What is realistic LLM extraction accuracy? | Benchmark with production-like documents | High |
| Q7 | Is Dragonfly suitable for production? | Evaluate maturity, HIPAA compliance | Medium |
| Q8 | Should we support custom validation rules? | User interviews, competitive analysis | Low |

### 10.3 Deferred Decisions

| # | Decision | Reason for Deferral | When to Revisit |
|---|----------|---------------------|-----------------|
| D1 | Typesense vs Meilisearch for hybrid search | Need semantic search evaluation | Phase 3 |
| D2 | Redis vs Dragonfly for production | Performance testing required | Phase 5 |
| D3 | Custom ML models for fraud detection | Evaluate PyMuPDF accuracy first | Post-MVP |

---

## Validation Checklist

Before implementation begins, confirm:

- [x] Business requirements clearly mapped to technical solution
- [x] All integration points identified and specified
- [x] Security requirements addressed (HIPAA, OWASP)
- [x] Performance requirements defined with targets
- [x] Risks identified with mitigation strategies
- [x] Implementation broken into manageable phases
- [x] Technology choices justified with evidence
- [x] **APPROVED: User decisions on open questions (Q1-Q4) - December 19, 2025**

---

## Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | | | |
| Technical Lead | | | |
| Security Lead | | | |
| Architecture Review | | | |

---

**Document Version**: 1.1
**Last Updated**: December 19, 2025
**Status**: ✅ APPROVED - Ready for Implementation

### Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Dec 19, 2025 | Initial design with Q1-Q4 decisions |
| 1.1 | Dec 19, 2025 | Enhanced rejection reasoning with evidence display (Section 3.3.1, 3.3.2, 4.5, 6.5) |
