# CampusEnergyDSL

Prototipo ejecutable de un lenguaje específico de dominio para expresar y simular
políticas de ahorro energético en un campus universitario. Incluye las diez reglas
del informe, validación estática, evaluación semántica con salvaguardas y generación
de artefactos `DecisionPlan` en JSON.

> **Modo seguro:** esta versión es una demostración. No se conecta a sensores,
> APIs ni actuadores y no puede apagar equipos reales.

## Requisitos

- Python 3.10 o posterior.
- Tkinter para abrir la interfaz gráfica (normalmente incluido con Python para Windows).

## Ejecutar en Windows

Abre PowerShell en la carpeta del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

La ventana presenta primero **Crear**, después **Reglas** y al final
**Demostración**:

- **Crear:** elige un espacio, las entradas/activadores disponibles, sus condiciones
  y la acción objetivo. Las condiciones aparecen en bloques verdes, los operadores
  Y/O en separadores grises y las fuentes de datos en bloques azules. Al seleccionar
  ocupación **Vacía**, aparece el campo requerido para indicar la duración en
  **segundos**. Un indicador valida la regla y sus restricciones de seguridad
  mientras la editas; **Guardar regla** solo se habilita si es válida.
- **Reglas:** consulta y busca las reglas guardadas, sus activadores, condiciones
  y acciones; también permite editarlas o probarlas con un escenario compatible.
- **Demostración:** muestra la política como bloques, ejecuta el escenario y
  presenta el resultado. El artefacto JSON se abre aparte cuando se solicita.

El catálogo sigue guardándose como `reglas_campus.dsl` y pasa por el parser y el
validador existentes. Las variables aparecen con nombres legibles; `tiempoVacio`
se expresa en segundos (por ejemplo, 900 segundos equivalen a 15 minutos).

Si PowerShell impide activar el entorno virtual, también puedes ejecutar los
comandos con el intérprete del entorno directamente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Ejecución por terminal

```powershell
python main.py --list-scenarios
python main.py --scenario ahorroBasico
python main.py --all
python -m pytest
```

Los planes JSON se guardan en `artifacts/` (carpeta creada al ejecutar). Para
elegir una ruta de salida en una ejecución individual:

```powershell
python main.py --scenario revisionLaboratorio --output artifacts\laboratorio.json
```

## Pipeline

```text
reglas_campus.dsl
    -> grammar.lark
    -> parser.py / astNodes.py
    -> validator.py
    -> interpreter.py
    -> decision.py
    -> generator.py
    -> artefacto JSON
```

- `grammar.lark`: gramática Lark para reglas `REGLA`, condiciones, operadores,
  comentarios y comandos.
- `astNodes.py`: nodos inmutables del AST.
- `parser.py`: análisis sintáctico y construcción del AST.
- `validator.py`: catálogo cerrado, tipos, valores permitidos, coherencia del
  equipo y controles estáticos de seguridad.
- `interpreter.py`: evaluación con cortocircuito.
- `decision.py`: salvaguardas y resolución `PERMITIDA`, `BLOQUEADA` o
  `REQUIERE AUTORIZACION`.
- `generator.py`: serialización del plan con contexto y evidencia.
- `main.py`: interfaz gráfica y opciones de terminal.
- `rule_editor.py`: editor visual de políticas, consulta del catálogo y persistencia
  de reglas creadas desde la interfaz.
- `escenarios.json`: diez contextos de demostración reproducibles.
- `tests/testPipeline.py`: pruebas del pipeline y escenarios de seguridad.

## Atributos del lenguaje

Las reglas pueden consultar los nueve atributos del dominio:

| Atributo | Tipo y valores |
| --- | --- |
| `codEspacio` | `AULA302`, `PASILLOB1`, `LABFISICA`, `LABQUIMICA`, `DATACENTER01` |
| `ocupacion` | `VACIO`, `OCUPADO` |
| `tiempoVacio` | Duración en segundos, entero mayor o igual a cero |
| `actividadActual` | `NINGUNA`, `CLASE`, `EXPERIMENTO` |
| `criticidad` | `BAJA`, `MEDIA`, `ALTA`, `EXTREMA` |
| `frescura` | `ACTUALIZADO`, `OBSOLETO`, `DESCONECTADO` |
| `bloqueTarifa` | `VALLE`, `MEDIA`, `PUNTA` |
| `demandaNeta` | Número mayor o igual a cero |
| `eventoProveedor` | `NORMAL`, `REDUCCION` |

Ejemplo:

```text
REGLA ahorroBasico:
CUANDO codEspacio = "AULA302"
Y ocupacion = "VACIO"
Y tiempoVacio >= 900
Y actividadActual = "NINGUNA"
Y criticidad = "BAJA"
Y frescura = "ACTUALIZADO"
ENTONCES apagar(AULA302.AIRE02);
```

Las reglas solo pueden usar equipos registrados para su espacio. Cortes con
criticidad extrema o telemetría insegura se rechazan o bloquean; laboratorios
restringidos requieren autorización humana con vigencia de quince minutos.
Las restricciones del equipo son metadatos internos del contexto, no atributos
que el autor de las reglas pueda modificar.

## Salida JSON

Cada ejecución coincidente produce un objeto `contextoEntrada` y un `planDecision`
con regla aplicada, resolución, acción propuesta, equipo objetivo, requisito de
autorización y evidencias evaluadas. Los casos sin coincidencia no producen una
orden.
