from __future__ import annotations

from dataclasses import dataclass

from astNodes import Rule


@dataclass(frozen=True)
class DecisionPlan:
    rule_name: str
    resolution: str
    proposed_action: str
    target_equipment: str
    requires_authorization: bool
    evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "reglaAplicada": self.rule_name,
            "estadoResolucion": self.resolution,
            "accionPropuesta": self.proposed_action,
            "equipoObjetivo": self.target_equipment,
            "requiereAutorizacion": self.requires_authorization,
            "evidencia": list(self.evidence),
        }


def resolve_decision(rule: Rule, context: dict[str, object]) -> DecisionPlan:
    action = rule.action.command
    target = rule.action.target
    evidence = [
        f"{key} = {context[key]}"
        for key in (
            "codEspacio",
            "ocupacion",
            "tiempoVacio",
            "actividadActual",
            "criticidad",
            "frescura",
            "bloqueTarifa",
            "demandaNeta",
            "eventoProveedor",
        )
    ]

    if action not in {"apagar", "modoAhorro", "recomendarApagado"}:
        evidence.append("La acción es informativa; no solicita cambios físicos.")
        return DecisionPlan(rule.name, "PERMITIDA", action, target, False, tuple(evidence))

    restriction = str(context.get("restriccionEquipo", "LIBRE"))
    freshness = context["frescura"]
    if context["criticidad"] == "EXTREMA" or restriction == "DURA":
        evidence.append("Bloqueo de seguridad: criticidad EXTREMA o restricción DURA.")
        return DecisionPlan(rule.name, "BLOQUEADA", action, target, False, tuple(evidence))

    if freshness in {"OBSOLETO", "DESCONECTADO"}:
        evidence.append(
            "Bloqueo defensivo: telemetría no actualizada; se asume el recinto ocupado."
        )
        return DecisionPlan(rule.name, "BLOQUEADA", action, target, False, tuple(evidence))

    if context["actividadActual"] == "CLASE":
        evidence.append("Bloqueo de continuidad: hay una clase activa en el recinto.")
        return DecisionPlan(rule.name, "BLOQUEADA", action, target, False, tuple(evidence))

    needs_authorization = (
        action == "recomendarApagado"
        or restriction == "AUTORIZABLE"
        or context["actividadActual"] == "EXPERIMENTO"
    )
    if needs_authorization:
        evidence.append("Requiere confirmación humana; vigencia de la solicitud: 15 minutos.")
        return DecisionPlan(
            rule.name,
            "REQUIERE AUTORIZACION",
            "recomendarApagado",
            target,
            True,
            tuple(evidence),
        )

    evidence.append("Reglas de seguridad satisfechas; decisión en modo simulación.")
    return DecisionPlan(rule.name, "PERMITIDA", action, target, False, tuple(evidence))
