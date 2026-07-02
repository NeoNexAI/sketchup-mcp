---
name: sketchup-usage
description: >-
  Guía para manejar bien el MCP de SketchUp (fork endurecido NeoNexAI). Úsala SIEMPRE
  que el trabajo implique SketchUp o cualquier tool de geometría 3D del servidor
  `sketchup` — crear/transformar/borrar componentes, materiales, operaciones booleanas,
  chaflán/redondeo de aristas, ensambles de carpintería o exportar la escena. Explica
  el flujo por ID, qué hace cada herramienta, cómo encadenarlas, y qué NO puede hacer
  (render fotorealista, código Ruby arbitrario). Aunque el usuario no nombre "SketchUp",
  si pide modelar/editar geometría 3D y el MCP está disponible, aplícala.
---

# SketchUp — cómo usar el MCP bien

Fork endurecido de `mhyrr/sketchup-mcp`: **sin `eval_ruby`** (no hay ejecución de código
arbitrario) y socket **solo en `127.0.0.1`**. Se opera con 12 herramientas acotadas.

## Antes de nada: dos piezas deben estar vivas

1. **SketchUp abierto** con la extensión "SketchUp MCP (NeoNexAI)" y su servidor
   arrancado (menú `Extensiones → SketchUp MCP → Start Server`, puerto `9876`).
2. El **servidor MCP Python** (lo arranca Claude vía `uvx neonexai-sketchup-mcp`).

Si una operación devuelve "Could not connect to SketchUp" → la extensión no está
arrancada o SketchUp no está abierto. Es el fallo nº1.

## El modelo mental: todo va por `entityID`

SketchUp identifica cada componente/grupo por un **ID entero**. El flujo natural es:

1. **Crear** geometría (`create_component`) o **leer selección** (`get_selection`).
2. Quedarte con el **ID** que devuelve.
3. **Operar por ID**: `transform_component`, `set_material`, booleanas, aristas,
   ensambles — todas reciben el ID de la(s) pieza(s).
4. **Exportar** (`export_scene`).

Si no tienes el ID de una pieza, pídele al usuario que la seleccione en SketchUp y usa
`get_selection` para recuperarlo.

## Herramientas

**Geometría base**
- `create_component(type, position=[x,y,z], dimensions=[w,h,d])` — crea (cubo/caja).
  Unidades = las del modelo (por defecto pulgadas en SketchUp; confirma con el usuario
  si trabaja en cm/m y convierte).
- `transform_component(id, position?, rotation?, scale?)` — mover/rotar/escalar. Rotación
  en grados [x,y,z].
- `delete_component(id)`.
- `get_selection()` — IDs y datos de lo seleccionado.

**Materiales**
- `set_material(id, material)` — nombre de material del modelo o color.

**Sólidos**
- `boolean_operation(operation, target_id, tool_id, delete_originals=false)` —
  `operation` ∈ `"union" | "difference" | "intersection"`. En diferencia, `target` es
  la pieza que se conserva y `tool` la que resta. **Requiere sólidos cerrados** (grupos/
  componentes manifold), no superficies sueltas.
- `chamfer_edges(entity_id, distance, edge_indices?, delete_original=true)` — chaflán.
- `fillet_edges(entity_id, radius, segments=8, edge_indices?, delete_original=true)` —
  redondeo. `segments` = suavidad. Sin `edge_indices` aplica a todas las aristas.

**Ensambles de carpintería** (mueble/interiorismo)
- `create_mortise_tenon(mortise_id, tenon_id, width, height, depth, offset_x/y/z)`.
- `create_dovetail(tail_id, pin_id, width, height, depth, angle=15, num_tails=3, ...)`.
- `create_finger_joint(board1_id, board2_id, width, height, depth, num_fingers=5, ...)`.

**Exportar**
- `export_scene(format="skp")` — `skp`, `dae`, `obj`… según lo que soporte la versión.

## Patrones frecuentes

- **Montar un mueble paramétrico:** crea las piezas con `create_component` → colócalas con
  `transform_component` → une o ensambla (booleana / mortise-tenon / dovetail) → materializa
  → exporta.
- **Editar algo que ya modeló el usuario:** pídele que lo seleccione → `get_selection` →
  opera por ID.
- **Redondear/biselar cantos:** localiza el ID → `fillet_edges`/`chamfer_edges`. Si solo
  quiere unas aristas, pásale `edge_indices`.

## Con cabeza

- Operaciones que **borran** (`delete_component`, `delete_originals=true`,
  `delete_original=true`) modifican el modelo del cliente. Antes de un cambio masivo o
  destructivo, resume qué vas a hacer y confirma. Recuerda al usuario que SketchUp tiene
  Ctrl+Z.
- Las **unidades** son la fuente de error nº2: aclara si trabaja en cm/m/pulgadas y convierte.
- Encadena varios pasos en una tanda; verifica con `get_selection` si dudas del estado.

## Qué NO hace (dilo claro)

- **No renderiza fotorealista** (Veras, V-Ray, Enscape). Sin API scriptable — el render se
  lanza desde su plugin, no desde aquí. El MCP construye/edita geometría.
- **No ejecuta Ruby arbitrario** (a propósito). Si algo no cubre la superficie de 12 tools,
  dilo — no hay vía "libre" en este fork por diseño de seguridad.

## ¿Presupuestos / planos 2D?

Esto es 3D en SketchUp. Para presupuestos usa el MCP de **Presto**; para planos DWG 2D,
**BricsCAD/multiCAD**. No mezcles.
