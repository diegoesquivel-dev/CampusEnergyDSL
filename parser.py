from __future__ import annotations

from pathlib import Path

from lark import Lark, Transformer, UnexpectedInput, v_args

from astNodes import (
    Action,
    Comparison,
    Condition,
    Conjunction,
    Disjunction,
    Literal,
    Negation,
    Rule,
)

_GRAMMAR_PATH = Path(__file__).with_name("grammar.lark")


class DSLParseError(ValueError):
    """A syntax error with a source location suitable for the editor."""


class _ASTBuilder(Transformer):
    def string(self, items: list[object]) -> str:
        return str(items[0])[1:-1]

    def number(self, items: list[object]) -> int | float:
        raw = str(items[0])
        return float(raw) if "." in raw else int(raw)

    def comparison(self, items: list[object]) -> Comparison:
        attribute, operator, value = items
        return Comparison(str(attribute), str(operator), value)  # type: ignore[arg-type]

    def negation(self, items: list[object]) -> Negation:
        return Negation(items[0])  # type: ignore[arg-type]

    def conjunction(self, items: list[object]) -> Condition:
        operands = tuple(items)
        return operands[0] if len(operands) == 1 else Conjunction(operands)  # type: ignore[return-value]

    def disjunction(self, items: list[object]) -> Condition:
        operands = tuple(items)
        return operands[0] if len(operands) == 1 else Disjunction(operands)  # type: ignore[return-value]

    def action(self, items: list[object]) -> Action:
        command, space_code, equipment_code = items
        return Action(str(command), str(space_code), str(equipment_code))

    def rule(self, items: list[object]) -> Rule:
        name, condition, action = items
        return Rule(str(name), condition, action)  # type: ignore[arg-type]

    def start(self, items: list[object]) -> list[Rule]:
        return list(items)  # type: ignore[return-value]


def parse_program(source: str) -> list[Rule]:
    try:
        grammar = _GRAMMAR_PATH.read_text(encoding="utf-8")
        parser = Lark(grammar, parser="lalr", start="start")
        tree = parser.parse(source)
        return _ASTBuilder().transform(tree)
    except UnexpectedInput as exc:
        context = exc.get_context(source, span=40).strip()
        raise DSLParseError(
            f"Error sintáctico en línea {exc.line}, columna {exc.column}:\n{context}"
        ) from exc


def parse_file(path: str | Path) -> list[Rule]:
    file_path = Path(path)
    try:
        source = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OSError(f"No se pudo leer el archivo DSL '{file_path}': {exc}") from exc
    return parse_program(source)
