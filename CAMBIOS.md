# Cambios del kit

<!-- Una entrada por versión, la más nueva arriba. La versión es la de VERSION.txt (fecha del fichero más nuevo,
     AAAA-MM-DD_HHMM). Escrita para quien tiene el kit instalado: qué cambia para él y en qué componente.
     `actualiza kit >` enseña las entradas posteriores a su versión. -->

## 2026-10-10 — versión 3: kit único
- **Un solo kit para Windows, Mac y Linux.** Los scripts detectan el sistema; la guía pregunta solo lo que cambia (paquetes, `python`/`python3`, keep-awake, rutas de Whisper).
- **Tus datos en un fichero:** `kit-datos.yaml` en tu lab (nombre, correos, uni, Moodle, asignaturas, colores…). Las plantillas se rellenan desde ahí con `kit/rellenar.py`.
- **`actualiza kit >`** (nuevo): trae la versión nueva (git o zip), enseña qué cambió y aplica solo eso, sin pisar lo que hayas cambiado tú (`ACTUALIZAR.md`).
- **Módulos opcionales** en `modulos/`: `moodle`, `uc3m`, `asignaturas` (un tutor por asignatura), `grok-bot`. La guía los ofrece según tus respuestas.
- Scripts (respecto a los kits por persona del 9 oct): `costlog.py` y `carpetas.py` funcionan en Mac/Linux (procesos separados con `start_new_session`; búsqueda en todo el disco desde `~`); `send.py` es opcional y abre ficheros con `open`/`xdg-open` fuera de Windows; `md2pdf.py` prueba el siguiente navegador si uno se cuelga y busca también `google-chrome-stable`, `microsoft-edge-stable` y Brave (el último).
- El kit ya no se mueve a `migracion/` al terminar: se queda intacto en `<LAB>/kit/` para poder actualizarlo.
