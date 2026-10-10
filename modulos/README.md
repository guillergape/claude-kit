# Módulos opcionales

Lo que solo le sirve a parte de la gente. La guía (`kit/CLAUDE.md`, fase 0) los ofrece **según las respuestas** de `kit-datos.yaml`; nunca se instalan sin preguntar. Cada uno se apunta en `modulos:` de `kit-datos.yaml`.

| Módulo | Qué es | Se ofrece si… | Fase |
|---|---|---|---|
| `moodle/` | Skill: Moodle por API (novedades, avisos, entregas, fechas, descargas), sin navegador | `MOODLE_URL` no está vacío | 3 |
| `uc3m/` | Preconfigura `moodle` para Aula Global + guías docentes, calendario de exámenes y Wuolah de la UC3M | `UNI` es la UC3M | 3 y 7 |
| `asignaturas/` | Un "tutor" por asignatura: `CLAUDE.md` del curso (comandos de estudio, estructura, estudio orientado a examen) + `CLAUDE.md` y `Main sources.md` por asignatura | estudia y quiere organizar las asignaturas con Claude | 7 |
| `grok-bot/` | Repartir el trabajo con otro agente siempre encendido (Grok Bot…) y volcar lo que sabe a las carpetas | `otro_agente` no está vacío | 7 |

Para añadir un módulo al kit: carpeta nueva aquí con un README (qué es, cuándo se ofrece, qué instala), una fila en esta tabla, su paso en la fase que toque de `kit/CLAUDE.md` y una entrada en `CAMBIOS.md`. Nada personal: solo datos públicos y marcadores (`<Nombre>`, `<UNI>`…).
