# prompt-redo — Ctrl+Y rehace en la caja del prompt de Claude Code

La caja del prompt tiene deshacer (`chat:undo`, Ctrl+Z) pero no rehacer. Este mod guarda lo que quita cada Ctrl+Z y lo devuelve con Ctrl+Y. Mientras hay algo que rehacer sale una línea `[ ↷ redo ] ctrl+y (n)` encima del prompt; en cuanto escribes algo nuevo se vacía, como en cualquier editor. Todo local, vale para cualquier cuenta. RAM: despreciable.

## Instalar (Claude, con la regla 3 de `kit/CLAUDE.md`: enseñar el cambio, `.bak-` / `.kit-`, validar el JSON)
1. Copia `kit/extras/prompt-redo/` → `<LAB>/extras/prompt-redo/` (con la carpeta oculta `.claude-plugin/`).
2. `~/.claude/settings.json` → **fusiona** en `env` la clave `CLAUDE_CODE_PLUGIN_DIRS` = la ruta absoluta de esa carpeta, con barras `/` (fragmento `_opcional_prompt_redo_env` de `plantillas/settings.fragment.json`). No pises nada: si ya tiene `env`, se añade la clave; si ya tiene `CLAUDE_CODE_PLUGIN_DIRS` con otro mod, pregúntale antes (sin probar con dos mods a la vez).
3. `~/.claude/keybindings.json` → **fusiona** `keybindings.fragment.json` (Chat: `ctrl+z` → `chat:undo`, `ctrl+y` → `null`; **Global**: `ctrl+y` → `app:cycleDiffBase`) sin quitar sus atajos. Si ya usa Ctrl+Z o Ctrl+Y para otra cosa, pregúntale.
4. La persona reinicia Claude Code. Comprobación (Windows): `<PY> -m pip install pywinpty` y `<PY> <LAB>/extras/prompt-redo/test_tui.py` → `ok` (≈40 s, abre un Claude oculto sin mandar ningún mensaje: 0 tokens, ~1 GB de RAM mientras corre). En Mac/Linux no hay test automático: que escriba algo, Ctrl+Z dos veces y Ctrl+Y dos veces, y vea volver el texto. Si cambias el mod: `claude plugin validate <LAB>/extras/prompt-redo`.

## Por qué ese atajo tan raro
Probado el 27 oct 2026 en un TUI oculto: un `ctrl+y` en el contexto Chat nunca llega (la caja del prompt se queda Ctrl+Y; sin asignar es un «yank» vacío que no produce `prompt.edit`). Asignado en Global a una acción, Ctrl+Y pulsa un botón del mod que nombra esa acción. **Efecto secundario:** con el panel de diff abierto, Ctrl+Y puede cambiar la base del diff en vez de rehacer.

## Probado
Windows 11 (autor del kit, 27 oct 2026; `test_tui.py` ok). **Mac/Linux: sin probar** (`test_tui.py` usa pywinpty, solo Windows).

## Quitarlo
Borra la clave `CLAUDE_CODE_PLUGIN_DIRS` de `env` y los tres atajos de `keybindings.json` (o vuelve a las copias `.bak-`), y reinicia Claude Code.
