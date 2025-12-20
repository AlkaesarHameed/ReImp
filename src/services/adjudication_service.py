"""
Claim Adjudication Orchestrator Service.
Source: Design Document Section 3.4 - Claim Adjudication Pipeline
Verified: 2025-12-18

Orchestrates the complete claim adjudication process including validation,
benefit calculation, and decision determination.
"""

import time
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from src.schemas.adjudication import (
    AdjudicationContext,
    AdjudicationDecision,
    AdjudicationResult,
    AdjudicationType,
    DenialReason,
    LineItemAdjudication,
)
from src.services.adjudication_validators import (
    DuplicateClaimChecker,
    EligibilityValidator,
    MedicalNecessityValidator,
    NetworkValidator,
    PolicyValidator,
    PriorAuthValidator,
    TimelyFilingChecker,
    get_duplicate_checker,
    get_eligibility_validator,
    get_medical_necessity_validator,
    get_network_validator,
    get_policy_validator,
    get_prior_auth_validator,
    get_timely_filing_checker,
)


class AdjudicationServiceError(Exception):
    """Base exception for adjudication service errors."""

    pass


class AdjudicationService:
    """
    Orchestrates the complete claim adjudication process.

    The adjudication pipeline consists of:
    1. Timely Filing Check - Verify claim submitted within limits
    2. Duplicate Check - Ensure not a duplicate claim
    3. Policy Validation - Verify policy is active and effective
    4. Eligibility Validation - Verify member is eligible
    5. Network Validation - Verify provider network status
    6. Prior Authorization - Check for required authorizations
    7. Medical Necessity - Validate diagnosis-procedure relationships
    8. Benefit Calculation - Calculate allowed amounts and patient responsibility
    9. FWA Check - Fraud, Waste, and Abuse detection
    10. Decision Determination - Auto-approve, deny, or flag for review
    """

    def __init__(
        self,
        policy_validator: Optional[PolicyValidator] = None,
        eligibility_validator: Optional[EligibilityValidator] = None,
        network_validator: Optional[NetworkValidator] = None,
        prior_auth_validator: Optional[PriorAuthValidator] = None,
        medical_necessity_validator: Optional[MedicalNecessityValidator] = None,
        duplicate_checker: Optional[DuplicateClaimChecker] = None,
        timely_filing_checker: Optional[TimelyFilingChecker] = None,
    ):
        """
        Initialize AdjudicationService with validators.

        Args:
            policy_validator: PolicyValidator instance
            eligibility_validator: EligibilityValidator instance
            network_validator: NetworkValidator instance
            prior_auth_validator: PriorAuthValidator instance
            medical_necessity_validator: MedicalNecessityValidator instance
            duplicate_checker: DuplicateClaimChecker instance
            timely_filing_checker: TimelyFilingChecker instance
        """
        self.policy_validator = policy_validator or get_policy_validator()
        self.eligibility_validator = eligibility_validator or get_eligibility_validator()
        self.network_validator = network_validator or get_network_validator()
        self.prior_auth_validator = prior_auth_validator or get_prior_auth_validator()
        self.medical_necessity_validator = (
            medical_necessity_validator or get_medical_necessity_validator()
        )
        self.duplicate_checker = duplicate_checker or get_duplicate_checker()
        self.timely_filing_checker = timely_filing_checker or get_timely_filing_checker()

    async def adjudicate_claim(
        self,
        context: AdjudicationContext,
        line_items: list[dict],
        diagnosis_codes: list[str],
        member_age: Optional[int] = None,
        member_gender: Optional[str] = None,
    ) -> AdjudicationResult:
        """
        Adjudicate a claim through the complete pipeline.

        Args:
            context: Adjudication context with claim details
            line_items: List of line item dictionaries with procedure_code, charged_amount, etc.
            diagnosis_codes: List of ICD-10 diagnosis codes
            member_age: Optional member age for medical necessity checks
            member_gender: Optional member gender for medical necessity checks

        Returns:
            AdjudicationResult with complete adjudication details
        """
        start_time = time.time()

        # Extract procedure codes from line items
        procedure_codes = [item.get("procedure_code") for item in line_items]

        # Initialize result
        result = AdjudicationResult(
            claim_id=context.claim_id,
            adjudication_timestamp=datetime.utcnow(),
            decision=AdjudicationDecision.PENDING_REVIEW,
            total_charged=context.total_charged,
            processing_notes=[],
            review_reasons=[],
        )

        try:
            # Step 1: Timely Filing Check
            if not context.skip_duplicate_check:  # Reuse flag for timely filing
                result.timely_filing = await self.timely_filing_checker.check(context)
                if not result.timely_filing.is_timely:
                    result.decision = AdjudicationDecision.DENIED
                    result.primary_denial_reason = DenialReason.TIMELY_FILING_EXCEEDED
                    result.denial_codes.append("TF001")
                    result.processing_notes.append("Claim denied: Timely filing exceeded")
                    return self._finalize_result(result, start_time)

            # Step 2: Duplicate Check
            if not context.skip_duplicate_check:
                result.duplicate_check = await self.duplicate_checker.check(
                    context, procedure_codes
                )
                if result.duplicate_check.is_duplicate:
                    result.decision = AdjudicationDecision.DENIED
                    result.primary_denial_reason = DenialReason.DUPLICATE_CLAIM
                    result.denial_codes.append("DUP001")
                    result.processing_notes.append("Claim denied: Duplicate claim detected")
                    return self._finalize_result(result, start_time)
                elif result.duplicate_check.possible_duplicate:
                    result.requires_review = True
                    result.review_reasons.append("Possible duplicate claim")

            # Step 3: Policy Validation
            result.policy_validation = await self.policy_validator.validate(context)
            if not result.policy_validation.is_valid:
                result.decision = AdjudicationDecision.DENIED
                result.primary_denial_reason = result.policy_validation.denial_reason
                result.denial_codes.append("POL001")
                result.processing_notes.append(
                    f"Claim denied: {result.policy_validation.denial_message}"
                )
                return self._finalize_result(result, start_time)

            # Step 4: Eligibility Validation
            if not context.skip_eligibility:
                result.eligibility_validation = await self.eligibility_validator.validate(
                    context
                )
                if not result.eligibility_validation.is_eligible:
                    result.decision = AdjudicationDecision.DENIED
                    result.primary_denial_reason = result.eligibility_validation.denial_reason
                    result.denial_codes.append("ELIG001")
                    result.processing_notes.append(
                        f"Claim denied: {result.eligibility_validation.denial_message}"
                    )
                    return self._finalize_result(result, start_time)

            # Step 5: Network Validation
            if not context.skip_network:
                result.network_validation = await self.network_validator.validate(context)
                if not result.network_validation.is_valid:
                    # Out of network doesn't necessarily deny - may adjust payment
                    if result.network_validation.denial_reason == DenialReason.PROVIDER_NOT_ENROLLED:
                        result.decision = AdjudicationDecision.DENIED
                        result.primary_denial_reason = result.network_validation.denial_reason
                        result.denial_codes.append("NET001")
                        result.processing_notes.append(
                            f"Claim denied: {result.network_validation.denial_message}"
                        )
                        return self._finalize_result(result, start_time)
                    elif result.network_validation.denial_reason == DenialReason.OUT_OF_NETWORK:
                        result.processing_notes.append("Out-of-network benefits applied")

            # Step 6: Prior Authorization
            if not context.skip_prior_auth:
                result.prior_auth_validation = await self.prior_auth_validator.validate(
                    context, procedure_codes
                )
                if not result.prior_auth_validation.is_valid:
                    result.decision = AdjudicationDecision.DENIED
                    result.primary_denial_reason = result.prior_auth_validation.denial_reason
                    result.denial_codes.append("AUTH001")
                    result.processing_notes.append(
                        f"Claim denied: {result.prior_auth_validation.denial_message}"
                    )
                    return self._finalize_result(result, start_time)

            # Step 7: Medical Necessity
            if not context.skip_medical_necessity:
                result.medical_necessity = await self.medical_necessity_validator.validate(
                    context, diagnosis_codes, procedure_codes, member_age, member_gender
                )
                if not result.medical_necessity.is_valid:
                    result.decision = AdjudicationDecision.DENIED
                    result.primary_denial_reason = result.medical_necessity.denial_reason
                    result.denial_codes.append("MED001")
                    result.processing_notes.append(
                        f"Claim denied: {result.medical_necessity.denial_message}"
                    )
                    return self._finalize_result(result, start_time)

            # Step 8: Calculate Benefits for each line item
            result.line_results = await self._calculate_line_items(
                context, line_items, result
            )

            # Calculate totals from line results
            result.calculate_totals()

            # Step 9: FWA Check (simplified)
            if not context.skip_fwa_check:
                fwa_result = await self._check_fwa(context, result)
                result.fwa_score = fwa_result.get("score", 0.0)
                result.fwa_flags = fwa_result.get("flags", [])

                if result.fwa_score >= context.fwa_threshold:
                    result.requires_review = True
                    result.review_reasons.append(f"FWA score {result.fwa_score:.2f} exceeds threshold")

            # Step 10: Determine Final Decision
            result = await self._determine_decision(context, result)

        except Exception as e:
            result.decision = AdjudicationDecision.PENDING_REVIEW
            result.requires_review = True
            result.review_reasons.append(f"Processing error: {str(e)}")
            result.processing_notes.append(f"Error during adjudication: {str(e)}")

        return self._finalize_result(result, start_time)

    async def _calculate_line_items(
        self,
        context: AdjudicationContext,
        line_items: list[dict],
        result: AdjudicationResult,
    ) -> list[LineItemAdjudication]:
        """Calculate benefits for each line item."""
        line_results = []

        # Get network status for payment adjustments
        is_in_network = (
            result.network_validation is None
            or result.network_validation.is_valid
        )

        # Get eligibility accumulators
        deductible_remaining = Decimal("500.00")  # Default
        oop_remaining = Decimal("4000.00")  # Default

        if result.eligibility_validation:
            deductible_remaining = result.eligibility_validation.deductible_remaining
            oop_remaining = result.eligibility_validation.oop_remaining

        # Track accumulated deductible across line items
        deductible_applied_total = Decimal("0")

        for item in line_items:
            line_result = LineItemAdjudication(
                line_number=item.get("line_number", 1),
                procedure_code=item.get("procedure_code", ""),
                charged_amount=Decimal(str(item.get("charged_amount", 0))),
            )

            # Calculate allowed amount (simplified - in production use fee schedule)
            charged = line_result.charged_amount
            allowed = await self._calculate_allowed_amount(
                item.get("procedure_code"),
                charged,
                is_in_network,
            )
            line_result.allowed_amount = allowed

            # Calculate patient responsibility
            remaining_for_deductible = deductible_remaining - deductible_applied_total

            if remaining_for_deductible > 0:
                deductible_for_line = min(allowed, remaining_for_deductible)
                line_result.deductible_applied = deductible_for_line
                deductible_applied_total += deductible_for_line
            else:
                line_result.deductible_applied = Decimal("0")

            # After deductible
            after_deductible = allowed - line_result.deductible_applied

            # Coinsurance (assume 80/20 in-network, 60/40 out-of-network)
            coinsurance_rate = Decimal("0.20") if is_in_network else Decimal("0.40")
            line_result.coinsurance_amount = after_deductible * coinsurance_rate

            # Calculate plan paid and patient responsibility
            line_result.paid_amount = after_deductible - line_result.coinsurance_amount
            line_result.patient_responsibility = (
                line_result.deductible_applied + line_result.coinsurance_amount
            )

            # Adjustment (difference between charged and allowed)
            line_result.adjustment_amount = charged - allowed

            # Set decision based on amounts
            if line_result.paid_amount > 0:
                line_result.decision = AdjudicationDecision.APPROVED
            elif line_result.patient_responsibility > 0:
                line_result.decision = AdjudicationDecision.APPROVED
            else:
                line_result.decision = AdjudicationDecision.DENIED

            line_results.append(line_result)

        return line_results

    async def _calculate_allowed_amount(
        self,
        procedure_code: str,
        charged_amount: Decimal,
        is_in_network: bool,
    ) -> Decimal:
        """Calculate allowed amount for a procedure (simplified)."""
        # In production, use fee schedule lookup
        # For demo, use percentage of charged amount

        # In-network: typically 70-80% of charged
        # Out-of-network: typically 50-60% of charged
        if is_in_network:
            allowed_pct = Decimal("0.75")
        else:
            allowed_pct = Decimal("0.55")

        allowed = charged_amount * allowed_pct
        return allowed.quantize(Decimal("0.01"))

    async def _check_fwa(
        self,
        context: AdjudicationContext,
        result: AdjudicationResult,
    ) -> dict:
        """Perform fraud, waste, and abuse checks (simplified)."""
        score = 0.0
        flags = []

        # Check 1: High claim amount
        if context.total_charged > context.auto_approve_threshold:
            score += 0.2
            flags.append("high_claim_amount")

        # Check 2: Multiple procedures
        if len(result.line_results) > 5:
            score += 0.1
            flags.append("multiple_procedures")

        # Check 3: Weekend service (potential upcoding indicator)
        if context.service_date.weekday() >= 5:
            score += 0.05
            flags.append("weekend_service")

        return {"score": score, "flags": flags}

    async def _determine_decision(
        self,
        context: AdjudicationContext,
        result: AdjudicationResult,
    ) -> AdjudicationResult:
        """Determine final adjudication decision."""
        # Check if any line items were approved
        approved_lines = [
            lr for lr in result.line_results
            if lr.decision == AdjudicationDecision.APPROVED
        ]
        denied_lines = [
            lr for lr in result.line_results
            if lr.decision == AdjudicationDecision.DENIED
        ]

        if not result.line_results:
            result.decision = AdjudicationDecision.PENDING_REVIEW
            result.requires_review = True
            result.review_reasons.append("No line items to process")
            result.adjudication_type = AdjudicationType.MANUAL
            return result

        # If requires review, set to pending
        if result.requires_review:
            result.decision = AdjudicationDecision.PENDING_REVIEW
            result.adjudication_type = AdjudicationType.ASSISTED
            return result

        # Determine based on line item results
        if len(approved_lines) == len(result.line_results):
            # All lines approved
            if result.total_paid > 0:
                result.decision = AdjudicationDecision.APPROVED
                result.processing_notes.append(
                    f"Claim approved: ${result.total_paid:.2f} payable"
                )
            else:
                # Patient responsibility only
                result.decision = AdjudicationDecision.APPROVED
                result.processing_notes.append(
                    "Claim approved: Full amount applied to patient responsibility"
                )
        elif len(denied_lines) == len(result.line_results):
            # All lines denied
            result.decision = AdjudicationDecision.DENIED
            result.processing_notes.append("Claim denied: All line items denied")
        else:
            # Partial approval
            result.decision = AdjudicationDecision.PARTIAL
            result.processing_notes.append(
                f"Claim partially approved: {len(approved_lines)}/{len(result.line_results)} lines"
            )

        # Determine adjudication type
        if (
            result.total_charged <= context.auto_approve_threshold
            and not result.requires_review
            and result.fwa_score is not None
            and result.fwa_score < context.fwa_threshold
        ):
            result.adjudication_type = AdjudicationType.AUTO
        else:
            result.adjudication_type = AdjudicationType.ASSISTED

        return result

    def _finalize_result(
        self,
        result: AdjudicationResult,
        start_time: float,
    ) -> AdjudicationResult:
        """Finalize the adjudication result with timing."""
        result.processing_time_ms = int((time.time() - start_time) * 1000)
        return result


# =============================================================================
# Factory Functions
# =============================================================================


_adjudication_service: Optional[AdjudicationService] = None


def get_adjudication_service() -> AdjudicationService:
    """Get singleton AdjudicationService instance."""
    global _adjudication_service
    if _adjudication_service is None:
        _adjudication_service = AdjudicationService()
    return _adjudication_service


def create_adjudication_service(
    policy_validator: Optional[PolicyValidator] = None,
    eligibility_validator: Optional[EligibilityValidator] = None,
    network_validator: Optional[NetworkValidator] = None,
    prior_auth_validator: Optional[PriorAuthValidator] = None,
    medical_necessity_validator: Optional[MedicalNecessityValidator] = None,
    duplicate_checker: Optional[DuplicateClaimChecker] = None,
    timely_filing_checker: Optional[TimelyFilingChecker] = None,
) -> AdjudicationService:
    """Create a new AdjudicationService instance with custom validators."""
    return AdjudicationService(
        policy_validator=policy_validator,
        eligibility_validator=eligibility_validator,
        network_validator=network_validator,
        prior_auth_validator=prior_auth_validator,
        medical_necessity_validator=medical_necessity_validator,
        duplicate_checker=duplicate_checker,
        timely_filing_checker=timely_filing_checker,
    )
