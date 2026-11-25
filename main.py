from __future__ import annotations

import argparse
import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from decision import DecisionPlan
from generator import generate_json, write_json
from interpreter import evaluate_named_rule
from parser import DSLParseError, parse_program
from rule_editor import (
    RuleManagerFrame,
    UI_COLORS,
    _RuleEditorDialog,
    configure_visual_style,
    render_rule_blocks,
    rule_title,
)
from validator import DSLValidationError, validate_context, validate_rules

BASE_DIR = Path(__file__).resolve().parent
RULES_PATH = BASE_DIR / "reglas_campus.dsl"
SCENARIOS_PATH = BASE_DIR / "escenarios.json"
DEFAULT_OUTPUT_DIR = BASE_DIR / "artifacts"


def load_scenarios() -> dict[str, dict[str, object]]:
    try:
        scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudieron cargar los escenarios: {exc}") from exc
    if not isinstance(scenarios, dict) or not scenarios:
        raise ValueError("El archivo de escenarios debe contener al menos un escenario.")
    return scenarios


def load_rule_source() -> str:
    try:
        return RULES_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise OSError(f"No se pudo leer el catálogo '{RULES_PATH}': {exc}") from exc


def execute_scenario(
    source: str, scenario_name: str, scenarios: dict[str, dict[str, object]]
) -> tuple[dict[str, object], DecisionPlan | None]:
    if scenario_name not in scenarios:
        raise ValueError(f"Escenario desconocido: '{scenario_name}'.")
    rules = parse_program(source)
    validate_rules(rules)
    scenario = scenarios[scenario_name]
    context = scenario.get("contexto")
    rule_name = scenario.get("regla")
    if not isinstance(context, dict) or not isinstance(rule_name, str):
        raise ValueError(f"Definición incompleta del escenario '{scenario_name}'.")
    validate_context(context)
    return scenario, evaluate_named_rule(rules, rule_name, context)


class CampusEnergyApp:
    def __init__(self, root: tk.Tk, scenarios: dict[str, dict[str, object]]) -> None:
        self.root = root
        self.scenarios = scenarios
        self.last_json: str | None = None
        configure_visual_style(root)
        self.root.title("CampusEnergyDSL — simulador de decisiones")
        self.root.geometry("1060x720")
        self.root.minsize(800, 560)

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        create_tab = ttk.Frame(notebook, padding=0)
        rules_tab = ttk.Frame(notebook, padding=0)
        demo_tab = ttk.Frame(notebook, padding=12)
        notebook.add(create_tab, text="Crear")
        notebook.add(rules_tab, text="Reglas")
        notebook.add(demo_tab, text="Demostración")
        self.notebook = notebook

        self.rule_manager = RuleManagerFrame(
            rules_tab,
            scenarios,
            RULES_PATH,
            on_create=lambda: notebook.select(create_tab),
        )
        self.rule_manager.pack(fill="both", expand=True)
        self.rule_creator = _RuleEditorDialog(
            self.rule_manager,
            None,
            self.rule_manager._save_rule,
            embedded_parent=create_tab,
        )

        toolbar = ttk.Frame(demo_tab)
        toolbar.pack(fill="x", pady=(0, 10))
        ttk.Label(toolbar, text="Escenario:").pack(side="left")
        self.scenario_name = tk.StringVar(value=next(iter(scenarios)))
        self.scenario_picker = ttk.Combobox(
            toolbar,
            textvariable=self.scenario_name,
            values=list(scenarios),
            state="readonly",
            width=34,
        )
        self.scenario_picker.pack(side="left", padx=(8, 14))
        ttk.Button(
            toolbar,
            text="Evaluar bloques",
            command=self.evaluate,
            style="Primary.TButton",
        ).pack(side="left")
        ttk.Button(toolbar, text="Ver artefacto JSON", command=self.show_json).pack(
            side="left", padx=8
        )
        ttk.Button(toolbar, text="Guardar JSON…", command=self.save_plan).pack(side="left")

        scenario_frame = ttk.Frame(demo_tab)
        scenario_frame.pack(fill="x", pady=(0, 10))
        self.demo_rule_title = ttk.Label(
            scenario_frame,
            text="",
            font=("Segoe UI", 13, "bold"),
        )
        self.demo_rule_title.pack(anchor="w", pady=(0, 3))
        self.scenario_description = ttk.Label(
            scenario_frame,
            text="",
            wraplength=950,
        )
        self.scenario_description.pack(anchor="w")
        self.demo_result = ttk.Label(
            scenario_frame,
            text="Selecciona «Evaluar bloques» para ejecutar la simulación.",
            font=("Segoe UI", 10, "bold"),
        )
        self.demo_result.pack(anchor="w", pady=(5, 0))

        self.demo_blocks = ttk.Frame(demo_tab)
        self.demo_blocks.pack(fill="both", expand=True)

        self.scenario_picker.bind("<<ComboboxSelected>>", lambda _event: self.show_scenario())
        self.show_scenario()

    def show_scenario(self) -> None:
        scenario = self.scenarios[self.scenario_name.get()]
        self.scenario_description.configure(
            text=f"{scenario.get('descripcion', '')}  ·  Modo de demostración: sin conexión "
            "a sensores ni actuadores reales."
        )
        self.last_json = None
        self.demo_result.configure(
            text="Selecciona «Evaluar bloques» para ejecutar la simulación.",
            foreground=UI_COLORS["muted"],
        )
        try:
            rules = parse_program(load_rule_source())
            validate_rules(rules)
            rule_name = scenario.get("regla")
            rule = next((item for item in rules if item.name == rule_name), None)
            if rule is None:
                raise ValueError(f"No se encontró la regla del escenario '{rule_name}'.")
            self.demo_rule_title.configure(text=rule_title(rule.name))
            render_rule_blocks(self.demo_blocks, rule)
        except (DSLParseError, DSLValidationError, ValueError, OSError) as exc:
            self._show_demo_error(str(exc))

    def evaluate(self) -> None:
        name = self.scenario_name.get()
        try:
            source = load_rule_source()
            rules = parse_program(source)
            validate_rules(rules)
            scenario, plan = execute_scenario(source, name, self.scenarios)
            rule_name = scenario.get("regla")
            rule = next((item for item in rules if item.name == rule_name), None)
            if rule is None:
                raise ValueError(f"No se encontró la regla del escenario '{rule_name}'.")
        except (DSLParseError, DSLValidationError, ValueError, OSError) as exc:
            self.last_json = None
            self._show_demo_error(f"Error al evaluar: {exc}")
            return

        if plan is None:
            self.last_json = None
            render_rule_blocks(
                self.demo_blocks,
                rule,
                "No coincide: las condiciones no se cumplen en este escenario.",
            )
            self.demo_result.configure(
                text="No coincide: no se propone una acción.",
                foreground=UI_COLORS["orange"],
            )
            return

        self.last_json = generate_json(scenario["contexto"], plan)  # type: ignore[arg-type]
        render_rule_blocks(
            self.demo_blocks,
            rule,
            f"Resultado: {plan.resolution}",
        )
        result_color = {
            "PERMITIDA": UI_COLORS["green"],
            "BLOQUEADA": UI_COLORS["red"],
            "REQUIERE AUTORIZACION": UI_COLORS["orange"],
        }.get(plan.resolution, UI_COLORS["muted"])
        self.demo_result.configure(
            text=f"Resultado: {plan.resolution}",
            foreground=result_color,
        )

    def show_json(self) -> None:
        if self.last_json is None:
            messagebox.showinfo(
                "Sin resultado",
                "Primero evalúa el escenario para generar el artefacto JSON.",
                parent=self.root,
            )
            return
        window = tk.Toplevel(self.root)
        window.title("Artefacto de decisión JSON")
        window.geometry("760x600")
        text = tk.Text(
            window,
            wrap="none",
            font=("Consolas", 10),
            background=UI_COLORS["input"],
            foreground=UI_COLORS["text"],
            padx=12,
            pady=12,
        )
        text.pack(fill="both", expand=True)
        text.insert("1.0", self.last_json)
        text.configure(state="disabled")

    def save_plan(self) -> None:
        if self.last_json is None:
            messagebox.showwarning("Sin resultado", "Evalúa un escenario coincidente antes de guardar.")
            return
        destination = filedialog.asksaveasfilename(
            title="Guardar artefacto de decisión",
            initialdir=str(DEFAULT_OUTPUT_DIR),
            initialfile=f"{self.scenario_name.get()}.json",
            defaultextension=".json",
            filetypes=[("Archivo JSON", "*.json")],
        )
        if not destination:
            return
        try:
            Path(destination).write_text(self.last_json + "\n", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("No se pudo guardar", str(exc))
            return
        messagebox.showinfo("Guardado", f"Artefacto guardado en:\n{destination}")

    def _show_demo_error(self, text: str) -> None:
        for child in self.demo_blocks.winfo_children():
            child.destroy()
        ttk.Label(
            self.demo_blocks,
            text=text,
            foreground=UI_COLORS["red"],
            wraplength=900,
        ).pack(anchor="w", pady=12)
        self.demo_result.configure(text="No se pudo mostrar la regla.", foreground=UI_COLORS["red"])


def _run_cli(args: argparse.Namespace) -> int:
    scenarios = load_scenarios()
    if args.list_scenarios:
        for name, scenario in scenarios.items():
            print(f"{name}: {scenario['descripcion']}")
        return 0

    source = load_rule_source()
    selected = list(scenarios) if args.all else [args.scenario]
    for name in selected:
        scenario, plan = execute_scenario(source, name, scenarios)
        if plan is None:
            print(f"{name}: SIN COINCIDENCIA — {scenario['descripcion']}")
            continue
        output_path = Path(args.output) if args.output and not args.all else DEFAULT_OUTPUT_DIR / f"{name}.json"
        write_json(scenario["contexto"], plan, output_path)  # type: ignore[arg-type]
        print(f"{name}: {plan.resolution} — {plan.proposed_action}({plan.target_equipment})")
        print(f"  JSON: {output_path}")
    return 0


def main() -> int:
    argument_parser = argparse.ArgumentParser(description="CampusEnergyDSL, simulador de políticas energéticas.")
    argument_parser.add_argument("--scenario", help="Evalúa un escenario por nombre.")
    argument_parser.add_argument("--all", action="store_true", help="Ejecuta los diez escenarios de demostración.")
    argument_parser.add_argument("--list-scenarios", action="store_true", help="Muestra los escenarios disponibles.")
    argument_parser.add_argument("--output", help="Ruta JSON para una ejecución con --scenario.")
    args = argument_parser.parse_args()

    if args.scenario or args.all or args.list_scenarios:
        try:
            return _run_cli(args)
        except (DSLParseError, DSLValidationError, ValueError, OSError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    try:
        root = tk.Tk()
        CampusEnergyApp(root, load_scenarios())
    except (DSLParseError, DSLValidationError, ValueError, OSError) as exc:
        print(f"No se pudo iniciar CampusEnergyDSL: {exc}", file=sys.stderr)
        return 1
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
