from __future__ import annotations

import json
from pathlib import Path

from decision import DecisionPlan


def generate_json(context: dict[str, object], plan: DecisionPlan) -> str:
    artifact = {
        "contextoEntrada": context,
        "planDecision": plan.to_dict(),
    }
    return json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=False)


def write_json(context: dict[str, object], plan: DecisionPlan, path: str | Path) -> Path:
    destination = Path(path)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(generate_json(context, plan) + "\n", encoding="utf-8")
    except OSError as exc:
        raise OSError(f"No se pudo guardar el artefacto JSON en '{destination}': {exc}") from exc
    return destination
