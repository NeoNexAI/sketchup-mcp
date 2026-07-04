# Security

## Security model

This project is a **hardened fork** of [mhyrr/sketchup-mcp](https://github.com/mhyrr/sketchup-mcp). The upstream project exposes an `eval_ruby` tool that lets the connected MCP client execute **arbitrary Ruby code inside SketchUp** — which, on the desktop Ruby API, means arbitrary file system and network access on the machine running SketchUp.

This fork removes that capability entirely, on both sides:

- **Python server** (`src/sketchup_mcp/server.py`): no `eval_ruby` tool exists. The 13 tools exposed are explicit, bounded functions (create/transform/delete a component, apply a material, boolean operations, chamfer/fillet edges, woodworking joints, export). There is no code-execution primitive.
- **Ruby extension** (`su_mcp/su_mcp/main.rb`): the `eval_ruby` handler and its dispatch entry have been deleted, not merely hidden behind a flag.
- **Network exposure**: the extension's TCP socket binds to `127.0.0.1` only. It does not accept connections from other machines.

If you diff this repository against upstream, that is the diff that matters.

## Supported versions

Only the latest published version on [PyPI](https://pypi.org/project/neonexai-sketchup-mcp/) receives fixes. Pin your installs to a specific version (e.g. `neonexai-sketchup-mcp==1.1.0`) rather than tracking `@latest`, so an upgrade is a deliberate, reviewed action rather than something that happens silently on your next restart.

## Reporting a vulnerability

Please report suspected vulnerabilities privately rather than opening a public issue:

- **Email**: [info@neonexai.com](mailto:info@neonexai.com)
- Or use GitHub's [private vulnerability reporting](https://github.com/NeoNexAI/sketchup-mcp/security/advisories/new) for this repository.

Include what you found, the affected version, and — if possible — a minimal way to reproduce it. We aim to acknowledge reports within a few business days.

## What's out of scope

- SketchUp itself, or vulnerabilities in Trimble's own Ruby API.
- The behavior of arbitrary third-party extensions installed alongside this one.
- Reports that require the attacker to already have code execution on the machine running SketchUp (at that point the SketchUp process is not the security boundary).
