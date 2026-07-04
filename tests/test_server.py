"""Tests del servidor MCP que no requieren SketchUp ni una extension viva.

Cubren la propiedad de seguridad central de este fork (ver SECURITY.md): que
no existe ninguna via de ejecucion de codigo arbitrario. Si una futura edicion
la reintroduce por accidente, este test la detiene en CI antes de publicar.
"""

from pathlib import Path

from sketchup_mcp import server

SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "sketchup_mcp"

EXPECTED_TOOLS = {
    "sketchup_status",
    "sketchup_get_selection",
    "sketchup_create_component",
    "sketchup_transform_component",
    "sketchup_delete_component",
    "sketchup_set_material",
    "sketchup_export_scene",
    "sketchup_boolean_operation",
    "sketchup_chamfer_edges",
    "sketchup_fillet_edges",
    "sketchup_create_mortise_tenon",
    "sketchup_create_dovetail",
    "sketchup_create_finger_joint",
}

# Construido por concatenacion a proposito: la ejecucion de codigo arbitrario
# es justo la propiedad que este fork elimina, y queremos comprobar su
# AUSENCIA en el texto fuente sin que el propio test parezca invocarla.
_CODE_EXEC_TOKEN = "ev" + "al" + "_ruby"
_RUBY_EXEC_TOKEN = "ev" + "al" + "("


def _registered_tool_names() -> set[str]:
    return set(server.mcp._tool_manager._tools.keys())


def test_expone_exactamente_las_13_tools_prefijadas():
    assert _registered_tool_names() == EXPECTED_TOOLS


def test_todas_las_tools_llevan_el_prefijo_sketchup():
    assert all(name.startswith("sketchup_") for name in _registered_tool_names())


def test_eval_ruby_no_esta_registrado_como_tool():
    # Propiedad de seguridad central del fork (ver SECURITY.md).
    assert _CODE_EXEC_TOKEN not in _registered_tool_names()
    assert not hasattr(server, _CODE_EXEC_TOKEN)


def test_codigo_fuente_python_no_contiene_eval_ruby():
    # Cinturon y tirantes: ni siquiera como funcion sin registrar.
    for path in SRC_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert _CODE_EXEC_TOKEN not in text, f"'{_CODE_EXEC_TOKEN}' reaparecio en {path}"


def test_conexion_falla_con_error_accionable_sin_sketchup():
    import json

    result = json.loads(server.sketchup_status())
    assert result["ok"] is False
    assert "Start Server" in result["error"]


def test_extension_ruby_no_contiene_ejecucion_de_codigo():
    # Cubre tambien el lado Ruby (su_mcp/su_mcp/main.rb): sin eval(...).
    ruby_main = SRC_DIR.parent.parent / "su_mcp" / "su_mcp" / "main.rb"
    text = ruby_main.read_text(encoding="utf-8")
    assert _RUBY_EXEC_TOKEN not in text, "la ejecucion de codigo reaparecio en la extension Ruby"
