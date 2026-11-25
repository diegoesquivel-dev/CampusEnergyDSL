from __future__ import annotations

import json
from pathlib import Path

import pytest

from astNodes import Comparison
from generator import generate_json, write_json
from interpreter import evaluate_named_rule
from main import execute_scenario, load_scenarios, load_rule_source
from parser import DSLParseError, parse_program
from rule_editor import build_rule, editable_groups, rule_slug, serialize_program
from validator import DSLValidationError, validate_rules


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def source() -> str:
    return load_rule_source()


@pytest.fixture(scope="module")
def rules(source: str):
    parsed = parse_program(source)
    validate_rules(parsed)
    return parsed


def test_catalog_parses_and_validates_all_ten_rules(rules) -> None:
    assert len(rules) == 10
    assert {rule.name for rule in rules} == {
        "ahorroBasico",
        "ahorroPasillo",
        "revisionLaboratorio",
        "alertaTelemetria",
        "ahorroHoraPunta",
        "atenuaSolarBaja",
        "excedenteSolarConfort",
        "respuestaEventoProveedor",
        "reduccionLaboratorioEvento",
        "alertaCriticaProveedor",
    }


def test_solar_and_supplier_rules_match_their_demo_contexts(source: str) -> None:
    scenarios = load_scenarios()
    for name in (
        "ahorroHoraPunta",
        "atenuaSolarBaja",
        "excedenteSolarConfort",
        "respuestaEventoProveedor",
    ):
        scenario, plan = execute_scenario(source, name, scenarios)
        assert scenario["regla"] == name
        assert plan is not None
        assert plan.resolution == "PERMITIDA"


def test_lab_decision_requires_human_approval(rules, source: str) -> None:
    scenario, plan = execute_scenario(source, "revisionLaboratorio", load_scenarios())
    assert plan is not None
    assert plan.resolution == "REQUIERE AUTORIZACION"
    assert plan.requires_authorization is True
    assert plan.proposed_action == "recomendarApagado"


def test_stale_telemetry_alert_does_not_trigger_a_cut(source: str) -> None:
    _, plan = execute_scenario(source, "alertaTelemetria", load_scenarios())
    assert plan is not None
    assert plan.resolution == "PERMITIDA"
    assert plan.proposed_action == "emitirAlerta"


def test_runtime_blocks_physical_action_in_extreme_criticality() -> None:
    rule = parse_program(
        'REGLA corte: CUANDO codEspacio = "AULA302" '
        "ENTONCES apagar(AULA302.AIRE02);"
    )
    validate_rules(rule)
    context = dict(load_scenarios()["ahorroBasico"]["contexto"])
    context["criticidad"] = "EXTREMA"
    plan = evaluate_named_rule(rule, "corte", context)
    assert plan is not None
    assert plan.resolution == "BLOQUEADA"


def test_runtime_blocks_physical_action_when_telemetry_is_stale() -> None:
    rule = parse_program(
        'REGLA corte: CUANDO codEspacio = "AULA302" '
        "ENTONCES apagar(AULA302.AIRE02);"
    )
    validate_rules(rule)
    context = dict(load_scenarios()["ahorroBasico"]["contexto"])
    context["frescura"] = "OBSOLETO"
    plan = evaluate_named_rule(rule, "corte", context)
    assert plan is not None
    assert plan.resolution == "BLOQUEADA"


def test_nonmatching_scenario_returns_no_plan(source: str) -> None:
    scenarios = load_scenarios()
    context = dict(scenarios["ahorroBasico"]["contexto"])
    context["tiempoVacio"] = 4
    scenarios["corto"] = {"regla": "ahorroBasico", "contexto": context}
    _, plan = execute_scenario(source, "corto", scenarios)
    assert plan is None


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            'REGLA mala: CUANDO codEspacio = "AULA302" Y campoInventado = 1 '
            'ENTONCES emitirAlerta(AULA302.AIRE02);',
            "atributo desconocido",
        ),
        (
            'REGLA mala: CUANDO codEspacio = "AULA302" Y criticidad = "EXTREMA" '
            'ENTONCES apagar(AULA302.AIRE02);',
            "criticidad EXTREMA",
        ),
        (
            'REGLA mala: CUANDO codEspacio = "AULA302" Y frescura = "OBSOLETO" '
            'ENTONCES apagar(AULA302.AIRE02);',
            "telemetría obsoleta",
        ),
        (
            'REGLA mala: CUANDO codEspacio = "PASILLOB1" '
            'ENTONCES apagar(PASILLOB1.AIRE02);',
            "no pertenece",
        ),
    ],
)
def test_static_validation_rejects_unsafe_or_invalid_rules(body: str, expected: str) -> None:
    with pytest.raises(DSLValidationError, match=expected):
        validate_rules(parse_program(body))


def test_parser_reports_invalid_syntax() -> None:
    with pytest.raises(DSLParseError, match="línea 1"):
        parse_program('REGLA rota: CUANDO codEspacio = "AULA302" ENTONCES apagar;')


def test_decision_json_has_documented_shape(rules, tmp_path: Path) -> None:
    context = dict(load_scenarios()["ahorroBasico"]["contexto"])
    plan = evaluate_named_rule(rules, "ahorroBasico", context)
    assert plan is not None
    artifact = json.loads(generate_json(context, plan))
    assert set(artifact) == {"contextoEntrada", "planDecision"}
    assert artifact["planDecision"]["reglaAplicada"] == "ahorroBasico"
    assert artifact["planDecision"]["estadoResolucion"] == "PERMITIDA"
    destination = write_json(context, plan, tmp_path / "decision.json")
    assert json.loads(destination.read_text(encoding="utf-8")) == artifact


def test_visual_block_roundtrip_preserves_default_rule_behavior(source: str) -> None:
    original_rules = parse_program(source)
    scenarios = load_scenarios()
    for original in original_rules:
        rebuilt = build_rule(
            original.name,
            original.action.space_code,
            editable_groups(original),
            original.action.command,
            original.action.equipment_code,
        )
        restored = parse_program(serialize_program([rebuilt]))
        validate_rules(restored)
        for scenario in scenarios.values():
            context = scenario["contexto"]
            if context["codEspacio"] != original.action.space_code:
                continue
            before = evaluate_named_rule([original], original.name, context)
            after = evaluate_named_rule(restored, original.name, context)
            assert (before is None) == (after is None)
            if before is not None and after is not None:
                assert before.resolution == after.resolution
                assert before.proposed_action == after.proposed_action


def test_visual_editor_can_create_a_new_persistable_rule() -> None:
    name = rule_slug("Ahorro suave para aula")
    rule = build_rule(
        name,
        "AULA302",
        [
            [
                Comparison("ocupacion", "=", "VACIO"),
                Comparison("tiempoVacio", ">=", 20),
            ]
        ],
        "modoAhorro",
        "AIRE02",
    )
    serialized = parse_program(serialize_program([rule]))
    validate_rules(serialized)
    assert serialized[0].name == "ahorro_suave_para_aula"
    assert serialized[0].action.command == "modoAhorro"
