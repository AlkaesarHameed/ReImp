"""
Eligibility Verification Service.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Orchestrates X12 270/271 eligibility verification:
- Generate eligibility inquiries
- Parse eligibility responses
- Cache and track eligibility status
- Integrate with claim processing
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
import logging
import asyncio

from src.services.edi.x12_270_generator import (
    X12270Generator,
    EligibilityInquiry,
    InquirySubscriber,
    InquiryProvider,
    InquiryPayer,
    InquiryDependent,
    ServiceTypeCode,
)
from src.services.edi.x12_271_parser import (
    X12271Parser,
    EligibilityResponse,
    EligibilityStatus,
    BenefitInfo,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Models
# =============================================================================


class EligibilityCheckStatus(str, Enum):
    """Status of eligibility check."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CACHED = "cached"


class EligibilityResultType(str, Enum):
    """Type of eligibility result."""
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    COVERAGE_TERMINATED = "coverage_terminated"
    MEMBER_NOT_FOUND = "member_not_found"
    PAYER_ERROR = "payer_error"
    UNKNOWN = "unknown"


@dataclass
class CoverageDetail:
    """Coverage detail from eligibility response."""
    service_type: str
    service_description: Optional[str] = None
    covered: bool = True
    in_network: Optional[bool] = None
    authorization_required: bool = False
    deductible: Optional[Decimal] = None
    deductible_remaining: Optional[Decimal] = None
    copay: Optional[Decimal] = None
    coinsurance_percent: Optional[Decimal] = None
    out_of_pocket_max: Optional[Decimal] = None
    out_of_pocket_remaining: Optional[Decimal] = None


@dataclass
class EligibilityCheckResult:
    """Result of eligibility verification."""
    # Identification
    check_id: str
    member_id: str
    payer_id: str

    # Status
    status: EligibilityCheckStatus
    result_type: EligibilityResultType
    is_eligible: bool

    # Coverage dates
    coverage_start: Optional[date] = None
    coverage_end: Optional[date] = None
    is_coverage_active: bool = False

    # Member info
    subscriber_name: Optional[str] = None
    group_number: Optional[str] = None
    group_name: Optional[str] = None
    plan_name: Optional[str] = None

    # Coverage details
    coverage_details: List[CoverageDetail] = field(default_factory=list)

    # Benefits summary
    deductible: Optional[Decimal] = None
    deductible_met: Optional[Decimal] = None
    out_of_pocket_max: Optional[Decimal] = None
    out_of_pocket_met: Optional[Decimal] = None

    # Raw data
    raw_response: Optional[EligibilityResponse] = None
    response_x12: Optional[str] = None

    # Errors
    errors: List[str] = field(default_factory=list)
    payer_message: Optional[str] = None

    # Metadata
    checked_at: datetime = field(default_factory=datetime.utcnow)
    cached: bool = False
    cache_expires_at: Optional[datetime] = None
    processing_time_ms: int = 0


@dataclass
class EligibilityRequest:
    """Request for eligibility verification."""
    # Member identification
    member_id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    group_number: Optional[str] = None

    # Dependent (if checking for dependent)
    dependent_first_name: Optional[str] = None
    dependent_last_name: Optional[str] = None
    dependent_dob: Optional[date] = None
    dependent_gender: Optional[str] = None

    # Provider
    provider_npi: str = ""
    provider_name: str = ""

    # Payer
    payer_id: str = ""
    payer_name: str = ""

    # Service
    service_date: date = field(default_factory=date.today)
    service_type_codes: List[ServiceTypeCode] = field(
        default_factory=lambda: [ServiceTypeCode.HEALTH_BENEFIT_PLAN_COVERAGE]
    )


# =============================================================================
# Service
# =============================================================================


class EligibilityService:
    """
    Eligibility Verification Service.

    Handles X12 270/271 eligibility verification workflow:
    - Generates 270 eligibility inquiry
    - Sends to payer (mock/real)
    - Parses 271 response
    - Caches results for performance

    Usage:
        service = EligibilityService()
        result = await service.check_eligibility(
            EligibilityRequest(
                member_id="MEM123",
                first_name="John",
                last_name="Doe",
                payer_id="PAYER1",
                ...
            )
        )
        if result.is_eligible:
            print("Member is eligible")
    """

    def __init__(
        self,
        db_session=None,
        cache_service=None,
        payer_gateway=None,
        cache_ttl_minutes: int = 60,
    ):
        """
        Initialize eligibility service.

        Args:
            db_session: Database session for logging
            cache_service: Redis/memory cache for caching results
            payer_gateway: Gateway for sending/receiving from payers
            cache_ttl_minutes: Cache TTL in minutes (default 60)
        """
        self.db = db_session
        self.cache = cache_service
        self.payer_gateway = payer_gateway
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.generator_270 = X12270Generator()
        self.parser_271 = X12271Parser()

        # In-memory cache for demo/testing
        self._memory_cache: Dict[str, EligibilityCheckResult] = {}

    async def check_eligibility(
        self,
        request: EligibilityRequest,
        tenant_id: Optional[UUID] = None,
        use_cache: bool = True,
    ) -> EligibilityCheckResult:
        """
        Check member eligibility.

        Args:
            request: Eligibility request with member/payer info
            tenant_id: Tenant ID for multi-tenancy
            use_cache: Whether to use cached results

        Returns:
            EligibilityCheckResult with eligibility status
        """
        start_time = datetime.utcnow()
        check_id = str(uuid4())

        # Check cache first
        if use_cache:
            cached = await self._get_cached_result(request)
            if cached:
                cached.check_id = check_id
                cached.cached = True
                logger.info(f"Eligibility check {check_id}: Cache hit for {request.member_id}")
                return cached

        try:
            logger.info(f"Eligibility check {check_id}: Starting for member {request.member_id}")

            # Generate 270 inquiry
            inquiry = self._build_inquiry(request)
            x12_270 = self.generator_270.generate(inquiry)

            # Send to payer and get response
            x12_271 = await self._send_to_payer(x12_270, request.payer_id)

            # Parse 271 response
            response = self.parser_271.parse(x12_271)

            # Build result
            result = self._build_result(
                check_id=check_id,
                request=request,
                response=response,
                x12_271=x12_271,
            )

            # Calculate processing time
            result.processing_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            # Cache the result
            if use_cache and result.status == EligibilityCheckStatus.COMPLETED:
                await self._cache_result(request, result)

            # Log to database
            if self.db:
                await self._log_eligibility_check(tenant_id, request, result)

            logger.info(
                f"Eligibility check {check_id}: Completed - "
                f"eligible={result.is_eligible}, status={result.result_type}"
            )

            return result

        except Exception as e:
            logger.error(f"Eligibility check {check_id} failed: {e}", exc_info=True)

            processing_time = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            return EligibilityCheckResult(
                check_id=check_id,
                member_id=request.member_id,
                payer_id=request.payer_id,
                status=EligibilityCheckStatus.FAILED,
                result_type=EligibilityResultType.PAYER_ERROR,
                is_eligible=False,
                errors=[str(e)],
                processing_time_ms=processing_time,
            )

    async def check_eligibility_batch(
        self,
        requests: List[EligibilityRequest],
        tenant_id: Optional[UUID] = None,
        concurrency: int = 5,
    ) -> List[EligibilityCheckResult]:
        """
        Check eligibility for multiple members.

        Args:
            requests: List of eligibility requests
            tenant_id: Tenant ID for multi-tenancy
            concurrency: Max concurrent checks

        Returns:
            List of eligibility results
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def check_with_semaphore(request):
            async with semaphore:
                return await self.check_eligibility(request, tenant_id)

        tasks = [check_with_semaphore(req) for req in requests]
        return await asyncio.gather(*tasks)

    async def verify_for_claim(
        self,
        member_id: str,
        payer_id: str,
        service_date: date,
        service_type_codes: Optional[List[ServiceTypeCode]] = None,
        tenant_id: Optional[UUID] = None,
    ) -> EligibilityCheckResult:
        """
        Quick eligibility verification for claim processing.

        Simplified method for use during claim adjudication.

        Args:
            member_id: Member ID
            payer_id: Payer ID
            service_date: Date of service
            service_type_codes: Service types to check
            tenant_id: Tenant ID

        Returns:
            EligibilityCheckResult
        """
        # In production, would lookup member info from database
        request = EligibilityRequest(
            member_id=member_id,
            first_name="",  # Would be from database
            last_name="",  # Would be from database
            payer_id=payer_id,
            payer_name="",  # Would be from database
            service_date=service_date,
            service_type_codes=service_type_codes or [
                ServiceTypeCode.HEALTH_BENEFIT_PLAN_COVERAGE
            ],
        )

        return await self.check_eligibility(request, tenant_id)

    def _build_inquiry(self, request: EligibilityRequest) -> EligibilityInquiry:
        """Build EligibilityInquiry from request."""
        subscriber = InquirySubscriber(
            member_id=request.member_id,
            first_name=request.first_name,
            last_name=request.last_name,
            date_of_birth=request.date_of_birth,
            gender=request.gender,
            group_number=request.group_number,
        )

        provider = InquiryProvider(
            npi=request.provider_npi or "1234567890",  # Default for demo
            name=request.provider_name or "Provider",
        )

        payer = InquiryPayer(
            payer_id=request.payer_id,
            name=request.payer_name or "Payer",
        )

        dependent = None
        if request.dependent_first_name:
            dependent = InquiryDependent(
                first_name=request.dependent_first_name,
                last_name=request.dependent_last_name or "",
                date_of_birth=request.dependent_dob,
                gender=request.dependent_gender,
            )

        return EligibilityInquiry(
            subscriber=subscriber,
            provider=provider,
            payer=payer,
            service_date=request.service_date,
            dependent=dependent,
            service_type_codes=request.service_type_codes,
        )

    async def _send_to_payer(self, x12_270: str, payer_id: str) -> str:
        """
        Send 270 inquiry to payer and get 271 response.

        In production, this would use a payer gateway.
        For demo, returns mock response.
        """
        if self.payer_gateway:
            return await self.payer_gateway.send_eligibility_inquiry(
                x12_270, payer_id
            )

        # Mock response for demo/testing
        return self._generate_mock_271_response(x12_270)

    def _generate_mock_271_response(self, x12_270: str) -> str:
        """Generate mock 271 response for testing."""
        now = datetime.now()

        # Extract some info from 270 for response
        control_number = "000000001"
        if "ISA*" in x12_270:
            parts = x12_270.split("*")
            if len(parts) > 13:
                control_number = parts[13].replace("~", "").strip()

        # Build mock 271 response
        response = f"""ISA*00*          *00*          *ZZ*PAYER          *ZZ*PROVIDER       *{now.strftime('%y%m%d')}*{now.strftime('%H%M')}*^*00501*{control_number}*0*P*:~
GS*HB*PAYER*PROVIDER*{now.strftime('%Y%m%d')}*{now.strftime('%H%M')}*1*X*005010X279A1~
ST*271*0001*005010X279A1~
BHT*0022*11*TRN123*{now.strftime('%Y%m%d')}*{now.strftime('%H%M')}~
HL*1**20*1~
NM1*PR*2*DEMO PAYER*****PI*PAYER123~
HL*2*1*21*1~
NM1*1P*2*DEMO PROVIDER*****XX*1234567890~
HL*3*2*22*0~
TRN*1*TRACE123*9DEMOORG~
NM1*IL*1*DOE*JOHN****MI*MEM123456~
DMG*D8*19800115*M~
DTP*346*D8*20230101~
DTP*347*D8*20251231~
EB*1**30**STANDARD PPO~
EB*C*IND*30**DEDUCTIBLE*23*500~
EB*C*IND*30**DEDUCTIBLE MET*23*350~
EB*G*IND*30**OUT OF POCKET*23*3000~
EB*G*IND*30**OUT OF POCKET MET*23*500~
EB*A*IND*30***23*20~
EB*B*IND*30***23*30~
MSG*MEMBER IS ELIGIBLE FOR BENEFITS~
SE*20*0001~
GE*1*1~
IEA*1*{control_number}~"""

        return response

    def _build_result(
        self,
        check_id: str,
        request: EligibilityRequest,
        response: EligibilityResponse,
        x12_271: str,
    ) -> EligibilityCheckResult:
        """Build EligibilityCheckResult from parsed response."""
        result = EligibilityCheckResult(
            check_id=check_id,
            member_id=request.member_id,
            payer_id=request.payer_id,
            status=EligibilityCheckStatus.COMPLETED,
            result_type=EligibilityResultType.UNKNOWN,
            is_eligible=response.is_eligible,
            is_coverage_active=response.coverage_active,
            coverage_start=response.plan_begin_date,
            coverage_end=response.plan_end_date,
            raw_response=response,
            response_x12=x12_271,
            errors=response.errors,
        )

        # Set result type
        if response.is_eligible:
            result.result_type = EligibilityResultType.ELIGIBLE
        elif response.rejection_reason:
            if "not found" in response.rejection_reason.lower():
                result.result_type = EligibilityResultType.MEMBER_NOT_FOUND
            else:
                result.result_type = EligibilityResultType.NOT_ELIGIBLE
        elif not response.coverage_active:
            result.result_type = EligibilityResultType.COVERAGE_TERMINATED
        else:
            result.result_type = EligibilityResultType.NOT_ELIGIBLE

        # Extract subscriber info
        if response.subscriber:
            result.subscriber_name = f"{response.subscriber.first_name} {response.subscriber.last_name}".strip()
            result.group_number = response.subscriber.group_number
            result.group_name = response.subscriber.group_name

        # Extract benefits
        for benefit in response.benefits:
            self._process_benefit(benefit, result)

        return result

    def _process_benefit(self, benefit: BenefitInfo, result: EligibilityCheckResult) -> None:
        """Process individual benefit and update result."""
        # Create coverage detail
        detail = CoverageDetail(
            service_type=benefit.service_type_code or "30",
            service_description=benefit.service_type_description,
            in_network=benefit.in_plan_network,
            authorization_required=benefit.authorization_required,
        )

        # Process by status
        if benefit.status == EligibilityStatus.DEDUCTIBLE:
            if benefit.monetary_amount:
                if result.deductible is None:
                    result.deductible = benefit.monetary_amount
                elif "met" in (benefit.message or "").lower():
                    result.deductible_met = benefit.monetary_amount
            detail.deductible = benefit.monetary_amount

        elif benefit.status == EligibilityStatus.OUT_OF_POCKET_STOP_LOSS:
            if benefit.monetary_amount:
                if result.out_of_pocket_max is None:
                    result.out_of_pocket_max = benefit.monetary_amount
                elif "met" in (benefit.message or "").lower():
                    result.out_of_pocket_met = benefit.monetary_amount

        elif benefit.status == EligibilityStatus.COINSURANCE:
            if benefit.percent:
                detail.coinsurance_percent = benefit.percent

        elif benefit.status == EligibilityStatus.COPAYMENT:
            if benefit.monetary_amount:
                detail.copay = benefit.monetary_amount

        elif benefit.status == EligibilityStatus.NON_COVERED:
            detail.covered = False

        if benefit.message:
            result.payer_message = benefit.message

        result.coverage_details.append(detail)

    def _get_cache_key(self, request: EligibilityRequest) -> str:
        """Generate cache key for eligibility request."""
        return f"elig:{request.payer_id}:{request.member_id}:{request.service_date.isoformat()}"

    async def _get_cached_result(
        self, request: EligibilityRequest
    ) -> Optional[EligibilityCheckResult]:
        """Get cached eligibility result."""
        key = self._get_cache_key(request)

        if self.cache:
            # Use Redis/external cache
            cached = await self.cache.get(key)
            if cached:
                return cached

        # Check memory cache
        if key in self._memory_cache:
            result = self._memory_cache[key]
            if result.cache_expires_at and result.cache_expires_at > datetime.utcnow():
                return result
            else:
                del self._memory_cache[key]

        return None

    async def _cache_result(
        self, request: EligibilityRequest, result: EligibilityCheckResult
    ) -> None:
        """Cache eligibility result."""
        key = self._get_cache_key(request)
        result.cache_expires_at = datetime.utcnow() + self.cache_ttl

        if self.cache:
            await self.cache.set(key, result, ttl=int(self.cache_ttl.total_seconds()))

        # Also store in memory cache
        self._memory_cache[key] = result

    async def _log_eligibility_check(
        self,
        tenant_id: Optional[UUID],
        request: EligibilityRequest,
        result: EligibilityCheckResult,
    ) -> None:
        """Log eligibility check to database."""
        # Would insert into eligibility_checks table
        logger.debug(
            f"Logging eligibility check: tenant={tenant_id}, "
            f"member={request.member_id}, result={result.result_type}"
        )

    def clear_cache(self) -> None:
        """Clear eligibility cache."""
        self._memory_cache.clear()


# =============================================================================
# Factory Function
# =============================================================================


_eligibility_service: Optional[EligibilityService] = None


def get_eligibility_service(
    db_session=None,
    cache_service=None,
    payer_gateway=None,
) -> EligibilityService:
    """
    Get or create eligibility service instance.

    Args:
        db_session: Database session
        cache_service: Cache service
        payer_gateway: Payer gateway

    Returns:
        EligibilityService instance
    """
    global _eligibility_service

    if _eligibility_service is None:
        _eligibility_service = EligibilityService(
            db_session=db_session,
            cache_service=cache_service,
            payer_gateway=payer_gateway,
        )

    return _eligibility_service
