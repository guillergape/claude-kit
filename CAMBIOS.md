# Cambios del kit

<!-- Una entrada por versión, la más nueva arriba. La versión es la de VERSION.txt (fecha del fichero más nuevo,
     AAAA-MM-DD_HHMM). Escrita para quien tiene el kit instalado: qué cambia para él y en qué componente.
     `actualiza kit >` enseña las entradas posteriores a su versión.
     Si la entrada trae algo nuevo (una función o herramienta nueva, no ajustes ni arreglos de lo que ya hay), pon
     justo bajo su título una línea `<!-- importante: sí`, cerrada igual que este comentario: va al aviso mensual
     a los suscriptores. -->

## 2026-10-31 — nuevo `extras/chrome-relogin/`: si Claude in Chrome pierde la sesión, vuelve a entrar solo
<!-- importante: sí -->
- **Nuevo `extras/chrome-relogin/`** (opcional, **solo Windows + Edge**): cuando la extensión Claude in Chrome pierde la sesión, un chat que la usa se quedaba parado hasta que pulsabas «Log in». `chrome_relogin.py` lo pulsa por ti (y el «Authorize» de claude.ai) con UI Automation, sin tokens ni capturas. Abre una ventana de Edge **fuera de pantalla**, no te roba el foco ni cambia tus pestañas, se niega a autorizar otra cuenta distinta de la tuya y borra todo lo que crea (también tras un cierre brusco). Probado con una simulación y con la extensión conectada; **aún no con una desconexión real**.
- **CLAUDE.md global** (`plantillas/CLAUDE.global.md`): sección nueva `kit:chrome-relogin` (si la extensión falla, lanzar el script y reintentar una vez). **Guía** (`CLAUDE.md`, fase 8 y tabla): se ofrece solo en Windows con Edge. Nada que actualizar en lo que tienes instalado; si lo quieres, pídele a tu Claude «chrome-relogin».

## 2026-10-30 — empezar la ventana de 5 h a una hora fija, con el ordenador apagado
<!-- importante: sí -->
- **Nueva guía `guias/ventana-5h.md`** (opcional): dos rutinas en la nube (invierno y verano, para no depender del cambio de hora) que cada día a la hora que elijas mandan «OK» con el modelo más pequeño, y así la ventana de 5 h empieza ahí aunque el ordenador esté apagado. Casi no gasta límite. Tu Claude las crea con la skill `schedule`; se pueden borrar desde claude.ai/code/routines. Creadas y programadas en una cuenta del autor; que abran la ventana de 5 h aún está sin comprobar.
- **Guía** (`CLAUDE.md`, fase 8): la ofrece solo si la quieres. Nada que actualizar en lo que tienes instalado; si la quieres, pídele a tu Claude «ventana de 5 h».

## 2026-10-30 — actualización general: bloqueos que se apuntan solos, `allow>`, vault, `login>`, Ctrl+Y en el prompt
- **costlog** (`costlog/costlog.py`, `textos.en.json`, `costlog.md`): **blocklog se apunta solo**: con cualquier mensaje, como mucho cada 10 min, lee aparte los transcripts de todos los chats y subagentes y apunta cada bloqueo nuevo (una fila por incidente, columna nueva `ids` para no duplicar; la solución se rellena sola si el mismo comando pasa después). `blocklog> <solución>` pasa a ser opcional. Tus filas viejas se respetan. El primer escaneo apunta también los bloqueos de antes: si no los quieres, pon una fecha en `START`. **`allow>` / `allow N>`**: copia al portapapeles tu autorización para la última denegación del clasificador en este chat, con la acción exacta; la pegas y la envías tú. `vault>` y `login>` si los instalas (abajo). `costlog> 4` solo apunta directo con nota de resultado `—` y correcciones `0`.
- **Nuevo `vault/`** (opcional): los tokens y claves de API de tus scripts en el almacén de credenciales del sistema (`from vault import get`), ventana con `vault>`; Claude nunca ve los valores. Probado en Windows; Mac/Linux sin probar.
- **Nuevo `login/`** (opcional, para quien tiene varias cuentas de Claude): `login> <cuenta>` cambia la cuenta de Claude Code; en Windows lo hace solo (Edge fuera de pantalla con perfil propio, lee el código de claude.ai de tu Gmail, pulsa Authorize). Tus cuentas van en `login.json`. Esta versión genérica aún no la ha probado nadie en real.
- **Nuevo `extras/prompt-redo/`** (opcional): mod de Claude Code para que Ctrl+Y rehaga lo que quitó Ctrl+Z en la caja del prompt (`env` de settings + `keybindings.json`, fusionados sin pisar nada).
- **send** (`costlog/send.py`, `guias/email.md`): el cuerpo del borrador se puede editar en la ventana; botón **Guardar borrador** (mismo borrador, adjuntos e hilo se quedan; se pierden negritas y enlaces); Enviar guarda antes si lo editaste; Ctrl+Z en el texto.
- **keep-awake** (`hooks/keep-awake.ps1.txt`, `keep-awake.md`): el brillo original ya no se pierde si un salvapantallas negro se cerró a la fuerza; la pantalla negra vuelve a quedarse delante.
- **md2pdf** (`skills/md2pdf/`): clases nuevas opcionales (`math-cond`, `box-def`, `box-g` / `grey-f`, `wide`) y resaltados que cubren fórmulas altas.
- **CLAUDE.md global** (`plantillas/CLAUDE.global.md`): secciones nuevas `kit:habitos` (explicaciones al final, prompts para otro chat en un bloque de código, decisiones pequeñas sin pedir OK, límite agotado → script en segundo plano) y `kit:vault`; `kit:bloqueos` habla de blocklog automático y `allow>`. **Guías:** `permisos-y-bloqueos.md` (cómo autorizar una denegación concreta), `trucos.md` (Ctrl+G en la terminal de VS Code). **Guía de instalación** (`CLAUDE.md`): los componentes nuevos en la tabla y en la fase 8.
- Para tenerlo: `actualiza kit >` (sustituye `costlog.py` y `send.py`, añade a tu `textos.json` las frases nuevas si no usas el español, y te ofrece los componentes nuevos).

## 2026-10-23 — el informe llega al autor sin correo (y avisar de que has actualizado)
<!-- importante: sí -->
- **Nuevo `tools/feedback.py`** (solo stdlib): manda `INFORME_MIGRACION.md` al autor del kit por un formulario privado, sin cuenta ni correo. Primero enseña qué se mandaría (tu carpeta de usuario sale como `<HOME>`); solo envía con `--enviar`, después de tu OK. Sin informe (`--nombre … --tipo actualizacion`) manda solo tu nombre, la versión y el tipo, para que el autor sepa cuánta gente usa y actualiza el kit. Si no puede (sin internet), plan B: el correo de siempre. `--test` lo prueba en local.
- **Guía** (`CLAUDE.md`, fase 9 pasos 6–7 y regla 7), `INFORME_MIGRACION.md` (comentarios), `ACTUALIZAR.md` (paso 5: al acabar una actualización sin nada que reportar, tu Claude te ofrece ese aviso en una línea, una vez) y `LEEME.md`/`README.md` (paso 3, *Ayudar a que crezca*, insignia de estrellas): usan `feedback.py` en vez de pedirte que respondas al correo, y cómo aportar (estrella, feedback, issues/PRs). Nada que actualizar en lo que tienes instalado.

## 2026-10-23 — prompts en espera: `wait>` / `go>` / `trigger>`
<!-- importante: sí -->
- **Nuevo `costlog/wait.py`** (opcional): `wait> <prompt>` lo guarda sin mandarlo (Claude no lo ve; un cierre de VS Code no lo pierde). Luego `go>` lo manda, `go all>` manda todos en cadena (cada uno solo si el anterior salió bien), `go reset>` al reiniciarse el límite de 5 h, `trigger> <evento>` cuando pase algo (p. ej. que otro chat acabe bien). También `wait plan>` (Claude lo parte en fases), `wait next>` (entra al acabar el turno), `wait edit>`, `wait drop>`. `wait>` solo lista todo. Mensajes en inglés. `go reset>` y `trigger auto>` usan el Programador de tareas en Windows; en Mac/Linux, un proceso suelto (no sobrevive a reiniciar el ordenador).
- **costlog** (`costlog/costlog.py`): llama a `wait.py` si está (bórralo si no lo quieres).
- **settings** (`plantillas/settings.fragment.json`): hook `Stop` → `wait.py stop` (para `wait next>`). **CLAUDE.md global**: sección nueva `kit:wait`. Para tenerlo: copia `wait.py` y `costlog.py`, añade el hook y la sección (`actualiza kit >` lo hace).

## 2026-10-23 — Moodle detrás de una VPN: GlobalProtect se conecta solo
<!-- importante: sí -->
- **moodle** (`modulos/moodle/moodle.py`, `SKILL.md` → *VPN*, `moodle.example.json`): clave nueva opcional `"vpn"` en `moodle.json`, un comando que `moodle.py` ejecuta una vez ante un `HTTP 403` antes de reintentar. Sin ella, nada cambia (solo el aviso del 403).
- **Nuevo `modulos/moodle/vpn-globalprotect.ps1.txt`** (Windows): pulsa *Connect* en GlobalProtect sin tocar ratón ni teclado; con SSO el login se completa solo en el navegador si ya tiene la sesión, y luego cierra esa ventana. No escribe nunca nada. Para instalarlo: `modulos/uc3m/README.md` → *Fuera de la uni, VPN*.
- **uc3m** (`README.md`): Aula Global solo funciona desde la red de la UC3M o con su VPN (desde el 2026-10-22); cómo dejar la VPN automática.

## 2026-10-22 — arreglos de una instalación en Windows (UC3M)
- **moodle** (`modulos/moodle/moodle.py`, `SKILL.md`):
  - comando nuevo **`token`**: guarda el token a partir del `moodlemobile://token=…` que copias de las DevTools (lo lee del portapapeles y lo vacía), sin que Claude lo vea nunca. El SKILL.md ofrece esta vía primero; la de Claude in Chrome sigue, avisando de que el token pasa por el chat.
  - el token solo se añade a descargas de tu propio Moodle (`site`); un enlace a otro sitio se salta y se avisa.
  - los títulos de avisos, materiales y fechas ya no salen con `&amp;` y similares.
  - si Python no se fía del certificado del Moodle (`CERTIFICATE_VERIFY_FAILED`, visto en Windows con Aula Global), el mensaje dice cómo arreglarlo (Windows: una petición con `Invoke-WebRequest`; Mac: `Install Certificates.command`).
  - un `HTTP 403` ya no sale como error de Python: el mensaje dice que es tu Moodle bloqueando la red (p. ej. solo desde el campus o la VPN), no el token.
- **status line** (`costlog/statusline.py`): «sem» sale en tu idioma (`wk` en inglés), vía `textos.json`. Al actualizar, copia también `textos.en.json` (o añade `"sem"` a tu `textos.json`).
- **`costlog/textos.py --test`**: ya no falla si borraste `send.py`; los textos de scripts no instalados solo se cuentan.
- **`rellenar.py`**: entiende las comillas escapadas como en YAML (`"…\"…"`, `'…''…'`) y una clave vacía con comentario (`asignaturas:   # …`) ya no toma el comentario como valor.
- **Guía** (`CLAUDE.md`): en Windows, Python ≥ 3.10 comprobado (el de la Store puede ser 3.9) y por ruta absoluta; md2pdf avisa de que `pymupdf` 2.x es una instalación grande; `powercfg /requests` pide terminal de administrador (también en `hooks/keep-awake.md`); fase 8 propone completar `autoMode.environment` con tus carpetas de confianza y ficheros secretos; fase 9 quita del CLAUDE.md del lab los comandos no instalados.
- **asignaturas** (`CLAUDE.curso.md`): la sección *Calendario* tiene una línea para quien no instaló la fase 6, y ya no menciona `Moodle links.md` (no lo creaba nada).
- **uc3m** (`README.md`): el login de Aula Global es SSO por `login.uc3m.es` (CAS), y nota del certificado en Windows. Desde el 2026-10-22, fuera de la uni Aula Global solo funciona con la VPN de la UC3M (GlobalProtect).
- **md2pdf** (`SKILL.md`): nada de `·` u otros símbolos Unicode dentro de `\text{}` (KaTeX da `\cdotp`).

## 2026-10-17 — Mac (probado en un Mac real)
- **md2pdf** (`skills/md2pdf/md2pdf.py`): en Mac, Chrome escribe el PDF y no se cierra; md2pdf se colgaba 3 min y fallaba. Ahora vigila hasta que el PDF (o el volcado de la página) está listo y cierra Chrome: unos segundos. Windows igual que antes. Edge de Mac añadido a la lista de navegadores.
- **Python en Mac** (tabla *Por sistema operativo* de `CLAUDE.md`): ruta absoluta de un Python ≥ 3.10 con tkinter, nunca `/usr/bin/python3` (3.9 de Apple). Si tus hooks usan `python3` y te funcionan, no hace falta cambiar nada.
- **keep-awake en Mac:** normalmente no hace falta (Claude Code ya lanza su `caffeinate`); `hooks/keep-awake.md`.
- **modo carpeta** (`costlog/carpetas.py`): en Mac/Linux la búsqueda en todo el ordenador salta `~/Library` y `~/.Trash`.
- Avisos de Mac en la tabla: permiso de privacidad para «Python» la 1.ª vez; Whisper con un Python muy nuevo → venv con 3.12.

## 2026-10-15 — ventanas de los scripts en tu idioma
- **costlog/blocklog/send/modo carpeta** (`costlog/costlog.py`, `carpetas.py`, `send.py`): las ventanas y mensajes salen en tu idioma (`IDIOMA`). Nuevos `costlog/textos.py` (busca las traducciones; sin ellas, español) y `costlog/textos.en.json` (inglés). Al actualizar, copia los dos y, si tu `IDIOMA` no es `es`, tu Claude crea `<LAB>/costlog/textos.json` (fase 2, punto 1, de `kit/CLAUDE.md`). Los datos que se apuntan en `costlog.csv` / `blocklog.csv` no cambian.
- Los demás scripts (`timelog.py`, `old.py`, `moodle.py`, `md2pdf.py`) ya escribían en inglés para Claude, que te lo cuenta en tu idioma.

## 2026-10-14 — pasar de un kit antiguo al nuevo
- **Si instalaste (o empezaste) un kit anterior a la v3** (zip `kit-claude-<nombre>-…` del 9 oct): `ACTUALIZAR.md` tiene una sección nueva, *Vienes de un kit antiguo*. Tu carpeta se queda como lab, el kit nuevo se clona dentro en `kit/`, se crea `kit-datos.yaml` a partir de tu informe, tus scripts parcheados se sustituyen por los del kit (ya traen los arreglos de Linux/Mac) y la instalación sigue desde la fase donde lo dejaste.

## 2026-10-10 — trucos de Codex
- `guias/trucos.md`: sección nueva **Codex (plugin `codex`)**: cómo arreglar «blocked by policy» en Windows (`~/.codex/config.toml` con `[windows] sandbox = "unelevated"`), subir el esfuerzo por defecto, y por qué `--write` necesita un hilo nuevo. Solo te afecta si usas el plugin de Codex.

## 2026-10-10 — inglés (y cualquier idioma)
- **Idioma de la instalación:** la guía pregunta primero el idioma (`IDIOMA` en `kit-datos.yaml`), te habla en él y traduce lo que instala (CLAUDE.md global, guías, plantillas). Si ya tienes el kit, añade `IDIOMA: es` a tu `kit-datos.yaml`.
- `README.md` en inglés para empezar; `actualiza kit >` aplica los cambios traducidos si tu copia no está en español.

## 2026-10-10 — versión 3: kit único
- **Un solo kit para Windows, Mac y Linux.** Los scripts detectan el sistema; la guía pregunta solo lo que cambia (paquetes, `python`/`python3`, keep-awake, rutas de Whisper).
- **Tus datos en un fichero:** `kit-datos.yaml` en tu lab (nombre, correos, uni, Moodle, asignaturas, colores…). Las plantillas se rellenan desde ahí con `kit/rellenar.py`.
- **`actualiza kit >`** (nuevo): trae la versión nueva (git o zip), enseña qué cambió y aplica solo eso, sin pisar lo que hayas cambiado tú (`ACTUALIZAR.md`).
- **Módulos opcionales** en `modulos/`: `moodle`, `uc3m`, `asignaturas` (un tutor por asignatura), `grok-bot`. La guía los ofrece según tus respuestas.
- Scripts (respecto a los kits por persona del 9 oct): `costlog.py` y `carpetas.py` funcionan en Mac/Linux (procesos separados con `start_new_session`; búsqueda en todo el disco desde `~`); `send.py` es opcional y abre ficheros con `open`/`xdg-open` fuera de Windows; `md2pdf.py` prueba el siguiente navegador si uno se cuelga y busca también `google-chrome-stable`, `microsoft-edge-stable` y Brave (el último).
- El kit ya no se mueve a `migracion/` al terminar: se queda intacto en `<LAB>/kit/` para poder actualizarlo.
