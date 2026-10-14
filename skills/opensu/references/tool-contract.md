# OpenSU command contract

The Skill bridge talks directly to the local SketchUp extension on `127.0.0.1:9876`.
All architectural dimensions are millimetres.

## Session / model QA

```text
python scripts/opensu.py status
python scripts/opensu.py inspect [--max-entities 200]
python scripts/opensu.py validate [--max-entities 1000]
```

`status` connects to the extension and runs a one-entity `inspect_model`, so it fails
when the port belongs to another program or an extension without the OpenSU tools.

`inspect` returns top-level groups/components (`truncated` / `total_inspectable_entities`
tell you if the list was cut off; the maximum is 1000) plus model-level `levels`,
`grids`, `spaces`, `entity_groups`, and a semantic summary. Always inspect before edits
and validate before completion.

Commands that accept `--name` / `--wall-name` resolve the name to an entity id by exact
match and refuse ambiguous names. On very large models, prefer the explicit `--*-id` flag.

## Levels

```text
python scripts/opensu.py define-level \
  --name Level_01 --elevation 0 --floor-to-floor 4500

python scripts/opensu.py define-level \
  --name Level_02 --elevation 4500 --floor-to-floor 4500
```

Level names and elevations must be unique. Levels are model metadata, not geometry.

## Floor / ceiling

```text
python scripts/opensu.py create-floor \
  --width 12000 --depth 8000 --thickness 150 \
  --origin 0 0 0 --name Floor_Level01_001

python scripts/opensu.py create-ceiling \
  --width 12000 --depth 8000 --thickness 100 \
  --origin 0 0 3900 --level-name Level_01 \
  --name Ceiling_Level01_001
```

The ceiling origin is its lower face.

## Column / beam / wall

```text
python scripts/opensu.py create-column \
  --center 1000 1000 150 --width 400 --depth 400 --height 4200 \
  --name Column_A01_001

python scripts/opensu.py create-beam \
  --start 1000 1000 3850 --end 7000 1000 3850 \
  --width 300 --height 500 --name Beam_A01_B01_001

python scripts/opensu.py create-wall \
  --start 0 0 150 --end 12000 0 150 \
  --height 4200 --thickness 200 --name Wall_Showroom_001
```

Beam start/end define its bottom centerline and must use the same Z. Wall thickness is
centered on the supplied wall centerline.

## Multiple openings on one wall

Call `create-opening` repeatedly against the same wall. The extension regenerates a
closed wall shell from the complete opening set.

```text
python scripts/opensu.py create-opening \
  --wall-name Wall_Showroom_001 \
  --offset 800 --width 1000 --height 2200 --sill 0 \
  --type door --name DoorOpening_001

python scripts/opensu.py create-opening \
  --wall-name Wall_Showroom_001 \
  --offset 2600 --width 1800 --height 1800 --sill 700 \
  --type window --name WindowOpening_001
```

Openings must remain inside the wall, may not overlap, and need unique names. For walls
with multiple openings, always pass `--opening-name` to door/window assembly creation.

## Door / window assemblies

```text
python scripts/opensu.py create-door \
  --wall-name Wall_Showroom_001 --opening-name DoorOpening_001 \
  --frame-width 60 --leaf-depth 40 --gap 5 --name Door_001

python scripts/opensu.py create-window \
  --wall-name Wall_Showroom_001 --opening-name WindowOpening_001 \
  --frame-width 60 --glass-thickness 8 --gap 5 --name Window_001
```

## Glass curtain wall / storefront

```text
python scripts/opensu.py create-curtain-wall \
  --start 0 0 150 --end 12000 0 150 \
  --height 4200 --panel-width 1500 --row-height 2100 \
  --mullion-width 60 --mullion-depth 120 \
  --glass-thickness 10 --gap 8 \
  --frame-color "#363A3D" --glass-color "#9CC9E8" --glass-opacity 0.35 \
  --name CurtainWall_Showroom_001
```

Use curtain walls for large glazed dealership/showroom facades. Use ordinary openings
for punched windows in opaque walls.

## Straight stair

```text
python scripts/opensu.py create-stair \
  --start 2000 2000 150 --end 6500 2000 4500 \
  --width 1400 --target-riser-height 165 \
  --level-name Level_01 --name Stair_L01_L02_001
```

The stair runs in a straight line from start to end. End Z must be above start Z. If
`--riser-count` is omitted, the extension calculates it from the requested target riser
height. The resulting actual riser height must be 80-220 mm and tread depth at least
150 mm.

## Flat roof + parapets

```text
python scripts/opensu.py create-flat-roof \
  --origin 0 0 9000 --width 12000 --depth 8000 \
  --slab-thickness 180 --parapet-height 900 --parapet-thickness 150 \
  --level-name Roof --name Roof_Main_001
```

This creates one roof assembly containing a closed slab plus four closed parapet solids.
Set `--parapet-height 0` to create the slab without parapets.

## Materials

```text
python scripts/opensu.py apply-material \
  --name Column_A01_001 --material-name Concrete \
  --color "#B8B8B8" --opacity 1.0
```

Opacity ranges from `0` to `1`. Material application is recursive by default.

## Validation expectations

`validate` checks, among other things:
- root loose geometry and duplicate architecture names;
- level metadata uniqueness and valid elevations;
- manifold solids for floors, walls, columns, beams, ceilings, stair steps, roof slabs,
  and parapets;
- wall-opening non-overlap and door/window linkage;
- curtain-wall size/grid metadata and glass panel presence;
- level references used by ceilings, stairs, and roofs.

Treat `valid: false` as incomplete work.

## Single-entity edits (`opensu_edit.py`)

Target with `--entity-id <id>` or `--name <exact name>`.

```text
python scripts/opensu_edit.py rename --name Wall_001 --new-name Wall_South_001
python scripts/opensu_edit.py set-tag --name Wall_South_001 --tag A-WALL
python scripts/opensu_edit.py set-visible --name Wall_South_001 --hide
python scripts/opensu_edit.py transform --name Column_3_B_Level_01 \
  --translation 0 600 0 [--rotate-z 90] [--pivot X Y Z]
python scripts/opensu_edit.py duplicate --name Column_3_B_Level_01 \
  --new-name Column_4_B_Level_01 --translation 8000 0 0
```

## Find, diagnose, batch repair, deletion (`opensu_repair.py`)

```text
python scripts/opensu_repair.py find [--name-contains Wall] [--type wall] [--tag A-WALL] \
  [--visible | --hidden] [--limit 200]
python scripts/opensu_repair.py diagnose [--max-entities 1000]
python scripts/opensu_repair.py batch-tag --id 101 --id 102 --tag A-WALL
python scripts/opensu_repair.py batch-visible --id 101 --id 102 --show
python scripts/opensu_repair.py batch-transform --id 101 --id 102 --translation 0 500 0 [--rotate-z 90]
python scripts/opensu_repair.py delete-confirmed --entity-id 101 \
  --confirm-name Wall_Temp_001 --confirm-delete
```

Batch commands take repeated `--id` flags and run as one undoable operation.
`delete-confirmed` requires the id, the exact current name, and `--confirm-delete`.

## Drawing pipeline (`opensu_semantics.py`, `opensu_multisheet.py`, `opensu_plan.py`)

```text
python scripts/opensu_semantics.py index-sheets <drawing-folder> [--output sheet-index.json]
python scripts/opensu_semantics.py template | lint <semantics.json> | apply <semantics.json>
python scripts/opensu_multisheet.py template | check <multisheet-pack.json>
python scripts/opensu_plan.py template [--output plan.json]
python scripts/opensu_plan.py lint <plan.json>
python scripts/opensu_plan.py execute <plan.json>
```

`execute` also has `--allow-blocking-uncertainties` and `--allow-existing-names`. Use them
only after the user explicitly accepts the uncertainty or the name reuse.

## Grid / Space layout (`opensu_layout.py`)

```text
python scripts/opensu_layout.py grid-point --at 3/B [--level Level_01] [--z-offset 0]
python scripts/opensu_layout.py grid-column --at 3/B --level Level_01 \
  [--width 500] [--depth 500] [--height 4500] [--base-offset 0] [--name ...]
python scripts/opensu_layout.py grid-beam --from 1/A --to 5/A --level Level_02 \
  [--width 300] [--height 600] [--bottom-offset -600] [--name ...]
python scripts/opensu_layout.py space-walls --space Office_01 \
  [--edges 1 2] [--thickness 100] [--height ...] [--base-offset 0] [--name-prefix ...]
python scripts/opensu_layout.py space-strategy --space Showroom_01
```

See `grid-driven-layout.md` for when these may be used.

## Logical entity groups (`opensu_groups.py`)

Members are given with repeated `--id <entity id>` and/or `--name <exact name>`.

```text
python scripts/opensu_groups.py list | roots
python scripts/opensu_groups.py inspect --group Showroom_Structure
python scripts/opensu_groups.py tree --group Level_01 [--max-depth N]
python scripts/opensu_groups.py create --group Showroom_Structure --name Wall_001 --name Column_1_A \
  [--child-group Columns] [--description ...] [--source-ref ...]
python scripts/opensu_groups.py add | remove --group Showroom_Structure --name Beam_1_A_3_A
python scripts/opensu_groups.py nest | unnest --parent Structure --child Columns
python scripts/opensu_groups.py move --group Columns (--parent Level_02 | --to-root)
python scripts/opensu_groups.py prune-missing --group Showroom_Structure
python scripts/opensu_groups.py rename --group Showroom_Structure --new-name Showroom_Main_Structure
python scripts/opensu_groups.py visible --group Showroom_Main_Structure (--show | --hide)
python scripts/opensu_groups.py tag --group Showroom_Main_Structure --tag A-SHOWROOM
python scripts/opensu_groups.py transform --group Showroom_Main_Structure \
  --translation 1000 0 0 [--rotate-z 90] [--pivot X Y Z]
python scripts/opensu_groups.py duplicate --group Showroom_Main_Structure \
  --new-group Showroom_Copy --translation 18000 0 0
python scripts/opensu_groups.py dissolve --group Showroom_Copy
```

See `semantic-grouping.md` for hierarchy and safety semantics.

## Current limitations

- Straight horizontal-plan walls, beams, and curtain walls only.
- Rectangular vertical columns only.
- Rectangular wall openings only.
- Stairs: straight here; L/U stairs with one landing in `advanced-geometry.md`.
  No spiral or multi-landing stairs.
- Rectangular ceilings/flat roofs here; polygon slabs/ceilings in `advanced-geometry.md`.
- No pitched roofs or curved walls yet.
- Never fall back to arbitrary Ruby execution.
