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
        self.root.title("CampusEnergyDSL — simulador de decisiones")
        self.root.geometry("1060x720")
        self.root.minsize(800, 560)

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        demo_tab = ttk.Frame(notebook, padding=12)
        editor_tab = ttk.Frame(notebook, padding=12)
        notebook.add(demo_tab, text="Demostración")
        notebook.add(editor_tab, text="Reglas DSL")
        self.notebook = notebook

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
        ttk.Button(toolbar, text="Evaluar", command=self.evaluate).pack(side="left")
        ttk.Button(toolbar, text="Guardar JSON…", command=self.save_plan).pack(side="left", padx=8)

        self.output = tk.Text(demo_tab, wrap="word", font=("Consolas", 10), state="disabled")
        self.output.pack(fill="both", expand=True)

        editor_controls = ttk.Frame(editor_tab)
        editor_controls.pack(fill="x", pady=(0, 8))
        ttk.Label(
            editor_controls,
            text="Puedes editar el catálogo y probarlo sin accionar equipos reales.",
        ).pack(side="left")
        ttk.Button(editor_controls, text="Guardar reglas", command=self.save_rules).pack(side="right")
        ttk.Button(editor_controls, text="Recargar archivo", command=self.reload_rules).pack(
            side="right", padx=8
        )
        self.rule_editor = tk.Text(editor_tab, wrap="none", font=("Consolas", 10), undo=True)
        self.rule_editor.pack(fill="both", expand=True)
        self.rule_editor.insert("1.0", load_rule_source())

        self.scenario_picker.bind("<<ComboboxSelected>>", lambda _event: self.show_scenario())
        self.show_scenario()
        self.evaluate()

    def show_scenario(self) -> None:
        scenario = self.scenarios[self.scenario_name.get()]
        self._show_output(
            f"{scenario.get('descripcion', '')}\n\n"
            "El motor trabaja en modo simulación: no se conecta a sensores ni a actuadores.\n"
            "Pulsa «Evaluar» para ejecutar el pipeline y generar el plan JSON."
        )

    def evaluate(self) -> None:
        name = self.scenario_name.get()
        try:
            scenario, plan = execute_scenario(
                self.rule_editor.get("1.0", "end-1c"), name, self.scenarios
            )
        except (DSLParseError, DSLValidationError, ValueError, OSError) as exc:
            self.last_json = None
            self._show_output(f"Error al evaluar:\n{exc}")
            return

        description = str(scenario.get("descripcion", ""))
        if plan is None:
            self.last_json = None
            self._show_output(
                f"{description}\n\nLa condición de la regla no se cumple en este contexto.\n"
                "No se genera una orden ni se accionan equipos."
            )
            return

        self.last_json = generate_json(scenario["contexto"], plan)  # type: ignore[arg-type]
        self._show_output(
            f"{description}\n\nResultado: {plan.resolution}\n\n"
            f"Artefacto DecisionPlan:\n{self.last_json}"
        )

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

    def save_rules(self) -> None:
        try:
            RULES_PATH.write_text(self.rule_editor.get("1.0", "end-1c"), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("No se pudieron guardar las reglas", str(exc))
            return
        messagebox.showinfo("Reglas guardadas", f"Catálogo actualizado:\n{RULES_PATH}")

    def reload_rules(self) -> None:
        try:
            source = load_rule_source()
        except OSError as exc:
            messagebox.showerror("No se pudo recargar", str(exc))
            return
        self.rule_editor.delete("1.0", "end")
        self.rule_editor.insert("1.0", source)

    def _show_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")


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
