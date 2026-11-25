from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

Literal: TypeAlias = str | int | float


@dataclass(frozen=True)
class Comparison:
    attribute: str
    operator: str
    value: Literal


@dataclass(frozen=True)
class Negation:
    operand: Condition


@dataclass(frozen=True)
class Conjunction:
    operands: tuple[Condition, ...]


@dataclass(frozen=True)
class Disjunction:
    operands: tuple[Condition, ...]


Condition: TypeAlias = Comparison | Negation | Conjunction | Disjunction


@dataclass(frozen=True)
class Action:
    command: str
    space_code: str
    equipment_code: str

    @property
    def target(self) -> str:
        return f"{self.space_code}.{self.equipment_code}"


@dataclass(frozen=True)
class Rule:
    name: str
    condition: Condition
    action: Action
