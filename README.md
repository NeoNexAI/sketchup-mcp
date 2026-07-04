# SketchUp MCP (hardened fork)

[![CI](https://github.com/NeoNexAI/sketchup-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/NeoNexAI/sketchup-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/neonexai-sketchup-mcp)](https://pypi.org/project/neonexai-sketchup-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/neonexai-sketchup-mcp)](https://pypi.org/project/neonexai-sketchup-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Connect **SketchUp** to any MCP client (Claude Desktop, Claude Code, etc.) and
drive it in natural language — create, transform and materialize geometry, run
boolean operations, chamfer/fillet edges, build woodworking joints, and export
the scene.

## Provenance

- Maintained by **[NeoNexAI Agency](https://github.com/NeoNexAI)** (AI
  consulting studio). Contact: `info@neonexai.com`.
- Hardened fork of [mhyrr/sketchup-mcp](https://github.com/mhyrr/sketchup-mcp),
  itself inspired by [blender-mcp](https://github.com/ahujasid/blender-mcp).
- **What "hardened" means:** the upstream project exposed an `eval_ruby` tool
  (arbitrary Ruby execution inside SketchUp → full disk/network access). This
  fork **removes it entirely** — Python server and Ruby extension — and the
  extension socket listens **only on `127.0.0.1`**. The tool surface is 13
  explicit, bounded tools. Audit the code yourself before installing, as you
  would with any third-party software: the diff vs upstream is public.

---

## Architecture (two pieces)

SketchUp has no external API: it can only be driven from its **embedded Ruby
API**. Hence two components working together:

```
MCP client (Claude Desktop / Claude Code)
        │  (MCP, stdio)
        ▼
  MCP server (Python, this package — uvx)
        │  (TCP socket 127.0.0.1:9876)
        ▼
  SketchUp extension (Ruby, su_mcp/)  ──►  SketchUp
```

## Requirements

- **SketchUp** 2021 or later (Windows; the Ruby extension uses only the
  standard SketchUp Ruby API).
- **Python 3.10+** and **uv/uvx** (`pip install uv` or
  `winget install astral-sh.uv`).

## Installation

### Step 1 — SketchUp extension (Ruby)

Copy `su_mcp.rb` **and** the `su_mcp/` folder from this repository into:

```
%AppData%\SketchUp\SketchUp 20XX\SketchUp\Plugins\
```

(replace `20XX` with your version). Restart SketchUp, then start the server:
menu **Extensions → SketchUp MCP → Start Server** (listens on `127.0.0.1:9876`).

Alternative: zip `su_mcp.rb` + `su_mcp/`, rename to `.rbz`, and install via
`Window → Extension Manager → Install Extension`.

### Step 2 — MCP server (Python)

Pin the version you audited (recommended — avoids silently pulling future
releases):

**Claude Desktop** — `%AppData%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sketchup": {
      "command": "uvx",
      "args": ["neonexai-sketchup-mcp==1.1.0"]
    }
  }
}
```

**Claude Code** — same block in `%UserProfile%\.claude.json`, or via CLI:

```bash
claude mcp add sketchup --scope user -- uvx neonexai-sketchup-mcp==1.1.0
```

**From GitHub instead of PyPI** (pin to a commit for reproducibility):

```json
"args": ["--from", "git+https://github.com/NeoNexAI/sketchup-mcp@main", "neonexai-sketchup-mcp"]
```

Restart the client. First call to make: `sketchup_status`.

---

## Tools (13)

| Tool | What it does |
|---|---|
| `sketchup_status` | Verify the connection (call first) |
| `sketchup_get_selection` | Ids + data of the current selection |
| `sketchup_create_component` | Create primitive (cube/cylinder/sphere/cone) |
| `sketchup_transform_component` | Move / rotate / scale by id |
| `sketchup_delete_component` | Delete by id |
| `sketchup_set_material` | Apply material/color |
| `sketchup_export_scene` | Export (skp/dae/obj/stl/png/jpg) |
| `sketchup_boolean_operation` | Union / difference / intersection of solids |
| `sketchup_chamfer_edges` | Bevel edges |
| `sketchup_fillet_edges` | Round edges |
| `sketchup_create_mortise_tenon` | Mortise & tenon joint |
| `sketchup_create_dovetail` | Dovetail joint |
| `sketchup_create_finger_joint` | Finger (box) joint |

### Example prompts

- "Create a 200×80×40 box at the origin and apply 'Wood_Cherry'."
- "Select that piece" → `sketchup_get_selection` → "move it 50 up in Z."
- "Boolean difference: subtract the cylinder (tool) from the block (target)."
- "Fillet all edges of that board with radius 1.5."
- "Export the scene to DAE."

**Units**: SketchUp models default to **inches**. Tell your assistant which
units you work in (cm/m) so it converts.

## What it does NOT do

- **No photorealistic rendering** — render plugins (V-Ray, Enscape, etc.)
  expose no scripting surface here; keep launching them from their own UI.
- **No arbitrary code execution** — by design. The 13 tools above are the
  whole surface.
- **No network access** — the extension accepts local connections only.

## Configuration (env vars)

| Variable | Default | Purpose |
|---|---|---|
| `SKETCHUP_MCP_HOST` | `127.0.0.1` | Extension host |
| `SKETCHUP_MCP_PORT` | `9876` | Extension port |
| `SKETCHUP_MCP_TIMEOUT` | `30` | Socket timeout (seconds) |

## Troubleshooting

- **"No se pudo conectar con SketchUp"** → the extension server is not
  running: `Extensions → SketchUp MCP → Start Server`.
- **Command errors** → open SketchUp's Ruby Console (`Window → Ruby Console`)
  for the detailed message.
- **Boolean operation fails** → both entities must be closed (manifold)
  solids, not open surfaces.

## License

MIT.
