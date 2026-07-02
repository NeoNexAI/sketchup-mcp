#!/bin/bash
# Dev helper — actualiza y reinicia el servidor MCP local.
# En uso normal, Claude arranca el servidor vía `uvx neonexai-sketchup-mcp`;
# este script es solo para desarrollo del propio paquete.

# Matar procesos existentes
pkill -f "sketchup_mcp" 2>/dev/null

# Actualizar a la última versión publicada
pip install --upgrade neonexai-sketchup-mcp

# Arrancar el servidor en segundo plano
python -m sketchup_mcp &

sleep 1
echo "neonexai-sketchup-mcp actualizado y servidor reiniciado"
