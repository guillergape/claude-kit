# <nombre del lab> — laboratorio de Claude

Esta carpeta no es solo para aprender Claude: es un **sandbox para experimentar con Claude y mejorarlo**:
- Probar cosas de las que aún no estoy seguro (flujos experimentales, ideas, prototipos).
- Mejorar Claude: conectores (MCP), plugins, skills, hooks y settings.
- Revisar cómo le pido las cosas y qué reglas sigue.
- Cuidar su memoria: qué va en `~/.claude/CLAUDE.md`, en los CLAUDE.md de proyecto y en la auto-memoria, sin duplicados.

## Cómo trabajar aquí
- Los experimentos pueden ser desordenados, pero **cada uno en su subcarpeta** (o fichero con nombre claro) con un README.
- Antes de cambiar algo global (`~/.claude/CLAUDE.md`, `~/.claude/settings.json`, MCP/plugins a nivel usuario), di qué cambia y por qué: afectan a todos los proyectos.
- Cuando algo funciona y vale la pena, di dónde debería vivir (CLAUDE.md global, skill, hook, memoria) en vez de dejarlo solo aquí.
- Cuando un experimento falla o se abandona, apunta brevemente por qué en su carpeta, para no repetirlo.

## Cost log y block log (hooks, 0 tokens)
- `costlog> <nota sesión 1–5> <nota resultado 1–5|-|NA> [nota]` al final de cualquier sesión → una fila en `costlog.csv` (lo hace el hook `costlog/costlog.py`; Claude no ve el mensaje). Columnas en `costlog.md`. Solo comparar entradas cuando lo pida. Si pido apuntar una sesión a mano (sin `costlog>`), añade una fila con el módulo `csv` de Python (`session_id` = `manual`); si el CSV está abierto en Excel, dímelo y espera.
- `blocklog> <solución>` → una fila en `blocklog.csv` por incidente de bloqueo (sacado del transcript). Funciona aunque el clasificador esté caído.
- `send> <palabras>` → ventana de borradores de Gmail para enviar yo (`costlog/send.py`).
- `_<carpeta>:` → modo carpeta (`costlog/carpetas.py`, configurado en `costlog/carpetas.json`).

## Contents
<!-- una línea por carpeta/fichero: qué es y su estado. Rellenar al terminar la migración. -->
- `costlog/` — hook `UserPromptSubmit` (`costlog>`, `blocklog>`, `send>`, modo carpeta) + status line.
- `costlog.csv` / `blocklog.csv` — registros (se crean solos).
- `costlog.md` — qué significa cada columna.
- `kit/` — el kit tal como llegó (clon de git o zip). **No se edita**: con él se compara al actualizar (`actualiza kit >`).
- `kit-datos.yaml` — mis datos para el kit (rellena las plantillas; qué está instalado).
- `INFORME_MIGRACION.md` — informe de la instalación, actualizaciones y uso de cada herramienta.
