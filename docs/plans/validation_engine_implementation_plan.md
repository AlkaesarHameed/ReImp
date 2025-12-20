# Validation Engine Implementation Plan

**Created**: December 19, 2025
**Design Reference**: [04_validation_engine_comprehensive_design.md](../design/04_validation_engine_comprehensive_design.md)
**Status**: PENDING APPROVAL

---

## Executive Summary

This implementation plan breaks down the High-Performance Claims Validation Engine into 5 phases with specific tasks, files to create/modify, dependencies to install, and acceptance criteria.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    NEW COMPONENTS TO BUILD                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1: Data Infrastructure                                    │
│  ├── Typesense collections (icd10, cpt, ncci, mue)              │
│  ├── Redis cache configuration                                   │
│  ├── Database schema (llm_settings, validation_results)         │
│  └── Data import scripts (CMS files)                            │
│                                                                  │
│  Phase 2: Core Validation Services                               │
│  ├── SearchGateway (Typesense abstraction)                      │
│  ├── CacheGateway (Redis abstraction)                           │
│  ├── PDFForensicsService (Rule 3)                               │
│  ├── ICDCPTCrosswalkValidator (Rule 4)                          │
│  ├── ICDICDValidator (Rule 6)                                   │
│  └── DemographicValidators (Rules 7-8)                          │
│                                                                  │
│  Phase 3: LLM Integration                                        │
│  ├── LLMGateway enhancement (LiteLLM + multi-provider)          │
│  ├── DataExtractor (Rules 1-2)                                  │
│  ├── ClinicalNecessityValidator (Rule 5)                        │
│  └── MedicalReportValidator (Rule 9)                            │
│                                                                  │
│  Phase 4: Configuration UI                                       │
│  ├── LLM Settings API endpoints                                 │
│  ├── Angular LLM Settings component                             │
│  └── Usage tracking endpoints                                   │
│                                                                  │
│  Phase 5: Integration & Testing                                  │
│  ├── ValidationOrchestrator                                     │
│  ├── E2E test suite                                             │
│  └── Performance optimization                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Data Infrastructure

### Objective
Set up Typesense search, Redis cache, and database schema for validation engine.

### Tasks

#### 1.1 Typesense Setup

**Files to Create:**
```
src/gateways/search_gateway.py          # Typesense client abstraction
src/services/data_import/               # Directory for import scripts
  ├── __init__.py
  ├── base_importer.py                  # Base importer class
  ├── icd10_importer.py                 # ICD-10-CM/PCS importer
  ├── cpt_importer.py                   # CPT/HCPCS importer
  ├── ncci_importer.py                  # NCCI PTP edits importer
  └── mue_importer.py                   # MUE limits importer
scripts/
  ├── setup_typesense.py                # Initialize collections
  └── import_medical_codes.py           # Run all importers
```

**Files to Modify:**
```
docker/docker-compose.local.yml         # Add Typesense service
src/core/config.py                      # Add Typesense config
requirements.txt                        # Add typesense-python
```

**Dependencies:**
| Package | Version | Purpose |
|---------|---------|---------|
| typesense | 0.21.0+ | Typesense Python client |

**Typesense Collections Schema:**
```python
# icd10_codes collection
{
    "name": "icd10_codes",
    "fields": [
        {"name": "code", "type": "string", "facet": True},
        {"name": "description", "type": "string"},
        {"name": "category", "type": "string", "facet": True},
        {"name": "is_billable", "type": "bool", "facet": True},
        {"name": "age_restrictions", "type": "string[]", "optional": True},
        {"name": "gender_restrictions", "type": "string[]", "optional": True}
    ],
    "default_sorting_field": "code"
}

# cpt_codes collection
{
    "name": "cpt_codes",
    "fields": [
        {"name": "code", "type": "string", "facet": True},
        {"name": "description", "type": "string"},
        {"name": "category", "type": "string", "facet": True},
        {"name": "rvu", "type": "float", "optional": True},
        {"name": "status", "type": "string", "facet": True}
    ]
}

# ncci_edits collection
{
    "name": "ncci_edits",
    "fields": [
        {"name": "column1_code", "type": "string", "facet": True},
        {"name": "column2_code", "type": "string", "facet": True},
        {"name": "modifier_indicator", "type": "string"},
        {"name": "effective_date", "type": "string"},
        {"name": "edit_type", "type": "string", "facet": True}
    ]
}

# mue_limits collection
{
    "name": "mue_limits",
    "fields": [
        {"name": "cpt_code", "type": "string", "facet": True},
        {"name": "practitioner_limit", "type": "int32"},
        {"name": "facility_limit", "type": "int32"},
        {"name": "outpatient_limit", "type": "int32"},
        {"name": "rationale", "type": "string"}
    ]
}
```

**Acceptance Criteria:**
- [ ] Typesense running in Docker
- [ ] All 4 collections created
- [ ] ICD-10 codes imported (~70,000 records)
- [ ] CPT codes imported (~10,000 records)
- [ ] NCCI edits imported (~500,000 records)
- [ ] MUE limits imported (~20,000 records)
- [ ] Search returns results in <50ms

---

#### 1.2 Redis Cache Configuration

**Files to Modify:**
```
src/services/cache.py                   # Enhance with validation cache patterns
src/core/config.py                      # Add cache TTL settings
docker/docker-compose.local.yml         # Ensure Redis configured
```

**Cache Key Patterns:**
```python
CACHE_PATTERNS = {
    "validation_result": "val:{claim_id}:{rule_id}",      # 5 min TTL
    "crosswalk": "xwalk:{icd}:{cpt}",                     # 1 hour TTL
    "provider": "prov:{npi}",                             # 30 min TTL
    "policy": "pol:{member_id}:{policy_id}",              # 15 min TTL
    "llm_settings": "llm:{tenant_id}:{task}",             # 10 min TTL
}
```

**Acceptance Criteria:**
- [ ] Redis configured with password protection
- [ ] Cache service supports all key patterns
- [ ] TTL configured per pattern
- [ ] Cache hit/miss metrics exposed

---

#### 1.3 Database Schema

**Files to Create:**
```
src/db/migrations/versions/xxx_add_validation_tables.py
src/models/llm_settings.py              # LLM configuration model
src/models/validation_result.py         # Validation result storage
src/models/claim_rejection.py           # Rejection with reasoning
src/schemas/llm_settings.py             # Pydantic schemas
src/schemas/validation_result.py
src/schemas/rejection.py
```

**Database Tables:**
```sql
-- LLM Settings (per-tenant, per-task)
CREATE TABLE llm_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    task_type VARCHAR(50) NOT NULL,  -- 'extraction', 'validation', 'necessity'
    provider VARCHAR(50) NOT NULL,   -- 'azure', 'openai', 'anthropic', 'ollama'
    model_name VARCHAR(100) NOT NULL,
    api_endpoint VARCHAR(500),
    temperature DECIMAL(3,2) DEFAULT 0.1,
    max_tokens INTEGER DEFAULT 4096,
    fallback_provider VARCHAR(50),
    fallback_model VARCHAR(100),
    rate_limit_rpm INTEGER DEFAULT 60,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, task_type)
);

-- Validation Results (historical)
CREATE TABLE validation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id),
    rule_id VARCHAR(20) NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- 'passed', 'failed', 'warning', 'skipped'
    confidence DECIMAL(3,2),
    details JSONB,
    evidence JSONB,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Claim Rejections (with reasoning)
CREATE TABLE claim_rejections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id),
    rejection_id VARCHAR(50) UNIQUE NOT NULL,
    rejection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    category VARCHAR(50) NOT NULL,
    risk_score DECIMAL(3,2),
    summary TEXT NOT NULL,
    reasoning JSONB NOT NULL,
    triggered_rules JSONB,
    appeal_deadline TIMESTAMP,
    appeal_status VARCHAR(20) DEFAULT 'none',
    created_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rejection Evidence
CREATE TABLE rejection_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rejection_id UUID NOT NULL REFERENCES claim_rejections(id),
    signal_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    details JSONB NOT NULL,
    document_id UUID,
    document_name VARCHAR(255),
    page_number INTEGER,
    reference_source VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_llm_settings_tenant ON llm_settings(tenant_id);
CREATE INDEX idx_validation_results_claim ON validation_results(claim_id);
CREATE INDEX idx_validation_results_rule ON validation_results(rule_id);
CREATE INDEX idx_claim_rejections_claim ON claim_rejections(claim_id);
CREATE INDEX idx_rejection_evidence_rejection ON rejection_evidence(rejection_id);
```

**Acceptance Criteria:**
- [ ] Migration runs successfully
- [ ] Models created with proper relationships
- [ ] Pydantic schemas validate correctly
- [ ] Multi-tenant isolation verified

---

## Phase 2: Core Validation Services

### Objective
Implement deterministic validation rules (3, 4, 6, 7, 8) with search and cache gateways.

### Tasks

#### 2.1 Search Gateway

**Files to Create:**
```
src/gateways/search_gateway.py
tests/gateways/test_search_gateway.py
```

**Interface:**
```python
class SearchGateway:
    async def search_icd10(self, query: str, limit: int = 10) -> List[ICD10Code]
    async def search_cpt(self, query: str, limit: int = 10) -> List[CPTCode]
    async def get_icd10_by_code(self, code: str) -> Optional[ICD10Code]
    async def get_cpt_by_code(self, code: str) -> Optional[CPTCode]
    async def check_ncci_edit(self, cpt1: str, cpt2: str) -> Optional[NCCIEdit]
    async def get_mue_limit(self, cpt: str) -> Optional[MUELimit]
    async def validate_icd_cpt_pair(self, icd: str, cpt: str) -> CrosswalkResult
```

**Acceptance Criteria:**
- [ ] All methods implemented and tested
- [ ] <50ms response time for searches
- [ ] Typo-tolerance working
- [ ] Proper error handling

---

#### 2.2 PDF Forensics Service (Rule 3)

**Files to Create:**
```
src/services/validation/pdf_forensics.py
src/schemas/forensics.py
tests/services/validation/test_pdf_forensics.py
```

**Dependencies:**
| Package | Version | Purpose |
|---------|---------|---------|
| PyMuPDF | 1.24.0+ | PDF analysis |
| python-magic | 0.4.27+ | File type detection |

**Detection Signals:**
```python
class ForensicSignal(Enum):
    METADATA_MISMATCH = "metadata_mismatch"
    SUSPICIOUS_PRODUCER = "suspicious_producer"
    RECENT_MODIFICATION = "recent_modification"
    FONT_INCONSISTENCY = "font_inconsistency"
    HASH_VERIFICATION_FAILED = "hash_verification_failed"
    LAYER_ANOMALY = "layer_anomaly"
    DIGITAL_SIGNATURE_INVALID = "digital_signature_invalid"
```

**Acceptance Criteria:**
- [ ] Detects metadata mismatches
- [ ] Identifies suspicious PDF producers
- [ ] Detects font inconsistencies
- [ ] Calculates risk score 0.0-1.0
- [ ] Returns evidence for rejection reasoning

---

#### 2.3 ICD-CPT Crosswalk Validator (Rule 4)

**Files to Create:**
```
src/services/validation/icd_cpt_crosswalk.py
tests/services/validation/test_icd_cpt_crosswalk.py
```

**Logic:**
```python
class ICDCPTCrosswalkValidator:
    async def validate(self, icd_codes: List[str], cpt_codes: List[str]) -> ValidationResult:
        """
        1. For each CPT code, find valid ICD-10 codes
        2. Check if submitted ICD codes match
        3. Flag mismatches with confidence score
        """
```

**Acceptance Criteria:**
- [ ] Validates all ICD-CPT pairs
- [ ] Returns specific mismatch details
- [ ] Uses Typesense for fast lookups
- [ ] Handles partial matches

---

#### 2.4 ICD×ICD Validator (Rule 6)

**Files to Create:**
```
src/services/validation/icd_conflict_validator.py
tests/services/validation/test_icd_conflict.py
```

**Conflict Types:**
- Mutually exclusive diagnoses
- Manifestation codes without etiology
- Sequencing errors
- Gender/age-specific conflicts

**Acceptance Criteria:**
- [ ] Detects mutually exclusive codes
- [ ] Validates manifestation/etiology pairs
- [ ] Returns conflict details for reasoning

---

#### 2.5 Demographic Validators (Rules 7-8)

**Files to Create:**
```
src/services/validation/demographic_validator.py
tests/services/validation/test_demographic.py
```

**Validation Rules:**
```python
# Age restrictions
AGE_RESTRICTED_CODES = {
    "Z00.121": {"min_age": 0, "max_age": 17},  # Pediatric routine exam
    "Z00.00": {"min_age": 18, "max_age": None},  # Adult routine exam
    # ...
}

# Gender restrictions
GENDER_RESTRICTED_CODES = {
    "C61": {"gender": "M"},  # Prostate cancer
    "C53": {"gender": "F"},  # Cervical cancer
    # ...
}
```

**Acceptance Criteria:**
- [ ] Validates age against ICD-10 restrictions
- [ ] Validates gender against ICD-10 restrictions
- [ ] Validates age/gender against CPT restrictions
- [ ] Returns specific violations

---

## Phase 3: LLM Integration

### Objective
Implement LLM-powered extraction and validation with configurable multi-provider support.

### Tasks

#### 3.1 Enhanced LLM Gateway

**Files to Modify:**
```
src/gateways/llm_gateway.py             # Enhance with LiteLLM + multi-provider
```

**Files to Create:**
```
src/services/llm_config_service.py      # Load tenant LLM settings
tests/gateways/test_llm_gateway.py
```

**Dependencies:**
| Package | Version | Purpose |
|---------|---------|---------|
| litellm | 1.50.0+ | LLM gateway with fallback |

**Features:**
- Multi-provider support (Azure, OpenAI, Anthropic, Ollama)
- Per-tenant configuration
- Automatic fallback on failure
- Rate limiting per tenant
- Token usage tracking

**Acceptance Criteria:**
- [ ] Supports all configured providers
- [ ] Fallback works correctly
- [ ] Rate limiting enforced
- [ ] Usage metrics tracked

---

#### 3.2 Data Extractors (Rules 1-2)

**Files to Create:**
```
src/services/extraction/insured_data_extractor.py    # Rule 1
src/services/extraction/code_extractor.py            # Rule 2
src/services/extraction/__init__.py
tests/services/extraction/test_extractors.py
```

**Extraction Prompts:**
```python
INSURED_DATA_PROMPT = """
Extract the following information from the medical document:
- Patient Name
- Date of Birth
- Member ID
- Policy Number
- Group Number
- Provider NPI (if present)

Return as structured JSON with confidence scores.
"""

CODE_EXTRACTION_PROMPT = """
Extract all medical codes from the document:
- ICD-10-CM diagnosis codes
- ICD-10-PCS procedure codes
- CPT/HCPCS codes
- Revenue codes
- Medication codes (NDC)

Return as structured JSON with page references.
"""
```

**Acceptance Criteria:**
- [ ] >90% extraction accuracy on test documents
- [ ] Returns confidence scores
- [ ] Handles multiple document types
- [ ] Provides page references for evidence

---

#### 3.3 Clinical Necessity Validator (Rule 5)

**Files to Create:**
```
src/services/validation/clinical_necessity.py
tests/services/validation/test_clinical_necessity.py
```

**LLM Prompt:**
```python
NECESSITY_PROMPT = """
Given the following medical claim:
- Diagnosis: {icd_codes}
- Procedures: {cpt_codes}
- Supporting documentation: {clinical_notes}

Evaluate if the procedures are medically necessary for the diagnoses.
Consider:
1. Clinical guidelines and standards of care
2. Medical necessity criteria (LCD/NCD)
3. Supporting documentation adequacy

Return:
- necessity_score: 0.0-1.0
- reasoning: detailed explanation
- evidence_references: specific document sections supporting decision
"""
```

**Acceptance Criteria:**
- [ ] Returns necessity score with reasoning
- [ ] References specific clinical guidelines
- [ ] Respects configurable confidence threshold
- [ ] Routes low confidence to human review queue

---

#### 3.4 Medical Report Validator (Rule 9)

**Files to Create:**
```
src/services/validation/medical_report_validator.py
tests/services/validation/test_medical_report.py
```

**Validation Checks:**
- Report date vs service date consistency
- Provider signature present
- Required sections complete
- Clinical findings support diagnoses

**Acceptance Criteria:**
- [ ] Validates report completeness
- [ ] Checks date consistency
- [ ] Returns missing elements list

---

## Phase 4: Configuration UI

### Objective
Build LLM settings management API and Angular frontend component.

### Tasks

#### 4.1 LLM Settings API

**Files to Create:**
```
src/api/routes/settings.py              # Settings endpoints
src/services/settings_service.py        # Business logic
tests/api/routes/test_settings.py
```

**API Endpoints:**
```
GET    /api/v1/settings/llm                    # Get all LLM settings
GET    /api/v1/settings/llm/{task_type}        # Get settings for task
PUT    /api/v1/settings/llm/{task_type}        # Update settings
GET    /api/v1/settings/llm/providers          # List available providers
GET    /api/v1/settings/llm/models/{provider}  # List models for provider
GET    /api/v1/settings/llm/usage              # Get usage metrics
POST   /api/v1/settings/llm/test               # Test provider connection
```

**Acceptance Criteria:**
- [ ] All endpoints implemented
- [ ] Multi-tenant isolation
- [ ] Validation on settings updates
- [ ] Provider connection test works

---

#### 4.2 Angular LLM Settings Component

**Files to Create:**
```
frontend/apps/claims-app/src/app/
  ├── features/settings/
  │   ├── settings.module.ts
  │   ├── settings-routing.module.ts
  │   ├── components/
  │   │   ├── llm-settings/
  │   │   │   ├── llm-settings.component.ts
  │   │   │   ├── llm-settings.component.html
  │   │   │   ├── llm-settings.component.scss
  │   │   │   └── llm-settings.component.spec.ts
  │   │   └── provider-config/
  │   │       ├── provider-config.component.ts
  │   │       └── provider-config.component.html
  │   └── services/
  │       └── settings.service.ts
```

**UI Features:**
- Task type selector (extraction, validation, necessity)
- Provider dropdown (Azure, OpenAI, Anthropic, Ollama)
- Model selector (filtered by provider)
- Temperature slider
- Max tokens input
- Fallback provider configuration
- Usage metrics display
- Test connection button

**Acceptance Criteria:**
- [ ] Settings form functional
- [ ] Provider/model dropdowns populated
- [ ] Changes save correctly
- [ ] Usage metrics display
- [ ] Connection test works

---

## Phase 5: Integration & Testing

### Objective
Build validation orchestrator, complete E2E testing, and optimize performance.

### Tasks

#### 5.1 Validation Orchestrator

**Files to Create:**
```
src/services/validation/orchestrator.py
src/services/validation/result_aggregator.py
src/services/validation/risk_scorer.py
tests/services/validation/test_orchestrator.py
```

**Orchestrator Flow:**
```python
class ValidationOrchestrator:
    async def validate_comprehensive(
        self,
        claim_id: str,
        documents: List[Document]
    ) -> ComprehensiveValidationResult:
        """
        1. Document Processing (OCR + Classification)
        2. Data Extraction (Rules 1-2) - Sequential
        3. Fraud Detection (Rule 3) - Parallel with step 4
        4. Medical Validation (Rules 4-8) - Parallel
        5. Documentation Check (Rule 9) - After step 2
        6. Coverage Validation (Rules 11-12) - Parallel with step 4
        7. Result Aggregation + Risk Scoring
        """
```

**Acceptance Criteria:**
- [ ] All 13 rules executed correctly
- [ ] Parallel execution working
- [ ] <2s total validation time
- [ ] Results persisted to database
- [ ] Rejection reasoning generated

---

#### 5.2 API Endpoint Integration

**Files to Modify:**
```
src/api/routes/claims.py                # Add comprehensive validation endpoint
```

**New Endpoints:**
```
POST   /api/v1/claims/validate-comprehensive   # Full validation
GET    /api/v1/claims/{id}/validation-results  # Get validation history
GET    /api/v1/claims/{id}/rejection           # Get rejection details
POST   /api/v1/claims/{id}/appeal              # Submit appeal
```

**Acceptance Criteria:**
- [ ] Endpoints functional
- [ ] Proper error responses
- [ ] Authentication enforced
- [ ] Rate limiting applied

---

#### 5.3 End-to-End Testing

**Files to Create:**
```
tests/e2e/
  ├── test_full_validation_flow.py
  ├── test_fraud_detection_flow.py
  ├── test_rejection_reasoning.py
  ├── test_llm_settings_ui.py
  └── fixtures/
      ├── sample_claims/
      ├── sample_documents/
      └── tampered_pdfs/
```

**Test Scenarios:**
1. Happy path: Valid claim passes all validations
2. Fraud path: Tampered PDF triggers fraud detection
3. Medical mismatch: ICD-CPT crosswalk failure
4. Low confidence: Routes to human review
5. LLM failover: Primary provider fails, fallback succeeds

**Acceptance Criteria:**
- [ ] All test scenarios pass
- [ ] >80% code coverage
- [ ] Performance tests pass
- [ ] Security tests pass

---

#### 5.4 Performance Optimization

**Optimization Targets:**
| Metric | Target | Measurement |
|--------|--------|-------------|
| Search latency | <50ms p95 | Typesense queries |
| Cache hit rate | >80% | Redis metrics |
| Full validation | <2s p95 | E2E timing |
| LLM extraction | <5s p95 | Per-document |

**Optimization Tasks:**
- [ ] Enable Typesense query caching
- [ ] Implement connection pooling
- [ ] Optimize parallel execution
- [ ] Add performance monitoring

---

## Dependencies Summary

### Python Packages to Add

```txt
# requirements.txt additions
typesense==0.21.0
litellm==1.50.0
PyMuPDF==1.24.0
python-magic==0.4.27
zen-engine==0.35.0  # GoRules ZEN (optional, for complex rules)
```

### Docker Services to Add

```yaml
# docker-compose.local.yml additions
typesense:
  image: typesense/typesense:27.1
  container_name: typesense
  ports:
    - "8108:8108"
  volumes:
    - typesense-data:/data
  environment:
    - TYPESENSE_API_KEY=${TYPESENSE_API_KEY}
    - TYPESENSE_DATA_DIR=/data
  command: --data-dir /data --api-key=${TYPESENSE_API_KEY}
```

---

## Risk Mitigation

| Risk | Mitigation | Phase |
|------|------------|-------|
| CMS data format changes | Version-specific importers, quarterly review | 1 |
| Typesense performance | Shard large collections, caching | 1 |
| LLM extraction accuracy | Confidence thresholds, human review | 3 |
| PDF forensics false positives | Tunable thresholds, appeal process | 2 |
| Multi-tenant data leakage | Strict tenant isolation, audit logging | All |

---

## Implementation Order

```
Phase 1 (Data Infrastructure)
├── 1.1 Typesense setup + data import
├── 1.2 Redis cache patterns
└── 1.3 Database migrations

Phase 2 (Core Validation) - Depends on Phase 1
├── 2.1 Search Gateway
├── 2.2 PDF Forensics (Rule 3)
├── 2.3 ICD-CPT Crosswalk (Rule 4)
├── 2.4 ICD×ICD Validator (Rule 6)
└── 2.5 Demographic Validators (Rules 7-8)

Phase 3 (LLM Integration) - Depends on Phase 1
├── 3.1 Enhanced LLM Gateway
├── 3.2 Data Extractors (Rules 1-2)
├── 3.3 Clinical Necessity (Rule 5)
└── 3.4 Medical Report Validator (Rule 9)

Phase 4 (Configuration UI) - Depends on Phase 1, 3
├── 4.1 LLM Settings API
└── 4.2 Angular Settings Component

Phase 5 (Integration) - Depends on Phase 2, 3, 4
├── 5.1 Validation Orchestrator
├── 5.2 API Integration
├── 5.3 E2E Testing
└── 5.4 Performance Optimization
```

---

## Approval Required

Before proceeding with implementation, please review and approve:

1. **Phase order and dependencies** - Is the sequence correct?
2. **File structure** - Does the proposed structure fit the project?
3. **Dependencies** - Are the package choices acceptable?
4. **Database schema** - Any changes to the proposed tables?
5. **API endpoints** - Any adjustments needed?
6. **Test coverage requirements** - Is 80% acceptable?

---

**Status**: PENDING APPROVAL
**Next Step**: Upon approval, begin Phase 1.1 (Typesense Setup)
