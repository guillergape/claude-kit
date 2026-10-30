# Permisos y bloqueos en Claude Code (lo que funcionó)

Experiencia de semanas usando Claude Code en **modo auto** (Shift+Tab hasta "auto"), donde un clasificador en el servidor decide si cada comando no permitido explícitamente se puede ejecutar.

## Los tres tipos de bloqueo
1. **Caída del clasificador** — error "auto mode classifier gave no verdict (error)". Fallo temporal del servidor, no un juicio. Todo Bash/PowerShell que no esté en la lista `allow` falla hasta que se recupera (minutos u horas). No depende del modelo ni del esfuerzo.
   - Qué hacer: reintentar **una** vez; si sigue, el usuario ejecuta el comando él mismo con `! <comando>` en el prompt (el `!` lo corre sin pasar por el clasificador y la salida entra en la conversación), o cambia a modo manual (Shift+Tab) mientras dure.
2. **Denegación con motivo** — "denied by the Claude Code auto mode classifier. Reason: [X]". Motivos vistos:
   - `[Auto-Mode Bypass]` / `[Self-Modification]`: Claude intenta ampliar sus propios permisos (editar `~/.claude/settings.json`, leer transcripts para fabricarse una allowlist, añadir `additionalDirectories`…), **aunque el usuario se lo pida palabra por palabra**. Solución: lo hace el usuario. Claude abre el fichero (`Start-Process notepad "$env:USERPROFILE\.claude\settings.json"`) y le dice el texto exacto y después de qué línea pegarlo (con las comas bien); luego Claude comprueba que el JSON es válido. No intentar rodearlo con otras herramientas.
   - `[Unrequested Commit in a Connected App]`: acciones con efecto fuera (abrir un formulario de solicitud `/apply`, enviar un email a alguien) que el clasificador no ve claramente pedidas. Ayuda decir antes en el chat "voy a rellenar, no enviar" y, si se repite, una entrada en `autoMode.allow` (abajo).
   - `[Real-World Transactions]`: pagos, opt-outs legales, etc. → lo hace el usuario (p. ej. con su propia ventana de envío).
3. **Safety check** — "a safety check separate from auto mode blocked this request because of earlier conversation content". Lo dispara algo anterior del chat, no el comando. Suele bastar con un chat nuevo o `! comando`.

**Regla para Claude:** cuando algo se bloquee, decirlo enseguida: qué se bloqueó, el error exacto y por qué (diagnóstico, marcando si es una suposición). No reintentar en silencio ni buscar rodeos. Los bloqueos se apuntan solos en `blocklog.csv` (el hook de `costlog.py` lee los transcripts de todos los chats y subagentes, como mucho cada 10 min); `blocklog> <solución>` añade qué lo arregló.

## Autorizar una denegación concreta — `allow>`
Cuando el clasificador deniega algo que tú sí quieres (p. ej. `[Self-Modification]` al editar un settings que le has pedido), lo que funciona es un mensaje **tuyo** que nombre **la acción exacta**:
- **Funcionó** (varias veces, con motivos distintos): «Autorizo explícitamente la acción que te denegó el clasificador: `<herramienta>: <comando exacto>` — solo esa, en este chat, una vez». **No funcionó** cuando el mensaje solo nombraba el objetivo («para hacer el formulario») o cuando Claude había elegido él un valor del comando (p. ej. un usuario que buscó él).
- **`allow>`** (o `allow N>` para la N-ésima más reciente) te deja esa frase en el portapapeles, con la hora, el motivo y el comando exacto de la última denegación del clasificador en este chat (también las de sus subagentes). La lees, la pegas (Ctrl+V) y la envías tú. El hook nunca la manda ni la mete en el chat: un script que escribe tu consentimiento es justo lo que el clasificador rechaza como `[Auto-Mode Bypass]`. Las caídas («no verdict»), los hooks y los safety checks no salen: un permiso no los arregla.
- **Alternativa sin pegar:** `/permissions` → *Recently denied* → aprobarla. Claude recibe el permiso pero solo lo usa en tu siguiente mensaje.
- Si la misma denegación se repite y es segura, mejor una entrada en `autoMode.allow` (abajo) que autorizarla cada vez.

## Ajustes que funcionaron (en `~/.claude/settings.json`)
- **Reglas `allow` exactas por script**, nunca de intérprete entero (`Bash(python:*)` el modo auto la ignora porque equivale a ejecutar cualquier cosa):
  ```json
  "Bash(<PY> \"<HOME>/.claude/skills/md2pdf/md2pdf.py\":*)",
  "PowerShell(<PY> \"<HOME>/.claude/skills/md2pdf/md2pdf.py\":*)"   ← la de PowerShell solo en Windows
  ```
  La regla solo casa con el comando escrito exactamente así (misma ruta, mismas barras `/`, mismas comillas): que el SKILL.md use esa forma. Una ruta relativa (`python _tools/x.py:*`) solo casa si se ejecuta desde esa carpeta.
- **Herramientas MCP de solo lectura** en `allow` para que no pregunten: lectura de Gmail/Calendar/Drive, `mcp__claude-in-chrome__get_page_text`, `read_page`, `find`, `tabs_context_mcp`… y las de **borrador** de Gmail (crear/actualizar/listar). Nunca las de enviar.
- `PowerShell(Get-ChildItem *)`, `PowerShell(Select-String *)`: lectura, seguras.
- **`additionalDirectories`**: carpetas a las que Claude puede acceder además de donde se arranca (p. ej. la de la uni y la de código). Lo pega el usuario (Claude recibe `[Self-Modification]`).
- **`autoMode.environment`**: descripción en prosa de tu entorno para el clasificador (qué carpetas son de confianza, qué datos son sensibles y a quién pueden ir). Se genera con `/auto-mode-setup` y se ve con `claude auto-mode config`.
- **`autoMode.allow`**: excepciones en prosa, empezando la lista por `"$defaults"`. Ejemplos que funcionaron:
  - "Solicitudes de prácticas que el usuario pide en el chat: abrir la página de la empresa, iniciar sesión y rellenar o subir campos está permitido. El botón final de enviar necesita el OK explícito del usuario para esa solicitud."
  - "Enviar emails desde mis cuentas a mis propias cuentas o sus alias `+` está permitido sin preguntar; a cualquier otra dirección, las reglas normales." (Fue necesario además de la excepción escrita en el CLAUDE.md: **el clasificador lee el CLAUDE.md, pero una excepción ahí no bastó**.)
- `/permissions` → *Recently denied* → `r` reintenta una denegación concreta.
- Antes de tocar settings: copia de seguridad (`settings.json.bak-AAAA-MM-DD`) y validar el JSON después.

## Hooks: ventaja contra los bloqueos
Los hooks (`UserPromptSubmit`, `SessionStart`, `Stop`…) los ejecuta Claude Code, **no pasan por el clasificador** y no gastan tokens. Por eso lo importante y repetitivo (cronómetro, costlog, modo carpeta) se movió a hooks: siguen funcionando durante una caída del clasificador.
