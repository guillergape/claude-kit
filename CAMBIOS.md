# Cambios del kit

<!-- Una entrada por versión, la más nueva arriba. La versión es la de VERSION.txt (fecha del fichero más nuevo,
     AAAA-MM-DD_HHMM). Escrita para quien tiene el kit instalado: qué cambia para él y en qué componente.
     `actualiza kit >` enseña las entradas posteriores a su versión. -->

## 2026-10-23 — prompts en espera: `wait>` / `go>` / `trigger>`
- **Nuevo `costlog/wait.py`** (opcional): `wait> <prompt>` lo guarda sin mandarlo (Claude no lo ve; un cierre de VS Code no lo pierde). Luego `go>` lo manda, `go all>` manda todos en cadena (cada uno solo si el anterior salió bien), `go reset>` al reiniciarse el límite de 5 h, `trigger> <evento>` cuando pase algo (p. ej. que otro chat acabe bien). También `wait plan>` (Claude lo parte en fases), `wait next>` (entra al acabar el turno), `wait edit>`, `wait drop>`. `wait>` solo lista todo. Mensajes en inglés. `go reset>` y `trigger auto>` usan el Programador de tareas en Windows; en Mac/Linux, un proceso suelto (no sobrevive a reiniciar el ordenador).
- **costlog** (`costlog/costlog.py`): llama a `wait.py` si está (bórralo si no lo quieres).
- **settings** (`plantillas/settings.fragment.json`): hook `Stop` → `wait.py stop` (para `wait next>`). **CLAUDE.md global**: sección nueva `kit:wait`. Para tenerlo: copia `wait.py` y `costlog.py`, añade el hook y la sección (`actualiza kit >` lo hace).

## 2026-10-23 — Moodle detrás de una VPN: GlobalProtect se conecta solo
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
