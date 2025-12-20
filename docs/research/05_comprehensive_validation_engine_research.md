# Comprehensive Claims Validation Engine Research Report

**Research Date**: December 19, 2025
**Focus**: High-Speed Validation Engine with 13 Validation Rules
**Researcher**: Claude Code (AI Assistant)
**Related Documents**:
- [03_configurable_hybrid_architecture_research.md](03_configurable_hybrid_architecture_research.md)
- [03_automated_validation_engine_design.md](../design/03_automated_validation_engine_design.md)

---

## 1. Executive Summary

This research report provides evidence-based recommendations for implementing a high-performance claims validation engine that:

1. **Implements 13 comprehensive validation rules** for medical claims
2. **Achieves sub-50ms search latency** using modern search engines
3. **Leverages caching** for frequently accessed validation data
4. **Provides configurable LLM settings** per the hybrid architecture

### Key Recommendations

| Component | Recommendation | Rationale |
|-----------|----------------|-----------|
| **Search Engine** | Typesense | Sub-50ms latency, typo-tolerance, easy setup |
| **Cache Layer** | Redis/Dragonfly | HIPAA-eligible, sub-ms response |
| **Medical Code DB** | CMS Downloads + Custom | Official source, quarterly updates |
| **PDF Forensics** | PyMuPDF + Custom | Lower-level access, hash-based detection |
| **LLM Config** | Multi-tenant with RBAC | Tenant isolation, centralized management |

---

## 2. Medical Code Databases Research

### 2.1 CMS ICD-10 Resources

**Source**: [CMS ICD-10 Official Page](https://www.cms.gov/medicare/coding-billing/icd-10-codes)
**Verified**: December 19, 2025

| Resource | URL | Update Frequency |
|----------|-----|------------------|
| ICD-10-CM Code Files | [cms.gov/icd-10](https://www.cms.gov/medicare/coding-billing/icd-10-codes) | Annual (Oct 1) |
| ICD-10 Mappings | [2025 Mappings](https://www.cms.gov/medicare/payment/medicare-advantage-rates-statistics/risk-adjustment/2025-model-software/icd-10-mappings) | Annual |
| Conversion Table | CMS Downloads | Annual |

**Key Finding**: CMS provides official FY 2025 ICD-10 code files effective October 1, 2024 - September 30, 2025. Updated files for April 2025 are available for encounters occurring April 1, 2025 onwards.

**Implementation Notes**:
- Download official CMS code files quarterly
- Parse into searchable format (JSON/database)
- Include crosswalk mappings for backward compatibility

### 2.2 NCCI Edits Database

**Source**: [CMS NCCI for Medicare](https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits)
**Verified**: December 19, 2025

```
Package: CMS NCCI Edit Files
Latest Version: v31.3 (PTP Edits effective Oct 1, 2025)
Update Frequency: Quarterly
License: Public Domain (US Government)
Maintenance: ACTIVE - Updated quarterly

Pros:
- Official CMS source
- Comprehensive procedure-to-procedure edits
- Free to use
- Well-documented

Cons:
- No API (downloadable files only)
- Requires parsing/transformation
- Large dataset

Security: ✓ No security concerns (public data)
Recommendation: USE - Essential for claim validation

Sources:
- Official: https://www.cms.gov/national-correct-coding-initiative-ncci
- PTP Edits: https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-procedure-procedure-ptp-edits
```

**NCCI Edit Types**:
1. **PTP (Procedure-to-Procedure) Edits**: Column 1/Column 2 code pairs
2. **MUE (Medically Unlikely Edits)**: Maximum unit limits
3. **Add-On Code Edits**: Primary procedure requirements

**Data Format**: ZIP files containing CSV/spreadsheet data

### 2.3 MUE (Medically Unlikely Edits)

**Source**: [CMS MUE Page](https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-medically-unlikely-edits-mues)
**Verified**: December 19, 2025

| File Type | Effective Date | Posted |
|-----------|---------------|--------|
| DME Supplier MUE | Jan 1, 2026 | Dec 1, 2025 |
| Outpatient Hospital MUE | Jan 1, 2026 | Dec 1, 2025 |
| Practitioner MUE | Jan 1, 2026 | Dec 1, 2025 |

**Key Finding**: Some MUE values are confidential (CMS contractors only). Published MUEs cover most common codes.

**Implementation**:
```python
# MUE Validation Rule Structure
class MUEEdit:
    hcpcs_code: str
    practitioner_mue: int
    outpatient_mue: int
    dme_mue: int
    mue_adjudication_indicator: str  # '1' = Line, '2' = Day, '3' = Date of Service
    mue_rationale: str
```

### 2.4 LCD/NCD Coverage Determinations

**Source**: [Medicare Coverage Database](https://www.cms.gov/medicare-coverage-database/search.aspx)
**Downloads**: [MCD Downloads](https://www.cms.gov/medicare-coverage-database/downloads/downloads.aspx)
**Verified**: December 19, 2025

```
Package: Medicare Coverage Database
Latest Update: September 2025 (Coverage API notice)
License: Public Domain
Maintenance: ACTIVE

Data Available:
- Local Coverage Determinations (LCDs) by state
- National Coverage Determinations (NCDs)
- Billing & Coding Articles
- Coverage guidelines

Download Options:
- "All" policies (historical + current)
- "Current" policies only
- XML/XLSX formats

Recommendation: USE - Critical for Rule 11 (Policy/TOB Validation)
```

**Coverage API**: CMS posted a notice about the Coverage API on September 18, 2025.

### 2.5 SNOMED CT to ICD-10 Mapping

**Source**: [NLM SNOMED CT Mapping](https://www.nlm.nih.gov/research/umls/mapping_projects/snomedct_to_icd10cm.html)
**Technical Specs**: [SNOMED March 2024](https://confluence.ihtsdotools.org/display/RMT/SNOMED+CT+Managed+Service+-+US+Edition+Mapping+SNOMED+CT+to+ICD-10-CM+Technical+Specifications+-+March+2024)

**Purpose**: Semi-automated generation of ICD-10-CM codes from clinical data encoded in SNOMED CT.

**Key Finding**: Full understanding of both SNOMED CT and ICD-10-CM semantics is required for accurate mapping.

---

## 3. High-Speed Search Engine Comparison

### 3.1 Comparison Matrix

| Feature | Typesense | Meilisearch | Elasticsearch |
|---------|-----------|-------------|---------------|
| **Latency** | Sub-50ms | Sub-50ms | Variable (50-500ms) |
| **Setup Complexity** | Low | Low | High |
| **Scaling** | Vertical | Vertical | Horizontal |
| **Typo Tolerance** | Built-in | Built-in | Requires config |
| **License** | GPL-3.0 | MIT | SSPL/Elastic License |
| **Memory Model** | In-RAM | In-RAM | Disk + Cache |
| **Max Dataset** | Millions | Limited | Billions |
| **Ops Overhead** | Minimal | Minimal | Significant |

**Sources**:
- [Meilisearch vs Typesense](https://www.meilisearch.com/blog/meilisearch-vs-typesense)
- [Typesense Comparison](https://typesense.org/docs/overview/comparison-with-alternatives.html)
- [Elasticsearch Benchmarks](https://medium.com/gigasearch/benchmarking-performance-elasticsearch-vs-competitors-d4778ef75639)

### 3.2 Typesense (RECOMMENDED)

```
Package: Typesense
Latest Version: 27.1 (verified Dec 2025)
License: GPL-3.0
Maintenance: ACTIVE

Pros:
- Sub-50ms search latency (consistent)
- Index in RAM for maximum performance
- Typo tolerance built-in
- Easy setup (Docker/Cloud)
- Efficient C++ implementation

Cons:
- GPL license (copyleft)
- Vertical scaling only
- Newer ecosystem

Security: ✓ No known CVEs
Alternatives: Meilisearch, Elasticsearch, Algolia
Recommendation: USE for medical code search

Sources:
- Official: https://typesense.org/docs/
- GitHub: https://github.com/typesense/typesense
- Python SDK: https://github.com/typesense/typesense-python
```

**Python SDK Setup**:
```python
import typesense

client = typesense.Client({
    'nodes': [{'host': 'localhost', 'port': '8108', 'protocol': 'http'}],
    'api_key': 'your-api-key',
    'connection_timeout_seconds': 2
})

# Medical code schema
schema = {
    'name': 'icd10_codes',
    'fields': [
        {'name': 'code', 'type': 'string', 'facet': True},
        {'name': 'description', 'type': 'string'},
        {'name': 'category', 'type': 'string', 'facet': True},
        {'name': 'chapter', 'type': 'string', 'facet': True},
        {'name': 'gender_specific', 'type': 'string', 'facet': True},
        {'name': 'age_range', 'type': 'string', 'facet': True}
    ]
}
```

### 3.3 Meilisearch (ALTERNATIVE)

```
Package: Meilisearch
Latest Version: 1.12.x (verified Dec 2025)
Python SDK: 0.31.x (30,260 weekly downloads)
License: MIT
Maintenance: ACTIVE

Pros:
- MIT License (more permissive)
- Hybrid search (semantic + keyword)
- Ollama embedder support (v1.8+)
- Near-instant indexing
- Sub-50ms search

Cons:
- Feature set more limited
- No distributed option
- Async indexing can mask true performance

Security: ✓ No known CVEs
Recommendation: CONSIDER if MIT license preferred

Sources:
- Official: https://www.meilisearch.com/
- GitHub: https://github.com/meilisearch/meilisearch
- Python: https://github.com/meilisearch/meilisearch-python
```

### 3.4 Implementation Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Search Layer Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐    │
│   │ Typesense   │    │ Typesense   │    │ Typesense       │    │
│   │ Collection: │    │ Collection: │    │ Collection:     │    │
│   │ ICD-10-CM   │    │ CPT/HCPCS   │    │ NCCI Edits      │    │
│   └──────┬──────┘    └──────┬──────┘    └────────┬────────┘    │
│          │                  │                     │             │
│          └──────────────────┴─────────────────────┘             │
│                             │                                    │
│                    ┌────────┴────────┐                          │
│                    │  Search Gateway │                          │
│                    │  (Unified API)  │                          │
│                    └────────┬────────┘                          │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                    Cache Layer (Redis/Dragonfly)                 │
│                             │                                    │
│   ┌─────────────────────────┴─────────────────────────────┐     │
│   │              Validation Result Cache                   │     │
│   │  - ICD-CPT crosswalk results (TTL: 24h)               │     │
│   │  - NCCI edit lookups (TTL: 24h)                       │     │
│   │  - MUE limits (TTL: 24h)                              │     │
│   │  - Provider network status (TTL: 1h)                  │     │
│   └───────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Caching Strategy Research

### 4.1 Redis for Healthcare

**Source**: [Redis Healthcare](https://redis.io/industries/healthcare/)
**HIPAA**: [AWS ElastiCache HIPAA](https://aws.amazon.com/about-aws/whats-new/2017/11/amazon-elasticache-for-redis-is-now-hipaa-eligible-to-help-you-power-secure-healthcare-applications-with-sub-millisecond-latency/)

```
Package: Redis
Latest Version: 7.4.x
License: BSD-3-Clause (Open Source) / Redis Source Available License (Enterprise)
Maintenance: ACTIVE

Pros:
- Sub-millisecond latency
- HIPAA eligible (AWS ElastiCache)
- Rich data structures
- Pub/Sub for real-time updates
- Proven in healthcare

Cons:
- Single-threaded (Redis < 7.0)
- Memory-bound
- Cluster complexity at scale

Security: ✓ HIPAA eligible via managed services
Recommendation: USE for validation caching

Sources:
- Claims Processing: https://redis.io/solutions/claims-processing/
- Healthcare: https://redis.io/industries/healthcare/
```

### 4.2 Dragonfly (High-Performance Alternative)

**Source**: [Dragonfly](https://www.dragonflydb.io/)
**GitHub**: [dragonflydb/dragonfly](https://github.com/dragonflydb/dragonfly)

```
Package: Dragonfly
Latest Version: 1.x (Active development)
License: BSL 1.1 (Business Source License)
Maintenance: ACTIVE

Pros:
- 25X throughput vs Redis
- Multi-threaded architecture
- 100% Redis API compatible
- Single instance up to 1TB
- No cluster complexity

Cons:
- BSL license restrictions
- Newer (less battle-tested)
- Managed services limited

Security: SOC 2, ISO 27001, HIPAA available via Dragonfly Cloud
Recommendation: CONSIDER for high-volume workloads

Sources:
- Official: https://www.dragonflydb.io/
- GitHub: https://github.com/dragonflydb/dragonfly
- Aiven: https://aiven.io/blog/what-is-dragonfly
```

### 4.3 Caching Strategy Implementation

```python
# config/cache_config.py

from enum import Enum
from pydantic import BaseSettings

class CacheProvider(str, Enum):
    REDIS = "redis"
    DRAGONFLY = "dragonfly"
    ELASTICACHE = "elasticache"

class CacheSettings(BaseSettings):
    CACHE_PROVIDER: CacheProvider = CacheProvider.REDIS
    CACHE_URL: str = "redis://localhost:6379"

    # TTL Configuration (seconds)
    CACHE_TTL_ICD_LOOKUP: int = 86400      # 24 hours
    CACHE_TTL_CPT_LOOKUP: int = 86400      # 24 hours
    CACHE_TTL_NCCI_EDIT: int = 86400       # 24 hours
    CACHE_TTL_MUE_LIMIT: int = 86400       # 24 hours
    CACHE_TTL_PROVIDER_NETWORK: int = 3600 # 1 hour
    CACHE_TTL_POLICY_TOB: int = 3600       # 1 hour
    CACHE_TTL_VALIDATION_RESULT: int = 300 # 5 minutes

    # Performance settings
    CACHE_MAX_CONNECTIONS: int = 50
    CACHE_TIMEOUT_MS: int = 100

    class Config:
        env_file = ".env"
```

### 4.4 Cache Key Strategy

```python
# Cache key patterns for validation data

CACHE_KEYS = {
    # Medical code lookups
    "icd10:code:{code}": "ICD-10 code details",
    "icd10:search:{query}": "ICD-10 search results",
    "cpt:code:{code}": "CPT code details",
    "cpt:search:{query}": "CPT search results",

    # NCCI validations
    "ncci:ptp:{code1}:{code2}": "PTP edit result",
    "ncci:mue:{code}:{setting}": "MUE limit",

    # Crosswalk lookups
    "crosswalk:icd-cpt:{icd_code}": "Valid CPT codes for ICD",
    "crosswalk:cpt-icd:{cpt_code}": "Valid ICD codes for CPT",

    # Coverage determinations
    "coverage:lcd:{mac}:{code}": "LCD coverage",
    "coverage:ncd:{code}": "NCD coverage",

    # Provider/network
    "provider:network:{npi}:{policy_id}": "Network status",
    "provider:details:{npi}": "Provider details",

    # Validation results
    "validation:claim:{claim_hash}": "Full validation result"
}
```

---

## 5. PDF Forensics & Fraud Detection

### 5.1 PyMuPDF for PDF Analysis

**Source**: [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
**GitHub Discussion**: [Tampering Detection](https://github.com/pymupdf/PyMuPDF/discussions/892)

```
Package: PyMuPDF
Latest Version: 1.26.7
License: AGPL-3.0 / Commercial
Maintenance: ACTIVE

Pros:
- Lower-level PDF access
- Fast processing
- Decompress editor changes
- Metadata extraction
- Cross-platform

Cons:
- Cannot definitively prove tampering
- Metadata not always present
- AGPL license (copyleft)

Security: ✓ No known CVEs
Alternatives: pdfplumber, PyPDF2, pdfrw
Recommendation: USE as foundation for fraud detection

Sources:
- Docs: https://pymupdf.readthedocs.io/
- Metadata: https://pymupdf.readthedocs.io/en/latest/document.html
```

### 5.2 PDF Tampering Detection Approach

**Source**: [PDF-Tamper-Analysis](https://github.com/alenperic/PDF-Tamper-Analysis)
**Research**: [University of Pretoria Method](https://www.bobsguide.com/unmasking-digital-forgery-a-new-frontier-in-pdf-security/)

**Detection Signals**:

| Signal | Weight | Detection Method |
|--------|--------|------------------|
| Metadata Mismatch | 0.25 | Creation vs modification date |
| Producer Software | 0.15 | Known editor signatures |
| Font Inconsistency | 0.20 | Multiple fonts in typed sections |
| Hash Verification | 0.20 | Page object hash changes |
| XMP Metadata | 0.10 | XML metadata discrepancies |
| Incremental Saves | 0.10 | Multiple save points |

### 5.3 Implementation

```python
# services/fwa/document_forensics.py

import hashlib
from dataclasses import dataclass
from typing import List, Dict, Optional
import fitz  # PyMuPDF

@dataclass
class ForensicSignal:
    signal_type: str
    severity: str  # low, medium, high, critical
    description: str
    location: Optional[str] = None
    confidence: float = 0.0

@dataclass
class ForensicAnalysis:
    document_id: str
    is_suspicious: bool
    risk_score: float  # 0.0 - 1.0
    signals: List[ForensicSignal]
    metadata: Dict[str, any]
    page_hashes: List[str]

class DocumentForensicsService:
    """Analyze PDFs for signs of tampering or forgery."""

    SUSPICIOUS_PRODUCERS = [
        "sejda", "pdf-editor", "nitro", "foxit",
        "adobe acrobat pro", "pdfelement"
    ]

    def analyze(self, pdf_bytes: bytes) -> ForensicAnalysis:
        """Perform forensic analysis on PDF document."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        signals = []

        # 1. Metadata Analysis
        metadata = doc.metadata
        signals.extend(self._analyze_metadata(metadata))

        # 2. Producer Software Check
        signals.extend(self._check_producer(metadata))

        # 3. Page Object Hashing
        page_hashes = self._compute_page_hashes(doc)

        # 4. Font Consistency Check
        signals.extend(self._check_font_consistency(doc))

        # 5. Incremental Save Detection
        signals.extend(self._check_incremental_saves(pdf_bytes))

        # Calculate risk score
        risk_score = self._calculate_risk_score(signals)

        return ForensicAnalysis(
            document_id=hashlib.sha256(pdf_bytes).hexdigest()[:16],
            is_suspicious=risk_score > 0.5,
            risk_score=risk_score,
            signals=signals,
            metadata=metadata,
            page_hashes=page_hashes
        )

    def _analyze_metadata(self, metadata: dict) -> List[ForensicSignal]:
        signals = []

        creation_date = metadata.get("creationDate")
        mod_date = metadata.get("modDate")

        if creation_date and mod_date:
            # Parse and compare dates
            if mod_date != creation_date:
                signals.append(ForensicSignal(
                    signal_type="metadata_mismatch",
                    severity="medium",
                    description=f"Document modified after creation",
                    confidence=0.7
                ))

        return signals

    def _check_producer(self, metadata: dict) -> List[ForensicSignal]:
        signals = []
        producer = (metadata.get("producer") or "").lower()

        for suspicious in self.SUSPICIOUS_PRODUCERS:
            if suspicious in producer:
                signals.append(ForensicSignal(
                    signal_type="suspicious_producer",
                    severity="high",
                    description=f"Edited with: {producer}",
                    confidence=0.85
                ))
                break

        return signals

    def _compute_page_hashes(self, doc) -> List[str]:
        """Compute hash of each page's content."""
        hashes = []
        for page in doc:
            content = page.get_text("rawdict")
            page_hash = hashlib.sha256(
                str(content).encode()
            ).hexdigest()[:16]
            hashes.append(page_hash)
        return hashes

    def _calculate_risk_score(self, signals: List[ForensicSignal]) -> float:
        if not signals:
            return 0.0

        severity_weights = {
            "low": 0.1,
            "medium": 0.3,
            "high": 0.6,
            "critical": 1.0
        }

        total_score = sum(
            severity_weights.get(s.severity, 0) * s.confidence
            for s in signals
        )

        return min(total_score / len(signals), 1.0)
```

---

## 6. Age/Gender Validation Database

### 6.1 Official Sources

**Source**: [ICD-10-CM Guidelines](https://stacks.cdc.gov/view/cdc/158747)
**Reference**: [ICD10Data.com](https://www.icd10data.com/)

### 6.2 Gender-Specific Codes

```yaml
# data/gender_specific_codes.yaml

male_only:
  diagnosis:
    - range: "N40-N42"
      description: "Prostate disorders"
    - code: "C61"
      description: "Malignant neoplasm of prostate"
    - code: "N46"
      description: "Male infertility"
    - range: "N47-N51"
      description: "Disorders of male genital organs"

  procedures:
    - code: "55840"
      description: "Prostatectomy"
    - code: "54150"
      description: "Circumcision"

female_only:
  diagnosis:
    - range: "N80-N98"
      description: "Noninflammatory disorders female genital tract"
    - range: "O00-O9A"
      description: "Pregnancy, childbirth, puerperium"
    - range: "C56-C57"
      description: "Ovarian/uterine cancer"
    - code: "N94.6"
      description: "Dysmenorrhea"

  procedures:
    - code: "58150"
      description: "Total abdominal hysterectomy"
    - code: "76801"
      description: "Ultrasound, pregnant uterus"
```

### 6.3 Age-Specific Codes

```yaml
# data/age_specific_codes.yaml

pediatric_only:  # Age < 18
  diagnosis:
    - range: "P00-P96"
      description: "Conditions originating in perinatal period"
      max_age_days: 28  # Newborn specific
    - range: "Q00-Q99"
      description: "Congenital malformations"
      note: "Some codes valid for adults"

  procedures:
    - code: "90460-90461"
      description: "Immunization administration (pediatric)"
      max_age: 18

adult_only:  # Age >= 18
  diagnosis:
    - code: "F03"
      description: "Unspecified dementia"
      min_age: 40
    - code: "N40"
      description: "Benign prostatic hyperplasia"
      min_age: 40

  procedures:
    - code: "J1745"
      description: "Infliximab injection"
      min_age: 18

age_ranges:
  preventive_visits:
    - code: "99381"
      description: "New patient, infant (< 1 year)"
      min_age: 0
      max_age: 1
    - code: "99382"
      description: "New patient, early childhood (1-4)"
      min_age: 1
      max_age: 4
    - code: "99383"
      description: "New patient, late childhood (5-11)"
      min_age: 5
      max_age: 11
    - code: "99384"
      description: "New patient, adolescent (12-17)"
      min_age: 12
      max_age: 17
    - code: "99385"
      description: "New patient, 18-39 years"
      min_age: 18
      max_age: 39
    - code: "99386"
      description: "New patient, 40-64 years"
      min_age: 40
      max_age: 64
    - code: "99387"
      description: "New patient, 65+ years"
      min_age: 65
```

### 6.4 Validation Implementation

```python
# services/medical/demographic_validator.py

from dataclasses import dataclass
from typing import List, Optional
from datetime import date
from dateutil.relativedelta import relativedelta

@dataclass
class DemographicValidationResult:
    is_valid: bool
    issues: List[str]
    warnings: List[str]

@dataclass
class PatientDemographics:
    date_of_birth: date
    gender: str  # 'M', 'F', 'U'

    @property
    def age_years(self) -> int:
        today = date.today()
        return relativedelta(today, self.date_of_birth).years

    @property
    def age_days(self) -> int:
        return (date.today() - self.date_of_birth).days

class DemographicValidator:
    """Validates diagnoses and procedures against patient demographics."""

    def __init__(self, rules_db):
        self.rules = rules_db

    def validate_diagnosis(
        self,
        patient: PatientDemographics,
        icd_code: str
    ) -> DemographicValidationResult:
        issues = []
        warnings = []

        # Gender validation
        gender_rule = self.rules.get_gender_rule(icd_code)
        if gender_rule:
            if gender_rule == "male_only" and patient.gender != "M":
                issues.append(
                    f"Diagnosis {icd_code} is male-specific but patient is {patient.gender}"
                )
            elif gender_rule == "female_only" and patient.gender != "F":
                issues.append(
                    f"Diagnosis {icd_code} is female-specific but patient is {patient.gender}"
                )

        # Age validation
        age_rule = self.rules.get_age_rule(icd_code)
        if age_rule:
            if age_rule.get("min_age") and patient.age_years < age_rule["min_age"]:
                issues.append(
                    f"Diagnosis {icd_code} requires age >= {age_rule['min_age']}, "
                    f"patient is {patient.age_years}"
                )
            if age_rule.get("max_age") and patient.age_years > age_rule["max_age"]:
                issues.append(
                    f"Diagnosis {icd_code} requires age <= {age_rule['max_age']}, "
                    f"patient is {patient.age_years}"
                )
            if age_rule.get("max_age_days") and patient.age_days > age_rule["max_age_days"]:
                warnings.append(
                    f"Diagnosis {icd_code} typically for newborns (<= {age_rule['max_age_days']} days)"
                )

        return DemographicValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            warnings=warnings
        )
```

---

## 7. Multi-Tenant LLM Configuration

### 7.1 Architecture Patterns

**Sources**:
- [Azure Multi-tenant AI](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/ai-ml)
- [Portkey Multi-tenant](https://portkey-docs.mintlify.dev/docs/guides/use-cases/multi-tenant-ai-feature)
- [AWS Gen AI Gateway](https://aws.amazon.com/blogs/machine-learning/build-a-multi-tenant-generative-ai-environment-for-your-enterprise-on-aws/)

### 7.2 Configuration Schema

```python
# config/llm_tenant_config.py

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class LLMProvider(str, Enum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    VLLM = "vllm"

class LLMUsageType(str, Enum):
    DOCUMENT_EXTRACTION = "document_extraction"
    MEDICAL_VALIDATION = "medical_validation"
    CODE_SUGGESTION = "code_suggestion"
    FRAUD_ANALYSIS = "fraud_analysis"
    GENERAL = "general"

class ProviderConfig(BaseModel):
    """Configuration for a specific LLM provider."""
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.1
    timeout_seconds: int = 60

class FallbackConfig(BaseModel):
    """Fallback configuration when primary fails."""
    provider: LLMProvider
    model: str
    trigger_on_error: bool = True
    trigger_on_low_confidence: bool = True
    confidence_threshold: float = 0.85

class TenantLLMConfig(BaseModel):
    """Per-tenant LLM configuration."""
    tenant_id: str
    tenant_name: str

    # Per-usage-type configurations
    configurations: Dict[LLMUsageType, ProviderConfig] = Field(default_factory=dict)

    # Global fallback
    fallback: Optional[FallbackConfig] = None

    # Rate limiting
    requests_per_minute: int = 60
    tokens_per_day: int = 1000000

    # Feature flags
    enable_caching: bool = True
    enable_audit_logging: bool = True
    enable_cost_tracking: bool = True

class GlobalLLMSettings(BaseModel):
    """System-wide LLM settings."""

    # Default configurations (used when tenant doesn't specify)
    defaults: Dict[LLMUsageType, ProviderConfig]

    # Available providers
    available_providers: List[LLMProvider]

    # Global limits
    max_concurrent_requests: int = 100
    global_rate_limit_rpm: int = 1000

    # Monitoring
    enable_metrics: bool = True
    metrics_retention_days: int = 30
```

### 7.3 Settings UI Components

```typescript
// Frontend: LLM Settings Component Structure

interface LLMProviderOption {
  id: string;
  name: string;
  logo: string;
  models: string[];
  requiresApiKey: boolean;
  supportsVision: boolean;
}

interface LLMSettingsState {
  // Per-task configuration
  documentExtraction: {
    provider: string;
    model: string;
    enabled: boolean;
  };
  medicalValidation: {
    provider: string;
    model: string;
    enabled: boolean;
  };
  fraudAnalysis: {
    provider: string;
    model: string;
    enabled: boolean;
  };

  // Fallback settings
  fallback: {
    enabled: boolean;
    provider: string;
    model: string;
    confidenceThreshold: number;
  };

  // Rate limits
  rateLimits: {
    requestsPerMinute: number;
    tokensPerDay: number;
  };
}

// Settings Panel Layout
const LLMSettingsPanel = () => {
  return (
    <TabView>
      <TabPanel header="Document Extraction">
        <ProviderSelector usage="document_extraction" />
        <ModelSelector />
        <ParameterSliders />
      </TabPanel>

      <TabPanel header="Medical Validation">
        <ProviderSelector usage="medical_validation" />
        <ModelSelector />
        <ParameterSliders />
      </TabPanel>

      <TabPanel header="Fraud Analysis">
        <ProviderSelector usage="fraud_analysis" />
        <ModelSelector />
        <ParameterSliders />
      </TabPanel>

      <TabPanel header="Fallback & Limits">
        <FallbackConfiguration />
        <RateLimitSettings />
        <CostTracking />
      </TabPanel>
    </TabView>
  );
};
```

### 7.4 Database Schema for Settings

```sql
-- LLM Provider Configurations
CREATE TABLE llm_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_type VARCHAR(50) NOT NULL,  -- openai, azure, ollama, etc.
    name VARCHAR(100) NOT NULL,
    api_base_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    supports_vision BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Available Models per Provider
CREATE TABLE llm_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID REFERENCES llm_providers(id),
    model_id VARCHAR(100) NOT NULL,
    display_name VARCHAR(200),
    max_tokens INTEGER,
    supports_functions BOOLEAN DEFAULT false,
    cost_per_1k_input DECIMAL(10, 6),
    cost_per_1k_output DECIMAL(10, 6),
    is_active BOOLEAN DEFAULT true
);

-- Tenant-specific Configurations
CREATE TABLE tenant_llm_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    usage_type VARCHAR(50) NOT NULL,  -- document_extraction, medical_validation, etc.
    provider_id UUID REFERENCES llm_providers(id),
    model_id UUID REFERENCES llm_models(id),
    temperature DECIMAL(3, 2) DEFAULT 0.10,
    max_tokens INTEGER DEFAULT 4096,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, usage_type)
);

-- Tenant Fallback Configurations
CREATE TABLE tenant_llm_fallbacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    fallback_provider_id UUID REFERENCES llm_providers(id),
    fallback_model_id UUID REFERENCES llm_models(id),
    trigger_on_error BOOLEAN DEFAULT true,
    trigger_on_low_confidence BOOLEAN DEFAULT true,
    confidence_threshold DECIMAL(3, 2) DEFAULT 0.85,
    UNIQUE(tenant_id)
);

-- API Keys (encrypted)
CREATE TABLE tenant_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    provider_id UUID REFERENCES llm_providers(id),
    encrypted_key BYTEA NOT NULL,
    key_hint VARCHAR(10),  -- Last 4 chars for display
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE(tenant_id, provider_id)
);

-- Usage Tracking
CREATE TABLE llm_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    provider_id UUID REFERENCES llm_providers(id),
    model_id UUID REFERENCES llm_models(id),
    usage_type VARCHAR(50),
    input_tokens INTEGER,
    output_tokens INTEGER,
    latency_ms INTEGER,
    was_fallback BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast queries
CREATE INDEX idx_usage_tenant_date ON llm_usage_logs(tenant_id, created_at);
CREATE INDEX idx_tenant_configs ON tenant_llm_configs(tenant_id);
```

---

## 8. Complete Validation Engine Architecture

### 8.1 System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         VALIDATION ENGINE ARCHITECTURE                        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                        API Layer (FastAPI)                               │ │
│  │  POST /api/v1/claims/validate-comprehensive                             │ │
│  │  GET  /api/v1/validation/rules                                          │ │
│  │  POST /api/v1/settings/llm                                              │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                          │
│                                    ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    Validation Orchestrator                               │ │
│  │  - Parallel rule execution                                              │ │
│  │  - Result aggregation                                                   │ │
│  │  - Risk scoring                                                         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                          │
│         ┌──────────────────────────┼──────────────────────────┐              │
│         │                          │                          │              │
│         ▼                          ▼                          ▼              │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐        │
│  │ Extraction  │           │ Medical     │           │ Coverage    │        │
│  │ Rules       │           │ Rules       │           │ Rules       │        │
│  │ (1, 2)      │           │ (4-9)       │           │ (11, 12)    │        │
│  └─────────────┘           └─────────────┘           └─────────────┘        │
│         │                          │                          │              │
│         └──────────────────────────┼──────────────────────────┘              │
│                                    │                                          │
│                                    ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                        Service Layer                                     │ │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ │ │
│  │  │ Search    │ │ Cache     │ │ LLM       │ │ Rules     │ │ Forensics │ │ │
│  │  │ Gateway   │ │ Gateway   │ │ Gateway   │ │ Gateway   │ │ Service   │ │ │
│  │  │(Typesense)│ │(Redis)    │ │(LiteLLM)  │ │(ZEN)      │ │(PyMuPDF)  │ │ │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                          │
│                                    ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                        Data Layer                                        │ │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐                  │ │
│  │  │ PostgreSQL    │ │ Typesense     │ │ Redis         │                  │ │
│  │  │ - Claims      │ │ - ICD-10      │ │ - Validation  │                  │ │
│  │  │ - Policies    │ │ - CPT/HCPCS   │ │   Cache       │                  │ │
│  │  │ - Settings    │ │ - NCCI Edits  │ │ - Session     │                  │ │
│  │  │ - Audit Logs  │ │ - Providers   │ │ - Rate Limit  │                  │ │
│  │  └───────────────┘ └───────────────┘ └───────────────┘                  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Validation Rules Summary

| Rule | Name | Data Source | Cache TTL | Blocking |
|------|------|-------------|-----------|----------|
| 1 | Extract Insured Data | OCR + LLM | N/A | No |
| 2 | Extract Codes/Services | OCR + LLM | N/A | No |
| 3 | Fraud Detection | PyMuPDF + ML | N/A | Yes |
| 4 | ICD-CPT Crosswalk | CMS + Typesense | 24h | Yes |
| 5 | Clinical Necessity | LLM + Notes | 5m | Yes |
| 6 | ICD×ICD Validation | CMS + Rules | 24h | Yes |
| 7 | Age/Gender (Dx) | Custom DB | 24h | Yes |
| 8 | Age/Gender (Px) | Custom DB | 24h | Yes |
| 9 | Medical Reports | LLM Analysis | 5m | No |
| 10 | Rejection Reasons | Rules Engine | 1h | Info |
| 11 | Policy/TOB | MCD + Policy | 1h | Yes |
| 12 | Network Coverage | Provider DB | 1h | No |

---

## 9. Performance Benchmarks & Targets

### 9.1 Target Performance

| Operation | Target Latency | Technology |
|-----------|---------------|------------|
| Code Search | < 50ms | Typesense |
| Cache Lookup | < 5ms | Redis/Dragonfly |
| NCCI Edit Check | < 100ms | Cache + Search |
| Full Validation | < 2s | Parallel execution |
| Document OCR | < 15s/page | PaddleOCR/Azure |
| LLM Extraction | < 30s | Ollama/GPT-4 |

### 9.2 Indexing Strategy

```python
# Typesense collection optimization

COLLECTIONS = {
    "icd10_codes": {
        "default_sorting_field": "usage_frequency",
        "token_separators": [".", "-"],
        "symbols_to_index": ["."],
        "fields": [
            {"name": "code", "type": "string", "index": True, "sort": True},
            {"name": "description", "type": "string"},
            {"name": "synonyms", "type": "string[]", "optional": True},
            {"name": "chapter", "type": "string", "facet": True},
            {"name": "category", "type": "string", "facet": True},
            {"name": "usage_frequency", "type": "int32"},  # For relevance
            {"name": "gender_specific", "type": "string", "facet": True},
            {"name": "age_min", "type": "int32", "optional": True},
            {"name": "age_max", "type": "int32", "optional": True}
        ]
    },

    "ncci_edits": {
        "fields": [
            {"name": "column1_code", "type": "string", "index": True},
            {"name": "column2_code", "type": "string", "index": True},
            {"name": "effective_date", "type": "int64"},
            {"name": "deletion_date", "type": "int64", "optional": True},
            {"name": "modifier_indicator", "type": "string"},
            {"name": "ptp_edit_rationale", "type": "string", "optional": True}
        ]
    }
}
```

---

## 10. Implementation Checklist

### Phase 1: Data Infrastructure (Week 1)
- [ ] Set up Typesense cluster
- [ ] Import CMS ICD-10-CM codes
- [ ] Import CPT/HCPCS codes
- [ ] Import NCCI PTP edits
- [ ] Import MUE limits
- [ ] Set up Redis/Dragonfly cache
- [ ] Configure cache TTLs

### Phase 2: Validation Services (Week 2)
- [ ] Implement Search Gateway
- [ ] Implement Cache Gateway
- [ ] Implement demographic validator
- [ ] Implement NCCI edit checker
- [ ] Implement MUE validator

### Phase 3: Forensics & LLM (Week 3)
- [ ] Implement PDF forensics service
- [ ] Configure LLM Gateway (per hybrid architecture)
- [ ] Implement clinical necessity validator
- [ ] Implement extraction services

### Phase 4: Configuration UI (Week 4)
- [ ] Create LLM settings database schema
- [ ] Build settings API endpoints
- [ ] Create Angular settings component
- [ ] Implement per-tenant configuration
- [ ] Add usage tracking/metrics

### Phase 5: Integration & Testing (Week 5)
- [ ] Integrate all validators
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Load testing
- [ ] Documentation

---

## 11. Evidence Citations

### Official Sources

| Resource | URL | Accessed |
|----------|-----|----------|
| CMS ICD-10 | https://www.cms.gov/medicare/coding-billing/icd-10-codes | Dec 19, 2025 |
| CMS NCCI | https://www.cms.gov/national-correct-coding-initiative-ncci | Dec 19, 2025 |
| CMS MUE | https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-medically-unlikely-edits-mues | Dec 19, 2025 |
| Medicare Coverage DB | https://www.cms.gov/medicare-coverage-database/search.aspx | Dec 19, 2025 |
| SNOMED CT Mapping | https://www.nlm.nih.gov/research/umls/mapping_projects/snomedct_to_icd10cm.html | Dec 19, 2025 |

### Technology Sources

| Package | URL | Version |
|---------|-----|---------|
| Typesense | https://typesense.org/docs/ | 27.1 |
| Meilisearch | https://www.meilisearch.com/ | 1.12.x |
| Redis | https://redis.io/ | 7.4.x |
| Dragonfly | https://www.dragonflydb.io/ | 1.x |
| PyMuPDF | https://pymupdf.readthedocs.io/ | 1.26.7 |

### Research References

| Topic | Source |
|-------|--------|
| PDF Forensics | https://github.com/alenperic/PDF-Tamper-Analysis |
| Multi-tenant LLM | https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/ai-ml |
| Search Benchmarks | https://medium.com/gigasearch/benchmarking-performance-elasticsearch-vs-competitors |

---

## 12. Recommendations Summary

### RECOMMENDED Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Search Engine | **Typesense** | Sub-50ms, typo-tolerance, easy setup |
| Cache | **Redis** (primary) | HIPAA-eligible, proven, sub-ms |
| Cache (alt) | **Dragonfly** | 25X performance for high volume |
| PDF Analysis | **PyMuPDF** | Low-level access, fast |
| LLM Gateway | **LiteLLM** | Provider abstraction, fallback |
| Rules Engine | **GoRules ZEN** | Open-source, JSON-based |

### Data Sources Priority

1. **CMS Official Downloads** - ICD-10, NCCI, MUE (quarterly sync)
2. **Medicare Coverage Database** - LCD/NCD coverage rules
3. **Custom Databases** - Age/gender rules, crosswalks
4. **Third-party APIs** - Provider network, NPI lookup

### Performance Architecture

1. **Layer 1: Cache** - Redis for hot data (< 5ms)
2. **Layer 2: Search** - Typesense for lookups (< 50ms)
3. **Layer 3: Database** - PostgreSQL for persistence
4. **Layer 4: External** - LLM, external APIs (async)

---

**Document Version**: 1.0
**Last Updated**: December 19, 2025
**Status**: Research Complete - Ready for Implementation
