"""
Adjudication Validation Services.
Source: Design Document Section 3.4 - Claim Adjudication Pipeline
Verified: 2025-12-18

Provides validation services for policy, eligibility, network, prior authorization,
medical necessity, duplicate claims, and timely filing checks.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from src.schemas.adjudication import (
    AdjudicationContext,
    DenialReason,
    DuplicateCheckResult,
    EligibilityValidationResult,
    MedicalNecessityResult,
    NetworkValidationResult,
    PolicyValidationResult,
    PriorAuthValidationResult,
    TimelyFilingResult,
    ValidationCheck,
    ValidationStatus,
)


# =============================================================================
# Policy Validator
# =============================================================================


class PolicyValidator:
    """Validates policy status and coverage for claims."""

    async def validate(
        self,
        context: AdjudicationContext,
        policy_data: Optional[dict] = None,
    ) -> PolicyValidationResult:
        """
        Validate policy for claim adjudication.

        Args:
            context: Adjudication context with claim details
            policy_data: Optional policy data (for testing/demo)

        Returns:
            PolicyValidationResult with validation details
        """
        result = PolicyValidationResult(
            policy_id=context.policy_id,
            checks=[],
        )

        # In production, fetch policy from database
        # For demo, use provided data or simulate
        if policy_data is None:
            policy_data = await self._fetch_policy_data(context.policy_id, context.tenant_id)

        # Check 1: Policy exists and is active
        policy_active_check = await self._check_policy_active(policy_data, context.service_date)
        result.checks.append(policy_active_check)
        result.policy_active = policy_active_check.status == ValidationStatus.PASSED

        # Check 2: Policy is effective for service date
        policy_effective_check = await self._check_policy_effective(
            policy_data, context.service_date
        )
        result.checks.append(policy_effective_check)
        result.policy_effective = policy_effective_check.status == ValidationStatus.PASSED

        # Check 3: Benefit not exhausted
        benefit_check = await self._check_benefit_available(policy_data, context)
        result.checks.append(benefit_check)
        result.benefit_available = benefit_check.status == ValidationStatus.PASSED

        # Determine overall validity
        result.is_valid = all([
            result.policy_active,
            result.policy_effective,
            result.benefit_available,
        ])

        # Set denial reason if not valid
        if not result.is_valid:
            if not result.policy_active:
                result.denial_reason = DenialReason.POLICY_INACTIVE
                result.denial_message = "Policy is not active"
            elif not result.policy_effective:
                result.denial_reason = DenialReason.POLICY_EXPIRED
                result.denial_message = "Policy not effective for date of service"
            elif not result.benefit_available:
                result.denial_reason = DenialReason.BENEFIT_EXHAUSTED
                result.denial_message = "Annual benefit maximum has been reached"

        result.policy_status = policy_data.get("status", "unknown")
        return result

    async def _fetch_policy_data(self, policy_id: UUID, tenant_id: UUID) -> dict:
        """Fetch policy data from database (simulated for demo)."""
        # In production, query database
        return {
            "id": policy_id,
            "status": "active",
            "effective_date": date.today() - timedelta(days=365),
            "termination_date": date.today() + timedelta(days=365),
            "annual_maximum": Decimal("1000000.00"),
            "used_amount": Decimal("50000.00"),
        }

    async def _check_policy_active(
        self, policy_data: dict, service_date: date
    ) -> ValidationCheck:
        """Check if policy is active."""
        status = policy_data.get("status", "unknown")
        is_active = status == "active"

        return ValidationCheck(
            check_name="policy_active",
            status=ValidationStatus.PASSED if is_active else ValidationStatus.FAILED,
            message=f"Policy status: {status}",
            code="POL001",
            details={"status": status},
        )

    async def _check_policy_effective(
        self, policy_data: dict, service_date: date
    ) -> ValidationCheck:
        """Check if policy is effective for service date."""
        effective_date = policy_data.get("effective_date", date.min)
        termination_date = policy_data.get("termination_date", date.max)

        is_effective = effective_date <= service_date <= termination_date

        return ValidationCheck(
            check_name="policy_effective",
            status=ValidationStatus.PASSED if is_effective else ValidationStatus.FAILED,
            message=f"Service date {service_date} {'within' if is_effective else 'outside'} policy period",
            code="POL002",
            details={
                "effective_date": str(effective_date),
                "termination_date": str(termination_date),
                "service_date": str(service_date),
            },
        )

    async def _check_benefit_available(
        self, policy_data: dict, context: AdjudicationContext
    ) -> ValidationCheck:
        """Check if annual benefit maximum not exhausted."""
        annual_max = policy_data.get("annual_maximum", Decimal("1000000.00"))
        used_amount = policy_data.get("used_amount", Decimal("0"))
        remaining = annual_max - used_amount

        has_benefit = remaining > 0

        return ValidationCheck(
            check_name="benefit_available",
            status=ValidationStatus.PASSED if has_benefit else ValidationStatus.FAILED,
            message=f"Remaining benefit: ${remaining:,.2f}",
            code="POL003",
            details={
                "annual_maximum": str(annual_max),
                "used_amount": str(used_amount),
                "remaining": str(remaining),
            },
        )


# =============================================================================
# Eligibility Validator
# =============================================================================


class EligibilityValidator:
    """Validates member eligibility for claims."""

    async def validate(
        self,
        context: AdjudicationContext,
        member_data: Optional[dict] = None,
    ) -> EligibilityValidationResult:
        """
        Validate member eligibility for claim adjudication.

        Args:
            context: Adjudication context with claim details
            member_data: Optional member data (for testing/demo)

        Returns:
            EligibilityValidationResult with validation details
        """
        result = EligibilityValidationResult(
            member_id=context.member_id,
            checks=[],
        )

        # In production, fetch member from database
        if member_data is None:
            member_data = await self._fetch_member_data(context.member_id, context.tenant_id)

        # Check 1: Member is active
        member_active_check = await self._check_member_active(member_data)
        result.checks.append(member_active_check)
        result.member_active = member_active_check.status == ValidationStatus.PASSED

        # Check 2: Coverage is effective for service date
        coverage_effective_check = await self._check_coverage_effective(
            member_data, context.service_date
        )
        result.checks.append(coverage_effective_check)
        result.coverage_effective = coverage_effective_check.status == ValidationStatus.PASSED

        # Check 3: Not within waiting period
        waiting_period_check = await self._check_waiting_period(
            member_data, context.service_date
        )
        result.checks.append(waiting_period_check)
        result.within_waiting_period = waiting_period_check.status == ValidationStatus.FAILED

        # Set accumulator values
        result.deductible_remaining = member_data.get("deductible_remaining", Decimal("0"))
        result.oop_remaining = member_data.get("oop_remaining", Decimal("0"))
        result.benefit_remaining = member_data.get("benefit_remaining", Decimal("0"))

        # Determine overall eligibility
        result.is_eligible = all([
            result.member_active,
            result.coverage_effective,
            not result.within_waiting_period,
        ])

        # Set denial reason if not eligible
        if not result.is_eligible:
            if not result.member_active:
                result.denial_reason = DenialReason.NOT_ELIGIBLE
                result.denial_message = "Member is not active"
            elif not result.coverage_effective:
                result.denial_reason = DenialReason.COVERAGE_TERMINATED
                result.denial_message = "Coverage not effective for date of service"
            elif result.within_waiting_period:
                result.denial_reason = DenialReason.NOT_ELIGIBLE
                result.denial_message = "Service date is within waiting period"

        return result

    async def _fetch_member_data(self, member_id: UUID, tenant_id: UUID) -> dict:
        """Fetch member data from database (simulated for demo)."""
        return {
            "id": member_id,
            "status": "active",
            "effective_date": date.today() - timedelta(days=180),
            "termination_date": None,
            "waiting_period_end": date.today() - timedelta(days=90),
            "deductible_remaining": Decimal("500.00"),
            "oop_remaining": Decimal("4000.00"),
            "benefit_remaining": Decimal("950000.00"),
        }

    async def _check_member_active(self, member_data: dict) -> ValidationCheck:
        """Check if member is active."""
        status = member_data.get("status", "unknown")
        is_active = status == "active"

        return ValidationCheck(
            check_name="member_active",
            status=ValidationStatus.PASSED if is_active else ValidationStatus.FAILED,
            message=f"Member status: {status}",
            code="ELIG001",
            details={"status": status},
        )

    async def _check_coverage_effective(
        self, member_data: dict, service_date: date
    ) -> ValidationCheck:
        """Check if coverage is effective for service date."""
        effective_date = member_data.get("effective_date", date.min)
        termination_date = member_data.get("termination_date") or date.max

        is_effective = effective_date <= service_date <= termination_date

        return ValidationCheck(
            check_name="coverage_effective",
            status=ValidationStatus.PASSED if is_effective else ValidationStatus.FAILED,
            message=f"Coverage {'effective' if is_effective else 'not effective'} for service date",
            code="ELIG002",
            details={
                "effective_date": str(effective_date),
                "termination_date": str(termination_date),
                "service_date": str(service_date),
            },
        )

    async def _check_waiting_period(
        self, member_data: dict, service_date: date
    ) -> ValidationCheck:
        """Check if service date is within waiting period."""
        waiting_period_end = member_data.get("waiting_period_end")

        if waiting_period_end is None:
            return ValidationCheck(
                check_name="waiting_period",
                status=ValidationStatus.PASSED,
                message="No waiting period applies",
                code="ELIG003",
            )

        is_past_waiting = service_date >= waiting_period_end

        return ValidationCheck(
            check_name="waiting_period",
            status=ValidationStatus.PASSED if is_past_waiting else ValidationStatus.FAILED,
            message=f"Waiting period {'completed' if is_past_waiting else 'in effect'}",
            code="ELIG003",
            details={
                "waiting_period_end": str(waiting_period_end),
                "service_date": str(service_date),
            },
        )


# =============================================================================
# Network Validator
# =============================================================================


class NetworkValidator:
    """Validates provider network participation."""

    async def validate(
        self,
        context: AdjudicationContext,
        provider_data: Optional[dict] = None,
    ) -> NetworkValidationResult:
        """
        Validate provider network status for claim adjudication.

        Args:
            context: Adjudication context with claim details
            provider_data: Optional provider data (for testing/demo)

        Returns:
            NetworkValidationResult with validation details
        """
        result = NetworkValidationResult(
            provider_id=context.provider_id,
            checks=[],
        )

        # In production, fetch provider from database
        if provider_data is None:
            provider_data = await self._fetch_provider_data(
                context.provider_id, context.tenant_id
            )

        # Check 1: Provider is enrolled
        enrolled_check = await self._check_provider_enrolled(provider_data)
        result.checks.append(enrolled_check)
        result.provider_enrolled = enrolled_check.status == ValidationStatus.PASSED

        # Check 2: Provider is in network
        network_check = await self._check_provider_in_network(
            provider_data, context.service_date
        )
        result.checks.append(network_check)
        result.provider_in_network = network_check.status == ValidationStatus.PASSED

        # Check 3: Provider is active
        active_check = await self._check_provider_active(provider_data)
        result.checks.append(active_check)
        result.provider_active = active_check.status == ValidationStatus.PASSED

        # Set network details
        result.network_status = provider_data.get("network_status", "unknown")
        result.network_tier = provider_data.get("network_tier")
        result.effective_date = provider_data.get("network_effective_date")

        # Determine overall validity
        result.is_valid = all([
            result.provider_enrolled,
            result.provider_in_network,
            result.provider_active,
        ])

        # Set denial reason if not valid
        if not result.is_valid:
            if not result.provider_enrolled:
                result.denial_reason = DenialReason.PROVIDER_NOT_ENROLLED
                result.denial_message = "Provider is not enrolled"
            elif not result.provider_in_network:
                result.denial_reason = DenialReason.OUT_OF_NETWORK
                result.denial_message = "Provider is out of network"
            elif not result.provider_active:
                result.denial_reason = DenialReason.PROVIDER_NOT_ENROLLED
                result.denial_message = "Provider is not active"

        return result

    async def _fetch_provider_data(self, provider_id: UUID, tenant_id: UUID) -> dict:
        """Fetch provider data from database (simulated for demo)."""
        return {
            "id": provider_id,
            "status": "active",
            "enrolled": True,
            "network_status": "in_network",
            "network_tier": "tier_1",
            "network_effective_date": date.today() - timedelta(days=365),
            "network_termination_date": None,
        }

    async def _check_provider_enrolled(self, provider_data: dict) -> ValidationCheck:
        """Check if provider is enrolled."""
        is_enrolled = provider_data.get("enrolled", False)

        return ValidationCheck(
            check_name="provider_enrolled",
            status=ValidationStatus.PASSED if is_enrolled else ValidationStatus.FAILED,
            message=f"Provider {'is' if is_enrolled else 'is not'} enrolled",
            code="NET001",
            details={"enrolled": is_enrolled},
        )

    async def _check_provider_in_network(
        self, provider_data: dict, service_date: date
    ) -> ValidationCheck:
        """Check if provider is in network for service date."""
        network_status = provider_data.get("network_status", "unknown")
        effective_date = provider_data.get("network_effective_date", date.min)
        termination_date = provider_data.get("network_termination_date") or date.max

        is_in_network = (
            network_status == "in_network"
            and effective_date <= service_date <= termination_date
        )

        return ValidationCheck(
            check_name="provider_in_network",
            status=ValidationStatus.PASSED if is_in_network else ValidationStatus.FAILED,
            message=f"Provider network status: {network_status}",
            code="NET002",
            details={
                "network_status": network_status,
                "effective_date": str(effective_date),
                "termination_date": str(termination_date),
            },
        )

    async def _check_provider_active(self, provider_data: dict) -> ValidationCheck:
        """Check if provider is active."""
        status = provider_data.get("status", "unknown")
        is_active = status == "active"

        return ValidationCheck(
            check_name="provider_active",
            status=ValidationStatus.PASSED if is_active else ValidationStatus.FAILED,
            message=f"Provider status: {status}",
            code="NET003",
            details={"status": status},
        )


# =============================================================================
# Prior Authorization Validator
# =============================================================================


class PriorAuthValidator:
    """Validates prior authorization requirements."""

    # Procedures commonly requiring prior authorization
    PRIOR_AUTH_REQUIRED_CPTS = {
        "27447",  # Total knee replacement
        "27130",  # Total hip replacement
        "63030",  # Spinal surgery
        "70553",  # MRI brain with contrast
        "70552",  # MRI brain without contrast
        "72148",  # MRI lumbar spine
        "74176",  # CT abdomen
        "77067",  # Screening mammography
        "43239",  # Upper GI endoscopy with biopsy
    }

    async def validate(
        self,
        context: AdjudicationContext,
        procedure_codes: list[str],
        auth_data: Optional[dict] = None,
    ) -> PriorAuthValidationResult:
        """
        Validate prior authorization for claim adjudication.

        Args:
            context: Adjudication context with claim details
            procedure_codes: List of procedure codes on claim
            auth_data: Optional authorization data (for testing/demo)

        Returns:
            PriorAuthValidationResult with validation details
        """
        result = PriorAuthValidationResult(checks=[])

        # Check if any procedures require prior auth
        requires_auth = any(
            code in self.PRIOR_AUTH_REQUIRED_CPTS for code in procedure_codes
        )
        result.auth_required = requires_auth

        if not requires_auth:
            result.is_valid = True
            result.checks.append(
                ValidationCheck(
                    check_name="prior_auth_required",
                    status=ValidationStatus.PASSED,
                    message="Prior authorization not required for submitted procedures",
                    code="AUTH001",
                )
            )
            return result

        # In production, fetch authorization from database
        if auth_data is None:
            auth_data = await self._fetch_auth_data(context.claim_id, procedure_codes)

        # Check 1: Authorization exists
        auth_exists_check = await self._check_auth_exists(auth_data)
        result.checks.append(auth_exists_check)

        if auth_exists_check.status != ValidationStatus.PASSED:
            result.is_valid = False
            result.denial_reason = DenialReason.NO_PRIOR_AUTH
            result.denial_message = "Prior authorization required but not on file"
            return result

        # Set authorization details
        result.auth_number = auth_data.get("auth_number")
        result.auth_status = auth_data.get("status")
        result.auth_effective_date = auth_data.get("effective_date")
        result.auth_expiry_date = auth_data.get("expiry_date")
        result.authorized_units = auth_data.get("authorized_units")
        result.used_units = auth_data.get("used_units", 0)

        # Check 2: Authorization is approved
        auth_approved_check = await self._check_auth_approved(auth_data)
        result.checks.append(auth_approved_check)

        # Check 3: Authorization is not expired
        auth_valid_check = await self._check_auth_valid(auth_data, context.service_date)
        result.checks.append(auth_valid_check)

        # Check 4: Units available
        units_check = await self._check_units_available(auth_data)
        result.checks.append(units_check)

        # Determine overall validity
        result.is_valid = all(
            check.status == ValidationStatus.PASSED for check in result.checks
        )

        # Set denial reason if not valid
        if not result.is_valid:
            if auth_approved_check.status != ValidationStatus.PASSED:
                result.denial_reason = DenialReason.PRIOR_AUTH_DENIED
                result.denial_message = "Prior authorization was denied"
            elif auth_valid_check.status != ValidationStatus.PASSED:
                result.denial_reason = DenialReason.PRIOR_AUTH_EXPIRED
                result.denial_message = "Prior authorization has expired"
            elif units_check.status != ValidationStatus.PASSED:
                result.denial_reason = DenialReason.PRIOR_AUTH_DENIED
                result.denial_message = "Authorized units have been exhausted"

        return result

    async def _fetch_auth_data(
        self, claim_id: UUID, procedure_codes: list[str]
    ) -> dict:
        """Fetch authorization data from database (simulated for demo)."""
        # In production, search for matching authorization
        return {
            "auth_number": "AUTH-2024-001234",
            "status": "approved",
            "effective_date": date.today() - timedelta(days=30),
            "expiry_date": date.today() + timedelta(days=60),
            "authorized_units": 1,
            "used_units": 0,
        }

    async def _check_auth_exists(self, auth_data: dict) -> ValidationCheck:
        """Check if authorization exists."""
        has_auth = auth_data.get("auth_number") is not None

        return ValidationCheck(
            check_name="auth_exists",
            status=ValidationStatus.PASSED if has_auth else ValidationStatus.FAILED,
            message=f"Authorization {'found' if has_auth else 'not found'}",
            code="AUTH002",
            details={"auth_number": auth_data.get("auth_number")},
        )

    async def _check_auth_approved(self, auth_data: dict) -> ValidationCheck:
        """Check if authorization is approved."""
        status = auth_data.get("status", "unknown")
        is_approved = status == "approved"

        return ValidationCheck(
            check_name="auth_approved",
            status=ValidationStatus.PASSED if is_approved else ValidationStatus.FAILED,
            message=f"Authorization status: {status}",
            code="AUTH003",
            details={"status": status},
        )

    async def _check_auth_valid(
        self, auth_data: dict, service_date: date
    ) -> ValidationCheck:
        """Check if authorization is valid for service date."""
        effective_date = auth_data.get("effective_date", date.min)
        expiry_date = auth_data.get("expiry_date", date.max)

        is_valid = effective_date <= service_date <= expiry_date

        return ValidationCheck(
            check_name="auth_valid",
            status=ValidationStatus.PASSED if is_valid else ValidationStatus.FAILED,
            message=f"Authorization {'valid' if is_valid else 'not valid'} for service date",
            code="AUTH004",
            details={
                "effective_date": str(effective_date),
                "expiry_date": str(expiry_date),
                "service_date": str(service_date),
            },
        )

    async def _check_units_available(self, auth_data: dict) -> ValidationCheck:
        """Check if authorized units are available."""
        authorized = auth_data.get("authorized_units", 0)
        used = auth_data.get("used_units", 0)
        remaining = authorized - used if authorized else None

        has_units = remaining is None or remaining > 0

        return ValidationCheck(
            check_name="units_available",
            status=ValidationStatus.PASSED if has_units else ValidationStatus.FAILED,
            message=f"Authorized units: {remaining if remaining is not None else 'unlimited'} remaining",
            code="AUTH005",
            details={
                "authorized_units": authorized,
                "used_units": used,
                "remaining": remaining,
            },
        )


# =============================================================================
# Medical Necessity Validator
# =============================================================================


class MedicalNecessityValidator:
    """Validates medical necessity based on diagnosis and procedure codes."""

    # Sample diagnosis-procedure mappings (production would use clinical database)
    VALID_COMBINATIONS = {
        # Diabetes-related
        ("E11.9", "82947"): True,  # Type 2 diabetes + glucose test
        ("E11.65", "83036"): True,  # DM with hyperglycemia + HbA1c
        # Hypertension-related
        ("I10", "93000"): True,  # Essential hypertension + ECG
        ("I10", "80061"): True,  # Essential hypertension + lipid panel
        # Respiratory
        ("J06.9", "99213"): True,  # Upper respiratory infection + office visit
        ("J18.9", "71046"): True,  # Pneumonia + chest x-ray
    }

    # Age-inappropriate procedures
    AGE_RESTRICTIONS = {
        "77067": (40, 999),  # Mammography: ages 40+
        "G0101": (18, 999),  # Pelvic exam: ages 18+
        "84153": (50, 999),  # PSA: ages 50+
    }

    # Gender-specific procedures
    GENDER_SPECIFIC = {
        "77067": ["F"],  # Mammography: female
        "G0101": ["F"],  # Pelvic exam: female
        "84153": ["M"],  # PSA: male
    }

    async def validate(
        self,
        context: AdjudicationContext,
        diagnosis_codes: list[str],
        procedure_codes: list[str],
        member_age: Optional[int] = None,
        member_gender: Optional[str] = None,
    ) -> MedicalNecessityResult:
        """
        Validate medical necessity for claim adjudication.

        Args:
            context: Adjudication context with claim details
            diagnosis_codes: List of ICD-10 diagnosis codes
            procedure_codes: List of CPT procedure codes
            member_age: Member age for age-appropriateness checks
            member_gender: Member gender for gender-appropriateness checks

        Returns:
            MedicalNecessityResult with validation details
        """
        result = MedicalNecessityResult(checks=[], flags=[])

        # Check 1: Valid ICD-10 codes
        icd_check = await self._check_icd10_valid(diagnosis_codes)
        result.checks.append(icd_check)
        result.icd10_valid = icd_check.status == ValidationStatus.PASSED

        # Check 2: Valid CPT codes
        cpt_check = await self._check_cpt_valid(procedure_codes)
        result.checks.append(cpt_check)
        result.cpt_valid = cpt_check.status == ValidationStatus.PASSED

        # Check 3: Diagnosis supports procedure
        combination_check = await self._check_diagnosis_supports_procedure(
            diagnosis_codes, procedure_codes
        )
        result.checks.append(combination_check)
        result.diagnosis_supports_procedure = (
            combination_check.status == ValidationStatus.PASSED
        )

        # Check 4: Age appropriate (if age provided)
        if member_age is not None:
            age_check = await self._check_age_appropriate(procedure_codes, member_age)
            result.checks.append(age_check)
            result.age_appropriate = age_check.status == ValidationStatus.PASSED

        # Check 5: Gender appropriate (if gender provided)
        if member_gender is not None:
            gender_check = await self._check_gender_appropriate(
                procedure_codes, member_gender
            )
            result.checks.append(gender_check)
            result.gender_appropriate = gender_check.status == ValidationStatus.PASSED

        # Check 6: Code combination validity
        combination_valid_check = await self._check_code_combination_valid(
            diagnosis_codes, procedure_codes
        )
        result.checks.append(combination_valid_check)
        result.code_combination_valid = (
            combination_valid_check.status == ValidationStatus.PASSED
        )

        # Determine overall validity
        result.is_valid = all([
            result.icd10_valid,
            result.cpt_valid,
            result.diagnosis_supports_procedure,
            result.age_appropriate,
            result.gender_appropriate,
            result.code_combination_valid,
        ])

        # Set denial reason if not valid
        if not result.is_valid:
            if not result.diagnosis_supports_procedure:
                result.denial_reason = DenialReason.NOT_MEDICALLY_NECESSARY
                result.denial_message = "Diagnosis does not support procedure"
            elif not result.age_appropriate:
                result.denial_reason = DenialReason.NOT_MEDICALLY_NECESSARY
                result.denial_message = "Procedure not appropriate for member age"
            elif not result.gender_appropriate:
                result.denial_reason = DenialReason.NOT_MEDICALLY_NECESSARY
                result.denial_message = "Procedure not appropriate for member gender"

        return result

    async def _check_icd10_valid(self, diagnosis_codes: list[str]) -> ValidationCheck:
        """Check if ICD-10 codes are valid format."""
        # Basic format validation (A00.0 to Z99.9)
        import re
        pattern = r"^[A-Z]\d{2}(\.\d{1,4})?$"

        invalid_codes = [
            code for code in diagnosis_codes
            if not re.match(pattern, code)
        ]

        is_valid = len(invalid_codes) == 0

        return ValidationCheck(
            check_name="icd10_valid",
            status=ValidationStatus.PASSED if is_valid else ValidationStatus.WARNING,
            message=f"All ICD-10 codes valid" if is_valid else f"Invalid codes: {invalid_codes}",
            code="MED001",
            details={
                "codes": diagnosis_codes,
                "invalid_codes": invalid_codes,
            },
        )

    async def _check_cpt_valid(self, procedure_codes: list[str]) -> ValidationCheck:
        """Check if CPT codes are valid format."""
        # CPT codes are 5 digits or HCPCS codes
        import re
        pattern = r"^(\d{5}|[A-Z]\d{4})$"

        invalid_codes = [
            code for code in procedure_codes
            if not re.match(pattern, code)
        ]

        is_valid = len(invalid_codes) == 0

        return ValidationCheck(
            check_name="cpt_valid",
            status=ValidationStatus.PASSED if is_valid else ValidationStatus.WARNING,
            message=f"All CPT codes valid" if is_valid else f"Invalid codes: {invalid_codes}",
            code="MED002",
            details={
                "codes": procedure_codes,
                "invalid_codes": invalid_codes,
            },
        )

    async def _check_diagnosis_supports_procedure(
        self, diagnosis_codes: list[str], procedure_codes: list[str]
    ) -> ValidationCheck:
        """Check if diagnoses support the procedures."""
        # In production, use clinical database or NCD/LCD rules
        # For demo, check against sample mappings or accept common patterns

        # Generally pass for standard office visits and common procedures
        common_procedures = {"99213", "99214", "99215", "99203", "99204", "99205"}

        if any(code in common_procedures for code in procedure_codes):
            return ValidationCheck(
                check_name="diagnosis_supports_procedure",
                status=ValidationStatus.PASSED,
                message="Standard evaluation/management code - diagnosis appropriate",
                code="MED003",
            )

        # Check known valid combinations
        for dx in diagnosis_codes:
            for px in procedure_codes:
                if self.VALID_COMBINATIONS.get((dx, px), False):
                    return ValidationCheck(
                        check_name="diagnosis_supports_procedure",
                        status=ValidationStatus.PASSED,
                        message="Valid diagnosis-procedure combination found",
                        code="MED003",
                        details={"diagnosis": dx, "procedure": px},
                    )

        # Default to passed with warning for unknown combinations
        return ValidationCheck(
            check_name="diagnosis_supports_procedure",
            status=ValidationStatus.PASSED,
            message="Diagnosis-procedure combination accepted (manual review may apply)",
            code="MED003",
            details={
                "diagnoses": diagnosis_codes,
                "procedures": procedure_codes,
            },
        )

    async def _check_age_appropriate(
        self, procedure_codes: list[str], member_age: int
    ) -> ValidationCheck:
        """Check if procedures are age-appropriate."""
        inappropriate = []

        for code in procedure_codes:
            if code in self.AGE_RESTRICTIONS:
                min_age, max_age = self.AGE_RESTRICTIONS[code]
                if not (min_age <= member_age <= max_age):
                    inappropriate.append(code)

        is_appropriate = len(inappropriate) == 0

        return ValidationCheck(
            check_name="age_appropriate",
            status=ValidationStatus.PASSED if is_appropriate else ValidationStatus.FAILED,
            message="All procedures age-appropriate" if is_appropriate else f"Age-inappropriate procedures: {inappropriate}",
            code="MED004",
            details={
                "member_age": member_age,
                "inappropriate_codes": inappropriate,
            },
        )

    async def _check_gender_appropriate(
        self, procedure_codes: list[str], member_gender: str
    ) -> ValidationCheck:
        """Check if procedures are gender-appropriate."""
        inappropriate = []

        for code in procedure_codes:
            if code in self.GENDER_SPECIFIC:
                allowed_genders = self.GENDER_SPECIFIC[code]
                if member_gender.upper() not in allowed_genders:
                    inappropriate.append(code)

        is_appropriate = len(inappropriate) == 0

        return ValidationCheck(
            check_name="gender_appropriate",
            status=ValidationStatus.PASSED if is_appropriate else ValidationStatus.FAILED,
            message="All procedures gender-appropriate" if is_appropriate else f"Gender-inappropriate procedures: {inappropriate}",
            code="MED005",
            details={
                "member_gender": member_gender,
                "inappropriate_codes": inappropriate,
            },
        )

    async def _check_code_combination_valid(
        self, diagnosis_codes: list[str], procedure_codes: list[str]
    ) -> ValidationCheck:
        """Check for invalid code combinations (edit checks)."""
        # In production, implement CCI (Correct Coding Initiative) edits
        # For demo, always pass

        return ValidationCheck(
            check_name="code_combination_valid",
            status=ValidationStatus.PASSED,
            message="No conflicting code combinations detected",
            code="MED006",
        )


# =============================================================================
# Duplicate Claim Checker
# =============================================================================


class DuplicateClaimChecker:
    """Checks for duplicate or near-duplicate claims."""

    async def check(
        self,
        context: AdjudicationContext,
        procedure_codes: list[str],
        existing_claims: Optional[list[dict]] = None,
    ) -> DuplicateCheckResult:
        """
        Check for duplicate claims.

        Args:
            context: Adjudication context with claim details
            procedure_codes: List of procedure codes on claim
            existing_claims: Optional list of existing claims (for testing/demo)

        Returns:
            DuplicateCheckResult with duplicate detection details
        """
        result = DuplicateCheckResult(checks=[])

        # In production, query database for similar claims
        if existing_claims is None:
            existing_claims = await self._fetch_similar_claims(context, procedure_codes)

        if not existing_claims:
            result.is_duplicate = False
            result.checks.append(
                ValidationCheck(
                    check_name="duplicate_check",
                    status=ValidationStatus.PASSED,
                    message="No similar claims found",
                    code="DUP001",
                )
            )
            return result

        # Check each existing claim for duplicate match
        best_match = None
        best_score = 0.0

        for existing in existing_claims:
            score, matching_fields = await self._calculate_similarity(
                context, procedure_codes, existing
            )

            if score > best_score:
                best_score = score
                best_match = existing
                result.matching_fields = matching_fields

        result.similarity_score = best_score

        # Determine if duplicate
        if best_score >= 0.95:  # Exact or near-exact duplicate
            result.is_duplicate = True
            result.original_claim_id = best_match.get("id")
            result.original_tracking_number = best_match.get("tracking_number")
            result.checks.append(
                ValidationCheck(
                    check_name="duplicate_check",
                    status=ValidationStatus.FAILED,
                    message=f"Duplicate claim detected (similarity: {best_score:.2%})",
                    code="DUP002",
                    details={
                        "original_claim_id": str(result.original_claim_id),
                        "matching_fields": result.matching_fields,
                    },
                )
            )
        elif best_score >= 0.75:  # Possible duplicate - flag for review
            result.possible_duplicate = True
            result.original_claim_id = best_match.get("id")
            result.original_tracking_number = best_match.get("tracking_number")
            result.checks.append(
                ValidationCheck(
                    check_name="duplicate_check",
                    status=ValidationStatus.WARNING,
                    message=f"Possible duplicate claim (similarity: {best_score:.2%})",
                    code="DUP003",
                    details={
                        "original_claim_id": str(result.original_claim_id),
                        "matching_fields": result.matching_fields,
                    },
                )
            )
        else:
            result.checks.append(
                ValidationCheck(
                    check_name="duplicate_check",
                    status=ValidationStatus.PASSED,
                    message="No duplicate claims detected",
                    code="DUP001",
                )
            )

        return result

    async def _fetch_similar_claims(
        self, context: AdjudicationContext, procedure_codes: list[str]
    ) -> list[dict]:
        """Fetch potentially similar claims from database (simulated)."""
        # In production, query for claims with same member, provider, dates, codes
        # For demo, return empty list (no duplicates)
        return []

    async def _calculate_similarity(
        self,
        context: AdjudicationContext,
        procedure_codes: list[str],
        existing: dict,
    ) -> tuple[float, list[str]]:
        """Calculate similarity score between claims."""
        matching_fields = []
        total_weight = 0.0
        matched_weight = 0.0

        # Member ID (weight: 0.20)
        total_weight += 0.20
        if str(context.member_id) == str(existing.get("member_id")):
            matched_weight += 0.20
            matching_fields.append("member_id")

        # Provider ID (weight: 0.15)
        total_weight += 0.15
        if str(context.provider_id) == str(existing.get("provider_id")):
            matched_weight += 0.15
            matching_fields.append("provider_id")

        # Service date (weight: 0.25)
        total_weight += 0.25
        if context.service_date == existing.get("service_date"):
            matched_weight += 0.25
            matching_fields.append("service_date")

        # Procedure codes (weight: 0.30)
        total_weight += 0.30
        existing_codes = set(existing.get("procedure_codes", []))
        claim_codes = set(procedure_codes)
        if existing_codes and claim_codes:
            code_overlap = len(existing_codes & claim_codes) / max(
                len(existing_codes), len(claim_codes)
            )
            matched_weight += 0.30 * code_overlap
            if code_overlap > 0:
                matching_fields.append("procedure_codes")

        # Charged amount (weight: 0.10)
        total_weight += 0.10
        existing_amount = existing.get("total_charged")
        if existing_amount and abs(context.total_charged - existing_amount) < Decimal("1.00"):
            matched_weight += 0.10
            matching_fields.append("total_charged")

        return matched_weight / total_weight if total_weight > 0 else 0.0, matching_fields


# =============================================================================
# Timely Filing Checker
# =============================================================================


class TimelyFilingChecker:
    """Checks if claim was filed within timely filing limits."""

    # Default filing limits by payer type (in days)
    DEFAULT_FILING_LIMITS = {
        "medicare": 365,
        "medicaid": 365,
        "commercial": 365,
        "workers_comp": 365,
        "auto": 365,
        "default": 365,
    }

    async def check(
        self,
        context: AdjudicationContext,
        payer_type: str = "commercial",
        filing_limit_override: Optional[int] = None,
    ) -> TimelyFilingResult:
        """
        Check if claim was filed timely.

        Args:
            context: Adjudication context with claim details
            payer_type: Type of payer for filing limit lookup
            filing_limit_override: Override for filing limit days

        Returns:
            TimelyFilingResult with timely filing determination
        """
        result = TimelyFilingResult(
            service_date=context.service_date,
            submission_date=context.submission_date.date(),
            checks=[],
        )

        # Determine filing limit
        result.filing_limit_days = (
            filing_limit_override
            or self.DEFAULT_FILING_LIMITS.get(
                payer_type, self.DEFAULT_FILING_LIMITS["default"]
            )
        )

        # Calculate days elapsed
        result.days_elapsed = (
            context.submission_date.date() - context.service_date
        ).days

        # Check if timely
        result.is_timely = result.days_elapsed <= result.filing_limit_days

        if result.is_timely:
            result.checks.append(
                ValidationCheck(
                    check_name="timely_filing",
                    status=ValidationStatus.PASSED,
                    message=f"Claim filed within {result.filing_limit_days} day limit ({result.days_elapsed} days elapsed)",
                    code="TF001",
                    details={
                        "days_elapsed": result.days_elapsed,
                        "filing_limit": result.filing_limit_days,
                    },
                )
            )
        else:
            result.denial_reason = DenialReason.TIMELY_FILING_EXCEEDED
            result.checks.append(
                ValidationCheck(
                    check_name="timely_filing",
                    status=ValidationStatus.FAILED,
                    message=f"Claim exceeds {result.filing_limit_days} day filing limit ({result.days_elapsed} days elapsed)",
                    code="TF002",
                    details={
                        "days_elapsed": result.days_elapsed,
                        "filing_limit": result.filing_limit_days,
                    },
                )
            )

        return result


# =============================================================================
# Factory Functions
# =============================================================================


_policy_validator: Optional[PolicyValidator] = None
_eligibility_validator: Optional[EligibilityValidator] = None
_network_validator: Optional[NetworkValidator] = None
_prior_auth_validator: Optional[PriorAuthValidator] = None
_medical_necessity_validator: Optional[MedicalNecessityValidator] = None
_duplicate_checker: Optional[DuplicateClaimChecker] = None
_timely_filing_checker: Optional[TimelyFilingChecker] = None


def get_policy_validator() -> PolicyValidator:
    """Get singleton PolicyValidator instance."""
    global _policy_validator
    if _policy_validator is None:
        _policy_validator = PolicyValidator()
    return _policy_validator


def get_eligibility_validator() -> EligibilityValidator:
    """Get singleton EligibilityValidator instance."""
    global _eligibility_validator
    if _eligibility_validator is None:
        _eligibility_validator = EligibilityValidator()
    return _eligibility_validator


def get_network_validator() -> NetworkValidator:
    """Get singleton NetworkValidator instance."""
    global _network_validator
    if _network_validator is None:
        _network_validator = NetworkValidator()
    return _network_validator


def get_prior_auth_validator() -> PriorAuthValidator:
    """Get singleton PriorAuthValidator instance."""
    global _prior_auth_validator
    if _prior_auth_validator is None:
        _prior_auth_validator = PriorAuthValidator()
    return _prior_auth_validator


def get_medical_necessity_validator() -> MedicalNecessityValidator:
    """Get singleton MedicalNecessityValidator instance."""
    global _medical_necessity_validator
    if _medical_necessity_validator is None:
        _medical_necessity_validator = MedicalNecessityValidator()
    return _medical_necessity_validator


def get_duplicate_checker() -> DuplicateClaimChecker:
    """Get singleton DuplicateClaimChecker instance."""
    global _duplicate_checker
    if _duplicate_checker is None:
        _duplicate_checker = DuplicateClaimChecker()
    return _duplicate_checker


def get_timely_filing_checker() -> TimelyFilingChecker:
    """Get singleton TimelyFilingChecker instance."""
    global _timely_filing_checker
    if _timely_filing_checker is None:
        _timely_filing_checker = TimelyFilingChecker()
    return _timely_filing_checker
