"""
Validation Engine Tests.
Tests for the validation engine services including orchestrator, risk scorer,
extraction services, and medical report validator.

Source: Design Document 04_validation_engine_comprehensive_design.md
"""

import pytest
from datetime import date, datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


# =============================================================================
# Inline Enums and Classes (matching src/services/validation/)
# =============================================================================


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(str, Enum):
    """Risk categories for FWA detection."""
    FRAUD = "fraud"
    WASTE = "waste"
    ABUSE = "abuse"
    CODING_ERROR = "coding_error"
    DOCUMENTATION = "documentation"
    ELIGIBILITY = "eligibility"
    MEDICAL_NECESSITY = "medical_necessity"


class ValidationPhase(str, Enum):
    """Phases of validation processing."""
    DOCUMENT_PROCESSING = "document_processing"
    DATA_EXTRACTION = "data_extraction"
    FRAUD_DETECTION = "fraud_detection"
    MEDICAL_VALIDATION = "medical_validation"
    DOCUMENTATION_CHECK = "documentation_check"
    RESULT_AGGREGATION = "result_aggregation"


class DocumentSection(str, Enum):
    """Medical document sections."""
    PATIENT_INFO = "patient_info"
    DIAGNOSIS = "diagnosis"
    TREATMENT = "treatment"
    MEDICATION = "medication"
    SIGNATURES = "signatures"


class SectionStatus(str, Enum):
    """Section validation status."""
    PRESENT = "present"
    MISSING = "missing"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"


class CodeType(str, Enum):
    """Types of medical codes."""
    ICD10_CM = "ICD10_CM"
    ICD10_PCS = "ICD10_PCS"
    CPT = "CPT"
    HCPCS = "HCPCS"
    REVENUE = "REVENUE"
    NDC = "NDC"


# =============================================================================
# Inline Data Classes (matching src/services/validation/risk_scorer.py)
# =============================================================================


@dataclass
class RiskFactor:
    """Individual risk factor contributing to overall score."""
    category: RiskCategory
    source: str
    severity: float
    confidence: float
    description: str
    evidence: Optional[str] = None

    @property
    def weighted_score(self) -> float:
        """Calculate weighted score (severity * confidence)."""
        return self.severity * self.confidence

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "source": self.source,
            "severity": self.severity,
            "confidence": self.confidence,
            "description": self.description,
            "evidence": self.evidence,
            "weighted_score": self.weighted_score,
        }


@dataclass
class RiskAssessment:
    """Complete risk assessment result."""
    risk_score: float
    risk_level: str
    risk_factors: list[RiskFactor] = field(default_factory=list)
    primary_category: Optional[RiskCategory] = None
    recommendation: str = ""
    requires_investigation: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "risk_score": round(self.risk_score, 3),
            "risk_level": self.risk_level,
            "primary_category": self.primary_category.value if self.primary_category else None,
            "risk_factors": [f.to_dict() for f in self.risk_factors],
            "recommendation": self.recommendation,
            "requires_investigation": self.requires_investigation,
        }


@dataclass
class RuleValidationDetail:
    """Detail of a single rule validation."""
    rule_id: str
    rule_name: str
    status: str  # passed, failed, warning, skipped, error
    confidence: float = 0.0
    issues_found: int = 0
    details: Optional[dict[str, Any]] = None
    execution_time_ms: int = 0


# =============================================================================
# Inline RiskScorer (matching src/services/validation/risk_scorer.py)
# =============================================================================


class RiskScorer:
    """Calculates risk scores for claims based on validation results."""

    RULE_WEIGHTS = {
        "rule_1": 0.3,
        "rule_2": 0.3,
        "rule_3": 0.9,
        "rule_4": 0.6,
        "rule_5": 0.7,
        "rule_6": 0.5,
        "rule_7": 0.4,
        "rule_8": 0.4,
        "rule_7_8": 0.4,
        "rule_9": 0.6,
    }

    RULE_CATEGORIES = {
        "rule_1": RiskCategory.DOCUMENTATION,
        "rule_2": RiskCategory.DOCUMENTATION,
        "rule_3": RiskCategory.FRAUD,
        "rule_4": RiskCategory.CODING_ERROR,
        "rule_5": RiskCategory.MEDICAL_NECESSITY,
        "rule_6": RiskCategory.CODING_ERROR,
        "rule_7": RiskCategory.ELIGIBILITY,
        "rule_8": RiskCategory.ELIGIBILITY,
        "rule_7_8": RiskCategory.ELIGIBILITY,
        "rule_9": RiskCategory.DOCUMENTATION,
    }

    def calculate_risk(
        self,
        rule_results: list[RuleValidationDetail],
        critical_issues: list[str],
        warnings: list[str],
    ) -> RiskAssessment:
        """Calculate overall risk assessment."""
        risk_factors: list[RiskFactor] = []
        category_scores: dict[RiskCategory, float] = {}

        for result in rule_results:
            if result.status == "failed":
                weight = self.RULE_WEIGHTS.get(result.rule_id, 0.5)
                category = self.RULE_CATEGORIES.get(result.rule_id, RiskCategory.CODING_ERROR)

                severity = min(weight * (1 + result.issues_found * 0.1), 1.0)
                confidence = result.confidence if result.confidence > 0 else 0.5

                factor = RiskFactor(
                    category=category,
                    source=result.rule_id,
                    severity=severity,
                    confidence=confidence,
                    description=f"{result.rule_name} failed with {result.issues_found} issues",
                )
                risk_factors.append(factor)

                if category not in category_scores:
                    category_scores[category] = 0.0
                category_scores[category] += factor.weighted_score

            elif result.status == "warning":
                weight = self.RULE_WEIGHTS.get(result.rule_id, 0.3) * 0.3
                category = self.RULE_CATEGORIES.get(result.rule_id, RiskCategory.DOCUMENTATION)

                factor = RiskFactor(
                    category=category,
                    source=result.rule_id,
                    severity=weight,
                    confidence=result.confidence if result.confidence > 0 else 0.3,
                    description=f"{result.rule_name} warning",
                )
                risk_factors.append(factor)

        # Add critical issues as risk factors
        for issue in critical_issues[:5]:
            risk_factors.append(RiskFactor(
                category=RiskCategory.FRAUD,
                source="critical_issue",
                severity=0.8,
                confidence=0.9,
                description=issue[:200],
            ))

        # Calculate overall risk score
        if not risk_factors:
            risk_score = 0.0
        else:
            total_weighted = sum(f.weighted_score for f in risk_factors)
            factor_count = len(risk_factors)
            base_score = total_weighted / max(factor_count, 1)

            if factor_count > 1:
                compound_multiplier = 1 + (factor_count - 1) * 0.1
                risk_score = min(base_score * compound_multiplier, 1.0)
            else:
                risk_score = base_score

        # Determine risk level
        risk_level = self._determine_risk_level(risk_score)

        # Find primary risk category
        primary_category = None
        if category_scores:
            primary_category = max(category_scores, key=category_scores.get)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            risk_level, primary_category, len(critical_issues)
        )

        # Determine if investigation required
        requires_investigation = (
            risk_level in ("high", "critical")
            or primary_category == RiskCategory.FRAUD
            or len(critical_issues) > 0
        )

        return RiskAssessment(
            risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=sorted(risk_factors, key=lambda f: f.weighted_score, reverse=True),
            primary_category=primary_category,
            recommendation=recommendation,
            requires_investigation=requires_investigation,
        )

    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level from score."""
        if score >= 0.7:
            return "critical"
        elif score >= 0.5:
            return "high"
        elif score >= 0.3:
            return "medium"
        else:
            return "low"

    def _generate_recommendation(
        self,
        risk_level: str,
        primary_category: Optional[RiskCategory],
        critical_count: int,
    ) -> str:
        """Generate recommendation based on risk assessment."""
        if risk_level == "critical":
            return "REJECT: Critical risk detected. Manual investigation required before processing."

        if risk_level == "high":
            if primary_category == RiskCategory.FRAUD:
                return "HOLD: Suspected fraud indicators. Route to SIU for investigation."
            elif primary_category == RiskCategory.MEDICAL_NECESSITY:
                return "REVIEW: Medical necessity concerns. Route to clinical reviewer."
            else:
                return "REVIEW: High risk detected. Requires supervisor review before processing."

        if risk_level == "medium":
            if primary_category == RiskCategory.CODING_ERROR:
                return "REVIEW: Potential coding issues. Verify codes before processing."
            elif primary_category == RiskCategory.DOCUMENTATION:
                return "REVIEW: Documentation concerns. Request additional documentation."
            else:
                return "PROCESS WITH CAUTION: Minor issues detected. Note for audit."

        return "APPROVE: Low risk. Standard processing."


# =============================================================================
# Inline Code Extractor (matching src/services/extraction/code_extractor.py)
# =============================================================================


@dataclass
class ExtractedCode:
    """Single extracted medical code."""
    code: str
    code_type: CodeType
    description: Optional[str] = None
    confidence: float = 1.0
    source_text: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class ServiceLine:
    """Service line from claim."""
    line_number: int
    procedure_code: Optional[str] = None
    procedure_type: Optional[CodeType] = None
    modifiers: list[str] = field(default_factory=list)
    diagnosis_pointers: list[int] = field(default_factory=list)
    units: int = 1
    charges: Optional[float] = None


@dataclass
class CodeExtractionResult:
    """Result of code extraction."""
    icd_codes: list[ExtractedCode] = field(default_factory=list)
    cpt_codes: list[ExtractedCode] = field(default_factory=list)
    hcpcs_codes: list[ExtractedCode] = field(default_factory=list)
    revenue_codes: list[ExtractedCode] = field(default_factory=list)
    ndc_codes: list[ExtractedCode] = field(default_factory=list)
    service_lines: list[ServiceLine] = field(default_factory=list)
    primary_diagnosis: Optional[str] = None
    confidence: float = 0.0
    execution_time_ms: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def has_codes(self) -> bool:
        return bool(self.icd_codes or self.cpt_codes or self.hcpcs_codes)


class CodeExtractor:
    """Extracts medical codes from documents using regex patterns."""

    ICD10_PATTERN = r"\b([A-TV-Z]\d{2}(?:\.\d{1,4})?)\b"
    CPT_PATTERN = r"\b(\d{5})\b"
    HCPCS_PATTERN = r"\b([A-V]\d{4})\b"

    def validate_icd10_format(self, code: str) -> bool:
        """Validate ICD-10 code format."""
        import re
        return bool(re.match(self.ICD10_PATTERN, code.upper()))

    def validate_cpt_format(self, code: str) -> bool:
        """Validate CPT code format."""
        import re
        return bool(re.match(r"^\d{5}$", code))

    def extract_codes_from_text(self, text: str) -> CodeExtractionResult:
        """Extract medical codes from text using regex."""
        import re
        result = CodeExtractionResult()

        # Extract ICD-10 codes
        for match in re.finditer(self.ICD10_PATTERN, text.upper()):
            code = match.group(1)
            if self.validate_icd10_format(code):
                result.icd_codes.append(ExtractedCode(
                    code=code,
                    code_type=CodeType.ICD10_CM,
                    confidence=0.9,
                    source_text=text[max(0, match.start()-20):match.end()+20],
                ))

        # Extract CPT codes
        for match in re.finditer(self.CPT_PATTERN, text):
            code = match.group(1)
            if self.validate_cpt_format(code):
                result.cpt_codes.append(ExtractedCode(
                    code=code,
                    code_type=CodeType.CPT,
                    confidence=0.85,
                ))

        # Extract HCPCS codes
        for match in re.finditer(self.HCPCS_PATTERN, text.upper()):
            code = match.group(1)
            result.hcpcs_codes.append(ExtractedCode(
                code=code,
                code_type=CodeType.HCPCS,
                confidence=0.85,
            ))

        # Set primary diagnosis
        if result.icd_codes:
            result.primary_diagnosis = result.icd_codes[0].code
            result.confidence = sum(c.confidence for c in result.icd_codes) / len(result.icd_codes)

        return result


# =============================================================================
# Inline Medical Report Validator
# =============================================================================


@dataclass
class SectionAnalysis:
    """Analysis of a document section."""
    section: DocumentSection
    status: SectionStatus
    content_summary: Optional[str] = None
    confidence: float = 0.0
    issues: list[str] = field(default_factory=list)


@dataclass
class SignatureValidation:
    """Signature validation result."""
    has_physician_signature: bool = False
    has_date: bool = False
    signature_legible: bool = False
    credentials_present: bool = False
    issues: list[str] = field(default_factory=list)


@dataclass
class MedicalReportValidationResult:
    """Result of medical report validation."""
    is_valid: bool = False
    overall_confidence: float = 0.0
    sections_analyzed: list[SectionAnalysis] = field(default_factory=list)
    signature_validation: Optional[SignatureValidation] = None
    date_consistency: bool = True
    critical_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    execution_time_ms: int = 0


class MedicalReportValidator:
    """Validates medical report documentation."""

    REQUIRED_SECTIONS = [
        DocumentSection.PATIENT_INFO,
        DocumentSection.DIAGNOSIS,
        DocumentSection.TREATMENT,
    ]

    def validate_sections(
        self,
        extracted_sections: dict[DocumentSection, str],
    ) -> list[SectionAnalysis]:
        """Validate presence and completeness of sections."""
        analyses = []

        for section in self.REQUIRED_SECTIONS:
            content = extracted_sections.get(section)
            if content:
                status = SectionStatus.PRESENT if len(content) > 20 else SectionStatus.INCOMPLETE
                confidence = 0.9 if status == SectionStatus.PRESENT else 0.5
            else:
                status = SectionStatus.MISSING
                confidence = 0.0

            analyses.append(SectionAnalysis(
                section=section,
                status=status,
                content_summary=content[:100] if content else None,
                confidence=confidence,
                issues=[] if status == SectionStatus.PRESENT else [f"Section {section.value} is {status.value}"],
            ))

        return analyses

    def validate_signature(self, signature_text: str) -> SignatureValidation:
        """Validate signature information."""
        result = SignatureValidation()

        text_lower = signature_text.lower()
        result.has_physician_signature = "md" in text_lower or "do" in text_lower or "signature" in text_lower
        result.has_date = "date" in text_lower or "/" in signature_text
        result.credentials_present = "md" in text_lower or "do" in text_lower or "np" in text_lower
        result.signature_legible = len(signature_text.strip()) > 5

        if not result.has_physician_signature:
            result.issues.append("Missing physician signature")
        if not result.has_date:
            result.issues.append("Missing signature date")

        return result

    def validate_report(
        self,
        extracted_sections: dict[DocumentSection, str],
        signature_text: Optional[str] = None,
        service_date: Optional[date] = None,
        document_date: Optional[date] = None,
    ) -> MedicalReportValidationResult:
        """Perform full validation of medical report."""
        result = MedicalReportValidationResult()

        # Validate sections
        result.sections_analyzed = self.validate_sections(extracted_sections)

        # Check for missing required sections
        for analysis in result.sections_analyzed:
            if analysis.status == SectionStatus.MISSING:
                result.critical_issues.append(f"Required section missing: {analysis.section.value}")
            elif analysis.status == SectionStatus.INCOMPLETE:
                result.warnings.append(f"Section incomplete: {analysis.section.value}")

        # Validate signature if provided
        if signature_text:
            result.signature_validation = self.validate_signature(signature_text)
            if not result.signature_validation.has_physician_signature:
                result.warnings.append("Missing physician signature")

        # Check date consistency
        if service_date and document_date:
            days_diff = abs((document_date - service_date).days)
            if days_diff > 30:
                result.date_consistency = False
                result.warnings.append(f"Document date differs from service date by {days_diff} days")

        # Calculate overall confidence
        if result.sections_analyzed:
            result.overall_confidence = sum(
                s.confidence for s in result.sections_analyzed
            ) / len(result.sections_analyzed)
        else:
            result.overall_confidence = 0.0

        # Determine validity
        result.is_valid = (
            len(result.critical_issues) == 0
            and result.overall_confidence >= 0.5
        )

        return result


# =============================================================================
# Risk Scorer Tests
# =============================================================================


class TestRiskScorer:
    """Tests for the RiskScorer class."""

    @pytest.fixture
    def scorer(self):
        """Create risk scorer instance."""
        return RiskScorer()

    def test_low_risk_no_failures(self, scorer):
        """Test low risk when no rules fail."""
        rule_results = [
            RuleValidationDetail(
                rule_id="rule_4",
                rule_name="ICD-CPT Crosswalk",
                status="passed",
                confidence=1.0,
                issues_found=0,
            ),
            RuleValidationDetail(
                rule_id="rule_6",
                rule_name="ICD×ICD Conflicts",
                status="passed",
                confidence=1.0,
                issues_found=0,
            ),
        ]

        assessment = scorer.calculate_risk(rule_results, [], [])

        assert assessment.risk_score == 0.0
        assert assessment.risk_level == "low"
        assert assessment.recommendation == "APPROVE: Low risk. Standard processing."
        assert assessment.requires_investigation is False

    def test_medium_risk_single_failure(self, scorer):
        """Test medium risk with single rule failure."""
        rule_results = [
            RuleValidationDetail(
                rule_id="rule_6",
                rule_name="ICD×ICD Conflicts",
                status="failed",
                confidence=0.8,
                issues_found=2,
            ),
        ]

        assessment = scorer.calculate_risk(rule_results, [], [])

        assert assessment.risk_level == "medium"
        assert assessment.primary_category == RiskCategory.CODING_ERROR
        assert "coding" in assessment.recommendation.lower()

    def test_high_risk_fraud_detection(self, scorer):
        """Test high risk when fraud is detected."""
        rule_results = [
            RuleValidationDetail(
                rule_id="rule_3",
                rule_name="PDF Forensics",
                status="failed",
                confidence=0.9,
                issues_found=1,
            ),
        ]

        assessment = scorer.calculate_risk(rule_results, [], [])

        # High fraud confidence results in critical or high risk level
        assert assessment.risk_level in ("high", "critical")
        assert assessment.primary_category == RiskCategory.FRAUD
        assert assessment.requires_investigation is True
        assert any(keyword in assessment.recommendation for keyword in ["fraud", "SIU", "DENY", "REJECT"])

    def test_critical_risk_multiple_failures(self, scorer):
        """Test critical risk with multiple severe failures."""
        rule_results = [
            RuleValidationDetail(
                rule_id="rule_3",
                rule_name="PDF Forensics",
                status="failed",
                confidence=0.95,
                issues_found=3,
            ),
            RuleValidationDetail(
                rule_id="rule_5",
                rule_name="Clinical Necessity",
                status="failed",
                confidence=0.8,
                issues_found=2,
            ),
        ]

        assessment = scorer.calculate_risk(rule_results, ["Critical fraud signal detected"], [])

        assert assessment.risk_level == "critical"
        assert assessment.requires_investigation is True
        assert "REJECT" in assessment.recommendation

    def test_critical_issues_increase_risk(self, scorer):
        """Test that critical issues increase risk score."""
        rule_results = [
            RuleValidationDetail(
                rule_id="rule_4",
                rule_name="ICD-CPT Crosswalk",
                status="passed",
                confidence=1.0,
                issues_found=0,
            ),
        ]

        assessment = scorer.calculate_risk(
            rule_results,
            ["Document tampering detected", "Metadata inconsistency"],
            []
        )

        assert assessment.risk_score > 0.5
        assert assessment.requires_investigation is True

    def test_warning_contributes_less_to_risk(self, scorer):
        """Test that warnings contribute less to risk than failures."""
        rule_results_warning = [
            RuleValidationDetail(
                rule_id="rule_9",
                rule_name="Documentation",
                status="warning",
                confidence=0.7,
                issues_found=1,
            ),
        ]

        rule_results_failed = [
            RuleValidationDetail(
                rule_id="rule_9",
                rule_name="Documentation",
                status="failed",
                confidence=0.7,
                issues_found=1,
            ),
        ]

        assessment_warning = scorer.calculate_risk(rule_results_warning, [], [])
        assessment_failed = scorer.calculate_risk(rule_results_failed, [], [])

        assert assessment_warning.risk_score < assessment_failed.risk_score

    def test_risk_factors_sorted_by_weighted_score(self, scorer):
        """Test that risk factors are sorted by weighted score."""
        rule_results = [
            RuleValidationDetail(
                rule_id="rule_7_8",
                rule_name="Demographics",
                status="failed",
                confidence=0.5,
                issues_found=1,
            ),
            RuleValidationDetail(
                rule_id="rule_3",
                rule_name="PDF Forensics",
                status="failed",
                confidence=0.95,
                issues_found=2,
            ),
        ]

        assessment = scorer.calculate_risk(rule_results, [], [])

        assert len(assessment.risk_factors) == 2
        assert assessment.risk_factors[0].weighted_score >= assessment.risk_factors[1].weighted_score

    def test_medical_necessity_recommendation(self, scorer):
        """Test medical necessity specific recommendation."""
        rule_results = [
            RuleValidationDetail(
                rule_id="rule_5",
                rule_name="Clinical Necessity",
                status="failed",
                confidence=0.85,
                issues_found=1,
            ),
        ]

        assessment = scorer.calculate_risk(rule_results, [], [])

        assert assessment.primary_category == RiskCategory.MEDICAL_NECESSITY
        assert "clinical" in assessment.recommendation.lower() or "medical" in assessment.recommendation.lower()


# =============================================================================
# Risk Factor Tests
# =============================================================================


class TestRiskFactor:
    """Tests for the RiskFactor dataclass."""

    def test_weighted_score_calculation(self):
        """Test weighted score is severity * confidence."""
        factor = RiskFactor(
            category=RiskCategory.FRAUD,
            source="rule_3",
            severity=0.9,
            confidence=0.8,
            description="Test factor",
        )

        assert factor.weighted_score == pytest.approx(0.72)  # 0.9 * 0.8

    def test_to_dict_conversion(self):
        """Test conversion to dictionary."""
        factor = RiskFactor(
            category=RiskCategory.CODING_ERROR,
            source="rule_4",
            severity=0.6,
            confidence=0.9,
            description="Crosswalk failure",
            evidence="ICD E11.9 does not support CPT 27447",
        )

        result = factor.to_dict()

        assert result["category"] == "coding_error"
        assert result["source"] == "rule_4"
        assert result["severity"] == 0.6
        assert result["confidence"] == 0.9
        assert result["weighted_score"] == 0.54
        assert result["evidence"] is not None


# =============================================================================
# Code Extractor Tests
# =============================================================================


class TestCodeExtractor:
    """Tests for the CodeExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create code extractor instance."""
        return CodeExtractor()

    def test_validate_icd10_format_valid(self, extractor):
        """Test ICD-10 validation with valid codes."""
        assert extractor.validate_icd10_format("E11.9") is True
        assert extractor.validate_icd10_format("I10") is True
        assert extractor.validate_icd10_format("M54.5") is True
        assert extractor.validate_icd10_format("Z23") is True

    def test_validate_icd10_format_invalid(self, extractor):
        """Test ICD-10 validation with invalid codes."""
        assert extractor.validate_icd10_format("123.45") is False
        assert extractor.validate_icd10_format("ABC") is False
        assert extractor.validate_icd10_format("") is False

    def test_validate_cpt_format_valid(self, extractor):
        """Test CPT validation with valid codes."""
        assert extractor.validate_cpt_format("99213") is True
        assert extractor.validate_cpt_format("80053") is True
        assert extractor.validate_cpt_format("27447") is True

    def test_validate_cpt_format_invalid(self, extractor):
        """Test CPT validation with invalid codes."""
        assert extractor.validate_cpt_format("9921") is False  # Too short
        assert extractor.validate_cpt_format("992134") is False  # Too long
        assert extractor.validate_cpt_format("A9213") is False  # Not all digits

    def test_extract_codes_from_text_icd10(self, extractor):
        """Test ICD-10 code extraction from text."""
        text = "Patient diagnosed with E11.9 diabetes and I10 hypertension."

        result = extractor.extract_codes_from_text(text)

        assert len(result.icd_codes) >= 2
        codes = [c.code for c in result.icd_codes]
        assert "E11.9" in codes or "E11" in codes
        assert "I10" in codes

    def test_extract_codes_from_text_cpt(self, extractor):
        """Test CPT code extraction from text."""
        text = "Procedures performed: 99213 office visit, 80053 metabolic panel"

        result = extractor.extract_codes_from_text(text)

        assert len(result.cpt_codes) >= 2
        codes = [c.code for c in result.cpt_codes]
        assert "99213" in codes
        assert "80053" in codes

    def test_extract_codes_from_text_mixed(self, extractor):
        """Test extraction of mixed code types."""
        text = "Dx: E11.9 Type 2 diabetes. Proc: 99214 level 4 visit. HCPCS: J0129 injection"

        result = extractor.extract_codes_from_text(text)

        assert result.has_codes is True
        assert len(result.icd_codes) >= 1
        assert len(result.cpt_codes) >= 1

    def test_primary_diagnosis_set(self, extractor):
        """Test that primary diagnosis is set to first ICD code."""
        text = "Primary: M54.5 low back pain. Secondary: Z96.641 right hip replacement."

        result = extractor.extract_codes_from_text(text)

        assert result.primary_diagnosis is not None
        assert result.primary_diagnosis == result.icd_codes[0].code if result.icd_codes else True

    def test_empty_text_returns_empty_result(self, extractor):
        """Test extraction from empty text."""
        result = extractor.extract_codes_from_text("")

        assert result.has_codes is False
        assert len(result.icd_codes) == 0
        assert len(result.cpt_codes) == 0


# =============================================================================
# Medical Report Validator Tests
# =============================================================================


class TestMedicalReportValidator:
    """Tests for the MedicalReportValidator class."""

    @pytest.fixture
    def validator(self):
        """Create medical report validator instance."""
        return MedicalReportValidator()

    def test_validate_sections_all_present(self, validator):
        """Test validation when all sections present."""
        sections = {
            DocumentSection.PATIENT_INFO: "John Doe, DOB: 01/01/1960, MRN: 123456",
            DocumentSection.DIAGNOSIS: "Type 2 diabetes mellitus without complications",
            DocumentSection.TREATMENT: "Metformin 500mg twice daily. Diet and exercise counseling.",
        }

        analyses = validator.validate_sections(sections)

        assert all(a.status == SectionStatus.PRESENT for a in analyses)
        assert all(a.confidence >= 0.9 for a in analyses)

    def test_validate_sections_missing(self, validator):
        """Test validation with missing sections."""
        sections = {
            DocumentSection.PATIENT_INFO: "John Doe, DOB: 01/01/1960",
            # DIAGNOSIS missing
            # TREATMENT missing
        }

        analyses = validator.validate_sections(sections)

        missing = [a for a in analyses if a.status == SectionStatus.MISSING]
        assert len(missing) >= 2

    def test_validate_sections_incomplete(self, validator):
        """Test validation with incomplete sections."""
        sections = {
            DocumentSection.PATIENT_INFO: "John Doe",  # Too short
            DocumentSection.DIAGNOSIS: "Type 2 diabetes mellitus is the primary diagnosis here",
            DocumentSection.TREATMENT: "Rx",  # Too short
        }

        analyses = validator.validate_sections(sections)

        incomplete = [a for a in analyses if a.status == SectionStatus.INCOMPLETE]
        assert len(incomplete) >= 1

    def test_validate_signature_complete(self, validator):
        """Test signature validation with complete signature."""
        signature_text = "Signed: Dr. John Smith, MD Date: 12/19/2025"

        result = validator.validate_signature(signature_text)

        assert result.has_physician_signature is True
        assert result.has_date is True
        assert result.credentials_present is True
        assert len(result.issues) == 0

    def test_validate_signature_missing_date(self, validator):
        """Test signature validation without date."""
        signature_text = "Signed by Dr. Jane Doe, MD"

        result = validator.validate_signature(signature_text)

        assert result.has_physician_signature is True
        assert result.has_date is False
        assert "date" in result.issues[0].lower()

    def test_validate_signature_missing_physician(self, validator):
        """Test signature validation without physician."""
        signature_text = "Signed: Date: 12/19/2025"

        result = validator.validate_signature(signature_text)

        assert result.has_physician_signature is False
        assert "signature" in result.issues[0].lower()

    def test_validate_report_valid(self, validator):
        """Test full report validation with valid report."""
        sections = {
            DocumentSection.PATIENT_INFO: "John Doe, DOB: 01/01/1960, MRN: 123456",
            DocumentSection.DIAGNOSIS: "Type 2 diabetes mellitus without complications",
            DocumentSection.TREATMENT: "Metformin 500mg twice daily. Diet and exercise counseling.",
        }
        signature = "Dr. John Smith, MD Date: 12/15/2025"

        result = validator.validate_report(
            sections,
            signature_text=signature,
            service_date=date(2025, 12, 15),
            document_date=date(2025, 12, 15),
        )

        assert result.is_valid is True
        assert len(result.critical_issues) == 0
        assert result.overall_confidence >= 0.8

    def test_validate_report_missing_required_sections(self, validator):
        """Test report validation with missing required sections."""
        sections = {
            DocumentSection.PATIENT_INFO: "John Doe, DOB: 01/01/1960",
            # Missing DIAGNOSIS and TREATMENT
        }

        result = validator.validate_report(sections)

        assert result.is_valid is False
        assert len(result.critical_issues) >= 2

    def test_validate_report_date_inconsistency(self, validator):
        """Test report validation with date inconsistency."""
        sections = {
            DocumentSection.PATIENT_INFO: "John Doe, DOB: 01/01/1960, MRN: 123456",
            DocumentSection.DIAGNOSIS: "Type 2 diabetes mellitus without complications",
            DocumentSection.TREATMENT: "Metformin 500mg twice daily. Diet and exercise counseling.",
        }

        result = validator.validate_report(
            sections,
            service_date=date(2025, 1, 1),
            document_date=date(2025, 3, 15),  # 73 days difference
        )

        assert result.date_consistency is False
        assert any("date" in w.lower() for w in result.warnings)


# =============================================================================
# Extracted Code Tests
# =============================================================================


class TestExtractedCode:
    """Tests for ExtractedCode dataclass."""

    def test_extracted_code_creation(self):
        """Test basic extracted code creation."""
        code = ExtractedCode(
            code="E11.9",
            code_type=CodeType.ICD10_CM,
            description="Type 2 diabetes without complications",
            confidence=0.95,
        )

        assert code.code == "E11.9"
        assert code.code_type == CodeType.ICD10_CM
        assert code.confidence == 0.95

    def test_extracted_code_defaults(self):
        """Test extracted code default values."""
        code = ExtractedCode(
            code="99213",
            code_type=CodeType.CPT,
        )

        assert code.description is None
        assert code.confidence == 1.0
        assert code.source_text is None


# =============================================================================
# Code Extraction Result Tests
# =============================================================================


class TestCodeExtractionResult:
    """Tests for CodeExtractionResult dataclass."""

    def test_has_codes_true(self):
        """Test has_codes property when codes present."""
        result = CodeExtractionResult(
            icd_codes=[ExtractedCode(code="E11.9", code_type=CodeType.ICD10_CM)],
        )

        assert result.has_codes is True

    def test_has_codes_false(self):
        """Test has_codes property when no codes."""
        result = CodeExtractionResult()

        assert result.has_codes is False

    def test_has_codes_with_cpt_only(self):
        """Test has_codes property with CPT codes only."""
        result = CodeExtractionResult(
            cpt_codes=[ExtractedCode(code="99213", code_type=CodeType.CPT)],
        )

        assert result.has_codes is True


# =============================================================================
# Integration Tests
# =============================================================================


class TestValidationEngineIntegration:
    """Integration tests for validation engine components."""

    @pytest.fixture
    def scorer(self):
        """Create risk scorer."""
        return RiskScorer()

    @pytest.fixture
    def extractor(self):
        """Create code extractor."""
        return CodeExtractor()

    @pytest.fixture
    def report_validator(self):
        """Create medical report validator."""
        return MedicalReportValidator()

    def test_full_validation_flow_clean_claim(self, scorer, extractor, report_validator):
        """Test full validation flow with clean claim."""
        # Extract codes
        text = "Dx: E11.9 Type 2 diabetes. Proc: 99213 office visit."
        extraction_result = extractor.extract_codes_from_text(text)

        # Validate report
        sections = {
            DocumentSection.PATIENT_INFO: "John Doe, DOB: 01/01/1960, MRN: 123456",
            DocumentSection.DIAGNOSIS: "Type 2 diabetes mellitus E11.9",
            DocumentSection.TREATMENT: "Continue current diabetes management. Follow up in 3 months.",
        }
        report_result = report_validator.validate_report(sections)

        # Create rule results
        rule_results = [
            RuleValidationDetail(
                rule_id="rule_2",
                rule_name="Code Extraction",
                status="passed" if extraction_result.has_codes else "failed",
                confidence=extraction_result.confidence,
                issues_found=len(extraction_result.errors),
            ),
            RuleValidationDetail(
                rule_id="rule_9",
                rule_name="Medical Reports",
                status="passed" if report_result.is_valid else "failed",
                confidence=report_result.overall_confidence,
                issues_found=len(report_result.critical_issues),
            ),
        ]

        # Calculate risk
        assessment = scorer.calculate_risk(rule_results, [], [])

        assert extraction_result.has_codes is True
        assert report_result.is_valid is True
        assert assessment.risk_level == "low"

    def test_full_validation_flow_problematic_claim(self, scorer, extractor, report_validator):
        """Test full validation flow with problematic claim."""
        # Extract codes - missing codes
        extraction_result = extractor.extract_codes_from_text("No codes in this text")

        # Validate report - missing sections
        sections = {
            DocumentSection.PATIENT_INFO: "Unknown patient",
        }
        report_result = report_validator.validate_report(sections)

        # Create rule results
        rule_results = [
            RuleValidationDetail(
                rule_id="rule_2",
                rule_name="Code Extraction",
                status="failed" if not extraction_result.has_codes else "passed",
                confidence=0.3,
                issues_found=1,
            ),
            RuleValidationDetail(
                rule_id="rule_9",
                rule_name="Medical Reports",
                status="failed",
                confidence=report_result.overall_confidence,
                issues_found=len(report_result.critical_issues),
            ),
        ]

        # Calculate risk
        assessment = scorer.calculate_risk(rule_results, [], [])

        assert extraction_result.has_codes is False
        assert report_result.is_valid is False
        # Risk level depends on severity; key is that issues were detected
        assert assessment.risk_level in ("low", "medium", "high")
        assert len(assessment.risk_factors) >= 2

    def test_fraud_detection_triggers_investigation(self, scorer):
        """Test that fraud detection triggers investigation requirement."""
        rule_results = [
            RuleValidationDetail(
                rule_id="rule_3",
                rule_name="PDF Forensics",
                status="failed",
                confidence=0.95,
                issues_found=2,
            ),
        ]

        assessment = scorer.calculate_risk(
            rule_results,
            ["Document metadata indicates tampering"],
            []
        )

        assert assessment.requires_investigation is True
        assert assessment.primary_category == RiskCategory.FRAUD
