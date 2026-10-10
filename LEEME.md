# Kit de Claude Code

> **Experimental.** Es un proyecto pequeño y en pruebas: las guías y scripts pueden cambiar o fallar sin aviso (lo menos probado es Mac). *(Quitar este aviso si el proyecto crece.)*

*English: [README.md](README.md). La instalación te pregunta primero el idioma.*

Herramientas y costumbres para trabajar con Claude Code, sin nada personal de nadie. Casi todo lo importante gasta **0 tokens** (lo hacen hooks y scripts, no el modelo). Vale para **Windows, Mac y Linux**: la instalación detecta tu sistema y te pregunta lo tuyo (nombre, correos, universidad, Moodle, asignaturas…), lo guarda en un fichero de datos y rellena todo desde ahí.

Repositorio (para `actualiza kit >`): https://github.com/guillergape/claude-kit

## Cómo empezar
1. Crea una carpeta **fija** para tu "laboratorio" de Claude (no en Descargas), p. ej. `~/claude-lab` (Windows: `C:\Users\<tú>\claude-lab`).
2. Mete el kit dentro **con el nombre `kit`**: `git clone https://github.com/guillergape/claude-kit kit` (así luego se actualiza con un `git pull`), o descomprime el zip y renombra la carpeta a `kit`.
3. Abre un terminal en la carpeta del lab (no dentro de `kit`) y arranca `claude`. Pon **Opus con esfuerzo high** (`/model`).
4. Pégale este mensaje:

> En esta carpeta, dentro de `kit/`, tengo un kit de herramientas para Claude Code que me han pasado. Es de un entorno seguro: lo han hecho por hobby, así que puede tener algún bug pequeño (no de seguridad). Sigue `kit/CLAUDE.md` desde la fase 0: mira mi sistema, hazme las preguntas, lístame lo que trae y pregúntame qué quiero instalar, y pregúntame también cuando no estés seguro de que algo me vaya a funcionar. No cambies nada global sin enseñarme antes el cambio. Ve apuntando todo en INFORME_MIGRACION.md.

5. Al terminar, tu Claude rellena `INFORME_MIGRACION.md`: mándaselo a quien te pasó el kit respondiendo a su correo (qué te llevaste, qué no y qué no funcionó). Copia en él la línea de `kit/VERSION.txt`.

## Después
- **`actualiza kit >`**: trae la versión nueva, te enseña qué cambió (`CAMBIOS.md`) y aplica solo eso, sin pisar lo que hayas cambiado tú.
- **`desinstalar kit >`**: quita lo del kit (todo o por partes) sin tocar lo tuyo.

## Lo más útil, en una línea
- **Status line**: ves en todo momento modelo, $ gastado, % del límite de 5 h y semanal, y % de contexto.
- **`costlog> 4 5 nota`** al acabar una sesión: apunta coste, tiempo, modelo y tu nota en un CSV, sin tokens. Con el tiempo sabes qué modelo/esfuerzo merece cada tarea.
- **`blocklog> cómo se arregló`**: apunta los bloqueos de permisos del modo auto con el error exacto.
- **`_<carpeta>: tarea`**: trabaja solo en esa carpeta (la encuentra un script por nombre, también con niveles: `_prog_p2:`).
- **`qq > pregunta`**: pregunta rápida que no cambia nada (`prog_p2 qq > …` = pregunta sobre esa carpeta).
- **md2pdf**: apuntes/resúmenes en Markdown con fórmulas → PDF bonito.
- **moodle** (módulo): `moodle >` te dice qué hay nuevo, avisos, entregas y fechas, sin abrir el navegador.
- **asignaturas** (módulo): un "tutor" por asignatura, con comandos de estudio orientados a examen.
- **keep-awake** (Windows): el portátil no se suspende mientras Claude trabaja (baja el brillo en su lugar).
- **transcribe**: audios de WhatsApp o grabaciones de clase → texto, en local y gratis.
- **guias/**: lo aprendido sobre permisos, calendario, email, Wuolah, Instinct, Overleaf…
