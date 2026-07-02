# Ejemplos de uso — SketchUp MCP (NeoNexAI)

Este fork se maneja **por lenguaje natural desde Claude**, no con scripts sueltos.
Abajo, un recetario de peticiones organizadas por herramienta.

> Los ejemplos que traía el upstream (`arts_and_crafts_cabinet.py`, `behavior_tester.py`,
> `simple_test.py`) usaban `eval_ruby` (ejecución de Ruby arbitrario) y **se han
> eliminado** por seguridad. El equivalente seguro es pedirle a Claude que use las
> herramientas acotadas.

## Crear y transformar

- "Crea una caja de 200×80×40 cm en el origen."
- "Crea tres cajas de 40×40×72 cm separadas 50 cm en X (patas de mesa)."
- "Mueve el último componente 50 cm en Z."
- "Escala esa pieza al 150 % en X."

## Materiales

- "Aplícale a esa pieza el material 'Wood_Cherry'."
- "Ponme la selección de color rojo."

## Operaciones booleanas

- "Resta el cilindro (tool) del bloque (target) — diferencia booleana."
- "Une esas dos piezas en un solo sólido."
- "Dame la intersección de los dos volúmenes."

## Aristas

- "Redondea todas las aristas de ese tablero con radio 1,5 cm (fillet)."
- "Achaflana las aristas superiores con 1 cm (chamfer)."

## Ensambles de carpintería

- "Haz un ensamble caja y espiga entre la pata y el travesaño."
- "Genera una cola de milano de 4 colas entre esas dos tablas."
- "Crea un ensamble de dedos (finger joint) de 5 dedos."

## Exportar

- "Exporta la escena a DAE."
- "Guarda la escena como SKP."

## Selección / inspección

- "¿Qué tengo seleccionado ahora mismo? Dame los IDs y dimensiones."

---

**Flujo típico**: crear geometría → obtener IDs con `get_selection` → transformar /
materializar / ensamblar por ID → exportar. Claude encadena estos pasos solo; tú describes
el resultado que quieres.
