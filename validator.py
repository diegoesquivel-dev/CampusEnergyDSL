from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from astNodes import (
    Action,
    Comparison,
    Condition,
    Conjunction,
    Disjunction,
    Negation,
    Rule,
)

SPACE_CODES = {"AULA302", "PASILLOB1", "LABFISICA", "LABQUIMICA", "DATACENTER01"}
EQUIPMENT_BY_SPACE = {
    "AULA302": {"AIRE02"},
    "PASILLOB1": {"LUM01"},
    "LABFISICA": {"EXTRACTOR01"},
    "LABQUIMICA": {"AIRE01"},
    "DATACENTER01": {"SERVIDOR01"},
}
ENUM_VALUES = {
    "codEspacio": SPACE_CODES,
    "ocupacion": {"VACIO", "OCUPADO"},
    "actividadActual": {"NINGUNA", "CLASE", "EXPERIMENTO"},
    "criticidad": {"BAJA", "MEDIA", "ALTA", "EXTREMA"},
    "frescura": {"ACTUALIZADO", "OBSOLETO", "DESCONECTADO"},
    "bloqueTarifa": {"VALLE", "MEDIA", "PUNTA"},
    "eventoProveedor": {"NORMAL", "REDUCCION"},
}
NUMERIC_ATTRIBUTES = {"tiempoVacio", "demandaNeta"}
ALL_ATTRIBUTES = set(ENUM_VALUES) | NUMERIC_ATTRIBUTES
COMMANDS = {"apagar", "modoAhorro", "recomendarApagado", "emitirAlerta"}
PHYSICAL_COMMANDS = {"apagar", "modoAhorro", "recomendarApagado"}
EQUALITY_ONLY = {"ocupacion", "actividadActual", "criticidad", "frescura", "bloqueTarifa", "eventoProveedor", "codEspacio"}
NUMERIC_OPERATORS = {"=", "!=", ">", "<", ">=", "<="}
EQUALITY_OPERATORS = {"=", "!="}


@dataclass(frozen=True)
class ValidationIssue:
    rule_name: str
    message: str

    def __str__(self) -> str:
        prefix = f"Regla '{self.rule_name}': " if self.rule_name else ""
        return prefix + self.message


class DSLValidationError(ValueError):
    def __init__(self, issues: Iterable[ValidationIssue]):
        self.issues = tuple(issues)
        super().__init__("\n".join(str(issue) for issue in self.issues))


def _comparisons(condition: Condition) -> list[Comparison]:
    if isinstance(condition, Comparison):
        return [condition]
    if isinstance(condition, Negation):
        return _comparisons(condition.operand)
    if isinstance(condition, (Conjunction, Disjunction)):
        return [item for child in condition.operands for item in _comparisons(child)]
    raise TypeError(f"Tipo de condición no reconocido: {type(condition).__name__}")


def _validate_comparison(rule: Rule, comparison: Comparison, issues: list[ValidationIssue]) -> None:
    attribute, operator, value = comparison.attribute, comparison.operator, comparison.value
    if attribute not in ALL_ATTRIBUTES:
        issues.append(ValidationIssue(rule.name, f"atributo desconocido '{attribute}'."))
        return

    if attribute in NUMERIC_ATTRIBUTES:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            issues.append(ValidationIssue(rule.name, f"'{attribute}' requiere un literal numérico."))
        elif value < 0:
            issues.append(ValidationIssue(rule.name, f"'{attribute}' no admite valores negativos."))
        if operator not in NUMERIC_OPERATORS:
            issues.append(ValidationIssue(rule.name, f"operador '{operator}' no válido para '{attribute}'."))
        if attribute == "tiempoVacio" and isinstance(value, float):
            issues.append(ValidationIssue(rule.name, "'tiempoVacio' requiere un literal entero."))
        return

    if not isinstance(value, str):
        issues.append(ValidationIssue(rule.name, f"'{attribute}' requiere un literal de texto."))
        return
    if operator not in EQUALITY_OPERATORS:
        issues.append(ValidationIssue(rule.name, f"operador '{operator}' no válido para '{attribute}'."))
    if value not in ENUM_VALUES[attribute]:
        choices = ", ".join(sorted(ENUM_VALUES[attribute]))
        issues.append(ValidationIssue(rule.name, f"valor '{value}' no permitido para '{attribute}' ({choices})."))


def validate_rules(rules: list[Rule]) -> None:
    issues: list[ValidationIssue] = []
    seen_names: set[str] = set()

    for rule in rules:
        if rule.name in seen_names:
            issues.append(ValidationIssue(rule.name, "el identificador está duplicado."))
        seen_names.add(rule.name)

        action: Action = rule.action
        if action.command not in COMMANDS:
            issues.append(ValidationIssue(rule.name, f"comando desconocido '{action.command}'."))
        if action.space_code not in SPACE_CODES:
            issues.append(ValidationIssue(rule.name, f"espacio desconocido '{action.space_code}'."))
        elif action.equipment_code not in EQUIPMENT_BY_SPACE[action.space_code]:
            issues.append(
                ValidationIssue(
                    rule.name,
                    f"el equipo '{action.target}' no pertenece al catálogo del espacio.",
                )
            )

        comparisons = _comparisons(rule.condition)
        for comparison in comparisons:
            _validate_comparison(rule, comparison, issues)

        declared_spaces = {
            comparison.value
            for comparison in comparisons
            if comparison.attribute == "codEspacio"
            and comparison.operator == "="
            and isinstance(comparison.value, str)
        }
        if declared_spaces != {action.space_code}:
            issues.append(
                ValidationIssue(
                    rule.name,
                    f"la condición debe limitarse al espacio '{action.space_code}'.",
                )
            )

        if action.command in PHYSICAL_COMMANDS:
            if any(
                comparison.attribute == "criticidad"
                and comparison.operator == "="
                and comparison.value == "EXTREMA"
                for comparison in comparisons
            ):
                issues.append(
                    ValidationIssue(rule.name, "no se permite una acción de ahorro con criticidad EXTREMA.")
                )
            if any(
                comparison.attribute == "frescura"
                and comparison.operator == "="
                and comparison.value in {"OBSOLETO", "DESCONECTADO"}
                for comparison in comparisons
            ):
                issues.append(
                    ValidationIssue(
                        rule.name,
                        "no se permite una acción física asociada a telemetría obsoleta o desconectada.",
                    )
                )

    if issues:
        raise DSLValidationError(issues)


def validate_context(context: dict[str, object]) -> None:
    missing = ALL_ATTRIBUTES - context.keys()
    if missing:
        raise ValueError(f"Faltan atributos de contexto: {', '.join(sorted(missing))}.")

    for attribute, allowed in ENUM_VALUES.items():
        value = context[attribute]
        if not isinstance(value, str) or value not in allowed:
            raise ValueError(
                f"Contexto inválido: '{attribute}' debe ser uno de {', '.join(sorted(allowed))}."
            )

    for attribute in NUMERIC_ATTRIBUTES:
        value = context[attribute]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise ValueError(f"Contexto inválido: '{attribute}' debe ser un número mayor o igual a cero.")
    if not isinstance(context["tiempoVacio"], int):
        raise ValueError("Contexto inválido: 'tiempoVacio' debe ser un entero.")
    restriction = context.get("restriccionEquipo", "LIBRE")
    if not isinstance(restriction, str) or restriction not in {
        "LIBRE",
        "AUTORIZABLE",
        "DURA",
    }:
        raise ValueError(
            "Contexto inválido: 'restriccionEquipo' debe ser LIBRE, AUTORIZABLE o DURA."
        )
