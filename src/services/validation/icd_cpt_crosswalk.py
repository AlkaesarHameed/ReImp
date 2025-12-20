"""
ICD-CPT Crosswalk Validator (Rule 4).

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Validates that procedure codes (CPT) are medically appropriate for
the submitted diagnosis codes (ICD-10).
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from src.gateways.search_gateway import get_search_gateway, SearchGateway
from src.services.validation_cache import get_validation_cache, ValidationCacheService

logger = logging.getLogger(__name__)


class CrosswalkStatus(str, Enum):
    """Crosswalk validation status."""

    VALID = "valid"
    INVALID = "invalid"
    UNCERTAIN = "uncertain"
    NOT_FOUND = "not_found"


@dataclass
class PairValidation:
    """Validation result for a single ICD-CPT pair."""

    icd_code: str
    cpt_code: str
    status: CrosswalkStatus
    confidence: float
    evidence: Optional[str] = None
    source: str = "DEFAULT"
    ncci_edit: bool = False
    mue_exceeded: bool = False
    mue_limit: Optional[int] = None
    units_claimed: Optional[int] = None


@dataclass
class CrosswalkValidationResult:
    """Complete crosswalk validation result."""

    is_valid: bool
    overall_confidence: float
    pair_validations: list[PairValidation]
    invalid_pairs: list[PairValidation]
    ncci_edits_found: list[dict[str, Any]]
    mue_violations: list[dict[str, Any]]
    warnings: list[str]
    execution_time_ms: int

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical validation issues."""
        return len(self.invalid_pairs) > 0 or len(self.ncci_edits_found) > 0

    def to_evidence_dict(self) -> dict[str, Any]:
        """Convert to evidence format for rejection."""
        return {
            "is_valid": self.is_valid,
            "confidence": self.overall_confidence,
            "invalid_pair_count": len(self.invalid_pairs),
            "ncci_edit_count": len(self.ncci_edits_found),
            "mue_violation_count": len(self.mue_violations),
            "invalid_pairs": [
                {
                    "icd": p.icd_code,
                    "cpt": p.cpt_code,
                    "status": p.status.value,
                    "evidence": p.evidence,
                }
                for p in self.invalid_pairs
            ],
            "ncci_edits": self.ncci_edits_found,
            "mue_violations": self.mue_violations,
        }


class ICDCPTCrosswalkValidator:
    """
    Validates ICD-CPT code pairings for medical appropriateness.

    Checks:
    1. ICD-CPT crosswalk validity (procedure supports diagnosis)
    2. NCCI PTP edits (bundling rules)
    3. MUE limits (maximum units)

    Source: Design Document Section 2.2 - Validation Rules (Rule 4)
    """

    def __init__(
        self,
        search_gateway: Optional[SearchGateway] = None,
        cache: Optional[ValidationCacheService] = None,
    ):
        """
        Initialize the crosswalk validator.

        Args:
            search_gateway: Typesense search gateway
            cache: Validation cache service
        """
        self._search_gateway = search_gateway
        self._cache = cache

    @property
    def search_gateway(self) -> SearchGateway:
        """Get search gateway instance."""
        if self._search_gateway is None:
            self._search_gateway = get_search_gateway()
        return self._search_gateway

    @property
    def cache(self) -> ValidationCacheService:
        """Get cache instance."""
        if self._cache is None:
            self._cache = get_validation_cache()
        return self._cache

    async def validate(
        self,
        icd_codes: list[str],
        cpt_codes: list[str],
        units_per_cpt: Optional[dict[str, int]] = None,
    ) -> CrosswalkValidationResult:
        """
        Validate all ICD-CPT code pairings.

        Args:
            icd_codes: List of ICD-10 diagnosis codes
            cpt_codes: List of CPT procedure codes
            units_per_cpt: Optional mapping of CPT codes to units claimed

        Returns:
            CrosswalkValidationResult with all validation details
        """
        import time
        start_time = time.perf_counter()

        pair_validations: list[PairValidation] = []
        ncci_edits_found: list[dict[str, Any]] = []
        mue_violations: list[dict[str, Any]] = []
        warnings: list[str] = []

        # Normalize codes
        icd_codes = [code.upper().strip() for code in icd_codes if code]
        cpt_codes = [code.upper().strip() for code in cpt_codes if code]
        units_per_cpt = units_per_cpt or {}

        if not icd_codes:
            warnings.append("No ICD-10 codes provided")
        if not cpt_codes:
            warnings.append("No CPT codes provided")

        # Step 1: Validate each ICD-CPT pair
        for icd in icd_codes:
            for cpt in cpt_codes:
                pair_result = await self._validate_pair(icd, cpt)
                pair_validations.append(pair_result)

        # Step 2: Check NCCI PTP edits between CPT codes
        for i, cpt1 in enumerate(cpt_codes):
            for cpt2 in cpt_codes[i+1:]:
                ncci_result = await self._check_ncci_edit(cpt1, cpt2)
                if ncci_result:
                    ncci_edits_found.append(ncci_result)

        # Step 3: Check MUE limits
        for cpt in cpt_codes:
            units = units_per_cpt.get(cpt, 1)
            mue_result = await self._check_mue_limit(cpt, units)
            if mue_result:
                mue_violations.append(mue_result)

        # Collect invalid pairs
        invalid_pairs = [
            p for p in pair_validations
            if p.status == CrosswalkStatus.INVALID
        ]

        # Calculate overall validity and confidence
        is_valid = (
            len(invalid_pairs) == 0 and
            len(ncci_edits_found) == 0 and
            len(mue_violations) == 0
        )

        if pair_validations:
            overall_confidence = sum(p.confidence for p in pair_validations) / len(pair_validations)
        else:
            overall_confidence = 0.5  # No data to validate

        execution_time = int((time.perf_counter() - start_time) * 1000)

        result = CrosswalkValidationResult(
            is_valid=is_valid,
            overall_confidence=overall_confidence,
            pair_validations=pair_validations,
            invalid_pairs=invalid_pairs,
            ncci_edits_found=ncci_edits_found,
            mue_violations=mue_violations,
            warnings=warnings,
            execution_time_ms=execution_time,
        )

        logger.info(
            f"Crosswalk validation: valid={is_valid}, "
            f"pairs={len(pair_validations)}, invalid={len(invalid_pairs)}, "
            f"ncci={len(ncci_edits_found)}, mue={len(mue_violations)}, "
            f"time={execution_time}ms"
        )

        return result

    async def _validate_pair(
        self,
        icd_code: str,
        cpt_code: str,
    ) -> PairValidation:
        """Validate a single ICD-CPT pair."""
        # Check cache first
        cached = await self.cache.get_crosswalk(icd_code, cpt_code)
        if cached:
            return PairValidation(
                icd_code=icd_code,
                cpt_code=cpt_code,
                status=CrosswalkStatus(cached.get("status", "uncertain")),
                confidence=cached.get("confidence", 0.5),
                evidence=cached.get("evidence"),
                source=cached.get("source", "CACHE"),
            )

        try:
            # Query Typesense for crosswalk data
            result = await self.search_gateway.validate_icd_cpt_pair(icd_code, cpt_code)

            if result.is_valid:
                status = CrosswalkStatus.VALID
            elif result.confidence < 0.3:
                status = CrosswalkStatus.INVALID
            else:
                status = CrosswalkStatus.UNCERTAIN

            pair_result = PairValidation(
                icd_code=icd_code,
                cpt_code=cpt_code,
                status=status,
                confidence=result.confidence,
                evidence=result.evidence,
                source=result.source,
            )

            # Cache the result
            await self.cache.set_crosswalk(
                icd_code,
                cpt_code,
                {
                    "status": status.value,
                    "confidence": result.confidence,
                    "evidence": result.evidence,
                    "source": result.source,
                }
            )

            return pair_result

        except Exception as e:
            logger.error(f"Error validating pair {icd_code}/{cpt_code}: {e}")
            return PairValidation(
                icd_code=icd_code,
                cpt_code=cpt_code,
                status=CrosswalkStatus.UNCERTAIN,
                confidence=0.5,
                evidence=f"Validation error: {str(e)}",
                source="ERROR",
            )

    async def _check_ncci_edit(
        self,
        cpt1: str,
        cpt2: str,
    ) -> Optional[dict[str, Any]]:
        """Check for NCCI PTP edit between two CPT codes."""
        try:
            edit = await self.search_gateway.check_ncci_edit(cpt1, cpt2)

            if edit:
                return {
                    "column1_code": edit.column1_code,
                    "column2_code": edit.column2_code,
                    "modifier_indicator": edit.modifier_indicator.value,
                    "can_use_modifier": edit.modifier_indicator.value == "1",
                    "rationale": edit.rationale,
                    "message": (
                        f"NCCI edit found: {edit.column1_code} and {edit.column2_code} "
                        f"should not be billed together"
                        + (". Modifier may be used." if edit.modifier_indicator.value == "1" else ".")
                    ),
                }

            return None

        except Exception as e:
            logger.error(f"Error checking NCCI edit {cpt1}/{cpt2}: {e}")
            return None

    async def _check_mue_limit(
        self,
        cpt_code: str,
        units_claimed: int,
    ) -> Optional[dict[str, Any]]:
        """Check if units claimed exceed MUE limit."""
        try:
            mue = await self.search_gateway.get_mue_limit(cpt_code)

            if mue:
                # Use practitioner limit as default
                limit = mue.practitioner_limit

                if units_claimed > limit:
                    return {
                        "cpt_code": cpt_code,
                        "units_claimed": units_claimed,
                        "mue_limit": limit,
                        "exceeded_by": units_claimed - limit,
                        "adjudicator": mue.adjudicator.value,
                        "rationale": mue.rationale,
                        "message": (
                            f"MUE violation: {units_claimed} units claimed for {cpt_code}, "
                            f"limit is {limit} units"
                        ),
                    }

            return None

        except Exception as e:
            logger.error(f"Error checking MUE limit for {cpt_code}: {e}")
            return None

    async def validate_single_pair(
        self,
        icd_code: str,
        cpt_code: str,
    ) -> PairValidation:
        """
        Validate a single ICD-CPT pair.

        Convenience method for single-pair validation.

        Args:
            icd_code: ICD-10 diagnosis code
            cpt_code: CPT procedure code

        Returns:
            PairValidation result
        """
        return await self._validate_pair(icd_code.upper().strip(), cpt_code.upper().strip())


# Singleton instance
_crosswalk_validator: Optional[ICDCPTCrosswalkValidator] = None


def get_crosswalk_validator() -> ICDCPTCrosswalkValidator:
    """Get or create the singleton crosswalk validator."""
    global _crosswalk_validator
    if _crosswalk_validator is None:
        _crosswalk_validator = ICDCPTCrosswalkValidator()
    return _crosswalk_validator
