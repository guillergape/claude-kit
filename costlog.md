# Cost log

Uso y coste de **cualquier** proceso hecho con Claude (programar, estudiar, emails, calendario, configuración, experimentos…). Objetivo: aprender qué modelo/esfuerzo necesita cada tipo de tarea y cuánto cuesta.

**Los datos van en `costlog.csv`** (una fila por sesión; se crea solo en el primer `costlog>`). Este fichero solo explica las columnas. Los bloqueos de permisos van aparte en `blocklog.csv` (`blocklog>`).

## Cómo se usa
- Al final de una sesión: `costlog> <nota sesión 1–5> <nota resultado 1–5 | - | NA | pendiente> [nota libre]`, p. ej. `costlog> 4 5 bien a la primera`, `costlog> 3 - tuve que corregirle dos veces`. Lo apunta un hook sin gastar tokens (Claude no ve el mensaje).
- `costlog>` solo, o mal escrito, o si el límite de 5 h / semanal se reinició a mitad, o si el CSV está abierto en Excel → se abre una ventana para rellenarlo (puede quedarse minimizada; los datos de uso quedan congelados en el momento del `costlog>`).
- `costlog> par 4 5 …` = había otros chats a la vez (también lo detecta solo): el % de uso no es solo de este chat, así que se estima con el $ de este chat × la mediana %/$ de tus sesiones sin paralelo (necesita ≥ 5 sesiones sin paralelo apuntadas).
- `blocklog> <cómo se arregló>` = apunta los comandos que se bloquearon en este chat (clasificador del modo auto caído o que deniega, safety check…), con la hora y el error exacto sacados del transcript.

## Columnas

| columna | significado |
|---|---|
| `date` | AAAA-MM-DD |
| `session_id` | sesión de Claude Code (lo escribe `costlog>`); `manual` = escrita a mano; `leftover` = un paso de `leftover n>` |
| `project` | carpeta donde corrió la sesión (cwd) |
| `task` | título del chat (o lo que pongas en la ventana): área + comando + ref, p. ej. `Prog práctica 2` |
| `model_effort` | p. ej. `Opus 5.5 high`; varios unidos con ` + ` |
| `n_questions` | prompts tuyos en la sesión |
| `n_corrected` | respuestas que tuviste que corregir o repedir |
| `nota_sesion` | 1–5 |
| `nota_pdf` | nota del resultado entregado (PDF, código, documento) 1–5; `—` = no hay nada que valorar; `pendiente` |
| `h5_start`, `h5_end` | % del límite de 5 h al empezar / terminar |
| `h5_reset` | `True` = la ventana de 5 h se reinició **durante** la sesión (start→end no mide; ver `usage_manual`) |
| `week_start`, `week_end`, `week_reset` | lo mismo con el límite semanal |
| `parallel` | `True` = otros chats de la misma cuenta a la vez; los % no son solo de esta sesión |
| `cost_usd` | $ de la sesión (contador de Claude Code; es por chat, otros chats no lo cambian) |
| `minutes` | del primer al último mensaje |
| `usage_manual` | tu estimación (solo se pide si hubo reinicio) o la estimación automática en paralelo |
| `note` | qué fue bien / mal |

- Celda vacía = no medido; `?` = desconocido; `—` = no aplica.
- Los % y el $ salen de la status line (`costlog/statusline.py`), que guarda instantáneas en `~/.claude/costlog-state/`. Sin plan Pro/Max (API key) no hay % de límites, solo $.
- No escribe si el CSV está abierto en Excel: la ventana se queda abierta con el error hasta que lo cierres.
