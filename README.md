# SketchUp MCP — NeoNexAI hardened fork

Conecta **SketchUp** con **Claude** (Claude Desktop o Claude Code) vía el Model Context
Protocol (MCP). Permite crear, transformar, materializar y exportar geometría en
SketchUp con lenguaje natural — "haz una mesa de 120×60×75", "redondea las aristas
de ese tablero 2 cm", "resta este volumen del muro", "expórtame la escena a DAE".

> **Fork endurecido de [mhyrr/sketchup-mcp](https://github.com/mhyrr/sketchup-mcp).**
> El original expone `eval_ruby` (ejecución de código Ruby arbitrario dentro de
> SketchUp → acceso total a disco y red). **Aquí `eval_ruby` está eliminado** — tanto
> del lado Python como del Ruby — y el socket escucha **solo en `127.0.0.1`** (nunca en
> red). Superficie de herramientas acotada y auditada. Ver [Seguridad](#seguridad).

---

## Qué necesita (dos piezas)

SketchUp no tiene API externa: solo se controla desde su **Ruby API embebida**. Por eso
el sistema tiene dos componentes que trabajan juntos:

1. **Extensión de SketchUp** (Ruby) — abre un servidor TCP local (puerto `9876`) dentro
   de SketchUp y ejecuta los comandos de geometría.
2. **Servidor MCP** (Python) — el puente que Claude arranca; traduce las peticiones de
   Claude a comandos para la extensión.

```
Claude Desktop / Claude Code
        │  (MCP, stdio)
        ▼
  Servidor MCP (Python, uvx)
        │  (socket TCP 127.0.0.1:9876)
        ▼
  Extensión SketchUp (Ruby)  ──►  SketchUp
```

---

## Requisitos

- **SketchUp** (2023 o posterior recomendado) con acceso a la Ruby Console.
- **Python 3.10+**.
- **uv / uvx** — gestor de paquetes Python. Si no lo tienen:
  ```powershell
  pip install uv
  ```
  o `winget install astral-sh.uv`.

---

## Instalación

### Paso 1 — Extensión de SketchUp

**Opción A (recomendada): copiar la carpeta a Plugins.**
Copia el archivo `su_mcp.rb` **y** la carpeta `su_mcp/` (ambos de este repositorio) dentro de:

```
%AppData%\SketchUp\SketchUp 2024\SketchUp\Plugins\
```
(ajusta `2024` a la versión instalada). Reinicia SketchUp.

**Opción B: empaquetar un `.rbz`.**
Comprime `su_mcp.rb` + carpeta `su_mcp/` en un `.zip`, renómbralo a `su_mcp.rbz`, y en
SketchUp: `Ventana → Extension Manager → Install Extension` → selecciona el `.rbz`.

Tras instalar, arranca el servidor dentro de SketchUp: menú **Extensiones → SketchUp MCP
→ Start Server**. Debe indicar que escucha en el puerto `9876`.

### Paso 2 — Conectar Claude al servidor MCP

Elige **una** de las dos opciones.

#### Opción 1 — con CLI (`claude mcp`)

Si tienen el CLI de Claude Code funcionando:

```bash
claude mcp add sketchup --scope user -- uvx neonexai-sketchup-mcp
```

#### Opción 2 — sin CLI (editar el JSON de configuración)

Si usan la app de Claude Desktop o el CLI da error, se configura a mano.

**Claude Desktop** — edita `%AppData%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sketchup": {
      "command": "uvx",
      "args": ["neonexai-sketchup-mcp"]
    }
  }
}
```

**Claude Code (config global)** — añade el mismo bloque `sketchup` dentro de
`mcpServers` en `%UserProfile%\.claude.json` (o el `.mcp.json` del proyecto).

Reinicia Claude. `uvx` descarga e instala el paquete automáticamente desde PyPI la
primera vez; para actualizar, `uvx` usa la última versión publicada.

---

## Herramientas disponibles

| Herramienta | Qué hace |
|---|---|
| `create_component` | Crea geometría (cubo/caja) con posición y dimensiones |
| `transform_component` | Mueve, rota o escala un componente por su ID |
| `delete_component` | Elimina un componente por su ID |
| `get_selection` | Devuelve los componentes seleccionados en SketchUp |
| `set_material` | Aplica un material/color a un componente |
| `export_scene` | Exporta la escena (`skp`, `dae`/`obj`, etc.) |
| `boolean_operation` | Unión / diferencia / intersección entre dos sólidos |
| `chamfer_edges` | Achaflana (bisela) las aristas de un sólido |
| `fillet_edges` | Redondea las aristas de un sólido |
| `create_mortise_tenon` | Ensamble caja y espiga entre dos piezas |
| `create_dovetail` | Ensamble cola de milano |
| `create_finger_joint` | Ensamble de dedos (caja) |

### Ejemplos de peticiones a Claude

- "Crea una caja de 200×80×40 cm en el origen y ponle material 'Wood_Cherry'."
- "Selecciona esa pieza y muévela 50 cm en Z."
- "Haz la diferencia booleana: resta el cilindro (tool) del bloque (target)."
- "Redondea todas las aristas de ese tablero con radio 1,5 cm."
- "Exporta la escena a DAE para llevarla a otro programa."

---

## Qué NO hace (honestidad técnica)

- **No renderiza fotorealista.** El render (Veras, V-Ray, Enscape) no es scriptable por
  esta vía — no tiene API pública. El MCP construye y modifica geometría; el render se
  sigue lanzando desde su plugin.
- **No sustituye el modelado fino manual.** Es un acelerador para operaciones repetitivas
  y paramétricas, no un modelador autónomo de proyectos completos.
- **No abre archivos ni navega por disco** — a diferencia del original, no ejecuta código
  arbitrario.

---

## Seguridad

Cambios frente al upstream (`mhyrr/sketchup-mcp`):

- **`eval_ruby` eliminado** del servidor Python (`server.py`) y del handler Ruby
  (`su_mcp/main.rb`). Era el motivo por el que el original se consideraba inseguro:
  permitía a Claude ejecutar cualquier código Ruby en la máquina.
- **Socket restringido a `127.0.0.1`** — el servidor de la extensión no acepta conexiones
  de red, solo del propio equipo.
- **Superficie acotada**: solo las 12 herramientas de la tabla, todas con parámetros
  explícitos y validados.

Auditar antes de instalar: `skill-vetter` sobre este repositorio (protocolo CISO NeoNexAI).

---

## Troubleshooting

- **"Could not connect to SketchUp"**: la extensión no está arrancada. Menú
  `Extensiones → SketchUp MCP → Start Server`.
- **Errores de comando**: abre la Ruby Console de SketchUp (`Ventana → Ruby Console`) para
  ver el mensaje detallado.
- **Timeouts**: divide la petición en pasos más pequeños.
- **`uvx` no encontrado**: instala `uv` (ver Requisitos) y reinicia la terminal/app.

---

## Licencia

MIT. Fork de [mhyrr/sketchup-mcp](https://github.com/mhyrr/sketchup-mcp), inspirado a su
vez en [blender-mcp](https://github.com/ahujasid/blender-mcp).
