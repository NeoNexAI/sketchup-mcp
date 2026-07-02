#!/usr/bin/env python3
"""MCP server for SketchUp.

Bridges an MCP client (e.g. Claude) with SketchUp through a local TCP socket
served by the companion SketchUp Ruby extension (see ``su_mcp/`` in this
repository). The extension listens on ``127.0.0.1:9876`` and executes a
curated set of geometry commands inside SketchUp.

Security model: this fork intentionally exposes NO arbitrary code execution.
Every tool maps to an explicit, bounded handler in the Ruby extension, and
the socket only accepts connections from the local machine.

Transport: stdio (local, one instance per desktop).
"""

from __future__ import annotations

import json
import logging
import os
import socket
from typing import Annotated, Any, Literal, Optional

from pydantic import Field
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sketchup_mcp")

__version__ = "1.1.0"

# Connection defaults — overridable for non-standard setups.
SKETCHUP_HOST = os.environ.get("SKETCHUP_MCP_HOST", "127.0.0.1")
SKETCHUP_PORT = int(os.environ.get("SKETCHUP_MCP_PORT", "9876"))
SOCKET_TIMEOUT_S = float(os.environ.get("SKETCHUP_MCP_TIMEOUT", "30"))

CONNECT_HELP = (
    "No se pudo conectar con SketchUp. Comprueba: (1) SketchUp esta abierto; "
    "(2) la extension 'SketchUp MCP' esta instalada; (3) el servidor esta "
    "arrancado: menu Extensiones > SketchUp MCP > Start Server (puerto "
    f"{SKETCHUP_PORT}). Reintenta despues."
)

mcp = FastMCP(
    "sketchup_mcp",
    instructions=(
        "SketchUp integration via a curated tool surface (create/transform/"
        "delete components, materials, boolean ops, edge chamfer/fillet, "
        "woodworking joints, scene export). Requires SketchUp running with "
        "the companion extension started. Arbitrary code execution is "
        "intentionally NOT exposed. Call sketchup_status first to verify the "
        "connection. All geometry uses the model's units (SketchUp defaults "
        "to inches)."
    ),
)


# --------------------------------------------------------------------------- #
# Socket client to the SketchUp extension
# --------------------------------------------------------------------------- #
class SketchupConnection:
    """Persistent client for the extension's local JSON-RPC socket."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self._request_id = 0

    def _connect(self) -> None:
        if self.sock is not None:
            return
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=SOCKET_TIMEOUT_S)
        except OSError as exc:
            self.sock = None
            raise ConnectionError(CONNECT_HELP) from exc

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def _receive_json(self) -> dict[str, Any]:
        """Read until a complete JSON document arrives (responses may chunk)."""
        assert self.sock is not None
        chunks: list[bytes] = []
        self.sock.settimeout(SOCKET_TIMEOUT_S)
        while True:
            chunk = self.sock.recv(8192)
            if not chunk:
                raise ConnectionError("SketchUp cerro la conexion antes de responder.")
            chunks.append(chunk)
            try:
                return json.loads(b"".join(chunks).decode("utf-8"))
            except json.JSONDecodeError:
                continue  # incomplete — keep reading

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke a named command in the extension; one retry on dead socket."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
            "id": self._next_id(),
        }
        payload = json.dumps(request).encode("utf-8") + b"\n"

        for attempt in (1, 2):
            self._connect()
            assert self.sock is not None
            try:
                self.sock.sendall(payload)
                response = self._receive_json()
                break
            except (socket.timeout, ConnectionError, OSError) as exc:
                self.close()
                if attempt == 2:
                    raise ConnectionError(CONNECT_HELP) from exc
                logger.info("Conexion caida, reintentando (%s)", exc)

        if isinstance(response, dict) and "error" in response:
            message = response["error"].get("message", "Error desconocido de SketchUp")
            raise RuntimeError(
                f"SketchUp devolvio un error: {message}. Revisa la Ruby Console "
                "de SketchUp (Ventana > Ruby Console) para el detalle."
            )
        return response.get("result", {}) if isinstance(response, dict) else {}

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id


_conn = SketchupConnection(SKETCHUP_HOST, SKETCHUP_PORT)


def _call(name: str, arguments: dict[str, Any]) -> str:
    """Shared tool body: call the extension and normalize the response/errors."""
    try:
        result = _conn.call(name, arguments)
        return json.dumps({"ok": True, "result": result}, ensure_ascii=False)
    except (ConnectionError, RuntimeError) as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001 — never crash the server on a tool call
        logger.exception("Fallo inesperado en %s", name)
        return json.dumps({"ok": False, "error": f"Fallo inesperado: {exc}"}, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Connection / inspection tools
# --------------------------------------------------------------------------- #
@mcp.tool(
    name="sketchup_status",
    annotations={
        "title": "Check SketchUp connection",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def sketchup_status() -> str:
    """Verify the connection to the SketchUp extension.

    Call this FIRST in a session. Returns {"ok": true} if SketchUp is running
    with the extension's server started, or an actionable error explaining how
    to start it (Extensiones > SketchUp MCP > Start Server).
    """
    try:
        _conn._connect()
        return json.dumps({"ok": True, "host": SKETCHUP_HOST, "port": SKETCHUP_PORT})
    except ConnectionError as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)


@mcp.tool(
    name="sketchup_get_selection",
    annotations={
        "title": "Get selected components",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def sketchup_get_selection() -> str:
    """Return the components currently selected in SketchUp (ids + basic data).

    Use it to obtain entity ids when the user says "this piece" — ask them to
    select it in SketchUp, then call this tool.
    """
    return _call("get_selection", {})


# --------------------------------------------------------------------------- #
# Geometry tools
# --------------------------------------------------------------------------- #
@mcp.tool(
    name="sketchup_create_component",
    annotations={
        "title": "Create component",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
def sketchup_create_component(
    type: Annotated[
        Literal["cube", "cylinder", "sphere", "cone"],
        Field(description="Primitive type to create"),
    ] = "cube",
    position: Annotated[
        Optional[list[float]],
        Field(description="[x, y, z] position in model units (default [0,0,0])"),
    ] = None,
    dimensions: Annotated[
        Optional[list[float]],
        Field(description="[width, depth, height] in model units (default [1,1,1])"),
    ] = None,
) -> str:
    """Create a primitive component in the model and return its entity id.

    SketchUp models default to inches — if the user works in cm/m, convert
    before calling. The returned id is used by every other tool.
    """
    if position is not None and len(position) != 3:
        return json.dumps({"ok": False, "error": "position debe ser [x, y, z] (3 numeros)."})
    if dimensions is not None and len(dimensions) != 3:
        return json.dumps({"ok": False, "error": "dimensions debe ser [ancho, fondo, alto] (3 numeros)."})
    return _call(
        "create_component",
        {"type": type, "position": position or [0, 0, 0], "dimensions": dimensions or [1, 1, 1]},
    )


@mcp.tool(
    name="sketchup_delete_component",
    annotations={
        "title": "Delete component",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def sketchup_delete_component(
    id: Annotated[str, Field(description="Entity id of the component to delete", min_length=1)],
) -> str:
    """Delete a component by entity id. Undoable in SketchUp with Ctrl+Z."""
    return _call("delete_component", {"id": id})


@mcp.tool(
    name="sketchup_transform_component",
    annotations={
        "title": "Transform component",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
def sketchup_transform_component(
    id: Annotated[str, Field(description="Entity id of the component", min_length=1)],
    position: Annotated[
        Optional[list[float]], Field(description="New [x, y, z] position (model units)")
    ] = None,
    rotation: Annotated[
        Optional[list[float]], Field(description="Rotation [x, y, z] in degrees")
    ] = None,
    scale: Annotated[
        Optional[list[float]], Field(description="Scale factors [x, y, z] (1 = unchanged)")
    ] = None,
) -> str:
    """Move, rotate and/or scale a component. Provide at least one transform."""
    if position is None and rotation is None and scale is None:
        return json.dumps({"ok": False, "error": "Indica al menos position, rotation o scale."})
    args: dict[str, Any] = {"id": id}
    if position is not None:
        args["position"] = position
    if rotation is not None:
        args["rotation"] = rotation
    if scale is not None:
        args["scale"] = scale
    return _call("transform_component", args)


@mcp.tool(
    name="sketchup_set_material",
    annotations={
        "title": "Set material",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def sketchup_set_material(
    id: Annotated[str, Field(description="Entity id of the component", min_length=1)],
    material: Annotated[
        str,
        Field(description="Material or color name (e.g. 'Wood_Cherry', 'red', '#CC0000')", min_length=1),
    ],
) -> str:
    """Apply a material or color to a component."""
    return _call("set_material", {"id": id, "material": material})


@mcp.tool(
    name="sketchup_export_scene",
    annotations={
        "title": "Export scene",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def sketchup_export_scene(
    format: Annotated[
        Literal["skp", "dae", "obj", "stl", "png", "jpg"],
        Field(description="Export format (availability depends on SketchUp version/edition)"),
    ] = "skp",
) -> str:
    """Export the current scene to a file; returns the path written by SketchUp."""
    return _call("export", {"format": format})


# --------------------------------------------------------------------------- #
# Solid operations
# --------------------------------------------------------------------------- #
@mcp.tool(
    name="sketchup_boolean_operation",
    annotations={
        "title": "Boolean operation between solids",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
def sketchup_boolean_operation(
    operation: Annotated[
        Literal["union", "difference", "intersection"],
        Field(description="Boolean operation. 'difference' keeps target minus tool."),
    ],
    target_id: Annotated[str, Field(description="Entity id of the solid to keep/modify", min_length=1)],
    tool_id: Annotated[str, Field(description="Entity id of the solid used as tool", min_length=1)],
    delete_originals: Annotated[
        bool, Field(description="Erase both source solids after the operation")
    ] = False,
) -> str:
    """Perform union/difference/intersection between two solids.

    Both entities must be CLOSED solids (manifold groups/components) — open
    surfaces will fail. Returns the entity id of the resulting group.
    """
    return _call(
        "boolean_operation",
        {
            "operation": operation,
            "target_id": target_id,
            "tool_id": tool_id,
            "delete_originals": delete_originals,
        },
    )


@mcp.tool(
    name="sketchup_chamfer_edges",
    annotations={
        "title": "Chamfer edges",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
def sketchup_chamfer_edges(
    entity_id: Annotated[str, Field(description="Entity id of the solid", min_length=1)],
    distance: Annotated[float, Field(description="Chamfer distance (model units)", gt=0)] = 0.5,
    edge_indices: Annotated[
        Optional[list[int]],
        Field(description="Edge indices to chamfer; omit to chamfer ALL edges"),
    ] = None,
    delete_original: Annotated[
        bool, Field(description="Replace the original solid with the chamfered result")
    ] = True,
) -> str:
    """Chamfer (bevel) the edges of a solid."""
    args: dict[str, Any] = {
        "entity_id": entity_id,
        "distance": distance,
        "delete_original": delete_original,
    }
    if edge_indices is not None:
        args["edge_indices"] = edge_indices
    return _call("chamfer_edges", args)


@mcp.tool(
    name="sketchup_fillet_edges",
    annotations={
        "title": "Fillet edges",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
def sketchup_fillet_edges(
    entity_id: Annotated[str, Field(description="Entity id of the solid", min_length=1)],
    radius: Annotated[float, Field(description="Fillet radius (model units)", gt=0)] = 0.5,
    segments: Annotated[
        int, Field(description="Segments around the rounded edge (smoothness)", ge=2, le=64)
    ] = 8,
    edge_indices: Annotated[
        Optional[list[int]],
        Field(description="Edge indices to fillet; omit to fillet ALL edges"),
    ] = None,
    delete_original: Annotated[
        bool, Field(description="Replace the original solid with the filleted result")
    ] = True,
) -> str:
    """Fillet (round) the edges of a solid."""
    args: dict[str, Any] = {
        "entity_id": entity_id,
        "radius": radius,
        "segments": segments,
        "delete_original": delete_original,
    }
    if edge_indices is not None:
        args["edge_indices"] = edge_indices
    return _call("fillet_edges", args)


# --------------------------------------------------------------------------- #
# Woodworking joints
# --------------------------------------------------------------------------- #
@mcp.tool(
    name="sketchup_create_mortise_tenon",
    annotations={
        "title": "Mortise & tenon joint",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
def sketchup_create_mortise_tenon(
    mortise_id: Annotated[str, Field(description="Entity id of the piece receiving the mortise", min_length=1)],
    tenon_id: Annotated[str, Field(description="Entity id of the piece receiving the tenon", min_length=1)],
    width: Annotated[float, Field(description="Joint width (model units)", gt=0)] = 1.0,
    height: Annotated[float, Field(description="Joint height (model units)", gt=0)] = 1.0,
    depth: Annotated[float, Field(description="Joint depth (model units)", gt=0)] = 1.0,
    offset_x: Annotated[float, Field(description="X offset of the joint")] = 0.0,
    offset_y: Annotated[float, Field(description="Y offset of the joint")] = 0.0,
    offset_z: Annotated[float, Field(description="Z offset of the joint")] = 0.0,
) -> str:
    """Create a mortise-and-tenon joint between two components."""
    return _call(
        "create_mortise_tenon",
        {
            "mortise_id": mortise_id,
            "tenon_id": tenon_id,
            "width": width,
            "height": height,
            "depth": depth,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "offset_z": offset_z,
        },
    )


@mcp.tool(
    name="sketchup_create_dovetail",
    annotations={
        "title": "Dovetail joint",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
def sketchup_create_dovetail(
    tail_id: Annotated[str, Field(description="Entity id of the tail board", min_length=1)],
    pin_id: Annotated[str, Field(description="Entity id of the pin board", min_length=1)],
    width: Annotated[float, Field(description="Joint width (model units)", gt=0)] = 1.0,
    height: Annotated[float, Field(description="Joint height (model units)", gt=0)] = 1.0,
    depth: Annotated[float, Field(description="Joint depth (model units)", gt=0)] = 1.0,
    angle: Annotated[float, Field(description="Dovetail angle in degrees", gt=0, lt=45)] = 15.0,
    num_tails: Annotated[int, Field(description="Number of tails", ge=1, le=20)] = 3,
    offset_x: Annotated[float, Field(description="X offset of the joint")] = 0.0,
    offset_y: Annotated[float, Field(description="Y offset of the joint")] = 0.0,
    offset_z: Annotated[float, Field(description="Z offset of the joint")] = 0.0,
) -> str:
    """Create a dovetail joint between two boards."""
    return _call(
        "create_dovetail",
        {
            "tail_id": tail_id,
            "pin_id": pin_id,
            "width": width,
            "height": height,
            "depth": depth,
            "angle": angle,
            "num_tails": num_tails,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "offset_z": offset_z,
        },
    )


@mcp.tool(
    name="sketchup_create_finger_joint",
    annotations={
        "title": "Finger (box) joint",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
def sketchup_create_finger_joint(
    board1_id: Annotated[str, Field(description="Entity id of the first board", min_length=1)],
    board2_id: Annotated[str, Field(description="Entity id of the second board", min_length=1)],
    width: Annotated[float, Field(description="Joint width (model units)", gt=0)] = 1.0,
    height: Annotated[float, Field(description="Joint height (model units)", gt=0)] = 1.0,
    depth: Annotated[float, Field(description="Joint depth (model units)", gt=0)] = 1.0,
    num_fingers: Annotated[int, Field(description="Number of fingers", ge=2, le=50)] = 5,
    offset_x: Annotated[float, Field(description="X offset of the joint")] = 0.0,
    offset_y: Annotated[float, Field(description="Y offset of the joint")] = 0.0,
    offset_z: Annotated[float, Field(description="Z offset of the joint")] = 0.0,
) -> str:
    """Create a finger (box) joint between two boards."""
    return _call(
        "create_finger_joint",
        {
            "board1_id": board1_id,
            "board2_id": board2_id,
            "width": width,
            "height": height,
            "depth": depth,
            "num_fingers": num_fingers,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "offset_z": offset_z,
        },
    )


def main() -> None:
    """Entry point (stdio transport)."""
    logger.info("sketchup_mcp %s — extension endpoint %s:%s", __version__, SKETCHUP_HOST, SKETCHUP_PORT)
    mcp.run()


if __name__ == "__main__":
    main()
