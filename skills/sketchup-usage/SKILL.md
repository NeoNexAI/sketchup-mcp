---
name: sketchup-usage
description: >-
  Guide for working well with the SketchUp MCP server (sketchup_* tools):
  creating/transforming/deleting components, materials, boolean operations,
  edge chamfer/fillet, woodworking joints and scene export. Use it when the
  user asks to model or edit 3D geometry in SketchUp through this MCP.
---

# SketchUp MCP — usage guide

This server exposes a curated set of 13 tools over a local socket to a
companion SketchUp extension. It intentionally has **no arbitrary code
execution** — if something is not covered by the tools below, say so instead
of trying workarounds.

## Before anything: two pieces must be alive

1. **SketchUp open** with the "SketchUp MCP" extension server started
   (menu `Extensions → SketchUp MCP → Start Server`, port `9876`).
2. The MCP server itself (the client launches it via `uvx`).

Start every session with **`sketchup_status`**. If it fails, the extension is
not running — tell the user how to start it (step 1 above).

## The mental model: everything works by entity id

1. **Create** geometry (`sketchup_create_component`) or **read the selection**
   (`sketchup_get_selection`) — both return entity **ids**.
2. **Operate by id**: transform, material, booleans, edges, joints.
3. **Export** (`sketchup_export_scene`).

If you don't have the id of a piece, ask the user to select it in SketchUp
and call `sketchup_get_selection`.

## Tools

**Inspection**: `sketchup_status` · `sketchup_get_selection`

**Geometry**: `sketchup_create_component` (cube/cylinder/sphere/cone, position,
dimensions) · `sketchup_transform_component` (position/rotation°/scale) ·
`sketchup_delete_component` · `sketchup_set_material`

**Solids**: `sketchup_boolean_operation` (union | difference | intersection;
requires CLOSED solids; `difference` keeps target minus tool) ·
`sketchup_chamfer_edges` · `sketchup_fillet_edges` (optional `edge_indices`,
omit for all edges)

**Woodworking joints**: `sketchup_create_mortise_tenon` ·
`sketchup_create_dovetail` · `sketchup_create_finger_joint`

**Export**: `sketchup_export_scene` (skp/dae/obj/stl/png/jpg — availability
depends on the SketchUp edition)

## Working carefully

- **Units are the #1 source of errors**: SketchUp defaults to inches. Ask the
  user what units they work in (cm/m/inches) and convert before calling.
- Destructive operations (`delete_component`, `delete_originals=true`,
  `delete_original=true`) modify the user's model. Summarize what you are
  about to do before bulk or destructive changes. Remind them Ctrl+Z undoes.
- Boolean operations need **manifold (closed) solids** — loose surfaces fail.
- Chain steps in one pass; verify state with `sketchup_get_selection` if in doubt.

## What this MCP does NOT do (say it clearly)

- **No photorealistic rendering** (V-Ray, Enscape and similar render plugins
  have no scripting surface here). This MCP builds and edits geometry; the
  render is launched from its own plugin.
- **No arbitrary Ruby execution** — by design, for security. The 13 tools
  above are the whole surface.
