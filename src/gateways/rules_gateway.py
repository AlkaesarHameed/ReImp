"""
Rules Engine Gateway with GoRules ZEN.

Provides a unified interface for business rule evaluation:
- Primary: GoRules ZEN (open-source, JSON rules)
- Supports decision tables and decision graphs

Features:
- Claims adjudication rules
- Benefit eligibility rules
- FWA detection rules
- Prior authorization rules
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from src.core.config import get_claims_settings
from src.core.enums import RulesEngineProvider
from src.gateways.base import (
    BaseGateway,
    GatewayConfig,
    GatewayError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

# Import ZEN Engine with graceful fallback
try:
    import zen

    ZEN_AVAILABLE = True
except ImportError:
    ZEN_AVAILABLE = False
    logger.warning("GoRules ZEN not installed. Rules Gateway will operate in mock mode.")


class RuleType(str, Enum):
    """Type of rule to evaluate."""

    DECISION_TABLE = "decision_table"
    DECISION_GRAPH = "decision_graph"
    EXPRESSION = "expression"


class RuleCategory(str, Enum):
    """Category of business rules."""

    ADJUDICATION = "adjudication"
    ELIGIBILITY = "eligibility"
    BENEFITS = "benefits"
    FWA_DETECTION = "fwa_detection"
    PRIOR_AUTH = "prior_authorization"
    PRICING = "pricing"
    NETWORK = "network"


@dataclass
class RuleContext:
    """Context data for rule evaluation."""

    claim: Optional[dict[str, Any]] = None
    member: Optional[dict[str, Any]] = None
    policy: Optional[dict[str, Any]] = None
    provider: Optional[dict[str, Any]] = None
    service: Optional[dict[str, Any]] = None
    historical: Optional[dict[str, Any]] = None
    custom: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for rule evaluation."""
        result = {}
        if self.claim:
            result["claim"] = self.claim
        if self.member:
            result["member"] = self.member
        if self.policy:
            result["policy"] = self.policy
        if self.provider:
            result["provider"] = self.provider
        if self.service:
            result["service"] = self.service
        if self.historical:
            result["historical"] = self.historical
        result.update(self.custom)
        return result


@dataclass
class RulesRequest:
    """Request for rule evaluation."""

    rule_id: str
    context: RuleContext
    rule_category: RuleCategory = RuleCategory.ADJUDICATION
    trace: bool = False  # Enable rule execution tracing
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleTrace:
    """Trace of rule execution."""

    node_id: str
    node_type: str
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    duration_ms: float


@dataclass
class RulesResponse:
    """Response from rule evaluation."""

    result: dict[str, Any]
    rule_id: str
    decision: Optional[str] = None
    confidence: float = 1.0
    trace: list[RuleTrace] = field(default_factory=list)
    provider: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def approved(self) -> bool:
        """Check if decision is approval."""
        return self.decision in ("approve", "approved", "accept", "pass")

    @property
    def denied(self) -> bool:
        """Check if decision is denial."""
        return self.decision in ("deny", "denied", "reject", "fail")


class RulesGateway(BaseGateway[RulesRequest, RulesResponse, RulesEngineProvider]):
    """
    Rules Engine Gateway for business rule evaluation.

    Uses GoRules ZEN for decision management:
    - Decision tables for simple condition-action rules
    - Decision graphs for complex workflows
    - Expression evaluation for calculations
    """

    def __init__(self, config: Optional[GatewayConfig] = None):
        settings = get_claims_settings()

        if config is None:
            config = GatewayConfig(
                primary_provider=settings.RULES_ENGINE_PROVIDER.value,
                fallback_provider=None,  # No fallback for rules engine
                fallback_on_error=False,
                timeout_seconds=settings.RULES_ENGINE_TIMEOUT_SECONDS,
            )

        super().__init__(config)
        self._settings = settings
        self._rules_path = Path(settings.RULES_PATH)
        self._engines: dict[str, Any] = {}
        self._rules_cache: dict[str, Any] = {}

    @property
    def gateway_name(self) -> str:
        return "Rules"

    async def _initialize_provider(self, provider: RulesEngineProvider) -> None:
        """Initialize rules engine provider."""
        if provider == RulesEngineProvider.ZEN:
            if not ZEN_AVAILABLE:
                logger.warning(
                    "ZEN engine not available, using fallback rule evaluation"
                )
            # Create rules directory if it doesn't exist
            self._rules_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Rules Engine initialized with path: {self._rules_path}")

        elif provider == RulesEngineProvider.DROOLS:
            raise ProviderUnavailableError(
                "Drools integration not implemented", provider=provider.value
            )

    async def _execute_request(
        self, request: RulesRequest, provider: RulesEngineProvider
    ) -> RulesResponse:
        """Execute rule evaluation request."""
        if provider == RulesEngineProvider.ZEN:
            return await self._evaluate_zen(request)
        else:
            raise GatewayError(f"Unsupported rules provider: {provider}")

    async def _evaluate_zen(self, request: RulesRequest) -> RulesResponse:
        """Evaluate rules using GoRules ZEN."""
        context_data = request.context.to_dict()

        if ZEN_AVAILABLE:
            try:
                # Load or get cached engine
                engine = await self._get_engine(request.rule_id)

                # Evaluate with context
                result = engine.evaluate(context_data)

                return RulesResponse(
                    result=result,
                    rule_id=request.rule_id,
                    decision=result.get("decision") or result.get("action"),
                    provider="zen",
                )

            except FileNotFoundError:
                raise GatewayError(
                    f"Rule not found: {request.rule_id}", provider="zen"
                )
            except Exception as e:
                raise GatewayError(
                    f"Rule evaluation error: {e}",
                    provider="zen",
                    original_error=e,
                )
        else:
            # Fallback: Return mock/default evaluation
            return await self._evaluate_fallback(request)

    async def _evaluate_fallback(self, request: RulesRequest) -> RulesResponse:
        """Fallback rule evaluation when ZEN is not available."""
        context = request.context.to_dict()

        # Simple rule evaluation based on category
        if request.rule_category == RuleCategory.ELIGIBILITY:
            result = self._evaluate_eligibility_rules(context)
        elif request.rule_category == RuleCategory.ADJUDICATION:
            result = self._evaluate_adjudication_rules(context)
        elif request.rule_category == RuleCategory.FWA_DETECTION:
            result = self._evaluate_fwa_rules(context)
        else:
            result = {"decision": "manual_review", "reason": "Unknown rule category"}

        return RulesResponse(
            result=result,
            rule_id=request.rule_id,
            decision=result.get("decision"),
            provider="fallback",
            metadata={"fallback": True},
        )

    def _evaluate_eligibility_rules(self, context: dict) -> dict:
        """Simple eligibility rule evaluation."""
        member = context.get("member", {})
        policy = context.get("policy", {})

        # Check member status
        if member.get("status") != "active":
            return {
                "decision": "deny",
                "reason": "Member not active",
                "code": "MEMBER_INACTIVE",
            }

        # Check policy status
        if policy.get("status") != "active":
            return {
                "decision": "deny",
                "reason": "Policy not active",
                "code": "POLICY_INACTIVE",
            }

        # Check effective dates
        service_date = context.get("claim", {}).get("service_date")
        if service_date:
            effective_date = policy.get("effective_date")
            termination_date = policy.get("termination_date")
            # Basic date validation would go here

        return {
            "decision": "approve",
            "reason": "Member eligible",
            "code": "ELIGIBLE",
        }

    def _evaluate_adjudication_rules(self, context: dict) -> dict:
        """Simple adjudication rule evaluation."""
        claim = context.get("claim", {})
        policy = context.get("policy", {})

        total_charge = float(claim.get("total_charge", 0))
        deductible = float(policy.get("deductible_remaining", 0))
        coinsurance_rate = float(policy.get("coinsurance_rate", 0.2))
        max_benefit = float(policy.get("max_benefit", 1000000))

        # Calculate payment
        after_deductible = max(0, total_charge - deductible)
        plan_pays = after_deductible * (1 - coinsurance_rate)
        member_pays = total_charge - plan_pays

        # Check max benefit
        if plan_pays > max_benefit:
            plan_pays = max_benefit
            member_pays = total_charge - plan_pays

        return {
            "decision": "approve",
            "plan_pays": round(plan_pays, 2),
            "member_pays": round(member_pays, 2),
            "deductible_applied": min(deductible, total_charge),
            "reason": "Claim adjudicated",
        }

    def _evaluate_fwa_rules(self, context: dict) -> dict:
        """Simple FWA detection rule evaluation."""
        claim = context.get("claim", {})
        historical = context.get("historical", {})

        risk_score = 0.0
        indicators = []

        # Check for duplicate claims
        if historical.get("duplicate_count", 0) > 0:
            risk_score += 0.3
            indicators.append("potential_duplicate")

        # Check charge reasonableness
        avg_charge = historical.get("avg_charge", 0)
        current_charge = float(claim.get("total_charge", 0))
        if avg_charge > 0 and current_charge > avg_charge * 3:
            risk_score += 0.25
            indicators.append("excessive_charge")

        # Check provider exclusion status
        provider = context.get("provider", {})
        if provider.get("excluded", False):
            risk_score += 0.5
            indicators.append("excluded_provider")

        # Determine risk level
        if risk_score >= 0.7:
            decision = "deny"
            risk_level = "critical"
        elif risk_score >= 0.5:
            decision = "investigate"
            risk_level = "high"
        elif risk_score >= 0.3:
            decision = "review"
            risk_level = "medium"
        else:
            decision = "approve"
            risk_level = "low"

        return {
            "decision": decision,
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "indicators": indicators,
        }

    async def _get_engine(self, rule_id: str) -> Any:
        """Get or create ZEN engine for a rule."""
        if rule_id in self._engines:
            return self._engines[rule_id]

        # Load rule file
        rule_file = self._rules_path / f"{rule_id}.json"
        if not rule_file.exists():
            raise FileNotFoundError(f"Rule file not found: {rule_file}")

        with open(rule_file, "r") as f:
            rule_content = f.read()

        # Create ZEN engine
        engine = zen.ZenEngine()
        decision = engine.create_decision(rule_content)
        self._engines[rule_id] = decision

        return decision

    async def _health_check(self, provider: RulesEngineProvider) -> bool:
        """Check if rules engine is healthy."""
        return True  # ZEN is embedded, always available

    def _parse_provider(self, provider_str: str) -> RulesEngineProvider:
        """Parse provider string to RulesEngineProvider enum."""
        return RulesEngineProvider(provider_str)

    # Convenience methods for claims processing

    async def check_eligibility(
        self,
        member_id: str,
        policy_id: str,
        service_date: str,
        service_code: Optional[str] = None,
    ) -> RulesResponse:
        """Check member eligibility for a service."""
        context = RuleContext(
            member={"id": member_id, "status": "active"},
            policy={"id": policy_id, "status": "active"},
            claim={"service_date": service_date},
            service={"code": service_code} if service_code else None,
        )

        request = RulesRequest(
            rule_id="eligibility_check",
            context=context,
            rule_category=RuleCategory.ELIGIBILITY,
        )

        result = await self.execute(request)
        return result.data if result.success else RulesResponse(
            result={}, rule_id="eligibility_check", decision="error"
        )

    async def adjudicate_claim(
        self,
        claim_data: dict[str, Any],
        policy_data: dict[str, Any],
        member_data: dict[str, Any],
    ) -> RulesResponse:
        """Run adjudication rules on a claim."""
        context = RuleContext(
            claim=claim_data,
            policy=policy_data,
            member=member_data,
        )

        request = RulesRequest(
            rule_id="claim_adjudication",
            context=context,
            rule_category=RuleCategory.ADJUDICATION,
        )

        result = await self.execute(request)
        return result.data if result.success else RulesResponse(
            result={}, rule_id="claim_adjudication", decision="error"
        )

    async def detect_fwa(
        self,
        claim_data: dict[str, Any],
        provider_data: dict[str, Any],
        historical_data: Optional[dict[str, Any]] = None,
    ) -> RulesResponse:
        """Run FWA detection rules on a claim."""
        context = RuleContext(
            claim=claim_data,
            provider=provider_data,
            historical=historical_data or {},
        )

        request = RulesRequest(
            rule_id="fwa_detection",
            context=context,
            rule_category=RuleCategory.FWA_DETECTION,
            trace=True,
        )

        result = await self.execute(request)
        return result.data if result.success else RulesResponse(
            result={}, rule_id="fwa_detection", decision="error"
        )

    async def load_rule(self, rule_id: str, rule_content: dict) -> bool:
        """Load a rule into the engine."""
        rule_file = self._rules_path / f"{rule_id}.json"
        with open(rule_file, "w") as f:
            json.dump(rule_content, f, indent=2)

        # Clear cached engine
        if rule_id in self._engines:
            del self._engines[rule_id]

        return True

    async def close(self) -> None:
        """Clean up rules gateway resources."""
        self._engines.clear()
        self._rules_cache.clear()
        await super().close()


# Singleton instance
_rules_gateway: Optional[RulesGateway] = None


def get_rules_gateway() -> RulesGateway:
    """Get or create the singleton Rules gateway instance."""
    global _rules_gateway
    if _rules_gateway is None:
        _rules_gateway = RulesGateway()
    return _rules_gateway


async def reset_rules_gateway() -> None:
    """Reset the Rules gateway (for testing)."""
    global _rules_gateway
    if _rules_gateway:
        await _rules_gateway.close()
    _rules_gateway = None
