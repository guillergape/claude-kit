# Desinstalar el kit — `desinstalar kit >`

<!-- Pieza del kit desde la versión 2 del método (2026-10-09). Vive en <LAB>/kit/DESINSTALAR.md. Lo sigue el Claude de la persona que recibió el kit. -->

Cuando la persona escriba `desinstalar kit >` (o lo pida con otras palabras), sigue estos pasos para quitar lo que instaló el kit y dejar su Claude como estaba antes. **La primera respuesta es siempre solo la revisión (pasos 1 y 2): no cambies nada hasta la confirmación del paso 3.**

## Reglas
1. **Lo suyo se queda por defecto.** Solo se quita lo que añadió el kit. Lo que la persona cambió después, aunque esté dentro de algo del kit, no se toca sin preguntarle uno por uno.
2. **Todo lo que se quite se copia antes** en `<LAB>/_desinstalado-AAAA-MM-DD/` (con la misma estructura de rutas), así la desinstalación también se puede deshacer.
3. **Orden:** primero `settings.json` (status line, hooks, permisos), después los ficheros. Si borras un script antes que el hook que lo llama, cada mensaje dará error.
4. **Nada global sin enseñar el cambio exacto** (como en la migración). Si el clasificador te deniega editar settings, ábrele el fichero y dale el bloque exacto que tiene que quitar.
5. Borrar = a la papelera con la orden `PAPELERA` de `<LAB>/kit-datos.yaml` (tabla *Por sistema operativo* de `kit/CLAUDE.md`), nunca borrado definitivo.

## Paso 1 — Inventario (sin cambios)
Fuentes: la lista `instalado:` de `<LAB>/kit-datos.yaml` y la tabla *Cambios hechos fuera de la carpeta del lab* de `<LAB>/INFORME_MIGRACION.md` (en kits anteriores a la versión 3, `<LAB>/migracion/INFORME_MIGRACION.md`). Para cada cosa, clasifícala:

| | Significa | Por defecto |
|---|---|---|
| 🟢 **Del kit, intacto** | igual que quedó al instalarlo | se quita |
| 🟡 **Mezclado** | del kit, pero la persona lo cambió después | se pregunta: quitar entero / quitar solo lo del kit / dejarlo |
| 🔵 **Suyo** | lo añadió la persona después y no es del kit | no se toca (solo se lista) |
| 🟣 **Datos e instalaciones** | `costlog.csv`, `blocklog.csv`, `~/.claude/costlog-state/`, `~/.moodle-token`, `carpetas.json`/`moodle.json`, los `CLAUDE.md` y `Main sources.md` que haya montado en su carpeta de la uni (ya son suyos), venv de Whisper (~2 GB), paquetes pip (`markdown-it-py`, `pymupdf`), MCP `google-workspace` y su proyecto de Google Cloud, memorias guardadas, `leftover.md`, `personas.md`, `kit-datos.yaml`, el propio `<LAB>/kit/` | se conservan; se pregunta |

Cómo saber si algo está intacto o mezclado:
- **`~/.claude/settings.json`**: compara en JSON (con Python, no a ojo) el `.bak-` (antes del kit), el `.kit-` (justo después) y el actual. Lo del kit = lo que está en `.kit-` y no en `.bak-`. Si sigue igual en el actual → 🟢; si existe cambiado → 🟡. El resto del actual → 🔵.
- **`~/.claude/CLAUDE.md`**: las secciones del kit van entre `<!-- kit:<nombre> -->` y `<!-- /kit:<nombre> -->`. Compara cada bloque con el del `.kit-`: igual → 🟢; distinto → 🟡 (enseña el diff). Fuera de las marcas → 🔵.
- **Carpetas y scripts** (`~/.claude/skills/<x>/`, `~/.claude/hooks/`, scripts del lab): compara con su original en `<LAB>/kit/` pasado por `rellenar.py` con su `kit-datos.yaml`: igual → 🟢, distinto → 🟡; fichero que no venía en el kit → 🔵.
- **Sin `.kit-` ni marcas** (instalado con el kit versión 1): usa el `.bak-` y las plantillas del kit para reconocer lo que es del kit; lo que no reconozcas con seguridad es 🟡, nunca 🟢.

## Paso 2 — Revisión
Enséñale:
1. **Resumen en números:** «Se quitarían N entradas de settings, M secciones del CLAUDE.md global y K ficheros/carpetas (X MB). Hay J cosas mezcladas que tienes que decidir tú. Se quedan L cosas tuyas.»
2. **Tabla por componente** (status line, costlog/blocklog/send, modo carpeta, keep-awake, cada skill, transcripción, extras, reglas globales…) con: dónde está, estado (🟢🟡🔵🟣) y qué pasaría.
3. **Avisos** que apliquen: «sin el hook, `costlog>` / `_<carpeta>:` / `send>` dejan de funcionar», «borrar el venv libera ~2 GB pero reinstalarlo tarda», «el proyecto de Google Cloud y sus credenciales se borran a mano en console.cloud.google.com», «quitar paquetes pip puede romper otras cosas tuyas que los usen».

Luego pregunta (selección):
- **Alcance:** todo · elegir componentes · solo desactivar (quitar hooks/status line/reglas, dejar los ficheros en el lab) · nada.
- Para cada 🟡: quitar entero · quitar solo lo del kit · dejarlo.
- Para cada 🟣: conservar · mover a `_desinstalado-…` · borrar.

## Paso 3 — Confirmación final
Repite la lista exacta de lo que se va a quitar (y lo que se queda) y el diff de cada fichero global. Pide un sí explícito. Si el alcance es **todo**, que escriba literalmente `DESINSTALAR`.

## Paso 4 — Hacerlo
1. Copia todo lo que se va a quitar o editar a `<LAB>/_desinstalado-AAAA-MM-DD/`.
2. `settings.json`: quita solo las entradas elegidas (Python `json`, comparando elemento a elemento) y valida que el JSON carga. Comprueba que ninguna ruta que quede en settings apunta a un fichero que vas a borrar.
3. `CLAUDE.md` global: quita los bloques elegidos con sus marcas.
4. Ficheros y carpetas a la Papelera. Lo de 🟣 solo si se eligió (`claude mcp remove …`, `pip uninstall …`).
5. Si es **todo** y no queda nada 🔵 ni 🟡 en un fichero global, ofrece en su lugar restaurar su `.bak-` tal cual (más limpio).

## Paso 5 — Comprobar y apuntar
1. Que reinicie Claude Code y escriba cualquier cosa: sin errores de hooks; la status line es la de antes (o ninguna).
2. Apunta en `INFORME_MIGRACION.md` una sección **Desinstalación**: fecha, alcance, qué se quitó, qué se quedó y por qué, dónde está la copia.
3. Dile cómo deshacerlo: todo está en `<LAB>/_desinstalado-AAAA-MM-DD/`; para volver a instalarlo, «reinstala desde `_desinstalado-…` usando el informe».
4. Si quitó todo, el propio lab (`<LAB>`) puede borrarlo él a mano cuando quiera; no lo borres tú.
