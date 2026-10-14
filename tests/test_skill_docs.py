"""Keep the opensu Skill documentation in sync with its bridge scripts."""

import argparse
import contextlib
import importlib
import re
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "opensu"
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import opensu  # noqa: E402

COMMAND_RE = re.compile(r"python scripts/(\w+)\.py ([a-z][a-z-]*)")
REFERENCE_RE = re.compile(r"`(references/[\w./-]+)`")


def _doc_files():
    return [SKILL_DIR / "SKILL.md", *sorted((SKILL_DIR / "references").glob("*.md"))]


def _subcommands(module_name):
    parser = importlib.import_module(module_name).build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    return set()


def test_documented_commands_exist():
    missing = []
    for doc in _doc_files():
        for script, command in COMMAND_RE.findall(doc.read_text(encoding="utf-8")):
            if not (SCRIPTS_DIR / f"{script}.py").is_file():
                missing.append(f"{doc.name}: scripts/{script}.py")
            elif command not in _subcommands(script):
                missing.append(f"{doc.name}: {script}.py {command}")
    assert not missing, "Docs reference unknown scripts/commands: " + ", ".join(sorted(set(missing)))


def test_skill_reference_paths_exist():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    missing = [path for path in REFERENCE_RE.findall(text) if not (SKILL_DIR / path).exists()]
    assert not missing, f"SKILL.md references missing files: {missing}"


def _fake_send(responses, calls):
    def send(command, arguments):
        calls.append((command, arguments))
        return responses[command]

    return send


def test_find_entity_id_uses_server_side_filter(monkeypatch):
    calls = []
    monkeypatch.setattr(opensu, "_send", _fake_send({
        "find_entities": {"entities": [
            {"entity_id": 7, "name": "Wall_South_0010", "opensu_type": "wall"},
            {"entity_id": 8, "name": "Wall_South_001", "opensu_type": "wall"},
        ]},
    }, calls))

    assert opensu._find_entity_id("Wall_South_001", "wall") == 8
    assert calls == [("find_entities", {"name_contains": "Wall_South_001", "limit": 1000, "opensu_type": "wall"})]


def test_find_entity_id_falls_back_to_inspect(monkeypatch):
    calls = []
    monkeypatch.setattr(opensu, "_send", _fake_send({
        "find_entities": {"entities": []},
        "inspect_model": {"entities": [{"entity_id": 3, "name": "Chair"}], "truncated": False},
    }, calls))

    assert opensu._find_entity_id("Chair") == 3
    assert [name for name, _ in calls] == ["find_entities", "inspect_model"]


def test_find_entity_id_reports_truncated_model(monkeypatch):
    monkeypatch.setattr(opensu, "_send", _fake_send({
        "find_entities": {"entities": []},
        "inspect_model": {"entities": [], "truncated": True},
    }, []))

    with pytest.raises(opensu.OpenSUError, match="more than 1000"):
        opensu._find_entity_id("Missing")


def test_find_entity_id_rejects_ambiguous_names(monkeypatch):
    monkeypatch.setattr(opensu, "_send", _fake_send({
        "find_entities": {"entities": [
            {"entity_id": 1, "name": "Column_A"},
            {"entity_id": 2, "name": "Column_A"},
        ]},
    }, []))

    with pytest.raises(opensu.OpenSUError, match="More than one"):
        opensu._find_entity_id("Column_A")


def test_status_requires_opensu_tools(monkeypatch):
    monkeypatch.setattr(opensu.socket, "create_connection", lambda *a, **k: contextlib.nullcontext())

    def send(command, arguments):
        raise opensu.OpenSUError("Unknown tool: inspect_model")

    monkeypatch.setattr(opensu, "_send", send)
    with pytest.raises(opensu.OpenSUError, match="did not answer as OpenSU"):
        opensu._status()

    monkeypatch.setattr(opensu, "_send", lambda c, a: {"model": {"title": "Demo"}, "total_inspectable_entities": 4})
    result = opensu._status()
    assert result["ok"] is True
    assert result["model_title"] == "Demo"
    assert result["total_inspectable_entities"] == 4
