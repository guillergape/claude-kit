# Trucos y lecciones sueltas

## Windows y el terminal (solo Windows)
- **Consola en cp1252:** imprimir texto con símbolos/fórmulas desde Python peta con `UnicodeEncodeError`. Ejecutar con `PYTHONIOENCODING=utf-8` o poner `sys.stdout.reconfigure(encoding="utf-8")` en el script; escribir ficheros siempre con `encoding="utf-8"`.
- **Los heredocs de Bash se comen las barras invertidas** (`\\` llega como `\`, `\f` se vuelve un salto de página): para scripts de Python con `\`, escribir el fichero con la herramienta Write en vez de un heredoc. Igual con `.tex`: escribirlos con Write/Edit, no con la shell.
- Python del Store: `python` puede ser el "alias" que abre la Store si no está instalado; comprobar `python --version`.
- **Excel por COM** desde PowerShell (`New-Object -ComObject Excel.Application`) hace gráficos nativos y los exporta a PNG. Leer un `.xlsx` sin openpyxl: descomprimirlo y leer `xl/sharedStrings.xml` + `xl/worksheets/sheet*.xml` (ojo a las celdas combinadas).
- **Descargas:** cuando un fichero de Descargas ya se ha usado del todo (movido a su sitio o su información guardada), borrarlo **a la Papelera de reciclaje**, no definitivo: `Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($path,'OnlyErrorDialogs','SendToRecycleBin')`. Si hay cualquier duda, no borrar. Decir qué se borró.
- Si Claude se queda "congelado" al dejar el portátil: ver `hooks/keep-awake.md`.

## Claude in Chrome (extensión del navegador)
- **La extensión va ligada a la cuenta de Claude**, no al navegador: si usas dos cuentas de Claude, los "Browser 1/2" que ve cada una son distintos. Una vez Claude estuvo 25 min mandando al usuario a pestañas que no existían en su pantalla. Regla: antes de pedirte nada en una pestaña, comprobar el navegador (`navigator.userAgent`) y **preguntarte si ves esa ventana**; nunca decir dónde está una pestaña sin comprobarlo.
- Para leer webs: `get_page_text` / `read_page` / `find` / `javascript_tool` (sacar solo los campos necesarios del DOM, o hacer `fetch()` a la API de la propia web con tu sesión). Capturas de pantalla solo si lo demás falla: son caras.
- `javascript_tool` devuelve `[BLOCKED: Cookie/query string data]` si lo que devuelves contiene URLs con parámetros: devolver ids y texto, no hrefs completos.
- Para descargar ficheros de una web con sesión: `fetch(url, {credentials:'include'})` en la página → `arrayBuffer()` → POST a un pequeño receptor local (`http.server` en 127.0.0.1 con CORS `*` que guarda el cuerpo con el nombre de una cabecera `X-Filename`).
- No disparar `alert`/`confirm` en las páginas: bloquean la extensión.
- Nunca enviar un formulario sin tu OK.

## Overleaf + git desde Claude Code (informes en grupo)
- Usar **el git propio de Overleaf**, sin GitHub en medio (remote `https://git@git.overleaf.com/<id del proyecto>`): `git push` aparece directamente en el proyecto compartido. Los compañeros editan en la web; quién cambió qué = el historial de Overleaf.
- Repo = solo el informe (`main.tex`, `sections/`, `figures/`).
- Si la carpeta está en Google Drive, poner el `.git` **fuera** (`git clone --separate-git-dir="<HOME>/.overleaf-git/<nombre>" …`; crear antes esa carpeta padre): Drive mete `desktop.ini` dentro de `.git` y rompe las refs.
- **Token:** Overleaf → Account settings → Git integration → Generate token (empieza por `olp_`). Guárdalo en tu gestor de contraseñas.
- **Guardarlo una sola vez** en el Administrador de credenciales: el primer `git clone`/`git fetch` normal abre la ventana de Git Credential Manager → **usuario `git`**, **contraseña = el token** (no tu contraseña de Overleaf). Después Claude hace pull/commit/push solo sin ver el token. Comprobar con `GCM_INTERACTIVE=never GIT_TERMINAL_PROMPT=0 git ls-remote origin`.
- **Errores que costaron una tarde:** (1) un 403 después de la ventana = credenciales mal escritas: reintentar con `git` + token antes de cambiar de método; (2) **nunca** `-c credential.helper=` (desactiva el gestor y pedirá el token en cada push/pull); (3) Claude debe explicar **antes** cómo rellenar esa ventana; (4) tras "hecho", comprobar (`ls -A`, `git status`).
- Nunca `push --force`. Si Overleaf rechaza el push, primero pull.
- Compilar en local: TinyTeX (`tlmgr install <paquetes>` con su `bin` en el PATH).

## Plugins que usa el autor del kit (opcionales)
- `ponytail` (marketplace GitHub `DietrichGebert/ponytail`): empuja a Claude a la solución más simple que funcione (menos código, stdlib antes que dependencias).
- `codex` (`openai/codex-plugin-cc`): segunda opinión con Codex. Solo si tienes cuenta de OpenAI.

## Codex (plugin `codex`): lo que da guerra
- **Windows: «blocked by policy» / «el acceso de solo lectura bloqueó la búsqueda y `rg`».** Sin `~/.codex/config.toml`, Codex no tiene sandbox en Windows y rechaza **todos** los comandos en solo lectura (no es culpa de la ruta, ni de Drive, ni de los espacios). Arreglo: crear `~/.codex/config.toml` con `[windows]` y `sandbox = "unelevated"`. `"elevated"` falla (`CreateProcessWithLogonW failed: 267`) y los flags viejos `experimental_windows_sandbox` / `elevated_windows_sandbox` están eliminados desde codex-cli 0.159. Si reaparece tras actualizar Codex, mirar primero que esa línea siga ahí.
- **Esfuerzo:** sin `--effort` el plugin pasa null y Codex usa `reasoning effort: none` → revisiones flojas. Poner `model_reasoning_effort = "high"` en el mismo `config.toml`, arriba del todo (antes de `[windows]`).
- **Solo lectura bloquea toda escritura, `%TEMP%` incluido**, así que cualquier script que cree temporales (Python `tempfile`, SciPy…) falla con «No usable temporary directory». Para revisiones que tienen que volver a ejecutar código: `--write` (workspace-write: carpeta de trabajo, `/tmp`, `$TMPDIR`).
- **Las ejecuciones con `--write` van en un hilo nuevo** (`--fresh`, o elegir «new thread» cuando pregunte): si continúas el hilo anterior conserva su sandbox de solo lectura y da «Access to the path … is denied».
- El subagente que reenvía la petición **quita `--write`** si el prompt dice «no modifiques nada / solo revisa»: pedirlo como «escribe solo en `<carpeta de pruebas>`».

## Promos de Anthropic
A veces dan crédito gratis para **sesiones en la nube** (cloud sessions de Claude Code, necesitan un repo de GitHub) con fecha de caducidad; mira el menú de uso de claude.ai. No cubre sesiones locales.
