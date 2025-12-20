"""
Benefit Rules Engine.

Integrates with GoRules ZEN engine for configurable benefit rules.
Provides JSON-based rule definitions for:
- Benefit calculations
- Deduction rules
- Validation rules
- Coverage determination

Source: Design Document Section 3.3 - Benefit Calculation Engine
Verified: 2025-12-18
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RuleOutcome(str, Enum):
    """Possible outcomes from rule evaluation."""

    APPROVE = "approve"
    DENY = "deny"
    REVIEW = "review"
    ADJUST = "adjust"
    CONTINUE = "continue"


@dataclass
class RuleCondition:
    """A single condition in a rule."""

    field: str
    operator: str  # eq, ne, gt, gte, lt, lte, in, not_in, contains, regex
    value: Any
    case_sensitive: bool = True


@dataclass
class RuleAction:
    """Action to take when rule matches."""

    type: str  # set, adjust, deny, approve, flag, add_code
    target: Optional[str] = None
    value: Any = None
    reason: Optional[str] = None


@dataclass
class BenefitRule:
    """A complete benefit rule definition."""

    id: str
    name: str
    description: str
    priority: int = 100  # Lower = higher priority
    enabled: bool = True

    # Conditions - ALL must match for rule to fire
    conditions: list[RuleCondition] = field(default_factory=list)

    # Actions to take when rule fires
    actions: list[RuleAction] = field(default_factory=list)

    # Outcome if rule fires
    outcome: RuleOutcome = RuleOutcome.CONTINUE

    # Metadata
    category: str = "general"
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None


@dataclass
class RuleContext:
    """Context for rule evaluation."""

    # Claim info
    claim_id: str
    tenant_id: str
    claim_type: str

    # Line item info
    procedure_code: str
    procedure_modifiers: list[str] = field(default_factory=list)
    diagnosis_codes: list[str] = field(default_factory=list)

    # Amounts
    charged_amount: Decimal = Decimal("0")
    allowed_amount: Decimal = Decimal("0")
    quantity: int = 1

    # Policy info
    policy_id: str = ""
    benefit_class: str = "silver"
    network_type: str = "ppo"
    is_in_network: bool = True

    # Accumulator status
    deductible_remaining: Decimal = Decimal("0")
    oop_remaining: Decimal = Decimal("0")
    benefit_remaining: Decimal = Decimal("0")

    # Service info
    service_date: Optional[date] = None
    place_of_service: str = "11"
    provider_specialty: str = ""

    # Additional context
    custom: dict = field(default_factory=dict)


@dataclass
class RuleResult:
    """Result from rule evaluation."""

    rule_id: str
    rule_name: str
    matched: bool = False
    outcome: RuleOutcome = RuleOutcome.CONTINUE

    # Modified values
    adjustments: dict = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)
    codes: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    # For denials
    denial_reason: Optional[str] = None


class BenefitRulesEngine:
    """
    Rules engine for benefit calculations.

    Evaluates configurable rules against claim/line item data
    to determine benefit decisions and adjustments.

    In production, this would integrate with GoRules ZEN engine.
    For demo mode, provides native Python rule evaluation.
    """

    def __init__(self):
        """Initialize rules engine."""
        self._rules: dict[str, BenefitRule] = {}
        self._rules_by_category: dict[str, list[BenefitRule]] = {}
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default benefit rules."""
        default_rules = [
            # =================================================================
            # Procedure-based rules
            # =================================================================
            BenefitRule(
                id="cosmetic_exclusion",
                name="Cosmetic Procedure Exclusion",
                description="Deny cosmetic procedures not medically necessary",
                priority=10,
                category="exclusion",
                conditions=[
                    RuleCondition(
                        field="procedure_code",
                        operator="in",
                        value=["15780", "15781", "15782", "15783", "15786", "15787"],  # Cosmetic codes
                    ),
                ],
                actions=[
                    RuleAction(type="deny", reason="Cosmetic procedure not covered"),
                    RuleAction(type="add_code", value="CO-96"),
                ],
                outcome=RuleOutcome.DENY,
            ),
            BenefitRule(
                id="experimental_exclusion",
                name="Experimental Treatment Exclusion",
                description="Deny experimental/investigational procedures",
                priority=10,
                category="exclusion",
                conditions=[
                    RuleCondition(
                        field="procedure_code",
                        operator="in",
                        value=["0075T", "0076T", "0077T"],  # Example experimental codes
                    ),
                ],
                actions=[
                    RuleAction(type="deny", reason="Experimental procedure not covered"),
                    RuleAction(type="add_code", value="CO-188"),
                ],
                outcome=RuleOutcome.DENY,
            ),

            # =================================================================
            # Network rules
            # =================================================================
            BenefitRule(
                id="out_of_network_reduction",
                name="Out-of-Network Reduction",
                description="Apply reduced coverage for out-of-network providers",
                priority=50,
                category="network",
                conditions=[
                    RuleCondition(field="is_in_network", operator="eq", value=False),
                ],
                actions=[
                    RuleAction(
                        type="adjust",
                        target="coverage_rate",
                        value=0.60,  # 60% coverage OON
                    ),
                    RuleAction(type="flag", value="out_of_network"),
                    RuleAction(type="add_code", value="N620"),
                ],
                outcome=RuleOutcome.CONTINUE,
            ),

            # =================================================================
            # Prior authorization rules
            # =================================================================
            BenefitRule(
                id="prior_auth_required_surgery",
                name="Prior Auth Required - Surgery",
                description="Flag surgical procedures requiring prior authorization",
                priority=30,
                category="prior_auth",
                conditions=[
                    RuleCondition(
                        field="procedure_code",
                        operator="regex",
                        value=r"^(2\d{4}|3\d{4}|4\d{4}|5\d{4}|6\d{4})$",  # Surgery range
                    ),
                    RuleCondition(field="charged_amount", operator="gt", value=1000),
                ],
                actions=[
                    RuleAction(type="flag", value="prior_auth_required"),
                    RuleAction(
                        type="set",
                        target="requires_prior_auth",
                        value=True,
                    ),
                ],
                outcome=RuleOutcome.CONTINUE,
            ),
            BenefitRule(
                id="prior_auth_required_imaging",
                name="Prior Auth Required - Advanced Imaging",
                description="Flag MRI/CT requiring prior authorization",
                priority=30,
                category="prior_auth",
                conditions=[
                    RuleCondition(
                        field="procedure_code",
                        operator="regex",
                        value=r"^7(0|1|2|3|4|5)\d{3}$",  # Radiology codes
                    ),
                ],
                actions=[
                    RuleAction(type="flag", value="prior_auth_required"),
                ],
                outcome=RuleOutcome.CONTINUE,
            ),

            # =================================================================
            # Quantity/frequency limits
            # =================================================================
            BenefitRule(
                id="high_quantity_review",
                name="High Quantity Review",
                description="Flag for review when quantity exceeds threshold",
                priority=60,
                category="fwa",
                conditions=[
                    RuleCondition(field="quantity", operator="gt", value=10),
                ],
                actions=[
                    RuleAction(type="flag", value="high_quantity"),
                    RuleAction(
                        type="set",
                        target="requires_review",
                        value=True,
                        reason="Quantity exceeds threshold",
                    ),
                ],
                outcome=RuleOutcome.REVIEW,
            ),

            # =================================================================
            # Amount-based rules
            # =================================================================
            BenefitRule(
                id="high_dollar_review",
                name="High Dollar Claim Review",
                description="Flag high-dollar line items for review",
                priority=70,
                category="fwa",
                conditions=[
                    RuleCondition(field="charged_amount", operator="gt", value=5000),
                ],
                actions=[
                    RuleAction(type="flag", value="high_dollar"),
                ],
                outcome=RuleOutcome.CONTINUE,
            ),
            BenefitRule(
                id="significant_variance",
                name="Significant Charge/Allowed Variance",
                description="Flag when charged significantly exceeds allowed",
                priority=70,
                category="audit",
                conditions=[
                    RuleCondition(field="custom.charge_ratio", operator="gt", value=3.0),
                ],
                actions=[
                    RuleAction(type="flag", value="charge_variance"),
                ],
                outcome=RuleOutcome.CONTINUE,
            ),

            # =================================================================
            # Benefit class rules
            # =================================================================
            BenefitRule(
                id="bronze_deductible_first",
                name="Bronze Plan - Apply Full Deductible",
                description="Bronze plans have higher deductible requirement",
                priority=40,
                category="benefit_class",
                conditions=[
                    RuleCondition(field="benefit_class", operator="eq", value="bronze"),
                    RuleCondition(field="deductible_remaining", operator="gt", value=0),
                ],
                actions=[
                    RuleAction(
                        type="set",
                        target="deductible_priority",
                        value="high",
                    ),
                ],
                outcome=RuleOutcome.CONTINUE,
            ),
            BenefitRule(
                id="platinum_no_deductible",
                name="Platinum Plan - No Deductible",
                description="Platinum plans skip deductible",
                priority=40,
                category="benefit_class",
                conditions=[
                    RuleCondition(field="benefit_class", operator="eq", value="platinum"),
                ],
                actions=[
                    RuleAction(type="set", target="skip_deductible", value=True),
                ],
                outcome=RuleOutcome.CONTINUE,
            ),

            # =================================================================
            # Place of service rules
            # =================================================================
            BenefitRule(
                id="er_copay",
                name="Emergency Room Copay",
                description="Apply ER copay for emergency visits",
                priority=45,
                category="copay",
                conditions=[
                    RuleCondition(field="place_of_service", operator="eq", value="23"),
                ],
                actions=[
                    RuleAction(
                        type="set",
                        target="copay_override",
                        value=250.00,
                    ),
                ],
                outcome=RuleOutcome.CONTINUE,
            ),
            BenefitRule(
                id="telehealth_discount",
                name="Telehealth Reduced Copay",
                description="Reduced copay for telehealth visits",
                priority=45,
                category="copay",
                conditions=[
                    RuleCondition(field="place_of_service", operator="eq", value="02"),
                ],
                actions=[
                    RuleAction(
                        type="adjust",
                        target="copay_multiplier",
                        value=0.50,  # 50% copay
                    ),
                ],
                outcome=RuleOutcome.CONTINUE,
            ),

            # =================================================================
            # Preventive care rules
            # =================================================================
            BenefitRule(
                id="preventive_100_coverage",
                name="Preventive Care - 100% Coverage",
                description="Preventive services covered at 100%",
                priority=20,
                category="preventive",
                conditions=[
                    RuleCondition(
                        field="procedure_code",
                        operator="in",
                        value=[
                            "99381", "99382", "99383", "99384", "99385",  # Preventive new
                            "99386", "99387", "99391", "99392", "99393",  # Preventive established
                            "99394", "99395", "99396", "99397",
                            "90460", "90461", "90471", "90472",  # Immunizations
                            "G0438", "G0439",  # Wellness visits
                        ],
                    ),
                ],
                actions=[
                    RuleAction(type="set", target="skip_deductible", value=True),
                    RuleAction(type="set", target="skip_coinsurance", value=True),
                    RuleAction(type="set", target="skip_copay", value=True),
                    RuleAction(type="flag", value="preventive_care"),
                ],
                outcome=RuleOutcome.APPROVE,
            ),
        ]

        for rule in default_rules:
            self.add_rule(rule)

    def add_rule(self, rule: BenefitRule) -> None:
        """Add a rule to the engine."""
        self._rules[rule.id] = rule

        if rule.category not in self._rules_by_category:
            self._rules_by_category[rule.category] = []
        self._rules_by_category[rule.category].append(rule)

        # Sort by priority
        self._rules_by_category[rule.category].sort(key=lambda r: r.priority)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the engine."""
        if rule_id not in self._rules:
            return False

        rule = self._rules.pop(rule_id)
        if rule.category in self._rules_by_category:
            self._rules_by_category[rule.category] = [
                r for r in self._rules_by_category[rule.category]
                if r.id != rule_id
            ]
        return True

    def evaluate(
        self,
        context: RuleContext,
        categories: Optional[list[str]] = None,
        stop_on_deny: bool = True,
    ) -> list[RuleResult]:
        """
        Evaluate all applicable rules against the context.

        Args:
            context: Rule evaluation context
            categories: Optional list of rule categories to evaluate
            stop_on_deny: Stop evaluation on first deny

        Returns:
            List of rule results
        """
        results: list[RuleResult] = []

        # Get rules to evaluate
        if categories:
            rules_to_eval = []
            for cat in categories:
                rules_to_eval.extend(self._rules_by_category.get(cat, []))
        else:
            rules_to_eval = list(self._rules.values())

        # Sort by priority
        rules_to_eval.sort(key=lambda r: r.priority)

        # Evaluate each rule
        for rule in rules_to_eval:
            if not rule.enabled:
                continue

            # Check effective dates
            if rule.effective_date and context.service_date:
                if context.service_date < rule.effective_date:
                    continue
            if rule.expiry_date and context.service_date:
                if context.service_date > rule.expiry_date:
                    continue

            result = self._evaluate_rule(rule, context)
            results.append(result)

            # Stop on deny if requested
            if stop_on_deny and result.outcome == RuleOutcome.DENY:
                break

        return results

    def _evaluate_rule(
        self,
        rule: BenefitRule,
        context: RuleContext,
    ) -> RuleResult:
        """Evaluate a single rule against context."""
        result = RuleResult(
            rule_id=rule.id,
            rule_name=rule.name,
        )

        # Check all conditions
        all_conditions_met = True
        for condition in rule.conditions:
            if not self._evaluate_condition(condition, context):
                all_conditions_met = False
                break

        if not all_conditions_met:
            return result

        # Rule matched - apply actions
        result.matched = True
        result.outcome = rule.outcome

        for action in rule.actions:
            self._apply_action(action, result)

        return result

    def _evaluate_condition(
        self,
        condition: RuleCondition,
        context: RuleContext,
    ) -> bool:
        """Evaluate a single condition."""
        # Get field value from context
        value = self._get_field_value(condition.field, context)

        if value is None:
            return False

        # Evaluate operator
        op = condition.operator
        target = condition.value

        if op == "eq":
            return value == target
        elif op == "ne":
            return value != target
        elif op == "gt":
            return float(value) > float(target)
        elif op == "gte":
            return float(value) >= float(target)
        elif op == "lt":
            return float(value) < float(target)
        elif op == "lte":
            return float(value) <= float(target)
        elif op == "in":
            return value in target
        elif op == "not_in":
            return value not in target
        elif op == "contains":
            return target in str(value)
        elif op == "regex":
            import re
            pattern = re.compile(target)
            return bool(pattern.match(str(value)))

        return False

    def _get_field_value(self, field: str, context: RuleContext) -> Any:
        """Get field value from context, supporting nested fields."""
        if "." in field:
            parts = field.split(".")
            obj = context

            for part in parts:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif isinstance(obj, dict) and part in obj:
                    obj = obj[part]
                else:
                    return None

            return obj

        return getattr(context, field, None)

    def _apply_action(self, action: RuleAction, result: RuleResult) -> None:
        """Apply an action to the result."""
        if action.type == "deny":
            result.denial_reason = action.reason or "Rule denied"

        elif action.type == "set":
            result.adjustments[action.target] = action.value

        elif action.type == "adjust":
            result.adjustments[action.target] = action.value

        elif action.type == "flag":
            result.flags.append(action.value)

        elif action.type == "add_code":
            result.codes.append(action.value)

    def get_rules_by_category(self, category: str) -> list[BenefitRule]:
        """Get all rules in a category."""
        return self._rules_by_category.get(category, [])

    def get_all_rules(self) -> list[BenefitRule]:
        """Get all rules."""
        return list(self._rules.values())

    def export_rules(self) -> str:
        """Export rules as JSON for ZEN engine format."""
        rules_data = []

        for rule in self._rules.values():
            rule_dict = {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "priority": rule.priority,
                "enabled": rule.enabled,
                "category": rule.category,
                "conditions": [
                    {
                        "field": c.field,
                        "operator": c.operator,
                        "value": c.value,
                    }
                    for c in rule.conditions
                ],
                "actions": [
                    {
                        "type": a.type,
                        "target": a.target,
                        "value": a.value,
                        "reason": a.reason,
                    }
                    for a in rule.actions
                ],
                "outcome": rule.outcome.value,
            }

            if rule.effective_date:
                rule_dict["effective_date"] = rule.effective_date.isoformat()
            if rule.expiry_date:
                rule_dict["expiry_date"] = rule.expiry_date.isoformat()

            rules_data.append(rule_dict)

        return json.dumps(rules_data, indent=2)

    def import_rules(self, json_data: str) -> int:
        """
        Import rules from JSON.

        Returns number of rules imported.
        """
        rules_data = json.loads(json_data)
        count = 0

        for rule_dict in rules_data:
            conditions = [
                RuleCondition(
                    field=c["field"],
                    operator=c["operator"],
                    value=c["value"],
                )
                for c in rule_dict.get("conditions", [])
            ]

            actions = [
                RuleAction(
                    type=a["type"],
                    target=a.get("target"),
                    value=a.get("value"),
                    reason=a.get("reason"),
                )
                for a in rule_dict.get("actions", [])
            ]

            rule = BenefitRule(
                id=rule_dict["id"],
                name=rule_dict["name"],
                description=rule_dict.get("description", ""),
                priority=rule_dict.get("priority", 100),
                enabled=rule_dict.get("enabled", True),
                category=rule_dict.get("category", "general"),
                conditions=conditions,
                actions=actions,
                outcome=RuleOutcome(rule_dict.get("outcome", "continue")),
            )

            self.add_rule(rule)
            count += 1

        return count


# =============================================================================
# Singleton Instance
# =============================================================================


_benefit_rules_engine: Optional[BenefitRulesEngine] = None


def get_benefit_rules_engine() -> BenefitRulesEngine:
    """Get singleton benefit rules engine instance."""
    global _benefit_rules_engine
    if _benefit_rules_engine is None:
        _benefit_rules_engine = BenefitRulesEngine()
    return _benefit_rules_engine
