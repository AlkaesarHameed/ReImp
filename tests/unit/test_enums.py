"""
Unit tests for core enumerations.
"""

import pytest

from src.core.enums import (
    AuditAction,
    BenefitClass,
    ClaimPriority,
    ClaimSource,
    ClaimStatus,
    ClaimType,
    CodingStandard,
    CoverageType,
    DiagnosisCodeSystem,
    DocumentType,
    FWARiskLevel,
    Gender,
    IntegrationMode,
    LLMProvider,
    MemberStatus,
    NetworkTier,
    NetworkType,
    OCRProvider,
    PaymentMethod,
    PaymentStatus,
    Permission,
    PolicyStatus,
    ProcedureCodeSystem,
    ProviderNetworkStatus,
    ProviderStatus,
    ProviderType,
    Relationship,
    Role,
    Specialty,
    TenantStatus,
    TranslationProvider,
)


class TestProviderEnums:
    """Tests for AI/ML provider enums."""

    def test_llm_provider_values(self):
        """Test LLM provider enum values."""
        assert LLMProvider.OLLAMA == "ollama"
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.ANTHROPIC == "anthropic"
        assert LLMProvider.AZURE_OPENAI == "azure_openai"

    def test_ocr_provider_values(self):
        """Test OCR provider enum values."""
        assert OCRProvider.PADDLEOCR == "paddleocr"
        assert OCRProvider.AZURE_DI == "azure_di"
        assert OCRProvider.TESSERACT == "tesseract"

    def test_translation_provider_values(self):
        """Test translation provider enum values."""
        assert TranslationProvider.LIBRETRANSLATE == "libretranslate"
        assert TranslationProvider.AZURE_TRANSLATOR == "azure_translator"

    def test_provider_status_values(self):
        """Test provider status enum values."""
        assert ProviderStatus.HEALTHY == "healthy"
        assert ProviderStatus.DEGRADED == "degraded"
        assert ProviderStatus.UNHEALTHY == "unhealthy"


class TestIntegrationModeEnum:
    """Tests for integration mode enum."""

    def test_demo_mode(self):
        """Test demo mode value."""
        assert IntegrationMode.DEMO == "demo"

    def test_live_mode(self):
        """Test live mode value."""
        assert IntegrationMode.LIVE == "live"


class TestClaimEnums:
    """Tests for claim-related enums."""

    def test_claim_type_values(self):
        """Test claim type enum values."""
        assert ClaimType.PROFESSIONAL == "professional"
        assert ClaimType.INSTITUTIONAL == "institutional"
        assert ClaimType.DENTAL == "dental"
        assert ClaimType.PHARMACY == "pharmacy"

    def test_claim_status_count(self):
        """Test claim status has expected number of states."""
        statuses = list(ClaimStatus)
        assert len(statuses) == 11

    def test_claim_status_transitions(self):
        """Test that key claim statuses exist."""
        assert ClaimStatus.DRAFT.value == "draft"
        assert ClaimStatus.SUBMITTED.value == "submitted"
        assert ClaimStatus.APPROVED.value == "approved"
        assert ClaimStatus.DENIED.value == "denied"
        assert ClaimStatus.PAID.value == "paid"
        assert ClaimStatus.CLOSED.value == "closed"

    def test_claim_priority_values(self):
        """Test claim priority enum values."""
        assert ClaimPriority.NORMAL == "normal"
        assert ClaimPriority.URGENT == "urgent"
        assert ClaimPriority.EXPEDITED == "expedited"

    def test_claim_source_values(self):
        """Test claim source enum values."""
        assert ClaimSource.PORTAL == "portal"
        assert ClaimSource.API == "api"
        assert ClaimSource.EDI == "edi"


class TestPolicyEnums:
    """Tests for policy-related enums."""

    def test_benefit_class_values(self):
        """Test benefit class enum values."""
        assert BenefitClass.BRONZE == "bronze"
        assert BenefitClass.SILVER == "silver"
        assert BenefitClass.GOLD == "gold"
        assert BenefitClass.PLATINUM == "platinum"
        assert BenefitClass.VIP == "vip"

    def test_policy_status_values(self):
        """Test policy status enum values."""
        assert PolicyStatus.ACTIVE == "active"
        assert PolicyStatus.SUSPENDED == "suspended"
        assert PolicyStatus.EXPIRED == "expired"
        assert PolicyStatus.CANCELLED == "cancelled"

    def test_coverage_type_values(self):
        """Test coverage type enum values."""
        coverage_types = list(CoverageType)
        assert len(coverage_types) >= 6
        assert CoverageType.INPATIENT == "inpatient"
        assert CoverageType.OUTPATIENT == "outpatient"

    def test_network_type_values(self):
        """Test network type enum values."""
        assert NetworkType.PPO == "ppo"
        assert NetworkType.HMO == "hmo"
        assert NetworkType.EPO == "epo"


class TestMemberEnums:
    """Tests for member-related enums."""

    def test_member_status_values(self):
        """Test member status enum values."""
        assert MemberStatus.ACTIVE == "active"
        assert MemberStatus.INACTIVE == "inactive"
        assert MemberStatus.TERMINATED == "terminated"
        assert MemberStatus.COBRA == "cobra"

    def test_relationship_values(self):
        """Test relationship enum values."""
        assert Relationship.SELF == "self"
        assert Relationship.SPOUSE == "spouse"
        assert Relationship.CHILD == "child"

    def test_gender_values(self):
        """Test gender enum values."""
        assert Gender.MALE == "male"
        assert Gender.FEMALE == "female"
        assert Gender.OTHER == "other"


class TestCodingEnums:
    """Tests for medical coding enums."""

    def test_coding_standard_values(self):
        """Test coding standard enum values."""
        assert CodingStandard.US == "us"
        assert CodingStandard.AU == "au"

    def test_diagnosis_code_system_values(self):
        """Test diagnosis code system enum values."""
        assert DiagnosisCodeSystem.ICD10_CM == "icd10_cm"
        assert DiagnosisCodeSystem.ICD10_AM == "icd10_am"

    def test_procedure_code_system_values(self):
        """Test procedure code system enum values."""
        assert ProcedureCodeSystem.CPT == "cpt"
        assert ProcedureCodeSystem.HCPCS == "hcpcs"
        assert ProcedureCodeSystem.ACHI == "achi"


class TestFWAEnums:
    """Tests for FWA (Fraud, Waste, Abuse) enums."""

    def test_fwa_risk_level_values(self):
        """Test FWA risk level enum values."""
        assert FWARiskLevel.LOW == "low"
        assert FWARiskLevel.MEDIUM == "medium"
        assert FWARiskLevel.HIGH == "high"
        assert FWARiskLevel.CRITICAL == "critical"


class TestRBACEnums:
    """Tests for RBAC enums."""

    def test_role_values(self):
        """Test role enum values."""
        assert Role.SUPER_ADMIN == "super_admin"
        assert Role.TENANT_ADMIN == "tenant_admin"
        assert Role.CLAIMS_PROCESSOR == "claims_processor"
        assert Role.VIEWER == "viewer"

    def test_permission_values(self):
        """Test permission enum values follow pattern."""
        # Claims permissions
        assert Permission.CLAIMS_READ == "claims:read"
        assert Permission.CLAIMS_CREATE == "claims:create"
        assert Permission.CLAIMS_APPROVE == "claims:approve"

        # Documents permissions
        assert Permission.DOCUMENTS_READ == "documents:read"
        assert Permission.DOCUMENTS_UPLOAD == "documents:upload"

        # Admin permissions
        assert Permission.ADMIN_USERS == "admin:users"
        assert Permission.ADMIN_TENANTS == "admin:tenants"


class TestAuditEnums:
    """Tests for audit-related enums."""

    def test_audit_action_values(self):
        """Test audit action enum values."""
        assert AuditAction.CREATE == "create"
        assert AuditAction.READ == "read"
        assert AuditAction.UPDATE == "update"
        assert AuditAction.DELETE == "delete"
        assert AuditAction.APPROVE == "approve"
        assert AuditAction.DENY == "deny"


class TestPaymentEnums:
    """Tests for payment-related enums."""

    def test_payment_status_values(self):
        """Test payment status enum values."""
        assert PaymentStatus.PENDING == "pending"
        assert PaymentStatus.PROCESSING == "processing"
        assert PaymentStatus.COMPLETED == "completed"
        assert PaymentStatus.FAILED == "failed"

    def test_payment_method_values(self):
        """Test payment method enum values."""
        assert PaymentMethod.ACH == "ach"
        assert PaymentMethod.CHECK == "check"
        assert PaymentMethod.WIRE == "wire"
