from __future__ import annotations

from astNodes import Comparison, Condition, Conjunction, Disjunction, Negation, Rule
from decision import DecisionPlan, resolve_decision
from validator import validate_context


def evaluate_condition(condition: Condition, context: dict[str, object]) -> bool:
    if isinstance(condition, Comparison):
        actual = context[condition.attribute]
        expected = condition.value
        return {
            "=": lambda: actual == expected,
            "!=": lambda: actual != expected,
            ">": lambda: actual > expected,  # type: ignore[operator]
            "<": lambda: actual < expected,  # type: ignore[operator]
            ">=": lambda: actual >= expected,  # type: ignore[operator]
            "<=": lambda: actual <= expected,  # type: ignore[operator]
        }[condition.operator]()
    if isinstance(condition, Negation):
        return not evaluate_condition(condition.operand, context)
    if isinstance(condition, Conjunction):
        return all(evaluate_condition(item, context) for item in condition.operands)
    if isinstance(condition, Disjunction):
        return any(evaluate_condition(item, context) for item in condition.operands)
    raise TypeError(f"Tipo de condición no reconocido: {type(condition).__name__}")


def evaluate_rule(rule: Rule, context: dict[str, object]) -> DecisionPlan | None:
    validate_context(context)
    if not evaluate_condition(rule.condition, context):
        return None
    return resolve_decision(rule, context)


def evaluate_named_rule(
    rules: list[Rule], rule_name: str, context: dict[str, object]
) -> DecisionPlan | None:
    matches = [rule for rule in rules if rule.name == rule_name]
    if not matches:
        raise ValueError(f"No existe la regla '{rule_name}' en el catálogo DSL.")
    return evaluate_rule(matches[0], context)
