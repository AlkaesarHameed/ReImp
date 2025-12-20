# Claims Adjudication Engine: FWA, Medical Necessity & Coding Validation Research

**Research Date**: December 19, 2025
**Focus**: Fraud/Waste/Abuse Detection, Medical Necessity Validation, American Medical Coding Systems
**Researcher**: Claude Code (AI Assistant)
**Related Documents**:
- [05_comprehensive_validation_engine_research.md](05_comprehensive_validation_engine_research.md)
- [04_validation_engine_comprehensive_design.md](../design/04_validation_engine_comprehensive_design.md)

---

## 1. Executive Summary

This research report provides comprehensive findings for building a **100% automated Claims Adjudication and Processing Engine** with:

1. **American Medical Coding Validation** (ICD-10-CM, CPT, HCPCS)
2. **Medical Necessity Validation** (LCD/NCD, InterQual, MCG)
3. **Fraud, Waste, and Abuse (FWA) Detection Engine**
4. **Trends Analytics and Audit Validation**

### Key Findings

| Component | Availability | Build vs Buy | Recommendation |
|-----------|-------------|--------------|----------------|
| ICD-10 Validation | CMS Free Data | Build | Use `icd10-cm` Python lib + CMS data |
| CPT/HCPCS Validation | AMA Licensed | License Required | Budget $10K-50K/year for AMA license |
| Medical Necessity | Commercial APIs | Integrate | InterQual/MCG or build from CMS LCD/NCD |
| FWA Detection | ML Models | Build | Scikit-learn + PyTorch for anomaly detection |
| Claims Parsing (X12) | Open Source | Build | `x12-edi-tools` or Databricks parser |
| Document OCR | Cloud APIs | Buy | Amazon Textract (HIPAA-eligible) |

### Critical Business Impact

- Healthcare fraud costs **$68 billion annually** in the US (NHCAA)
- Medicare/Medicaid improper payments: **$31.46 billion** (2022)
- AI-powered FWA detection can improve detection by **10x** over rules-based systems
- Industry automation saves **$222 billion** per 2024 CAQH Index

---

## 2. American Medical Coding Systems

### 2.1 ICD-10-CM/PCS (Diagnosis & Procedure Codes)

**Source**: [CMS ICD-10 Official](https://www.cms.gov/medicare/coding-billing/icd-10-codes)
**Verified**: December 19, 2025

```
Package: CMS ICD-10-CM/PCS Code Sets
Latest Version: FY 2025 (October 1, 2024 - September 30, 2025)
Update Frequency: Annual (October 1)
License: Public Domain (US Government)
Maintenance: ACTIVE

Pros:
- Official authoritative source
- Free to use
- Comprehensive code set
- Includes GEM mappings (ICD-9 to ICD-10)

Cons:
- Annual updates require system refresh
- Large dataset (~72,000+ codes)
- Complex hierarchical structure

Security: No security concerns (public data)
Recommendation: USE - Essential for diagnosis validation

Sources:
- Official: https://www.cms.gov/medicare/coding-billing/icd-10-codes
- Code Files: https://www.cms.gov/medicare/coding-billing/icd-10-codes/downloads
```

**Data Files Available**:

| File | Description | Format |
|------|-------------|--------|
| ICD-10-CM Code Descriptions | Full code list with descriptions | TXT/XML |
| ICD-10-PCS Code Tables | Procedure codes | TXT/XML |
| POA Exempt Codes | Present on Admission exclusions | TXT |
| Conversion Table | Previous year mappings | TXT |
| GEM Files | General Equivalence Mappings | TXT |

### 2.2 CPT Codes (Current Procedural Terminology)

**Source**: [AMA CPT Resources](https://www.ama-assn.org/practice-management/cpt/cpt-coding-resources)
**Verified**: December 19, 2025

```
Package: AMA CPT Code Set
Latest Version: CPT 2025 (effective January 1, 2025)
Update Frequency: Annual (January 1)
License: PROPRIETARY - AMA License Required
Maintenance: ACTIVE

Pros:
- Industry standard for procedures
- Comprehensive coverage
- Regular updates
- Category I, II, III codes

Cons:
- REQUIRES COMMERCIAL LICENSE
- License costs $10K-50K+ annually
- Cannot redistribute freely
- Strict usage restrictions

Security: No security concerns
Recommendation: LICENSE REQUIRED - Budget accordingly

Sources:
- Official: https://www.ama-assn.org/practice-management/cpt
- RVU Files: CMS MPFS downloads
- License: Contact AMA directly
```

**License Considerations**:
- **Internal Use License**: For claims processing systems
- **Data File License**: For importing code descriptions
- **API Integration**: May require separate agreements
- **Redistribution**: Strictly prohibited without agreement

### 2.3 HCPCS Level II Codes

**Source**: [CMS HCPCS](https://www.cms.gov/medicare/regulations-guidance/physician-self-referral/list-cpt-hcpcs-codes)
**Verified**: December 19, 2025

```
Package: CMS HCPCS Level II
Latest Version: 2025 (updated quarterly)
Update Frequency: Quarterly
License: Public Domain (US Government)
Maintenance: ACTIVE

Pros:
- Free to use
- Covers DME, ambulance, drugs
- Quarterly updates
- Supplements CPT codes

Cons:
- Less comprehensive than CPT
- Requires integration with CPT

Security: No security concerns
Recommendation: USE - Essential for complete procedure coverage

Sources:
- Official: https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system
- Downloads: https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system/hcpcs-quarterly-update
```

### 2.4 Python Libraries for Medical Coding

#### icd10-cm (PyPI)

```
Package: icd10-cm
Latest Version: Check PyPI
License: MIT
Maintenance: ACTIVE

Features:
- icd10.find("J20.0") - Find code details
- icd10.exists("J20.0") - Validate code exists
- Get description, chapter, block
- Check if code is billable

Pros:
- Simple API
- Free and open source
- Lightweight

Cons:
- ICD-10-CM only
- No CPT/HCPCS support
- Manual updates needed

Recommendation: USE for ICD-10 validation

Source: https://pypi.org/project/icd10-cm/
```

**Example Usage**:
```python
import icd10

# Validate and lookup ICD-10 code
code = icd10.find("J20.0")
if code:
    print(f"Code: {code.code}")
    print(f"Description: {code.description}")
    print(f"Billable: {code.billable}")
    print(f"Chapter: {code.chapter}")

# Check if code exists
if icd10.exists("J20.0"):
    print("Valid ICD-10 code")
```

#### hccpy (HCC Risk Adjustment)

```
Package: hccpy
Latest Version: 0.1.10 (April 2024)
License: Apache 2.0
Maintenance: ACTIVE

Features:
- HCC risk score calculation
- ICD-10 to HCC mapping
- CPT eligibility checking (requires AMA license)
- RAF score computation

Pros:
- Production-ready HCC implementation
- Risk adjustment calculations
- Well-documented

Cons:
- CPT data requires separate AMA license
- No ICD-9 support

Recommendation: USE for risk adjustment

Source: https://github.com/yubin-park/hccpy
```

---

## 3. Medical Necessity Validation

### 3.1 Overview of LCD/NCD System

**Source**: [CMS Medicare Coverage Database](https://www.cms.gov/medicare-coverage-database/search.aspx)
**Verified**: December 19, 2025

#### National Coverage Determinations (NCDs)

NCDs are **national policy** statements granting, limiting, or excluding Medicare coverage for specific medical items or services. They are developed by CMS through an evidence-based process and apply uniformly across all states.

**Key Characteristics**:
- Developed by CMS (not contractors)
- Apply nationwide
- Take precedence over LCDs
- Include coverage criteria, NOT billing codes
- Published in Medicare Coverage Database

#### Local Coverage Determinations (LCDs)

LCDs are **regional decisions** made by Medicare Administrative Contractors (MACs) determining whether a service is reasonable and necessary within their jurisdiction.

**Key Characteristics**:
- Developed by individual MACs
- Apply only within MAC jurisdiction
- Include ICD-10 codes linked to CPT/HCPCS
- Define medical necessity criteria
- More granular than NCDs

### 3.2 Coverage Database Access

**Source**: [MCD Downloads](https://www.cms.gov/medicare-coverage-database/downloads/downloads.aspx)
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

Recommendation: USE - Critical for medical necessity validation
```

**Data Structure**:
```yaml
LCD Example:
  lcd_id: "L35014"
  contractor_name: "Novitas Solutions"
  jurisdiction: ["JH", "JL"]
  title: "Magnetic Resonance Imaging (MRI)"

  covered_codes:
    cpt_codes: ["70551", "70552", "70553"]

  covered_diagnoses:
    icd10_codes:
      - code: "M54.2"
        description: "Cervicalgia"
      - code: "G89.29"
        description: "Other chronic pain"

  limitations:
    - "Prior authorization required for >3 MRIs/year"
    - "Must document conservative treatment failure"
```

### 3.3 Commercial Medical Necessity Systems

#### InterQual (Optum)

**Source**: [InterQual Criteria](https://business.optum.com/en/operations-technology/clinical-decision-support/interqual.html)
**Verified**: December 19, 2025

```
Package: InterQual Criteria
Vendor: Optum (UnitedHealth Group)
License: Commercial (Enterprise Agreement)
Maintenance: ACTIVE

Features:
- Level of care criteria
- Medical necessity validation
- Clinical decision support
- Cloud-based integration
- Real-time UM decisions

Pros:
- Industry-leading criteria
- Evidence-based (1,200+ expert panel)
- Comprehensive coverage
- Cloud integration available

Cons:
- EXPENSIVE (enterprise pricing)
- Requires vendor integration
- Vendor lock-in

Security: HIPAA compliant
Recommendation: CONSIDER for enterprise deployments

Sources:
- Official: https://business.optum.com/en/operations-technology/clinical-decision-support/interqual
- Overview: https://content.naic.org/sites/default/files/national_meeting/Optum%20Presentation_0.pdf
```

#### MCG Health (Hearst Health)

**Source**: [MCG Care Guidelines](https://www.mcg.com/)
**Verified**: December 19, 2025

```
Package: MCG Care Guidelines
Vendor: MCG Health (Hearst)
License: Commercial
Maintenance: ACTIVE

Features:
- Evidence-based guidelines
- Inpatient/outpatient criteria
- Recovery facility criteria
- Ambulatory care

Pros:
- Widely adopted
- Regular updates
- Comprehensive

Cons:
- Commercial license required
- Integration complexity

Recommendation: CONSIDER as InterQual alternative
```

### 3.4 Building Custom Medical Necessity Validation

For a custom implementation using CMS data:

```python
# services/medical_necessity/lcd_ncd_validator.py

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class CoverageDecision(str, Enum):
    COVERED = "covered"
    NOT_COVERED = "not_covered"
    REQUIRES_REVIEW = "requires_review"
    NO_LCD_NCD = "no_lcd_ncd"

@dataclass
class MedicalNecessityResult:
    decision: CoverageDecision
    lcd_id: Optional[str]
    ncd_id: Optional[str]
    covered_diagnoses: List[str]
    missing_diagnoses: List[str]
    limitations: List[str]
    rationale: str

class LCDNCDValidator:
    """
    Validates medical necessity against LCD/NCD criteria.

    Data sources:
    - CMS Medicare Coverage Database (LCD/NCD)
    - Contractor-specific billing articles
    """

    def __init__(self, coverage_db):
        self.coverage_db = coverage_db

    def validate(
        self,
        cpt_code: str,
        icd10_codes: List[str],
        mac_jurisdiction: str,
        place_of_service: str
    ) -> MedicalNecessityResult:
        """
        Check if procedure is medically necessary given diagnoses.

        Args:
            cpt_code: CPT/HCPCS procedure code
            icd10_codes: List of diagnosis codes
            mac_jurisdiction: MAC jurisdiction code (e.g., "JH")
            place_of_service: Place of service code

        Returns:
            MedicalNecessityResult with coverage decision
        """
        # 1. Check for NCD (national takes precedence)
        ncd = self.coverage_db.find_ncd(cpt_code)
        if ncd:
            return self._evaluate_coverage(ncd, icd10_codes)

        # 2. Check for LCD (regional)
        lcd = self.coverage_db.find_lcd(cpt_code, mac_jurisdiction)
        if lcd:
            return self._evaluate_coverage(lcd, icd10_codes)

        # 3. No LCD/NCD - general Medicare rules apply
        return MedicalNecessityResult(
            decision=CoverageDecision.NO_LCD_NCD,
            lcd_id=None,
            ncd_id=None,
            covered_diagnoses=[],
            missing_diagnoses=[],
            limitations=[],
            rationale="No specific LCD/NCD found. General Medicare coverage rules apply."
        )

    def _evaluate_coverage(
        self,
        coverage_determination,
        submitted_diagnoses: List[str]
    ) -> MedicalNecessityResult:
        """Evaluate submitted diagnoses against coverage criteria."""

        covered_codes = set(coverage_determination.covered_icd10_codes)
        submitted = set(submitted_diagnoses)

        # Find matching diagnoses
        matched = submitted & covered_codes
        missing = submitted - covered_codes

        if matched:
            decision = CoverageDecision.COVERED
            rationale = f"Diagnosis(es) {list(matched)} support medical necessity"
        elif missing:
            decision = CoverageDecision.NOT_COVERED
            rationale = "No submitted diagnosis matches LCD/NCD coverage criteria"
        else:
            decision = CoverageDecision.REQUIRES_REVIEW
            rationale = "Manual review required"

        return MedicalNecessityResult(
            decision=decision,
            lcd_id=getattr(coverage_determination, 'lcd_id', None),
            ncd_id=getattr(coverage_determination, 'ncd_id', None),
            covered_diagnoses=list(matched),
            missing_diagnoses=list(missing),
            limitations=coverage_determination.limitations,
            rationale=rationale
        )
```

---

## 4. Fraud, Waste, and Abuse (FWA) Detection

### 4.1 Industry Overview

**Sources**:
- [AI-Powered FWA Detection](https://medium.com/@adnanmasood/the-healthcare-payers-algorithm-vi-ai-powered-fraud-waste-and-abuse-fwa-detection-208c64622c22)
- [Healthcare Fraud Detection Research](https://www.mdpi.com/2078-2489/16/9/730)

**Verified**: December 19, 2025

### Economic Impact

| Metric | Value | Source |
|--------|-------|--------|
| Annual Healthcare Fraud (US) | $68 billion | NHCAA |
| % of Healthcare Expenditure | 3-10% | Industry estimates |
| Medicare/Medicaid Improper Payments | $31.46 billion (2022) | CMS |
| Potential AI Savings | $300 million+ | Industry projections |

### 4.2 Types of Healthcare Fraud

#### Upcoding

**Definition**: Assigning a higher-paying billing code than the service actually performed.

**Detection Signals**:
- E/M level distribution anomalies (excessive 99215 vs 99213)
- Procedure complexity vs documentation
- Provider pattern deviation from peers

**Example**:
```python
# Upcoding Detection Rule
class UpcodingDetector:
    """Detect potential upcoding patterns."""

    # Expected E/M distribution for primary care
    EXPECTED_EM_DISTRIBUTION = {
        "99211": 0.05,  # 5%
        "99212": 0.15,  # 15%
        "99213": 0.50,  # 50%
        "99214": 0.25,  # 25%
        "99215": 0.05   # 5%
    }

    def analyze_provider_pattern(self, provider_npi: str, claims: list) -> float:
        """
        Compare provider's E/M distribution to expected.
        Returns anomaly score (0-1, higher = more anomalous).
        """
        actual_dist = self._calculate_distribution(claims)

        # Chi-square test or KL divergence
        anomaly_score = self._calculate_divergence(
            actual_dist,
            self.EXPECTED_EM_DISTRIBUTION
        )

        return anomaly_score
```

#### Unbundling

**Definition**: Splitting a single procedure into separate components and billing each as distinct services.

**Detection Method**: NCCI Procedure-to-Procedure (PTP) edits

**Example Unbundling**:
- Billing 99213 + 99214 on same day (mutually exclusive)
- Billing component codes separately instead of comprehensive code
- Billing global period services separately

#### Duplicate Claims

**Definition**: Submitting the same claim multiple times, often with minor alterations.

**Detection Signals**:
- Same patient, provider, service date, procedure
- Minor variations (different modifiers, amounts)
- Sequential claim IDs

```python
# Duplicate Claim Detection
from hashlib import sha256

def generate_claim_fingerprint(claim: dict) -> str:
    """Generate unique fingerprint for duplicate detection."""
    key_fields = [
        claim.get("patient_id"),
        claim.get("provider_npi"),
        claim.get("service_date"),
        claim.get("cpt_code"),
        claim.get("diagnosis_codes", []),
        claim.get("units")
    ]

    fingerprint = sha256(
        str(key_fields).encode()
    ).hexdigest()

    return fingerprint

def detect_duplicates(claims: list) -> list:
    """Find potential duplicate claims."""
    fingerprints = {}
    duplicates = []

    for claim in claims:
        fp = generate_claim_fingerprint(claim)

        if fp in fingerprints:
            duplicates.append((
                fingerprints[fp]["claim_id"],
                claim["claim_id"]
            ))
        else:
            fingerprints[fp] = claim

    return duplicates
```

### 4.3 Machine Learning Approaches

**Source**: [ML in Healthcare Fraud Detection Survey](https://journalofbigdata.springeropen.com/articles/10.1186/s40537-025-01295-3)
**Verified**: December 19, 2025

#### Recommended ML Techniques

| Technique | Use Case | Pros | Cons |
|-----------|----------|------|------|
| **Isolation Forest** | Anomaly detection | Fast, handles high dimensions | Hard to interpret |
| **Local Outlier Factor** | Provider outlier detection | Good for local anomalies | Sensitive to parameters |
| **Autoencoders** | Pattern anomaly | Learns complex patterns | Requires training data |
| **Random Forest** | Classification | Interpretable, robust | Needs labeled data |
| **XGBoost** | Classification | High accuracy | Needs labeled data |
| **Graph Neural Networks** | Network fraud | Detects collusion | Complex implementation |

#### Feature Engineering for FWA

```python
# features/fwa_feature_engineering.py

from dataclasses import dataclass
import numpy as np

@dataclass
class FWAFeatures:
    """Features for FWA machine learning models."""

    # Provider-level features
    provider_claim_count: int
    provider_avg_charge: float
    provider_unique_patients: int
    provider_unique_diagnoses: int
    provider_specialty_avg_deviation: float

    # Claim-level features
    charge_amount: float
    units_billed: int
    diagnosis_count: int
    procedure_count: int
    service_duration_days: int

    # Pattern features
    weekend_service_flag: bool
    after_hours_flag: bool
    same_day_procedures_count: int
    modifier_count: int

    # Network features
    out_of_network_flag: bool
    distance_to_provider_miles: float

    # Historical features
    prior_denial_rate: float
    prior_adjustment_rate: float
    appeal_rate: float
```

#### Model Implementation

```python
# models/fwa_detector.py

from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
import numpy as np

class FWADetector:
    """
    Fraud, Waste, and Abuse detection using ensemble methods.

    Combines multiple anomaly detection algorithms for robust detection.
    """

    def __init__(self, contamination: float = 0.05):
        self.contamination = contamination
        self.scaler = StandardScaler()

        # Ensemble of detectors
        self.detectors = {
            "isolation_forest": IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=100
            ),
            "lof": LocalOutlierFactor(
                contamination=contamination,
                novelty=True,
                n_neighbors=20
            )
        }

        self.is_fitted = False

    def fit(self, X: np.ndarray):
        """Fit detectors on training data (normal claims)."""
        X_scaled = self.scaler.fit_transform(X)

        for name, detector in self.detectors.items():
            detector.fit(X_scaled)

        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict anomaly scores for claims.

        Returns:
            Array of anomaly scores (higher = more anomalous)
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")

        X_scaled = self.scaler.transform(X)

        # Get predictions from each detector
        scores = []
        for name, detector in self.detectors.items():
            if hasattr(detector, "decision_function"):
                raw_scores = -detector.decision_function(X_scaled)
            else:
                raw_scores = -detector.score_samples(X_scaled)

            # Normalize to 0-1
            normalized = (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-10)
            scores.append(normalized)

        # Ensemble average
        ensemble_scores = np.mean(scores, axis=0)

        return ensemble_scores

    def flag_suspicious(self, X: np.ndarray, threshold: float = 0.7) -> np.ndarray:
        """Flag claims above anomaly threshold."""
        scores = self.predict(X)
        return scores > threshold
```

### 4.4 Pre-Payment vs Post-Payment Detection

**Source**: [Launch Consulting FWA Article](https://www.launchconsulting.com/posts/how-ai-enabled-fraud-waste-and-abuse-detection-can-put-an-end-to-pay-and-chase)
**Verified**: December 19, 2025

| Approach | Timing | Pros | Cons |
|----------|--------|------|------|
| **Pre-Payment** | Before payment | Prevents losses, real-time | May delay legitimate claims |
| **Post-Payment** | After payment | Complete data, no delays | Recovery is difficult |
| **Hybrid** | Both | Best of both | Complex implementation |

**Recommendation**: Implement **hybrid approach** with:
- Pre-payment rules for known fraud patterns
- Post-payment ML for complex pattern detection

---

## 5. X12 EDI Claims Processing

### 5.1 Transaction Standards

**Source**: [HIPAA EDI Standards](https://www.cigna.com/health-care-providers/coverage-and-claims/hipaa-compliance-standards)
**Verified**: December 19, 2025

| Transaction | X12 Code | Purpose |
|-------------|----------|---------|
| Professional Claim | 837P | CMS-1500 claims |
| Institutional Claim | 837I | UB-04 claims |
| Remittance Advice | 835 | Payment explanation |
| Eligibility Inquiry | 270 | Coverage check request |
| Eligibility Response | 271 | Coverage check response |
| Claim Status Inquiry | 276 | Claim status request |
| Claim Status Response | 277 | Claim status response |

### 5.2 Python Libraries for X12 EDI

#### x12-edi-tools

```
Package: x12-edi-tools
Latest Version: 0.1.2 (July 30, 2024)
License: MIT
Maintenance: ACTIVE

Features:
- Parse 837 (claims) and 835 (remittance)
- 270/271 eligibility support
- JSON/CSV conversion

Pros:
- MIT license
- Active development
- Multiple format support

Cons:
- Newer library
- Smaller community

Recommendation: CONSIDER for new implementations

Source: https://pypi.org/project/x12-edi-tools/
```

#### Databricks X12 EDI Parser

```
Package: Databricks X12 EDI Ember
Latest Version: Active development
License: Databricks
Maintenance: ACTIVE

Features:
- Enterprise-grade parsing
- 837i/837p, 835, 834 support
- Spark integration
- Scalable architecture

Pros:
- Production-ready
- Handles large volumes
- Modular design

Cons:
- Databricks dependency
- Enterprise focus

Recommendation: USE for enterprise scale

Source: https://github.com/databricks-industry-solutions/x12-edi-parser
```

### 5.3 X12 837 Claim Structure

```
+-------------------------------------------------------------+
|                    X12 837P Structure                        |
+-------------------------------------------------------------+
| ISA - Interchange Control Header                            |
|   GS - Functional Group Header                              |
|     ST - Transaction Set Header (837)                       |
|       BHT - Beginning of Hierarchical Transaction           |
|       +-- 1000A - Submitter Name                            |
|       +-- 1000B - Receiver Name                             |
|       +-- 2000A - Billing Provider Hierarchy                |
|       |   +-- 2010AA - Billing Provider Name                |
|       |   +-- 2010AB - Pay-to Address                       |
|       +-- 2000B - Subscriber Hierarchy                      |
|       |   +-- 2010BA - Subscriber Name                      |
|       |   +-- 2010BB - Payer Name                           |
|       |   +-- 2300 - Claim Information                      |
|       |       +-- CLM - Claim Details                       |
|       |       +-- DTP - Service Dates                       |
|       |       +-- HI - Diagnosis Codes                      |
|       |       +-- 2400 - Service Lines                      |
|       |           +-- SV1 - Professional Service            |
|       |           +-- DTP - Service Date                    |
|       |           +-- REF - Line Reference                  |
|     SE - Transaction Set Trailer                            |
|   GE - Functional Group Trailer                             |
| IEA - Interchange Control Trailer                           |
+-------------------------------------------------------------+
```

---

## 6. Document Processing (OCR/NLP)

### 6.1 OCR Solutions Comparison

**Sources**:
- [Amazon Textract](https://aws.amazon.com/textract/)
- [OCR Benchmarking Study](https://link.springer.com/article/10.1007/s42001-021-00149-1)

**Verified**: December 19, 2025

| Solution | Accuracy | Speed | HIPAA | Cost |
|----------|----------|-------|-------|------|
| **Amazon Textract** | High | 10-15s/page | Eligible | $1.50-70/1K pages |
| **Google Document AI** | Highest | 10-15s/page | Compliant | Similar |
| **Azure Document Intelligence** | High | 10-15s/page | Compliant | Similar |
| **Tesseract** | Medium | 2-17s/page | N/A (self-hosted) | Free |
| **PaddleOCR** | High | Fast | N/A (self-hosted) | Free |

### 6.2 Amazon Textract for Healthcare

```
Package: Amazon Textract
HIPAA: ELIGIBLE (since 2018)
Compliance: SOC, ISO, PCI, GDPR

Features:
- Form extraction
- Table extraction
- Query-based extraction
- Medical document support

Pros:
- HIPAA eligible
- High accuracy
- AWS integration
- Lambda integration

Cons:
- Cloud-dependent
- Per-page pricing
- Latency for batches

Recommendation: USE for medical document processing

Sources:
- Official: https://aws.amazon.com/textract/
- HIPAA: https://aws.amazon.com/blogs/machine-learning/amazon-textract-is-now-hipaa-eligible/
- Healthcare: https://aws.amazon.com/blogs/industries/automating-claims-adjudication-workflows-using-amazon-textract-and-amazon-comprehend-medical/
```

### 6.3 Claims Document Processing Pipeline

```
+-------------------------------------------------------------+
|              Document Processing Pipeline                    |
+-------------------------------------------------------------+
|                                                              |
|  +----------+    +----------+    +----------+    +--------+  |
|  | Document |--->|   OCR    |--->|   NLP    |--->| Struct |  |
|  |  Upload  |    | Extract  |    | Extract  |    |  Data  |  |
|  +----------+    +----------+    +----------+    +--------+  |
|       |              |               |               |       |
|       v              v               v               v       |
|  +----------+  +----------+  +----------+  +------------+   |
|  |  Format  |  |   Raw    |  | Entities |  |   Claim    |   |
|  |Detection |  |   Text   |  |  Codes   |  |   Object   |   |
|  +----------+  +----------+  +----------+  +------------+   |
|                                                              |
|  Supported Formats:                                         |
|  - PDF (scanned & native)                                   |
|  - Images (PNG, JPG, TIFF)                                  |
|  - CMS-1500, UB-04 forms                                    |
|  - EOBs, Superbills                                         |
|                                                              |
+-------------------------------------------------------------+
```

---

## 7. HIPAA Compliance Requirements

### 7.1 Security Safeguards

**Source**: [HHS HIPAA](https://www.hhs.gov/hipaa/index.html)
**Verified**: December 19, 2025

| Category | Requirements |
|----------|--------------|
| **Administrative** | Security policies, workforce training, risk analysis |
| **Physical** | Facility access controls, workstation security |
| **Technical** | Access control, encryption, audit logs, integrity controls |

### 7.2 Technical Requirements Checklist

```yaml
# HIPAA Technical Requirements for Claims Processing

encryption:
  at_rest:
    algorithm: "AES-256"
    key_management: "AWS KMS / Azure Key Vault / HashiCorp Vault"
  in_transit:
    protocol: "TLS 1.3"
    certificate: "SHA-256 minimum"

access_control:
  authentication:
    method: "Multi-Factor Authentication (MFA)"
    password_policy: "NIST SP 800-63B compliant"
  authorization:
    model: "Role-Based Access Control (RBAC)"
    principle: "Least Privilege"
  session:
    timeout: "15 minutes inactivity"
    concurrent: "Limited per user"

audit_logging:
  events:
    - "All PHI access"
    - "Authentication attempts"
    - "Authorization changes"
    - "Data exports"
  retention: "6 years minimum"
  integrity: "Tamper-evident logging"

data_integrity:
  backup:
    frequency: "Daily minimum"
    retention: "Per organization policy"
    testing: "Quarterly restore tests"
  validation:
    checksums: "Required for PHI transfers"

breach_notification:
  timeline: "60 days to HHS"
  requirements: "HIPAA Breach Notification Rule"
```

### 7.3 Business Associate Agreements (BAAs)

Required BAAs for claims processing:
- Cloud providers (AWS, Azure, GCP)
- OCR/Document processing services
- ML/AI service providers
- Data analytics platforms
- Clearinghouse connections

---

## 8. Architecture Recommendation

### 8.1 Complete System Architecture

```
+------------------------------------------------------------------------------+
|                    CLAIMS ADJUDICATION ENGINE ARCHITECTURE                    |
+------------------------------------------------------------------------------+
|                                                                               |
|  +-------------------------------------------------------------------------+ |
|  |                         INGESTION LAYER                                  | |
|  |  +-----------+  +-----------+  +-----------+  +-----------+             | |
|  |  |  X12 837  |  |  FHIR API |  |  Document |  |  Manual   |             | |
|  |  |  Parser   |  |  Claims   |  |  Upload   |  |  Entry    |             | |
|  |  +-----+-----+  +-----+-----+  +-----+-----+  +-----+-----+             | |
|  +---------+-------------+-------------+-------------+-----------------------+ |
|            |             |             |             |                        |
|            +-------------+-------------+-------------+                        |
|                                  |                                            |
|                                  v                                            |
|  +-------------------------------------------------------------------------+ |
|  |                       DOCUMENT PROCESSING                                | |
|  |  +-----------+  +-----------+  +-----------+                            | |
|  |  |  Amazon   |  |  Medical  |  |  Data     |                            | |
|  |  |  Textract |->|  NLP      |->|  Extract  |                            | |
|  |  |  OCR      |  |  (LLM)    |  |           |                            | |
|  |  +-----------+  +-----------+  +-----------+                            | |
|  +-------------------------------------------------------------------------+ |
|                                  |                                            |
|                                  v                                            |
|  +-------------------------------------------------------------------------+ |
|  |                      VALIDATION ENGINE                                   | |
|  |  +----------------+ +----------------+ +----------------------+          | |
|  |  | CODE VALIDATION| |MEDICAL NECESS. | |   COVERAGE CHECK     |          | |
|  |  | - ICD-10       | | - LCD/NCD      | |   - Policy/TOB       |          | |
|  |  | - CPT/HCPCS    | | - InterQual    | |   - Network Status   |          | |
|  |  | - NCCI Edits   | | - Clinical     | |   - Prior Auth       |          | |
|  |  | - MUE Limits   | |   Notes        | |                      |          | |
|  |  | - Age/Gender   | |                | |                      |          | |
|  |  +----------------+ +----------------+ +----------------------+          | |
|  +-------------------------------------------------------------------------+ |
|                                  |                                            |
|                                  v                                            |
|  +-------------------------------------------------------------------------+ |
|  |                        FWA DETECTION ENGINE                              | |
|  |  +-----------+ +-----------+ +-----------+ +---------------+            | |
|  |  |  Upcoding | | Unbundling| |  Duplicate| |   Anomaly     |            | |
|  |  |  Detection| |  Detection| |  Detection| |   Detection   |            | |
|  |  |  (Rules)  | |  (NCCI)   | |  (Hash)   | |   (ML Models) |            | |
|  |  +-----------+ +-----------+ +-----------+ +---------------+            | |
|  +-------------------------------------------------------------------------+ |
|                                  |                                            |
|                                  v                                            |
|  +-------------------------------------------------------------------------+ |
|  |                      ADJUDICATION ENGINE                                 | |
|  |  +-------------+ +-------------+ +-----------------------------+        | |
|  |  |   PRICING   | |   BENEFITS  | |      DECISION ENGINE        |        | |
|  |  |   ENGINE    | |   ENGINE    | |  - Auto-Adjudicate (80%+)   |        | |
|  |  |   - Fee Sch | |   - Deduct  | |  - Pend for Review          |        | |
|  |  |   - Contract| |   - Copay   | |  - Deny with Reason         |        | |
|  |  |   - Discount| |   - Coinsur | |  - Request Info             |        | |
|  |  +-------------+ +-------------+ +-----------------------------+        | |
|  +-------------------------------------------------------------------------+ |
|                                  |                                            |
|                                  v                                            |
|  +-------------------------------------------------------------------------+ |
|  |                   ANALYTICS & REPORTING                                  | |
|  |     Trends | FWA Dashboards | Audit Trails | Compliance Reports          | |
|  +-------------------------------------------------------------------------+ |
|                                                                               |
+-------------------------------------------------------------------------------+
|                              DATA LAYER                                       |
|  +-------------+ +-------------+ +-------------+ +-------------+             |
|  |  PostgreSQL | |  Typesense  | |  Redis      | |  S3/Blob    |             |
|  |  - Claims   | |  - ICD-10   | |  - Cache    | |  - Documents|             |
|  |  - Policies | |  - CPT/HCPCS| |  - Sessions | |  - Attachmts|             |
|  |  - Providers| |  - NCCI     | |  - Rate Lim | |  - Audit Log|             |
|  |  - Audit Log| |  - Providers| |             | |             |             |
|  +-------------+ +-------------+ +-------------+ +-------------+             |
+------------------------------------------------------------------------------+
```

### 8.2 Technology Stack Recommendation

| Layer | Technology | Reason |
|-------|------------|--------|
| **Backend** | FastAPI (Python) | Async, OpenAPI, typing |
| **Database** | PostgreSQL + TimescaleDB | Relational + time-series |
| **Search** | Typesense | Sub-50ms, typo-tolerance |
| **Cache** | Redis/Dragonfly | HIPAA-eligible, sub-ms |
| **ML/AI** | Scikit-learn + PyTorch | Industry standard |
| **OCR** | Amazon Textract | HIPAA-eligible |
| **Queue** | Celery + Redis | Async processing |
| **API Gateway** | Kong/AWS API Gateway | Rate limiting, auth |
| **Frontend** | Angular | Enterprise-ready |

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Set up HIPAA-compliant infrastructure
- [ ] Implement X12 837/835 parsing
- [ ] Import CMS ICD-10 and HCPCS data
- [ ] Import NCCI edits and MUE limits
- [ ] Set up Typesense search

### Phase 2: Code Validation (Weeks 3-4)
- [ ] ICD-10 code validation
- [ ] CPT/HCPCS validation (with AMA license)
- [ ] NCCI edit checking
- [ ] MUE limit validation
- [ ] Age/gender validation

### Phase 3: Medical Necessity (Weeks 5-6)
- [ ] Import LCD/NCD data from CMS
- [ ] Build diagnosis-procedure crosswalk
- [ ] Implement medical necessity validation
- [ ] Optional: InterQual/MCG integration

### Phase 4: FWA Detection (Weeks 7-8)
- [ ] Implement rules-based fraud detection
- [ ] Build ML anomaly detection models
- [ ] Duplicate claim detection
- [ ] Upcoding/unbundling detection

### Phase 5: Adjudication Engine (Weeks 9-10)
- [ ] Pricing engine integration
- [ ] Benefits calculation
- [ ] Auto-adjudication rules
- [ ] Exception queue management

### Phase 6: Analytics & Polish (Weeks 11-12)
- [ ] Dashboard implementation
- [ ] Trend analytics
- [ ] Audit trail system
- [ ] Performance optimization
- [ ] Load testing

---

## 10. Evidence Citations

### Official Sources

| Resource | URL | Accessed |
|----------|-----|----------|
| CMS ICD-10 | https://www.cms.gov/medicare/coding-billing/icd-10-codes | Dec 19, 2025 |
| CMS HCPCS | https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system | Dec 19, 2025 |
| CMS NCCI | https://www.cms.gov/national-correct-coding-initiative-ncci | Dec 19, 2025 |
| Medicare Coverage DB | https://www.cms.gov/medicare-coverage-database/search.aspx | Dec 19, 2025 |
| AMA CPT | https://www.ama-assn.org/practice-management/cpt | Dec 19, 2025 |
| HHS HIPAA | https://www.hhs.gov/hipaa/index.html | Dec 19, 2025 |

### Technology Sources

| Package | URL | Version |
|---------|-----|---------|
| icd10-cm | https://pypi.org/project/icd10-cm/ | Latest |
| hccpy | https://github.com/yubin-park/hccpy | 0.1.10 |
| x12-edi-tools | https://pypi.org/project/x12-edi-tools/ | 0.1.2 |
| fhir.resources | https://pypi.org/project/fhir.resources/ | 8.0.0 |
| Databricks X12 | https://github.com/databricks-industry-solutions/x12-edi-parser | Active |
| Amazon Textract | https://aws.amazon.com/textract/ | Current |

### Research References

| Topic | Source |
|-------|--------|
| AI-Powered FWA | https://medium.com/@adnanmasood/the-healthcare-payers-algorithm-vi-ai-powered-fraud-waste-and-abuse-fwa-detection-208c64622c22 |
| ML Healthcare Fraud | https://www.mdpi.com/2078-2489/16/9/730 |
| Healthcare Fraud Survey | https://journalofbigdata.springeropen.com/articles/10.1186/s40537-025-01295-3 |
| InterQual | https://business.optum.com/en/operations-technology/clinical-decision-support/interqual |
| AWS Claims Adjudication | https://aws.amazon.com/blogs/industries/automating-claims-adjudication-workflows-using-amazon-textract-and-amazon-comprehend-medical/ |
| HIPAA Software Dev | https://www.cabotsolutions.com/blog/hipaa-compliant-software-development-checklist-2024 |

---

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| AMA CPT license cost | High | Medium | Budget $10K-50K/year |
| LCD/NCD data complexity | High | High | Incremental implementation |
| False positives in FWA | Medium | High | Human review queue, tunable thresholds |
| HIPAA breach | Low | Critical | SOC 2, encryption, access controls, BAAs |
| True 100% automation | High | Medium | Set realistic target (80-90% auto-adjudication) |
| Regulatory changes | Medium | Medium | Flexible rules engine, quarterly updates |
| ML model drift | Medium | Medium | Continuous monitoring, retraining pipeline |

---

## 12. Recommendations Summary

### BUILD vs BUY Matrix

| Component | Recommendation | Rationale |
|-----------|----------------|-----------|
| ICD-10/HCPCS Validation | BUILD | Free CMS data, simple logic |
| CPT Validation | LICENSE + BUILD | AMA license required |
| NCCI/MUE Validation | BUILD | Free CMS data |
| Medical Necessity | HYBRID | Build from LCD/NCD, consider InterQual for complex |
| FWA Detection | BUILD | Custom ML models for your data |
| Claims Parsing | BUILD | Open source libraries available |
| Document OCR | BUY | Amazon Textract (HIPAA-eligible) |
| Analytics | BUILD | Custom dashboards |

### Key Success Factors

1. **Start with rules-based validation** before ML
2. **Budget for AMA CPT license** (~$10K-50K/year)
3. **Plan for 80-90% auto-adjudication** (not 100%)
4. **Build exception queues** for edge cases
5. **Quarterly updates** for CMS code files
6. **Continuous ML model monitoring** for drift

---

**Document Version**: 1.0
**Last Updated**: December 19, 2025
**Status**: Research Complete - Ready for Implementation
