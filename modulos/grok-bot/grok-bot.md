# Grok Bot + Claude Code — un "bot" por asignatura en los dos

<!-- Módulo `grok-bot` del kit: para quien ya usa un agente siempre encendido (Grok Bot u otro parecido). El autor del kit no usa Grok Bot: lo de abajo sale de reseñas de terceros de oct 2026 (vellum.ai, composio.dev, digitalapplied.com, aitoolsreview.co.uk), así que compruébalo en la app. -->

## Qué es cada uno

| | Grok Bot (xAI) | Claude Code + este kit |
|---|---|---|
| Dónde corre | Un ordenador virtual en la nube de xAI, **siempre encendido** (aunque tu PC esté apagado); apps de escritorio y móvil | Tu PC, sobre tus carpetas |
| Varios "bots" | Bots con nombre, cada uno con su rol; uno puede hacer de jefe y repartir a los demás | **Una carpeta por asignatura con su `CLAUDE.md`** = un tutor por asignatura. Arrancar Claude dentro de esa carpeta = hablar con ese bot, con su propio historial; `_<asig>:` desde cualquier sitio |
| Ficheros | Los de la máquina virtual, **compartida por todos tus Bots** | Los tuyos, en tu disco o tu Google Drive |
| Memoria | Interna: no se puede ver, corregir ni exportar una a una | Ficheros que lees y editas: `CLAUDE.md`, `Main sources.md`, `calendar.md`, la memoria de Claude |
| Programado | Rutinas por horario o por evento | Solo cuando abres Claude (o un hook) |
| Seguridad | Los Bots comparten máquina, navegador y credenciales: no son compartimentos estancos | Lo que permitas en `settings.json` |

## Reparto propuesto (decídelo con <Nombre>)
- **La fuente de verdad es la carpeta de la asignatura** (`Main sources.md`, `calendar.md`, apuntes). Un dato nuevo que traiga un Bot se apunta ahí. Los Bots no deberían llevar su propia versión de fechas o evaluación, porque acabarían diciendo cosas distintas.
- **Grok Bot: lo que necesita estar siempre encendido o en el móvil.** Mirar Moodle y los avisos cada día y avisarte al móvil, recordatorios, dudas rápidas desde el móvil, rutinas programadas.
- **Claude Code: lo que toca tus ficheros.** `moodle >` (descarga por API y archiva en la carpeta de cada asignatura, sin navegador), apuntes en PDF (`create notes|ejs|esq`), corregir ejercicios (`help ejs`), labs e informes, calendario.
- **Nada dos veces.** Que Moodle lo descargue uno solo (Claude, porque los ficheros tienen que acabar en tu carpeta); el Bot, como mucho, avisa. Lo mismo con el calendario: lo lleva uno.
- Apunta el reparto en la tabla *Otro agente* del `CLAUDE.md` del curso (módulo `asignaturas`) y en el `CLAUDE.md` de cada asignatura (línea *Grok Bot de esta asignatura*).

## Pasar lo que sabe cada Bot a su carpeta (fase 7, una vez por Bot)
Como la memoria del Bot no se puede exportar, se le pide un volcado. <Nombre> le pega esto a cada Bot:

> Hazme un volcado completo de todo lo que sabes de <asignatura> para pasárselo a otro asistente. Incluye: profesor(es) y su contacto; qué material sigue el curso y dónde está; evaluación y pesos; fechas (exámenes, entregas, labs, recuperaciones, cancelaciones), cada una con su fuente y si está confirmada; qué exámenes pasados, problemas o apuntes tienes y de dónde salieron; qué te he pedido que hagas siempre (rutinas, formato, idioma, cómo explicarme); y qué tareas haces tú solo y cada cuánto. Marca "(sin confirmar)" lo que no sepas seguro. No inventes nada: si no lo sabes, dilo.

<Nombre> te pasa la respuesta (pegada en el chat, o guardada como `<Asig>/00_Syllabus & Schedule/_grok_volcado_<AAAA-MM-DD>.md`). Entonces:
1. **Repártela:** fechas → `calendar.md` (y `Main sources.md` si son exámenes); evaluación, fuentes y material de examen → `Main sources.md`; cómo quiere que le expliquen → `CLAUDE.md` de la asignatura; rutinas del Bot → tabla *Otro agente*.
2. Cada dato con **`fuente: Grok Bot <nombre>, <fecha>`**. Lo que el Bot marque sin confirmar, igual.
3. **Si choca** con lo que ya hay (p. ej. lo que ya había en la carpeta), no elijas tú: enséñale las dos versiones y pregunta.
4. Las fechas confirmadas, al calendario (fase 6), con sus reglas; antes, busca que no estén ya (el Bot puede haberlas metido).

## Puente entre los dos (solo si hace falta; sin probar)
- Si la carpeta de la uni está en **Google Drive** y los Bots pueden leer Drive: dile a cada Bot que lea el `Main sources.md` y el `calendar.md` de su asignatura antes de contestar sobre fechas o evaluación (dale la ruta). Así hay una sola versión.
- Si un Bot descarga algo, que lo deje en `<Asig>/_grok/` en Drive; el paso 2 de `<Asig> >` lo encuentra y propone dónde archivarlo.
- Si se monta, apunta en el informe qué funcionó.

## Cuidado
- **No pongas en la máquina de Grok** el token de Moodle (`~/.moodle-token`) ni los tokens del MCP de Google: todos los Bots los verían.
- Al borrar un Bot pueden quedar sus logins y ficheros: revoca el acceso en cada servicio.
- Si te interesa comparar con otro agente de este tipo, `kit/guias/instinct.md` es el que está probando el autor del kit.
