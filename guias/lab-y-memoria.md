# La carpeta laboratorio y la memoria de Claude

## La carpeta "learning claude" (aquí: tu carpeta lab)
No es solo para aprender Claude: es un **sandbox para experimentar con Claude y mejorarlo**:
- Probar cosas de las que aún no estás seguro (flujos, ideas, prototipos).
- Mejorar Claude: conectores (MCP), plugins, skills, hooks, settings.
- Revisar cómo le pides las cosas y qué reglas sigue.
- Mantener limpia su memoria: qué va en `~/.claude/CLAUDE.md` (global), en el CLAUDE.md de cada proyecto y en la auto-memoria, sin repetir lo mismo en dos sitios.

Normas que funcionan:
- **Cada experimento en su subcarpeta** con un `README.md` (qué se probó, qué funcionó, qué no y **por qué**, para no repetirlo). Si se abandona, se apunta el motivo ahí.
- Antes de cambiar algo global (`~/.claude/CLAUDE.md`, `~/.claude/settings.json`, MCP o plugins a nivel usuario), Claude dice qué cambia y por qué, y espera tu OK.
- Cuando algo funciona y merece quedarse, decidir **dónde vive**: regla para todos los proyectos → CLAUDE.md global; procedimiento largo que se usa a veces → skill; algo que tiene que pasar siempre, sin tokens → hook; un hecho o preferencia → memoria. No dejarlo solo en la carpeta del experimento.
- El CLAUDE.md del lab lleva una sección **Contents** con una línea por carpeta/fichero (qué es y su estado).
- Registro de coste (`costlog>`) y de bloqueos (`blocklog>`), para decidir con datos qué modelo/esfuerzo usar.

## Cómo juzgar cualquier propuesta: eficacia → eficiencia → simpleza
En este orden: **eficacia** (¿da mejor resultado?), **eficiencia** (¿gasta menos tokens/tiempo?), **simpleza** (¿es más fácil de usar y mantener?). Veredicto corto de cada una. **Nunca recortar coste si baja la calidad**: medir antes de recomendar un ahorro, y preferir comprobaciones gratis y deterministas (scripts) a pasar trabajo a un modelo más barato.
- Evidencia: se probó pasar la skill de md2pdf a un subagente Sonnet para ahorrar; costó 3–8× más que hacerlo en la conversación con Opus y se le escaparon fallos que Opus había visto.

## Modelos y esfuerzo
- Opus para lo difícil (razonamiento, depuración no trivial, cambios en muchos ficheros, ejercicios/exámenes), Sonnet/Haiku para lo simple (eventos, borradores, ediciones pequeñas). Esfuerzo por modelo en `~/.claude/settings.json` → `modelSettings.<modelo>.effortLevel`.
- Regla útil en el CLAUDE.md global: si Claude **no** es Opus y aparece una señal concreta (el mismo arreglo falla dos veces, le corriges dos veces lo mismo, no puede verificar el resultado, está adivinando), que lo diga y recomiende `/model opus` en vez de entregar algo flojo.
- Haiku 4.5 no tenía esfuerzo; Haiku 5.5 sí.
- `/btw` (pregunta lateral) se queda en el contexto hasta el siguiente `/clear`: no es gratis.

## La auto-memoria
Claude Code guarda memoria por proyecto en `~/.claude/projects/<proyecto>/memory/`: un fichero por hecho con frontmatter (`name`, `description`, `type: user|feedback|project|reference`) y un índice `MEMORY.md` con una línea por memoria.
- `feedback` = cómo quieres que trabaje (correcciones y lo que funcionó), con **Why:** y **How to apply:**.
- `project` = trabajo en curso, decisiones, incidentes (con fechas absolutas, nunca "ayer").
- `reference` = enlaces, IDs, dónde está algo.
- Antes de guardar, buscar si ya hay una que lo cubra y actualizarla; borrar las que resulten falsas; no guardar lo que ya está en el código, el git o un CLAUDE.md. Enlazar memorias relacionadas con `[[nombre]]`.
- Ejemplos útiles: "cuando el usuario tenga que editar settings.json, abrírselo en el Bloc de notas y darle el texto exacto y la línea"; "calidad antes que coste, con la evidencia".

## Lista `leftover` (gastar el límite semanal que sobra)
Fichero `leftover.md` en el lab con tareas autocontenidas (rutas absolutas, proyecto, qué es "hecho") para cuando sobra límite antes del reinicio semanal. Comandos: `leftover add> <tarea>` (solo añadir), `leftover >` (ver), `leftover n>` (hacer los n primeros pasos, **cada uno en su propio subagente, uno detrás de otro** para tener contexto limpio, y apuntar cada paso con `costlog.py --mark` antes y `--leftover …` después). Plantilla en `plantillas/leftover.md`.
