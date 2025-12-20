"""
Pydantic Schemas for Claims Processing System.

This module exports all request/response schemas for the API.
"""

from src.schemas.auth import TokenResponse, UserLogin, UserRegister
from src.schemas.user import UserCreate, UserResponse, UserUpdate
from src.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate

# Claims Processing Schemas
from src.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListResponse,
    TenantStatusUpdate,
    TenantSettingsUpdate,
    TenantSettingsResponse,
)
from src.schemas.policy import (
    PolicyCreate,
    PolicyUpdate,
    PolicyResponse,
    PolicyListResponse,
    PolicyBulkUpload,
    PolicyUploadResult,
    CoverageLimitCreate,
    CoverageLimitResponse,
)
from src.schemas.member import (
    MemberCreate,
    MemberUpdate,
    MemberResponse,
    MemberListResponse,
    MemberBulkUpload,
    EligibilityCheckRequest,
    EligibilityCheckResponse,
)
from src.schemas.healthcare_provider import (
    ProviderCreate,
    ProviderUpdate,
    ProviderResponse,
    ProviderListResponse,
    ProviderBulkUpload,
    NPIVerifyRequest,
    NPIVerifyResponse,
)
from src.schemas.claim import (
    ClaimCreate,
    ClaimUpdate,
    ClaimResponse,
    ClaimListResponse,
    ClaimSubmitResponse,
    ClaimStatusResponse,
    ClaimAdjudicate,
    ClaimLineItemCreate,
    ClaimLineItemResponse,
    ClaimDocumentResponse,
    ClaimStatusHistoryResponse,
    ClaimProcessingResult,
    AdjudicationResult,
    MedicalReviewResult,
    FWAAnalysisResult,
    PatientInfo,
    ProviderInfo,
)
from src.schemas.permission import (
    PermissionCreate,
    PermissionUpdate,
    PermissionResponse,
    PermissionListResponse,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleListResponse,
    RoleSummary,
    RolePermissionsUpdate,
    UserRoleAssign,
    UserRoleResponse,
    UserRolesResponse,
    UserPermissionsCheck,
    UserPermissionsCheckResult,
    TokenClaims,
    TokenClaimsCreate,
    RequiredPermission,
    PermissionDenied,
)

# EDI Schemas
# Source: Design Document 06_high_value_enhancements_design.md
from src.schemas.edi import (
    EDI837SubmitRequest,
    EDI837ProcessResult,
    EDI837ValidationResult,
    EDI835GenerateRequest,
    EDI835GenerateResult,
    EDI835RetrieveResponse,
    EDITransactionResponse,
    EDITransactionListResponse,
    EDITransactionStats,
    ParsedClaim837Response,
)

__all__ = [
    # Auth
    "TokenResponse",
    "UserLogin",
    "UserRegister",
    # User
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    # Document
    "DocumentCreate",
    "DocumentResponse",
    "DocumentUpdate",
    # Tenant
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    "TenantListResponse",
    "TenantStatusUpdate",
    "TenantSettingsUpdate",
    "TenantSettingsResponse",
    # Policy
    "PolicyCreate",
    "PolicyUpdate",
    "PolicyResponse",
    "PolicyListResponse",
    "PolicyBulkUpload",
    "PolicyUploadResult",
    "CoverageLimitCreate",
    "CoverageLimitResponse",
    # Member
    "MemberCreate",
    "MemberUpdate",
    "MemberResponse",
    "MemberListResponse",
    "MemberBulkUpload",
    "EligibilityCheckRequest",
    "EligibilityCheckResponse",
    # Provider
    "ProviderCreate",
    "ProviderUpdate",
    "ProviderResponse",
    "ProviderListResponse",
    "ProviderBulkUpload",
    "NPIVerifyRequest",
    "NPIVerifyResponse",
    # Claim
    "ClaimCreate",
    "ClaimUpdate",
    "ClaimResponse",
    "ClaimListResponse",
    "ClaimSubmitResponse",
    "ClaimStatusResponse",
    "ClaimAdjudicate",
    "ClaimLineItemCreate",
    "ClaimLineItemResponse",
    "ClaimDocumentResponse",
    "ClaimStatusHistoryResponse",
    "ClaimProcessingResult",
    "AdjudicationResult",
    "MedicalReviewResult",
    "FWAAnalysisResult",
    "PatientInfo",
    "ProviderInfo",
    # Permission/Role
    "PermissionCreate",
    "PermissionUpdate",
    "PermissionResponse",
    "PermissionListResponse",
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
    "RoleListResponse",
    "RoleSummary",
    "RolePermissionsUpdate",
    "UserRoleAssign",
    "UserRoleResponse",
    "UserRolesResponse",
    "UserPermissionsCheck",
    "UserPermissionsCheckResult",
    "TokenClaims",
    "TokenClaimsCreate",
    "RequiredPermission",
    "PermissionDenied",
    # EDI
    "EDI837SubmitRequest",
    "EDI837ProcessResult",
    "EDI837ValidationResult",
    "EDI835GenerateRequest",
    "EDI835GenerateResult",
    "EDI835RetrieveResponse",
    "EDITransactionResponse",
    "EDITransactionListResponse",
    "EDITransactionStats",
    "ParsedClaim837Response",
]
