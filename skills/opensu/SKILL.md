---
name: opensu
description: >-
  Architectural modeling in a live SketchUp model through the OpenSU extension
  (millimetres, bundled Python bridge scripts). Use when the user wants to build,
  reconstruct, inspect, organize, repair, or validate a building in SketchUp —
  including modeling from drawings/PDFs/images, levels, grids, spaces, walls,
  columns, beams, openings, doors/windows, curtain walls, stairs, roofs, Tags and
  materials, logical entity groups, and controlled deletion. 中文触发：SketchUp 建模、
  按图纸/PDF 建模、轴网、楼层、功能区、4S 店、幕墙、修模型、检查模型。
  Not for generic furniture/woodworking/boolean geometry through the sketchup_* MCP tools.
---

# OpenSU

Drive SketchUp only through the bundled bridge scripts — never ad-hoc socket code or arbitrary Ruby.

| Script | Purpose |
| --- | --- |
| `scripts/opensu.py` | status, inspect, validate, levels, core elements, materials |
| `scripts/opensu_advanced.py` | L/U stairs, polygon slabs/ceilings, slab/roof openings |
| `scripts/opensu_edit.py` | single-entity rename/Tag/visibility/transform/duplicate |
| `scripts/opensu_repair.py` | find, diagnose, batch repair, controlled deletion |
| `scripts/opensu_plan.py` | Plan Spec template / lint / execute |
| `scripts/opensu_multisheet.py` | cross-sheet evidence pack template / check |
| `scripts/opensu_semantics.py` | sheet index, persistent grids/spaces |
| `scripts/opensu_layout.py` | grid points, grid columns/beams, Space partitions, program strategy |
| `scripts/opensu_groups.py` | persistent logical entity groups and their hierarchy |

## Running the scripts

- Scripts live in this Skill's `scripts/` directory. Call them by absolute path and keep the
  user's project as the working directory, so drawing/JSON paths stay relative to the project:
  `python <skill-dir>/scripts/opensu.py status`. Commands below abbreviate this as `scripts/...`.
- If `python` is not found (common on Windows), use `py -3`.
- Exact flags are in `references/tool-contract.md`; when unsure, run `<script> <command> --help`
  instead of guessing.
- Every command prints JSON with `ok`. Treat `ok: false` as a failure to report, not to retry blindly.

## Always start with the live model

1. `python scripts/opensu.py status`. It confirms that OpenSU itself answers, not just that the port is open.
2. If it fails, ask the user to open SketchUp and choose `Extensions > MCP Server > Start Server`;
   if the error says the port answered but not as OpenSU, they need the OpenSU extension installed/enabled.
3. `python scripts/opensu.py inspect` before any mutation. Check existing levels, grids, spaces,
   entity groups, names, and Tags before creating anything that could duplicate them.
4. Use millimetres. Preserve existing user geometry unless the request explicitly changes it.

## Pick the workflow, then read its reference

| Situation | Read |
| --- | --- |
| Modeling from drawings, PDFs, images, or CAD exports | `references/drawing-reconstruction.md` |
| More than one sheet contributes dimensions | `references/multisheet-fusion.md` |
| Sheet index, persistent grids, Spaces / program zones | `references/sheet-grid-spaces.md` |
| Columns/beams on grids, walls from Space edges, 4S dealership programs | `references/grid-driven-layout.md` |
| Logical entity groups and parent/child group trees | `references/semantic-grouping.md` |
| Writing a Plan Spec | `references/plan-spec.schema.json`, `references/examples/` |
| Flags for core elements, edits, and repair | `references/tool-contract.md` |
| L/U stairs, polygon slabs/ceilings, slab openings | `references/advanced-geometry.md` |

Direct requests ("draw a 12 m × 8 m showroom box") can go straight to the core commands.

## Drawing-set workflow (summary)

Never model directly from visual impression:

```text
index sheets → read the real sheets → XYZ + levels + grids
→ multi-sheet pack + check (if >1 sheet contributes)
→ semantics lint → Plan Spec lint → Plan Spec execute → semantics apply
→ grid/Space-driven layout where evidenced → inspect → validate → smallest repair
```

Non-negotiables (details in the references):

- Evidence ranks printed dimensions > grid/dimension chains > explicit details > derived from exact
  > calibrated scale > pixel estimate. Pixel estimates need explicit user permission.
- Never average contradictory authoritative dimensions. Equal-strength disagreement beyond tolerance is blocking.
- Do not execute while `blocking_conflicts` or blocking uncertainties remain, unless the user explicitly
  resolves or accepts them. Do not bypass lint/execute guards just to continue.
- Filename-based sheet indexing is only a starting point. Check sheet id/kind/revision against the real pages.
- Program labels (showroom, workshop, …) guide reasoning but never create dimensions, and never imply
  fire separation, accessibility, structure, or code compliance.
- A Space is not a room and a Space edge is not a wall. Only wall the edges the drawing or user evidences.
- Grids are not permission to place structure. Columns/beams on grids need plan evidence or explicit instruction.
- Default grid convention: numbered = X, lettered = Y, `3/B` = X from `3`, Y from `B`. Follow the
  project's convention if it differs, and never switch midway.

## Modeling order

levels → grids → floors/slabs → slab/shaft openings → columns/beams → walls → wall openings
→ doors/windows → curtain walls → ceilings → stairs → roof/parapets → materials/Tags
→ Spaces → evidenced Space partitions → inspect → validate → smallest repair → inspect + validate again.

Use stable semantic names: `Level_01`, `Column_3_B_Level_01`, `Beam_1_A_5_A_Level_02`,
`Wall_South_001`, `CurtainWall_Showroom_001`, `Showroom_01`.

## Building rules

- Wall thickness is centred on the centerline. Wall direction matters, because opening offsets are directional.
- Beam endpoints are the bottom centerline and share Z.
- Create wall openings before door/window assemblies; assemblies read opening metadata, so do not guess rotation.
- Use curtain walls for continuous glazing only when the drawings show it.
- Use slab openings where stairs/shafts penetrate floors.
- Put Tags on Groups/Components, never on raw edges/faces.

## Logical entity groups (essentials)

- Groups are semantic only. They never create a native parent SketchUp Group or reparent geometry.
- Membership comes from explicit user intent, drawing evidence, or an existing group, never from proximity alone.
- `dissolve` removes only the relationship and never deletes geometry. `prune-missing` only after a stale
  member is confirmed.
- Read `references/semantic-grouping.md` before nesting, transforming, or duplicating groups.

## Editing, repair, deletion

- For existing errors: `opensu_repair.py diagnose`, then apply the smallest repair, inspect, validate, and repeat
  only for remaining issues.
- Grid/Space-driven entities record provenance. Validation reports semantic drift; never silently snap
  user geometry back.
- Delete only via `opensu_repair.py delete-confirmed`, with explicit user intent, the exact entity id, the exact
  current name, and confirmation. Never infer delete targets from partial names, and never delete loose user geometry.

## Done means

- no loose root architecture faces/edges
- no non-manifold OpenSU solids where solids are expected
- valid levels/grids/spaces, no broken layout or group references
- final `validate` returns `valid=true`. Drift warnings are reported to the user, not auto-fixed.

## Current limits

- No arbitrary Ruby execution, ever.
- Grid bubbles / room labels are not drawn. Groups are not physically nested.
- Grid layout covers points, columns, straight beams, and straight Space-edge walls. There is no automatic
  framing of a whole grid range.
- Stairs: straight, L, U only. Polygon slabs/ceilings may be concave but not self-intersecting.
- No pitched roofs or curved walls.
- If a request exceeds the tool surface, say what is missing instead of pretending it was modeled.
