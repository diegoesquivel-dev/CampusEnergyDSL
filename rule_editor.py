from __future__ import annotations

import json
import re
import unicodedata
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable

from astNodes import (
    Action,
    Comparison,
    Condition,
    Conjunction,
    Disjunction,
    Negation,
    Rule,
)
from interpreter import evaluate_named_rule
from parser import parse_program
from validator import (
    ENUM_VALUES,
    EQUIPMENT_BY_SPACE,
    NUMERIC_ATTRIBUTES,
    SPACE_CODES,
    DSLValidationError,
    validate_rules,
)

SPACE_LABELS = {
    "AULA302": "Aula 302",
    "PASILLOB1": "Pasillo B1",
    "LABFISICA": "Laboratorio de Física",
    "LABQUIMICA": "Laboratorio de Química",
    "DATACENTER01": "Centro de datos",
}
UI_COLORS = {
    "window": "#1b1f26",
    "surface": "#252b33",
    "raised": "#2d343e",
    "input": "#20252c",
    "border": "#3c4653",
    "text": "#e6edf5",
    "muted": "#a7b3c2",
    "blue": "#1299d2",
    "blue_dark": "#087eaf",
    "green": "#35a853",
    "red": "#dc3d3d",
    "orange": "#f0a52b",
}
EQUIPMENT_LABELS = {
    ("AULA302", "AIRE02"): "Aire acondicionado 02",
    ("PASILLOB1", "LUM01"): "Iluminación 01",
    ("LABFISICA", "EXTRACTOR01"): "Extractor 01",
    ("LABQUIMICA", "AIRE01"): "Aire acondicionado 01",
    ("DATACENTER01", "SERVIDOR01"): "Servidor 01",
}
ATTRIBUTE_LABELS = {
    "ocupacion": "Ocupación del espacio",
    "tiempoVacio": "Minutos sin ocupación",
    "actividadActual": "Actividad actual",
    "criticidad": "Nivel de criticidad",
    "frescura": "Estado del sensor",
    "bloqueTarifa": "Horario de tarifa",
    "demandaNeta": "Demanda neta (kW)",
    "eventoProveedor": "Evento del proveedor",
}
VALUE_LABELS = {
    "VACIO": "Vacío",
    "OCUPADO": "Ocupado",
    "NINGUNA": "Sin actividad",
    "CLASE": "Clase en curso",
    "EXPERIMENTO": "Experimento en curso",
    "BAJA": "Baja",
    "MEDIA": "Media",
    "ALTA": "Alta",
    "EXTREMA": "Extrema",
    "ACTUALIZADO": "Actualizado",
    "OBSOLETO": "Obsoleto",
    "DESCONECTADO": "Desconectado",
    "VALLE": "Valle",
    "PUNTA": "Punta",
    "NORMAL": "Sin evento",
    "REDUCCION": "Solicitud de reducción",
}
ACTION_LABELS = {
    "apagar": "Proponer apagado",
    "modoAhorro": "Activar modo ahorro",
    "recomendarApagado": "Solicitar aprobación para apagado",
    "emitirAlerta": "Emitir alerta informativa",
}
ACTION_NAMES = {label: name for name, label in ACTION_LABELS.items()}
SPACE_NAMES = {label: code for code, label in SPACE_LABELS.items()}
RESERVED_NAMES = {
    "REGLA",
    "CUANDO",
    "ENTONCES",
    "Y",
    "O",
    "NO",
    "apagar",
    "modoAhorro",
    "recomendarApagado",
    "emitirAlerta",
}
DEFAULT_TITLES = {
    "ahorroBasico": "Ahorro en aulas vacías",
    "ahorroPasillo": "Ahorro de iluminación en pasillos",
    "revisionLaboratorio": "Revisión de laboratorio",
    "alertaTelemetria": "Alerta de telemetría",
    "ahorroHoraPunta": "Ahorro en hora punta",
    "atenuaSolarBaja": "Atenuación por baja generación solar",
    "excedenteSolarConfort": "Alerta de excedente solar",
    "respuestaEventoProveedor": "Respuesta a evento del proveedor",
    "reduccionLaboratorioEvento": "Reducción en laboratorio",
    "alertaCriticaProveedor": "Protección del centro de datos",
}


def configure_visual_style(root: tk.Tk) -> None:
    root.configure(background=UI_COLORS["window"])
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure(
        ".",
        background=UI_COLORS["surface"],
        foreground=UI_COLORS["text"],
        font=("Segoe UI", 10),
    )
    style.configure("TFrame", background=UI_COLORS["surface"])
    style.configure("TLabel", background=UI_COLORS["surface"], foreground=UI_COLORS["text"])
    style.configure(
        "TButton",
        background=UI_COLORS["raised"],
        foreground=UI_COLORS["text"],
        padding=(10, 6),
        borderwidth=0,
    )
    style.map(
        "TButton",
        background=[("active", UI_COLORS["blue"]), ("pressed", UI_COLORS["blue_dark"])],
        foreground=[("disabled", UI_COLORS["muted"])],
    )
    style.configure(
        "Primary.TButton",
        background=UI_COLORS["blue"],
        foreground="#ffffff",
        padding=(12, 7),
        font=("Segoe UI", 10, "bold"),
    )
    style.map("Primary.TButton", background=[("active", UI_COLORS["blue_dark"])])
    style.configure(
        "Save.TButton",
        background=UI_COLORS["green"],
        foreground="#ffffff",
        padding=(12, 7),
        font=("Segoe UI", 10, "bold"),
    )
    style.configure(
        "Danger.TButton",
        background=UI_COLORS["red"],
        foreground="#ffffff",
        padding=(10, 6),
    )
    style.configure(
        "TEntry",
        fieldbackground=UI_COLORS["input"],
        foreground=UI_COLORS["text"],
        insertcolor=UI_COLORS["text"],
        bordercolor=UI_COLORS["border"],
        padding=6,
    )
    style.configure(
        "TCombobox",
        fieldbackground=UI_COLORS["input"],
        background=UI_COLORS["raised"],
        foreground=UI_COLORS["text"],
        arrowcolor=UI_COLORS["text"],
        bordercolor=UI_COLORS["border"],
        padding=5,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", UI_COLORS["input"])],
        foreground=[("readonly", UI_COLORS["text"])],
        selectbackground=[("readonly", UI_COLORS["input"])],
        selectforeground=[("readonly", UI_COLORS["text"])],
    )
    style.configure("TCheckbutton", background=UI_COLORS["surface"], foreground=UI_COLORS["text"])
    style.map("TCheckbutton", background=[("active", UI_COLORS["surface"])])
    style.configure("TNotebook", background=UI_COLORS["window"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=UI_COLORS["raised"],
        foreground=UI_COLORS["muted"],
        padding=(14, 8),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", UI_COLORS["surface"]), ("active", UI_COLORS["raised"])],
        foreground=[("selected", UI_COLORS["blue"]), ("active", UI_COLORS["text"])],
    )
    style.configure("TPanedwindow", background=UI_COLORS["window"])
    style.configure("Vertical.TScrollbar", background=UI_COLORS["raised"], troughcolor=UI_COLORS["window"])


def rule_title(name: str) -> str:
    if name in DEFAULT_TITLES:
        return DEFAULT_TITLES[name]
    return re.sub(r"(?<!^)(?=[A-Z])", " ", name).replace("_", " ").capitalize()


def rule_slug(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_name).strip("_")
    if not slug or not slug[0].isalpha():
        slug = f"regla_{slug}" if slug else "regla_nueva"
    if slug.upper() in RESERVED_NAMES:
        slug = f"regla_{slug}"
    return slug


def _dnf(condition: Condition, negate: bool = False) -> list[list[Condition]]:
    if isinstance(condition, Comparison):
        atom: Condition = Negation(condition) if negate else condition
        return [[atom]]
    if isinstance(condition, Negation):
        return _dnf(condition.operand, not negate)
    if isinstance(condition, (Conjunction, Disjunction)):
        is_conjunction = isinstance(condition, Conjunction) != negate
        branches = [_dnf(child, negate) for child in condition.operands]
        if is_conjunction:
            result = [[]]
            for child_branches in branches:
                result = [left + right for left in result for right in child_branches]
            return result
        return [branch for child_branches in branches for branch in child_branches]
    raise TypeError(f"Tipo de condición no reconocido: {type(condition).__name__}")


def editable_groups(rule: Rule) -> list[list[Condition]]:
    groups: list[list[Condition]] = []
    for branch in _dnf(rule.condition):
        visible: list[Condition] = []
        for atom in branch:
            comparison = atom.operand if isinstance(atom, Negation) else atom
            if not isinstance(comparison, Comparison):
                raise ValueError("La regla contiene una condición que no se puede editar como bloque.")
            if comparison.attribute == "codEspacio":
                if comparison.operator != "=" or comparison.value != rule.action.space_code:
                    raise ValueError("La regla tiene una condición de espacio incompatible con su equipo.")
                continue
            visible.append(atom)
        groups.append(visible)
    return groups


def build_rule(
    name: str,
    space_code: str,
    groups: list[list[Condition]],
    command: str,
    equipment_code: str,
) -> Rule:
    scoped_condition: Condition = Comparison("codEspacio", "=", space_code)
    if groups and not any(not group for group in groups):
        branch_conditions: list[Condition] = []
        for group in groups:
            if len(group) == 1:
                branch_conditions.append(group[0])
            elif group:
                branch_conditions.append(Conjunction(tuple(group)))
        if branch_conditions:
            any_branch: Condition = (
                branch_conditions[0]
                if len(branch_conditions) == 1
                else Disjunction(tuple(branch_conditions))
            )
            scoped_condition = Conjunction((scoped_condition, any_branch))
    return Rule(
        name,
        scoped_condition,
        Action(command, space_code, equipment_code),
    )


def _condition_source(condition: Condition) -> str:
    if isinstance(condition, Comparison):
        literal = json.dumps(condition.value, ensure_ascii=False) if isinstance(
            condition.value, str
        ) else str(condition.value)
        return f"{condition.attribute} {condition.operator} {literal}"
    if isinstance(condition, Negation):
        return f"NO ({_condition_source(condition.operand)})"
    if isinstance(condition, Conjunction):
        return "(" + " Y ".join(_condition_source(item) for item in condition.operands) + ")"
    if isinstance(condition, Disjunction):
        return "(" + " O ".join(_condition_source(item) for item in condition.operands) + ")"
    raise TypeError(f"Tipo de condición no reconocido: {type(condition).__name__}")


def serialize_rule(rule: Rule) -> str:
    return (
        f"REGLA {rule.name}:\n"
        f"CUANDO {_condition_source(rule.condition)}\n"
        f"ENTONCES {rule.action.command}"
        f"({rule.action.space_code}.{rule.action.equipment_code});"
    )


def serialize_program(rules: list[Rule]) -> str:
    return (
        "# Catálogo de políticas CampusEnergyDSL, administrado desde la interfaz visual.\n\n"
        + "\n\n".join(serialize_rule(rule) for rule in rules)
        + "\n"
    )


class RuleManagerFrame(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        scenarios: dict[str, dict[str, object]],
        rules_path: Path,
    ) -> None:
        super().__init__(master, padding=12)
        self.scenarios = scenarios
        self.rules_path = rules_path
        self.rules: list[Rule] = []
        self.visible_rules: list[Rule] = []
        self._create_layout()
        self.refresh_catalog()

    def _create_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(
            header,
            text="Políticas del campus",
            font=("Segoe UI", 17, "bold"),
        ).pack(side="left")
        ttk.Label(
            header,
            text="Crea y organiza reglas usando bloques. El código DSL se guarda automáticamente.",
        ).pack(side="left", padx=16, pady=(5, 0))

        actions = ttk.Frame(self)
        actions.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(
            actions,
            text="＋ Crear regla",
            command=self.create_rule,
            style="Primary.TButton",
        ).pack(side="left")
        ttk.Button(actions, text="Editar bloques", command=self.edit_selected).pack(
            side="left", padx=6
        )
        ttk.Button(
            actions,
            text="Eliminar",
            command=self.delete_selected,
            style="Danger.TButton",
        ).pack(side="left")
        ttk.Button(actions, text="Actualizar", command=self.refresh_catalog).pack(side="right")

        split = ttk.Panedwindow(self, orient="horizontal")
        split.grid(row=2, column=0, sticky="nsew")
        list_panel = ttk.Frame(split, padding=(0, 0, 10, 0))
        detail_panel = ttk.Frame(split, padding=(10, 0, 0, 0))
        split.add(list_panel, weight=1)
        split.add(detail_panel, weight=3)

        ttk.Label(list_panel, text="Buscar una regla").pack(anchor="w")
        self.search_var = tk.StringVar()
        search = ttk.Entry(list_panel, textvariable=self.search_var)
        search.pack(fill="x", pady=(4, 8))
        self.search_var.trace_add("write", lambda *_args: self._populate_list())

        list_frame = ttk.Frame(list_panel)
        list_frame.pack(fill="both", expand=True)
        self.rule_list = tk.Listbox(
            list_frame,
            width=31,
            activestyle="dotbox",
            font=("Segoe UI", 10),
            background=UI_COLORS["raised"],
            foreground=UI_COLORS["text"],
            selectbackground=UI_COLORS["blue"],
            selectforeground="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground=UI_COLORS["border"],
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.rule_list.yview)
        self.rule_list.configure(yscrollcommand=scrollbar.set)
        self.rule_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.rule_list.bind("<<ListboxSelect>>", lambda _event: self.show_selected())
        self.rule_list.bind("<Double-Button-1>", lambda _event: self.edit_selected())

        self.details = ttk.Frame(detail_panel)
        self.details.pack(fill="both", expand=True)
        self.empty_detail = ttk.Label(
            self.details,
            text="Selecciona una regla para ver sus bloques y probarla.",
            anchor="center",
        )
        self.empty_detail.pack(fill="both", expand=True)

    def refresh_catalog(self, selected_name: str | None = None) -> None:
        try:
            source = self.rules_path.read_text(encoding="utf-8")
            rules = parse_program(source)
            validate_rules(rules)
        except (OSError, ValueError, DSLValidationError) as exc:
            messagebox.showerror("No se pudo cargar el catálogo", str(exc), parent=self.winfo_toplevel())
            return
        self.rules = rules
        self._populate_list(selected_name)

    def _populate_list(self, selected_name: str | None = None) -> None:
        old_selection = selected_name or self._selected_rule_name()
        query = self.search_var.get().casefold() if hasattr(self, "search_var") else ""
        self.visible_rules = [
            rule
            for rule in self.rules
            if query in rule_title(rule.name).casefold()
            or query in rule.name.casefold()
            or query in rule.action.space_code.casefold()
        ]
        self.rule_list.delete(0, "end")
        for rule in self.visible_rules:
            self.rule_list.insert(
                "end",
                f"{rule_title(rule.name)}  ·  {SPACE_LABELS[rule.action.space_code]}",
            )
        selected_index = next(
            (index for index, rule in enumerate(self.visible_rules) if rule.name == old_selection),
            0 if self.visible_rules else None,
        )
        if selected_index is None:
            self._show_empty()
            return
        self.rule_list.selection_set(selected_index)
        self.rule_list.activate(selected_index)
        self.show_selected()

    def _selected_rule_name(self) -> str | None:
        selection = self.rule_list.curselection()
        if not selection:
            return None
        index = selection[0]
        if index >= len(self.visible_rules):
            return None
        return self.visible_rules[index].name

    def _selected_rule(self) -> Rule | None:
        name = self._selected_rule_name()
        return next((rule for rule in self.rules if rule.name == name), None)

    def show_selected(self) -> None:
        rule = self._selected_rule()
        if rule is None:
            self._show_empty()
            return
        for child in self.details.winfo_children():
            child.destroy()

        title = ttk.Label(self.details, text=rule_title(rule.name), font=("Segoe UI", 17, "bold"))
        title.pack(anchor="w", pady=(0, 3))
        ttk.Label(
            self.details,
            text=f"{SPACE_LABELS[rule.action.space_code]}  ·  "
            f"{EQUIPMENT_LABELS.get((rule.action.space_code, rule.action.equipment_code), 'Equipo')}",
        ).pack(anchor="w", pady=(0, 12))

        groups_panel = ttk.Frame(self.details)
        groups_panel.pack(fill="both", expand=True)
        try:
            groups = editable_groups(rule)
        except ValueError as exc:
            ttk.Label(groups_panel, text=str(exc), foreground="#b91c1c").pack(anchor="w")
            return
        for group_index, group in enumerate(groups):
            if group_index:
                ttk.Label(
                    groups_panel,
                    text="O BIEN",
                    foreground="#b45309",
                    font=("Segoe UI", 9, "bold"),
                ).pack(anchor="w", pady=5)
            card = tk.Frame(groups_panel, bg=UI_COLORS["raised"], padx=10, pady=8)
            card.pack(fill="x", pady=3)
            ttk.Label(
                card,
                text=f"Grupo {group_index + 1}  ·  deben cumplirse todos",
                background=UI_COLORS["raised"],
                foreground=UI_COLORS["muted"],
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor="w", pady=(0, 5))
            if not group:
                ttk.Label(card, text="Sin condiciones adicionales.", background="#f1f5f9").pack(
                    anchor="w"
                )
            for condition in group:
                ttk.Label(
                    card,
                    text=self._condition_label(condition),
                    background=UI_COLORS["input"],
                    foreground=UI_COLORS["text"],
                    padding=(8, 5),
                ).pack(anchor="w", fill="x", pady=2)

        action_card = tk.Frame(self.details, bg="#173754", padx=10, pady=8)
        action_card.pack(fill="x", pady=(10, 5))
        ttk.Label(
            action_card,
            text=f"ACCIÓN  ·  {ACTION_LABELS[rule.action.command]}",
            background="#173754",
            foreground="#8bd3ff",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        test_row = ttk.Frame(self.details)
        test_row.pack(fill="x", pady=(8, 0))
        ttk.Label(test_row, text="Probar con datos de:").pack(side="left")
        scenario_names = [
            name
            for name, item in self.scenarios.items()
            if isinstance(item.get("contexto"), dict)
            and item["contexto"].get("codEspacio") == rule.action.space_code
        ]
        self.test_scenario = tk.StringVar(value=scenario_names[0] if scenario_names else "")
        self.test_picker = ttk.Combobox(
            test_row,
            textvariable=self.test_scenario,
            values=scenario_names,
            state="readonly",
            width=30,
        )
        self.test_picker.pack(side="left", padx=8)
        ttk.Button(test_row, text="▶ Probar regla", command=self.test_selected).pack(side="left")
        self.test_result = ttk.Label(self.details, text="", wraplength=650)
        self.test_result.pack(anchor="w", pady=(7, 0))

    def _show_empty(self) -> None:
        for child in self.details.winfo_children():
            child.destroy()
        ttk.Label(
            self.details,
            text="Selecciona una regla para ver sus bloques y probarla.",
            anchor="center",
        ).pack(fill="both", expand=True)

    @staticmethod
    def _condition_label(condition: Condition) -> str:
        negated = isinstance(condition, Negation)
        comparison = condition.operand if negated else condition
        if not isinstance(comparison, Comparison):
            return "Condición lógica"
        attribute = ATTRIBUTE_LABELS.get(comparison.attribute, comparison.attribute)
        value = comparison.value
        if isinstance(value, str):
            value = VALUE_LABELS.get(value, SPACE_LABELS.get(value, value))
        operator = {"=": "es", "!=": "no es", ">": "mayor que", "<": "menor que", ">=": "al menos", "<=": "como máximo"}.get(comparison.operator, comparison.operator)
        prefix = "NO " if negated else ""
        return f"{prefix}{attribute} {operator} {value}"

    def create_rule(self) -> None:
        self._open_editor(None)

    def edit_selected(self) -> None:
        rule = self._selected_rule()
        if rule is None:
            messagebox.showinfo("Selecciona una regla", "Elige primero una regla para editar.")
            return
        self._open_editor(rule)

    def _open_editor(self, rule: Rule | None) -> None:
        editor = _RuleEditorDialog(self, rule, self._save_rule)
        self.wait_window(editor.window)

    def _save_rule(self, updated: Rule, old_name: str | None) -> None:
        rules = list(self.rules)
        if old_name is None:
            if any(rule.name == updated.name for rule in rules):
                raise ValueError(f"Ya existe una regla llamada '{updated.name}'.")
            rules.append(updated)
        else:
            if updated.name != old_name and any(rule.name == updated.name for rule in rules):
                raise ValueError(f"Ya existe una regla llamada '{updated.name}'.")
            rules = [
                updated if rule.name == old_name else rule
                for rule in rules
            ]
        validate_rules(rules)
        self.rules_path.write_text(serialize_program(rules), encoding="utf-8")
        self.refresh_catalog(updated.name)

    def delete_selected(self) -> None:
        rule = self._selected_rule()
        if rule is None:
            messagebox.showinfo("Selecciona una regla", "Elige primero una regla para eliminar.")
            return
        if not messagebox.askyesno(
            "Eliminar regla",
            f"¿Eliminar «{rule_title(rule.name)}» del catálogo?",
            parent=self.winfo_toplevel(),
        ):
            return
        remaining = [item for item in self.rules if item.name != rule.name]
        try:
            validate_rules(remaining)
            self.rules_path.write_text(serialize_program(remaining), encoding="utf-8")
        except (OSError, DSLValidationError) as exc:
            messagebox.showerror("No se pudo eliminar", str(exc), parent=self.winfo_toplevel())
            return
        self.refresh_catalog()

    def test_selected(self) -> None:
        rule = self._selected_rule()
        if rule is None or not self.test_scenario.get():
            return
        scenario = self.scenarios[self.test_scenario.get()]
        context = scenario.get("contexto")
        if not isinstance(context, dict):
            messagebox.showerror("Escenario inválido", "El escenario no contiene un contexto válido.")
            return
        try:
            plan = evaluate_named_rule([rule], rule.name, context)
        except (ValueError, TypeError) as exc:
            messagebox.showerror("No se pudo probar la regla", str(exc), parent=self.winfo_toplevel())
            return
        if plan is None:
            result = "No coincide: las condiciones no se cumplen en este escenario."
        else:
            result = f"{plan.resolution}  ·  {ACTION_LABELS[rule.action.command]}"
            if plan.requires_authorization:
                result += "  ·  requiere autorización humana"
        self.test_result.configure(text=result, foreground="#047857" if plan else "#b45309")


class _RuleEditorDialog:
    def __init__(
        self,
        manager: RuleManagerFrame,
        rule: Rule | None,
        on_save: Callable[[Rule, str | None], None],
    ) -> None:
        self.manager = manager
        self.rule = rule
        self.on_save = on_save
        self.old_name = rule.name if rule else None
        self.groups: list[dict[str, object]] = []
        self.window = tk.Toplevel(manager)
        self.window.title("Crear política con bloques" if rule is None else "Editar política con bloques")
        self.window.geometry("960x780")
        self.window.minsize(720, 600)
        self.window.configure(background=UI_COLORS["window"])
        self.window.transient(manager.winfo_toplevel())
        self.window.grab_set()

        self._create_form()
        if rule:
            self._load_rule(rule)
        else:
            self._add_group()
        self._render_groups()

    def _create_form(self) -> None:
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(1, weight=1)

        header = ttk.Frame(self.window, padding=(16, 12, 16, 8))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(
            header,
            text="Diseña la regla con bloques",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="Selecciona el espacio, añade condiciones y define qué debe proponer el sistema.",
        ).pack(anchor="w", pady=(3, 0))

        form = ttk.Frame(header)
        form.pack(fill="x", pady=(12, 0))
        self.title_var = tk.StringVar()
        self.space_var = tk.StringVar()
        self.action_var = tk.StringVar()
        self.equipment_var = tk.StringVar()

        ttk.Label(form, text="Nombre de la regla").grid(row=0, column=0, sticky="w")
        self.title_entry = ttk.Entry(form, textvariable=self.title_var, width=35)
        self.title_entry.grid(row=1, column=0, sticky="ew", padx=(0, 14), pady=(3, 10))
        ttk.Label(form, text="Espacio").grid(row=0, column=1, sticky="w")
        self.space_picker = ttk.Combobox(
            form,
            textvariable=self.space_var,
            values=list(SPACE_NAMES),
            state="readonly",
            width=28,
        )
        self.space_picker.grid(row=1, column=1, sticky="ew", pady=(3, 10))
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        self.canvas = tk.Canvas(
            self.window,
            highlightthickness=0,
            background=UI_COLORS["window"],
        )
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=8)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 16), pady=8)
        self.groups_frame = tk.Frame(
            self.canvas,
            background=UI_COLORS["window"],
            padx=8,
            pady=8,
        )
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.groups_frame, anchor="nw"
        )
        self.groups_frame.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(self.canvas_window, width=event.width),
        )

        footer = ttk.Frame(self.window, padding=(16, 8, 16, 14))
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        effect_card = ttk.LabelFrame(footer, text="ACCIÓN PROPUESTA  ·  ENTONCES", padding=10)
        effect_card.pack(fill="x", pady=(0, 10))
        ttk.Label(effect_card, text="Tipo").grid(row=0, column=0, sticky="w")
        ttk.Label(effect_card, text="Equipo objetivo").grid(row=0, column=1, sticky="w")
        self.action_picker = ttk.Combobox(
            effect_card,
            textvariable=self.action_var,
            values=list(ACTION_NAMES),
            state="readonly",
            width=38,
        )
        self.action_picker.grid(row=1, column=0, sticky="ew", padx=(0, 14), pady=(3, 0))
        self.equipment_picker = ttk.Combobox(
            effect_card,
            textvariable=self.equipment_var,
            state="readonly",
            width=35,
        )
        self.equipment_picker.grid(row=1, column=1, sticky="ew", pady=(3, 0))
        effect_card.columnconfigure(0, weight=1)
        effect_card.columnconfigure(1, weight=1)

        controls = ttk.Frame(footer)
        controls.pack(fill="x")
        ttk.Button(
            controls,
            text="＋ Agregar condición (Y)",
            command=self._add_condition,
            style="Primary.TButton",
        ).pack(side="left")
        ttk.Button(
            controls,
            text="＋ Grupo alternativo (O)",
            command=self._add_group,
            style="Primary.TButton",
        ).pack(side="left", padx=8)
        ttk.Button(controls, text="Cancelar", command=self.window.destroy).pack(side="right")
        ttk.Button(
            controls,
            text="Guardar regla",
            command=self._save,
            style="Save.TButton",
        ).pack(side="right", padx=(0, 8))

        section_header = ttk.Label(
            self.groups_frame,
            text="CONDICIONES DE ACTIVACIÓN  ·  CUANDO",
            background=UI_COLORS["window"],
            foreground=UI_COLORS["text"],
            font=("Segoe UI", 11, "bold"),
        )
        section_header.pack(anchor="w", pady=(0, 3))
        ttk.Label(
            self.groups_frame,
            text="Añade criterios del espacio, los sensores y la energía. "
            "Dentro de un grupo se cumplen todos (Y); entre grupos basta uno (O).",
            background=UI_COLORS["window"],
            foreground=UI_COLORS["muted"],
            wraplength=800,
        ).pack(anchor="w", pady=(0, 8))

        self.groups_container = tk.Frame(
            self.groups_frame,
            background=UI_COLORS["window"],
        )
        self.groups_container.pack(fill="both", expand=True)
        self.space_picker.bind("<<ComboboxSelected>>", self._space_changed)

    def _load_rule(self, rule: Rule) -> None:
        self.title_var.set(rule_title(rule.name))
        self.title_entry.configure(state="readonly")
        self.space_var.set(SPACE_LABELS[rule.action.space_code])
        self.action_var.set(ACTION_LABELS[rule.action.command])
        self._update_equipment_choices(rule.action.equipment_code)
        self.groups = []
        for group in editable_groups(rule):
            rows = []
            for condition in group:
                negated = isinstance(condition, Negation)
                comparison = condition.operand if negated else condition
                if not isinstance(comparison, Comparison):
                    raise ValueError("No se puede cargar una condición no compatible con el editor visual.")
                rows.append(
                    {
                        "attribute": comparison.attribute,
                        "operator": comparison.operator,
                        "value": comparison.value,
                        "negated": negated,
                    }
                )
            self.groups.append({"rows": rows})

    def _space_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._update_equipment_choices()

    def _update_equipment_choices(self, selected_code: str | None = None) -> None:
        space = SPACE_NAMES.get(self.space_var.get())
        equipment_codes = sorted(EQUIPMENT_BY_SPACE.get(space, set()))
        labels = [EQUIPMENT_LABELS.get((space, code), code) for code in equipment_codes]
        self.equipment_picker.configure(values=labels)
        selected = selected_code or (equipment_codes[0] if equipment_codes else "")
        self.equipment_var.set(EQUIPMENT_LABELS.get((space, selected), ""))

    def _add_group(self) -> None:
        self.groups.append(
            {
                "rows": [
                    {
                        "attribute": "ocupacion",
                        "operator": "=",
                        "value": "VACIO",
                        "negated": False,
                    }
                ]
            }
        )
        if hasattr(self, "groups_frame"):
            self._render_groups()

    def _add_condition(self, group_index: int | None = None) -> None:
        if not self.groups:
            self._add_group()
            return
        index = len(self.groups) - 1 if group_index is None else group_index
        rows = self.groups[index]["rows"]
        assert isinstance(rows, list)
        rows.append(
            {
                "attribute": "tiempoVacio",
                "operator": ">=",
                "value": 15,
                "negated": False,
            }
        )
        self._render_groups()

    def _render_groups(self) -> None:
        for child in self.groups_container.winfo_children():
            child.destroy()
        for group_index, group in enumerate(self.groups):
            if group_index:
                ttk.Label(
                    self.groups_frame,
                    text="O BIEN · basta con que se cumpla uno de los grupos",
                    foreground=UI_COLORS["orange"],
                    background=UI_COLORS["window"],
                    font=("Segoe UI", 9, "bold"),
                ).pack(anchor="w", pady=(10, 4))
            card = tk.Frame(
                self.groups_container,
                background=UI_COLORS["surface"],
                highlightbackground=UI_COLORS["border"],
                highlightthickness=1,
                padx=10,
                pady=9,
            )
            card.pack(fill="x", pady=3)
            heading = ttk.Frame(card)
            heading.pack(fill="x", pady=(0, 6))
            ttk.Label(
                heading,
                text=f"GRUPO {group_index + 1}  ·  se cumplen todas las condiciones",
                background=UI_COLORS["surface"],
                foreground="#8bc7ff",
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left")
            ttk.Button(
                heading,
                text="Eliminar grupo",
                command=lambda index=group_index: self._remove_group(index),
                style="Danger.TButton",
            ).pack(side="right")
            rows = group["rows"]
            assert isinstance(rows, list)
            for row_index, row in enumerate(rows):
                if row_index:
                    ttk.Label(
                        card,
                        text="Y TAMBIÉN",
                        background=UI_COLORS["surface"],
                        foreground=UI_COLORS["muted"],
                        font=("Segoe UI", 8, "bold"),
                    ).pack(anchor="w", pady=(4, 1))
                self._render_condition_row(card, group_index, row_index, row)
            ttk.Button(
                card,
                text="＋ Añadir condición a este grupo",
                command=lambda index=group_index: self._add_condition(index),
            ).pack(anchor="w", pady=(7, 0))
        self.groups_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _render_condition_row(
        self,
        parent: tk.Misc,
        group_index: int,
        row_index: int,
        row: dict[str, object],
    ) -> None:
        line = tk.Frame(parent, background=UI_COLORS["input"], padx=6, pady=6)
        line.pack(fill="x")
        negated = tk.BooleanVar(value=bool(row["negated"]))
        ttk.Checkbutton(line, text="NO", variable=negated).pack(side="left", padx=(0, 5))
        attribute_var = tk.StringVar()
        current_attr = str(row["attribute"])
        attribute_var.set(ATTRIBUTE_LABELS.get(current_attr, current_attr))
        attribute_values = list(ATTRIBUTE_LABELS.values())
        attribute_picker = ttk.Combobox(
            line,
            textvariable=attribute_var,
            values=attribute_values,
            state="readonly",
            width=25,
        )
        attribute_picker.pack(side="left", padx=3)

        operator_var = tk.StringVar(value=str(row["operator"]))
        operator_picker = ttk.Combobox(
            line,
            textvariable=operator_var,
            state="readonly",
            width=8,
        )
        operator_picker.pack(side="left", padx=3)
        value_frame = ttk.Frame(line)
        value_frame.pack(side="left", padx=3)
        value_var = tk.StringVar()
        value_widget: ttk.Widget

        def set_value_widget(*_args: object) -> None:
            nonlocal value_widget
            current_label = attribute_var.get()
            attribute = next(
                (key for key, label in ATTRIBUTE_LABELS.items() if label == current_label),
                current_attr,
            )
            operators = ["=", "!="] if attribute not in NUMERIC_ATTRIBUTES else [
                "=", "!=", ">", "<", ">=", "<="
            ]
            operator_picker.configure(values=operators)
            if operator_var.get() not in operators:
                operator_var.set(operators[0])
            for child in value_frame.winfo_children():
                child.destroy()
            if attribute in NUMERIC_ATTRIBUTES:
                raw = str(row["value"]) if row.get("attribute") == attribute else ""
                value_var.set(raw)
                value_widget = ttk.Entry(value_frame, textvariable=value_var, width=18)
            else:
                options = sorted(ENUM_VALUES[attribute])
                labels = [VALUE_LABELS.get(value, SPACE_LABELS.get(value, value)) for value in options]
                inverse = dict(zip(labels, options))
                raw = str(row["value"]) if row.get("attribute") == attribute else options[0]
                display = VALUE_LABELS.get(raw, SPACE_LABELS.get(raw, raw))
                value_var.set(display if display in labels else labels[0])
                value_widget = ttk.Combobox(
                    value_frame,
                    textvariable=value_var,
                    values=labels,
                    state="readonly",
                    width=20,
                )
                value_widget._dsl_values = inverse  # type: ignore[attr-defined]
            value_widget.pack()
            row["attribute"] = attribute
            row["attribute_var"] = attribute_var
            row["operator_var"] = operator_var
            row["value_var"] = value_var
            row["negated_var"] = negated
            row["value_widget"] = value_widget
            row["value"] = (
                value_var.get()
                if attribute in NUMERIC_ATTRIBUTES
                else getattr(value_widget, "_dsl_values", {}).get(value_var.get(), row["value"])
            )

            def remember_value(*_value_args: object) -> None:
                if attribute in NUMERIC_ATTRIBUTES:
                    row["value"] = value_var.get()
                else:
                    choices = getattr(value_widget, "_dsl_values", {})
                    row["value"] = choices.get(value_var.get(), row["value"])

            value_var.trace_add("write", remember_value)

        def attribute_changed(_event: tk.Event[tk.Misc]) -> None:
            selected_attribute = next(
                (key for key, label in ATTRIBUTE_LABELS.items() if label == attribute_var.get()),
                current_attr,
            )
            row["attribute"] = selected_attribute
            row["value"] = (
                ""
                if selected_attribute in NUMERIC_ATTRIBUTES
                else sorted(ENUM_VALUES[selected_attribute])[0]
            )
            set_value_widget()

        attribute_picker.bind("<<ComboboxSelected>>", attribute_changed)
        row["attribute_picker"] = attribute_picker
        operator_var.trace_add("write", lambda *_args: row.update(operator=operator_var.get()))
        negated.trace_add("write", lambda *_args: row.update(negated=negated.get()))
        set_value_widget()
        ttk.Button(
            line,
            text="−",
            width=3,
            command=lambda gi=group_index, ri=row_index: self._remove_condition(gi, ri),
            style="Danger.TButton",
        ).pack(side="left", padx=(5, 0))

    def _remove_group(self, index: int) -> None:
        del self.groups[index]
        self._render_groups()

    def _remove_condition(self, group_index: int, row_index: int) -> None:
        rows = self.groups[group_index]["rows"]
        assert isinstance(rows, list)
        del rows[row_index]
        self._render_groups()

    def _read_groups(self) -> list[list[Condition]]:
        result: list[list[Condition]] = []
        for group in self.groups:
            rows = group["rows"]
            assert isinstance(rows, list)
            conditions: list[Condition] = []
            for row in rows:
                attribute_var = row.get("attribute_var")
                operator_var = row.get("operator_var")
                value_var = row.get("value_var")
                negated_var = row.get("negated_var")
                value_widget = row.get("value_widget")
                if not all(
                    (
                        isinstance(attribute_var, tk.StringVar),
                        isinstance(operator_var, tk.StringVar),
                        isinstance(value_var, tk.StringVar),
                        isinstance(negated_var, tk.BooleanVar),
                    )
                ):
                    raise ValueError("Completa cada bloque de condición antes de guardar.")
                label = attribute_var.get()
                attribute = next(
                    (key for key, display in ATTRIBUTE_LABELS.items() if display == label),
                    None,
                )
                if attribute is None:
                    raise ValueError("Selecciona una variable para cada bloque.")
                raw_value: object = value_var.get()
                if attribute in NUMERIC_ATTRIBUTES:
                    try:
                        raw_value = float(raw_value) if "." in str(raw_value) else int(str(raw_value))
                    except ValueError as exc:
                        raise ValueError(f"Escribe un número válido para «{ATTRIBUTE_LABELS[attribute]}».") from exc
                else:
                    value_map = getattr(value_widget, "_dsl_values", {})
                    if raw_value not in value_map:
                        raise ValueError("Selecciona un valor válido para cada bloque.")
                    raw_value = value_map[raw_value]
                comparison = Comparison(attribute, operator_var.get(), raw_value)  # type: ignore[arg-type]
                conditions.append(
                    Negation(comparison) if negated_var.get() else comparison
                )
            result.append(conditions)
        return result

    def _save(self) -> None:
        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("Falta el nombre", "Escribe un nombre para la regla.", parent=self.window)
            return
        if self.old_name is None:
            name = rule_slug(title)
        else:
            name = self.old_name
        space = SPACE_NAMES.get(self.space_var.get())
        if space not in SPACE_CODES:
            messagebox.showwarning("Falta el espacio", "Selecciona un espacio.", parent=self.window)
            return
        command = ACTION_NAMES.get(self.action_var.get())
        if command is None:
            messagebox.showwarning("Falta la acción", "Selecciona una acción.", parent=self.window)
            return
        equipment_choices = EQUIPMENT_BY_SPACE[space]
        equipment_code = next(
            (
                code
                for code in equipment_choices
                if EQUIPMENT_LABELS.get((space, code)) == self.equipment_var.get()
            ),
            None,
        )
        if equipment_code is None:
            messagebox.showwarning("Falta el equipo", "Selecciona un equipo objetivo.", parent=self.window)
            return
        try:
            groups = self._read_groups()
            updated = build_rule(name, space, groups, command, equipment_code)
            validate_rules(
                [
                    item
                    for item in self.manager.rules
                    if item.name != self.old_name
                ]
                + [updated]
            )
            self.on_save(updated, self.old_name)
        except (ValueError, OSError, DSLValidationError) as exc:
            messagebox.showerror("Revisa la regla", str(exc), parent=self.window)
            return
        self.window.destroy()

    def _update_scroll_region(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
