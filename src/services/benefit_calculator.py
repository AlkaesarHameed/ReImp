"""
Benefit Calculation Engine.

Calculates insurance benefits for claims including:
- Fee schedule lookups
- Deductible application
- Coinsurance calculation
- Copay handling
- Out-of-pocket maximum tracking
- Benefit limit enforcement

Source: Design Document Section 3.3 - Benefit Calculation Engine
Verified: 2025-12-18
"""

import logging
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional
from uuid import UUID
import time

from src.schemas.benefit import (
    AdjustmentCategory,
    BenefitCalculationContext,
    BenefitDecision,
    ClaimBenefitResult,
    LineItemBenefitResult,
    LineItemInput,
    MemberEligibility,
)
from src.services.benefit_lookup import BenefitLookupService, get_benefit_lookup_service

logger = logging.getLogger(__name__)


class BenefitCalculator:
    """
    Core benefit calculation engine.

    Calculates allowed amounts, patient responsibility,
    and insurance payment for each line item on a claim.
    """

    def __init__(
        self,
        lookup_service: Optional[BenefitLookupService] = None,
    ):
        """
        Initialize benefit calculator.

        Args:
            lookup_service: Optional benefit lookup service
        """
        self.lookup_service = lookup_service or get_benefit_lookup_service()

    async def calculate_claim_benefits(
        self,
        context: BenefitCalculationContext,
        line_items: list[LineItemInput],
    ) -> ClaimBenefitResult:
        """
        Calculate benefits for an entire claim.

        Args:
            context: Calculation context with policy/member info
            line_items: List of line items to calculate

        Returns:
            ClaimBenefitResult with all calculated amounts
        """
        start_time = time.perf_counter()

        # Initialize result
        result = ClaimBenefitResult(
            claim_id=context.claim_id,
            calculation_timestamp=datetime.now(timezone.utc),
        )

        # Get eligibility if not provided
        if not context.eligibility:
            context.eligibility = await self.lookup_service.lookup_eligibility(
                member_id=context.member_id,
                policy_id=context.policy_id,
                service_date=context.service_date,
            )

        # Check eligibility
        if not context.eligibility.is_eligible:
            # Return denied result for all lines
            for line_input in line_items:
                line_result = LineItemBenefitResult(
                    line_number=line_input.line_number,
                    procedure_code=line_input.procedure_code,
                    charged_amount=line_input.charged_amount,
                    quantity=line_input.quantity,
                    fee_schedule_amount=Decimal("0"),
                    allowed_amount=Decimal("0"),
                    non_covered_amount=line_input.charged_amount,
                    patient_responsibility=line_input.charged_amount,
                    decision=BenefitDecision.DENY,
                    denial_reason="Member not eligible",
                )
                line_result.add_adjustment(
                    AdjustmentCategory.NON_COVERED,
                    line_input.charged_amount,
                    code="CO-27",
                    description="Member not eligible",
                )
                result.line_results.append(line_result)

            result.calculate_totals()
            result.calculation_time_ms = int((time.perf_counter() - start_time) * 1000)
            return result

        # Initialize running accumulators from current state
        context.running_deductible_applied = context.eligibility.deductible_met
        context.running_out_of_pocket = context.eligibility.out_of_pocket_met
        context.running_benefit_used = context.eligibility.limit_used

        # Calculate each line item
        for line_input in line_items:
            line_result = await self._calculate_line_item(context, line_input)
            result.line_results.append(line_result)

            # Update running accumulators
            context.running_deductible_applied += line_result.deductible_applied
            context.running_out_of_pocket += line_result.patient_responsibility
            context.running_benefit_used += line_result.benefit_paid

        # Calculate totals
        result.calculate_totals()

        # Set final accumulator values
        result.new_deductible_met = context.running_deductible_applied
        result.new_out_of_pocket_met = context.running_out_of_pocket
        result.new_annual_limit_used = context.running_benefit_used

        # Record rules applied
        result.rules_applied = [
            "fee_schedule_lookup",
            "deductible_application" if context.apply_deductible else None,
            "coinsurance_calculation" if context.apply_coinsurance else None,
            "copay_application" if context.apply_copay else None,
            "benefit_limit_check" if context.check_limits else None,
            "exclusion_check" if context.check_exclusions else None,
        ]
        result.rules_applied = [r for r in result.rules_applied if r]

        result.calculation_time_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            f"Benefit calculation complete: claim={context.claim_id}, "
            f"lines={len(line_items)}, "
            f"total_paid={result.total_benefit_paid}, "
            f"patient_resp={result.total_patient_responsibility}"
        )

        return result

    async def _calculate_line_item(
        self,
        context: BenefitCalculationContext,
        line_input: LineItemInput,
    ) -> LineItemBenefitResult:
        """
        Calculate benefit for a single line item.

        This is the core calculation logic implementing the benefit calculation steps:
        1. Fee schedule lookup
        2. Exclusion check
        3. Determine allowed amount
        4. Apply deductible
        5. Calculate coinsurance
        6. Apply copay
        7. Check OOP maximum
        8. Check benefit limits
        """
        eligibility = context.eligibility

        # Initialize result
        result = LineItemBenefitResult(
            line_number=line_input.line_number,
            procedure_code=line_input.procedure_code,
            charged_amount=line_input.charged_amount,
            quantity=line_input.quantity,
            fee_schedule_amount=Decimal("0"),
            allowed_amount=Decimal("0"),
        )

        # Step 1: Check exclusions
        if context.check_exclusions:
            if line_input.procedure_code in eligibility.excluded_procedures:
                result.decision = BenefitDecision.DENY
                result.denial_reason = "Procedure excluded from coverage"
                result.non_covered_amount = line_input.charged_amount
                result.patient_responsibility = line_input.charged_amount
                result.add_adjustment(
                    AdjustmentCategory.NON_COVERED,
                    line_input.charged_amount,
                    code="CO-96",
                    description="Non-covered charge(s)",
                )
                return result

            # Check diagnosis exclusions
            for dx_code in line_input.diagnosis_codes:
                if dx_code in eligibility.excluded_conditions:
                    result.decision = BenefitDecision.DENY
                    result.denial_reason = f"Diagnosis {dx_code} excluded from coverage"
                    result.non_covered_amount = line_input.charged_amount
                    result.patient_responsibility = line_input.charged_amount
                    result.add_adjustment(
                        AdjustmentCategory.NON_COVERED,
                        line_input.charged_amount,
                        code="CO-167",
                        description="Excluded diagnosis",
                    )
                    return result

        # Step 2: Fee schedule lookup
        if line_input.override_allowed_amount is not None:
            result.fee_schedule_amount = line_input.override_allowed_amount
        else:
            fee_lookup = await self.lookup_service.lookup_fee_schedule(
                procedure_code=line_input.procedure_code,
                tenant_id=context.tenant_id,
                fee_schedule_id=context.fee_schedule_id,
                modifiers=line_input.modifiers,
                is_facility=context.place_of_service in ("21", "22", "23"),  # Hospital settings
            )

            if not fee_lookup.found:
                # Unknown procedure - flag for review
                result.decision = BenefitDecision.PEND
                result.denial_reason = "Procedure code not in fee schedule"
                result.remark_codes.append("N56")  # Procedure requires review
                # Use charged amount as allowed for now
                result.fee_schedule_amount = line_input.charged_amount
            else:
                result.fee_schedule_amount = fee_lookup.adjusted_amount

        # Step 3: Determine allowed amount
        # Allowed = min(charged, fee_schedule) * quantity
        unit_allowed = min(line_input.charged_amount, result.fee_schedule_amount)
        result.allowed_amount = (unit_allowed * line_input.quantity).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Add contractual adjustment if charged > allowed
        contractual_adj = line_input.charged_amount - result.allowed_amount
        if contractual_adj > 0:
            result.add_adjustment(
                AdjustmentCategory.CONTRACTUAL,
                contractual_adj,
                code="CO-45",
                description="Charge exceeds fee schedule/maximum allowable",
            )

        # Step 4: Check benefit limits
        if context.check_limits:
            remaining_limit = (
                eligibility.annual_limit - context.running_benefit_used
            )

            if remaining_limit <= 0:
                result.decision = BenefitDecision.DENY
                result.denial_reason = "Annual benefit limit exceeded"
                result.non_covered_amount = result.allowed_amount
                result.patient_responsibility = result.allowed_amount
                result.add_adjustment(
                    AdjustmentCategory.EXCEEDED_LIMIT,
                    result.allowed_amount,
                    code="CO-119",
                    description="Benefit maximum exceeded",
                )
                return result

            # Cap benefit to remaining limit
            if result.allowed_amount > remaining_limit:
                excess = result.allowed_amount - remaining_limit
                result.non_covered_amount = excess
                result.add_adjustment(
                    AdjustmentCategory.EXCEEDED_LIMIT,
                    excess,
                    code="CO-119",
                    description="Benefit maximum exceeded",
                )
                result.allowed_amount = remaining_limit

        # Working amount for patient responsibility calculation
        working_amount = result.allowed_amount - result.non_covered_amount

        # Step 5: Apply deductible
        if context.apply_deductible and eligibility.annual_deductible > 0:
            remaining_deductible = (
                eligibility.annual_deductible - context.running_deductible_applied
            )

            if remaining_deductible > 0:
                deductible_to_apply = min(working_amount, remaining_deductible)
                result.deductible_applied = deductible_to_apply.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                result.add_adjustment(
                    AdjustmentCategory.DEDUCTIBLE,
                    result.deductible_applied,
                    code="PR-1",
                    description="Deductible amount",
                )
                working_amount -= result.deductible_applied

        # Step 6: Calculate coinsurance
        if context.apply_coinsurance and working_amount > 0:
            # Get coinsurance rate based on network status
            if context.is_in_network:
                coverage_rate = eligibility.in_network_rate
            else:
                coverage_rate = eligibility.out_of_network_rate

            # Patient pays the coinsurance portion (1 - coverage_rate)
            coinsurance_rate = Decimal("1") - coverage_rate
            result.coinsurance_amount = (working_amount * coinsurance_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            if result.coinsurance_amount > 0:
                result.add_adjustment(
                    AdjustmentCategory.COINSURANCE,
                    result.coinsurance_amount,
                    code="PR-2",
                    description="Coinsurance amount",
                )

        # Step 7: Check out-of-pocket maximum
        if context.apply_deductible or context.apply_coinsurance:
            remaining_oop = (
                eligibility.out_of_pocket_max - context.running_out_of_pocket
            )

            # Total patient responsibility so far
            current_patient_amount = (
                result.deductible_applied +
                result.coinsurance_amount +
                result.copay_amount
            )

            # Cap at OOP max
            if remaining_oop <= 0:
                # OOP max already met - no patient responsibility
                result.deductible_applied = Decimal("0")
                result.coinsurance_amount = Decimal("0")
                result.copay_amount = Decimal("0")
                result.remark_codes.append("N89")  # OOP max reached
            elif current_patient_amount > remaining_oop:
                # Reduce to stay within OOP max
                reduction = current_patient_amount - remaining_oop

                # Reduce coinsurance first, then deductible
                if result.coinsurance_amount >= reduction:
                    result.coinsurance_amount -= reduction
                else:
                    reduction -= result.coinsurance_amount
                    result.coinsurance_amount = Decimal("0")
                    result.deductible_applied = max(
                        Decimal("0"),
                        result.deductible_applied - reduction
                    )

                result.remark_codes.append("N89")  # OOP max reached

        # Step 8: Calculate final amounts
        result.patient_responsibility = (
            result.deductible_applied +
            result.coinsurance_amount +
            result.copay_amount +
            result.non_covered_amount
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        result.benefit_paid = (
            result.allowed_amount -
            result.deductible_applied -
            result.coinsurance_amount -
            result.copay_amount -
            result.non_covered_amount
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Ensure non-negative
        result.benefit_paid = max(Decimal("0"), result.benefit_paid)

        # Set decision
        if result.decision == BenefitDecision.PEND:
            pass  # Keep pending
        elif result.benefit_paid > 0:
            if result.non_covered_amount > 0 or result.decision == BenefitDecision.PEND:
                result.decision = BenefitDecision.PAY_PARTIAL
            else:
                result.decision = BenefitDecision.PAY
        elif result.patient_responsibility == result.charged_amount:
            # All charged to patient
            if result.non_covered_amount == result.charged_amount:
                result.decision = BenefitDecision.DENY
            else:
                result.decision = BenefitDecision.PAY  # Applied to deductible/coinsurance

        return result

    async def calculate_single_line(
        self,
        procedure_code: str,
        charged_amount: Decimal,
        tenant_id: UUID,
        policy_id: UUID,
        member_id: UUID,
        provider_id: UUID,
        service_date: datetime,
        quantity: int = 1,
        modifiers: Optional[list[str]] = None,
        is_in_network: bool = True,
    ) -> LineItemBenefitResult:
        """
        Convenience method to calculate benefit for a single line item.

        Useful for quick calculations or preview scenarios.
        """
        from uuid import uuid4

        context = BenefitCalculationContext(
            claim_id=uuid4(),  # Temporary ID
            tenant_id=tenant_id,
            policy_id=policy_id,
            member_id=member_id,
            provider_id=provider_id,
            service_date=service_date.date() if isinstance(service_date, datetime) else service_date,
            is_in_network=is_in_network,
        )

        line_input = LineItemInput(
            line_number=1,
            procedure_code=procedure_code,
            modifiers=modifiers or [],
            charged_amount=charged_amount,
            quantity=quantity,
            service_date=context.service_date,
        )

        return await self._calculate_line_item(context, line_input)


# =============================================================================
# Patient Share Calculator
# =============================================================================


class PatientShareCalculator:
    """
    Dedicated calculator for patient share calculations.

    Handles the detailed breakdown of:
    - Deductible
    - Copay
    - Coinsurance
    - Out-of-pocket maximum
    """

    @staticmethod
    def calculate_deductible(
        allowed_amount: Decimal,
        annual_deductible: Decimal,
        deductible_met: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate deductible to apply.

        Args:
            allowed_amount: Amount to apply deductible to
            annual_deductible: Total annual deductible
            deductible_met: Already met deductible

        Returns:
            Tuple of (deductible_applied, remaining_after_deductible)
        """
        remaining_deductible = annual_deductible - deductible_met
        remaining_deductible = max(Decimal("0"), remaining_deductible)

        deductible_applied = min(allowed_amount, remaining_deductible)
        remaining_after = allowed_amount - deductible_applied

        return (
            deductible_applied.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            remaining_after.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        )

    @staticmethod
    def calculate_coinsurance(
        amount: Decimal,
        coverage_rate: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate coinsurance amounts.

        Args:
            amount: Amount to apply coinsurance to
            coverage_rate: Insurance coverage rate (e.g., 0.80 for 80%)

        Returns:
            Tuple of (coinsurance_amount, benefit_amount)
        """
        coinsurance_rate = Decimal("1") - coverage_rate
        coinsurance_amount = amount * coinsurance_rate
        benefit_amount = amount * coverage_rate

        return (
            coinsurance_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            benefit_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        )

    @staticmethod
    def calculate_copay(
        copay_fixed: Optional[Decimal],
        copay_percentage: Optional[Decimal],
        allowed_amount: Decimal,
    ) -> Decimal:
        """
        Calculate copay amount.

        Args:
            copay_fixed: Fixed copay amount (e.g., $30)
            copay_percentage: Percentage copay (e.g., 0.20 for 20%)
            allowed_amount: Allowed amount for calculation

        Returns:
            Copay amount
        """
        if copay_fixed is not None and copay_fixed > 0:
            return copay_fixed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if copay_percentage is not None and copay_percentage > 0:
            copay = allowed_amount * copay_percentage
            return copay.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return Decimal("0")

    @staticmethod
    def apply_oop_max(
        patient_amounts: dict[str, Decimal],
        oop_max: Decimal,
        oop_met: Decimal,
    ) -> dict[str, Decimal]:
        """
        Apply out-of-pocket maximum cap.

        Args:
            patient_amounts: Dict with 'deductible', 'coinsurance', 'copay'
            oop_max: Out-of-pocket maximum
            oop_met: Already met OOP

        Returns:
            Adjusted patient amounts
        """
        remaining_oop = max(Decimal("0"), oop_max - oop_met)

        total_patient = sum(patient_amounts.values())

        if total_patient <= remaining_oop:
            return patient_amounts

        # Need to reduce - cap at remaining OOP
        if remaining_oop <= 0:
            return {k: Decimal("0") for k in patient_amounts}

        # Proportionally reduce each component
        reduction_ratio = remaining_oop / total_patient

        return {
            k: (v * reduction_ratio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            for k, v in patient_amounts.items()
        }


# =============================================================================
# Singleton Instances
# =============================================================================


_benefit_calculator: Optional[BenefitCalculator] = None


def get_benefit_calculator() -> BenefitCalculator:
    """Get singleton benefit calculator instance."""
    global _benefit_calculator
    if _benefit_calculator is None:
        _benefit_calculator = BenefitCalculator()
    return _benefit_calculator
