"""
Explanation of Benefits (EOB) Generator Service.
Source: Design Document Section 3.4 - Claim Adjudication Pipeline
Verified: 2025-12-18

Generates EOB documents from adjudicated claims for member communication.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from src.schemas.adjudication import (
    AdjudicationResult,
    EOBLineItem,
    EOBSummary,
    ExplanationOfBenefits,
    LineItemAdjudication,
)


class EOBGeneratorError(Exception):
    """Base exception for EOB generation errors."""

    pass


class EOBGenerator:
    """
    Generates Explanation of Benefits documents from adjudicated claims.

    The EOB contains:
    - Claim identification and dates
    - Member information
    - Provider information
    - Service line item details with amounts
    - Payment summary and patient responsibility
    - Accumulator status (deductible, out-of-pocket)
    - Important messages and appeal instructions
    """

    # Standard messages based on claim status
    STANDARD_MESSAGES = {
        "approved": [
            "This is not a bill. Your provider may bill you for the amount shown as 'Your Responsibility'.",
            "If you have questions about this explanation, please call Member Services.",
        ],
        "partial": [
            "This is not a bill. Some services were not covered or were reduced.",
            "You may be responsible for the amounts shown. Please review each line item.",
            "If you have questions about denied services, please call Member Services.",
        ],
        "denied": [
            "This claim has been denied. Please review the reason codes for each service.",
            "You may appeal this decision within 180 days of this notice.",
            "For assistance with your appeal, please call Member Services.",
        ],
        "pending": [
            "This claim is pending additional review.",
            "No action is required from you at this time.",
            "You will receive an updated EOB once processing is complete.",
        ],
    }

    APPEAL_INSTRUCTIONS = """To appeal this decision:
1. Write a letter explaining why you disagree with the decision
2. Include your Member ID, claim number, and date of service
3. Attach any supporting documentation from your provider
4. Mail to: Appeals Department, PO Box 12345, City, ST 12345
5. Or fax to: (555) 123-4567

You have 180 days from the date of this notice to file an appeal.
For questions, call Member Services at 1-800-555-0123."""

    def __init__(self):
        """Initialize EOBGenerator."""
        pass

    async def generate_eob(
        self,
        adjudication_result: AdjudicationResult,
        member_info: dict,
        provider_info: dict,
        claim_info: dict,
    ) -> ExplanationOfBenefits:
        """
        Generate an EOB from an adjudication result.

        Args:
            adjudication_result: Completed adjudication result
            member_info: Member details (name, id_display, group_number)
            provider_info: Provider details (name, address)
            claim_info: Claim details (tracking_number, service_dates)

        Returns:
            ExplanationOfBenefits document
        """
        # Generate EOB number
        eob_number = self._generate_eob_number()

        # Build line items
        line_items = await self._build_line_items(
            adjudication_result.line_results,
            claim_info.get("service_date_from", date.today()),
            provider_info.get("name", ""),
        )

        # Build summary
        summary = await self._build_summary(
            adjudication_result,
            claim_info.get("deductible_status", ""),
            claim_info.get("oop_status", ""),
        )

        # Get messages based on decision
        decision_key = adjudication_result.decision.value
        if decision_key == "pending_review" or decision_key == "pending_info":
            decision_key = "pending"
        messages = list(self.STANDARD_MESSAGES.get(decision_key, []))

        # Add specific denial messages if applicable
        if adjudication_result.primary_denial_reason:
            denial_msg = self._get_denial_message(adjudication_result.primary_denial_reason)
            if denial_msg:
                messages.insert(0, denial_msg)

        # Determine if appeal instructions needed
        appeal_instructions = None
        if adjudication_result.decision.value in ["denied", "partial"]:
            appeal_instructions = self.APPEAL_INSTRUCTIONS

        # Build EOB
        eob = ExplanationOfBenefits(
            eob_number=eob_number,
            claim_tracking_number=claim_info.get("tracking_number", ""),
            claim_id=adjudication_result.claim_id,
            generated_date=date.today(),
            service_date_from=claim_info.get("service_date_from", date.today()),
            service_date_to=claim_info.get("service_date_to", date.today()),
            payment_date=self._calculate_payment_date(adjudication_result),
            member_name=member_info.get("name", ""),
            member_id_display=member_info.get("id_display", ""),
            group_number=member_info.get("group_number"),
            provider_name=provider_info.get("name", ""),
            provider_address=provider_info.get("address"),
            line_items=line_items,
            summary=summary,
            messages=messages,
            appeal_instructions=appeal_instructions,
            claim_status=self._get_claim_status_text(adjudication_result.decision.value),
        )

        return eob

    async def _build_line_items(
        self,
        line_results: list[LineItemAdjudication],
        service_date: date,
        provider_name: str,
    ) -> list[EOBLineItem]:
        """Build EOB line items from adjudication line results."""
        eob_lines = []

        for lr in line_results:
            # Calculate not covered amount
            not_covered = lr.charged_amount - lr.allowed_amount

            # Get procedure description (in production, use code lookup)
            description = self._get_procedure_description(lr.procedure_code)

            # Determine line status
            if lr.decision.value == "approved":
                status = "processed"
                remark = None
            elif lr.decision.value == "denied":
                status = "denied"
                remark = lr.denial_message or "Service not covered"
            else:
                status = "pending"
                remark = "Under review"

            eob_line = EOBLineItem(
                line_number=lr.line_number,
                service_date=service_date,
                procedure_code=lr.procedure_code,
                procedure_description=description,
                provider_name=provider_name,
                charged_amount=lr.charged_amount,
                allowed_amount=lr.allowed_amount,
                plan_paid=lr.paid_amount,
                your_responsibility=lr.patient_responsibility,
                deductible=lr.deductible_applied,
                copay=lr.copay_amount,
                coinsurance=lr.coinsurance_amount,
                not_covered=not_covered,
                status=status,
                remark=remark,
            )
            eob_lines.append(eob_line)

        return eob_lines

    async def _build_summary(
        self,
        result: AdjudicationResult,
        deductible_status: str,
        oop_status: str,
    ) -> EOBSummary:
        """Build EOB summary from adjudication result."""
        # Calculate not covered total
        not_covered = result.total_charged - result.total_allowed

        summary = EOBSummary(
            total_charges=result.total_charged,
            total_allowed=result.total_allowed,
            plan_paid=result.total_paid,
            your_responsibility=result.total_patient_responsibility,
            applied_to_deductible=result.total_deductible,
            copay_amount=result.total_copay,
            coinsurance_amount=result.total_coinsurance,
            not_covered_amount=not_covered,
            deductible_status=deductible_status or self._format_deductible_status(result),
            oop_status=oop_status or self._format_oop_status(result),
        )

        return summary

    def _generate_eob_number(self) -> str:
        """Generate unique EOB number."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid4())[:8].upper()
        return f"EOB-{timestamp}-{unique_id}"

    def _calculate_payment_date(self, result: AdjudicationResult) -> Optional[date]:
        """Calculate payment date based on adjudication."""
        if result.decision.value == "approved" and result.total_paid > 0:
            # Typically payment within 14-30 days
            # For demo, return 14 days from adjudication
            return (result.adjudication_timestamp + __import__("datetime").timedelta(days=14)).date()
        return None

    def _get_claim_status_text(self, decision: str) -> str:
        """Get human-readable claim status."""
        status_map = {
            "approved": "Processed and Paid",
            "denied": "Denied",
            "partial": "Partially Processed",
            "pending_review": "Pending Review",
            "pending_info": "Additional Information Needed",
        }
        return status_map.get(decision, "Processing")

    def _get_denial_message(self, denial_reason) -> Optional[str]:
        """Get human-readable denial message."""
        denial_messages = {
            "not_eligible": "The member was not eligible for coverage on the date of service.",
            "coverage_terminated": "Member coverage has been terminated.",
            "not_covered_member": "This member is not covered under this policy.",
            "policy_inactive": "The policy was not active on the date of service.",
            "policy_expired": "The policy had expired on the date of service.",
            "benefit_exhausted": "The annual benefit maximum has been reached.",
            "not_covered_service": "This service is not covered under your plan.",
            "excluded_procedure": "This procedure is excluded from coverage.",
            "excluded_diagnosis": "This diagnosis is excluded from coverage.",
            "cosmetic_procedure": "Cosmetic procedures are not covered.",
            "experimental": "Experimental or investigational treatments are not covered.",
            "no_prior_auth": "Prior authorization was required but not obtained.",
            "prior_auth_expired": "The prior authorization had expired.",
            "prior_auth_denied": "Prior authorization was denied.",
            "out_of_network": "The provider is out-of-network.",
            "provider_not_enrolled": "The provider is not enrolled with this plan.",
            "not_medically_necessary": "This service was not deemed medically necessary.",
            "frequency_exceeded": "The frequency limit for this service has been exceeded.",
            "missing_documentation": "Required documentation was not submitted.",
            "invalid_documentation": "Documentation submitted was invalid or incomplete.",
            "duplicate_claim": "This claim appears to be a duplicate.",
            "timely_filing_exceeded": "This claim was not filed within the required time limit.",
            "fwa_flagged": "This claim has been flagged for review.",
            "cob_primary_payer": "Another insurance is the primary payer.",
        }
        return denial_messages.get(denial_reason.value if hasattr(denial_reason, 'value') else str(denial_reason))

    def _get_procedure_description(self, procedure_code: str) -> str:
        """Get procedure description from code (simplified)."""
        # In production, use comprehensive code lookup
        descriptions = {
            "99213": "Office visit, established patient, 15 min",
            "99214": "Office visit, established patient, 25 min",
            "99215": "Office visit, established patient, 40 min",
            "99203": "Office visit, new patient, 30 min",
            "99204": "Office visit, new patient, 45 min",
            "99205": "Office visit, new patient, 60 min",
            "99385": "Preventive visit, 18-39 years",
            "99386": "Preventive visit, 40-64 years",
            "99387": "Preventive visit, 65+ years",
            "80053": "Comprehensive metabolic panel",
            "80061": "Lipid panel",
            "82947": "Glucose quantitative",
            "83036": "Hemoglobin A1C",
            "85025": "Complete blood count (CBC)",
            "87880": "Strep test, rapid",
            "93000": "Electrocardiogram (ECG)",
            "71046": "Chest x-ray, 2 views",
            "70553": "MRI brain with contrast",
            "72148": "MRI lumbar spine without contrast",
            "74176": "CT abdomen and pelvis",
            "77067": "Screening mammography",
            "90471": "Immunization administration",
            "90714": "Tdap vaccine",
            "90732": "Pneumococcal vaccine",
            "90658": "Influenza vaccine",
            "36415": "Venipuncture",
        }
        return descriptions.get(procedure_code, f"Procedure {procedure_code}")

    def _format_deductible_status(self, result: AdjudicationResult) -> str:
        """Format deductible status string."""
        if result.eligibility_validation:
            remaining = result.eligibility_validation.deductible_remaining
            # Assume standard deductible of $1500 for display
            met = Decimal("1500") - remaining
            return f"${met:,.2f} of $1,500.00 met"
        return ""

    def _format_oop_status(self, result: AdjudicationResult) -> str:
        """Format out-of-pocket status string."""
        if result.eligibility_validation:
            remaining = result.eligibility_validation.oop_remaining
            # Assume standard OOP max of $6000 for display
            met = Decimal("6000") - remaining
            return f"${met:,.2f} of $6,000.00 met"
        return ""


# =============================================================================
# Factory Functions
# =============================================================================


_eob_generator: Optional[EOBGenerator] = None


def get_eob_generator() -> EOBGenerator:
    """Get singleton EOBGenerator instance."""
    global _eob_generator
    if _eob_generator is None:
        _eob_generator = EOBGenerator()
    return _eob_generator


def create_eob_generator() -> EOBGenerator:
    """Create a new EOBGenerator instance."""
    return EOBGenerator()
