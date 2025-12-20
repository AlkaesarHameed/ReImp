"""
X12 EDI Services for Claims Processing.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Provides X12 EDI integration:
- 837P/837I claim parsing (inbound)
- 835 remittance generation (outbound)
- 270/271 eligibility (bidirectional)
"""

from src.services.edi.x12_base import (
    X12Segment,
    X12Loop,
    X12Transaction,
    X12Tokenizer,
    TransactionType,
    X12ValidationError,
    X12ParseError,
)
from src.services.edi.x12_837_parser import (
    X12837Parser,
    ParsedClaim837,
    ServiceLine837,
    DiagnosisInfo,
    ProviderInfo,
    SubscriberInfo,
)
from src.services.edi.x12_835_generator import (
    X12835Generator,
    RemittanceAdvice,
    ClaimPayment,
    ServicePayment,
)
from src.services.edi.edi_service import (
    EDIService,
    get_edi_service,
)
from src.services.edi.x12_270_generator import (
    X12270Generator,
    EligibilityInquiry,
    InquirySubscriber,
    InquiryProvider,
    InquiryPayer,
    ServiceTypeCode,
)
from src.services.edi.x12_271_parser import (
    X12271Parser,
    EligibilityResponse,
    EligibilityStatus,
    BenefitInfo,
)
from src.services.edi.eligibility_service import (
    EligibilityService,
    EligibilityRequest,
    EligibilityCheckResult,
    EligibilityCheckStatus,
    EligibilityResultType,
    get_eligibility_service,
)

__all__ = [
    # Base
    "X12Segment",
    "X12Loop",
    "X12Transaction",
    "X12Tokenizer",
    "TransactionType",
    "X12ValidationError",
    "X12ParseError",
    # 837 Parser
    "X12837Parser",
    "ParsedClaim837",
    "ServiceLine837",
    "DiagnosisInfo",
    "ProviderInfo",
    "SubscriberInfo",
    # 835 Generator
    "X12835Generator",
    "RemittanceAdvice",
    "ClaimPayment",
    "ServicePayment",
    # EDI Service
    "EDIService",
    "get_edi_service",
    # 270 Generator
    "X12270Generator",
    "EligibilityInquiry",
    "InquirySubscriber",
    "InquiryProvider",
    "InquiryPayer",
    "ServiceTypeCode",
    # 271 Parser
    "X12271Parser",
    "EligibilityResponse",
    "EligibilityStatus",
    "BenefitInfo",
    # Eligibility Service
    "EligibilityService",
    "EligibilityRequest",
    "EligibilityCheckResult",
    "EligibilityCheckStatus",
    "EligibilityResultType",
    "get_eligibility_service",
]
