# Claims Adjudication Engine - Extended Design Document

**Design Date**: December 19, 2025
**Feature**: Full Claims Adjudication Engine with FWA Detection, Medical Necessity, Auto-Adjudication
**Author**: Claude Code (AI Assistant)
**Status**: DRAFT - Pending Review
**Base Design**: [04_validation_engine_comprehensive_design.md](04_validation_engine_comprehensive_design.md)
**Research Reference**: [06_claims_adjudication_fwa_research.md](../research/06_claims_adjudication_fwa_research.md)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Gap Analysis](#2-gap-analysis)
3. [Extended Architecture](#3-extended-architecture)
4. [New Component Designs](#4-new-component-designs)
5. [Enhanced Validation Rules](#5-enhanced-validation-rules)
6. [API Contracts (Extended)](#6-api-contracts-extended)
7. [Data Models](#7-data-models)
8. [Technology Additions](#8-technology-additions)
9. [Security & Compliance](#9-security--compliance)
10. [Implementation Phases](#10-implementation-phases)
11. [Risk Register](#11-risk-register)
12. [Open Questions for Review](#12-open-questions-for-review)

---

## 1. Executive Summary

### 1.1 Purpose

This document **extends** the approved design document (04) to add capabilities for a **100% Automated Claims Adjudication Engine**. The extensions cover:

1. **X12 EDI Integration** - Native claims intake via 837P/837I
2. **LCD/NCD Medical Necessity** - CMS coverage database validation
3. **ML-based FWA Detection** - Advanced anomaly detection
4. **Auto-Adjudication Engine** - Pricing, benefits, and decision automation
5. **HCC Risk Adjustment** - Risk scoring for value-based care
6. **Trends Analytics** - Dashboards and audit capabilities

### 1.2 Key Additions to Original Design

| Addition | Impact | Priority |
|----------|--------|----------|
| X12 EDI Parser | New ingestion pathway | P0 |
| LCD/NCD Validator | Enhances Rule 5 | P0 |
| ML FWA Detector | Enhances Rule 3 | P1 |
| Pricing Engine | New component | P0 |
| Benefits Engine | New component | P0 |
| Auto-Adjudication | New component | P0 |
| HCC Risk Scoring | New feature | P1 |
| Analytics Dashboard | New component | P2 |
| CPT License Budget | Business requirement | P0 |

### 1.3 Target Automation Rate

> **Goal**: 80-90% auto-adjudication rate for clean claims

| Claim Type | Target Auto-Adjudication |
|------------|-------------------------|
| Professional (837P) | 85% |
| Institutional (837I) | 80% |
| DME/Ambulance | 75% |
| Complex/Exception | Manual review |

---

## 2. Gap Analysis

### 2.1 Capabilities Comparison

| Capability | Design Doc 04 | Research Doc 06 | Status |
|-----------|--------------|-----------------|--------|
| 13 Validation Rules | YES | YES | Covered |
| Sub-50ms Search | YES | YES | Covered |
| PDF Fraud Detection | YES | Enhanced with ML | **EXTEND** |
| LLM Extraction | YES | YES | Covered |
| Medical Necessity | Rule 5 (LLM) | LCD/NCD + LLM | **EXTEND** |
| X12 EDI Parsing | NO | YES | **ADD** |
| Claims Adjudication | OUT OF SCOPE | YES | **ADD** |
| Pricing Engine | NO | YES | **ADD** |
| Benefits Calculation | NO | YES | **ADD** |
| HCC Risk Scoring | NO | YES | **ADD** |
| Trends Analytics | NO | YES | **ADD** |
| CPT Licensing | Not addressed | Required | **ADD** |

### 2.2 New Validation Rules

Extending the original 13 rules:

| Rule # | Name | Type | Description |
|--------|------|------|-------------|
| 13 | MUE Limit Validation | Extended | Medically Unlikely Edits (already in 05) |
| 14 | LCD Medical Necessity | **NEW** | Local Coverage Determination validation |
| 15 | NCD Medical Necessity | **NEW** | National Coverage Determination validation |
| 16 | Duplicate Claim Detection | **NEW** | Fingerprint-based duplicate detection |
| 17 | Upcoding Detection | **NEW** | E/M distribution analysis |
| 18 | Unbundling Detection | **NEW** | NCCI PTP edit validation |
| 19 | HCC Risk Validation | **NEW** | Risk adjustment accuracy check |

---

## 3. Extended Architecture

### 3.1 Complete System Architecture

```
+==============================================================================+
|                    CLAIMS ADJUDICATION ENGINE - FULL ARCHITECTURE            |
+==============================================================================+
|                                                                               |
|  +-----------------------------------------------------------------------+   |
|  |                         INGESTION LAYER                                |   |
|  |  +-------------+ +-------------+ +-------------+ +-------------+       |   |
|  |  |   X12 837   | |   FHIR R4   | |  Document   | |   Manual    |       |   |
|  |  |   Parser    | |   API       | |   Upload    | |   Entry     |       |   |
|  |  | (837P/837I) | |   Claims    | |   (OCR)     | |   UI        |       |   |
|  |  +------+------+ +------+------+ +------+------+ +------+------+       |   |
|  +---------|---------------|---------------|---------------|-------------+   |
|            |               |               |               |                 |
|            +---------------+-------+-------+---------------+                 |
|                                    |                                         |
|                                    v                                         |
|  +-----------------------------------------------------------------------+   |
|  |                    CLAIMS NORMALIZATION SERVICE                        |   |
|  |  - Unified claim model regardless of source                            |   |
|  |  - Code standardization (ICD-10, CPT, HCPCS)                          |   |
|  |  - Data enrichment (provider lookup, member verification)             |   |
|  +-----------------------------------------------------------------------+   |
|                                    |                                         |
|                                    v                                         |
|  +-----------------------------------------------------------------------+   |
|  |                    VALIDATION ENGINE (Extended)                        |   |
|  |  +------------------+  +------------------+  +--------------------+    |   |
|  |  | EXTRACTION RULES |  | MEDICAL RULES    |  | COVERAGE RULES     |    |   |
|  |  | (Rules 1-2)      |  | (Rules 4-10)     |  | (Rules 11-12)      |    |   |
|  |  +------------------+  +------------------+  +--------------------+    |   |
|  |  +------------------+  +------------------+  +--------------------+    |   |
|  |  | FRAUD RULES      |  | LCD/NCD RULES    |  | FWA ML RULES       |    |   |
|  |  | (Rule 3)         |  | (Rules 14-15)    |  | (Rules 16-18)      |    |   |
|  |  | + ML Detection   |  | + NEW            |  | + NEW              |    |   |
|  |  +------------------+  +------------------+  +--------------------+    |   |
|  +-----------------------------------------------------------------------+   |
|                                    |                                         |
|                                    v                                         |
|  +-----------------------------------------------------------------------+   |
|  |                    ADJUDICATION ENGINE (NEW)                           |   |
|  |  +------------------+  +------------------+  +--------------------+    |   |
|  |  | PRICING ENGINE   |  | BENEFITS ENGINE  |  | DECISION ENGINE    |    |   |
|  |  | - Fee schedules  |  | - Deductible     |  | - Auto-adjudicate  |    |   |
|  |  | - Contracts      |  | - Copay          |  | - Pend for review  |    |   |
|  |  | - Discounts      |  | - Coinsurance    |  | - Deny with reason |    |   |
|  |  | - Global periods |  | - OOP Max        |  | - Request info     |    |   |
|  |  +------------------+  +------------------+  +--------------------+    |   |
|  +-----------------------------------------------------------------------+   |
|                                    |                                         |
|                                    v                                         |
|  +-----------------------------------------------------------------------+   |
|  |                    OUTPUT & ANALYTICS (NEW)                            |   |
|  |  +------------------+  +------------------+  +--------------------+    |   |
|  |  | X12 835          |  | FHIR ExplanationOf|  | ANALYTICS          |    |   |
|  |  | Remittance       |  | Benefit          |  | DASHBOARD          |    |   |
|  |  | Generator        |  |                  |  | - FWA trends       |    |   |
|  |  |                  |  |                  |  | - Provider scores  |    |   |
|  |  |                  |  |                  |  | - Audit trails     |    |   |
|  |  +------------------+  +------------------+  +--------------------+    |   |
|  +-----------------------------------------------------------------------+   |
|                                                                               |
+===============================================================================+
|                              DATA LAYER                                       |
|  +-------------+ +-------------+ +-------------+ +-------------+             |
|  |  PostgreSQL | |  Typesense  | |  Redis      | |  S3/Blob    |             |
|  |  - Claims   | |  - ICD-10   | |  - Cache    | |  - Documents|             |
|  |  - Policies | |  - CPT      | |  - Sessions | |  - EDI Files|             |
|  |  - Adjudic. | |  - LCD/NCD  | |  - ML Model | |  - Audit    |             |
|  |  - Contracts| |  - NCCI     | |    Results  | |             |             |
|  +-------------+ +-------------+ +-------------+ +-------------+             |
+===============================================================================+
```

### 3.2 Data Flow: End-to-End Claim Processing

```
Claim Submission (Any Source)
         |
         v
+---------------------+
| INGESTION           |
| - X12 837 Parser    |
| - FHIR Receiver     |
| - Document OCR      |
| - Manual Entry      |
+----------+----------+
           |
           v
+---------------------+
| NORMALIZATION       |
| - Unified Model     |
| - Code Validation   |
| - Data Enrichment   |
+----------+----------+
           |
           v
+---------------------+     +-------------------+
| ELIGIBILITY CHECK   |---->| 270/271 Service   |
| - Member active?    |     | (Real-time)       |
| - Policy in force?  |     +-------------------+
| - Coverage dates?   |
+----------+----------+
           |
           v
+---------------------+
| VALIDATION ENGINE   |      Rules 1-19
| - Fraud Detection   |<---> Typesense
| - Code Validation   |<---> Redis Cache
| - Medical Necessity |<---> LLM Gateway
| - LCD/NCD Check     |<---> CMS Database
| - FWA ML Detection  |<---> ML Models
+----------+----------+
           |
     +-----+-----+
     |           |
  VALID       INVALID
     |           |
     v           v
+--------+  +--------+
| ADJUD- |  | REJECT |
| ICATION|  | QUEUE  |
+---+----+  +--------+
    |
    +---------------------+
    |                     |
AUTO-ADJUDICATE    PEND FOR REVIEW
    |                     |
    v                     v
+--------+          +--------+
| PRICE  |          | MANUAL |
| CLAIM  |          | QUEUE  |
+---+----+          +--------+
    |
    v
+---------------------+
| CALCULATE BENEFITS  |
| - Apply deductible  |
| - Apply copay       |
| - Apply coinsurance |
| - Check OOP max     |
+----------+----------+
           |
           v
+---------------------+
| GENERATE OUTPUT     |
| - X12 835 Remittance|
| - EOB Document      |
| - FHIR Response     |
+----------+----------+
           |
           v
+---------------------+
| ANALYTICS & AUDIT   |
| - Log all decisions |
| - Update dashboards |
| - Generate reports  |
+---------------------+
```

---

## 4. New Component Designs

### 4.1 X12 EDI Integration Service

**Purpose**: Parse incoming X12 837 claims and generate X12 835 remittances.

```python
# src/services/edi/x12_parser.py

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class TransactionType(str, Enum):
    CLAIM_837P = "837P"    # Professional
    CLAIM_837I = "837I"    # Institutional
    REMIT_835 = "835"      # Remittance
    ELIG_270 = "270"       # Eligibility Request
    ELIG_271 = "271"       # Eligibility Response

@dataclass
class X12Segment:
    """Represents a single X12 segment."""
    segment_id: str
    elements: List[str]

@dataclass
class X12Transaction:
    """Parsed X12 transaction."""
    transaction_type: TransactionType
    control_number: str
    sender_id: str
    receiver_id: str
    segments: List[X12Segment]

@dataclass
class ParsedClaim837:
    """Normalized claim data from 837."""
    # Header
    transaction_control_number: str
    submitter_name: str
    receiver_name: str

    # Billing Provider (Loop 2010AA)
    billing_provider_npi: str
    billing_provider_name: str
    billing_provider_address: dict
    billing_provider_taxonomy: str

    # Subscriber (Loop 2010BA)
    subscriber_id: str
    subscriber_name: str
    subscriber_dob: str
    subscriber_gender: str
    payer_name: str
    payer_id: str

    # Claim (Loop 2300)
    claim_id: str
    total_charge: float
    place_of_service: str
    admission_date: Optional[str]
    discharge_date: Optional[str]

    # Diagnoses (Loop 2300 HI segments)
    principal_diagnosis: str
    other_diagnoses: List[str]

    # Service Lines (Loop 2400)
    service_lines: List[dict]

class X12ParserService:
    """
    Service for parsing X12 EDI transactions.

    Supports:
    - 837P (Professional Claims)
    - 837I (Institutional Claims)
    - 835 (Remittance Advice)
    - 270/271 (Eligibility)
    """

    def __init__(self, config: dict):
        self.delimiter = config.get("element_delimiter", "*")
        self.segment_terminator = config.get("segment_terminator", "~")

    def parse_837(self, edi_content: str) -> ParsedClaim837:
        """Parse 837P or 837I claim into normalized model."""
        segments = self._tokenize(edi_content)

        # Determine transaction type from ST segment
        transaction_type = self._get_transaction_type(segments)

        if transaction_type == TransactionType.CLAIM_837P:
            return self._parse_837p(segments)
        elif transaction_type == TransactionType.CLAIM_837I:
            return self._parse_837i(segments)
        else:
            raise ValueError(f"Unsupported transaction type: {transaction_type}")

    def generate_835(self, adjudication_result: dict) -> str:
        """Generate X12 835 remittance advice from adjudication result."""
        segments = []

        # ISA - Interchange Control Header
        segments.append(self._build_isa_segment(adjudication_result))

        # GS - Functional Group Header
        segments.append(self._build_gs_segment(adjudication_result))

        # ST - Transaction Set Header
        segments.append(f"ST*835*0001")

        # BPR - Financial Information
        segments.append(self._build_bpr_segment(adjudication_result))

        # TRN - Reassociation Trace Number
        segments.append(self._build_trn_segment(adjudication_result))

        # Loop 1000A - Payer Identification
        # Loop 1000B - Payee Identification
        # Loop 2000 - Header Number
        # Loop 2100 - Claim Payment Information
        # Loop 2110 - Service Payment Information

        # SE - Transaction Set Trailer
        # GE - Functional Group Trailer
        # IEA - Interchange Control Trailer

        return self.segment_terminator.join(segments)

    def _tokenize(self, content: str) -> List[X12Segment]:
        """Tokenize EDI content into segments."""
        raw_segments = content.strip().split(self.segment_terminator)
        segments = []

        for raw in raw_segments:
            if not raw.strip():
                continue
            elements = raw.split(self.delimiter)
            segment = X12Segment(
                segment_id=elements[0],
                elements=elements[1:]
            )
            segments.append(segment)

        return segments
```

### 4.2 LCD/NCD Medical Necessity Validator

**Purpose**: Validate procedures against CMS coverage determinations.

```python
# src/services/medical_necessity/coverage_validator.py

from dataclasses import dataclass
from typing import List, Optional, Set
from enum import Enum
import json

class CoverageType(str, Enum):
    NCD = "ncd"   # National Coverage Determination
    LCD = "lcd"   # Local Coverage Determination

class CoverageDecision(str, Enum):
    COVERED = "covered"
    NOT_COVERED = "not_covered"
    REQUIRES_REVIEW = "requires_review"
    NO_COVERAGE_POLICY = "no_coverage_policy"

@dataclass
class CoverageDetermination:
    """Coverage determination record from CMS."""
    determination_id: str
    coverage_type: CoverageType
    title: str
    contractor_name: Optional[str]  # For LCDs
    jurisdiction: List[str]         # MAC jurisdiction codes
    effective_date: str
    end_date: Optional[str]

    # Coverage details
    covered_cpt_codes: Set[str]
    covered_icd10_codes: Set[str]
    limitations: List[str]
    documentation_requirements: List[str]

@dataclass
class MedicalNecessityResult:
    """Result of medical necessity validation."""
    decision: CoverageDecision
    determination_id: Optional[str]
    coverage_type: Optional[CoverageType]

    # Matching details
    matched_diagnoses: List[str]
    unmatched_diagnoses: List[str]

    # Requirements
    limitations: List[str]
    documentation_requirements: List[str]

    # Explanation
    rationale: str
    confidence: float

class LCDNCDValidator:
    """
    Validates medical necessity against LCD/NCD criteria.

    Data Sources:
    - CMS Medicare Coverage Database (MCD)
    - Local downloads updated quarterly

    Hierarchy:
    1. NCD (National) takes precedence
    2. LCD (Local) applies within MAC jurisdiction
    3. No policy = general Medicare rules
    """

    def __init__(self, coverage_db, cache_service):
        self.coverage_db = coverage_db
        self.cache = cache_service

    async def validate(
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
            mac_jurisdiction: MAC jurisdiction code (e.g., "JH", "JL")
            place_of_service: Place of service code

        Returns:
            MedicalNecessityResult with coverage decision
        """
        # Check cache first
        cache_key = f"lcd_ncd:{cpt_code}:{mac_jurisdiction}:{hash(tuple(sorted(icd10_codes)))}"
        cached = await self.cache.get(cache_key)
        if cached:
            return MedicalNecessityResult(**json.loads(cached))

        # 1. Check for NCD (national takes precedence)
        ncd = await self.coverage_db.find_ncd(cpt_code)
        if ncd:
            result = self._evaluate_coverage(ncd, icd10_codes)
            await self.cache.set(cache_key, json.dumps(result.__dict__), ttl=86400)
            return result

        # 2. Check for LCD (regional)
        lcd = await self.coverage_db.find_lcd(cpt_code, mac_jurisdiction)
        if lcd:
            result = self._evaluate_coverage(lcd, icd10_codes)
            await self.cache.set(cache_key, json.dumps(result.__dict__), ttl=86400)
            return result

        # 3. No LCD/NCD - general Medicare rules apply
        return MedicalNecessityResult(
            decision=CoverageDecision.NO_COVERAGE_POLICY,
            determination_id=None,
            coverage_type=None,
            matched_diagnoses=[],
            unmatched_diagnoses=icd10_codes,
            limitations=[],
            documentation_requirements=[],
            rationale="No specific LCD/NCD found for this procedure. General Medicare coverage rules apply.",
            confidence=1.0
        )

    def _evaluate_coverage(
        self,
        determination: CoverageDetermination,
        submitted_diagnoses: List[str]
    ) -> MedicalNecessityResult:
        """Evaluate submitted diagnoses against coverage criteria."""

        covered_codes = determination.covered_icd10_codes
        submitted = set(submitted_diagnoses)

        # Find matching diagnoses
        matched = submitted & covered_codes
        unmatched = submitted - covered_codes

        if matched:
            decision = CoverageDecision.COVERED
            rationale = f"Diagnosis(es) {list(matched)} support medical necessity per {determination.coverage_type.value.upper()} {determination.determination_id}"
            confidence = len(matched) / len(submitted)
        elif unmatched and not matched:
            decision = CoverageDecision.NOT_COVERED
            rationale = f"No submitted diagnosis matches {determination.coverage_type.value.upper()} {determination.determination_id} coverage criteria"
            confidence = 0.95
        else:
            decision = CoverageDecision.REQUIRES_REVIEW
            rationale = "Manual review required - unable to determine coverage"
            confidence = 0.5

        return MedicalNecessityResult(
            decision=decision,
            determination_id=determination.determination_id,
            coverage_type=determination.coverage_type,
            matched_diagnoses=list(matched),
            unmatched_diagnoses=list(unmatched),
            limitations=determination.limitations,
            documentation_requirements=determination.documentation_requirements,
            rationale=rationale,
            confidence=confidence
        )
```

### 4.3 ML-based FWA Detection Service

**Purpose**: Detect fraud, waste, and abuse using machine learning anomaly detection.

```python
# src/services/fwa/ml_detector.py

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
import joblib

class FWAType(str, Enum):
    UPCODING = "upcoding"
    UNBUNDLING = "unbundling"
    DUPLICATE = "duplicate"
    PHANTOM_BILLING = "phantom_billing"
    IDENTITY_FRAUD = "identity_fraud"
    ANOMALY = "anomaly"

class RiskLevel(str, Enum):
    LOW = "low"           # 0.0 - 0.3
    MEDIUM = "medium"     # 0.3 - 0.6
    HIGH = "high"         # 0.6 - 0.8
    CRITICAL = "critical" # 0.8 - 1.0

@dataclass
class FWAFeatures:
    """Feature set for FWA ML models."""

    # Provider-level features
    provider_npi: str
    provider_claim_count_30d: int
    provider_avg_charge: float
    provider_unique_patients_30d: int
    provider_unique_diagnoses_30d: int
    provider_specialty_deviation: float  # vs peers

    # Claim-level features
    claim_id: str
    charge_amount: float
    units_billed: int
    diagnosis_count: int
    procedure_count: int
    service_duration_days: int

    # Pattern features
    is_weekend_service: bool
    is_after_hours: bool
    same_day_procedures_count: int
    modifier_count: int

    # Network features
    is_out_of_network: bool
    distance_to_provider_miles: float

    # Historical features
    provider_prior_denial_rate: float
    provider_prior_adjustment_rate: float
    provider_appeal_rate: float
    member_prior_claim_count: int

@dataclass
class FWADetectionResult:
    """Result of FWA ML detection."""
    claim_id: str
    overall_risk_score: float
    risk_level: RiskLevel

    # Individual model scores
    isolation_forest_score: float
    lof_score: float

    # Detected patterns
    detected_patterns: List[Dict]

    # Recommendations
    recommendation: str  # 'auto_approve', 'flag_review', 'flag_investigation'
    explanation: List[str]

class FWAMLDetector:
    """
    Machine Learning-based FWA detection.

    Models:
    - Isolation Forest: Overall anomaly detection
    - Local Outlier Factor: Provider-level outliers
    - Custom rules: Pattern-based detection

    Training:
    - Models trained on historical clean claims
    - Contamination rate tuned to expected fraud rate (1-5%)
    - Retraining scheduled monthly
    """

    def __init__(
        self,
        contamination: float = 0.03,  # Expected 3% fraud rate
        model_path: Optional[str] = None
    ):
        self.contamination = contamination
        self.scaler = StandardScaler()
        self.is_fitted = False

        # Initialize models
        self.isolation_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=200,
            max_samples='auto',
            n_jobs=-1
        )

        self.lof = LocalOutlierFactor(
            contamination=contamination,
            novelty=True,
            n_neighbors=20,
            n_jobs=-1
        )

        if model_path:
            self.load_models(model_path)

    def fit(self, features: np.ndarray, feature_names: List[str]):
        """
        Fit models on historical clean claims data.

        Args:
            features: Feature matrix (n_samples, n_features)
            feature_names: Names of features for interpretability
        """
        self.feature_names = feature_names

        # Scale features
        X_scaled = self.scaler.fit_transform(features)

        # Fit models
        self.isolation_forest.fit(X_scaled)
        self.lof.fit(X_scaled)

        self.is_fitted = True

    def detect(self, claim_features: FWAFeatures) -> FWADetectionResult:
        """
        Detect potential FWA in a single claim.

        Returns:
            FWADetectionResult with risk scores and recommendations
        """
        if not self.is_fitted:
            raise ValueError("Models must be fitted before detection")

        # Convert features to array
        X = self._features_to_array(claim_features)
        X_scaled = self.scaler.transform(X.reshape(1, -1))

        # Get anomaly scores from each model
        if_score = -self.isolation_forest.decision_function(X_scaled)[0]
        lof_score = -self.lof.decision_function(X_scaled)[0]

        # Normalize scores to 0-1
        if_normalized = self._normalize_score(if_score)
        lof_normalized = self._normalize_score(lof_score)

        # Ensemble score (weighted average)
        overall_score = 0.6 * if_normalized + 0.4 * lof_normalized

        # Apply rule-based adjustments
        patterns, rule_adjustment = self._check_rules(claim_features)
        overall_score = min(1.0, overall_score + rule_adjustment)

        # Determine risk level
        risk_level = self._score_to_level(overall_score)

        # Generate recommendation and explanation
        recommendation, explanation = self._generate_recommendation(
            overall_score, risk_level, patterns, claim_features
        )

        return FWADetectionResult(
            claim_id=claim_features.claim_id,
            overall_risk_score=round(overall_score, 4),
            risk_level=risk_level,
            isolation_forest_score=round(if_normalized, 4),
            lof_score=round(lof_normalized, 4),
            detected_patterns=patterns,
            recommendation=recommendation,
            explanation=explanation
        )

    def _check_rules(self, features: FWAFeatures) -> Tuple[List[Dict], float]:
        """Apply rule-based pattern detection."""
        patterns = []
        adjustment = 0.0

        # Rule: High charge amount vs provider average
        if features.charge_amount > features.provider_avg_charge * 3:
            patterns.append({
                "type": FWAType.UPCODING.value,
                "description": f"Charge ${features.charge_amount:.2f} is {features.charge_amount/features.provider_avg_charge:.1f}x provider average",
                "severity": "high"
            })
            adjustment += 0.15

        # Rule: Many procedures same day
        if features.same_day_procedures_count > 10:
            patterns.append({
                "type": FWAType.UNBUNDLING.value,
                "description": f"{features.same_day_procedures_count} procedures on same day",
                "severity": "medium"
            })
            adjustment += 0.10

        # Rule: Weekend + After hours + Out of network
        if features.is_weekend_service and features.is_after_hours and features.is_out_of_network:
            patterns.append({
                "type": FWAType.PHANTOM_BILLING.value,
                "description": "Weekend + after-hours + out-of-network service",
                "severity": "high"
            })
            adjustment += 0.20

        # Rule: Provider has high denial rate
        if features.provider_prior_denial_rate > 0.20:
            patterns.append({
                "type": FWAType.ANOMALY.value,
                "description": f"Provider denial rate {features.provider_prior_denial_rate:.1%} exceeds threshold",
                "severity": "medium"
            })
            adjustment += 0.10

        return patterns, adjustment

    def _normalize_score(self, raw_score: float) -> float:
        """Normalize anomaly score to 0-1 range."""
        # Sigmoid normalization
        return 1 / (1 + np.exp(-raw_score))

    def _score_to_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score >= 0.8:
            return RiskLevel.CRITICAL
        elif score >= 0.6:
            return RiskLevel.HIGH
        elif score >= 0.3:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _generate_recommendation(
        self,
        score: float,
        level: RiskLevel,
        patterns: List[Dict],
        features: FWAFeatures
    ) -> Tuple[str, List[str]]:
        """Generate recommendation and explanation."""

        explanation = []

        if level == RiskLevel.CRITICAL:
            recommendation = "flag_investigation"
            explanation.append("Claim flagged for immediate investigation due to critical risk indicators")
        elif level == RiskLevel.HIGH:
            recommendation = "flag_review"
            explanation.append("Claim flagged for manual review due to high risk indicators")
        elif level == RiskLevel.MEDIUM:
            recommendation = "flag_review"
            explanation.append("Claim flagged for review due to moderate risk indicators")
        else:
            recommendation = "auto_approve"
            explanation.append("Claim passes FWA screening")

        # Add pattern explanations
        for pattern in patterns:
            explanation.append(f"[{pattern['type'].upper()}] {pattern['description']}")

        return recommendation, explanation

    def save_models(self, path: str):
        """Save fitted models to disk."""
        joblib.dump({
            'scaler': self.scaler,
            'isolation_forest': self.isolation_forest,
            'lof': self.lof,
            'feature_names': self.feature_names,
            'is_fitted': self.is_fitted
        }, path)

    def load_models(self, path: str):
        """Load models from disk."""
        data = joblib.load(path)
        self.scaler = data['scaler']
        self.isolation_forest = data['isolation_forest']
        self.lof = data['lof']
        self.feature_names = data['feature_names']
        self.is_fitted = data['is_fitted']
```

### 4.4 Auto-Adjudication Engine

**Purpose**: Automated claim pricing and payment determination.

```python
# src/services/adjudication/auto_adjudicator.py

from dataclasses import dataclass
from typing import List, Optional, Dict
from decimal import Decimal
from enum import Enum
from datetime import date

class AdjudicationDecision(str, Enum):
    APPROVED = "approved"           # Auto-approved, proceed to payment
    APPROVED_REDUCED = "approved_reduced"  # Approved at reduced amount
    PENDED = "pended"               # Needs manual review
    DENIED = "denied"               # Rejected with reason
    INCOMPLETE = "incomplete"       # Needs additional information

@dataclass
class PricingResult:
    """Result of claim pricing calculation."""
    service_line_id: str
    cpt_code: str
    units: int

    # Charges
    billed_amount: Decimal
    allowed_amount: Decimal

    # Pricing method
    pricing_method: str  # 'fee_schedule', 'contract', 'uc', 'default'
    fee_schedule_id: Optional[str]
    contract_id: Optional[str]

    # Adjustments
    adjustments: List[Dict]  # [{'reason': 'CO-45', 'amount': Decimal}]

@dataclass
class BenefitsResult:
    """Result of benefits calculation."""
    allowed_amount: Decimal

    # Member responsibility
    deductible_applied: Decimal
    copay_applied: Decimal
    coinsurance_applied: Decimal

    # Limits
    deductible_remaining: Decimal
    oop_max_remaining: Decimal

    # Payment
    plan_payment: Decimal
    member_responsibility: Decimal

@dataclass
class AdjudicationResult:
    """Complete adjudication result."""
    claim_id: str
    decision: AdjudicationDecision

    # Validation summary
    validation_passed: bool
    validation_errors: List[str]
    validation_warnings: List[str]

    # FWA check
    fwa_passed: bool
    fwa_risk_score: float
    fwa_flags: List[str]

    # Pricing
    total_billed: Decimal
    total_allowed: Decimal
    pricing_details: List[PricingResult]

    # Benefits
    total_deductible: Decimal
    total_copay: Decimal
    total_coinsurance: Decimal
    total_plan_payment: Decimal
    total_member_responsibility: Decimal

    # Decision details
    decision_reason: str
    decision_code: str

    # Audit
    auto_adjudicated: bool
    adjudication_timestamp: str
    rules_applied: List[str]

class AutoAdjudicationEngine:
    """
    Automated claims adjudication engine.

    Process:
    1. Receive validated claim
    2. Check eligibility (if not already done)
    3. Price claim lines using fee schedules/contracts
    4. Apply member benefits (deductible, copay, coinsurance)
    5. Make payment determination

    Target: 80-90% auto-adjudication rate for clean claims
    """

    def __init__(
        self,
        pricing_service,
        benefits_service,
        fwa_detector,
        rules_engine
    ):
        self.pricing = pricing_service
        self.benefits = benefits_service
        self.fwa = fwa_detector
        self.rules = rules_engine

    async def adjudicate(
        self,
        claim: dict,
        validation_result: dict,
        eligibility_response: dict
    ) -> AdjudicationResult:
        """
        Adjudicate a validated claim.

        Args:
            claim: Normalized claim data
            validation_result: Output from validation engine
            eligibility_response: 270/271 eligibility check result

        Returns:
            AdjudicationResult with decision and payment details
        """

        # 1. Check validation result
        if not validation_result.get('can_submit', False):
            return self._create_denial(
                claim,
                "VALIDATION_FAILED",
                validation_result.get('errors', [])
            )

        # 2. Check eligibility
        if not eligibility_response.get('is_eligible', False):
            return self._create_denial(
                claim,
                "NOT_ELIGIBLE",
                [eligibility_response.get('reason', 'Member not eligible')]
            )

        # 3. Run FWA detection
        fwa_result = await self.fwa.detect(self._extract_fwa_features(claim))

        if fwa_result.risk_level.value in ['critical', 'high']:
            return self._create_pend(
                claim,
                "FWA_FLAG",
                f"FWA risk score {fwa_result.overall_risk_score:.2f}",
                fwa_result
            )

        # 4. Price claim lines
        pricing_results = []
        for line in claim.get('service_lines', []):
            pricing = await self.pricing.price_line(
                cpt_code=line['cpt_code'],
                units=line['units'],
                billed_amount=Decimal(str(line['charge_amount'])),
                provider_npi=claim['provider_npi'],
                place_of_service=claim['place_of_service'],
                policy_id=claim['policy_id']
            )
            pricing_results.append(pricing)

        total_allowed = sum(p.allowed_amount for p in pricing_results)

        # 5. Apply benefits
        benefits_result = await self.benefits.calculate(
            member_id=claim['member_id'],
            policy_id=claim['policy_id'],
            allowed_amount=total_allowed,
            service_date=claim['service_date'],
            claim_type=claim.get('claim_type', 'professional')
        )

        # 6. Apply adjudication rules
        rules_result = await self.rules.evaluate(
            claim=claim,
            validation=validation_result,
            pricing=pricing_results,
            benefits=benefits_result
        )

        # 7. Determine decision
        if rules_result.get('pend_reason'):
            return self._create_pend(
                claim,
                rules_result['pend_reason'],
                rules_result.get('pend_message', ''),
                fwa_result
            )

        # 8. Auto-approve
        return AdjudicationResult(
            claim_id=claim['claim_id'],
            decision=AdjudicationDecision.APPROVED,
            validation_passed=True,
            validation_errors=[],
            validation_warnings=validation_result.get('warnings', []),
            fwa_passed=True,
            fwa_risk_score=fwa_result.overall_risk_score,
            fwa_flags=[],
            total_billed=sum(Decimal(str(l['charge_amount'])) for l in claim.get('service_lines', [])),
            total_allowed=total_allowed,
            pricing_details=pricing_results,
            total_deductible=benefits_result.deductible_applied,
            total_copay=benefits_result.copay_applied,
            total_coinsurance=benefits_result.coinsurance_applied,
            total_plan_payment=benefits_result.plan_payment,
            total_member_responsibility=benefits_result.member_responsibility,
            decision_reason="Claim approved for payment",
            decision_code="A0",
            auto_adjudicated=True,
            adjudication_timestamp=date.today().isoformat(),
            rules_applied=rules_result.get('rules_applied', [])
        )

    def _create_denial(
        self,
        claim: dict,
        reason_code: str,
        errors: List[str]
    ) -> AdjudicationResult:
        """Create denial result."""
        return AdjudicationResult(
            claim_id=claim['claim_id'],
            decision=AdjudicationDecision.DENIED,
            validation_passed=False,
            validation_errors=errors,
            validation_warnings=[],
            fwa_passed=True,
            fwa_risk_score=0.0,
            fwa_flags=[],
            total_billed=Decimal('0'),
            total_allowed=Decimal('0'),
            pricing_details=[],
            total_deductible=Decimal('0'),
            total_copay=Decimal('0'),
            total_coinsurance=Decimal('0'),
            total_plan_payment=Decimal('0'),
            total_member_responsibility=Decimal('0'),
            decision_reason="; ".join(errors),
            decision_code=reason_code,
            auto_adjudicated=True,
            adjudication_timestamp=date.today().isoformat(),
            rules_applied=[]
        )

    def _create_pend(
        self,
        claim: dict,
        reason: str,
        message: str,
        fwa_result
    ) -> AdjudicationResult:
        """Create pended result for manual review."""
        return AdjudicationResult(
            claim_id=claim['claim_id'],
            decision=AdjudicationDecision.PENDED,
            validation_passed=True,
            validation_errors=[],
            validation_warnings=[],
            fwa_passed=fwa_result.risk_level.value == 'low',
            fwa_risk_score=fwa_result.overall_risk_score,
            fwa_flags=fwa_result.explanation,
            total_billed=Decimal('0'),
            total_allowed=Decimal('0'),
            pricing_details=[],
            total_deductible=Decimal('0'),
            total_copay=Decimal('0'),
            total_coinsurance=Decimal('0'),
            total_plan_payment=Decimal('0'),
            total_member_responsibility=Decimal('0'),
            decision_reason=f"[{reason}] {message}",
            decision_code="P1",
            auto_adjudicated=False,
            adjudication_timestamp=date.today().isoformat(),
            rules_applied=[]
        )
```

### 4.5 HCC Risk Scoring Service

**Purpose**: Calculate HCC risk adjustment scores for value-based care.

```python
# src/services/risk/hcc_calculator.py

from dataclasses import dataclass
from typing import List, Dict, Optional
from decimal import Decimal

@dataclass
class HCCResult:
    """HCC Risk Adjustment calculation result."""
    member_id: str

    # Demographics
    age: int
    gender: str
    dual_status: bool  # Medicare-Medicaid dual eligible
    originally_disabled: bool

    # HCC mapping
    icd10_codes: List[str]
    mapped_hccs: List[Dict]  # [{'hcc': 19, 'description': 'Diabetes', 'coefficient': 0.125}]

    # Interactions
    disease_interactions: List[Dict]

    # Final scores
    demographic_score: Decimal
    disease_score: Decimal
    interaction_score: Decimal
    total_risk_score: Decimal

    # Normalization
    normalized_risk_score: Decimal  # Relative to average (1.0)

    # Revenue impact
    estimated_monthly_payment: Decimal

class HCCRiskCalculator:
    """
    HCC Risk Adjustment Calculator using CMS-HCC Model.

    Uses the hccpy library for CMS-HCC V28 model calculations.

    Purpose:
    - Calculate member risk scores for Medicare Advantage
    - Support value-based care programs
    - Identify coding accuracy issues
    """

    def __init__(self, hcc_engine):
        """
        Initialize with hccpy engine.

        Example:
            from hccpy import HCCEngine
            engine = HCCEngine()
            calculator = HCCRiskCalculator(engine)
        """
        self.engine = hcc_engine

    def calculate(
        self,
        member_id: str,
        icd10_codes: List[str],
        age: int,
        gender: str,  # 'M' or 'F'
        dual_status: bool = False,
        originally_disabled: bool = False,
        model_version: str = "28"  # CMS-HCC V28
    ) -> HCCResult:
        """
        Calculate HCC risk score for a member.

        Args:
            member_id: Member identifier
            icd10_codes: List of ICD-10-CM diagnosis codes
            age: Member age in years
            gender: 'M' or 'F'
            dual_status: Is member dual-eligible (Medicare+Medicaid)
            originally_disabled: Originally entitled due to disability
            model_version: CMS-HCC model version

        Returns:
            HCCResult with risk scores and HCC mappings
        """
        # Map ICD-10 codes to HCCs
        hcc_mappings = []
        for icd_code in icd10_codes:
            hccs = self.engine.icd10_to_hcc(icd_code)
            for hcc in hccs:
                hcc_mappings.append({
                    'icd10': icd_code,
                    'hcc': hcc,
                    'description': self.engine.hcc_description(hcc),
                    'coefficient': self.engine.hcc_coefficient(hcc, age, gender)
                })

        # Calculate demographic score
        demographic_score = self.engine.demographic_score(
            age=age,
            gender=gender,
            dual=dual_status,
            originally_disabled=originally_disabled
        )

        # Calculate disease score
        unique_hccs = list(set(m['hcc'] for m in hcc_mappings))
        disease_score = sum(
            self.engine.hcc_coefficient(hcc, age, gender)
            for hcc in unique_hccs
        )

        # Calculate interactions
        interactions = self.engine.calculate_interactions(unique_hccs, age, gender)
        interaction_score = sum(i['coefficient'] for i in interactions)

        # Total risk score
        total_score = demographic_score + disease_score + interaction_score

        # Normalize to average of 1.0
        average_benchmark = Decimal('1.0')
        normalized_score = Decimal(str(total_score)) / average_benchmark

        # Estimate payment impact (example: base payment * risk score)
        base_monthly_payment = Decimal('1000')  # Configurable
        estimated_payment = base_monthly_payment * normalized_score

        return HCCResult(
            member_id=member_id,
            age=age,
            gender=gender,
            dual_status=dual_status,
            originally_disabled=originally_disabled,
            icd10_codes=icd10_codes,
            mapped_hccs=hcc_mappings,
            disease_interactions=interactions,
            demographic_score=Decimal(str(demographic_score)),
            disease_score=Decimal(str(disease_score)),
            interaction_score=Decimal(str(interaction_score)),
            total_risk_score=Decimal(str(total_score)),
            normalized_risk_score=normalized_score,
            estimated_monthly_payment=estimated_payment
        )

    def validate_coding_accuracy(
        self,
        historical_codes: List[str],
        current_claim_codes: List[str]
    ) -> Dict:
        """
        Validate coding accuracy by comparing historical vs current.

        Flags potential issues:
        - Missing chronic conditions
        - Suspiciously high HCC counts
        - Year-over-year RAF score changes
        """
        historical_hccs = set()
        current_hccs = set()

        for code in historical_codes:
            historical_hccs.update(self.engine.icd10_to_hcc(code))

        for code in current_claim_codes:
            current_hccs.update(self.engine.icd10_to_hcc(code))

        # Missing chronic conditions (should persist year-over-year)
        chronic_hccs = {19, 20, 21}  # Example: diabetes variants
        missing_chronic = historical_hccs & chronic_hccs - current_hccs

        return {
            'historical_hcc_count': len(historical_hccs),
            'current_hcc_count': len(current_hccs),
            'new_hccs': list(current_hccs - historical_hccs),
            'dropped_hccs': list(historical_hccs - current_hccs),
            'missing_chronic': list(missing_chronic),
            'accuracy_flag': len(missing_chronic) > 0
        }
```

---

## 5. Enhanced Validation Rules

### 5.1 Extended Rules Table

| Rule # | Name | Source | Blocking | Description |
|--------|------|--------|----------|-------------|
| 1 | Insured Data Extraction | LLM | No | Extract member/policy from documents |
| 2 | Code/Service Extraction | LLM | No | Extract ICD-10, CPT from documents |
| 3 | Fraud Detection | PyMuPDF + **ML** | Yes | PDF forensics + ML anomaly |
| 4 | ICD-CPT Crosswalk | Typesense | Yes | Validate dx supports px |
| 5 | Clinical Necessity | **LCD/NCD** + LLM | Yes | Medical necessity per coverage |
| 6 | ICD×ICD Validation | Rules | Yes | Invalid dx combinations |
| 7 | Diagnosis Demographics | Rules | Yes | Age/gender for dx |
| 8 | Procedure Demographics | Rules | Yes | Age/gender for px |
| 9 | Medical Reports | LLM | No | Supporting documentation |
| 10 | Rejection Reasons | Rules | Info | Explain rejections |
| 11 | Policy/TOB Coverage | Cache | Yes | Table of benefits |
| 12 | Network Coverage | DB | No | Provider network status |
| 13 | MUE Limits | CMS | Yes | Medically unlikely edits |
| **14** | **LCD Medical Necessity** | **CMS** | **Yes** | **Local coverage determination** |
| **15** | **NCD Medical Necessity** | **CMS** | **Yes** | **National coverage determination** |
| **16** | **Duplicate Detection** | **Hash** | **Yes** | **Fingerprint-based duplicates** |
| **17** | **Upcoding Detection** | **ML** | **Flag** | **E/M distribution analysis** |
| **18** | **Unbundling Detection** | **NCCI** | **Yes** | **PTP edit validation** |
| **19** | **HCC Risk Validation** | **hccpy** | **No** | **Risk adjustment accuracy** |

### 5.2 Rule Integration Points

```
Validation Orchestrator
         |
         +-- EXTRACTION PHASE
         |   +-- Rule 1: Insured Data
         |   +-- Rule 2: Code Extraction
         |
         +-- FRAUD PHASE
         |   +-- Rule 3: PDF Forensics + ML Detection
         |   +-- Rule 16: Duplicate Detection (NEW)
         |
         +-- MEDICAL VALIDATION PHASE
         |   +-- Rule 4: ICD-CPT Crosswalk
         |   +-- Rule 5: Clinical Necessity (Enhanced)
         |   +-- Rule 6: ICD×ICD Validation
         |   +-- Rule 7: Dx Demographics
         |   +-- Rule 8: Px Demographics
         |   +-- Rule 13: MUE Limits
         |   +-- Rule 14: LCD Validation (NEW)
         |   +-- Rule 15: NCD Validation (NEW)
         |   +-- Rule 18: Unbundling Detection (NEW)
         |
         +-- COVERAGE PHASE
         |   +-- Rule 11: Policy/TOB
         |   +-- Rule 12: Network Coverage
         |
         +-- DOCUMENTATION PHASE
         |   +-- Rule 9: Medical Reports
         |   +-- Rule 10: Rejection Reasoning
         |
         +-- FWA ML PHASE (Parallel)
         |   +-- Rule 17: Upcoding Detection (NEW)
         |   +-- ML Anomaly Detection (NEW)
         |
         +-- RISK ADJUSTMENT PHASE (Optional)
             +-- Rule 19: HCC Validation (NEW)
```

---

## 6. API Contracts (Extended)

### 6.1 X12 EDI Endpoints

```yaml
# POST /api/v1/edi/837
# Submit X12 837 claim (P or I)
Request:
  Content-Type: application/edi-x12
  Body: Raw X12 837 content

Response:
  Status: 202 Accepted
  Body:
    {
      "transaction_id": "uuid",
      "control_number": "string",
      "status": "received",
      "claims_extracted": 5,
      "processing_url": "/api/v1/edi/837/{transaction_id}/status"
    }

# GET /api/v1/edi/835/{claim_id}
# Get X12 835 remittance for adjudicated claim
Response:
  Content-Type: application/edi-x12
  Body: Raw X12 835 remittance advice
```

### 6.2 Adjudication Endpoints

```yaml
# POST /api/v1/adjudication/process
# Process validated claim through adjudication
Request:
  Content-Type: application/json
  Body:
    {
      "claim_id": "uuid",
      "validation_result_id": "uuid",
      "options": {
        "auto_adjudicate": true,
        "calculate_hcc": true
      }
    }

Response:
  Status: 200 OK
  Body:
    {
      "adjudication_id": "uuid",
      "claim_id": "uuid",
      "decision": "approved",
      "decision_code": "A0",

      "pricing": {
        "total_billed": 1500.00,
        "total_allowed": 1200.00,
        "adjustments": [
          {"reason": "CO-45", "amount": 300.00}
        ]
      },

      "benefits": {
        "deductible_applied": 100.00,
        "copay_applied": 25.00,
        "coinsurance_applied": 215.00,
        "plan_payment": 860.00,
        "member_responsibility": 340.00
      },

      "fwa": {
        "passed": true,
        "risk_score": 0.12,
        "flags": []
      },

      "hcc": {
        "calculated": true,
        "risk_score": 1.25,
        "mapped_hccs": [19, 85]
      }
    }
```

### 6.3 Analytics Endpoints

```yaml
# GET /api/v1/analytics/fwa/dashboard
# FWA analytics dashboard data
Response:
  Body:
    {
      "period": "2025-12",
      "summary": {
        "total_claims_reviewed": 50000,
        "fwa_flagged": 1500,
        "fwa_rate": 0.03,
        "estimated_savings": 450000.00
      },
      "by_type": [
        {"type": "upcoding", "count": 500, "amount": 150000},
        {"type": "unbundling", "count": 400, "amount": 120000},
        {"type": "duplicate", "count": 350, "amount": 100000}
      ],
      "top_providers": [
        {"npi": "1234567890", "flag_count": 25, "risk_score": 0.85}
      ],
      "trends": [
        {"month": "2025-10", "rate": 0.028},
        {"month": "2025-11", "rate": 0.030},
        {"month": "2025-12", "rate": 0.030}
      ]
    }
```

---

## 7. Data Models

### 7.1 New Database Tables

```sql
-- X12 EDI Transaction Log
CREATE TABLE edi_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_type VARCHAR(10) NOT NULL,  -- 837P, 837I, 835, 270, 271
    direction VARCHAR(10) NOT NULL,         -- inbound, outbound
    control_number VARCHAR(50) NOT NULL,
    sender_id VARCHAR(50),
    receiver_id VARCHAR(50),
    raw_content TEXT,
    parsed_content JSONB,
    claims_count INTEGER,
    status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- LCD/NCD Coverage Determinations
CREATE TABLE coverage_determinations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    determination_id VARCHAR(20) NOT NULL UNIQUE,
    coverage_type VARCHAR(10) NOT NULL,     -- 'ncd', 'lcd'
    title VARCHAR(500) NOT NULL,
    contractor_name VARCHAR(200),
    jurisdiction VARCHAR(20)[],             -- MAC jurisdiction codes
    effective_date DATE NOT NULL,
    end_date DATE,
    covered_cpt_codes VARCHAR(10)[],
    covered_icd10_codes VARCHAR(10)[],
    limitations TEXT[],
    documentation_requirements TEXT[],
    full_text TEXT,
    source_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_coverage_cpt ON coverage_determinations USING GIN(covered_cpt_codes);
CREATE INDEX idx_coverage_icd ON coverage_determinations USING GIN(covered_icd10_codes);

-- Adjudication Results
CREATE TABLE adjudication_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id),
    validation_result_id UUID,

    decision VARCHAR(20) NOT NULL,
    decision_code VARCHAR(10),
    decision_reason TEXT,

    -- Pricing
    total_billed DECIMAL(12, 2),
    total_allowed DECIMAL(12, 2),
    pricing_details JSONB,

    -- Benefits
    deductible_applied DECIMAL(10, 2),
    copay_applied DECIMAL(10, 2),
    coinsurance_applied DECIMAL(10, 2),
    plan_payment DECIMAL(12, 2),
    member_responsibility DECIMAL(12, 2),

    -- FWA
    fwa_passed BOOLEAN,
    fwa_risk_score DECIMAL(5, 4),
    fwa_flags JSONB,

    -- HCC
    hcc_calculated BOOLEAN DEFAULT FALSE,
    hcc_risk_score DECIMAL(6, 4),
    mapped_hccs INTEGER[],

    -- Audit
    auto_adjudicated BOOLEAN DEFAULT TRUE,
    reviewed_by UUID,
    review_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FWA ML Model Results
CREATE TABLE fwa_ml_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id),

    overall_risk_score DECIMAL(5, 4) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,

    isolation_forest_score DECIMAL(5, 4),
    lof_score DECIMAL(5, 4),

    detected_patterns JSONB,
    recommendation VARCHAR(30),
    explanation TEXT[],

    model_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fwa_risk ON fwa_ml_results(overall_risk_score);
CREATE INDEX idx_fwa_claim ON fwa_ml_results(claim_id);

-- HCC Risk Scores
CREATE TABLE hcc_risk_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL,
    claim_id UUID REFERENCES claims(id),

    calculation_date DATE NOT NULL,

    demographic_score DECIMAL(6, 4),
    disease_score DECIMAL(6, 4),
    interaction_score DECIMAL(6, 4),
    total_risk_score DECIMAL(6, 4),
    normalized_risk_score DECIMAL(6, 4),

    icd10_codes VARCHAR(10)[],
    mapped_hccs INTEGER[],

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_hcc_member ON hcc_risk_scores(member_id, calculation_date);

-- Fee Schedules
CREATE TABLE fee_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_name VARCHAR(200) NOT NULL,
    schedule_type VARCHAR(50),              -- 'medicare', 'medicaid', 'commercial'
    effective_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fee_schedule_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fee_schedule_id UUID NOT NULL REFERENCES fee_schedules(id),
    cpt_code VARCHAR(10) NOT NULL,
    modifier VARCHAR(10),
    place_of_service VARCHAR(5),

    facility_rate DECIMAL(10, 2),
    non_facility_rate DECIMAL(10, 2),

    effective_date DATE,
    end_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fee_schedule_id, cpt_code, modifier, place_of_service)
);

CREATE INDEX idx_fee_cpt ON fee_schedule_items(cpt_code);
```

### 7.2 Typesense Collections (Extended)

```python
# LCD/NCD Coverage Collection
LCD_NCD_SCHEMA = {
    'name': 'coverage_determinations',
    'fields': [
        {'name': 'determination_id', 'type': 'string', 'index': True},
        {'name': 'coverage_type', 'type': 'string', 'facet': True},
        {'name': 'title', 'type': 'string'},
        {'name': 'contractor_name', 'type': 'string', 'optional': True},
        {'name': 'jurisdiction', 'type': 'string[]', 'facet': True},
        {'name': 'covered_cpt_codes', 'type': 'string[]'},
        {'name': 'covered_icd10_codes', 'type': 'string[]'},
        {'name': 'effective_date', 'type': 'int64'},
        {'name': 'end_date', 'type': 'int64', 'optional': True}
    ]
}

# NCCI PTP Edits Collection
NCCI_PTP_SCHEMA = {
    'name': 'ncci_ptp_edits',
    'fields': [
        {'name': 'column1_code', 'type': 'string', 'index': True},
        {'name': 'column2_code', 'type': 'string', 'index': True},
        {'name': 'effective_date', 'type': 'int64'},
        {'name': 'deletion_date', 'type': 'int64', 'optional': True},
        {'name': 'modifier_indicator', 'type': 'string'},  # 0, 1, 9
        {'name': 'ptp_edit_rationale', 'type': 'string', 'optional': True}
    ]
}
```

---

## 8. Technology Additions

### 8.1 New Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| `x12-edi-tools` | 0.1.2 | X12 EDI parsing | MIT |
| `hccpy` | 0.1.10 | HCC risk calculation | Apache 2.0 |
| `scikit-learn` | 1.5.x | ML anomaly detection | BSD-3 |
| `joblib` | 1.4.x | Model serialization | BSD-3 |

### 8.2 CPT License Requirement

**CRITICAL**: CPT code validation requires AMA license.

| License Type | Estimated Cost | Purpose |
|--------------|---------------|---------|
| Internal Use | $10,000-25,000/year | Claims processing |
| Data File | $5,000-15,000/year | Code descriptions |
| Total | **$15,000-40,000/year** | Full implementation |

**Action Required**: Budget approval and AMA contract negotiation before implementation.

### 8.3 Data Import Schedule

| Data Source | Frequency | Automation |
|-------------|-----------|------------|
| CMS ICD-10 | Annual (October 1) | Automated download + import |
| CMS HCPCS | Quarterly | Automated download + import |
| CMS NCCI Edits | Quarterly | Automated download + import |
| CMS MUE | Quarterly | Automated download + import |
| LCD/NCD | Weekly | Automated sync from MCD |
| AMA CPT | Annual (January 1) | Manual import (license) |

---

## 9. Security & Compliance

### 9.1 HIPAA Technical Checklist

```yaml
encryption:
  at_rest:
    algorithm: "AES-256-GCM"
    key_management: "AWS KMS"
    key_rotation: "Annual"
  in_transit:
    protocol: "TLS 1.3"
    cipher_suites: "TLS_AES_256_GCM_SHA384"
    certificate: "SHA-256, 2048-bit RSA"

access_control:
  authentication:
    method: "SAML 2.0 / OIDC"
    mfa: "Required for all users"
    session_timeout: "15 minutes inactivity"
  authorization:
    model: "RBAC with attribute-based exceptions"
    roles:
      - claims_processor
      - claims_supervisor
      - fwa_investigator
      - auditor
      - admin

audit_logging:
  phi_access:
    - "All claim views"
    - "All member data access"
    - "All document downloads"
  retention: "7 years"
  format: "JSON, tamper-evident"
  storage: "S3 with Object Lock"

data_integrity:
  backups:
    frequency: "Daily full, hourly incremental"
    retention: "90 days"
    encryption: "AES-256"
    testing: "Monthly restore tests"
```

### 9.2 Required BAAs

| Vendor | Service | Status |
|--------|---------|--------|
| AWS | Cloud infrastructure | Required |
| OpenAI/Azure/Anthropic | LLM services | Required |
| Typesense Cloud | Search (if hosted) | Required |
| Redis Cloud | Cache (if hosted) | Required |

---

## 10. Implementation Phases

### Phase 1: X12 EDI & LCD/NCD (Weeks 1-3)

- [ ] Implement X12 837P parser
- [ ] Implement X12 837I parser
- [ ] Import LCD/NCD data from CMS
- [ ] Build coverage determination validator
- [ ] Integrate Rules 14-15 into validation engine

### Phase 2: ML FWA Detection (Weeks 4-5)

- [ ] Build FWA feature extraction pipeline
- [ ] Train Isolation Forest model on historical data
- [ ] Train LOF model
- [ ] Implement duplicate detection (Rule 16)
- [ ] Implement upcoding detection (Rule 17)
- [ ] Implement unbundling detection (Rule 18)

### Phase 3: Adjudication Engine (Weeks 6-8)

- [ ] Build pricing engine with fee schedules
- [ ] Build benefits calculation engine
- [ ] Implement auto-adjudication rules
- [ ] Build pend/exception queue management
- [ ] Generate X12 835 remittances

### Phase 4: HCC & Analytics (Weeks 9-10)

- [ ] Integrate hccpy for risk scoring
- [ ] Implement Rule 19 (HCC validation)
- [ ] Build FWA analytics dashboard
- [ ] Build provider risk scoring dashboard
- [ ] Implement audit trail reports

### Phase 5: Integration & Testing (Weeks 11-12)

- [ ] End-to-end integration testing
- [ ] Performance testing (target: 80% auto-adjudication)
- [ ] Security audit
- [ ] HIPAA compliance verification
- [ ] Production deployment

---

## 11. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CPT license delays | Medium | High | Start AMA negotiations early |
| ML model accuracy | Medium | High | Start with rules, add ML incrementally |
| LCD/NCD data complexity | High | Medium | Parse incrementally, validate carefully |
| Auto-adjudication rate < 80% | Medium | Medium | Tune rules, expand exceptions gradually |
| X12 parsing edge cases | High | Low | Use established library, test extensively |
| HIPAA audit findings | Low | Critical | Pre-audit with compliance consultant |
| Integration complexity | Medium | Medium | Modular design, extensive testing |

---

## 12. Open Questions for Review

### Business Questions

1. **CPT License Budget**: Approve estimated $15K-40K/year for AMA CPT license?
2. **Auto-adjudication Target**: Confirm 80-90% target or adjust?
3. **Manual Review SLA**: What is the target turnaround for pended claims?
4. **HCC Calculation**: Required for all claims or only Medicare Advantage?

### Technical Questions

1. **X12 Library Choice**: Use `x12-edi-tools` or build custom parser?
2. **ML Model Training**: What historical data is available for training?
3. **LCD/NCD Updates**: Weekly sync acceptable or need real-time?
4. **Fee Schedule Source**: Where do fee schedules come from? Manual upload?

### Integration Questions

1. **Clearinghouse Integration**: Will X12 come directly or via clearinghouse?
2. **Payment System**: How does adjudication result flow to payment?
3. **EHR Integration**: Is FHIR integration required for medical records?

---

**Document Version**: 1.0 (DRAFT)
**Last Updated**: December 19, 2025
**Status**: Pending Review
**Next Steps**: Review meeting to address open questions
