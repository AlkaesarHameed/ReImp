"""
Core Enumerations for Claims Processing System.
Source: Design Document 01_configurable_claims_processing_design.md
Verified: 2025-12-18
"""

from enum import Enum


# =============================================================================
# Provider Configuration Enums
# =============================================================================


class LLMProvider(str, Enum):
    """Available LLM providers for document parsing and analysis."""

    OLLAMA = "ollama"  # Primary: Qwen2.5-VL via Ollama
    OPENAI = "openai"  # Fallback: GPT-4 Vision
    ANTHROPIC = "anthropic"  # Alternative: Claude
    AZURE_OPENAI = "azure_openai"  # Enterprise: Azure OpenAI


class OCRProvider(str, Enum):
    """Available OCR providers for document text extraction."""

    TESSERACT = "tesseract"  # Primary: Open-source, widely available
    PADDLEOCR = "paddleocr"  # Alternative: PaddlePaddle-based
    AZURE_DI = "azure_di"  # Fallback: Azure Document Intelligence


class TranslationProvider(str, Enum):
    """Available translation providers for i18n."""

    LIBRETRANSLATE = "libretranslate"  # Primary: Open-source
    AZURE_TRANSLATOR = "azure_translator"  # Fallback: Commercial
    GOOGLE_TRANSLATE = "google_translate"  # Alternative: Commercial


class RulesEngineProvider(str, Enum):
    """Available rules engine providers."""

    ZEN = "zen"  # Primary: GoRules ZEN
    PYTHON = "python"  # Fallback: Custom Python rules


class MedicalNLPProvider(str, Enum):
    """Available medical NLP providers."""

    MEDCAT = "medcat"  # Primary: UMLS-based
    MEDSPACY = "medspacy"  # Fallback: Non-UMLS
    AWS_COMPREHEND = "aws_comprehend"  # Commercial alternative


class CurrencyProvider(str, Enum):
    """Available currency conversion providers."""

    FAWAZAHMED = "fawazahmed"  # Primary: Free API
    FIXER = "fixer"  # Fallback: Commercial
    EXCHANGERATE = "exchangerate"  # Alternative


# =============================================================================
# Integration Mode Enums
# =============================================================================


class IntegrationMode(str, Enum):
    """System integration mode."""

    DEMO = "demo"  # Demo mode: local database, simulated external systems
    LIVE = "live"  # Live mode: real external system integrations


class ProviderStatus(str, Enum):
    """Health status of a provider."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# =============================================================================
# Claim Processing Enums
# =============================================================================


class ClaimType(str, Enum):
    """Types of insurance claims."""

    PROFESSIONAL = "professional"  # CMS-1500 style claims
    INSTITUTIONAL = "institutional"  # UB-04 style claims
    DENTAL = "dental"  # Dental claims (ADA form)
    PHARMACY = "pharmacy"  # Pharmacy/prescription claims


class ClaimStatus(str, Enum):
    """Claim lifecycle status.

    State Machine Transitions:
    DRAFT -> SUBMITTED
    SUBMITTED -> DOC_PROCESSING
    DOC_PROCESSING -> VALIDATING | NEEDS_REVIEW
    VALIDATING -> ADJUDICATING | DENIED
    ADJUDICATING -> APPROVED | DENIED | NEEDS_REVIEW
    APPROVED -> PAYMENT_PROCESSING
    PAYMENT_PROCESSING -> PAID | NEEDS_REVIEW
    PAID -> CLOSED
    NEEDS_REVIEW -> APPROVED | DENIED
    DENIED -> CLOSED
    """

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


class ClaimPriority(str, Enum):
    """Claim processing priority."""

    NORMAL = "normal"
    URGENT = "urgent"
    EXPEDITED = "expedited"


class ClaimSource(str, Enum):
    """Source of claim submission."""

    PORTAL = "portal"  # Web portal submission
    API = "api"  # Direct API submission
    EDI = "edi"  # EDI 837 transaction
    FAX = "fax"  # Faxed/scanned submission
    MAIL = "mail"  # Mailed paper claim


# =============================================================================
# Document Processing Enums
# =============================================================================


class DocumentType(str, Enum):
    """Types of documents that can be processed."""

    CLAIM_FORM = "claim_form"  # CMS-1500, UB-04, etc.
    INVOICE = "invoice"  # Provider invoice
    PRESCRIPTION = "prescription"  # Rx prescription
    LAB_RESULT = "lab_result"  # Laboratory results
    MEDICAL_RECORD = "medical_record"  # Medical records
    EOB = "eob"  # Explanation of Benefits
    AUTHORIZATION = "authorization"  # Prior authorization
    OTHER = "other"


class DocumentStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# Policy & Benefit Enums
# =============================================================================


class BenefitClass(str, Enum):
    """Insurance benefit class tiers."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    VIP = "vip"


class PolicyStatus(str, Enum):
    """Policy lifecycle status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"


class CoverageType(str, Enum):
    """Types of coverage within a policy."""

    INPATIENT = "inpatient"
    OUTPATIENT = "outpatient"
    DENTAL = "dental"
    OPTICAL = "optical"
    MATERNITY = "maternity"
    PHARMACY = "pharmacy"
    MENTAL_HEALTH = "mental_health"
    EMERGENCY = "emergency"


class NetworkType(str, Enum):
    """Provider network types."""

    PPO = "ppo"  # Preferred Provider Organization
    HMO = "hmo"  # Health Maintenance Organization
    EPO = "epo"  # Exclusive Provider Organization
    POS = "pos"  # Point of Service


class NetworkTier(str, Enum):
    """Provider network tiers."""

    PREFERRED = "preferred"  # Highest coverage
    IN_NETWORK = "in_network"  # Standard in-network
    OUT_OF_NETWORK = "out_of_network"  # Reduced coverage


# =============================================================================
# Provider (Healthcare) Enums
# =============================================================================


class ProviderType(str, Enum):
    """Healthcare provider types."""

    PHYSICIAN = "physician"
    HOSPITAL = "hospital"
    CLINIC = "clinic"
    LABORATORY = "laboratory"
    PHARMACY = "pharmacy"
    IMAGING_CENTER = "imaging_center"
    SPECIALIST = "specialist"
    URGENT_CARE = "urgent_care"


class Specialty(str, Enum):
    """Medical specialties."""

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
    PSYCHIATRY = "psychiatry"
    NEUROLOGY = "neurology"
    ONCOLOGY = "oncology"
    GASTROENTEROLOGY = "gastroenterology"


class ProviderNetworkStatus(str, Enum):
    """Provider's network participation status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    TERMINATED = "terminated"


# =============================================================================
# Member/Patient Enums
# =============================================================================


class MemberStatus(str, Enum):
    """Member enrollment status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"
    COBRA = "cobra"  # COBRA continuation
    PENDING = "pending"


class Relationship(str, Enum):
    """Relationship to subscriber."""

    SELF = "self"
    SPOUSE = "spouse"
    CHILD = "child"
    DOMESTIC_PARTNER = "domestic_partner"
    DEPENDENT = "dependent"
    OTHER = "other"


class Gender(str, Enum):
    """Gender options."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


# =============================================================================
# Coding System Enums
# =============================================================================


class CodingStandard(str, Enum):
    """Medical coding standards."""

    US = "us"  # ICD-10-CM, CPT, HCPCS
    AU = "au"  # ICD-10-AM, ACHI


class DiagnosisCodeSystem(str, Enum):
    """Diagnosis code systems."""

    ICD10_CM = "icd10_cm"  # US Clinical Modification
    ICD10_AM = "icd10_am"  # Australian Modification
    ICD9_CM = "icd9_cm"  # Legacy (pre-2015)


class ProcedureCodeSystem(str, Enum):
    """Procedure code systems."""

    CPT = "cpt"  # Current Procedural Terminology (US)
    HCPCS = "hcpcs"  # Healthcare Common Procedure Coding System (US)
    ACHI = "achi"  # Australian Classification of Health Interventions
    ICD10_PCS = "icd10_pcs"  # Inpatient procedures (US)
    CDT = "cdt"  # Dental codes


# =============================================================================
# Payment Enums
# =============================================================================


class PaymentStatus(str, Enum):
    """Payment processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"
    ON_HOLD = "on_hold"


class PaymentMethod(str, Enum):
    """Payment disbursement methods."""

    ACH = "ach"  # Electronic bank transfer
    CHECK = "check"  # Paper check
    WIRE = "wire"  # Wire transfer
    VIRTUAL_CARD = "virtual_card"  # Virtual payment card
    EFT = "eft"  # Electronic funds transfer


# =============================================================================
# FWA (Fraud, Waste, Abuse) Enums
# =============================================================================


class FWARiskLevel(str, Enum):
    """FWA risk classification."""

    LOW = "low"  # 0.0 - 0.3
    MEDIUM = "medium"  # 0.3 - 0.6
    HIGH = "high"  # 0.6 - 0.8
    CRITICAL = "critical"  # 0.8 - 1.0


class FWAFlagType(str, Enum):
    """Types of FWA flags."""

    DUPLICATE = "duplicate"
    UPCODING = "upcoding"
    UNBUNDLING = "unbundling"
    PHANTOM_BILLING = "phantom_billing"
    PATTERN_ANOMALY = "pattern_anomaly"
    PROVIDER_EXCLUDED = "provider_excluded"
    MEDICAL_NECESSITY = "medical_necessity"


# =============================================================================
# Audit Enums
# =============================================================================


class AuditAction(str, Enum):
    """Types of auditable actions."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SUBMIT = "submit"
    APPROVE = "approve"
    DENY = "deny"
    REVIEW = "review"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"


class AuditResourceType(str, Enum):
    """Types of auditable resources."""

    CLAIM = "claim"
    DOCUMENT = "document"
    POLICY = "policy"
    MEMBER = "member"
    PROVIDER = "provider"
    PAYMENT = "payment"
    USER = "user"
    TENANT = "tenant"
    CONFIGURATION = "configuration"


# =============================================================================
# Tenant & RBAC Enums
# =============================================================================


class TenantStatus(str, Enum):
    """Tenant account status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    CANCELLED = "cancelled"


class Role(str, Enum):
    """System roles for RBAC."""

    SUPER_ADMIN = "super_admin"  # System-wide admin
    TENANT_ADMIN = "tenant_admin"  # Tenant administrator
    CLAIMS_MANAGER = "claims_manager"  # Can manage claims
    CLAIMS_PROCESSOR = "claims_processor"  # Can process claims
    CLAIMS_REVIEWER = "claims_reviewer"  # Can review flagged claims
    VIEWER = "viewer"  # Read-only access
    API_CLIENT = "api_client"  # API-only access


class Permission(str, Enum):
    """Granular permissions for RBAC."""

    # Claims
    CLAIMS_READ = "claims:read"
    CLAIMS_CREATE = "claims:create"
    CLAIMS_UPDATE = "claims:update"
    CLAIMS_DELETE = "claims:delete"
    CLAIMS_SUBMIT = "claims:submit"
    CLAIMS_APPROVE = "claims:approve"
    CLAIMS_DENY = "claims:deny"
    CLAIMS_REVIEW = "claims:review"

    # Documents
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_UPLOAD = "documents:upload"
    DOCUMENTS_DELETE = "documents:delete"

    # Policies
    POLICIES_READ = "policies:read"
    POLICIES_CREATE = "policies:create"
    POLICIES_UPDATE = "policies:update"
    POLICIES_DELETE = "policies:delete"

    # Members
    MEMBERS_READ = "members:read"
    MEMBERS_CREATE = "members:create"
    MEMBERS_UPDATE = "members:update"
    MEMBERS_DELETE = "members:delete"

    # Providers
    PROVIDERS_READ = "providers:read"
    PROVIDERS_CREATE = "providers:create"
    PROVIDERS_UPDATE = "providers:update"
    PROVIDERS_DELETE = "providers:delete"

    # Admin
    ADMIN_USERS = "admin:users"
    ADMIN_TENANTS = "admin:tenants"
    ADMIN_CONFIGURATION = "admin:configuration"
    ADMIN_AUDIT = "admin:audit"

    # Reports
    REPORTS_VIEW = "reports:view"
    REPORTS_EXPORT = "reports:export"
